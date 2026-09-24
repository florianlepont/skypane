/* SPDX-FileCopyrightText: 2026 YODE PTE LTD
 * SPDX-FileCopyrightText: 2026 Florian Lepont
 * SPDX-License-Identifier: Apache-2.0
 *
 * Modified from FlightPortrait (github.com/flightportrait/frame) for
 * SkyPane; the changes are listed in firmware/VENDOR.md. */
/* SkyPane NVS schema — trimmed from flightportrait/frame's own
 * `main/nvs_schema.h` (@ ce3335fc), which defines roughly thirty keys
 * supporting BLE provisioning, possession pairing, OTA build-profile
 * tracking, shipping mode and Security-2/QR state. None of that is
 * compiled into this project this phase (see firmware/VENDOR.md
 * "Deliberately Not Vendored"). This is the COMPLETE list of what a
 * SkyPane device remembers: four keys in the `skypane` namespace on the
 * default `nvs` partition, plus one more key in that same namespace on
 * its own dedicated `secret` partition.
 *
 * A later phase reintroducing provisioning MUST migrate this namespace
 * IN PLACE rather than renaming it, mirroring upstream's own warning
 * (docs/PROTOCOL.md §4 at the pinned commit) — an app factory-reset
 * erases the default `nvs` partition's `skypane` namespace wholesale, so
 * a rename would silently orphan every already-provisioned unit's stored
 * token, image hash and failure count rather than migrating them
 * forward. The `secret` partition below is untouched by that
 * factory-reset path, and deliberately keeps the same namespace name so
 * a future migration only ever has one namespace to track.
 */
#pragma once

#define FP_NVS_NAMESPACE "skypane"

/* Bearer token returned by POST /device/v1/setup; sent thereafter as
 * `Authorization: Bearer <token>` on every /display and /log call. */
#define FP_NVS_DEVICE_TOKEN "dev_token"

/* Last successfully blitted image hash, "sha256:<hex>" — compared
 * against the server's next `image_hash` to decide the hash-skip. May
 * also hold FP_FAULT_SCREEN_HASH ("fault:no-connection",
 * fault_screen.h) after app_main.c's DEVICE-06 fault screen was drawn
 * (quick task 260924-u7n) — that sentinel is deliberately never shaped
 * like a real "sha256:<64 hex>" server hash, so the first healthy poll
 * after recovery can never mistake it for one and always redraws the
 * real picture. */
#define FP_NVS_IMAGE_HASH "image_hash"

/* Consecutive-failure counter driving fp_backoff_seconds(n). Lives in
 * NVS, not RTC memory, because RTC memory does not survive power loss
 * or a brownout — see firmware/VENDOR.md and 01-PATTERNS.md's
 * Exponential Backoff shared pattern. */
#define FP_NVS_BACKOFF_N "backoff_n"

/* Boot counter — diagnostic only, emitted in the "wake reason=... boot_count=..."
 * log line. */
#define FP_NVS_BOOT_COUNT "boot_count"

/* The enrolment secret's own NVS partition (firmware/partitions.csv),
 * kept apart from the default `nvs` partition above so re-provisioning a
 * device (firmware/provision.sh) can never touch the token, image hash
 * or backoff keys, and so an application factory-reset of the default
 * partition can never erase the one copy of this device's credential.
 * The application only ever reads this key — it never writes or erases
 * the `secret` partition (enrol_secret.c). */
#define FP_NVS_SECRET_PARTITION "secret"
#define FP_NVS_ENROL_SECRET "enrol_secret"
