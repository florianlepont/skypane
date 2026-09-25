# Phase 42: Remote firmware update over the air (OTA), promoted from SEED-009 - Context

**Gathered:** 2026-09-25
**Status:** Ready for planning (execution after Phase 41, see G-41)
**Source:** `.planning/seeds/SEED-009-remote-firmware-update-ota.md`, a read-only scout of the repository on 2026-09-25, and a `/gsd-discuss-phase 42` session with the developer the same day (in French; decisions recorded here in English)

<domain>
## Phase Boundary

A firmware release reaches the frame on the wall without a USB cable. CI builds and signs a release when the developer pushes a tag. The deploy job puts it on the VPS. The developer picks a release in a new companion **Update** tab and confirms. The frame gets the offer at its next wake, shows an "Updating…" screen, downloads the signed image into the inactive OTA slot, and reboots into it on trial. It keeps the image only after one fully successful poll; otherwise the bootloader rolls back. The companion shows the running version, the update state, any rollback and the version history, and a push notification reports success or failure.

**In scope:**
- Firmware: offer parsing, OTA download, signature and hash checks, trial boot, rollback, the "Updating…" screen, reporting the OTA outcome.
- byos: the offer in `/device/v1/display` and serving release images.
- Server/companion: the release registry, the Update tab, notifications.
- CI: tag-triggered signed build, publication through the deploy job, and a check on the Let's Encrypt chain.
- One hardware session.

**Not in this phase:**
- Hardware secure boot, flash encryption, NVS encryption and any eFuse change. D-A1 rejects them; it did not defer them.
- Anti-rollback by security version, which would burn eFuses. The version floor (D-11) is software-only.
- More than one device. The design must not rule it out, but there is no per-device targeting UI (see Deferred).
- Waking the frame early to deliver an update. The offer lands at the next scheduled wake.
</domain>

<decisions>
## Implementation Decisions

### Execution gate (locked)
- **G-41:** no plan runs before Phase 41 is complete on `main`. Phases 35, 36 and 37-11 still change what this phase builds on:
  - `firmware/` comments (35-21);
  - byos request handling and the content-addressed `/img/<sha>.bin` (INT-05);
  - byos `--bind 127.0.0.1`, which forbids new outbound connections from byos (37-11);
  - `server/` and companion module layout (39/40).
- Every plan re-reads the files it edits on the current `main`. The line numbers in this file are from the 2026-09-25 scout.

### Trigger and the companion Update tab
- **D-01:** Nothing ships to the frame without the operator. A published release is only *available*. It becomes *scheduled* when the developer clicks **Install** in the companion. There is no automatic rollout on deploy.
- **D-02:** Firmware management lives in a new **Update** page ("Mise à jour" in French), a third entry in the nav's **Advanced** group: Health, Device, Update.
  - It is added through `NAV_GROUPS` in `companion/layout.py`, so the sidebar, bottom tab bar and dropdown stay one iteration.
  - The mobile bottom tab bar goes from six to seven entries. The UI contract must prove it still fits at 375–390 px, both languages, with measured tap targets. If it does not fit, the fix is a layout decision for the UI phase. Do not move the page back into Health or Device without asking.
- **D-03:** The page shows four things:
  1. The **running version**, as last reported by `X-Fw-Version`.
  2. The **update state** with its timestamp: available / scheduled (at the next wake, with the expected wake time) / in progress / installed / failed.
  3. A visible **rollback warning** when the frame came back on the previous image after a failed trial.
  4. The **version history**: every published release, and which were installed when.
- **D-04:** Install asks for **confirmation**. The dialog names the version and the next expected wake time.
  - The companion has a no-JS contract, so the confirmation must also work without JS (for example a confirmation page after a native POST).
  - With JS it may use the existing `<dialog>` pattern (`panel-lookup-dialog`).
- **D-05:** A scheduled install can be **cancelled** until the device starts downloading. After the device has acknowledged the offer, Cancel is gone.
- **D-06:** **Any published release can be installed**, including an older one: a voluntary downgrade. So the offer rule is "the operator's chosen release differs from the running version", not "newer than". This only works above the floor in D-11.
- **D-07:** Each release in the list shows its version (the tag), date, and the `firmware/` commits since the previous release. These notes are generated in CI from `git log` between tags, with no hand-written text. They are stored with the release.
- **D-08:** A **push notification** fires on success ("Firmware X installed") and on failure ("Update failed, back on Y"). It reuses `server/notify.py` and the configured topic. The French strings go in its `_BODY_FR` table, and the same no-URL-in-logs rules apply.

