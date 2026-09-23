---
phase: 34-firmware-resilience-power-security-cleanup
plan: 09
subsystem: firmware
tags: [esp-http-client, esp-tls, mbedtls, tcp-transport, rtc-memory, esp-idf]

# Dependency graph
requires:
  - phase: 34-firmware-resilience-power-security-cleanup
    provides: "plan 34-06's api_client.h public surface (fp_api_setup(void)/fp_api_get_display/fp_api_download/fp_api_release(void)) and http_client_new() as the single esp_http_client_init call site"
  - phase: 34-firmware-resilience-power-security-cleanup
    provides: "plan 34-07's wake_guard.h (fp_wake_checkpoint) and plan 34-08's app_main.c/state_machine.c wiring that arms the wake budget and calls fp_wake_checkpoint() around every api_client.c call before this plan's own download-loop checkpoint runs"
  - phase: 34-firmware-resilience-power-security-cleanup
    provides: "plan 34-04's Kconfig symbols (CONFIG_SKYPANE_TLS_SESSION_PERSIST, CONFIG_ESP_TLS_CLIENT_SESSION_TICKETS=y, CONFIG_ESP_HTTP_CLIENT_ENABLE_CUSTOM_TRANSPORT=y) already in sdkconfig.defaults"
provides:
  - "api_client.c restructured around a module-static per-wake esp_http_client handle (session_client()): setup, display and a same-origin download share one connection; clear_request_headers() deletes every telemetry/auth header before each request sets only what it needs; small_request()/fp_api_download() retry once on a fresh connection when the handle has already connected successfully this wake, never after a response status was read; the download read loop calls fp_wake_checkpoint() after every esp_http_client_read; fp_api_release() logs the `http connects=<n> first_connect_ms=<n> tls_offered=<0|1> tls_saved_len=<n>` diagnostic line and tears down the handle and the custom SSL transport"
  - "tls_session.c/.h - fp_tls_session_offer/save/forget/offered/saved_len: best-effort TLS session persistence across deep sleep via mbedtls_ssl_session_save/_load into RTC memory, active only when CONFIG_SKYPANE_TLS_SESSION_PERSIST && CONFIG_ESP_TLS_CLIENT_SESSION_TICKETS && ESP_IDF_VERSION == v5.3.1 - a no-op (full handshake every wake) outside that exact combination"
  - "firmware/main/CMakeLists.txt REQUIRES gains tcp_transport for esp_transport_ssl_* / esp_transport_get_context_data"
affects: ["34-10", "34-11"]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "esp_http_client custom-transport reuse: a module-static esp_http_client_handle_t + esp_transport_handle_t, created once per wake and retargeted per request via esp_http_client_set_url/set_method/set_timeout_ms, cleaned up in exactly one place (fp_api_release) instead of once per call site"
    - "Retry-once gated by a connect counter, not a boolean: s_connects (incremented only inside the HTTP_EVENT_ON_CONNECTED handler, i.e. only on a genuine new TCP+TLS connect, never on a reused-connection open) distinguishes 'this handle's very first connect just failed' (no retry - a real problem) from 'a handle that already worked once just failed' (retry once - the peer likely closed the keep-alive)"
    - "Private-struct mirror gated by an exact ESP_IDF_VERSION pin: tls_session.c's fp_transport_esp_tls_mirror_t copies tcp_transport's private transport_esp_tls_t field-for-field to reach a field neither esp_transport nor esp_tls exposes publicly, compiled in only for the one IDF patch version it was verified against; every public function degrades to a no-op outside that pin"

key-files:
  created:
    - firmware/main/tls_session.h
    - firmware/main/tls_session.c
  modified:
    - firmware/main/api_client.c
    - firmware/main/CMakeLists.txt

key-decisions:
  - "Task 1 and Task 2 were committed as genuinely separate, individually-buildable states: Task 1's commit has zero references to tls_session.h (fp_api_release logs literal 0/false for tls_offered/tls_saved_len, matching the plan's own 'until Task 2 lands use 0' wording) and was verified to compile and pass check_production_config.sh on its own before Task 2's wiring was reapplied - not just conceptually separable, actually built and tested standalone."
  - "Retry-once eligibility is keyed off s_connects (a real connect happened at least once this wake) rather than a separate 'had a response' flag - simpler, and events only fire on a genuine new TCP+TLS connect (confirmed by reading esp_http_client_connect()'s `if (client->state < HTTP_STATE_CONNECTED)` skip-on-reuse guard in the v5.3.1 container source), so the same counter that feeds the diagnostic line also gates the retry decision correctly."
  - "fp_tls_session_save() is called once per wake, right after the first successful esp_http_client_fetch_headers() on s_http, not after the full response body is read - matches the plan's 'after the first request that returned any HTTP status' wording and doesn't wait on a full-body read that a later validation failure might still error out of."
  - "The download's cross-origin one-shot path (http_client_new(), unchanged from plan 34-06) never participates in retry-once or TLS-session save/forget - those only apply to s_http, since a one-shot client by definition never has a 'previous successful connect' to compare against."

