# Phase 61 Plan 54: Other pages in style A, and the 43px root cause

Owner decisions D37 and D38 on the real pages; no content, control, route or rule changed.

## Part A: why controls measured 43px instead of 44px

Root cause: the card entrance translated by fractional pixels, and when the card already sits at a fractional offset the browser hit-tests the 44px control one pixel short (reproduced with `a.calendar-manage` at 360px: box 44px, hit area 129x43, transform `translateY(0.154px)` on the arriving section). The same thing explains `a.login-signin` and the `#pair-code` 43.99998 reading. The rise is now in whole pixels (`steps(12)`) with the fade in its own animation, so no moment of the entrance can change a control's reach; no test tolerance was added.

- Regression test `test_controls_keep_44px_at_every_point_of_the_entrance` in `companion/test_browser_overhaul_sweep.py` (50 cases): every swept page at 360 and 1280 is frozen at 0.13, 0.37, 0.61 and 0.83 of the entrance timeline and every control is measured by box (rounded to 0.01) and by hit reach. Verified to fail on the previous stylesheet (`hit area 129x43`) and pass now.
- Without the finite-animation wait, the whole sweep (288 cases, `-n 4`, under load) passes.
- `test_browser_sky_motion` adapted in place for the two animation names.

## Part B: pages polished

- Glass and radius scale on the Airline editor table, Audit table, standalone empty states (Flight history), Airline lightbox (blurred), save bar (bar glass); card hover shadows restored after the glass rule; solid fallbacks kept.
- Entrance applied to the blocks that sit straight on the sky; soft finite accent bar on the active sidebar item and eased active tab pill (transform/opacity only on pseudo-element or pill).
- Layout defects found on the real pages and fixed: Fleet State card broke one word per line at 1280 (health rows now use a container query), Account frame rows squeezed text to a few characters per line at 360 (action stacks under the row).
- Placeholder ink was the browser default (3.5 to 3.8:1); now secondary ink at full opacity.
- New cases in `companion/test_browser_overhaul_sweep.py` (126 cases): translucent surfaces on the 20px radius; at most 6 blurred elements per page; every animation finite except the status pulse and halo; zero layout shift from the entrance on Home, Account and Flight history; text, link, placeholder and disabled contrast on the real pages under the four light skies and the dark night sky. Static check added in `test_sky_contrast.py`; `test_companion_app_04` motion-token spenders updated in place.
- `61-UI-SPEC.md` updated.

## Notes

- The Airline collection page has a small real layout shift (the info button and sort control move when the filter bar script enhances it, about 0.0015). It is not caused by an animation and was left out of the layout-shift test; Flight history is the third page instead.
- The Users page at 360px still wraps long email addresses by character; left as is (not an inconsistency of the new language).
- `render_baseline.json` unchanged (no served HTML moved).

## Screenshots (scratchpad, `/tmp/claude-0/-home-user-skypane/4b1e4fdb-1c1f-5685-9cba-073edbf39a04/scratchpad/shots/`)

Names are `b54-before-<page>-<p|d>-<light|dark>-<sky>.png` and `b54-after-...` for pages flights, collection, location, pers-look, pers-special, pers-calendar, pers-arrivals, account, console-fleet, console-users, console-airlines, console-audit, home (p = 360px, d = 1280px; light has dawn, day, dusk, night; dark has night). Contact sheets (desktop light, desktop dark, phone light, phone dark) are in `.../scratchpad/sheets/b54-before-<page>.png` and `b54-after-<page>.png` (after sheets for flights, console-fleet, account, console-audit, console-airlines).

## Gates and full suite

ruff, mypy, `check_comment_history`, `check_function_size`, `test_phase47_freeze` green; `companion/app.py` 1473 lines. Full suite after the last stylesheet change (`-n 4`, companion + test-support + stub-server): 8148 passed, 4 skipped, 1 failed (`test_browser_display_looks` calendar bottom sheet measured mid slide-in, a load-dependent flake in a file not touched by the styles; fixed by waiting for the sheet's finite animations, then 4 parallel runs of the file under CPU load, 13/13 each). An earlier full run found and led to fixes for stylesheet-structure, motion-budget, dirty-bar rule-count and test-guard failures (all adapted in place).
