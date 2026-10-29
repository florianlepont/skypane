---
phase: 49-per-hardware-ota-registry
plan: 05
subsystem: ota
tags: [firmware, registry, publish, build-gate, grandfather]
requires: [49-01, 49-03, 49-04]
provides:
  - publish_release validates the image against the declared type's FirmwareTarget on the add path only
  - per-type monotonic build gate (_apply_build_gate), GRANDFATHERED_MAX_TAG = "fw-v1.0.2"
  - _signing_policy(hardware_type) hook (strict: signature required, no modulus comparison)
affects: [49-06 CLI, 49-09 manifest generator, 49-10 signing profile]
key-files:
  modified:
    - server/firmware_registry.py
    - server/firmware_cli.py
    - server/test_firmware_registry.py
    - server/test_firmware_reconcile.py
    - server/test_retired_notifications.py
    - stub-server/test_ota_offer.py
    - deploy/tests/test_release_manifest.py
    - companion/test_update_page.py
    - companion/test_update_actions.py
    - companion/test_browser_update.py
    - companion/test_browser_ux_helpers.py
decisions:
  - "Grandfather tag confirmed against git tag --list 'fw-v*' (after git fetch --tags origin): fw-v1.0.0, fw-v1.0.1, fw-v1.0.2 exist, so GRANDFATHERED_MAX_TAG stays fw-v1.0.2"
  - "Signing option S (one key for all types): _signing_policy stays (True, None) for every type; no per-type modulus comparison yet"
  - "The manifest build cross-check runs inside the add path (after the exists short-circuit), against the descriptor version"
metrics:
  tasks: 2
  completed: 2026-10-29
requirements: [OTA-01, OTA-02]
---

# Phase 49 Plan 05: Publish validation, grandfather rule and build gate Summary

publish_release now splits into _validate_manifest, _validate_image, _apply_build_gate and _store_image. A new (type, version, sha) is checked against the type's firmware target (chip id, project_name, descriptor version, signature, size bound) and the per-type build gate before anything is written. An already registered (type, version, sha) still returns "exists" without validation. Manifests without hardware_type are accepted only for legacy releases up to fw-v1.0.2.

## Tasks

| Task | Commit | Notes |
|------|--------|-------|
| 1 Image validation and grandfather rule | cc989216 | |
| 2 Per-type build gate | cc989216 | same file; one commit |

## Deviations from Plan

- **[Rule 3 - Blocking] Tasks 1 and 2 share one commit and tests were written with the code**, not RED first; both touch only publish_release and its tests.
- **[Rule 3 - Blocking] Fixtures declare hardware_type.** The grandfather rule rejects tags above fw-v1.0.2 without hardware_type, so every test manifest for fw-v1.1.0 and later in server, stub-server, deploy and companion tests now carries `hardware_type`. In deploy/tests/test_release_manifest.py the round-trip test sets it by hand because scripts/fw_release_manifest.py does not emit it yet.
- **[Rule 3 - Blocking] firmware_cli import-bench manifest declares the legacy type** (one line in server/firmware_cli.py), otherwise bench import of a tag above fw-v1.0.2 would fail until plan 49-06 adds a type option.
- MAX_IMAGE_BYTES is kept (used by byos and scripts); the registry's size bound now comes from the type's FirmwareTarget.max_app_bytes (legacy 0x250000, asserted).

## Interim state to note for later plans

- scripts/fw_release_manifest.py does not yet emit hardware_type, and the deploy importer feeds its manifests to publish_release: a release tagged above fw-v1.0.2 will be rejected on import until plan 49-09 adds the field (this is the intended T-49-14 behaviour).
- The firmware_cli import-bench command is legacy-only until 49-06.

## Verification (run)

- pytest server stub-server deploy/tests test-support companion (-n auto --no-cov, SKYPANE_REQUIRE_BROWSER=1, local Playwright browsers): 4492 passed, 8 skipped (root permission bits, openssl backdating).
- server/.venv/bin/ruff check server stub-server deploy test-support companion scripts: pass.
- server/.venv/bin/mypy: no issues in 16 source files.
- scripts/check_function_size.py check --max 80 server stub-server: 574 functions, none over.
- scripts/check_comment_history.py check: exit 0.
- Not run: the coverage-gated scripts/run-all-tests.sh.
- Note: a first full run before the companion fixture fix showed 28 failures and 78 errors in companion browser/update tests (manifests without hardware_type); fixed in the same commit and the rerun was clean.

## Known Stubs

None.

## Self-Check: PASSED

Commit cc989216 exists; server/firmware_registry.py and this file exist.
