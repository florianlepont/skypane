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
                 Retained as the documented fallback for when
                 history.db is unreachable; from-history-db (below) is
                 the primary channel.

  from-history-db
                 Convert JSON-Lines device_health rows (one JSON object
                 per line, as printed by the canonical read-only remote
                 query documented in cmd_from_history_db()'s own comment
                 block) into the same bracketed [ISO-8601] shape
                 check-battery already parses, reading from the given
                 file paths (concatenated in order) or from stdin when
                 none are given. Writes converted lines to stdout only;
                 malformed or reading-less rows are dropped, with a
                 single dropped-line count written to stderr. This is
                 the primary observation channel: history.db's
                 device_health table is filled continuously and durably
                 by production, with no setup step of any kind.

  check-battery  Read one or more captured server stdout logs — stamped
                 locally by `stamp`, converted from journald by
                 `from-journal`, or converted from history.db by
                 `from-history-db` — (concatenated in the order given)
                 and decide whether they show a valid unattended battery
                 discharge run, as opposed to a run interrupted by a
                 sleeping host or a pack that was never actually off USB
                 power. Also computes the mAh-per-cycle figure and
                 a two-ended projection band for candidate wake
                 intervals. In gated mode (the default) prints one
                 PASS/FAIL line per check plus a summary line and exits
                 0 only when every check passed. In --status mode,
                 prints the same derived figures with no gating at all
                 and always exits 0 — the daily check-in command, which
                 must never fail a developer's routine glance just
                 because the run has not finished yet.

  run-report     Turn raw device_health JSON-Lines rows plus an owner-supplied
                 params file (--params) into a JSON report (--out) and a
                 human summary. Three verdicts stay separate - continuity,
                 voltage_validity, baseline - and the cycle count is
                 reconciled three ways (nominal, observed polls, device
                 boot-counter delta). Thresholds are the fixed
                 pre-registered values, with no flags to retune them.
                 Refuses with exit 2, writing no report, when a required
                 param is missing, no usable row exists, rows are out of
                 order, or rows predate the pre-registration time.
                 An optional reference_interval_s param (frozen from the
                 first 48 hours, see reference-interval) replaces the
                 configured interval as the unit of the coverage and gap
                 gates; the figures against the configured interval are
                 always reported alongside, as information.

  reference-interval  Compute the proposed reference interval from a raw
                 export: the mean poll-to-poll gap over the first 48 hours
                 after the first row, excluding gaps above 3 times the
                 configured interval, rounded half-up to whole seconds.
                 Prints the value, the gaps used and excluded and the
                 export's sha256. Refuses (exit 2) when the export covers
                 less than 48 hours or leaves too few gaps. Only the first
                 48 hours are ever read.

  selftest       Run check-backoff against the three fixtures under
                 hardware/fixtures/, and check-battery against five
                 more (including a from-journal-converted one and a
                 from-history-db-converted one) — eight fixtures in
                 total — each with the flags it is meant to be judged
                 under, and assert the good ones are accepted while the
                 bad ones are rejected. A checker that has never been
                 shown a bad log has not been tested.

Only argparse, datetime, hashlib, json, os, re, subprocess and sys are
imported - no pip install, matching this phase's zero-external-install
property. json parses from-history-db's JSON-Lines input and hashlib
fingerprints the raw export in run-report; sqlite3 is deliberately not
imported here — history.db lives on the VPS and is read over SSH, never
opened directly by this file.
"""
import argparse
import datetime
import hashlib
import json
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
    """Normalize a journalctl short-iso timestamp - or a device_health
    `ts` value, read by from-history-db - so it satisfies
    datetime.datetime.fromisoformat() the same way on every Python
    release this project might run under. Two changes only, nothing
    else: a trailing "Z" becomes "+00:00", and a four-digit offset
    written without a colon (e.g. "+0200") gains one ("+02:00").
    fromisoformat() before Python 3.11 rejects both of those raw forms;
    normalizing them here removes the whole question of which minor
    version the developer's machine or the VPS happens to run. No
    timezone conversion and no fractional-second truncation happen
    here - the instant in time is left exactly as journald (or
    device_health) recorded it. Both cmd_from_journal() and
    cmd_from_history_db() call this same function unchanged - no third
    normalization is required.
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


# --- Battery discharge-run analysis ------------------------------
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


def parse_battery_lines(lines):
    """Return (all_matches, polls) for an iterable of log lines, with the
    same meaning as load_battery_polls() has for a set of files.
    """
    all_matches = 0
    polls = []
    for line in lines:
        m = BATTERY_MV_RE.search(line)
        if not m:
            continue
        all_matches += 1
        ts = parse_timestamp(line)
        if ts is not None:
            polls.append(BatteryPoll(ts, int(m.group(1)), line))
    return all_matches, polls


