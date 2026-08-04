# Phase 1: Foundation — Hardware Bring-up & ADS-B Validation - Pattern Map

**Mapped:** 2026-08-04
**Files analyzed:** 10 (firmware: 6, stub server: 1, ADS-B test: 1, sdkconfig: 2)
**Analogs found:** 10 / 10 — **all external** (no local codebase exists; this is a greenfield repo)

## Important Note on Analog Source

This repository currently contains only `.planning/` and `.claude/CLAUDE.md` — **no application code exists to search for local analogs.** RESEARCH.md's authors already fetched and inspected the live `github.com/flightportrait/frame` repository (Apache-2.0) directly this session (not from training-data recall), and it is treated here as the closest — and only — available analog/reference implementation for every file in this phase. Per CONTEXT.md/RESEARCH.md's explicit "Don't Hand-Roll" guidance, most of these files should be **vendored/forked directly** from that repo rather than written from scratch, then trimmed of production-only features (BLE provisioning, OTA, signed re-pair, QR pairing).

All "Match Quality" values below are `external-vendor` (copy/adapt from the reference repo) rather than `exact`/`role-match` (which would imply an in-repo analog).

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|--------------------|------|-----------|-----------------|----------------|
| `firmware/main/app_main.c` | controller (wake dispatcher) | event-driven | `flightportrait/frame` `main/app_main.c` | external-vendor |
| `firmware/main/api_client.c/.h` | service (HTTP client) | request-response | `flightportrait/frame` `main/api_client.c/.h` | external-vendor |
| `firmware/main/backoff.c/.h` | utility (pure function) | transform | `flightportrait/frame` `main/backoff.c/.h` | external-vendor (verbatim) |
| `firmware/main/epd13in3e.c/.h` | driver (panel blit) | streaming (SPI) | `flightportrait/frame` `main/epd13in3e.c/.h` | external-vendor (verbatim) |
| `firmware/main/panel.c/.h` | service (blit orchestration) | transform | `flightportrait/frame` `main/panel.c/.h` | external-vendor (simplify guard) |
| `firmware/main/nvs_schema.h` | config/model | CRUD (persisted state) | `flightportrait/frame` `main/nvs_schema.h` | external-vendor (trimmed) |
| `firmware/main/sdkconfig.defaults` + `sdkconfig.ee02.defaults` | config | — | `flightportrait/frame` `sdkconfig.ee02.defaults` | external-vendor (unverified on real hw — this phase verifies it) |
| `stub-server/byos_server.py` | service (local HTTP stub server) | request-response | `flightportrait/frame` `examples/byos_server.py` | external-vendor (near-verbatim, stdlib-only) |
| `adsb-test/query_aggregator.py` | utility (throwaway test script) | request-response | none (new pattern) — use stdlib `urllib.request` per RESEARCH.md Code Examples | no-analog (see below) |
| `firmware/tests/test_backoff.c` | test | transform | `flightportrait/frame` `tests/` (pure-C, compiles with plain `cc`) | external-vendor (pattern; exact filenames unconfirmed — verify when vendoring) |

## Pattern Assignments

### `firmware/main/app_main.c` (controller, event-driven)

**Analog:** `flightportrait/frame` `main/app_main.c` (fetched directly this session; verbatim structure captured in RESEARCH.md "Pattern 1")

**Core wake→poll→backoff→sleep pattern** (RESEARCH.md lines 205-235):
```c
void app_main(void) {
    nvs_handle_t nvs;
    nvs_open(FP_NVS_NAMESPACE, NVS_READWRITE, &nvs);

    esp_err_t poll_result = fp_poll_and_display(nvs); // your api_client.c wrapper

    if (poll_result == ESP_OK) {
        nvs_set_u8(nvs, FP_NVS_BACKOFF_N, 0);
        nvs_commit(nvs);
        uint32_t sleep_s = fp_last_sleep_s(); // from server response, or a fixed test interval
        nvs_close(nvs);
        esp_sleep_enable_timer_wakeup((uint64_t)sleep_s * 1000000ULL);
        esp_deep_sleep_start();
    } else {
        uint8_t n = 0;
        nvs_get_u8(nvs, FP_NVS_BACKOFF_N, &n);
        uint32_t backoff_s = fp_backoff_seconds(n); // min(2^n * 5min, 6h)
        if (n < UINT8_MAX) nvs_set_u8(nvs, FP_NVS_BACKOFF_N, n + 1);
        nvs_commit(nvs);
        nvs_close(nvs);
        esp_sleep_enable_timer_wakeup((uint64_t)backoff_s * 1000000ULL);
        esp_deep_sleep_start();
    }
}
```

