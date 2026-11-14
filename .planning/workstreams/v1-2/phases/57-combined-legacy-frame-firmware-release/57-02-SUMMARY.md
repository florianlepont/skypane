---
phase: 57-combined-legacy-frame-firmware-release
plan: 02
subsystem: stub-server
tags: [byos, ota, hardware-claim]
requires: []
provides:
  - "X-Hw-Type contradiction handling in GET /device/v1/display"
affects: [stub-server/byos_server.py]
key-files:
  created: [stub-server/test_hw_claim.py]
  modified: [stub-server/byos_server.py]
decisions:
  - "A claim can only withdraw the offer and the container; the type always comes from fleet.db"
requirements-completed: [OTA-04]
completed: 2026-11-14
---

# Phase 57 Plan 02: X-Hw-Type server handling Summary

A well-formed X-Hw-Type that differs from the server-assigned type now withdraws the firmware offer and the image container (the frame gets the raw 960000-byte panel); a frame with no header, or a malformed one, is served exactly as before.

## What changed

- `stub-server/byos_server.py`: `_HW_TYPE_CLAIM_RE`, `claim_contradicts()`, a deduplicated `_log_claim_mismatch_once()` (mac and regex-validated claim only), `_UNSET` sentinel.
- `_handle_display` resolves the hardware type once (before any lock), passes `hardware_type=` and `withhold_offer=` to `_record_device_report_and_offer`, whose in-function resolution remains only as the default for direct callers. fw_version and ota_result are still recorded for a contradicting frame; no "offered" event is written.
- `_pending_response` drops the container on a contradiction (pending frames already carry `firmware: None`).
- The claim is never stored and added to no frozen header list.

## Commits

- b6b43e06: feat(57-02): withdraw firmware offer and container on a contradicting X-Hw-Type (both tasks; Task 2 needed no further edits)

## Verification (what ran)

Local venv built from `server/requirements-dev.txt` with `--require-hashes` (the `.venv` from the session hook was not present, so one was created in the scratchpad).

- `pytest stub-server/test_hw_claim.py test_image_negotiation.py test_phase47_freeze.py test_ota_offer.py`: 96 passed
- `pytest stub-server -n auto`: 383 passed, 1 skipped (root ignores directory permission bits)
- `pytest server -n auto`: 3540 passed, 3 skipped (root permission-bit skips)
- ruff on the two files, mypy (45 source files), `check_function_size.py check --max 80 server stub-server`, `check_comment_history.py check`: all clean
- `test_phase47_freeze.py`, `measured_fields_freeze.json`, `test_ota_offer.py` unmodified.

Not run: `./scripts/run-all-tests.sh` with the coverage gate (expects `server/.venv`), so the coverage floor was not measured locally; new code is fully exercised by test_hw_claim.py. Browser/companion tests not run.

## Deviations from Plan

None in behaviour. Notes: Task 2 produced no code changes, so there is one commit for both tasks. The fleet-frame and pending-frame variants use a real fleet.db row and the pairing flow rather than the simulated-hardware switch, since a made-up claim string suffices.

## Known Stubs

None.

## Self-Check: PASSED
