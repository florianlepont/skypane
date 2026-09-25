# Phase 42: Remote firmware update over the air (OTA) - Research

**Researched:** 2026-09-25
**Domain:** ESP32-S3 OTA (esp_https_ota, bootloader app rollback, signed-app verification without secure boot), CI signing/release pipeline, byos/companion offer surface
**Confidence:** MEDIUM-HIGH overall; HIGH on rollback/deep-sleep mechanics and upstream OTA re-derivation, MEDIUM on signed-app-without-secure-boot specifics (official docs are terse), LOW on exact CI/companion wiring since Phases 35-40 (G-41 dependency) are not yet on `main`.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Execution gate:** G-41 - no plan for this phase runs before Phase 41 is complete on `main`. Phases 35, 36 and 37-11 still change what this phase builds on (firmware comments, byos content-addressed `/img/<sha>.bin`, byos `--bind 127.0.0.1` / no outbound, `server/`/companion module layout). Every plan re-reads the files it edits on the current `main`; this research's line numbers/paths are from the 2026-09-25 scout and (see "Verified against current `main`" below) several referenced constructs (`atomic_write`, `exclusive_lock`, content-addressed `/img/<sha>.bin`, `--bind 127.0.0.1`) **do not exist on `main` yet**.

- **D-01:** Nothing ships to the frame without the operator. A published release is only *available*; it becomes *scheduled* only when the developer clicks Install. No automatic rollout.
- **D-02:** Firmware management lives in a new **Update** page ("Mise à jour"), a third entry in the nav's Advanced group (Health, Device, Update), added through `NAV_GROUPS` in `companion/layout.py`. The mobile bottom tab bar's "More" sheet grows from two Advanced links to three; the UI contract must prove it still fits at 375-390px, both languages, measured tap targets.
- **D-03:** The Update page shows: running version (`X-Fw-Version`); update state + timestamp (available/scheduled/in progress/installed/failed); a rollback warning when the frame came back on the previous image after a failed trial; version history (every published release, which were installed when).
- **D-04:** Install asks for confirmation, naming the version and the next expected wake time; must work without JS (native POST + confirmation page) and may use the existing `<dialog>` pattern (`panel-lookup-dialog`) with JS.
- **D-05:** A scheduled install can be cancelled until the device starts downloading; Cancel disappears once the device has acknowledged the offer.
- **D-06:** Any published release can be installed, including an older one (voluntary downgrade) - offer rule is "chosen release differs from running version", not "newer than". Only above the version floor (D-11).
- **D-07:** Each release shows version (tag), date, and `firmware/` commits since the previous release, generated in CI from `git log` between tags, no hand-written text.
- **D-08:** A push notification fires on success ("Firmware X installed") and failure ("Update failed, back on Y"), reusing `server/notify.py` and its topic; French strings go in `_BODY_FR`; same no-URL-in-logs rule.
- **D-09:** Release images are signed; the frame refuses an unsigned/wrongly-signed image even from a compromised VPS. Use ESP-IDF signed-app verification **without hardware secure boot** (`CONFIG_SECURE_SIGNED_APPS_NO_SECURE_BOOT` / `CONFIG_SECURE_SIGNED_ON_UPDATE_NO_SECURE_BOOT`). **No eFuse burned** (D-A1). The first image with this verification must be flashed over USB once (factory + the OTA slot) during the hardware session. SHA-256 and size checks against the offer stay too, to catch a truncated download before signature verification.
- **D-10:** The private signing key is a GitHub Actions secret; CI signs every release build. An encrypted offline backup exists on the developer's Mac or password manager, generated once, never stored on the VPS. Key-generation/backup is a documented, human-run step, not automation.
- **D-11:** Software version floor - the server never offers, and the device never accepts, a release older than the first OTA-capable release. No eFuse involved; the floor is compiled into firmware and lives in the server registry.
- **D-12:** An update is deferred while the existing battery-low alert is active (below 3500 mV, cleared at 3600, `server/poll_loop.py`) - no new threshold. The device also refuses to start an update when its own measured `X-Battery-Mv` is below that level.
- **D-13:** Quiet hours and display-off do not delay the update; it goes out at the frame's next wake regardless of mode. Wake cadence itself is unchanged.
- **D-14:** A dedicated "Updating..." screen is shown always, including during quiet hours and with the display off. After the update, the next normal poll redraws whatever the current mode calls for. Wording/visual language follows Phase 12 hold-screen conventions; UI phase fixes exact wording.
- **D-15:** Three attempts. Each failed download/signature/hash/trial-boot counts toward normal backoff. After the third, the release is marked failed, the offer withdrawn, failure notification fires, operator decides again.
- **D-16:** A git tag creates a release (pattern fixed at planning, e.g. `fw-v1.3.0`). CI builds with `firmware/build.sh`, signs, records version/SHA-256/size/date/generated notes. Repo has no tags today; `build.sh` uses `git describe --tags --always --dirty`. Planning must make the tag the reported `PROJECT_VER` for release builds and keep untagged dev builds distinguishable. Releases are identified/compared by registry entry, not by parsing version strings (because of D-06).
- **D-17:** Signed images reach the VPS through the existing reviewer-gated deploy job (`ci.yml` deploy, `deploy/deploy.sh`, `activate.sh`), into the state directory (`/opt/skypane/state/firmware/`), outside per-release code directories, surviving deploys and covered by the nightly backup. The device downloads only from the VPS (the ISRG-only CA bundle cannot reach GitHub Releases).
- **D-18:** Every release is kept (~1 MB each); no pruning.
- **D-19:** Let's Encrypt chain guard in CI - a check fails when the production host's certificate chain no longer leads to a root in `firmware/main/certs`. This check needs the network, so it cannot be a pytest test (pytest-socket guard); it is a separate CI job or scheduled workflow. The CA bundle is compiled into the app image, so a normal release is the delivery channel - no separate CA-update channel.

### Claude's Discretion
- The offer's wire format inside `/device/v1/display` (version, HTTPS URL, SHA-256, size; add a signature field only if the scheme needs it outside the image).
- How the device reports OTA progress/outcome (new telemetry header, or `X-Boot-Reason` + version change) and where the server stores it (`history_db.device_health` records `fw_version` today, only indirectly from Caddy logs).
- Release image URL layout - mirror INT-05's content-addressed `/img/<sha>.bin` (e.g. `/fw/<sha>.bin`, strict name regex, 404 otherwise) unless research finds a reason not to.
- Where in a wake the download runs relative to the normal poll/blit, and how the wake deadline (`wake_guard.c`/`wake_deadline.c`) is extended for it.
- Whether the "Updating..." screen is drawn on-device (like `fault_screen.c`) or served as an image, respecting D-14 and the energy cost of one full refresh.
- Where the release registry lives (state file or `history_db`); must use the atomic-write/lock helpers from Phase 36.