**Subtraction guidance (Anti-Patterns, RESEARCH.md line 282):** Strip BLE Security-2 provisioning, OTA, signed re-pair, and factory/production sdkconfig branches. Hardcode WiFi credentials and stub-server address/token — Phase 1 does not need dynamic provisioning.

**Persistence rule (Pattern 3, RESEARCH.md lines 255-267):** `backoff_n` must use NVS, not `RTC_DATA_ATTR` — RTC memory only survives deep sleep, not power loss/brownout. Vendor flightportrait's own NVS-based backoff persistence, not a simplified RTC-only version.

---

### `firmware/main/backoff.c/.h` (utility, transform)

**Analog:** `flightportrait/frame` `main/backoff.c` — vendor **as-is**, it's a pure function with no board dependencies.

**Exact formula** (RESEARCH.md lines 242-253, source verified verbatim):
```c
#define BACKOFF_BASE_S (5u * 60u)   /* 5 minutes */
#define BACKOFF_MAX_S  (6u * 3600u) /* 6 hours */

uint32_t fp_backoff_seconds(uint8_t n) {
    if (n >= 7) {           /* 2^7 * 5min = 640min > 6h, saturates */
        return BACKOFF_MAX_S;
    }
    uint32_t s = BACKOFF_BASE_S << n;
    return s > BACKOFF_MAX_S ? BACKOFF_MAX_S : s;
}
```

**Test pattern:** flightportrait ships pure-C contract tests under `tests/`, compiling with plain `cc` (no ESP-IDF needed). Suggested quick-run command (RESEARCH.md Validation Architecture): `cc -o /tmp/test_backoff tests/test_backoff.c main/backoff.c && /tmp/test_backoff`. Confirm exact filenames in the reference repo when vendoring — not individually enumerated this research session.

---

### `firmware/main/epd13in3e.c/.h` (driver, streaming/SPI)

**Analog:** `flightportrait/frame` `main/epd13in3e.c/.h` — vendor **as-is**. This is a native ESP-IDF dual-chip driver for the exact 13.3" Spectra 6 panel, already Kconfig-pin-configurable.

**Critical board-specific caveat (Anti-Patterns, RESEARCH.md lines 283-284 and Pitfall 1, lines 300-304):** Do NOT inherit E1004 pin assignments. On the EE02 board specifically, `CS_M=44` and `EN=43` collide with UART0 RX/TX — the sdkconfig must use `CONFIG_ESP_CONSOLE_USB_SERIAL_JTAG=y` / `CONFIG_ESP_CONSOLE_UART_DEFAULT=n`. A pin conflict here silently corrupts panel behavior (partial refresh, wrong colors) rather than throwing an obvious error — treat this as a known trap when vendoring, not a hypothetical.

---

### `firmware/main/panel.c/.h` (service, transform)

**Analog:** `flightportrait/frame` `main/panel.c/.h` — vendor, but simplify the refresh-spacing guard to Phase 1's needs (no production refresh-rate-limiting logic required for a spike).

---

### `firmware/main/nvs_schema.h` (config/model, CRUD)

**Analog:** `flightportrait/frame` `main/nvs_schema.h` — vendor, trimmed.

**Trim to exactly three fields** (RESEARCH.md Recommended Project Structure, line 189):
- `dev_token` — hardcoded/simple for Phase 1 (not the full provisioning flow)
- `image_hash` — for the hash-based "no change" skip logic
- `backoff_n` — the persisted exponential-backoff counter (see Pattern 3 above)

---

### `stub-server/byos_server.py` (service, request-response)

**Analog:** `flightportrait/frame` `examples/byos_server.py` — vendor near-verbatim.

