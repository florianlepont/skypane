---
phase: 03-visual-polish-on-real-glass
plan: 01
subsystem: ui
tags: [pillow, fonts, typography, zilla-slab, ofl, palette]

# Dependency graph
requires:
  - phase: 02-plane-view-end-to-end-slice
    provides: render.py's zone-stacking layout (state label, silhouette, flight number, route/airline lines, bottom tag) and panel_format.py's palette/wire-format bridge
provides:
  - Vendored Zilla Slab SemiBold/Bold (SIL OFL 1.1) with pinned-commit provenance, replacing Inter across the entire active render path
  - Four typographic role constants (LABEL_FONT/CAPTION_FONT/DESTINATION_FONT/FLIGHT_NUMBER_FONT) expressing D-16's co-equal flight-number/destination hero pair
  - panel_format.padded_palette() as the single shared palette-padding function
  - PALETTE_RGB updated to D-13's interim community-estimate panel-RGB triples (Yellow/Red/Blue/Green)
affects: [03-02-mood-background, 03-03-illustration-livery, 03-04-hardware-calibration]

# Tech tracking
tech-stack:
  added: ["Zilla Slab (SIL OFL 1.1, Mozilla Foundation) - static SemiBold/Bold TTFs"]
  patterns:
    - "Font role constants as a declared (path, size, weight) contract - call sites select a role, never a bare font path or size"
    - "padded_palette() as the single source of the 768-int Pillow palette, shared by new_canvas() and (from 03-02) any quantization-built canvas"

key-files:
  created:
    - server/assets/fonts/ZillaSlab-SemiBold.ttf
    - server/assets/fonts/ZillaSlab-Bold.ttf
    - server/assets/fonts/ZillaSlab-OFL.txt
  modified:
    - server/assets/fonts/VENDOR.md
    - server/panel_format.py
    - server/plane/render.py
    - server/test_render.py

key-decisions:
  - "Resolved google/fonts commit f473a26ceba660d85cf223ff121dea1fe91cfcb6 (most recent commit touching ofl/zillaslab at retrieval time 2026-08-26) as the pinned download source for both TTFs and OFL.txt - never a branch ref (T-03-01-01)"
  - "D-13 interim panel-RGB triples applied to PALETTE_RGB: Yellow (240,224,80), Red (160,32,32), Blue (80,128,184), Green (96,128,80) - Black/White unchanged, no palette index or wire nibble touched"
  - "D-16's co-equal hero pair resolved as FLIGHT_NUMBER_FONT 72px Bold vs DESTINATION_FONT 64px SemiBold (8px gap, both heavy cuts); CAPTION_FONT 40px SemiBold is strictly subordinate to both"

patterns-established:
  - "Font-role contract pattern: exactly four named (path, size, weight) tuples gate every glyph on the panel - no call site may reference a bare font path or hardcode a size"

requirements-completed: [PLANE-01, PLANE-02]

