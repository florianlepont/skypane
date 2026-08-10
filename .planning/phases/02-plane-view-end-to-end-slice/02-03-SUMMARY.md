---
phase: 02-plane-view-end-to-end-slice
plan: 03
subsystem: ui
tags: [pillow, e-ink, python, image-processing, cc0, silhouette]

requires:
  - phase: 02-plane-view-end-to-end-slice
    plan: 02
    provides: server/plane/render.py's STATE_BACKGROUND/STATE_INK dicts, draw_state_label(), load_binary_mask(), build_canvas(), the zone-stacking constants reserving zone 3's vertical footprint (FLIGHT_NUMBER_TOP_Y), and server/assets/icons/VENDOR.md's existing Lucide-entry structure
provides:
  - server/assets/icons/aircraft-silhouette.svg / .png — vendored CC0 (freesvg.org/OpenClipart SVG ID 178507) aircraft silhouette, pre-rasterized and cleaned to a flat solid 1800x830 mask, with full VENDOR.md provenance including the source nose orientation ("left")
  - server/plane/render.py's paste_mask() — the single shared mask-compositing helper (load -> resize -> hard-threshold -> optional mirror -> paste), now used by both the state-label glyph and the silhouette
  - server/plane/render.py's draw_silhouette() and the public SILHOUETTE_* geometry constants (SILHOUETTE_PATH, SILHOUETTE_TARGET_W, SILHOUETTE_MAX_H, SILHOUETTE_ZONE_TOP, SILHOUETTE_ZONE_HEIGHT, SILHOUETTE_SOURCE_NOSE) — the panel's primary visual anchor, mirrored nose-right/nose-left by state
  - A render-time guard rail in _build_active_canvas asserting the composited canvas is still exactly two palette indices
  - server/test_render.py — extended to 19/19 green checks covering silhouette presence, state-mirroring, safe-box/no-overlap geometry, and empty-state absence
affects: [02-04-enrichment-route, 02-05-deploy-hardware-verify]

tech-stack:
  added: []
  patterns:
    - "Flood-fill silhouette extraction from detailed line-art: dilate the traced ink to close hairline gaps, flood-fill the true exterior background from multiple canvas-edge seed points, treat every pixel the flood fill didn't reach (both original ink and now-enclosed interior detail) as the solid shape, erode back to restore the true boundary - turns a multi-subpath evenodd-fill clipart SVG into one clean flat silhouette without a vector editor"
    - "paste_mask(canvas, mask_path, box, fill_index, mirror=False) as the single shared call site for Pattern 2's full resize-threshold-mirror-paste ordering, so no future caller can accidentally skip the hard-threshold step"
    - "Read recorded source-asset orientation (SILHOUETTE_SOURCE_NOSE) from documentation rather than hardcoding a per-state flip boolean, so a future re-rasterization that changes orientation fails legibly instead of silently mirroring wrong"

key-files:
  created:
    - server/assets/icons/aircraft-silhouette.svg
    - server/assets/icons/aircraft-silhouette.png
  modified:
    - server/assets/icons/VENDOR.md
    - server/plane/render.py
    - server/test_render.py