### Authenticity
- **D-09:** Release images are **signed**, and the frame refuses an unsigned or wrongly signed image, even one served by a compromised VPS.
  - Use ESP-IDF's signed-app verification **without hardware secure boot** (`CONFIG_SECURE_SIGNED_APPS_NO_SECURE_BOOT` / `CONFIG_SECURE_SIGNED_ON_UPDATE_NO_SECURE_BOOT`). **No eFuse is burned** (D-A1).
  - The researcher must confirm for ESP32-S3 on IDF 5.3.1:
    - which signature scheme applies;
    - where the trusted public key comes from in no-secure-boot mode, and what rotating the key would require;
    - that the `factory` partition image carries the same verification;
    - that `esp_https_ota` enforces the check before the boot partition is switched.
  - The first image with this verification must be flashed over **USB, once**: `factory` plus the OTA slot, during the hardware session.
  - SHA-256 and size checks against the offer stay as well. They catch a truncated download before signature verification.
- **D-10:** The private signing key is a **GitHub Actions secret**, and CI signs every release build. An **encrypted offline backup** exists on the developer's Mac or password manager. It is generated once and **never stored on the VPS**. The key-generation and backup procedure is a documented, human-run step, not automation.
- **D-11:** **Software version floor.** The server never offers, and the device never accepts, a release older than the first OTA-capable release. Installing one would end remote updates for good. No eFuse is involved. The floor lives in the firmware (compiled in) and in the server registry.

### When an update applies
- **D-12:** **Battery:** an update is deferred while the existing battery-low alert is active (below 3500 mV, cleared at 3600, `server/poll_loop.py`). There is no new threshold or setting. The device also refuses to start when its own measured `X-Battery-Mv` is below that level, so a stale server view cannot drain it.
- **D-13:** **Quiet hours and display off do not delay it.** A scheduled update goes out at the frame's next wake whatever the mode. The wake cadence itself is unchanged: quiet hours still park the frame until the window ends.
- **D-14:** The e-ink panel shows a dedicated **"Updating…" screen** during the update, **always**, including during quiet hours and with the display switched off. After the update, the next normal poll redraws whatever the current mode calls for: normal view or hold screen. A successful update is followed by a normal redraw. A rollback lands on the previous image, which then polls normally. The screen's wording follows the frame's existing language and visual conventions (Phase 12 hold screens), and the UI phase fixes it.
- **D-15:** **Three attempts.** Each failed attempt counts toward the device's normal backoff. A failed download, signature, hash or trial boot counts as one attempt. After the third, the release is marked **failed**, the offer is withdrawn, the failure notification fires, and the operator decides again in the companion.

### Release pipeline
- **D-16:** A **git tag** creates a release. The pattern is fixed at planning, for example `fw-v1.3.0`.
  - CI builds with `firmware/build.sh`, signs, and records version, SHA-256, size, date and generated notes.
  - Today the repository has **no tags**, and `build.sh` uses `git describe --tags --always --dirty`. Planning must make the tag the reported `PROJECT_VER` for release builds, and keep untagged dev builds distinguishable. Because of D-06, releases are identified and compared by registry entry, not by parsing version strings.
- **D-17:** Signed images reach the VPS **through the existing reviewer-gated deploy job** (`ci.yml` deploy, `deploy/deploy.sh`, `activate.sh`). They go into the state directory (`/opt/skypane/state/firmware/`), outside the per-release code directories, so they survive deploys and the nightly backup covers them. The device downloads only from the VPS: the ISRG-only CA bundle cannot reach GitHub Releases.
- **D-18:** **Every release is kept** (about 1 MB each), which D-06's downgrade needs. There is no pruning.
- **D-19:** **Let's Encrypt chain guard in CI.** A check fails when the certificate chain served by the production host no longer leads to a root in `firmware/main/certs`. The developer then publishes a release with updated certificates before the frame loses TLS.
  - The CA bundle is compiled into the app image, so a normal release is the delivery channel. There is no separate CA-update channel.
  - This check needs the network, so it cannot be a pytest test under the pytest-socket guard. It is a separate CI job or scheduled workflow.

