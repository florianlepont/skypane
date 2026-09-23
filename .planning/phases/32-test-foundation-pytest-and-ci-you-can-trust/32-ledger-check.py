#!/usr/bin/env python3
"""Migration ledger tool for Phase 32 (32-CONTEXT.md "Migration ledger",
32-RESEARCH.md Pattern 1). One tool, three jobs, all driven by the same
per-harness baseline transcript + ledger fragment pair:

  --capture     run each of the 15 server-side harnesses standalone under
                the CURRENT (pre-migration) interpreter and record its own
                PASS/FAIL transcript to 32-BASELINE/<key>.txt, then
                (re)write 32-BASELINE/INDEX.md. Never grep source for
                `check(` call sites - some checks are loop-emitted, so the
                only reliable ground truth is the harness's own stdout
                (32-RESEARCH.md Pitfall 1).

  <harness> ... / --all (default)
                for each named harness (or all 15), load its baseline
                transcript and its ledger fragment (32-ledger/<key>.md,
                written by the plan that migrates that harness) and prove
                every baseline check is accounted for: mapped 1:1 to a
                real pytest node id ("ported"), or explicitly "deleted"
                with a non-empty reason, or "pending" (only counts as
                mapped with --allow-pending).

  --assemble    requires every one of the 15 fragments to pass --check,
                then concatenates them into 32-MIGRATION-LEDGER.md with a
                summary table and grand totals. Run once, by 32-13.

  --self-test   runs the pure parsing/matching/validation logic against
                in-memory strings (no filesystem, no subprocess) and
                exits 0 only if every case in this file's own docstring
                claims holds. RED before the logic below is implemented,
                GREEN after.

Stdlib only. Runnable as `server/.venv/bin/python3 <this file> ...` from
anywhere - the repo root and phase directory are both located from
__file__, never from cwd.
"""
import argparse
import datetime
import os
import re
import subprocess
import sys

# --- Location -----------------------------------------------------------
# This file lives directly inside the phase directory
# (.planning/phases/32-test-foundation-.../32-ledger-check.py). Three
# dirname() calls walk phase-dir -> phases -> .planning -> repo root.
PHASE_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(PHASE_DIR)))
BASELINE_DIR = os.path.join(PHASE_DIR, "32-BASELINE")
LEDGER_DIR = os.path.join(PHASE_DIR, "32-ledger")
LEDGER_FILE = os.path.join(PHASE_DIR, "32-MIGRATION-LEDGER.md")

# --- The 15 server-side harnesses (32-CONTEXT.md TST-02 scope) ---------
# Mirrors scripts/run_all_tests.py's own HARNESSES list (the server-side
# subset of it), which this migration eventually retires.
HARNESSES = [
    "server/test_calendar_rules.py",
    "server/test_colour_rules.py",
    "server/test_config_history.py",
    "server/test_dither.py",
    "server/test_enrich.py",
    "server/test_illustrations.py",
    "server/test_manual_resolutions.py",
    "server/test_notify.py",
    "server/test_panel_preview.py",
    "server/test_pipeline_e2e.py",
    "server/test_plane_detection.py",
    "server/test_poll_loop.py",
    "server/test_render.py",
    "server/test_runway_config.py",
    "stub-server/test_poll_cycle.py",
]


def harness_key(harness):
    """server/test_dither.py -> server__test_dither;
    stub-server/test_poll_cycle.py -> stub-server__test_poll_cycle."""
    return harness.replace("/", "__")[: -len(".py")]


# --- Baseline transcript parsing ----------------------------------------
# Every harness prints "PASS <label>" or "FAIL <label> - <reason>" per
# check (server/test_dither.py:39-48 is the canonical minimal example) and
# ends with "<name>: <passed>/<total> checks pass". A harness with an
# early-abort summary line mid-file (server/test_config_history.py:1660)
# prints more than one such line - the LAST one is authoritative.
SUMMARY_RE = re.compile(r"^(?P<name>.+): (?P<passed>\d+)/(?P<total>\d+) checks pass\s*$")


