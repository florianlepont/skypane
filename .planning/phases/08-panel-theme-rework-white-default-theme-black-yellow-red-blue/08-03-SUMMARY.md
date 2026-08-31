---
phase: 08-panel-theme-rework-white-default-theme-black-yellow-red-blue
plan: 03
subsystem: rendering
tags: [pillow, pt-serif, e-ink-legibility, font-provenance, render]

# Dependency graph
requires:
  - phase: 08-panel-theme-rework-white-default-theme-black-yellow-red-blue
    provides: "08-01's five-entry THEMES registry (white/black/yellow/red/sky), consumed by the per-theme rectangle-spy regression check added in Task 2"
provides:
  - "server.plane.render's six active-state font-role constants all point at PTSerif-Bold.ttf (weight 700), replacing PTSerif-Regular.ttf"
  - "PREVIOUS_LINE2_FONT grown from 16px to 20px (D-11)"
  - "_paint_text_backing() and all six of its call sites removed - no replacement box/outline/shadow (D-05)"
  - "server/assets/fonts/VENDOR.md's PT Serif entry carries a Phase 8 Supersession subsection and a dated correction to its stale Known-risk note (D-07)"
affects: [08-06]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "_RectangleSpy: monkeypatches ImageDraw.ImageDraw.rectangle, mirroring test_render.py's pre-existing _TextSpy technique, to assert no rectangle is ever filled with a state's own background index behind text"

key-files:
  created: []
  modified:
    - server/plane/render.py
    - server/test_render.py
    - server/assets/fonts/VENDOR.md

key-decisions:
  - "The real on-disk call-site count for _paint_text_backing() was six, matching this plan's own stated count, not PATTERNS.md's stale four - verified by grep before editing per the plan's own instruction"
  - "The plan's acceptance-criteria grep 'fit_text_size(PT_SERIF_BOLD is exactly 4' is stale against the real file: a pre-existing fifth call site (EMPTY_HEADING_FONT's fit_text_size call, already PT_SERIF_BOLD before this plan touched anything) makes the true count 5. Verified via git diff that exactly 4 lines changed (the two Regular->Bold pairs in draw_main_text_block()/draw_previous_text_block()) and 0 PT_SERIF_REGULAR references remain - the behavioural intent, not the stale literal, is what was checked"
  - "The rectangle-drawing spy's observed set for a plain two-flight active render is empty (draw_frame() is no longer called from the active render path since an unrelated 2026-08-28 quick task, and the backing plate is now gone too) - the new check passes vacuously per-render by construction and was NOT narrowed, since a vacuous pass is still a real regression guard against either mechanism being reintroduced"

patterns-established: []

requirements-completed: [D-05, D-06, D-07, D-11]

coverage:
  - id: D1
    description: "Every active-state text role (STATE_LABEL_FONT, TOP_TAG_FONT, MAIN_LINE1_FONT, MAIN_LINE2_FONT, PREVIOUS_LINE1_FONT, PREVIOUS_LINE2_FONT) renders in PT Serif Bold at weight 700, including both fit_text_size() call sites that read the font path directly rather than through the role tuple (D-06)"
    requirement: "D-06"
    verification:
      - kind: unit
        ref: "server/test_render.py#_pt_serif_bold_is_the_active_weight"
        status: pass
      - kind: unit
        ref: "server/test_render.py#_no_regular_weight_glyph_on_an_active_panel"
        status: pass
    human_judgment: false
  - id: D2
    description: "The text-backing-plate rectangle (_paint_text_backing()) is removed entirely, on every theme, with no replacement box/outline/shadow substituted (D-05)"
    requirement: "D-05"
    verification:
      - kind: unit
        ref: "server/test_render.py#_paint_text_backing_helper_is_gone"
        status: pass
      - kind: unit
        ref: "server/test_render.py#_no_background_filled_rectangle_behind_text_on_any_theme"
        status: pass
    human_judgment: false
  - id: D3
    description: "PREVIOUS_LINE2_FONT's size grows from 16px to 20px, floor unchanged (D-11)"
    requirement: "D-11"
    verification:
      - kind: unit
        ref: "server/test_render.py#_previous_line2_font_grew_to_20px"
        status: pass
    human_judgment: false
  - id: D4
    description: "PTSerif-Regular.ttf stays vendored with provenance intact, marked superseded in VENDOR.md mirroring the Zilla Slab/Inter precedent, with the stale Known-risk claim corrected rather than deleted (D-07)"
    requirement: "D-07"
    verification:
      - kind: other
        ref: "grep -cE '^### Supersession' server/assets/fonts/VENDOR.md -ge 2 (passed, see below)"
        status: pass
      - kind: other
        ref: "shasum -a 256 server/assets/fonts/PTSerif-Regular.ttf server/assets/fonts/PTSerif-Bold.ttf matches both digests recorded in VENDOR.md"
        status: pass
    human_judgment: false
  - id: D5
    description: "Whether the panel actually reads as legible on real Spectra 6 glass with the plate gone and the weight heavier - not resolvable by any automated check in this plan"
    verification: []
    human_judgment: true
    rationale: "Preview PNGs (/tmp/08-03-t1.png, /tmp/08-03-t2-sky.png) are screen-only, explicitly does not satisfy D-13; plan 08-06's blocking on-glass session is the gate for this."

