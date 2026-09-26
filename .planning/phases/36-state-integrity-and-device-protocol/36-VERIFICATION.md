---
phase: 36-state-integrity-and-device-protocol
verified: 2026-09-26T11:23:28Z
status: human_needed
score: 14/14 must-haves verified
overrides_applied: 0
human_verification:
  - test: "Production poll unit honours the start timeout"
    expected: "systemctl show skypane-poll.service -p TimeoutStartUSec shows 1min 30s"
    why_human: "Needs the deployed VPS systemd instance; the unit file's static text is verified in-repo (TimeoutStartSec=90s, deploy/tests/test_units.py), but the running system's parsed value can only be checked after deploy."
  - test: "Device still refreshes after a panel change mid-wake, on real hardware"
    expected: "Trigger /poll-now twice in quick succession during a wake; the frame shows the image it was told about, no verify failure in the frame log"
    why_human: "Needs the real e-ink frame and firmware wake cycle; the equivalent byos-side behaviour (content-addressed /img/<sha>.bin survives a panel swap between /display and download) is already covered by an automated subprocess test."
---

# Phase 36: State integrity and device protocol Verification Report

**Phase Goal:** No shared file can be torn or lose an update, the device always downloads the image it was told about, and no single bad input or slow upstream can hang or fail a cycle.
**Verified:** 2026-09-26T11:23:28Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (Roadmap Success Criteria + PLAN must-haves)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Concurrent-save reproduction (2 processes × 200 saves) runs with zero exceptions and zero lost updates | VERIFIED | `server/test_poll_lock.py::test_two_processes_x_200_locked_increments_end_at_400_no_lost_updates` spawns 2 subprocesses × 200 locked increments through `poll_loop.poll_cycle_lock`/`save_poll_state`; asserts both exit 0, empty stderr, final counter == 400, no leftover `.tmp`. Ran green in this verification session (`pytest -q server/test_poll_lock.py` — passed). SUMMARY records the RED run against pre-change code failed 4/5 times with `FileNotFoundError` on the shared fixed `.tmp` name. |
| 2 | One `atomic_write` helper; no fixed `.tmp` name left in Python code (byos local copy and `deploy/activate.sh` excepted) | VERIFIED | Exactly two `def atomic_write`/`def _atomic_write` definitions repo-wide: `server/atomic_io.py:144` (the shared helper) and `stub-server/byos_server.py:124` (documented vendor-boundary copy, parity-tested). Every remaining `.tmp` suffix in Python code (`server/atomic_io.py`, `companion/app.py`, `stub-server/byos_server.py`, `deploy/backup/backup_gate.py`) comes from `tempfile.mkstemp(..., suffix=".tmp")` (unique per-write names), not a fixed `path + ".tmp"`. `server/device_config.py`, `server/plane/colour_rules.py`, `server/plane/manual_resolutions.py`, `server/plane/calendar_rules.py`, `server/poll_loop.py`, `companion/app.py`, `companion/theme_preview.py` all import/use `atomic_io`. `deploy/backup/skypane_backup.py`'s unique `.partial-<archive>`/`.tmp-` names and `deploy/activate.sh`'s symlink swap are confirmed out of scope per 36-CONTEXT and untouched. |
| 3 | `/img/<unknown sha>` → 404; a panel swap mid-wake no longer fails SHA verification | VERIFIED | `stub-server/byos_server.py`: `_publish_image()` writes `img/<sha>.bin` via `_atomic_write` before the JSON answer; `_IMG_PATH_RE` full-path regex serves only `^/img/[0-9a-f]{64}\.bin$`; any other path/hash → 404. `stub-server/test_byos_hardening.py::test_display_publishes_image_and_img_endpoint_serves_it_by_hash` replaces the served `--image` file with different bytes between `/display` and the download and asserts the download still returns the originally-advertised hash's bytes; `test_img_endpoint_404_for_unknown_or_malformed_paths` covers unknown hash, path traversal, wrong case, query string, no extension, bare `/img/`, and a 63-hex name, all → 404. Both pass. |
| 4a | byos survives malformed `Content-Length`/`mac` input | VERIFIED | `read_body_json()`: missing `Content-Length` → 0; non-integer/negative → 400; > 64 KiB (`MAX_BODY_BYTES`) → 413, neither reads the body. `Handler.timeout` (15s default, `--request-timeout` override) drops a stalled client. `bearer_ok()` uses `hmac.compare_digest` against every stored token, no early exit. `/device/v1/log` skips non-dict entries. Non-string `mac` already fixed by Phase 34 (`normalize_mac()`), re-confirmed not regressed. Tests: `test_malformed_content_length_gets_400_or_413_without_hanging`, `test_stalled_client_dropped_after_request_timeout_others_still_served`, `test_client_sending_nothing_is_closed_after_timeout_no_traceback`, `test_bearer_ok_wrong_right_and_non_ascii`, `test_log_endpoint_skips_non_dict_entries_and_accepts_dict_ones`, `test_log_endpoint_rejects_deeply_nested_body_with_422_not_500` — all pass. |
| 4b | The poll unit has a start timeout | VERIFIED | `deploy/skypane-poll.service` line 24: `TimeoutStartSec=90s`. `deploy/tests/test_units.py` asserts `cp["Service"]["TimeoutStartSec"] == "90s"` — passes. Production confirmation of the running unit is a human item (see below). |
| 5 | A transient adsbdb error is never cached as a miss | VERIFIED | `server/plane/enrich.py::_lookup()`: 404 or routeless 2xx → cached as a miss; any raised exception, 429, other 5xx, or non-404 4xx → `return None, False` "WITHOUT touching the cache" (code comment + behaviour match). `CACHE_MISS_TTL_S`/`CACHE_HIT_TTL_S` with `cached_at`-based expiry, legacy-entry handling, and LRU touch-on-read (`cache[key] = cache.pop(key)`) all present and covered by `server/test_enrich.py`. |
| 6 | INT-01: one poll cycle at a time, across processes; `/poll-now` never blocks | VERIFIED | `server/poll_loop.py`: `poll_cycle_lock()` wraps `run_once()`'s whole body over `atomic_io.exclusive_lock`; oneshot waits `POLL_LOCK_WAIT_S=10s` (default), companion's `_handle_poll_now()` calls `run_once(..., lock_timeout_s=0)`, catches `poll_loop.PollBusy` → `FLASH_KEY_POLL_ALREADY_RUNNING`, never blocking the request thread. `companion/test_poll_now_lock.py` and `server/test_poll_lock.py` pass. |
| 7 | INT-03: `save_device_config` has no lost updates | VERIFIED | `server/device_config.py`: module `_SAVE_LOCK = threading.Lock()` plus `atomic_io.exclusive_lock(<state_dir>/device_config.lock)` around the whole load-merge-write. `server/test_state_writers.py` covers concurrent multi-thread saves. |
| 8 | INT-04: theme preview and illustration caches are atomic, pruned, bounded | VERIFIED | `companion/theme_preview.py`: `atomic_io.atomic_write` + `_prune_preview_cache()` (stale-signature removal, bound to `THEME_PREVIEW_CACHE_MAX_FILES=64`). `companion/illustration_normalize.py`: `_cached_normalized_png_bytes` wrapped in `functools.lru_cache(maxsize=NORMALIZED_CACHE_MAX_ENTRIES=128)`. `companion/test_preview_cache.py` passes. |
| 9 | INT-07: bounded poll cycle — every outbound HTTP call has a total deadline | VERIFIED | `server/http_fetch.py::bounded_get`/`pinned_request` provide deadline+byte-cap and pinned-address connection; used by `server/plane/detect.py::query_provider` (`PROVIDER_DEADLINE_S`), `server/plane/enrich.py::default_transport` (`ADSBDB_DEADLINE_S`), `server/plane/calendar_rules.py::fetch_ics` (`CALENDAR_FETCH_DEADLINE_S`), `server/notify.py` (`NOTIFY_DEADLINE_S`). `server/test_http_fetch.py` and per-module tests pass. |
| 10 | INT-09: Caddy log tailer never fails the cycle on bad input | VERIFIED | `server/history_db.py::tail_caddy_battery_log` reads binary, only complete (`\n`-terminated) lines, byte-exact offsets, guards `datetime.fromtimestamp()` against `OverflowError`/`OSError`/`ValueError`; `ingest_caddy_battery_log` resets a bad stored offset to 0. `server/test_caddy_tail.py` passes. |
| 11 | INT-10: provider JSON shape is type-checked | VERIFIED | `server/plane/detect.py::query_provider` raises `ValueError` for a non-dict body or non-list aircraft field; drops non-dict aircraft records before geofencing. `server/test_plane_detection.py` passes. |
| 12 | INT-11: full traceback on cycle failure | VERIFIED | `server/poll_loop.py::main()`: generic `except Exception` branch prints a one-line summary then `traceback.print_exc(file=sys.stdout)` before `return 1`; `PollBusy` handled separately without a traceback (expected, bounded outcome). |
| 13 | INT-12: calendar clock and lock — `last_synced_at` from injected clock, lock not held during fetch | VERIFIED | `refresh_calendar_registry()`: lock → load/throttle/record attempt → unlock → `fetch_ics()` (unlocked) → lock → reload/re-check URL, discard as `FETCH_SUPERSEDED` if the URL changed mid-fetch, else persist with `last_synced_at=now` (the injected clock) → unlock. `_calendar_registry_lock()` delegates to `atomic_io.exclusive_lock`. `server/test_calendar_rules.py` passes. |
| 14 | INT-13: queued-but-undisplayed detection still advances last-detection | VERIFIED | `server/poll_loop.py` held branch (line ~1253): `_record_history(..., detected=flight is not None)` while still passing the held `flight=None`/`current_flight` for display state; `_record_history` advances `META_LAST_DETECTION` on `flight is not None or detected`. |
| 15 | INT-14: pin the resolved address for outbound connections | VERIFIED | `server/http_fetch.py::pinned_request`/`resolve_public_addresses`/`address_is_public`: resolves once, refuses any non-public answer, connects only to a checked address via an `http.client.HTTPSConnection` subclass, TLS verified against the hostname. Used by both `calendar_rules.default_calendar_transport` and `notify.default_notify_transport`. `server/test_http_fetch.py` (32 tests, captured sockets, no network) passes. |

