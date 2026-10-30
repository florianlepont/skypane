---
phase: 49-per-hardware-ota-registry
plan: 09
subsystem: ota
tags: [ci, release-manifest, firmware-image, workflow]
requires: [49-01, 49-05]
provides:
  - release manifest carries hardware_type and build (derived from the descriptor version)
  - fw_release_manifest.py --hardware-type and --check-only
  - DEFAULT_REQUIRE_SIGNATURE / DEFAULT_EXPECTED_MODULUS constants for plan 49-10 to replace
  - firmware-release.yml step "Verify image descriptor and signature sector"
affects: [49-10]
key-files:
  modified:
    - scripts/fw_release_manifest.py
    - deploy/tests/test_release_manifest.py
    - .github/workflows/firmware-release.yml
decisions:
  - "Signing option S: the script validates with require_signature=True and expected_modulus=None, held in two module constants"
  - "MAX_IMAGE_BYTES removed from the script; size_bound(type) reads the hardware profile's max_app_bytes (0x250000 for legacy, asserted by a test)"
  - "The existing --tag is the version the descriptor must equal (no new --version option)"
metrics:
  tasks: 2
  completed: 2026-10-29
requirements: [OTA-01, OTA-02]
---

# Phase 49 Plan 09: CI release manifest declares type and build Summary

fw_release_manifest.py now parses the signed image with the shared server.firmware_image validator, refuses a chip, project name, descriptor version, signature-sector or size mismatch (exit 2, field-named message, no manifest written), and emits hardware_type (default legacy) and build (from the descriptor version via firmware_registry.build_number). The release workflow runs a new check-only step after espsecure verify_signature. Legacy asset names, ci.yml and firmware/build.sh are untouched.

## Tasks

| Task | Commit | Notes |
|------|--------|-------|
| 1 Manifest hardware_type, build, descriptor check | af6dc86e, 5df62740 | second commit fixes a test assumption about sector rounding |
| 2 Workflow verification step | 25f1232a | check-only step; manifest step passes the legacy type and PYTHONPATH=. |

## Deviations from Plan

- **Tests were written together with the code**, not as a separate RED commit.
- **Oversized-image test merged.** The old oversized test and the new bound test both build multi-megabyte synthetic images (about 50 s each); they are one parametrized test over 0x250000 (passes) and 0x250001 (fails). The builder rounds the over case up to a whole signature sector, so the test asserts the exact size only for the passing case.
- **Round-trip test** no longer sets hardware_type by hand (the script emits it).
- `--out` is required only without `--check-only` (checked after parsing).

## Verification (run)

- pytest deploy/tests/test_release_manifest.py (-n auto): 55 passed. Includes: type and build emitted, unknown or unavailable type exits 2, mismatch cases (chip, project_name, version, unsigned), size bound equals 0x250000 and the legacy profile's max_app_bytes, check-only writes nothing, run with a blocked Pillow import, publish_release round trip.
- pytest server stub-server deploy/tests test-support companion (-n auto --no-cov, SKYPANE_REQUIRE_BROWSER=1, local Playwright browsers): 4574 passed, 8 skipped (root permission bits, openssl backdating).
- ruff check server stub-server deploy test-support companion scripts: pass.
- mypy: no issues in 16 source files.
- scripts/check_function_size.py check --max 80 server stub-server: 595 functions, none over.
- scripts/check_comment_history.py check: exit 0.
- Workflow YAML parsed with ruby's YAML (PyYAML is not installed in the venv or system python): ok.
- Not run: shellcheck and actionlint (not installed); the workflow itself (not triggered by instruction); the coverage-gated run-all-tests.sh. The new workflow step was not exercised against a real signed CI image (none available locally); only against synthetic images.

## Known Stubs

None.

## Self-Check: PASSED

Commits af6dc86e, 5df62740, 25f1232a exist; modified files exist.
