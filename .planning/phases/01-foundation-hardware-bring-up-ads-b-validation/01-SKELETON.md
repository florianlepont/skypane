# Walking Skeleton — Ink Frame

**Phase:** 1 — Foundation: Hardware Bring-up & ADS-B Validation
**Generated:** 2026-08-04

> This document records the architectural decisions Phases 2–4 build on top of without renegotiating. It is the frozen contract that plans `01-02`, `01-03`, `01-05` and `01-06` implement, and the reference those plans read before writing code.

---

## Capability Proven End-to-End

**A battery-capable ESP32-S3 frame wakes on its own timer, joins Wi-Fi, polls a local server over the device protocol, downloads a 960,000-byte panel image, proves the image is intact by SHA-256 and exact byte count, blits it onto the 13.3" Spectra 6 glass, and returns to deep sleep — with no manual intervention inside the cycle.**

That is the thinnest slice that touches every layer the whole product depends on: firmware boot, radio, HTTP client, protocol contract, integrity verification, panel driver, durable state, and deep sleep. Everything Phases 2–4 add is *content* flowing through this pipe, not a change to the pipe.

---

## Architectural Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Firmware framework | ESP-IDF, pinned to **v5.3.1** | Fine-grained sleep-current control is the whole point of a battery-only device, and Phase 1's own success criteria (backoff, deep sleep, measured mAh/cycle) need it. Per **D-06**, no Arduino prototyping detour — starting in Arduino would mean redoing the work before Phase 1 could be called done. 5.3.1 is the version the reference project's own build notes verify. |
| Build environment | Containerised: `espressif/idf:v5.3.1` via `firmware/build.sh` | No host toolchain install, so a broken host Python environment can never silently block hardware day. RESEARCH.md Pitfall 4: `idf.py --version` answers happily on a broken environment and only a real build proves the toolchain works. Image tag is pinned, never `latest`. |
| Flashing | Native host `esptool` (Homebrew), **not** containerised | Docker Desktop on macOS does not reliably pass USB serial devices into containers. Build in the container, flash on the host. Homebrew rather than pip keeps the phase's zero-pip-install property intact. |
| Firmware source strategy | **Vendor** from `flightportrait/frame` at pinned commit `ce3335fc5e566bcc6ccd29966ec39bf5c5318f12` (Apache-2.0) | This is a live, Apache-2.0 ESP-IDF codebase containing a native dual-controller driver for this exact Spectra 6 panel and a board profile already targeting this exact kit. The work is subtraction and configuration, not invention. Pinned to a commit, never a branch. |
| Provenance discipline | `firmware/VENDOR.md` and `stub-server/VENDOR.md` record upstream path, pin, licence, and every local delta | Picking up an upstream fix later must be a diff, not an archaeology project. |
| Board target | Seeed **XIAO ESP32-S3 Plus + EE02** driver board, 13.3" Spectra 6 (1200×1600, 6 colour) | **D-05**. The kit is pre-matched to drive the tricky dual-chip panel and matches the reference hardware, enabling direct driver reuse. |
| Board configuration | `sdkconfig.defaults` + `sdkconfig.ee02.defaults` applied as an **ordered overlay**, never merged | Keeps both board profiles independently reproducible. The EE02 profile is vendored verbatim, comments included — its comments distinguish measured fact from unverified assumption, and that distinction is load-bearing for bring-up. |
| Console routing | **USB Serial/JTAG**; default UART console disabled | On this board the panel's master chip-select and power-enable signals share GPIOs with UART0 RX/TX. A console left on UART drives the panel instead of printing, and the symptom is a wrong-looking picture rather than an error. This is configured away before the panel is ever powered. |
| Device↔server protocol | Three endpoints (`/device/v1/setup`, `/device/v1/display`, `/device/v1/log`) + an image URL, bearer-token auth — see **Protocol Contract** below | The contract is canonical for both sides. Nailing it down with a host-side harness before hardware exists means any later mismatch is a firmware bug rather than an unknown. |
| Transport (Phase 1) | **Plain HTTP** to the local stub; TLS code path stays compiled in and reachable | The protocol explicitly permits a hand-set BYOS base to be plain http, so the local stub needs no certificate — significant setup saved for a developer who has stated limited hardware experience. See **Transport Decision** below for the hard boundary. |
| Server (Phase 1) | Local stdlib-only Python 3 stub on the developer's own laptop | **D-09**. Provisioning the real Hetzner VPS is deferred to Phase 2, when the real rendering pipeline is built — no point paying for or managing a VPS before it is needed. |
| Integrity gate | A buffer reaches the panel only when its length is **exactly 960000 bytes** *and* its SHA-256 matches the server-declared `image_hash` | Untrusted bytes would otherwise stream straight into the panel controllers. The gate is proven by asserting it *rejects* a flipped byte and a one-byte truncation, not merely that it accepts good input. |
| Durable state | **NVS**, one namespace, exactly four keys: bearer token, last displayed image hash, consecutive-failure counter, boot counter | RTC memory survives deep sleep but not power loss or brownout. A failure counter that resets on brownout is exactly the counter that lets a device hot-loop until the battery is flat. A later phase reintroducing provisioning migrates this namespace **in place** rather than renaming it. |
| Failure behaviour | `fp_backoff_seconds(n) = min(2^n × 5 min, 6 h)`, vendored verbatim, counter persisted in NVS | Reusing the upstream curve unchanged keeps this device's failure behaviour directly comparable to the reference architecture, and it is DEVICE-03's stated success criterion. Proven across its whole input domain by pure-C assertions on the laptop. |
| Sleep invariant | **No code path reachable from `app_main` returns without entering deep sleep** | A device that stays awake on an unexpected path is a flat battery. |
| Credentials (Phase 1) | Gitignored `firmware/main/secrets.h` generated from a committed `secrets.example.h` template; four `INK_`-prefixed macros | Phase 1 has no BLE provisioning — the device talks only to a local stub the developer controls. The ignore rule is placed *before* any credential file exists, so no commit window ever opens. Explicitly marked phase-scoped so a later phase does not inherit it. |
| Observability | A fixed, greppable **log-line contract** (five line shapes) emitted every wake | Hardware verification must be a captured log a script can check, not someone's recollection. Frozen in `firmware/VENDOR.md § Log Line Contract` once plan 01-05 lands. |
| Dependency policy | **Zero package-manager installs** for all Phase 1 work | Python is stdlib-only (`urllib.request`, `http.server`, `hashlib`, `json`); C sources are vendored, not pulled from the component registry; the toolchain arrives as a pinned container image. Nothing to audit, no `[ASSUMED]`/`[SUS]`/`[SLOP]` package gate to trip. |
| ADS-B validation | Aggregator API first (adsb.fi + airplanes.live), **deliberately unwired** from the firmware | **D-01/D-02/D-03**. Costs nothing, needs no hardware, no antenna, no legal ambiguity. The RTL-SDR fallback is reached for only if aggregator coverage at the near-ground segment of runway 3 proves insufficient, and per **D-04** its cost is a separate budget line outside the €300 display+compute ceiling. |
| Directory layout | Four top-level workspaces: `firmware/`, `stub-server/`, `adsb-test/`, `hardware/` | See **Directory Layout** below. Each is independently runnable; the ADS-B track shares no code with the device loop, which is what lets both proceed in parallel. |

