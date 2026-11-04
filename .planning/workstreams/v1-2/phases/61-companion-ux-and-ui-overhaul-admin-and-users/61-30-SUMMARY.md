---
phase: 61-companion-ux-and-ui-overhaul-admin-and-users
plan: 30
subsystem: companion
tags: [airline-collection, read-model, personal-space, badges, rarity]
requires: [61-17, 61-29]
provides: [read-only Airline collection at /airlines for every role, airline_collection read model, editing flows pointed at /airlines/manage]
key-files:
  created:
    - companion/airline_collection.py
    - companion/pages/airline_collection_page.py
    - companion/test_airline_collection.py
    - companion/test_airline_collection_page.py
    - companion/test_browser_airline_collection.py
  modified:
    - companion/routes.py
    - companion/app.py
    - companion/pages/airlines_page.py
    - companion/post_actions.py
    - companion/resolve_dialog.py
    - companion/health_sections.py
    - companion/i18n_fr/airlines.py
    - companion/static/style.css
    - companion/testdata/render_baseline.json
metrics:
  completed: 2026-11-04
---

# Phase 61 Plan 30: Airline collection

`/airlines` is now a read-only, lightly gamified collection for an administrator, an owner and a co-manager alike: progress headline and bar, five badges, filter chips, sort, text filter, a grid of picture cards with rarity and New pills, and a read-only sheet per card. The editing page lives only at `/airlines/manage` (administrator), and every editing flow now points there. Commits: b509d06 (read model), 1304fe8 (page, routes, strings, CSS, repointed tests, pins), 9bebb35 (browser proof, parity).

## What changed

- **Read model** (`companion/airline_collection.py`): `airline_collection(conn, now, overrides)` returns one entry per curated airline in list order plus one per uncurated airline seen, and a summary (spotted, total, earned badges, next goal). SELECT only, no table, no write. Constants `REGULAR_MIN=10`, `OCCASIONAL_MIN=3`, `BADGE_THRESHOLDS=(1,5,10,25,50)`, `NEW_WINDOW_DAYS=7`, `RECENT_CALLSIGNS=5`. NULL, empty and blank airlines appear nowhere ("Airline unknown" is a History display fallback for a NULL airline, never stored). Airline text is matched to curated names with `normalise_airline_key`; a renamed curated airline (owner override) keeps its card and history through `airline_sheet.card_sheet`.
- **No double counting (checked).** The poll loop stores a second `runway_events` row for one pass when the corroboration flag flips, 30 s apart. The collection counts flights: it applies the same `flight_card.fold_repeated_passes` fold Home and Flights use (same hex, callsign, route and direction under 60 s apart count once, newest kept). Counts equal the history page's flights; storage is untouched. Distinct passes (another day, another aircraft) each count. This refines the plan's "seen n times equals the events", which held for the seeded fixtures (all distinct passes); both behaviours are tested.
- **Page** (`companion/pages/airline_collection_page.py`): header, progress card first, empty state (when nothing spotted), one GET form (chip radios, search field, sort select, Apply), grid, one `ui_modal` sheet per shown card. Chip, sort and `q` are validated server-side (unknown values default, `q` capped at 60 characters, escaped). Dialog ids are `dlg-airline-<normalised key>`. Pictures use the existing illustration route, size constants and cache buster; no artwork gives the dashed placeholder. Dimming (opacity 0.45, grayscale) is on the picture only. `GET /airlines` handler moved out of `app.py` into the page module (`app.py` 1492 to 1470 lines); the administrator `?resolve=` 303 to the manage page is kept.
- **Editing flows pointed at the manage route.** The editing module's own links (resolve links, sheet links, back and skip links), the POST redirects in `post_actions.py` (rename, reset, delete, resolve, upload), `resolve_dialog.return_route`, and Health's per-row Resolve link (`/airlines/manage?resolve=%s`, direct instead of through the redirect) all use `MANAGE_ROUTE`. Without this, after a rename or delete an administrator would have landed on the read-only collection with the flash and sheet parameters.
- **Strings**: 38 EN/FR ids under `airlines.collection_*` (the i18n area must be an existing `i18n_fr` module); "Rare" is in the unchanged-in-French list.
- **CSS**: hand-written from existing tokens (progress, badges, grid 2/3/4 columns at 360/700/1280, card, rarity pill and dots, dimmed picture, facts list); no new size, weight, keyframe or duration.

