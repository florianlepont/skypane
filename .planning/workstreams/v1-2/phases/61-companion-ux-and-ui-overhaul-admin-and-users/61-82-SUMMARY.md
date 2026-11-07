# Phase 61 Plan 82: Opening splash, loading indicators and the Battery row Summary

Owner decisions D-F (opening splash and loading indicators; W71, W75, W76, W104) and D-L (Battery row on Home, W113), delivered as two separate parts in one commit.

## Part 1: opening splash and loading indicators (D-F)

- **Splash "Cadre" (original P2 concept, owner change applied):** a blank frame outline draws itself; inside it the e-paper refresh runs (one soft inversion, four colour sweeps, a scan line that uncovers the sharp logo from its ghost); the real preload progress thickens the outline (SVG `stroke-dashoffset` attribute); at 100% the page opens from the frame's rectangle (per-element `clip-path` animation). No coloured artwork, no dithered interface. The logo is small (30px phone, 36px from 960px), centred in the frame and present (ghosted) from the first frame.
- **Gate (`splash-boot.js`, synchronous, in the head after the stylesheet):** puts `splash-on` on `<html>` before first paint. Shown once per session (`sessionStorage` guard written first, in try/catch; unavailable storage means no splash), skipped when the stylesheet came from the cache (resource timing: transfer smaller than the body), skipped on the second visit, no JS means no splash. Its own cap removes the class even if the main script never runs.
- **Overlay markup:** server-rendered in the shared shell by the new `companion/ui_splash.py` (after the icon sprite), `display: none` until `splash-on`. No inline style anywhere: values go through attributes, classes and `Element.animate`. EN/FR words (Loading / Ready) in `i18n_fr/common.py`.
- **Main script (`splash.js`, deferred, first in the shell order):** preloads with real events in four weighted groups (fonts via `document.fonts.ready`, stylesheets, the page's scripts seen through resource timing, key images; window `load` completes all), eases the bar toward the real progress, sets `inert` on every top-level page element while the splash shows and removes it at the end. Hard cap 3000 ms total (the preload counts as done at 1900 ms so scan, opening and finish fit). Reduced motion: static logo and progress, then reveal at once (no animation started). The sequence is a frozen table on `window.skypaneSplash` (one flash, kind `flash`; logged flash start times), so the flash rate (1 per sequence, limit 3 per second) holds by construction and is asserted.
- **Loading indicators:** the Location map shows a "Loading the map…" / "Chargement de la carte…" note with a bounded spinner from the moment the map is built until Leaflet's tile layer fires `load` (or tiles fail, the map gives up, or 8 s pass), centred over the map (W76). Flight pictures that are not loaded keep the existing shimmer placeholder (6 bounded iterations); tapping a not-yet-loaded picture on Flights now waits for the large picture and opens the dialog only when it is ready (the thumbnail keeps its placeholder meanwhile; a second tap opens it at once if the network stalls; the shared-element view transition runs only from a loaded thumbnail) (W75).
- **Title transitions (W71):** the per-title `view-transition-name: skypane-title` is removed, so every page change cross-fades titles with the root exactly like the rest of the page. `VIEW_TRANSITION_NAMES` in the UX helpers and the docstring of the uniqueness test are updated in place.
- **Test fixture:** the shared `new_context` fixture now arrives with the session already marked (every other browser test is a returning visitor); `new_context(splash=True)` opts a context into the splash.

## Part 2: Battery row on Home (D-L)

- A third row "Battery" / "Batterie" in the Home Frame group (under Screen and Quiet hours), shown to **every** person (user and administrator): icon tile, "69 % · Niveau normal" (level word: Normal level / Low / Very low, from the existing strings plus one new "Normal level"), a thin level bar (SVG, percentage attributes, no inline style) and "Autonomie estimée : environ N semaines/jours" only when `battery.battery_life_estimate()` supports an honest figure (hidden when charging or with too little history). No reading: "Aucune mesure pour l'instant" and no bar. Charging: the existing "Probablement en charge" wording and no estimate. New module `companion/pages/home_battery_row.py`; wiring in `home_page.py`; CSS classes `frame-battery*` (named so the existing "no home-battery dial for a user" guard keeps meaning). Existing amber/red low-battery notification, the administrator's hero dial and the live frame are untouched; the `home_page` docstring no longer says users see no battery.

## Tests

New: `companion/test_browser_splash.py` (12: once per session and inert-then-open, hard cap, second visit skipped, no JS, logo size and centring at t=0 at 390 and 1280, reduced motion static in both themes, flash rate by construction, map loading note EN/FR and on failure), `companion/test_browser_home_battery_row.py` (30: normal/low/charging at 360 and 1280, EN/FR, light/dark, bar width, no reading, plain user without the dial), `companion/test_browser_picture_loading.py` (3). Updated in place: the deferred script count test (20 scripts, the splash gate being a plain head script), the shell and error page digests, `test_home_state_card.py` and `test_browser_charging_pill.py` (Home carries the Battery row, with the charging words, but no dial and no pill), `test_browser_ux_02.py` (the History picture dialog test loads the picture first, since the dialog now opens once its picture is ready), the view-transition name table, the render baseline.

Screenshots: scratchpad `shots82/` (splash sequence at 390 and 1280, light and dark; battery states at 360 and 1280, light and dark; map loading).

## Deviations from Plan

- The splash skips whenever the stylesheet was served from cache (first visit of a session for a returning visitor skips too). This follows "skipped when assets are cached/fast"; the consequence is that the splash is seen on first-ever visits and after deployments that change the stylesheet.
- An administrator now sees the battery twice on Home (hero dial and the new row); the dial was left as is by the brief.
- `app.py` untouched (route constants for the two new scripts live in `static_files.py` only, the 1500-line ceiling).

## Known Stubs

None.

## Self-Check: PASSED