---

## Directory Layout

```
firmware/                       # ESP-IDF project root
├── CMakeLists.txt              # project(inkframe); PROJECT_VER
├── partitions.csv              # vendored verbatim (OTA slots retained but unused)
├── sdkconfig.defaults          # base profile: ESP32-S3, OPI PSRAM, 12 KiB app_main stack, BT off
├── sdkconfig.ee02.defaults     # EE02 overlay: 8 panel pins, USB Serial/JTAG console
├── build.sh                    # containerised build -> build-ee02/inkframe.bin
├── flash.sh                    # host-side flash + read-back verification (explicit port required)
├── monitor.sh                  # serial capture -> hardware/logs/
├── VENDOR.md                   # upstream pin, vendored-file table, trim log, log-line contract
├── main/
│   ├── app_main.c              # wake dispatch, backoff persistence, deep-sleep entry
│   ├── state_machine.c/.h      # poll -> hash-skip -> download -> verify -> blit -> persist
│   ├── api_client.c/.h         # the three endpoints, telemetry headers, streamed verified download
│   ├── wifi.c/.h               # STA join from secrets.h macros; radio off before sleep
│   ├── backoff.c/.h            # min(2^n x 5min, 6h) — vendored verbatim, pure function
│   ├── api_base.c/.h           # server base URL normaliser — vendored verbatim, pure function
│   ├── epd13in3e.c/.h          # native ESP-IDF dual-controller Spectra 6 driver — vendored verbatim
│   ├── panel.c/.h              # dual chip-select blit orchestration — vendored verbatim
│   ├── panel_guard.c/.h        # minimum refresh spacing; refuses overlapping blits — vendored verbatim
│   ├── Kconfig.projbuild       # API base, hw rev, 8 panel pins, panel guard, 3 retained control pins
│   ├── nvs_schema.h            # namespace + exactly 4 keys
│   ├── secrets.example.h       # committed template
│   └── secrets.h               # GITIGNORED — real credentials, never committed
└── tests/
    ├── test_backoff.c          # pure-C, compiles with plain cc, no ESP-IDF, no hardware
    ├── test_api_base.c
    ├── test_panel_guard.c
    └── run_host_tests.sh       # one command, all hardware-free suites

stub-server/                    # Phase 1 local stub (D-09) — throwaway, never deployed
├── byos_server.py              # vendored @ ce3335fc + a --state-dir flag
├── make_test_panel.py          # deterministic Spectra 6 panel .bin generator
├── test_poll_cycle.py          # end-to-end protocol contract harness; exit 0 == contract holds
├── README.md                   # run commands, LAN targeting, transport decision, telemetry capture
└── VENDOR.md

adsb-test/                      # standalone validation track — NOT wired into the device loop
├── runway3.json                # geofence: center, radius, bbox, altitude ceiling, per-claim source
├── query_aggregator.py         # single-shot geofenced query against both providers
├── sample_window.py            # unattended windowed sampler -> JSONL
├── analyze_samples.py          # viability metrics against a pre-committed threshold
├── RESULTS.md                  # dated verdict + the D-02 fallback decision
└── README.md

hardware/                       # hardware-facing docs and evidence
├── BOM.md                      # priced, budget-checked, order-tracked
├── BRINGUP-LOG.md              # assembly, serial path, flashing, board-profile verification
└── logs/
    └── first-light.log         # the first full wake -> poll -> blit -> sleep, captured
```

