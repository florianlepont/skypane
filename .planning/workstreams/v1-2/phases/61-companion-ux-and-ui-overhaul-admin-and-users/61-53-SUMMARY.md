# Phase 61 Plan 53: Home in style A

Owner decisions D37 and D38, applied to the real Home page on top of the 61-52 foundations. All content, controls, rules and routes are unchanged.

## What changed

- **Greeting** (`companion/pages/home_greeting.py`, `nav-dropdown.js`, `i18n_fr/home.py`): decorative `aria-hidden` line under the unchanged `<h1>` (above it, it pushed the title past the phone title-gap limit); neutral server text "Hello"/"Bonjour", swapped by script from the local hour (morning 05-12, afternoon 12-17, evening 17-21, night); the active frame's name is a second line when the person has several frames. Height reserved, so no layout shift. `layout.page_header()` gained a trailing optional `trail_html`.
- **Plane on a trail**: inline SVG, only when the page has a recent flight (first Recent flights row); finite 1.2s `skypane-plane-fly`, `--motion-flight`; reduced motion shows it at rest.
- **Status dot**: pulse kept; a wider glow layer added to the existing ring.
- **Entrance**: `.reveal` on the state card; state, current frame and recent flights stagger 0/60/120 ms.
- **Fills (item 4)**: skipped. Home has no progress bar or counter badge for a signed-in person (the battery dial renders only on a bare, principal-less render).
- **Tab bar legibility (item 6)**: cause was the nearly transparent bar glass over scrolling page content (a white picture washed out the dark theme's labels, and the accent "Console" label failed 4.5:1 over dark content in Light). `--glass-bar-bg` is now 0.94 white / `rgba(16, 21, 48, 0.9)`; the space-switch cell is 68px wide with no extra margin.

## Tests

- New `companion/test_browser_home_greeting.py` (37 cases): greeting per hour edge, EN and FR, h1 unchanged; no-script default; frame line only with several frames, with reserved height; plane only with a flight; one finite 1.2s flight resting at `transform: none`; reduced motion; title/trail/greeting boxes identical without script, mid-flight and settled at 1280 and 360, no overflow; card stagger 0/60/120 ms; tab bar at 360 and 390, light and dark, four skies: inactive labels >= 4.5:1 over white and black behind the bar, not clipped, cells >= 44px, switch cell >= 68px.
- New static test in `test_sky_contrast.py` for the bar glass over any content.
- Adapted in place: `test_home_state_card` (class string now ends with `reveal`), `test_companion_app_04` (`--motion-flight` is a documented third exception spent only by the plane).
- `companion/testdata/render_baseline.json` regenerated deliberately.

## Deviations

- Greeting bands split the sky's "day" band at noon (morning/afternoon).
- Fills skipped as above.
- Test hardening in place (no assertion weakened): `test_browser_overhaul_sweep._open` and `test_browser_home_state_card._open_user_home` now wait for the finite entrance animations to end before hit-testing/measuring (the display-calendar 360 hit-area case flaked 3 of 8 at the previous HEAD); `test_browser_sky_motion` expects Home's sections to start one stagger step in (the state card enters first); `test_browser_user_pairing._height` rounds to 0.01px (a 44px field read 43.99998).

## Gates

ruff, mypy, `check_comment_history`, `check_function_size`, `test_phase47_freeze` green; `companion/app.py` untouched (1473 lines). New and touched Home browser files run 3 times in a row with zero failures. Full suite (`-n 4`, companion + test-support + stub-server): 7971 passed, 4 skipped, 1 failed (`test_browser_user_pairing` 43.99998px sub-pixel flake, fixed afterwards as above and re-run 3 times green).
