---
phase: 38-efficiency-companion-poll-cycle-storage
reviewed: 2026-09-26T21:38:23Z
depth: standard
files_reviewed: 10
files_reviewed_list:
  - companion/app.py
  - companion/layout.py
  - companion/pages/health_page.py
  - companion/static/freshness.js
  - deploy/Caddyfile
  - server/history_db.py
  - server/plane/detect.py
  - server/poll_loop.py
  - scripts/measure_efficiency.py
  - test-support/efficiency_probe.py
findings:
  critical: 2
  warning: 3
  info: 5
  total: 10
status: issues_found
---

# Phase 38: Code Review Report

**Reviewed:** 2026-09-26T21:38:23Z
**Depth:** standard
**Files Reviewed:** 10
**Status:** issues_found

## Summary

I reviewed the changed regions of `git diff ed56221 HEAD -- . ':!.planning'`, reading into callees where the diff depends on them: `home_page._status_tiles_html`, `calendar_rules`, `_notify_*_transition`, and `ingest_caddy_battery_log`.

Several parts hold up under tracing:

- **Auth on the 304 path.** `require_session()` runs before `page_context()`, and the token is computed after that. The 304 requires `X-Requested-With: freshness`.
- **Compression placement.** `encode` is only in the companion Caddy block.
- **Cache policy.** Static CSS/JS use `public, no-cache`. The runway image stays `private` behind the session.
- **Connection scope.** The thread-local scope is isolated per thread, and the lazy open is correct.
- **Schema-once set.** It is guarded by a lock.
- **Batch rollback.** `write_batch` commits or rolls back only at the outermost level.
- **ntfy and transactions.** No write transaction is open while ntfy runs: every writer outside a batch commits at once, and `SELECT` does not start a transaction in legacy isolation mode.
- **Provider order.** Results are collected in `provider_names` order.

Two defects are blockers:

1. The per-provider spacing wait is computed from a wall-clock value stored in `history.db` and has no upper bound. One timestamp in the future stops polling for good.
2. The Home freshness token leaves out `META_LAST_PIPELINE_RUN`, but Home's Flight-data tile shows that timestamp as plain text. The tile stays frozen until the forced refresh, and a test locks in this behaviour.

There are also three warnings, all in the new write and freshness paths:

- The commit order between the runway-event insert and the `poll_state` save was reversed, so a crash can now duplicate events.
- The all-or-nothing batch can now roll back the pipeline heartbeat.
- The Display token does not include the calendar secret file.

## Narrative Findings (AI reviewer)

## Critical Issues

### CR-01: The provider spacing wait has no upper bound and uses a stored wall-clock value; one timestamp in the future stops polling permanently

**File:** `server/plane/detect.py:691-697`, `server/poll_loop.py:620-650` (`_load_provider_last_calls`), `server/poll_loop.py:760-764` (persist)

**Issue:** `_spaced_query` computes `wait = previous + MIN_SECONDS_BETWEEN_CALLS - clock()` and calls `sleep(wait)` with no cap.

- `previous` comes from the `provider_last_call:<name>` meta row. That row holds a `time.time()` value written by an earlier process.
- If the stored value is ahead of the current clock, the worker sleeps for that whole gap. That happens when:
  - the VPS clock was ahead at boot and NTP later stepped it back;
  - a `history.db` was restored from a host with a skewed clock;
  - the meta row was edited by hand.
- `last_call_at[name] = clock()` runs only after the sleep. The row is persisted only later, in `_record_history`.

As a result:

- **Timer oneshot:** systemd kills the unit at `TimeoutStartSec=90s` before the row is overwritten. Every later cycle reads the same future value and is killed the same way, so detection stops for good.
- **Companion `/poll-now`:** `run_once` runs in the request thread with no systemd timeout. It sleeps while holding `_POLL_LOCK` and `poll.lock`. Every timer cycle then fails the lock wait, and the only way out is restarting the companion.
- **Stored `"inf"`:** `float("inf")` parses, and `time.sleep(inf)` raises `OverflowError`. That error is not in `(requests.RequestException, ValueError)`, so the whole cycle fails every time.

**Fix:** Cap the wait, and reject non-finite or future values when loading.

```python
# detect._spaced_query
with lock:
    previous = last_call_at.get(name)
    now = clock()
    wait = 0.0
    if previous is not None and math.isfinite(previous):
        # Never wait longer than one spacing interval: a stored value in the
        # future (clock stepped back, restored DB) must not stall the cycle.
        wait = min(max(previous + MIN_SECONDS_BETWEEN_CALLS - now, 0.0),
                   MIN_SECONDS_BETWEEN_CALLS)
```

```python
# poll_loop._load_provider_last_calls
value = float(raw)
if not math.isfinite(value) or value > time.time() + detect.MIN_SECONDS_BETWEEN_CALLS:
    continue
last_call_at[name] = value
```

Add a test that stores a future value and asserts `sleep` is called with at most `MIN_SECONDS_BETWEEN_CALLS`.