**Rule:** the ADS-B track shares no source with the device loop this phase. That separation is what lets the two highest-risk unknowns be de-risked in parallel rather than in series.

---

## Protocol Contract (Frozen)

The contract both sides implement. `stub-server/test_poll_cycle.py` asserts every row of this table before any hardware exists; `firmware/main/api_client.c` implements the client half. The canonical upstream source is `docs/PROTOCOL.md` at the pinned commit — where this table and that document disagree, **the protocol document wins** and the disagreement is recorded in `stub-server/VENDOR.md`.

| Call | Method + path | Auth | Request | Success | Rejections | Client timeout |
|---|---|---|---|---|---|---|
| Enrol | `POST /device/v1/setup` | setup secret | JSON body with `mac`, `hw_rev` | `200` + `device_token`: exactly 64 **lowercase** hex chars | `422` on body missing `mac`; `401` on wrong secret | 15 s |
| Poll | `GET /device/v1/display` | `Authorization: Bearer <device_token>` | Telemetry headers `X-Battery-Mv`, `X-Rssi`, `X-Fw-Version`, `X-Boot-Reason` | `200` + display response (below) | `401` with no Authorization header; `401` with a bearer never issued | 20 s |
| Download | `GET` the returned `image_url` | — | — | Exactly **960000** bytes | — | 30 s |
| Log | `POST /device/v1/log` | `Authorization: Bearer <device_token>` | JSON body with a `logs` array | `200` with `ok` true | — | 15 s |

**Display response field rules** — validated *before any field is copied*:

| Field | Rule |
|---|---|
| `image_hash` | `sha256:` prefix followed by 64 **lowercase** hex characters. Uppercase hex is rejected. |
| `sleep_s` | Integer within `1` … `4294967295`. Zero is rejected. This bound is what stops a hostile or buggy server parking the device for years. |
| `reset` | JSON boolean. |
| `image_url` | Non-empty string whose scheme is `http` or `https`. |
| `firmware` | Null in Phase 1 (OTA is out of scope). |

