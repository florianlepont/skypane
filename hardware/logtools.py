#!/usr/bin/env python3
"""hardware/logtools.py — stdlib-only log timestamper and backoff-sequence
checker for captured SkyPane serial logs.

Subcommands:
  stamp          Prefix stdin lines with a wall-clock ISO-8601 timestamp,
                 flushing after every line. Sits at the head of a
                 multi-hour capture pipeline (firmware/monitor.sh | stamp
                 > log), so a block-buffered writer would otherwise
                 cluster every timestamp at the moment the pipe closes —
                 destroying the interval evidence this whole plan exists
                 to collect.

  check-backoff  Read one or more captured logs (concatenated in the
                 order given) and decide whether they show a real
                 exponential backoff — as opposed to a fixed-interval
                 retry, or a failure counter that resets whenever the
                 device loses power. Prints one PASS/FAIL/SKIP line per
                 check plus a summary line, and exits 0 only when every
                 check passed.

  from-journal   Convert journalctl -o short-iso output into the
                 bracketed [ISO-8601] shape check-battery already
                 parses, reading from the given file paths (concatenated
                 in order) or from stdin when none are given. Writes
                 converted lines to stdout only; journal markers and
                 lines that fail conversion are dropped, with a single
                 dropped-line count written to stderr. Bridges the
                 production server's journald record onto the exact
                 checker that was written for a locally captured pipe.

  check-battery  Read one or more captured server stdout logs — stamped
                 locally by `stamp`, or converted from journald by
                 `from-journal` — (concatenated in the order given) and
                 decide whether they show a valid unattended battery
                 discharge run, as opposed to a run interrupted by a
                 sleeping host or a pack that was never actually off USB
                 power. Also computes the D-07 mAh-per-cycle figure and
                 a two-ended projection band for candidate wake
                 intervals. In gated mode (the default) prints one
                 PASS/FAIL line per check plus a summary line and exits
                 0 only when every check passed. In --status mode,
                 prints the same derived figures with no gating at all
                 and always exits 0 — the daily check-in command, which
                 must never fail a developer's routine glance just
                 because the run has not finished yet.

  selftest       Run check-backoff against the three fixtures under
                 hardware/fixtures/, and check-battery against four
                 more (including a from-journal-converted one), each
                 with the flags it is meant to be judged under, and
                 assert the good ones are accepted while the bad ones
                 are rejected. A checker that has never been shown a
                 bad log has not been tested.

Only argparse, datetime, os, re, subprocess and sys are imported — no pip
install, matching this phase's zero-external-install property.
"""
import argparse
import datetime
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
FIXTURES_DIR = os.path.join(HERE, "fixtures")

# The exponential-backoff curve: min(2^n * 5min, 6h). This table is what
# this script CHECKS a captured device log against — it is not the
# definition of the curve. The curve itself is defined and asserted
# across its whole input domain (including n=255, no overflow) in
# firmware/main/backoff.c, proven by firmware/tests/run_host_tests.sh.
# If this table and backoff.c ever disagree, fix this table to match
# backoff.c, not the other way around.
CURVE_TABLE = {
    0: 300,
    1: 600,
    2: 1200,
    3: 2400,
    4: 4800,
    5: 9600,
    6: 19200,
}
CURVE_CAP_S = 21600  # n >= 7


def curve_seconds(n):
    return CURVE_TABLE.get(n, CURVE_CAP_S)


# --- Log Line Contract parsing (firmware/VENDOR.md "## Log Line Contract") ---
#
# Every line may carry a host-added `[ISO-8601]` prefix from `stamp` and
# an ESP log prefix (e.g. "I (746) skypane: ") before the contract
# text, so every pattern below is applied with .search(), not .match().

TS_RE = re.compile(r"^\[([^\]]+)\]")

# journalctl -o short-iso line shape (see `from-journal` below):
#   2026-08-01T00:00:00+0200 hostname python3[1234]:   telemetry: ...
# Group 1 is the timestamp (offset may be Z, +HHMM or +HH:MM); the
# hostname and syslog identifier (with an optional bracketed pid) are
# matched but not captured, since the identifier is derived from the
# interpreter binary journald ran (e.g. "python3"), not any fixed
# script name, and must not be pinned to a particular value. Group 2 is
# the rest of the line, i.e. whatever the unit actually printed to
# stdout, preserved exactly including its own leading whitespace.
JOURNAL_RE = re.compile(
    r"^([0-9]{4}-[0-9]{2}-[0-9]{2}[T ][0-9]{2}:[0-9]{2}:[0-9]{2}"
    r"(?:\.[0-9]+)?(?:Z|[+-][0-9]{2}:?[0-9]{2})?)"
    r"\s+\S+\s+[^\s:]+(?:\[\d+\])?:\s?(.*)$"
)

