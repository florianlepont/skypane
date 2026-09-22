---
phase: 31-ci-test-suite-parallelize-companion-test-browser-ux-py-to-cu
plan: 04
subsystem: testing
tags: [ci, worker-pool, coverage, docker, ci-parity, contention]

requires:
  - phase: 31-01
    provides: "companion/test_browser_ux_helpers.py shared module, 31-BASELINE-CHECKS.txt, 31-TIMINGS.md pre-split baseline"
  - phase: 31-02
    provides: "companion/test_browser_ux_health_drawings.py (11 checks)"
  - phase: 31-03
    provides: "companion/test_browser_ux_quiet_wake.py (9 checks), companion/test_browser_ux.py reduced to 76/76"
provides:
  - "Both extracted harnesses wired into scripts/run_all_tests.py's HARNESSES/EXPECTED_SLOWEST — CI now runs all 24 harnesses with zero .github/workflows/ci.yml change (D-07)"
  - "All four stale harness-count figures (18/22 -> 24) corrected across scripts/run_all_tests.py and pyproject.toml"
  - "A real, measured post-split JOBS=4 timing baseline plus the D-05 gate arithmetic and verdict, recorded in 31-TIMINGS.md"
  - "A fixed cross-file AST regression in companion/test_companion_app.py's CFG-79 check, exposed by this plan's wiring"
affects: [31-05]

tech-stack:
  added: []
  patterns:
    - "Non-root user inside the linux/amd64 Docker correctness container, to avoid root's permission-check bypass false-failing read-only-directory simulation tests — a new wrinkle on 31-01/31-02/31-03's established Docker-verification recipe"
    - "Local total wall time == the reduced parent's own wall time (bounded critical path), used as the empirical basis for a labelled CI-job-level estimate per D-01's own methodology"

key-files:
  created: []
  modified:
    - scripts/run_all_tests.py
    - pyproject.toml
    - companion/test_companion_app.py
    - .planning/phases/31-ci-test-suite-parallelize-companion-test-browser-ux-py-to-cu/31-TIMINGS.md

key-decisions:
  - "Measured the D-05 timing comparison natively (same host/architecture as plan 01's own JOBS=4 baseline) rather than in Docker, since QEMU-emulated linux/amd64 runs 4-5x slower and would not be comparable to plan 01's native 240.9s figure — used Docker only for the separate correctness proof, exactly splitting the two concerns the way plans 01-03 already established."
  - "Ran the Docker correctness verification as a non-root user (with the Playwright Chromium cache copied into that user's home) after discovering root's own permission-check bypass silently false-failed four read-only-directory-simulation checks — an artifact of the verification environment, not of this plan's code changes."
  - "Recommended against a mechanical Flights extraction even under the plan's own 'gate missed -> extract Flights' template, because the measured pool-contention finding (every non-browser harness slowed 22-77% with zero code changes) suggests a fourth concurrent Chromium process is unlikely to help under the current mechanism; flagged this explicitly for plan 05's checkpoint alongside the standard two-branch recommendation."

requirements-completed: [D-01, D-03, D-05, D-06, D-07]

