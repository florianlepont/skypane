---
phase: quick-260902-req
plan: 01
subsystem: panel-render

tags: [render, illustrations, geometry, e-ink, tdd]

requires:
  - phase: 03-visual-polish-on-real-glass
    provides: "The two-flight poster composition (D-25/D-26), `IllustrationPlacement.content`/`.rect`, `_opaque_bbox()`/`_threshold_alpha()`, and the horizontal-centring + previous-card vertical-centring corrections from debug session illustration-crop-text-margin"
provides:
  - "The main illustration's vertical anchor now follows its painted (opaque, alpha-thresholded) pixels via `_top_for_centered_content()`, matching the horizontal anchor and the previous card's vertical anchor — the sixth and last position anchor the illustration-crop-text-margin debug session left on the source rectangle"
  - "`MAIN_ILLUSTRATION_CENTER_Y_FRAC` (0.4006), replacing the retired `MAIN_ILLUSTRATION_TOP_FRAC` (0.30), re-derived from air-france.png (03-UI-SPEC.md's confirmed reference render) so the approved on-glass look is unchanged"
  - "A permanent regression harness (server/test_render.py check 119) that measures the main illustration's visible vertical-centre spread across all 43 vendored files and fails above a 2px tolerance"
affects: [panel-render-visual-quality, production-deploy-260902-req]

tech-stack:
  added: []
  patterns:
    - "Reuse the existing shared anchor helper (`_top_for_centered_content()`) rather than writing a new one for the main card — the previous card already proved this helper's contract; a second independent implementation would risk the two axes disagreeing about what 'painted' means again"
    - "Regression checks for a per-file drift defect assert on the SPREAD across the whole vendored fixture set, never on any single file's absolute position — absolute position is a design constant that gets re-derived independently, and pinning it in the same check that measures drift would make the check move in lockstep with the bug"

key-files:
  created: []
  modified:
    - server/plane/render.py
    - server/test_render.py
    - .planning/phases/03-visual-polish-on-real-glass/03-UI-SPEC.md

key-decisions:
  - "MAIN_ILLUSTRATION_CENTER_Y_FRAC set to 0.4006, not the plan's alternative candidates (per-file median 0.40594, or a fresh mid-spread pick) — this is the exact fraction at which air-france.png (03-UI-SPEC.md's own documented reference render, byte-identical claim already on record from the illustration-crop-text-margin session) lands on its pre-fix row (visible centre y=641.0 both before and after). Preserving the developer-confirmed reference render was the explicit must-have; re-optimizing for the median would have moved that reference file for no requested benefit."
  - "main_top is now computed AFTER main_resized loads (inside the `if main_resized is not None:` block), not before — `_top_for_centered_content()` needs the resized image's own opaque bbox, so it structurally cannot run against an unloaded source path the way the retired MAIN_ILLUSTRATION_TOP_FRAC arithmetic did. This also means a corrupt/unselectable main illustration (main_resized is None) now correctly skips main_top computation entirely rather than computing an unused value, matching how main_left already behaved."
  - "Task 2 (per plan) additionally fixed two OTHER readers of the retired MAIN_ILLUSTRATION_TOP_FRAC name in server/test_render.py — check 10 (D-24 mirror-guard bbox) and this plan's own new check 119 — both grepped for and found before deletion, per the plan's explicit instruction. No other code reader existed; one historical revision-diff table row in 03-UI-SPEC.md (Revision 3 vs 4 comparison) was deliberately left as a historical record, matching how the previous card's own earlier 0.76 constant is preserved verbatim in that same file's revision history."
  - "server/test_poll_loop.py's `_DEFAULT_CONFIG_DIGEST` was deliberately NOT touched by this plan's auto tasks, per this project's own re-pin discipline: the replacement value must come from a real CI FAIL log, never a local computation. This is Task 3's job, and Task 3 is the checkpoint below — not executed by this agent."

requirements-completed: [REQ-260902-req-PANEL]