WAKE_RE = re.compile(r"wake reason=([\w-]+) boot_count=(\d+)")
POLL_OK_RE = re.compile(r"poll ok sleep_s=(\d+) hash_skip=([01])")
POLL_FAIL_RE = re.compile(r"poll fail step=(\w+) backoff_n=(\d+) sleep_s=(\d+)")
SLEEP_ENTER_RE = re.compile(r"sleep enter sleep_s=(\d+)")

# The stub server (stub-server/byos_server.py, log_telemetry()) prints
# battery telemetry on its own line, e.g.:
#   "  telemetry: X-Fw-Version=0.1.0-p1 X-Boot-Reason=power-on X-Rssi=-52 X-Battery-Mv=4150"
# after `stamp` has prefixed it with "[ISO-8601] ". The token is searched
# for anywhere in the line, tolerating whatever separator/surrounding
# text the upstream server code emits, rather than matched against a
# reformatted expectation.
BATTERY_MV_RE = re.compile(r"X-Battery-Mv\D*(\d+)")


class Event(object):
    __slots__ = ("kind", "ts", "line", "fields")

    def __init__(self, kind, ts, line, **fields):
        self.kind = kind
        self.ts = ts
        self.line = line
        self.fields = fields

    def __repr__(self):
        return "Event(%s, %r)" % (self.kind, self.fields)


def parse_timestamp(line):
    m = TS_RE.match(line)
    if not m:
        return None
    try:
        return datetime.datetime.fromisoformat(m.group(1))
    except ValueError:
        return None


def normalize_journal_timestamp(raw):
    """Normalize a journalctl short-iso timestamp so it satisfies
    datetime.datetime.fromisoformat() the same way on every Python
    release this project might run under. Two changes only, nothing
    else: a trailing "Z" becomes "+00:00", and a four-digit offset
    written without a colon (e.g. "+0200") gains one ("+02:00").
    fromisoformat() before Python 3.11 rejects both of those raw forms;
    normalizing them here removes the whole question of which minor
    version the developer's machine or the VPS happens to run. No
    timezone conversion and no fractional-second truncation happen
    here - the instant in time is left exactly as journald recorded it.
    """
    if raw.endswith("Z"):
        return raw[:-1] + "+00:00"
    m = re.search(r"[+-][0-9]{2}[0-9]{2}$", raw)
    if m:
        offset = m.group(0)
        return raw[:m.start()] + offset[:3] + ":" + offset[3:]
    return raw


def parse_line(line):
    """Return an Event for the first Log Line Contract shape this line
    matches, or None if it matches none of them.
    """
    ts = parse_timestamp(line)

    m = WAKE_RE.search(line)
    if m:
        return Event("wake", ts, line, reason=m.group(1), boot_count=int(m.group(2)))

    m = POLL_OK_RE.search(line)
    if m:
        return Event("poll_ok", ts, line, sleep_s=int(m.group(1)), hash_skip=int(m.group(2)))

    m = POLL_FAIL_RE.search(line)
    if m:
        return Event("poll_fail", ts, line, step=m.group(1),
                      backoff_n=int(m.group(2)), sleep_s=int(m.group(3)))

    m = SLEEP_ENTER_RE.search(line)
    if m:
        return Event("sleep_enter", ts, line, sleep_s=int(m.group(1)))

    return None


def load_events(paths):
    events = []
    for path in paths:
        with open(path, "r", errors="replace") as fh:
            for line in fh:
                ev = parse_line(line)
                if ev is not None:
                    events.append(ev)
    return events


# --- Checks -----------------------------------------------------------


class CheckResult(object):
    def __init__(self, name, status, reason=""):
        self.name = name
        self.status = status  # "PASS" | "FAIL" | "SKIP"
        self.reason = reason

    def line(self):
        if self.status == "PASS":
            return "PASS %s" % self.name
        if self.status == "SKIP":
            return "SKIP %s - %s" % (self.name, self.reason)
        return "FAIL %s - %s" % (self.name, self.reason)


def check_min_steps(events, min_steps):
    name = "at least %d failed polls are present" % min_steps
    fails = [e for e in events if e.kind == "poll_fail"]
    if len(fails) >= min_steps:
        return CheckResult(name, "PASS")
    return CheckResult(name, "FAIL", "only %d failed poll(s) found" % len(fails))


