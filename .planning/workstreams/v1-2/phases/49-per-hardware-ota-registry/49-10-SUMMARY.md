---
phase: 49-per-hardware-ota-registry
plan: 10
subsystem: ota
tags: [signing, firmware-image, per-type-policy, bench-deferral]
requires: [49-09]
provides:
  - FirmwareTarget.require_signature and signing_pubkey (per-type signing policy, option S)
  - committed-key modulus check at publish time and in the release manifest script
  - firmware/SIGNING.md "Verification status" with bench procedure and recorded deferral
status: complete-with-deferral
metrics:
  tasks: 3
  completed: 2026-10-30
---

# Phase 49 Plan 10: Per-type signing policy and bench proof Summary

Status: complete-with-deferral. The hardware-free work is done and verified. Success criterion 3 (OTA-03 device side: a running device accepts a correctly signed OTA image and rejects a wrongly signed one with `fail-image`) is DEFERRED and UNMET. It must not be reported as passed.

## Tasks

| Task | Commit | Notes |
|------|--------|-------|
| 1 Read RSA modulus of a committed public key | bf608a6d | |
| 2 Per-type signing policy and committed-key check (option S) | da5f0508 | |
| 3 Bench proof of on-device rejection | ab8e244e | DEFERRED: no bench unit; deferral recorded in firmware/SIGNING.md |

## Task 3 deferral

On 2026-10-30 the owner (Florian Lepont) answered the human-verify checkpoint: no bench unit is available, and the on-device rejection test is deferred to the first second-hardware session. No bench run took place and no result was observed or recorded. The bench results table in firmware/SIGNING.md reads "not run" with verdict DEFERRED.

Consequence recorded in firmware/SIGNING.md: no second non-simulated hardware may be provisioned until the bench procedure has been run and its result recorded. The Phase 42 evidence (wrong-key and tampered image refused on the live EE02 frame) is labelled legacy-only earlier evidence; it does not cover a second hardware type and is not a pass of this bench run.

## Verification done without hardware

- `python3 scripts/check_comment_history.py check`: exit 0
- `sh firmware/tests/check_production_config.sh static`: PASS
- Automated checks from Tasks 1 and 2 (Kconfig chain, C policy verdicts, image structure, artifact-key modulus, per-type policy) as listed in firmware/SIGNING.md "Checked without hardware". The server-side key check compares the embedded modulus only; it never verifies an RSA-PSS signature (espsecure.py in CI and the device do).

## Not proven (needs hardware)

- Device accepts a correctly signed image and rejects a wrongly signed or unsigned one with `fail-image`.
- `fail-image` / `fail-floor` tokens round-trip into the server reconcile.
- Rollback behaviour for a wrong-hardware image.

## Deviations from Plan

Reported at the checkpoint:

1. **firmware/signing key shipped in the deploy archive and the ci.yml shipped-files list.** The committed public key (firmware/signing/skypane-signing-pubkey.pem) is needed on the VPS for the publish-time modulus check, so it is included in the deploy archive and listed in the ci.yml shipped files.
2. **`import-bench --allow-foreign-key`.** Bench images are signed with a throwaway key, so `server.firmware_cli import-bench` gained this flag. It skips the key comparison only; an image without a signature sector is still refused, and it cannot be used for a real release.
3. **Relaxed policy skips the modulus check on an unsigned image.** When a type's policy does not require a signature, an unsigned image is not subjected to the modulus comparison (there is no embedded modulus to compare).

## Requirements

OTA-03 is NOT marked complete: its device-side part is unmet. `requirements.mark-complete` was intentionally not run.

## Known Stubs

None.

## Self-Check: PASSED

Commits bf608a6d, da5f0508, ab8e244e exist; SIGNING.md records the deferral.
