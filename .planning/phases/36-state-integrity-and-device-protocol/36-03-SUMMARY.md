---
phase: 36-state-integrity-and-device-protocol
plan: 03
subsystem: infra
tags: [byos, atomic-write, content-addressing, http-hardening, hmac, stdlib]

# Dependency graph
requires:
  - phase: 36-01
    provides: "server/atomic_io.py: atomic_write(path, data, mode=None) - the contract byos._atomic_write mirrors (not imported; byos's vendor boundary)"
provides:
  - "stub-server/byos_server.py: _atomic_write(path, data, mode=None) - byos's own unique-temp-name atomic writer, used by save_state, save_registry (mode=0o600) and save_battery_state"
  - "stub-server/byos_server.py: _publish_image/_prune_images - content-addressed <state-dir>/img/<sha256>.bin, bounded to IMG_KEEP=8, GET /img/<sha>.bin serving exactly the published file"
  - "stub-server/byos_server.py: MAX_BODY_BYTES/REQUEST_TIMEOUT_S/--request-timeout, a hardened read_body_json() and bearer_ok(), non-dict /device/v1/log entries skipped"
affects: [37-11]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "byos keeps a local copy of server/atomic_io.py's atomic-write contract (mkstemp same-dir, unique temp name, fchmod before write, fsync, os.replace) instead of importing it, proven equal by a parity test parametrised over both callables rather than a source-text drift guard"
    - "content-addressed image serving: publish to img/<sha256>.bin before advertising the hash, prune to the newest N by mtime while never removing the just-advertised digest, serve only a full-path regex match"
    - "a length-check sentinel (_BAD_LENGTH) lets read_body_json() answer its own 400/413 without reading the body, while do_POST still owns every other response"

key-files:
  created: [stub-server/test_byos_hardening.py]
  modified: [stub-server/byos_server.py, stub-server/.gitignore]

key-decisions:
  - "_atomic_write is a single function (mkstemp -> fchmod -> write -> fsync -> os.replace, cleanup in except/finally), not a two-phase staged_write like server/atomic_io.py's - byos's three callers never need staged_write's inspect-before-commit step, so the smaller local copy is enough."
  - "_prune_images keeps at most IMG_KEEP survivors by taking the newest IMG_KEEP by mtime and swapping the oldest one out for keep_digest whenever keep_digest itself falls outside that window - guarantees both 'never more than IMG_KEEP files' and 'never prunes the just-advertised hash' with one pass, no special-casing."
  - "bearer_ok() iterates over list(self.state[\"tokens\"].values()) and keeps comparing after a match (no early return) so its timing does not depend on which stored token, if any, matched; both sides are encoded UTF-8/surrogateescape so a non-ASCII presented value degrades to \"no match\" rather than raising (the header block itself is parsed Latin-1, so no byte sequence a client sends can raise here)."
  - "log_message() reads self.command/self.path via getattr(...): a TimeoutError raised while BaseHTTPRequestHandler.handle_one_request() is still reading the request line (a client that connects and sends nothing) is caught before parse_request() ever sets those attributes, and the pre-existing direct-attribute log_message would have turned that into an unhandled AttributeError instead of the timeout log."
  - "REQUIREMENTS.md: INT-05 and INT-06 marked Complete (owned end-to-end here); INT-02 stays Pending - server/poll_loop.py, device_config.py and the other fixed-'.tmp'-name callers this phase's sibling plans still have to migrate are the same requirement, just not this plan's files."

requirements-completed: [INT-05, INT-06]

# Metrics
duration: 45min
completed: 2026-09-26
---

# Phase 36 Plan 03: byos hardening (atomic writes, content-addressed images, request hardening) Summary

**byos_server.py now writes its three state files through its own unique-temp-name `_atomic_write`, serves panel images by content hash from `<state-dir>/img/` (bounded to 8 files, the just-advertised hash never pruned), and survives a malformed `Content-Length`, a stalled client, a bad bearer token or a non-dict log entry without a 500 or a thread traceback.**

## Performance