**Client-side behaviour rules:**

1. **Hash-skip.** If the returned `image_hash` equals the hash stored in NVS, skip the download entirely.
2. **Verify before blit.** A downloaded buffer reaches the panel only when its length is exactly 960000 bytes *and* its SHA-256 digest equals the hex portion of `image_hash`. A mismatch is a failed wake.
3. **Persist after blit.** The new hash is written to NVS **only after a successful blit** — so a blit that never happened cannot cause the next wake to skip.
4. **Deferred ≠ failed.** When the panel guard's refresh spacing has not elapsed, the attempt is *deferred*: the failure counter is untouched, the hash is not recorded, and the device sleeps only until the panel may draw. Treating a deferred draw as a failure would back a perfectly healthy device off for minutes.
5. **Fail → back off.** Any failure increments the NVS failure counter and sleeps `fp_backoff_seconds(n)`, never a fixed retry interval.

---

## Panel Byte Format (Frozen)

| Property | Value |
|---|---|
| Resolution | 1200 × 1600, portrait-native (no rotation applied anywhere) |
| File size | Exactly **960,000** bytes — no header, no compression |
| Row layout | 1600 rows × 600 bytes |
| Packing | Two horizontally adjacent pixels per byte; the **LEFT** pixel occupies the **HIGH** nibble |
| Legal nibble codes | `0x0` black, `0x1` white, `0x2` yellow, `0x3` red, `0x5` blue, `0x6` green — the six Spectra 6 colours. No other value is legal. |
| Controllers | Two, each driving one 600-pixel-wide half. A visible discontinuity down the middle seam indicates a master/slave chip-select problem. |

The Phase 1 test image is a six-band palette pattern (200 px per band, left-to-right: black, white, yellow, red, blue, green), chosen so a correct blit shows six clean stripes while a swapped nibble order or a wrong chip-select split is instantly visible on the glass.

---

## Transport Decision

**Phase 1: plain HTTP.** The device protocol explicitly permits a hand-set BYOS server target to be plain `http` — only the compiled-in production default requires strict HTTPS. The local stub therefore needs no certificate and no trust configuration.

**Accepted consequence:** the bearer token travels in cleartext on the developer's home LAN. The exposure is a throwaway token issued by a stub the developer runs, on their own network, for the duration of one phase.

**Hard boundary:** this allowance is scoped to the Phase 1 throwaway stub and **does not carry forward**. The ESP-TLS and public CA bundle code path stays compiled in and reachable in the firmware, so Phase 2's move to a real HTTPS server on the VPS is a **configuration change, not a code change**. A comment at the firmware's base-URL resolution point records this, `stub-server/README.md` records it on the server side, and it is registered as an accepted risk in the plans' threat models.

---

## Log Line Contract

Five fixed line shapes, emitted with the ESP log tag `inkframe`. Their token spelling is a **contract, not a style choice** — the hardware verification plans grep captured serial logs for these exact shapes. Plan `01-05` implements them and freezes them in `firmware/VENDOR.md § Log Line Contract`.

| When | Line shape |
|---|---|
| Every wake | `wake reason=<rtc\|power-on\|button\|other> boot_count=<n>` |
| Successful poll | `poll ok sleep_s=<n> hash_skip=<0\|1>` |
| Failed poll | `poll fail step=<wifi\|http\|status\|json\|download\|verify\|blit> backoff_n=<n> sleep_s=<n>` |
| Successful blit | `blit ok bytes=960000 sha256_ok=1` |
| Immediately before sleeping | `sleep enter sleep_s=<n>` |

The contract deliberately contains **no credential values** — not the bearer token, not the Wi-Fi password, not the setup secret. A credential appearing in a captured log is a firmware logging defect to fix, not merely something to redact before committing.

---

## Stack Touched in Phase 1

The template's web-app checklist, adapted for an embedded device. Each box is the *thinnest real thing*, not a stub.

