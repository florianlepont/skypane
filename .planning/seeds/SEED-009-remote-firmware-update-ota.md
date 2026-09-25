---
id: SEED-009
status: promoted
promoted_date: 2026-09-25
promoted_to: "Phase 42 (ROADMAP.md)"
planted: 2026-09-24
planted_during: "v1.0 audit remediation (Phases 32–41), after Phase 34 (firmware)"
trigger_when: "Milestone v1.1 — earmarked by the developer on 2026-09-24, together with SEED-007 and SEED-008."
target_milestone: v1.1
scope: large
---

# SEED-009: Update the frame's firmware remotely (OTA), without a USB cable

## Why This Matters

Every firmware change today means taking the frame off the wall and
reflashing it over USB. Phase 34 alone shipped fifteen firmware fixes, and
more are coming (SEED-008's power tuning, any future view). Worse, some
failures can only be fixed by a reflash:

- the custom CA bundle trusts two ISRG roots only; if Let's Encrypt moves
  the VPS's issuing chain outside them, every frame in the field fails
  every TLS handshake and **cannot be reached to be fixed**
  (`firmware/VENDOR.md`, CA-bundle note);
- a bad per-device secret or a server-side token loss that re-enrolment
  cannot recover still needs USB.

Remote update turns "unscrew the frame" into "publish a release".

## Feasibility — what the hardware and the code already give us

Checked against the repository on 2026-09-24:

- **The chip supports it natively.** The ESP32-S3 with ESP-IDF 5.3 has
  `esp_https_ota` (download over HTTPS straight into the inactive app
  slot) and bootloader app rollback.
- **The flash layout is already OTA-ready.** `firmware/partitions.csv`
  (8 MB flash) keeps `otadata`, `factory`, `ota_0` and `ota_1`, each app
  slot 0x250000 (≈ 2.3 MB). The current image is ≈ 1.05 MB
  (`hardware/BRINGUP-LOG.md`, `verify_flash` of `inkframe.bin`), so an
  update fits with more than 50 % headroom. The upstream author kept the
  slots on purpose so that enabling OTA later needs no partition
  migration (`firmware/VENDOR.md`).
- **Upstream had OTA, and it was removed on purpose.** FlightPortrait's
  firmware handled a firmware offer in the `/device/v1/display` response
  (`fw_*` fields) and wrote the partition; Phase 1 trimmed it out
  (`firmware/VENDOR.md`, `api_client.c`/`.h` rows). `api_client.c` still
  ignores a `firmware` field explicitly. Re-deriving from upstream
  (Apache-2.0) is an option.
- **Rollback is off only because nothing uses it yet.** Phase 34
  (plan 34-04) set `CONFIG_BOOTLOADER_APP_ROLLBACK_ENABLE=n` "until this
  project implements OTA"; OTA is exactly what turns it back on.
- **The version string is ready.** FW-15 derives `PROJECT_VER` from
  `git describe` and the device already sends `X-Fw-Version`, so the
  server knows what each frame runs.

## Design sketch (to be challenged at milestone time)

1. **Offer:** `GET /device/v1/display` gains an optional `firmware`
   object — version, HTTPS URL, SHA-256, size — only when the device's
   `X-Fw-Version` is older than the release assigned to it.
2. **Download:** `esp_https_ota` into the inactive slot, over the same
   pinned-CA HTTPS client; size and SHA-256 verified before switching
   the boot partition.
3. **Trial boot:** reboot into the new image with rollback enabled; the
   image marks itself valid (`esp_ota_mark_app_valid_cancel_rollback`)
   only after one fully successful poll. A crash, watchdog reset or
   failed poll rolls back automatically; `factory` stays the last resort.
4. **Authenticity:** HTTPS + hash protects the transport, not the
   origin. Signed app images **without hardware secure boot**
   (`CONFIG_SECURE_SIGNED_APPS_NO_SECURE_BOOT`) verify a signature
   before accepting the update and **burn no eFuse** — consistent with
   the audit's decision D-A1 (no irreversible eFuse changes).
5. **Battery and timing guards:** only above a battery threshold, never
   during quiet hours or with the display off, never mid-blit; a failed
   download counts toward backoff like any other failure.
6. **Server and companion:** CI's `firmware.yml` builds and signs the
   release artifact; the server stores it; the companion's Health page
   shows each frame's running version and lets the operator promote a
   release (and see a rollback if one happened).

## Open questions for the developer

- Automatic update as soon as a release is promoted, or manual approval
  in the companion each time?
- Where does the signing key live (CI secret vs offline on the
  developer's machine), and who can publish a release?
- Is signed-image verification worth its complexity for a one-device
  personal frame, or is HTTPS + pinned CA + SHA-256 enough?
- Battery threshold under which an update is deferred (depends on
  SEED-008's pack decision).
- Should an OTA also be able to ship a new CA bundle ahead of a
  Let's Encrypt chain change (the main safety reason for this seed)?

## Scope Estimate

**Large** — firmware (offer parsing, OTA download, rollback, signing),
server (release storage, offer logic, per-device targeting), companion
(version display, promote/rollback UI), CI (signed artifacts), and one
hardware session to prove update, rollback after a forced crash, and
recovery from `factory`.

## Breadcrumbs

- `firmware/partitions.csv` — OTA slots already present
- `firmware/VENDOR.md` — why OTA was removed, why slots were kept,
  rollback and CA-bundle notes
- `firmware/main/api_client.c` — the ignored `firmware` field
- `firmware/sdkconfig.defaults` — `CONFIG_BOOTLOADER_APP_ROLLBACK_ENABLE=n`
- `stub-server/byos_server.py` — `/device/v1/display`, where the offer goes
- `.github/workflows/firmware.yml` — where a release artifact would be built
- `.planning/audits/2026-09-23-code-audit.md` — D-A1 (no eFuse), FW-07,
  FW-13, FW-15

## Notes

Planted 2026-09-24 at the developer's request ("pouvoir mettre à jour le
firmware à distance si la carte ESP le permet"), for milestone v1.1
alongside SEED-007 and SEED-008.