def load_battery_polls(paths):
    """Return (all_matches, polls): all_matches is the count of lines
    carrying an X-Battery-Mv token regardless of whether they also carry
    a timestamp; polls is the list of BatteryPoll for the lines that
    carry both. The distinction lets check_timestamps_and_min_polls tell
    "no battery telemetry at all" apart from "battery telemetry present,
    but the stamp filter (for a local capture), the from-journal
    conversion step, or the from-history-db conversion step (for a
    server-side capture) was left out of the pipeline".
    """
    all_matches = 0
    polls = []
    for path in paths:
        with open(path, "r", errors="replace") as fh:
            file_matches, file_polls = parse_battery_lines(fh)
        all_matches += file_matches
        polls.extend(file_polls)
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
            "- the stamp filter (local capture), the from-journal "
            "conversion step, or the from-history-db conversion step "
            "(both server-side captures) was left out of the pipeline, "
            "destroying the elapsed-time evidence")
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


def check_coverage(stats, min_coverage, basis=""):
    name = "coverage is at least %.2f%s" % (min_coverage, basis)
    if stats["coverage"] >= min_coverage:
        return CheckResult(name, "PASS")
    return CheckResult(name, "FAIL",
        "coverage is %.3f (observed=%d, nominal=%.1f), below %.2f - the "
        "frame losing home Wi-Fi or internet, the server unit restarting, "
        "or journald having rotated the earliest entries out of the "
        "window being converted are the likely causes" %
        (stats["coverage"], stats["observed"], stats["nominal"], min_coverage))


def check_max_gap(stats, max_gap_intervals, basis=""):
    name = "no gap between consecutive polls exceeds %g interval(s)%s" % (
        max_gap_intervals, basis)
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


# --- from-history-db: the read-only bridge from history.db's
# device_health table -------------------------------------------------
#
# The canonical remote query (run on the VPS, not by this script - this
# file deliberately does not import sqlite3; history.db lives on the
# server and is read over SSH, never opened directly here). Fed to
# `python3 -` on the remote's stdin via a quoted here-document, so a
# quote- and semicolon-laden one-liner never has to survive SSH's two
# levels of shell re-parsing:
#
#   ssh root@<vps-ip> "python3 - '<since-iso-8601>'" <<'PY'
#   import json, sqlite3, sys
#   conn = sqlite3.connect('file:/opt/skypane/state/history.db?mode=ro', uri=True)
#   conn.execute('PRAGMA busy_timeout=5000')
#   conn.row_factory = sqlite3.Row
#   rows = conn.execute(
#       'SELECT ts, battery_mv, fw_version, boot_reason, rssi '
#       'FROM device_health WHERE ts >= ? ORDER BY ts', (sys.argv[1],))
#   for row in rows:
#       print(json.dumps(dict(row)))
#   PY
#
# The read-only `mode=ro` URI is load-bearing, not decorative: the
# 30-second `skypane-poll.timer` ingest oneshot is writing to this
# database continuously, and a read-only connection cannot create,
# modify, or recover its WAL - so an external reader can neither corrupt
# the store nor lock out the writer. `PRAGMA busy_timeout=5000` matches
# the discipline `history_db.connect()` already applies to its own
# connections (Pitfall 9), so a read landing mid-commit waits briefly
# instead of raising "database is locked".
#
# Why regenerating the whole window is unconditionally safe on this
# channel: `device_health` has keep-forever retention (see
# server/history_db.py:18) and is never pruned, and
# record_device_health() inserts with INSERT OR IGNORE against a
# UNIQUE(ts, battery_mv) constraint, so re-reading an overlapping range
# cannot double-count. Neither of the two hazards the journald bridge
# (cmd_from_journal, above) has to defend against - an earliest-entries
# rotation that silently shortens the window, and duplicated polls from
# appending overlapping reads - can occur against a keep-forever table
# with a uniqueness constraint on the insert. No rotation-triggered
# repair path is needed or provided here; this is a genuine
# simplification relative to from-journal, not an omission.
def history_row_to_line(row):
    """Return the bracketed [ISO-8601] telemetry line for one parsed
    device_health row, or None when the row carries no usable measurement:
    it is not an object, has no non-empty string `ts`, its `battery_mv`
    cannot be coerced to int, or the assembled line fails
    parse_timestamp().
    """
    if not isinstance(row, dict):
        return None
    ts_raw = row.get("ts")
    if not isinstance(ts_raw, str) or not ts_raw:
        return None
    try:
        battery_mv = int(row.get("battery_mv"))
    except (TypeError, ValueError):
        return None

    tokens = []
    for header, value in (
        ("X-Fw-Version", row.get("fw_version")),
        ("X-Boot-Reason", row.get("boot_reason")),
        ("X-Rssi", row.get("rssi")),
        ("X-Battery-Mv", battery_mv),
    ):
        if value is None or value == "":
            continue
        tokens.append("%s=%s" % (header, value))
    out = "[%s]   telemetry: %s" % (normalize_journal_timestamp(ts_raw), " ".join(tokens))
    if parse_timestamp(out) is None:
        return None
    return out