- **Duration:** ~45 min
- **Started:** 2026-09-26T08:15:00Z (approx., first read of the plan)
- **Completed:** 2026-09-26T09:00:00Z (approx.)
- **Tasks:** 3 (all TDD: RED test commit then GREEN feat commit)
- **Files modified:** 3 (1 created: `stub-server/test_byos_hardening.py`; 2 modified: `stub-server/byos_server.py`, `stub-server/.gitignore`)

## Accomplishments
- **INT-02 (byos copy):** `_atomic_write` gives byos's three writers (`save_state`, `save_registry` at mode 0o600, `save_battery_state`) unique per-write temp names, replacing every fixed `path + ".tmp"`. A behaviour-parity test proves it shares `server/atomic_io.py`'s exact observable contract (str/bytes round trip, default mode from the umask, explicit mode, `os.replace` failure leaves the original untouched with no leftover temp, 8 threads x 50 writes land one complete payload) without ever importing `server.*` - byos's stdlib-only vendor boundary (`stub-server/VENDOR.md`) is unchanged.
- **INT-05:** `GET /device/v1/display` now publishes the served image to `<state-dir>/img/<sha256>.bin` (write once per new hash, refresh mtime on a re-advertised one) and prunes to the newest `IMG_KEEP=8` files before answering, so a panel swapped on disk between `/display` and the device's download can no longer produce a hash mismatch. `GET /img/<sha>.bin` now matches the full path against `_IMG_PATH_RE` and serves only that published file; path traversal, a wrong-case extension, a query string, a missing extension, the bare `/img/` path, a 63-hex name and an unpublished hash are all 404. A write failure (full or read-only state dir) answers 503 `"image unavailable"` instead of advertising an unservable hash.
- **INT-06 (remainder):** `read_body_json()` now rejects a missing (treated as 0), negative or non-integer `Content-Length` with 400, and one above `MAX_BODY_BYTES` (64 KiB) with 413 - neither case ever reads the body, both close the connection - and catches `RecursionError` alongside the existing decode errors, so a pathologically nested log body answers 422 instead of killing the connection. `Handler.timeout` (15 s default, `--request-timeout` override) drops a stalled client without pinning a `ThreadingHTTPServer` thread. `bearer_ok()` now compares every stored token with `hmac.compare_digest`, no early exit. `/device/v1/log` skips non-dict entries instead of crashing on `entry.get`. `log_message()` uses `getattr` so a timeout before the request line is parsed cannot itself raise.
- Confirmed already fixed by earlier phases and not redone here: the non-string `mac` crash (Phase 34, FW-08, `normalize_mac()`) and the enrolment secret's `hmac.compare_digest` (`secret_matches`) - only the bearer-token check needed the same treatment in this plan.
- 37-11 preconditions checked: `stub-server/byos_server.py` still builds its server with the single expression `ThreadingHTTPServer(("0.0.0.0", args.port), Handler)`, and still makes no outbound connection (no `urllib`, `requests`, `http.client` or `socket.create_connection` calls anywhere in the file) - 37-11's `--bind`/`IPAddressDeny=any` work applies unchanged.
- `stub-server/test_poll_cycle.py` was **not** changed: its end-to-end test already calls `/device/v1/display` before downloading `image_url` in every check, which is exactly the flow content-addressing requires, so no assumption in that file broke.

## Task Commits

Each task is a RED/GREEN pair:

1. **Task 1: `_atomic_write` for byos's three writers, with a parity test (INT-02)**
   - `5e6d91b` (test, RED) + `a68ae99` (feat, GREEN)
2. **Task 2: content-addressed image download (INT-05)**
   - `9da1aaf` (test, RED) + `14a3a38` (feat, GREEN)
3. **Task 3: request hardening (INT-06 remainder)**
   - `b4bcd5a` (test, RED) + `db1156d` (feat, GREEN)

_TDD tasks: each is a test -> feat pair (RED then GREEN); no refactor commit was needed for any task._

