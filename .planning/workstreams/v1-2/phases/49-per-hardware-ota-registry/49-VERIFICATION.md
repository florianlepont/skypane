---
phase: 49-per-hardware-ota-registry
verified: 2026-10-30T00:00:00Z
status: passed
score: 3/4 must-haves verified, 1 accepted by override
overrides_applied: 1
overrides:
  - must_have: "The chosen OTA integrity check is verified on the device-side code path (second half of roadmap criterion 3, OTA-03)"
    reason: "Not run: no non-live bench unit exists. The owner closed the phase on 2026-10-31 and carried the bench run to Phase 58 (HW2-02); Phase 57 may not start its live-frame OTA before it has passed. OTA-03 stays Pending in REQUIREMENTS.md."
    accepted_by: owner
    accepted_at: 2026-10-31
gaps: []
human_verification:
  - test: "Bench run of the firmware/SIGNING.md procedure on a non-live unit (OTA-03 device side)"
    expected: "Unit accepts a correctly signed OTA image; a wrongly signed image is refused, the unit keeps its firmware, and the next poll carries X-Ota-Result fail-image;<version> (visible in device_report.json)"
    why_human: "Needs a physical bench unit; owner deferred it on 2026-10-30 because none is available. Not run, no result recorded."
  - test: "Round-trip of fail-image / fail-floor tokens from a real device into reconcile, and rollback behaviour for a wrong-hardware image"
    expected: "Tokens recorded on the right type's registry; wrong-hardware image rolled back"
    why_human: "Device behaviour; same bench session."
---

# Phase 49: Per-Hardware OTA Registry Verification Report

**Phase Goal:** The owner can publish and schedule firmware per hardware type, and no frame can ever be offered a binary built for another type or an older build.
**Status:** human_needed at verification time (2026-10-30). OTA-03 was NOT fully met: the signing decision is recorded (option S) but the device-side verification is deferred and unproven. This must not be read as passed on that point.

**Closed by the owner, 2026-10-31:** Phase 49 is closed with the OTA-03 device-side verification unproven and carried to Phase 58 (HW2-02), where the evaluation unit is the non-live bench unit. Nothing about that verification has been run; the two human items above stay open and now belong to Phase 58.
**Re-verification:** No (initial)

## Observable Truths

| # | Truth (ROADMAP SC) | Status | Evidence |
|---|--------------------|--------|----------|
| 1 | Owner publishes and schedules per hardware type; a simulated frame of each type is offered only a release of its own server-assigned type | VERIFIED | Per-type documents (`registry_path`, `_type_document_name`); `publish_release/schedule_release/cancel_schedule(hardware_type=...)`; byos `resolve_hardware_type` reads only fleet.db (never device input), `_registry_for_type` loads that type's document, `_offer_for_type` additionally requires `release.hardware_type == device type`. Update page type chooser EN/FR with browser tests. |
| 2 | Wrong app descriptor / chip target rejected; lower build refused | VERIFIED | `_validate_image` -> `firmware_image.validate_for_target` (chip id, project name, descriptor version, size bound, signature sector, committed-key modulus); `_check_declared_type` (manifest type must equal target; omission only for legacy up to the grandfather tag); `_apply_build_gate` strictly-above per type, non-bench; `allow_foreign_key` only for bench. Tests in `server/test_firmware_image.py`, `test_firmware_registry.py`, `test_firmware_cli.py` pass. |
| 3 | Signing decision recorded before second hardware, and chosen integrity check verified on the device-side code path | PARTIAL / NOT MET | Decision recorded: option S, 2026-10-29, owner Florian Lepont (`firmware/SIGNING.md` "Decision record"). Hardware-free checks exist (Kconfig chain script, `test_ota_policy.c` host tests, server-side modulus check, espsecure verify in CI). The on-device rejection of a wrongly signed or unsigned image was NOT run: bench results table reads "not run / DEFERRED". Phase 42 evidence is legacy-only and explicitly not a substitute. SIGNING.md forbids provisioning a non-simulated second hardware until the bench run is recorded. |
| 4 | Live frame's registry entries unchanged; `*.pre-fleet` copy | VERIFIED | Legacy type keeps `registry.json`; `_serialisable` strips `hardware_type`/`build` so the on-disk shape is unchanged; `_write_pre_fleet_copy` writes the exact bytes once, never overwritten; `test_ota_fleet_regression.py` passes. |

**Score:** 3/4 (criterion 3 partial).

## Adversarial checks

- (a) Cross-type / older-build offers: unresolved type returns no offer and sees no schedule; fleet.db unavailable resolves only MACs present in legacy devices.json (to legacy), so a fleet.db-only device is never offered the legacy binary; unknown or non-available (sim gate off) stored type returns None; simulated types read their own documents; double check on release type. Downloads are content-addressed and unauthenticated by design, gating is at the offer. Note: an owner may deliberately schedule an older published release above the floor (decision D-03, voluntary rollback); this is by design, not a gap. With option S, same-chip same-project-name types rely only on server typing on the device side (recorded in SIGNING.md).
- (b) Validation: covered above; the modulus check compares the embedded modulus only and never verifies the RSA-PSS signature (done by espsecure in CI and the device). Unsigned image skips modulus check only when a type's policy does not require a signature (all current types require it).
- (c) Live registry: unchanged shape, pre-fleet copy verified.
- (e) Phase 47 freeze: `stub-server/test_phase47_freeze.py` untouched since Phase 48 and passes.

## Spot checks

| Command | Result |
|---------|--------|
| Full suite `pytest -n auto --no-cov` with browser tests required | 4752 passed, 8 skipped (environment skips: non-root euid, openssl backdating), 650 s |
| firmware_cli/image/reconcile/registry + OTA fleet/offer + phase47 freeze tests | 336 passed |

## Requirements Coverage

| Requirement | Status | Evidence |
|-------------|--------|----------|
| OTA-01 | SATISFIED | SC1, SC4 |
| OTA-02 | SATISFIED | SC2 |
| OTA-03 | NOT FULLY MET | Decision recorded; device-side verification deferred (human item) |

## Anti-patterns

None blocking found in the files examined; no debt markers observed in the reviewed modules.

## Tracking reconciliation (edited)

- REQUIREMENTS.md: OTA-01 and OTA-02 stay checked; OTA-03 stays unchecked, its traceability row now says "Pending (decision recorded; device-side bench check deferred)".
- ROADMAP.md: Phase 49 checkbox changed from `[x]` to `[ ]` with a note, and the progress table row no longer says Complete (now "Human verification pending"), since criterion 3 is unmet.

## Gaps Summary

No code gaps. One outstanding human item: run the SIGNING.md bench procedure on a non-live unit before provisioning any second non-simulated hardware (Phase 58 depends on this). On 2026-10-31 the owner closed the phase and carried this item to Phase 58.

---

_Verified: 2026-10-30_
_Verifier: Claude (gsd-verifier)_
