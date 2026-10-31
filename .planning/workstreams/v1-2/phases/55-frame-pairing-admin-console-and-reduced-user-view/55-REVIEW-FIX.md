---
phase: 55-frame-pairing-admin-console-and-reduced-user-view
fixed_at: 2026-10-31T00:00:00Z
review_path: .planning/workstreams/v1-2/phases/55-frame-pairing-admin-console-and-reduced-user-view/55-REVIEW.md
iteration: 1
findings_in_scope: 6
fixed: 6
skipped: 0
status: all_fixed
---

# Phase 55: Code Review Fix Report

A selected subset of the review was fixed. Each fix has behaviour tests that fail
on the previous code.

## Fixed

### CR-01: crash-safe directory wipe on reassign and re-activate

Files: `server/fleet_ops.py`, `companion/console_lifecycle.py`,
`companion/i18n_fr/admin_lifecycle.py`, tests in `server/test_fleet_ops.py` and
`companion/test_console_lifecycle.py`. Commit a3a17cbd.

- The device directory is renamed aside (same filesystem, inside the busy guard),
  the database and audit row are written, COMMIT runs, and only then is the
  renamed directory deleted. A failure before or at COMMIT rolls the database back
  and renames the directory back. A failed delete after COMMIT is logged and the
  renamed directory is left for cleanup; the frame already has a fresh empty
  provisioned directory.
- The live frame (state path ".") is never renamed or wiped.
- `handle_reassign` and `handle_reactivate` catch `OpsError`, `ValueError`,
  `OSError` and `sqlite3.Error`, write a `failed` audit row with a reason enum
  only (`refused`, `invalid_path`, `storage_error`) and show a new "Action failed"
  error flash (English and French) instead of a 500.
- One existing test (`test_failure_during_wipe_rolls_back_reassign`) patched
  `wipe_device_dir`, which the new flow no longer calls. It now injects the
  failure at `provision_device_dir` and `audit_append` and checks more (database
  dump and file tree unchanged, no leftover directory). No test was removed.

### WR-02: location and settings save consistency

Files: `companion/pages/config_page.py`, `companion/console_locations.py`,
`companion/test_location_picker.py`. Commit eeb268c8.

When `save_device_config` fails after a location was assigned, the previous
location is restored and an audited `failed` row is written next to the original
`ok` row, so the form is never half-applied and the "save failed" flash is true.
A failure of the later calendar-URL write is unchanged (the settings were already
saved at that point).

### Info items

- State path check and claim id check (IN-02), commit a3a17cbd:
  `reassign_frame` and `reactivate_frame` refuse (`OpsError`) unless the stored
  path equals `devices/<the frame's own id>`. `claim_pairing_code` regenerates
  the device id (savepoint, up to 8 tries) when `devices/<id>` already exists,
  so an existing directory is never inherited or deleted.
- Id regexes (IN-04), commit a40b7f11: `\A...\Z` in `console_users.py` and
  `console_locations.py`.
- Location names (IN-05), commit a40b7f11: categories `Cf` are stripped as well
  as `Cc`, `Zl` and `Zp`.
- Usage counts (IN-03), commit a40b7f11: `fleet_db.location_usage_counts` takes an
  optional owner; non-admins see counts of their own frames, admins keep the
  global count. Deleting a location used by a foreign frame is still refused.

## Left out (by instruction)

- WR-01 (live-frame reassign keeps previous data): owner decision D-13.
- WR-03 (CSRF scope): owner decision D-20.
- WR-04 (CLI wipes without busy guard) and IN-01, IN-06 to IN-09: reported to the
  owner by the orchestrator.

---

_Fixed: 2026-10-31_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