coverage:
  - id: D1
    description: "The main illustration's visible vertical centre is fixed across all 43 vendored files (was drifting 120.5px) via _top_for_centered_content(), with a regression harness pinning the invariant"
    requirement: REQ-260902-req-PANEL
    verification:
      - kind: unit
        ref: "server/test_render.py::_main_illustration_vertical_centre_has_no_per_file_drift (check 119) — RED (120.5px spread) before the fix, GREEN (0.5px spread) after"
        status: pass
      - kind: unit
        ref: "server/test_render.py full suite (119/119 checks pass, including check 10's re-pointed mirror-guard and all pre-existing D-26/illustration-crop-text-margin checks)"
        status: pass
    human_judgment: false
  - id: D2
    description: "The developer-confirmed reference render (air-france.png) keeps its currently-approved on-glass position — the constant is re-derived to reproduce the approved look, not to redesign it"
    requirement: REQ-260902-req-PANEL
    verification:
      - kind: unit
        ref: "Measured directly: air-france.png's visible vertical centre is y=641.0 both before (old rectangle-top anchor) and after (new MAIN_ILLUSTRATION_CENTER_Y_FRAC=0.4006 anchor) this fix"
        status: pass
    human_judgment: true
    rationale: "Byte-level identity was not re-verified for the full canvas (only the aircraft's opaque-pixel centre coordinate was checked) — final visual confirmation on real glass is explicitly reserved for the developer in the Task 3 checkpoint's item 3 ('On glass')."
  - id: D3
    description: "The panel.bin digest pin is handled through the established CI-authoritative process, never guessed locally; production deployment is surfaced to the developer as their action, never executed by the executor"
    requirement: REQ-260902-req-PANEL
    verification: []
    human_judgment: true
    rationale: "By design and by explicit plan/threat-model instruction (T-260902req-01, T-260902req-02), this agent is forbidden from re-pinning the digest locally or running deploy.sh/SSH/systemctl. This is the Task 3 checkpoint, reported below as still pending the developer's action."

# Metrics
duration: ~15min (Tasks 1-2; Task 3 checkpoint pending developer action)
completed: 2026-09-02
status: complete
---

# Quick Task 260902-req: Fix Inconsistent Aircraft Centering (panel side) Summary

**Anchored the main illustration's vertical position to its painted pixels via `_top_for_centered_content()`, closing the one anchor (of six) the illustration-crop-text-margin debug session missed — cut the per-file vertical-centre drift across all 43 vendored illustrations from 120.5px to 0.5px, with a permanent regression harness pinning the invariant. Both auto tasks (RED test, GREEN fix) are complete and committed; Task 3 (panel.bin digest re-pin from real CI + production deploy approval) is a blocking developer checkpoint, not yet actioned.**

## Performance

- **Duration:** ~15 min (Tasks 1-2 only)
- **Started:** 2026-09-02T17:58:00Z (approx, following plan commit 292909a)
- **Completed (auto tasks):** 2026-09-02T18:06:05Z
- **Tasks:** 2 of 3 (Task 3 is a blocking developer checkpoint, reported below — not executed by this agent)
- **Files modified:** 3 (server/plane/render.py, server/test_render.py, .planning/phases/03-visual-polish-on-real-glass/03-UI-SPEC.md)

