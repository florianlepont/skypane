---
phase: quick-261117-edp
plan: 01
type: execute
autonomous: true
---

# Quick 261117-edp: device parameter on the battery-history export

Owner-approved 2026-11-17. The owner needs the second-hardware frame's
`device_health` history through the read-only bearer-token export.

## Task 1: `device=<id>` on `GET /api/export/battery-history` only

- Files: `companion/export_api.py`, `companion/test_export_battery_device.py`
- Action: accept exactly `since` plus one `device`; check the id against
  `device_dirs.DEVICE_ID_RE` before anything else; look it up in fleet.db
  (registered, else retired with kept data); build the directory from the
  stored state path through `device_dirs.resolve_state_dir`; read with
  `history_db.export_device_health` (read-only). Without `device` nothing
  changes.
- Verify: new behaviour tests plus the existing export tests.
- Done: 400 malformed/duplicate/other parameter, 404 unregistered, 503 no
  readable history.db, other routes still refuse `device`.

## Task 2: document it in `deploy/README.md`

- Route, parameter, errors, unknown ids refused.