**Why this exact file (Don't Hand-Roll table, RESEARCH.md line 293):** Zero-dependency stdlib-only (`argparse`, `hashlib`, `json`, `os`, `secrets`, `sys`, `http.server`), already implements bearer tokens, hash-based no-change responses, and the exact response shape firmware's `api_client.c` expects — matches the 3-endpoint contract (`/setup`, `/display`, `/log`) from `docs/PROTOCOL.md`.

**Invocation pattern** (RESEARCH.md line 275, Pattern 4):
```bash
python3 byos_server.py --image test_panel.bin --port 8642 --sleep 300
```

**Protocol decision baked into this pattern:** `docs/PROTOCOL.md` §5 explicitly permits a plain-HTTP BYOS override for hand-set (non-default) server targets — no self-signed TLS cert setup is required for Phase 1's local-only stub server (D-09, Open Question 1). Firmware's BYOS/api_base override must point at `http://<laptop-lan-ip>:8642` rather than the compiled-in HTTPS default. Flag this plain-HTTP path in code comments as "Phase 1 only" so it is not carried into Phase 2's real VPS deployment (Security Domain, RESEARCH.md line 463).

---

### `adsb-test/query_aggregator.py` (utility, request-response)

**No analog exists** — this is a new throwaway script pattern specific to this phase, not present in flightportrait/frame (which has no ADS-B aggregator integration; that's unique to Ink Frame's own requirements).

**Reference pattern to follow** (RESEARCH.md Code Examples, lines 332-347) — stdlib `urllib.request`, no pip install:
```bash
# adsb.fi
curl "https://opendata.adsb.fi/api/v2/lat/48.7233/lon/2.3794/dist/5"
# airplanes.live
curl "https://api.airplanes.live/v2/point/48.7233/2.3794/5"
```

Both are free, no-auth, 1 req/sec REST endpoints with position+radius queries (RESEARCH.md Standard Stack). Query both in parallel per Open Question 2's recommendation; only investigate ADS-B Exchange if both fall short. The actual validation test is querying during a known runway-3 departure/arrival window and checking for plausible low-altitude/ground-speed values — not just "does the API return data over Orly generally" (Pitfall 3, RESEARCH.md lines 312-316).

---

## Shared Patterns

### Exponential Backoff (cross-cutting: app_main.c + backoff.c + NVS)
**Source:** `flightportrait/frame` `main/backoff.c` + NVS-persisted `backoff_n` field
**Apply to:** `firmware/main/app_main.c`, `firmware/main/backoff.c/.h`, `firmware/main/nvs_schema.h`
**Rule:** `min(2^n × 5min, 6h)`, persisted in NVS (not RTC memory) so it survives power loss, not just deep sleep. This is DEVICE-03's explicit success criterion — do not substitute a fixed-interval retry.

### SHA-256 Download Verification (cross-cutting: api_client.c + panel.c)
**Source:** ESP-IDF's `mbedtls` SHA-256 API (per Don't Hand-Roll table, RESEARCH.md line 294) — flightportrait's `api_client.c` already uses this, don't hand-roll a checksum.
**Apply to:** `firmware/main/api_client.c/.h` (verify before handing buffer to panel.c), `firmware/main/panel.c/.h` (reject and treat as failed wake → triggers backoff on hash/size mismatch, exact 960,000-byte check).

### Plain-HTTP BYOS Local Stub Allowance (cross-cutting: api_client.c + byos_server.py)
**Source:** `docs/PROTOCOL.md` §5 (flightportrait/frame), RESEARCH.md Pattern 4 and Open Question 1
**Apply to:** `firmware/main/api_client.c/.h` (BYOS override must accept a plain-HTTP base URL for Phase 1), `stub-server/byos_server.py` (serves plain HTTP, no cert needed)
**Explicit boundary:** This plain-HTTP allowance is Phase-1-only (local dev stub); Phase 2+'s real Hetzner VPS must use real HTTPS. Comment this clearly in firmware code so it isn't silently carried forward.

### EE02 Board-Specific Pin/Console Config (cross-cutting: sdkconfig + epd13in3e.c)
**Source:** `flightportrait/frame` `sdkconfig.ee02.defaults`
**Apply to:** `firmware/main/sdkconfig.ee02.defaults`, `firmware/main/epd13in3e.c/.h`
**Rule:** `CONFIG_ESP_CONSOLE_USB_SERIAL_JTAG=y` / `CONFIG_ESP_CONSOLE_UART_DEFAULT=n` — never merge E1004 defaults onto this profile; 6 of 8 panel pins differ, and `CS_M`/`EN` collide with UART0 RX/TX specifically on EE02.

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `adsb-test/query_aggregator.py` | utility | request-response | No ADS-B integration exists anywhere in flightportrait/frame (out of scope for that project); RESEARCH.md's Code Examples section (stdlib `urllib.request` against adsb.fi/airplanes.live) is the closest available reference and should be used directly — see Pattern Assignments above |
| Local RTL-SDR/readsb fallback tooling (D-02, conditional) | service | streaming | Deferred — only needed if the aggregator-API path proves insufficient; not scoped for this pattern map since D-02 makes it conditional. If needed, RESEARCH.md's "State of the Art" section recommends `readsb` (modern fork) over unmaintained `dump1090` |

## Metadata

**Analog search scope:** Entire repository (`.planning/`, `.claude/CLAUDE.md` only — confirmed via CONTEXT.md/RESEARCH.md's explicit "no code exists" statements); external search scope was `github.com/flightportrait/frame` (already fetched/verified directly by RESEARCH.md's authors this session, not re-fetched here to avoid redundant reads)
**Files scanned:** 0 local (none exist) / 10 external reference files already characterized in RESEARCH.md
**Pattern extraction date:** 2026-08-04