key-decisions:
  - "The source SVG (freesvg.org/OpenClipart 178507) is a detailed 3/4-aerial-view line-art drawing (a single evenodd-fill compound path with outline strokes, window rows, and panel-line shading), not already a flat silhouette - UI-SPEC's own executor note anticipated this. Built a from-scratch morphological cleanup pipeline (Pillow only, no numpy/scipy in the venv) rather than hand-editing the vector art, since no vector editor is available in this environment: dilate ink to close two hairline outline gaps (a fuselage cheatline channel and a tail-assembly gap) that otherwise let a background flood-fill leak into the aircraft's interior, flood-fill the true background from multiple edge seeds, fill everything unreached as solid, erode back, light Gaussian-blur-then-rethreshold smoothing pass"
  - "Sized the silhouette by fitting within both the ~900px width cap and the existing 260px height cap (SILHOUETTE_MAX_H, unchanged from 02-02's zone-3 reservation) while preserving the vendored asset's own ~2.22:1 aspect ratio, rather than assuming width is always the binding constraint - the height cap binds first for this asset, producing a ~577x260 silhouette comfortably under the 900px ceiling. This keeps 02-02's already-reserved zone-3 footprint (and FLIGHT_NUMBER_TOP_Y=1028) completely unchanged, matching the plan's 'without ever moving what this plan already renders' contract"
  - "Extracted paste_mask() as the one shared compositing call site and refactored draw_state_label()'s glyph paste to use it too (rather than adding a parallel silhouette-only path), keeping exactly one Image.point() threshold call site in the module (inside load_binary_mask()) for the regression guard"
  - "Renamed 02-02's private zone-3 geometry constants (_ZONE1_STATE_LABEL_HEIGHT, _ZONE3_SILHOUETTE_MAX_HEIGHT, _ZONE3_HEIGHT) to public SILHOUETTE_*/ZONE1_* names so test_render.py's assertions reference the renderer's own numbers instead of re-deriving them - values and FLIGHT_NUMBER_TOP_Y (1028) are unchanged, this is a pure rename"
  - "Deferred requirements.mark-complete for PLANE-01/PLANE-02 - same rationale as 02-01/02-02: this plan supplies the poster's visual centrepiece, but the requirement text also needs D-02 enrichment (route/airline, 02-04) and hardware-verified White-on-saturated legibility (02-05's QA checkpoint) before the requirement text is fully true"

patterns-established:
  - "SILHOUETTE_SOURCE_NOSE is the single source of truth for the vendored asset's orientation - draw_silhouette() computes the mirror boolean by comparing each state's required nose direction against this constant, so the mirroring logic itself never hardcodes which state gets flipped"

requirements-completed: []

coverage:
  - id: D1
    description: "Vendored freesvg.org/OpenClipart SVG ID 178507 (CC0, confirmed via the page's publicdomain/zero/1.0 licence meta tag) with full provenance in VENDOR.md, including the source nose orientation and every cleanup step performed to turn the line-art source into a flat solid mask"
    requirement: "PLANE-01, PLANE-02"
    verification:
      - kind: unit
        ref: "server/test_render.py's PNG-dimension/mode acceptance check plus manual VENDOR.md content review (178507, CC0, retrieval date, Local modifications section, source nose orientation note all present)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Silhouette centrepiece composited into both active states: substantial White fill inside the reserved zone-3 band (proving it isn't a no-op paste), mirrored nose-right/nose-left by state via a foreground-shape-only comparison (so a background colour swap alone can't satisfy the check), bounding box inside the 1072x1472 safe box with no overlap into the state-label or flight-number caption zones, exactly two palette indices preserved after compositing, and never drawn for the Empty state (verified by spying on draw_silhouette())"
    requirement: "PLANE-01, PLANE-02"
    verification:
      - kind: unit
        ref: "server/test_render.py (19/19 checks)"
        status: pass
    human_judgment: true
    rationale: "White-on-saturated-Blue/Green legibility and whether the silhouette actually 'reads as an ambient poster... the first thing the eye lands on' remain unverified on real Spectra 6 hardware (02-UI-SPEC.md's flagged open item, carried since 02-01/02-02) - only 02-05's physical-panel QA checkpoint can close this; rendered-byte correctness alone does not prove visual legibility or composition quality."

duration: 40min
completed: 2026-08-10
status: complete
---

# Phase 2 Plan 3: Aircraft Silhouette Centrepiece Summary

**Vendored a CC0 aircraft-silhouette clipart, ran it through a from-scratch Pillow flood-fill cleanup pipeline to turn its detailed line-art into a flat solid mask, and composited it as the panel's mirrored, White, hard-edged visual centrepiece on the full-bleed Blue/Green poster field.**

## Performance

- **Duration:** 40 min
- **Tasks:** 2 completed
- **Files modified:** 5 (2 created, 3 modified)