### Claude's Discretion
- The offer's wire format inside `/device/v1/display`. The seed sketch has version, HTTPS URL, SHA-256 and size; add a signature field only if the scheme needs it outside the image.
- How the device reports OTA progress and outcome: a new telemetry header, or `X-Boot-Reason` plus version change. Also where the server stores it. `history_db.device_health` already records `fw_version`, but only indirectly from Caddy logs.
- Release image URL layout. Mirror INT-05's content-addressed `/img/<sha>.bin` (for example `/fw/<sha>.bin`, strict name regex, 404 otherwise) unless research finds a reason not to.
- Where in a wake the download runs relative to the normal poll and blit, and how the wake deadline (`wake_guard.c` / `wake_deadline.c`) is extended for it.
- Whether the "Updating…" screen is drawn on the device (like `fault_screen.c`) or served as an image. The choice must respect D-14 and the energy cost of one full refresh.
- Where the release registry lives (state file or `history_db`). It must use the atomic-write and lock helpers from Phase 36.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### The idea and its history
- `.planning/seeds/SEED-009-remote-firmware-update-ota.md` — feasibility, design sketch, breadcrumbs, the open questions this CONTEXT answers
- `firmware/VENDOR.md` — why upstream OTA was removed (the rows for `api_client.c`/`.h`), why the OTA slots were kept, the rollback note (FW-13), and the CA-bundle note (ISRG-only trust store, no OTA path yet)
- `.planning/audits/2026-09-23-code-audit.md` — FW-07, FW-13, FW-15 (version string), D-A1

### Locked prior decisions
- `.planning/phases/34-firmware-resilience-power-security-cleanup/34-CONTEXT.md` — D-A1 (no eFuse: no flash/NVS encryption, rejected rather than deferred), D-34-01/02 (enrolment secret and re-enrolment), D-34-04 (ISRG X1/X2 only)
- `.planning/phases/36-state-integrity-and-device-protocol/36-CONTEXT.md` — `atomic_write` / `exclusive_lock`, byos's vendor boundary (never imports `server.*`), INT-05 content-addressed image serving, byos request hardening
- `.planning/phases/37-security-and-operations-hardening/37-CONTEXT.md` — release directories and atomic swap (D-09), post-deploy health check (D-10), backups (D-03..D-06), byos binding (37-11)
- `.planning/phases/12-remote-display-on-off-toggle/12-CONTEXT.md` — display-off sleep rule and the hold screens' visual language
- `.planning/research/PITFALLS.md` — updating the CA bundle through OTA, and defined, tested OTA-failure behaviour
- `.claude/skills/sketch-findings-skypane/SKILL.md` — companion design system; navigation groups and bottom tab bar (`references/mobile-navigation.md`)

