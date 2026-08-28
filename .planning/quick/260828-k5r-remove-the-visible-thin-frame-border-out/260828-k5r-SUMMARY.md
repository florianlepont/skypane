---
phase: quick-260828-k5r
plan: 260828-k5r
subsystem: rendering
tags: [pillow, e-ink, spectra6, tdd, render-pipeline]

# Dependency graph
requires:
  - phase: "03-visual-polish-on-real-glass"
    provides: "the D-26 thin outline (draw_frame()) and FRAME_INSET_FRAC/FRAME_STROKE_PX geometry this task removes/retains"
  - phase: "06-companion-configuration-web-interface"
    provides: "server/test_poll_loop.py's pinned _DEFAULT_CONFIG_DIGEST byte-identity gate, now stale locally pending the deferred CI re-pin"
provides:
  - "server/plane/render.py: the D-26 outline is no longer drawn on active-state panels (_build_active_canvas()'s draw_frame() call removed); FRAME_INSET_FRAC/FRAME_STROKE_PX and draw_frame() itself retained unmodified"
  - "server/test_render.py: check 72 - real build_canvas()-path regression proving the outline is genuinely absent (not just absent from draw_frame() called in isolation)"
  - ".planning/phases/03-visual-polish-on-real-glass/03-UI-SPEC.md: dated amendment recording the outline's removal, historical prose left intact"
affects: ["06.x backlog phases (companion status pages that surface render output)", "server/test_poll_loop.py (pending CI re-pin, deferred)"]

# Tech tracking
tech-stack:
  added: []
  patterns: []

key-files:
  created: []
  modified:
    - server/plane/render.py
    - server/test_render.py
    - .planning/phases/03-visual-polish-on-real-glass/03-UI-SPEC.md

key-decisions:
  - "Task 1 executed in full (TDD RED->GREEN): check 72 added and observed failing 71/72 against unmodified code, then the draw_frame() call removed, confirmed 72/72 with checks 16/70 untouched"
  - "Task 2 Steps 1/2/4 executed by the sub-agent; Step 3 (push branch, wait for CI, read the Linux digest from a FAIL line, re-pin, push again) completed afterward by the orchestrator with the developer's explicit approval ('oui pousse'): pushed dc8dedf, opened PR #17 (no PR existed for this branch and CI only triggers on push-to-main or pull_request), read the real ubuntu-latest FAIL line (run 33172916595: digest 6d580b949e1b4b0398794fd3979eef6331611012ff2533b4cd4678a89766ddac != pinned 45b17a3e...), re-pinned server/test_poll_loop.py with a dated note (commit aeac512), pushed again, and confirmed CI green (run 33173185100)"
  - "Plan's Task 1 automated verify command (grep -c 'draw_frame(canvas' server/plane/render.py = 0) has a self-matching false positive: the retained function signature 'def draw_frame(canvas, ink_idx):' itself contains the substring 'draw_frame(canvas', so the literal grep returns 1, not 0, even in the fully-compliant end state the plan itself requires (helper definition unmodified). Verified manually that the only match is the def line, not a call site - the actual done-criterion ('no call form remains') is satisfied. Documented here rather than silently treated as passing."
  - "Task 2 Step 1's reconstruct-and-compare check needed the ACTUAL server/test_render.py TEST_ROUTE fixture (airline-only route with None city/IATA fields does not reproduce the pinned baselines); once corrected to the real fixture (Transavia France / ORY-PMI), all three checks passed exactly with zero fallback needed - re-drawing the outline on the post-edit canvas reproduces the pre-edit baseline digest byte-for-byte for both active states"

requirements-completed: ["QUICK-260828-k5r"]

