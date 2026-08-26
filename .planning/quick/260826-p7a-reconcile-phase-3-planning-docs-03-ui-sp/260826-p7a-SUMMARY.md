---
task: 260826-p7a
phase: 03-visual-polish-on-real-glass
type: quick
subsystem: planning-docs
tags: [documentation, reconciliation, phase-3, ui-spec]
dependency-graph:
  requires: []
  provides:
    - .planning/phases/03-visual-polish-on-real-glass/03-UI-SPEC.md (Revision 4)
    - .planning/phases/03-visual-polish-on-real-glass/03-RESEARCH.md (Reconciliation Addendum)
    - .planning/phases/03-visual-polish-on-real-glass/03-03-PLAN.md (reconciled)
    - .planning/phases/03-visual-polish-on-real-glass/03-04-PLAN.md (reconciled)
  affects:
    - Wave 4 execution of 03-04-PLAN.md (on-glass verification battery)
tech-stack:
  added: []
  patterns:
    - "Documentation-reconciliation via superseding annotation (append/mark, never delete) — same discipline 03-CONTEXT.md's own addenda already use"
key-files:
  created: []
  modified:
    - .planning/phases/03-visual-polish-on-real-glass/03-UI-SPEC.md
    - .planning/phases/03-visual-polish-on-real-glass/03-RESEARCH.md
    - .planning/phases/03-visual-polish-on-real-glass/03-03-PLAN.md
    - .planning/phases/03-visual-polish-on-real-glass/03-04-PLAN.md
decisions: []
metrics:
  duration: ~45min
  completed: 2026-08-26
status: complete
---

# Reconcile Phase 3 planning docs with shipped design Summary

Rewrote four stale Phase 3 planning documents to match the two-flight poster layout already implemented, tested (26/6/5 checks passing), and committed on `main` (commits 7663cb2, e52602e, c20a8eb, f8db99a) — none of `server/`, `firmware/`, `hardware/`, or `deploy/` was touched.

## What Changed

### 03-UI-SPEC.md — rewritten wholesale as Revision 4

Replaced the entire document with a record of the shipped design: PT Serif Regular typography (not Zilla Slab), a flat single-color background per state (not a dithered mood gradient), a thin ivory frame, and a current-plus-previous two-flight composition (not a single mirrored silhouette). Every geometry/font/palette number is cited verbatim from `server/plane/render.py`'s live constants (verified by importing the module and asserting each value's string form appears in the document). New sections: Revision 4 note, Design System, Canvas and Geometry, Layout and Composition, Typography, Colour, Copywriting Contract, Rendering Rules, a Supersession Table (11 rows: what Revision 3 specified vs. what shipped), six numbered Open Items for the Wave 4 checkpoint, and a reset Checker Sign-Off.

Key facts recorded: PT Serif Regular reintroduces the hairline-legibility risk the project has now walked back and forth across three times (Inter → Zilla Slab → PT Serif Bold → PT Serif Regular); nose-left is now permanent in both states (D-24, mirroring dropped after a real mirrored illustration looked "bizarre"); the palette contract is a simple legality-plus-dominance assertion, not spatially scoped; Blue `(110,180,225)`/Green `(140,195,130)` are developer-confirmed (D-21), Yellow/Red remain interim D-13 estimates; line 2 is airline-name-only (not `{airline} · {aircraft_type}`) because real per-flight aircraft type is deferred to Phase 3.1.

### 03-RESEARCH.md — appended, nothing deleted (0 line deletions confirmed via `git diff --numstat`)

Added a dated "Reconciliation Addendum" section before `## Metadata`. It records two overturned headline recommendations — the Zilla Slab font pick (D-20 rejected it after a real preview; PT Serif Regular, D-27, was chosen instead and reintroduces the exact hairline risk Zilla Slab was engineered to avoid) and the dithered mood-background recipe (D-21 reverted it to a flat fill after seeing the speckled result; `build_mood_background()` and its constants were removed from `dither.py` entirely) — plus a corrected Validation Architecture reconciliation noting the shipped harness counts are 26/6/5, not the document's original `EXPECTED_CHECK_COUNT = 25` baseline, and that `server/test_illustrations.py` was never created despite `03-03-PLAN.md` calling for it. A separate "survived unchanged" list keeps the addendum from reading as a blanket invalidation (full 6-color dithering mechanics, the no-remap rule, the corrected alpha-hard-threshold requirement, the stroke-width prohibition, the non-background-index counting technique, and the Phase-2-legibility-finding-does-not-transfer rule all remain load-bearing).

### 03-03-PLAN.md — reconciled with partial execution