def parse_baseline(text):
    """Parse a harness transcript into (rows, total).

    rows: list of ("PASS"|"FAIL", label) tuples in source order. A FAIL
    label carries its full " - <reason>" tail verbatim; a PASS label does
    not. Any line that isn't a PASS/FAIL/summary line is noise and is
    ignored.

    total: the <total> from the LAST "<name>: <p>/<t> checks pass" line
    found (None if no such line exists).
    """
    rows = []
    total = None
    for line in text.splitlines():
        if line.startswith("PASS "):
            rows.append(("PASS", line[len("PASS ") :]))
            continue
        if line.startswith("FAIL "):
            rows.append(("FAIL", line[len("FAIL ") :]))
            continue
        m = SUMMARY_RE.match(line)
        if m:
            total = int(m.group("total"))
    return rows, total


def baseline_check_lines(text):
    """The raw PASS/FAIL lines only, in source order - what --check
    matches ledger fragment rows against."""
    return [line for line in text.splitlines() if line.startswith("PASS ") or line.startswith("FAIL ")]


def label_matches(baseline_line, ledger_label):
    """Does one raw baseline transcript line match a ledger fragment row's
    "Old check label" cell?

    PASS lines match only on exact label equality after rstrip. FAIL
    lines match when the line starts with "FAIL " + label + " - " (the
    harness's own reason follows), or equals "FAIL " + label exactly (a
    FAIL with no reason text) - never on a label that is merely a text
    prefix of a longer check name (see the RED-phase self-test case
    proving "FAIL boomer - x" does not match label "boom").
    """
    if baseline_line.startswith("PASS "):
        return baseline_line[len("PASS ") :].rstrip() == ledger_label.rstrip()
    if baseline_line.startswith("FAIL "):
        rest = baseline_line[len("FAIL ") :]
        return rest == ledger_label or rest.startswith(ledger_label + " - ")
    return False


# --- Ledger fragment escaping / parsing ----------------------------------


def escape_label(label):
    """Labels containing "|" are written escaped as "\\|" in a fragment's
    markdown table (a literal "|" would otherwise be read as a new
    column)."""
    return label.replace("|", "\\|")


def unescape_label(text):
    return text.replace("\\|", "|")


def parse_fragment_rows(text):
    """Parse a ledger fragment's markdown table:

        | # | Old check label | Disposition | New node id / reason |
        | --- | --- | --- | --- |
        | 1 | some label | ported | server/test_dither.py::test_foo |

    into a list of {"n":, "label":, "disposition":, "target":} dicts, with
    "|" unescaped inside label/target. Header and separator rows are
    skipped.
    """
    rows = []
    for line in text.splitlines():
        stripped = line.strip()
        if not (stripped.startswith("|") and stripped.endswith("|")):
            continue
        inner = stripped[1:-1]
        cells = [c.strip() for c in re.split(r"(?<!\\)\|", inner)]
        if len(cells) != 4:
            continue
        n = cells[0]
        if n == "#":
            continue  # header row
        if re.fullmatch(r"-+", n):
            continue  # "| --- | --- | --- | --- |" separator row
        rows.append(
            {
                "n": n,
                "label": unescape_label(cells[1]),
                "disposition": cells[2],
                "target": unescape_label(cells[3]),
            }
        )
    return rows


# --- Pure validation logic (the part --self-test exercises in-memory) ---


