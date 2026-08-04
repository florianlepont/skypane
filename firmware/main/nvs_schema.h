/* SPDX-FileCopyrightText: 2026 YODE PTE LTD
 * SPDX-License-Identifier: Apache-2.0 */
/* Ink Frame NVS schema — trimmed from flightportrait/frame's own
 * `main/nvs_schema.h` (@ ce3335fc), which defines roughly thirty keys
 * supporting BLE provisioning, possession pairing, OTA build-profile
 * tracking, shipping mode and Security-2/QR state. None of that is
 * compiled into this project this phase (see firmware/VENDOR.md
 * "Deliberately Not Vendored"). This is the COMPLETE list of what an
 * Ink Frame device remembers in Phase 1: the namespace, plus exactly
 * four keys.
 *
 * A later phase reintroducing provisioning MUST migrate this namespace
 * IN PLACE rather than renaming it, mirroring upstream's own warning
 * (docs/PROTOCOL.md §4 at the pinned commit) — an app factory-reset
 * erases this namespace wholesale, so a rename would silently orphan
 * every already-provisioned unit's stored token, image hash and failure
 * count rather than migrating them forward.
 */
#pragma once

#define FP_NVS_NAMESPACE "inkframe"

/* Bearer token returned by POST /device/v1/setup; sent thereafter as
 * `Authorization: Bearer <token>` on every /display and /log call. */
#define FP_NVS_DEVICE_TOKEN "dev_token"

/* Last successfully blitted image hash, "sha256:<hex>" — compared
 * against the server's next `image_hash` to decide the hash-skip. */
#define FP_NVS_IMAGE_HASH "image_hash"

/* Consecutive-failure counter driving fp_backoff_seconds(n). Lives in
 * NVS, not RTC memory, because RTC memory does not survive power loss
 * or a brownout — see firmware/VENDOR.md and 01-PATTERNS.md's
 * Exponential Backoff shared pattern. */
#define FP_NVS_BACKOFF_N "backoff_n"

/* Boot counter — diagnostic only, emitted in the "wake reason=... boot_count=..."
 * log line. */
#define FP_NVS_BOOT_COUNT "boot_count"