## Files Created/Modified
- `stub-server/byos_server.py` - `_read_umask`/`_DEFAULT_FILE_MODE`/`_atomic_write` (Task 1); `IMG_DIRNAME`/`IMG_KEEP`/`_IMG_NAME_RE`/`_IMG_PATH_RE`/`_publish_image`/`_prune_images`, rewritten `/device/v1/display` and `/img/` branches, updated module docstring (Task 2); `MAX_BODY_BYTES`/`REQUEST_TIMEOUT_S`/`_BAD_LENGTH`, rewritten `read_body_json`/`bearer_ok`/`log_message`, non-dict log entries skipped, `--request-timeout` flag (Task 3)
- `stub-server/test_byos_hardening.py` (new) - `Harness` (a seeded-token variant of `test_poll_cycle.py`'s/`test_devices_registry.py`'s own harness pattern), `load_byos_module`, `http_request`, `_raw_request` (hand-built HTTP/1.1 over a socket, for headers a high-level client would normalise or reject), and 26 behaviour tests across the three tasks
- `stub-server/.gitignore` - `*.tmp` replaces the single `byos_state.json.tmp` line; `img/` added ahead of the content-addressed cache directory

## Decisions Made
See `key-decisions` in the frontmatter: `_atomic_write`'s single-function shape (vs. `server/atomic_io.py`'s two-phase `staged_write`), `_prune_images`'s one-pass "top-IMG_KEEP-by-mtime, swap in keep_digest if it fell out" algorithm, `bearer_ok()`'s no-early-return iteration with UTF-8/surrogateescape encoding on both sides, `log_message()`'s `getattr` defensiveness, and the REQUIREMENTS.md Complete/Pending split for INT-02 vs. INT-05/INT-06.

## Deviations from Plan

None - plan executed exactly as written. The three tasks' `<action>` and `<interfaces>` sections were followed as specified; every acceptance-criteria grep (no `+ ".tmp"`, exactly one `tempfile.mkstemp`, no `server.*` import, no `startswith("/img/")`, `_IMG_PATH_RE` present, `IMG_KEEP = 8` exactly once, the single `ThreadingHTTPServer` line, no outbound-call pattern, `hmac.compare_digest` at least twice, no `in self.state["tokens"].values()`) passed on the first implementation attempt.

## Issues Encountered
- Two new tests initially sent a raw `/device/v1/log` request with no `Authorization` header while asserting on `read_body_json()`'s length-validation behaviour; `do_POST` checks `bearer_ok()` before reading the body on that endpoint, so both requests hit 401 instead of the length check. Fixed by adding a seeded-token `Authorization` header to those raw requests (test-only change, not a deviation from the plan's production-code instructions - `/device/v1/log`'s auth-before-body-read ordering was already correct and unchanged).

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- `stub-server/byos_server.py` is ready for **37-11** (`--bind 127.0.0.1`, `IPAddressDeny=any`): the server-construction expression and the no-outbound-connection invariant it depends on are both confirmed unchanged by this plan.
- `_atomic_write`'s duplication of `server/atomic_io.py`'s contract remains a live **Phase 39 (ARC-05)** input: once byos's "never import `server.*`" vendor boundary is retired, `_atomic_write`/`_read_umask`/`_DEFAULT_FILE_MODE` in `byos_server.py` can be deleted in favour of importing `server.atomic_io.atomic_write` directly - the parity test in `test_byos_hardening.py` is what will need to change (or drop) at that point, not a new equivalence proof.
- No blockers for the rest of wave 2 (36-04..36-06) or wave 3 (36-07).

## Self-Check: PASSED

- FOUND: stub-server/test_byos_hardening.py
- FOUND: stub-server/byos_server.py (modified)
- FOUND: stub-server/.gitignore (modified)
- FOUND commit 5e6d91b (test RED, Task 1)
- FOUND commit a68ae99 (feat GREEN, Task 1)
- FOUND commit 9da1aaf (test RED, Task 2)
- FOUND commit 14a3a38 (feat GREEN, Task 2)
- FOUND commit b4bcd5a (test RED, Task 3)
- FOUND commit db1156d (feat GREEN, Task 3)

## TDD Gate Compliance

All three TDD tasks show the required RED -> GREEN sequence in git log:
- Task 1: `5e6d91b test(36-03): ...` then `a68ae99 feat(36-03): ...`
- Task 2: `9da1aaf test(36-03): ...` then `14a3a38 feat(36-03): ...`
- Task 3: `b4bcd5a test(36-03): ...` then `db1156d feat(36-03): ...`

No REFACTOR commit was needed for any task.

---
*Phase: 36-state-integrity-and-device-protocol*
*Completed: 2026-09-26*
