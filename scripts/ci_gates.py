#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
"""Checks the totals of JUnit reports from the parallel test jobs. Stdlib only.

Subcommands:
  totals [--min-executed N] [--max-skipped K] FILE...
      Sums every `testsuite` of every file, prints per-file and grand totals,
      and exits 1 when there is any failure or error, when fewer than N tests
      executed (tests minus skipped), or when more than K tests were skipped.
      A missing file, a file that is not JUnit XML, or no file at all exits 2.
  artifacts --expected N (--with-coverage | --without-coverage) DIR
      Counts the JUnit files (junit-*.xml) and coverage data files (.coverage)
      under DIR. Exits 1 unless there are exactly N JUnit files and, with
      --with-coverage, exactly N coverage files. With --without-coverage the
      run did not measure coverage (pull requests): it prints that fact and
      exits 1 if any coverage file is present anyway, since that means the
      run measured and the coverage gate must not be skipped.
"""
import argparse
import os
import sys
import xml.etree.ElementTree as ET

# The number of tests the suite must execute and the number it may skip, as
# measured on the CI run of 2026-11-27 on main (run 45993237674: 17,598
# executed, none skipped). The executed floor may only go up; the skipped
# ceiling only down, with one exception: on 2026-11-27 it was lowered by 7 (to
# 17,591) because the owner approved deleting four functions that only tests
# called, together with the 7 tests that exercised only them.
MIN_EXECUTED = 17591
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


COVERAGE_NOT_MEASURED = "coverage: not measured on pull requests; measured on main"


def count_files(directory):
    """Returns (junit_files, coverage_files) found anywhere under directory."""
    junit = coverage = 0
    for _, _, names in os.walk(directory):
        for name in names:
            if name == ".coverage":
                coverage += 1
            elif name.startswith("junit-") and name.endswith(".xml"):
                junit += 1
    return junit, coverage


def command_artifacts(args):
    junit, coverage = count_files(args.directory)
    print(f"expected {args.expected} shards; found {coverage} coverage files "
          f"and {junit} JUnit files")
    reasons = []
    if junit != args.expected:
        reasons.append(f"{junit} JUnit files, expected {args.expected}")
    if args.with_coverage:
        if coverage != args.expected:
            reasons.append(f"{coverage} coverage files, expected {args.expected}")
    elif coverage:
        reasons.append(f"{coverage} coverage files found in a run that "
                       "should not have measured coverage")
    else:
        print(COVERAGE_NOT_MEASURED)
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
    artifacts = sub.add_parser("artifacts")
    artifacts.add_argument("--expected", type=int, required=True)
    mode = artifacts.add_mutually_exclusive_group(required=True)
    mode.add_argument("--with-coverage", dest="with_coverage", action="store_true")
    mode.add_argument("--without-coverage", dest="with_coverage", action="store_false")
    artifacts.add_argument("directory")
    args = parser.parse_args(argv)
    if args.command == "artifacts":
        return command_artifacts(args)
    return command_totals(args)


if __name__ == "__main__":
    sys.exit(main())
