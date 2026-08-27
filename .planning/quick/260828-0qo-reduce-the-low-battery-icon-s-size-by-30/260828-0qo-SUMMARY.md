---
phase: 05-low-battery-indicator
plan: 260828-0qo
subsystem: ui
tags: [pillow, rendering, e-ink, battery-icon, on-glass-correction]

# Dependency graph
requires:
  - phase: 05-low-battery-indicator (05-02)
    provides: draw_battery_icon() and the BATTERY_ICON_* constants this plan rescales
provides:
  - Bottom-left battery-low glyph rendered at 70% of its former linear size
  - Repinned test_render.py Checks B/C/D and test_pipeline_e2e.py's battery panel-diff window
  - 05-UI-SPEC.md Revision 2, a dated on-glass correction record
affects: [06-final-on-glass-verification]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Live on-glass tuning: real-hardware feedback triggers a dated Revision N block in the UI-SPEC rather than a silent overwrite (same pattern as Phase 3's D-20/D-21/D-22, D-26/D-27)"
    - "Test containment windows derived from source-of-truth constants (BATTERY_ICON_BOX computed from render.BATTERY_ICON_*) instead of restated literals, so they can't silently drift out of sync"

key-files:
  created: []
  modified:
    - server/plane/render.py
    - server/test_render.py
    - server/test_pipeline_e2e.py
    - .planning/phases/05-low-battery-indicator/05-UI-SPEC.md

key-decisions:
  - "All four size constants reduced by round(original * 0.7); BATTERY_ICON_LEFT/BOTTOM/FILL_FRAC held byte-for-byte unchanged since they are position/ratio, not size"
  - "Stroke width lands at 2px, which happens to equal FRAME_STROKE_PX exactly - kept as the deliberate e-ink legibility floor rather than reduced further"
  - "Nub centring became asymmetric (5px gap above, 6px below) as a consequence of the odd BODY_H-NUB_H=11 leftover under floor division - documented as intended, not a defect"

patterns-established:
  - "Test geometry windows computed from source constants (not hand-written literals) survive future resize/retune iterations without a stale-window bug"

requirements-completed: [DEVICE-04]

coverage:
  - id: D1
    description: "Battery icon renders at 70% linear size (45/22/6/11/2 constants), anchored at the unchanged bottom-left corner, still reading as a battery (outline body, solid nub, partial fill)"
    requirement: "DEVICE-04"
    verification:
      - kind: unit
        ref: "server/test_render.py#_battery_icon_geometry_derives_from_spacing_scale"
        status: pass
      - kind: unit
        ref: "server/test_render.py#_battery_icon_ink_and_hollow_interior"
        status: pass
      - kind: unit
        ref: "server/test_render.py#_battery_icon_conditional_draw_is_spatially_contained"
        status: pass
      - kind: integration
        ref: "server/test_pipeline_e2e.py#_real_battery_poll_changes_only_the_icon_region"
        status: pass
    human_judgment: false
  - id: D2
    description: "Real on-glass confirmation that 70% is the right amount of reduction (not too small) after the follow-up deploy"
    verification: []
    human_judgment: true
    rationale: "Requires viewing the physical 13.3\" Spectra 6 panel after a production redeploy - not observable from this sandbox; explicitly named as the plan's human-check step"

# Metrics
duration: ~10min
completed: 2026-08-28
status: complete
---

# Phase 05 Quick Task 260828-0qo: Battery Icon Size Reduction Summary

**Shrunk the bottom-left low-battery glyph to 70% of its shipped linear size (72×32px nominal → 51×22px), a live on-glass tuning correction against the real Spectra 6 panel, with the same anchor, four-part shape contract, and containment/default-off guarantees intact.**

## Performance

- **Duration:** ~10 min
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- Rescaled `BATTERY_ICON_BODY_W/H`, `NUB_W/H`, `STROKE_PX` to `round(original * 0.7)` (45/22/6/11/2), leaving `BATTERY_ICON_LEFT`/`BOTTOM`/`FILL_FRAC` byte-for-byte unchanged
- Total bounding box moved from `(64, 1504, 136, 1536)` to `(64, 1514, 115, 1536)` — same bottom-left anchor, 51×22px nominal instead of 72×32px
- Repinned all dependent assertions in `test_render.py` (Check B now derives its containment window from `render`'s own constants instead of a hand-written literal; Check C's four pixel probes recomputed; Check D's spacing-scale identity checks replaced with derivation checks plus a stroke-floor assertion and a centred-to-within-one-pixel nub check) — still exactly 46/46 checks
- Repinned `test_pipeline_e2e.py`'s battery panel-diff row/byte-column window to the new icon footprint, with failure messages now interpolating the bounds instead of restating them
- Recorded the change in `05-UI-SPEC.md` as a dated `### Revision 2 — live on-glass size correction (2026-08-28)` block, citing quick task 260828-0qo and the Phase 3 D-20/D-21/D-22/D-26/D-27 on-glass-correction precedent, with the constant table, derived bounding boxes, nub-centring statement, stroke rationale, and collision-check figures all brought in line

## Task Commits

1. **Task 1: Rescale the battery-icon constants and repin every dependent assertion** - `0939bec` (feat) - TDD RED/GREEN in a single commit (test files edited and confirmed RED first, then constants edited and confirmed GREEN, per the plan's instruction to stage both edits before committing)
2. **Task 2: Record the reduction in 05-UI-SPEC.md as a dated on-glass correction** - `56b6640` (docs)

_Note: Task 1 was worked as a genuine RED→GREEN cycle (tests edited and run failing against the still-old constants, then the constants changed and re-run passing) but committed as a single `feat` commit per this task's file scope, since `render.py` and its test files are inseparable parts of one constants-only change._

## Files Created/Modified

- `server/plane/render.py` - Five rescaled `BATTERY_ICON_*` constants, updated header comment block, updated `draw_battery_icon()` docstring (footprint 52×23px for nominal 51×22, returns `(64, 1514, 115, 1536)`)
- `server/test_render.py` - `BATTERY_ICON_BOX` now computed from `render`'s constants (Check B); Check C's four pixel probes recomputed for the new geometry; Check D rewritten to assert `round(original * 0.7)` derivation, the `STROKE_PX >= FRAME_STROKE_PX` legibility floor, and centred-to-within-one-pixel nub gaps instead of the old exact-8px-gap/spacing-scale-identity assertions
- `server/test_pipeline_e2e.py` - Battery panel-diff window repinned to rows `1514..1536` / byte columns `32..57`; the existing row-1520/byte-35 nibble probe confirmed to still land inside the new fill rectangle and left in place with a comment naming why
- `.planning/phases/05-low-battery-indicator/05-UI-SPEC.md` - Revision 2 dated correction block, updated constant table, derived bounding boxes, nub-centring statement, stroke rationale (both occurrences), and collision-check figures; `revised: 2026-08-28` added to frontmatter

## Decisions Made

- All four size constants reduced by a uniform `round(original * 0.7)`; `BATTERY_ICON_LEFT`, `BATTERY_ICON_BOTTOM`, and `BATTERY_ICON_FILL_FRAC` deliberately held byte-for-byte constant since they are position/ratio properties, not linear size
- The nub's vertical centring became asymmetric (5px gap above, 6px below) as a direct, intended consequence of the odd `BODY_H - NUB_H = 11` leftover under floor division — documented in both `render.py`'s comment and `05-UI-SPEC.md`'s Revision 2 block as expected behaviour, not a defect
- `BATTERY_ICON_STROKE_PX` now equals `FRAME_STROKE_PX` (2px) rather than exceeding it; kept as the deliberate e-ink legibility floor the 0.7 reduction stops at, rather than continuing toward an illegible 1px hairline
- 05-UI-SPEC.md's pre-existing `NUB_H` row (which read 14px, a stale figure that never actually shipped — 05-02 had already changed it to 16px for grid alignment) was corrected to name 16px, not 14px, as the value genuinely superseded by this revision

## Deviations from Plan

None - plan executed exactly as written. The one discretionary call (Task 1's commit granularity: whether to split the RED test-edit and GREEN constant-edit into two separate commits or one) was resolved by committing once, since the plan's own `<files>` list for Task 1 spans all three code files together and the task's `<done>` criterion checks `git diff --name-only` for exactly those three files as a single unit.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Code, tests, and documentation are all committed and green (9/9 test harnesses, ruff, `scripts/check-attribution.sh`)
- **Immediate next step (outside this plan's scope, per the objective's stated follow-up):** redeploy the server to production so the smaller icon reaches the real panel, then perform the plan's `<human-check>` — confirm on the physical 13.3" Spectra 6 panel that the glyph still reads unambiguously as a battery at the reduced size, and that 70% is the right amount of reduction rather than too much
- If the developer judges the new size still wrong after the redeploy, that is another tuning iteration on these same constants, not a defect in this change

---
*Phase: 05-low-battery-indicator (quick task 260828-0qo)*
*Completed: 2026-08-28*

## Self-Check: PASSED

All 5 claimed files confirmed present on disk; both task commits (`0939bec`, `56b6640`) confirmed present in git history.