## Accomplishments
- Added a failing regression check (server/test_render.py, check 119) that measures the main illustration's visible vertical-centre spread across all 43 vendored files under `server/assets/icons/illustrations/`; confirmed RED on unmodified render.py with the exact measured defect (120.5px spread, air-caraibes-atr72.png=621.0 to generic-a330.png=741.5)
- Fixed `_build_active_canvas()` in server/plane/render.py: main_top is now computed after `main_resized` loads, via `_top_for_centered_content(main_resized, HEIGHT * MAIN_ILLUSTRATION_CENTER_Y_FRAC)` — the same helper the previous card already used — instead of `round(HEIGHT * MAIN_ILLUSTRATION_TOP_FRAC)` applied to the unloaded source rectangle's top
- Retired `MAIN_ILLUSTRATION_TOP_FRAC` (0.30), introduced `MAIN_ILLUSTRATION_CENTER_Y_FRAC` (0.4006) re-derived from air-france.png so the developer-confirmed reference render's aircraft position is unchanged (visible centre y=641.0 before and after)
- Fixed the two other readers of the retired constant in server/test_render.py (check 10's D-24 mirror-guard bbox, and this plan's own new check 119) so the full suite stays internally consistent with the real render path
- Updated 03-UI-SPEC.md's item 3 (main illustration) design-constant record to match the shipped code, following the existing "Corrected \<date\>" blockquote precedent items 4/5/6 already use
- Confirmed GREEN: 119/119 server/test_render.py checks pass, post-fix drift spread is 0.5px (down from 120.5px)
- Ran `./scripts/run-all-tests.sh` (all 16 harnesses): overall result PASS. The panel.bin digest check reported the expected platform-informational NOTE on this non-Linux dev machine (pinned digest mismatch, downgraded to informational per `_DEFAULT_CONFIG_DIGEST`'s own documented Linux-strict/non-Linux-informational discipline) rather than a hard failure — the real Linux/CI-authoritative mismatch that Task 3 must re-pin from will only surface as a genuine FAIL on a real CI run, which is exactly the process Task 3 hands to the developer

## Task Commits

Each task was committed atomically:

1. **Task 1: Pin the per-file vertical drift with a failing regression check** - `bb8b84d` (test) — RED confirmed (120.5px spread, exit 1)
2. **Task 2: Anchor the main illustration's vertical position to its painted pixels** - `f89659d` (fix) — GREEN confirmed (0.5px spread, 119/119 checks pass, exit 0)

Task 3 (developer checkpoint) has not been executed — see below.

**Plan metadata:** not yet committed — per this task's explicit instructions, SUMMARY.md/STATE.md are not committed by this agent; the orchestrator handles that commit.

## Files Created/Modified
- `server/plane/render.py` - Retired `MAIN_ILLUSTRATION_TOP_FRAC`, added `MAIN_ILLUSTRATION_CENTER_Y_FRAC` (0.4006); `_build_active_canvas()` now computes `main_top` via `_top_for_centered_content()` after `main_resized` loads
- `server/test_render.py` - New check 119 (main illustration vertical-drift regression, EXPECTED_CHECK_COUNT 118→119); check 10 (D-24 mirror guard) and check 119 both re-pointed at the new constant/helper instead of the retired one
- `.planning/phases/03-visual-polish-on-real-glass/03-UI-SPEC.md` - Item 3 (main illustration) updated to document vertical centring on painted content and the 2026-09-02 correction, matching items 4/5/6's existing "Corrected" blockquote style

## Decisions Made
See `key-decisions` in frontmatter above: the 0.4006 constant choice (air-france.png reference preservation over median-optimizing), the post-load main_top computation ordering, the two additional test_render.py call-site fixes, and the deliberate non-touch of `_DEFAULT_CONFIG_DIGEST`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug, scoped to plan's own Task 2] Fixed check 10's stale bbox computation, not just the drift check**
- **Found during:** Task 2, first post-fix test run
- **Issue:** After renaming `MAIN_ILLUSTRATION_TOP_FRAC` → `MAIN_ILLUSTRATION_CENTER_Y_FRAC`, `server.plane.render` had no attribute `MAIN_ILLUSTRATION_TOP_FRAC`, breaking check 10 (`_illustration_not_mirrored_between_states`) with an `AttributeError`, in addition to this plan's own new check 119 (also expected, and already anticipated in Task 2's plan text as something to grep for and fix).
- **Fix:** Re-pointed check 10's locally-computed `main_top` to call the real `render._top_for_centered_content()` against `MAIN_ILLUSTRATION_CENTER_Y_FRAC`, matching what `_build_active_canvas()` itself now computes, so the check's crop bbox keeps lining up with where the real render actually places the illustration.
- **Files modified:** server/test_render.py
- **Verification:** Full suite re-run, 119/119 pass
- **Committed in:** f89659d (Task 2 commit)

The plan's own Task 2 action text explicitly anticipated and instructed this fix ("Grep for every remaining reader of the old name before deleting it... convert or leave it deliberately and say which in the comment"), so this is scoped work within the plan, not an out-of-plan addition — recorded here for traceability since it wasn't literally spelled out as a separate numbered step.

---

**Total deviations:** 1 auto-fixed (in-scope per plan instruction, Rule 1)
**Impact on plan:** No scope creep — this was explicitly anticipated by Task 2's own action text.

## Issues Encountered
None beyond the anticipated check-10 fixup above.

