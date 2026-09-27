---
phase: 38-efficiency-companion-poll-cycle-storage
fixed_at: 2026-09-26T22:20:06Z
review_path: .planning/phases/38-efficiency-companion-poll-cycle-storage/38-REVIEW.md
iteration: 1
findings_in_scope: 7
fixed: 7
skipped: 0
status: all_fixed
---

# Phase 38: Code Review Fix Report

**Fixed at:** 2026-09-26T22:20:06Z
**Source review:** .planning/phases/38-efficiency-companion-poll-cycle-storage/38-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 7 (CR-01, CR-02, WR-01, WR-02, WR-03, IN-01, IN-04)
- Fixed: 7
- Skipped: 0

Scope was CR-01, CR-02, WR-01, WR-02, WR-03, plus IN-01 and IN-04 (both
confirmed small and local against the current code). IN-02, IN-03, IN-05
were left as documented, per the task's explicit scope.

## Fixed Issues

### CR-01: The provider spacing wait had no upper bound and used a stored wall-clock value

**Files modified:** `server/plane/detect.py`, `server/poll_loop.py`, `server/test_plane_detection.py`, `server/test_poll_loop.py`
**Commit:** `258fee8`
**Applied fix:** Verified against the current code - `detect._spaced_query()`'s wait was exactly as described, uncapped. Clamped `wait` to `[0, MIN_SECONDS_BETWEEN_CALLS]` and treated a non-finite `previous` the same as "no previous call" (matching the review's own snippet). Hardened `poll_loop._load_provider_last_calls()` to drop a non-finite or future-dated stored value (`value > time.time() + detect.MIN_SECONDS_BETWEEN_CALLS`) before it ever reaches `detect`, added `import math` to `poll_loop.py` (already present in `detect.py`).
**Tests:** `test_spacing_clamps_a_future_stored_last_call_at` and `test_spacing_treats_non_finite_last_call_at_as_absent` (server/test_plane_detection.py) drive `detect.poll_current_aircraft()` with a future/non-finite injected `last_call_at` and a fake `sleep` recorder, asserting every recorded wait is `<= MIN_SECONDS_BETWEEN_CALLS` and that a non-finite value produces zero sleep calls and no exception. `test_load_provider_last_calls_drops_non_finite_and_future_values` (server/test_poll_loop.py) seeds `history.db` meta rows directly with `"nan"` and a future timestamp and asserts `_load_provider_last_calls()` drops both.

### CR-02: The Home freshness token left out the pipeline-run timestamp Home's own Flight-data tile displays

**Files modified:** `companion/app.py`, `companion/test_freshness_token.py`
**Commit:** `f20530c`
**Applied fix:** Verified `home_page._status_tiles_html()` does render `health["pipeline_detail_html"]` (the same `META_LAST_PIPELINE_RUN`-derived timestamp Health's own Pipeline tile shows) as plain text inside `.home-status-grid`. Changed `_freshness_db_signal()`'s `want_pipeline_run` gate to `slug in (layout.REFRESH_PAGE_HEALTH, layout.REFRESH_PAGE_HOME)` and corrected both that function's own docstring and `test_freshness_token.py`'s bug-locking assertion: `test_pipeline_run_meta_advance_changes_only_health_token` (asserted `after_home == before_home`) is now `test_pipeline_run_meta_advance_changes_health_and_home_tokens`, asserting Home's token DOES change (Flights still doesn't). The identical-cycle stability test lost its Home assertion too (renamed to `test_identical_second_poll_cycle_leaves_display_and_flights_tokens_unchanged`), with a new sibling `test_identical_second_poll_cycle_still_changes_the_home_token` documenting that Home is now expected to change every cycle, same as Health.
**Tests:** the two renamed/added tests above, both passing against a real `app_server_in_process`.

### WR-01: A runway event was committed before the poll_state that deduplicates it, with an ntfy call in between