Added a Reconciliation Note recording per-task status: Task 1 shipped (`illustrations.py`/`HANDOFF.md` in commit `21c4ed6`) but its test harness (`server/test_illustrations.py`) was never created; Task 2's hand-off completed (eight PNGs vendored, `--validate` passes, Transavia France added later in `e52602e`) but its provenance record (`server/assets/icons/illustrations/VENDOR.md`) was never created; Task 3 was superseded by implementation — the shipped code has no `draw_dithered_illustration()`/`_fit_illustration_size()`, the equivalent landed as `draw_illustration()` in commit `f8db99a`, driven by the two-flight layout. Every truth/decision/behavior bullet/action step/success criterion asserting nose-direction-changes-by-state was marked `**[SUPERSEDED by D-24]**` inline rather than deleted (15 "supersed" occurrences, 9 "nose-left" mentions). The threat register's T-03-03-07 disposition was adjusted to reflect that a reversed source file now renders reversed identically in both states (a cosmetic asset defect) rather than backwards in only one (a state-specific bug).

### 03-04-PLAN.md — verification battery re-scoped to the shipped design

Task 1: the `02-UI-SPEC.md` colour addendum now targets `_assert_legal_palette()`'s legality-plus-dominance contract (not a spatially-scoped exception that doesn't exist) and points at `03-UI-SPEC.md` Revision 4; the calibration-preview criterion corrected from "three PNGs" to the shipped single `palette-swatches.png`. Task 2's eight-step battery (A-H) rewritten: Step B retargets PT Serif Regular's hairline risk as the headline item with `PTSerif-Bold.ttf` named as the documented fallback, and asks separately about the previous card's 16px/12px-floor text (the smallest ever rendered); Step C is a new bezel-clipping check (the frame sits inside the old 64px safe band, unverified against real hardware per `render.py`'s own docstring); Step D rewrites the state-distinction question around colour+label-only cues now that nose direction isn't one; Steps E/F are new (two-flight composition legibility, D-23 wordmark detail at both illustration scales); the tracking and quiet-zone-plate questions were deleted (neither mechanism exists). Task 3's tuning scope narrowed to Yellow/Red only — Blue/Green are D-21-locked and must not be re-tuned; all references to `MOOD_LIGHT_TINT_MIX`/`MOOD_NOISE_AMPLITUDE`/`QUIET_ZONE_PAD` were corrected to state they were removed from the shipped code. The context block's dead `03-03-SUMMARY.md` reference was replaced with a pointer to `03-03-PLAN.md`'s own reconciliation note.

## Two Open Documentation Gaps (carried forward to STATE.md)

These were confirmed absent by direct filesystem check during planning and remain open — they are not fixed by this reconciliation, only recorded:

1. **`server/test_illustrations.py`** — the test harness `03-03-PLAN.md` Task 1 specified was never created.
2. **`server/assets/icons/illustrations/VENDOR.md`** — the per-file provenance record (sha256 digests, airline, aircraft type, generation date/tool) `03-03-PLAN.md` Task 2 specified was never created.

Both are now explicitly named in `03-03-PLAN.md`'s Reconciliation Note and carried into `03-04-PLAN.md`'s Task 3 "carry the open items forward" list, so Wave 4's execution (or a future quick task) can close them rather than let them die silently in a stale plan file.

## Deviations from Plan

None — plan executed exactly as written. All three tasks' automated `<verify>` commands and acceptance criteria passed as specified; `git status --porcelain server/ firmware/ hardware/ deploy/` remained empty throughout.

## Self-Check

- `.planning/phases/03-visual-polish-on-real-glass/03-UI-SPEC.md` — FOUND, Revision 4 content confirmed via live import verification against `server/plane/render.py`.
- `.planning/phases/03-visual-polish-on-real-glass/03-RESEARCH.md` — FOUND, addendum appended after `## Sources`, before `## Metadata`; 0 deletions confirmed via `git diff --numstat`.
- `.planning/phases/03-visual-polish-on-real-glass/03-03-PLAN.md` — FOUND, reconciliation note and inline supersession markers present.
- `.planning/phases/03-visual-polish-on-real-glass/03-04-PLAN.md` — FOUND, re-scoped battery (Steps A-H) and corrected tuning scope present.
- Commit `4faf21a` (03-UI-SPEC.md Revision 4) — FOUND in `git log`.
- Commit `59d16de` (03-RESEARCH.md addendum) — FOUND in `git log`.
- Commit `818e3ba` (03-03/03-04-PLAN.md reconciliation) — FOUND in `git log`.
- `server/test_render.py` (26/26), `server/test_dither.py` (6/6), `server/test_poll_loop.py` (5/5) — all pass unchanged, confirming zero disturbance to the render pipeline this reconciliation documents.

## Self-Check: PASSED

## Threat Flags

None — this is a documentation-only reconciliation with no new network surface, dependency, or executable artifact.