## Tests

- `test_airline_collection.py` (21): rarity and boundaries, uncurated airline spotted but not in total, NULL/blank airlines, curated order, first/last/types/callsigns, New within 7 days, badge thresholds, empty history, a pass stored twice counts once, the same aircraft another day counts again, key normalisation, renamed airline, hostile text, read-only.
- `test_airline_collection_page.py` (17): the three roles get identical read-only pages (no file input, only a GET form, no `/airlines/...` link), counts, unseen cards, empty state, sheets with no form or input, server-side chip/sort/q, fallback and capping, hostile stored text escaped, French strings, resolve redirect for an administrator only, an owner's POST to an editing route is a 404.
- `test_browser_airline_collection.py` (17, Chromium): 360 and 1280 px x EN/FR x light/dark with no overflow, 2 or 4 columns, cards/chips/field/select/Apply at least 44 px and owning their centre, badge pills at least 44 px, headline first under the header, card opens its sheet with focus inside and Escape returns focus to the card, dimmed card keeps seen-card text colour and 4.5:1 contrast (both themes), chips/sort/field through Apply and the hash-link sheet with scripts blocked, instant text filter with scripts, 2 taps on a phone (More, Airline collection) and 1 on desktop (sidebar link). Stress: 4 parallel runs of this module, plus the airline list, sheet and Health-resolve browser modules, 0 failures after fixing one theme-transition race in the contrast test (it now waits for the theme repaint).
- `test_personal_space_parity.py`: collection identical for administrator and user (existing parametrised test) and a new read-only/count check in EN and FR.
- Repointed in place to `/airlines/manage` (intent and assertions kept): test_airline_sheet, test_browser_airline_list, test_browser_airline_sheet, test_browser_health_resolve, test_browser_flights_cards, test_browser_ux_01/02/04, test_health_resolve_dialog, test_device_actions, test_device_links (plus a new collection scope test), test_csrf, test_companion_app_03/05, test_status_pages_06/07, test_view_pages_02/03/04, test_i18n (collection title in the French page check). `test_companion_app_05`'s editorial-floor test additionally measures the editor page so its caption floors keep their strength; `test_browser_console` reference paths include the editor.
- `render_baseline.json`: 8 entries moved (`/airlines` x 4, `/health` x 4 for the Resolve link); sign-in digests did not move.

## Deviations from Plan

1. **[Rule 1 - Bug] Editing flows still pointed at `/airlines`.** See above; not in the plan's file list (post_actions, resolve_dialog, health_sections, airlines_page links) but required for the editor to keep working.
2. **[Rule 1] Per-flight counting** (fold of repeated passes) instead of one per stored event, as the owner asked; see above.
3. **Sort and chips apply through the Apply button; no auto-submit script.** The plan says Apply hides under the script gate where the select submits on change. That needs a new global script (registration in the shell script order, static routes, CSP and script tests, a tight `app.py` line budget). Apply stays visible with and without scripts; the instant text filter still uses `list-filter.js`. Easy to add later.
4. **Locked badge text** is 70% text colour (the muted colour used elsewhere, over 4.5:1); the dashed border and glyph are 50%. The spec's "50% text colour" for the whole badge would fail 4.5:1.
5. **Progress value** is capped at the total (uncurated airlines count toward "spotted" but not the total, as specified).
6. **`PANEL_LOOKUP` script dropped** from the `/airlines` script table (the collection has no lightbox); only `list-filter.js` is needed.
7. The step-count doc (`61-STEP-COUNTS.md`) has no row for V1; the measured 2 taps (phone) and 1 (desktop) are asserted in the browser test.

## Known Stubs

None.

## Gates

ruff, mypy (29 modules), comment-history, function size (931 functions, none over 80), Phase 47 freeze (21 passed): clean. Full companion + test-support + stub-server run with `-n auto` after the final code commit: 7351 passed, 4 skipped (root-only permission-bit tests, not browser tests), 0 failed. The coverage-gate script (`run-all-tests.sh`) was not run; this is not the last code plan.

## Self-Check: PASSED