coverage:
  - id: D1
    description: "The D-26 outline is removed from active-state panels; production render.py no longer calls draw_frame(), while the helper, FRAME_INSET_FRAC, and FRAME_STROKE_PX all survive unmodified"
    requirement: "QUICK-260828-k5r"
    verification:
      - kind: unit
        ref: "server/test_render.py#the D-26 outline is genuinely absent from a real build_canvas() render (check 72)"
        status: pass
      - kind: unit
        ref: "server/test_render.py#draw_frame() draws a thin outline at the ~2.5%-of-width inset (D-26) (check 16, untouched)"
        status: pass
      - kind: unit
        ref: "server/test_render.py#draw_source_fault_badge()'s bounding box stays inside the drawn frame (check 70, untouched)"
        status: pass
    human_judgment: false
  - id: D2
    description: "New check 72 was demonstrated genuinely RED (71/72) against the unmodified code before the removal landed, proving the border was really being drawn on the real render path"
    requirement: "QUICK-260828-k5r"
    verification:
      - kind: other
        ref: "commit 7e2e116's message quotes the exact FAIL line: state='departing' point=(600, 30) read index 1, expected background index 4"
        status: pass
    human_judgment: false
  - id: D3
    description: "Zero collateral change proof: empty state byte-identical to pre-edit baseline; both active states' digests moved; re-drawing the outline back onto each post-edit canvas reproduces the exact pre-edit digest for that state"
    requirement: "QUICK-260828-k5r"
    verification:
      - kind: other
        ref: "throwaway scratchpad script 260828-k5r-verify-collateral.py - all three checks PASS with zero fallback needed (see Deviations section for the fixture-correction detail)"
        status: pass
    human_judgment: false
  - id: D4
    description: "Local suite baseline: ./scripts/run-all-tests.sh shows exactly one red harness (server/test_poll_loop.py, 42/43), sole FAIL is the pinned-digest check reporting a new local digest, no other new failures"
    requirement: "QUICK-260828-k5r"
    verification:
      - kind: integration
        ref: "scripts/run-all-tests.sh full run - FAILED harnesses (1): server/test_poll_loop.py; all other 14 harnesses green"
        status: pass
    human_judgment: false
  - id: D5
    description: ".planning/phases/03-visual-polish-on-real-glass/03-UI-SPEC.md carries a dated amendment recording the removal; historical prose describing the frame as shipped is left intact"
    requirement: "QUICK-260828-k5r"
    verification:
      - kind: other
        ref: "git show dc8dedf -- .planning/phases/03-visual-polish-on-real-glass/03-UI-SPEC.md"
        status: pass
    human_judgment: false
  - id: D6
    description: "server/test_poll_loop.py's _DEFAULT_CONFIG_DIGEST is re-pinned from a real GitHub Actions ubuntu-latest FAIL line (never local/container-computed), with a dated re-pin note, and CI is green after the push"
    verification:
      - kind: integration
        ref: "PR #17, run 33172916595's FAIL line (digest 6d580b94...) re-pinned in commit aeac512; run 33173185100 confirms 'Lint, test, coverage, attribution' PASS"
        status: pass
    human_judgment: false

# Metrics
duration: ~45min (35min sub-agent + ~10min orchestrator push/CI round-trip)
completed: 2026-08-28
status: complete
---

# Quick Task 260828-k5r: Remove the visible thin frame border Summary

**Removed the single production call to `draw_frame()` in `_build_active_canvas()` (server/plane/render.py), added real-render-path regression coverage proving it, amended the design record, and re-pinned `server/test_poll_loop.py`'s `_DEFAULT_CONFIG_DIGEST` from a real CI run after the developer approved the push. CI is green.**

## Performance

- **Duration:** ~45 min (35min sub-agent execution + ~10min orchestrator push/CI round-trip)
- **Completed:** 2026-08-28
- **Tasks:** 2 of 2 complete
- **Files modified:** 4 (server/plane/render.py, server/test_render.py, .planning/phases/03-visual-polish-on-real-glass/03-UI-SPEC.md, server/test_poll_loop.py)

## Status: COMPLETE

Task 1 (TDD RED→GREEN removal of the outline) and Task 2 (collateral-change proof, local suite baseline, UI-spec amendment, and the CI digest re-pin) are all done and verified.

Task 2 Step 3 — deferred by the sub-agent since it requires pushing to the remote — was completed by the orchestrator after the developer explicitly approved ("oui pousse"): pushed `dc8dedf`, opened PR #17 (no PR existed for this branch, and `.github/workflows/ci.yml` only triggers on push-to-`main` or a `pull_request` event, not a plain branch push), read the real ubuntu-latest FAIL line from run `33172916595` (`panel.bin digest 6d580b94... != pinned 45b17a3e...`), re-pinned `server/test_poll_loop.py` line ~137 with a dated note (commit `aeac512`), pushed again, and confirmed run `33173185100`'s "Lint, test, coverage, attribution" check is green.

**Remaining, outside this quick task's scope:** whether/when to merge PR #17 into `main` and redeploy — a separate decision left to the developer.

## Task Commits

1. **Task 1, Step 1 (RED): add failing check 72** - `7e2e116` (test)
2. **Task 1, Steps 2-4 (GREEN): remove the draw_frame() call** - `04b07e2` (feat)
3. **Task 2, Step 4: amend 03-UI-SPEC.md** - `dc8dedf` (docs)
4. **Task 2, Step 3: re-pin `_DEFAULT_CONFIG_DIGEST` from real CI** - `aeac512` (fix, orchestrator, post-approval)

Task 2 Steps 1 and 2 produced no committed artifacts by design — Step 1's verification script is a throwaway scratchpad file (`/private/tmp/.../scratchpad/260828-k5r-verify-collateral.py`, not part of the repo); Step 2 is a read-only test-suite run.