- [ ] **Project scaffold** — ESP-IDF project builds a real ESP32-S3 binary from a container; hardware-free C test suite runs with plain `cc` (plan `01-03`)
- [ ] **Routing → protocol endpoints** — all three device endpoints answered by a real local server, asserted by an automated contract harness (plan `01-02`)
- [ ] **Persistence → one real read AND one real write** — NVS boot counter, image hash and failure counter written on one wake and read on the next (plans `01-03`, `01-05`)
- [ ] **UI → the glass** — a verified 960,000-byte image physically blitted onto the panel by the device's own poll cycle (plans `01-05`, `01-06`)
- [ ] **Deployment → documented local full-stack run** — `stub-server/README.md` gives the three commands that generate an image, serve it, and prove the contract; `firmware/build.sh` + `flash.sh` + `monitor.sh` give the device half (plans `01-02`, `01-03`, `01-06`)
- [ ] **Power → deep sleep entered and exited unaided** — the device sleeps for the server-supplied interval and wakes itself (plans `01-05`, `01-06`)

---

## Which Plans Form the Skeleton

| Plan | Wave | Role | In the skeleton? |
|---|---|---|---|
| `01-01` — Bill of materials + place the orders | 1 | Procurement gate. Starts the shipping clock on day one so lead time overlaps the software-only work (**D-08**). Guards the one irreversible mistake in the phase: reversed battery polarity. | **Enabler** — not itself a slice layer, but a hard prerequisite for `01-06` |
| `01-02` — Local stub server + protocol contract harness | 1 | The **server half** of the skeleton. Proves the entire poll contract on the laptop with zero hardware, so a later mismatch is a firmware bug rather than an unknown. | **Yes — core** |
| `01-03` — ESP-IDF scaffold + host-testable firmware behaviours | 1 | The **firmware foundation**. Retires the toolchain risk before hardware day and proves the backoff curve by assertion across its whole domain. | **Yes — core** |
| `01-04` — ADS-B aggregator validation | 1 | A **parallel, independent validation track** (per **D-01/D-02**). Deliberately unwired from the poll loop; validates groundwork for PLANE-03, which Phase 2 delivers. | **No — separate track** |
| `01-05` — Full EE02 firmware: panel stack, network stack, wake loop | 2 | The **device half** of the skeleton. Every clause of DEVICE-03 as a flashable binary, plus the log-line contract that makes the hardware plans verifiable. | **Yes — core** |
| `01-06` — First light on real hardware | 3 | The skeleton **standing up**. Sealed box → picture on the glass, driven end to end by the device polling its own server. Also the verification event for a board profile its own authors marked as never driven on real hardware. | **Yes — core, and the closing event** |

**The skeleton is complete when `01-06`'s six palette bands are correct on the glass** — colour order right, continuous across the two-controller seam, full coverage, portrait orientation, and the console gone quiet after its sleep-entry line.

### Beyond the skeleton — remaining Phase 1 success criteria

The Walking Skeleton satisfies ROADMAP success criterion **1** (a full wake → poll → download → display → deep-sleep cycle against a stub server). Plan `01-04` addresses criterion **3** (plane-detection data-source viability, reframed API-first by D-01/D-03).

Criteria **2** (exponential backoff observed on real hardware when the server is unreachable) and **4** (multiple wake/poll/sleep cycles on battery alone, producing a measured mAh/cycle figure per **D-07**) broaden past the skeleton and are **not covered by plans `01-01`–`01-06`**. The existing plan set repeatedly forward-references two further plans — `01-07` (repeatability + backoff on hardware) and `01-08` (battery time-to-depletion) — which do not currently exist on disk. Both depend on `01-06` and on the battery pack from `01-01`; both consume the log-line contract and the stub server's telemetry stdout stream established here.

---

## Out of Scope (Deferred to Later Slices)

Explicit, so no future phase re-litigates Phase 1's minimalism.

