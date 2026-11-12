# Phase 61 Plan 112: Location top edge on iPhone (status bar band and veil) Summary

The status bar zone of the phone Location page is now the bare map (the app bar's fade no longer covers it), and one fixed strip in the tile ground colour touches the top edge again, as the fixed map did in the last build the owner ledger records as good. Nothing here is confirmed on an iPhone.

## Commit

- `5d5559b2` fix: Location status bar zone is the bare map, with one fixed ground strip at the top edge

## Which earlier build was matched, and what differed

The build matched is the one after PR #318 (`3573db7b`, round 16). It is the only build for which the ledger records the owner seeing the top as wanted ("the top of the map now goes under the status bar", round 16, W171 update). The build `75635805` (#331), which plan 61-111 matched, is not it: 61-111 showed its top-edge chain is identical to the deployed build, and the owner still sees the band on that build.

Top-edge chain, `3573db7b` against HEAD before this plan (phones, below 960px):

| | after #318 (good) | since #330 (band and veil) |
|---|---|---|
| `.place-map` | `position: fixed; inset: 0`, ground colour, touches the top edge | `position: absolute` in the page container (document content, for the bottom edge) |
| fixed boxes touching the top edge | one (the map) | none |
| `body` background | transparent | ground colour `#F2EFE9` |
| `html` background, theme-color tags, app bar (transparent, absolute), app bar fade | same | same |

So the one thing lost at the top edge in #330 is a fixed, ground-coloured box touching it. The band colour the owner describes (pale beige) is the body ground colour, so the tint was already the map ground; recolouring `html` or the theme-color tags would not have changed what is seen, and was not done.

## Causes

(b) Home Screen app, found and verified in Chromium: `.site-header::before`, the app bar's fade (canvas colour at 85 percent fading to transparent), started 4px from the top and was as tall as the bar plus 20px. The bar is padded by the top safe-area inset, so with a 59px inset the fade covered the whole status bar zone at 85 to about 50 percent opacity: a pale veil over the map in the light theme, a dark one in the dark theme. In a Safari tab the inset is 0, so it only sat behind the logo row. This fade is in the #318 build too, so it does not by itself explain why that build looked right; it is a real veil either way.

(a) Safari tab, and the blurred edge of (b), hypothesis only: iOS 26 Safari treats the status bar zone by what is fixed at the top edge. With a fixed box there it continues that box's colour and, as far as I remember WebKit's behaviour, drops its own blurred edge effect; with nothing fixed there it shows the page background under a blur whose lower edge is visible. Since #330 nothing is fixed at the top. I could not check this against WebKit sources or a device.

## Changes

- `companion/static/style-place.css`: the fade starts at `safe-top + space-xs` and is shorter by `safe-top` (unchanged in a tab, where the inset is 0).
- `companion/pages/place_page.py` and `style-place.css`: a new `<div class="place-edge" aria-hidden="true">` in the stage; below 960px, while the map or its loading placeholder shows, it is `position: fixed; top: 0; left: 0; right: 0; height: var(--space-xs)` (4px), `--color-map-ground`, `z-index: 16` (above the app bar, so it is the topmost box at the edge). Hidden without scripts and from 960px (the map itself is fixed there).
- Kept: the map as document content (bottom edge), the compact sheet, the page opening, `html`/`body` colours, theme-color tags. No meta tag, no safe-area offset on the map.
- The two parts are independent: the fade is the `::before` rule at about line 695, the strip is the `.place-edge` block plus `_edge_html()`.

Known cost: in the Home Screen app the strip is a 4px ground-coloured line at the physical top of the screen, above the clock. It is the same colour as the tiles' land, but it is not map.

## Tests

`companion/test_browser_place_document_map.py`:
- `test_the_phone_top_edge_is_the_bare_map_under_the_status_bar_with_one_fixed_ground_strip` (360 and 390, light and dark, forced 59px inset) replaces the 61-111 test that required no fixed box at the top. It asserts: exactly one fixed box touches the top edge, `.place-edge`, full width, 2 to 4px, ground colour, opaque, no backdrop filter, topmost at the edge; the app bar has no fill, image or blur and its pseudo-element starts at or below 59px; a screenshot of the top 59px is the same with the app bar hidden (at most 2 levels of 255, the frame button's shadow in the dark theme measured 1); the first 4 rows are ground and the rest is not a flat ground fill; the rest of the 61-111 chain (map absolute at 0, container clips, no transform/filter/contain, colours, theme-color tags, no scroll).
- `test_the_ground_strip_is_fixed_at_the_top_while_the_map_loads_and_absent_on_a_wide_screen` (light and dark).
- Checked red first: on the previous stylesheet all six cases fail; with only the old fade restored the four top-edge cases fail on the fade.
- `companion/test_browser_overhaul_sweep.py`: the warm-fill rule exempts `.place-edge`, as it does the map box and the Location body (three Location phone cases failed on it).

Render baseline regenerated; `61-UI-SPEC.md` 9.0c carries a three-line revision note. The sign-in digests did not move.

## Verified, and not

Verified in headless Chromium: the geometry, colours and stacking above, and that nothing of the app bar paints in a 59px status bar zone.

Only the owner's phone can confirm:
1. Home Screen app: no veil and no blurred edge under the status bar.
2. Safari tab: what the status bar zone looks like. A tab's page starts below the status bar, so the page cannot draw tiles there; the best this technique can give is the ground colour continued upwards without a blurred edge, which is what the #318 build gave. If the owner's "fully transparent" memory comes from a tab, it was this.
3. That a 4px strip is enough for Safari to count it as fixed at the edge.

## If the owner still sees it, in this order

1. Veil still there in the Home Screen app, band in the tab unchanged: Safari is not counting the strip. Raise `.place-edge` to 8 to 12px; if still nothing, make the app bar itself `position: fixed` on this page with a ground-coloured strip as its top part.
2. Veil gone in the Home Screen app but the 4px line is noticed: lower the strip to 1 or 2px, then try it transparent (Safari may still count a transparent fixed box, but may then fall back to the page colour in a tab).
3. Tab band still read as a header although it has no blurred edge: this is the tab limit in point 2 above. The only route to real tiles there is the old fixed map (#318), which loses the tiles under Safari's bottom bar (W171); that is an owner trade-off, not a fix.
4. Band or veil in a different colour than the map ground (bluish or dark): Safari is using `html` (`--color-secondary`); set `html.map-ready` to `--color-map-ground` on phones. The theme helper `_set_ui_theme` compares the page colour between themes and needs adapting.
5. Nothing changes at all: a Safari Web Inspector session on the device (Mac needed) to read which element Safari samples; no further blind attempt is worth it.

## Deviations

- The brief's minimum (make `html.map-ready` and the theme-color tags the map ground) was not applied: the orchestrator's later correction replaced the tint target with "match the good build", that build has the same `html` colour and theme-color tags as today, and the observed band is already the ground colour. It is item 4 above.
- One commit instead of one per part: the fade and the strip share one test.
- Commit trailer names the model that actually wrote the commit (Claude Fable 5.2), not the name in the executor rules file.
- [Rule 3] warm-fill sweep exemption for the strip.

## Tests run

ruff (whole repo), mypy (45 files), `check_comment_history`, `check_function_size`, `stub-server/test_phase47_freeze.py`, the render snapshot (`--write`), `test_sign_in_surfaces`, `test_suite_guards`, `test_page_styles`, `test_structure_guards`, `test_stylesheet_structure`, `test_contrast_check`; browser and page files: all `test_browser_place*`, `test_browser_location*`, `test_browser_detection`, `tab_bar_float`, `status_bar_band`, `foundations`, `contrast_edges`, `surfaces`, `overhaul_sweep`, `overhaul_steps`, `save_bar`, `round11_fixes`, `round8_fixes`, `audit3_fixes`, `page_opening`, `splash`, `perf_remaining`, `test_detection_page`, `test_detection_position`, `test_place_page`, `test_place_save`, `test_place_map_assets`, `test_location_picker`, `test_shell_meta`, `test_page_policy_headers`, `test_companion_app_0*`, `test_view_pages_0*`: 2307 passed, 3 failed (the sweep, fixed, then its 72 Location cases passed), 2 skipped (`test_companion_app_01.py` lines 664 and 704, need a non-root user; not browser tests, unrelated to this page). The two new tests ran 12 times in four parallel loops with no failure. The full suite was not run (cadence).
