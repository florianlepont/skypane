---
phase: 68-console-and-companion-visual-improvements
plan: 31
subsystem: server history counters, Health page
tags: [route-directories, history-db, schema-migration, health-page]
requires: [68-12, 68-13, 68-33]
provides:
  - per-directory lookup counters (route_lookups) and the answering directory per flight (runway_events.route_directory)
  - Health page cards "route directories" and "answered by"
key-files:
  created:
    - companion/pages/route_sources_card.py
    - server/test_route_directory_status.py
    - companion/test_health_route_sources.py
    - companion/test_browser_health_route_sources.py
  modified:
    - server/history_db.py
    - server/plane/enrich.py
    - server/poll_cycle.py
    - companion/pages/health_page.py
    - companion/static/style-admin.css
    - companion/i18n_fr/health.py
    - companion/testdata/render_baseline.json
    - server/test_config_history.py
    - companion/test_fleet_tiles.py
    - companion/test_browser_fleet_detail_pages.py
requirements: [CON-01]
---

# Phase 68 Plan 31: Route sources (levels A and B) Summary

Per-directory status (VRS standing data, adsbdb) and "answered by" built exactly as decided on 2026-11-18; level C (comparison per aircraft, extra request) is not built.

## What was built

- **history.db schema version 1** (`PRAGMA user_version` 0 -> 1, the first stamp this database has had): new table `route_lookups(ts, directory, outcome)` (one row per request that really left the process; cache hits make none; 14-day retention) and new nullable column `runway_events.route_directory` ("vrs", "adsbdb", NULL = none or a row from before the column).
- **enrich.py**: `LookupReport` (optional `report=` argument of `resolve_route`) collects `(directory, outcome)` with outcome found / none / failed, and the directory whose route was returned. Return values are unchanged. A transient failure (exception, 429, 5xx, other 4xx) is counted as `failed` and is still never cached (unchanged cache code; tested).
- **poll_cycle.py**: counters are written in an isolated SAVEPOINT (`route_lookups`), like the trace and the unshown events, so a fault there cannot touch the heartbeat or the runway event. The directory is stored with the event; it is cleared when the route is replaced by the airline-only fallback (route contradicting the direction). No extra network request; the route chosen, the image and the wake interval do not change.
- **Health page** (frame Health, administrators only, platform group after Identification): card 1 = both directories (name, "Reachable"/"Not reachable"/"No request yet", its role "Tried first" / "Used when the first has no route", last answer, lookups of the last 24 h, found share, failed share); card 2 = "Answered by", "VRS n . adsbdb m", "Last 7 days: N flights" and a share bar. States: empty, healthy, degraded. EN/FR. No new route, no access-matrix change.

## Phase 64-owned and other files touched

`companion/pages/health_page.py` (8 lines added net; 1268 lines), `companion/static/style-admin.css` (route bar rule), `companion/i18n_fr/health.py`, `server/history_db.py` (additive; Home statistics functions and plan 33 functions untouched), `server/plane/enrich.py`, `server/poll_cycle.py`. Open pull requests: #517 (plan 30) touches other files.

## Schema migration safety

- `init_schema()` steps are idempotent: `CREATE TABLE/INDEX IF NOT EXISTS`, guarded `ALTER TABLE ... ADD COLUMN` (a "duplicate column name" from a concurrent process counts as done), then the stamp is raised only when lower (never lowered; a newer stamp is kept). Interrupted before the stamp = steps repeat next connect.
- Runs on first `connect()` of whichever process comes first (poll oneshot or companion); both can run on the same file (WAL, busy_timeout 5 s). ALTER ADD COLUMN is O(1), existing rows read NULL.
- Rollback-safe: the previous release's INSERT names its columns, so it still writes to a migrated file (tested).
- Backup: `history.db` is already snapshotted whole with the SQLite backup API (WAL-safe); the new table rides in the same file. `deploy/backup/skypane_backup.py` INCLUDE / KNOWN_EXCLUDED classify by file name: no new file, nothing new to classify. `deploy/activate.sh` and `server/fleet_migrate` only handle `fleet.db`; history.db is migrated lazily on connect, no deploy step to add. A snapshot taken before the migration opens and migrates (tested).
- Tests: `server/test_route_directory_status.py` (database of the previous schema migrated without losing a row, migrating twice changes nothing, migration while another connection holds a read transaction, snapshot of the previous schema restored, previous release can still write); `server/test_config_history.py` updated: the old "no schema version stamp" test became "stamps once, never lowers", and the table-count guard went from five to six.

