# Phase 62: Plane Screen Redesign - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md - this log preserves the alternatives considered.

**Date:** 2026-11-09
**Phase:** 62-plane-screen-redesign
**Areas discussed:** layouts, colours and landing, city splitting, landscape and firmware

---

## Layouts
Which layouts ship: A and B only / A, B and C / A only. **Chosen:** A, B and C plus a version of A with the diagonal band (free text).
How a frame picks one: per-frame setting / tied to theme / one for all. **Chosen:** per-frame setting. **Follow-up:** it lives in the Personalisation tab, as the theme does today.
Default layout: A + diagonal / A / B. **Chosen:** B (whole aircraft).

## Colours and landing
Landing vs takeoff: fixed green / second colour chosen by the owner / same colour. **Chosen:** second colour chosen by the owner.
Fate of the 18 themes: replaced by 5 pairings / old themes kept for the old layout / 5 pairings plus green. **Chosen:** replaced by 5 pairings.

## City splitting
Rule: automatic plus manual corrections / hand-written table / automatic only. **Chosen:** automatic plus manual corrections. **Follow-up (owner):** the split is 100% automatic, no manual corrections table.
Unknown destination: airline name / flight number / fixed word. **Chosen:** airline name.

## Landscape and firmware
Status screens in landscape: portrait and landscape / portrait first / portrait only. **Chosen:** portrait and landscape.
Firmware masks: regenerate without OTA / keep the look / regenerate with OTA. **Chosen:** regenerate without OTA.

## Claude's Discretion
Margins, spacing, sizes, icon redraw, crop points per aircraft type.

## Deferred Ideas
Real-panel validation; redrawing aircraft illustrations if enlarged ones are too soft.

## Planning-time decisions (2026-11-09)
- Default for unconfigured frames: B for everyone at deploy (rejected: keep the old render until a later decision).
- One line in landscape and for names of 3 letters or fewer (rejected: always two lines).
- Layout C: owner states all four layouts were mocked and validated; built as mocked.
- Defaults assumed, to confirm at plan review: stored green themes map to grey; white / black has no band.

## Execution-time decisions (2026-11-09)
- Marseille: the owner prefers two lines (MARS / EILLE, the automatic result) over forcing MAR / SEI / LLE; the splitter is not changed.
- Layout A as rendered by the code did not match the validated mock-up (the cockpit was cut off by the left edge because the nose half's width followed the cut fraction); a follow-up fix keeps the visible nose half at the mock-up width whatever the cut fraction.
- Direction word: must be displayed on every layout and format (landscape A, B and C had none in the mock-ups). Hyphens in destinations are not kept.