def cmd_from_history_db(args):
    """Convert JSON-Lines `device_health` rows (one JSON object per line,
    as printed by the canonical remote query documented above) into the
    bracketed [ISO-8601] shape check-battery already parses, reading
    from the given file paths (concatenated in order) or from stdin
    when none are given. Writes converted lines to stdout only.

    JSON Lines rather than a single JSON array is a deliberate choice: a
    line-at-a-time parser degrades to "drop that one line and count it"
    when anything unexpected arrives on the pipe (an SSH banner, a
    truncated final line, a warning the remote shell emitted), whereas a
    whole-stdin array parse fails totally on the same input. It also
    mirrors cmd_from_journal()'s existing shape exactly, so the two
    converters read as siblings.

    A row is dropped and counted when: it is not valid JSON; it is valid
    JSON but not an object; it has no non-empty string `ts`; or its
    `battery_mv` cannot be coerced to int, including null or absent -
    a real production shape, not a hypothetical one:
    tail_caddy_battery_log() yields battery_mv=None whenever the header
    is absent or non-integer, and such a row carries no measurement at
    all. Extra keys the query did not ask for (e.g. `id`) are ignored
    rather than rendered into the message. A single
    "from-history-db: dropped N" summary is written to stderr so a
    redirect of stdout into the run log stays clean, and a silently
    truncated conversion still reads as visible.
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
        line = raw_line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except ValueError:
            dropped += 1
            continue
        if not isinstance(row, dict):
            dropped += 1
            continue
        out = history_row_to_line(row)
        if out is None:
            dropped += 1
            continue
        sys.stdout.write(out + "\n")
    sys.stdout.flush()
    sys.stderr.write("from-history-db: dropped %d line(s)\n" % dropped)
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


# --- run-report: second-discharge evidence from the raw export ---------
#
# The thresholds below are fixed in advance of any run and are never
# tuned from the data: run-report offers no flags to change them.

RUN_THRESHOLDS = {
    "min_days": 1,
    "min_coverage": 0.95,
    "max_gap_intervals": 3,
    "min_mv_drop": 100,
    "cutoff_mv": 3400,
}
RUN_REQUIRED_PARAMS = (
    "capacity_mah", "interval_s", "protocol_confirmed_utc",
    "disconnect_time_utc", "end_reason", "firmware_version",
    "server_revision",
)
DEFAULT_PARK_MV = 3300
REFERENCE_WINDOW_S = 48 * 3600
REFERENCE_GAP_FACTOR = 3  # gaps above this many configured intervals are excluded
REFERENCE_MIN_GAPS = 100


class RunReportError(Exception):
    """Input that run-report refuses to turn into evidence."""


def _aware_timestamp(value, label):
    if not isinstance(value, str) or not value:
        raise RunReportError("%s must be an ISO-8601 timestamp string" % label)
    try:
        ts = datetime.datetime.fromisoformat(normalize_journal_timestamp(value))
    except ValueError:
        raise RunReportError("%s is not a valid ISO-8601 timestamp: %r" % (label, value))
    if ts.tzinfo is None:
        raise RunReportError("%s must carry a timezone offset: %r" % (label, value))
    return ts


def _int_param(params, key, minimum, default=None):
    value = params.get(key)
    if value is None:
        return default
    if isinstance(value, bool) or not isinstance(value, int):
        raise RunReportError("param %s must be an integer" % key)
    if value < minimum:
        raise RunReportError("param %s must be at least %d" % (key, minimum))
    return value


def validate_run_params(params):
    """Return a normalised copy of the owner-supplied params, or raise
    RunReportError naming the first problem. Required keys must be present
    and non-null so a schema example can never be mistaken for evidence.
    """
    if not isinstance(params, dict):
        raise RunReportError("params file must contain a JSON object")
    for key in RUN_REQUIRED_PARAMS:
        if params.get(key) is None or params.get(key) == "":
            raise RunReportError("missing required param: %s" % key)
    out = {
        "capacity_mah": _int_param(params, "capacity_mah", 1),
        "interval_s": _int_param(params, "interval_s", 1),
        "park_mv": _int_param(params, "park_mv", 0, DEFAULT_PARK_MV),
        "boot_count_start": _int_param(params, "boot_count_start", 0),
        "boot_count_end": _int_param(params, "boot_count_end", 0),
        "production_interval_before_s": _int_param(
            params, "production_interval_before_s", 1),
        "production_interval_restored_s": _int_param(
            params, "production_interval_restored_s", 1),
        "protocol_confirmed": _aware_timestamp(
            params["protocol_confirmed_utc"], "protocol_confirmed_utc"),
        "disconnect_time": _aware_timestamp(
            params["disconnect_time_utc"], "disconnect_time_utc"),
        "end_time": None,
    }
    if params.get("end_time_utc") is not None:
        out["end_time"] = _aware_timestamp(params["end_time_utc"], "end_time_utc")
    if params["end_reason"] not in ("depleted", "ceiling"):
        raise RunReportError("param end_reason must be 'depleted' or 'ceiling'")
    out["end_reason"] = params["end_reason"]
    for key in ("firmware_version", "server_revision"):
        if not isinstance(params[key], str):
            raise RunReportError("param %s must be a string" % key)
        out[key] = params[key]
    days = params.get("ceiling_days")
    if days is not None and (isinstance(days, bool)
                             or not isinstance(days, (int, float)) or days <= 0):
        raise RunReportError("param ceiling_days must be a positive number")
    if out["end_reason"] == "ceiling" and days is None:
        raise RunReportError("missing required param: ceiling_days (end_reason is ceiling)")
    out["ceiling_days"] = days
    start, end = out["boot_count_start"], out["boot_count_end"]
    if start is not None and end is not None and end < start:
        raise RunReportError("boot_count_end is below boot_count_start")
    _validate_reference_params(params, out)
    return out


def _validate_reference_params(params, out):
    """Add the optional frozen reference interval to the normalised params.
    The value is bounded to [interval_s, REFERENCE_GAP_FACTOR x interval_s]:
    the helper never yields more, because it excludes larger gaps. A value
    needs a non-empty source note, and a source without a value is refused,
    so a half-filled freeze is never read as a decision either way.
    """
    interval = out["interval_s"]
    value = _int_param(params, "reference_interval_s", interval)
    source = params.get("reference_interval_source")
    digest = params.get("reference_interval_export_sha256")
    if value is None:
        if source not in (None, "") or digest not in (None, ""):
            raise RunReportError(
                "reference_interval_source / reference_interval_export_sha256 "
                "given without reference_interval_s")
        out.update(reference_interval=None, reference_source=None,
                   reference_export_sha256=None)
        return
    ceiling = REFERENCE_GAP_FACTOR * interval
    if value > ceiling:
        raise RunReportError(
            "param reference_interval_s must be at most %d (%d x interval_s)"
            % (ceiling, REFERENCE_GAP_FACTOR))
    if not isinstance(source, str) or not source.strip():
        raise RunReportError(
            "param reference_interval_source is required with reference_interval_s")
    if digest not in (None, "") and not (
            isinstance(digest, str) and re.fullmatch(r"[0-9a-f]{64}", digest)):
        raise RunReportError(
            "param reference_interval_export_sha256 must be 64 lowercase hex digits")
    out.update(reference_interval=value, reference_source=source.strip(),
               reference_export_sha256=digest or None)


def _load_export_rows(raw_text):
    """Split a JSON-Lines export into (rows, lines, dropped): the parsed
    rows that carry a usable reading, their bracketed telemetry lines (same
    order), and the count of non-empty lines that were dropped.
    """
    rows, lines, dropped = [], [], 0
    for raw_line in raw_text.splitlines():
        if not raw_line.strip():
            continue
        try:
            row = json.loads(raw_line)
        except ValueError:
            dropped += 1
            continue
        line = history_row_to_line(row)
        if line is None:
            dropped += 1
            continue
        rows.append(row)
        lines.append(line)
    return rows, lines, dropped


def _require_fresh_ordered(polls, params):
    if any(p.ts.tzinfo is None for p in polls):
        raise RunReportError("row timestamps must carry a timezone offset")
    for a, b in zip(polls, polls[1:]):
        if b.ts < a.ts:
            raise RunReportError(
                "rows are not in chronological order (%s follows %s)" %
                (b.ts.isoformat(), a.ts.isoformat()))
    if polls[0].ts < params["protocol_confirmed"]:
        raise RunReportError(
            "export predates the pre-registration: first row %s is before "
            "protocol_confirmed_utc %s" %
            (polls[0].ts.isoformat(), params["protocol_confirmed"].isoformat()))
    if params["end_time"] is not None and polls[-1].ts > params["end_time"]:
        raise RunReportError(
            "last row %s is after end_time_utc %s" %
            (polls[-1].ts.isoformat(), params["end_time"].isoformat()))


def compute_reference_interval(polls, interval_s):
    """Return the proposed reference interval computed from the first 48
    hours of `polls` (chronological BatteryPoll list), or raise
    RunReportError. Gaps between consecutive polls inside
    [first, first + 48 h] are averaged after dropping gaps above
    REFERENCE_GAP_FACTOR x interval_s; the mean is rounded half-up to whole
    seconds. Later rows are never read, so the value cannot depend on how
    the run ended.
    """
    if len(polls) < 2:
        raise RunReportError("export has fewer than two rows")
    first = polls[0].ts
    if (polls[-1].ts - first).total_seconds() < REFERENCE_WINDOW_S:
        raise RunReportError(
            "export covers %.1f h, less than the 48 h the reference interval "
            "is measured over" % ((polls[-1].ts - first).total_seconds() / 3600.0))
    cutoff = first + datetime.timedelta(seconds=REFERENCE_WINDOW_S)
    window = [p for p in polls if p.ts <= cutoff]
    gaps = [(b.ts - a.ts).total_seconds() for a, b in zip(window, window[1:])]
    limit = REFERENCE_GAP_FACTOR * interval_s
    used = [g for g in gaps if g <= limit]
    if len(used) < REFERENCE_MIN_GAPS:
        raise RunReportError(
            "only %d gap(s) of %d in the first 48 h are at most %d s; need at "
            "least %d" % (len(used), len(gaps), limit, REFERENCE_MIN_GAPS))
    mean = sum(used) / len(used)
    return {
        "reference_interval_s": int(mean + 0.5),
        "mean_gap_s": mean,
        "gaps_used": len(used),
        "gaps_excluded": len(gaps) - len(used),
        "exclusion_limit_s": limit,
        "window_start": first.isoformat(),
        "window_end": window[-1].ts.isoformat(),
    }


def _rows_to_ordered_polls(raw):
    rows, lines, _ = _load_export_rows(raw.decode("utf-8", errors="replace"))
    if not lines:
        raise RunReportError("no usable rows in the export")
    _, polls = parse_battery_lines(lines)
    if len(polls) != len(rows):
        raise RunReportError("rows could not all be timestamped")
    if any(p.ts.tzinfo is None for p in polls):
        raise RunReportError("row timestamps must carry a timezone offset")
    for a, b in zip(polls, polls[1:]):
        if b.ts < a.ts:
            raise RunReportError(
                "rows are not in chronological order (%s follows %s)" %
                (b.ts.isoformat(), a.ts.isoformat()))
    return polls


def _reference_interval_check(polls, p):
    """Continuity check: the frozen value must be what the first 48 hours of
    this very export give, so it cannot have been derived from later data."""
    name = "frozen reference interval equals the value recomputed from the first 48 h"
    try:
        again = compute_reference_interval(polls, p["interval_s"])
    except RunReportError as exc:
        return CheckResult(name, "FAIL", "cannot recompute: %s" % exc), None
    if again["reference_interval_s"] != p["reference_interval"]:
        return CheckResult(name, "FAIL",
            "params carry %d s, the first 48 h of the export give %d s" %
            (p["reference_interval"], again["reference_interval_s"])), again
    return CheckResult(name, "PASS"), again


def _verdict(results):
    status = "FAIL" if any(r.status == "FAIL" for r in results) else "PASS"
    return {"status": status,
            "checks": [{"name": r.name, "status": r.status, "reason": r.reason}
                       for r in results]}


def _continuity_verdict(polls, normal, normal_stats, params, th):
    results = [check_timestamps_and_min_polls(len(normal), normal)]
    basis = ""
    if params["reference_interval"] is not None:
        basis = " (against the %d s reference interval)" % params["reference_interval"]
    if results[0].status == "PASS":
        results.append(check_span(normal_stats, th["min_days"]))
        results.append(check_coverage(normal_stats, th["min_coverage"], basis))
        results.append(check_max_gap(normal_stats, th["max_gap_intervals"], basis))
    ceiling = params["ceiling_days"]
    name = "span does not exceed the ceiling by more than one interval"
    if ceiling is None:
        results.append(CheckResult(name, "SKIP", "no ceiling_days given"))
    else:
        span_days = (polls[-1].ts - polls[0].ts).total_seconds() / 86400.0
        limit = ceiling + params["interval_s"] / 86400.0
        if span_days <= limit:
            results.append(CheckResult(name, "PASS"))
        else:
            results.append(CheckResult(
                name, "FAIL", "span is %.3f day(s), ceiling is %g day(s) "
                "plus one interval" % (span_days, ceiling)))
    return results


def _voltage_verdict(full_stats, params, th):
    results = [check_mv_drop(full_stats, th["min_mv_drop"])]
    if params["end_reason"] == "depleted":
        results.append(check_depleted(full_stats, th["cutoff_mv"]))
    else:
        results.append(CheckResult(
            "last observed millivolt reading is at or below the %d mV cutoff"
            % th["cutoff_mv"], "SKIP",
            "run ended at the ceiling, so the result is a bound, not a depletion"))
    return results


def _baseline_verdict(rows, params):
    seen = sorted({str(r["fw_version"]) for r in rows
                   if r.get("fw_version") not in (None, "")})
    name = "firmware versions in the export equal the recorded baseline"
    if not seen:
        result = CheckResult(name, "FAIL",
            "no row carries fw_version, so the baseline cannot be verified")
    elif seen == [params["firmware_version"]]:
        result = CheckResult(name, "PASS")
    else:
        result = CheckResult(name, "FAIL",
            "export carries %s, recorded baseline is %s" %
            (seen, params["firmware_version"]))
    return result, seen


def _relative_difference(value, reference):
    if value is None or not reference:
        return None
    return (value - reference) / float(reference)


def _boot_witness(params, full_stats, normal_stats, th, observed_full):
    start, end = params["boot_count_start"], params["boot_count_end"]
    delta = None
    status = "computable"
    if start is None or end is None:
        missing = [k for k, v in (("boot_count_start", start),
                                  ("boot_count_end", end)) if v is None]
        status = "not computable: %s not recorded" % " and ".join(missing)
    else:
        delta = end - start
    return {
        "nominal": normal_stats["nominal"],
        "observed_normal": normal_stats["observed"],
        "observed_full": observed_full,
        "parked_polls": observed_full - normal_stats["observed"],
        "boot_delta": delta,
        "boot_delta_status": status,
        "nominal_vs_observed_normal": _relative_difference(
            normal_stats["observed"], normal_stats["nominal"]),
        "boot_vs_observed_full": _relative_difference(delta, observed_full),
    }


def _boot_reason_counts(rows):
    counts = {}
    for row in rows:
        key = row.get("boot_reason") or "(none)"
        counts[key] = counts.get(key, 0) + 1
    return counts


def _restore_section(p):
    before = p["production_interval_before_s"]
    restored = p["production_interval_restored_s"]
    return {
        "production_interval_before_s": before,
        "production_interval_restored_s": restored,
        "recorded": before is not None and restored is not None,
    }


def build_run_report(raw, params, thresholds=None):
    """Return the run report as a plain dict from the raw JSON-Lines export
    (bytes) and the owner-supplied params, or raise RunReportError.

    Continuity and coverage are judged on the normal-cadence window, which
    ends at the first reading at or below park_mv; voltage validity and the
    boot-counter reconciliation use the full window.
    """
    th = dict(RUN_THRESHOLDS)
    th.update(thresholds or {})
    p = validate_run_params(params)
    rows, lines, dropped = _load_export_rows(raw.decode("utf-8", errors="replace"))
    if not lines:
        raise RunReportError("no usable rows in the export")
    all_matches, polls = parse_battery_lines(lines)
    if len(polls) != len(rows):
        raise RunReportError("rows could not all be timestamped")
    _require_fresh_ordered(polls, p)

    end_idx = next((i for i, q in enumerate(polls) if q.mv <= p["park_mv"]),
                   len(polls) - 1)
    normal = polls[:end_idx + 1]
    interval = p["interval_s"]
    judged = p["reference_interval"] or interval
    full_stats = compute_battery_stats(
        polls, interval, p["capacity_mah"], p["boot_count_start"], p["boot_count_end"])
    normal_stats = compute_battery_stats(
        normal, judged, p["capacity_mah"], None, None)

    continuity = _continuity_verdict(polls, normal, normal_stats, p, th)
    reference = _reference_outcome(polls, normal, p, continuity)
    reconciliation = _boot_witness(p, full_stats, normal_stats, th, len(polls))
    if reconciliation["boot_delta"] is not None:
        continuity.append(check_boot_reconciliation(full_stats, th["min_coverage"]))
    baseline_result, fw_seen = _baseline_verdict(rows, p)

    reasons = _boot_reason_counts(rows)
    gaps = [(b.ts - a.ts).total_seconds() for a, b in zip(normal, normal[1:])]

    report = {
        "verdicts": {
            "continuity": _verdict(continuity),
            "voltage_validity": _verdict(_voltage_verdict(full_stats, p, th)),
            "baseline": _verdict([baseline_result]),
        },
        "thresholds": th,
        "reconciliation": reconciliation,
        "cadence": {
            "configured_interval_s": interval,
            "effective_mean_gap_s": (sum(gaps) / len(gaps)) if gaps else None,
            "max_gap_s": max(gaps) if gaps else None,
        },
        "window": {
            "first_ts": polls[0].ts.isoformat(),
            "last_ts": polls[-1].ts.isoformat(),
            "span_days": full_stats["span_days"],
            "normal_window_end_ts": normal[-1].ts.isoformat(),
            "disconnect_time_utc": p["disconnect_time"].isoformat(),
        },
        "endpoints": {
            "first_mv": polls[0].mv,
            "open_mv": full_stats["open_mv"],
            "close_mv": full_stats["close_mv"],
            "drop_mv": full_stats["drop_mv"],
            "last_mv": full_stats["last_mv"],
            "last_poll_mv": normal[-1].mv,
        },
        "baseline": {
            "firmware_version": p["firmware_version"],
            "server_revision": p["server_revision"],
            "fw_versions_seen": fw_seen,
            "boot_reason_counts": reasons,
        },
        "restore": _restore_section(p),
        "export": {
            "row_count": len(rows),
            "dropped_rows": dropped,
            "sha256": hashlib.sha256(raw).hexdigest(),
        },
        "energy_normal_window": {
            "basis": "observed poll count in the normal-cadence window",
            "mah_per_cycle": normal_stats["mah_per_cycle"],
            "mah_per_day": normal_stats["mah_per_day"],
        },
    }
    if reference is not None:
        report["reference_interval"] = reference
    return report


def _reference_outcome(polls, normal, p, continuity):
    """Append the frozen-value check to `continuity` and return the report
    block, or return None when no reference interval is in use."""
    if p["reference_interval"] is None:
        return None
    check, recomputed = _reference_interval_check(polls, p)
    continuity.append(check)
    return _reference_section(p, normal, recomputed)


def _reference_section(p, normal, recomputed):
    """Report block present only when a frozen reference interval is used:
    which interval each continuity gate was judged against and why, plus
    the same figures against the configured interval as information that
    never drives a verdict.
    """
    configured = compute_battery_stats(
        normal, p["interval_s"], p["capacity_mah"], None, None)
    gaps = [(b.ts - a.ts).total_seconds() for a, b in zip(normal, normal[1:])]
    mean_gap = (sum(gaps) / len(gaps)) if gaps else None
    ref = p["reference_interval"]
    return {
        "reference_interval_s": ref,
        "reference_interval_source": p["reference_source"],
        "reference_interval_export_sha256": p["reference_export_sha256"],
        "recomputed_from_first_48h": recomputed,
        "judged_against": {
            "coverage": "reference_interval_s",
            "max_gap_intervals": "reference_interval_s",
            "nominal_cycles": "reference_interval_s",
            "span_ceiling": "configured_interval_s",
        },
        "informational_vs_configured": {
            "configured_interval_s": p["interval_s"],
            "coverage": configured["coverage"],
            "nominal": configured["nominal"],
            "max_gap_intervals": configured["max_gap"],
        },
        "normal_window_mean_gap_s": mean_gap,
        "normal_window_mean_gap_vs_reference": _relative_difference(mean_gap, ref),
    }


def _print_reference_summary(ref):
    if ref is None:
        return
    info = ref["informational_vs_configured"]
    print("reference interval: continuity gates judged against %d s (frozen, "
          "source: %s); informational only, against the configured %d s: "
          "coverage=%.3f max gap=%.2f interval(s)" %
          (ref["reference_interval_s"], ref["reference_interval_source"],
           info["configured_interval_s"], info["coverage"],
           info["max_gap_intervals"]))
    drift = ref["normal_window_mean_gap_vs_reference"]
    if drift is not None:
        print("reference interval: normal-window mean gap is %+.1f%% against "
              "the frozen value" % (drift * 100.0))


def print_run_summary(report):
    for name in ("continuity", "voltage_validity", "baseline"):
        verdict = report["verdicts"][name]
        print("%s: %s" % (name, verdict["status"]))
        for check in verdict["checks"]:
            if check["status"] == "PASS":
                print("  PASS %s" % check["name"])
            else:
                print("  %s %s - %s" % (check["status"], check["name"], check["reason"]))
    _print_reference_summary(report.get("reference_interval"))
    rec = report["reconciliation"]
    print("cycle reconciliation: nominal=%.2f observed(normal)=%d "
          "observed(full)=%d parked=%d boot-delta=%s" %
          (rec["nominal"], rec["observed_normal"], rec["observed_full"],
           rec["parked_polls"],
           rec["boot_delta"] if rec["boot_delta"] is not None
           else rec["boot_delta_status"]))
    cad = report["cadence"]
    if cad["effective_mean_gap_s"] is not None:
        print("cadence: configured=%ds effective mean gap=%.1fs max gap=%.0fs" %
              (cad["configured_interval_s"], cad["effective_mean_gap_s"],
               cad["max_gap_s"]))
    win, end = report["window"], report["endpoints"]
    print("window: %s to %s (%.3f day(s)), normal cadence ends %s" %
          (win["first_ts"], win["last_ts"], win["span_days"],
           win["normal_window_end_ts"]))
    print("endpoints mV: first=%d open=%.1f close=%.1f drop=%.1f last=%d" %
          (end["first_mv"], end["open_mv"], end["close_mv"], end["drop_mv"],
           end["last_mv"]))
    base = report["baseline"]
    print("baseline: firmware=%s server=%s seen=%s" %
          (base["firmware_version"], base["server_revision"],
           ",".join(base["fw_versions_seen"]) or "none"))
    rest = report["restore"]
    print("restore: before=%s restored=%s recorded=%s" %
          (rest["production_interval_before_s"],
           rest["production_interval_restored_s"], rest["recorded"]))
    exp = report["export"]
    print("export: rows=%d dropped=%d sha256=%s" %
          (exp["row_count"], exp["dropped_rows"], exp["sha256"]))


def cmd_run_report(args):
    """Build and print the run report, writing --out only on success.
    Exit 0 when all three verdicts pass, 1 when any fails, 2 when the
    inputs are refused.
    """
    try:
        try:
            with open(args.params, "r") as fh:
                params = json.load(fh)
        except (OSError, ValueError) as exc:
            raise RunReportError("cannot read params file: %s" % exc)
        try:
            if args.rows:
                with open(args.rows, "rb") as fh:
                    raw = fh.read()
            else:
                raw = sys.stdin.buffer.read()
        except OSError as exc:
            raise RunReportError("cannot read rows: %s" % exc)
        report = build_run_report(raw, params)
    except RunReportError as exc:
        sys.stderr.write("run-report: refused: %s\n" % exc)
        return 2
    if args.out:
        with open(args.out, "w") as fh:
            fh.write(json.dumps(report, sort_keys=True, indent=2) + "\n")
    print_run_summary(report)
    ok = all(v["status"] == "PASS" for v in report["verdicts"].values())
    return 0 if ok else 1


def cmd_reference_interval(args):
    """Print the proposed reference interval for the continuity gates,
    computed from the first 48 hours of the export. Exit 0 with the value,
    2 when the export cannot support it.
    """
    try:
        if args.interval_s < 1:
            raise RunReportError("--interval-s must be at least 1")
        try:
            if args.rows:
                with open(args.rows, "rb") as fh:
                    raw = fh.read()
            else:
                raw = sys.stdin.buffer.read()
        except OSError as exc:
            raise RunReportError("cannot read rows: %s" % exc)
        result = compute_reference_interval(_rows_to_ordered_polls(raw), args.interval_s)
    except RunReportError as exc:
        sys.stderr.write("reference-interval: refused: %s\n" % exc)
        return 2
    print("reference_interval_s: %d" % result["reference_interval_s"])
    print("window: %s to %s (first 48 h only)" %
          (result["window_start"], result["window_end"]))
    print("gaps used: %d, excluded (above %d s): %d, unrounded mean %.3f s" %
          (result["gaps_used"], result["exclusion_limit_s"],
           result["gaps_excluded"], result["mean_gap_s"]))
    print("export_sha256: %s" % hashlib.sha256(raw).hexdigest())
    return 0


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


def _run_converted_battery_case(script_path, battery_common, subcommand, fixture_name):
    """Convert `fixture_name` via `subcommand` (from-journal or
    from-history-db), then run check-battery over the converted output
    exactly as a daily check-in would, and additionally require its
    telemetry messages equal battery-good.log's - proving the bridge is
    lossless for content the checker already accepts, not merely that
    some output happened to pass. Prints one PASS/FAIL line naming
    `fixture_name` (minus its extension) and returns True on PASS.
    """
    label = os.path.splitext(fixture_name)[0]
    fixture_path = os.path.join(FIXTURES_DIR, fixture_name)
    tmp_path = os.path.join(
        os.environ.get("TMPDIR", "/tmp") or "/tmp",
        "logtools-selftest-%s-%d.log" % (label, os.getpid()))
    conv = subprocess.run(
        [sys.executable, script_path, subcommand, fixture_path],
        capture_output=True, text=True)
    with open(tmp_path, "w") as fh:
        fh.write(conv.stdout)
    check_proc = subprocess.run(
        [sys.executable, script_path, "check-battery", tmp_path] +
        battery_common + ["--expect-depleted"],
        capture_output=True, text=True)
    accepted = (check_proc.returncode == 0)
    converted_msgs = _telemetry_messages(tmp_path)
    good_msgs = _telemetry_messages(os.path.join(FIXTURES_DIR, "battery-good.log"))
    messages_match = (converted_msgs == good_msgs)
    os.remove(tmp_path)

    if accepted and messages_match:
        print("PASS %s (accepted via %s, telemetry messages match "
              "battery-good.log)" % (label, subcommand))
        return True

    reasons = []
    if not accepted:
        reasons.append("check-battery exit code %d" % check_proc.returncode)
    if not messages_match:
        reasons.append("converted telemetry messages differ from "
                        "battery-good.log (%d vs %d)" %
                        (len(converted_msgs), len(good_msgs)))
    print("FAIL %s (%s)" % (label, "; ".join(reasons)))
    return False


def cmd_selftest(_args):
    """Run check-backoff and check-battery, each as a subprocess of this
    same script, against the fixtures under hardware/fixtures/ with the
    flags each one is meant to be judged under. Asserts every good
    fixture is accepted (exit 0) and every negative fixture is rejected
    (non-zero exit). Also converts battery-journal.log through
    from-journal and battery-history-db.jsonl through from-history-db,
    asserting each result is accepted and its telemetry messages are
    byte-identical (stripped) to battery-good.log's - eight fixtures in
    total.
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

    if not _run_converted_battery_case(
            script_path, battery_common, "from-journal", "battery-journal.log"):
        all_ok = False
    if not _run_converted_battery_case(
            script_path, battery_common, "from-history-db", "battery-history-db.jsonl"):
        all_ok = False

    return 0 if all_ok else 1


