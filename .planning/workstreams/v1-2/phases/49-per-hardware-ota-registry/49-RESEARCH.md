# Phase 49: Per-Hardware OTA Registry - Research

**Researched:** 2026-10-29
**Domain:** Python stdlib firmware-release registry, ESP-IDF 5.3.1 app image format, OTA signing (RSA-3072 signed apps without hardware secure boot), CI release manifest
**Confidence:** HIGH on code facts and on image parsing (verified against the real signed `fw-v1.0.2` asset); MEDIUM on signing-option tradeoffs (on-device behaviour not hardware-verified); signing decision itself is NOT made here.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Publishing stays on the current channel: tag, CI build, reviewed deploy, `firmware_cli import-dir` on the VPS. The hardware type is added to the release manifest and to `firmware_cli`. No web upload of binaries in this phase: the companion is still guarded only by the shared password until Phases 54-55.
- **D-02:** Scheduling stays on the companion Update page, extended with a hardware-type choice and an independent schedule per type. With one type in production the page must look and behave as today.

### Not discussed (planner and researcher resolve within the success criteria)
- Registry shape per hardware type and the migration of `firmware/registry.json` (the live frame's entries keep working unchanged; a `*.pre-fleet` copy is kept before any rewrite).
- How a binary's app descriptor and chip target are checked against the declared type, and the monotonic build number that refuses downgrades.
- The OTA signing decision (OTA-03). Images are already signed today (RSA-3072, no eFuse, see `firmware/SIGNING.md`). The planner must surface the owner's decision (one key or one per type, any one-time cable flash) as an explicit checkpoint, recorded before any second hardware is provisioned. It is not decided here.

### Claude's Discretion
Module and function names, registry document layout, CLI verb names, test layout, plan split and waves.

### Deferred Ideas (OUT OF SCOPE)
- Direct binary upload from the companion: revisit after Auth0 and roles (Phases 54-55).

Also out of scope per the phase boundary: the combined legacy-frame firmware release (OTA-04, Phase 57), Auth0/roles (54-55), the second hardware itself (58).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| OTA-01 | Publish and schedule firmware per hardware type; a frame is only ever offered a release of its own server-assigned type | Per-type registry slices (Architecture Pattern 1), server-side type resolution with fail-closed rules (Pattern 2), companion per-type Update page (Pattern 6) |
| OTA-02 | Binary whose app descriptor or chip target does not match the declared type is rejected; downgrades refused by a monotonic build number | Stdlib image parser verified on a real signed image (Pattern 3, Code Examples), build-number derivation and publish gate (Pattern 4) |
| OTA-03 | Owner decides whether OTA images are signed, records it (incl. any one-time cable flash) before the second hardware is provisioned; integrity mechanism verified device-side | Signing option matrix (Pattern 5), exact limits of a hardware-free device-side verification test (Validation Architecture) |
</phase_requirements>

## Summary

The registry is one global document (`server/firmware_registry.py:184-192`): one `releases[]`, one `floor_version`, one `schedule`, one `last_outcome`, one `reconciled_seq`. Release identity is the version string alone (`_find_release`, `:457-461`; `publish_release` duplicate check `:568-575`), so two hardware types built from the same `fw-vX.Y.Z` tag would collide. The device-side OTA check is only `project_name == "skypane"` + version equals offer + floor (`firmware/main/ota_policy.c:12,119-137`, `ota.c:67-90`); `esp_https_ota` itself additionally rejects a wrong chip id (ESP-IDF v5.3.1 `esp_ota_verify_chip_id`, see Sources). Today nothing in the offer path knows the hardware type.

Recommended shape: keep `firmware/registry.json` exactly as the **legacy-type document** and add one sibling document per additional hardware type (`firmware/registry.<hardware-key>.json`), all behind the existing single `registry.lock`. Every existing pure function (`compute_offer`, `reconcile`, `update_view`, `acknowledged`) keeps its signature and operates on one document, so the roughly 2,000 lines of existing registry/offer/companion tests stay valid unchanged and cross-type offers are impossible by construction (a type's offer function never sees another type's releases). The device's type is resolved server-side from `fleet.db` (never from a device header), fails closed on anything unknown, and is stamped into the device-report entry so the poll loop and the Update page need no `fleet.db` access.

Image verification needs only `struct` + `hashlib`: I parsed the real signed `fw-v1.0.2` release asset (1,118,208 bytes, sha256 matches `release.json`) and confirmed header magic, chip id `0x0009`, app descriptor at file offset 32 (version at 48, project_name at 80), the appended SHA-256, and the 4 KiB-aligned Secure Boot V2 signature block (digest and CRC32 both match). The monotonic build number should be derived from the **signed descriptor `version` string** (`fw-vMAJOR.MINOR.PATCH`), because the ESP `secure_version` field only exists with anti-rollback, which burns eFuses and is forbidden (`firmware/SIGNING.md:78-82`, `check_production_config.sh`).

**Primary recommendation:** per-type registry documents (legacy = unchanged `registry.json`), type resolved from `fleet.db` with fail-closed fallback, a stdlib `server/firmware_image.py` parser used by `publish_release`, `firmware_cli` and CI, `build` derived from the signed descriptor version and enforced at publish time, and a blocking owner checkpoint for OTA-03 whose device-side proof is explicitly split into "host-provable" and "needs a bench unit".

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Publish a release for a type (parse, validate, store) | API / Backend (`server/firmware_registry.py`, `firmware_cli`) | CI (manifest generation) | D-01: only the deploy-time CLI writes releases; no web upload |
| Resolve device -> hardware type | Database / Storage (`fleet.db`) read by byos | Backend cache in `device_report.json` | Server-assigned, authoritative; the device must never report its own type |
| Compute the offer for a device | API / Backend (byos `compute_offer`) | -- | Pure function over the device's type slice |
| Schedule / cancel per type | API / Backend (`schedule_release`) | Browser (Update page forms) | D-02 |
| Binary integrity (hash, size, signature, chip id, project name) | Device firmware (`ota.c`, ESP-IDF) | Server publish-time pre-checks, CI `espsecure verify_signature` | Server checks are early rejection; the device is the real boundary |
| Build number / downgrade refusal | API / Backend (publish gate) | Device floor (`CONFIG_SKYPANE_OTA_FLOOR_VERSION`) | Device has no anti-rollback (eFuse forbidden) |
| Release manifest generation | CI (`scripts/fw_release_manifest.py`) | -- | All fields derived from git + image |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python stdlib (`struct`, `hashlib`, `json`, `zlib`) | 3.14 prod / 3.13 local venv (verified `python3 --version` = 3.13.17) | Image parsing, hashing, registry I/O | Project rule: stdlib + Pillow + requests only (`.claude/CLAUDE.md`); no new dependency |
| `server/atomic_io.py` (`atomic_write`, `exclusive_lock`) | in repo | All registry writes/locks | Module docstring `firmware_registry.py:21-26` forbids a second implementation |
| `server/hardware.py` (`FirmwareTarget`, `available_types`, `get_profile`) | in repo | Declared-type source of truth | Phase 48 D-05 |
| `server/fleet_db.py` (`connect_readonly`, `get_device_by_mac`) | in repo | Device -> type | Phase 48 |
| pytest 9.1.1 + xdist | in repo | Tests | `./scripts/run-all-tests.sh` |

### Supporting
| Tool | Purpose | When to Use |
|------|---------|-------------|
| `espsecure.py verify_signature --version 2` (esptool, in the pinned `espressif/idf` container) | RSA-PSS signature verification | CI only (`firmware-release.yml:148-165`) and `flash.sh`; NOT available on this machine (`command -v espsecure.py` empty). Never reimplement RSA-PSS in Python |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| stdlib image parser | `esptool image_info` / `esp-idf-size` | Adds a dependency to the server and CI python; the header layout is 4 fixed structs |
| per-type documents | one document with `types{}` sections | See Pattern 1 comparison |

**Installation:** none. No new package is introduced by this phase.

## Package Legitimacy Audit

No external package is installed or recommended by this phase (stdlib only), so slopcheck was not run and the audit table is empty.

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| (none) | -- | -- | -- | -- | -- | -- |

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Architecture Patterns

### System Architecture Diagram

```
 git tag fw-vX.Y.Z (on main)
        |
        v
 firmware-release.yml: build -> sign (RSA-3072, env firmware-signing) -> espsecure verify
        |   + NEW: parse descriptor, check vs hardware.py FirmwareTarget, emit manifest
        |     {version, sha256, size, commit, notes, hardware_type, build}
        v
 GitHub Release assets  (skypane-<tag>.bin + release.json  [+ per-type files later])
        |
        v   reviewed ci.yml deploy -> activate.sh
 firmware_cli import-dir  (as skypane user, before symlink swap)
        |
        v
 publish_release(state_dir, manifest, image, hardware_type)
   1 manifest + sha/size check            (exists today)
   2 parse image (firmware_image.py)      --> reject: bad magic, chip id, project_name,
   3 descriptor.version == manifest.version, signature sector present   | type mismatch
   4 under registry_lock: duplicate? -> "exists"   (idempotent, no new checks)
   5 build gate: build > max(non-bench build of THIS type)  --> reject if lower
   6 store firmware/<sha>.bin, append to firmware/registry[.<type>].json
        |
        v
 firmware/registry.json  (legacy type, unchanged shape)    firmware/registry.<key>.json (other types)
        |  schedule_release / cancel_schedule  <-- companion Update page (type chooser, D-02)
        v
 byos GET /device/v1/display
   token -> MAC -> hardware_type (fleet.db; legacy fallback only for MACs in devices.json; else none)
   -> load THAT type's document only -> compute_offer(...) -> {"firmware": offer | null}
   -> stamp entry["hardware_type"] in device_report.json
        |
        v
 frame: /fw/<sha>.bin -> esp_https_ota: chip id, project_name, version==offer, floor, sha256, signature
        |
        v
 X-Ota-Result / X-Fw-Version  -> device_report.json -> poll loop apply_reconcile (per type)
```

### Pattern 1: Registry shape (Question 1)

**Facts that drive the choice**
- `_normalise_registry` rebuilds the dict from known keys only (`firmware_registry.py:278-302`); any unknown top-level key is dropped on the next write by an older release. `apply_reconcile` writes only when `reconciled_seq` moves (`:823`), but `schedule_release`/`cancel_schedule`/`publish_release` always write.
- Existing tests read `registry["schedule"]`, `registry["releases"]` straight off `load_registry` (e.g. `stub-server/test_ota_offer.py:123`), and fixtures write whole documents. Total existing surface: `server/test_firmware_registry.py` (1,260 lines), `test_firmware_cli.py` (555), `test_firmware_reconcile.py` (199), `stub-server/test_ota_offer.py` (892), `companion/test_update_page.py` (837), `test_update_actions.py` (379), `test_browser_update.py` (800). Baseline run on 2026-10-29: 207 passed in 22 s for the registry/cli/reconcile/offer/manifest subset (`-n0 --no-cov`).
- `reconciled_seq` is a single global counter over a single global event sequence in `device_report.json` (`byos_server.py:914-920`).

| Criterion | A. One document, legacy at top level + `types{}` for others | B. Per-type documents (legacy = `registry.json` untouched) |
|-----------|-------------------------------------------------|-----------------------------|
| Live frame entries unchanged | Yes, but the file is rewritten with a new key | Yes, byte-compatible shape forever |
| Rollback of code after a 2nd type has data | Old `_normalise_registry` silently drops `types{}` on its next write (second type's schedule/installed history lost; releases re-importable from GitHub Releases because deploy re-imports all) | Old code never opens `registry.<key>.json`; nothing lost |
| Cross-type offer impossible by construction | Needs discipline: slice adapter on every call | Yes: function only ever receives one type's document |
| Existing pure functions / tests | Need a slice adapter in/out of the one document | Unchanged; add a `hardware_type=LEGACY_KEY` default parameter to the I/O wrappers |
| Locking / atomicity | One lock, one write | One lock file (`registry.lock`) reused for all types; each write is one file (no cross-type atomicity is needed) |
| `reconciled_seq` | One global | One per document; each type reconciles only events from its own devices |
| `/fw/<sha>.bin` membership check (`byos_server.py:1203-1206`) | One load | Load legacy + each available type's document (small N) |
| `*.pre-fleet` copy | Essential (shape changes) | Still taken before the first rewrite of `registry.json` by the new code, per success criterion 4 |

**Recommendation: B.** Per-type documents named `firmware/registry.<hardware-key>.json` for every non-legacy key; the legacy key (`hardware.LEGACY_KEY = "xiao-ee02-13in3-spectra6"`, `hardware.py:24`) maps to `registry.json`. The key must be validated with `hardware.is_known(key)` AND a `[a-z0-9-]{1,64}` regex before any path is built (same rule as `firmware_image_path`, `:134-141`). The planner should confirm this with the owner only if the "one document" wording in OTA-01 matters; nothing in the requirements mandates it.

Concrete changes in `firmware_registry.py` (all additive):
- `registry_path(state_dir, hardware_type=LEGACY_KEY)`, `_load_registry_for_write(state_dir, hardware_type=LEGACY_KEY)`, `_save_registry(state_dir, doc, hardware_type=LEGACY_KEY)`; `load_registry(state_dir, hardware_type=LEGACY_KEY)`. Default arguments keep every existing caller (including `poll_cycle.py:260`, `byos_server.py:891,1203`, `companion/app.py:1188-1204`) working.
- Release entries gain `hardware_type` (absent = legacy; `_normalise_release` fills it) and `build` (absent = derived from `parse_version(version)`; no data rewrite needed to be correct).
- Old documents get **no** forced rewrite: `_normalise_registry` fills defaults at read time.
- **`*.pre-fleet`:** inside `_save_registry`, before the first write of an existing `registry.json`, copy the current bytes to `registry.json.pre-fleet` if that file does not exist yet (use `atomic_io.atomic_write` on the bytes read; never overwrite an existing `.pre-fleet`). Because `_save_registry` is the only writer, this covers publish, schedule, cancel and reconcile. Do it under the lock the caller already holds. `deploy/backup/skypane_backup.py:46-50` archives `firmware/` recursively and excludes only `*.lock` and listed names, so the copy and the per-type documents are backed up with no allow-list change (the `.corrupt-<ts>` files are likewise archived; harmless).

**Schedule semantics:** `schedule`, `floor_version`, `last_outcome`, `reconciled_seq` are all per document, which is exactly D-02 "independent schedule per type". `acknowledged()` scans events by `schedule_id` (random 8-byte hex, `:624-625`), so it is already type-safe.

**Device-report coupling:** `device_report.json` stays one file keyed by MAC (Phase 48 constraint, `48-RESEARCH.md:161`). Add `hardware_type` to `_normalise_device_entry` (`:408-423`) and have byos set it every poll. `reconcile(registry, device_report, now)` and `update_view` must then consider only entries whose `hardware_type` (missing = legacy) equals the document's type. Without this filter a type-B device's `installed` event would be attributed to the legacy schedule when versions coincide (`reconcile` stale-id branch `:794-808` writes `last_outcome` from any event).

### Pattern 2: Only a frame's own type is ever offered (Question 2)

Layers, in order:
1. **Type resolution (byos, before taking any lock):** token -> MAC is already done by `_resolve_device_id` (`byos_server.py:819-837`, device id in the report is the MAC). Add `resolve_hardware_type(state_dir, mac)`:
   - `fleet.db` migrated and readable (`_fleet_view` logic `:337-361`): `SELECT hardware_type FROM devices WHERE mac = ?` (`fleet_db.get_device_by_mac`, `fleet_db.py:421`). No row -> no offer.
   - Returned key must satisfy `hardware.is_known(key)` and `key in hardware.available_types()`. A simulated key with the gate off, or a key no longer in code, -> no offer (fail closed; log once via the `_note_fleet_status` style).
   - **Legacy fallback mode** (fleet.db absent/unmigrated/faulted: `_fleet_view` returns None, `:343-357`): return `LEGACY_KEY` **only if the MAC is in the legacy `devices.json` registry** (`load_registry(state_dir)["devices"]`, `byos_server.py:237`); otherwise no offer. Reason: `issue_token` writes the token to the legacy state for every enrolled device (`:391-392`), so a fleet-only second-type device authenticates in fallback mode; defaulting it to legacy would offer it the EE02 binary. Legacy `devices.json` entries only ever come from `devices_cli`, which mirrors them as `LEGACY_KEY` (`_apply_mirror`, `:458`).
   - Do NOT use anything the device sends (`hw_rev` in the setup body `:412`, `X-Fw-Version`) for authorisation (milestone anti-pattern, `research/SUMMARY.md:55`).
2. **Structural isolation:** `compute_offer` receives only that type's document. Add a defence-in-depth assertion in the offer path: the matched release's `hardware_type` equals the resolved type, else no offer.
3. **Serving:** `/fw/<sha>.bin` is unauthenticated and content-addressed by design (`byos_server.py:1196-1202`); it does not know who is asking. Leave it (the device only follows offers), but note it for the threat model: type isolation of the *download* relies on device-side checks (chip id, project name, signature), not on the route.
4. **Device:** chip id mismatch is rejected by `esp_https_ota` before the first write; `project_name` is hard-coded `"skypane"` (`ota_policy.c:12`, `:127`).

Fallback/unknown behaviour must be pinned by tests (see Validation Architecture). Note `_fleet_view` opens SQLite on every call and byos already calls it several times per poll (`bearer_ok` `:1052`, `_resolve_device_id` via `effective_tokens` `:872`); resolve the type once per poll and pass it through, keeping the SQLite read outside `registry_lock` + `_device_report_lock` (`:890`).

**Sim types caveat:** `SIM_CLONE_KEY` reuses the legacy `FirmwareTarget` object (`hardware.py:105`) and `SIM_LANDSCAPE_KEY` has the same `idf_target`/`project_name` (`:123-127`). A descriptor check cannot distinguish simulated types from each other or from legacy. The criterion "a simulated frame of each type is offered only a release of its own type" is therefore satisfied by registry keying + server-side typing (Patterns 1-2), and the descriptor test must use a deliberately different `project_name` or chip id for its negative case.

### Pattern 3: Verifying an uploaded/imported binary with stdlib only (Question 3)

New leaf module (suggested `server/firmware_image.py`, stdlib only, importable from `scripts/fw_release_manifest.py` with `PYTHONPATH=.`; `hardware.py` -> `panel_format` imports Pillow only under `TYPE_CHECKING`, `panel_format.py:11`, so CI's bare `python3` can import it; verify in the CI step).

**Layout verified (ESP-IDF v5.3.1 headers and the real fw-v1.0.2 asset):**

| Field | File offset | Size | Verified value on fw-v1.0.2 |
|-------|-------------|------|------------------------------|
| image `magic` | 0 | 1 | `0xE9` |
| `segment_count` | 1 | 1 | 9 |
| `chip_id` (LE u16) | 12 | 2 | `0x0009` = ESP32-S3 |
| `hash_appended` | 23 | 1 | 1 |
| first segment header | 24 | 8 | load_addr, data_len |
| `esp_app_desc_t` (256 B) | 32 | 256 | magic `0xABCD5432` at 32 |
| `secure_version` (u32) | 36 | 4 | 0 |
| `version` (char[32]) | 48 | 32 | `fw-v1.0.2` |
| `project_name` (char[32]) | 80 | 32 | `skypane` |

Image end = end of 16-byte-aligned block containing the checksum byte after the last segment, plus 32 appended SHA-256 bytes when `hash_appended` is 1 (verified: `sha256(data[:end_of_checksum]) == appended digest`). The signature sector follows at the next 4 KiB boundary: byte 0 `0xE7`, byte 1 `0x02`, bytes 4..36 = SHA-256 of all preceding bytes, modulus (little-endian) at 36..420, exponent at 420..424, CRC32 (zlib) over the first 1196 bytes at 1196. On fw-v1.0.2 the block sits at offset 1,114,112 and the file ends exactly 4,096 bytes later; the digest and CRC both match; the embedded modulus equals the modulus in the committed `firmware/signing/skypane-signing-pubkey.pem` once byte-reversed.

**Chip id table** (v5.3.1 `esp_chip_id_t`): esp32 0x0000, esp32s2 0x0002, esp32c3 0x0005, esp32s3 0x0009, esp32c2 0x000C, esp32c6 0x000D, esp32h2 0x0010, esp32p4 0x0012. An unknown `idf_target` string in `FirmwareTarget` must fail closed.

**Checks, in order, all raising `ValueError("<field>: ...")` like the existing code:**
1. length >= 288, magic `0xE9`, `0 < segment_count <= 16` (the 16 limit is `ESP_IMAGE_MAX_SEGMENTS`, value not re-verified this session; take it from the header or treat as ASSUMED).
2. `chip_id == CHIP_IDS[target.idf_target]`.
3. app descriptor magic; `project_name == target.project_name`; both strings NUL-terminated, ASCII, within 32 bytes.
4. `descriptor.version` matches `RELEASE_TAG_RE` (or `VERSION_RE` for bench) and equals `manifest["version"]` (the device does the same equality, `ota_policy.c:130`).
5. Segment walk reaches a consistent end; appended SHA-256 matches; signature sector present at the 4 KiB boundary with `0xE7`/`0x02`, file length == sector offset + 4096, embedded digest == sha256 of preceding bytes. This rejects an unsigned or truncated image at publish time (an unsigned image aborts at boot, `SIGNING.md:70-76`). Whether the embedded modulus must equal a specific committed public key depends on the OTA-03 decision (Pattern 5); build the check as a parameter.
6. size within the per-type slot limit (see Pitfall 3).

**What the server check does not prove:** RSA-PSS validity of the signature. That stays with `espsecure.py verify_signature` in CI (`firmware-release.yml:148-165`). Do not hand-roll RSA verification.

**Where it runs:** `publish_release` (so `import-dir` and `import-bench` both get it), plus a CI step that fails the release job before publishing. Run descriptor validation only on the **add** path, after the idempotent `exists` short-circuit (`:569-571`), so a re-import of an already-registered tag can never gain a new failure mode (the importer re-imports every release on every deploy, `firmware_cli.py:119-134`). Existing tests fabricate non-ESP payloads (`firmware_cli` tests use `tag.encode() + b"-image-payload"`, `test_firmware_cli.py:21`), so Wave 0 must add a test-support builder for valid synthetic images (`test-support/`, shared by registry, CLI and manifest tests) and migrate those fixtures.

### Pattern 4: Monotonic build number (Question 3, second half)

**Where it can come from (options):**
| Source | Verdict |
|--------|---------|
| Signed descriptor `version` (`fw-vX.Y.Z`) -> `build = major*10**8 + minor*10**4 + patch` | **Recommended.** Covered by the image digest/signature, so a hostile manifest cannot lie; components are at most 4 digits (`RELEASE_TAG_RE`, `firmware_registry.py:59-61`), so the mapping is injective and order-preserving; reuses `parse_version` (`:155-165`); no firmware change; matches the tags already in the repo (`fw-v1.0.0`, `1.0.1`, `1.0.2`) |
| ESP `secure_version` in the descriptor | Not usable: only settable with `CONFIG_BOOTLOADER_APP_ANTI_ROLLBACK` (Kconfig `depends on`), which burns eFuses (16 increments max) and is forbidden (`SIGNING.md:78-82`, `check_production_config.sh` anti-rollback ban). fw-v1.0.2 carries 0 |
| Manifest `build` integer (e.g. CI run number) | Not inside the signed image, so server cannot trust it; at most cross-check against the derived value |
| `git rev-list --count` | Same trust problem, plus branch-dependent |

Store `build` on each release entry and surface it in the manifest (`fw_release_manifest.py:195-202`) as a cross-check: if present it must equal the derived value.

**Interaction with tags, floor and voluntary downgrades**
- Tags are repo-wide, not per type. A tag that builds two types yields two images with the same `version`; identity is therefore `(hardware_type, version)`, which Pattern 1 gives for free (separate documents).
- **Publish gate:** a new non-bench release must have `build` strictly greater than the highest non-bench `build` already in **that type's** document. Same version + same sha -> `exists` (idempotent). Same version + different sha -> existing ValueError (`:572-575`). Lower build -> new ValueError (`build: ...`). Bench versions (`-bench1` suffix, `VERSION_RE`) are exempt and must not be counted as "current" (their `parse_version` ties with the release, `:155-165`).
- **Importer ordering bug to fix:** `cmd_import_dir` iterates `sorted(os.listdir(base))` (`firmware_cli.py:136`), a lexicographic sort (`fw-v1.10.0` < `fw-v1.2.0`). With a monotonic gate, importing several *new* tags into an empty/restored registry in that order would refuse the lower build after the higher one. Sort by `(build, name)` using `parse_version`; names that do not parse sort last and are rejected as today (`:144-145`).
- **Floor:** stays per document (`floor_version` defaults to `FLOOR_VERSION = "fw-v1.0.0"`, `:52`). The device compiles its own floor (`CONFIG_SKYPANE_OTA_FLOOR_VERSION`, `firmware/main/Kconfig.projbuild:34-43`), which "must match the floor enforced independently by the server's release registry". A new type's first firmware should carry a floor equal to its first release; set the type's server floor to match. Floor and build gate are different checks: floor is a lower bound on what may be offered, the gate is an upper-side ordering at publish time.
- **Voluntary downgrade conflict (needs owner confirmation, see Open Questions):** today any published release at or above the floor that differs from the running version can be scheduled, including older ones (`schedule_release` docstring `:599-605`, `_direction_from_running` `:850-860`, Update page words an older one as a rollback). The phase goal says "no frame can ever be offered ... an older build". Success criterion 2 only says "a lower build number than the current one is refused" at upload. The milestone pitfall file (`research/PITFALLS.md:85`) suggests "offer only if offered > running" with an explicit logged "allow downgrade" override. This is a product decision; do not silently remove an existing, tested operator feature.

### Pattern 5: OTA-03 signing options (Question 4) - options only, NOT decided

**Verified current mechanism** (committed `sdkconfig.defaults`: `CONFIG_SECURE_SIGNED_APPS_NO_SECURE_BOOT=y`, `CONFIG_SECURE_SIGNED_ON_UPDATE_NO_SECURE_BOOT=y`, `CONFIG_SECURE_SIGNED_APPS_RSA_SCHEME=y`, `CONFIG_BOOTLOADER_APP_ROLLBACK_ENABLE=y`; no anti-rollback/secure-boot/flash-encryption, enforced by `check_production_config.sh`):
- `fp_ota_apply` (`ota.c:38-184`) order: `esp_https_ota_begin` -> descriptor check via `fp_ota_image_check` (project, version==offer, floor) -> download -> size -> read-back SHA-256 vs offer -> `esp_https_ota_finish`, the only commit point where signature verification happens (`ota.c:171-181`; failure maps to `fail-image`).
- Per ESP-IDF v5.3.1 Secure Boot V2 docs: in this mode the key used for the update check is the public key in the **currently running app's** signature block; only the first signature block / first key is used; multiple trusted keys require full Secure Boot (eFuse, forbidden here); the running app's own signature is not verified on boot, but an unsigned initial app aborts at startup (consistent with `SIGNING.md:70-76`, observed 2026-09-29).
- Consequence: **a device's trusted key is whatever key signed the image it currently runs.** The first image on a new board is cable-flashed anyway, so that board's key is chosen for free at that moment.

| Option | Live frame | New hardware | Cross-type protection on device | Costs / risks |
|--------|-----------|--------------|--------------------------------|---------------|
| S. One key for all types (status quo) | No change, no cable flash | Cable flash signed with the existing key | Signature gives none. Only chip id (rejected by `esp_https_ota` if chips differ) and `project_name` (only if the new type's firmware uses a different name AND the live frame's `FP_OTA_PROJECT_NAME`="skypane" check sees it). Same chip + same project name = server typing is the only guard | One key compromise = whole fleet; rotation needs a transition release per generation (`SIGNING.md:151-162`) |
| P. One key per hardware type | Keeps its current key (= the legacy type's key) | Cable flash signed with its own new key; CI needs a second secret (e.g. `FW_SIGNING_KEY_<TYPE>` in `firmware-signing`, or a second environment) and a per-type signing step; `flash.sh` and manifest need a per-type public key path | A wrong-type binary fails the device's signature check regardless of server bugs | N keys to back up/rotate; CI matrix; per-type public keys committed under `firmware/signing/`; more reviewer-gated work |
| M. Single key + unique `project_name` per type | No change | Unique name (e.g. `skypane-<slug>`) set at build; its firmware's `FP_OTA_PROJECT_NAME` must be compiled to it (today a `#define`, `ota_policy.c:12`) | The live frame's existing "skypane" check rejects other names with no firmware change; the new type's firmware rejects "skypane" | `CMakeLists.txt` `project(skypane)` is hard-coded (needs per-type build parametrisation, Phase 58 work); cheap insurance, still no cryptographic separation |
| N. Do not sign the new type (TLS + SHA-256 only) | n/a | Its sdkconfig must opt out of the shared `SECURE_SIGNED_*` lines; otherwise an unsigned image aborts at boot (`SIGNING.md:70-76`) | None | Weakest; allowed by OTA-03's wording ("decide whether OTA images are signed") but must be an explicit recorded choice; a later move to signing needs a cable flash (any option that changes what a device already trusts, other than a normal key-rotation release, needs one) |
| (Not viable) dual-sign with old+new key | -- | -- | -- | Only the first signature block/key is honoured in no-secure-boot mode (docs above) |

One-time cable flashes: always one for any new hardware's first image (inherent). The live frame needs a cable flash only on loss/compromise of its key (`SIGNING.md:160-162`) or if its trust configuration changes by means other than a normal rotation release. Combinations are possible (S+M, P+M). The decision must be recorded (suggested home: a "Decision record (OTA-03)" section in `firmware/SIGNING.md`, plus a plan checkpoint of type decision/human-verify) and must precede provisioning of any non-simulated second type.

**What a hardware-free device-side verification test can and cannot prove**

Can prove (all runnable in CI without a board):
- The Kconfig chain that enables on-device verification: `check_production_config.sh static|built` already asserts the `SECURE_SIGNED_*` lines and the absence of eFuse options in defaults and in the built sdkconfig. Extend, do not duplicate.
- The decision logic in C: `fp_ota_image_check` verdicts (wrong project, version mismatch, below floor) via `firmware/tests/test_ota_policy.c` through `run_host_tests.sh` (already in `firmware.yml` host-tests).
- That the artifact is signed by the intended key: `espsecure.py verify_signature` (CI/`flash.sh`) plus the server-side check that the image has a well-formed signature sector whose embedded modulus equals the committed public key (verified true for fw-v1.0.2).
- That the server refuses binaries the device would refuse for reasons visible in the header (chip id, project name, version, missing signature sector).
Cannot prove without hardware (or an emulator, unverified here):
- That `esp_https_ota_finish` actually returns `ESP_ERR_OTA_VALIDATE_FAILED` for a wrongly-signed or unsigned OTA image on the running firmware, i.e. that the running app really uses its own embedded key and rejects others. The repo only has an observation of the *boot-time* abort for an unsigned image (`SIGNING.md:70-76`); no recorded observation of a rejected OTA.
- The `fail-image`/`fail-floor` result tokens round-trip from a real device through `X-Ota-Result` into `reconcile`.
- Rollback behaviour with `CONFIG_BOOTLOADER_APP_ROLLBACK_ENABLE` for a wrong-hardware image.
Recommended split for planning: automated tests cover the first list; the second list becomes a documented manual bench step (bench key + `import-bench`, per `SIGNING.md:173-186,198-209`) and a `checkpoint:human-verify` task tied to the first real second-hardware session (Phase 58) and, for the live frame, to whenever Phase 47 permits a deploy. State this honestly in the plan: criterion 3's "verified on the device-side code path" is satisfied for the policy code and configuration, and remains an explicit manual check for the cryptographic accept/reject.

### Pattern 6: Companion Update page per type, `firmware_cli`, CI (Question 5)

**Update page (D-02).** Current structure: `update_view(registry, device_report, now)` -> `update_page(ctx, view, ...)` (`companion/pages/update_page.py:575-608`); routes `INSTALL_ROUTE="/update/install"`, `CANCEL_ROUTE="/update/cancel"` (`:24-25`); POST handlers `companion/app.py:1163-1233`; `update_view` picks `_most_recent_device_entry` across **all** devices (`firmware_registry.py:828-842`, docstring "single-frame UI").
- Add `hardware_type` (default `LEGACY_KEY`) to `load_registry`, `update_view`, `schedule_release`, `cancel_schedule`. `update_view` filters device-report entries by type.
- Selector shown only when more than one type is relevant: types in `hardware.available_types()` that have at least one release or one device. With exactly one (production today) render nothing new and add no query parameter, hidden field or heading: the page must be byte-identical to today's. Use `GET /update?type=<key>` (default legacy) and a hidden `hardware_type` field in the Install/Cancel/confirm forms only when the selector is shown (the server must still default to legacy when the field is absent, so old bookmarked forms work).
- Validate the posted type with `hardware.available_types()` before any use; the existing `version` validation (`app.py:1178-1184`) stays. `update_install_confirm_page` takes the type for its sentence only if the selector is shown.
- Type labels come from `HardwareProfile.label` (`hardware.py:83`); new UI strings need EN and FR entries in `companion/i18n_fr/update.py` (project rule: every user-facing literal is bilingual).
- A `since the page looks and behaves as today` test: render the page with a one-type registry and assert equality with the pre-change rendering (use `test-support/companion_render_snapshot.py`; existing `companion/test_update_page.py` already covers the single-type DOM).

**`firmware_cli` (D-01).**
- Manifest field `hardware_type` (optional). Absent -> legacy **only** for grandfathered releases (see Pitfall 4); present -> must satisfy `hardware.is_known` and be available in this environment.
- `import-dir`: keep `<dir>/<tag>/skypane-<tag>.bin` + `release.json` (legacy, unchanged). Additional types as additive files in the same tag directory (e.g. `release-<key>.json` + `skypane-<key>-<tag>.bin`); an importer that does not know them ignores them, so the rollback release keeps working. Sort by build (Pattern 4). Keep the "already registered -> report but do not block" tolerance (`firmware_cli.py:119-176`).
- `import-bench` gains `--hardware-type` (default legacy); bench images stay exempt from the build gate.
- `list` gains `--hardware-type` or a per-type heading; keep today's one-line-per-release output when only the legacy type has releases (`list` prints `version published_at size installed_count`, `:259-264`; ops docs call it at `deploy/README.md:436-440`).
- Optional new verb `check-image --hardware-type T FILE` (same parser) usable by CI and by hand.

**CI (`firmware-release.yml`, `scripts/fw_release_manifest.py`, `ci.yml`).**
- `build_manifest` (`fw_release_manifest.py:175-202`): add `hardware_type` (new `--hardware-type`, default legacy key) and `build`; call the shared parser on the signed image so a descriptor/type mismatch fails the release job before `gh release create` (`firmware-release.yml:167-176` step; run with `PYTHONPATH=.`). Keep `MAX_IMAGE_BYTES` source-of-truth in one place (currently duplicated, `:22-24`).
- Add a step "Verify image descriptor and signature sector" after the existing `espsecure verify_signature` step (`:148-165`).
- Asset naming: leave the legacy asset names untouched. `ci.yml:207-237` downloads exactly `skypane-${tag}.bin` and `release.json` and skips a release lacking either; extend it additively (extra `--pattern` entries) only when a second type actually builds (Phase 58). Phase 49 should not restructure `firmware/build.sh` (EE02-specific `build-ee02`).
- Do not publish releases for a second type in this phase: there is no second firmware yet; only the registry, manifest and checks must be ready and tested with synthetic images.

### Recommended Project Structure
```
server/
├── firmware_image.py        # NEW: stdlib app-image parser + validators (no I/O beyond bytes)
├── firmware_registry.py     # MODIFIED: hardware_type param, per-type paths, build gate, pre-fleet copy
├── firmware_cli.py          # MODIFIED: --hardware-type, build-ordered import
├── hardware.py              # MODIFIED: FirmwareTarget gains max_app_bytes (see Pitfall 3)
stub-server/byos_server.py   # MODIFIED: resolve_hardware_type, per-type document in the offer path, /fw/ over all types
companion/pages/update_page.py, companion/app.py, companion/i18n_fr/update.py  # type chooser
scripts/fw_release_manifest.py   # hardware_type + build + descriptor check
test-support/                    # NEW: valid-synthetic-ESP-image builder shared by tests
```

### Anti-Patterns to Avoid
- **Trusting the device for its type** (`hw_rev`, headers, project name): the server assigns type (`research/SUMMARY.md:55,77`).
- **Defaulting an unknown device to the legacy type**: fail closed (Pattern 2).
- **A second lock or write path** for new documents: reuse `registry_lock` / `atomic_write`.
- **Adding validation to the already-registered path**: breaks idempotent re-import and can block every deploy.
- **Reusing `FirmwareTarget.max_image_bytes` as the firmware size bound** (Pitfall 3).
- **Hand-rolled RSA verification** in Python.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| RSA-PSS signature verification | Python modular-exponentiation verifier | `espsecure.py verify_signature` in CI/`flash.sh`; server only checks structure + key modulus | Crypto bugs; the project already has the tool in a pinned container |
| File locking / atomic writes | New flock/rename code | `atomic_io.exclusive_lock`, `atomic_write` | Module contract `firmware_registry.py:21-26` |
| Version ordering | New comparator | `parse_version` / `at_or_above_floor` (`:155-174`) | Already the single definition; device mirrors it in C |
| Device-type authority | Header/`hw_rev` sniffing | `fleet.db` `devices.hardware_type` | Server-assigned, FK-backed |
| Image-header parsing | Calling esptool from the server | 24-byte header + 256-byte descriptor via `struct` | Fixed layouts, verified on a real image |

**Key insight:** every guarantee here is a small additive check composed from existing primitives; the risk is in the seams (idempotent re-import, rollback compatibility, fallback typing), not in the checks themselves.

## Runtime State Inventory

Not a rename phase, but it changes a persisted format, so the same questions apply.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | `/opt/skypane/state/firmware/registry.json` (live; 3 real releases per tags `fw-v1.0.0`-`fw-v1.0.2`; contents on the VPS NOT inspected from here), `device_report.json` keyed by MAC (may hold a legacy `"default"` bucket, `48-RESEARCH.md:161`), content-addressed `firmware/<sha>.bin` | Code edit only: read-time defaults fill `hardware_type`/`build`; `registry.json.pre-fleet` taken at first rewrite; no data migration. Operator step (unverified): run `firmware_cli list` on the VPS before deploy and confirm no non-bench release is out of version order |
| Live service config | byos and companion read the registry per request (no cache); poll loop `apply_reconcile` (`poll_cycle.py:260`) | None beyond code deploy; deploy waits for Phase 47 (STATE.md decisions) |
| OS-registered state | systemd units run `firmware_cli import-dir` via `activate.sh:226` | None: CLI flags are additive, default args unchanged |
| Secrets/env vars | `FW_SIGNING_KEY` in GitHub environment `firmware-signing`; `SKYPANE_SIM_HARDWARE` gate | New per-type secret only if OTA-03 picks per-type keys |
| Build artifacts | GitHub Release assets for fw-v1.0.0-2 lack `hardware_type` in `release.json` (fw-v1.0.2 manifest verified: version, sha256, size, commit, notes, released_at only) | Importer must keep accepting them (grandfather rule, Pitfall 4) |

## Common Pitfalls

### Pitfall 1: Old release rewriting a new registry shape
**What goes wrong:** rolling back byos/companion after a second type exists makes the old `_normalise_registry` (`:278-302`) drop unknown keys on its next write.
**Why:** whitelist-by-construction normaliser.
**Avoid:** per-type documents (Pattern 1 B); never add keys to `registry.json` that matter for correctness; test: an old-shape reader/writer round trip leaves `registry.<key>.json` untouched.
**Warning signs:** a test that loads a doc with unknown keys, saves, and asserts equality.

### Pitfall 2: Same-descriptor types (sim clone, same-chip second board)
**What goes wrong:** the descriptor check passes for a wrong-type binary when `project_name` and chip are identical (`hardware.py:105,123-127`; any second ESP32-S3 board that keeps `project(skypane)`).
**Avoid:** registry keying + server typing carry the guarantee; give the real second type a unique `project_name` (also protects the live frame through its existing on-device check); tests use differing descriptors for negative cases.

### Pitfall 3: `FirmwareTarget.max_image_bytes` is the DISPLAY image size, not the firmware bound
**What goes wrong:** `hardware.py:89-93` sets it to `panel_format.IMAGE_BYTES` (960,000) and the landscape sim to 192,000 (`_packed_image_bytes(800, 480)`, `:126`). Using it to cap a firmware binary would reject the real 1,118,208-byte fw-v1.0.2 image.
**Avoid:** add a distinct field (e.g. `max_app_bytes`, default `0x250000` = ota slot in `firmware/partitions.csv`) with a default so the frozen dataclass stays constructible; keep `MAX_IMAGE_BYTES` (`firmware_registry.py:55`, `fw_release_manifest.py:24`, `byos_server.py:1213`) as the legacy value; a new type's slot size comes from its own partition table (unknown until Phase 58). `hardware.py` is in the mypy list: keep annotations (`pyproject.toml [tool.mypy] files`).

### Pitfall 4: "Absent hardware_type means legacy" is a brick path
**What goes wrong:** a type-B binary published with a manifest lacking `hardware_type` is validated against the legacy target and, if descriptors coincide, accepted as legacy -> offered to the live frame.
**Avoid:** CI always emits `hardware_type`; the importer accepts an absent field only for grandfathered releases (already registered, or tags at or below a pinned constant set to the newest tag existing when this phase ships, currently `fw-v1.0.2` per `git tag --list 'fw-v*'`). Anything newer without the field is rejected with a clear message.

### Pitfall 5: Lexicographic import order vs the monotonic gate
See Pattern 4. Sort by build.

### Pitfall 6: Fallback-mode typing
See Pattern 2 (`issue_token` writes legacy tokens for every device).

### Pitfall 7: Device-report cross-attribution
`reconcile` consumes events from all devices and `update_view` picks the globally most recent device. Without the `hardware_type` filter a type-B event can close or fail the legacy schedule (`reconcile` `:754-808`, `_most_recent_device_entry` `:828-842`).

### Pitfall 8: Existing fixtures use non-ESP payloads
`test_firmware_cli.py:21`, `test_firmware_registry.py`, `test_ota_offer.py` publish arbitrary bytes. Descriptor validation breaks them all unless a shared builder is introduced first (Wave 0), or validation is injectable. Prefer the shared builder over a test-only bypass flag (a bypass is a production code path that tests then do not exercise).

### Pitfall 9: Function-size gate and comment-history guard
`scripts/check_function_size.py check --max 80 server stub-server` counts code lines excluding docstrings; `_record_device_report_and_offer` is already large (`byos_server.py:855-972`) and `publish_release` is ~80 lines (`:514-596`). Adding checks inline will breach the gate: extract `_validate_manifest`, `_validate_image`, `_apply_build_gate`, `_store_image` helpers. Comments must carry no plan/phase/ticket IDs (`scripts/check_comment_history.py check`, CI `ci.yml:106`); do not write "Phase 49" or "OTA-02" in code comments.

## Code Examples

Verified against the real fw-v1.0.2 asset (offsets above) and a synthetic builder round trip; not yet in the repo.

```python
# Source: ESP-IDF v5.3.1 esp_app_format.h / esp_app_desc.h layouts; checked on skypane-fw-v1.0.2.bin
import hashlib, struct

_APP_DESC_MAGIC = 0xABCD5432
_CHIP_IDS = {"esp32": 0x0000, "esp32s2": 0x0002, "esp32c3": 0x0005, "esp32s3": 0x0009,
             "esp32c2": 0x000C, "esp32c6": 0x000D, "esp32h2": 0x0010, "esp32p4": 0x0012}

def _cstr(raw):
    if b"\0" not in raw:
        raise ValueError("descriptor: unterminated string")
    return raw.split(b"\0", 1)[0].decode("ascii")

def parse_app_image(data):
    if len(data) < 24 + 8 + 256 or data[0] != 0xE9:
        raise ValueError("image: not an ESP application image")
    chip_id = struct.unpack_from("<H", data, 12)[0]
    if struct.unpack_from("<I", data, 32)[0] != _APP_DESC_MAGIC:
        raise ValueError("descriptor: missing app descriptor")
    return {"chip_id": chip_id, "version": _cstr(data[48:80]),
            "project_name": _cstr(data[80:112]), "segments": data[1],
            "hash_appended": data[23]}

def image_end(data):
    """Offset just past the appended SHA-256 (or the checksum byte)."""
    offset = 24
    for _ in range(data[1]):
        _, length = struct.unpack_from("<II", data, offset)
        offset += 8 + length
    end = (offset + 1 + 15) & ~15           # checksum is the last byte of a 16-byte block
    if data[23] == 1:
        if hashlib.sha256(data[:end]).digest() != data[end:end + 32]:
            raise ValueError("image: appended SHA-256 mismatch")
        end += 32
    return end

def signature_sector(data, end):
    """Offset of the single Secure Boot V2 block, or raise."""
    pos = (end + 4095) & ~4095
    if len(data) != pos + 4096 or data[pos] != 0xE7 or data[pos + 1] != 0x02:
        raise ValueError("signature: no well-formed signature sector")
    if data[pos + 4:pos + 36] != hashlib.sha256(data[:pos]).digest():
        raise ValueError("signature: embedded digest does not match image")
    return pos
```

Per-type path helper (key validated twice):
```python
_TYPE_KEY_RE = re.compile(r"\A[a-z0-9][a-z0-9-]{0,63}\Z")

def registry_path(state_dir, hardware_type=hardware.LEGACY_KEY):
    if hardware_type == hardware.LEGACY_KEY:
        return os.path.join(firmware_dir(state_dir), REGISTRY_FILE)
    if not _TYPE_KEY_RE.match(hardware_type) or not hardware.is_known(hardware_type):
        raise ValueError("hardware_type: unknown %r" % (hardware_type,))
    return os.path.join(firmware_dir(state_dir), "registry.%s.json" % hardware_type)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| One global registry, version-only identity | `(hardware_type, version)` | This phase | Prevents cross-type offers |
| Device check = `project_name == "skypane"` only | Unchanged on live frame (Phase 57 may extend) | -- | Server must not rely on it as a second line (`research/ARCHITECTURE.md:17`) |

**Deprecated/outdated:** milestone research proposed "registry schema 2 with per-device schedules" (`research/ARCHITECTURE.md:51,102`); CONTEXT D-02 narrowed it to per-type schedules, which this document follows.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `ESP_IMAGE_MAX_SEGMENTS` is 16 | Pattern 3 | Parser would reject/accept the wrong segment count; read from the header file or drop the upper bound |
| A2 | Per-type documents are acceptable to the owner vs "one registry" | Pattern 1 | Planner may need to switch to the one-document variant (adapter layer) |
| A3 | Pinning grandfathered releases at "tags <= fw-v1.0.2" is right; a newer legacy tag may be published before this phase deploys | Pitfall 4 | Importer rejects a legitimate newer undeclared tag; set constant at deploy time |
| A4 | A later move of a device from unsigned to signed images needs a cable flash | Pattern 5 option N | Option N's cost estimate off; not verified against IDF behaviour |
| A5 | The VPS registry holds only in-order, non-bench-conflicting releases | Runtime State | Gate or ordering may surprise; check with `firmware_cli list` before deploy |
| A6 | Second hardware's firmware can use a distinct `project_name` | Pitfall 2, Option M | Build parametrisation (`CMakeLists.txt`, `FP_OTA_PROJECT_NAME`) is Phase 58 work and unverified |
| A7 | Emulators (QEMU/Wokwi) can or cannot exercise the OTA signature path | Pattern 5 | Unverified either way; planner should not assume it |

## Open Questions (RESOLVED)

1. **Voluntary downgrade vs "never an older build".**
   - Known: Update page and `schedule_release` deliberately allow older published releases at or above the floor; goal text forbids offering an older build; criterion 2 only requires publish-time refusal.
   - Unclear: whether the owner wants the rollback feature kept.
   - Recommendation: keep it (expand-only, tested, floor-bounded), document that "older build" is enforced at publish time and by the floor, and ask the owner to confirm in the plan checkpoint. If not kept: `compute_offer` must additionally refuse `build(offer) < build(reported)` and the Update page drops the older-release Install form.
   - RESOLVED: by CONTEXT D-03 (voluntary rollback above the floor stays; the lower-build refusal applies at publish time, per type, non-bench only).
2. **OTA-03 signing option** (S, P, M, N, combinations): owner decision, checkpoint before any second hardware is provisioned.
   - RESOLVED (as a checkpoint, not a decision): plan 49-02 presents the options to the owner and records the answer in `firmware/SIGNING.md`; plan 49-10 implements only the matching verification branch. The choice stays undecided in the planning artifacts.
3. **Per-type version series:** should a second type reuse the repo-wide `fw-v*` tag series (assumed here) or get its own prefix? Reusing means a tag may release only one of several types; `build` must stay monotonic only within a type.
   - RESOLVED: by the default accepted in CONTEXT D-03 (a second type reuses the repo-wide `fw-v*` tag series).
4. **Acceptable level of the manual bench proof** for criterion 3 (see Validation Architecture), and when it can happen (Phase 47 gating, Phase 58 hardware).
   - RESOLVED: by the blocking human-verify checkpoint in plan 49-10 (bench proof or an explicit deferral with a provisioning block; a deferral leaves success criterion 3 unmet and is reported as such).
5. **Real-image fixture:** may the 1.1 MB `fw-v1.0.2` asset (or only its first 288 bytes plus signature sector) be committed as a golden fixture? Not decided; synthetic builder is the default.
   - RESOLVED: by the default accepted in CONTEXT D-03 (synthetic image builder, no committed real-image fixture).

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| python3 | server, tests, CI scripts | yes | 3.13.17 (prod 3.14) | -- |
| pytest in `server/.venv` | tests | yes | 9.1.1 | -- |
| cc | firmware host tests (`run_host_tests.sh`) | yes | present (`/usr/bin/cc`) | -- |
| docker | firmware build/sign (`build.sh`, CI) | yes (binary present; daemon not probed) | -- | CI only |
| espsecure.py | local signature verification | no | -- | Run inside the pinned `espressif/idf` container; unit tests must not require it |
| gh (REST) | fetching release assets for fixtures | works via `gh api` only (GraphQL blocked) | -- | -- |
| Playwright browser | companion browser tests | not probed | -- | CI enforces |

**Missing dependencies with no fallback:** none for the server-side work.
**Missing with fallback:** espsecure.py (container).

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.1.1 (+ xdist, cov, pytest-socket guard, pytest-playwright for `companion/test_browser_*`) |
| Config file | `pyproject.toml` (`[tool.pytest.ini_options]`, `[tool.mypy]`, ruff) |
| Quick run command | `server/.venv/bin/python -m pytest server/test_firmware_registry.py server/test_firmware_cli.py server/test_firmware_reconcile.py stub-server/test_ota_offer.py deploy/tests/test_release_manifest.py -q -n0 --no-cov` (currently 207 passed, ~22 s) |
| Full suite command | `./scripts/run-all-tests.sh` |
| Gates | `ruff check .`, `mypy`, `python scripts/check_function_size.py check --max 80 server stub-server`, `python scripts/check_comment_history.py check`, `sh firmware/tests/run_host_tests.sh`, `sh firmware/tests/check_production_config.sh static` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| OTA-01 | Two sim types, each scheduled differently, each polled through real byos: each frame is offered only its own type's release; the other's schedule never appears | integration (byos in-process, existing `test_ota_offer.py` harness) | `pytest stub-server/test_ota_offer.py -k hardware -q` | Wave 0 (new tests; harness exists) |
| OTA-01 | Unknown/absent type, sim key with gate off, fleet.db fault + MAC not in devices.json -> no offer; fault + MAC in devices.json -> legacy offer | integration | same file | Wave 0 |
| OTA-01 | Independent schedules, cancel and reconcile per type; foreign-type events do not move the other schedule | unit | `pytest server/test_firmware_registry.py server/test_firmware_reconcile.py -k type` | Wave 0 |
| OTA-01 | Update page: one type renders identical to today; two types show chooser; POST validates type | unit + browser | `pytest companion/test_update_page.py companion/test_update_actions.py -q` ; `companion/test_browser_update.py` | partially exists |
| OTA-02 | Reject wrong magic, chip id, project name, version != manifest, unterminated strings, missing/short signature sector, bad appended digest; accept valid; accept a stored real-shape image | unit | `pytest server/test_firmware_image.py -q` | Wave 0 |
| OTA-02 | Lower build refused, equal+same sha idempotent, equal+different sha refused, bench exempt, per-type independence, numeric import order | unit | `pytest server/test_firmware_registry.py server/test_firmware_cli.py -k build` | Wave 0 |
| OTA-02 | Re-import of already registered release never re-validates; absent `hardware_type` only for grandfathered | unit | `pytest server/test_firmware_cli.py` | Wave 0 |
| OTA-03 | Policy verdicts for the device decision code | C host test | `sh firmware/tests/run_host_tests.sh` | exists (extend if firmware code changes) |
| OTA-03 | Production config chain unchanged and, per decision, extended | shell | `sh firmware/tests/check_production_config.sh static` | exists |
| OTA-03 | Server accepts an image only if embedded modulus matches the key chosen for its type (if the decision includes it) | unit | `pytest server/test_firmware_image.py -k key` | Wave 0, conditional on decision |
| OTA-03 | Real device rejects a wrongly-signed OTA image and reports `fail-image` | manual bench | n/a (hardware) | manual-only, justified above |
| Criterion 4 | A copy of the real live-shaped `registry.json` still drives `compute_offer`/`update_view`/`schedule_release` unchanged; `.pre-fleet` created once, byte-identical to the original, never overwritten | unit | `pytest server/test_firmware_registry.py -k pre_fleet` | Wave 0 |
| Manifest | `fw_release_manifest.py` emits `hardware_type`, `build`; refuses descriptor/type mismatch; output round-trips through `publish_release` | subprocess | `pytest deploy/tests/test_release_manifest.py -q` | exists, extend |

### Sampling Rate
- **Per task commit:** the quick command above (plus `ruff check` on touched files).
- **Per wave merge:** `./scripts/run-all-tests.sh` plus the function-size and comment-history gates.
- **Phase gate:** full suite green, mypy clean, firmware host tests and `check_production_config.sh static` green before `/gsd:verify-work`.

### Wave 0 Gaps
- [ ] `test-support/` helper that builds a valid synthetic signed-shape ESP image (header, descriptor, segment, checksum, appended SHA-256, signature sector) with controllable chip id/project name/version, and migrate the arbitrary-bytes fixtures in `test_firmware_cli.py`, `test_firmware_registry.py`, `test_ota_offer.py`, `deploy/tests/test_release_manifest.py`.
- [ ] `server/test_firmware_image.py`.
- [ ] A golden-shape regression: first 288 bytes + signature sector layout of the real fw-v1.0.2 (decision needed, Open Question 5).
- [ ] Behaviour-over-source: tests assert registry files, byos JSON, rendered HTML via the existing fixtures, never source text or `.planning/` (`companion/test_suite_guards.py` applies to `companion/test_*.py`); a doc-heading test for the signing decision record would be a source-text test, so verify the checkpoint through the plan instead, or follow the `deploy/tests/test_docs.py` precedent outside `companion/` knowingly.

## Security Domain

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no (unchanged) | existing device bearer tokens |
| V3 Session Management | no | -- |
| V4 Access Control | yes | companion still shared-password only (D-01); type resolution server-side; no new unauthenticated write route |
| V5 Input Validation | yes | whitelist regexes for version/sha/type key; fixed-offset binary parsing with length checks; manifest size cap `_MAX_MANIFEST_BYTES` |
| V6 Cryptography | yes | never hand-roll; RSA-PSS verified by espsecure in CI and by ESP-IDF on device; SHA-256 via `hashlib` |
| V12 Files | yes | content-addressed storage, symlink refusal in importer (`firmware_cli.py:101-110`), type key never joined into a path unvalidated |

### Known Threat Patterns
| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Wrong-hardware binary offered (brick) | Tampering / DoS | per-type documents, server-assigned type, descriptor+chip check at publish, device chip-id check |
| Downgrade to vulnerable build | Tampering | publish-time build gate, per-type floor, device floor |
| Path traversal via type key or sha | Tampering | regex + `hardware.is_known`; existing `firmware_image_path` |
| Malformed manifest/binary crashing the importer | DoS | bounded reads, `ValueError` per item, importer keeps going for already-registered tags |
| Hostile `device_report.json` growth | DoS | existing per-device event cap (`:91`, `:422`) |
| Compromised VPS pushing unsigned/foreign-signed code | Spoofing / EoP | device signature check against running app's key; key never on VPS (`SIGNING.md:146-149`) |
| Fleet-wide impact of single signing key | EoP | OTA-03 options P/M |

## Sources

### Primary (HIGH confidence)
- Repository files read in full or in the cited ranges: `server/firmware_registry.py`, `server/hardware.py`, `server/fleet_db.py`, `server/firmware_cli.py`, `stub-server/byos_server.py` (300-480, 740-980, 1040-1275), `companion/pages/update_page.py`, `companion/app.py:1120-1280`, `firmware/main/ota.c`, `ota_policy.c`, `firmware/SIGNING.md`, `firmware/partitions.csv`, `firmware/sdkconfig.defaults`, `.github/workflows/firmware-release.yml`, `ci.yml:100-250`, `scripts/fw_release_manifest.py`, `deploy/README.md:394-456`, `deploy/backup/skypane_backup.py:40-150`, `.planning/workstreams/v1-2/research/{SUMMARY,PITFALLS,ARCHITECTURE}.md`.
- Real artifact: GitHub Release `fw-v1.0.2` asset `skypane-fw-v1.0.2.bin` fetched via `gh api` (sha256 `510007c1...ec6b` equals `release.json`); parsed in an isolated interpreter.
- ESP-IDF v5.3.1 source headers fetched from raw.githubusercontent.com: `components/esp_app_format/include/esp_app_desc.h` (descriptor layout, 256-byte assert), `components/bootloader_support/include/esp_app_format.h` (image header 24-byte assert, chip ids), `components/bootloader/Kconfig.projbuild` (`BOOTLOADER_APP_SECURE_VERSION depends on BOOTLOADER_APP_ANTI_ROLLBACK`), `components/esp_https_ota/src/esp_https_ota.c` (`esp_ota_verify_chip_id` before first write).
- ESP-IDF v5.3.1 docs: `security/secure-boot-v2.html` (signature block format; "Signed App Verification Without Hardware Secure Boot": running app's key, first block only, no multi-key), `api-reference/system/ota.html`, `system/app_image_format.html`.

### Secondary (MEDIUM confidence)
- Docs-derived statement that `esp_ota_end`/`esp_https_ota_finish` return `ESP_ERR_OTA_VALIDATE_FAILED` for signature failure with signed-app options (ota.html); consistent with `ota.c:176-179` but not observed on hardware.

### Tertiary (LOW confidence)
- `ESP_IMAGE_MAX_SEGMENTS` = 16 (training knowledge, A1); emulator capabilities (A7).

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - stdlib only, no new package.
- Architecture: HIGH for code seams (all cited), MEDIUM for the per-type-document choice (design judgement, A2).
- Image verification: HIGH - offsets validated on a real signed release.
- Signing options: MEDIUM - IDF docs read, no hardware observation of OTA rejection.
- Pitfalls: HIGH for those derived from code; Pitfall 4 constant depends on release timing (A3).

**Research date:** 2026-10-29
**Valid until:** 2026-11-28 (stable; revisit if ESP-IDF pin or `firmware-release.yml` changes)
