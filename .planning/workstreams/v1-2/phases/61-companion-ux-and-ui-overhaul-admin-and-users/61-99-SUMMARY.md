---
phase: 61-companion-ux-and-ui-overhaul-admin-and-users
plan: 99
subsystem: companion-ui
tags: [audit-3, d52, tab-bar, location-map, csrf, glossary, safari-tint, place-search]
key-files:
  created:
    - companion/airline_display.py
    - companion/test_browser_place_label_clearance.py
    - companion/test_browser_place_search_loading.py
    - companion/test_browser_remaining_audit_fixes.py
  modified:
    - companion/static/style.css
    - companion/static/place-card.js
    - companion/pages/place_page.py
    - companion/pages/users_page.py
    - companion/pages/co_managers_card.py
    - companion/pages/components_page.py
    - companion/pages/airline_table.py
    - companion/pages/airline_sheet.py
    - companion/airline_collection.py
    - companion/post_actions.py
    - companion/ui_nav.py
    - companion/ui_segmented.py
    - companion/ui_base.py
    - companion/routes.py
    - companion/login_page.py
    - companion/app.py
    - companion/i18n_fr/*.py
metrics:
  completed: 2026-11-09
---

# Phase 61 Plan 99: Remaining audit-3 UX points (D52) Summary

Every remaining audit-3 point of D52 is either fixed below or recorded with its reason. Screenshots are in `scratchpad/shots99/` (see the note at the end). `companion/app.py` is 1485 lines (net +2: the 404 page clears the request token), `place-card.js` 410, `place-map.js` untouched at 1486.

## 1-10: the plan's items

| # | Point | Outcome |
|---|-------|---------|
| 1 | V15 tab bar | Labels are 11px (was 12px) and the space switch cell is 76px (was 69px) with 4px pill padding, so "Mon cadre" / "My frame" keep clear air inside their outline and "Location" (the longest destination label) fits its equal cell at 360px. Contract of `assert_bar` (test-support/nav_spaces_support.py): the destination cells stay within 1px of each other, the switch cell is the one fixed, wider cell, and every label keeps at least 6px (3px each side) inside its pill. |
| 2 | V19 stray label | `place-card.js` hides (visibility, still measured) any airport code label that meets the details card, the sheet, the search, the mode chips, the tools row or the map's own edge, and shows it again once clear; the sweep also runs every frame while a pan or zoom glides. Browser test at 1280 and 390: after panning six times no painted label meets a floating box (and the test proves labels were hidden at some point). |
| 3 | V22 Air Algérie | New `companion/airline_display.py` (display-name mapping only). The Airline collection, the editor (name field, filter text keeps the built-in spelling too) and the airline sheet show "Air Algérie"; the built-in key `Air Algerie`, the hidden `airline` field, the illustration key and everything the frame render reads are unchanged. Posting the displayed spelling back is a reset, not a rename. |
| 4 | V27 owner row | Person rows (owner and co-managers) never wrap: the action stays on the row's first line, the address truncates with an ellipsis and its full value is the element's `title`. Browser test at 360/390, EN/FR, plus a forced long address. |
| 5 | V28 Invited | Logic unchanged (no bound sign-in identity). Wording: "Invited, not signed in yet" / "Invité, pas encore connecté", with a `title` and an `aria-label` explaining that the mark goes away at the first sign-in. |
| 6 | L8 phone offer | On phones the script moves `#place-nearest` into the tools row (above the Save/locate buttons, over the map) and the CSS shows only a one-line 44px follow button (the sentence stays for screen readers). The sheet no longer grows: the first attempt (a one-line chip inside the sheet) lifted the sheet over the dropped pin and broke the pin-drag test, so it was replaced. New browser test at 360/390: one line, sheet within 28% of the viewport, pin above the sheet top, the pin can still be grabbed and dragged, tapping the button follows the airport; the existing pin-drag test is green. |
| 7 | CSRF on /ui-theme and /ui-lang | Both routes are in `CSRF_ROUTE_KEYS`; the segmented forms carry the token (`segmented_buttons_html(hidden_html=...)`), no-script and script alike. 404 bodies are now identical whoever asked (the 404 page clears the request token; an administrator's unknown-device 404 had carried one). SameSite and the Origin gate are unchanged. ~12 existing tests that posted the forms without a token now send one. |
| 8 | Glossary | See below. |
| 9 | Safari bands | See below. |
| 10 | 14 PARTIAL rows | See below. |
| 11 | Place search feedback (added during the plan) | See below. |

### 8. Naming glossary

Rule (written in the catalogue reference and shown live on the Components page, family "Page names"): one name per page; title, document title, sidebar and headings use the full name; the phone tab shows a word of that name, never another word.

| Page | Full name (EN / FR) | Tab bar (EN / FR) |
|------|---------------------|-------------------|
| Home | Home / Accueil | same |
| Flights | Flight history / Historique des vols | History / Vols |
| Location | Location and detection / Lieu et détection | Location / Lieu |
| Style | **Style / Style** (was Personalisation / Personnalisation) | Style / Style |
| Airlines | Airlines / Compagnies | (More sheet) |
| Airline editor | Airline editor / Éditeur de compagnies | Editor / Éditeur |
| Users | Users / Utilisateurs | Users / Équipe |

Applied: the only tab whose word was not in its page name was Style/Personalisation, so the page, its document title and its section nav ("Style sections" / "Sections de style") now say Style in both languages (`nav.display_short` removed). French "allure" is the one word for look (already so after V23; no "look" in French strings). Documented exception: FR Users keeps the tab "Équipe" because "Utilisateurs" does not fit a cell (the title and every heading say Utilisateurs). Tests that pinned the old wording were retargeted in place: `test_nav_personal_console`, `test_browser_nav_spaces`, `test_status_pages_05`, `test_personalisation_page`, `test_config_page_04b/05`, `test_i18n`, `test_companion_app_04`, `test_browser_personalisation_selector`, `test_browser_overhaul_steps`; the title round-trip test allows the identical French word "Style" (`SAME_IN_FRENCH`).

### 9. Safari bands around the Location map (cannot be verified without a device)

Implemented, only on the Location page, only while the map runs, only at phone widths (`max-width: 699.98px`) and only in a browser tab (`display-mode: browser`, so the installed web app and its translucent status bar are untouched):
- two fixed 4px strips along the top and bottom edges in `--color-secondary`, which is the map's own background (light and dark);
- `place-card.js` points both `theme-color` tags at the same colour for that page (Safari tints its top bar from them).

Honest limits: no iPhone was available. Whether Safari samples a 4px strip, and which Safari versions tint the bottom bar from fixed elements, is Safari's behaviour and is not verified here; the browser tests check the strips' geometry and colour, the theme-color tags and the absence of both on a wide screen. The map tiles are not themed (light in both themes), so in the dark theme the bars take the dark placeholder colour, not the light tile colour. Existing pixel checks that required the edge rows to be tiles were retargeted: they read just past the strips (and check the bottom strip's colour); the top strip lies under the app bar and is covered by the computed-style test.

### 10. The 14 PARTIAL workflow rows (WORKFLOWS3.json)

| Row | Outcome |
|-----|---------|
| L8-owner-phone-en | Fixed here (item 6). |
| NL2-admin-desk-en (login next=/users) | Fixed in 61-98, verified: `test_audit3_fixes` (`login_redirect("/users")` keeps `next`) and the browser test of the sign-in landing; green. |
| NF-note (Flights sort and search history) | Fixed in 61-98 (Enter, chips, sort and Clear add history entries), verified by `test_browser_audit3_fixes`. |
| NR1-note (owner Rename) | Fixed in 61-98 (Frame name row on Home), verified. |
| NSL4 (refused special-look key) | Fixed in 61-98 (400 form, typed values kept), verified. |
| NS4 (session expired, return to page) | Fixed in 61-98 (`next` for device-scoped paths), verified. |
| NS1b (login explains expiry) | Fixed in 61-98 ("Your session expired"), verified. |
| NS2b (unsaved edits after expiry) | The user returns to the same page (61-98). The unsaved edits themselves are deliberately not kept (storing form values across a session end would put page data where no session guards it); the expiry card now says so: "Changes you had not saved were not kept." / FR. |
| NCS-settings (settings CSRF) | Fixed in 61-98 (settings and quick routes), verified; `/ui-theme` and `/ui-lang` closed here (item 7). |
| ND4b (leave with unsaved changes) | Fixed in 61-98 (`beforeunload` guard), verified. |
| NJ1b (no-JS airline upload buttons) | Fixed in 61-98 (44px Upload button in every opened menu), pinned by a test, verified. |
| NPA1b (pairing success shows the id) | Fixed in 61-98 ("Unnamed frame"), verified. |
| NBF1b (reload after a refused code) | Fixed in 61-98 (303 to `/pair-frame?refused=1`), verified. |
| LN (login next, all routes) | Fixed in 61-98 (`companion/next_route.py`), open-redirect tests extended, verified. |

### 11. Place search feedback

Typing 3 or more characters shows, at once and under the airport matches, a last list row with a small spinner and "Searching…" / "Recherche en cours…" (the existing finite `.place-loading__spinner`, reduced-motion safe). The geocoder's answer replaces it with the places, with "No place found" / "Aucun lieu trouvé" for an empty answer, or "Search unavailable right now" / "Recherche indisponible pour le moment" on failure. The pause before the request is 500 ms (was 700); the throttle is unchanged and still holds (one request in flight, at least 1.5 s between starts, cached by query; a burst of typing sends one request). A real fix in passing: a late answer for an older query was displayed (the freshness check compared the typed text with itself); it compares with the query now. Browser test with a held (delayed) fake geocoder: row visible before the answer and gone after, empty, error, French, throttle.

## Components page and catalogue

`/components` gained the family "Page names" (live table of tab label and page name, EN/FR) and a Lists state "Place search: pending, nothing found, failed". The catalogue reference (`.claude/skills/sketch-findings-skypane/references/component-catalogue.md`) documents the status row, the phone offer and the glossary.

## Deviations from Plan

- [Rule 1 - Bug] 404 bodies differed between an unknown path and an administrator's unknown device once the theme form carried a token; the 404 page now clears the request token (`app.py`, +2 lines).
- [Rule 1 - Bug] The late-answer check of the place suggestions compared the typed text with itself (fixed, see item 11).
- Existing browser pixel tests of the full-bleed map and one place-pins assertion were retargeted (strips; a slow machine can reach the new 500 ms pause, so the "no request" assertion became "no request other than for what was typed").
- Item 6's first design (chip inside the sheet) was abandoned for the tools-row placement, see above.
- `test_status_pages_06/07` (CSS source tests of the tab bar) and `test_browser_more_sheet` pinned 12px labels and a switch within 16px of the equal cells; retargeted to 11px and 76px against about 52px. `test_browser_co_managers` pinned "the long address wraps" and the button wrapping under it; retargeted to the D52 contract (one line, ellipsis with the full value in the title, button beside the address).

## Known Stubs

None.

## Threat Flags

None (the CSRF change closes a gap; no new endpoint).

## Tests run

- Gates: `ruff check .`, `mypy` (29 modules), `scripts/check_comment_history.py check`, `scripts/check_function_size.py check --max 80 server stub-server` (942 functions, none over 80), `stub-server/test_phase47_freeze.py` (21 passed).
- Non-browser: `pytest companion test-support stub-server -m "not browser" -n 8` run once mid-plan (8 failures, all retargeted above), plus the affected files re-run after each fix.
- Targeted run (`-n 8`): `test_browser_overhaul_sweep.py` (whole, includes the finite-animation guard), `test_page_scripts`, `test_companion_app_0*`, `test_stylesheet_structure`, `test_suite_guards`, `test_structure_guards`, `test_sign_in_surfaces`, `test_render_baseline`, `test_components_page`, `test_browser_components_page` and every browser file matching nav, tab, users, fleet, place, location, airline, account, login, theme, more_sheet, status_bar, remaining, audit3, foundations, motion, co_managers, page_title, segment: 2136 passed, 11 failed (all pinned the old 12px tab labels or the wrapping address; retargeted and re-run green: `test_browser_more_sheet`, `test_browser_co_managers` 47 passed). The new and changed browser files were stressed in 4 parallel processes (4 x 68 passed).
- Render baseline, sign-in digests and goldens were regenerated deliberately (`companion_render_snapshot.py --write`; digests in `test_sign_in_surfaces.py`).

## Not done / limits

- Safari tint cannot be verified without a device (item 9).
- Screenshots in `scratchpad/shots99/`: `tab_bar_360_fr_admin.png`, `location_390_offer.png` (only these two were taken).