coverage:
  - id: D1
    description: "companion/test_browser_ux_health_drawings.py and companion/test_browser_ux_quiet_wake.py registered as HARNESSES entries (with inline comments) and as EXPECTED_SLOWEST entries ahead of server/test_render.py; all four stale harness-count figures (docstring, HARNESSES header, coverage-parallel comment, pyproject.toml header) corrected to 24; companion/test_browser_ux_helpers.py confirmed absent from both lists; pyproject.toml's parallel/omit/fail_under untouched; .github/ untouched"
    requirement: "D-07"
    verification:
      - kind: unit
        ref: "AST assertion over scripts/run_all_tests.py: len(HARNESSES)==24, all unique and existing, both new entries present in both lists ahead of server/test_render.py, helper module absent"
        status: pass
      - kind: other
        ref: "server/.venv/bin/ruff check scripts/ ; server/.venv/bin/ruff check . (whole repo)"
        status: pass
      - kind: other
        ref: "git status --porcelain .github/ (empty)"
        status: pass
    human_judgment: false
  - id: D2
    description: "The full 24-harness suite passes end-to-end at JOBS=4 with the coverage threshold intact (93% > 83% fail_under), verified via a linux/amd64 Docker container matching CI's ubuntu-latest architecture (run as a non-root user); 76+11+9=96 checks conserved across the three companion/test_browser_ux*.py files; a real cross-file regression in companion/test_companion_app.py (broken by 31-01's own extraction, first exposed when this plan wired all 24 harnesses to run together) found and fixed"
    requirement: "D-03"
    verification:
      - kind: integration
        ref: "docker exec --user testuser ... JOBS=4 scripts/run_all_tests.py (linux/amd64) -> ==> Result: PASS, 24/24 ==> PASS lines, coverage TOTAL 93%"
        status: pass
      - kind: unit
        ref: "server/.venv/bin/python3 companion/test_companion_app.py -> companion-app: 317/317 checks pass (post-fix)"
        status: pass
    human_judgment: false
  - id: D3
    description: "31-TIMINGS.md carries a post-split section (3 native JOBS=4 samples, full per-harness table, both browser harnesses called out), the suite-level and CI-job-level delta arithmetic against plan 01's baseline, the pool-contention root-cause finding, the three required caveats, and a D-05/D-06 gate verdict + recommendation for plan 05's checkpoint (including the Flights non-contiguity flag)"
    requirement: "D-05"
    verification: []
    human_judgment: true
    rationale: "The go/no-go call on whether to open a D-05 follow-up phase is explicitly the developer's decision at plan 05's checkpoint (D-05's own text: 'the incremental win wasn't judged worth the additional risk'), not something this plan can auto-pass. This plan's job — done — is to make that decision cheap to take with real arithmetic, not to make it."

duration: ~2h30m
completed: 2026-09-22
status: complete
---

# Phase 31 Plan 04: Worker-Pool Wiring + D-05 Timing Verdict Summary

**Wired both extracted browser harnesses into `scripts/run_all_tests.py`'s existing worker pool with zero CI/YAML change, then measured the real JOBS=4 wall-time delta and found the D-05 gate MISSED on every local sample — not because the extraction was wrong, but because three concurrent Chromium processes now contend for the pool's four worker slots, slowing every other harness down 22-77% and eating most of the intrinsic per-check savings.**

## Performance