## Deploy checklist (what the owner should check after deploy)

1. `journalctl -u skypane-poll -n 50`: no line `poll_loop: history write failed:` and no line `poll_loop: route_lookups failed:` (the two lines written when the migration or the counter write fails; the cycle itself continues either way). Normal `poll_loop: ... route_source=...` lines continue as before.
2. `sqlite3 <state>/history.db "PRAGMA user_version"` prints `1`; `.tables` lists `route_lookups`.
3. After a few cycles with traffic: `SELECT directory, outcome, COUNT(*) FROM route_lookups GROUP BY 1,2` has rows; the Health page of the frame shows both directory cards and the "Answered by" card (it fills as new flights are recorded; older flights stay unknown and are not counted).
4. Frame image and wake interval unchanged (golden render tests cover this).
5. A failing directory shows "Not reachable" only when its most recent request failed; it recovers on the next answered request.

## Tests run

- Server: `pytest server stub-server test-support deploy/tests -n auto`: 4951 passed, 5 skipped (pre-existing root-permission skips). Includes `server/test_golden_render.py`, `server/test_golden_giant_render.py`, `stub-server/test_phase47_freeze.py` (unedited) and `server/test_route_directory_status.py`, `server/test_vrs_routes.py`, `deploy/tests/test_backup.py`.
- Companion targeted (every test file mentioning health_page, health_sections, health_rows, i18n_fr health, style-admin, health-row, view=health, history_db, route_source, recent_runway_events; the Health/System browser files `test_browser_battery_card`, `charging_pill`, `fleet_detail_pages`, `health_route_sources`, `home_state_card`, `motion_live`, `surfaces`, `system_tiles`, `ux_01`, `ux_03`, `ux_health_drawings`) plus `test_render_baseline`, `test_stylesheet_structure`, `test_suite_guards`, `test_structure_guards`, `test_i18n`, with `SKYPANE_REQUIRE_BROWSER=1`: see the result line in the hand-back report. Not run: the other browser shards (CI).
- `ruff check .` clean; `mypy` clean (49 files); `scripts/check_function_size.py check --max 80 server stub-server` none over 80 (`init_schema` kept at 80 by moving the new table to a helper); `scripts/check_comment_history.py check` clean; `companion/app.py` 1497 lines, `health_page.py` 1268.

## Baseline diff

`companion/testdata/render_baseline.json` regenerated once: 16 captures changed, all only by the cache-busting hash of `style-admin.css` in `/fleet`, `/fleet?flash=saved`, `/fleet?view=system` and `/settings/calendar/disconnect` (EN/FR, light/dark). No capture shows the new cards (the Health page is not in the baseline).

## Deviations from Plan

- Level C and the "Route sources" comparison card (D-26) are intentionally not built (owner decision).
- Plan file list had `companion/health_sections.py` and `server/test_golden_render.py`: neither needed a change.
- D-14 (hand-built `banner__pill` markup in `health_page.py`): there is none in that file (its only hand-built pill is `toast__pill` in the anomaly banner, a different component); nothing replaced. The new cards use no pill markup.
- Existing assertions adapted to the new intended page: `test_fleet_tiles` card count 5 -> 7; `test_browser_fleet_detail_pages` "one card per row" now "one card per topic" (the two directories are two rows of one card, as in the mock).
- "adsbdb" and the " . " in "VRS n . adsbdb m" are not translated ids (identical in French, which the i18n sweep rejects as catalogue entries).

## Divergences from the approved mock

- Facts (last answer, lookups, shares) are left-aligned label/value pairs like every other Health row (existing page convention); the mock right-aligns the values.
- Relative times use the page's own format ("4m ago"), the mock writes "4 min ago".
- The mock puts the role ("tried first") in the small label line, the name in bold and "Reachable" at the right, and joins the window to "Answered by"; the built rows keep the page's row anatomy (name, verdict, then body), because `test_browser_ux_health_drawings` requires one-line, column-aligned names and the French role sentence would wrap in the name column. The role and the window are therefore body notes.
- The mock's phone figure exists only for level A; the built phone shows level B (the bar), so the phone mock capture is level A.
- A directory never asked reads "No request yet" (neutral); the mock shows only healthy and degraded.

## Known Stubs

None.

## Self-Check: PASSED
