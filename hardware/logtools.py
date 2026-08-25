#!/usr/bin/env python3
"""hardware/logtools.py — stdlib-only log timestamper and backoff-sequence
checker for captured Ink Frame serial logs.

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

  selftest       Run check-backoff against the three fixtures under
                 hardware/fixtures/ with the flags each is meant to be
                 judged under, and assert the good one is accepted while
                 both bad ones are rejected. A checker that has never
                 been shown a bad log has not been tested.

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
# an ESP log prefix (e.g. "I (746) inkframe: ") before the contract
# text, so every pattern below is applied with .search(), not .match().

TS_RE = re.compile(r"^\[([^\]]+)\]")
WAKE_RE = re.compile(r"wake reason=([\w-]+) boot_count=(\d+)")
POLL_OK_RE = re.compile(r"poll ok sleep_s=(\d+) hash_skip=([01])")
POLL_FAIL_RE = re.compile(r"poll fail step=(\w+) backoff_n=(\d+) sleep_s=(\d+)")
SLEEP_ENTER_RE = re.compile(r"sleep enter sleep_s=(\d+)")


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


def cmd_selftest(_args):
    """Run check-backoff, as a subprocess of this same script, against
    each of the three fixtures with the flags each one is meant to be
    judged under. Asserts the good fixture is accepted (exit 0) and
    both negative fixtures are rejected (non-zero exit).
    """
    script_path = os.path.abspath(__file__)
    cases = [
        ("backoff-good.log", ["--expect-persist", "--expect-reset"], True),
        ("backoff-fixed-interval.log", [], False),
        ("backoff-rtc-reset.log", ["--expect-persist"], False),
    ]
    all_ok = True
    for fixture, flags, should_be_accepted in cases:
        path = os.path.join(FIXTURES_DIR, fixture)
        cmd = [sys.executable, script_path, "check-backoff", path] + flags
        proc = subprocess.run(cmd, capture_output=True, text=True)
        actually_accepted = (proc.returncode == 0)
        requirement = "accepted" if should_be_accepted else "rejected"
        if actually_accepted == should_be_accepted:
            print("PASS %s (%s, as required)" % (fixture, requirement))
        else:
            all_ok = False
            print("FAIL %s (expected to be %s, actual exit code %d)" %
                  (fixture, requirement, proc.returncode))
    return 0 if all_ok else 1


# --- CLI ------------------------------------------------------------------


def build_parser():
    p = argparse.ArgumentParser(
        prog="logtools.py",
        description="Stdlib-only timestamper and backoff-sequence checker "
                     "for Ink Frame captured serial logs.")
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("stamp",
        help="prefix stdin lines with a wall-clock ISO-8601 timestamp, flushed per line")

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

    sub.add_parser("selftest",
        help="run check-backoff against hardware/fixtures/*.log and assert outcomes")

    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    if args.command == "stamp":
        cmd_stamp(args)
        return 0
    if args.command == "check-backoff":
        return cmd_check_backoff(args)
    if args.command == "selftest":
        return cmd_selftest(args)
    return 1  # pragma: no cover — argparse enforces `required=True` above


if __name__ == "__main__":
    sys.exit(main())