### Code the phase touches
- `firmware/partitions.csv` — `otadata`, `factory`, `ota_0`/`ota_1` (0x250000 each)
- `firmware/sdkconfig.defaults` — `CONFIG_BOOTLOADER_APP_ROLLBACK_ENABLE=n`, custom CA bundle (`main/certs`)
- `firmware/main/api_client.c` — HTTP session and CA attach, telemetry headers, display-response parsing (the ignored `firmware` field)
- `firmware/main/app_main.c`, `state_machine.c`, `backoff.c`, `sleep_decision.c`, `wake_guard.c`, `wake_deadline.c`, `fault_screen.c`
- `firmware/build.sh`, `firmware/CMakeLists.txt` — `PROJECT_VER` from `git describe`
- `stub-server/byos_server.py` — `/device/v1/display` (`"firmware": None` today), `/img/`, bearer auth, `log_telemetry`
- `server/device_config.py`, `server/history_db.py` (`device_health.fw_version`), `server/notify.py`, `server/poll_loop.py` (battery thresholds)
- `companion/layout.py` (`NAV_GROUPS`), `companion/app.py` (`do_POST`, Origin gate, quick-toggle pattern), `companion/pages/`, `companion/i18n_fr/`
- `.github/workflows/firmware.yml`, `.github/workflows/ci.yml` (deploy job), `deploy/deploy.sh`, `deploy/activate.sh`, `deploy/README.md`

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **The flash layout is already OTA-ready.** 8 MB flash, `ota_0`/`ota_1` of about 2.3 MB each against an image of about 1.05 MB, with `factory` never OTA-written. No partition migration is needed.
- **Telemetry already arrives.** Every request carries `X-Fw-Version` (from `esp_app_get_description()->version`), `X-Battery-Mv`, `X-Boot-Reason` and `X-Rssi`.
- **byos's `/device/v1/display` builds `sleep_s`** from wake interval, display off, battery critical and quiet hours, and returns `"firmware": None`: the hook for the offer.
- **Session and certificates.** `api_client.c` has one reused TLS session per wake with `esp_crt_bundle_attach`. OTA should reuse the same trust store.
- **`server/notify.py`** is a one-attempt push sender, never raises, and already has an EN/FR body table.
- **Operator actions.** Companion operator actions are POSTs behind the Origin/Sec-Fetch-Site gate (`do_POST`); `_handle_quick_toggle` and `_handle_poll_now` are the models.
- **Device fault screen.** `fault_screen.c` already draws a screen on the device without a server image.

### Established Patterns
- **Server decides the cadence.** Quiet hours, display off and battery critical are all server-side through `sleep_s`. The device only sleeps for what it is told, so an offer always lands at a wake boundary.
- **Failures and backoff.** A failure increments `FP_NVS_BACKOFF_N` and follows `backoff.c` (5 min base, doubling, 6 h cap). A 401/403 wipes the token and triggers re-enrolment.
- **Behaviour over source.** Tests assert behaviour, never source text (`companion/test_suite_guards.py`). The pytest-socket guard blocks non-loopback network in tests. Firmware host tests run in `firmware.yml`.
- **No history IDs in comments.** `scripts/check_comment_history.py check` enforces this. Comments are in English and the companion is bilingual.
- **Firmware licensing.** Firmware files are Apache-2.0, derived from FlightPortrait, and every modification is listed in `firmware/VENDOR.md`. Upstream's removed OTA handling (the `fw_*` fields) may be re-derived.

### Integration Points
- byos `/device/v1/display`: add the offer. Serve images from a strict route next to `/img/`.
- `firmware/main/api_client.c` and the wake loop in `app_main.c` / `state_machine.c`.
- `sdkconfig.defaults`: enable rollback and signed-app verification.
- Companion: `NAV_GROUPS` plus a new page module, the FR strings, and new POST routes (install, cancel).
- CI:
  - `firmware.yml` gets a tag-triggered signed build that uploads an artifact (it has neither today, and `contents: read` only);
  - the `ci.yml` deploy job copies it into the state directory;
  - a new network-reaching job or workflow checks the chain.

</code_context>

<specifics>
## Specific Ideas

- "Remote update turns 'unscrew the frame' into 'publish a release'" (seed).
- The main safety reason: if Let's Encrypt moves the chain outside ISRG X1/X2, a frame without OTA cannot be reached to be fixed. D-19's CI guard plus OTA-delivered certificates close that gap.
- The developer chose the "Updating…" screen even at night and with the display off, knowingly: it costs a refresh, and the developer wants to see it.
- The developer questioned the seed's "Health page" placement and asked for a dedicated Update tab under Advanced instead.
- The hardware session proves four things on real glass, each recorded in `hardware/BRINGUP-LOG.md`:
  - a signed update installs;
  - an unsigned or tampered image is refused;
  - a forced crash on a trial image rolls back;
  - recovery from `factory` works.

</specifics>

<deferred>
## Deferred Ideas

- Per-device release targeting and a multi-frame UI: one frame today. The registry should not assume a single device forever, but no UI is built.
- An automatic rollout mode or "auto-install" switch, rejected for now in favour of D-01.
- A separate CA-bundle update channel. Not needed while the bundle is compiled into the app image.

</deferred>

---

*Phase: 42-remote-firmware-update-over-the-air-ota-promoted-from-seed-0*
*Context gathered: 2026-09-25*
