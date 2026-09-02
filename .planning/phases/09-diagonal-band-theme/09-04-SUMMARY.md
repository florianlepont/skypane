---
phase: 09-diagonal-band-theme
plan: 04
subsystem: rendering
tags: [e-ink, on-glass-verification, hardware, typography, data-cleaning]

# Dependency graph
requires:
  - phase: 09-diagonal-band-theme (plan 09-03)
    provides: Full band composition (registry, drawing primitive, split top labels, three-tier text hierarchy on both cards) - the on-screen-only state this session put in front of real ink for the first time
provides:
  - "Real Spectra 6 glass sign-off on all 5 band colours (both states), all 4 content-ladder tiers, previous-card clearance, and the whole composition at distance"
  - "Unconditional white ink for every band theme's main-card text (server/plane/render.py)"
  - "_role_fit_tracked_text_size() - a tracking-aware shrink-to-fit helper, alongside the existing _role_fit_text_size()"
  - "_band_edges(canvas_y, w) - the diagonal band's own left/right pixel edges at a given y, factored out of _band_center_x()"
  - "Band-width-aware shrink-to-fit for all three band text roles on both cards, replacing the earlier SAFE_BOX-width fit that let text overflow the band itself"
  - "enrich._primary_city_name() - reduces a '/'-separated compound municipality name to its first segment, wired into _parse_route() for both origin_city and destination_city"
  - "hardware/BRINGUP-LOG.md Phase 9 entry, dated 2026-09-02"
affects: [rendering, plane-theme-config, flight-data-enrichment]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Real-glass verdict overrides a plausible-sounding hypothesis rather than being assumed to confirm it - black ink on the lighter, dithered Blue Light band was tried specifically because the physics argument for it was sound, and rejected anyway once seen on real ink."
    - "When real ink disagrees with a screen preview, root-cause before widening the fix - the first ink fix (extending white ink from band_black to band_blue) was verified as a real, separate finding via a second on-glass render, not assumed to generalize; only after Green and Red also failed on real ink was the rule made unconditional."
    - "Distinguish a canvas-boundary overflow from a band-boundary overflow before choosing a fix - _assert_within_canvas() never fired, which ruled out a hard clip and pointed at the real cause (white text past the band's edge landing on White, i.e. invisible, not literally cut)."
    - "Verify a stress-test fixture is real before trusting a fix it inspired - Phase 7's own long-name fixture was confirmed, live against the real API, to be an artificially extreme string; the actual worst real case (a genuine Orly destination) was found by querying api.adsbdb.com directly rather than assumed from the fabricated one."

key-files:
  created:
    - .planning/phases/09-diagonal-band-theme/09-04-SUMMARY.md
  modified:
    - server/plane/render.py
    - server/test_render.py
    - server/plane/enrich.py
    - server/test_enrich.py
    - hardware/BRINGUP-LOG.md

key-decisions:
  - "White ink widened from band_black-only to unconditional for every band theme, based on two rounds of real on-glass findings (Blue and Green both failed with black ink, not just Black) rather than a single observation - each extension was independently re-confirmed on glass before being generalized further."
  - "Black ink on band_blue_light was tried and explicitly rejected on real glass despite a sound contrast-luminance argument for it - the developer's direct comparison verdict ('c'est mieux en blanc') overrides the hypothesis, and the code was reverted to the simpler unconditional-white rule rather than kept as a band_dithered-conditional special case."
  - "The band text overflow's real cause (band-width, not canvas-width) was found by rendering locally with --preview and visually inspecting a cropped PNG, not by continuing to guess-and-redeploy against real hardware - cheaper to diagnose locally once the symptom was described, reserving hardware cycles for confirmation."
  - "The remaining overflow on an extreme fixture was resolved as a data-layer fix (enrich._primary_city_name(), shortening the source city name) rather than continuing to lower the render layer's minimum font size, per the developer's own diagnosis - confirmed as the right call by checking real production data: no airline_name in the project's actual history.db exceeds ~20 characters, and the compound-municipality pattern was confirmed live against the real API for two genuine airports."
  - "BAND_MAIN_ROUTE_MIN_SIZE reverted from a mid-session 12px stopgap back to the original 16px once the data-layer fix was in place - the lower floor was a workaround for a problem now fixed closer to its source, and 16px stays more legible for the common case."

requirements-completed: [PHASE9-8]