PR: [#17](https://github.com/florianlepont/skypane/pull/17) (open, CI green, not yet merged).

## Files Created/Modified

- `server/plane/render.py` - Deleted the one-line `draw_frame(canvas, fg_idx)` call in `_build_active_canvas()`; replaced the stale D-26 comment with one describing the removal and why `FRAME_INSET_FRAC` survives. `draw_frame()`, `FRAME_INSET_FRAC` (0.025), `FRAME_STROKE_PX` (2) all unchanged.
- `server/test_render.py` - Added check 72 (real `build_canvas()`-path absent-border regression, 7 sample points per active state, derived from `FRAME_INSET_FRAC`/`WIDTH`/`HEIGHT`, never hardcoded literals); `EXPECTED_CHECK_COUNT` 71 → 72.
- `.planning/phases/03-visual-polish-on-real-glass/03-UI-SPEC.md` - Dated amendment appended directly under the Canvas and Geometry constants table; all historical prose describing the frame as shipped (Design System table row, safe-box rationale, on-glass checklist) left intact.
- `server/test_poll_loop.py` - `_DEFAULT_CONFIG_DIGEST` re-pinned to `6d580b949e1b4b0398794fd3979eef6331611012ff2533b4cd4678a89766ddac`, read from PR #17's own CI FAIL output (run 33172916595), with a dated re-pin note.

## Decisions Made

- Followed the plan's TDD execution order exactly for Task 1: RED committed separately from GREEN, with the exact FAIL line captured in the RED commit message as evidence.
- For Task 2 Step 1's reconstruct-and-compare proof, used the real `TEST_ROUTE` fixture from `server/test_render.py` (Transavia France / ORY→PMI) rather than an invented placeholder — the first attempt with a simplified route dict produced non-matching digests purely because it wasn't the actual rendered fixture, not because of any real collateral pixel change. Once corrected, all three checks (empty byte-identity, active-state digest movement, exact reconstruction) passed with zero fallback needed, meaning the full per-pixel-band diff fallback (built against the actual pre-edit `render.py` at `git show HEAD~2`) was implemented and available but not needed to reach a PASS verdict.
- Did not touch `server/test_poll_loop.py` at all, per the explicit constraint that Step 3 (the only step that legitimately produces a new pin value) is deferred.

## Deviations from Plan

### Auto-fixed Issues

None — Task 1 and Task 2 Steps 1/2/4 were executed exactly as specified, with two verification-only findings worth recording (not code deviations):

**1. [Verification-script bug, not a code bug] Task 1's automated verify grep self-matches the retained function signature**
- **Found during:** Task 1, Step 4 (final verification)
- **Issue:** The plan's own automated verify command `test "$(grep -c 'draw_frame(canvas' server/plane/render.py)" = "0"` cannot pass in the fully-compliant end state the plan itself specifies, because the retained (and explicitly required-unmodified) function signature `def draw_frame(canvas, ink_idx):` contains the substring `draw_frame(canvas` and is matched by the same grep pattern intended to detect call sites.
- **Fix:** None applied to code — verified manually via `grep -n 'draw_frame(canvas' server/plane/render.py` that the sole match is the `def` line (line 399), not a call site, satisfying the plan's actual "done" criterion ("No call form of the frame helper remains anywhere in render.py"). Documented here rather than silently claiming the literal grep passed.
- **Files modified:** None (documentation only, this SUMMARY).
- **Verification:** `grep -n 'draw_frame(canvas' server/plane/render.py` → single match at line 399, the `def` line.

**2. [Fixture correction in throwaway verification script] Initial reconstruct-and-compare attempt used an invented route dict**
- **Found during:** Task 2, Step 1
- **Issue:** The first version of the scratchpad verification script hand-typed a simplified `TEST_ROUTE` (airline name only, `None` city/IATA fields) rather than reading the real fixture from `server/test_render.py`. This produced non-matching digests in checks 2 and 3, which could have been misread as evidence of unintended collateral pixel movement.
- **Fix:** Replaced the invented route with `server/test_render.py`'s actual `TEST_ROUTE` fixture (Transavia France, ORY→PMI). Re-ran; all three checks passed exactly, confirming the outline was the only change.
- **Files modified:** Scratchpad-only (`/private/tmp/.../scratchpad/260828-k5r-verify-collateral.py`, not part of the repo).
- **Verification:** Re-run output: `CHECK 1 PASS`, `CHECK 2 PASS` (both states), `CHECK 3 PASS` (both states, exact digest match, no fallback needed).

---

**Total deviations:** 0 code deviations; 2 verification-process findings documented above.
**Impact on plan:** None on shipped code. Both findings are about verification tooling/process, not about `render.py`'s or `test_render.py`'s actual behavior, which matches the plan's intent exactly.

## Issues Encountered

None beyond the two verification-process findings above, both resolved within this session.

## User Setup Required

None - no external service configuration required. (Task 2 Step 3 requires developer **approval to push**, which is a workflow gate, not an environment/service setup step — see Status section.)

## Next Phase Readiness

**Complete.** The render-pipeline change, its regression coverage, the UI-spec amendment, and the CI digest re-pin are all done, tested, committed, and pushed. PR #17 is open with CI green; merging it (and redeploying) is a separate decision left to the developer, and does not block any other in-flight work.

## Self-Check: PASSED

- FOUND: server/plane/render.py
- FOUND: server/test_render.py
- FOUND: .planning/phases/03-visual-polish-on-real-glass/03-UI-SPEC.md
- FOUND: commit 7e2e116 (test RED)
- FOUND: commit 04b07e2 (feat GREEN)
- FOUND: commit dc8dedf (docs UI-SPEC amendment)
- FOUND: commit aeac512 (fix: CI digest re-pin)
- FOUND: PR #17, CI green

---
*Phase: quick-260828-k5r*
*Completed: 2026-08-28*
