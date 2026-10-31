---
phase: 56-per-hardware-rendering-battery-profiles-health-and-credits
plan: 03
subsystem: companion
tags: [credits, i18n, public-route, compliance]
requires: []
provides:
  - public bilingual GET /credits page driven by companion/credits.json
affects: [companion/routes.py, companion/app.py, companion/login_page.py]
key-files:
  created:
    - companion/credits.json
    - companion/credits_page.py
    - companion/i18n_fr/credits.py
    - companion/test_credits_page.py
  modified:
    - companion/routes.py
    - companion/app.py
    - companion/login_page.py
    - companion/test_access_matrix.py
    - companion/test_route_table.py
    - companion/test_sign_in_surfaces.py
    - companion/testdata/render_baseline.json
requirements-completed: [HWR-02]
duration: ~25 min
completed: 2026-10-30
---

# Phase 56 Plan 03: Public credits page Summary

Public, bilingual /credits page rendered from one validated JSON file, citing adsb.fi (linked to https://adsb.fi), adsb.lol, adsbdb and OurAirports, reachable from the login card.

## Commits
- 0e227473: data file, `load_credits` validator, markup, French strings, unit tests
- 753c8b80: `GET /credits` PUBLIC route, `_handle_credits_get`, access-matrix row, HTTP tests
- 40cd8c4c: "Credits" accent text link on the login card (EN/FR) plus baseline updates

## Behaviour
- `load_credits` raises ValueError for: bad JSON, unknown version, extra/missing keys, missing/duplicate/required ids, non-https or host-less URL, adsb.fi URL off its host, missing description.en/fr.
- All text goes through `escape_html`; links are https only with `rel="noopener noreferrer"`; file path is fixed (`DEFAULT_PATH`).
- Route is PUBLIC and not device-scoped; `/devices/<id>/credits` is refused. Health alert is admin-only (as the 404 page).

## Verification
- `pytest companion -n auto --no-cov`: 3573 passed, 561 skipped (browser tests skip: Chromium not installed in this sandbox, so the 360 px check was not run in a browser; HTML assertions only).
- ruff, mypy, comment-history check clean.

## Deviations from Plan
**[Rule 3 - Blocking] Existing pinned tests covering the login page / public route set.** Adding the route and the login link broke `test_route_table.py` (public-route lists), `test_sign_in_surfaces.py` (login SHA-256 pins) and `companion/testdata/render_baseline.json` (login snapshots; regenerated with `companion_render_snapshot.py --write`, only the four login entries changed). Updated in the Task 3 commit.
Also: message id `credits.license` (English "License") instead of "Licence", because the i18n sweep rejects a French value identical to the English one.

## Known Stubs
None.

## Self-Check: PASSED
