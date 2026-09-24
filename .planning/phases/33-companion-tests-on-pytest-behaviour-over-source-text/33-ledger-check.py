#!/usr/bin/env python3
"""Migration ledger tool for Phase 33 (33-CONTEXT.md "Migration ledger and
parity", 33-MIGRATION-RULES.md sections 0, 1 and 4). Extends
32-ledger-check.py's architecture (baseline transcript -> ledger fragment
-> validate_fragment() pure matching -> --assemble concatenation) for a
STAGED migration: the 9 companion harnesses migrate across several plans
each, so a harness's ledger fragment legitimately has `pending` rows even
mid-migration. The rule this tool enforces is that a fragment's pending-row
count always equals the shrunk legacy harness's own remaining
`EXPECTED_CHECK_COUNT` - every check is always accounted for as either
still-legacy or already-ported, never both, never neither.

  --capture       run each of the 9 companion harnesses standalone under the
                  CURRENT (pre-migration) interpreter and record its own
                  PASS/FAIL transcript to 33-BASELINE/<key>.txt, then
                  (re)write 33-BASELINE/INDEX.md. Never grep source for
                  `check(` call sites - some checks are loop-emitted, so the
                  only reliable ground truth is the harness's own stdout.
                  The 3 browser harnesses need a real Chromium
                  (PLAYWRIGHT_BROWSERS_PATH is inherited from the caller's
                  environment); a transcript with a `SKIP ` line, with zero
                  PASS/FAIL lines, or whose PASS+FAIL count disagrees with
                  its own printed total is REJECTED (kept on disk with a
                  `.rejected` suffix, non-zero exit) - a browser harness that
                  silently SKIPped must never read as a real baseline run.

  --scaffold [harness...|--all] [--force]
                  write 33-ledger/<key>.md for each named harness (or all 9,
                  with --all) with every baseline row set to `pending`, an
                  empty target. Refuses to overwrite an existing fragment
                  unless --force is given.

  --add-check <harness> <label> --source <sha>
                  record a check added to a harness AFTER its baseline was
                  captured (33-MIGRATION-RULES.md section 0: a Phase 37
                  merge landing a new legacy check() call on a harness that
                  is still legacy). Appends `PASS <label>` to
                  33-BASELINE/<key>.addendum.txt, preceded by a
                  `# added after audit baseline: <sha>` comment line, and
                  appends a `pending` row to that harness's fragment.
                  Prints a reminder to bump the legacy EXPECTED_CHECK_COUNT.

  <harness> ... / --all (default)
                  for each named harness (or all 9), load its baseline
                  transcript (+ addendum, if any) and its ledger fragment
                  (33-ledger/<key>.md, written by --scaffold and flipped by
                  the plans that migrate that harness) and prove every
                  baseline check is accounted for: mapped 1:1 to a real
                  pytest node id ("ported"), explicitly "deleted" with a
                  non-empty reason, or "pending" (only counts as mapped with
                  --allow-pending, and only when the pending count equals
                  the shrunk legacy harness's own remaining
                  EXPECTED_CHECK_COUNT - the staged-migration rule).

  --assemble      requires every one of the 9 fragments to pass --check with
                  zero pending rows, then concatenates them into
                  33-MIGRATION-LEDGER.md (keeping that file's own scaffolded
                  header verbatim up to its `<!-- fragments -->` marker
                  line) with a summary table and grand totals. Run once, by
                  33-33. Also prints `phase33_total=<n>` on stdout.

  --self-test     runs the pure parsing/matching/validation logic against
                  in-memory strings (no filesystem, no subprocess) and
                  exits 0 only if every case in this file's own docstring
                  claims holds, plus the staged-migration cases 33-01 added
                  on top of 32's. RED before the logic below is
                  implemented, GREEN after.

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
# (.planning/phases/33-companion-tests-.../33-ledger-check.py). Three
# dirname() calls walk phase-dir -> phases -> .planning -> repo root.
PHASE_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(PHASE_DIR)))
BASELINE_DIR = os.path.join(PHASE_DIR, "33-BASELINE")
LEDGER_DIR = os.path.join(PHASE_DIR, "33-ledger")
LEDGER_FILE = os.path.join(PHASE_DIR, "33-MIGRATION-LEDGER.md")

# --- The 9 companion harnesses (33-CONTEXT.md TST-10/TST-11 scope) ------
BROWSER_HARNESSES = {
    "companion/test_browser_ux_health_drawings.py",
    "companion/test_browser_ux_quiet_wake.py",
    "companion/test_browser_ux.py",
}

HARNESSES = [
    "companion/test_contrast_check.py",
    "companion/test_i18n.py",
    "companion/test_view_pages.py",
    "companion/test_config_page.py",
    "companion/test_companion_app.py",
    "companion/test_status_pages.py",
    "companion/test_browser_ux_health_drawings.py",
    "companion/test_browser_ux_quiet_wake.py",
    "companion/test_browser_ux.py",
]


def harness_key(harness):
    """server/test_dither.py -> server__test_dither;
    stub-server/test_poll_cycle.py -> stub-server__test_poll_cycle."""
    return harness.replace("/", "__")[: -len(".py")]


# --- Baseline transcript parsing ----------------------------------------
# Every harness prints "PASS <label>" or "FAIL <label> - <reason>" per
# check and ends with "<name>: <passed>/<total> checks pass". A harness
# with an early-abort summary line mid-file prints more than one such line
# - the LAST one is authoritative. companion/test_i18n.py is the one
# outlier: its summary line is "<passed>/<total> checks pass" with NO
# "<name>: " prefix at all, so that group is optional.
SUMMARY_RE = re.compile(r"^(?:(?P<name>.+): )?(?P<passed>\d+)/(?P<total>\d+) checks pass\s*$")


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


def combine_baseline_and_addendum(baseline_lines, addendum_text):
    """The transcript's own PASS/FAIL lines, followed by the addendum
    file's PASS lines (33-MIGRATION-RULES.md section 0: a check added to a
    still-legacy harness after the baseline was captured, recorded by
    `--add-check`). A line in the addendum starting with "#" is a comment
    (e.g. "# added after audit baseline: <sha>") and is ignored. Pure -
    takes the already-parsed baseline lines and the addendum's raw text (or
    None if there is no addendum file), so --self-test can exercise it
    in-memory."""
    if not addendum_text:
        return list(baseline_lines)
    combined = list(baseline_lines)
    for line in addendum_text.splitlines():
        if line.startswith("#"):
            continue
        if line.startswith("PASS "):
            combined.append(line)
    return combined


def load_baseline_lines(key):
    """Filesystem wrapper: reads 33-BASELINE/<key>.txt and, if present,
    33-BASELINE/<key>.addendum.txt, and combines them via
    combine_baseline_and_addendum()."""
    baseline_path = os.path.join(BASELINE_DIR, key + ".txt")
    with open(baseline_path) as f:
        transcript_text = f.read()
    lines = baseline_check_lines(transcript_text)
    addendum_path = os.path.join(BASELINE_DIR, key + ".addendum.txt")
    addendum_text = None
    if os.path.isfile(addendum_path):
        with open(addendum_path) as f:
            addendum_text = f.read()
    return combine_baseline_and_addendum(lines, addendum_text)


def validate_transcript(stdout):
    """Does a freshly captured transcript look like a real run? Returns
    None when it does, or a human-readable rejection reason otherwise.
    Rejects: a line starting "SKIP " (a browser harness that gave up
    without a real Chromium must never read as a real baseline - it exits
    0 and looks superficially like success); zero PASS/FAIL lines; or a
    PASS+FAIL count that disagrees with the transcript's own last
    "checks pass" summary line (the harness aborted early)."""
    for line in stdout.splitlines():
        if line.startswith("SKIP "):
            return "transcript contains a line starting 'SKIP ' (the harness did not really run)"
    rows, total = parse_baseline(stdout)
    if not rows:
        return "transcript has zero PASS/FAIL lines"
    if total is None or len(rows) != total:
        return "PASS+FAIL count (%d) does not match the transcript's own printed total (%r)" % (len(rows), total)
    return None


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


def remaining_legacy_count(source):
    """The int from the LAST line matching `^EXPECTED_CHECK_COUNT\\s*=\\s*(\\d+)`
    in a legacy harness's source, or None if no such line exists (or
    `source` itself is None: the legacy file no longer exists). A legacy
    harness has exactly one authoritative EXPECTED_CHECK_COUNT assignment
    (33-MIGRATION-RULES.md section 1) but this takes the LAST match rather
    than assuming that, matching parse_baseline()'s own "last one wins"
    convention for early-abort summary lines."""
    if source is None:
        return None
    matches = re.findall(r"^EXPECTED_CHECK_COUNT\s*=\s*(\d+)", source, re.MULTILINE)
    if not matches:
        return None
    return int(matches[-1])


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
      - staged-migration consistency (33-MIGRATION-RULES.md section 1):
        if any row is pending, `harness_source` must not be None (the
        legacy harness must still exist) and its `remaining_legacy_count`
        must equal the pending-row count; if zero rows are pending,
        `harness_source` must be None or contain neither
        "EXPECTED_CHECK_COUNT" nor "def check(" (a fully-migrated harness
        leaves no legacy idiom behind)
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

    pending = counts["pending"]
    if pending > 0:
        if harness_source is None:
            failures.append("legacy harness missing while %d rows pending" % pending)
        else:
            remaining = remaining_legacy_count(harness_source)
            if remaining != pending:
                failures.append(
                    "legacy harness still runs %s checks (remaining EXPECTED_CHECK_COUNT) "
                    "but ledger has %d pending rows" % (remaining, pending)
                )
    elif harness_source is not None:
        if "EXPECTED_CHECK_COUNT" in harness_source or "def check(" in harness_source:
            failures.append(
                "harness source still contains EXPECTED_CHECK_COUNT or def check( "
                "even though the fragment declares zero pending rows"
            )

    return failures, counts


# --- Filesystem/subprocess glue (not exercised by --self-test) ----------


def collect_node_ids_and_errors():
    """Run `pytest --collect-only -q` once and return (node_ids,
    error_files, returncode). Parses stdout even on a non-zero exit code,
    because a sibling plan may be mid-edit on another file in the same
    working tree - a collection error in a file OTHER than the harness
    being checked (and its own new modules) is the caller's problem to
    warn about, not to fail on.
    """
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q", "-p", "no:cacheprovider", "companion", "test-support"],
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
    lines = load_baseline_lines(key)
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
    # The harness's own new modules (companion/test_<stem>_NN.py, part of a
    # staged migration's chain) count as "this harness" for error purposes
    # too - a collection error there is this check's problem, not a
    # sibling plan's.
    stem_key = key.split("__", 1)[-1]  # "companion__test_status_pages" -> "test_status_pages"
    own_prefix = "companion/%s" % stem_key

    def is_own_file(path):
        norm = os.path.normpath(path).replace(os.sep, "/")
        return norm == norm_harness or (norm.startswith(own_prefix) and norm.endswith(".py"))

    own_errors = {e for e in error_files if is_own_file(e)}
    other_errors = {e for e in error_files if not is_own_file(e)}
    if other_errors and verbose:
        print(
            "WARNING: pytest --collect-only reported collection errors in other files "
            "(a sibling plan may be mid-edit): %r" % sorted(other_errors),
            file=sys.stderr,
        )
    if own_errors:
        fail("pytest --collect-only itself failed to collect this harness or its own modules: %r" % sorted(own_errors))
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


def get_chromium_executable_path():
    """The Chromium executable path pytest-playwright would launch, or
    "n/a" if playwright isn't importable or no browser is installed at all
    (a bare `sync_playwright().start().chromium.executable_path` reports
    the path even when the underlying binary is missing on disk, so this
    is a "would launch from here", not a "definitely launches" check -
    good enough for INDEX.md provenance)."""
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        return "n/a"
    try:
        p = sync_playwright().start()
        try:
            return p.chromium.executable_path
        finally:
            p.stop()
    except Exception:
        return "n/a"


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
    browsers_path = os.environ.get("PLAYWRIGHT_BROWSERS_PATH", "n/a")
    chromium_path = get_chromium_executable_path()

    lines = [
        "# Baseline capture index",
        "",
        "Captured: %s (UTC)" % timestamp,
        "Python version: %s" % python_version,
        "euid: %s" % euid,
        "Capture commit: %s" % git_rev,
        "PLAYWRIGHT_BROWSERS_PATH: %s" % browsers_path,
        "Chromium executable path: %s" % chromium_path,
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

        rejection = validate_transcript(stdout)
        if rejection is not None:
            rejected_path = out_path + ".rejected"
            with open(rejected_path, "w") as f:
                f.write(stdout)
            print(
                "REJECTED %s: %s (transcript kept at %s, not %s)"
                % (harness, rejection, rejected_path, out_path),
                file=sys.stderr,
            )
            return 1

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


def cmd_scaffold(args):
    targets = HARNESSES if args.all else args.harnesses
    if not targets:
        print("no harnesses given (name one or more, or pass --all)", file=sys.stderr)
        return 1
    os.makedirs(LEDGER_DIR, exist_ok=True)
    for harness in targets:
        key = harness_key(harness)
        baseline_path = os.path.join(BASELINE_DIR, key + ".txt")
        if not os.path.isfile(baseline_path):
            print(
                "no baseline transcript for %s at %s (run --capture first)" % (harness, baseline_path),
                file=sys.stderr,
            )
            return 1
        fragment_path = os.path.join(LEDGER_DIR, key + ".md")
        if os.path.isfile(fragment_path) and not args.force:
            print("refusing to overwrite existing fragment %s (use --force)" % fragment_path, file=sys.stderr)
            return 1

        lines = load_baseline_lines(key)
        out = [
            "# Ledger: %s" % harness,
            "",
            "Baseline: `%s.txt`, %d checks" % (key, len(lines)),
            "",
            "| # | Old check label | Disposition | New node id / reason |",
            "| --- | --- | --- | --- |",
        ]
        for i, line in enumerate(lines, start=1):
            label = line[len("PASS ") :] if line.startswith("PASS ") else line[len("FAIL ") :]
            out.append("| %d | %s | pending | |" % (i, escape_label(label)))
        out.append("")
        with open(fragment_path, "w") as f:
            f.write("\n".join(out) + "\n")
        print("wrote %s (%d pending rows)" % (fragment_path, len(lines)))
    return 0


def cmd_add_check(args):
    harness, label = args.add_check
    if not args.source:
        print("--add-check requires --source <sha>", file=sys.stderr)
        return 1
    key = harness_key(harness)
    os.makedirs(BASELINE_DIR, exist_ok=True)
    addendum_path = os.path.join(BASELINE_DIR, key + ".addendum.txt")
    with open(addendum_path, "a") as f:
        f.write("# added after audit baseline: %s\n" % args.source)
        f.write("PASS %s\n" % label)

    fragment_path = os.path.join(LEDGER_DIR, key + ".md")
    existing_rows = 0
    if os.path.isfile(fragment_path):
        with open(fragment_path) as f:
            existing_rows = len(parse_fragment_rows(f.read()))
    with open(fragment_path, "a") as f:
        f.write("| %d | %s | pending | |\n" % (existing_rows + 1, escape_label(label)))

    print("added pending row #%d for %r to %s" % (existing_rows + 1, label, fragment_path))
    print(
        "REMINDER: bump %s's legacy EXPECTED_CHECK_COUNT so it still equals its pending-row count"
        % harness
    )
    return 0


def cmd_assemble(_args):
    results = [check_one(h, allow_pending=False) for h in HARNESSES]
    if not all(r["ok"] for r in results):
        print("cannot assemble: one or more fragments failed --check (see above)", file=sys.stderr)
        return 1

    header_lines = []
    if os.path.isfile(LEDGER_FILE):
        with open(LEDGER_FILE) as f:
            existing = f.read()
        marker = "<!-- fragments -->"
        idx = existing.find(marker)
        if idx != -1:
            header_lines = existing[: idx + len(marker)].splitlines()
    if not header_lines:
        header_lines = ["# Phase 33 Migration Ledger", "", "<!-- fragments -->"]

    lines = list(header_lines)
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append("| Harness | Baseline | Addendum | Ported | Deleted | Fragment |")
    lines.append("| --- | ---: | ---: | ---: | ---: | --- |")
    grand_baseline = grand_addendum = grand_ported = grand_deleted = 0
    for harness, result in zip(HARNESSES, results):
        key = harness_key(harness)
        addendum_path = os.path.join(BASELINE_DIR, key + ".addendum.txt")
        addendum_count = 0
        if os.path.isfile(addendum_path):
            with open(addendum_path) as f:
                addendum_count = sum(1 for line in f if line.startswith("PASS "))
        counts = result["counts"]
        baseline_only = result["baseline_count"] - addendum_count
        lines.append(
            "| %s | %d | %d | %d | %d | `33-ledger/%s.md` |"
            % (harness, baseline_only, addendum_count, counts["ported"], counts["deleted"], key)
        )
        grand_baseline += baseline_only
        grand_addendum += addendum_count
        grand_ported += counts["ported"]
        grand_deleted += counts["deleted"]
    lines.append("")
    lines.append(
        "Grand totals: %d baseline checks, %d addendum checks, %d ported, %d deleted."
        % (grand_baseline, grand_addendum, grand_ported, grand_deleted)
    )
    lines.append("")
    for harness, result in zip(HARNESSES, results):
        lines.append("## %s" % harness)
        lines.append("")
        lines.append(result["fragment_text"].rstrip())
        lines.append("")

    with open(LEDGER_FILE, "w") as f:
        f.write("\n".join(lines) + "\n")
    print("wrote %s" % LEDGER_FILE)
    print("phase33_total=%d" % (grand_baseline + grand_addendum))
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

    def case_parse_baseline_no_name_prefix():
        # 33-01 Task 1 behavior: test_i18n.py prints "24/24 checks pass"
        # with no "<name>: " prefix, unlike every other companion harness.
        rows, total = parse_baseline("PASS a\nFAIL b - boom\n24/24 checks pass")
        expect(total == 24, "parse_baseline must accept a summary line with no name prefix: got %r" % (total,))
        rows2, total2 = parse_baseline("x: 1/2 checks pass")
        expect(total2 == 2, "parse_baseline must still accept a prefixed summary line: got %r" % (total2,))

    def case_validate_fragment_staged_pending_matches_remaining():
        baseline_lines = ["PASS a", "PASS b", "PASS c", "PASS d", "PASS e"]
        rows = [
            {"label": "a", "disposition": "ported", "target": "companion/test_x.py::test_a"},
            {"label": "b", "disposition": "ported", "target": "companion/test_x.py::test_b"},
            {"label": "c", "disposition": "pending", "target": ""},
            {"label": "d", "disposition": "pending", "target": ""},
            {"label": "e", "disposition": "pending", "target": ""},
        ]
        node_ids = {"companion/test_x.py::test_a", "companion/test_x.py::test_b"}
        source_ok = "some header\nEXPECTED_CHECK_COUNT = 3\ndef main():\n"
        failures_out, counts = validate_fragment(rows, baseline_lines, node_ids, source_ok, allow_pending=True)
        expect(failures_out == [], "staged pending==remaining should have zero failures: %r" % (failures_out,))
        expect(counts["pending"] == 3, "staged pending count: %r" % (counts,))

        source_stale = "some header\nEXPECTED_CHECK_COUNT = 4\ndef main():\n"
        failures_out2, _counts2 = validate_fragment(rows, baseline_lines, node_ids, source_stale, allow_pending=True)
        expect(
            any("remaining" in m and "4" in m and "3" in m for m in failures_out2),
            "a stale remaining EXPECTED_CHECK_COUNT must fail, mentioning 'remaining' and both numbers: %r"
            % (failures_out2,),
        )

    def case_validate_fragment_pending_with_missing_legacy_file():
        baseline_lines = ["PASS a"]
        rows = [{"label": "a", "disposition": "pending", "target": ""}]
        failures_out, _counts = validate_fragment(rows, baseline_lines, set(), None, allow_pending=True)
        expect(
            any("legacy harness missing" in m for m in failures_out),
            "pending rows with harness_source None must fail: %r" % (failures_out,),
        )

    def case_validate_fragment_zero_pending_ok_and_leftover_fails():
        baseline_lines = ["PASS a"]
        rows = [{"label": "a", "disposition": "ported", "target": "companion/test_x.py::test_a"}]
        node_ids = {"companion/test_x.py::test_a"}
        failures_out, _counts = validate_fragment(rows, baseline_lines, node_ids, None, allow_pending=False)
        expect(failures_out == [], "zero pending with harness_source None must be OK: %r" % (failures_out,))
        failures_out2, _counts2 = validate_fragment(
            rows, baseline_lines, node_ids, "EXPECTED_CHECK_COUNT = 0\n", allow_pending=False
        )
        expect(
            any("still contains" in m for m in failures_out2),
            "zero pending but source still has EXPECTED_CHECK_COUNT must fail: %r" % (failures_out2,),
        )
        failures_out3, _counts3 = validate_fragment(
            rows, baseline_lines, node_ids, "def check(name, fn):\n", allow_pending=False
        )
        expect(
            any("still contains" in m for m in failures_out3),
            "zero pending but source still has def check( must fail: %r" % (failures_out3,),
        )

    def case_combine_baseline_and_addendum():
        transcript_lines = ["PASS a", "FAIL b - boom"]
        addendum_text = "# added after audit baseline: deadbeef\nPASS c\n# a comment\nPASS d\n"
        combined = combine_baseline_and_addendum(transcript_lines, addendum_text)
        expect(
            combined == ["PASS a", "FAIL b - boom", "PASS c", "PASS d"],
            "combine_baseline_and_addendum must append addendum PASS lines, skipping '#' comments: %r" % (combined,),
        )
        combined_none = combine_baseline_and_addendum(transcript_lines, None)
        expect(
            combined_none == transcript_lines,
            "combine_baseline_and_addendum with no addendum must return the transcript lines unchanged: %r"
            % (combined_none,),
        )

    def case_validate_transcript_rejects_skip_and_empty():
        expect(
            validate_transcript("SKIP something\n1/1 checks pass\n") is not None,
            "a transcript with a SKIP line must be rejected",
        )
        expect(
            validate_transcript("no checks here\n") is not None,
            "a transcript with zero PASS/FAIL lines must be rejected",
        )
        expect(
            validate_transcript("PASS a\nPASS b\na: 2/2 checks pass\n") is None,
            "a clean transcript whose PASS+FAIL count matches its own total must be accepted",
        )
        expect(
            validate_transcript("PASS a\na: 2/2 checks pass\n") is not None,
            "a transcript whose PASS+FAIL count does not match its own total must be rejected",
        )

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
        ("parse_baseline no name prefix", case_parse_baseline_no_name_prefix),
        ("validate_fragment staged pending matches remaining", case_validate_fragment_staged_pending_matches_remaining),
        ("validate_fragment pending with missing legacy file", case_validate_fragment_pending_with_missing_legacy_file),
        ("validate_fragment zero pending ok / leftover fails", case_validate_fragment_zero_pending_ok_and_leftover_fails),
        ("combine_baseline_and_addendum", case_combine_baseline_and_addendum),
        ("validate_transcript rejects SKIP and empty", case_validate_transcript_rejects_skip_and_empty),
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
    parser.add_argument("harnesses", nargs="*", help="harness paths to check/scaffold (default: all 9)")
    parser.add_argument("--capture", action="store_true", help="capture pre-migration baseline transcripts")
    parser.add_argument("--force", action="store_true", help="with --capture/--scaffold, overwrite an existing file")
    parser.add_argument("--all", action="store_true", help="explicit alias for the default (check/scaffold all 9)")
    parser.add_argument(
        "--allow-pending", action="store_true", help="a 'pending' ledger row counts as mapped (used by staged migrations)"
    )
    parser.add_argument("--assemble", action="store_true", help="assemble all 9 fragments into the migration ledger")
    parser.add_argument("--scaffold", action="store_true", help="write all-pending ledger fragments for the given harnesses")
    parser.add_argument(
        "--add-check",
        nargs=2,
        metavar=("HARNESS", "LABEL"),
        help="record a check added to HARNESS after its baseline was captured",
    )
    parser.add_argument("--source", help="commit sha for --add-check (required)")
    parser.add_argument("--self-test", action="store_true", help="run the pure-logic self-tests and exit")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    if args.self_test:
        return run_self_tests()
    if args.capture:
        return cmd_capture(args)
    if args.scaffold:
        return cmd_scaffold(args)
    if args.add_check:
        return cmd_add_check(args)
    if args.assemble:
        return cmd_assemble(args)
    return cmd_check(args)


if __name__ == "__main__":
    sys.exit(main())