### Deferred Ideas (OUT OF SCOPE)
- Per-device release targeting / multi-frame UI. The registry should not assume a single device forever, but no UI is built.
- An automatic rollout mode / "auto-install" switch, rejected in favour of D-01.
- A separate CA-bundle update channel - not needed while the bundle is compiled into the app image.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| OTA-01 | Offer in `/device/v1/display` gated on scheduled+differs+floor+battery-not-low; quiet hours/display-off don't withhold | See "Offer gating" under Architecture Patterns; byos `sleep_s` composition precedent in `byos_server.py` lines ~560-600 |
| OTA-02 | `esp_https_ota` download over ISRG bundle into inactive slot; size+SHA-256 check; signature verified before boot-partition switch | See "esp_https_ota flow" and "Signed app verification" sections; upstream `ota.c` gives a size/hash pattern to extend, not a signature one (upstream has none) |
| OTA-03 | Rollback enabled; new image self-confirms after one successful poll; crash/watchdog/failed poll on trial rolls back; factory is last resort | See "Rollback + deep sleep" pitfall (HIGH confidence, cites upstream's exact call site) |
| OTA-04 | Signed images, no eFuse; CI signs with a GitHub Actions secret; documented human key-gen/backup procedure | See "Signed app verification without secure boot" |
| OTA-05 | Version floor enforced by both server and device; no eFuse | See "Version floor" under Architecture Patterns |
| OTA-06 | Device refuses update below its own measured battery-low level; 3 attempts then failed+withdrawn | See D-12/D-15 mapping in Architecture Patterns and Common Pitfalls (battery race) |
| OTA-07 | "Updating..." screen always, including quiet hours/display-off; normal redraw after | See "Updating screen: on-device vs served" |
| OTA-08 | Companion Update page (nav, states, rollback warning, history); confirm with/without JS; cancel until download starts; any release >= floor installable | See "Companion Update page" and corrected mobile-nav finding |
| OTA-09 | Push notification success/failure via `server/notify.py`, EN/FR | See "Notification integration" |
| OTA-10 | Tag-triggered CI build+sign+notes; reviewer-gated deploy copies into state dir; every release kept | See "Release pipeline (CI)" |
| OTA-11 | Network-reaching CI check that the production cert chain leads to a certs/ root | See "Let's Encrypt chain guard (OTA-11)" |
| OTA-12 | One hardware session proving signed-update install, unsigned/tampered rejection, forced-crash rollback, factory recovery | See "Validation Architecture" hardware session row |
</phase_requirements>

## Summary

FlightPortrait upstream (the vendored base, pinned commit `ce3335fc`) **had a working, simple OTA implementation** that SkyPane's Phase 1 vendoring deliberately excluded (`main/ota.c`/`main/ota.h`, `fp_ota_apply()`/`fp_ota_confirm_if_pending()`, wired into `state_machine.c`/`app_main.c`). This is directly re-derivable — not from this repo's own git history (`git log -S` across all 55 commits found nothing; the removed code was never committed here, it was excluded during the initial vendoring cut) but from GitHub at the pinned commit via `raw.githubusercontent.com` (Apache-2.0, publicly fetchable, confirmed working in this session). Re-derivation gives SkyPane a proven pattern for: apply-before-hash-skip ordering, `esp_ota_get_next_update_partition`/`esp_ota_begin`/`esp_ota_write`/`esp_ota_end`/`esp_ota_set_boot_partition`, and — critically — **exactly where `esp_ota_mark_app_valid_cancel_rollback()` must be called relative to deep sleep** (see the Common Pitfalls section; this is the single highest-risk mechanical detail in the whole phase). Upstream has **no** signed-app verification at all (D-09's signing requirement is new work, not re-derivable), and upstream's OTA-download loop uses a fixed 4 KB static buffer read directly with `esp_http_client_read` rather than `esp_https_ota` — SkyPane should use the higher-level `esp_https_ota` API instead (matches D-02/OTA-02's naming and gives partial-download/img-desc helpers upstream's hand-rolled loop lacks), but should keep upstream's confirm-timing pattern exactly.

Signed-app-verification-without-secure-boot (`CONFIG_SECURE_SIGNED_APPS_NO_SECURE_BOOT`) is confirmed via official ESP-IDF docs to burn **no eFuse** and to use the **same RSA-3072 (or, in v5.x, also ECDSA/ECDSA-P256/P384) signature scheme as Secure Boot V2**, but the trust anchor in no-secure-boot mode is *the public key embedded in the signature block of the currently-running app itself* — not a hardware-locked key. This has a real implication CONTEXT.md's own questions anticipated: a compromised VPS serving an image signed with a *different* keypair than the one baked into the currently-flashed app will be rejected (good — this is the D-09 guarantee), but the mechanism is trust-on-first-flash, not trust-on-hardware: the security boundary is "whatever public key shipped in the first USB-flashed image," which is exactly what D-09 already anticipates by requiring a USB flash of the first signed image. Key rotation is possible only via a new signed release (the new key's public half ships inside the new signed image) but the very first rotation-capable release must itself be signed by the *current* key or accepted over USB - there is no remote path to change the trusted key once the device only trusts images signed by key A.

The other load-bearing finding is deep-sleep/rollback interaction (OTA-03). ESP-IDF's own docs do not explicitly discuss deep sleep, but the mechanism (a deep-sleep wake re-runs the second-stage bootloader, which is where the OTA rollback/pending-verify check lives — unless `CONFIG_BOOTLOADER_SKIP_VALIDATE_IN_DEEP_SLEEP` is set, which this project's sdkconfig does not set) combined with an independently-documented real-world bug (ESPHome shipped exactly this failure mode before 2026.8.0: any device that deep-sleeps before confirming rollback loses the update on the very next wake) means: **the device must call `esp_ota_mark_app_valid_cancel_rollback()` after the first successful post-update poll and before that same wake's `esp_deep_sleep_start()` call — never deferred to "the next wake."** Upstream's own code does exactly this (`app_main.c` calls `fp_ota_confirm_if_pending()` right after a non-failed poll, immediately before `fp_deep_sleep()`), which independently corroborates the mechanism.

**Primary recommendation:** re-derive `ota.c`/`ota.h` from the pinned upstream commit as the mechanical skeleton, replace the hand-rolled download loop with `esp_https_ota_begin/perform/finish` (or the partial-download variant if PSRAM/RAM headroom is tight), add `esp_https_ota_get_img_desc()`-based image-descriptor checks plus the SHA-256/size check already used by `fp_api_download()`'s pattern, enable `CONFIG_BOOTLOADER_APP_ROLLBACK_ENABLE=y` (a bootloader rebuild+USB reflash, done once during the hardware session alongside the first signed image), enable `CONFIG_SECURE_SIGNED_APPS_NO_SECURE_BOOT`+`CONFIG_SECURE_SIGNED_ON_UPDATE_NO_SECURE_BOOT`, sign every CI-built release with `espsecure.py sign_data --version 2` using a GitHub Actions secret key, and call the confirm-rollback function at the exact point upstream does — immediately after the first successful poll following an update, before that wake's deep sleep.

## Verified against current `main` (G-41 dependency check)

Checked directly against the repository at research time (2026-09-25), because CONTEXT.md's own line numbers are scout-dated and several canonical refs point at not-yet-landed phases:

