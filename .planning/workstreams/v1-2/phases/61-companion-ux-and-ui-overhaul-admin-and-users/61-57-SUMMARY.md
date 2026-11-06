# Phase 61 Plan 57: Navigation chrome Summary

A floating Liquid Glass tab bar on the phone, a transparent phone app bar, and a frame button with a glass popover (in the top bar of every device-scoped page and of the Console Fleet page) that replaces the tile strip and its fold.

## What changed

- **Floating tab bar.** `.tab-bar` (below 960px) is a 68px pill (`--tab-bar-h`), 12px from the sides (`--tab-bar-gap`, plus the safe areas) and `calc(12px + var(--safe-bottom))` above the bottom, `--radius-pill`, with its own glass: `blur(26px) saturate(200%)` (and `-webkit-`) inside the glass `@supports` block, a translucent fill `--bar-bg` (white 0.66 Light, `rgba(20,24,34,0.86)` Dark), a sheen gradient, a 1px light border, an inset specular highlight and a long soft shadow (`--bar-shadow`). The active item is an inner glass pill (`--bar-pill-bg`) with the graphite (ivory in Dark) label. The administrator's Console / My frame switch stays the first cell (68px, accent outline); its divider and right margin were dropped to win the pixel the longest French label ("Compagnies") needs at 360px. Page content, toasts, the save bar and the map stage clear bar + gap + safe area through the same tokens. The Dark bar over a pure white backdrop: the bar fill is 0.86 (not the 0.62 suggested) because the active pill (white 0.18) must still hold 4.5:1 for the ivory label over white; measured by the new contrast tests over white, black and both sky ends in all four theme cascades.
- **Phone app bar.** Transparent, no border, no blur, safe-top padding, brand left, frame button right. It was not turned into a glass bar (the audit's alternative was to drop the bar fill).
- **Frame button and popover** (`companion/frame_menu.py`, new). A native `<details class="frame-menu">`: a 44px glass pill (status dot, name with ellipsis, chevron; `aria-haspopup`, `aria-expanded` kept by modal.js) and a 300px (max `100vw - 24px`) glass panel hung under it, out of flow (no layout shift), anchored the same way on a phone and a desktop (no bottom sheet needed down to 360px). Rows (>= 52px) are plain links to the same page of each frame under its `/devices/<id>` prefix: CSS picture, name, last-seen word, owner line (frames of other people, Console), status dot, check on the frame in view. Under a separator: "System" (Console only) and "Add a frame". Shown to everyone with a frame in scope (a single-frame user still sees it, with only the Add row). Desktop: top right of the content column, level with the page title; the title row reserves 12rem so it never runs under the button; the map's top-right controls hang below it. Escape, outside tap, focus return and the dialog opener of the Add row are in modal.js; the entrance reuses the finite `skypane-soft-in`.
- **Console Fleet.** `console_fleet_view.frame_menu_html` builds the same button (frames problems first, System, Add a frame opening `#dlg-add-frame`); the page builds it while building its body and the shell reads it back (`frame_menu.stash_console_menu` / `header_menu_html`). `/fleet?frame=<id>` and `/fleet?view=system` stay the row links; the content follows the selection.
- **Removed:** `ul.frame-tiles`, `details.frame-fold`, `strip_fold_html`, `frame_tile_html`, `add_tile_html`, `frame_switcher_html`, the `skypane.frameStrip` localStorage memory and the fold logic in nav-dropdown.js, their CSS (about 230 lines) and the fold's phone styles. Strings stay (`nav.frame_strip_aria`, `nav.frame_tile_seen`, `nav.frame_tile_add`); `nav.frame_button` ("Choisir un cadre") is new.
- **Desktop sidebar.** The current item is a solid graphite pill (ivory in Dark) with the on-accent label; the accent bar beside it is gone.
- **Owner line only when it tells frames apart.** A lone frame (a co-manager with one shared frame) shows no "Shared by" line, which keeps the existing rule that a co-manager never receives the owner's email on a single-frame page.
- **Add row destination.** In the personal space the Add row is `/pair-frame` for everyone (an administrator's personal space equals a user's, which `test_personal_space_parity` enforces); on a Console page an administrator gets `/fleet?pair=1`, on the Fleet page the dialog.

## Not done

- **Hide on scroll down / show on scroll up** was implemented first and then removed: a bar that slides off-screen leaves its taps outside the viewport for pointer-driven automation and assistive tools (Playwright cannot scroll a fixed element back into view), for no measurable gain. The bar never moves.

## Tests

New: `companion/test_browser_frame_menu.py` (replaces `test_browser_frame_sheet.py`: open/close, Escape, focus return, aria state, outside tap, keyboard, no script, 360/390/1440 x EN/FR x both themes for geometry, rows >= 52px, no layout shift, panel inside the viewport, title alignment, Console owner lines, personal list with no System row or owner line, reduced motion), `companion/test_browser_tab_bar_float.py` (margins, forced `--safe-bottom`, last content above the bar at the end of the page on Home/Flights/Fleet at 360 and 390 with and without an inset, switch first and set apart, inner active pill, ink over white and black in both themes, transparent app bar clearing a forced `--safe-top`, reduced motion, no script), `test-support/frame_menu_support.py`, `test_sky_contrast` (bar fill over white, black, both sky ends, all cascades; geometry tokens).

Updated in place (none weakened): `test_frame_switcher`, `test_frame_sheet`, `test_device_selector`, `test_console_fleet_view`, `test_console_fleet_page`, `test_device_links`, `test_device_routes`, `test_airline_editor`, `test_user_view_http`, `test_co_manager_access`, `test_co_managers_page`, `test_device_scope_owner`, `test_page_scripts` (the hook is now `details.frame-menu` -> modal.js), `test_companion_app_02` and `_04`, `test_status_pages_06` and `_07` (floating geometry), `test_personal_space_parity` (ids normalised in link text too), and the browser files `device_selector`, `fleet_dialogs`, `fleet_page`, `console`, `console_fleet_view`, `user_pairing`, `overhaul_steps`, `overhaul_sweep`, `home_greeting`, `home_state_card`, `surfaces`, `airline_editor`, `detection` (accent budget allows the graphite sidebar pill and the Add row chip), `foundations`, `sky_motion`, `nav_spaces`, `space_switch`. `test_browser_frame_fold.py` is deleted (its subject, the fold, is gone). `companion/testdata/render_baseline.json` regenerated.

## Step counts

Frame switching is the button, then the row: S2 2, U2 several 2, A7 2, A3 5, A4 retire 5, A4 reassign 6, A5 6 (see `61-STEP-COUNTS.md`).

## Deviations

- Bar fill alpha 0.86 in Dark instead of the example 0.62 (contrast of the active pill over white); active pill token and tab-bar padding token (`--tab-bar-pad: 2px`) added so "Compagnies" fits at 360px in French.
- The frame button is 44px high (the spec said 38-40) to meet the 44px target rule.
- The button's width on a desktop is capped at 11rem and the title row reserves 12rem, so the Airline collection header keeps its title, bar and badges on one line at 1280px (the collection status basis went from 360px to 300px for the same reason).

## Screenshots

`/tmp/claude-0/-home-user-skypane/4b1e4fdb-1c1f-5685-9cba-073edbf39a04/scratchpad/shots57/` holds `{home,fleet}-{phone,desk}-{light,dark}-{closed,open}.png` (390x844 and 1440x900, popover closed and open). The "before" images are the plan 61-56 "after" set in `scratchpad/shots56/`.

## Verification

ruff, mypy, comment-history, function-size (931 functions, none over 80) and `test_phase47_freeze` green; `companion/app.py` unchanged at 1473 lines. Full suite (companion + test-support + stub-server, `-n 4`, after the last code change): 8225 passed, 4 skipped (root-permission skips), 0 failed. One earlier run showed `test_browser_update.py::test_twelve_releases...[390-en]` failing under load; it passed alone and in the clean full run (flaky under load, unrelated to this plan).
