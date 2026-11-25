---
phase: 68-console-and-companion-visual-improvements
plan: 46
subsystem: companion
tags: [airlines, roles, fleet-wide, access-control, leak-tests]
requirements: [CON-01]
key-files:
  created:
    - companion/fleet_unresolved.py
    - companion/airline_fleet_world.py
    - companion/test_airline_fleet_roles.py
    - companion/test_browser_airline_fleet_roles.py
  modified:
    - companion/pages/airlines_page.py
    - companion/pages/airline_collection_page.py
    - companion/device_scope.py
    - companion/i18n_fr/airlines.py
    - companion/test_status_pages_05b.py
    - companion/testdata/render_baseline.json
metrics:
  completed: 2026-11-23
---

# Phase 68 Plan 46: Airlines by role (administrator: whole fleet, user: own frames)

## Current behaviour found (before this plan)

| | User | Administrator |
|---|---|---|
| Page | Personal "Airlines" collection, `/devices/<id>/airlines` (`OWNER_DEVICE`, read-only) | Console "Editor", `/airlines/manage` (`ADMIN_DEVICE`); the admin also has the personal page |
| Sightings feeding it | Only the one frame opened (`ctx.state_dir`); a user with two frames saw one at a time | Editor: `collection_across` over every frame in the request scope (an admin's scope is the whole fleet) |
| Airlines listed | Built-in catalogue (unseen ones dimmed) plus uncurated airlines that frame saw | Built-in catalogue, hand-named, promoted and known-by-name rows; an uncurated airline seen by a frame (no prefix named) had NO row |
| Unresolved prefixes | Not shown at all | Only the poll state of the single frame in the URL (the un-prefixed Editor = the admin's default frame); other frames' prefixes were invisible and a prefix seen only elsewhere was refused as stale |
| Naming a prefix, uploading artwork, rename, delete | Refused (all `ADMIN_DEVICE`) | Allowed; names and artwork are fleet-wide (plans 41, 42) |

## What changed

- `companion/fleet_unresolved.py` (new): `scope_dirs(state_dir)` (frames in the request scope plus the page frame, deduplicated) and `merged_registry(dirs)`: counts added, earliest first seen, latest last seen, sample callsign of the frame that saw it last (the earlier directory wins a tie), malformed entries skipped. Read-only.
- `airlines_page._gap_rows_for_grid` and `unresolved_row_for_prefix` (the single read/write membership test used by the resolve POST, the suggest routes and the dialog) use the merged registry. The threshold (3), cap (12) and `(-count, prefix)` order are evaluated on the merged counts; a prefix with a manual resolution is still excluded. The resolve POST now accepts a prefix any frame saw.
- Editor: airlines seen by any frame that no list knows (e.g. adsbdb names) get a "known by name only" row (with the Artwork button) via `_seen_only_names`; sightings were already merged. Artwork is already fleet-wide (plan 42).
- User page: `device_scope.own_history_dirs` gives a plain user's scope (owned and co-managed frames) and nothing else; `airline_collection_page._entries_for` merges those frames' sightings. Anyone else (admin on the personal page) keeps the single page frame. One-line caption "Airlines your frame has seen" (FR "Les compagnies vues par votre cadre", `airlines.collection_purpose`, in `companion/i18n_fr/airlines.py`).
- No route, role or permission changed; render baseline regenerated once (4 lines: the new caption).

## Follow-up after the owner's answers (second commit)

- The user page is PER FRAME again: the merge across a user's frames and `device_scope.own_history_dirs` are gone; the page for frame X reads only frame X's history. Isolation stays: the route gate (`OWNER_DEVICE`) lets a user reach only own or co-managed frames.
- The user page lists ONLY airlines the frame saw. Removed with everything that only served them: the dimmed "Not yet seen" cards, the "x of N spotted" headline and progress bar, the All/Spotted/Not yet seen chips and the `show` query parameter, the "goal complete" sentence; EN/FR strings `collection_progress`, `_one`, `collection_complete`, `collection_show*`, `collection_not_seen` (no orphans); CSS (`.collection-progress__headline`, `__bar` rules, `.collection-card--unseen`, `.collection-sheet__unseen`, chip rules of the control bar); JS defaults/comments in `list-filter.js`. Kept: next-badge goal, badge pill, sort, search, legend. A frame with no sighting shows only the empty state. A fleet-wide name or picture shows on an airline the frame saw.
- Tests adapted to the new intended behaviour: `test_airline_collection_page.py` (progress/unseen/chips tests rewritten: only seen cards, empty state, goal sentence, no `show` filter), `test_browser_airline_collection.py` (docstring, selectors, progress line became the goal line, phone header is one bar line, no-script/sort tests without chips, sticky test uses a 400 px window because three cards no longer scroll a phone page; removed: dimmed-card contrast test, show-chip offline test, chip tab-swap test, progress-sentence test (replaced by a goal-sentence test)), `test_browser_page_opening.py` (removed the airlines-chips thumb test), `test_browser_segment_centring.py` (`/airlines` has no chips now), `test_personal_space_parity.py` (count read from the "Airlines: 1" status), plus my own `test_airline_fleet_roles.py` (per-frame test, seen-only test). Render baseline regenerated once more.
- Verified: 134 companion test files (airline, device_scope, principal, collection, /airlines) plus render baseline, i18n, suite guards: 7187 passed, 3 skipped; ruff, mypy, function size, comment history clean; `companion/app.py` 1497, no JS over 1500.
- Captures: `scratchpad/p46/after2/` (user page, 390/1440, EN/FR, light).

## Decisions (user side; superseded where noted above)

- Unidentified prefixes: a user could never name or see them, so they see none; tests assert no prefix, no resolve form or route in their page.
- (Superseded) the merge across a user's frames was reverted: the page is per frame.

## Tests

- New `companion/test_airline_fleet_roles.py` (15, HTTP): two users, two frames plus the live frame, one admin; exact gap rows (prefixes, sample callsign, merged counts) on the Editor opened on any frame, merged views, seen-only rows, fleet artwork, resolving a prefix only another frame saw, stale prefix still refused, exact seen lists per user, no prefix/forms for users, leak test (other user's airline, prefix, callsign, type label, frame name, manual name and cached suggestion absent from the page and its dialogs), user cannot open the other frame or the Editor, no write ability (resolve refused, registry and artwork dir unchanged), co-managed frame merged, merge unit tests (sums, extremes, order independence, malformed), cap and threshold on merged counts.
- New `companion/test_browser_airline_fleet_roles.py` (12, browser): Editor and both users' pages at 360 and 1280 px, EN/FR, no horizontal overflow, caption, leak check on the full page content.
- Adapted (one): `test_status_pages_05b.py::test_airlines_page_reads_the_poll_state_and_only_reads_history` asserted the page module binds `state_store`; it now asserts the fleet merge module reads the poll state through `state_store` and the page binds the merge.
- Ran (SKYPANE_REQUIRE_BROWSER=1): all 95 companion test files mentioning airlines_page, airline_collection, airline_table, airline_rows, manual_resolutions, device_scope or principal plus `test_render_baseline`: 5450 passed, 2 skipped (root permission bits), the two failures were the adapted test and the baseline (regenerated). Then suite guards, i18n, the new files: 450 passed. ruff, mypy (49 files), function size (1221, none over 80), comment history, `companion/app.py` 1497 lines all clean. Not run: the full suite.

## Security reasoning

Scope, not the page, decides which frames are read: an admin's scope is the fleet, a user's is exactly their owned and co-managed frames (`load_devices_for`), and `own_history_dirs` for a user never adds the page frame, so another user's directory cannot be reached even by a forged URL (the `OWNER_DEVICE` gate already refuses foreign frames). The merged-prefix membership test is reachable only through `ADMIN_DEVICE` routes. Fleet-wide names and artwork reach a user only through their own sightings.

## Owner decisions

Answered: (1) only airlines the frame saw; (2) per frame; (3) no unidentified prefixes for users. None open.

## Before/after captures

`/tmp/claude-0/-home-user-skypane/1ebaf6ab-90c3-5997-a366-609c87d2992c/scratchpad/p46/{before,after}/` (admin-editor and user-airlines, 390 and 1440 px, EN/FR, light).

## Self-Check: PASSED