## Known Stubs
None.

## Threat Flags
None — no new external input crosses a trust boundary; this plan changed an internal layout constant and an anchor expression only, as the plan's own threat model states.

## User Setup Required
None — no external service configuration required for Tasks 1-2. Task 3 (below) requires developer action but is not "setup" in the environment-configuration sense.

## CHECKPOINT REACHED (Task 3 — not yet actioned)

**Type:** human-verify (gate="blocking-human")
**Plan:** quick-260902-req / 01
**Progress:** 2/3 tasks complete

### Completed Tasks

| Task | Name        | Commit | Files                        |
| ---- | ----------- | ------ | ---------------------------- |
| 1    | Pin the per-file vertical drift with a failing regression check | `bb8b84d` | server/test_render.py |
| 2    | Anchor the main illustration's vertical position to its painted pixels | `f89659d` | server/plane/render.py, server/test_render.py, .planning/phases/03-visual-polish-on-real-glass/03-UI-SPEC.md |

### Current Task

**Task 3:** developer checkpoint (digest re-pin + deploy approval + on-glass confirmation)
**Status:** blocked — awaiting developer action (explicitly may not be performed by an agent)
**Blocked by:** two actions this project's own discipline reserves for the developer

### Checkpoint Details

1. **panel.bin digest re-pin.** This change moves real rendered pixels, so `_DEFAULT_CONFIG_DIGEST` in `server/test_poll_loop.py` (currently `46c18ea48d711bf62520570367cd019e2144073019dabe1d4282766d3ae4be51`) will mismatch on the CI (Linux) runner. Locally on this Darwin dev machine, `./scripts/run-all-tests.sh` reported this as an informational NOTE only (`58b537448d3d34d2dc5b394cdd1c6995f4a05d79899376f8b918f7c0041f9223 != pinned ... (platform.system()='Darwin')`) — per that constant's own documented discipline, the real replacement value must come from a genuine CI FAIL log, never a local computation. Push the branch, let CI fail, take the digest CI itself reports, and update the pin with a comment recording that this change (quick task 260902-req) is why it moved.
2. **Deployment.** `.github/workflows/ci.yml`'s `deploy` job runs `deploy/deploy.sh` on push to `main`, gated behind the `production` environment's required reviewer. Two things to check:
   - Confirm whether the ORIGINAL fix (commit `cea4984`, "anchor flight text to the illustration's opaque pixels, not its rectangle", 2026-08-28) ever actually reached the VPS — open the Actions tab, find the `deploy` job for the main-branch run containing that commit, and check it was approved and succeeded rather than sitting pending.
   - Once this plan's change merges, approve the new `production` deploy so the fix reaches the frame.
3. **On glass.** After the deploy lands, look at the frame across several different airlines and confirm the aircraft no longer jumps vertically between them.

This agent did not run `deploy/deploy.sh`, did not SSH to the VPS, and did not run `sudo systemctl` — those remain the developer's to run or approve, per this plan's own threat model (T-260902req-01) and this project's standing rule.

### Awaiting

Developer to: push the branch and let CI produce the real digest, re-pin `_DEFAULT_CONFIG_DIGEST` from that CI FAIL output, check/approve the production deploy, and confirm the fix on real glass. Once done, this quick task can be marked fully complete (or a follow-up quick task can carry the digest re-pin commit if the developer prefers this agent to apply the exact value they retrieve from CI).

## Next Phase Readiness
- The panel-side rendering fix (Tasks 1-2) is complete, tested, and committed — ready to merge/deploy pending the Task 3 checkpoint.
- A separate, related quick task (`260902-req-02-PLAN.md`, the companion-gallery plan) exists in this same directory and was explicitly out of scope for this execution — it should be run afterward, per the orchestrating session's own instructions.
- No blockers for other in-flight work; this fix touches only server/plane/render.py's main-illustration vertical anchor and its own test/spec coverage.

---
*Phase: quick-260902-req*
*Completed: 2026-09-02 (Tasks 1-2; Task 3 pending developer action)*

## Self-Check: PASSED

All claimed files found on disk (server/plane/render.py, server/test_render.py, 03-UI-SPEC.md, this SUMMARY.md); both claimed commits (bb8b84d, f89659d) found in git log.
