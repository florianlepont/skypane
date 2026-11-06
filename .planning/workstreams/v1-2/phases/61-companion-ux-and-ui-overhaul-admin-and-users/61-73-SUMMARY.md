# Phase 61 Plan 73: Motion M1 and M3 Summary

Live Home (M1) and pull to refresh on the phone's Flights list (M3), ported from the demos onto the real pages, reusing `motion.js` and the 61-72 tokens.

**Requirements:** owner decision D43 (M1, M3).

## What changed

- **M1 (`static/motion.js`, `freshness.js`):**
  - The status dot already pulses (`home-state__dot--pulse`), unchanged.
  - The "Next update in ..." countdown is already rewritten each second by `relative-time.js` (server text stays correct without JS); `motion.js` adds a short roll (`opacity`/`transform`, WAAPI) on every change.
  - The countdown's leading figure counts up once on first render (rAF, `--motion-count` 600ms, starts at the smallest number with the same digit count so the width holds, the last frame writes the server's text back; the battery reading is covered too, dormant because the personal Home shows none).
  - `freshness.js` now dispatches `skypane-regions-swapping` before a swap; `motion.js` records the Recent flights rows' tops (key: callsign plus detail text) and after the swap slides a new row in at the top (`translateY(-14px)`, opacity) while the rows below glide from their old whole-pixel position (FLIP, `--motion-enter`, `--ease-out`).
- **M3 (`motion.js`, `freshness.js`, `style.css`):** Pointer Events on Flights at 699.98px and below. A drag down starting at scrollY 0 moves the list (transform only, damped 0.5, max 90) with an indicator pill ("Pull to refresh" / "Release to refresh" / the refresh pill's "Updating…"); release at 56px or more asks `freshness.js` for a refresh through the new `skypane-refresh-request` event (full fetch, no If-None-Match), spins the icon, waits for `skypane-refresh-done` (6s give-up), then settles on the spring and the first eight cards enter staggered (`--motion-stagger`). If no refresh loop answers the request the page reloads. `touch-action: pan-down` is set on `.history-cards` only while the page is at the top (class `is-pullable`), so every other vertical pan scrolls natively. No start inside inputs, horizontally scrollable ancestors, or with an open `dialog`. Reduced motion: the gesture still refreshes once; no list movement, spin, roll, count-up, slide or stagger.
- **Strings:** `common.pull_to_refresh`, `common.release_to_refresh` (EN in `ui_nav.py`, FR in `i18n_fr/common.py`), rendered on `<body>` as `data-pull-text` / `data-pull-release-text` by `ui_shell.py`.
- **Token:** `--motion-count`. No new `@keyframes` (WAAPI), no inline style attribute.
- Render baseline, the three sign-in digests and the motion-token pin updated in place.

## Tests

New `companion/test_browser_motion_live.py` (10 tests): count-up runs up and ends at the served text (no-JS page shows that text); countdown decreases and rolls on each tick; reduced motion: no count-up, no animation; new row enters at the top, rows below glide by whole negative pixels, all end in place and the list below does not move; reduced motion: no slide; mouse pull past 56 refreshes once (short pull does not), indicator and stagger; no trigger when scrolled; touch drag (CDP) refreshes once; reduced motion pull: one refresh, no animation or list move; no trigger with an open dialog. Ran 4 parallel processes of the file, three rounds after fixing a flaky bound: all 10 passing each time.

## Deviations from Plan

- **No Refresh link exists on Flights** (retired when the page got its self-refresh, quick task 260902-chc), so "the link stays working without JS" has nothing to keep; without JS the page simply stays as rendered. The pull uses the freshness fetch via the new event.
- **No numbers on the personal Home other than the countdown** (the battery dial renders only outside personal view), so count-up targets the countdown figure and the dormant battery value.
- The countdown tick is a roll on the changing text, not a new m:ss format: `relative-time.js` already ticks (seconds under a minute, minutes above) and its wording is pinned to the server's.
- `touch-action: pan-down` (Chromium: leaves finger-up pans to the browser, delivers finger-down pointer events); `pan-up` was tried first and the browser cancelled the drag. Browsers without these values scroll natively and the mouse/pen path still works.

## Screenshots

`scratchpad/shots73/` (Home and Flights mid-pull, light and dark, 390).

## Self-Check: PASSED
