---
phase: quick-261102-r7x
plan: 01
status: complete
subsystem: companion / audit page
tags: [audit, co-managers, i18n]
key-files:
  modified:
    - companion/pages/audit_page.py
    - companion/console_lifecycle.py
    - companion/i18n_fr/admin_lifecycle.py
    - companion/test_browser_console.py
  created:
    - companion/test_audit_co_manager_detail.py
metrics:
  completed: 2026-11-02
---

# Quick 261102-r7x: Audit page shows who and why for co-manager rows

Successful `device.co_manager_add` / `device.co_manager_remove` rows now show
the person's e-mail (looked up in the users table at render time) and a plain
reason label, in both the card list and the desktop table. The stored detail
is still never rendered.

## What changed

- `console_lifecycle._co_manager_note` reads the detail only for those two
  actions with outcome `ok`, takes the two whitelisted keys
  `co_manager_user_id` and `via`, and resolves the id to an e-mail. A missing
  or unknown id gives "Unknown user"; unparsable detail gives an empty note.
- `audit_page` maps `(action, via)` through `REASON_LABELS`; anything else is
  "Other reason". Everything is HTML-escaped. The e-mail uses the existing
  `co-manager__email` wrapping class; no new CSS.
- Denied and failed rows (reason codes `malformed`, `unknown`, `ineligible`,
  `duplicate`, `write`) show no person and no reason: the typed address is
  never stored, and the codes are not shown.

## Via values found and labels

| Action | via | English | French |
|---|---|---|---|
| add | owner | Added by the frame owner | Ajouté par le propriétaire du cadre |
| add | admin | Added by an administrator | Ajouté par un administrateur |
| remove | self | Left the frame | A quitté le cadre |
| remove | owner | Removed by the frame owner | Retiré par le propriétaire du cadre |
| remove | admin | Removed by an administrator | Retiré par un administrateur |
| remove | reassign | Frame reassigned to a new owner | Cadre réattribué à un nouveau propriétaire |
| remove | retire | Frame retired | Cadre retiré |
| remove | delete | Frame deleted | Cadre supprimé |
| remove | owner_disabled | Frame owner was disabled | Le propriétaire du cadre a été désactivé |
| any other | any other | Other reason | Autre raison |

Written by: `companion/co_managers.py` (owner, admin, self),
`fleet_db.remove_device` (delete), `fleet_db._remove_owned_co_managers`
(owner_disabled), `fleet_ops.reassign_frame` (reassign),
`fleet_ops.retire_frame` (retire). `park_retired` writes no co-manager audit.

## Touches Phase 55 code

- `companion/pages/audit_page.py`: the module invariant "the stored detail JSON
  is never rendered" is kept and reworded; the page now also receives a
  `CoManagerNote` (e-mail and reason word chosen by the caller from a
  whitelist). `AuditEvent` gained an optional trailing `note` field, so
  existing constructors still work.
- `companion/console_lifecycle.py`: `_event` now builds the note; adds one
  users-table lookup per co-manager row on the Audit page.
- `companion/i18n_fr/admin_lifecycle.py`: 13 new ids.
- Existing audit tests were not modified.

## Verification

- Gates: ruff, mypy, comment-history, function-size, Phase 47 freeze test all
  pass.
- `./scripts/run-all-tests.sh` (no arguments): 8720 passed, 8 skipped.
- New tests: 18 behaviour tests in `companion/test_audit_co_manager_detail.py`
  (add by owner/admin, remove by owner/admin, leave, reassign, owner disable,
  retire, delete, unknown via, unknown/missing user, no raw detail, malformed
  detail, escaping, other actions unchanged, French) and 2 browser tests (1000
  px and 360 px, long e-mail, person and reason visible, no horizontal scroll).

## Deviations

None. Browser desktop width used is 1000 px as requested (the shared
`VIEWPORT_DESKTOP` is 1280).
