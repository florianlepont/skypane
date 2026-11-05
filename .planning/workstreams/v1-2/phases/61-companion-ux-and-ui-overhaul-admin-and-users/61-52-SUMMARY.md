# Phase 61 Plan 52: Sky and motion foundations

Owner decisions D37 and D38: visual direction A ("sky and motion") for the whole companion, applied to the real current pages through the shared stylesheet and tokens only. No page markup, content, control, route or rule changed; `render_baseline.json` is unchanged because no served HTML moved.

## What changed

- **Sky.** `html::before` is a fixed, non-interactive three-stop gradient from `--sky-top/--sky-mid/--sky-bottom` (no `background-attachment: fixed`, no layout space, no overflow); `html` keeps `--color-canvas` as the floor and `body` is transparent. Tokens exist in the default, `@media (prefers-color-scheme: dark)`, explicit light and explicit dark blocks. Light mode has four skies (dawn, day, dusk, pale moonlit night) chosen by `html[data-sky]`, which `nav-dropdown.js` (the script every page already carries; no new script, route or CSP change) sets from the viewer's local hour: 05-08 dawn, 08-17 day, 17-21 dusk, else night. Without script, and on the sign-in page (which has no script by contract), the sky is day. Dark (explicit, or Auto on a dark system via `html[data-sky][data-ui-theme="auto"]`) is always the deep night sky.
- **Frosted glass.** `--glass-bg`, `--glass-bar-bg`, `--glass-border`, `--shadow-glass`, `--glass-blur`. One `@supports (backdrop-filter)` block at the end of the stylesheet makes the surfaces translucent; every surface keeps its solid `--color-dominant` / `--color-secondary` base fill outside it. The blur is limited to the sidebar, tab bar, phone header, Home state card, sign-in card, the two sheets and dialogs; repeated cards (sections, tiles, collection/airline cards, frame tiles, runway cards) are translucent only. The desktop sidebar is a floating rounded panel (16px margin, grid column widened by the same 16px, dirty-bar and toast offsets updated to match). `--radius-card` is 20px and the card rules that used the 8px control radius now use it.
- **Typography.** `--font-page-title-size` is a clamp: 30-34px on a phone, 44-48px from 960px; page title leading 1.08, tracking -0.02em; existing font stacks.
- **Motion.** Tokens `--motion-enter` (400ms), `--motion-stagger` (60ms), `--ease-out`; `skypane-reveal` keyframes on `.reveal` and `.dashboard-main .page-section`, staggered through `--reveal-index` (nth-child, capped at 5), fill-mode `backwards` only so the final state is the plain layout state and no stacking context is left behind. The primary button lifts 1px on hover (press feedback already existed). The single existing `prefers-reduced-motion: reduce` rule now also zeroes `animation-delay`; the reduce/no-preference block counts are unchanged.

## Tests

- New `companion/test_sky_contrast.py` (static, served CSS): all six sky cascades declare their stops; Dark is always night (explicit and Auto + dark system); the four light skies differ; body text and accent clear 4.5:1 on every sky stop and on the card and bar glass composited over every stop; rarity inks too; the glass is only applied inside the backdrop-filter `@supports` block with a solid base fill token for every glass selector, blur kept to at most 10 surfaces; the sky is a fixed pseudo-element; one reduced-motion rule covers duration, delay and transitions; the entrance never fills forwards.
- New `companion/test_browser_sky_motion.py` (22 cases, run 3 times in a row, zero failures): every hour band edge sets the expected `data-sky` (mocked `Date.prototype.getHours`) and text/accent stay readable on the live computed stops and glass; four different gradients; Dark/Auto-dark always night at any hour; no-script default day; fixed sky with no overflow at 1280 and 360; entrance duration 0.4s with a 60ms stagger and a settled state of `transform: none`, `opacity: 1`, no running animation; reduced motion zeroes the entrance; sidebar and tab bar blur where supported.
- Adapted in place, none weakened: `test_companion_app_04` (motion-token budget now lists `--motion-enter` and `--motion-stagger` and pins their only spenders); the canvas colour is now carried by `<html>` (the body is transparent so the sky shows), so `test_browser_ux_helpers._THEME_PROBE`, `test_browser_airline_collection`, `test_browser_flights_cards` and `test_browser_frame_fold` read it from `documentElement`; `test_browser_airline_collection` (dimmed-card contrast now composites the translucent card over the sky, `_channels` reads rgba alpha) and `test_browser_ux_health_drawings` (chart-area contrast measured against the card composited over the sky).

## Deviations / notes

- The look picker's runway cards are translucent but keep no glass shadow: an existing test pins an unselected card to no box-shadow because selection is drawn as a shadow ring.
- The history stub card (ticket notches painted in the card colour) stays solid on purpose.
- The Light "night" sky is a pale indigo, not dark, so the dark ink stays readable; the deep night sky belongs to the Dark theme.
- `test_browser_user_pairing` `#pair-code` once measured 43.99998px in a loaded full run (sub-pixel flake, passes alone; the field's rule was not touched).
- Screenshots (before = HEAD stylesheet, after = this plan; Home, Flights, Airlines, Display, desktop and phone, light and dark): `/tmp/claude-0/-home-user-skypane/4b1e4fdb-1c1f-5685-9cba-073edbf39a04/scratchpad/shots/before-*.png` and `after-*.png`.

## Gates

ruff, mypy, `check_comment_history`, `check_function_size`, `test_phase47_freeze` green; `companion/app.py` untouched. Full suite result recorded in the final report.
