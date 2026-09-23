---
phase: 32-test-foundation-pytest-and-ci-you-can-trust
plan: 02
subsystem: testing
tags: [migration-ledger, baseline-capture, tdd, pytest-collect-only]

# Dependency graph
requires: []
provides:
  - 32-ledger-check.py: stdlib capture/check/assemble/self-test tool every harness-migration
    plan (32-03..32-10) and the final assembly plan (32-13) use to prove its ledger fragment is
    complete
  - 32-BASELINE/*.txt (15 transcripts) + 32-BASELINE/INDEX.md: the pre-migration ground-truth
    PASS/FAIL transcript for every one of the 15 server-side harnesses, captured before any
    rewrite
  - 32-MIGRATION-LEDGER.md: scaffold (format, rules, verification command, per-harness status
    table) that 32-13 regenerates wholesale via --assemble once every fragment lands
affects: [32-03, 32-04, 32-05, 32-06, 32-07, 32-08, 32-09, 32-10, 32-13]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Ledger fragments are disjoint per-harness files (32-ledger/<key>.md), so parallel
       migration plans in the same wave never conflict writing to one shared ledger file."
    - "check() mode parses `pytest --collect-only -q` output even on a non-zero exit code,
       distinguishing a collection error in the harness under test (a real failure) from one in
       a sibling file a parallel plan may be mid-editing (a warning only)."
    - "validate_fragment() is a pure function (rows/lines/node-ids/source-text in, failures/
       counts out) with zero filesystem or subprocess access, so --self-test can exercise every
       CONTEXT.md-mandated failure mode (row-count mismatch, label multiset mismatch, missing
       ported node id, empty deleted reason, ungated pending row, leftover
       EXPECTED_CHECK_COUNT/def check() marker) against in-memory strings alone."

key-files:
  created:
    - .planning/phases/32-test-foundation-pytest-and-ci-you-can-trust/32-ledger-check.py
    - .planning/phases/32-test-foundation-pytest-and-ci-you-can-trust/32-BASELINE/INDEX.md
    - .planning/phases/32-test-foundation-pytest-and-ci-you-can-trust/32-BASELINE/*.txt (15 transcripts)
    - .planning/phases/32-test-foundation-pytest-and-ci-you-can-trust/32-MIGRATION-LEDGER.md
  modified: []

key-decisions:
  - "label_matches() operates on the raw baseline transcript line (not a pre-split label/reason
     pair) so the FAIL '<label> - <reason>' vs PASS '<label>' asymmetry from the harnesses' own
     print format (server/test_dither.py:39-48) is handled in one place, with an explicit
     self-test proving a text-prefix label ('boom' against 'FAIL boomer - x') does NOT
     false-positive-match."
  - "check() mode fails the harness under test on its own collection error, but only WARNS on a
     collection error in another file - CONTEXT.md's parallel-plan constraint (a sibling
     migration plan may be mid-edit on another harness in the same wave) means a strict
     'pytest --collect-only must exit 0' rule would make every parallel migration plan's own
     ledger check spuriously fail on a neighbour's in-progress work."
  - "The EXPECTED_CHECK_COUNT/def check( leftover-marker check only fires once a fragment
     declares at least one ported or deleted row - a fragment that is entirely 'pending' (the
     one staged-migration case CONTEXT.md allows, though none is currently planned) must not be
     penalized for the harness legitimately still carrying the pre-migration idiom."

requirements-completed: [TST-02]

# Metrics
duration: 13min
completed: 2026-09-23
---

# Phase 32 Plan 02: Migration ledger baseline and tool Summary

**A stdlib capture/check/assemble tool (27 self-tests, TDD RED->GREEN) plus the actual pre-migration baseline for all 15 server-side harnesses (769 checks, 767 PASS / 2 FAIL) and a `32-MIGRATION-LEDGER.md` scaffold, captured and written before any harness is rewritten.**

## Performance

- **Duration:** 13 min (14:00:42 first commit -> 14:13:58 last commit)
- **Tasks:** 2 (Task 1 executed as an explicit RED -> GREEN TDD cycle)
- **Files created:** 18 (`32-ledger-check.py`, `32-BASELINE/INDEX.md`, 15 `32-BASELINE/*.txt` transcripts, `32-MIGRATION-LEDGER.md`)

## Accomplishments
- `32-ledger-check.py` (stdlib only): `--capture` runs a harness under the current interpreter
  and writes its transcript + refreshes `INDEX.md`; the default "check" mode loads a harness's
  baseline + its `32-ledger/<key>.md` fragment and proves every baseline check is accounted for
  (row count, label multiset via `label_matches()`, `ported` node ids checked against a live
  `pytest --collect-only -q`, non-empty `deleted` reasons, `pending` gated by
  `--allow-pending`, and a leftover-marker check once a fragment declares ported/deleted rows);
  `--assemble` concatenates all 15 passing fragments into the final ledger.
- `--self-test` (27 in-memory checks, no filesystem/subprocess) proves the described matching
  and failure semantics directly: confirmed RED (11/11 failing against `NotImplementedError`
  stubs) before the real logic existed, then GREEN (27/27) after.
- Ran `--capture` for real against all 15 server-side harnesses from the repo root: 769 checks
  total, every transcript's own PASS+FAIL count matches its own printed total (no early-abort
  truncation anywhere).
- `32-MIGRATION-LEDGER.md` scaffolded with the fragment format, the matching/verification rules,
  the per-harness verification command, and a status table (baseline count + owning migration
  plan 32-03..32-10 + status "pending") for all 15 harnesses, written before any of them is
  touched.

## Task Commits

Each task was committed atomically:

1. **Task 1: Ledger tool (capture, check, assemble)** - `e4bb381` (test, RED) + `3a6665c` (feat, GREEN)
2. **Task 2: Capture the 15 baselines and scaffold the ledger** - `9a6a10c` (feat)

**Plan metadata:** (this commit, docs: complete plan)

_Note: Task 1 is `tdd="true"`. The RED commit stubs `parse_baseline`, `label_matches`,
`escape_label`/`unescape_label`, `parse_fragment_rows` and `validate_fragment` to
`raise NotImplementedError`, with `--self-test` confirmed exiting 1 (11/11 in-memory checks
failing) before any real logic existed; the GREEN commit restores the full implementation,
`--self-test` then passing 27/27. Between RED and GREEN, `ruff check` caught one unused `time`
import left over from an earlier draft (Rule 1 auto-fix, folded into the GREEN commit rather
than given its own commit since it was caught before GREEN was ever committed)._

## Files Created/Modified
- `32-ledger-check.py` (new) - capture/check/assemble/self-test tool, ~500 lines, stdlib only
- `32-BASELINE/INDEX.md` (new) - capture metadata (Python 3.11.15, euid 0, capture commit
  `3a6665c9`, UTC timestamp) + per-harness PASS/FAIL/total/exit-code/summary-line table + grand
  total (769) + a `## Notes` section on the 2 root-sandbox FAILs
- `32-BASELINE/*.txt` (new, 15 files) - one raw PASS/FAIL transcript per harness, named
  `<harness-path-with-__-for-/>.txt` (e.g. `server__test_dither.txt`)
- `32-MIGRATION-LEDGER.md` (new) - scaffold: format/rules, verification command, 15-row status
  table (all `pending`, migrating plan assigned per 32-RESEARCH.md's proposed batching)

## Decisions Made
- `label_matches()` takes the raw transcript line rather than a pre-parsed `(status, text)`
  tuple, so the FAIL-vs-PASS asymmetry in what a "label" means (FAIL lines carry a
  `- <reason>` tail the ledger doesn't repeat) lives in exactly one function, with a dedicated
  self-test case (`"FAIL boomer - x"` must NOT match label `"boom"`) guarding against an
  accidental substring match.
- `check()` mode's own collection-error handling distinguishes "the harness under test itself
  failed to collect" (a real failure) from "some other file in the tree failed to collect" (a
  warning only) - required because CONTEXT.md's parallel-execution model means a sibling
  migration plan (e.g. 32-03 running in the same wave as 32-04) may leave another harness in a
  transiently broken mid-edit state that a strict single collect-only-must-be-clean rule would
  wrongly blame on the harness actually being checked.
- The `EXPECTED_CHECK_COUNT`/`def check(` leftover-marker check is gated on the fragment
  declaring at least one `ported` or `deleted` row, not unconditional - a fragment that is
  entirely `pending` (CONTEXT.md's allowed-but-unplanned staged-migration case) legitimately
  still points at an unmigrated harness and must not be penalized for it.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Removed an unused `import time`**
- **Found during:** Task 1, between the RED and GREEN implementation passes
- **Issue:** An early draft imported `time` for a per-harness timing feature that was cut from
  the final design (capture already reports exit code and PASS/FAIL/total; wall-clock timing
  wasn't part of the plan's `<behavior>`/`<action>` spec); `ruff check` flagged it as F401
  (unused import) after the GREEN implementation replaced the stubs.
- **Fix:** Removed the import.
- **Files modified:** `32-ledger-check.py`
- **Commit:** Folded into `3a6665c` (the GREEN commit) - caught during verification before that
  commit was made, so no separate fix commit was needed.

No other deviations - both tasks' automated verification and acceptance criteria passed as
written.

## Issues Encountered

`server/test_manual_resolutions.py`'s baseline transcript has 2 FAIL lines out of 23 (21/23).
Both are the WR-11 `os.chmod(0o500)` read-only-directory checks at source lines 439 and 461:
this sandbox runs as `euid 0` (confirmed in `INDEX.md`), and root ignores read-only directory
permission bits by design, so the write each check expects to fail instead succeeds. This is
the exact "4×WR-11, 1×`anomaly_active()`" root-sandbox condition `32-01-SUMMARY.md` and
`STATE.md`'s own session history already document repeatedly - 2 of those 4 WR-11 checks live
in this file, the other 2 and the `anomaly_active()` check are in `companion/test_*.py`
(out of this phase's TST-02 scope). Per this plan's own scope (capture the baseline, never
modify a harness) and the deviation-rule scope boundary (only auto-fix issues the current
task's changes directly cause), this was recorded faithfully in `INDEX.md`'s `## Notes`
section with source line references rather than hidden, fixed, or worked around. The migration
plan that ports this harness (32-04) is where `32-RESEARCH.md`'s own `requires_non_root` /
`pytest.mark.skipif(os.geteuid() == 0, ...)` pattern is expected to be applied to these two
checks.

## Next Phase Readiness
- `32-ledger-check.py`, the 15 baseline transcripts, and the `32-MIGRATION-LEDGER.md` scaffold
  are all in place for `32-03` onward: each harness-migration plan writes its own
  `32-ledger/<key>.md` fragment and verifies it with
  `server/.venv/bin/python3 .../32-ledger-check.py <harness>` before considering that harness's
  migration done.
- No harness source was touched by this plan (`git diff --quiet server/ stub-server/` verified
  clean both before and after capture) - every one of the 15 still carries
  `EXPECTED_CHECK_COUNT`, ready for its own migration plan to rewrite it.
- No blockers. The one root-sandbox WR-11 condition noted above is environment-specific,
  already known from prior sessions, and does not affect this plan's own deliverables (the
  baseline capture faithfully records it rather than needing to work around it) or any later
  plan's ability to build on this one.

---
*Phase: 32-test-foundation-pytest-and-ci-you-can-trust*
*Completed: 2026-09-23*

## Self-Check: PASSED

All 4 created files confirmed present on disk (`32-ledger-check.py`, `32-BASELINE/INDEX.md`,
`32-MIGRATION-LEDGER.md`, this summary); all 3 task commit hashes (`e4bb381`, `3a6665c`,
`9a6a10c`) confirmed present in `git log --oneline --all`.
