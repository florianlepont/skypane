# Phase 36: State integrity and device protocol - Research

**Researched:** 2026-09-25 (inline by the orchestrator, against `main` at `9eb92a6`)
**Domain:** file-level concurrency (flock, atomic rename), a stdlib HTTP device server, bounded outbound HTTP, SSRF pinning
**Confidence:** HIGH for the re-located evidence (every row read in the code), MEDIUM for line numbers at execution time (Phase 35's remaining plans still edit comments in several of these files)

## Summary

All 14 findings are still open, except two sub-items of INT-06 that Phase 34 already fixed (typed `mac`, `hmac.compare_digest` for the enrolment secret). The ledger's line numbers are stale: Phase 35 cut `poll_loop.py` from ~2000 to 1307 lines, `byos_server.py` to 661 and `companion/app.py` to 2258, and `detect.py`, `enrich.py`, `calendar_rules.py` now live under `server/plane/`. Executors must re-locate by symbol, not by line.

**Primary recommendation:** land two small stdlib helpers first (`server/atomic_io.py` for `atomic_write` + `exclusive_lock`, and one outbound-HTTP module for the total deadline and the pinned connection), then migrate callers file by file in parallel plans, with `poll_loop.py` + `companion/app.py` last because they consume the most helpers.

## Re-located findings (current evidence)

| ID | Where now (`9eb92a6`) | Status | Notes |
|----|----------------------|--------|-------|
| INT-01 | `server/poll_loop.py` `run_once()` (l. 679) has no cross-process lock; `companion/app.py` `_POLL_LOCK = threading.Lock()` (l. 439) guards `_handle_poll_now()` (l. 1935) only inside the companion process; the timer oneshot is `main()` (l. 1292) | Open | `_POLL_LOCK` is also taken by the two calendar-sync handlers (l. 1631, 1916); keep it as the in-process fast path |
| INT-02 | Fixed `path + ".tmp"`: `poll_loop.py` `save_poll_state` (l. 488), `write_panel_atomic` (l. 515); `device_config.py` `save_device_config` (l. 580); `byos_server.py` `save_state` (l. 104), `save_registry` (l. 161, 0600 via `os.open`), `save_battery_state` (l. 462); `deploy/backup/backup_gate.py` `_cmd_ack` (l. 123, `.last-pull.tmp`). pid(+tid) names: `calendar_rules.py` (l. 710, 772), `colour_rules.py` (l. 238, 277), `manual_resolutions.py` (l. 307, 355), `companion/app.py` illustration upload (l. 1402-1404, pid only), `companion/theme_preview.py` (l. 204, pid only). Non-atomic: `poll_loop._save_to_gallery` saves the PNG in place (l. 673) | Open | 11 fixed/pid-only sites + 1 non-atomic. `skypane_backup.py`'s `.partial-<name>` is per-archive and self-cleaning: out of scope |
| INT-03 | `server/device_config.py` `save_device_config` (l. 473-591): load → merge → write, no lock | Open | Only the companion calls it (`app.py` l. 2009, `config_page.py` l. 3364), from `ThreadingHTTPServer` threads |
| INT-04 | `companion/theme_preview.py` `cached_preview_bytes` (l. 184-208): pid-only temp name shared by threads, cache files keyed by signature never pruned; `companion/illustration_normalize.py` `@functools.lru_cache(maxsize=None)` keyed by `(path, mtime_ns)` (l. 69) | Open | |
| INT-05 | `byos_server.py` `do_GET` `/img/` branch (l. 604-614) serves the current `--image` for any path under `/img/` | Open | Firmware side confirmed below |
| INT-06 | `Handler.read_body_json` (l. 474-479): `int(Content-Length)` unbounded, negative → `rfile.read(-1)` reads to EOF (blocks on keep-alive); no `Handler.timeout`; `bearer_ok` (l. 481-484) uses `in values()`; `/device/v1/log` calls `entry.get` on each list item (l. 531) | Partly fixed | Typed `mac` fixed by FW-08 (`normalize_mac`, l. 124); enrolment secret already `hmac.compare_digest` (l. 205) |
| INT-07 | `deploy/skypane-poll.service`: `Type=oneshot`, no `TimeoutStartSec` (systemd default for oneshot is *infinity*); `requests.get(..., timeout=)` in `detect.query_provider` (l. 328), `enrich.default_transport` (l. 132), `calendar_rules.default_calendar_transport` (l. 1050, stream=True); `notify.default_notify_transport` (urllib, l. 102) | Open | `timeout=` in requests bounds connect and each socket read, not the transfer |
| INT-08 | `server/plane/enrich.py` `lookup_route` (l. 282-336) caches `{"found": False}` on any exception and any non-2xx; `trim_cache` (l. 606) is FIFO; no timestamps | Open | Cache lives in `poll_state.json["enrichment_cache"]` |
| INT-09 | `server/history_db.py` `tail_caddy_battery_log` (l. 441-505): text-mode `for line in fh` then `fh.tell()` → a partial last line is skipped and the offset moves past it; `ingest_caddy_battery_log` (l. 507) does `int(stored_offset)` unguarded; `datetime.fromtimestamp(ts_raw)` (l. 490) unguarded | Open | `_record_history` catches only `sqlite3.Error, OSError`, so a `ValueError`/`OverflowError` fails the cycle |
| INT-10 | `server/plane/detect.py` `query_provider` (l. 319-332): `data.get(...)` on a non-dict raises `AttributeError`, which `poll_current_aircraft` (l. 690) does not catch; non-dict records reach `ac.get` in `filter_in_geofence` | Open | |
| INT-11 | `server/poll_loop.py` `main()` (l. 1292-1303) prints `type(exc).__name__: exc` only | Open | |
| INT-12 | `server/plane/calendar_rules.py` `refresh_calendar_registry` (l. 1163-1245): `last_synced_at = datetime.now(timezone.utc)` (l. 1226); the whole load-throttle-fetch-write runs inside `_calendar_registry_lock` (l. 1187), so a companion save waits up to the fetch time (lock timeout 15 s > fetch timeout) | Open | |
| INT-13 | `server/poll_loop.py` held branch (l. 1119-1182) calls `_record_history(state_dir, None, ...)`, and `_record_history` (l. 584) sets `META_LAST_DETECTION` only `if flight is not None` (l. 618) | Open | Read by `companion/pages/health_page.py` "Last aircraft detected" |
| INT-14 | `calendar_rules._host_is_safe` (l. 967-990) docstring claims DNS-rebinding protection; the fetch then calls `requests.get(url)`, which resolves again. `notify.send_notification` (l. 107) reuses `_url_is_safe` then `urllib` resolves again | Open | Decision in CONTEXT: pin |

## Firmware check for INT-05 (no firmware change)

- `firmware/main/api_client.c` `fp_api_download`: reads up to 960 000 bytes, rejects oversize, computes SHA-256 only when `status == 200 && got == FP_IMAGE_BYTES`, and `fp_download_verdict` returns `BAD_TRANSFER` (→ `ESP_FAIL`) or `HASH_MISMATCH` (→ `FP_ERR_IMAGE_VERIFY`).
- `firmware/main/state_machine.c`: a download error returns `FP_POLL_FAILED` with step `download` or `verify`; the NVS hash is only stored after a successful blit, so the next wake retries.
- Today's bug: `/display` advertises hash X, the poll loop swaps `panel.bin` to Y before the device fetches, byos serves Y under `/img/X.bin` → `verify` failure and backoff. With content addressing the device gets X (correct) or a 404 (only if X was pruned) → `download` failure, retried. Both are handled by existing firmware paths.

## Architecture patterns to reuse

- **flock:** `calendar_rules._calendar_registry_lock` (l. 153-192) is the house pattern: `os.open(path, O_CREAT|O_RDWR, 0o600)`, `LOCK_EX|LOCK_NB` polled until a monotonic deadline, `TimeoutError` on expiry, unlock in `finally`, POSIX-only import guard. `exclusive_lock` generalises it (plus a `blocking=False` mode that raises immediately).
- **Atomic write with a secret mode:** `byos_server.save_registry` creates the temp with `os.open(..., 0o600)` so the file is never briefly world-readable; `calendar_rules` URL-secret writer does the same (l. 772-802). `atomic_write(mode=...)` must create the temp with that mode (mkstemp already creates 0600; `os.fchmod` to a wider mode before rename when asked, never chmod-after-rename).
- **Two OS processes in a test:** `stub-server/test_poll_cycle.py` byos harness (`subprocess.Popen` on a free port, `tmp_path` state dir) and `test-support/companion_app_server.py` `AppServer`. For INT-01 a simpler `multiprocessing` (spawn context) or `subprocess` running a tiny `python -c` loop over the real `poll_loop` lock + `save_poll_state` is enough; it needs no sockets.
- **Fake upstreams:** `conftest.py` `fake_providers` fixture, `_stub_adsbdb` in `server/test_poll_loop.py`, the calendar `transport=` seam, the notify `transport=` seam.
- **Clock seams:** `poll_loop.now_s()` (monkeypatched by the `clock` fixture in `server/test_poll_loop.py`), `refresh_calendar_registry(state_dir, now, ...)`.

## Design notes per requirement

- **INT-01:** acquire the lock at the top of `run_once()` (before any state read) and release in `finally`. Expose a "busy" signal the companion can catch without blocking (e.g. `run_once(..., wait_for_lock=False)` raising a dedicated `PollBusy`). The oneshot waits with a bounded timeout (below `TimeoutStartSec`). The existing companion test that two concurrent `POST /poll-now` yield one `poll_already_running` must stay green; add one where the lock is held by another process.
- **INT-02:** `mkstemp` gives a unique name and 0600; the file must also be `fsync`ed before `os.replace` (power loss on a VPS is rare, but the rename is only meaningful after the data is durable). The temp suffix stays `.tmp` so `skypane_backup.py`'s `KNOWN_EXCLUDED` `*.tmp` keeps covering leftovers. mkstemp creates 0600, while `open(path, "w")` gave `0o666 & ~umask` (0640 under the units' `UMask=0027` and the setgid `state/` group). All four services run as `skypane`, so 0600 would still be readable by them, but the group read the operator and backups rely on would silently disappear. Default `mode=None` must therefore reproduce `0o666 & ~umask` (read the umask once, thread-safely, e.g. at import); an explicit `mode` (0600 for secrets) is applied with `os.fchmod` on the temp fd before the rename.
- **INT-05:** byos writes `img/<sha>.bin` before answering `/display`; the write happens only when the hash is new (one 960 KB write per panel change). Prune after the write, newest N by mtime, ignoring names that do not match the hash pattern. `/img/` must match the full path `^/img/([0-9a-f]{64})\.bin$`; anything else is 404 (today any `/img/*` path returns the image).
- **INT-06:** `BaseHTTPRequestHandler.timeout` is applied to the connection socket by `StreamRequestHandler.setup()`. Cap the body before reading. Return 400 for a malformed length and 413 for an oversized one; never read the body in those cases.
- **INT-07:** a helper like `bounded_get(url, headers, connect_timeout, read_timeout, deadline_s, max_bytes)` built on `requests.get(stream=True)` and `iter_content`, raising a `requests.Timeout` subclass on deadline so existing `except requests.RequestException` handlers keep working. For the pinned stdlib connection (INT-14) set the socket timeout to `min(read_timeout, remaining)` before each read.
- **INT-08:** `lookup_route(callsign, cache, transport=None, timeout=..., now=None)`; `resolve_route` passes `now` through; `poll_loop` passes `now_s()` (wave 3). On a transient failure return `None` without touching the cache.
- **INT-12:** after the fetch, reload the registry under the lock and compare the configured URL with the fetched one before writing; if different, return the reloaded registry with `FETCH_SKIPPED_*`/`FETCH_FAILED` semantics the callers already understand (check `companion/app.py` flash mapping).
- **INT-14:** `http.client.HTTPSConnection` subclass whose `connect()` does `socket.create_connection((pinned_ip, port), timeout)` then `ssl.create_default_context().wrap_socket(sock, server_hostname=hostname)`; request line and `Host` header use the hostname. Resolution: `getaddrinfo` once, refuse if any address is not public (existing `_address_is_public`), connect to the first. Redirect hops in `fetch_ics` re-resolve and re-pin per hop. The calendar response object must keep the attributes `fetch_ics` reads (`status_code`, `is_redirect`, `headers.get`, `iter_content`, `close`) so the existing fake-transport tests stay valid; notify keeps "no redirects" (a 3xx is a failure).

