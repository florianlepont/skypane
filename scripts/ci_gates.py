#!/usr/bin/env python3
"""Checks the totals of JUnit reports from the parallel test jobs. Stdlib only.

Subcommands:
  totals [--min-executed N] [--max-skipped K] FILE...
      Sums every `testsuite` of every file, prints per-file and grand totals,
      and exits 1 when there is any failure or error, when fewer than N tests
      executed (tests minus skipped), or when more than K tests were skipped.
      A missing file, a file that is not JUnit XML, or no file at all exits 2.
"""
import argparse
import sys
import xml.etree.ElementTree as ET

# The number of tests the suite must execute and the number it may skip, as
# measured on the last full run of the unsplit job (12,821 passed, none
# skipped). The executed floor may only go up; the skipped ceiling only down.
MIN_EXECUTED = 12821
MAX_SKIPPED = 0


class ReportError(Exception):
    """A report file is missing or is not JUnit XML."""


def read_totals(path):
    """Returns (tests, failures, errors, skipped) summed over a file's suites."""
    try:
        root = ET.parse(path).getroot()
    except (OSError, ET.ParseError) as exc:
        raise ReportError(f"{path}: {exc}") from exc
    suites = [root] if root.tag == "testsuite" else list(root.iter("testsuite"))
    if not suites:
        raise ReportError(f"{path}: no testsuite element")
    totals = [0, 0, 0, 0]
    for suite in suites:
        for index, name in enumerate(("tests", "failures", "errors", "skipped")):
            totals[index] += int(suite.get(name, "0"))
    return tuple(totals)


def judge(grand, min_executed, max_skipped):
    """Returns the list of reasons the grand totals are not acceptable."""
    tests, failures, errors, skipped = grand
    reasons = []
    if failures or errors:
        reasons.append(f"{failures} failure(s) and {errors} error(s)")
    if tests - skipped < min_executed:
        reasons.append(
            f"executed {tests - skipped} tests, fewer than the {min_executed} required")
    if skipped > max_skipped:
        reasons.append(f"{skipped} skipped, more than the {max_skipped} allowed")
    return reasons


def command_totals(args):
    if not args.files:
        print("no JUnit file given", file=sys.stderr)
        return 2
    try:
        per_file = [(path, read_totals(path)) for path in args.files]
    except ReportError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    for path, (tests, failures, errors, skipped) in per_file:
        print(f"{path}: {tests} tests, {failures} failures, {errors} errors, "
              f"{skipped} skipped")
    grand = tuple(sum(totals[i] for _, totals in per_file) for i in range(4))
    print(f"total: {grand[0]} tests, {grand[1]} failures, {grand[2]} errors, "
          f"{grand[3]} skipped, {grand[0] - grand[3]} executed")
    reasons = judge(grand, args.min_executed, args.max_skipped)
    for reason in reasons:
        print(f"FAIL: {reason}", file=sys.stderr)
    return 1 if reasons else 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    totals = sub.add_parser("totals")
    totals.add_argument("--min-executed", type=int, default=MIN_EXECUTED)
    totals.add_argument("--max-skipped", type=int, default=MAX_SKIPPED)
    totals.add_argument("files", nargs="*")
    return command_totals(parser.parse_args(argv))


if __name__ == "__main__":
    sys.exit(main())