## Accomplishments
- Retrieved freesvg.org/OpenClipart SVG ID 178507 ("Passenger aircraft silhouette clip art") via its download endpoint (required a page-visit-then-referer request, not a bare GET) and confirmed CC0 licensing directly from the page's `publicdomain/zero/1.0` licence meta tag
- Discovered the source asset is a detailed 3/4-aerial-view line-art drawing (a single SVG `<path>` using an evenodd fill rule to trace outline strokes, window rows, and panel-line shading) rather than an already-flat silhouette, and built a Pillow-only morphological cleanup pipeline to turn it into "one clean solid jet in profile" per UI-SPEC's executor note: dilate ink to close two hairline gaps that otherwise leaked a background flood-fill into the aircraft's interior, flood-fill the true background from multiple canvas-edge seeds, fill everything the flood fill didn't reach as solid, erode back, smooth
- Verified the cleaned silhouette survives the render pipeline's own resize-then-threshold step at simulated render size (~579x260) without fragmenting
- Extended `server/plane/render.py` with `paste_mask()` (the single shared mask-compositing call site, refactoring the existing state-label glyph paste to use it too) and `draw_silhouette()`, mirroring nose-right for departing / nose-left for arriving by comparing the recorded source orientation (`SILHOUETTE_SOURCE_NOSE = "left"`) against each state's requirement
- Sized the silhouette to fit within both UI-SPEC's ~900px width cap and 02-02's existing 260px height cap while preserving the vendored asset's own aspect ratio - the height cap binds first (~577x260), leaving 02-02's zone-3 reservation and `FLIGHT_NUMBER_TOP_Y` completely untouched
- Added a render-time guard-rail assertion (exactly two palette indices after compositing) and raised `server/test_render.py` from 15 to 19 checks, all green: silhouette-presence, state-mirroring (foreground-shape-only, so a background colour swap can't accidentally pass it), safe-box/no-overlap geometry, and a structural spy-based check that the Empty state never calls `draw_silhouette()`

## Task Commits

Each task was committed atomically:

1. **Task 1: Vendor and pre-rasterize the CC0 silhouette, extend the render harness to demand it (RED)** - `6f2e5f0` (test)
2. **Task 2: Composite the silhouette centrepiece with hard edges and state mirroring** - `0c223e9` (feat)

## Files Created/Modified
- `server/assets/icons/aircraft-silhouette.svg` - vendored source SVG (provenance only, never parsed at runtime)
- `server/assets/icons/aircraft-silhouette.png` - pre-rasterized 1800x830 flat solid grayscale mask (cleaned via the flood-fill pipeline)
- `server/assets/icons/VENDOR.md` - new `aircraft-silhouette` provenance entry: source URL, SVG ID 178507, retrieval date, CC0 licence, full cleanup-step documentation, source nose orientation, and the carried-forward "flightportrait's poster renderer is closed source" note
- `server/plane/render.py` - `SILHOUETTE_PATH`, `SILHOUETTE_TARGET_W`, `SILHOUETTE_MAX_H`, `SILHOUETTE_ZONE_TOP`, `SILHOUETTE_ZONE_HEIGHT`, `SILHOUETTE_SOURCE_NOSE`, `ZONE1_STATE_LABEL_HEIGHT` (renamed public), `paste_mask()`, `draw_silhouette()`, the two-palette-index guard rail in `_build_active_canvas()`
- `server/test_render.py` - `EXPECTED_CHECK_COUNT` raised 15 -> 19; four new silhouette checks

## Decisions Made
- Built the silhouette cleanup pipeline from scratch in Pillow (dilate/flood-fill/erode/smooth) rather than reaching for a vector editor or a new dependency, since neither `rsvg-convert`/`Inkscape` nor `numpy`/`scipy` are available in this environment and the source SVG's evenodd multi-subpath structure isn't something a simple rasterize-and-threshold pass could turn into a flat shape
- Let the height cap (260px, unchanged from 02-02) bind before the 900px width cap for this specific asset's aspect ratio, rather than forcing the silhouette to hit 900px wide and overflow the already-reserved zone-3 footprint
- Fixed a logic bug in Task 1's own just-written empty-state test during Task 2 (see Deviations below) rather than leaving it as a known-broken assertion

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed a wrong-invariant assertion in the empty-state silhouette test written in Task 1**
- **Found during:** Task 2 (implementing `draw_silhouette()` and running the harness green)
- **Issue:** Task 1's "empty state contains no silhouette pixels" check asserted the zone-3 Y band must be uniformly White for the Empty state. This is the wrong invariant: the Empty state's heading/body text is vertically centred on the *whole* 1600px canvas and legitimately passes through that Y range as Black-on-White (the opposite fg/bg pair the active states use), so the check false-failed against genuinely correct behaviour rather than catching a real regression.
- **Fix:** Replaced the pixel-band check with a direct structural test: monkeypatch `render.draw_silhouette` with a call-counting spy, build the empty-state canvas, and assert the spy was never invoked. This tests the actual UI-SPEC guarantee ("nothing detected, nothing to depict") without depending on text-layout geometry.
- **Files modified:** `server/test_render.py`
- **Verification:** `server/test_render.py` 19/19 green; all four `server/test_*.py` harnesses plus `stub-server/test_poll_cycle.py` (15/15) remain green with no regressions
- **Committed in:** `0c223e9` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 test-logic bug)
**Impact on plan:** The fix corrects a test I wrote in the immediately-preceding commit within this same plan; it does not touch any implementation code path or change what Task 2 delivers. No scope creep.