## Common pitfalls

- **Lock ordering / deadlock:** `run_once` holds `poll.lock` and, inside, `refresh_calendar_registry` takes `calendar_rules.lock`; the companion's calendar-save handler takes only `calendar_rules.lock`. Never take `poll.lock` while holding `calendar_rules.lock`. `device_config.lock` is taken by the companion only (the poll loop only reads). Document the order in `atomic_io`.
- **flock is per open file description:** two threads in one process opening the lock file separately do exclude each other with `flock` on Linux, but relying on that is fragile; keep the thread lock too (INT-03, `_POLL_LOCK`).
- **Tests that monkeypatch `save_poll_state` or read `panel.bin.tmp`:** grep `server/`, `stub-server/`, `companion/` tests for `.tmp` and for the helper names before changing signatures.
- **Behaviour-over-source rule:** do not write a test that greps the tree for `".tmp"`; prove unique names by behaviour (concurrent writers, no exception, no leftover) and check the "no fixed name" criterion with `grep` in acceptance criteria.
- **byos drift guard:** `stub-server/test_poll_cycle.py` already reads source text for the quiet-hours drift guard (pre-existing, outside the companion guard's scope). Do not add another source-text guard for `_atomic_write`; use a behaviour-parity test.
- **37-11 compatibility:** keep `ThreadingHTTPServer(("0.0.0.0", args.port), Handler)` as a single expression and add no outbound call to byos (37-11 greps for both).
- **pytest-socket:** the pinned-TLS test must run a loopback TLS server with a self-signed cert generated at test time (or stub `socket.create_connection` and `ssl.SSLContext.wrap_socket` to capture arguments). Prefer the capture approach: no certificate tooling needed.

## Proposed plan structure (for the planner; files disjoint per wave)

| Wave | Plan | Requirements | Files |
|------|------|--------------|-------|
| 1 | 36-01 atomic_io | G-35 gate, INT-02 (helper), flock helper | `server/atomic_io.py`, `server/test_atomic_io.py` |
| 1 | 36-02 outbound HTTP | G-35 gate, INT-07 (deadline helper), INT-14 (pinned primitive) | new module(s) under `server/` + tests |
| 2 | 36-03 byos | INT-02 (byos copy), INT-05, INT-06 | `stub-server/byos_server.py`, `stub-server/test_byos_hardening.py` (new), `stub-server/test_poll_cycle.py` (only if the e2e test needs the new `/img` contract) |
| 2 | 36-04 config/caches | INT-02, INT-03, INT-04 | `server/device_config.py`, `server/plane/colour_rules.py`, `server/plane/manual_resolutions.py`, `companion/theme_preview.py`, `companion/illustration_normalize.py`, `deploy/backup/backup_gate.py`, their tests |
| 2 | 36-05 calendar + notify | INT-02 (calendar), INT-07 (calendar/notify), INT-12, INT-14 | `server/plane/calendar_rules.py`, `server/notify.py`, `server/test_calendar_rules.py`, `server/test_notify.py` |
| 2 | 36-06 upstream parsing | INT-07 (detect/enrich), INT-08, INT-09, INT-10 | `server/plane/enrich.py`, `server/plane/detect.py`, `server/history_db.py`, their tests |
| 3 | 36-07 poll cycle | INT-01 (+ reproduction), INT-02 (poll_loop, gallery, companion upload), INT-07 (unit), INT-11, INT-13, enrich clock wiring | `server/poll_loop.py`, `companion/app.py`, `deploy/skypane-poll.service`, `server/test_poll_loop.py`, `server/test_poll_lock.py` (new), companion tests touching `/poll-now` |

## Validation Architecture

- **Framework:** pytest 9 with xdist and coverage (`./scripts/run-all-tests.sh` = `pytest -n auto --cov`), config in `pyproject.toml`; pytest-socket non-loopback guard + DNS guard in `conftest.py`.
- **Quick command per plan:** `server/.venv/bin/python -m pytest -q <the plan's test files>` plus `server/.venv/bin/ruff check .` and `server/.venv/bin/python scripts/check_comment_history.py check`.
- **Full command per wave:** `./scripts/run-all-tests.sh`.
- **Per-requirement proof:**
  - INT-01: two OS processes × 200 locked read-increment-save cycles through the real `poll_loop` lock and `save_poll_state` → final counter 400, zero exceptions in either child; a second test with the lock held by another process → companion `POST /poll-now` answers the "already running" flash without waiting.
  - INT-02: N threads and 2 processes writing the same path through `atomic_write` → no exception, final content is one complete payload, no `*.tmp` left; failure injection (write raises) leaves no temp and the old file intact; mode preserved. Tree grep in acceptance: no `+ ".tmp"` and no `%d.tmp`/`getpid()`-only temp name in production code.
  - INT-03: concurrent `save_device_config` from threads with disjoint fields → every field lands (no lost update).
  - INT-04: two threads rendering the same cold preview → no exception, one file; stale-signature files removed; cache directory bounded; `lru_cache` reports a finite `maxsize`.
  - INT-05: byos subprocess: `/display` → X; replace image → `/img/X.bin` returns bytes hashing to X; `/img/<64 hex unknown>.bin` → 404; `/img/../x` and non-hex → 404; `img/` never exceeds N files.
  - INT-06: byos subprocess: negative, non-numeric and oversized `Content-Length` → 4xx without hanging; a client that sends headers and stalls is dropped after `Handler.timeout` and the next request is served; wrong bearer → 401; `logs: [1, "x", null]` → no 500.
  - INT-07: fake slow-trickle transport → call ends by the deadline with a timeout error the caller already handles; `deploy/tests/test_units.py` (already parses the units) gains an assertion that `skypane-poll.service` has `TimeoutStartSec=90s` (the value chosen in CONTEXT).
  - INT-08: 429/503/timeout → not cached, re-queried next call; 404 → cached miss that expires after 1 day; hit expires after 30 days; read moves entry to the end, trim evicts least recently used.
  - INT-09: partial last line → offset stops before it and the line is ingested once complete; offset "abc" or "-5" → reset, no raise; `ts` = 1e20 → line skipped, no raise.
  - INT-10: provider body `[]`, `"x"`, `{"ac": "x"}`, `{"ac": [1, None]}` → provider counted as failed or records dropped, cycle completes.
  - INT-11: `main()` with `run_once` raising → exit 1 and stdout contains `Traceback (most recent call last)`.
  - INT-12: `last_synced_at` equals the injected `now`; a registry save by another thread completes while a (fake, blocking) fetch is in progress; a URL changed during the fetch is not overwritten by the stale fetch result.
  - INT-13: a cycle that queues a second aircraft updates `last_detection` to that cycle's time.
  - INT-14: with a resolver that returns a public address first and a private one after, the connection goes to the first (checked) address and TLS `server_hostname` is the URL hostname; any private address in the first answer refuses the fetch.

## Sources

- Code on `main` at `9eb92a6` (files and lines cited above), firmware sources read only.
- Python docs: `fcntl.flock`, `tempfile.mkstemp`, `os.replace`, `socketserver.StreamRequestHandler.timeout`, `http.client.HTTPSConnection`, `ssl.SSLContext.wrap_socket(server_hostname=)`; systemd.service(5) `TimeoutStartSec` (oneshot default: infinity).
