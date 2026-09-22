---
phase: 31-ci-test-suite-parallelize-companion-test-browser-ux-py-to-cu
plan: 05
subsystem: testing
tags: [ci, worker-pool, timing, decision-checkpoint, pool-contention]

requires:
  - phase: 31-04
    provides: "Both extractions wired into scripts/run_all_tests.py's worker pool (24 harnesses), the measured post-split JOBS=4 timing baseline, and the D-05 gate arithmetic showing MISSED on every sample"
provides:
  - "The developer's measured decision on the optional third (Flights) extraction: skip-flights, recorded verbatim with reasoning"
  - "Two additional fresh JOBS=4 samples (212.7s, 210.8s) on the unchanged post-plan-04 code, combined with plan 04's three into a five-sample closing D-05 verdict"
  - "The phase's final written D-05 verdict (MISSED against the ~30-40% bar on every sample) and an explicit recommendation against opening the follow-up settings-mega-cluster decomposition phase"
affects: []

tech-stack:
  added: []
  patterns:
    - "Checkpoint decisions are recorded verbatim in the SUMMARY with the developer's own reasoning, not paraphrased, so a later reader can tell the call was measured rather than assumed"
    - "A skip-branch plan still re-measures and tightens the underlying evidence (two more samples) rather than treating 'skip' as 'do nothing at all' — the closing verdict is stronger for it"

key-files:
  created: []
  modified:
    - .planning/phases/31-ci-test-suite-parallelize-companion-test-browser-ux-py-to-cu/31-TIMINGS.md

key-decisions:
  - "Developer selected skip-flights at the Task 1 checkpoint: D-05's gate missed on every one of plan 04's three local-proxy samples, D-06 explicitly sanctions stopping at diminishing returns, and this matched both plan 04's own recommendation and the executing agent's independent read of the same evidence. The developer explicitly did not request a real CI number first, treating the local-proxy evidence as decisive."
  - "Consequently Task 2 was a no-op by design: no companion/test_browser_ux_flights.py was created, companion/test_browser_ux.py stayed at 76 checks, and scripts/run_all_tests.py/EXPECTED_SLOWEST were not touched."
  - "Combined all five JOBS=4 samples measured across plans 04 and 05 (not just this plan's two) into the closing D-05 verdict, since the two new samples alone would understate the variance already visible in plan 04's three — the five-sample spread (9.1% to 29.6% job-level estimate) is itself the strongest evidence that pool contention, not a fixed cost, dominates the measurement."
  - "Recommended against opening the follow-up settings-mega-cluster decomposition phase at this time, reasoning tied to the measured pool-contention mechanism (adding a fourth-plus concurrent Chromium harness to an already-contended four-slot pool is unlikely to help) and the mega-cluster's materially harder decomposition profile (~70% of check bodies, 34 interleaved Display checks + 7 Device checks, cross-page check bodies, shared local closures) rather than to appetite."

requirements-completed: [D-04, D-05, D-06, D-07]

coverage:
  - id: D1
    description: "Task 1 checkpoint: the developer was shown the pre-split/post-split totals, the suite-level and CI-job-level percentages, the three browser harnesses' individual wall times, the critical-path finding, and the Flights non-contiguity scope correction (independently re-verified against the live file), then selected skip-flights with reasoning recorded verbatim"
    requirement: "D-04"
    verification:
      - kind: manual_procedural
        ref: "Checkpoint dispatch return message (gate numbers, options, recommendation) plus the coordinator's relayed verbatim developer decision and reasoning, both reproduced in this SUMMARY's Decisions Made section"
        status: pass
    human_judgment: true
    rationale: "This is a developer decision by design (D-04's own text), not something automation can classify — the coverage entry records that the decision process itself (evidence shown before the answer was taken) was followed correctly, which is a judgment call about process integrity."
  - id: D2
    description: "Task 2 no-op honored: no source file created or modified under the skip-flights branch"
    requirement: "D-06"
    verification:
      - kind: other
        ref: "git status --porcelain companion/ scripts/ (empty, confirmed before and after Task 2)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Task 3: full suite re-measured at JOBS=4 (two fresh native samples, 212.7s and 210.8s), combined with plan 04's three samples into a five-sample closing D-05 verdict written into 31-TIMINGS.md, with a for/against recommendation on the follow-up decomposition phase and the required CI-caveat/gh-run-view note"
    requirement: "D-05"
    verification:
      - kind: integration
        ref: "PYTHON=server/.venv/bin/python3 JOBS=4 ./scripts/run-all-tests.sh, two runs (/tmp/31-05-suite-run1.txt, /tmp/31-05-suite-run2.txt) -> 212.7s and 210.8s; companion/test_browser_ux.py standalone -> 73/76 checks pass (3 known pre-existing env-only failures, same signatures documented since 31-01)"
        status: pass
    human_judgment: false
  - id: D4
    description: "D-07 held for the whole phase: .github/workflows/ci.yml received no change in this plan or any prior plan of phase 31"
    requirement: "D-07"
    verification:
      - kind: other
        ref: "git status --porcelain .github/ (empty)"
        status: pass
    human_judgment: false