def validate_fragment(fragment_rows, baseline_lines, node_ids, harness_source, allow_pending):
    """Does a parsed ledger fragment fully and correctly account for a
    harness's baseline transcript? Pure function - no filesystem, no
    subprocess - so --self-test can exercise it with synthetic in-memory
    data.

    Returns (failures, counts): failures is a list of human-readable
    reasons (empty means OK); counts is {"ported":, "deleted":, "pending":}.

    Fails when:
      - row count != baseline count
      - the label multiset differs (a baseline check with no matching
        ledger row, or a ledger row with no matching baseline check)
      - a row's disposition is not one of ported/deleted/pending
      - a "ported" row's target is absent from node_ids
      - a "deleted" row has an empty target (reason)
      - a "pending" row exists and allow_pending is False
      - the harness source still contains "EXPECTED_CHECK_COUNT" or
        "def check(" while the fragment declares ported/deleted rows
        (a contradiction: the ledger claims migration happened but the
        old harness idiom is still on disk)
    """
    failures = []
    if len(fragment_rows) != len(baseline_lines):
        failures.append(
            "row count mismatch: ledger has %d rows, baseline has %d checks"
            % (len(fragment_rows), len(baseline_lines))
        )

    remaining = list(baseline_lines)
    unmatched_rows = []
    counts = {"ported": 0, "deleted": 0, "pending": 0}
    for row in fragment_rows:
        disp = row["disposition"]
        if disp not in ("ported", "deleted", "pending"):
            failures.append("row %r has an unknown disposition %r (must be ported/deleted/pending)" % (row["label"], disp))
        elif disp == "ported":
            counts["ported"] += 1
            if row["target"] not in node_ids:
                failures.append(
                    "ported row %r targets node id %r, not found in `pytest --collect-only` output"
                    % (row["label"], row["target"])
                )
        elif disp == "deleted":
            counts["deleted"] += 1
            if not row["target"].strip():
                failures.append("deleted row %r has an empty reason" % (row["label"],))
        else:  # pending
            counts["pending"] += 1
            if not allow_pending:
                failures.append("row %r is pending and --allow-pending was not given" % (row["label"],))

        match_index = None
        for i, line in enumerate(remaining):
            if label_matches(line, row["label"]):
                match_index = i
                break
        if match_index is None:
            unmatched_rows.append(row["label"])
        else:
            del remaining[match_index]

    if unmatched_rows:
        failures.append("ledger rows with no matching baseline check: %r" % (unmatched_rows,))
    if remaining:
        failures.append("baseline checks with no matching ledger row: %r" % (remaining,))

    if (counts["ported"] or counts["deleted"]) and harness_source is not None:
        if "EXPECTED_CHECK_COUNT" in harness_source or "def check(" in harness_source:
            failures.append(
                "harness source still contains EXPECTED_CHECK_COUNT or def check( "
                "even though the fragment declares ported/deleted rows"
            )

    return failures, counts


# --- Filesystem/subprocess glue (not exercised by --self-test) ----------


def collect_node_ids_and_errors():
    """Run `pytest --collect-only -q` once and return (node_ids,
    error_files, returncode). Parses stdout even on a non-zero exit code,
    because a sibling plan may be mid-edit on another file in the same
    working tree - a collection error in a file OTHER than the harness
    being checked is the caller's problem to warn about, not to fail on.
    """
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q", "-p", "no:cacheprovider", "server", "stub-server"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    node_ids = set()
    error_files = set()
    for raw in proc.stdout.splitlines():
        line = raw.strip()
        if "::" in line and not line.startswith("=") and not line.lower().startswith("error"):
            node_ids.add(line)
            continue
        m = re.match(r"^ERROR\s+(\S+)", line)
        if m:
            error_files.add(m.group(1))
    return node_ids, error_files, proc.returncode


def check_one(harness, allow_pending, verbose=True):
    """Check one harness's ledger fragment against its baseline. Returns a
    dict: {"harness", "ok", "baseline_count", "counts", "fragment_text"}.
    """
    result = {
        "harness": harness,
        "ok": False,
        "baseline_count": None,
        "counts": None,
        "fragment_text": None,
    }

    def fail(msg):
        if verbose:
            print("%s: FAIL - %s" % (harness, msg), file=sys.stderr)

    key = harness_key(harness)
    baseline_path = os.path.join(BASELINE_DIR, key + ".txt")
    if not os.path.isfile(baseline_path):
        fail("no baseline transcript at %s (run --capture first)" % baseline_path)
        return result
    with open(baseline_path) as f:
        baseline_text = f.read()
    lines = baseline_check_lines(baseline_text)
    result["baseline_count"] = len(lines)

    fragment_path = os.path.join(LEDGER_DIR, key + ".md")
    if not os.path.isfile(fragment_path):
        fail("no ledger fragment at %s" % fragment_path)
        return result
    with open(fragment_path) as f:
        fragment_text = f.read()
    result["fragment_text"] = fragment_text
    fragment_rows = parse_fragment_rows(fragment_text)

    node_ids, error_files, _rc = collect_node_ids_and_errors()
    norm_harness = os.path.normpath(harness)
    other_errors = {e for e in error_files if os.path.normpath(e) != norm_harness}
    harness_has_error = any(os.path.normpath(e) == norm_harness for e in error_files)
    if other_errors and verbose:
        print(
            "WARNING: pytest --collect-only reported collection errors in other files "
            "(a sibling plan may be mid-edit): %r" % sorted(other_errors),
            file=sys.stderr,
        )
    if harness_has_error:
        fail("pytest --collect-only itself failed to collect this harness")
        return result

    harness_path = os.path.join(REPO_ROOT, harness)
    harness_source = None
    if os.path.isfile(harness_path):
        with open(harness_path) as f:
            harness_source = f.read()

    failures, counts = validate_fragment(fragment_rows, lines, node_ids, harness_source, allow_pending)
    result["counts"] = counts
    if failures:
        for msg in failures:
            fail(msg)
        return result

    result["ok"] = True
    if verbose:
        print(
            "%s: %d/%d baseline checks mapped (%d ported, %d deleted, %d pending)"
            % (harness, len(fragment_rows), len(lines), counts["ported"], counts["deleted"], counts["pending"])
        )
    return result