## Issues Encountered
- Retrieving the vendored SVG required visiting the freesvg.org page first and replaying its session cookie + `Referer` header on the `/download/178507` request - a bare GET to the download endpoint returned HTTP 200 with an empty body (no error signal), which could easily be mistaken for a working download; resolved by using a cookie jar and explicit `-e` referer flag with `curl`.
- The source SVG's actual content (a detailed 3/4-view line drawing) did not match my initial assumption of "already a flat silhouette clipart" - discovered this by rendering and visually inspecting the raw rasterization before committing to a processing approach, then iterated the flood-fill parameters (dilation kernel size 3/5/7/9/11/15) against the actual leak points until the cleanup produced one continuous solid shape with no residual hairline gaps.

## User Setup Required
None - no external service configuration required this plan.

## Next Phase Readiness
- `server/plane/render.py`'s `SILHOUETTE_*` constants and `draw_silhouette()`/`paste_mask()` are stable public APIs; 02-04's enrichment work (route/airline caption lines) slots in below the silhouette without touching this plan's zone-3 geometry.
- A-02-02-01 (02-02's unvalidated departure-side deadband threshold) and this plan's White-on-saturated-Blue/Green legibility question are both carried forward explicitly for 02-05's hardware QA checklist, alongside a new item: confirm on real glass that the silhouette's flat-fill detail level (window/panel-line detail removed during cleanup) still reads recognisably as a passenger jet at viewing distance, and that the ~577x260 render size feels proportionate as the poster's primary visual anchor.
- No blockers. All four `server/test_*.py` harnesses (19+14+6+5 checks) and `stub-server/test_poll_cycle.py` (15/15) are green with no regressions. Two preview PNGs (departing/arriving, `--state departing`/`--state arriving`) were rendered and eyeballed: the silhouette mirrors correctly (nose-right on Blue for DEPARTING, nose-left on Green for ARRIVING) and the panel now reads as a full-bleed poster with the aircraft as the dominant visual element, matching 02-UI-SPEC.md Revision 2's composition intent.

---
*Phase: 02-plane-view-end-to-end-slice*
*Completed: 2026-08-10*

## Self-Check: PASSED

All 5 modified/created files verified present on disk; all 3 commits (`6f2e5f0`, `0c223e9`, `65e63bf`) verified present in git history.