def check_curve(events):
    name = "every failed poll's interval matches the curve for its own counter"
    for e in events:
        if e.kind != "poll_fail":
            continue
        expected = curve_seconds(e.fields["backoff_n"])
        if e.fields["sleep_s"] != expected:
            return CheckResult(name, "FAIL",
                "backoff_n=%d reported sleep_s=%d, curve requires %d (line: %r)" %
                (e.fields["backoff_n"], e.fields["sleep_s"], expected, e.line.rstrip()))
    return CheckResult(name, "PASS")


def check_sequence(events):
    name = "failed-poll counters form a gapless sequence, reset only by a success"
    expected = 0
    for e in events:
        if e.kind == "poll_ok":
            expected = 0
        elif e.kind == "poll_fail":
            if e.fields["backoff_n"] != expected:
                return CheckResult(name, "FAIL",
                    "expected backoff_n=%d, got %d (line: %r)" %
                    (expected, e.fields["backoff_n"], e.line.rstrip()))
            expected += 1
    return CheckResult(name, "PASS")


def check_distinct_intervals(events):
    name = "at least four distinct sleep intervals across failed polls"
    intervals = sorted(set(e.fields["sleep_s"] for e in events if e.kind == "poll_fail"))
    if len(intervals) >= 4:
        return CheckResult(name, "PASS")
    return CheckResult(name, "FAIL", "only %d distinct interval(s) seen: %s" %
        (len(intervals), intervals))


def check_sleep_entry_follows(events):
    name = "every failed poll is immediately followed by a matching sleep-entry event"
    for i, e in enumerate(events):
        if e.kind != "poll_fail":
            continue
        nxt = events[i + 1] if i + 1 < len(events) else None
        if nxt is None or nxt.kind != "sleep_enter":
            return CheckResult(name, "FAIL",
                "no sleep-entry event immediately follows failed poll (line: %r)" %
                e.line.rstrip())
        if nxt.fields["sleep_s"] != e.fields["sleep_s"]:
            return CheckResult(name, "FAIL",
                "failed poll armed sleep_s=%d but the following sleep-entry reported "
                "sleep_s=%d (line: %r)" %
                (e.fields["sleep_s"], nxt.fields["sleep_s"], e.line.rstrip()))
    return CheckResult(name, "PASS")


def check_wall_clock(events, tolerance_pct):
    name = "wall-clock gap between wakes matches the previously armed interval within tolerance"
    if not any(e.ts is not None for e in events):
        return CheckResult(name, "SKIP", "no timestamps present in the supplied logs")

    armed = None
    last_wake = None
    for e in events:
        if e.kind == "sleep_enter":
            armed = e
        elif e.kind == "wake":
            if last_wake is not None and armed is not None and \
                    e.ts is not None and last_wake.ts is not None:
                gap = (e.ts - last_wake.ts).total_seconds()
                interval = armed.fields["sleep_s"]
                lo = interval * (1 - tolerance_pct / 100.0)
                hi = interval * (1 + tolerance_pct / 100.0) + 60
                if not (lo <= gap <= hi):
                    return CheckResult(name, "FAIL",
                        "gap of %.0fs between consecutive wakes falls outside "
                        "[%.0f, %.0f]s for the armed interval of %ds (wake line: %r)" %
                        (gap, lo, hi, interval, e.line.rstrip()))
            last_wake = e
    return CheckResult(name, "PASS")


def check_persist(events):
    name = "a power-on wake persists a non-zero backoff counter across the power cycle"
    found = False
    for i, e in enumerate(events):
        if e.kind == "wake" and e.fields["reason"] == "power-on":
            nxt = events[i + 1] if i + 1 < len(events) else None
            if nxt is not None and nxt.kind == "poll_fail":
                if nxt.fields["backoff_n"] == 0:
                    return CheckResult(name, "FAIL",
                        "power-on wake (line: %r) was followed by backoff_n=0 - the "
                        "counter did not survive the power cycle" % e.line.rstrip())
                found = True
    if not found:
        return CheckResult(name, "FAIL",
            "no power-on wake was followed by a failed poll")
    return CheckResult(name, "PASS")


def check_reset(events):
    name = "a successful poll is followed later by a failed poll reset to counter 0 / 300s"
    seen_success = False
    for e in events:
        if e.kind == "poll_ok":
            seen_success = True
        elif e.kind == "poll_fail" and seen_success:
            if e.fields["backoff_n"] == 0 and e.fields["sleep_s"] == 300:
                return CheckResult(name, "PASS")
    return CheckResult(name, "FAIL",
        "no failed poll reporting backoff_n=0 sleep_s=300 was found after a successful poll")


