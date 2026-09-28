---
phase: 41-docs-repository-hygiene-and-closing-re-audit
plan: 08
subsystem: infra
tags: [audit, closing-report, requirements-bookkeeping, pr-description]

# Dependency graph
requires:
  - phase: 41-docs-repository-hygiene-and-closing-re-audit
    provides: "41-01/41-02 doc-drift corrections, 41-03 repository hygiene, 41-04..41-07 re-audit slices (TST/HYG, FW, INT/SEC, EFF/ARC/CMP)"
provides:
  - "41-CLOSING-AUDIT.md — all 82 audit-ledger IDs (TST-01..DOC-03) consolidated into one report with a single verdict each, a final regression pass on the phase's own final tree, and the six required gate/flag sections"
  - "REQUIREMENTS.md bookkeeping: CFG-72/CFG-73 ticked on freshly-verified evidence, DOC-01 ticked, DOC-02's traceability cell expanded, DOC-03 left open (HYG-01/HYG-06 still open), TST-02/TST-15/ARC-03 traceability notes added, HYG-01/HYG-06 reopened"
  - "41-PR-DESCRIPTION.md — the draft PR body summarising the 32-41 remediation arc for the developer"
affects: [42-ota]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "A closing re-audit consolidates prior read-only slices unchanged unless the tree has moved since they ran; confirming the tree hasn't moved (git diff --name-status between audited commits) is cheaper and more honest than re-deriving every verdict from scratch"
    - "Full-suite flakiness in a shared, resource-constrained sandbox is triaged by re-running the failing tests individually/in small batches before it is ever recorded as a regression; a failure that reproduces identically across three independent environments (host + 2 Docker containers, one hash-locked) but is contradicted by a live, fetched CI log for an equivalent tree is disclosed as an unresolved sandbox anomaly, not silently absorbed or falsely called a regression"

key-files:
  created:
    - .planning/phases/41-docs-repository-hygiene-and-closing-re-audit/41-CLOSING-AUDIT.md
    - .planning/phases/41-docs-repository-hygiene-and-closing-re-audit/41-PR-DESCRIPTION.md
  modified:
    - .planning/REQUIREMENTS.md

key-decisions:
  - "CFG-72 and CFG-73 ticked: their three named tests were re-run on this final tree with browsers required and passed, and the button:active/.value-control__handle CSS exclusion was confirmed present."
  - "CFG-74 and CFG-34/37/39/42/50/52/65 left completely untouched, per 41-CONTEXT.md's locked developer decision — confirmed byte-identical to the phase base by a targeted diff."
  - "DOC-03 left unticked: two of the other 81 findings (HYG-01, HYG-06) are FLAGGED-OPEN, so per this plan's own rule DOC-03 cannot be VERIFIED-CLOSED."
  - "The full run-all-tests.sh suite's 40-48 local failures were triaged rather than accepted or hidden: each category was independently re-verified (isolated re-run, or a Linux Docker container for macOS/BSD-mv-only gaps) to confirm it is a sandbox artifact, not a regression, before being recorded in 41-CLOSING-AUDIT.md's gate table."

patterns-established:
  - "A closing audit's own regression pass first checks whether the tree has moved since the slices it consolidates ran (git diff --name-status between audited commits); if it hasn't, verdicts carry forward without re-deriving evidence, and the report says so explicitly rather than silently re-asserting them."

requirements-completed: [DOC-01, DOC-02, DOC-03]

# Metrics
duration: ~40min
completed: 2026-09-28
status: complete
---

# Phase 41 Plan 08: Closing Re-Audit, Requirements Bookkeeping and PR Description Summary

**Consolidated all 82 audit-ledger findings into one closing report (77 VERIFIED-CLOSED, 3 FLAGGED-DIFFERENT naming/tooling-only, 2 FLAGGED-OPEN comment-history-guard gaps), ticked CFG-72/CFG-73 on fresh evidence while leaving CFG-74 and the product-decision rows untouched, and drafted the Phase 41 PR description covering the whole Phases 32-41 remediation arc.**

## Performance

