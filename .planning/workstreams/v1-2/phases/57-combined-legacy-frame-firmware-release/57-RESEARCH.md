# Phase 57: Combined Legacy-Frame Firmware Release - Research

**Researched:** 2026-11-14
**Domain:** ESP-IDF 5.3.1 firmware wake flow (C), BYOS device protocol (Python stdlib), OTA rollback, release pipeline
**Confidence:** HIGH on code facts (all read in this session); MEDIUM on bootloader rollback with an unconfirmed trial (documented, one half observed on the real frame, one half not); LOW on S3 CRC timing (estimate, not measured)

## Summary

The image reader, the OTA machinery and the 401 token erase already exist. What is missing is wiring and three small behaviour changes. (1) `imgc_parse` is called by nothing: the download buffer, the length gate and the SHA-256 gate in `api_client.c` assume exactly 960000 bytes, so a container body (960024 bytes) is rejected today as `download`. (2) No request header announces the container or the hardware type. (3) After a repeated 401 the frame does keep its token-erase and growing backoff, but on the second consecutive `auth`/`enrol` failure it draws the on-device NO CONNECTION screen, which replaces the last image. That contradicts D-04 and is the only real 401 gap.

All server work is additive in `stub-server/byos_server.py`: read one new header, compare with the type resolved from `fleet.db`, and on a contradiction withhold the firmware offer and serve the legacy raw image. A header-less frame (the current firmware) takes the exact same code path as today.

Nothing here could be built in this environment: the Docker daemon is not running and there is no ESP-IDF toolchain, so no C that touches ESP-IDF headers can be compiled here. The pure C host suites do run and are green (15 suites, `check_panel_diff` PASS). `pytest` is not installed here, so the Python suites were not run. The compile of the new `state_machine.c`/`api_client.c` code is first proven by `firmware.yml` in CI.