**Files modified:** `server/poll_loop.py`, `server/test_poll_loop.py`
**Commit:** `35a3bb2`
**Applied fix:** Verified the ordering in the shared tail (flight-detected/held/empty branches all funnel into it): `_record_history()` commits first, then `_notify_silence_transition()` runs (ntfy HTTP call), then `_persist_poll_state()` wrote the dedup fields - exactly the window the finding describes. Chose the "persist before notify" design named in the task guidance: moved the cycle's save to run BEFORE the notify call (using the existing `poll_state_baseline`), then added a second, conditional save after notify using the just-persisted string as the new baseline, only firing if the notify hook's own `poll_state["notifications"]` mutation changed anything beyond what was already written. Steady-state cycles still write 0 or 1 time; only a cycle with both a branch mutation and a genuine notify transition writes twice - matching the review's own stated invariant ("the steady state is still one write or none per cycle"). Left the hold branch's own (separate) record_history/notify/persist sequence untouched - it never sets the dedup fields, so it carries no duplication risk, and the finding cites only the shared-tail branches.
**Tests:** `test_crash_during_notify_after_history_commit_does_not_duplicate_the_event` monkeypatches `poll_loop._notify_silence_transition` to raise `SystemExit`, confirms `poll_state.json`'s dedup fields (`last_recorded_hex`) are already on disk at the moment of the simulated crash, then runs a second cycle and asserts `recent_runway_events` still holds exactly 1 row.

### WR-02: The all-or-nothing write_batch let a failed Caddy-log ingest or provider-meta write roll back the heartbeat and event

**Files modified:** `server/history_db.py`, `server/poll_loop.py`, `server/test_poll_loop.py`
**Commit:** `12c39ad`
**Applied fix:** Verified `_record_history()`'s single `write_batch` covered the event insert, the three per-cycle meta keys, the Caddy-log ingest, the wake epoch, and the provider-timestamp meta rows, and that `ingest_caddy_battery_log()` did its file read (up to 10 MiB) and its DB writes in one call, inside that batch. Split `history_db.ingest_caddy_battery_log()` into `read_caddy_battery_log()` (pure meta SELECT + file I/O, no writer) and `apply_caddy_battery_log()` (the actual inserts + offset write), keeping the combined `ingest_caddy_battery_log()` name as a thin wrapper for its other direct callers (server/test_caddy_tail.py, server/test_config_history.py, server/test_history_db_scope.py - all still pass unmodified). `_record_history()` now calls `read_caddy_battery_log()` BEFORE its `write_batch` opens, and wraps both the Caddy-log apply and the provider-timestamp meta writes in their own SQLite SAVEPOINTs (via a new `_run_isolated_write()` helper) nested inside the outer batch, so either accessory write's own fault rolls back only itself and is logged, never the heartbeat or the event.
**Tests:** `test_caddy_ingest_failure_does_not_roll_back_heartbeat_or_event` monkeypatches `history_db.apply_caddy_battery_log` to raise `sqlite3.OperationalError` and asserts the runway event and `META_LAST_PIPELINE_RUN` both still commit while no `device_health` row is inserted. `test_provider_last_call_meta_failure_does_not_roll_back_heartbeat` does the same for a provider-meta `set_meta` fault. `test_caddy_log_tail_reads_before_the_write_batch_opens` spies on `read_caddy_battery_log` to assert it runs at `conn._batch_depth == 0`, proving the read never holds the write lock.

### WR-03: The Display freshness token left out the calendar secret file, and file stamps missed permission changes

**Files modified:** `companion/app.py`, `companion/test_freshness_token.py`
**Commit:** `a55db91`
**Applied fix:** Verified `config_page._aspect_card_html()` reads `calendar_configured`/`calendar_drift`, both derived from `calendar_rules.calendar_secret_path()`, which `_freshness_file_stamps()` never stamped (only the registry beside it was), and that `calendar_secret_mode_is_unsafe()` reads `st_mode` alone, which a bare `chmod` changes without touching `st_mtime`/`st_size`. Changed `_freshness_file_stamp()` to return `[st_mtime_ns, st_ctime_ns, st_size, st_mode]` and added a `calendar_secret` entry to `_freshness_file_stamps()`.
**Tests:** `test_calendar_secret_chmod_changes_display_token` (marked `@requires_non_root`, since root ignores permission bits - matches the existing project convention for chmod-based tests) seeds a real secret via `calendar_rules.save_calendar_url()`, chmods it to `0o644`, and asserts `/display`'s token changes. `test_calendar_secret_removed_changes_display_token` removes the file and asserts the same.