# --- Battery discharge-run analysis (D-07) ------------------------------
#
# check-battery reads captured stub-server stdout (not device console
# output) and treats every timestamped line carrying an X-Battery-Mv
# telemetry reading as one observed poll, and therefore one observed
# wake - the device polls exactly once per wake, so this log doubles as
# a wake counter and a voltage log.


class BatteryPoll(object):
    __slots__ = ("ts", "mv", "line")

    def __init__(self, ts, mv, line):
        self.ts = ts
        self.mv = mv
        self.line = line


def load_battery_polls(paths):
    """Return (all_matches, polls): all_matches is the count of lines
    carrying an X-Battery-Mv token regardless of whether they also carry
    a timestamp; polls is the list of BatteryPoll for the lines that
    carry both. The distinction lets check_timestamps_and_min_polls tell
    "no battery telemetry at all" apart from "battery telemetry present,
    but the stamp filter (for a local capture) or the from-journal
    conversion step (for a server-side capture) was left out of the
    pipeline".
    """
    all_matches = 0
    polls = []
    for path in paths:
        with open(path, "r", errors="replace") as fh:
            for line in fh:
                m = BATTERY_MV_RE.search(line)
                if not m:
                    continue
                all_matches += 1
                ts = parse_timestamp(line)
                if ts is not None:
                    polls.append(BatteryPoll(ts, int(m.group(1)), line))
    return all_matches, polls