- **Duration:** ~2h30m (roughly a third spent provisioning the linux/amd64 Docker correctness container — including a non-root-user detour after root's own permission bypass false-failed four unrelated checks — and running the full 24-harness suite three times natively plus once in Docker for the timing/correctness split)
- **Completed:** 2026-09-22
- **Tasks:** 3/3 completed
- **Files modified:** 4 (2 wiring files, 1 cross-file regression fix, 1 measurement artifact)

## Accomplishments

- Registered `companion/test_browser_ux_health_drawings.py` and `companion/test_browser_ux_quiet_wake.py` in `HARNESSES` (right after their parent, each with an inline comment naming the extracting plan) and in `EXPECTED_SLOWEST` (ahead of `server/test_render.py`, with plans 02/03's measured standalone times) — CI now runs all 24 harnesses through the existing worker pool with `.github/workflows/ci.yml` completely untouched, exactly as D-07 requires.
- Corrected all four stale harness-count figures (`scripts/run_all_tests.py`'s docstring, its `HARNESSES` header comment, its coverage-parallel comment inside `main()`, and `pyproject.toml`'s `[tool.coverage.run]` header comment) from 18/22 to the live AST count of 24.
- Found and fixed a real, pre-existing cross-file regression: `companion/test_companion_app.py`'s CFG-79 check statically parses `test_browser_ux.py` looking for a module-level `Assign` node named `VIEW_TRANSITION_ROUTES` — but 31-01-PLAN.md Task 2 moved that assignment into the shared `test_browser_ux_helpers.py` module, leaving only an import behind. The check false-failed the first time all 24 harnesses ran together in this plan's JOBS=4 suite (the combination no prior plan exercised). Re-targeted the AST parse at the constant's actual current declaration site.
- Measured the post-split JOBS=4 wall time on the same host/architecture as plan 01's native pre-split baseline: three samples (209.5s, 279.4s, 258.2s) against the 240.9s pre-split figure. Suite-level delta ranges from +13.0% to -16.0% (mean -3.4%); the D-01-methodology CI-job-level estimate ranges from 9.1% to 29.6% (mean/median 15-18%) — every sample misses D-05's ~30-40% bar.
- Root-caused the shortfall: every non-browser harness (`server/test_render.py` +62%, `companion/test_status_pages.py` +77%, `server/test_poll_loop.py` +59%, `companion/test_companion_app.py` +22%) got measurably slower post-split with zero code changes to any of them, because `EXPECTED_SLOWEST`'s submission order now puts three Chromium-launching harnesses into three of the pool's four worker slots simultaneously — where only one used to run at a time. This is the T-31-11 threat-register finding, realized and measured.
- Proved correctness end-to-end via a `linux/amd64` Docker container (matching CI's real architecture), run as a non-root user: `==> Result: PASS`, 24/24 `==> PASS` lines, `76+11+9=96` checks conserved, coverage `93%` (well above the `83%` `fail_under` floor).
- Wrote the full D-05/D-06 gate verdict into `31-TIMINGS.md`: MISSED on every local sample, with the specific recommendation that plan 05 read a real `gh run view` CI timing before deciding (per RESEARCH.md's own phase-gate requirement) rather than trust this local proxy alone, and a flag that the early Flights cluster is not contiguous should it be extracted regardless.

## Task Commits

1. **Task 1: Register the two extracted harnesses and correct every stale harness count** - `da860ac` (feat)
2. **Task 2: Run the full suite at JOBS=4 and record the measured post-split wall time** - `64ba819` (fix — the VIEW_TRANSITION_ROUTES regression found while executing this task) + `f2c65cf` (docs, folded together with Task 3 below since both write to the same file)
3. **Task 3: Record the D-05 gate position and the follow-up recommendation** - `f2c65cf` (docs)

**Plan metadata:** (this commit)

## Files Created/Modified

- `scripts/run_all_tests.py` - Two new `HARNESSES`/`EXPECTED_SLOWEST` entries with inline comments; docstring, `HARNESSES` header comment and coverage-parallel comment corrected from 18/22 to 24
- `pyproject.toml` - `[tool.coverage.run]` header comment corrected from 18 to 24; no other change
- `companion/test_companion_app.py` - CFG-79's `VIEW_TRANSITION_ROUTES` AST parity check re-targeted from `test_browser_ux.py` to `test_browser_ux_helpers.py` (its actual declaration site since 31-01)
- `.planning/phases/31-ci-test-suite-parallelize-companion-test-browser-ux-py-to-cu/31-TIMINGS.md` - Post-split measurement section (3 native samples + full timing table), Docker correctness section, suite-level/job-level delta arithmetic, pool-contention root-cause analysis, the three required caveats, and the D-05/D-06 gate verdict + plan-05 recommendation

## Decisions Made

- **Timing measured natively, correctness measured in Docker — the same split plans 01-03 already established, applied here to the full 24-harness suite rather than a single file.** QEMU-emulated `linux/amd64` runs 4-5x slower than native, so Docker's own wall-time numbers (445.6s total) are explicitly excluded from the D-05 arithmetic; only the three native samples feed the comparison against plan 01's native 240.9s baseline.
- **Ran the Docker correctness container as a non-root user.** The first Docker attempt (as root) false-failed four checks that simulate a read-only state directory via `chmod` — root bypasses that simulation entirely on Linux, which is a verification-environment artifact rather than a code defect. Created a non-root user, chowned the venv and repo to it, and copied the Playwright Chromium cache into its home directory (the first non-root attempt silently SKIPPED all three browser harnesses with an exit-0 "Chromium not found" because the cache lived under `/root/.cache`).
- **Went beyond the plan's own "gate missed -> recommend Flights" template with an explicit caveat.** The pool-contention finding (three concurrent Chromium processes slowing down every other harness) suggests a fourth concurrent browser is unlikely to be a clean win under the current mechanism, possibly worse. Recorded this directly in the plan-05 recommendation alongside the standard two branches, rather than mechanically recommending Flights because the gate read as missed.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] companion/test_companion_app.py's VIEW_TRANSITION_ROUTES parity check false-failed against the extracted helper module**
- **Found during:** Task 2 (first full-suite JOBS=4 run after Task 1's wiring)
- **Issue:** The CFG-79 check statically AST-parses `companion/test_browser_ux.py` looking for a module-level `Assign` node named `VIEW_TRANSITION_ROUTES`, deliberately reading the file as text rather than importing it. 31-01-PLAN.md Task 2 (executed in a prior plan) moved that assignment into `companion/test_browser_ux_helpers.py` and left only an import behind in `test_browser_ux.py` — so the AST walk found no `Assign` node, even though the constant's value never changed. This combination (`test_companion_app.py` and the reshaped `test_browser_ux.py` running in the same suite) was never exercised together by plans 01-03, since none of them ran the full wired suite.
- **Fix:** Re-targeted the AST parse at `companion/test_browser_ux_helpers.py`, the constant's actual current declaration site, updating the surrounding comment to explain the relocation.
- **Files modified:** `companion/test_companion_app.py`
- **Verification:** `server/.venv/bin/python3 companion/test_companion_app.py` -> `companion-app: 317/317 checks pass` (a separate, unrelated one-off `BrokenPipeError` transient network flake on the first re-run attempt did not reproduce on a second run, confirming it was noise, not caused by this fix).
- **Committed in:** `64ba819`

---

**Total deviations:** 1 auto-fixed (1 bug). No architectural changes, no scope creep — the fix was a one-line retarget of an existing check's file path plus an updated comment.
**Impact on plan:** Necessary to reach a genuine full-suite green run; without it, the Docker correctness proof in Task 2 would have shown a false failure unrelated to this plan's own wiring changes.

## Issues Encountered

- **Native JOBS=4 runs on this host cannot produce a literal `==> Result: PASS` for `companion/test_browser_ux.py`, for the same pre-existing environmental reasons 31-01/31-03 already documented and root-caused** (Blink's `EditingMacBehavior` treats `Control+A` as "move to line start" rather than select-all on native macOS; one intermittent arm64-Chromium DOM-detach compositor race). All three native timing samples in this plan hit exactly these known checks, never a new one. The Docker `linux/amd64` run — matching CI's real architecture — is what proves genuine end-to-end correctness (24/24 PASS); the native runs exist solely for wall-time comparability with plan 01's own native baseline.
- **A false permission-bypass failure under Docker root, unrelated to this plan.** Documented above under Decisions Made — resolved by running as a non-root user, not by touching any test or application code.
- **The measured wall-time result was not the hoped-for clean win.** Investigated rather than tuned away, per Task 2's explicit instruction: the root cause is CPU contention among three simultaneously-launched Chromium processes now occupying three of the pool's four worker slots (T-31-11), not a defect in either extracted file (both remain individually and jointly verdict-preserving per the Docker run). This is written up in full in `31-TIMINGS.md`'s "Critical path and pool contention" section for plan 05's checkpoint.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Plan 05's checkpoint has a complete, arithmetic-backed basis for the extract-or-stop decision: the D-05 gate reads as MISSED on every local sample (job-level estimate 9.1%-29.6%, all below the ~30-40% bar), with the specific, measured root cause (worker-pool contention among concurrent Chromium processes) written up rather than asserted.
- The explicit recommendation for plan 05: get a real CI `gh run view` timing before finalizing the call (this local proxy is on a 10-core host; CI's real runner has only 4 vCPUs, per RESEARCH.md's own Pitfall 5, which could make the contention better or worse there — this file cannot resolve that from local numbers alone). If CI confirms the local finding, D-05's own text says to stop rather than open a follow-up phase, and specifically not to extract Flights mechanically under the current worker-pool mechanism.
- If Flights is extracted anyway, plan 05 needs one fact RESEARCH.md's original line-range analysis did not carry forward: the early Flights cluster is not contiguous in the current file — a quiet-hours-caption hit-target check sits between the first Flights check and the icon-hit-targets check, in file order at this plan's commit. The extraction must anchor on check names, not a line range, and must leave that check behind.
- No open blockers. `24/24` harnesses are live in CI's worker pool starting with this commit; `.github/workflows/ci.yml` needed no change.

---
*Phase: 31-ci-test-suite-parallelize-companion-test-browser-ux-py-to-cu*
*Completed: 2026-09-22*