requirements-completed: [FW-10, FW-02, FW-14]

# Metrics
duration: ~65min
completed: 2026-09-23
---

# Phase 34 Plan 09: api_client keep-alive client, budgeted download, best-effort TLS session persistence Summary

**One `esp_http_client` handle now serves every request of a wake (setup + display + same-origin download share one TCP+TLS connection instead of three), the download loop is bounded by the wake budget via `fp_wake_checkpoint()`, and a new `tls_session.c` best-effort persists the TLS session across deep sleep in RTC memory, pinned to exactly ESP-IDF v5.3.1's private transport struct layout with a full-handshake fallback on any mismatch.**

## Performance

- **Duration:** ~65 min
- **Completed:** 2026-09-23
- **Tasks:** 2/2 completed
- **Files modified:** 3 (2 created, 1 modified twice across the two task commits; CMakeLists.txt modified once)

## Accomplishments

- **`api_client.c` restructured around `session_client()`** (Task 1): a module-static `s_http`/`s_tls`/`s_origin` replace a fresh `esp_http_client_init()` per call. The first request of a wake creates the handle (attaching a custom SSL transport for https, with `save_client_session = true` so esp_http_client's own in-process session-ticket carry works across the handle's own reconnects); every later request on the shared origin just calls `esp_http_client_set_url`/`set_method`/`set_timeout_ms`. `esp_http_client_close()` is no longer called after a successful response - that was the exact behavior forcing a fresh TCP+TLS connection per request before this plan.
- **Header hygiene (T-34-09-01)**: `clear_request_headers()` deletes `Authorization`, `Content-Type`, `X-Rssi`, `X-Battery-Mv`, `X-Fw-Version`, `X-Boot-Reason` before every request on the shared handle sets only what it needs - the image download clears all of them and sets none, so a bearer token can never reach the image host. A download whose URL resolves to a different `scheme://host[:port]` than `s_origin` (a presigned CDN URL, say) never touches the shared handle at all: it gets a fresh one-shot client via the unchanged `http_client_new()`, with no shared headers to leak in the first place.
- **Retry-once on a stale connection (T-34-09-06)**: `small_request()` and `fp_api_download()`'s open path retry exactly once, on a fresh connection, when `esp_http_client_open`/`write`/`fetch_headers` fails - but only when `s_connects > 0` (this wake has connected successfully at least once already) and never once a response status has been read. `s_connects` is incremented only inside an `HTTP_EVENT_ON_CONNECTED` handler, which - confirmed by reading `esp_http_client_connect()`'s source in the v5.3.1 container - fires only on a genuine new TCP+TLS connect, never on a reused, still-open connection. This is what keeps the LAN stub (HTTP/1.0, closes after every response) working under the new keep-alive default.
- **Budgeted download (FW-02)**: the read loop in `fp_api_download()` calls `fp_wake_checkpoint()` after every `esp_http_client_read()`, so a trickling transfer - one that never individually exceeds the per-read timeout but keeps the connection alive indefinitely - cannot outlive the whole-wake budget armed by plan 34-08's `app_main.c`.
- **Diagnostic line (FW-10)**: `fp_api_release()` logs `http connects=<n> first_connect_ms=<n> tls_offered=<0|1> tls_saved_len=<n>` (tag `fp_api`) whenever a handle was opened this wake, then tears it down - `esp_http_client_cleanup()` only destroys its own `transport_list`, confirmed by reading its source, never a custom transport handed in via `config.transport`, so `fp_api_release()` also calls `esp_transport_destroy(s_tls)` explicitly. Idempotent and safe to call when nothing was opened.
- **`tls_session.c/.h`** (Task 2, new): `fp_tls_session_offer()`/`_save()`/`_forget()`/`_offered()`/`_saved_len()`. The guarded implementation (`CONFIG_SKYPANE_TLS_SESSION_PERSIST && CONFIG_ESP_TLS_CLIENT_SESSION_TICKETS && ESP_IDF_VERSION == ESP_IDF_VERSION_VAL(5, 3, 1)`) mirrors `tcp_transport`'s private `transport_esp_tls_t` struct field-for-field (re-verified against the v5.3.1 container source at implementation time, not just at plan time) to reach its `session_ticket` field via `esp_transport_get_context_data()`, then uses only public `mbedtls_ssl_session_save`/`_load`/`_init`/`_free` and `esp_tls_free_client_session`/`esp_transport_ssl_session_ticket_operation` to flatten/restore it - no `memcpy` of the struct itself anywhere (`grep -n memcpy firmware/main/tls_session.c` returns nothing). RTC storage: `RTC_DATA_ATTR uint8_t s_blob[3072]` / `uint16_t s_len` / `char s_origin[FP_API_BASE_MAX]`. Every public function is a no-op (`return false`/`0`) outside the guarded config - a device on that path simply pays a full handshake every wake, unchanged from before this plan. Wired into `api_client.c`: `fp_tls_session_offer()` right after creating `s_tls` (https only, before the first connect), `fp_tls_session_save()` once per wake right after the first `esp_http_client_fetch_headers()` success on `s_http`, `fp_tls_session_forget()` when a connect offered a session but then failed (`s_connects == 0` at the point of failure).
- **`CMakeLists.txt`**: `tcp_transport` added to `REQUIRES` (both `api_client.c` and `tls_session.c` now include `esp_transport_ssl.h` directly).
- Verified against the real `espressif/idf:v5.3.1` container throughout: production build clean after Task 1 alone (tls_session.c/.h untracked, api_client.c had zero references to them) and again after Task 2's wiring was reapplied, byte-identical binary size to a single combined build (`0xf6bb0` bytes both times); dev build (`SKYPANE_PROFILE=dev`, `CONFIG_SKYPANE_ALLOW_HTTP=y`, exercising the `s_tls == NULL` plain-http path) clean; a scratch build with `CONFIG_SKYPANE_TLS_SESSION_PERSIST=n` also clean and smaller (`0xf5670` vs `0xf6bb0` bytes), confirming the guarded block compiles out; `check_production_config.sh static`/`built` both `PASS` after every build; `sh firmware/tests/run_host_tests.sh` 8/8 after every step (unaffected - neither touched file has a host-test counterpart); `idf.py size` on the production build reports RTC SLOW `.data` at 3212/8192 bytes (39.21% used, 4980 free) - essentially the `3072 + 2 + 128 = 3202`-byte reservation this plan adds, plus alignment padding.