### CR-02: The Home freshness token leaves out the pipeline-run timestamp that Home's Flight-data tile displays

**File:** `companion/app.py:641-668` (`_freshness_db_signal`), `companion/app.py:738-740` (`want_pipeline_run=(slug == REFRESH_PAGE_HEALTH)`); the rendered side is `companion/pages/home_page.py:345-353`

**Issue:** `_freshness_db_signal` adds `META_LAST_PIPELINE_RUN` only for Health. Its docstring says the other three pages "must never see it change". That is not true for Home:

- `_status_tiles_html()` shows `health["pipeline_detail_html"]` in the Flight-data tile. That value is `concise_timestamp_html(pipeline_ts, now)`, i.e. "HH:MM (just now)".
- `_plain_text_from_markup()` flattens it to plain text, so `relative-time.js` cannot update it on the client.
- `.home-status-grid` is one of Home's declared swap regions.

The pipeline runs every 30 s. Its `pipeline_state` stays "ok", so the token does not change, every tick gets a 304, and the tile keeps showing the old time. For example, "Flight data: up to date · 14:32 (just now)" can stay on screen until about 14:37. That is up to about 5 min 15 s, until the forced refresh. Before this phase, every 45 s tick refreshed the tile.

On a page whose purpose is a real-time glance, this is wrong information in a region the swap was built to keep current. `companion/test_freshness_token.py:376-403` (`test_pipeline_run_meta_advance_changes_only_health_token`) asserts `after_home == before_home`, which locks the bug in.

**Fix:** Include the pipeline-run timestamp for Home too, and correct the test and the docstring.

```python
"db": _freshness_db_signal(
    state_dir,
    want_pipeline_run=slug in (layout.REFRESH_PAGE_HEALTH, layout.REFRESH_PAGE_HOME)),
```

Alternatively, render the Home tile's detail through `relative_time_html` so the client updates it. Even then, the absolute "HH:MM" half still needs the meta value in the token.

## Warnings

### WR-01: A runway event is now committed before the `poll_state` that deduplicates it, with an ntfy call in between; a crash duplicates events

**File:** `server/poll_loop.py:1244-1245`, `1295-1300`, `1405-1413`

**Issue:** In the flight branch, `poll_state["last_recorded_hex"]`, together with its confirmed-state and corroboration companions, marks an event as already recorded.

- **Before:** `save_poll_state()` ran before `_record_history()` inserted the `runway_events` row.
- **Now:** `_record_history()` commits the row first. Then `_notify_silence_transition()` runs, which can make an ntfy HTTP call with a 5 s timeout plus DNS. Only after that does `_persist_poll_state()` write the dedup fields.

If the process dies in that window, the next cycle's `_should_record_event()` sees the old `last_recorded_*` values and inserts the same event again. `runway_events` is keep-forever, and the Flights page and statistics count duplicates. Ways the process can die there:

- SIGKILL or OOM;
- the systemd 90 s timeout;
- an `OSError` from `atomic_write` (disk full);
- a companion restart during `/poll-now`.

The old order could lose an event on a crash; the new order duplicates it.

**Fix:** Persist `poll_state` before the history write, and persist again after the silence hook only if the hook changed `notifications`. That second write happens only on a genuine silent/recovered transition, so the steady state is still one write or none per cycle.

```python
_persist_poll_state(state_dir, poll_state, poll_state_baseline)
_record_history(...)
before = json.dumps(poll_state.get("notifications"), sort_keys=True)
... _notify_silence_transition(...)
if json.dumps(poll_state.get("notifications"), sort_keys=True) != before:
    save_poll_state(state_dir, poll_state)
```

Another option is to make the event insert idempotent, for example a unique key on `(hex, confirmed_state, corroborated, ts-bucket)`.

### WR-02: The all-or-nothing `write_batch` lets a failed Caddy-log ingest or provider-meta write roll back the pipeline heartbeat and the runway event

**File:** `server/poll_loop.py:730-767`, `server/history_db.py:293-328`

**Issue:** Every write in `_record_history` now shares one transaction:

- the event insert;
- `META_LAST_PIPELINE_RUN`;
- `META_SOURCE_FAULT`;
- `META_LAST_DETECTION`;
- the Caddy-log ingest, which runs one `INSERT OR IGNORE` per log line;
- the wake epoch;
- the provider timestamps.

A `sqlite3.Error` from any of them rolls back all of them. Before, each write committed on its own, so a failing Caddy-log ingest could not stop the heartbeat. Now, a persistent ingest fault stops `META_LAST_PIPELINE_RUN` from advancing. The Health page and the nav dot then report "Flight data is stale" while the pipeline is running fine, and the detected event is lost too. Examples of such a fault:

- a malformed row that trips a constraint;
- `SQLITE_FULL`;
- a corrupt page reached only by the `device_health` insert.

The batch also holds the write lock while `tail_caddy_battery_log` reads up to a 10 MiB log from disk, so companion writers wait on `busy_timeout` for longer.

