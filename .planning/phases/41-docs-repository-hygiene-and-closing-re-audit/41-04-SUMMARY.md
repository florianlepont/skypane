---
phase: 41-docs-repository-hygiene-and-closing-re-audit
plan: 04
subsystem: testing
tags: [pytest, ci, coverage, comment-history-guard, migration-ledger, github-actions]

requires:
  - phase: 32-test-foundation-pytest-and-ci-you-can-trust
    provides: pytest/xdist/cov infra, hash-locked deps, CI on production Python, migration ledger
  - phase: 33-companion-tests-on-pytest-behaviour-over-source-text
    provides: shared app-server fixture, pytest-playwright policy, behaviour-over-source guard, closing parity ledger
  - phase: 35-comment-purge-in-english-and-dead-code
    provides: comment-history guard (scripts/check_comment_history.py), English-only rule, dead-code removal
provides:
  - Independent re-verification of TST-01..TST-15 and HYG-01..HYG-06 against current code (not the phases' own claims)
  - Live GitHub Actions evidence closing 2 of Phase 32's 3 human_needed CI-only items (3.14 resolution, hash-install, Playwright cache hit)
  - A guard-evasion hunt proving the comment-history guard's regex has a real, currently-exploited gap (letter-suffixed decision IDs, dotted UI-SPEC section numbers, bare Phase-Plan IDs)
  - Root-cause diagnosis of why both migration-ledger checkers (32-ledger-check.py, 33-ledger-check.py) now fail: Phase 39's ARC refactor renamed/strengthened tests after Phase 32/33 closed, not a migration regression
affects: [41-05, 41-06, 41-07, 41-08]

tech-stack:
  added: []
  patterns:
    - "Ledger-check scripts must be invoked with server/.venv/bin/python3, never the bare system python3 (which lacks pytest and silently breaks their internal pytest --collect-only subprocess, producing misleading 'not found' failures)"
    - "Guard-evasion hunting: reuse a checker's own per-language comment/docstring extractors rather than a blind grep, so hits are pre-filtered to comment/docstring context and string literals are never mistaken for comments"

key-files:
  created:
    - .planning/phases/41-docs-repository-hygiene-and-closing-re-audit/41-REAUDIT-TST-HYG.md
  modified: []

key-decisions:
  - "TST-02/TST-15 marked FLAGGED-DIFFERENT, not FLAGGED-OPEN: the migration ledger closed correctly at Phase 32/33's own close (proven by the phases' own VERIFICATION.md); today's ledger-checker failures are 100% traced to Phase 39 (commit 8ee39d7) renaming/strengthening 6-10 tests afterward, with no lost coverage or test count — a stale verification script, not a regression"
  - "HYG-01/HYG-06 marked FLAGGED-OPEN, not VERIFIED-CLOSED: the guard-evasion hunt found 21 genuine history references (10 letter-suffixed D-IDs, 11 dotted UI-SPEC section numbers) plus 2 bare Phase-Plan IDs across 12 files — systematic, not 'a handful', per the plan's own rubric"
  - "TST-06's dynamic concurrency/cancellation edge cases were not re-triggered live (would require an engineered double-push against production); kept as the one still-unproven CI-only behaviour, matching Phase 32's own original human-verification scope"

requirements-completed: []  # DOC-03 spans 4 re-audit slices (41-04..41-07) plus the 41-08 closing merge; not complete until 41-08

duration: 20min
completed: 2026-09-28
---

# Phase 41 Plan 04: Re-audit TST-01..TST-15 and HYG-01..HYG-06 Summary

**Independently re-verified all 21 Phase 32/33/35 audit findings against current code and live CI: 17 VERIFIED-CLOSED, 2 FLAGGED-DIFFERENT (stale ledger-checker scripts, not lost coverage), 2 FLAGGED-OPEN (a real comment-history-guard regex gap with 21 live exploits found and a minimal 3-edit fix proposed).**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-09-28T05:43:23Z
- **Completed:** 2026-09-28T06:02:49Z
- **Tasks:** 2 completed
- **Files modified:** 1 (`41-REAUDIT-TST-HYG.md`, created)

## Accomplishments

- Ran every gate the plan named against current code: full pytest suite (root, browser installed live), ruff, mypy, comment-history guard, function-size gate, firmware host tests, and both Phase 32/33 migration-ledger checkers — recorded exit codes and key figures for all of them in the report's "Gate runs" table.
- Fetched a live GitHub Actions job log (run `36377045745`, commit `c4457f36`) over the public API to directly close 2 of Phase 32's 3 `human_needed` CI-only items: Python 3.14.7 resolves on Actions, and the hash-enforced `pip install --require-hashes` succeeds there; also confirmed a real Playwright cache hit (`Cache hit for: playwright-Linux-1.63.0-headless-shell`).
- Diagnosed why both migration-ledger checker scripts (`32-ledger-check.py --all`, `33-ledger-check.py --all`) now exit 1: traced every "not found" row to a specific Phase 39 (`8ee39d7`) rename or strengthening of the underlying test, confirming no coverage or test-count was actually lost.
- Built a guard-evasion hunt that reuses `scripts/check_comment_history.py`'s own per-language comment/docstring extractors (so hits are pre-scoped to real comments, not string literals) against the broader ID-shape patterns the plan named, then manually triaged all 167 raw hits down to 21 genuine, systematic guard-evading history references (10 letter-suffixed decision IDs, 11 dotted UI-SPEC section numbers) plus 2 bare Phase-Plan IDs, distinguishing them from 146 false positives (quiet-hours windows, real Orly runway designators, dates, arithmetic).
- Wrote all 21 verdicts into `41-REAUDIT-TST-HYG.md` with the required report format (Header, Gate runs, one table per source phase, closing `## Flags` section), each verdict backed by a `file:line`, a command/test run in this pass, or a fetched CI run URL.

## Task Commits

Each task was committed atomically:

1. **Task 1: Run the gates and re-audit TST-01..TST-15 (Phases 32 and 33)** - `97a87bd` (docs)
2. **Task 2: Re-audit HYG-01..HYG-06 (Phase 35), including guard-evading history references** - `bb81edb` (docs)

**Plan metadata:** (this commit) `docs(41-04): complete closing re-audit slice 1 plan`

## Files Created/Modified

- `.planning/phases/41-docs-repository-hygiene-and-closing-re-audit/41-REAUDIT-TST-HYG.md` - Per-finding re-audit report: Header (audited commit, uid, tool availability), Gate runs table (10 rows), Phase 32 TST table (9 rows), Phase 33 TST table (6 rows), Phase 35 HYG table (6 rows), closing Flags section

## Decisions Made

- TST-02/TST-15 → FLAGGED-DIFFERENT (see key-decisions above): the substance of the migration (no hand-rolled harnesses, full parity, coverage above the pre-migration floor) is intact; only the standalone ledger-check tooling's hardcoded node-id expectations have gone stale relative to Phase 39's later, unrelated refactor. Recommended 41-08 decide whether to update or retire the two ledger scripts before the milestone archives.
- HYG-01/HYG-06 → FLAGGED-OPEN (see key-decisions above), with a concrete, minimal fix proposed in the report's Notes column (three regex edits to `scripts/check_comment_history.py`'s `d-id` and `bare-plan-id` patterns, plus one new `uispec-section` pattern) — not implemented here, since this plan is read-only-on-report per its own scope (DOC-03 fixes, if any, belong to a later plan/phase per 41-CONTEXT.md).
- TST-06's dynamic concurrency behaviour stays unproven-by-direct-reproduction in this pass (deliberately, to avoid an unsafe live double-push against production); the static YAML shape was re-verified instead and 10 recent green `main` runs (including their `deploy` jobs) were cited as consistent-with-but-not-proof-of the specific edge cases.

