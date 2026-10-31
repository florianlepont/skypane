---
phase: 53-detection-modes-airport-runway-and-position-radius
plan: 08
subsystem: companion
tags: [detection, companion, position-mode, locations, dirty-state]
requires: [53-06]
provides:
  - position panel (location select, whole-km radius_km) on /detection
  - minimal location create/edit form scoped to the device owner
  - leave-guard bypass and carried unsaved values in dirty-state.js
key-files:
  created:
    - companion/test_detection_position.py
  modified:
    - companion/pages/detection_page.py
    - companion/detection_actions.py
    - companion/i18n_fr/detection.py
    - companion/static/style.css
    - companion/static/dirty-state.js
    - companion/test_detection_page.py
    - companion/app.py
    - companion/flash.py
    - companion/test_i18n.py
requirements-completed: [DET-03]
completed: 2026-10-31
---

# Phase 53 Plan 08: Position mode, locations and page-local navigation Summary

Position mode now works end to end on `/detection`: an owner (or an admin acting for the owner) picks a saved location and a whole-kilometre radius, can add or edit locations from the same page, and the page's own searches no longer trip the leave-guard or lose a typed radius.

## Commits

- e1b8b05 position panel, locations card, POST branches, French strings, stylesheet items 6 and 7, tests
- d937d54 dirty-state.js block (data-detection-nav, data-dirty-carried), carried-value tests

## Behaviour

- Subject of the Locations card, select and form is the device owner (admin acting on another user's device sees the "Locations of this frame's owner" wording; ownerless device: the admin's own list; non-admin: always their own). Rows are read with `fleet_db.list_locations_for(..., is_admin=False)` so an admin never sees every location here.
- Position POST validates (posted mode only): location id (missing, malformed, not the subject's -> "not available"; rounded coordinates outside the France box -> message without numbers), radius by `^\d{1,3}$` then `validate_radius_km`. Then `set_device_location_checked`, then `apply_position_selection`; any `PermissionError`/`ValueError` maps to the field message, `OSError`/`sqlite3.Error` to the save-failed flash. A runway post ignores location and radius and vice versa. No `required` on detection-form controls, form is `novalidate`.
- Location form (own POST, `action=save_location`): name 1-60, comma or dot decimals (max 6 decimals, no exponent/NaN), France box on rounded values, Europe/Paris only; edit re-checks ownership inside a transaction; the stored owner is always the subject (a forged `owner_user_id` is ignored).
- The select/summary print only rounded coordinates; the location list shows the stored ones. Out-of-box locations are disabled with " — outside France". With no location the panel shows the empty state, an "Add a location" link and no radius field.
- GET gets the location scope through `Handler._detection_locations()`, so a saved position setting now shows `Aircraft within 9 km of Home`, `NEARBY · 9 KM`, `Watching Within 9 km`; an unusable location still shows the legacy Orly values with the "No usable location" docked toast.
- dirty-state.js: one block. `submit` on `form[data-detection-nav]` and a plain primary click on `a[data-detection-nav]` copy the live `mode`, `radius_km`, `location_id` into hidden inputs or the link query (fragment and other keys kept) and set `suppressGuard`; `pageshow` with `persisted` re-arms the guard. A bar with `data-dirty-carried="<plain url>"` stays visible at init, counts as one unsaved change ("Detection changed"), and its Cancel navigates to that URL. The server sets the attribute when the URL carries a differing mode, radius or location, and after a rejected detection POST. Invalid carried radius (non-digits) is ignored.

## Verification

- `pytest companion stub-server/test_phase47_freeze.py` (all of companion including browser tests): 4381 passed, 3 skipped (root permission bits).
- Browser tests DID run: `PLAYWRIGHT_BROWSERS_PATH` pointed at a scratch directory (outside the repo) holding symlinks `chromium*-1248 -> /opt/pw-browsers/*-1243`; nothing committed changed, no `playwright install`. Additionally an uncommitted probe drove the real flow at 360 px with scripts on: radius 12 typed in position mode, switch to Airport and runway, search "cdg" (guard not armed at submit, URL carries `radius_km=12&location_id=1`), pick LFPG (guard not armed), switch back -> radius reads 12, bar visible and the guard armed, Cancel -> plain `/detection`, radius 9, bar hidden. The probe file was deleted.
- ruff clean, mypy clean (28 files), function-size gate (905 functions, none over 80), comment-history check exit 0, `test_companion_app_02`/`03` dirty-state token tests pass unchanged.
- `git diff dirty-state.js`: additions only except the init line `bar.hidden = true` -> `bar.hidden = !carried` (the single guarded condition the plan allowed).

## Deviations from Plan

**1. [Rule 3 - Blocking] Files outside the plan's list**
- `companion/app.py` (new `Handler._detection_locations`) and `companion/flash.py` (`location_saved` flash key, success tone): the GET lambda in `routes.py` cannot import `detection_actions` (import cycle through `flash`), so the scope is obtained through a handler method; `routes.py` only changed its lambda to call it.
- `companion/routes.py`: one-line lambda change for the above.
- `companion/test_i18n.py`: `detection.field_latitude`, `detection.field_longitude` and `detection.location_option` added to the identical-in-French allowlist (Latitude/Longitude are the same word; the option is a name plus numbers).

**2. [Rule 1 - Bug in earlier test] 53-06 tests updated**
- `test_runway_cards_show_real_designators_for_cdg`: the "no `required`" check now excludes the location form, which keeps native `required` as the plan allows.
- The interim rejection case `mode=position` -> "Choose a detection mode." is now "Choose a location." (position is a real mode).

**3. [Design] Unsaved-state baseline for carried values**
- The select's baseline is the device's location when usable, else the first usable one, so a freshly loaded page is not reported as carried-dirty. A carried bar is made dirty in the script by giving the snapshot a marker for `mode` so the "Detection changed" label is produced by the existing section logic.

## Known Stubs

None.

## Threat Flags

None. T-53-34 to T-53-38 mitigations are covered by `test_detection_position.py` (cross-user location ids, foreign Origin 403, escaped names, rounded coordinates only).

## Self-Check: PASSED

Files and both commits exist (`git log` shows e1b8b05 and d937d54); STATE.md and ROADMAP.md untouched as instructed.
