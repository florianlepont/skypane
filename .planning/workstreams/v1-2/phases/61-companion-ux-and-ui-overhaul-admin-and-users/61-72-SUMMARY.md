# Phase 61 Plan 72: Motion M2, M4, M5, M8 Summary

Four owner-approved motion ideas ported from the demos onto the real pages with the look unchanged: picture placeholders with a blur-up (M2), a spring press on buttons, rows and chips (M4), a sliding tab-bar pill (M5) and a spring switch with a tick (M8).

**Requirements:** owner decision D43 (M2, M4, M5, M8).

## What changed

- **M2 (`static/motion.js`, `style.css`):** a picture still loading (Home picture, Flights thumbnails, the Style preview, also when the preview swaps its `src`) marks its container `.is-loading`; a soft band sweeps across it (`translateX` of a pseudo-element, infinite, off under reduced motion). On `load`/`error` the mark is removed and the picture fades in once from a blur (`.is-revealed`, `filter` and `opacity` only, removed on `animationend`). A cached picture is left alone; without the script nothing is marked.
- **M4 (`style.css`):** one block, `:active { scale: .97; transition: scale var(--motion-press) }`, on buttons (not value-control handles, not `.switch`), `.mobile-nav__link`, `.sidebar-link`, `.history-card`, `.filter-chip__box`, `.tab-bar__pill`, `.frame-menu__button`, `.filter-bar__search`. The release spring is `scale` appended to each element's own transition (`--motion-spring`, `--motion-spring-duration`), so their colour transitions are kept. No JS. `scale` is a separate property from `transform` (the existing `translateY(1px)` press still composes).
- **M5 (`static/motion.js`, `style.css`):** a `.tab-bar__slider` span is inserted in the bar and moved with a whole-pixel `translate` under the active link; on a plain left click on another tab it glides there on the spring with a short `scale` stretch while the real navigation proceeds. `view-transition-name: skypane-tab-slider` is on the class (one element per document), so the cross-document transition carries the pill to its new place. The bar class `tab-bar--slider` makes the active link's own pill transparent only once the slider has a box; without JS the active link keeps its own pill. A click another handler cancels returns the pill (zero-delay check on `defaultPrevented`). A `ResizeObserver` keeps it under the active cell as the cells settle.
- **M8 (`style.css`, `static/quick-switch.js`):** the thumb springs on `transform` and stretches on press with `scale` (origin on the side it leaves from), instead of the demo's `width`; the button itself never scales so its 44px target holds. A click on a switch adds `.switch--tick` (a ring that grows and fades, `scale` and `opacity`) and calls `navigator.vibrate(10)` where supported; both skipped under reduced motion.
- **Tokens:** `--motion-spring`, `--motion-spring-duration` (420ms), `--motion-press` (90ms), `--motion-shimmer` (1.3s), `--motion-reveal` (900ms). Reduced motion: the global override plus, in the existing reduced-motion block, `animation: none` for the sweep, blur-up, ring and stretch, and `scale: none` on every press; JS skips the glide, the reveal and the vibration.
- **Wiring:** new shell script `/static/motion.js` (`MOTION_SCRIPT_SRC`, in `static_files.py`, `ui_base.py`, `layout.py`, `ui_shell.py`, one alias line in `app.py`, now 1478 lines). It is a separate script because `nav-dropdown.js` is pinned timer- and `matchMedia`-free.

## Tests

New `companion/test_browser_motion.py` (12 tests): the pill ends under the active tab after real navigations at 360 and 390 in whole pixels; a cancelled click returns the pill; no-JS keeps the active link's own pill; the placeholder class appears while a held picture loads and is gone after; reduced motion gives ~0ms transitions, no ring, no vibration, no press scale, no glide; the switch stretches, ticks, vibrates `[10]`, keeps a 44px box mid-animation and passes the settle-probe hit test at 360 and 1280; a press scales to .97 and springs back to rest with `scale` in its transition list; hit targets settle on `/`, `/flights`, `/fleet?tab=settings`.

Updated in place (subject changed): `test_companion_app_04.py` (motion tokens: new layer tokens pinned, shimmer and reveal each spent by exactly one animation), `test_companion_app_03.py` (nineteen shell scripts), `test_browser_ux_helpers.py` and so `test_browser_ux_02.py` (the new view-transition name on every route; the preview crossfade test now waits for the blur-up to finish before asserting full opacity), `test_sign_in_surfaces.py` digests, `companion/testdata/render_baseline.json` regenerated (one more script tag on every authenticated page).

## Deviations from Plan

- The demo's blur-up also scaled the picture 1.05 to 1; dropped, because the existing layout-shift guard (`test_images_hold_their_place_before_they_arrive`) measures the picture's box right after it arrives and a scale changes `getBoundingClientRect`. Blur and opacity only.
- The demo's thumb stretch used `width` and the ring a `box-shadow`; both are `scale`/`opacity` here (transform/opacity only).
- Motion lives in a new `motion.js` rather than `nav-dropdown.js` (see Wiring).
- The tick fires on any click of a `.switch` handled by `quick-switch.js`'s page set (not on pages that do not load it); the spring and stretch are CSS and apply to every switch.

## Screenshots

`scratchpad/shots72/` (home placeholder and blur-up, tab slide mid-way, flights after, switch pressed and ring, light and dark at 390).

## Self-Check: PASSED