def write_index(rows):
    python_version = sys.version.split()[0]
    euid = os.geteuid() if hasattr(os, "geteuid") else "n/a"
    try:
        git_rev = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, capture_output=True, text=True, check=True
        ).stdout.strip()
    except Exception:
        git_rev = "unknown"
    timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    lines = [
        "# Baseline capture index",
        "",
        "Captured: %s (UTC)" % timestamp,
        "Python version: %s" % python_version,
        "euid: %s" % euid,
        "Capture commit: %s" % git_rev,
        "",
        "| Harness | Transcript | PASS | FAIL | Total | Exit code | Summary line |",
        "| --- | --- | ---: | ---: | ---: | --- | --- |",
    ]
    grand_total = 0
    for row in rows:
        lines.append(
            "| %s | `%s.txt` | %d | %d | %s | %s | %s |"
            % (
                row["harness"],
                row["key"],
                row["pass"],
                row["fail"],
                row["total"] if row["total"] is not None else "?",
                row["exit_code"],
                (row["summary"] or "").replace("|", "\\|"),
            )
        )
        if row["total"]:
            grand_total += row["total"]
    lines.append("")
    lines.append("Grand total: %d checks across %d harnesses" % (grand_total, len(rows)))
    lines.append("")
    with open(os.path.join(BASELINE_DIR, "INDEX.md"), "w") as f:
        f.write("\n".join(lines) + "\n")


def cmd_capture(args):
    targets = args.harnesses if args.harnesses else HARNESSES
    os.makedirs(BASELINE_DIR, exist_ok=True)
    index_rows = []
    for harness in targets:
        key = harness_key(harness)
        out_path = os.path.join(BASELINE_DIR, key + ".txt")
        if os.path.exists(out_path) and not args.force:
            print("refusing to overwrite existing baseline %s (use --force)" % out_path, file=sys.stderr)
            return 1
        harness_path = os.path.join(REPO_ROOT, harness)
        with open(harness_path) as f:
            source = f.read()
        if "EXPECTED_CHECK_COUNT" not in source:
            print(
                "refusing to capture %s: no EXPECTED_CHECK_COUNT found in it (already migrated?)" % harness,
                file=sys.stderr,
            )
            return 1

        exit_code = None
        stdout = ""
        try:
            proc = subprocess.run(
                [sys.executable, harness_path], cwd=REPO_ROOT, capture_output=True, text=True, timeout=900
            )
            stdout = proc.stdout + proc.stderr
            exit_code = proc.returncode
        except subprocess.TimeoutExpired as exc:
            stdout = (exc.stdout or "") + (exc.stderr or "")
            exit_code = "TIMEOUT(900s)"

        with open(out_path, "w") as f:
            f.write(stdout)

        rows, total = parse_baseline(stdout)
        pass_count = sum(1 for status, _ in rows if status == "PASS")
        fail_count = sum(1 for status, _ in rows if status == "FAIL")
        summary_line = ""
        for line in reversed(stdout.splitlines()):
            if SUMMARY_RE.match(line):
                summary_line = line
                break
        if total is None or (pass_count + fail_count) != total:
            print(
                "WARNING: %s printed %d PASS/FAIL lines but its own last summary total is %r "
                "(the harness may have aborted early - stop and report this)" % (harness, pass_count + fail_count, total),
                file=sys.stderr,
            )
        index_rows.append(
            {
                "harness": harness,
                "key": key,
                "pass": pass_count,
                "fail": fail_count,
                "total": total,
                "summary": summary_line,
                "exit_code": exit_code,
            }
        )
        print("%s -> %s (%d PASS, %d FAIL, exit %s)" % (harness, out_path, pass_count, fail_count, exit_code))

    write_index(index_rows)
    return 0