**Score:** 15/15 truths verified (14 requirement IDs INT-01..INT-14, all mapped)

### 37-11 Precondition Check

| Precondition | Status | Evidence |
|---|---|---|
| Server construction stays one expression `ThreadingHTTPServer(("0.0.0.0", args.port), Handler)` | VERIFIED | `stub-server/byos_server.py:882`, single matching line, no other `ThreadingHTTPServer(` construction found. |
| byos makes no outbound connection | VERIFIED | No `urllib`, `requests.`, `http.client`, or `socket.create_connection`/`socket.socket(` calls found anywhere in `stub-server/byos_server.py`. |

### Required Artifacts

| Artifact | Expected | Status | Details |
|---|---|---|---|
| `server/atomic_io.py` | `atomic_write`, `staged_write`, `exclusive_lock`, `LockBusy`, `DEFAULT_FILE_MODE` | VERIFIED | All present; 19+ behaviour tests in `server/test_atomic_io.py`, all pass. |
| `server/http_fetch.py` | `bounded_get`, `pinned_request`, `address_is_public`, `resolve_public_addresses`, exception types | VERIFIED | All present, exported; `server/test_http_fetch.py` (32 tests) passes, module coverage 98%. |
| `deploy/skypane-poll.service` | `TimeoutStartSec=90s` | VERIFIED | Present at line 24; asserted by `deploy/tests/test_units.py`. |
| `stub-server/byos_server.py` | `_atomic_write`, content-addressed `img/`, request hardening | VERIFIED | All present and exercised by `stub-server/test_byos_hardening.py`. |
| `server/device_config.py` | locked `save_device_config` | VERIFIED | `_SAVE_LOCK` + `atomic_io.exclusive_lock`. |
| `companion/theme_preview.py` | atomic, pruned, bounded preview cache | VERIFIED | `THEME_PREVIEW_CACHE_MAX_FILES`, `_prune_preview_cache`. |
| `server/plane/calendar_rules.py` | pinned transport, split lock, injected clock, atomic writes | VERIFIED | `pinned_request`, three-step `refresh_calendar_registry`, `_calendar_registry_lock` → `exclusive_lock`. |
| `server/notify.py` | pinned, deadline-bounded POST | VERIFIED | `pinned_request`, `NOTIFY_DEADLINE_S`. |
| `server/plane/enrich.py` | TTL + LRU adsbdb cache, transient-safe | VERIFIED | `CACHE_MISS_TTL_S`/`CACHE_HIT_TTL_S`, `_lookup()`. |
| `server/plane/detect.py` | type-checked provider body, bounded transport | VERIFIED | `query_provider` uses `http_fetch.bounded_get`, raises `ValueError` on bad shape. |
| `server/history_db.py` | binary, newline-exact Caddy tailer | VERIFIED | `tail_caddy_battery_log`. |
| `server/poll_loop.py` | `poll_cycle_lock`, `PollBusy`, atomic writes, traceback, last-detection fix | VERIFIED | All present, `server/test_poll_lock.py`/`server/test_poll_loop.py` pass. |