duration: ~45min
completed: 2026-09-22
status: complete
---

# Phase 31 Plan 05: D-05 Checkpoint Decision (skip-flights) and Closing Verdict Summary

**Developer selected skip-flights on plan 04's measured local-proxy evidence; two additional JOBS=4 samples (212.7s, 210.8s) were folded into a five-sample closing verdict showing D-05's ~30-40% bar MISSED on every sample (9.1%-29.6%, mean 22.4%, median 28.7%), with an explicit recommendation against opening the follow-up settings-mega-cluster decomposition phase.**

## Performance

- **Duration:** ~45min (dominated by two full-suite JOBS=4 re-measurement runs, ~213s and ~211s wall time each, plus one standalone confirmation run of companion/test_browser_ux.py)
- **Completed:** 2026-09-22
- **Tasks:** 3/3 completed (Task 1: checkpoint decision; Task 2: no-op per skip-flights; Task 3: re-measurement + closing verdict)
- **Files modified:** 1 (`31-TIMINGS.md`)

## Accomplishments

- Presented the Task 1 checkpoint with the concrete numbers required by the plan: pre-split total (240.9s), post-split totals (three plan-04 samples: 209.5s/279.4s/258.2s), the suite-level delta range (+13.0% to -16.0%), the D-01-methodology CI-job-level estimate range (9.1%-29.6%), the three browser harnesses' individual wall times, and plan 04's critical-path finding that the reduced parent still bounds total wall time — with the pool-contention mechanism (three concurrent Chromium harnesses slowing every non-browser harness 22-77%) called out as the reason a fourth extraction was unlikely to help.
- Independently re-verified the Flights non-contiguity scope correction directly against the live file (`companion/test_browser_ux.py` lines 1063/1170/1231/1313) before presenting the decision, confirming `_the_quiet_schedule_link_meets_the_hit_target_floor_at_360px` genuinely sits between the first and second early Flights checks.
- Received the developer's decision via the coordinator: **skip-flights**, with reasoning that D-05's gate missed on every plan-04 sample, D-06 sanctions stopping at diminishing returns, and this matched both plan 04's own recommendation and this executor's independent read — the developer explicitly declined to request a real CI number first.
- Honored Task 2 as a true no-op: confirmed via `git status --porcelain companion/ scripts/` (empty both before and after) that no file was touched — no `companion/test_browser_ux_flights.py` was created and `companion/test_browser_ux.py` stayed at 76 checks.
- Re-measured the full 24-harness suite at `JOBS=4` twice on the unchanged post-plan-04 code (212.7s, 210.8s) — both runs failing only the same three pre-existing, environment-only checks documented since `31-01-SUMMARY.md` (two `Control+A`-selection checks, one DOM-detach compositor race), confirming no regression.
- Combined all five samples now measured across plans 04 and 05 into the closing verdict: job-level estimate range 9.1%-29.6% (mean 22.4%, median 28.7%) — MISSED against D-05's ~30-40% bar on every sample, though the top three samples come within 1-2 points of the 30% floor, itself evidence of high pool-contention-driven variance rather than a stable, precisely-measurable figure.
- Wrote the phase's final recommendation against opening the follow-up settings-mega-cluster decomposition phase, reasoning from the measured pool-contention mechanism and the mega-cluster's materially harder decomposition profile (~70% of check bodies, 34 interleaved Display checks, 7 Device checks, cross-page check bodies, shared local closures) — and repeated the required CI caveat that this branch has not been pushed, so no real `gh run view` number exists yet, and the verdict should be revisited on the first real CI run.

## Task Commits

1. **Task 1: Decide whether the optional Flights extraction is worth taking** - no commit (checkpoint only; no source file was modified, confirmed by `git status --porcelain companion/ scripts/` before and after)
2. **Task 2: create companion/test_browser_ux_flights.py and reduce the parent** - no commit (no-op under the skip-flights branch, as the plan specifies)
3. **Task 3: Close the phase — re-run the suite, record the D-05 verdict** - `3e5f061` (docs)

**Plan metadata:** (this commit)

## Files Created/Modified

- `.planning/phases/31-ci-test-suite-parallelize-companion-test-browser-ux-py-to-cu/31-TIMINGS.md` - Appended the "Phase 31 Closing Verdict" section: the Task 1 checkpoint outcome and reasoning, two fresh JOBS=4 samples with a full per-harness table, delta arithmetic against both the pre-split baseline and plan 04's post-split measurement, the combined five-sample D-05 gate verdict (MISSED), the recommendation against the follow-up decomposition phase, the CI/`gh run view` caveat, and confirmation that D-07 held for the whole phase.

## Decisions Made