**Fix:** Keep the heartbeat and event commit atomic with each other, but isolate the accessory ingest in a savepoint. Its failure should roll back only its own rows and offset, and be logged.

```python
with history_db.write_batch(conn):
    ... event, pipeline_run, source_fault, last_detection, wake epoch, provider meta ...
    if caddy_log:
        conn.execute("SAVEPOINT caddy_ingest")
        try:
            history_db.ingest_caddy_battery_log(conn, caddy_log)
            conn.execute("RELEASE caddy_ingest")
        except (sqlite3.Error, OSError) as exc:
            conn.execute("ROLLBACK TO caddy_ingest"); conn.execute("RELEASE caddy_ingest")
            print("poll_loop: caddy ingest failed: %s" % type(exc).__name__)
```

Another option is to tail the log before opening the batch, so no file I/O happens under the write lock.

### WR-03: The Display freshness token leaves out the calendar secret file, and file stamps miss permission changes

**File:** `companion/app.py:601-638` (`_freshness_file_stamp`, `_freshness_file_stamps`)

**Issue:** Display renders `calendar_configured` and `calendar_drift` through `config_page._aspect_card_html`, and they also control whether the disconnect form appears. Both are read from `calendar_rules.calendar_secret_path(state_dir)`, which is not among the stamped files; only the registry, `calendar_rules.json`, is. In addition, `calendar_drift` is `True` exactly when the secret file's mode has group or other bits set. A `chmod` changes only `st_mode` and `st_ctime`, never `st_mtime_ns` or `st_size`.

So these changes are invisible to the token until the forced refresh:

- a drift appearing or being fixed;
- the secret being removed by hand;
- a `save_calendar_url` path that leaves the registry untouched (`calendar_rules.py:722`), or one whose registry was already missing.

The drift banner is a security signal: the secret may have been exposed.

**Fix:** Stamp the secret file, and include the mode and change time in every stamp.

```python
return [st.st_mtime_ns, st.st_ctime_ns, st.st_size, st.st_mode]
...
"calendar_secret": _freshness_file_stamp(calendar_rules.calendar_secret_path(state_dir)),
```

## Info

### IN-01: The Paris date feeds only the Health token, but Home also renders values that depend on the day

**File:** `companion/app.py:749-755`; `companion/pages/home_page.py:676` (`_day_checkins`), `home_page.py:318-319`

**Issue:** Home's day band buckets check-ins by the Paris calendar day. Its next-wake `local_clock_text(..., now_parsed=now)` also chooses day qualifiers relative to `now`. At midnight, with no new check-in (for example a parked or silent frame), the token for Home and Display does not change. The page keeps yesterday's band until the forced refresh.

Health's corroboration and statistics windows (`cutoff = now - N days`) likewise lose rows over time without the token changing.

**Fix:** Add `paris_date` for Home and Display too. Optionally hash `_cutoff_iso` at hour granularity for Health.

### IN-02: The freshness token has no code or build identity

**File:** `companion/app.py:733-758`

**Issue:** After a deploy that changes page markup, `skypane-companion` restarts but the inputs are the same. Open tabs keep getting 304s and show the old markup in swap regions for up to about 5 min.

**Fix:** Hash a process-start or git-SHA constant into `parts`, for example `"build": _BOOT_ID`.

### IN-03: The schema-once key misses an in-place restore

**File:** `server/history_db.py:196-206`

**Issue:** `cp backup.db history.db` rewrites the same inode with a non-empty file. The companion's key `(realpath, st_dev, st_ino)` stays marked ready, so `init_schema()` is never re-run. `init_schema()` is the only migration mechanism. If the restored file is missing a table added later (for example `wake_epochs`), the long-running companion can fail on it until the next poll oneshot recreates the table, within about 30 s.

**Fix:** Add `st_mtime_ns` of the main file to the key, or re-run `init_schema` on `sqlite3.OperationalError: no such table`. Otherwise, document that a restore needs a restart.

### IN-04: `_LazyContext` removes a loader before running it

**File:** `companion/app.py:1159-1164`

**Issue:** If a loader raises, its key is left neither loaded nor lazy. A second read then raises `KeyError`, which hides the original exception in logs and tracebacks. The current loaders are all fail-safe, but the class invites future ones that are not.

**Fix:** Pop the loader only after it succeeds, or re-insert it in `except`.

### IN-05: The `If-Modified-Since` fallback treats a date without a zone as local time

**File:** `companion/app.py:515`

**Issue:** For a date with a `-0000` zone, `email.utils.parsedate_to_datetime` returns a naive `datetime`, and `.timestamp()` then reads it as the server's local time. This is harmless on a UTC host, and browsers send `If-None-Match`, which takes precedence. It is still a latent comparison bug.

**Fix:** `dt = parsedate_to_datetime(ims); dt = dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)`.

---

_Reviewed: 2026-09-26T21:38:23Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
