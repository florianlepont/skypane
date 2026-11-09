---
phase: 61-companion-ux-and-ui-overhaul-admin-and-users
plan: 98
subsystem: companion-ui
tags: [audit-3, visual, workflows, csrf, login-next, performance, etag, js-minify, history-cache]
key-files:
  created:
    - companion/history_cache.py
    - companion/js_minify.py
    - companion/pages/home_rename_row.py
    - companion/test_audit3_fixes.py
    - companion/test_browser_audit3_fixes.py
    - companion/test_history_cache.py
    - companion/test_js_minify.py
  modified:
    - companion/static/style.css
    - companion/static/dirty-state.js
    - companion/static/list-filter.js
    - companion/static/prefetch.js
    - companion/static/session-guard.js
    - companion/app.py
    - companion/routes.py
    - companion/next_route.py
    - companion/login_page.py
    - companion/user_pairing.py
    - companion/post_actions.py
    - companion/device_dispatch.py
    - companion/device_scope.py
    - companion/ui_shell.py
    - companion/ui_components.py
    - companion/static_files.py
    - companion/history_query.py
    - companion/airline_collection.py
    - companion/pages/history_page.py
    - companion/pages/home_page.py
    - companion/pages/airline_collection_page.py
    - companion/pages/config_page.py
    - companion/pages/personalisation_cards.py
    - companion/settings/theme.py
    - companion/settings/calendar.py
    - companion/settings/quiet_hours.py
    - companion/settings/runway_led.py
    - companion/i18n_fr/*.py
metrics:
  completed: 2026-11-09
---

# Phase 61 Plan 98: Remaining audit-3 findings Summary

The remaining audit-3 visual findings, the workflow findings (login `next`, session-expiry notice, owner Rename row, CSRF on settings and quick routes, pairing, special-look and no-script gaps, leave guard, Flights history) and the performance quick wins (folded-history cache, comment-free scripts, idle prefetch limits, lazy hidden previews, image ETags) are fixed or explicitly decided below. Screenshots are in `scratchpad/shots98/`.

## A. Visual findings

| Id | Outcome |
|----|---------|
| V01 | The logo never shrinks and the frame button shrinks to the rest of the bar with an ellipsis; the Home greeting line is cut with an ellipsis (checked at 360 and 390 with a 48-character name). |
| V02 | The Flights picture dialog is one opaque card (padding, border, shadow-pop) holding the picture, the dated caption and a standard secondary Close; it no longer floats over the table. |
| V05 | The New badge sits in the card's corner, outside the picture (test retargeted: clear of the picture). |
| V08 | A 12-hour browser draws the 24-hour time over the time field's own text (the field stays the control and follows edits), so the value is told once, in the form the rest of the page uses, in both languages. The old test that required the second line is retargeted. |
| V11 | The Fleet column spans the same width as the title and the frame button (the 800px centred column is gone). |
| V12 | A one-line entity row centres its status dot on the title (phone and desktop); a row with a second line keeps it on the title's line. |
| V13 | Already one line at 1280 (44px pill) after plan 97; no change. |
| V14 | Users table columns rebalanced (user 29 %, role 22 %, frames 12 %, last sign-in 12 %): addresses stay whole at 1280. |
| V15 | The More caret is centred over the dots instead of sitting in the pill's corner (where it met the active pill). The switch cell keeps its 69px and padding: geometry tests pin equal cells and whole labels at 360, and a wider switch truncated "Location"; the label/outline gap is unchanged. |
| V16 | The tab bar shows for a signed-in user on the 404, 403 and credits pages (their frames are put in the request scope for the shell); the 404 copy uses typographic apostrophes in English. |
| V17 | The calendar connect page is one card titled "Connect a calendar" (the look picture is gone); every form view has room under the docked Save bar. |
| V18 | The phone route is always on its own line; sorted by airline or direction each group is named by its airline or direction; the lead thumbnail has a hairline (the empty gutter in the audit was a plain white fixture render). |
| V19 | Not changed: the stray label is a real airport marker's label peeking out between the sidebar and the Location card, not a stylesheet defect. |
| V20 | The dark radial glow behind the frame button on the desktop map is removed (the button has its own opaque surface). |
| V21 | On a phone the Save bar shows the short "Modifications non enregistrées" (the list of areas is for wide screens). |
| V22 | The airline sheet's callsigns are chips, "Last seen" is a date like "First seen", and the sheet drops the picture slot when there is no picture. "Air Algerie" is the built-in name (it feeds the frame's render and the illustration key), so it is not changed here. |
| V23 | French says "allure" everywhere (tab, title, section, delete dialog); a catalogue test refuses "look spécial". |
| V24 | Form views have bottom padding for the bar, and typing arms the leave guard. |
| V25 | A frame that never contacted SkyPane shows no Battery row (the banner and the state word already say it once). |
| V27 | Kept: the owner row's action drops under the address when it does not fit, the address is never broken. |
| V28 | Verified: "Invited" means the user has no bound sign-in identity (`has_identity`), which is correct for real data; the audit's fixtures mint cookies without one. No change. |

## B. Workflow findings

- Login `?next=`: every authenticated GET page route of the route table is kept (`/account`, `/users`, `/fleet`, `/devices/<id>/...` through the device-scoped routes), less the retired redirect routes; the open-redirect protections and their tests are unchanged and extended. `companion/next_route.py` holds the check and `login_redirect()`.
- Session expiry: a signed-out visit that carried a session cookie, and the session-guard redirect, add `expired=1`; the login card shows "Your session expired" / "Votre session a expiré" (never over a sign-in error).
- Owners get a "Frame name" row in the Home Frame group linking to the Rename page (owner and administrators only, not co-managers).
- CSRF: the settings form, the quick switches (including the LED and the toast Undo form) and the calendar look form now carry the session token and the routes require it; the in-page script already forwarded it. SameSite and the Origin gate stay. ~30 existing tests that posted without a token send one now (shared helpers `with_csrf` or a token appended by the rig).
- Pairing: an unnamed frame is called "Unnamed frame" wherever it is named (never `d_xxxxxxxx`), and its Rename field starts empty; a refused code is answered by a 303 to `/pair-frame?refused=1` (no 200 POST page, the typed code is not kept or echoed).
- A refused special-look key re-renders the New special look form (400) with the typed kind, key and look and the key's own error.
- No-script airlines editor: every per-illustration upload form already shows a 44px Upload button once its menu is open (the audit looked at closed menus); a test pins it.
- Leave guard: the form pages (New special look, Calendar connect, calendar look) arm `beforeunload` once their values differ from the loaded ones (the settings pages already did).
- Flights: Enter, chips, sort and Clear add a history entry; live typing and Load more replace it; Back/Forward reload the shown state.
- L8: kept hidden on phones, by design: showing the offer (sentence plus a 44px button) lifted the sheet's top from about 600 to 400 of 844px and over the pin the visitor had just dropped (the pin-drag browser test caught it). The Airport mode offers the airports on a phone.

## C. Performance

- N01: `companion/history_cache.py` keeps the folded history per database file and invalidates on the file's modification time and size plus the row count and highest id (events are insert-only; WAL commits move the count at once); Flights, the Airlines collection and the Airline editor use it, and the airline key function is memoised.
- N03: `companion/js_minify.py` strips comments from served scripts (served bytes only; strings, regexes and template literals are copied verbatim; indentation kept): 335,488 to 225,955 bytes. Every served script is checked with `node --check` in a test.
- N02: idle prefetch warms the two likeliest tabs only (Home: Flights, Personalisation; Flights: Home, Personalisation; elsewhere: Flights, Home); intent warming is unchanged; `/` and `/airlines/manage` are never prefetched.
- P16: the hidden look panel's picture is lazy and the small look pictures exist only in `<noscript>` (the inline picker replaces them); a Departures page went from 28 preview requests to 1-2. The all-views render (nothing hidden) keeps its three pictures eager, so that shipped test stands.
- N06: cacheable images (previews, illustrations, gallery) carry a strong ETag and answer `If-None-Match` with a bodiless 304.

## Tests run

- Gates: ruff, mypy (29 modules), `check_comment_history.py check`, `check_function_size.py check --max 80 server stub-server`, `stub-server/test_phase47_freeze.py` (21 passed); `companion/app.py` is 1483 lines.
- Non-browser: `pytest companion test-support stub-server -m "not browser" -n 6`: 6924 passed, 4 skipped (includes the render baseline, the sign-in digests and goldens, `test_page_scripts`, `test_companion_app_0*`, `test_stylesheet_structure`, `test_suite_guards`, `test_structure_guards`, `test_sign_in_surfaces`, `test_components_page`).
- Browser: every `companion` test marked `browser` (`-n 6`): 2664 passed, including the whole `test_browser_overhaul_sweep.py`, `test_browser_components_page.py` and the finite-animation guard; the new `test_browser_audit3_fixes.py` and `test_browser_quiet_hours_modal.py` were also run four times in parallel (4 x 34 passed).
- New tests: `companion/test_audit3_fixes.py`, `companion/test_browser_audit3_fixes.py`, `companion/test_history_cache.py`, `companion/test_js_minify.py`.

## Deviations from Plan

- Existing tests retargeted in place (never weakened): New pill position, quiet-hours twin, tab bar More marker, idle prefetch set, expiry `next` Location and the logout `next`, device-id existence check (id masked), Flights airline groups (unit and browser), French terms, special-look refusal (400 form), pairing refusal (303), connect page (no picture), JS comment ratio floor, `beforeunload` listener lookup, the picture dialog (opaque panel instead of picture alone, two tests), the Fleet column (full content width instead of a centred 840px column, two tests), detection bar message (wide screens list the areas, phones show the short message), the Origin gate's fetch (sends the token), the overhaul sweep's frame-name exemption, baselines and digests.
- The Undo form of a quick-switch toast (`toast_post_action_html`) had no token and would have been refused once the quick routes required one: it carries the token now (found by `test_toasts`).
- L8 (phone nearest-airport offer) is kept hidden, see above; V19, V22's "Air Algerie", V27 and V13 are skipped for the reasons in the table; V28 verified correct.

## Known limits

- `/ui-theme` and `/ui-lang` still rely on SameSite and the Origin gate (outside this plan's scope).
- The Home Rename row, the 24-hour twin and the airline sheet chips use existing components (`ui_groups.row`, the field twin, `.type-chip`); no new component family was added, so the Components page is unchanged. The catalogue notes the picture dialog and the one-line dot rule.