- **skip-flights selected at the Task 1 checkpoint.** Reasoning given by the developer (relayed via the coordinator): "D-05's gate missed on every local sample, D-06 explicitly sanctions stopping at diminishing returns, and this matches both plan 04's and your own independent recommendation." The developer did not ask for a real CI number first — the local-proxy evidence was treated as decisive.
- **Combined this plan's two new samples with plan 04's three into one five-sample closing verdict**, rather than reporting only the two new numbers, because the five-sample spread (9.1% to 29.6% job-level estimate, on identical code) is itself the clearest evidence in the phase that a local proxy on this host cannot pin the true D-05 figure down precisely — reporting fewer samples would have understated that uncertainty.
- **Recommended against opening the follow-up settings-mega-cluster decomposition phase**, tied explicitly to the measured pool-contention mechanism (adding more concurrent Chromium-launching harnesses to an already-contended four-worker pool is unlikely to help and could make it worse) and to the mega-cluster's harder decomposition profile — not to a fixed target number, per D-06.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Task 3's own AST verify one-liner (as written in the plan) raises AttributeError**
- **Found during:** Task 3, running the plan's provided verify command for `HARNESSES`/`EXPECTED_SLOWEST` wiring
- **Issue:** The plan's verify script accesses `.elts` directly on the matched `ast.Assign` node (`[a for a in t.body if ...][0].elts`), but `ast.Assign` has no `elts` attribute — only `ast.Assign.value` (the `ast.List` node) does. Running the script verbatim raises `AttributeError: 'Assign' object has no attribute 'elts'` before any assertion can run.
- **Fix:** Ran the equivalent check locally with `.value.elts` inserted (`[a for a in t.body if ...][0].value.elts`), which correctly enumerates `HARNESSES`/`EXPECTED_SLOWEST` list elements. This is a self-contained correction to my own verification invocation — no plan file, source file, or committed artifact was edited to make this fix; it only affects how I confirmed the acceptance criteria.
- **Files modified:** None (verification-only; the corrected one-liner was run directly in the shell, not written to any file)
- **Verification:** Corrected script printed `final-wiring-ok 24 flights= False`, matching the skip-flights branch's expected `HARNESSES` count (24, unchanged) and confirming no flights entry exists in either list.
- **Committed in:** N/A (no file changed by this fix)

---

**Total deviations:** 1 auto-fixed (1 bug, in the plan's own verify tooling, not in any shipped artifact)
**Impact on plan:** No impact on scope or shipped artifacts — the fix only corrected how this executor confirmed the wiring was unchanged; the underlying acceptance criteria (24 harnesses, no flights entry, helper module absent) were still fully verified.

## Issues Encountered

- **`companion/test_browser_ux.py` cannot report a literal `76/76` on this native macOS/arm64 host**, for the same pre-existing, fully environmental reasons documented since `31-01-SUMMARY.md` and re-confirmed unchanged in `31-04-SUMMARY.md`: Blink's `EditingMacBehavior` makes `Control+A` a no-op for text selection on native macOS (only Linux's `EditingUnixBehavior` — the real `ubuntu-latest` CI runner — treats it as select-all), plus one intermittent arm64-Chromium DOM-detach compositor race. Both native full-suite re-runs and the standalone confirmation run in this plan hit exactly these same three known checks, never a new one — `73/76 checks pass` is the correct, expected transcript on this host, and the check *count* (76, unchanged) is what the skip-flights branch's acceptance criteria actually require. Correctness at 96/96 (conserved across the three companion/test_browser_ux*.py files) was already proven end-to-end in Docker by plan 04 and nothing in this plan touched any of those three files.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- **D-05 is closed with a written verdict:** MISSED against the ~30-40% bar on every one of five local-proxy samples (9.1%-29.6%, mean 22.4%, median 28.7%), with an explicit recommendation against opening a follow-up settings-mega-cluster decomposition phase, reasoning tied to the measured pool-contention mechanism and the mega-cluster's harder decomposition profile.
- **The recommendation is not final in the strictest sense** — it is a local-proxy verdict. `31-TIMINGS.md` states explicitly that D-05's authoritative figure comes from a real CI `gh run view` measurement on this branch, which has not yet been pushed, and that the verdict should be revisited if a real CI number disagrees materially (the CI runner's 4 vCPUs vs. this host's 10 could shift the pool-contention finding in either direction).
- **Phase 31 is otherwise complete:** both mandatory extractions (Health-Drawings, Quiet-Wake) are wired and verdict-preserving (96 checks conserved across three files), 24/24 harnesses run in the existing worker pool with zero `.github/workflows/ci.yml` change (D-07 held end to end), and the optional third extraction was declined on measured evidence rather than by default.
- No open blockers for this phase. Any future revisit of the settings mega-cluster should first address the pool-contention mechanism itself (more CI cores, or a concurrency cap on Chromium-launching harnesses) rather than repeating the same extraction pattern into the same contended pool.

---
*Phase: 31-ci-test-suite-parallelize-companion-test-browser-ux-py-to-cu*
*Completed: 2026-09-22*

## Self-Check: PASSED

- FOUND: `.planning/phases/31-ci-test-suite-parallelize-companion-test-browser-ux-py-to-cu/31-05-SUMMARY.md`
- FOUND: `.planning/phases/31-ci-test-suite-parallelize-companion-test-browser-ux-py-to-cu/31-TIMINGS.md`
- FOUND commit `3e5f061` (Task 3)