coverage:
  - id: D1
    description: "All 5 band colours judged on real Spectra 6 glass in both DEPARTING/ARRIVING states, with a true-to-preview and legibility verdict for each, including the black-band (and, as found, blue/green/red-band) white-ink verdict"
    requirement: "PHASE9-8"
    verification:
      - kind: human_judgment
        ref: "hardware/BRINGUP-LOG.md Phase 9 entry, Step A"
        status: pass
    human_judgment: true
  - id: D2
    description: "All 4 content-ladder tiers re-rendered and judged against the final geometry on real ink, including tier 3's promotion behaviour and the no-raw-callsign confirmation"
    requirement: "PHASE9-8"
    verification:
      - kind: human_judgment
        ref: "hardware/BRINGUP-LOG.md Phase 9 entry, Step B"
        status: pass
    human_judgment: true
  - id: D3
    description: "Previous card's band-collision clearance explicitly confirmed on real ink at the final geometry, not inferred from the main card's own check"
    requirement: "PHASE9-8"
    verification:
      - kind: human_judgment
        ref: "hardware/BRINGUP-LOG.md Phase 9 entry, Step C"
        status: pass
    human_judgment: true
  - id: D4
    description: "The whole composition judged at typical viewing distance; poll timer restarted with a real post-restart poll cycle observed, working tree clean"
    requirement: "PHASE9-8"
    verification:
      - kind: human_judgment
        ref: "hardware/BRINGUP-LOG.md Phase 9 entry, Step D and Teardown"
        status: pass
      - kind: integration
        ref: "sudo systemctl is-active skypane-poll.timer -> active; journalctl showed Finished skypane-poll.service after restart"
        status: pass
    human_judgment: true

# Metrics
duration: ~3h (interactive on-glass session, including two unplanned but developer-authorized scope extensions)
completed: 2026-09-02
status: complete
---

# Phase 9 Plan 04: On-Glass Verification Summary

**Every visual/textual decision spike 003-diagonal-band-theme made was put in front of real Spectra 6 glass for the first time; real ink disagreed with the screen preview on ink colour and text overflow, both found and fixed in session, plus two developer-driven extensions (a real shrink-to-fit mechanism for band text, and a data-layer fix for compound city names) beyond the plan's original scope.**

## Performance

- **Duration:** ~3h (interactive, real-hardware session)
- **Completed:** 2026-09-02
- **Tasks:** 2/2
- **Files modified:** 5 (`server/plane/render.py`, `server/test_render.py`, `server/plane/enrich.py`, `server/test_enrich.py`, `hardware/BRINGUP-LOG.md`)

## Accomplishments
- All 5 band colours (Blue, Blue Light, Green Light, Red, Black) confirmed on real glass in both states, all 4 content-ladder tiers confirmed on Blue Light, previous-card clearance confirmed across all 5 colours, and the whole composition confirmed at distance.
- White ink widened from a `band_black`-only exception to unconditional for every band theme, after Blue and Green were each independently found illegible with black text on real ink and re-confirmed fixed.
- Main-card dash rule widened 24px → 48px on real-ink feedback ("tout short").
- Text block's shared `center_x` re-anchored from the block's top y to its vertical midpoint, spreading the trapezoid's centreline drift evenly across all three lines instead of concentrating it at the bottom.
- Added a real shrink-to-fit mechanism for the band's three text roles (previously fixed-size, unlike every other active-state text role) - `_role_fit_tracked_text_size()` alongside the existing `_role_fit_text_size()`, explicitly authorized by the developer before being added (a new fit mechanism is out-of-bounds by this plan's own default scope).
- Root-caused the actual overflow bug: text was fit against `SAFE_BOX`'s width, not the diagonal band's own narrower, height-varying width - white text extending past the band's edge onto White simply vanished (white-on-white), reading as a hard clip though `_assert_within_canvas()` never fired. Fixed via a new `_band_edges()` helper (factored out of `_band_center_x()`) so each line fits against the band's real width at its own y.
- Added `enrich._primary_city_name()`, reducing a `/`-separated compound municipality name (confirmed live against `api.adsbdb.com`: Toulon-Hyères Airport, a real Orly route, is `"Toulon/Hyeres/Le Palyvestre"`) to its first segment before the existing sentence-case pass - a project-wide fix, not scoped to this theme, wired into both `origin_city` and `destination_city`.
- `hardware/BRINGUP-LOG.md` gained a dated Phase 9 entry under Panel Observations, matching the Phase 7/8 entries' structure and honesty standard (method limits stated, open items carried forward explicitly).

## Task Commits

Each correction was committed atomically as it was confirmed on glass:

1. **Ink/dash/centring corrections** - `f003c93` (fix) - white ink widened to unconditional, dash width 24px→48px, centre-x anchored at block midpoint, band-width-aware shrink-to-fit added and wired
2. **City-name data fix** - `750c0d6` (fix) - `_primary_city_name()` added and wired into `_parse_route()`
3. **BRINGUP-LOG.md entry** - `389d5c6` (docs)

**Plan metadata:** committed separately below (docs: complete plan)

## Files Created/Modified
- `server/plane/render.py` - unconditional band white ink, `BAND_MAIN_DASH_W` 24→48, `_band_edges()`, `_band_center_x()` refactored to use it, `_role_fit_tracked_text_size()`, band-width-aware re-fit for both cards' text roles
- `server/test_render.py` - ink-swap check widened to all 5 band ids (was black/red-only)
- `server/plane/enrich.py` - `_primary_city_name()`, wired into `_parse_route()`
- `server/test_enrich.py` - 2 new checks (50 → 52)
- `hardware/BRINGUP-LOG.md` - Phase 9 entry under Panel Observations

