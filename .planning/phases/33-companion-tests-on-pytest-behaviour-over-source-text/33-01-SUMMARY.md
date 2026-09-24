---
phase: 33-companion-tests-on-pytest-behaviour-over-source-text
plan: 01
subsystem: testing
tags: [pytest, playwright, migration-ledger, companion, chromium]

# Dependency graph
requires:
  - phase: 32-test-foundation-pytest-and-ci-you-can-trust
    provides: 32-ledger-check.py's architecture (baseline transcript -> ledger fragment -> validate_fragment() -> --assemble), reused and extended here
provides:
  - "33-ledger-check.py: capture/scaffold/add-check/check/assemble/self-test tool for the staged companion-harness migration"
  - "33-BASELINE/: 9 real pre-migration transcripts (1250 checks) plus INDEX.md with FAIL classification and the +1 discrepancy trace"
  - "33-ledger/: 9 all-pending ledger fragments, one per companion harness"
  - "33-MIGRATION-LEDGER.md scaffold: purpose, format, TST-12 rubric, staged-migration rule, status table (harness -> owning plans), verification command, <!-- fragments --> marker for 33-33"
affects: [33-04, 33-05, 33-06, 33-07, 33-08, 33-09, 33-10, 33-11, 33-12, 33-13, 33-14, 33-15, 33-16, 33-17, 33-18, 33-19, 33-20, 33-21, 33-22, 33-23, 33-24, 33-25, 33-26, 33-27, 33-28, 33-29, 33-30, 33-31, 33-33]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Staged-migration ledger consistency: a fragment's pending-row count must equal the shrunk legacy harness's own remaining EXPECTED_CHECK_COUNT (validate_fragment()'s remaining_legacy_count() rule), so large harnesses can migrate across many plans while the suite stays provably fully accounted for after every one"
    - "Addendum mechanism: a check added to a still-legacy harness after its baseline was captured is recorded via --add-check into <key>.addendum.txt (PASS lines + a '# added after audit baseline: <sha>' comment) rather than re-capturing the whole baseline"
    - "Capture-time transcript validation: --capture rejects (non-zero exit, .rejected suffix) any transcript with a SKIP line, zero PASS/FAIL lines, or a PASS+FAIL count that disagrees with the harness's own printed total - a browser harness that silently skipped must never read as a real baseline"

key-files:
  created:
    - .planning/phases/33-companion-tests-on-pytest-behaviour-over-source-text/33-ledger-check.py
    - .planning/phases/33-companion-tests-on-pytest-behaviour-over-source-text/33-BASELINE/INDEX.md
    - .planning/phases/33-companion-tests-on-pytest-behaviour-over-source-text/33-BASELINE/*.txt (9 transcripts)
    - .planning/phases/33-companion-tests-on-pytest-behaviour-over-source-text/33-ledger/*.md (9 all-pending fragments)
    - .planning/phases/33-companion-tests-on-pytest-behaviour-over-source-text/33-MIGRATION-LEDGER.md
  modified: []

key-decisions:
  - "Reused 32-ledger-check.py's architecture unchanged and only extended it (per 33-RESEARCH.md's explicit recommendation), rather than rewriting from scratch, to keep the two phases' ledger tooling interchangeable for anyone comparing them later"
  - "check_one()'s collection-error handling now treats a harness's own new modules (companion/test_<stem>_NN.py) as part of 'this harness' for fail-vs-warn purposes, not just its original legacy path - needed because staged migration means a harness's checked files span more than one path at a time"
  - "Left the /nonexistent/definitely-not-here directory in place rather than force-deleting it: this session's own safety tooling blocks rm -rf on it, and 33-25 (the plan migrating this exact check) is the correct place to fix the root cause by using a tmp_path-scoped path instead"

patterns-established:
  - "Migration ledger fragments are always scaffolded all-pending before any harness rewrite begins, and a single `--allow-pending --all` command proves the whole 9-harness baseline is accounted for at every point in the 28-plan migration"

requirements-completed: [TST-15]

# Metrics
duration: 16min
completed: 2026-09-24
---

# Phase 33 Plan 01: Companion Migration Ledger Baseline Summary

**Captured real, browser-verified pre-migration baselines for all 9 companion test harnesses (1250 checks total) and built the staged-migration ledger tool and scaffold that every one of Phase 33's 28 migration plans will use to prove no check is silently dropped.**

## Performance

- **Duration:** ~16 min
- **Started:** 2026-09-24T08:38:57Z (previous plan's completion timestamp)
- **Completed:** 2026-09-24T08:54:30Z
- **Tasks:** 2/2 completed
- **Files modified:** 21 (1 tool file, 2 new directories with 9+9 files, 1 ledger scaffold)

## Accomplishments

- Extended `32-ledger-check.py` into `33-ledger-check.py`: staged-migration `validate_fragment()` rule (pending rows must equal the legacy harness's own remaining `EXPECTED_CHECK_COUNT`), an optional summary-line name prefix (`test_i18n.py` has none), an addendum mechanism for checks added mid-migration (`--add-check`), an all-pending scaffolder (`--scaffold`), and capture-time transcript validation that rejects a `SKIP` line or a PASS+FAIL/total mismatch.
- Captured real PASS/FAIL transcripts for all 9 companion harnesses under the current (pre-migration) interpreter, including the 3 browser harnesses run against a freshly installed, matching Chromium r1243 (not the stale r1194 cached at `/opt/pw-browsers`) — 1250 checks total (1247 PASS, 3 FAIL), matching 33-RESEARCH.md's independently measured figure exactly.
- Classified all 3 FAILs in `33-BASELINE/INDEX.md` as known root-sandbox artifacts (2 `os.chmod` WR-11 checks in `test_companion_app.py`, 1 `anomaly_active("/nonexistent/...")` mkdir-as-root in `test_status_pages.py`) and traced the +1 discrepancy between the audit's expected 1249 and the measured 1250 to commit `17d5bc7` (plan 32-11 Task 1, TST-03), which added exactly one new check after the audit baseline was taken.
- Scaffolded all 9 ledger fragments (`33-ledger/*.md`) with every row `pending`, and wrote the `33-MIGRATION-LEDGER.md` scaffold (purpose, fragment format, the TST-12 rubric, the staged-migration rule, a status table mapping each harness to its owning plans, the verification command, and a `<!-- fragments -->` marker for 33-33's `--assemble`).

## Task Commits

Each task was committed atomically (Task 1 followed the TDD RED/GREEN cycle since it carries `tdd="true"`):

1. **Task 1 (RED): add failing self-tests for staged companion ledger rules** - `a8cb602` (test)
2. **Task 1 (GREEN): implement 33-ledger-check.py for staged companion migration** - `3655cc9` (feat)
3. **Task 2: capture the 9 baselines, scaffold fragments, trace the +1** - `06280eb` (docs)

## Files Created/Modified

- `.planning/phases/33-companion-tests-on-pytest-behaviour-over-source-text/33-ledger-check.py` - capture/scaffold/add-check/check/assemble/self-test tool, extended from 32's for staged migration (42/42 self-test checks pass, ruff clean)
- `.planning/phases/33-companion-tests-on-pytest-behaviour-over-source-text/33-BASELINE/INDEX.md` - per-harness PASS/FAIL/total table, interpreter/euid/commit/Chromium provenance, and a Notes section classifying every FAIL and tracing the +1
- `.planning/phases/33-companion-tests-on-pytest-behaviour-over-source-text/33-BASELINE/companion__test_*.txt` (9 files) - real pre-migration transcripts, one per harness
- `.planning/phases/33-companion-tests-on-pytest-behaviour-over-source-text/33-ledger/companion__test_*.md` (9 files) - all-pending ledger fragments, one per harness
- `.planning/phases/33-companion-tests-on-pytest-behaviour-over-source-text/33-MIGRATION-LEDGER.md` - the ledger scaffold every later plan and 33-33's `--assemble` builds on

## Decisions Made

- Reused `32-ledger-check.py`'s architecture unchanged (copy, then extend) rather than rewriting, per 33-RESEARCH.md's explicit recommendation.
- `check_one()`'s collection-error handling was extended to treat a harness's own new modules (`companion/test_<stem>_NN.py`) as "this harness" for fail-vs-warn purposes, since staged migration means a harness's checked surface spans more than one file at a time — not explicitly specified by the plan's `<behavior>` list, but required for the tool to be usable by the staged-migration chains it exists to serve.
- Left the `/nonexistent/definitely-not-here` directory the root-run capture created in place (this session's safety tooling refuses `rm -rf` on it) rather than force-removing it; flagged in INDEX.md for 33-25 (which migrates this exact check) to fix at the root with a `tmp_path`-scoped path.

## Deviations from Plan

None - plan executed exactly as written. The one implementation choice not explicitly dictated by the plan's `<behavior>` list (own-module collection-error handling, described above) is a straightforward extension of 32's existing "collection error in another file is a warning" logic to staged migration's multi-file-per-harness reality, not a deviation from any stated requirement.

## Issues Encountered

- `/opt/pw-browsers` held a stale Chromium r1194 while `playwright==1.63.0` needs r1243 — resolved per 33-MIGRATION-RULES.md section 0's documented pre-flight: installed a fresh headless-shell r1243 to `/tmp/skypane-pw-browsers` via `PLAYWRIGHT_BROWSERS_PATH`, verified launchable, then used it for the capture. This scratch path is not committed and every later browser-plan (33-19..33-24) will need the same pre-flight until a permanent fix lands.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- All 28 migration plans (33-04..33-31) can now run `33-ledger-check.py --allow-pending <harness>` against a real baseline and a real scaffold from their very first commit.
- 33-33 has everything `--assemble` needs once every fragment reaches zero pending rows: the `<!-- fragments -->` marker, the status table, and the verification command already in place.
- No blockers. The stale-Chromium-cache issue is a known, already-solved precondition for every future browser-harness plan, not an open blocker.

---
*Phase: 33-companion-tests-on-pytest-behaviour-over-source-text*
*Completed: 2026-09-24*

## Self-Check: PASSED

All claimed files found on disk (`33-ledger-check.py`, `33-BASELINE/INDEX.md`,
`33-MIGRATION-LEDGER.md`, this summary) and all 4 commit hashes (`a8cb602`, `3655cc9`,
`06280eb`, `8098cff`) found in `git log --oneline --all`.