### IN-01: The Paris date fed only the Health token, but Home and Display also render day-dependent values

**Files modified:** `companion/app.py`, `companion/test_freshness_token.py`
**Commit:** `d69edae`
**Applied fix:** Verified `home_page._day_checkins()` buckets by the Paris calendar day and that both `home_page.py` and `config_page.py` call `layout.local_clock_text()` with a day-relative qualifier for the next-wake time. Small, local change: widened the existing `if slug == layout.REFRESH_PAGE_HEALTH: parts["paris_date"] = ...` guard to `slug in (layout.REFRESH_PAGE_HEALTH, layout.REFRESH_PAGE_HOME, layout.REFRESH_PAGE_DISPLAY)`.
**Tests:** `test_paris_midnight_rollover_changes_home_and_display_tokens` jumps `history_db.utc_now_iso()` by 2 real minutes across a Europe/Paris midnight boundary and asserts both Home's and Display's tokens change. Verified as a genuine regression test by temporarily reverting the one-line fix locally and confirming the test fails against the pre-fix code, then restoring it.

### IN-04: `_LazyContext` removed a loader before running it

**Files modified:** `companion/app.py`, `companion/test_page_context.py`
**Commit:** `f619e8f`
**Applied fix:** Verified `_LazyContext.__getitem__()` popped `self._loaders[key]` before calling the loader, so a raising loader left the key neither resolved nor lazy, and a second read fell through to `dict.__getitem__()`'s `KeyError`, masking the original exception. Small, local change: reordered to call the loader first and only `del self._loaders[key]` after it returns successfully.
**Tests:** `test_lazy_context_getitem_keeps_a_raising_loader_pending_for_retry` (companion/test_page_context.py, added `import pytest` to that file, which had none before) uses a loader that raises once then succeeds, and asserts the key stays `in ctx` after the raise and that a retry re-runs the same loader and returns its second-attempt value. Verified as a genuine regression test the same way as IN-01's.

## Skipped Issues

None - all seven in-scope findings were fixed.

## Left as documented (out of scope per the task)

- **IN-02** (freshness token has no code/build identity): left untouched.
- **IN-03** (schema-once key misses an in-place restore): left untouched.
- **IN-05** (`If-Modified-Since` fallback treats a date without a zone as local time): left untouched.

## Verification

- `server/.venv/bin/python3 -m pytest` on every touched test file (`server/test_poll_loop.py`, `server/test_plane_detection.py`, `companion/test_freshness_token.py`, `companion/test_page_context.py`): 216 passed, 2 skipped (root-only chmod tests), 0 failed.
- `ruff check` on every touched source/test file: all checks passed.
- `scripts/check_comment_history.py check`: no violations (no plan/phase/finding IDs introduced into comments or docstrings).
- Full suite via `PLAYWRIGHT_BROWSERS_PATH=... SKYPANE_REQUIRE_BROWSER=1 ./scripts/run-all-tests.sh`: 3032 passed, 7 skipped, 1 failed - the one failure is the pre-existing, known local old-Chromium test `test_the_heros_grouping_holds_at_both_widths_and_owes_nothing_to_a_script[chromium]`, matching the task's stated acceptable-failure allowance.
- `stub-server/byos_server.py` and `deploy/README.md` were not touched.
- No files outside `server/` and `companion/` (plus this report) were modified. `STATE.md`/`ROADMAP.md` were not edited.

---

_Fixed: 2026-09-26T22:20:06Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