## Deviations from Plan

None - plan executed exactly as written. No code was modified (this plan is read-only on the codebase per its own objective); the only artifact produced is the report file the plan specifies.

## Issues Encountered

- Both migration-ledger checker scripts (`32-ledger-check.py`, `33-ledger-check.py`) silently produce misleading "not found in `pytest --collect-only`" failures for every single row when invoked with the bare system `python3` (which lacks `pytest` installed) — the scripts use `sys.executable` internally for their `pytest --collect-only` subprocess, so the wrong interpreter causes collection to fail with no diagnostic linking it to the interpreter choice. Resolved by re-running with `server/.venv/bin/python3` explicitly; documented this footgun directly in the Gate runs table so 41-05..41-08 don't repeat it.
- GitHub CLI (`gh`) is not installed in this sandbox; used unauthenticated `curl` against the public REST API instead (per 41-CONTEXT.md's own suggested fallback), including following a redirect to Azure blob storage to read a job's raw log text for cache-hit/Python-version evidence.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `41-REAUDIT-TST-HYG.md` is ready for 41-08 to merge alongside the other three re-audit slices (41-05, 41-06, 41-07).
- Two follow-up items surfaced for 41-08's disposition: (1) whether to update or retire the now-stale `32-ledger-check.py`/`33-ledger-check.py` node-id expectations before the milestone archives; (2) the small `scripts/check_comment_history.py` regex fix (letter-suffixed D-IDs, dotted UI-SPEC section numbers, bare Phase-Plan IDs) and the corresponding ~12-file comment reword this plan intentionally did not apply (read-only re-audit scope).
- No blockers for continuing to 41-05/41-06/41-07 (the other three re-audit slices) or to 41-08's merge.

---
*Phase: 41-docs-repository-hygiene-and-closing-re-audit*
*Completed: 2026-09-28*

## Self-Check: PASSED

- FOUND: `.planning/phases/41-docs-repository-hygiene-and-closing-re-audit/41-REAUDIT-TST-HYG.md`
- FOUND: `.planning/phases/41-docs-repository-hygiene-and-closing-re-audit/41-04-SUMMARY.md`
- FOUND commit `97a87bd` (Task 1)
- FOUND commit `bb81edb` (Task 2)