coverage:
  - id: D1
    description: "Zilla Slab SemiBold/Bold vendored from a pinned google/fonts commit with per-file sha256 digests and full OFL 1.1 provenance in VENDOR.md; no Regular/Light/Medium/italic cut present"
    requirement: "PLANE-01"
    verification:
      - kind: unit
        ref: "server/test_render.py - 'the four typographic role constants exist with exactly sizes 36/40/64/72 and weights 700/600/600/700, all pointing at a vendored Zilla Slab file'"
        status: pass
      - kind: other
        ref: "ls server/assets/fonts/ (exact 6-file listing) + grep for 40-hex SHA, sha256 lines, SIL OFL 1.1, 'no longer referenced' - all confirmed during execution"
        status: pass
    human_judgment: false
  - id: D2
    description: "render.py exposes exactly four typographic roles (36/40/64/72px, 2 weights) and no active code path references Inter; BODY_FONT/HEADING_FONT removed"
    requirement: "PLANE-01"
    verification:
      - kind: unit
        ref: "server/test_render.py - role-constant, LABEL_TRACKING_PX, and BODY_FONT/HEADING_FONT-removal checks"
        status: pass
      - kind: other
        ref: "grep -v '^ *#' server/plane/render.py | grep -c 'Inter-' == 0"
        status: pass
    human_judgment: false
  - id: D3
    description: "Flight number and destination/origin read as a co-equal hero pair (8px size gap, both heavy cuts); airline line is strictly subordinate (D-16)"
    requirement: "PLANE-02"
    verification:
      - kind: unit
        ref: "server/test_render.py - 'the hero pair is co-equal: FLIGHT_NUMBER_FONT - DESTINATION_FONT size gap is 8px...'"
        status: pass
    human_judgment: false
  - id: D4
    description: "A genuinely long destination/origin city name (Santiago de Compostela–Rosalía de Castro) and a long airline name both shrink via fit_text_size() without breaching the safe box - automated half of D-04; on-glass half deferred to 03-04"
    requirement: "PLANE-01"
    verification:
      - kind: unit
        ref: "server/test_render.py - 'a genuinely long destination/origin city name (Santiago de Compostela) shrinks via fit_text_size()...'"
        status: pass
    human_judgment: false
  - id: D5
    description: "PALETTE_RGB carries D-13's interim muted-ink triples while every palette index and wire nibble is provably unchanged"
    verification:
      - kind: unit
        ref: "server/test_render.py full suite (32/32) + server/test_pipeline_e2e.py (5/5) + server/test_runway_config.py (14/14), all green with no index/nibble regression"
        status: pass
      - kind: other
        ref: "pf.INDEX_TO_NIBBLE == {0:0x0,1:0x1,2:0x2,3:0x3,4:0x5,5:0x6} asserted directly"
        status: pass
    human_judgment: false
  - id: D6
    description: "Visual sanity check: developing/empty state preview PNGs show the new hierarchy and font correctly"
    verification: []
    human_judgment: true
    rationale: "Preview colours are explicitly nominal render-internal RGB triples (D-P2-03), not colour-accurate - genuine on-glass legibility judgment is a 03-04 checkpoint, not this plan's job; this plan's own preview inspection (visually confirmed during execution) is a sanity check, not a substitute for the hardware checkpoint."

duration: 20min
completed: 2026-08-26
status: complete
---

# Phase 3 Plan 1: Zilla Slab Typography & D-13 Interim Palette Summary

**Vendored Zilla Slab (SIL OFL 1.1) from a pinned google/fonts commit, replaced Inter across the entire render pipeline with four declared typographic roles implementing D-16's co-equal flight-number/destination hero pair, and moved PALETTE_RGB onto D-13's interim muted-ink approximation.**

## Performance

- **Duration:** 20 min
- **Started:** 2026-08-26T12:21:00Z
- **Completed:** 2026-08-26T12:41:57Z
- **Tasks:** 2 completed (Task 2 followed RED/GREEN TDD)
- **Files modified:** 7 (3 new font assets, 4 modified)

## Accomplishments