## Decisions Made
- Widened the white-ink override incrementally (black → +blue → +green, each re-confirmed on glass) rather than jumping straight to "unconditional" on the first finding - only generalized once the pattern held across three separate colours.
- Explicitly tried and rejected black ink on `band_blue_light` despite a real luminance argument for it, on direct developer instruction to test the hypothesis rather than assume it - real ink overruled the theory.
- Diagnosed the band-width overflow locally (via `--preview` + a cropped PNG inspection) rather than continuing to guess-and-redeploy against the VPS, once the symptom was clearly described - cheaper and faster than burning further hardware cycles on an undiagnosed bug.
- Resolved the residual extreme-fixture overflow as a data-layer fix (shortening the source city name) rather than a render-layer one (shrinking the font further), per the developer's own diagnosis, verified against real production data before committing to the approach: `history.db`'s longest real observed `airline` value is ~20 characters (no concern), and the compound-municipality pattern was confirmed live against two genuine airports rather than assumed.
- Reverted `BAND_MAIN_ROUTE_MIN_SIZE` from a mid-session 12px stopgap to the original, more legible 16px once the data-side fix made the lower floor unnecessary for real destinations.

## Deviations from Plan
- **Two developer-authorized scope extensions beyond this plan's original `<in_session_correction_scope>`:**
  1. Adding a shrink-to-fit mechanism to the band text roles - explicitly listed as "not bounded" by the plan itself ("a genuine fit-mechanism gap is NOT bounded"). Proceeded only after explicit developer instruction ("2 mais on le fait maintenant").
  2. Editing `server/plane/enrich.py` - entirely outside this plan's declared `files_modified` (`hardware/BRINGUP-LOG.md`, `server/plane/render.py`, `server/test_render.py`). Proceeded only after explicit developer instruction ("maintenant et dans le projet").
  Both were flagged as scope extensions before being applied, not silently absorbed into "bounded correction" framing.
- The plan's Step A originally called for both DEPARTING and ARRIVING renders per colour; after Blue and Blue Light were each confirmed in both states, the developer asked to drop the redundant second-state check for the remaining colours ("no need to validate each time arriving/departure... it's almost the same design") - Green Light, Red, and Black were each checked in one state only. Recorded here as a real, developer-directed simplification of the verification battery, not a silent gap.

## Issues Encountered
- `companion/test_companion_app.py` failed once inside the parallel `scripts/run-all-tests.sh` run but passed clean (69/69) when run in isolation immediately after - a flaky parallel-run interaction, not a real regression (confirmed: no code in this plan touches `companion/`). Not investigated further since it did not reproduce.
- `server/test_poll_loop.py`'s pinned `panel.bin` digest check failed throughout this session, as expected: the pre-existing macOS/Linux Pillow font-rendering difference, unrelated to this plan's changes. Not re-pinned locally, per that file's own standing rule (re-pin only from a real CI run's output).
- The CLI's manual `--callsign` test path has no way to force an `aircraft_type` value, so the airline·type line's " · {type}" suffix could not be exercised on real glass this session. Confirmed as a pre-existing test-tooling gap (no `--aircraft-type` flag exists in `plane/render.py`'s CLI), not a regression, by reading the CLI argument construction directly.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 9's diagonal-band theme is now fully implemented, on-glass verified, and documented - all 8 PHASE9-1..8 clauses of the phase Goal are closed.
- `server/test_render.py` and `server/test_enrich.py` are both fully green; `scripts/run-all-tests.sh` is green except the pre-existing, unrelated `test_poll_loop.py` digest quirk.
- Open items carried forward (see `hardware/BRINGUP-LOG.md`'s Phase 9 entry for full detail): the frame's mounting state (desk/wall) was not asked about this session; the band-width-aware fit was verified on one band colour/position, not all 5 with long names; `_primary_city_name()`'s rule was checked against 2 real airports, not exhaustively against every possible compound municipality name.
- This was the phase's last plan - Phase 9 is ready to be marked complete in ROADMAP.md/STATE.md.

---
*Phase: 09-diagonal-band-theme*
*Completed: 2026-09-02*

## Self-Check: PASSED

- FOUND: server/plane/render.py
- FOUND: server/test_render.py
- FOUND: server/plane/enrich.py
- FOUND: server/test_enrich.py
- FOUND: hardware/BRINGUP-LOG.md
- FOUND: .planning/phases/09-diagonal-band-theme/09-04-SUMMARY.md
- FOUND: f003c93 (render.py/test_render.py commit)
- FOUND: 750c0d6 (enrich.py/test_enrich.py commit)
- FOUND: 389d5c6 (BRINGUP-LOG.md commit)