**Primary recommendation:** Wire `imgc_parse` in `state_machine.c` right after `fp_api_release()`/`fp_wifi_stop()` and before `fp_panel_draw()`, passing `view.payload` (no copy, `panel.c` and `epd13in3e.c` untouched); send `X-Img-Fmt: 1` and `X-Hw-Type: <key>` on the display request only; make `fp_fault_screen_should_draw` never draw for `auth`/`enrol`; resolve the type once in `_handle_display` and gate offers plus the container on it; prove rollback with the existing dev-only `SKYPANE_FAULT=nvs` / `slow_wake` images on the EE04 bench unit only.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** The owner-set lock of 2026-10-31 stays. Publication waits for the `firmware/SIGNING.md` bench procedure on a non-live unit. The owner has no spare board, so the unit is the Seeed EE04 of Phase 58 (not yet arrived). Phase 57 prepares everything; publication is a later owner gesture.
- **D-02:** No cable flash is needed. The live frame already verifies signatures (cable-flashed once with signed fw-v1.0.0 on 2026-09-29; signed OTA to fw-v1.0.1; wrong-key, tampered and unsigned images refused and crash rollback seen on the real frame, see `hardware/BRINGUP-LOG.md`). The release must be signed with the same key as fw-v1.0.x. Not yet seen on a device: an image that boots but cannot reach the server (this phase's risk) rolling back.
- **D-03:** Base is `main` / fw-v1.0.4 (in service, installed by OTA per the owner; install date not yet given; read it with `firmware_cli list`).
- **D-04:** After repeated 401 the frame shows nothing new: it keeps its last image and retries with growing spacing. No new on-device screen. The existing token-erase and re-enrol on the next wake stays.
- **D-05:** The frame sends a new hardware-type request header (none exists today). Name and format are for the planner, additive to the protocol.
- **D-06:** On a contradiction between the header and the type stored in the fleet database, the server refuses only firmware offers and the new container. The legacy raw image is still served, so the frame stays reachable. A frame that sends no header (current firmware) is served exactly as today.
- **D-07:** Everything ships in one combined version. The 47.1 reference measurement is taken on the combined version. If the 14-day window already started on fw-v1.0.4, installing the combined version restarts it. Phase 47.2 will need its own later firmware release.

### Claude's Discretion
Header name, backoff schedule, host-test design, release instructions layout.

### Deferred Ideas (OUT OF SCOPE)
- On-device "frame not recognised" screen (declined).
- Phase 47.2 wake-energy reduction: separate later release.

Phase scope limits (CONTEXT.md and task): this phase prepares, builds (CI) and documents the release. No `publish_release`, no production registry import, no companion schedule, no `fw-v*` tag pushed, no merge to main, no flashing. Do not touch Phase 47/47.1 files or `hardware/`. Wake interval and existing protocol unchanged; `stub-server/test_phase47_freeze.py` must stay green.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| OTA-04 | All firmware changes needed on the current frame (image-header reader, any hardware header, recovery after repeated 401) ship in one release, only once Phase 47 allows it and the OTA signing bench procedure of `firmware/SIGNING.md` has passed on a non-live unit. | Sections "Image reader wiring", "Hardware header", "401 recovery", "Rollback and fail-safe", "Release deliverables". Publication gate = owner action after the EE04 bench run (D-01); this phase stops at a CI-built, documented, unpublished release. |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- Code, identifiers, comments, docstrings, docs and commit messages in English. Companion UI strings stay bilingual (not touched here).
- Comments say what the code does when not obvious, and why. No plan, ticket, decision, review or phase IDs in comments; `scripts/check_comment_history.py check` enforces this in CI. (So no "D-06", "Phase 57" or "OTA-04" in C or Python comments.)
- Server code is Python 3.14 stdlib + Pillow + requests only. Function-size gate: max 80 lines over `server`/`stub-server` (`scripts/check_function_size.py`); `_handle_display` and `_record_device_report_and_offer` are already large, so new logic goes in small helpers.
- Tests: pytest + xdist, pytest-socket non-loopback guard, behaviour-over-source rule (tests assert served bytes/headers or a browser, never source text or `.planning/`), ruff, mypy (module list in `pyproject.toml`), coverage gate at the measured floor. Firmware host tests are the separate `./firmware/tests/run_host_tests.sh`.
- Firmware: ESP-IDF 5.3.1 in `espressif/idf:v5.3.1`, Apache-2.0, vendored-file changes listed in `firmware/VENDOR.md` (must be updated for every changed vendored file).
- GSD workflow: file changes go through a GSD command (execution belongs to `/gsd-execute-phase`, not this research).

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Container validation before display | Device firmware (`state_machine.c`, pure `image_container.c`) | - | Must run before the buffer reaches `fp_panel_draw`; IMG-03. |
| Announcing `X-Img-Fmt` / hardware type | Device firmware (`api_client.c`) | Server (reads, never trusts for grants) | The device states what it can read; the server decides. |
| Deciding container vs legacy, withholding offers on contradiction | API / Backend (`byos_server.py`) | Database (`fleet.db` type) | Type is server-assigned (OTA-01); a claim can only restrict, never grant. |
| 401 recovery (erase, re-enrol, backoff, keep image) | Device firmware (`api_client.c`, `sleep_decision.c`, `fault_screen.c`) | Server (answers 401/200 on setup) | Entirely a device wake-loop policy. |
| Rollback of an unreachable trial image | Bootloader (ESP-IDF) | `ota.c` classification, server reconcile | App rollback is bootloader behaviour; firmware only decides when to confirm. |
| Signed release image | CI (`firmware-release.yml`, reviewer-gated) | Owner (tag, schedule) | Signing key lives only in the `firmware-signing` environment. |

## Standard Stack

No new libraries. Everything uses what is vendored or already in the repo.

### Core
| Component | Version | Purpose | Why Standard |
|-----------|---------|---------|--------------|
| ESP-IDF | 5.3.1 (`espressif/idf:v5.3.1`) | Build and runtime | Pinned in `firmware/build.sh`; `[VERIFIED: firmware/build.sh]` |
| `firmware/main/image_container.[ch]` | in repo | Container + legacy reader, pure C | Host-tested against golden fixtures shared with `server/image_container.py` `[VERIFIED: codebase]` |
| `server/image_container.py` | in repo | Encoder, `negotiate_version` | Already used by byos `_served_image` `[VERIFIED: codebase]` |
| `server/hardware.py` | in repo | `LEGACY_KEY = "xiao-ee02-13in3-spectra6"`, `is_known`, `available_types` | Type vocabulary for the new header value `[VERIFIED: codebase]` |

### Supporting
| Component | Purpose | When to Use |
|-----------|---------|-------------|
| `firmware/tests/run_host_tests.sh` | Hardware-free C suites, discovers `tests/test_<name>.c` against `main/<name>.c` | Every new pure function |
| `firmware/tests/check_log_contract.sh`, `check_production_config.sh` | CI guards that run in `firmware.yml` | After any new `fail_step_out` token or Kconfig symbol |
| `stub-server/test_*.py` with `FrameServer` subprocess fixture | Real-process byos tests | Server header tests |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Pure-C 256-entry CRC table | `esp_rom_crc32_le` (ROM) | ROM needs no flash but its inversion convention is not stated in `esp_rom_crc.h` (header says callers wrap with `~`); cannot be checked on the host. Table version is bit-testable on the host. Use the table. `[CITED: raw.githubusercontent.com/espressif/esp-idf/v5.3.1/components/esp_rom/include/esp_rom_crc.h]` |
| New step token `image` | reuse `verify` | `verify` is already documented, allow-listed and needs no `VENDOR.md` row; with the sticky legacy fallback below a second consecutive parse failure cannot happen. Reuse `verify`. |

**Installation:** none (no packages). **Package Legitimacy Audit:** not applicable, this phase installs no external packages (slopcheck not run).

## Architecture Patterns

### System Architecture Diagram

```
wake (timer)
  |
  v
app_main: LED, wake guard, NVS, fp_ota_boot_check, reset-reason, battery
  |
  v
fp_poll_once (state_machine.c)
  wifi --> [no token?] --> fp_api_setup (POST /device/v1/setup)
  |                          401/403 -> "enrol" fail
  v
fp_api_get_display  GET /device/v1/display
  headers: Authorization, X-Rssi, X-Battery-Mv, X-Fw-Version, X-Boot-Reason,
           [X-Ota-Result], X-Wake-Stats,
           NEW X-Img-Fmt: 1  (omitted when NVS imgfmt_bad set)
           NEW X-Hw-Type: <compiled-in key>
  |  401 -> erase token -> "auth" fail -> backoff (no fault screen)
  v
server _handle_display
  resolve type ONCE (fleet.db) -> contradiction? (header well-formed AND != type)
     yes: offer=None, announced=None (raw 960000)      no/absent: as today
  -> {image_url, image_hash, sleep_s, firmware, ...}
  |
  v
OTA offer branch (unchanged) --> hash-skip (unchanged) --> alloc 960000+256 (PSRAM)
  |
  v
fp_api_download: read <= cap, SHA-256 over ALL received bytes (header included)
  |
  v
fp_api_release + fp_wifi_stop  (radio off before CPU work)
  |
  v
imgc_parse(buf, got, 1200, 1600, &view)   <-- CRC32 over 960000 B here
  |-- error: free buf, NVS hash untouched (last image stays), set imgfmt_bad,
  |          fail step "verify" -> backoff -> sleep      (trial image: no confirm => rollback)
  v
fp_panel_draw(view.payload)  -> NVS hash write only after a successful blit
  v
app_main: fp_sleep_decide -> fp_ota_confirm_if_pending -> deep sleep
```

### Recommended Project Structure (files touched)
```
firmware/main/
├── image_container.c   # replace bit-by-bit CRC with a 256-entry table (pure, host-tested)
├── api_client.c/.h     # buffer cap, length gate, return body length, two new headers, delete them in clear_request_headers
├── validate.c/.h       # fp_body_len_plausible, fp_hw_type_valid (pure)
├── state_machine.c     # parse before draw, step "verify", imgfmt_bad flag, fp_diag line
├── fault_screen.c      # drop "auth" and "enrol" from the allow-list
├── nvs_schema.h        # imgfmt_bad (string key)
├── Kconfig.projbuild   # SKYPANE_HW_TYPE string
firmware/sdkconfig.ee02.defaults  # CONFIG_SKYPANE_HW_TYPE="xiao-ee02-13in3-spectra6"
firmware/VENDOR.md, docs/IMAGE-FORMAT.md   # adoption notes become "as built"
stub-server/byos_server.py        # claim parse + contradiction helper, small edits in 3 call sites
stub-server/test_hw_claim.py      # new server tests
```
Do NOT edit `panel.c`, `epd13in3e.c` (the `check_panel_diff.sh` guard allows only timer reads), `wake_telemetry.*`, `wake_record.*`, `stub-server/measured_fields_freeze.json`, `stub-server/test_phase47_freeze.py`, `hardware/`.

### Pattern 1: Parse before draw, no copy
**What:** After the download passes the SHA-256 gate, call `imgc_parse` on the whole body and hand `view.payload` to `fp_panel_draw`. `imgc_parse` never touches a display buffer and returns a pointer into the caller's body (`[VERIFIED: firmware/main/image_container.h]`).
**Why no copy and no alignment risk:** `epd_blit` already sends `buf + row*600 + offset` with offset 0 or 300 per row (`send_half`), so the SPI driver already handles unaligned PSRAM source addresses; a payload at body+24 adds no new case `[VERIFIED: firmware/main/epd13in3e.c send_half]`. Panel files stay untouched, `check_panel_diff.sh` stays PASS.
```c
/* state_machine.c, after fp_api_release(); fp_wifi_stop(); fp_wake_checkpoint(); */
imgc_view_t view;
int64_t t_crc = esp_timer_get_time();
imgc_status_t st = imgc_parse(buf, body_len, FP_PANEL_W, FP_PANEL_H, &view);
ESP_LOGI("fp_diag", "image fmt=%s st=%d crc_ms=%" PRIu32,
         st == IMGC_OK ? "container" : "legacy", (int)st, elapsed_ms_since(t_crc));
if (st != IMGC_OK && st != IMGC_LEGACY_OK) {
    heap_caps_free(buf);
    fp_nvs_set_str(FP_NVS_IMGFMT_BAD, "1");   /* name: planner's choice */
    *fail_step_out = "verify";
    return FP_POLL_FAILED;
}
err = fp_panel_draw(view.payload);
```
Keep `ESP_LOGI(TAG, "blit ok bytes=960000 sha256_ok=1")` byte-for-byte (`check_log_contract.sh` greps it; `payload_len` is 960000 anyway).

### Pattern 2: Claim can only restrict
**What:** The server never grants anything from a device header. `X-Hw-Type` is parsed with `\A[a-z0-9-]{1,64}\Z`; anything else is treated as absent. A contradiction exists only when a well-formed claim is present AND a type is resolved AND they differ. On a contradiction: `offer = None` and `announced = None` (raw image). Unresolved type plus a claim is not a contradiction (offers are already withheld for unresolved types).
```python
# stub-server/byos_server.py (shape only)
_HW_TYPE_CLAIM_RE = re.compile(r"\A[a-z0-9-]{1,64}\Z")

def claim_contradicts(raw_claim, resolved_type):
    """True when a well-formed X-Hw-Type differs from the server-assigned type.
    A claim only ever withdraws privileges; it never selects a type."""
    if not isinstance(raw_claim, str) or not _HW_TYPE_CLAIM_RE.match(raw_claim):
        return False
    return resolved_type is not None and raw_claim != resolved_type
```
Single-resolution invariant: `test_hardware_type_is_resolved_once_outside_the_locks` (stub-server/test_ota_offer.py) asserts exactly one `resolve_hardware_type` call, outside the locks. So resolve once in `_handle_display` (before serving the image) and pass the result into `_record_device_report_and_offer` through a new optional keyword whose default keeps the current in-function resolve (other tests call that function directly). Pending/retired frames (`_pending_response`) have `row["hardware_type"]` at hand: use `claim_contradicts(headers.get("X-Hw-Type"), row["hardware_type"])` there; the pending display carries `"firmware": None` already, so only the container choice changes.

### Anti-Patterns to Avoid
- **Reading the new header into any store or log line shaped like the frozen headers.** `test_telemetry_headers_reach_exactly_the_frozen_places` freezes what is stored/logged; `X-Unlisted-Probe` must have no effect. Read the claim, compare, at most print one deduplicated "claim mismatch" line (mac + sanitized claim, like `_log_unresolved_type_once`); store nothing.
- **Using header name `X-Hardware-Type` or `X-Hw-Rev`.** `test_hardware_claimed_by_the_device_has_no_effect` (stub-server/test_ota_offer.py:1033) sends exactly those and asserts a claim changes nothing. Use `X-Hw-Type` so that test stays valid unmodified.
- **A second `resolve_hardware_type` call in the display path** (breaks the once-only test).
- **Putting the new headers on the setup or download requests.** `clear_request_headers` must delete both, and the same-origin download goes through the shared handle (a header left on it would reach the image request).
- **Touching `FP_NVS_IMAGE_HASH` on a failed parse.** Last image stays and the next wake re-fetches.
- **Growing X-Wake-Stats/`wake_record` for the CRC time.** That grammar is the Phase 47.1 contract; log `crc_ms` in a separate `fp_diag` line only.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Container validation | A second parser in `state_machine.c` | `imgc_parse` | Golden-fixture tested, 64-bit length arithmetic, validation order fixed by `docs/IMAGE-FORMAT.md` |
| Hash of a body with header | Hash payload only | existing `mbedtls_sha256` over all `got` bytes | Server hashes the exact bytes served, header included (`docs/IMAGE-FORMAT.md` "Hash and URL") |
| Exponential backoff | New 401-specific schedule | `fp_backoff_seconds` via `fp_sleep_decide` (5 min doubling, 6 h cap) | Already grows per consecutive failure and persists in NVS; sufficient for D-04 |
| Rollback | Custom "revert" code | `CONFIG_BOOTLOADER_APP_ROLLBACK_ENABLE=y` + `fp_ota_confirm_if_pending` after a good poll | Already in `sdkconfig.defaults:22`, proven by H42-10 crash rollback |
| Signing | Local signing for the release | `firmware-release.yml` in the `firmware-signing` environment | Key never leaves the gated environment (`firmware/SIGNING.md`) |

**Key insight:** every piece of risk in this phase is in glue code that touches the wake path. Keep each new decision a small pure function with a host test; keep the ESP-IDF glue to one-line calls.

## Findings by Research Question

### 1. Image reader wiring, cost, failure behaviour

**Current download gate (the blocker).** `fp_api_download` (api_client.c:680-802) reads at most `FP_IMAGE_BYTES`, sets `oversize` if one more byte exists, requires `got == FP_IMAGE_BYTES`, then SHA-256s `FP_IMAGE_BYTES` bytes. `fp_poll_once` allocates `FP_IMAGE_BYTES` (state_machine.c:285). A 960024-byte container therefore fails as `download` today. `[VERIFIED: codebase]`

**Required changes (smallest set):**
- `api_client.h`: add `FP_PANEL_W 1200`, `FP_PANEL_H 1600`, `FP_IMAGE_MAX_HEADER 256` and `FP_IMAGE_BUF_BYTES (FP_IMAGE_BYTES + FP_IMAGE_MAX_HEADER)`, with `_Static_assert(FP_PANEL_W * FP_PANEL_H / 2 == FP_IMAGE_BYTES)`. `header_len` is a `u8` in the format, so 255 is the hard maximum; a cap of 256 covers any v1 extension. Allocation `heap_caps_malloc(FP_IMAGE_BUF_BYTES, MALLOC_CAP_SPIRAM|MALLOC_CAP_8BIT)`: +256 bytes of PSRAM, no internal RAM change.
- `fp_api_download(url, hash, buf, cap, &body_len)`: read up to `cap`; `oversize` = a byte exists beyond `cap`; plausibility via a new pure `fp_body_len_plausible(got, legacy_len, max_header)` (true when `got == legacy_len` or `legacy_len+24 <= got <= legacy_len+max_header`); SHA-256 over `got`; call the existing `fp_download_verdict(status, got, got, oversize, hex, expected)` after the plausibility check so `fp_download_verdict` and its tests stay unchanged. `imgc_parse` then does the exact length check.
- `docs/IMAGE-FORMAT.md` "Adoption notes" already lists exactly these three items (buffer, hash over everything, announce only when the reader exists). `[VERIFIED: docs/IMAGE-FORMAT.md]`

**Where to call it.** In `fp_poll_once` after the download returns OK, after `fp_api_release(); fp_wifi_stop(); fp_wake_checkpoint();` (state_machine.c:310-312) and before `fp_panel_draw` (:315). Radio is off before the CPU-bound CRC (saves radio time); the failure exit `fail_and_sleep` is safe there (`maybe_draw_fault_screen` re-calls `fp_api_release`/`fp_wifi_stop`, both idempotent). Free `buf` on every exit path (the existing code frees it before each early return).

**Failure behaviour.** Return `FP_POLL_FAILED` with `*fail_step_out = "verify"`; `app_main` then calls `fail_and_sleep("verify")`: `fp_sleep_decide(FAILED, n, ...)` gives `fp_backoff_seconds(n)` and persists `n+1`. `FP_NVS_IMAGE_HASH` is never written, so the last image stays on the glass and the next wake re-fetches. `verify` is in `kAllowed` of `fp_fault_screen_should_draw`, so from the second consecutive failure the generic NO CONNECTION screen would replace the picture. To make that unreachable and to guarantee the frame stays reachable if the server ever serves a bad container after the trial wake, set a sticky NVS `imgfmt_bad` flag on the first parse failure; `telemetry` code omits `X-Img-Fmt` while it is set, so the next wake receives the raw 960000 bytes, which `imgc_parse` accepts as `IMGC_LEGACY_OK`. This flag is recommended (small: one NVS key via the existing string helpers, one pure `announce` predicate). It is not cleared automatically; clearing needs an NVS erase or a later release. `[ASSUMED: owner has no objection to a sticky opt-out; low risk because SHA-256 passes first, so a parse failure means a server bug, not transport corruption]`

**CRC cost.** `imgc_crc32` is bit-by-bit (8 shifts per byte). Host measurement in this session (x86, -O1, 960000 bytes): bitwise 10.1 ms, 256-entry table 2.5 ms, identical result to `zlib.crc32` (about 4x). On the in-order ESP32-S3 the ratio is expected to be at least as large. Absolute S3 numbers are NOT measured: an estimate is about 40 cycles/byte bitwise (roughly 0.2 to 0.4 s) versus about 6 to 10 cycles/byte table (roughly 40 to 80 ms), plus PSRAM read time, at the unverified CPU clock `[ASSUMED]` (no `CONFIG_ESP_DEFAULT_CPU_FREQ_MHZ` line in the committed defaults, so the IDF default applies; not read from a build here). Against a redraw wake of tens of seconds (the blit alone is budgeted 70 s, `FP_WAKE_STAGE_BLIT_S`) this is under 1 percent, but Phase 47.1 measures wake energy, so cheap is better: use the table (1 KB `.rodata`, no RAM, no ROM dependency) and log `crc_ms` once on the bench unit. Flash: the image is 0x150000 of 0x250000 per the Phase 62 CI build, 43 percent free; a few hundred bytes is irrelevant. `[CITED: 62-VERIFICATION.md]`

**SHA-256 stays the authenticity gate.** The container CRC only detects corruption (`docs/IMAGE-FORMAT.md`). `mbedtls_sha256` already runs over the same buffer today, so the wake gains one extra pass, not a new class of work.

### 2. Headers: name, format, where each side reads

- **Per-request setting:** `fp_api_get_display` does `clear_request_headers(http); auth_header(http); telemetry_headers(...); wake_stats_header(http);` (api_client.c:603-606). Add one `capability_headers(http)` call after `wake_stats_header` and delete both names in `clear_request_headers` (api_client.c:76-86). Display request only.
- **Name and format (recommended):** `X-Img-Fmt: 1` (already specified, `docs/IMAGE-FORMAT.md`; `negotiate_version` accepts 1-3 digits) and `X-Hw-Type: xiao-ee02-13in3-spectra6` (the exact `hardware.LEGACY_KEY`, grammar `[a-z0-9-]{1,64}`, same grammar used for registry file names). The value comes from a new Kconfig string `SKYPANE_HW_TYPE` defaulted in `sdkconfig.ee02.defaults`, so a future EE04 build sets its own key without code change. Add a pure `fp_hw_type_valid(const char*)` in `validate.c` and call it before setting the header (a bad Kconfig value sends no header rather than a bad one). Add a shell check in `firmware/tests/` that the Kconfig default equals `server.hardware.LEGACY_KEY` (python3 is available in the `firmware.yml` runner) so the two cannot drift. `[VERIFIED: codebase]` for LEGACY_KEY, `[ASSUMED]` for the header name (planner's call per D-05).
- **Server read points:** `byos_server.py` `_served_image(headers.get("X-Img-Fmt"), ...)` at line 1685 (live and fleet frames, `_handle_display`) and line 1459 (`_pending_response`). The offer is computed in `_record_device_report_and_offer` (line 1237) which already calls `resolve_hardware_type` once at 1263.
- **Implementation of D-06:** see Pattern 2. In `_handle_display`: resolve once (`resolve_hardware_type(self.args.state_dir, ctx.mac)`), compute `contradiction`, set `announced = None if contradiction else headers.get("X-Img-Fmt")`, pass `hardware_type=` and `withhold_offer=contradiction` into `_record_device_report_and_offer`; inside it keep recording `fw_version`/`ota_result` (a mismatching frame is still reported honestly) and only skip `_offer_for_type` (no "offered" event is written for a withheld offer). Keep each helper under the 80-line gate.
- **No-header frame:** `claim_contradicts(None, ...)` is False, `announced` is the raw `X-Img-Fmt` header (also absent for the current firmware), so the response path is byte-for-byte what `test_phase47_freeze.py` and `test_image_negotiation.py` already pin.
- **Hash side effect (accepted, documented):** a frame that starts announcing sees a different `image_hash` once (hash of container bytes), so it does one extra full redraw. With a contradiction the frame is served raw, whose hash equals its stored one, so it just hash-skips. `[CITED: docs/IMAGE-FORMAT.md]`

### 3. 401 recovery: what exists, what is missing

**Exists (verified in code):**
- `fp_api_get_display`: a 401/403 on `/device/v1/display` erases `FP_NVS_DEVICE_TOKEN` (api_client.c:611-616), returns `FP_ERR_HTTP_AUTH`, step token `auth`.
- Next wake: `fp_api_has_token()` is false, so `fp_api_setup()` runs before the display call (state_machine.c:132-148); a 401/403 on setup returns `FP_ERR_ENROL_REJECTED`, step `enrol`.
- Both are failures, so `fp_sleep_decide(FAILED, n)` returns `fp_backoff_seconds(n)` = 300 s x 2^n capped at 21600 s (6 h) and persists `n+1`; `n` resets to 0 only on a healthy wake. So spacing already grows 5, 10, 20, 40, 80, 160 min, then 6 h. `[VERIFIED: backoff.c, sleep_decision.c]`
- No hardware evidence of the 401 erase/re-enrol path exists in `hardware/BRINGUP-LOG.md` (grep found none). `[VERIFIED: grep]`

**Missing:**
1. **The NO CONNECTION screen on `auth`/`enrol`.** `fp_fault_screen_should_draw` allow-lists `auth` and `enrol` (fault_screen.c:42-45) and fires at `next_backoff_n >= 2`, i.e. on the 2nd consecutive failure. It writes the sentinel hash and puts a different picture on the glass. D-04 says the frame keeps its last image and shows nothing. Fix: remove `"auth"` and `"enrol"` from `kAllowed` (and from the doc comments in `fault_screen.h`/VENDOR.md); an unlisted token already defaults to not drawing.
2. **Host-testable policy.** The behaviour lives in ESP-IDF files and is not testable on the host today. Everything that is a decision is already pure: backoff, sleep plan, screen gate, status classification (`fp_http_status_classify`). Test those as a sequence (below). The erase-then-enrol I/O itself can only be seen on a bench unit.
3. Nothing else is missing: no new on-device UI, no new NVS counter, no schedule change. Note one accepted cost: while a frame is in a long 401 loop it makes two requests per wake (enrol + display) once it has re-enrolled; the 6 h cap bounds that to 4 wakes/day.

**Host tests (new, no new module needed):**
- `test_fault_screen.c`: `fp_fault_screen_should_draw("auth", n, false)` and `("enrol", n, false)` are false for n = 0, 2, 5, 255; other allow-listed tokens unchanged (`wifi`, `http`, `status`, `json`, `download`, `verify`, `secret`, `config`).
- `test_sleep_decision.c` (HOST_TEST_DEPS already `backoff.c`): simulate 12 consecutive `FAILED` outcomes starting at n=0: sleep is non-decreasing, first is 300, reaches 21600 and stays, `next_backoff_n` increments; then one `OK` with server `sleep_s=300` gives `sleep_s==300` and `next_backoff_n==0` (recovery resets spacing).
- `test_validate.c`: `fp_http_status_classify(401)` and `(403)` are AUTH, 500 is not (verify existing cases cover it; add if not).

### 4. What Phase 62 and 47.1 left in `firmware/`

- **Phase 62:** regenerated `fault_screen_mask.h` and `updating_screen_mask.h` (123 x 1275 bytes of mask each, plus `tools/gen_fault_screen.py`). `git diff fw-v1.0.4 HEAD -- firmware` is empty, so main's firmware equals the `fw-v1.0.4` tag (tag `d99578ca`, 2026-11-10); the combined release carries them automatically and adds nothing from 62. The Phase 62 CI build was 0x150000 bytes in a 0x250000 slot. `[VERIFIED: git]` `fault_screen.h` still says "about 32 KB" for the mask; the real figure is about 157 KB per mask, a stale comment to fix while touching the file.
- **47.1:** `wake_telemetry.[ch]`, `wake_record.[ch]`, the `X-Wake-Stats` header (display request only), per-stage timings, `epd_spi_ms`, `check_panel_diff.sh`. All already in main. The combined release must carry them unchanged and must not break their contracts: the header grammar (server `wake_stats.py` max 192 bytes, CI compares), the previous-wake record written at the single sleep exit, the panel-diff guard. New code must not add fields to either, and must not add any panel-file change.
- **What changes wake duration in the combined release:** (a) one CRC pass over 960000 bytes (about 0.05 to 0.4 s, estimate); (b) 24 more body bytes and two extra request headers (negligible); (c) on the OTA wake itself about 62 s `[CITED: BRINGUP-LOG.md]`; (d) the first wake after install redraws once because the hash changes (one full refresh, about 31.5 s measured per `panel_guard.h`), and installing restarts the 47.1 baseline window (D-07). Healthy hash-skip wakes are unchanged. No change to cadence, `sleep_s`, request count or TLS.
- **Unverified:** which version the live frame runs today (D-03 says fw-v1.0.4 installed by OTA, date not given). Read `device_report.json` / `firmware_cli list` before any publish decision.

### 5. Rollback and fail-safe

**What the code does when a trial image boots but cannot finish a poll:**
- `fp_ota_confirm_if_pending()` is called only on the healthy path, immediately before `enter_deep_sleep` (app_main.c:423). Every failure exit (`fail_and_sleep`, nvs, reset, deadline, json) skips it, so the image stays `ESP_OTA_IMG_PENDING_VERIFY`.
- ESP-IDF app rollback: PENDING_VERIFY becomes ABORTED if a reset occurs without `esp_ota_mark_app_valid_cancel_rollback()`, and the bootloader boots the previous app. `[CITED: docs.espressif.com/projects/esp-idf/en/v5.3.1/esp32s3/api-reference/system/ota.html]` The firmware's own comment relies on deep-sleep wake re-entering the bootloader's pending-verify check (app_main.c:415-422); the docs page fetched here does not state this for deep sleep, so it is `[ASSUMED]` from project comments plus H42-07 (indirect evidence on the real frame: after a successful confirm the frame stayed on the new version over many deep-sleep wakes). A trial image that stays unconfirmed through a deep sleep was NOT observed on hardware; only the crash/panic variant (H42-10) was.
- After rollback the previous firmware's `fp_ota_boot_check` classifies `ROLLED_BACK` (running != try, last invalid partition version == try) and reports `X-Ota-Result: rollback;<version>`; the server counts attempts (3 attempts, then the schedule fails, per the H42-10 evidence). The rolled-back image first needs a wake (the unreachable-trial wake sleeps the backoff, 300 s at n=0) then runs the old firmware.
- A genuine Wi-Fi outage during the trial wake also rolls back a healthy image. Existing behaviour, accepted, retried by the schedule.
- New-image-specific risk is exactly the new code path: first trial wake always downloads and parses the container (the hash changes), so a parse bug, a bad header grammar or an oversize body fails the wake and the image rolls back before it is ever confirmed. If the server contradicts the header (D-06) the frame gets raw and hash-skips, which confirms the image. That is intended.
- `ota_policy.c` itself decides nothing new. No change to `ota.c`, `ota_policy.c`, or `sdkconfig.defaults` is required or advisable.

**What can be tested where:**
| Behaviour | Host (`cc`) | CI | EE04 bench only |
|-----------|-------------|----|-----------------|
| Boot classification incl. rollback/interrupted | `test_ota_policy.c` (`boot_classify_cases`) existing | `firmware.yml` host job | - |
| Container accept/reject, legacy accept, CRC table equals zlib | `test_image_container.c` + fixtures | same | - |
| Compile of new glue, image size vs slot, production config | - | `firmware.yml` build + `check_production_config.sh built` | - |
| Bootloader rolls back an unconfirmed trial across deep sleep | no | no | yes |
| Rollback on "boots but never completes a poll" | no | no | yes: build dev images with `SKYPANE_FAULT=nvs` and `SKYPANE_FAULT=slow_wake` (both end in a failure sleep without confirming), sign with the bench key, schedule to the bench unit, expect `rollback` result then old version |
| Signature rejection of wrong/unsigned image | no | `espsecure verify_signature` in release job | yes (SIGNING.md bench procedure, step 5-6) |
| Real frame still polls, correct image after OTA | no | no | live-frame check by owner after publication (out of this phase) |

`SKYPANE_FAULT=...` builds are refused outside `SKYPANE_PROFILE=dev` (`firmware/build.sh`), so a fault image can never be a release. The fault options exist today; no new fault code is needed. Residual: the EE04 bench unit needs a build compatible with its panel (Phase 58 driver spike). Whether an EE02-profile image can even run its OTA mechanics there is unverified; the planner should state this as a dependency on Phase 58, not solve it here. `[ASSUMED]`

**Proposed new host tests for fail-safe:**
- `test_image_container.c`: table CRC equals the bit-by-bit reference on all fixtures and on a generated 960000-byte body; framed full-size body with header_len 24 and with header_len 255 parses; a body at `legacy_len + 256` (past the cap) is rejected by `fp_body_len_plausible`.
- `test_validate.c`: `fp_body_len_plausible` boundaries (960000 ok, 959999 no, 960023 no, 960024 ok, 960255 ok, 960256 no); `fp_hw_type_valid` (accepts the key, rejects empty, uppercase, `;`, space, 65 chars, NULL).
- announce predicate: `(imgfmt_bad == 0) -> announce`, any non-zero -> omit (pure, in `validate.c`).

### 6. Release deliverables and how to build without publishing

- **Pipeline (`firmware-release.yml`):** triggers on tag push `fw-v*`; `guard` job checks the tag shape and that the commit is an ancestor of `origin/main`; `release` job runs in the reviewer-gated `firmware-signing` environment: `SKYPANE_RELEASE_TAG=<tag> ./firmware/build.sh`, `check_production_config.sh built`, `check_log_contract.sh`, sign with the secret key in a `--network none` container pinned by digest, `espsecure.py verify_signature` against `firmware/signing/skypane-signing-pubkey.pem`, `scripts/fw_release_manifest.py --check-only` then generate `release.json`/notes, `gh release create`, then `gh workflow run ci.yml --ref main`. So pushing the tag publishes a GitHub Release and the next production deploy imports every release into the VPS registry (ci.yml "Download firmware releases"), still not scheduled to any frame. Therefore this phase must not push the tag, and must not merge (the guard also requires the commit on main). `[VERIFIED: .github/workflows/firmware-release.yml, ci.yml]`
- **Build/verify without a tag:** the Docker daemon here is not running (`/var/run/docker.sock` absent), `idf.py` is not installed; local `./firmware/build.sh` is not usable in this environment. Use `firmware.yml` (runs on push or pull request touching `firmware/**`): host tests, `check_production_config.sh static`, `check_log_contract.sh`, `./firmware/build.sh` (unsigned, `PROJECT_VER` from `git describe`), `check_production_config.sh built`. It uploads no artifact, so CI proves compile, config and (if a size check is added) slot fit, but yields no downloadable image. If a size figure is wanted, add a step to `firmware.yml` that prints `stat -c %s firmware/build-ee02/skypane.bin` against `0x250000` and fails under a chosen free margin; do not add an upload step that makes an unsigned image easy to flash (`flash.sh` refuses unsigned images anyway). The signed image only exists after the owner's tag and approval. `[VERIFIED: firmware.yml]`
- **Version:** latest tag `fw-v1.0.4`; the device version floor is `fw-v1.0.0` and the build number is derived from the version string (monotonic at publish time). A protocol-additive feature release suggests `fw-v1.1.0`; the owner chooses at tag time. `[ASSUMED]`
- **Release instructions (deliverable, English):** one owner-facing document in the phase folder (not shipped code, no phase IDs needed in code comments). Layout: (1) Preconditions checklist (Phase 47 allows it per owner; SIGNING.md bench table filled with observed results on the EE04; server release containing D-06 deployed first; frame running version read from `firmware_cli list`). (2) What the release contains and what each change does for the live frame (reader, two headers, 401 behaviour, one extra redraw, restarted 47.1 window). (3) Procedure: merge to main (owner), choose tag, `git tag fw-vX.Y.Z && git push origin fw-vX.Y.Z`, approve the `firmware-signing` environment, CI signs and verifies, deploy imports, then the companion Update page schedules to the legacy type. (4) Signature verification: `espsecure.py verify_signature --version 2 --keyfile firmware/signing/skypane-signing-pubkey.pem skypane-<tag>.bin`, plus compare sha256 with `release.json`. (5) Rollback and abort: companion cancel before the frame is offered; crash/unconfirmed rollback is automatic; voluntary rollback by scheduling an older already-published release above the floor; last resort USB flash with the signed factory image (SIGNING.md). (6) Post-install checks: frame reports the new `X-Fw-Version`, `installed` event, next wake at the usual cadence, one redraw then hash-skips, `fp_diag image fmt=container crc_ms=` (bench), battery reading, no `rollback`/`fail-*` events in `device_report.json`. (7) What to watch for the 47.1 window restart.

### 7. Residual risk of the frame becoming unreachable

| # | Risk | Mitigation in this plan | Still open |
|---|------|-------------------------|-----------|
| R1 | New image cannot parse what the server sends | Parse fails on the trial wake, no confirm, bootloader rolls back; sticky `imgfmt_bad` keeps later wakes on raw | Unconfirmed-trial rollback not yet seen on a device |
| R2 | New image crashes | Panic rollback, seen on the real frame (H42-10) | - |
| R3 | Server mismatch/misconfiguration with the header | D-06: raw image still served, no offer | Server deploy must precede firmware |
| R4 | A bug in `fp_api_download` size logic bricks every download | CI host tests for the pure gates; trial wake downloads first, so the failure is caught before confirm | Compile and runtime of glue only provable in CI/bench |
| R5 | 401 loop on the live frame | Existing token erase + re-enrol + backoff to 6 h, no screen | Token erase path has no hardware evidence |
| R6 | Wrong or unsigned image | Signature gates seen on the real frame (SIGNING.md, BRINGUP-LOG) | - |
| R7 | Wi-Fi outage during the trial wake rolls back a healthy image | Schedule retries (3 attempts) | Accepted existing behaviour |
| R8 | Image grows past the slot | 43% free at the last measurement | Re-check in CI after the change |

## Common Pitfalls

### Pitfall 1: Hash computed over the payload instead of the whole body
**What goes wrong:** every container download reports `verify` and the frame rolls back.
**Why:** the server hashes the exact bytes served, header included.
**How to avoid:** hash all `got` bytes; unit-test the plausibility gate and keep `fp_download_verdict` unchanged.
**Warning signs:** `sha256 MISMATCH, dropping image` only when `X-Img-Fmt` is sent.

### Pitfall 2: Header name collides with an existing "no effect" test
**What goes wrong:** `test_hardware_claimed_by_the_device_has_no_effect` fails or its meaning is muddied.
**How to avoid:** use `X-Hw-Type`; add a new test that a contradicting claim removes the offer, and keep the old test unchanged.

### Pitfall 3: Second type resolution in the display path
**What goes wrong:** `test_hardware_type_is_resolved_once_outside_the_locks` fails.
**How to avoid:** resolve once in `_handle_display`, pass into `_record_device_report_and_offer` through an optional argument.

### Pitfall 4: Announcing the container while the server cannot be sure of the type
**What goes wrong:** a mismatch serves a container to a frame of another type (wrong dimensions rejected by the reader, but it would still be a failed wake).
**How to avoid:** the contradiction check wraps both the offer and `_served_image`.

### Pitfall 5: `X-Img-Fmt` left on the shared handle for the image GET
**What goes wrong:** the same-origin download reuses `s_http`; stale headers travel with it.
**How to avoid:** extend `clear_request_headers` with both new names; the existing `clear_request_headers(http)` call before the download then removes them.

### Pitfall 6: Failed-parse path writes the image hash or draws the fault screen
**What goes wrong:** last image lost or hash recorded for a picture never shown.
**How to avoid:** return before `fp_nvs_set_str(FP_NVS_IMAGE_HASH, ...)`; keep the sticky flag so a second failure cannot reach the NO CONNECTION gate.

### Pitfall 7: Editing frozen files
`panel.c`, `epd13in3e.c` (panel-diff guard), `wake_telemetry.*`, `wake_record.*`, `measured_fields_freeze.json`, `test_phase47_freeze.py`, `hardware/`. Any edit fails a guard or breaks the owner's measurement contract.

### Pitfall 8: Stale documentation claims
`firmware/VENDOR.md` says the reader is "not linked into the shipped binary until a later release" and `docs/IMAGE-FORMAT.md` has "Nothing in this change is wired". Update both to the as-built description; every changed vendored file needs its VENDOR.md row updated (and `check_comment_history.py` must stay clean).

## Runtime State Inventory

Not a rename or migration phase, but two state items matter for the frame:

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | NVS `image_hash` on the live frame holds the hash of the raw image; after the OTA the container hash differs, forcing one redraw. New NVS key `imgfmt_bad` (string key, because `nvs_util.h` only offers `fp_nvs_get_str`/`set_str`/`erase_key`) added (absent = announce). | Code edit only; no migration. Document the one extra redraw. |
| Live service config | Server `fleet.db` hardware type of the live frame must be `xiao-ee02-13in3-spectra6` (the header value); `device_report.json` stamps it. | Verify with `firmware_cli list` / fleet CLI before publication; none changed by this phase. |
| OS-registered state | None. | None. |
| Secrets/env vars | Signing key stays in the `firmware-signing` environment; no change. | None. |
| Build artifacts | `firmware/build-ee02/` is per-build; `sdkconfig` is wiped by `build.sh` each time. | None. |

## Code Examples

### Announcement and claim headers (display request only)
```c
// firmware/main/api_client.c (shape; names are the planner's)
static void capability_headers(esp_http_client_handle_t http)
{
    char off[4] = "";
    fp_nvs_get_str(FP_NVS_IMGFMT_BAD, off, sizeof(off)); /* absent = "" */
    if (fp_imgfmt_announce(off[0] != 0)) {
        esp_http_client_set_header(http, "X-Img-Fmt", "1");
    }
    if (fp_hw_type_valid(CONFIG_SKYPANE_HW_TYPE)) {
        esp_http_client_set_header(http, "X-Hw-Type", CONFIG_SKYPANE_HW_TYPE);
    }
}
```
and in `clear_request_headers`: `esp_http_client_delete_header(http, "X-Img-Fmt"); esp_http_client_delete_header(http, "X-Hw-Type");`.

### Table CRC, drop-in for `imgc_crc32`
```c
// firmware/main/image_container.c: same signature and result as zlib.crc32
static uint32_t crc_table[256]; /* or a const initialised table, 1 KB .rodata */
uint32_t imgc_crc32(const uint8_t *data, size_t len)
{
    uint32_t crc = 0xFFFFFFFFu;
    for (size_t i = 0; i < len; i++) {
        crc = (crc >> 8) ^ kCrcTable[(crc ^ data[i]) & 0xFFu];
    }
    return crc ^ 0xFFFFFFFFu;
}
```
Use a `static const uint32_t kCrcTable[256]` literal (generated once, checked in, verified by the host test against the existing bitwise code) rather than a lazily built table, so there is no init-order or reentrancy question. The host benchmark in this session confirmed table and bitwise results are identical on a 960000-byte buffer.

### Server mismatch test shape (stub-server, FrameServer subprocess like `test_image_negotiation.py`)
```python
def test_contradicting_claim_serves_raw_and_no_offer(...):
    live = seed(...)  # legacy type, a release scheduled for it
    doc = poll(server, live, {"X-Img-Fmt": "1", "X-Hw-Type": "seeed-ee04-7in3-spectra6"})
    assert doc["firmware"] is None
    assert len(fetch_bytes(doc["image_url"])) == 960000          # raw, not 960024
    doc = poll(server, live, {"X-Img-Fmt": "1", "X-Hw-Type": hardware.LEGACY_KEY})
    assert len(fetch_bytes(doc["image_url"])) == 960024          # container
    assert doc["firmware"] is not None
```
The mismatch value needs a key `hardware.is_known` does not have to know: the claim is only compared as a string, so a made-up well-formed key is enough; a simulated type needs `SKYPANE_SIM_HARDWARE=1` only for the fleet-frame variants.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Exact 960000-byte download gate | Legacy raw or SPIM container, both accepted by `imgc_parse` | Phase 50 (reader/spec), wired here | Frame can receive either form |
| Type from `X-Fw-Version`/`hw_rev` | Server-assigned type from `fleet.db`; device claim only restricts | Phase 49 | A mislabelled or misflashed frame is never offered the wrong binary |
| Generic NO CONNECTION on any comm failure | Not for `auth`/`enrol` | This phase | Last image survives a revoked credential |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Deep-sleep wake re-enters the bootloader's pending-verify check, so an unconfirmed trial rolls back at the next wake | Rollback | Trial could stay on an image that never confirms; bench check D-01 covers it |
| A2 | S3 CRC cost: table about 40-80 ms, bitwise about 0.2-0.4 s | Q1 | Only energy-model precision; measure `crc_ms` on the bench |
| A3 | Header name `X-Hw-Type` and value format (the server hardware key) | Q2 | Planner/owner may prefer another name; server grammar and tests move with it |
| A4 | Sticky `imgfmt_bad` opt-out is acceptable to the owner | Q1 | Container path stays off for that frame until reflash or NVS erase |
| A5 | Suggested version `fw-v1.1.0` | Release | Owner picks any monotonic tag |
| A6 | EE04 bench unit can run the OTA mechanics of an image built by this project | Rollback | Bench step may need a Phase 58 build; plan needs a contingency |
| A7 | CPU clock is the IDF default for S3 (not read from a build) | Q1 | Timing estimate shifts |

## Open Questions

1. **Should the NO CONNECTION screen also stay off for other token classes?**
   - What we know: D-04 covers only repeated 401.
   - What's unclear: whether `secret`/`config` (provisioning defects) should keep drawing.
   - Recommendation: change only `auth` and `enrol`; leave the rest.
2. **Which exact version does the live frame run, and is the 47.1 window already running?**
   - Not readable from the repository. Read `firmware_cli list` and the report entry before any publication decision; owner-only.
3. **Does the server D-06 change need to be deployed before the firmware?**
   - It is a BYOS deploy, which the roadmap gates on Phase 47 for frame-touching production deploys. The change is a no-op for the header-less live frame (freeze test), so the owner may release it earlier; the firmware works against an older server (unknown headers ignored, container not served, raw accepted).
4. **Bench unit.** EE04 build compatibility for the rollback scenarios depends on Phase 58.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `cc` (host C compiler) | `run_host_tests.sh` | yes | system cc | - |
| Python 3 | tooling, shell checks | yes | /usr/local/bin/python3 (pytest not installed) | install pytest in CI only |
| Docker daemon | `firmware/build.sh` | no (`/var/run/docker.sock` missing) | CLI 29.9.2, no daemon | `firmware.yml` in CI |
| ESP-IDF toolchain | firmware compile | no | - | CI container `espressif/idf:v5.3.1` |
| `espsecure.py`, `gh` auth, signing key | signing | not used here | - | `firmware-release.yml` only, owner-gated |

**Missing with no fallback in this environment:** a local firmware compile. The planner must schedule the CI run (push of the work branch, which is an executor action, never a merge or tag) as the compile gate.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | firmware: plain C asserts compiled by `cc -std=c11`; server: pytest + xdist (`./scripts/run-all-tests.sh`) |
| Config file | `firmware/tests/run_host_tests.sh`; `pyproject.toml` |
| Quick run command | `./firmware/tests/run_host_tests.sh` (about seconds); `python3 -m pytest stub-server/test_hw_claim.py stub-server/test_image_negotiation.py stub-server/test_phase47_freeze.py -q` |
| Full suite command | `./scripts/run-all-tests.sh` plus the `firmware.yml` workflow |

### Phase Requirements to Test Map (roadmap criteria)
| Criterion | Behavior | Test Type | Automated Command | File Exists? |
|-----------|----------|-----------|-------------------|-------------|
| C1: one release bundles reader, hardware header, 401 recovery | All three present in one build; image builds production-clean | CI build + host | `firmware.yml` (`check_production_config.sh built`, `check_log_contract.sh`) | exists, extend |
| C1 (reader) | Container and legacy accepted, malformed rejected before display; table CRC == zlib | host unit | `./firmware/tests/run_host_tests.sh` (`test_image_container`) | extend |
| C1 (download gate) | Body length gate and hw-type grammar | host unit | `test_validate` | extend |
| C1 (401) | `auth`/`enrol` never draw; backoff grows to 6 h and resets on success | host unit | `test_fault_screen`, `test_sleep_decision` | extend |
| C1 (publication gate) | Nothing published: no `fw-v*` tag created, no merge | manual/CI observation | `git tag --list 'fw-v*'` unchanged, `gh release list` unchanged | n/a |
| C1 (bench gate) | Signing bench procedure passed on non-live unit | manual-only (hardware) | SIGNING.md table filled with observed results | manual |
| C2: wakes on cadence, correct image, container only after announcing | Header-less frame unchanged; announcing frame gets container; mismatch gets raw | server integration | `pytest stub-server/test_phase47_freeze.py stub-server/test_image_negotiation.py stub-server/test_hw_claim.py` | freeze/negotiation exist; hw_claim is new (Wave 0) |
| C2 (cadence on device) | `sleep_s` honoured, one redraw then hash-skip | manual-only (EE04 bench, later live frame) | `firmware/monitor.sh` capture: `poll ok sleep_s=`, `hash_skip=1` | manual |
| C3: failed update stays on previous firmware | Wrong signature refused; unconfirmed/crashing trial rolls back | host (classification) + manual-only | `test_ota_policy`; bench `SKYPANE_FAULT=nvs` / `slow_wake` images | existing + manual |
| Phase 47 freeze | No change for header-less frame | server integration | `pytest stub-server/test_phase47_freeze.py` | exists |

### Sampling Rate
- **Per task commit:** `./firmware/tests/run_host_tests.sh`; for server tasks the three stub-server test files above.
- **Per wave merge:** full `./scripts/run-all-tests.sh`; `firmware.yml` green on the work branch.
- **Phase gate:** firmware.yml green (compile, size, log contract, production config) + all host and server suites green + release instructions reviewed. Bench items are explicit owner-gated manual checks, recorded as "not run" until the EE04 arrives (do not tick them).

### Wave 0 Gaps
- [ ] `stub-server/test_hw_claim.py` (match, contradiction on live, fleet and pending frames, absent, malformed, no store/no log of the claim; the old claims test unchanged).
- [ ] New host cases in `test_image_container.c`, `test_validate.c`, `test_fault_screen.c`, `test_sleep_decision.c` (listed above).
- [ ] `firmware/tests/` shell check that `CONFIG_SKYPANE_HW_TYPE` default equals `server.hardware.LEGACY_KEY` (run in `firmware.yml` build job).
- [ ] Optional `firmware.yml` image-size step.

## Security Domain

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes (401 recovery) | Existing bearer token + enrolment secret; token erased on 401, re-enrol on next wake; no new credential handling |
| V3 Session Management | no | - |
| V4 Access Control | yes | Offer authorisation stays server-assigned type; the new claim can only withdraw (Pattern 2) |
| V5 Input Validation | yes | Strict regex for `X-Hw-Type`; `negotiate_version` for `X-Img-Fmt`; `imgc_parse` 64-bit length checks; plausibility gate before parse |
| V6 Cryptography | yes | No new crypto; SHA-256 over whole body remains the authenticity gate, CRC is corruption-only; signing via existing RSA-3072 CI flow |

### Known Threat Patterns
| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Device claims another type to obtain another type's firmware | Elevation | Claim ignored for grants; only restricts (tested) |
| Spoofed header to deny a victim service | Denial | Header is per request and tied to the authenticated device's own token; it affects only that device's own response |
| Oversized or malformed container to overflow buffer | Tampering | Hard cap on read, `imgc_parse` validation before any use, SHA-256 before parse |
| Log/state injection via the header | Tampering | Regex-validated, never stored, dedup log line prints sanitized value only |
| Signing key exposure | Information disclosure | Unchanged: key only in `firmware-signing`, `--network none` signing container |

## Sources

### Primary (HIGH confidence)
- Repository, read in this session: `firmware/main/{app_main,state_machine,api_client,image_container,ota,sleep_decision,backoff,fault_screen,panel,epd13in3e,wake_deadline}.[ch]`, `firmware/tests/*`, `firmware/SIGNING.md`, `firmware/VENDOR.md`, `docs/IMAGE-FORMAT.md`, `stub-server/byos_server.py`, `stub-server/test_phase47_freeze.py`, `stub-server/test_ota_offer.py`, `stub-server/measured_fields_freeze.json`, `server/hardware.py`, `server/image_container.py`, `.github/workflows/{firmware,firmware-release}.yml`, `hardware/BRINGUP-LOG.md` (OTA session), Phase 49 research, Phase 55 handoff, Phase 62 verification.
- Host run: `./firmware/tests/run_host_tests.sh` (15 suites pass); CRC benchmark and zlib equality (scratch, not committed).
- ESP-IDF v5.3.1 OTA docs, App Rollback section: https://docs.espressif.com/projects/esp-idf/en/v5.3.1/esp32s3/api-reference/system/ota.html
- ESP-IDF `esp_rom_crc.h` v5.3.1: https://raw.githubusercontent.com/espressif/esp-idf/v5.3.1/components/esp_rom/include/esp_rom_crc.h

### Secondary (MEDIUM confidence)
- None.

### Tertiary (LOW confidence)
- S3 CRC timing and CPU clock (estimates, flagged A2/A7).

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH, nothing new, all in repo.
- Architecture: HIGH, every integration point read in code; MEDIUM on rollback-across-deep-sleep for an unconfirmed (non-crashing) trial.
- Pitfalls: HIGH, each tied to a specific existing test or guard.

**Not verified here:** any ESP-IDF compile; any hardware behaviour of the new code; the Python suites (pytest absent); the running version and install date of the live frame; S3 timing.

**Research date:** 2026-11-14
**Valid until:** 2026-12-14 (stable; revisit if Phase 58 changes the bench build or the hardware vocabulary)