## Task Commits

1. **Task 1: One shared client per wake with retry-once, header hygiene, budgeted download and connection diagnostics** - `e4dd181` (feat)
2. **Task 2: Best-effort TLS session resumption across deep sleep (tls_session.c)** - `23673b1` (feat)

**Plan metadata:** committed in this same response, immediately after this file.

## Files Created/Modified

- `firmware/main/api_client.c` - restructured around `session_client()`/`small_request()`/`fp_api_download()` for connection reuse, retry-once, header hygiene, download-loop checkpointing, and the diagnostic release line; wired to `tls_session.c` in the second commit
- `firmware/main/tls_session.h`/`.c` - new: best-effort TLS session persistence across deep sleep, pinned to ESP-IDF v5.3.1
- `firmware/main/CMakeLists.txt` - `tcp_transport` added to `REQUIRES`

## Decisions Made

See `key-decisions` in the frontmatter - repeated here for visibility:

- Task 1 and Task 2 were committed as genuinely separate, individually-buildable states (not just separable in principle): Task 1's own commit was built and verified standalone, with `fp_api_release()`'s diagnostic line hardcoding `tls_offered=0`/`tls_saved_len=0` exactly as the plan's own prose anticipates ("until Task 2 lands use 0"), before Task 2's wiring was reapplied via the reverse of the same edits.
- Retry-once eligibility uses the existing `s_connects` diagnostic counter (incremented only on a genuine new TCP+TLS connect, confirmed against `esp_http_client_connect()`'s source) rather than a second boolean - one signal serves both the diagnostic line and the retry decision.
- `fp_tls_session_save()` fires once per wake right after the first successful `fetch_headers()`, not after a full response body is read, matching the plan's "returned any HTTP status" wording and not gating persistence on a later JSON-validation outcome.
- The one-shot cross-origin download path (unchanged `http_client_new()`) never participates in retry-once or TLS-session logic - both are keyed to `s_http`/`s_connects`, and a one-shot handle has no "previous connect this wake" to compare against by construction.

## Deviations from Plan

None - plan executed exactly as written. Every acceptance-criteria grep and count matches what the plan specified; `git diff firmware/main/api_client.h` is empty (public API unchanged from plan 34-06, as required); the production and dev container builds, the production-config checks, and the host test suite all passed after each task.

## Issues Encountered

None. Docker (`espressif/idf:v5.3.1`) was available throughout, so every build-gated verification ran for real, including two checks beyond the plan's own minimum:
- Read `esp_http_client.c`, `transport_ssl.c`, `esp_tls.c`/`esp_tls_mbedtls.c`, `esp_tls.h` and `mbedtls/ssl.h` directly from the v5.3.1 container before writing any code, to confirm (rather than assume) the private `transport_esp_tls_t` field order, that `esp_http_client_cleanup()` does not free a custom transport, that `esp_http_client_connect()` skips a real connect (and thus the `HTTP_EVENT_ON_CONNECTED` event) when the handle is already in `HTTP_STATE_CONNECTED` or later, and the exact semantics of `esp_tls_get_client_session()`/`esp_tls_free_client_session()`/`mbedtls_ssl_session_save`/`_load`.
- Beyond the plan's "build with the switch both on and off" instruction, also confirmed the RTC SLOW segment size via `idf.py size` (3212/8192 bytes) and that a from-scratch Task-1-only build (without `tls_session.c`/`.h` present at all in the working tree at build time... in practice the files existed on disk but untracked; `api_client.c`'s Task-1 state has zero symbol references to any `fp_tls_session_*` function, so the build would succeed identically even with those files physically absent) compiles and links cleanly, to make the two-commit split a real, verified boundary rather than a cosmetic one.