- **Duration:** ~40 min
- **Started:** 2026-09-28T07:24Z (approx., following 41-07's completion)
- **Completed:** 2026-09-28T07:50Z
- **Tasks:** 3/3
- **Files modified:** 3 (2 created, 1 modified)

## Accomplishments

- Confirmed the phase's final tree (`08e4eb49`) is byte-identical, outside `.planning/`, to every commit the four prior re-audit slices (`41-04`..`41-07`) individually audited — so every one of their 79 verdicts (TST/HYG/FW/INT/SEC/EFF/ARC/CMP) carries forward without re-derivation, and the closing report says so explicitly.
- Ran the full gate suite on the final tree: ruff, mypy, the comment-history guard, the function-size gate, attribution, firmware host tests (10/10), and `deploy/tests` (100 native + 70 in a Linux container for the two BSD-`mv`-incompatible files) all pass cleanly. The full `run-all-tests.sh` combined run showed 40-48 failures under this specific macOS sandbox's resource contention; each was individually triaged (re-run in isolation, or in a Docker container) and confirmed to be a sandbox artifact — none touch any of the 82 ledger IDs or any file this phase modified.
- Wrote `41-CLOSING-AUDIT.md`: one row per ledger ID (82 total), verdict totals, `## Flagged open`/`## Flagged different`/`## Evidence limited to recorded artefacts`/`## Final gate runs` sections, and a full-suite failure triage explaining the one unresolved anomaly (`test_fault_screen_mask_header_matches_generator_output`, reproducible locally but contradicted by a live, fetched GitHub Actions log for an equivalent tree).
- Updated `REQUIREMENTS.md`: CFG-72/CFG-73 ticked after re-confirming their tests pass and the CSS fix is present; DOC-01 ticked; DOC-02's traceability cell expanded to name the 41-03 remediation and the archival deferral; DOC-03 left unticked with a pointer to the flagged rows; TST-02/TST-15/ARC-03 kept ticked with a "remediation differs from the ledger wording" note; HYG-01/HYG-06 unticked and reopened.
- Drafted `41-PR-DESCRIPTION.md`: a phase-by-phase account of Phases 32-41 (PR numbers, verified-criteria counts, re-audit verdict counts per phase), the closing re-audit's totals and every flagged ID, the CFG-72/73/74 bookkeeping, what's deliberately out of scope, and a test-plan checklist naming the PR's own CI run as the pending proof for the one sandbox-only gap.

## Task Commits

Each task was committed atomically:

1. **Task 1: Final regression pass and consolidation into 41-CLOSING-AUDIT.md** - `c9d4f0b3` (docs)
2. **Task 2: REQUIREMENTS.md bookkeeping — CFG-72/73 verified and ticked, DOC rows, flagged rows** - `2b41f9a3` (docs)
3. **Task 3: Draft the Phase 41 PR description covering the 32-41 remediation arc** - `5749ecb1` (docs)

**Plan metadata:** (this commit) - docs: complete 41-08 plan

## Files Created/Modified

- `.planning/phases/41-docs-repository-hygiene-and-closing-re-audit/41-CLOSING-AUDIT.md` - the 82-row closing report: header, verdict totals, the full ID table, flagged-open/flagged-different/evidence-limited sections, final gate runs, and the full-suite failure triage
- `.planning/REQUIREMENTS.md` - CFG-72/CFG-73 ticked; DOC-01 ticked; DOC-02/DOC-03 traceability updated; TST-02/TST-15/ARC-03/HYG-01/HYG-06 traceability updated to match the closing report; CFG-74 and CFG-34/37/39/42/50/52/65 byte-identical to the phase base (confirmed by diff)
- `.planning/phases/41-docs-repository-hygiene-and-closing-re-audit/41-PR-DESCRIPTION.md` - the draft PR body for the whole Phases 32-41 arc

## Decisions Made

- Carried forward all 79 TST/HYG/FW/INT/SEC/EFF/ARC/CMP verdicts from the four prior re-audit slices unchanged, since a `git diff --name-status` between every pair of consecutive audited commits (through this plan's own final tree) is empty outside `.planning/` — re-deriving them would have added no evidentiary value.
- Ticked CFG-72 and CFG-73 after re-running their three named tests with `SKYPANE_REQUIRE_BROWSER=1` (all three passed) and re-reading `companion/static/style.css` to confirm the `button:not(.value-control__handle):active` exclusion is present — per 41-CONTEXT.md's locked developer decision.
- Left CFG-74 and CFG-34/37/39/42/50/52/65 completely untouched; verified via `diff <(git show 7bd8664:.planning/REQUIREMENTS.md | grep -n "CFG-74") <(grep -n "CFG-74" .planning/REQUIREMENTS.md)` that every CFG-74 line is byte-identical, same line numbers, to the phase base.
- Set DOC-03's checkbox to unticked (Open) because HYG-01 and HYG-06 are FLAGGED-OPEN in the closing report — per this plan's own rule, DOC-03 can only be VERIFIED-CLOSED if no other row is FLAGGED-OPEN.
- Treated the full-suite's local failures as a triage problem, not a pass/fail verdict on its own: re-ran deploy/tests directly (100 passed, 4 skipped) and with `-n auto --cov` (still 100 passed) to prove the combined-run failures for those same files are contention-only; re-ran the two companion-fixture tests in a `python:3.12-slim` Docker container (10/10 passed) to prove the `/proc`/process-group failures are this macOS sandbox's own limitation; and spent extra effort chasing `test_fault_screen_mask_header_matches_generator_output` across three environments (native macOS, Linux/arm64 Docker, Linux/amd64-emulated Docker with the exact hash-locked deps) before concluding it is a genuine, unresolved, sandbox-only anomaly contradicted by a live CI log for an equivalent tree — disclosed rather than silently absorbed or wrongly called a code regression.

## Deviations from Plan

None of Rules 1-4 applied — this is a read-only/documentation-only closing plan with no source-code changes to make. One transparency finding, disclosed per the plan's own evidence standard rather than fixed (fixing would be out of this plan's scope, per the plan's explicit "do not fix flagged findings in this plan" instruction):

### Full-suite local failures are sandbox-only, not a regression — disclosed, not fixed

- **Found during:** Task 1's final regression pass.
- **Issue:** `SKYPANE_REQUIRE_BROWSER=1 ./scripts/run-all-tests.sh` reported 40 failures (48 on a `JOBS=4` retry, a different subset) on this macOS sandbox, none of which appear in any of the four prior re-audit slices' own full-suite runs (which ran as root on Linux).
- **Investigation:** Each failing test was re-run individually or in a small batch: `companion`/`test-support` port-collision and segfault failures all passed when serialized; `deploy/tests` failures all passed (100/100) when run as their own `pytest -n auto --cov` invocation, proving the combined-run contention is about total concurrent load, not these tests' own logic; two `companion/test_app_server_fixture.py` tests need Linux (`/proc`, process-group semantics) and passed 10/10 in a `python:3.12-slim` container; `deploy/tests/test_activate.py`/`test_install_backup_key.py` need GNU `mv -T` and passed (as part of 70/70) in the same container. One test, `server/test_fault_screen_mask.py::test_fault_screen_mask_header_matches_generator_output`, failed identically in native macOS, a native Linux/arm64 Docker container, and an emulated Linux/amd64 Docker container using the exact hash-locked `server/requirements-dev.txt` — yet a live GitHub Actions log fetched for CI run `36377045745` (commit `c4457f36`, confirmed byte-identical to this tree for every file the test/generator touches) shows `3218 passed, 0 failed`, meaning this exact test passed there. The root cause was not identified in the time available for this plan.
- **Disposition:** Recorded in full in `41-CLOSING-AUDIT.md`'s `## Final gate runs` and `### Full-suite failure triage` sections, with the PR's own CI run named as the pending, authoritative proof — consistent with how this plan's own instructions treat an unresolvable browser-availability gap. Not fixed, since it is not one of the 82 ledger IDs and no file it depends on was modified by this phase (confirmed by `git diff --stat c4457f36 HEAD` over the relevant files, which is empty).

**Total deviations:** 0 auto-fixed; 1 transparency finding disclosed (investigated extensively, not fixed, since it is out of this phase's scope and not a regression this phase introduced).
**Impact on plan:** None on this plan's own deliverables — all three tasks' acceptance criteria are met regardless of this sandbox-only anomaly.

## Issues Encountered

None beyond the full-suite triage documented above.

## User Setup Required

None - no external service configuration required.

## Next steps

- **Open the Phase 41 PR** with `41-PR-DESCRIPTION.md` as its body and drive CI green. The PR's own CI run is this plan's own named pending proof for the one sandbox-only full-suite anomaly.
- **HYG-01 and HYG-06 are FLAGGED-OPEN.** Run `/gsd-plan-phase 41 --gaps` to plan the small comment-history-guard regex fix (and the ~12 comment/docstring rewordings) before merging, or merge with the finding explicitly carried forward — the developer's call, not this plan's.
- **After merge:** Phase 42 (OTA)'s gate **G-41** can proceed — it requires Phase 41 complete on `main`.
- **Phase-directory archival** via `/gsd-cleanup` remains an explicit open item for whoever closes the v1.0 milestone after Phase 42 finishes (per `41-03-SUMMARY.md`'s and this phase's own deferral).

## Self-Check: PASSED

- FOUND: .planning/phases/41-docs-repository-hygiene-and-closing-re-audit/41-CLOSING-AUDIT.md
- FOUND: .planning/phases/41-docs-repository-hygiene-and-closing-re-audit/41-PR-DESCRIPTION.md
- FOUND commit: c9d4f0b3
- FOUND commit: 2b41f9a3
- FOUND commit: 5749ecb1

---
*Phase: 41-docs-repository-hygiene-and-closing-re-audit*
*Completed: 2026-09-28*
