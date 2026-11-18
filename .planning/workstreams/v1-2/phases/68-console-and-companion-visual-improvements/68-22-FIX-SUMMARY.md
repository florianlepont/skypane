# Phase 68 Plan 22 Fix: the 36 new failures after waves 2 and 3

All 36 failures listed in 68-22-SUMMARY.md are resolved. The full suite then ran once (`SKYPANE_REQUIRE_BROWSER=1 ./scripts/run-all-tests.sh`): 15841 passed, 8 skipped, 8 failed, coverage 96.18 % (gate 93 %). Of the 8, 7 are the failures already known on HEAD (`test_sign_in_surfaces` 2, `test_config_page_03`, `test_config_page_05`, `test_companion_app_01` 2, `test_sky_contrast` glass); the 8th, `test_companion_app_04` motion budget, was caused by the stagger fix below and is fixed in the last commit (42 passed). Golden render tests and `stub-server/test_phase47_freeze.py` stay green. ruff, mypy, function size (max 80), comment-history and `app.py` (1490 lines) pass.

## Commits

| Commit | Area |
|--------|------|
| 17c1bb46 | Save bar button centring (CSS bug) and Components overflow check |
| ba22f50a | Firmware history chip wording |
| 173fb9ba | Home title size and frame-picture radius (Foundations) |
| ebc52c5f | Airlines editor stagger (CSS bug) and Flights column test |
| 4050a49a | Home new-flight slide ported to the strip; motion tests on the new Home |
| de7b174c | Palette preview content address (JS bug) and Audit panel colours |
| 6d5f8f13 | Render baseline regenerated once (only `?v=` hashes moved, verified) |
| 5cd5d6cc | Motion budget guard lists the new stagger rule |

## Per-failure cause and fix

**test_browser_components_page buttons centred (8): real visual bug, CSS fixed.** `.dirty-bar > .btn` and `.dirty-bar--inline > .btn` used the `padding: 0 X` shorthand, which reset the vertical padding that centres a text-only `.btn` (the cap-height trimmed `inline-block` rule). The Cancel link sat at the top of its 44 px box (15.6 px off centre) on every save bar. Both rules now set `padding-inline` only (`companion/static/style.css`). This also fixed the real Cancel and Save buttons on every page with a save bar.

**test_browser_components_page overflow at 360 (4): test adapted, no CSS bug.** The six boxes are Audit filter chips inside `.filter-bar__chips--links`, a one-line track with `overflow-x: auto` on a phone (the owner rule: chips scroll on one line inside their container). The track itself is 41 to 319 px inside the 24 to 336 px card. The check now skips chips whose track scrolls sideways; the track and everything else still must stay inside the card.

**test_browser_round11_fixes firmware history (4): test updated.** The approved Update mockup labels the current version's chip `Running` / `En cours` (and the date line `Installed`). Expected text changed accordingly.

**test_browser_foundations titles (4): test updated.** The Home title is now the frame name beside its pencil: 32 px on a phone as in the approved Home mockup (`.nm h3`), 44 px on a desktop like every page title (the old test expected the removed hero's 28 and 48).

**test_browser_foundations radius (2): test updated.** `--radius-frame-pic: 5px` is a documented token (sketch-findings tokens-and-theming: the drawn portrait frame, never a capsule) used by the Home latest-flight picture and strip tiles. The test now asserts the token value and allows 5 px.

**test_browser_page_opening /airlines/manage stagger (2): real bug, CSS fixed.** The editor now has a gaps table followed by the main table, and both opened at two steps. A `.airlines-table--gaps ~ .airlines-table` rule gives the second three steps, so the opening is 0, 60, 120, 180. The motion budget guard (`test_companion_app_04`) lists the new rule.

**test_browser_page_opening Flights columns (2): test adapted.** Plan 20 stopped drawing the Flights header row (absolute 1 px `thead`), so its `th` widths are meaningless. The test now measures the cells of the first flight row, which is what the fixed table layout governs.

**test_browser_motion_live (4), more_sheet (1), sky_motion (2): Home changed, behaviour kept where it fits.**
- Countdown, switch and animation tests read the new markup (`.home-state__next .info-tip`, `.home-pill--switch`).
- The new-flight slide read `li.row` in the old Recent flights list, which no longer exists, so a new detection never animated. It is restored on the approved strip: `motion.js` keys tiles by call sign and a new tile slides in at the start (`translateX(-14px)` and fade) while the tiles after it glide by whole pixels; reduced motion stays free of animation. Tests assert tiles, their order and final positions.
- The ambient-loops test dropped the removed `.hero__picture` pseudo-element; the entrance tests read `.reveal` blocks (delays 0.06 to 0.3 s, capped at five steps).

**test_browser_ux_03 palette and ux_04 cancel (2): real JS bug fixed.** Plan 36 made previews content-addressed (`&v=`), but the picker script rebuilt the picture URL from a template that cannot carry a per-theme address, so keying the palette or cancelling fetched an unversioned, uncached URL. `theme-preview.js` now takes the address of the radio label's own `data-preview-src` when it is the same preview.

**test_browser_console colour tokens (1): test adapted.** The opened Audit event is a tinted panel in the approved Audit mockup (page ink at 5 % ground, 80 % terms). These two mixes are counted as already in use in the reference probe, resolved in the theme under test; nothing else was loosened.

## Visual change

Only the save bar buttons changed visually (Cancel and Save labels centred). Before and after full-page captures of the Components page save bar specimens, 360 and 1280 px, light and dark, are in `/tmp/claude-0/-home-user-skypane/1ebaf6ab-90c3-5997-a366-609c87d2992c/scratchpad/p22fix/components-savebar-{360,1280}-{light,dark}-{BEFORE,AFTER}.png` (BEFORE restores the old padding rule by injection). The stagger and script fixes change timing and fetched URLs only.

## Render baseline

Regenerated once with `PYTHONPATH=. test-support/companion_render_snapshot.py --write` because the changed `style.css`, `motion.js` and `theme-preview.js` moved the `?v=` content hashes linked from every page. Verified that with `?v=` hashes normalised the old and new baselines are identical.

## Design-system divergences

None introduced. The 32/44 px Home title, the 5 px frame-picture radius, the Running chip and the Audit panel tint all follow the approved mockups and sketch-findings-skypane; the earlier Home disc divergence in 68-22-SUMMARY.md stands.

## Deviations from Plan

The `test_companion_app_04` failure was caused by the stagger fix and fixed in the same area (Rule 1). Dead `.hero*` CSS and the `.hero__picture` selector in `motion.js` remain from plan 13 and were left alone (out of scope).

## Remaining known failures (not in this list, unchanged)

`test_sign_in_surfaces` (2), `test_config_page_03`, `test_config_page_05`, `test_companion_app_01` (2), `test_sky_contrast` glass test. The earlier `test_browser_ux_02` crossfade failure did not reproduce in the full run.