# Metrics
duration: ~25min
completed: 2026-08-31
status: complete
---

# Phase 8 Plan 03: Bold text weight replaces the removed backing plate Summary

**Every active-state text role switched from PT Serif Regular to PT Serif Bold, the text-backing-plate rectangle deleted outright with nothing substituted, the previous card's caption grown to 20px, and the font-provenance record corrected to explain the functional (not taste-driven) reason for the switch.**

## Performance

- **Duration:** ~25min (commit span; wall time including reads/verification longer)
- **Started:** 2026-08-31T09:47:26Z (approx, following 08-02's completion)
- **Completed:** 2026-08-31T10:02:06Z (last commit, UTC)
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments

- `server/plane/render.py`'s six active-state font-role constants (`STATE_LABEL_FONT`, `TOP_TAG_FONT`, `MAIN_LINE1_FONT`, `MAIN_LINE2_FONT`, `PREVIOUS_LINE1_FONT`, `PREVIOUS_LINE2_FONT`) all repointed from `PTSerif-Regular.ttf` (weight 400) to `PTSerif-Bold.ttf` (weight 700), matching `EMPTY_HEADING_FONT`'s existing shape exactly.
- The two `fit_text_size()` call-site pairs inside `draw_main_text_block()` and `draw_previous_text_block()` — which read `PT_SERIF_REGULAR` directly rather than through the role tuple — were also repointed at `PT_SERIF_BOLD`. This is the half of the change a tuple-only edit would silently miss; a new behavioural check (monkeypatching `render._font`, the seam both direct role lookups and `fit_text_size()` itself call through) proves no `PTSerif-Regular.ttf` glyph is ever requested while rendering a full two-flight active panel, in either state.
- `PREVIOUS_LINE2_FONT`'s size grew from 16px to 20px (D-11); its overflow floor (`PREVIOUS_LINE2_MIN_SIZE = 12`) is unchanged.
- `_paint_text_backing()` and all six of its call sites (two each in `draw_top_labels()`, `draw_main_text_block()`, `draw_previous_text_block()`) were deleted outright — nothing substituted: no outline, no `stroke_width`/`stroke_fill`, no offset shadow, no replacement rectangle, no per-theme conditional. A removal-rationale comment, written in prose (so it cannot match a live-reference grep), sits where the helper used to be, recording why it existed and why it's gone. `bg_idx` stays on all three drawing functions' signatures and call sites (PATTERNS.md's instruction), each now carrying a one-line "deliberately retained" docstring note.
- `server/plane/render.py`'s module docstring corrected on two stale claims: the D-27 paragraph now states Phase 8's Bold switch and its functional (not taste-driven) reason, citing the real Phase 7 on-glass finding that Regular was already confirmed legible; the CFG-01 paragraph now states the registry holds five entries, not one.
- `server/test_render.py` grew 78→82 checks: the active-weight assertion inverted (Bold, not Regular) with `EMPTY_BODY_FONT` pinned as the one remaining active Regular reference; a `PREVIOUS_LINE2_FONT` size/floor check; a behavioural no-Regular-glyph check; a helper-is-gone check; and a `_RectangleSpy`-driven check (new class, mirrors `_TextSpy`) proving no rectangle is ever filled with a state's own background index, looped across every registered theme (`device_config.THEME_IDS`) and both active states.
- `server/assets/fonts/VENDOR.md`'s PT Serif entry gained a `### Supersession (Phase 8 — D-06/D-07)` subsection (mirroring the Zilla Slab entry's own shape, but distinguishing this as a *functional* supersession rather than a taste change) and a dated correction inside the existing `### Known risk` subsection, stating what Phase 7's real on-glass session actually found (Regular legible at every role) and why Phase 8 changed the weight regardless. Original text kept intact above the correction. Both font files, both digests, the commit SHA and the licence text are all byte-unchanged.

## Task Commits

Each task was committed atomically:

1. **Task 1: Switch every active-state text role to PT Serif Bold and grow the previous card's caption to 20px** - `25b9997` (feat)
2. **Task 2: Remove the solid text backing-plate rectangle entirely, on every theme** - `e45dd4b` (feat)
3. **Task 3: Record the PT Serif Regular supersession in VENDOR.md and correct its now-stale risk note** - `5acc5a8` (docs)

_No separate plan-metadata docs commit yet — pending state/roadmap update below._

## Files Created/Modified

- `server/plane/render.py` - six role constants repointed to Bold (weight 700); `PREVIOUS_LINE2_FONT` grown to 20px; the four `fit_text_size()` call sites in `draw_main_text_block()`/`draw_previous_text_block()` repointed to `PT_SERIF_BOLD`; `_paint_text_backing()` and its six call sites deleted, replaced by a prose removal-rationale comment; `bg_idx` parameters marked deliberately retained; module docstring's D-27/CFG-01 paragraphs corrected
- `server/test_render.py` - active-weight check inverted (Bold) plus `EMPTY_BODY_FONT` pin; new `PREVIOUS_LINE2_FONT` size/floor check; new behavioural no-Regular-glyph check (spies on `render._font`); new `_paint_text_backing`-is-gone check; new `_RectangleSpy` class + per-theme/per-state no-background-filled-rectangle check; `EXPECTED_CHECK_COUNT` 78→82
- `server/assets/fonts/VENDOR.md` - new Supersession subsection under the PT Serif entry; dated correction inside the existing Known-risk subsection; no font file, digest, commit SHA or licence text touched

## Decisions Made

- **Real on-disk `EXPECTED_CHECK_COUNT` baseline vs. plan's cited value:** the plan's own read_first correctly pointed at the on-disk value of 78 (matching 08-01-SUMMARY.md's own recorded 76→78 growth) rather than assuming a stale literal — confirmed via grep before editing. Task 1 raised it to 80 (+2: the behavioural no-Regular check and the `PREVIOUS_LINE2_FONT` size/floor check); Task 2 raised it to 82 (+2, exactly as the plan specified: helper-is-gone + rectangle-spy checks).
- **Real backing-plate call-site count vs. PATTERNS.md's four vs. this plan's six:** grepped before editing (`grep -c '_paint_text_backing(draw'` → 6, plus 1 for the definition itself). The real count matched this plan's own stated six, not PATTERNS.md's stale four (two in `draw_top_labels()`, two in `draw_main_text_block()`, two in `draw_previous_text_block()`). All six removed in one commit alongside the definition.
- **Rectangle-drawing calls captured by Task 2's spy (`_RectangleSpy`):** for a plain two-flight active render (no `battery_low`, no `source_fault`), the observed set is **empty** — zero rectangle calls at all. This is because `draw_frame()` (the panel's decorative outline) was already stopped being called from the active render path by an unrelated 2026-08-28 quick task (260828-k5r, recorded in a pre-existing comment at `_build_active_canvas()`), and the text-backing-plate is now also gone. The assertion (`no captured rectangle is filled with the state's own background index`) was **not narrowed** to text-bbox-overlapping rectangles as the plan's fallback path allowed — a vacuous per-render pass is still a genuine regression guard: if either `draw_frame()` were ever re-enabled with a `bg_idx` fill, or a backing plate were reintroduced, this check would start failing immediately. The check loops every registered theme (`device_config.THEME_IDS`, from 08-01: white/black/yellow/red/sky) and both active states.
- **Observed failure message from Task 1's deliberate call-site revert** (acceptance-criteria demonstration, not committed): reverting `draw_main_text_block()`'s second `fit_text_size()` call site from `PT_SERIF_BOLD` back to `PT_SERIF_REGULAR` and re-running the suite produced: `FAIL no PTSerif-Regular.ttf glyph is drawn anywhere on an active-state panel, in either state (D-06) - behavioural, catches a half-applied fit_text_size() call site - PTSerif-Regular.ttf was requested 2 time(s) on an active-state panel - expected zero (D-06): [...]` at `79/80 checks pass`. The change was then restored and the suite re-confirmed green at `80/80` before committing.
- **`fit_text_size(PT_SERIF_BOLD` acceptance-criterion imprecision (informational, no code change needed):** the plan's own literal acceptance check states `grep -c 'fit_text_size(PT_SERIF_BOLD' server/plane/render.py` should be exactly 4. The real on-disk count is **5** — a pre-existing fifth call site (`_build_empty_canvas()`'s `fit_text_size(PT_SERIF_BOLD, EMPTY_HEADING_FONT[1], ...)`, which already used Bold before this plan touched anything, since the empty-state heading was always Bold) was not accounted for by the plan author. Verified the real behavioural intent instead: `git diff` confirms exactly 4 lines changed (the Regular→Bold pairs in `draw_main_text_block()`/`draw_previous_text_block()`), and `grep -c 'fit_text_size(PT_SERIF_REGULAR'` is 0.
- **Two preview PNGs written** (Task 1: `/tmp/08-03-t1.png`, departing state, default White theme; Task 2: `/tmp/08-03-t2-sky.png`, departing state, Sky theme) — both confirm by eye that flight text is visibly heavier (Bold) and the previous card's caption is larger (20px), and the Sky-theme render confirms no rectangular plate remains behind any text run. **Both are monitor checks only and explicitly do not discharge D-13** — that gate is plan 08-06's blocking on-glass verification session.

## Deviations from Plan

None — plan executed exactly as written. The three items above (acceptance-criterion count imprecision, vacuous-but-unnarrowed rectangle assertion, empty spy-observed set) are documented findings the plan itself anticipated and instructed to record, not unplanned deviations from Rules 1-4.

## Issues Encountered

None beyond the documented findings above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Every active-state text role is now PT Serif Bold and the backing plate is gone, on every theme (white/black/yellow/red/sky) - this is the load-bearing rendering change plan 08-06's blocking on-glass session must verify against real Spectra 6 ink.
- `server/assets/fonts/VENDOR.md` now accurately documents which weight is active and why, closing the D-07 provenance gap.
- Full suite: 14/15 canonical harnesses green (`scripts/run-all-tests.sh`, 91% coverage). The sole failure, `server/test_poll_loop.py`'s pinned `panel.bin` digest check, is the known pre-existing macOS-local-render-vs-Linux-CI-pinned-digest mismatch flagged in this plan's own execution context - confirmed unrelated (re-pinning that digest is explicitly plan 08-05's job).
- None of the rendering changes in this plan have been seen on real Spectra 6 ink yet - screen-confirmed only via the two preview PNGs above, same open item every prior Phase 8 plan has recorded. Plan 08-06's blocking on-glass session is where that check happens.

---
*Phase: 08-panel-theme-rework-white-default-theme-black-yellow-red-blue*
*Completed: 2026-08-31*