### Key Link Verification

| From | To | Via | Status | Details |
|---|---|---|---|---|
| `atomic_io.atomic_write` | `os.replace` | fsynced mkstemp temp | WIRED | `server/atomic_io.py:144-` implementation confirmed; multi-thread/multi-process tests pass. |
| `atomic_io.exclusive_lock` | `fcntl.flock` | LOCK_EX\|LOCK_NB polled to monotonic deadline | WIRED | Confirmed in source and by cross-process/cross-thread lock tests. |
| `/device/v1/display image_url` | `<state_dir>/img/<sha>.bin` | `_publish_image()` before JSON answer | WIRED | Confirmed by `test_display_publishes_image_and_img_endpoint_serves_it_by_hash`. |
| `GET /img/<sha>.bin` | `<state_dir>/img/<sha>.bin` | full-path regex match | WIRED | `_IMG_PATH_RE`, confirmed by 404 test suite. |
| `companion/app.py _handle_poll_now` | `poll_loop.run_once(lock_timeout_s=0)` | `except poll_loop.PollBusy -> FLASH_KEY_POLL_ALREADY_RUNNING` | WIRED | Confirmed at `companion/app.py:1967-1975`. |
| `server/poll_loop.py run_once` | `atomic_io.exclusive_lock(<state_dir>/poll.lock)` | `poll_cycle_lock` | WIRED | Confirmed; two-process reproduction passes. |
| `calendar_rules.default_calendar_transport` | `http_fetch.pinned_request` | GET, per-hop timeout clamped | WIRED | Confirmed at `server/plane/calendar_rules.py:1016-1021`. |
| `notify.default_notify_transport` | `http_fetch.pinned_request` | POST, no redirects | WIRED | Confirmed at `server/notify.py:95-105`. |
| `detect.query_provider` | `http_fetch.bounded_get` | GET with deadline/byte cap | WIRED | Confirmed at `server/plane/detect.py:361-364`. |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|---|---|---|---|---|
| INT-01 | 01, 07 | Cross-process poll lock, no lost updates | SATISFIED | `poll_cycle_lock`, `server/test_poll_lock.py` reproduction passes at 400/400. |
| INT-02 | 01, 03, 04, 05, 07 | One `atomic_write` helper, no fixed `.tmp` name | SATISFIED | `server/atomic_io.py` + byos parity copy; grep confirms no other fixed-name writer. |
| INT-03 | 04 | `save_device_config` thread lock + flock | SATISFIED | `server/device_config.py`. |
| INT-04 | 04 | `mkstemp`, pruning, bounded caches | SATISFIED | `theme_preview.py`, `illustration_normalize.py`. |
| INT-05 | 03 | Content-addressed `img/<sha>.bin`, 404 on unknown | SATISFIED | `stub-server/byos_server.py`, `test_byos_hardening.py`. |
| INT-06 | 03 | Validated length, `Handler.timeout`, `hmac.compare_digest` | SATISFIED | `stub-server/byos_server.py`. |
| INT-07 | 02, 05, 06, 07 | `TimeoutStartSec`, total deadline per HTTP call | SATISFIED | `deploy/skypane-poll.service`, `server/http_fetch.py` usage across modules. |
| INT-08 | 06, 07 | adsbdb cache: miss only on 404/empty, TTL, LRU | SATISFIED | `server/plane/enrich.py::_lookup`/`_fresh_entry`/`trim_cache`. |
| INT-09 | 06 | Caddy tailer: complete lines, guarded ts/offset | SATISFIED | `server/history_db.py`. |
| INT-10 | 06 | Provider body type-checked | SATISFIED | `server/plane/detect.py::query_provider`. |
| INT-11 | 07 | Full traceback on cycle failure | SATISFIED | `server/poll_loop.py::main()`. |
| INT-12 | 05 | Injected clock, lock released during fetch | SATISFIED | `server/plane/calendar_rules.py::refresh_calendar_registry`. |
| INT-13 | 07 | Queued detection updates last-detection | SATISFIED | `server/poll_loop.py` held branch, `detected=flight is not None`. |
| INT-14 | 02, 05 | Pin resolved address for outbound connections | SATISFIED | `server/http_fetch.py::pinned_request`, used by calendar + notify. |