def cmd_assemble(_args):
    results = [check_one(h, allow_pending=False) for h in HARNESSES]
    if not all(r["ok"] for r in results):
        print("cannot assemble: one or more fragments failed --check (see above)", file=sys.stderr)
        return 1

    lines = [
        "# Phase 32 Migration Ledger",
        "",
        "Generated by `32-ledger-check.py --assemble`. Do not hand-edit; re-run `--assemble` instead.",
        "",
        "## Format",
        "",
        "Each fragment lives at `32-ledger/<key>.md`, one per harness, with the header",
        "`# Ledger: <harness>`, a `Baseline:` line naming the transcript and its check count, then a table:",
        "",
        "| # | Old check label | Disposition | New node id / reason |",
        "| --- | --- | --- | --- |",
        "",
        "Disposition is one of `ported`, `deleted`, `pending`. A `|` inside a label is escaped as `\\|`.",
        "",
        "## Summary",
        "",
        "| Harness | Baseline | Ported | Deleted | Fragment |",
        "| --- | ---: | ---: | ---: | --- |",
    ]
    grand_baseline = grand_ported = grand_deleted = 0
    for harness, result in zip(HARNESSES, results):
        key = harness_key(harness)
        counts = result["counts"]
        lines.append(
            "| %s | %d | %d | %d | `32-ledger/%s.md` |"
            % (harness, result["baseline_count"], counts["ported"], counts["deleted"], key)
        )
        grand_baseline += result["baseline_count"]
        grand_ported += counts["ported"]
        grand_deleted += counts["deleted"]
    lines.append("")
    lines.append("Grand totals: %d baseline checks, %d ported, %d deleted." % (grand_baseline, grand_ported, grand_deleted))
    lines.append("")
    for harness, result in zip(HARNESSES, results):
        lines.append("## %s" % harness)
        lines.append("")
        lines.append(result["fragment_text"].rstrip())
        lines.append("")

    with open(LEDGER_FILE, "w") as f:
        f.write("\n".join(lines) + "\n")
    print("wrote %s" % LEDGER_FILE)
    return 0


def cmd_check(args):
    targets = args.harnesses if args.harnesses else HARNESSES
    ok = True
    for harness in targets:
        result = check_one(harness, args.allow_pending)
        if not result["ok"]:
            ok = False
    return 0 if ok else 1


# --- Self-test (exercises the pure logic above with in-memory data) -----


