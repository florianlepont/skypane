# Phase 1: Foundation — Hardware Bring-up & ADS-B Validation - Research

**Researched:** 2026-08-04
**Domain:** ESP-IDF embedded firmware (deep sleep / poll / backoff), e-paper driver bring-up, ADS-B data-source validation (aggregator API + RTL-SDR fallback)
**Confidence:** MEDIUM-HIGH (firmware/protocol findings are HIGH — verified directly against the live flightportrait/frame repository; ADS-B aggregator specifics and battery figures are LOW-MEDIUM and require Phase 1's own empirical test to resolve)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Plane-detection validation approach (reopens a prior "pending" decision in PROJECT.md)**
- **D-01:** Test an ADS-B aggregator API first (e.g. ADS-B Exchange, adsb.fi, airplanes.live) as the primary candidate data source for runway-3 plane detection — no local hardware, no antenna, no legal ambiguity, near-zero cost/time to test.
- **D-02:** Only fall back to a local RTL-SDR receiver (and, if reception is confirmed viable, a permanent Raspberry Pi + dump1090/readsb setup forwarding to the VPS) if the aggregator API's coverage at runway 3 — specifically near-ground/low-altitude, which is the hardest case for any receiver — proves insufficient.
- **D-03:** This reverses/supersedes PROJECT.md's current framing of the ADS-B aggregator as "documented fallback only" and local ADS-B as primary — Phase 1's validation should test API-first. **Downstream note:** PROJECT.md/REQUIREMENTS.md's "Out of Scope" and "Key Decisions" sections should be updated after Phase 1 validation confirms which path wins (not before).
- **D-04:** If the local RTL-SDR/Pi fallback is ever needed, its cost is tracked as a **separate budget line**, not counted against the €300 "display + compute" hardware ceiling.

**Firmware bring-up path**
- **D-05:** Board hardware stays as originally planned — Seeed XIAO ESP32-S3 Plus + EE02 kit.
- **D-06:** Firmware development goes straight to ESP-IDF — no Arduino-framework prototyping detour.

**Battery measurement method**
- **D-07:** Use the simple time-to-depletion method: charge fully, run normal wake/poll/sleep cycle untouched, note days/cycles until dead or low-battery. Divide capacity (mAh) by days-until-dead. No extra hardware (rejected: USB inline power meter).

**Hardware readiness & stub server hosting**
- **D-08:** Nothing purchased yet. Plan must budget shipping/lead time before hands-on hardware work, and sequence software-only work (stub server, ESP-IDF setup, aggregator API test) ahead of hardware-dependent work where possible.
- **D-09:** The Phase 1 "stub server" runs locally (user's own computer/network), not the real Hetzner VPS. VPS provisioning deferred to Phase 2.

### Claude's Discretion
- Specific choice of which ADS-B aggregator API to test first (ADS-B Exchange vs. adsb.fi vs. airplanes.live) — left to the researcher/planner.
- Exact wake-interval cadence used during the Phase 1 backoff/battery test — left to the planner.
- Local stub server implementation details (language/framework) — left to the planner, lightweight/throwaway.

### Deferred Ideas (OUT OF SCOPE)
- Whether to build the permanent local ADS-B receiver pipeline (Raspberry Pi + dump1090/readsb + forwarder to VPS) — deferred until Phase 1 determines whether the aggregator API path is sufficient.
- Provisioning the real Hetzner VPS — deferred to Phase 2.
- Updating PROJECT.md/REQUIREMENTS.md's ADS-B framing — should happen once Phase 1's validation produces a result, not before.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DEVICE-03 | Device wakes on a schedule, polls the server over HTTPS, downloads and displays a new image if available, then returns to deep sleep, with exponential backoff on failure | flightportrait's live `docs/PROTOCOL.md`, `main/backoff.c`, `main/app_main.c`, `main/state_machine.c` verified directly (§ Code Examples, § Architecture Patterns) give an exact, provable contract and reference implementation to build the stub-server test against |
| DEVICE-05 | Device runs on battery power only (no wall power, no solar) for v1 | § Battery Measurement Gotchas + § Environment Availability document what's knowable in advance (deep-sleep current is board-dependent and NOT reliably predictable from datasheets) and confirm D-07's time-to-depletion method is sound |
</phase_requirements>

## Summary

This phase has two largely independent validation tracks that can run in parallel once hardware ships: (1) firmware bring-up on real XIAO ESP32-S3 Plus + EE02 hardware against a local stub server, and (2) an ADS-B data-source test that — per CONTEXT.md's reopened decision — now starts with a zero-hardware aggregator API call rather than an RTL-SDR receiver.

The single biggest finding of this research: **flightportrait/frame is not just a reference architecture to study, it is a live, Apache-2.0-licensed ESP-IDF codebase directly usable as a starting point**, including a native (non-Arduino) ESP-IDF driver for the exact 13.3" Spectra 6 dual-chip panel (`main/epd13in3e.c/.h`) and a board profile that already targets the XIAO ESP32-S3 Plus + EE02 kit (`sdkconfig.ee02.defaults`). This resolves the "no confirmed off-the-shelf ESP-IDF driver" concern flagged in STATE.md as a blocker — verified directly against the repository, not inferred. The EE02 profile is explicitly flagged by flightportrait's own maintainers as **not yet confirmed on live hardware** at the time of writing, so Phase 1's hands-on bring-up work IS the validation that profile still needs — this is a legitimate, load-bearing task for the phase, not busywork.

For the ADS-B track, both adsb.fi and airplanes.live offer genuinely free, no-auth, rate-limited (1 req/sec) REST APIs with a position+radius query — either is trivially testable with a single `curl`/script call before any hardware ships. ADS-B Exchange's free/hobby tier terms were less consistently documented across sources in this session and should be spot-checked live before committing engineering time to it specifically. The open question this phase must answer empirically — because no source claims to answer it in general — is whether **any** aggregator's contributing feeders have adequate line-of-sight/antenna elevation to see aircraft at the low-altitude, near-ground segment of runway 3 specifically, as opposed to cruise-altitude overflights, which aggregators handle trivially well.

For battery measurement, the research surfaced an important calibration point: ESP32-S3 **datasheet-level deep-sleep current figures are not a reliable predictor of what a stock development board (like the XIAO ESP32-S3 Plus) will actually draw**, because onboard peripherals (USB-UART bridge, power LED, always-on LDO) commonly add 1000x over the bare-SoC figure. This validates D-07's approach of a real on-hardware time-to-depletion measurement rather than trusting any pre-purchase estimate.

**Primary recommendation:** Fork/vendor the relevant files from `flightportrait/frame` (`main/epd13in3e.c/.h`, `main/backoff.c/.h`, `main/panel.c/.h` as a starting point, `examples/byos_server.py` as the stub server) rather than writing this from scratch; strip out everything Phase 1 doesn't need (BLE provisioning, OTA, factory/production sdkconfig profiles, signed re-pair) to keep the spike minimal; test both ADS-B aggregator APIs (adsb.fi, airplanes.live) with a single unauthenticated script before ordering any RTL-SDR hardware; and treat the EE02 sdkconfig profile as unverified until this phase's own hands-on flash confirms it.

## Architectural Responsibility Map

This is an embedded/IoT project, not a multi-tier web app — tiers are adapted accordingly.

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Wake / poll / deep-sleep / backoff state machine | Device Firmware (ESP32-S3) | Local Stub Server | Firmware owns the loop and the backoff timer (NVS-persisted per protocol); the stub server only needs to answer the 3 protocol endpoints correctly and can also deliberately return failures/be turned off to exercise backoff |
| HTTPS poll protocol contract | Device Firmware | Local Stub Server | Firmware implements the client (`api_client.c` pattern); stub server implements the 3-endpoint contract from `docs/PROTOCOL.md` — both sides must agree on the same contract, which is why the reference protocol doc is canonical for both |
| E-paper panel driver / rendering | Device Firmware | — | Fully on-device; no server-side rendering needed for Phase 1 (any valid 960,000-byte `.bin` test image suffices) |
| ADS-B position data acquisition | External Data Source (aggregator API or RTL-SDR) | Local Test Script | Not wired into the device loop in Phase 1 — validated as a standalone question ("can we get the data at all") via a throwaway script hitting the aggregator API or a locally-run dump1090/readsb instance |
| Battery power management & measurement | Physical Hardware | Device Firmware | The actual mAh/cycle figure is a hardware-measurement fact (time-to-depletion); firmware only controls how efficiently it uses power (sleep current tuning, radio-off timing) |

## Standard Stack

### Core
| Library / Tool | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| ESP-IDF | ≥ 5.3 (5.3.1 pinned in flightportrait's own dev bench notes) | Firmware framework | [VERIFIED: github.com/flightportrait/frame] Confirmed directly in the live repo's `README.md` build instructions and CI; matches CLAUDE.md's existing recommendation |
| flightportrait/frame firmware sources (forked/vendored, not full clone) | main branch, 2026 | Starting point for `app_main.c`, `state_machine.c`, `backoff.c/.h`, `epd13in3e.c/.h`, `panel.c/.h` | [VERIFIED: github.com/flightportrait/frame] Apache-2.0 licensed; directly fetched and inspected file-by-file this session, not inferred from search summaries |
| `examples/byos_server.py` (flightportrait) | current main | Reference local stub server (stdlib-only Python) | [VERIFIED: github.com/flightportrait/frame/blob/main/examples/byos_server.py] Implements exactly the 3 protocol endpoints Phase 1 needs to exercise; zero external dependencies; already handles bearer tokens, hash-based "no change" responses, and configurable `--sleep` |
| Python 3 (stdlib only) | 3.9+ is fine for the stub server itself; flightportrait's own ESP-IDF *build tooling* needs 3.12 specifically | Runs the local stub server and any throwaway ADS-B aggregator test script | [CITED: github.com/flightportrait/frame README] `byos_server.py` uses only `argparse`, `hashlib`, `json`, `os`, `secrets`, `sys`, `http.server` — no pip install needed for the stub server. Note: this machine currently has Python 3.9.6 — sufficient for the stub server, but if you set up ESP-IDF's own Python venv locally (as opposed to Docker), flightportrait's own README warns 3.9 is missing `ruamel.yaml` and 3.13 is unsupported for the IDF tooling itself |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Docker (`espressif/idf:v5.3.1` image) | — | ESP-IDF build without a local toolchain install | [VERIFIED: local machine] Docker 29.4.3 is already installed on this machine. Use `docker run --rm -v $PWD:/project -w /project espressif/idf:v5.3.1 idf.py build` for **building** — this sidesteps flightportrait's own documented Python-version pitfall entirely. **Caveat:** flashing over USB serial from inside Docker Desktop on macOS is unreliable/unsupported without extra device-passthrough setup — plan to install ESP-IDF natively (or use `idf.py` only for `flash`/`monitor` while building in Docker) |
| `urllib.request` (Python stdlib) | — | Query ADS-B aggregator API (adsb.fi / airplanes.live) in a throwaway test script | No external package needed for a single `GET` request to a public, unauthenticated JSON API — avoids any package-legitimacy question entirely |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Forking flightportrait's `epd13in3e.c` driver | Porting Waveshare's own `EPD_13in3e` C reference driver directly | flightportrait's version is already ESP-IDF-shaped and pin-configurable via Kconfig; Waveshare's is a generic reference (often Arduino/STM32-oriented) that would need more adaptation work — no reason to skip flightportrait's version for Phase 1 |
| Python stdlib for the ADS-B test script | `requests` package | `requests` is a fine, well-known package if preferred, but stdlib `urllib.request` needs zero install and is sufficient for one GET call — recommended default to keep Phase 1 minimal, per the user's stated preference for low-setup approaches |
| adsb.fi or airplanes.live first | ADS-B Exchange first | ADS-B Exchange's free/hobby tier terms were the least consistently documented of the three across sources this session (see Assumptions Log A3) — start with adsb.fi or airplanes.live, whose no-auth public REST endpoints were directly confirmed via their own GitHub-hosted docs |

**Installation:**
```bash
# Stub server — no install needed, stdlib only
python3 examples/byos_server.py --image path/to/panel.bin --port 8642 --sleep 3600

# ESP-IDF build via Docker (no native toolchain install required)
docker run --rm -v $PWD:/project -w /project espressif/idf:v5.3.1 idf.py build

# ADS-B aggregator test — no install needed (stdlib urllib), example adsb.fi call:
curl "https://opendata.adsb.fi/api/v2/lat/48.7233/lon/2.3794/dist/5"
# example airplanes.live call:
curl "https://api.airplanes.live/v2/point/48.7233/2.3794/5"
```

**Version verification:** ESP-IDF ≥5.3 confirmed directly against the live flightportrait repo's build instructions (not training-data recall). No pip/npm packages are being installed for Phase 1's core work, so the standard `npm view` / `pip index versions` verification step is not applicable this phase (see Package Legitimacy Audit below).

## Package Legitimacy Audit

**Not applicable this phase.** Phase 1's software work (ESP-IDF firmware, local stub server, ADS-B aggregator test script) requires **zero external package installations**:
- ESP-IDF's own toolchain is fetched by `idf.py`/Docker image, not a project dependency to audit.
- `byos_server.py` is Python stdlib-only (verified by direct inspection of its imports).
- The recommended ADS-B test script uses `urllib.request` (stdlib).
- Firmware C sources vendor flightportrait's files directly (Apache-2.0) rather than pulling them as an ESP-IDF component-registry dependency — no `idf_component.yml` external dependency is required for the pieces Phase 1 needs (note: flightportrait's own `main/idf_component.yml` pulls a `qrcode` component for QR pairing display, but that feature is out of scope for Phase 1 — do not vendor the QR/pairing code path).

If the planner chooses to use `requests` instead of stdlib `urllib.request` for convenience, run `pip index versions requests` and the package-legitimacy gate before adding it — but this is optional and not required to complete Phase 1.

## Architecture Patterns

### System Architecture Diagram

```
┌─────────────────────────────┐
│   XIAO ESP32-S3 Plus + EE02 │
│   (deep sleep, RTC timer)   │
└──────────────┬───────────────┘
               │ wake (timer or button)
               ▼
     ┌───────────────────┐
     │ app_main.c         │  boot → read NVS backoff_n → dispatch
     │ (wake dispatcher)  │
     └─────────┬──────────┘
               │
               ▼
     ┌───────────────────┐        HTTP(S) GET/POST         ┌─────────────────────┐
     │ api_client.c        │◄───────────────────────────────►│ Local Stub Server     │
     │ (poll /device/v1/   │   /setup, /display, /log         │ (byos_server.py or    │
     │  display)            │                                  │  equivalent, laptop)  │
     └─────────┬────────────┘                                 └───────────┬───────────┘
               │ image_hash unchanged? → skip                             │ serves
               │ else download .bin (960,000 bytes)                       │ test .bin image
               ▼                                                          │
     ┌───────────────────┐                                                │
     │ SHA-256 verify +   │◄───────────────────────────────────────────────┘
     │ size check          │
     └─────────┬────────────┘
               │ ok                              │ fail (any step)
               ▼                                 ▼
     ┌───────────────────┐             ┌───────────────────────┐
     │ epd13in3e.c blit   │             │ backoff.c: sleep       │
     │ (dual-chip SPI)    │             │ min(2^n × 5min, 6h);   │
     └─────────┬───────────┘             │ n persisted in NVS     │
               │                          └───────────┬────────────┘
               ▼                                       │
     ┌───────────────────────────────────────────────────┐
     │ esp_deep_sleep_start() for sleep_s (from server,   │
     │ or backoff interval on failure)                     │
     └───────────────────────────────────────────────────┘

  ── separate, unwired validation track ──

     ┌──────────────────┐    GET /v2/point/lat/lon/radius   ┌─────────────────────┐
     │ throwaway Python   │─────────────────────────────────►│ adsb.fi /            │
     │ test script         │◄─────────────────────────────────│ airplanes.live        │
     │ (laptop)            │        JSON aircraft array         │ (public, no auth)     │
     └──────────────────┘                                    └─────────────────────┘
               │  if coverage insufficient near runway 3 (fallback path)
               ▼
     ┌──────────────────┐    1090 MHz     ┌───────────────────┐
     │ RTL-SDR dongle +   │◄───────────────│ real aircraft       │
     │ readsb/dump1090     │   ADS-B RF     │ transiting runway 3 │
     │ (laptop or Pi)      │                 └───────────────────┘
     └──────────────────┘
```

### Recommended Project Structure
```
firmware/
├── main/
│   ├── app_main.c        # wake dispatch → poll-or-fail → deep sleep (vendor from flightportrait, strip provisioning/OTA)
│   ├── api_client.c/.h    # implements POST /setup, GET /display (§ Code Examples)
│   ├── backoff.c/.h       # min(2^n * 5min, 6h) — vendor as-is from flightportrait, it's a pure function
│   ├── epd13in3e.c/.h     # native ESP-IDF dual-chip Spectra 6 driver — vendor as-is from flightportrait
│   ├── panel.c/.h         # blit orchestration + refresh-spacing guard — vendor, simplify guard to Phase-1 needs
│   ├── nvs_schema.h       # trim to: dev_token (hardcoded/simple for Phase 1), image_hash, backoff_n
│   ├── sdkconfig.defaults
│   └── sdkconfig.ee02.defaults   # vendor from flightportrait — UNVERIFIED on real hardware, this phase verifies it
└── CMakeLists.txt

stub-server/
└── byos_server.py         # vendor from flightportrait examples/, stdlib-only, zero setup

adsb-test/
└── query_aggregator.py    # throwaway script: query adsb.fi / airplanes.live near Orly, print results
```

### Pattern 1: Minimal Wake → Poll → Backoff → Sleep Loop
**What:** The canonical device-side state machine flightportrait uses, simplified for Phase 1 (no BLE provisioning, no OTA, no signed re-pair — those are out of scope for DEVICE-03/05).
**When to use:** As the skeleton for Phase 1's `app_main.c`.
**Example:**
```c
// Pattern verified against github.com/flightportrait/frame/main/{app_main.c,backoff.c}
// Source: https://github.com/flightportrait/frame (Apache-2.0)

static RTC_DATA_ATTR bool s_first_boot = true; // optional; NVS is the durable store

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

### Pattern 2: Exponential Backoff Function (verified, exact)
**What:** The precise backoff formula flightportrait ships, directly usable.
**When to use:** DEVICE-03's exponential-backoff success criterion.
**Example:**
```c
// Source: https://github.com/flightportrait/frame/blob/main/main/backoff.c (Apache-2.0), fetched and confirmed verbatim
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

### Pattern 3: ESP-IDF Deep Sleep with Persistent Backoff Counter
**What:** Correct use of NVS (not RTC memory) for a counter that must survive both sleep AND power loss.
**When to use:** Any state (like `backoff_n`) that must persist reliably. RTC memory (`RTC_DATA_ATTR`) only survives deep sleep, not power loss/brownout — NVS is the durable choice flightportrait itself uses for `backoff_n`.
**Example:**
```c
// Source: https://docs.espressif.com/projects/esp-idf/en/stable/esp32s3/api-guides/deep-sleep-stub.html (Espressif official docs)
// RTC_DATA_ATTR persists across deep sleep only:
RTC_DATA_ATTR int wake_count;

// For durability across power loss too, use NVS (as flightportrait's backoff_n does):
esp_sleep_enable_timer_wakeup(sleep_us);
esp_deep_sleep_start();
```

### Pattern 4: Local BYOS Stub Server (plain HTTP, protocol-compliant)
**What:** `docs/PROTOCOL.md` §5 explicitly allows a "hand-set BYOS base" to be plain HTTP (only the compiled-in production default requires strict HTTPS). This means Phase 1's local stub server does **not** need a self-signed TLS certificate to be protocol-compliant.
**When to use:** For the local-only Phase 1 stub server (D-09). Saves significant setup complexity for a non-technical user.
**Example:**
```bash
# Source: https://github.com/flightportrait/frame/blob/main/examples/byos_server.py (Apache-2.0), verified directly
python3 byos_server.py --image test_panel.bin --port 8642 --sleep 300
# Device firmware must be built with its BYOS/api_base override pointed at
# http://<laptop-lan-ip>:8642 rather than the compiled-in HTTPS default.
```
**Caveat for the plan:** the phase's stated success criterion says "HTTPS poll" — decide explicitly whether to (a) accept plain HTTP for Phase 1's local stub (simpler, protocol-compliant via BYOS override, recommended default) or (b) stand up a self-signed cert + trust it in firmware to more faithfully test the HTTPS code path. See Open Questions.

### Anti-Patterns to Avoid
- **Building the full flightportrait feature set for Phase 1:** BLE Security-2 provisioning, OTA, signed re-pair, and factory/production `sdkconfig` profiles are real complexity flightportrait needs for a shipping consumer product — none of it is required by DEVICE-03/DEVICE-05. Hardcode WiFi credentials and the stub server's address/token for Phase 1; wire up provisioning only when a later phase actually needs it.
- **Trusting `sdkconfig.ee02.defaults` pin values as pre-verified:** flightportrait's own maintainers flag this profile "NOT YET CONFIRMED ON LIVE HARDWARE." Treat Phase 1's first successful blit on real EE02 hardware as the actual verification event, not a formality.
- **Inheriting E1004 button/pin assignments on the EE02 board:** 6 of 8 panel pins differ between the two boards, and `CS_M`/`EN` collide with UART0 RX/TX on the EE02 specifically (must use USB-Serial/JTAG console, not UART console, on this board).
- **Assuming datasheet deep-sleep current for planning:** the ESP32-S3 SoC's bare-die figure is not representative of what a dev board with a USB-UART bridge, power LED, and always-on LDO actually draws in practice — measure on the real board (D-07).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| E-paper dual-chip panel driver | A custom SPI blit routine for the 13.3" Spectra 6 from the Waveshare datasheet | `flightportrait/frame`'s `main/epd13in3e.c/.h` (Apache-2.0) | Already ported from the Waveshare reference driver, already ESP-IDF-shaped, already Kconfig-pin-configurable for exactly this panel |
| Exponential backoff timing | A bespoke backoff scheme | `flightportrait/frame`'s `main/backoff.c` (`min(2^n × 5min, 6h)`) | Trivial function, but reusing the exact reference formula keeps Phase 1's behavior directly comparable to the reference architecture the whole project is modeled on |
| Local test/stub HTTP server for the poll protocol | A Flask/FastAPI app implementing `/setup`, `/display`, `/log` from scratch | `flightportrait/frame`'s `examples/byos_server.py` | Zero-dependency, already implements bearer tokens, hash-based no-change responses, and the exact response shape firmware will expect |
| SHA-256 download verification | Custom checksum logic | ESP-IDF's `mbedtls` SHA-256 API (already what `api_client.c` uses) | Standard, audited crypto primitive; no reason to hand-roll |

**Key insight:** For this phase specifically, the highest-leverage "don't hand-roll" decision is not a library choice but a **scope** choice — flightportrait/frame already solved the exact hard problems this phase needs solved (dual-chip driver, backoff, protocol contract), so Phase 1's real engineering work is *subtraction* (removing production-only complexity) and *verification* (does the EE02 profile actually work on real hardware), not building any of this from zero.

## Common Pitfalls

### Pitfall 1: EE02 board profile pin/console conflicts
**What goes wrong:** Console output over UART silently drives the panel's chip-select or power-enable lines incorrectly (because `CS_M=44`/`EN=43` are UART0 RX/TX on this board), which "reads as an art bug" (per flightportrait's own comments) rather than an obvious wiring failure.
**Why it happens:** The EE02's GPIO pinout reassigns pins that are UART0 on other boards; this is board-specific and easy to inherit incorrectly from E1004 defaults.
**How to avoid:** Use `CONFIG_ESP_CONSOLE_USB_SERIAL_JTAG=y` / `CONFIG_ESP_CONSOLE_UART_DEFAULT=n` as `sdkconfig.ee02.defaults` specifies; never merge E1004 pin values onto the EE02 profile.
**Warning signs:** Panel behaves erratically (partial refresh, wrong colors, no response) specifically when serial console logging is active.

### Pitfall 2: Datasheet deep-sleep current ≠ dev-board deep-sleep current
**What goes wrong:** Planning battery life or wake-interval cadence off ESP32-S3 datasheet figures (single-digit µA class) produces wildly optimistic estimates.
**Why it happens:** Stock development boards add onboard peripherals (USB-UART bridge chip, power LED, voltage regulator with non-trivial quiescent draw) that can add ~1000x over the bare SoC figure.
**How to avoid:** Treat any pre-measurement number as a rough sanity check only; D-07's time-to-depletion test on the actual purchased board is the real source of truth.
**Warning signs:** N/A pre-measurement — this is precisely why Phase 1's success criterion #4 exists.

### Pitfall 3: Assuming general ADS-B "dense coverage" implies runway-level, near-ground coverage
**What goes wrong:** Reading "Paris has dense feeder coverage" as sufficient evidence the aggregator will see aircraft in the specific low-altitude/taxi/rollout segment of runway 3.
**Why it happens:** Aggregator marketing and general coverage maps describe airspace-wide coverage (cruise-altitude overflights are trivial for any nearby feeder to see); near-ground reception specifically depends on whether a contributing feeder has adequate line-of-sight/antenna elevation toward that runway segment, which general coverage claims don't guarantee.
**How to avoid:** Query the aggregator API for a live aircraft known to be on/near runway 3 at test time (e.g. during a scheduled departure window) and check whether it appears with a plausible low altitude/ground-speed value — this is the actual test, not reading coverage-map marketing copy.
**Warning signs:** Aggregator API returns aircraft over Orly generally but nothing (or stale/high-altitude-only) data during a known runway-3 departure/arrival window.

### Pitfall 4: ESP-IDF Python toolchain version mismatch (native install path)
**What goes wrong:** `idf.py --version` succeeds even with a broken Python environment (per flightportrait's own dev notes: "answers happily on a broken env; only a build is evidence the toolchain works"), so a broken environment isn't obvious until deep into a build.
**Why it happens:** flightportrait's own maintainers document that Python 3.9 is missing `ruamel.yaml` for the ESP-IDF tooling and 3.13 is unsupported — 3.12 is the tested version. This machine currently has Python 3.9.6 natively.
**How to avoid:** Prefer the Docker path (`espressif/idf:v5.3.1` image) for building, which sidesteps host Python version entirely; if installing ESP-IDF natively for flashing/monitoring, explicitly use a Python 3.12 environment rather than the system Python 3.9.
**Warning signs:** `idf.py build` fails with an error that does not mention Python in its first line, despite the root cause being the Python environment.

### Pitfall 5: Local stub server HTTPS vs. protocol's plain-HTTP BYOS allowance
**What goes wrong:** Spending Phase 1 setup time generating and trusting a self-signed TLS certificate for the local stub server, when the protocol explicitly permits a plain-HTTP BYOS override — or conversely, building firmware that hardcodes HTTPS-only and can't test against a local plain-HTTP stub at all.
**Why it happens:** The phase's own success-criteria wording says "HTTPS poll," which could be read as requiring TLS even for the throwaway local stub.
**How to avoid:** Decide explicitly (see Open Questions) whether Phase 1 tests the plain-HTTP BYOS path (simpler, still protocol-compliant, recommended given the user's stated preference for low-setup approaches) or the full HTTPS path (more production-representative, tests real TLS/CA-bundle firmware code) — don't let this be an implicit accident.
**Warning signs:** Firmware TLS handshake failures that are actually "the stub server isn't serving HTTPS at all" rather than a real cert problem.

## Code Examples

### ADS-B Aggregator API — position query (adsb.fi)
```bash
# Source: https://github.com/adsbfi/opendata (official README, verified this session)
# Base URL: https://opendata.adsb.fi/api/
# Rate limit: 1 req/sec on public endpoints, no auth required
# Orly-Ville / runway 3 approx coords: 48.7233 N, 2.3794 E — 5 NM radius covers the runway area
curl "https://opendata.adsb.fi/api/v2/lat/48.7233/lon/2.3794/dist/5"
```

### ADS-B Aggregator API — position query (airplanes.live)
```bash
# Source: https://airplanes.live/api-guide/ (official docs, corroborated via WebSearch this session)
# Base URL: https://api.airplanes.live/v2/
# Rate limit: 1 req/sec, no auth/API key required
curl "https://api.airplanes.live/v2/point/48.7233/2.3794/5"
```

### ESP-IDF Deep Sleep Timer Wake
```c
// Source: https://docs.espressif.com/projects/esp-idf/en/stable/esp32s3/api-guides/deep-sleep-stub.html
uint64_t sleep_us = (uint64_t)sleep_s * 1000000ULL;
esp_sleep_enable_timer_wakeup(sleep_us);
esp_deep_sleep_start();
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| dump1090 (original, unmaintained upstream) | readsb (modern fork) | Ongoing community migration, per multiple current setup guides | [CITED: multiple ADS-B community guides] Use readsb if/when the RTL-SDR fallback path is needed; dump1090 is still functional but less actively maintained |
| ADS-B Exchange API Lite | ADS-B Exchange "Community API" (renamed) | 2026-era rebrand referenced across sources this session | [CITED: adsbexchange.com developer hub] Naming/tier structure appears to have changed recently — treat any older documentation/blog post referencing "API Lite" pricing as potentially stale; verify live before committing |

**Deprecated/outdated:**
- Arduino-framework firmware as the primary/shipped path: superseded for this project by D-06 (straight to ESP-IDF) — Arduino remains useful only as flightportrait's own `arduino-sd-demo` no-network bring-up sanity check, not for the actual DEVICE-03/05 work.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | ADS-B Exchange's specific free/hobby-tier rate limit and pricing figures | Standard Stack / Alternatives Considered | If wrong, the planner might budget the wrong service as primary; low risk since D-01/D-02 already say to test multiple aggregators and adsb.fi/airplanes.live were more solidly confirmed as free+no-auth this session |
| A2 | General claim that "Paris/France has dense ADS-B feeder coverage" translates to adequate near-ground coverage specifically at <home-city>/runway 3 | Summary, Common Pitfalls #3 | This is explicitly what Phase 1's success criterion #3 must test empirically — treat this claim as background context only, never as a substitute for the live test |
| A3 | RTL-SDR fallback hardware cost estimate (~€75-100 for dongle+Pi+antenna+microSD) | Code Examples / Don't Hand-Roll context, Standard Stack alternatives | If actual EU pricing/shipping differs meaningfully, D-04's "separate budget line" sizing could be off; low risk since this fallback path may not even be needed depending on Phase 1's aggregator-API test result |
| A4 | Seeed EE02 kit shipping lead time (5-10 business days from one distributor vs. 4-6 weeks pre-sale from another) | Environment Availability / plan sequencing | If the longer lead time applies, D-08's "sequence software-only work first" guidance becomes even more important — moderate risk to phase timeline if not confirmed at order time |
| A5 | ESP32-S3 bare-SoC deep sleep current figures cited in passing (~7µA class) | Common Pitfalls #2 | Low risk — this claim is explicitly framed as unreliable for planning purposes; D-07's real measurement is the load-bearing number, not this figure |

**If this table is empty:** N/A — see entries above. All firmware/protocol/repo-structure claims in this document (Standard Stack Core, Architecture Patterns, Code Examples, Don't Hand-Roll driver/backoff/stub-server rows) were directly verified against the live `github.com/flightportrait/frame` repository via GitHub's raw content and API this session, not assumed from training data — those are tagged `[VERIFIED: github.com/flightportrait/frame]` throughout and are NOT in this table.

## Open Questions

1. **Local stub server: plain HTTP (BYOS override) or self-signed HTTPS for Phase 1?**
   - What we know: `docs/PROTOCOL.md` §5 explicitly permits a plain-HTTP BYOS override for hand-set (non-default) server targets; the phase's stated success criterion says "HTTPS poll."
   - What's unclear: Whether "HTTPS poll" in the phase description is a hard requirement to test the real TLS code path, or just describing the eventual production behavior (which Phase 2+'s real VPS will use).
   - Recommendation: Default to plain HTTP for Phase 1's local stub server (simpler, protocol-compliant, matches the user's stated preference for low-setup approaches) unless the planner/user wants Phase 1 to also validate the TLS/CA-bundle code path early. This should be an explicit planning decision, not an accident.

2. **Which ADS-B aggregator to test first, and in what order?**
   - What we know: adsb.fi and airplanes.live both have directly-confirmed free, no-auth, 1 req/sec REST endpoints with position+radius queries. ADS-B Exchange's free-tier specifics were less consistently documented this session.
   - What's unclear: Which one (if any) has a contributing feeder with adequate near-ground visibility of runway 3 specifically — genuinely unknowable without testing.
   - Recommendation: Test adsb.fi and airplanes.live in parallel first (both are a single unauthenticated `curl` call, effectively free to try both), fall back to investigating ADS-B Exchange's current terms only if both come up short.

3. **Does the EE02 board ship with the battery connector/charging circuit pre-wired for the time-to-depletion test, or does it need assembly?**
   - What we know: CLAUDE.md's existing hardware table describes the EE02 kit as including "a battery connector with an on/off power switch, a built-in charging circuit" (per Seeed's own product page).
   - What's unclear: Exact assembly steps to go from "kit arrives" to "battery-powered device running the wake/poll/sleep loop unattended" — not deeply verified this session, low risk given the kit is explicitly marketed as including this.
   - Recommendation: Budget a small buffer in the plan for unboxing/assembly friction (D-08 already calls for this generally); Seeed's own kit documentation should be the first read once hardware arrives.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| ESP-IDF native toolchain | Firmware build/flash | ✗ | — | Use Docker (`espressif/idf:v5.3.1`) for building; native install still likely needed for USB flashing/monitoring on macOS |
| Docker | Firmware build (via container) | ✓ | 29.4.3 | — |
| Python 3 | Stub server, ADS-B test script | ✓ | 3.9.6 (system) | Sufficient for stdlib-only stub server and test script; if setting up native ESP-IDF Python env, use a 3.12 venv instead per flightportrait's own documented pitfall |
| RTL-SDR dongle + antenna | RTL-SDR fallback path only (D-02) | ✗ (not purchased) | — | N/A — this is the fallback hardware itself; not needed unless the aggregator-API path proves insufficient |
| XIAO ESP32-S3 Plus + EE02 kit | All hands-on firmware/display bring-up | ✗ (not purchased) | — | None — this is the core hardware; D-08 requires ordering before hands-on work starts. Lead time reported 5-10 business days (one distributor) to 4-6 weeks (pre-sale listing elsewhere) — confirm at order time |
| Battery pack (5000-6000mAh, JST-PH) | Battery time-to-depletion test | ✗ (not purchased) | — | None — required for DEVICE-05's success criterion |

**Missing dependencies with no fallback:**
- XIAO ESP32-S3 Plus + EE02 kit and battery pack — must be ordered before any hands-on hardware work; D-08 already requires the plan to sequence software-only work (stub server, ESP-IDF/Docker setup, ADS-B aggregator test) ahead of this.

**Missing dependencies with fallback:**
- Native ESP-IDF toolchain — Docker image covers the build step; flashing/monitoring may still need a native install depending on how Docker Desktop's USB passthrough behaves on this Mac (untested this session — flag as a first-hands-on-day risk, not a blocker to plan around in advance).

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | flightportrait's own `tests/` directory: pure-C contract tests, compile with plain `cc`, no hardware or ESP-IDF required [VERIFIED: github.com/flightportrait/frame repo listing shows `tests/` alongside `main/`] |
| Config file | none — see Wave 0 (Phase 1 has no existing project test infrastructure; this is a greenfield repo) |
| Quick run command | `cc -o /tmp/test_backoff tests/test_backoff.c main/backoff.c && /tmp/test_backoff` (pattern — exact file names in flightportrait's `tests/` were not individually enumerated this session; confirm actual filenames when vendoring) |
| Full suite command | Manual on-hardware run: full wake→poll→display→sleep cycle observed over multiple cycles (this phase is fundamentally a hardware-in-the-loop validation, not a unit-test-covered feature) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DEVICE-03 | Backoff formula correctness (`min(2^n × 5min, 6h)`) | unit | pure-C test against vendored `backoff.c`, pattern from flightportrait's own `tests/` | ❌ Wave 0 — must vendor/write |
| DEVICE-03 | Full wake→poll→download→verify→display→sleep cycle, repeatable | manual/hardware-in-loop | Observe N consecutive cycles against the local stub server; log boot reason/telemetry each wake | ❌ Wave 0 — needs stub server + real hardware, no automation possible for the physical display step |
| DEVICE-03 | Exponential backoff triggers when stub server unreachable (not fixed-interval retry) | manual/hardware-in-loop | Stop the stub server, observe sleep interval growth across consecutive failed wakes (via serial log / X-Boot-Reason on next success) | ❌ Wave 0 — needs real hardware |
| DEVICE-05 | Time-to-depletion battery measurement | manual | Charge full, run unattended, log days-to-dead, compute mAh/cycle | ❌ Wave 0 — needs real hardware + battery pack; not automatable by definition |
| (validation, not a formal REQ) | ADS-B aggregator returns plausible near-ground data for runway 3 | manual/scripted | `curl`/Python script against adsb.fi and airplanes.live during a known departure/arrival window | ❌ Wave 0 — throwaway script, no existing file |

### Sampling Rate
- **Per task commit:** Pure-C `backoff.c` unit test (fast, no hardware).
- **Per wave merge:** Full manual hardware-in-loop cycle observation (this phase is inherently manual/hardware-gated — most "tests" here are physical observations, not CI-automatable).
- **Phase gate:** All 4 phase success criteria (repeatable full cycle, exponential backoff, ADS-B reception validated, measured mAh/cycle) confirmed via direct observation before `/gsd-verify-work`.

### Wave 0 Gaps
- [ ] Vendor/adapt `backoff.c` unit test from flightportrait's `tests/` pattern (pure C, no IDF needed) — confirms the backoff formula in isolation before any hardware exists.
- [ ] `stub-server/byos_server.py` vendored and runnable — needed before firmware can be tested at all.
- [ ] `adsb-test/query_aggregator.py` — throwaway script, needed before the ADS-B validation criterion can be tested; can run before any hardware ships.
- [ ] ESP-IDF build environment confirmed working (Docker build succeeds against a minimal `app_main.c`) — needed before hardware arrives, so build issues surface early rather than blocking hands-on time.

*Given this phase is fundamentally a hardware/physical-world validation spike, most "tests" are direct observation rather than CI-automatable assertions — this is expected and appropriate for a foundation/spike phase, not a gap to force-fit into automation.*

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-------------------|
| V2 Authentication | Partial | Full bearer-token issuance flow (`/setup`) can be simplified/hardcoded for Phase 1's throwaway stub server rather than implementing production-grade provisioning — but the poll (`/display`) call should still send *some* `Authorization: Bearer <token>` header so the firmware code path matches what production will need later |
| V3 Session Management | No | No session concept in this device-initiated poll protocol beyond the long-lived bearer token; N/A |
| V4 Access Control | No | Single-device, single-server, local-network-only for Phase 1; no multi-tenant/access-control surface |
| V5 Input Validation | Yes | Firmware must validate the `/display` JSON response before acting on it: `sleep_s` in range, `image_hash` exactly `sha256:` + 64 lowercase hex, `reset` boolean — this is exactly what flightportrait's own protocol doc specifies firmware must reject on malformed/oversized/truncated fields |
| V6 Cryptography | Yes | SHA-256 verification of the downloaded `.bin` payload before blit (never trust an unverified buffer) — use ESP-IDF's `mbedtls`, never hand-roll a checksum |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|----------------------|
| Corrupted/truncated image download blitted to the panel | Tampering | SHA-256 hash check + exact 960,000-byte size check before blit, per protocol — reject and treat as a failed wake (triggers backoff) rather than blitting a partial/corrupt buffer |
| Device hot-looping against an unreachable server, draining battery | Denial of Service (self-inflicted) | Exponential backoff (`min(2^n × 5min, 6h)`), persisted in NVS so it survives deep sleep — this is DEVICE-03's own success criterion |
| Local stub server running plain HTTP on the LAN | Information Disclosure (low severity, local-network-only) | Acceptable for a throwaway local Phase 1 stub per protocol's own BYOS allowance; not acceptable for production (Phase 2+ VPS uses real HTTPS) — do not carry the plain-HTTP pattern forward past Phase 1 |
| Hardcoded/shared bearer token or WiFi credentials in Phase 1 firmware for expedience | Spoofing (low severity, dev-only) | Acceptable specifically because Phase 1's device only ever talks to a local stub server the developer controls; flag explicitly in code comments as "Phase 1 only, replace before Phase 2+" so it isn't accidentally carried into a later phase's shipped firmware |

## Sources

### Primary (HIGH confidence)
- github.com/flightportrait/frame (repository root, README.md, docs/PROTOCOL.md, main/app_main.c, main/backoff.c, main/epd13in3e.c/.h, main/nvs_schema.h, sdkconfig.ee02.defaults, examples/byos_server.py) — fetched and inspected directly via GitHub raw content and API this session, not via search summary
- docs.espressif.com — ESP-IDF Programming Guide, "Deep-sleep Wake Stubs - ESP32-S3" (stable/latest) — official Espressif documentation, fetched directly

### Secondary (MEDIUM confidence)
- github.com/adsbfi/opendata README.md — official adsb.fi API documentation, fetched directly
- adsbexchange.com developer hub / api-lite pages — official pages, but content across different pages was somewhat inconsistent this session (see Assumptions Log A1)

### Tertiary (LOW confidence)
- airplanes.live API guide/docs — referenced via search, not directly fetched this session; endpoint shape corroborated by adsb.fi's compatible-format claim
- Various RTL-SDR/dump1090/readsb setup guides (Medium, Gigabyte Grove, satsignal.eu, etc.) — WebSearch summary only, general hobbyist consensus rather than a single authoritative source
- General ADS-B low-altitude coverage limitation claims — WebSearch summary of aviation/technical sources, not specific to Orly/runway 3 (Phase 1's own test is the actual answer here)
- Seeed EE02 kit shipping lead-time figures — third-party distributor pages (OpenELAB, shop.app), not Seeed's own current stock page

## Metadata

**Confidence breakdown:**
- Standard stack / firmware architecture: HIGH — verified directly against the live flightportrait/frame repository (code, not just docs/marketing)
- ADS-B aggregator API mechanics (adsb.fi, airplanes.live): MEDIUM — official docs fetched directly, but pricing/terms nuances (ADS-B Exchange especially) were inconsistent across sources
- ADS-B near-ground coverage viability at this specific site: LOW — inherently unknowable without Phase 1's own empirical test; this is expected, not a research gap
- Battery/deep-sleep power figures: LOW — explicitly flagged as unreliable pre-measurement; D-07's real test is the load-bearing source of truth

**Research date:** 2026-08-04
**Valid until:** ~14 days for the flightportrait repo/protocol specifics (active project, could change), ~30 days for ESP-IDF/RTL-SDR general guidance (stable), re-verify ADS-B Exchange pricing/terms at time of actual testing regardless of this document's age (fast-moving/inconsistent this session)