## User Setup Required

None - no external service configuration required. `firmware/main/secrets.h` (gitignored) is present and unchanged from before this plan.

## Next Phase Readiness

- **What plan 34-10 needs:** `firmware/VENDOR.md`'s "Original To This Repository" table needs one new line for `tls_session.c/.h`, and the vendored-file table's `api_client.c` row needs its "no (modified)" description updated to mention connection reuse - this plan does not touch `VENDOR.md` itself (out of this plan's `files_modified` scope; 34-10 owns it per the environment notes). The Log Line Contract is untouched (verified: no line in `app_main.c`'s five contract lines was touched by this plan; the new `http connects=...` and `TLS session saved (...)` lines are diagnostic, tagged `fp_api`/`fp_tls`, not part of the contract).
- **What the 34-11 hardware session needs to observe (no hardware attached to this session, so none of the following is proven on real silicon yet):**
  1. Whether Caddy on the VPS actually resumes the offered TLS session (an abbreviated handshake, no full certificate exchange) - this plan makes resumption safe and measurable, not verified to work end-to-end against the real server.
  2. The real `mbedtls_ssl_session_save()`-reported size for a session Caddy issues, to confirm the 3072-byte `FP_TLS_SESSION_MAX` reservation is enough (TLS 1.2 session tickets are typically hundreds of bytes to ~1-2 KB; TLS 1.3 tickets can run larger) - `tls_session.c` logs `TLS session saved (%u bytes)` on every successful save for exactly this purpose, and warns and drops the session (falls back to a full handshake) if the real size exceeds the reservation, so an undersized reservation degrades safely rather than corrupting anything.
  3. Per 34-11's own H-04 step: `fp_api` line's `http connects=1` per wake confirms the reuse actually holds against Caddy (not just the LAN stub); `tls_offered=0` on the first wake after a fresh boot/reset and `tls_offered=1` on later wakes, with `first_connect_ms` compared between the two, is the concrete measurement that closes out FW-10's "~28 s per-cycle overhead" investigation from 34-RESEARCH.md.
  4. Whether a genuine mid-wake stale-connection scenario (the server actually closing a keep-alive connection between two requests of the same wake) exercises the retry-once path correctly on real hardware/network timing, not just the LAN stub's HTTP/1.0-always-closes behavior this plan's container build could reason about but not observe live.
- No open blockers. `firmware/main/api_client.c`, `tls_session.c`/`.h`, and the touched line of `CMakeLists.txt` are single-owner for this plan.

---
*Phase: 34-firmware-resilience-power-security-cleanup*
*Completed: 2026-09-23*

## Self-Check: PASSED

- FOUND: `firmware/main/api_client.c` (modified)
- FOUND: `firmware/main/tls_session.h`
- FOUND: `firmware/main/tls_session.c`
- FOUND: `firmware/main/CMakeLists.txt` (modified)
- FOUND commit `e4dd181` (Task 1)
- FOUND commit `23673b1` (Task 2)