All 14 requirement IDs declared across the phase's seven plans (01–07) are accounted for; none orphaned. REQUIREMENTS.md marks all 14 `[x]` Complete for Phase 36, consistent with this verification's independent code evidence (not merely trusted from the checklist).

### Anti-Patterns Found

None found. Scanned every file touched across plans 01–07 for `TBD`/`FIXME`/`XXX`/`TODO`/`HACK`/`PLACEHOLDER`, "not yet implemented"/"coming soon", and empty-return stub shapes. All matches (`XXX` as an IATA-code test fixture value, `XXXXXX` in a `mkstemp` pattern docstring, "placeholder" in legitimate docstrings/comments about template filling and adsbdb cache-miss placeholders, and `return []`/`return {}` as genuine default-value code paths) are false positives, not debt markers or stubs.

### Behavioral Spot-Checks / Test Execution

| Check | Command | Result | Status |
|---|---|---|---|
| Targeted phase tests | `server/.venv/bin/python -m pytest -q server/test_poll_lock.py stub-server/test_byos_hardening.py server/test_atomic_io.py server/test_http_fetch.py` | 76 passed, 1 skipped (root ignores directory permission bits — expected under root) | PASS |
| Full suite | `./scripts/run-all-tests.sh` | 2721 passed, 133 skipped (Playwright Chromium missing in this sandbox + root-permission skips — both expected here), coverage 93.85% (floor 93.0%) | PASS |
| Lint | `server/.venv/bin/ruff check .` | All checks passed! | PASS |
| Comment-history guard | `server/.venv/bin/python scripts/check_comment_history.py check` | exit 0, no output | PASS |
| 37-11 preconditions | grep for `ThreadingHTTPServer(` and outbound-connection calls in `stub-server/byos_server.py` | single expression at line 882; zero outbound-connection calls | PASS |

