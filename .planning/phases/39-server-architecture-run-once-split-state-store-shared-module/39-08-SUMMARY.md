---
phase: 39-server-architecture-run-once-split-state-store-shared-module
plan: 08
subsystem: server
tags: [render, package-split, panel-renderer, function-size, monkeypatch-seams]

requires:
  - phase: 39-server-architecture-run-once-split-state-store-shared-module
    provides: "39-03: explicit state_dir injection into render.build_canvas/_build_active_canvas (this plan's layout.py inherits that signature unchanged)"
provides:
  - "server/plane/render/ package: style.py, text.py, glyphs.py, hold_screens.py, layout.py, cli.py, __main__.py"
  - "server.plane.render stays importable with the full historical public/private surface, via __init__.py re-exports"
  - "python3 -m server.plane.render as the documented CLI entry point (server/plane/render.py's own sys.path bootstrap dropped)"
  - "The three ARC-01 size offenders inherited from render.py (build_parser 98, draw_main_text_block 91, main 84) are each <=80 code lines"
affects: [39-13]

tech-stack:
  added: []
  patterns:
    - "Seam discipline inside a split package: a function another submodule calls goes through the module attribute (text.draw_main_text_block(), hold_screens._build_hold_canvas(), layout.draw_illustration()), never a bare/`from`-imported name - a test that rebinds the OLD flat-module name must retarget to the submodule that actually looks the name up at call time, or the rebind is a silent no-op."
    - "Break an import cycle by relocating the shared function, not by deferring the import: draw_source_fault_badge()/draw_battery_icon() moved to glyphs.py (a leaf module both layout.py and hold_screens.py can import) instead of hold_screens.py importing layout.py locally inside a function body."