- Zilla Slab SemiBold and Bold vendored from immutable commit `f473a26ceba660d85cf223ff121dea1fe91cfcb6` of `google/fonts`, with per-file sha256 digests and full SIL OFL 1.1 provenance recorded in `server/assets/fonts/VENDOR.md`; Inter marked superseded (retained, not deleted)
- `render.py`'s three-role Inter scale (`LABEL_FONT`/`BODY_FONT`/`HEADING_FONT`) replaced by four Zilla Slab roles (`LABEL_FONT` 36px Bold, `CAPTION_FONT` 40px SemiBold, `DESTINATION_FONT` 64px SemiBold, `FLIGHT_NUMBER_FONT` 72px Bold) — an 8px size gap between the two hero elements, both in heavy cuts, with the airline caption strictly subordinate
- `LABEL_TRACKING_PX` widened from 4 to 6 (D-15's wide letter-spacing instruction)
- `PALETTE_RGB` indices 2/3/4/5 moved to D-13's interim community-estimate triples; `padded_palette()` extracted as the single shared palette-padding function `new_canvas()` now calls
- `test_render.py` extended from 25 to 32 checks pinning every new contract element (role constants, tracking, retired-role removal, hero-pair gap, long-name shrink path, determinism) — RED confirmed against pre-change `render.py`, GREEN confirmed after

## Task Commits

Each task was committed atomically:

1. **Task 1: Vendor Zilla Slab and apply D-13 palette** - `c9bbf0d` (feat)
2. **Task 2 RED: failing tests for the role swap** - `57031ac` (test)
2. **Task 2 GREEN: implement the role swap** - `715287a` (feat)

## Files Created/Modified

- `server/assets/fonts/ZillaSlab-SemiBold.ttf` - vendored static SemiBold (600) cut
- `server/assets/fonts/ZillaSlab-Bold.ttf` - vendored static Bold (700) cut
- `server/assets/fonts/ZillaSlab-OFL.txt` - SIL OFL 1.1 licence text
- `server/assets/fonts/VENDOR.md` - Zilla Slab provenance entry + Inter supersession note
- `server/panel_format.py` - PALETTE_RGB D-13 interim triples, new `padded_palette()`
- `server/plane/render.py` - four typographic role constants, all call sites re-pointed
- `server/test_render.py` - 7 new checks, `EXPECTED_CHECK_COUNT` 25 -> 32

## Font Digests & Measured Line Heights

Recorded for 03-02's quiet-zone geometry, which depends on these exact line heights:

| Role | Font path | Size | Weight | Ascent | Descent | Line height |
|---|---|---|---|---|---|---|
| Label | ZillaSlab-Bold.ttf | 36px | 700 | 34 | 10 | 44px |
| Caption | ZillaSlab-SemiBold.ttf | 40px | 600 | 38 | 11 | 49px |
| Destination/Origin | ZillaSlab-SemiBold.ttf | 64px | 600 | 61 | 17 | 78px |
| Flight Number | ZillaSlab-Bold.ttf | 72px | 700 | 68 | 19 | 87px |

- Resolved pinned commit: `f473a26ceba660d85cf223ff121dea1fe91cfcb6`
- `ZillaSlab-SemiBold.ttf` sha256: `aafcb295b88d520357db1ecf9a1c3167055e87e9ddf5f63e560cbd139ec2805e`
- `ZillaSlab-Bold.ttf` sha256: `4ec3a04a4eef37074b42ef542e4d874e13646668cfe65256e0bf100441cf8719`

## Decisions Made

- Resolved `google/fonts` commit via `GET /repos/google/fonts/commits?path=ofl/zillaslab&per_page=1` rather than trusting the "release 1.501" text in `03-UI-SPEC.md` — the commits API gives an immutable SHA directly, which is what T-03-01-01's mitigation requires; the UI-SPEC's release-number mention was informational, not itself a pinnable ref.
- Chose commit-SHA pinning (per `03-01-PLAN.md`'s explicit instruction) over any tagged-release pinning scheme, since `google/fonts` doesn't tag per-family releases the way `rsms/inter` does.
- Kept the flight-number caption's fit through `fit_text_size()` even though ICAO callsigns rarely need shrinking, per the plan's explicit "defensively wrapped" instruction — this makes all three text-hero elements (flight number, destination, airline) go through the same shrink mechanism.

## Deviations from Plan

None - plan executed exactly as written. The TDD task (Task 2) followed the RED -> GREEN cycle: extended `test_render.py` first (confirmed 4 checks failed against the pre-change `render.py`, all traceable to the not-yet-implemented font swap), then implemented `render.py`'s changes to turn all 32 checks green. No REFACTOR commit was needed — the GREEN implementation required no follow-up cleanup.

One planning-time correction (not a deviation from an instruction, but worth recording): the long-name stress test's route dict places the long city name on `origin_city`, which `enrich.city_for_state()` only surfaces for the `arriving` state (not `departing`) — matching the plan's own acceptance-criteria Python snippet, which renders with `state='arriving'`. The task's prose description said "render departing" informally but the acceptance-criteria code block was authoritative and unambiguous; the test was written to match the acceptance criteria exactly.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Font vendoring and typography groundwork is complete and tested; `03-02` (mood background) can build directly on `padded_palette()` and the now-final `PALETTE_RGB` D-13 interim triples.
- The measured line heights above are exactly what `03-02`'s quiet-zone rectangle sizing needs — no re-derivation required.
- No blockers. `03-04`'s hardware calibration pass still owns the actual on-glass verification of both D-13's interim RGB values and Zilla Slab's dithered-background legibility (flagged as a fresh, not-pre-verified checkpoint in `03-UI-SPEC.md`).

---
*Phase: 03-visual-polish-on-real-glass*
*Completed: 2026-08-26*

## Self-Check: PASSED

All 7 claimed files found on disk (`server/assets/fonts/ZillaSlab-SemiBold.ttf`, `ZillaSlab-Bold.ttf`, `ZillaSlab-OFL.txt`, `VENDOR.md`, `server/panel_format.py`, `server/plane/render.py`, `server/test_render.py`). All 3 claimed commit hashes (`c9bbf0d`, `57031ac`, `715287a`) found in git log.