def compute_battery_stats(polls, interval_s, capacity_mah, boot_start, boot_end):
    """Compute the derived figures from a list of BatteryPoll, in the
    order given (assumed chronological, matching the order the logs
    were concatenated in). Uses windowed means (first/last tenth of
    samples) rather than single first/last readings, because a single
    instantaneous reading taken while the radio is transmitting is
    noisy enough to mislead on its own.
    """
    observed = len(polls)
    first, last = polls[0], polls[-1]
    span_s = (last.ts - first.ts).total_seconds()
    span_days = span_s / 86400.0
    nominal = (span_s / interval_s) if interval_s else 0.0
    coverage = (observed / nominal) if nominal > 0 else 0.0

    max_gap = 0.0
    for a, b in zip(polls, polls[1:]):
        gap_s = (b.ts - a.ts).total_seconds()
        gap_intervals = (gap_s / interval_s) if interval_s else 0.0
        if gap_intervals > max_gap:
            max_gap = gap_intervals

    tenth = max(1, observed // 10)
    open_mv = sum(p.mv for p in polls[:tenth]) / float(tenth)
    close_mv = sum(p.mv for p in polls[-tenth:]) / float(tenth)
    drop_mv = open_mv - close_mv
    last_mv = last.mv

    boot_delta = None
    if boot_start is not None and boot_end is not None:
        boot_delta = boot_end - boot_start

    if boot_delta is not None:
        cycle_count, cycle_source = boot_delta, "device boot-counter delta"
    elif observed > 0:
        cycle_count, cycle_source = observed, "observed poll count"
    else:
        cycle_count, cycle_source = nominal, "nominal count"

    mah_per_day = (capacity_mah / span_days) if span_days > 0 else None
    mah_per_cycle = (capacity_mah / cycle_count) if cycle_count else None

    return {
        "first_ts": first.ts, "last_ts": last.ts,
        "span_s": span_s, "span_days": span_days,
        "observed": observed, "nominal": nominal, "coverage": coverage,
        "max_gap": max_gap,
        "open_mv": open_mv, "close_mv": close_mv, "drop_mv": drop_mv,
        "last_mv": last_mv,
        "boot_delta": boot_delta,
        "cycle_count": cycle_count, "cycle_source": cycle_source,
        "mah_per_day": mah_per_day, "mah_per_cycle": mah_per_cycle,
    }


def check_timestamps_and_min_polls(all_matches, polls):
    name = "logs carry timestamps and at least two battery-bearing polls"
    if not all_matches:
        return CheckResult(name, "FAIL",
            "no X-Battery-Mv telemetry found in the supplied log(s)")
    if not polls:
        return CheckResult(name, "FAIL",
            "battery telemetry is present but no line carries a timestamp "
            "- the stamp filter (local capture) or the from-journal "
            "conversion step (server-side capture) was left out of the "
            "pipeline, destroying the elapsed-time evidence")
    if len(polls) < 2:
        return CheckResult(name, "FAIL",
            "only %d timestamped battery poll(s) found, need at least 2" %
            len(polls))
    aware = sum(1 for p in polls if p.ts.tzinfo is not None)
    if 0 < aware < len(polls):
        return CheckResult(name, "FAIL",
            "%d of %d timestamped polls carry timezone-offset information "
            "and %d do not - this is almost always a stamp-produced log "
            "(no offset) concatenated with a from-journal-converted one "
            "(carries an offset); analyse them as what they are rather "
            "than as one consistent series" %
            (aware, len(polls), len(polls) - aware))
    return CheckResult(name, "PASS")


def check_span(stats, min_days):
    name = "run spans at least %g day(s)" % min_days
    if stats["span_days"] >= min_days:
        return CheckResult(name, "PASS")
    return CheckResult(name, "FAIL",
        "span is %.3f day(s) (%.0fs), need >= %g - a pack that empties "
        "inside a day is not a battery-life result" %
        (stats["span_days"], stats["span_s"], min_days))


def check_coverage(stats, min_coverage):
    name = "coverage is at least %.2f" % min_coverage
    if stats["coverage"] >= min_coverage:
        return CheckResult(name, "PASS")
    return CheckResult(name, "FAIL",
        "coverage is %.3f (observed=%d, nominal=%.1f), below %.2f - the "
        "frame losing home Wi-Fi or internet, the server unit restarting, "
        "or journald having rotated the earliest entries out of the "
        "window being converted are the likely causes" %
        (stats["coverage"], stats["observed"], stats["nominal"], min_coverage))


def check_max_gap(stats, max_gap_intervals):
    name = "no gap between consecutive polls exceeds %g interval(s)" % max_gap_intervals
    if stats["max_gap"] <= max_gap_intervals:
        return CheckResult(name, "PASS")
    return CheckResult(name, "FAIL",
        "largest gap between consecutive polls is %.2f interval(s), "
        "exceeds %g" % (stats["max_gap"], max_gap_intervals))


def check_mv_drop(stats, min_mv_drop):
    name = "millivolt drop between opening and closing windows is at least %d mV" % min_mv_drop
    if stats["drop_mv"] >= min_mv_drop:
        return CheckResult(name, "PASS")
    return CheckResult(name, "FAIL",
        "drop is %.1f mV (opening mean=%.1f, closing mean=%.1f), below "
        "%d mV - the pack may never have left USB power" %
        (stats["drop_mv"], stats["open_mv"], stats["close_mv"], min_mv_drop))


def check_depleted(stats, cutoff_mv):
    name = "last observed millivolt reading is at or below the %d mV cutoff" % cutoff_mv
    if stats["last_mv"] <= cutoff_mv:
        return CheckResult(name, "PASS")
    return CheckResult(name, "FAIL",
        "last observed reading is %d mV, above the %d mV cutoff - the "
        "run did not end by depletion" % (stats["last_mv"], cutoff_mv))


def check_boot_reconciliation(stats, min_coverage):
    name = "device boot-counter delta does not exceed observed polls by more than 1/min-coverage"
    delta = stats["boot_delta"]
    observed = stats["observed"]
    limit = (observed * (1.0 / min_coverage)) if min_coverage else float("inf")
    if delta <= limit:
        return CheckResult(name, "PASS")
    return CheckResult(name, "FAIL",
        "boot-counter delta is %d, observed polls is %d, limit is %.2f - "
        "the device woke far more often than it polled, i.e. it was "
        "waking and failing, not waking and polling" %
        (delta, observed, limit))


def print_battery_derived(stats, interval_s):
    print("span: %.3f day(s) (%.0fs), from %s to %s" %
        (stats["span_days"], stats["span_s"], stats["first_ts"].isoformat(),
         stats["last_ts"].isoformat()))
    boot_part = ""
    if stats["boot_delta"] is not None:
        boot_part = " device-boot-delta=%d" % stats["boot_delta"]
    print("cycle counts: observed=%d nominal=%.2f%s" %
        (stats["observed"], stats["nominal"], boot_part))
    print("coverage: %.3f" % stats["coverage"])
    if stats["mah_per_day"] is not None:
        print("mAh/day: %.2f" % stats["mah_per_day"])
    if stats["mah_per_cycle"] is not None:
        print("mAh/cycle: %.3f (dividing by %s = %.2f cycles)" %
            (stats["mah_per_cycle"], stats["cycle_source"], stats["cycle_count"]))
    print("battery mV: opening window mean=%.1f closing window mean=%.1f "
        "drop=%.1f last=%d" %
        (stats["open_mv"], stats["close_mv"], stats["drop_mv"], stats["last_mv"]))
    print("projection band (days) for candidate wake intervals - lower "
        "bound assumes all drain is standing leakage (life unchanged), "
        "upper bound assumes all drain is per-wake (life scales linearly "
        "with the interval); a single-cadence run cannot separate the two:")
    for candidate in (300, 900, 3600):
        ratio = (candidate / float(interval_s)) if interval_s else 0.0
        per_wake_life = stats["span_days"] * ratio
        leakage_life = stats["span_days"]
        lo, hi = sorted((per_wake_life, leakage_life))
        print("  %5ds interval: %.2f-%.2f days" % (candidate, lo, hi))


# --- Subcommands --------------------------------------------------------


def cmd_stamp(_args):
    """Read stdin line-at-a-time, write each line to stdout prefixed with
    the local wall-clock time as ISO-8601 (second resolution), flushing
    after every line. Uses an explicit readline() loop rather than
    `for line in sys.stdin` so a line becomes visible the moment it is
    available on the pipe, independent of any readahead buffering.
    """
    while True:
        line = sys.stdin.readline()
        if not line:
            break
        ts = datetime.datetime.now().isoformat(timespec="seconds")
        out = "[%s] %s" % (ts, line)
        if not out.endswith("\n"):
            out += "\n"
        sys.stdout.write(out)
        sys.stdout.flush()


def cmd_from_journal(args):
    """Convert journalctl -o short-iso lines into the bracketed
    [ISO-8601] shape check-battery already parses, reading from the
    given file paths (concatenated in order) or from stdin when none
    are given, and writing converted lines to stdout only. Any input
    line that does not match the journal shape, or whose assembled
    output fails parse_timestamp(), is dropped rather than passed
    through - the durable record must never contain a line this script
    itself cannot vouch for. A single "from-journal: dropped N" summary
    is written to stderr so a redirect of stdout into the run log stays
    clean, and a silently truncated conversion still reads as visible.
    """
    def iter_lines():
        if args.logs:
            for path in args.logs:
                with open(path, "r", errors="replace") as fh:
                    for raw_line in fh:
                        yield raw_line
        else:
            for raw_line in sys.stdin:
                yield raw_line

    dropped = 0
    for raw_line in iter_lines():
        line = raw_line.rstrip("\n")
        m = JOURNAL_RE.match(line)
        if not m:
            dropped += 1
            continue
        ts_norm = normalize_journal_timestamp(m.group(1))
        message = m.group(2)
        out = "[%s] %s" % (ts_norm, message)
        if parse_timestamp(out) is None:
            dropped += 1
            continue
        sys.stdout.write(out + "\n")
    sys.stdout.flush()
    sys.stderr.write("from-journal: dropped %d line(s)\n" % dropped)
    return 0


def cmd_check_backoff(args):
    events = load_events(args.logs)
    results = [
        check_min_steps(events, args.min_steps),
        check_curve(events),
        check_sequence(events),
        check_distinct_intervals(events),
        check_sleep_entry_follows(events),
        check_wall_clock(events, args.tolerance),
    ]
    if args.expect_persist:
        results.append(check_persist(events))
    if args.expect_reset:
        results.append(check_reset(events))

    for r in results:
        print(r.line())

    total = len(results)
    passed = sum(1 for r in results if r.status in ("PASS", "SKIP"))
    print("backoff: %d/%d checks pass" % (passed, total))

    ok = all(r.status != "FAIL" for r in results)
    return 0 if ok else 1


def cmd_check_battery(args):
    all_matches, polls = load_battery_polls(args.logs)
    ts_check = check_timestamps_and_min_polls(all_matches, polls)

    if args.status:
        # Never gates, never fails - this is the daily check-in command.
        # Prints no PASS/FAIL lines at all, only the derived figures (or,
        # if there's not yet enough data, a plain one-line notice).
        if ts_check.status == "FAIL":
            print("battery: %s" % ts_check.reason)
            return 0
        stats = compute_battery_stats(polls, args.interval_s, args.capacity_mah,
                                       args.boot_start, args.boot_end)
        print_battery_derived(stats, args.interval_s)
        last_ts = polls[-1].ts
        # Converted (from-journal) timestamps carry a timezone offset;
        # stamp-produced ones do not. Subtracting an offset-carrying
        # timestamp from a naive "now" raises, and the daily check-in is
        # precisely the command that must never fail a routine glance.
        now = datetime.datetime.now(last_ts.tzinfo) if last_ts.tzinfo is not None \
            else datetime.datetime.now()
        age_s = (now - last_ts).total_seconds()
        print("age of last poll: %.0f s" % age_s)
        return 0

    results = [ts_check]
    if ts_check.status == "FAIL":
        for r in results:
            print(r.line())
        print("battery: %d/%d checks pass" % (0, len(results)))
        return 1

    stats = compute_battery_stats(polls, args.interval_s, args.capacity_mah,
                                   args.boot_start, args.boot_end)
    results.append(check_span(stats, args.min_days))
    results.append(check_coverage(stats, args.min_coverage))
    results.append(check_max_gap(stats, args.max_gap_intervals))
    results.append(check_mv_drop(stats, args.min_mv_drop))
    if args.expect_depleted:
        results.append(check_depleted(stats, args.cutoff_mv))
    if args.boot_start is not None and args.boot_end is not None:
        results.append(check_boot_reconciliation(stats, args.min_coverage))

    for r in results:
        print(r.line())

    total = len(results)
    passed = sum(1 for r in results if r.status in ("PASS", "SKIP"))
    print("battery: %d/%d checks pass" % (passed, total))

    print_battery_derived(stats, args.interval_s)

    ok = all(r.status != "FAIL" for r in results)
    return 0 if ok else 1


def _telemetry_messages(path):
    """Read a bracketed-timestamp log and return the stripped message
    text (everything after "] ") of every line carrying X-Battery-Mv,
    in file order. Used only by cmd_selftest's battery-journal case to
    compare a from-journal-converted fixture against battery-good.log.
    """
    out = []
    with open(path, "r", errors="replace") as fh:
        for line in fh:
            if not line.startswith("["):
                continue
            if "] " not in line:
                continue
            msg = line.split("] ", 1)[1].rstrip("\n")
            if "X-Battery-Mv" in msg:
                out.append(msg.strip())
    return out


def cmd_selftest(_args):
    """Run check-backoff and check-battery, each as a subprocess of this
    same script, against the fixtures under hardware/fixtures/ with the
    flags each one is meant to be judged under. Asserts every good
    fixture is accepted (exit 0) and every negative fixture is rejected
    (non-zero exit). Also converts battery-journal.log through
    from-journal and asserts the result is accepted and its telemetry
    messages are byte-identical (stripped) to battery-good.log's.
    """
    script_path = os.path.abspath(__file__)
    battery_common = ["--interval-s", "3600", "--min-days", "1",
                       "--capacity-mah", "3000"]
    cases = [
        ("check-backoff", "backoff-good.log",
         ["--expect-persist", "--expect-reset"], True),
        ("check-backoff", "backoff-fixed-interval.log", [], False),
        ("check-backoff", "backoff-rtc-reset.log",
         ["--expect-persist"], False),
        ("check-battery", "battery-good.log",
         battery_common + ["--expect-depleted"], True),
        ("check-battery", "battery-gap.log",
         battery_common + ["--expect-depleted"], False),
        ("check-battery", "battery-flat-mv.log",
         battery_common + ["--expect-depleted"], False),
    ]
    all_ok = True
    for command, fixture, flags, should_be_accepted in cases:
        path = os.path.join(FIXTURES_DIR, fixture)
        cmd = [sys.executable, script_path, command, path] + flags
        proc = subprocess.run(cmd, capture_output=True, text=True)
        actually_accepted = (proc.returncode == 0)
        requirement = "accepted" if should_be_accepted else "rejected"
        if actually_accepted == should_be_accepted:
            print("PASS %s (%s, as required)" % (fixture, requirement))
        else:
            all_ok = False
            print("FAIL %s (expected to be %s, actual exit code %d)" %
                  (fixture, requirement, proc.returncode))

    # battery-journal: convert via from-journal, then run check-battery
    # over the converted output exactly as a daily check-in would, and
    # additionally require its telemetry messages equal battery-good.log's
    # - proving the bridge is lossless for content the checker already
    # accepts, not merely that some output happened to pass.
    journal_path = os.path.join(FIXTURES_DIR, "battery-journal.log")
    tmp_path = os.path.join(
        os.environ.get("TMPDIR", "/tmp") or "/tmp",
        "logtools-selftest-battery-journal-%d.log" % os.getpid())
    conv = subprocess.run(
        [sys.executable, script_path, "from-journal", journal_path],
        capture_output=True, text=True)
    with open(tmp_path, "w") as fh:
        fh.write(conv.stdout)
    check_proc = subprocess.run(
        [sys.executable, script_path, "check-battery", tmp_path] +
        battery_common + ["--expect-depleted"],
        capture_output=True, text=True)
    journal_accepted = (check_proc.returncode == 0)
    converted_msgs = _telemetry_messages(tmp_path)
    good_msgs = _telemetry_messages(os.path.join(FIXTURES_DIR, "battery-good.log"))
    messages_match = (converted_msgs == good_msgs)
    os.remove(tmp_path)

    if journal_accepted and messages_match:
        print("PASS battery-journal.log (accepted via from-journal, "
              "telemetry messages match battery-good.log)")
    else:
        all_ok = False
        reasons = []
        if not journal_accepted:
            reasons.append("check-battery exit code %d" % check_proc.returncode)
        if not messages_match:
            reasons.append("converted telemetry messages differ from "
                            "battery-good.log (%d vs %d)" %
                            (len(converted_msgs), len(good_msgs)))
        print("FAIL battery-journal.log (%s)" % "; ".join(reasons))

    return 0 if all_ok else 1


# --- CLI ------------------------------------------------------------------


def build_parser():
    p = argparse.ArgumentParser(
        prog="logtools.py",
        description="Stdlib-only timestamper and backoff-sequence checker "
                     "for SkyPane captured serial logs.")
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("stamp",
        help="prefix stdin lines with a wall-clock ISO-8601 timestamp, flushed per line")

    fj = sub.add_parser("from-journal",
        help="convert journalctl -o short-iso lines into the bracketed "
             "[ISO-8601] shape check-battery parses")
    fj.add_argument("logs", nargs="*",
        help="log file path(s), read and concatenated in the order given; "
             "reads stdin when none are given")

    cb = sub.add_parser("check-backoff",
        help="check captured log(s) for a real exponential backoff curve")
    cb.add_argument("logs", nargs="+",
        help="log file path(s), read and concatenated in the order given")
    cb.add_argument("--min-steps", type=int, default=5,
        help="minimum number of failed polls required (default: 5)")
    cb.add_argument("--tolerance", type=float, default=15,
        help="wall-clock tolerance as a percentage (default: 15)")
    cb.add_argument("--expect-persist", action="store_true",
        help="require the counter to survive a power-on wake, non-zero")
    cb.add_argument("--expect-reset", action="store_true",
        help="require a success to reset the counter back to 0 / 300s")

    bat = sub.add_parser("check-battery",
        help="check captured server stdout - stamped locally or converted "
             "from journald via from-journal - for a valid unattended "
             "battery discharge run and compute the D-07 mAh/cycle figure")
    bat.add_argument("logs", nargs="+",
        help="log file path(s), read and concatenated in the order given")
    bat.add_argument("--capacity-mah", type=int, required=True,
        help="the pack's rated capacity in mAh")
    bat.add_argument("--interval-s", type=int, default=300,
        help="the server's configured sleep value in seconds (default: 300)")
    bat.add_argument("--min-days", type=float, default=1,
        help="minimum run span in days required (default: 1)")
    bat.add_argument("--min-coverage", type=float, default=0.95,
        help="minimum observed/nominal poll coverage required (default: 0.95)")
    bat.add_argument("--max-gap-intervals", type=float, default=3,
        help="maximum allowed gap between consecutive polls, in "
             "intervals (default: 3)")
    bat.add_argument("--min-mv-drop", type=int, default=100,
        help="minimum millivolt drop between opening and closing "
             "windows required (default: 100)")
    bat.add_argument("--cutoff-mv", type=int, default=3400,
        help="millivolt value at or below which the pack is considered "
             "depleted (default: 3400)")
    bat.add_argument("--boot-start", type=int, default=None,
        help="device NVS boot counter read before the run started")
    bat.add_argument("--boot-end", type=int, default=None,
        help="device NVS boot counter read after the run ended "
             "(post-mortem boot already subtracted out, if it incremented it)")
    bat.add_argument("--expect-depleted", action="store_true",
        help="require the run to have ended by depletion (last reading "
             "at or below --cutoff-mv)")
    bat.add_argument("--status", action="store_true",
        help="ungated daily check-in: print derived figures only, no "
             "PASS/FAIL gating, always exits 0")

    sub.add_parser("selftest",
        help="run check-backoff and check-battery against "
             "hardware/fixtures/*.log and assert outcomes")

    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    if args.command == "stamp":
        cmd_stamp(args)
        return 0
    if args.command == "from-journal":
        return cmd_from_journal(args)
    if args.command == "check-backoff":
        return cmd_check_backoff(args)
    if args.command == "check-battery":
        return cmd_check_battery(args)
    if args.command == "selftest":
        return cmd_selftest(args)
    return 1  # pragma: no cover — argparse enforces `required=True` above


if __name__ == "__main__":
    sys.exit(main())