### Probe Execution

Not applicable — this phase has no `scripts/*/tests/probe-*.sh` files and its PLAN/SUMMARY/VALIDATION documents describe pytest-based verification, not shell probes. Skipped.

### Human Verification Required

### 1. Production poll unit start timeout

**Test:** After deploying this phase to the VPS, run `systemctl show skypane-poll.service -p TimeoutStartUSec`.
**Expected:** Output shows `TimeoutStartUSec=1min 30s`.
**Why human:** Needs the deployed systemd instance to parse and report the unit's live timer value; the static unit file text (`TimeoutStartSec=90s`) and its regression test (`deploy/tests/test_units.py`) are already verified in-repo, but confirming the deployed daemon's own interpretation requires production access this verifier does not have.

**Result (2026-09-26, developer on the VPS, after the 37-11 deploy of `34bc038`):** `TimeoutStartUSec=1min 30s`: PASSED.

### 2. On-frame panel-swap check (optional)

**Test:** Trigger `/poll-now` twice in quick succession during a real device wake.
**Expected:** The frame shows the image it was told about; no `verify` failure appears in the frame's log.
**Why human:** Needs the physical e-ink frame and firmware wake cycle. The equivalent server-side behaviour (byos serving the originally-advertised hash's bytes even after the underlying `--image` file changes) is already covered by an automated subprocess test (`test_display_publishes_image_and_img_endpoint_serves_it_by_hash`); this item only adds confidence that the real firmware's SHA-256 verification path (`firmware/main/api_client.c`) behaves the same way end to end, which this phase's CONTEXT explicitly notes had no firmware change.

### Gaps Summary

No gaps found. All 14 phase requirement IDs (INT-01..INT-14) and all 5 ROADMAP success criteria are independently verified against the actual codebase (not SUMMARY claims): source code was read directly for every claimed mechanism, the specific reproduction/regression tests were located and re-run rather than trusted, the targeted test subset and the full suite both pass, ruff and the comment-history guard are green, and the 37-11 precondition on `byos_server.py` holds. The only two items not resolvable from this sandbox are genuinely infrastructure-bound (a production systemd query and an optional real-hardware check) and were already flagged as manual-only in `36-VALIDATION.md`; per this phase's instructions they do not block `passed`-level confidence on the automatable checks, but per the standard decision tree any non-empty human-verification list yields `status: human_needed` rather than `passed`.

---

*Verified: 2026-09-26T11:23:28Z*
*Verifier: Claude (gsd-verifier)*