key-files:
  created:
    - server/plane/render/style.py
    - server/plane/render/text.py
    - server/plane/render/glyphs.py
    - server/plane/render/hold_screens.py
    - server/plane/render/layout.py
    - server/plane/render/cli.py
    - server/plane/render/__main__.py
  modified:
    - server/plane/render/__init__.py (git mv'd from server/plane/render.py, then reduced to re-exports)
    - server/test_render.py
    - README.md
    - pyproject.toml

key-decisions:
  - "draw_source_fault_badge/draw_battery_icon moved to glyphs.py, not layout.py as the research's own line-range table located them: both are called from hold_screens.py's shared _build_hold_canvas(), and hold_screens.py must not import layout.py (layout.build_canvas() dispatches into hold_screens.py, so the reverse import would cycle). glyphs.py depends on neither, so both siblings can reach it."
  - "_band_edges()/_band_center_x() (pure diagonal-band geometry) moved to style.py rather than staying beside draw_diagonal_band() in layout.py: text.py's band-theme text blocks need them, and text.py cannot import layout.py without creating the same kind of cycle layout.py already has with hold_screens.py."
  - "The render.py sys.path bootstrap was dropped entirely, not moved to cli.py: the plan's own action text made this conditional on whether `python3 server/plane/render/cli.py` needs to keep working, and Task 2's own README change standardizes on `python3 -m server.plane.render` (run from the repo root), which needs no bootstrap."
  - "Found and fixed three additional rebind-retargeting hazards beyond the three the plan's research explicitly named (_font, draw_main_text_block, draw_previous_text_block): draw_illustration (in _PlacementSpy), and _build_hold_canvas/_build_dimmed_hold_canvas (in two dispatch-proof tests) are the exact same hazard - the plan's own <behavior> and acceptance criteria required the untouched suite to keep passing for real, which these three tests would not have done silently. Retargeted all three to the submodule that actually defines/calls them (render.layout, render.hold_screens), each with a non-vacuity assertion."

requirements-completed: []

duration: ~70min
completed: 2026-09-27
---

# Phase 39 Plan 08: render/ package split with a stable import surface Summary

**`server/plane/render.py` (2049 lines) is now a package of six submodules (style, text, glyphs, hold_screens, layout, cli) plus `__main__.py`, with `server.plane.render` re-exporting the full historical surface so nothing outside this plan needed a single edit, and the three inherited ARC-01 size offenders (build_parser, draw_main_text_block, main) are each under 80 code lines.**

## Performance

- **Duration:** ~70 min
- **Tasks:** 2/2 completed
- **Files modified/created:** 11 (7 created, 4 modified; 1 of the modified files, `render.py`, was git-mv'd into the new package's `__init__.py`)

## Accomplishments

- `server/plane/render/` package: `style.py` (spacing, fonts, state colours, headline copy, frame/band/battery geometry, the two canvas-bounds assertion helpers, the diagonal band's pure edge-geometry helpers), `text.py` (font fitting, tracked text, the main/previous flight text blocks, both plain and band-theme variants), `glyphs.py` (the five centred hold-screen glyphs plus the two small status indicators - source-fault badge, low-battery icon), `hold_screens.py` (the five non-active-flight canvases and the two shared hold compositions), `layout.py` (band painting, top labels, illustration load/resize/cache/placement, `build_canvas`/`render_panel`), `cli.py` (the preview CLI) and `__main__.py` (`python3 -m server.plane.render`).
- `__init__.py` re-exports every name any caller or test in this repo reaches through `render.` - about 150 names total, both public and private, plus the `device_config`/`illustrations`/`Image`/`ImageDraw`/`WIDTH`/`HEIGHT` module/constant attributes - verified by a new literal-list surface test (`test_package_exposes_every_name_callers_and_tests_use`) and a submodule-presence test.
- Output is byte-identical to the pre-split file: verified programmatically against the git-committed original across every state (departing/arriving/empty/quiet_hours/display_off/battery_empty), 3 themes (white, band_blue, band_red) including both airline-only and identifier-stripped route variants, and all four source_fault/battery_low combinations - zero mismatches in either verification pass (Task 1 and Task 2).
- Found and fixed the exact rebind-retargeting hazard the plan's own research had already diagnosed for `_font`/`draw_main_text_block`/`draw_previous_text_block`, but in three MORE places the research didn't name: `_PlacementSpy` rebinding `draw_illustration` (used by 5 tests), and two dispatch-proof tests rebinding `_build_hold_canvas`/`_build_dimmed_hold_canvas`. All three call sites are intra-module bare calls (same defining module as the caller) that a rebind on the package object cannot reach - retargeted to `render.layout.draw_illustration`, `render.hold_screens._build_hold_canvas`, `render.hold_screens._build_dimmed_hold_canvas`, each with a non-vacuity assertion (an existing `len(calls) != 1`/`len(placements) != 2` check, or a new call-counter where the existing assertion alone would have passed vacuously - `test_non_band_text_blocks_unaffected_by_band_idx_kwarg` and `test_band_black_main_card_ink_swaps_to_white`).
- The three ARC-01 size offenders render.py carried over are fixed: `cli.py`'s `build_parser()` (98 -> ~6 code lines) delegates to four section helpers called in their original order (byte-identical `--help`, diffed and confirmed); `main()` (84 -> ~9) delegates to `_preview_inputs()`/`_render_preview()`/`_write_outputs()`; `text.py`'s `draw_main_text_block()` (91 -> ~4) dispatches to `_draw_main_block_plain()` (unchanged) or `_draw_main_block_band()` plus its own two helpers. `scripts/check_function_size.py check --max 80 server/plane/render` reports 72 functions scanned, none over 80.
- Full suite: 2976 passed / 139 skipped, 94% coverage; ruff and the comment-history guard clean across the whole repo; `git diff --name-only` across both commits touches no file under `companion/` or `firmware/`.

## Task Commits

1. **Task 1: carve render.py into the package with explicit re-exports; retarget the rebinding tests and the source-text test** - `062cac9` (feat)
2. **Task 2: bring build_parser, main and draw_main_text_block under 80 code lines; README usage** - `ed86fa6` (refactor)

## Files Created/Modified

- `server/plane/render/__init__.py` - git-mv'd from `render.py`; module docstring rewritten for the package + `-m` usage; explicit re-export blocks from every submodule plus `Image`/`ImageDraw`/`ImageFont`, `device_config`, `illustrations`, `dither`/`enrich`/`runway_config`, and the `panel_format` WIDTH/HEIGHT/IDX_* constants
- `server/plane/render/style.py` - spacing/typography/state-colour/geometry constants, `state_background_index`/`state_ink_index`/`runway_tag_text`/`empty_heading_text`, `_band_edges`/`_band_center_x`, `_assert_in_safe_box`/`_assert_within_canvas`
- `server/plane/render/text.py` - `_font`/`fit_text_size`/tracked-text helpers/`_flight_line1_text`/`_flight_line2_text`/`display_airline_name`, `draw_main_text_block` (split into `_draw_main_block_plain`/`_draw_main_block_band`/`_main_block_band_classify`/`_main_block_band_center_x`), `draw_previous_text_block`
- `server/plane/render/glyphs.py` - the five hold-screen glyph drawers plus `draw_source_fault_badge`/`draw_battery_icon` (moved here from their research-assigned home in layout.py to break a would-be import cycle with hold_screens.py)
- `server/plane/render/hold_screens.py` - the five non-active-flight canvas builders and the two shared hold compositions (`_build_hold_canvas`/`_build_dimmed_hold_canvas`)
- `server/plane/render/layout.py` - `draw_diagonal_band`/`draw_frame`/`draw_top_labels`, illustration load/resize/cache/placement, `_build_active_canvas`/`build_canvas`/`render_panel`
- `server/plane/render/cli.py` - `build_parser` (split into `_add_flight_arguments`/`_add_output_arguments`/`_add_route_shaping_arguments`/`_add_state_arguments`), `main` (split into `_preview_route_for`/`_preview_inputs`/`_render_preview`/`_write_outputs`)
- `server/plane/render/__main__.py` - `python3 -m server.plane.render` entry point
- `server/test_render.py` - retargeted every rebind that crossed a module boundary, added non-vacuity assertions, retargeted the no-stroke-outline source-text test to scan every `.py` under `server/plane/render/`, added the full-surface and submodule-presence tests
- `README.md` (repo root) - the direct-script `server/plane/render.py` usage line becomes `python3 -m server.plane.render`
- `pyproject.toml` - the E402 ignore comment drops render.py's now-zero bootstrap count

## Decisions Made

See `key-decisions` in the frontmatter: `draw_source_fault_badge`/`draw_battery_icon` relocated to `glyphs.py` to avoid an import cycle; `_band_edges`/`_band_center_x` relocated to `style.py` for the same reason; the sys.path bootstrap dropped entirely rather than moved; three additional rebind hazards found and fixed beyond the plan's own named three.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `_PlacementSpy` rebinding `render.draw_illustration` would have been a silent no-op post-split**
- **Found during:** Task 1's read-first pass over `server/test_render.py` (tracing every `render.<name> = ` rebind site against the planned module assignment)
- **Issue:** `draw_illustration()` and its one caller, `_build_active_canvas()`, both land in `layout.py`. `_build_active_canvas()` looks `draw_illustration` up as a bare name in `layout.py`'s own module globals, not the package's. A rebind on `server.plane.render.draw_illustration` (the package re-export) would not reach that lookup, so 5 tests using `_PlacementSpy` would either see an empty `.placements` list (caught loudly by their own `len(...) != 2` guard) or, worse, silently observe the real unspied function's return value in a context that assumed a spy was active.
- **Fix:** Retargeted `_PlacementSpy.__enter__`/`__exit__` to rebind `render.layout.draw_illustration` instead of `render.draw_illustration`.
- **Files modified:** `server/test_render.py`
- **Verification:** All 5 tests using `_PlacementSpy` pass; `len(placements.placements) != 2` guards would have failed loudly had the retarget been wrong.
- **Committed in:** `062cac9`

**2. [Rule 1 - Bug] Two dispatch-proof tests rebinding `_build_hold_canvas`/`_build_dimmed_hold_canvas` had the same hazard**
- **Found during:** Task 1's same read-first pass
- **Issue:** `_build_battery_empty_canvas()`/`_build_no_connection_canvas()` and `_build_hold_canvas()`/`_build_dimmed_hold_canvas()` all land in `hold_screens.py`; the callers use bare intra-module calls. A rebind on the package object would be a silent no-op for the same structural reason as #1.
- **Fix:** Retargeted both tests to rebind `render.hold_screens._build_hold_canvas`/`render.hold_screens._build_dimmed_hold_canvas`.
- **Files modified:** `server/test_render.py`
- **Verification:** Both tests' own `len(calls) != 1` non-vacuity guard passes for real (would fail loudly - `0 != 1` - had the retarget been wrong).
- **Committed in:** `062cac9`

**3. [Rule 1 - Bug] `test_non_band_text_blocks_unaffected_by_band_idx_kwarg` would have passed vacuously post-split without a stronger check**
- **Found during:** Task 1, applying the plan's own explicit correction (research §3/conventions) for `draw_main_text_block`/`draw_previous_text_block` rebinds to this specific test
- **Issue:** This test's assertion is a byte-identity comparison between a "wired" and an "unwired" render. If the rebind silently missed the real call site, BOTH renders would use the real function and stay byte-identical - the test would pass for the wrong reason, exactly the vacuity trap the plan's conventions section warned about for a sibling test.
- **Fix:** Retargeted the rebind to `render.text.draw_main_text_block`/`render.text.draw_previous_text_block` and added a per-theme call-counter, failing loudly if either spy is never reached.
- **Files modified:** `server/test_render.py`
- **Verification:** Test passes with the call-counter proving both spies fire on every one of the 11 non-band themes.
- **Committed in:** `062cac9`

**4. [Rule 1 - Bug] `test_band_black_main_card_ink_swaps_to_white` had the same vacuity risk**
- **Found during:** Task 1, same pass
- **Issue:** This test infers ink-swap behaviour from a pixel diff between a "with text" and a "without text" (no-op) render. If the no-op rebind never reached the real call site, both renders would be identical and `ink_values` would be empty - the test's own existing assertions (`IDX_WHITE not in ink_values`) would fail, but not for the reason the test claims to check, and a future change that broke the retarget could mask the real regression this test protects against.
- **Fix:** Retargeted to `render.text.draw_main_text_block` and added an explicit call-recording list, failing loudly per-theme if the no-op spy is never invoked.
- **Files modified:** `server/test_render.py`
- **Verification:** Test passes across all 7 registered band themes with the non-vacuity check active.
- **Committed in:** `062cac9`

**5. [Rule 3 - Blocking] README.md usage line lives at the repo root, not `server/README.md` as the plan named**
- **Found during:** Task 2's action step, searching for the `server/plane/render.py` usage line to update
- **Issue:** `server/README.md` has no render-invocation line at all; the actual usage example the plan's action text describes is `README.md:104` (repo root).
- **Fix:** Updated the repo-root `README.md` instead.
- **Files modified:** `README.md`
- **Verification:** `grep -n "python3 -m server.plane.render" README.md` matches; the updated command was run and produced a valid panel + preview PNG.
- **Committed in:** `ed86fa6`

---

**Total deviations:** 5 auto-fixed - 4 Rule 1 (bugs: rebind-retargeting hazards the split would otherwise have introduced silently or vacuously), 1 Rule 3 (blocking: the plan named the wrong file for an otherwise-correct edit).
**Impact on plan:** All five are mechanical consequences of the split itself (or of a stale file reference), not scope creep. No behaviour changed; the fixes make the test suite's existing guarantees hold for real after the move, matching the plan's own "byte-identical output... apart from retargeted rebinding sites" success criterion.

## Issues Encountered

None beyond the deviations above.

## User Setup Required

None - no external service configuration required.

## Known Stubs

None.

## Threat Flags

None - `T-39-17` (palette legality, `_assert_legal_palette` moved verbatim into `layout.py` and still runs on every `build_canvas`), `T-39-18` (illustration cache stays bounded and keyed the same way, now in `layout.py`) and `T-39-19` (fault-screen provenance text left untouched, verified byte-identical against the committed header via `test_fault_screen_mask.py`) are all exactly as the plan's own threat register anticipated. No new network endpoint, auth path, file-access pattern or schema change was introduced.

## Next Phase Readiness

ARC-03's render-split clause and ARC-01's three inherited size-offender clauses are functionally complete for this plan's scope; per this phase's own convention (39-02's premature tick was reverted), REQUIREMENTS.md is left untouched here - only the phase's close-out plan (39-13) flips ARC-* to Complete. The render package's public import path (`server.plane.render`) is unchanged, so no companion or firmware file needed an edit, and 39-13's close-out pass can rely on the existing `firmware/tools/gen_fault_screen.py` and `companion/theme_preview.py` call sites working as-is.

## Self-Check: PASSED

- FOUND: server/plane/render/__init__.py
- FOUND: server/plane/render/style.py
- FOUND: server/plane/render/text.py
- FOUND: server/plane/render/glyphs.py
- FOUND: server/plane/render/hold_screens.py
- FOUND: server/plane/render/layout.py
- FOUND: server/plane/render/cli.py
- FOUND: server/plane/render/__main__.py
- FOUND commit: 062cac9
- FOUND commit: ed86fa6

---
*Phase: 39-server-architecture-run-once-split-state-store-shared-module*
*Completed: 2026-09-27*
