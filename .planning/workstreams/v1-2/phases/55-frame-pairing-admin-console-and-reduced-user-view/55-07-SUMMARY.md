---
phase: 55-frame-pairing-admin-console-and-reduced-user-view
plan: 07
subsystem: byos-device-protocol
tags: [pairing, byos, cli, backup, freeze]
requires: [55-02, 55-03, 55-05]
provides:
  - byos pending/retired enrolment and display branch (_handle_pending_display, _pending_panel, _issue_pairing_code)
  - GET /img/p_<id>/<sha>.bin route over pairing/<id>/img/
  - fleet_cli verbs register-pending, pending-list, retire, reactivate; pending-aware remove; assign through fleet_ops.reassign_frame
  - backup excludes pairing/; schema 3 rows covered by restore tests
  - stub-server/test_pairing_freeze.py (freeze siblings)
affects: [55-09, 55-10]
tech-stack:
  added: []
  patterns:
    - PendingContext outcome from _device_context, early return in _handle_display
    - pairing screens content-addressed under pairing/<pending id>/, never root img/
key-files:
  created:
    - stub-server/test_pending_pairing.py
    - stub-server/test_pairing_freeze.py
  modified:
    - stub-server/byos_server.py
    - stub-server/fleet_cli.py
    - stub-server/test_fleet_cli.py
    - deploy/backup/skypane_backup.py
    - deploy/tests/test_backup.py
key-decisions:
  - "Retired screen is stored as retired.bin (pairing screen as panel.bin) so a stale pairing image can never be served to a retired frame."
  - "A MAC present in both devices and pending_devices makes _fleet_view raise FleetDbError internally, which degrades to the legacy-files fallback and a fault status (fails closed) instead of preferring one table."
requirements-completed: [AUTH-04]
duration: ~45min
completed: 2026-10-31
---

# Phase 55 Plan 07: Device-side pairing Summary

A registered but unclaimed frame now enrols through the unchanged setup call and polls the unchanged display endpoint, receiving a rotating pairing code screen (300 s sleep); a retired frame receives the retired screen (86400 s sleep) and keeps a valid token; the live frame's path is byte-identical.

## Tasks and commits

| Task | Commit | Content |
|------|--------|---------|
| 1 | 3b06d39 | byos pending enrolment, display branch, image route, 12 subprocess tests |
| 2 | 65fe9b9 | CLI verbs, pending-aware remove, assign via fleet_ops, 7 new CLI tests |
| 3 | f4e093b | `pairing` in KNOWN_EXCLUDED, restore round-trip and no-drift tests, freeze siblings (3 tests) |

## Verification

- `pytest stub-server deploy/tests/test_backup.py`: 364 passed, 1 skipped (root permission-bit skip).
- `stub-server/test_phase47_freeze.py` green and unmodified; `measured_fields_freeze.json`, `hardware/`, `firmware/` untouched.
- ruff (whole repo), mypy (26 files), `check_comment_history.py check`, `check_function_size.py check --max 80 server stub-server` (811 functions): clean.

## Behaviour notes

- Pending enrolment writes the token to `pending_devices.token` only; `byos_state.json` and `devices.json` bytes are unchanged (tested).
- The pending branch never calls `_record_device_report_and_offer`, `save_battery_state` or `_record_device_health`; battery and firmware version go to the pending row via `touch_pending`. Root `img/`, `battery_state.json`, `poll_state.json` and `devices/` are untouched (tested).
- The code is issued inside one `BEGIN IMMEDIATE` transaction (re-reading the row), the plaintext exists only in the request and the pixels; `panel.bin` is mode 0600; one `pairing.issue` audit row per issue with actor label `frame:<pending id>`. A live unexpired code is never re-issued, so the hash is stable between wakes.
- `_apply_mirror` raises for a pending MAC (surfaced by `mirror_to_fleet` as a message, no devices row created).

## Deviations from Plan

- [Rule 2 - robustness] Retired image kept in `retired.bin` instead of `panel.bin` (see key decisions).
- Test 2 "no plaintext code in the database" runs in-process against `byos_server._pending_panel` with a monkeypatched generator, because byos is a subprocess in the other tests and cannot be monkeypatched; the subprocess tests assert the audit and column contents instead.
- argparse abbreviates `--secret` to `--secret-sha256`, so a `--secret <raw>` call is accepted syntactically and refused by the 64-hex validation (exit 2, nothing written); the test asserts that and that other raw-secret flag names are rejected.
- `fleet_cli main` now maps `fleet_ops.NotFound` to exit 1 and other `OpsError` (live-frame protected, duplicate, owner unavailable, busy) to exit 2.

## Notes for the owner

- **Behaviour change:** `fleet_cli devices assign` now goes through `fleet_ops.reassign_frame`: assigning a non-live frame wipes the previous owner's data and re-provisions it; the live frame only changes owner. Documented operator runbooks should say so.
- byos now imports `server.pairing_image` (Pillow) and `server.fleet_ops`; Pillow is already in the shared venv the service runs from (`server/requirements.txt`), but a byos deployed without it would fail at import.
- The pairing image URL space is unauthenticated and content-addressed like the existing image route (accepted, T-55-07-02).
- Unchanged firmware needs no change: it reads `image_url`, `image_hash`, `sleep_s` and ignores the rest; no firmware work was needed.
- Existing `test_devices_assign_keeps_one_owner` still passes unchanged (live frame owner change); no old-semantics test needed rewriting.

## Known Stubs

None.

## Threat Flags

None beyond the plan's register.

## Self-Check: PASSED

Files present: stub-server/test_pending_pairing.py, stub-server/test_pairing_freeze.py, this SUMMARY. Commits 3b06d39, 65fe9b9, f4e093b exist.