# --- CLI ------------------------------------------------------------------


def _add_run_report_parsers(sub):
    rr = sub.add_parser("run-report",
        help="turn raw device_health JSON-Lines rows plus a params file "
             "into a report with separate continuity, voltage-validity "
             "and baseline verdicts")
    rr.add_argument("rows", nargs="?", default=None,
        help="JSON-Lines rows file; reads stdin when omitted")
    rr.add_argument("--params", required=True,
        help="owner-supplied params JSON (see run2-params.example.json)")
    rr.add_argument("--out", default=None,
        help="write the JSON report here (only on a non-refused run)")

    ri = sub.add_parser("reference-interval",
        help="compute the proposed continuity reference interval from the "
             "first 48 hours of a raw device_health export")
    ri.add_argument("rows", nargs="?", default=None,
        help="JSON-Lines rows file; reads stdin when omitted")
    ri.add_argument("--interval-s", type=int, required=True,
        help="the configured wake interval in seconds (gaps above 3x it "
             "are excluded)")


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

    fhd = sub.add_parser("from-history-db",
        help="convert JSON-Lines device_health rows into the bracketed "
             "[ISO-8601] shape check-battery parses")
    fhd.add_argument("logs", nargs="*",
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

    _add_run_report_parsers(sub)

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
    if args.command == "from-history-db":
        return cmd_from_history_db(args)
    if args.command == "check-backoff":
        return cmd_check_backoff(args)
    if args.command == "check-battery":
        return cmd_check_battery(args)
    if args.command == "run-report":
        return cmd_run_report(args)
    if args.command == "reference-interval":
        return cmd_reference_interval(args)
    if args.command == "selftest":
        return cmd_selftest(args)
    return 1  # pragma: no cover — argparse enforces `required=True` above


if __name__ == "__main__":
    sys.exit(main())