**Firmware features deliberately not vendored or compiled:**
- BLE Security-2 provisioning and its protocol contract — replaced by a gitignored `secrets.h` for a device that talks only to a local stub. A later phase reintroduces real provisioning and migrates the NVS namespace in place.
- OTA firmware update and partition writing — the partition table's OTA slots are retained unchanged (an unused partition costs only flash address space; changing the layout later would be a migration).
- Pairing registration, signature computation, signed re-pair, and the pairing acknowledgement path.
- QR display and its component-registry dependency.
- Remote-reset branch.
- Button handler and view switching — Phase 4 (DEVICE-01). The three EE02 control-pin Kconfig options **are retained without a consumer**, because their values are measured hardware fact from a real key sweep and losing them would mean re-deriving that measurement.
- Low-battery indicator — Phase 4 (DEVICE-04). The telemetry channel it will read (`X-Battery-Mv` on every poll) is live from Phase 1.

**Server and data:**
- Any real rendering — Phase 1 serves a synthetic six-band palette image. Pillow, fonts, layout and 6-colour dithering are Phase 2.
- Real flight or transit data in the device loop — Phase 2 and Phase 3.
- Hetzner VPS provisioning — Phase 2 (**D-09**). The Phase 1 stub is throwaway and never deployed.
- HTTPS certificates for the stub — the TLS code path stays compiled in but unexercised until Phase 2.

**Hardware:**
- Enclosure — no confirmed public EE02 design exists; the panel sits on the bench for validation.
- Solar and wall power — out of scope for v1 by project constraint.
- USB inline power meter — rejected by **D-07** in favour of the simpler time-to-depletion method.
- RTL-SDR dongle, 1090 MHz antenna, and any permanent receiver host — conditional on `01-04`'s verdict (**D-02**), priced on a separate budget line outside the €300 ceiling (**D-04**), and explicitly **not ordered** during Phase 1's procurement plan.

**Process:**
- Updating PROJECT.md and REQUIREMENTS.md's "local ADS-B primary, aggregator fallback" framing — per **D-03** that rewrite happens *after* `01-04` produces a result, not before. Finding out is the point of the phase.

---

## Invariants Later Phases Must Not Renegotiate

1. The **960,000-byte panel format** — size, packing, nibble order, and the six legal colour codes.
2. The **three-endpoint protocol shape** and its display-response field rules.
3. **Verify before blit**: exact byte count *and* SHA-256, with no code path to the panel that bypasses it.
4. **Persist the hash only after a successful blit.**
5. The **NVS namespace** — migrate in place, never rename.
6. The **backoff curve** `min(2^n × 5 min, 6 h)` with its counter in NVS, not RTC memory.
7. **No path out of `app_main` that does not enter deep sleep.**
8. The **log-line contract** — changing a token silently breaks every hardware verification downstream.
9. **Vendored-at-a-pinned-commit** with a VENDOR.md delta log; a re-pin is a deliberate, reviewable act followed by re-running the host tests.
10. The **EE02 console stays on USB Serial/JTAG** — moving it back to UART drives the panel's chip-select and power-enable lines.

---

## Subsequent Slice Plan

Each later phase adds one vertical slice on top of this skeleton without altering its architectural decisions.

**Phase 2 — Plane View, end-to-end slice.**
A user sees flight number, airline and destination for the next plane on runway 3, rendered on the glass. Replaces the local stub with the real rendering server on a Hetzner CX22 VPS, and swaps the plane data source in behind a single module (per `01-04`'s recorded verdict). The device firmware change is expected to be **one macro**: `INK_API_BASE` moves from `http://<laptop-lan-ip>:8642` to the VPS's `https://` base — the TLS path is already compiled in. The panel byte format, protocol contract, integrity gate, NVS schema, backoff curve and log contract are all unchanged. Phase 2 additionally consumes `01-06`'s recorded panel observations (measured refresh duration, actual colour rendition, ghosting) to tune its rendering.

**Phase 3 — RER View, second slice.**
Live next-RER-departure data from the IDFM PRIM platform, plus a "leave by" cue and a disruption banner. A second data source behind the *same* server contract. The device loop is untouched — Phase 3 is entirely server-side plus rendering.

**Phase 4 — View switching, fresh polls, low battery.**
Wires the physical button to switch views, guarantees a fresh poll on every switch, and surfaces a low-battery indicator. This is where the three control-pin Kconfig options retained in Phase 1 finally get a consumer, where the `button` wake reason already present in the log contract starts occurring, and where the `X-Battery-Mv` telemetry header the stub server has been printing since Phase 1 becomes user-visible.
