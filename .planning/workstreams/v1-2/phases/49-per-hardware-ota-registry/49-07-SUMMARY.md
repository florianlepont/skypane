---
phase: 49-per-hardware-ota-registry
plan: 07
subsystem: ota
tags: [byos, firmware, offer, hardware-type, fail-closed, reconcile]
requires: [49-03, 49-05]
provides:
  - byos resolve_hardware_type (fleet.db authority, legacy devices.json fallback, fail closed)
  - per-type offer composition with a release/type recheck
  - hardware_type stamp (or firmware_registry.UNRESOLVED_TYPE) on every device-report entry
  - multi-document /fw/<sha>.bin membership
  - poll loop reconciles every type (apply_reconcile_all)
affects: [49-08 and later companion Update page, 49-09 manifest generator]
key-files:
  modified:
    - stub-server/byos_server.py
    - stub-server/test_ota_offer.py
    - server/poll_cycle.py
    - server/test_poll_cycle_steps.py
decisions:
  - "A legacy frame's report entry is not rewritten solely to add the stamp: an unstamped entry already reads as the legacy type, and a rewrite triggered by an unrelated header (X-Battery-Mv) would break the Phase 47 telemetry freeze. The stamp is written whenever the entry is written for another reason, and an unstamped or differently stamped entry of any non-legacy or unresolved device is rewritten at once"
  - "Unresolved devices still record fw_version and result events (stamped with the sentinel) but see a registry with no schedule, so no event is attributed to a schedule"
  - "The unknown-type log line is printed once per (mac, stored type)"
metrics:
  tasks: 2
  completed: 2026-10-29
requirements: [OTA-01]
---

# Phase 49 Plan 07: Type-aware, fail-closed BYOS offers Summary

The offer path resolves the device's hardware type once per poll from fleet.db (never from anything the device sends), offers only a release of that type's own document, and stamps the type into the device-report entry; the poll loop reconciles every type.

## Tasks

| Task | Commit | Notes |
|------|--------|-------|
| 1 RED | 09cba48e | per-hardware offer tests (9 failed first) |
| 1 GREEN | 5891bfe1 | resolve_hardware_type, _offer_for_type, _registry_for_type, stamp |
| 2 RED | 73b7379a | multi-type /fw and reconcile-all tests |
| 2 GREEN | 309f3739 | _is_registered_release, apply_reconcile_all in poll_cycle |

## Behaviour

- Fleet.db row present: its hardware_type must be known and in available_types, else no offer. No row: no offer. Fleet.db absent, unmigrated or faulted: the legacy type resolves only for a MAC in devices.json, so a fleet-only device is never offered the legacy binary.
- `_offer_for_type` composes compute_offer over that type's document and withholds the offer unless the matched release carries the resolved type.
- Resolution happens before registry_lock and the device-report lock (asserted by a hook test).
- Unresolved devices get the UNRESOLVED_TYPE stamp, never an offer, and cannot move any registry document (legacy bytes asserted unchanged after reconcile).
- `_record_device_report_and_offer` was split (`_next_event_seq`, `_stamp_hardware_type`, `_registry_for_type`, `_offer_for_type`); the long seq-flooring comment now lives in `_next_event_seq`'s docstring.

## Deviations from Plan

- **[Rule 1 - Bug] Stamp must not force a write for a legacy frame.** The first implementation re-stamped every unstamped entry and rewrote device_report.json on an X-Battery-Mv-only poll, which test_phase47_freeze.py caught (X-Battery-Mv "added" to the stored-in-device-report list). Fixed in `_stamp_hardware_type` as described under decisions; the freeze file is unmodified.
- **Existing offer harness seeds devices.json.** The fallback rule needs the legacy MAC in devices.json, but the existing tests only seeded byos_state.json tokens. An autouse fixture in test_ota_offer.py now registers KNOWN_MAC in devices.json; no existing test body was changed.
- Task 2 stamp, unresolved and reconcile behaviours were already satisfied by the Task 1 implementation plus plan 03, so those tests were green on first run; only the /fw and poll-loop tests were red first.

## Verification (run)

- `stub-server/test_phase47_freeze.py` and `stub-server/test_fleet_auth.py`, unmodified: pass (run explicitly together with test_ota_offer.py and server/test_poll_cycle_steps.py: 105 passed).
- `pytest server stub-server deploy/tests test-support companion -n auto --no-cov` with SKYPANE_REQUIRE_BROWSER=1 and the local Playwright browsers: 4533 passed, 8 skipped (root permission bits, openssl backdating).
- ruff check (server stub-server deploy test-support companion scripts): pass. mypy: no issues in 16 source files. check_function_size (max 80): 595 functions, none over. check_comment_history: exit 0.
- Not run: the coverage-gated scripts/run-all-tests.sh.

## Known Stubs

None.

## Threat Flags

None. /fw stays unauthenticated and content-addressed (T-49-22 accepted).

## Self-Check: PASSED

Commits 09cba48e, 5891bfe1, 73b7379a, 309f3739 exist; byos_server.py and this file exist.
