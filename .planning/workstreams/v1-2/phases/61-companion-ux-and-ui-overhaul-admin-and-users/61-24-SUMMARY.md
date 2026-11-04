---
phase: 61-companion-ux-and-ui-overhaul-admin-and-users
plan: 24
subsystem: companion
tags: [leaflet, csp, permissions-policy, compliance]
requires: [61-23]
provides: [vendored Leaflet 1.9.4, per-route CSP and Permissions-Policy, map-source credits and compliance]
key-files:
  created:
    - companion/page_policy.py
    - companion/static/vendor/leaflet/leaflet.js
    - companion/static/vendor/leaflet/leaflet.css
    - companion/static/vendor/leaflet/LICENSE
    - companion/static/vendor/leaflet/VENDOR.md
    - companion/test_vendored_leaflet.py
    - companion/test_page_policy_headers.py
  modified:
    - companion/app.py
    - companion/routes.py
    - companion/detection_actions.py
    - companion/static_files.py
    - companion/credits.json
    - COMPLIANCE.md
    - companion/test_compliance_credits.py
    - companion/test_credits_page.py
metrics:
  completed: 2026-11-03
---

# Phase 61 Plan 24: External-content foundation for the map page

Leaflet 1.9.4 is vendored unmodified and served from the static allowlist; the location page alone sends the widened CSP and `Permissions-Policy: geolocation=(self)`; credits and COMPLIANCE.md cover Leaflet, the OSM tile server and Nominatim.

## What changed

- **Vendoring:** the npm tarball was fetched with curl into an empty scratchpad directory and extracted there; sizes and SHA-256 of `dist/leaflet.js`, `dist/leaflet.css` and `LICENSE` matched the pinned values before anything was copied. `VENDOR.md` records source, hashes, scan, licence, why 1.9.4, images not vendored, upgrade note. Three public no-cache routes (`LEAFLET_*_ROUTE`) were added; not in the shell script order. No manifest or lockfile.
- **Policies:** new `companion/page_policy.py` (a `PagePolicy` pair, default and map) so `routes.py` and `detection_actions.py` can name the map policy without importing `app.py`. `send_html` and `_send_hardening_headers` take a `policy` argument defaulting to the existing pair; `_render_tab` takes it too. The detection GET route and `detection_actions._rerender` (every refused POST: save_place 400, legacy save_detection and save_location 200) pass `MAP_PAGE_POLICY`. The default CSP is byte-identical. Every response now also carries `Permissions-Policy: geolocation=()` (no such header existed before), `geolocation=(self)` on the map page.
- **Credits and compliance:** credits.json gains `leaflet`, `openstreetmap-tiles`, `nominatim` (EN/FR); COMPLIANCE.md gains three sections, the intro count (ten sources) and the status table.

## Tests

`test_vendored_leaflet.py` (served bytes hash, sizes, content types, scan on served bytes, no marker images), `test_page_policy_headers.py` (map policy on GET and the three refused POSTs, default pair and no external host on every exact GET route for admin and anonymous, 404/403/redirects/export/POST success, string has no wildcard, http:, blob:, unsafe-eval, frame-src), additions to the credits and compliance tests. `render_baseline.json` regenerated: no change; sign-in digests unchanged.

## Policy check (fetched 2026-11-03) and differences from the spec

- Tile policy: a Referrer-Policy that blocks the Referer is forbidden. The global `same-origin` header stays; the map code must set the tile layer referrer policy (`origin`) as the spec already says.
- Nominatim: needs a Referer or identifying User-Agent. With the global `same-origin` policy a cross-origin `fetch` sends no Referer, so the map plan's search `fetch` must pass `referrerPolicy: 'origin'`. The spec only mentions this for tiles. It also asks that the service be switchable without a software update; the host is a constant (documented as acceptable).
- Both pages are recorded as "behaviour pending the map plan" in COMPLIANCE.md.

## Gates

ruff, mypy (29 modules), comment-history, function size (931, none over 80), `scripts/check-attribution.sh` (67 assets attributed), Phase 47 freeze (21 passed): clean. No edit to deploy/, stub-server/, hardware/. `deploy/Caddyfile` sets no conflicting CSP or Permissions-Policy header (only Strict-Transport-Security).
Full `companion test-support stub-server -n auto --no-cov`: 6967 passed, 4 skipped, 2 failed: `companion/test_browser_device_selector.py::test_open_sheet_fits_with_44px_targets[chromium-1280-{light,dark}-fr]` (a file from plan 61-23, untouched here). Re-run alone it failed on a different parameter (`1280-light-en`, other params passed): the sheet footer link measures 43.99997 px against a 44 px floor, a sub-pixel rounding flake at 1280 px that moves between runs. Not caused by this plan; not fixed.

## Deviations

1. Policy constants live in the new `companion/page_policy.py` instead of `app.py` (import cycle); `app.py` re-exports `CONTENT_SECURITY_POLICY`, `DEFAULT_PAGE_POLICY`, `MAP_PAGE_POLICY`.
2. The plan said every other route "sends geolocation=()": no Permissions-Policy header existed, so it is added to every response.
3. Un-prefixed `/detection` redirects (303) to the device-scoped URL, so the header test checks the 200 on `/devices/<id>/detection` and the redirect keeps the default pair.

## Known Stubs

None. Tile and search behaviour land with the map plan (place-map.js).

## Self-Check: PASSED