| Referenced construct | Exists on `main` today? | Detail |
|---|---|---|
| `atomic_write` / `exclusive_lock` helpers (Phase 36) | **No** | No hits anywhere in `server/` or `stub-server/` for either name. The release registry (Claude's Discretion) cannot use them yet; if Phase 36 has not landed by the time this phase executes, the plan must either block on it (G-41 already requires this) or the plan-checker must re-verify at plan time. |
| Content-addressed `/img/<sha>.bin` route (INT-05) | **No** | `byos_server.py`'s only `/img/` handling is a generic `self.path.startswith("/img/")` branch (line 598), not a strict `<sha>.bin` regex route. The offer's release-image route (Claude's Discretion) should mirror whatever INT-05 actually ships, re-read at plan time — not this scout's description of it. |
| byos `--bind 127.0.0.1`, no outbound (37-11) | **No** | `byos_server.py` still binds `ThreadingHTTPServer(("0.0.0.0", args.port), Handler)` (line 654). Today byos also does no outbound calls; D-17 requires the release file to be served by byos from the state-dir firmware store (an inbound-only file read, not an outbound call), so this should stay compatible with 37-11 once it lands — but re-verify 37-11's exact wording (some framings of "no outbound" could be read as also restricting local `open()` of files outside its image dir; unlikely, but worth a one-line confirmation at plan time). |
| `server/` and companion module layout used by CONTEXT (39/40) | Partially | `companion/pages/` exists with 5 page modules (`airlines_page.py`, `config_page.py`, `health_page.py`, `history_page.py`, `home_page.py`) but no `device_page.py`/`update_page.py` yet, and `companion/layout.py` still shows `NAV_GROUPS` with only Health/Device in the Advanced group (2 entries, not 3). |
| `CONFIG_BOOTLOADER_APP_ROLLBACK_ENABLE` | `=n` (confirmed, `firmware/sdkconfig.defaults` line 19) | Matches VENDOR.md's own note; OTA-03 requires flipping to `y`, which needs a bootloader rebuild (see Rollback section) and — since a bootloader change is a flash-layout-adjacent change — is exactly the kind of thing that must happen during the one USB session, not remotely. |
| Signed-app Kconfig options (`CONFIG_SECURE_SIGNED_APPS_NO_SECURE_BOOT`, etc.) | Not present | Not referenced anywhere in `firmware/sdkconfig*.defaults` today; this phase adds them from scratch. |

**Implication for planning:** every plan task touching `byos_server.py`, `server/`, or `companion/` should include an explicit "re-read current `main` before editing" step, exactly as G-41 already instructs — this is not new guidance, just a confirmation that the gap is real and material as of this research date.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Offer decision (which release, if any, to advertise) | API/Backend (byos) | Database/Storage (release registry) | byos already composes `sleep_s` from several server-side signals (quiet hours, battery, display-off) at `/device/v1/display`; the offer is one more composed field, decided server-side so the device stays a dumb executor |
| Release storage (binaries, metadata, notes) | Database/Storage (state dir file store, outside git-managed release dirs per D-17) | — | Must survive redeploys (D-17) and the nightly backup; a code-directory location would not |
| Signature verification | Browser/Client tier equivalent = **Device firmware (bootloader + esp_https_ota)** | — | This is the one tier that must never trust the network path; HTTPS+CA protects transport, the embedded public key protects origin |
| Download + flash write | Device firmware | — | `esp_https_ota` writing into the inactive OTA partition; no other tier can perform this |
| Trial-boot / rollback decision | Device firmware (bootloader) | — | Bootloader-driven state machine (`ESP_OTA_IMG_PENDING_VERIFY`); the app only confirms or lets it lapse |
| Release publish / operator approval workflow | Frontend Server equivalent = **Companion (server-rendered, no-JS-first)** | API/Backend (routes) | D-01/D-04/D-05 are all operator-facing state transitions; companion already owns this pattern for quick-toggle actions |
| CI build + sign | Build/CD tier (not in the 5-tier table, but architecturally equivalent to "trusted build" in the API/Backend security boundary) | — | The only place the private key touches automation; never the VPS |
| Notification | API/Backend (`server/notify.py`) | — | Existing one-attempt push sender; reused unchanged in shape |
| CA-chain guard | Build/CD tier (scheduled/network-reaching CI job) | — | Cannot be a pytest test under the pytest-socket guard; must be its own workflow |

## Standard Stack

### Core
| Component | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| ESP-IDF | v5.3.1 (pinned, same container as today) | OTA APIs, bootloader, signed-app verification | Already the project's toolchain; no version change needed for any OTA-01..12 requirement |
| `esp_https_ota` component | Bundled with IDF 5.3.1 | HTTPS download into inactive OTA slot | Higher-level than upstream's hand-rolled `esp_http_client_read` loop; provides `esp_https_ota_get_img_desc`, partial-download, and header-based re-verification for free `[CITED: docs.espressif.com/.../esp_https_ota.html]` |
| `esp_ota_ops` (bootloader_support) | Bundled | `esp_ota_get_next_update_partition`, `esp_ota_mark_app_valid_cancel_rollback`, `esp_ota_mark_app_invalid_rollback_and_reboot`, `esp_ota_get_state_partition` | Existing rollback API; upstream already used it minimally (`fp_ota_confirm_if_pending`) `[VERIFIED: raw.githubusercontent.com fetch of pinned upstream commit]` |
| `espsecure.py` | Bundled with the `espressif/idf:v5.3.1` container | `sign_data --version 2` app image signing | Ships inside ESP-IDF, not a separate registry package — no new install-time supply-chain surface `[CITED: docs.espressif.com secure-boot-v2.html]` |
| mbedtls SHA-256 (`mbedtls/sha256.h`) | Bundled | Streaming hash of the downloaded image for the size/hash check ahead of signature verification | Already used by upstream's `fp_ota_apply` and this project's own `fp_api_download` |

### Supporting
| Component | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `git log <prev-tag>..<tag> -- firmware/` | n/a (git itself) | Generate D-07's release notes in CI | Every tagged release build |
| `openssl s_client -showcerts -connect host:443` | n/a | OTA-11's chain check | Scheduled/on-push CI job, not pytest |
| pytest-playwright (already in the stack) | already pinned in `server/requirements*.txt` | Companion Update-page browser tests | Behaviour-over-source assertions on the new page |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `esp_https_ota` high-level API | Upstream's hand-rolled `esp_http_client_read` loop into `esp_ota_write` (what `fp_ota_apply` actually does) | Upstream's approach is simpler and already proven in this exact codebase's ancestry, but re-implements what `esp_https_ota` already does correctly (partial download, img-desc, standard error codes); recommend `esp_https_ota` for OTA-02's "checks size and SHA-256... before the boot partition is switched" wording, since `esp_https_ota_is_complete_data_received()` + a manual SHA-256 accumulator (mirroring upstream's own accumulator, just fed by `esp_https_ota_perform`'s buffer instead of a raw socket read) gets both the higher-level ergonomics and the exact size/hash gate D-09 requires |
| RSA-3072 signing (`espsecure.py sign_data --version 2` default) | ECDSA (`--version 2 --sign-scheme ...` where IDF supports it) | RSA-3072 is Secure Boot V2's documented default and what the "same scheme as Secure Boot V2" no-secure-boot mode reuses; no evidence in official docs that ECDSA changes any eFuse behavior differently, but RSA-3072 is the better-documented, lower-risk default — use it unless a later research pass finds a concrete reason to prefer ECDSA (e.g. smaller signature/image size, which matters less here given ~1.05 MB images already have >50% partition headroom) |
| A new `/fw/<sha>.bin` byos route | Reusing whatever INT-05's `/img/<sha>.bin` route becomes, parameterized by a `kind=firmware` distinction or a sibling `/fw/` tree under the same content-addressing scheme | Mirroring INT-05 (Claude's Discretion says to, "unless research finds a reason not to") is right, but INT-05 does not exist on `main` yet (see verification table above) — the plan must re-derive the exact route shape from INT-05's actual landed code, not this research's guess |

**Installation:** No new package installs. Every OTA-relevant API/tool (`esp_https_ota`, `esp_ota_ops`, `espsecure.py`) ships inside the already-pinned `espressif/idf:v5.3.1` container image; `openssl` and `git` are already CI runner defaults.

## Package Legitimacy Audit

**Not applicable — this phase installs no new external packages.** All cryptographic/OTA tooling (`espsecure.py`, `esp_https_ota`, `mbedtls`) is bundled inside the already-pinned ESP-IDF v5.3.1 toolchain container; the CI signing key is a GitHub Actions secret (data, not a package); the companion/server side reuses existing stdlib-only dependencies. No `pip install`/`npm install` additions are proposed by this research. The slopcheck/registry-verification gate is skipped for this phase on that basis.

## Architecture Patterns

### System Architecture Diagram

```
                    ┌─────────────────────────────────────────┐
   developer        │  git tag fw-vX.Y.Z  ──▶  firmware.yml   │
   (git push --tags)│  (tag-triggered job, separate from the  │
                    │   existing push/PR build job)            │
                    │    1. build with build.sh, PROJECT_VER=tag│
                    │    2. espsecure.py sign_data (secret key) │
                    │    3. sha256sum + size + git log notes    │
                    │    4. upload-artifact (signed .bin + meta)│
                    └───────────────┬───────────────────────────┘
                                    │ artifact
                                    ▼
                    ┌─────────────────────────────────────────┐
                    │  ci.yml `deploy` job (reviewer-gated)    │
                    │    downloads the firmware.yml artifact,  │
                    │    copies into                            │
                    │    /opt/skypane/state/firmware/<sha>.bin  │
                    │    + registry entry (available)           │
                    └───────────────┬───────────────────────────┘
                                    │
                                    ▼
        ┌───────────────────────────────────────────────────────┐
        │ Companion Update page (operator, D-01..D-08)            │
        │   sees "available" → clicks Install → confirms          │
        │   registry entry → "scheduled"                           │
        └───────────────┬───────────────────────────────────────┘
                         │ next device wake
                         ▼
        ┌───────────────────────────────────────────────────────┐
        │ byos GET /device/v1/display                             │
        │   composes sleep_s (existing) AND now composes          │
        │   "firmware": {version, url, sha256, size} IF            │
        │     scheduled release differs from X-Fw-Version AND      │
        │     release >= floor AND battery-low alert not active    │
        │   (quiet hours / display-off do NOT withhold it)          │
        └───────────────┬───────────────────────────────────────┘
                         │ HTTPS response
                         ▼
        ┌───────────────────────────────────────────────────────┐
        │ Device firmware (state_machine.c, after display parse,  │
        │   BEFORE the hash-skip check — matches upstream)          │
        │   1. own battery check (refuse below low-level)           │
        │   2. draw "Updating…" screen (on-device, fault_screen-    │
        │      style — no server round trip, D-14)                  │
        │   3. esp_https_ota_begin/perform/finish into inactive slot│
        │   4. size + SHA-256 check (accumulated during perform)    │
        │   5. signature verified by esp_ota_end/bootloader          │
        │      (CONFIG_SECURE_SIGNED_ON_UPDATE_NO_SECURE_BOOT)       │
        │   6. esp_ota_set_boot_partition + esp_restart()            │
        │      (NOT deep sleep — a real reboot, matching upstream)   │
        └───────────────┬───────────────────────────────────────┘
                         │ esp_restart() → 2nd-stage bootloader
                         │ sees ESP_OTA_IMG_NEW → sets PENDING_VERIFY
                         ▼
        ┌───────────────────────────────────────────────────────┐
        │ New image boots, runs a full normal wake (Wi-Fi, poll)  │
        │   IF poll succeeds: esp_ota_mark_app_valid_cancel_       │
        │     rollback() BEFORE this wake's esp_deep_sleep_start()  │
        │     (the critical ordering — see Common Pitfalls)          │
        │   IF poll fails / crashes / watchdog resets: next boot     │
        │     (deep-sleep wake OR reset) finds PENDING_VERIFY         │
        │     still set → bootloader auto-rolls-back to the          │
        │     previous slot, marks new image INVALID                 │
        └───────────────┬───────────────────────────────────────┘
                         │ outcome (success/rollback), reported via
                         │ telemetry header on next poll
                         ▼
        ┌───────────────────────────────────────────────────────┐
        │ byos/server records outcome (device_health.fw_version   │
        │   already tracks this; add an explicit outcome field)    │
        │   → registry "installed" or "failed"                     │
        │   → server/notify.py push (D-08)                          │
        │   → Companion Update page reflects state + rollback flag  │
        └───────────────────────────────────────────────────────┘
```

### Recommended integration points (existing files, no new project structure needed)
```
firmware/main/
├── ota.c / ota.h            # NEW — re-derived skeleton from upstream pinned commit,
│                             #   rewritten onto esp_https_ota + signature awareness
├── api_client.c/.h           # parse the new "firmware" object into fp_display_t
│                             #   (currently explicitly ignored, api_client.c:569)
├── state_machine.c           # call fp_ota_apply() before the hash-skip check
├── app_main.c                # call fp_ota_confirm_if_pending() after a successful
│                             #   post-update poll, before THIS wake's deep sleep
├── fault_screen.c            # candidate pattern for the on-device "Updating…" screen
│                             #   (same on-device dither/mask technique, new mask)
└── sdkconfig.defaults        # CONFIG_BOOTLOADER_APP_ROLLBACK_ENABLE=y,
                              #   CONFIG_SECURE_SIGNED_APPS_NO_SECURE_BOOT=y,
                              #   CONFIG_SECURE_SIGNED_ON_UPDATE_NO_SECURE_BOOT=y,
                              #   CONFIG_SECURE_BOOT_BUILD_SIGNED_BINARIES=n (CI signs
                              #   out-of-band, so the private key never touches the
                              #   build system — see D-10)
```

### Pattern 1: Offer gating mirrors existing `sleep_s` composition
**What:** `/device/v1/display`'s `sleep_s` is already composed from wake interval + display-off + battery-critical + quiet-hours overrides (`byos_server.py`, see the module docstring). The firmware offer should be composed the same way: a pure function of (scheduled release, current `X-Fw-Version`, floor, battery-low-alert-active) with no special-casing for quiet hours/display-off (D-13 says they must NOT withhold it — the opposite of how they affect `sleep_s`).
**When to use:** OTA-01.
**Example (pattern, not literal code — INT-05/Phase 36-37 land the actual file layout):**
```python
# Source: pattern only — byos_server.py's existing sleep_s composition
# (module docstring) is the precedent to follow, not literal code to copy.
def firmware_offer(scheduled_release, current_fw_version, floor_version,
                    battery_low_active):
    if battery_low_active:
        return None  # D-12: deferred, not withdrawn — offered again next wake
    if scheduled_release is None:
        return None
    if scheduled_release.version == current_fw_version:
        return None  # already running it
    if version_below_floor(scheduled_release.version, floor_version):
        return None  # D-11, defensive — the registry should already exclude this
    return {
        "version": scheduled_release.version,
        "url": scheduled_release.url,       # content-addressed, mirrors INT-05
        "sha256": scheduled_release.sha256,
        "size": scheduled_release.size,
    }
```

### Pattern 2: OTA apply before hash-skip, exact upstream precedent
**What:** Upstream's `state_machine.c` applies a firmware offer *before* the image-hash-skip check, with a comment: "OTA before hash-skip: a firmware offer must land even on a wake where the art is unchanged." `[VERIFIED: raw.githubusercontent.com/flightportrait/frame/ce3335fc.../main/state_machine.c]`
**When to use:** Answers the "Claude's Discretion" question about where in a wake the download runs.
**Example:**
```c
/* Source: pinned upstream commit ce3335fc, main/state_machine.c
 * (re-derive into SkyPane's own fp_poll_once(), adapted for
 * esp_https_ota instead of the raw esp_http_client_read loop shown here) */
if (disp.has_fw) {
    ESP_LOGI(TAG, "OTA offered: %s", disp.fw_version);
    if (fp_ota_apply(disp.fw_url, disp.fw_sha256) == ESP_OK) {
        esp_restart();   /* NOT deep sleep — reboots straight into the trial image */
    }
    ESP_LOGW(TAG, "OTA failed, continuing this wake normally");
    fp_errlog_record(FP_ERRLOG_ERROR, "ota apply failed");
}
```
SkyPane adaptation notes: (1) insert the D-14 "Updating…" screen draw immediately before `fp_ota_apply()`, since the device commits to a visible-effort update attempt at that point; (2) insert the D-12 battery self-check before even attempting the draw/download; (3) `fp_ota_apply()` itself must gain the signature-verification awareness (D-09) that upstream never had — upstream's version only checks size+SHA-256, never a signature, so this part is new work, not re-derivable.

### Pattern 3: Rollback confirmation, exact upstream precedent (the critical ordering)
**What:** Upstream's `app_main.c` calls `fp_ota_confirm_if_pending()` unconditionally after a poll that did **not** fail, immediately before `fp_deep_sleep(sleep_s)` — and never on the failure path, because `sleep_after_failure(nvs)` (called inside the `if (result == FP_POLL_FAILED)` branch) does not return. `[VERIFIED: raw.githubusercontent.com/flightportrait/frame/ce3335fc.../main/app_main.c lines ~313-330]`
**When to use:** OTA-03's "marks itself valid only after one fully successful poll."
**Example:**
```c
/* Source: pinned upstream commit ce3335fc, main/app_main.c */
uint32_t sleep_s = FALLBACK_SLEEP_S;
fp_poll_result_t result = fp_poll_once(poll_boot_reason(wake, action), &sleep_s);
if (result == FP_POLL_FAILED) {
    sleep_after_failure(nvs);   /* does not return */
}
nvs_set_u8(nvs, FP_NVS_BACKOFF_N, 0);
nvs_commit(nvs);
nvs_close(nvs);
fp_ota_confirm_if_pending();    /* <-- must run before the deep sleep below */
/* ...deferred-sleep adjustment... */
fp_deep_sleep(sleep_s);
```
This ordering is the one place in the whole phase where getting it wrong is silent and catastrophic: if confirmation is deferred to "the next wake" instead of the same wake as the first successful poll, the device will deep-sleep with `ESP_OTA_IMG_PENDING_VERIFY` still set, and the very next wake's boot (which re-runs the 2nd-stage bootloader) will see the still-unconfirmed pending state and roll back a perfectly healthy update. See Common Pitfalls below.

### Anti-Patterns to Avoid
- **Confirming rollback validity on a timer/counter across multiple wakes ("confirm after N successful wakes"):** tempting for extra safety margin, but every additional deep-sleep wake between the trial boot and confirmation is a window where an otherwise-healthy update looks unconfirmed to the bootloader and gets rolled back on that wake's boot. Confirm on the *first* successful poll, same wake, full stop.
- **Signing at compile time on the developer's laptop (`CONFIG_SECURE_BOOT_BUILD_SIGNED_BINARIES=y`):** would require the private key to be present on every machine that builds firmware, contradicting D-10's "never stored on the VPS" and "GitHub Actions secret" model. Keep `CONFIG_SECURE_BOOT_BUILD_SIGNED_BINARIES=n` and sign out-of-band in the CI job with `espsecure.py sign_data`, exactly as the option's own doc text implies ("the private signing key does not need to be present on the build system").
- **Treating `esp_ota_end()`'s `ESP_ERR_OTA_VALIDATE_FAILED` as equivalent to a download/hash failure for backoff counting:** D-15 counts "a failed download, signature, hash or trial boot" as one attempt each toward backoff — but they are different failure classes worth distinguishing in telemetry/logging (mirroring the existing Log Line Contract's per-cause `step=` tokens), even though they all count the same toward the attempt counter.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| HTTPS download into inactive OTA slot with resumability | A custom chunked-read loop (upstream's own `fp_ota_apply` is exactly this — a hand-rolled 4 KB `esp_http_client_read` loop) | `esp_https_ota_begin/perform/finish` (or the single-call `esp_https_ota()`), optionally with `partial_http_download` | Handles buffer sizing, header re-fetch, and completeness checking (`esp_https_ota_is_complete_data_received`) that a hand-rolled loop must reinvent |
| Image authenticity | A custom HMAC-over-HTTPS scheme, or trusting SHA-256 alone as "good enough" (SEED-009's own open question) | ESP-IDF's built-in signed-app verification (`CONFIG_SECURE_SIGNED_APPS_NO_SECURE_BOOT`) | Bootloader-integrated, reuses the same RSA-3072/Secure-Boot-V2 signature format the ESP-IDF toolchain already understands; a custom scheme would need its own verify-before-boot hook, which the bootloader itself is the only code that runs early enough to provide |
| Rollback state tracking | A custom "did the last update work" flag in NVS, checked manually each boot | `esp_ota_get_state_partition` / `ESP_OTA_IMG_PENDING_VERIFY` / `esp_ota_mark_app_valid_cancel_rollback` / `esp_ota_mark_app_invalid_rollback_and_reboot` | This is exactly what `CONFIG_BOOTLOADER_APP_ROLLBACK_ENABLE` exists for; a hand-rolled NVS flag cannot intercept the boot *before* the bad image runs — only the bootloader can |
| Release notes generation | Hand-written changelog entries per release | `git log <prev-tag>..<tag> -- firmware/` in the CI job (D-07 already specifies this) | Explicitly what D-07 asks for — no separate tool needed |

**Key insight:** every OTA-specific "don't hand-roll" item in this phase already has a first-class ESP-IDF mechanism; the actual engineering risk is not in choosing the right primitive but in **sequencing** them correctly across a deep-sleep-cycling device (see Common Pitfalls) and in the parts ESP-IDF deliberately does *not* provide (D-09's signing is opt-in and undocumented in upstream; D-11's version floor is pure application logic ESP-IDF has no opinion on).

## Common Pitfalls

### Pitfall 1: Deep sleep silently rolling back a healthy update (HIGH confidence, HIGH severity)
**What goes wrong:** The device installs an update, reboots into the trial image, but instead of confirming validity in the same wake as its first successful poll, it defers confirmation (e.g. "confirm after a full normal cycle" or "confirm on the wake after next"). It then deep-sleeps. The next wake re-runs the second-stage bootloader (deep sleep is not exempt from bootloader re-validation unless `CONFIG_BOOTLOADER_SKIP_VALIDATE_IN_DEEP_SLEEP` is set — not the case here), which finds the image still in `ESP_OTA_IMG_PENDING_VERIFY` state and rolls it back, even though the update actually worked.
**Why it happens:** It's intuitive to think of deep sleep as "pausing," not "rebooting," so confirmation logic that assumes it can run "sometime soon" rather than "before the very next sleep" looks correct in review but fails on real hardware.
**How to avoid:** Call `esp_ota_mark_app_valid_cancel_rollback()` unconditionally after the first non-failed poll of the freshly-booted trial image, and unconditionally before that same wake's `esp_deep_sleep_start()` call — exactly the ordering upstream's `app_main.c` already uses (see Pattern 3). Do not add any wake-count or time-based delay to this call.
**Warning signs:** A hardware-session test that reboots into a signed update, lets it deep-sleep once, and then finds the device back on the old firmware despite the update having appeared to succeed — this is OTA-12's "forced crash on a trial image rolls back" test category, but this pitfall produces the *same symptom* on a healthy update, which would be a false-positive rollback and must be told apart in the hardware session's log capture (`X-Boot-Reason` / reset reason on the wake immediately after the reboot).
**Confidence:** MEDIUM-HIGH — ESP-IDF's own OTA docs do not explicitly discuss deep sleep (confirmed by direct fetch of the v5.3.1 OTA page), so this is inferred from (a) the documented mechanism that deep sleep wake re-enters the bootloader and (b) an independently-documented real product (ESPHome) that shipped and then fixed exactly this bug. Flag for hardware-session verification (OTA-12) rather than treating as fully proven.

### Pitfall 2: Enabling `CONFIG_BOOTLOADER_APP_ROLLBACK_ENABLE` without reflashing the bootloader
**What goes wrong:** Flipping the Kconfig option and only reflashing the app partition (as a normal OTA would) leaves the *old* bootloader running, which never sets `ESP_OTA_IMG_PENDING_VERIFY` or performs the rollback check — the app's own calls to `esp_ota_mark_app_valid_cancel_rollback()`/`esp_ota_get_state_partition()` become silent no-ops against old bootloader behavior.
**Why it happens:** `CONFIG_BOOTLOADER_APP_ROLLBACK_ENABLE` is a *bootloader* Kconfig option, not an app option — changing it changes the bootloader binary, which only takes effect after a bootloader reflash, which is not something OTA itself can ever do (OTA only writes `ota_0`/`ota_1` app slots, never the bootloader or `factory` region per `partitions.csv`'s own header comment: "Bootloader + factory are NEVER OTA'd").
**How to avoid:** This is exactly why D-09 already requires the first signed image plus rollback-enabled bootloader to be flashed over USB during the one hardware session — confirmed correct by this research. No further mitigation needed beyond making sure the hardware-session plan explicitly reflashes bootloader + `factory` + one OTA slot, not just the app.
**Warning signs:** `esp_ota_get_state_partition()` never returns `ESP_OTA_IMG_PENDING_VERIFY` even right after a fresh OTA — a strong signal the running bootloader predates the Kconfig change.

### Pitfall 3: Signature verification happening later than callers assume
**What goes wrong:** OTA-02 says "verifies the image signature before the boot partition is switched." Official docs show `esp_ota_end()` can return `ESP_ERR_OTA_VALIDATE_FAILED` for a bad signature, and `esp_ota_set_boot_partition()` can independently return the same error — implying re-validation happens at *both* points, not just once. Code that treats a successful `esp_ota_end()` as sufficient proof of a valid signature (and defers the "switch boot partition" step to later, on the assumption it's now safe) could still hit a late rejection.
**Why it happens:** The two-step validate/switch API surface reads as "validate once, then switch," but the docs' wording ("returns X if signature validation failed" on *both* functions) suggests defense-in-depth re-checking rather than a single checkpoint.
**How to avoid:** Treat `esp_ota_end()` and `esp_ota_set_boot_partition()` as a single atomic "commit" step in code — check both return values, and do not draw any user-facing "verified" conclusion (e.g. the Updating screen's outcome, or the telemetry the server records) until both have returned `ESP_OK`. Given `esp_https_ota_finish()` wraps both of these calls internally, using the high-level `esp_https_ota` API (recommended above) makes this pitfall largely moot — one `esp_https_ota_finish()` return code to check, not two.
**Confidence:** MEDIUM — official docs are explicit about the two return points but do not explain *why* both exist; treat as "verify defensively at the one finish() call" rather than building custom logic around the distinction.

### Pitfall 4: Battery-check race between server-side gating and device-side self-check (D-12)
**What goes wrong:** The server withholds the offer while its last-known `X-Battery-Mv` reading is below 3500 mV, but battery readings only arrive once per wake — if the battery drops mid-download (a genuinely higher current draw than an ordinary poll+blit), the device could be well below 3500 mV by the time the trial reboot happens, even though the wake that *started* the update looked fine server-side.
**Why it happens:** D-12's server-side gate is inherently one poll stale; D-12 anticipates this ("so a stale server view cannot drain it") by also requiring the device's own self-check, but that self-check (as written) only naturally happens at the *start* of the wake, before the download begins — not mid-download, when the actual voltage sag from sustained Wi-Fi+flash-write current would show up.
**How to avoid:** Perform the device's own battery self-check both (a) at the start of the wake, before attempting the update at all, and (b) is not strictly needed again mid-download since `esp_https_ota`/the flash-write path itself has no natural checkpoint to re-read the ADC without adding real complexity — the pragmatic mitigation is accepting D-12's own framing (refuse to *start*) and relying on the LiPo's actual internal resistance/capacity margin (documented elsewhere in `hardware/BRINGUP-LOG.md`, not re-verified in this research pass) to make a mid-download brownout unlikely in practice, then let a genuine brownout show up as reset_reason=brownout on the next wake, which the existing reset/backoff machinery already classifies (see VENDOR.md's `reset` token).
**Confidence:** LOW-MEDIUM — this is reasoned from the existing architecture's own stated intent, not independently verified against a real discharge curve for a mid-download load profile. Flag as an assumption for the hardware session to observe, not something to over-engineer in software.

## Code Examples

### Signed-app verification Kconfig (recommended values)
```
# Source: ESP-IDF v5.3.1 docs (security-features-enablement-workflows.html,
# secure-boot-v2.html) — CITED, not directly quoted verbatim (fetch tool
# summarized rather than returned raw text on first attempt; the option
# names below are the well-known, stable ESP-IDF Kconfig symbol names and
# should be confirmed against `idf.py menuconfig`'s search (/) during
# implementation, not taken purely from this research).
CONFIG_SECURE_SIGNED_APPS_NO_SECURE_BOOT=y
CONFIG_SECURE_SIGNED_ON_UPDATE_NO_SECURE_BOOT=y
CONFIG_SECURE_BOOT_BUILD_SIGNED_BINARIES=n   # CI signs out-of-band (D-10)
CONFIG_BOOTLOADER_APP_ROLLBACK_ENABLE=y      # bootloader change — USB reflash required
```

### CI signing step (pattern)
```yaml
# Source: pattern derived from espsecure.py's documented CLI shape
# (docs.espressif.com secure-boot-v2.html) + this repo's existing secret-
# handling convention (ci.yml's env: pattern for DEPLOY_SSH_PRIVATE_KEY,
# never interpolated into run: text — same rule applies to the signing key).
- name: Sign release image
  env:
    FW_SIGNING_KEY: ${{ secrets.FW_SIGNING_KEY }}
  run: |
    printf '%s\n' "$FW_SIGNING_KEY" > /tmp/signing-key.pem
    docker run --rm -v "$PWD/firmware:/project" -v /tmp/signing-key.pem:/key.pem \
      espressif/idf:v5.3.1 \
      espsecure.py sign_data --version 2 --keyfile /key.pem \
      -o /project/build-ee02/skypane-signed.bin /project/build-ee02/skypane.bin
    shred -u /tmp/signing-key.pem
```

### Rollback confirmation call site (re-derived, adapted)
See Pattern 3 above under Architecture Patterns — the literal upstream code is the authoritative example; do not re-derive a different ordering.

## State of the Art

| Old Approach (upstream, pre-Phase-1 vendoring) | Current Approach (this phase) | When Changed | Impact |
|--------------------------------------------------|-------------------------------|---------------|--------|
| Hand-rolled `esp_http_client_read` loop into `esp_ota_write`, no signature check, HTTPS+SHA-256 only | `esp_https_ota` high-level API + signed-app verification (no secure boot, no eFuse) | This phase (OTA-02/OTA-04) | Closes the "compromised VPS serves a valid-looking but malicious image" gap upstream never addressed; SEED-009's own open question ("is signed-image verification worth its complexity...or is HTTPS + pinned CA + SHA-256 enough") is answered by D-09: no, because HTTPS+CA only protects transport, not origin, once the VPS itself is the threat model (SEED-009's stated primary risk) |
| No version floor concept | Software version floor (D-11), enforced in both server registry and compiled firmware | This phase (OTA-05) | Without it, D-06's downgrade feature could strand a device on a pre-OTA firmware with no remote recovery path — the exact failure mode SEED-009 was created to eliminate |

**Deprecated/outdated:** None — this is greenfield OTA work layered onto an unchanged ESP-IDF version; nothing here supersedes a previous SkyPane OTA implementation because none existed.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Deep-sleep wake re-runs the bootloader's rollback/pending-verify check (not exempted the way `CONFIG_BOOTLOADER_SKIP_VALIDATE_IN_DEEP_SLEEP`, unset here, would exempt it) | Common Pitfalls #1, Summary | If wrong (deep sleep is somehow exempt by default), the confirm-before-sleep ordering is still safe but would be over-cautious rather than necessary — low downside either way, but the *opposite* error (assuming exemption when there is none) is the dangerous direction, which is why this research recommends the cautious ordering regardless |
| A2 | `CONFIG_SECURE_SIGNED_APPS_NO_SECURE_BOOT` burns no eFuse, confirmed via a WebFetch summary of ESP-IDF's own v5.3.1 secure-boot-v2 doc page, not a verbatim-quoted source block | Signed app verification, D-09 mapping | If the summary tool mis-extracted this, D-09's hard "no eFuse" requirement could be silently violated; the plan-checker should require a manual `idf.py menuconfig` / `espefuse.py summary` diff check during the hardware session (already implied by OTA-12's checklist) as a second confirmation before flashing the fleet's only device |
| A3 | RSA-3072 (Secure Boot V2's documented default signature algorithm) is the scheme `CONFIG_SECURE_SIGNED_APPS_NO_SECURE_BOOT` reuses, rather than a different/newer default in IDF 5.3.1 specifically | Standard Stack, Alternatives Considered | If IDF 5.3.1 defaults to ECDSA instead, the `espsecure.py sign_data --version 2` invocation shape may need a `--sign-scheme` flag not shown in this research; low risk since the CLI's own `--help` output (available inside the pinned container) is authoritative and should be consulted at implementation time regardless |
| A4 | Upstream's exact `fp_ota_confirm_if_pending()` call site (immediately after a non-failed poll, before that wake's deep sleep) is both correct AND sufficient for SkyPane's needs, with no additional wake-budget/watchdog interaction | Pattern 3, Common Pitfalls #1 | If SkyPane's own `wake_guard.c`/`wake_deadline.c` budget expires between the confirm call and the deep-sleep call on a slow wake, the confirm call itself is cheap (an NVS-adjacent otadata write) and should complete well within budget — flagged here only because this research did not trace `fp_wake_checkpoint()` call-site interaction with a hypothetical `fp_ota_confirm_if_pending()` insertion point in SkyPane's actual (not upstream's) `app_main.c`, which the planner must do against current `main` |
| A5 | Mid-download battery brownout risk (Pitfall 4) is adequately covered by existing reset/backoff classification rather than needing new mitigation | Common Pitfalls #4 | If wrong, a device could enter a brownout-during-flash-write loop that corrupts an OTA slot repeatedly rather than cleanly failing — the hardware session (OTA-12) does not explicitly test this scenario today; consider adding a low-battery-during-download bench test if the discretion allows |

**If this table is empty:** N/A — see rows above; several assumptions here are downstream of tool summarization (WebFetch) rather than raw source text, which the source hierarchy in this document's tooling instructions flags as needing extra care versus a verbatim CITED quote.

## Open Questions

1. **Exact Kconfig symbol set and defaults for IDF 5.3.1's signed-app-without-secure-boot mode**
   - What we know: `CONFIG_SECURE_SIGNED_APPS_NO_SECURE_BOOT` and `CONFIG_SECURE_SIGNED_ON_UPDATE_NO_SECURE_BOOT` are the documented option names (per CONTEXT.md's own OTA-04 wording, cross-checked against WebFetch summaries of the v5.3.1 secure-boot-v2 doc page); the no-secure-boot public key comes from "the signature block of the currently running app."
   - What's unclear: whether IDF 5.3.1 specifically requires any *additional* option (e.g. an explicit `CONFIG_SECURE_BOOT_VERSION` selector, or a minimum `partition_table` flag) beyond the two named options, and the exact `idf.py menuconfig` help text for each.
   - Recommendation: during the first implementation task, run `idf.py menuconfig` inside the pinned container and capture the actual help text + full dependency chain for both options (the container has this offline once the image is pulled) rather than relying further on external doc summaries.

2. **Whether `esp_https_ota`'s partial-download mode is needed given actual heap/PSRAM headroom**
   - What we know: the device has OPI PSRAM (per VENDOR.md), and the framebuffer alone already needs `heap_caps_malloc(FP_IMAGE_BYTES, MALLOC_CAP_SPIRAM|...)` (960,000 bytes) per wake; `esp_https_ota` without partial-download needs its own mbedTLS RX buffer (documented as reducible to 4 KB with partial-download, implying it is larger by default).
   - What's unclear: this research did not measure actual free heap at the point OTA would run (after the framebuffer allocation/free cycle, before or after Wi-Fi teardown) on real hardware.
   - Recommendation: measure free heap during the hardware session (OTA-12) before committing to partial-download vs. default buffering; default buffering is simpler and should be tried first given the ~1.05 MB image already fits comfortably in the OTA partition's headroom.

3. **How the release registry represents "the first OTA-capable release" for the D-11 floor**
   - What we know: D-11 says the floor "lives in the firmware (compiled in) and in the server registry," and D-06 means releases are compared by registry entry, not parsed version strings.
   - What's unclear: the exact registry schema (state file vs. `history_db`) is explicitly Claude's Discretion and blocked on Phase 36's `atomic_write`/`exclusive_lock` helpers landing first (confirmed absent from `main` today).
   - Recommendation: defer the registry schema decision to the plan itself, written against whatever `main` looks like at plan time — this research deliberately does not prescribe a schema given the G-41 gate.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `espressif/idf:v5.3.1` Docker image | Build + sign | ✓ (already pulled by `firmware/build.sh` in existing CI) | v5.3.1 (pinned) | — |
| `espsecure.py` | CI signing (OTA-04) | ✓ (bundled in the above image) | matches IDF 5.3.1 | — |
| `openssl` CLI | OTA-11 chain check | ✓ (standard on `ubuntu-latest` GitHub runners) | runner default | — |
| GitHub Actions secrets store | Signing key (D-10), deploy SSH key (existing) | ✓ (already used for `DEPLOY_SSH_PRIVATE_KEY`/`DEPLOY_HOST_KEY`) | — | — |
| `git` (tags, `git log` for notes) | OTA-10 (D-07, D-16) | ✓ | — | — |
| Real ESP32-S3 EE02 hardware | OTA-12 | Not verifiable from this sandbox — assumed available per "one hardware session" scoping in CONTEXT.md | — | None; OTA-12 cannot be satisfied without it |

**Missing dependencies with no fallback:**
- Real hardware for OTA-12 — inherent to the requirement, already scoped as "one hardware session," not a gap this research can close.

**Missing dependencies with fallback:**
- None identified; every CI/build/sign dependency is already present in the existing pipeline.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + pytest-xdist + pytest-cov (server/companion/byos), `firmware/tests/run_host_tests.sh` (C host tests, no ESP-IDF), pytest-playwright (companion browser tests) |
| Config file | `pyproject.toml` (`[tool.pytest.ini_options]`, `[tool.coverage...]`); `firmware/tests/run_host_tests.sh` (naming-convention discovery, no separate config file) |
| Quick run command | `./scripts/run-all-tests.sh -k ota` (once OTA-named tests exist); `bash firmware/tests/run_host_tests.sh` for firmware-only |
| Full suite command | `./scripts/run-all-tests.sh` (Python side); `bash firmware/tests/run_host_tests.sh` + `bash firmware/build.sh` (firmware side, both already run in `firmware.yml`) |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| OTA-01 | Offer appears/withheld under the right conditions | unit (pure function) + integration (byos response shape) | `pytest stub-server/test_ota_offer.py -x` (or wherever the offer-composition test lands, mirroring `test_poll_cycle.py`'s existing pattern) | ❌ Wave 0 |
| OTA-02 | Size/hash check rejects a truncated/corrupt download | firmware host test (pure C, no ESP-IDF) for the size/hash-check helper function, mirroring `validate.c`'s existing pattern | `bash firmware/tests/run_host_tests.sh` (new `test_ota_verify.c`) | ❌ Wave 0 |
| OTA-03 | Rollback state machine (confirm/never-confirm) | Cannot be a host test (needs the real bootloader) — **hardware-session only** for the actual rollback; a host test can still cover the pure "should I confirm" decision logic if any is extracted into a pure function | `bash firmware/tests/run_host_tests.sh` (logic only) + hardware session (real rollback) | ❌ Wave 0 (logic) / hardware (behavior) |
| OTA-04 | Unsigned/wrongly-signed image refused | **Hardware-session only** — signature verification is bootloader-level and cannot be host-tested without ESP-IDF's real crypto+bootloader stack | Hardware session (OTA-12's own "unsigned or tampered image is refused" bullet) | manual-only, justified: no host-testable seam |
| OTA-05 | Floor enforced server-side and device-side | unit (server registry function) + firmware host test (compiled-in floor comparison, pure C) | `pytest server/test_firmware_registry.py -x`; `bash firmware/tests/run_host_tests.sh` | ❌ Wave 0 (both) |
| OTA-06 | Battery self-refusal; 3-attempt backoff | firmware host test (pure decision function, mirrors `sleep_decision.c`'s existing testable-extraction pattern) + server unit (battery-gate composition) | `bash firmware/tests/run_host_tests.sh`; `pytest server/test_ota_battery_gate.py -x` | ❌ Wave 0 |
| OTA-07 | "Updating…" screen renders in every mode | firmware host test (pure render function, mirrors `fault_screen.c`'s testable design) + Python-port cross-check (mirrors `tools/gen_fault_screen.py`'s existing dual-implementation pattern) if the screen is on-device | `bash firmware/tests/run_host_tests.sh`; `pytest server/test_updating_screen_mask.py -x` (if a mask is generated, mirroring `test_fault_screen_mask.py`) | ❌ Wave 0 |
| OTA-08 | Update page: states, confirm w/wo JS, cancel window, history | pytest-playwright (JS path) + plain-request pytest (no-JS path, mirrors existing companion behaviour-over-source pattern) | `pytest companion/test_update_page.py -x` | ❌ Wave 0 |
| OTA-09 | Notification EN/FR on success/failure | unit (mirrors `server/test_notify.py`'s existing pattern, if present — verify at plan time) | `pytest server/test_notify.py -k ota -x` | Verify existing file at plan time |
| OTA-10 | Tag build → sign → notes → deploy copy | Cannot run in pytest (needs the real CI/tag trigger and GitHub Actions secrets) — verified by a real tagged release during/after the phase, plus a shell-level dry-run test of the notes-generation step (`git log` output shape) | `bash deploy/tests/test_release_notes.sh` (new, mirrors `deploy/tests/test_units.py`'s fake-root pattern for testing shell logic without real infra) | manual-only for the real trigger; ❌ Wave 0 for the notes-generation logic |
| OTA-11 | CI cert-chain guard | Cannot be pytest (pytest-socket guard blocks non-loopback network) — a separate GitHub Actions workflow step is itself the "test"; a local dry-run of the `openssl`+chain-check script against a known-good/known-bad cert pair can be a host-level shell test | New `.github/workflows/firmware-chain-check.yml` (or similar); shell test with fixture certs | ❌ Wave 0 (fixture-based shell test); workflow itself is not pytest |
| OTA-12 | Hardware session: install, reject, rollback, factory recovery | manual-only, hardware | Recorded in `hardware/BRINGUP-LOG.md` per existing convention | manual-only, justified: real bootloader/crypto/battery behavior has no host-testable equivalent |

### Sampling Rate
- **Per task commit:** the narrowest applicable command above (`bash firmware/tests/run_host_tests.sh` for firmware logic changes; `pytest <specific file> -x` for server/companion changes).
- **Per wave merge:** `bash firmware/tests/run_host_tests.sh && bash firmware/build.sh` (firmware) and `./scripts/run-all-tests.sh` (Python) both green.
- **Phase gate:** full suite green (both firmware and Python sides) before `/gsd:verify-work`; OTA-04/OTA-03(rollback)/OTA-12 remain gated on the one hardware session regardless of how green the automated suite is — do not mark those requirements done on automated tests alone.

### Wave 0 Gaps
- [ ] `stub-server/test_ota_offer.py` (or equivalent) — covers OTA-01
- [ ] `firmware/tests/test_ota_verify.c` (new host test, mirrors `test_validate.c`'s pattern) — covers OTA-02, OTA-05 (device side), OTA-06 (device side)
- [ ] `server/test_firmware_registry.py` — covers OTA-05 (server side), OTA-10 (registry writes)
- [ ] `server/test_ota_battery_gate.py` — covers OTA-06 (server side)
- [ ] `companion/test_update_page.py` (Playwright + no-JS) — covers OTA-08
- [ ] Fixture certs + shell test for OTA-11's chain-check logic, independent of the real network-reaching workflow
- [ ] Confirm whether `server/test_notify.py` already exists and its extension pattern for new body strings (OTA-09) — not confirmed in this research pass

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | Indirect | Existing bearer-token device auth (`enrol_secret.h`) is unchanged; OTA rides the same authenticated `/device/v1/display` channel |
| V3 Session Management | No | No new session surface; companion reuses its existing session cookie for the Update page |
| V4 Access Control | Yes | Only the authenticated companion operator (existing companion auth) may schedule/cancel an install; byos must not accept a firmware offer request from an unauthenticated device (already enforced by the existing bearer-token gate) |
| V5 Input Validation | Yes | The offer's `version`/`url`/`sha256`/`size` fields need the same rigor as the existing `image_url`/`image_hash`/`sleep_s` validators in `validate.c` — extend that module, don't inline new checks in `api_client.c` (matches the project's own established pattern) |
| V6 Cryptography (esp. V6.2/V10 Malicious Code / Secure SDLC concerns for signing) | Yes | Never hand-roll signature verification (use ESP-IDF's bootloader-integrated signed-app check); never hand-roll the SHA-256 hash format (reuse `validate.c`'s existing hash-shape validator, extended for the firmware SHA field) |
| V14 Configuration | Yes | `CONFIG_SECURE_BOOT_BUILD_SIGNED_BINARIES=n` is itself a security-relevant configuration choice (keeps the private key off build machines) — document it in `firmware/VENDOR.md`'s Operational notes, matching that file's existing convention for security-relevant sdkconfig choices |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| VPS compromise serves a malicious but well-formed image (SEED-009's own stated primary threat) | Tampering / Spoofing | Signed-app verification (D-09) — the device only trusts images signed by the key baked into its currently-running app; a compromised VPS cannot produce a valid signature without the private key, which never touches the VPS (D-10) |
| Downgrade attack (attacker offers an old, vulnerable-but-validly-signed release) | Tampering | D-11's version floor is the only defense against this for releases *below* the floor; note this is a **soft** floor (no eFuse anti-rollback), so an attacker with access to any validly-signed release above the floor could still offer a downgrade *within* the allowed range — this is explicitly accepted by D-06 (voluntary downgrade is a feature) and D-11 (floor is software-only, "an attacker with real influence over the registry" is out of this phase's threat model, consistent with SEED-009's single-device personal-frame framing) |
| Replay of an old signed offer response | Tampering / Spoofing | The offer rides inside the same bearer-token-authenticated, HTTPS+CA-pinned `/device/v1/display` response the device already trusts for its normal poll; no additional replay-specific mitigation identified as necessary beyond what already protects that endpoint — flag as an open question if a future audit wants a nonce/freshness field on the offer itself |
| Signing key leak (GitHub Actions secret exfiltrated) | Elevation of Privilege | D-10's encrypted offline backup + "never on the VPS" already minimizes blast radius to "attacker can sign a new malicious release," not "attacker can flash arbitrary devices remotely" (still requires convincing the operator to Install it, per D-01's no-auto-rollout rule) — a leaked key's practical mitigation is revocation via a *new* keypair in a new signed release, which requires the *old* key to sign the transition release (see Summary's key-rotation note) or a USB reflash if the old key is fully compromised and untrusted |
| DoS via a bad/oversized offer (malformed `size`/`sha256`, or a URL pointing at an enormous file) | Denial of Service | Extend `validate.c`'s existing bounded-field validators to the firmware offer fields (matches V5 above); the device's existing wake-budget (`wake_guard.c`/`wake_deadline.c`) already caps how long any single wake — including one that starts a doomed download — can run before it self-aborts into failure/backoff, providing a second layer of DoS containment specific to this project's architecture |
| Battery-drain DoS via repeated forced update attempts | Denial of Service (physical/availability) | D-15's three-attempt cap plus normal backoff already bounds this; D-12's battery-low self-refusal is the primary defense against an update attempt itself being the drain vector |

## Sources

### Primary (HIGH confidence)
- `raw.githubusercontent.com/flightportrait/frame/ce3335fc5e566bcc6ccd29966ec39bf5c5318f12/main/{ota.c,ota.h,api_client.c,state_machine.c,app_main.c}` — direct fetch of the pinned upstream commit VENDOR.md itself documents and links; confirms the exact removed OTA implementation and its call-site ordering. `[VERIFIED: direct fetch, this session]`
- This repository's own `firmware/VENDOR.md`, `firmware/partitions.csv`, `firmware/sdkconfig.defaults`, `firmware/main/{wake_guard.h,wake_deadline.h,fault_screen.h}`, `firmware/CMakeLists.txt`, `firmware/build.sh`, `.github/workflows/firmware.yml`, `.github/workflows/ci.yml`, `deploy/{deploy.sh,activate.sh,README.md,Caddyfile}`, `server/{device_config.py,history_db.py,notify.py,poll_loop.py}`, `companion/layout.py`, `stub-server/byos_server.py`, `.claude/skills/sketch-findings-skypane/references/mobile-navigation.md` — read directly this session.

### Secondary (MEDIUM confidence)
- ESP-IDF v5.3.1 docs, `esp32s3/security/secure-boot-v2.html` and `esp32s3/security/security-features-enablement-workflows.html` (fetched via WebFetch summarization, not verbatim quote-extracted) — signed-app-without-secure-boot eFuse behavior, RSA-3072 scheme, `espsecure.py sign_data`, `CONFIG_SECURE_BOOT_BUILD_SIGNED_BINARIES`.
- ESP-IDF v5.3.1 docs, `esp32s3/api-reference/system/ota.html` and `esp32s3/api-reference/system/esp_https_ota.html` (WebFetch summarization) — `CONFIG_BOOTLOADER_APP_ROLLBACK_ENABLE`, `ESP_OTA_IMG_PENDING_VERIFY`, `esp_https_ota_begin/perform/finish`, `partial_http_download`.

### Tertiary (LOW confidence)
- ESPHome documentation/changelog reference (via WebSearch summary, not directly fetched) describing a pre-2026.8.0 bug where deep sleep before confirmation caused every OTA update to roll back — used only as corroborating real-world evidence for the deep-sleep/rollback mechanism inferred from official docs, not as an authoritative ESP-IDF source itself.

## Metadata

**Confidence breakdown:**
- Standard stack (esp_https_ota, esp_ota_ops, espsecure.py): HIGH - these are the project's own already-pinned toolchain, and upstream's re-derivable code independently confirms the rollback API surface.
- Signed-app-without-secure-boot mechanics: MEDIUM - official docs confirmed no-eFuse and the RSA-3072/running-app-public-key trust model, but via WebFetch summarization rather than verbatim quotes; recommend a `idf.py menuconfig` + `espefuse.py summary` cross-check during implementation (Open Question 1, Assumption A2).
- Deep-sleep/rollback interaction: MEDIUM-HIGH - the single most important pitfall in the phase, backed by (a) the documented general mechanism, (b) upstream's own exact call-site precedent, and (c) independent real-world corroboration (ESPHome), but not by an ESP-IDF doc sentence that says "deep sleep" explicitly.
- CI/companion wiring specifics: LOW - Phases 35-40 (G-41 dependency) are confirmed absent from `main` as of this research date; every companion/byos-specific recommendation here is a pattern to follow, not a file/line-number-accurate plan, and must be re-derived against `main` at plan time exactly as G-41 already requires.

**Research date:** 2026-09-25
**Valid until:** 2026-10-25 (30 days) for the ESP-IDF/upstream findings (stable, version-pinned); effectively until G-41 clears for the `main`-dependent findings, since those are gated on other phases landing, not on time passing.