def run_self_tests():
    failures = []
    checks = [0]

    def expect(cond, msg):
        checks[0] += 1
        if not cond:
            failures.append(msg)

    def run_case(name, fn):
        try:
            fn()
        except Exception as exc:  # a raising stub is a RED failure, not a crash
            checks[0] += 1
            failures.append("%s raised %r" % (name, exc))

    def case_parse_baseline():
        rows, total = parse_baseline("PASS a\nFAIL b - boom\nnoise\nx: 1/2 checks pass")
        expect(rows == [("PASS", "a"), ("FAIL", "b - boom")], "parse_baseline rows: got %r" % (rows,))
        expect(total == 2, "parse_baseline total: got %r" % (total,))

    def case_parse_baseline_last_summary_wins():
        rows, total = parse_baseline("PASS a\nx: 1/5 checks pass\nFAIL b - boom\nx: 1/2 checks pass")
        expect(len(rows) == 2, "parse_baseline should still find both PASS/FAIL rows: got %r" % (rows,))
        expect(total == 2, "parse_baseline must use the LAST summary line (early-abort case): got %r" % (total,))

    def case_label_matches():
        expect(label_matches("FAIL b - boom", "b") is True, "FAIL ... - <reason> should match its bare label")
        expect(label_matches("FAIL b", "b") is True, "a FAIL line with no reason text should match exactly")
        expect(
            label_matches("FAIL boomer - x", "boom") is False,
            "a label that is only a text PREFIX of a longer check name must not match",
        )
        expect(label_matches("PASS a", "a") is True, "PASS should match on exact label equality")
        expect(label_matches("PASS a ", "a") is True, "PASS matching must rstrip")
        expect(label_matches("PASS ab", "a") is False, "PASS must not match a partial label")

    def case_escape_unescape():
        expect(escape_label("a|b") == "a\\|b", "escape_label: got %r" % (escape_label("a|b"),))
        expect(unescape_label("a\\|b") == "a|b", "unescape_label: got %r" % (unescape_label("a\\|b"),))
        expect(unescape_label(escape_label("x|y|z")) == "x|y|z", "escape/unescape must round-trip")

    def case_parse_fragment_rows():
        table = (
            "| # | Old check label | Disposition | New node id / reason |\n"
            "| --- | --- | --- | --- |\n"
            "| 1 | a\\|b | ported | server/test_dither.py::test_a |\n"
            "| 2 | c | deleted | superseded by test_a |\n"
        )
        rows = parse_fragment_rows(table)
        expect(len(rows) == 2, "parse_fragment_rows should find 2 data rows: got %r" % (len(rows),))
        expect(rows[0]["label"] == "a|b", "parse_fragment_rows must unescape labels: got %r" % (rows[0]["label"],))
        expect(rows[0]["disposition"] == "ported", "disposition parse failed: %r" % (rows[0],))
        expect(rows[1]["target"] == "superseded by test_a", "target parse failed: %r" % (rows[1],))

    def case_validate_fragment_happy_path():
        baseline_lines = ["PASS a|b", "FAIL c - boom"]
        rows = [
            {"label": "a|b", "disposition": "ported", "target": "server/test_dither.py::test_a"},
            {"label": "c", "disposition": "deleted", "target": "superseded by test_a"},
        ]
        node_ids = {"server/test_dither.py::test_a"}
        failures_out, counts = validate_fragment(rows, baseline_lines, node_ids, "", allow_pending=False)
        expect(failures_out == [], "happy path should have zero failures: %r" % (failures_out,))
        expect(counts == {"ported": 1, "deleted": 1, "pending": 0}, "happy path counts: %r" % (counts,))

    def case_validate_fragment_row_count_mismatch():
        baseline_lines = ["PASS a|b", "FAIL c - boom"]
        rows = [{"label": "a|b", "disposition": "ported", "target": "server/test_dither.py::test_a"}]
        failures_out, _counts = validate_fragment(rows, baseline_lines, {"server/test_dither.py::test_a"}, "", False)
        expect(
            any("row count mismatch" in m for m in failures_out),
            "row-count mismatch should be reported: %r" % (failures_out,),
        )

    def case_validate_fragment_ported_node_id_missing():
        baseline_lines = ["PASS a|b", "FAIL c - boom"]
        rows = [
            {"label": "a|b", "disposition": "ported", "target": "server/test_dither.py::test_MISSING"},
            {"label": "c", "disposition": "deleted", "target": "superseded"},
        ]
        failures_out, _counts = validate_fragment(rows, baseline_lines, {"server/test_dither.py::test_a"}, "", False)
        expect(
            any("not found in `pytest --collect-only`" in m for m in failures_out),
            "a ported row whose node id was not collected must fail: %r" % (failures_out,),
        )

    def case_validate_fragment_deleted_empty_reason():
        baseline_lines = ["PASS a|b", "FAIL c - boom"]
        rows = [
            {"label": "a|b", "disposition": "ported", "target": "server/test_dither.py::test_a"},
            {"label": "c", "disposition": "deleted", "target": ""},
        ]
        failures_out, _counts = validate_fragment(rows, baseline_lines, {"server/test_dither.py::test_a"}, "", False)
        expect(
            any("empty reason" in m for m in failures_out),
            "a deleted row with an empty reason must fail: %r" % (failures_out,),
        )

    def case_validate_fragment_pending_gating():
        baseline_lines = ["PASS a|b", "FAIL c - boom"]
        rows = [
            {"label": "a|b", "disposition": "pending", "target": ""},
            {"label": "c", "disposition": "deleted", "target": "superseded"},
        ]
        node_ids = set()
        failures_out, _counts = validate_fragment(rows, baseline_lines, node_ids, "", allow_pending=False)
        expect(
            any("pending" in m and "--allow-pending" in m for m in failures_out),
            "a pending row without --allow-pending must fail: %r" % (failures_out,),
        )
        failures_out2, counts2 = validate_fragment(rows, baseline_lines, node_ids, "", allow_pending=True)
        expect(
            not any("--allow-pending was not given" in m for m in failures_out2),
            "with --allow-pending a pending row must count as mapped: %r" % (failures_out2,),
        )
        expect(counts2["pending"] == 1, "pending count with allow_pending=True: %r" % (counts2,))

    def case_validate_fragment_leftover_markers():
        baseline_lines = ["PASS a|b", "FAIL c - boom"]
        rows = [
            {"label": "a|b", "disposition": "ported", "target": "server/test_dither.py::test_a"},
            {"label": "c", "disposition": "deleted", "target": "superseded"},
        ]
        node_ids = {"server/test_dither.py::test_a"}
        failures_out, _counts = validate_fragment(rows, baseline_lines, node_ids, "EXPECTED_CHECK_COUNT = 2\n", False)
        expect(
            any("still contains" in m for m in failures_out),
            "leftover EXPECTED_CHECK_COUNT must fail a fully-ported/deleted fragment: %r" % (failures_out,),
        )
        failures_out2, _counts2 = validate_fragment(rows, baseline_lines, node_ids, "def check(name, fn):\n", False)
        expect(
            any("still contains" in m for m in failures_out2),
            "leftover def check( must fail a fully-ported/deleted fragment: %r" % (failures_out2,),
        )

    for name, fn in [
        ("parse_baseline", case_parse_baseline),
        ("parse_baseline (last summary wins)", case_parse_baseline_last_summary_wins),
        ("label_matches", case_label_matches),
        ("escape/unescape", case_escape_unescape),
        ("parse_fragment_rows", case_parse_fragment_rows),
        ("validate_fragment happy path", case_validate_fragment_happy_path),
        ("validate_fragment row count mismatch", case_validate_fragment_row_count_mismatch),
        ("validate_fragment ported node id missing", case_validate_fragment_ported_node_id_missing),
        ("validate_fragment deleted empty reason", case_validate_fragment_deleted_empty_reason),
        ("validate_fragment pending gating", case_validate_fragment_pending_gating),
        ("validate_fragment leftover markers", case_validate_fragment_leftover_markers),
    ]:
        run_case(name, fn)

    if failures:
        print("SELF-TEST FAILED (%d/%d checks failed):" % (len(failures), checks[0]))
        for msg in failures:
            print(" - %s" % msg)
        return 1
    print("SELF-TEST OK (%d checks)" % checks[0])
    return 0


# --- CLI -------------------------------------------------------------


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("harnesses", nargs="*", help="harness paths to check (default: all 15)")
    parser.add_argument("--capture", action="store_true", help="capture pre-migration baseline transcripts")
    parser.add_argument("--force", action="store_true", help="with --capture, overwrite an existing transcript")
    parser.add_argument("--all", action="store_true", help="explicit alias for the default (check all 15)")
    parser.add_argument(
        "--allow-pending", action="store_true", help="a 'pending' ledger row counts as mapped (used by staged migrations)"
    )
    parser.add_argument("--assemble", action="store_true", help="assemble all 15 fragments into the migration ledger")
    parser.add_argument("--self-test", action="store_true", help="run the pure-logic self-tests and exit")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    if args.self_test:
        return run_self_tests()
    if args.capture:
        return cmd_capture(args)
    if args.assemble:
        return cmd_assemble(args)
    return cmd_check(args)


if __name__ == "__main__":
    sys.exit(main())
