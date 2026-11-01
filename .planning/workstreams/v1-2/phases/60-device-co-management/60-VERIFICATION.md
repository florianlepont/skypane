---
phase: 60-device-co-management
verified: 2026-11-01T00:00:00Z
status: human_needed
score: 4/4 roadmap criteria verified in code
human_verification:
  - test: "Owner go-live checklist in 60-HANDOFF.md (deploy after merge, live Orly frame check, accept rollback caveat)"
    expected: "Live frame unchanged after migration to schema 4; previous release refuses schema 4 as documented"
    why_human: "No merge or deploy was done; production behaviour and the rollback trade-off need the owner's decision"
---

# Phase 60: Device Co-Management Verification

Goal: a frame keeps exactly one primary owner and can also be managed by co-managers, added by the owner or by an admin.

Initial verification, no previous VERIFICATION.md. Branch `milestone/v1.2-phase-60-co-management`. No gaps found.

## Roadmap criteria

| # | Criterion | Status | Evidence |
|---|-----------|--------|----------|
| 1 | Co-manager views and changes settings like the owner, cannot retire, reassign or remove the owner | VERIFIED | `companion/access.py` `authorized_device_id` admits a co-manager through the injected `is_co_manager` for `OWNER_DEVICE` routes. The lookup is read on every request in `app.py` `_co_manager_lookup` and fails closed on `OperationalError`. Retire, reassign and reactivate live only under `console_routes` (ADMIN_ONLY); no `OWNER_DEVICE` route exists in `console_routes.py`. `test_co_manager_access.py` has HTTP tests for display, rules, airline and detection changes by a co-manager and a 404 on retire, reassign, reactivate and every admin page. The only code that deletes membership rows is `co_managers._remove_row`, which cannot touch `devices.owner_user_id`. |
| 2 | Owner and admin add and remove among invited users; a co-manager cannot add | VERIFIED | `routes.py` registers `/co-managers/add` and `/co-managers/remove` as `OWNER_ONLY_DEVICE` with `csrf=True`. `access.decide` sets `allow_co_manager = False` for `device-owner`, so a co-manager gets 404. `fleet_db.find_eligible_co_manager` and `add_co_manager` check invited, non-disabled, non-owner and non-duplicate inside one `BEGIN IMMEDIATE`. `test_co_managers.py::test_a_co_manager_or_stranger_cannot_add_or_remove` covers the refusal. |
| 3 | Non-owner non-co-manager still gets 404; matrix has co-manager rows | VERIFIED | `test_access_matrix.py` has a fifth principal `co-manager` and an `owner-only-device` kind (co-manager gets not-found). `matrix_rows_co_managers.py` registers the three new routes. A parametrised test checks a co-manager of frame A against frame B on every `OWNER_DEVICE` route, with a 404 body identical to the unknown-path 404. `test_a_stranger_gets_404_for_the_shared_frame` and the after-removal 404 tests also exist. |
| 4 | One-primary-owner rule holds; add and remove audited | VERIFIED | Migration `_migrate_v4` creates the table with PK (device_id, user_id), plus two triggers. `device_co_managers_not_owner` blocks inserting the owner. `devices_owner_not_co_manager` blocks making a co-manager the owner. `fleet_ops.reassign_frame` deletes the new owner's membership and audits it before the owner update, in the same transaction. `retire_frame`, `park_retired` and `remove_device` clear and audit membership rows in the same transaction. `audit.record_in` shares the transaction in `handle_add` and `_remove_row`, so an audit failure rolls the change back. Refusals are audited as `denied` with a short internal reason and no address. |

## Specific risks probed

- **Co-manager reaching an ADMIN_ONLY route or retire/reassign:** not possible. The gate only affects device-scoped routes. Admin routes check role first, and tests assert 404 for a co-manager on the admin pages and lifecycle routes.
- **Invited users' e-mails leaking to non-admins:** the candidate list (`eligible_co_manager_candidates`) is filled only when `principal.role == ADMIN` (`co_managers._card_view`). A non-admin owner sees only a typed field. All add failures end in the same flash key and the address is never echoed. Co-managers and the owner see the owner's and members' e-mails on a shared frame, as locked in D-06. An owner can still learn whether a typed address is invited from success versus refusal; this is inherent to D-08, so it is informational.
- **Add by a co-manager:** blocked at the gate (`OWNER_ONLY_DEVICE`). Leave reads no form and only deletes the caller's own row.
- **CSRF:** all three POST routes carry `csrf=True`. Forms embed `layout.csrf_field()`. `test_csrf.py` and `test_route_table.py` were updated and pass.
- **Atomicity:** verified in code, see criterion 4.
- **Membership surviving an owner change:** only the new owner's own row is dropped, which is by design in D-03. The triggers cover any other path. `assign_owner` has no non-test caller.
- **Freeze:** `git diff origin/main --name-only` shows no `firmware`, `hardware` or `stub-server/test_phase47_freeze.py` change. The only new stub-server file is `test_co_manager_live_frame.py`. The migration is expand-only (one table, one index, two triggers). `git diff origin/main -- .planning/workstreams/v1-2/phases/55-*` is empty. The ROADMAP and STATE diffs touch only Phase 60 lines.

## Behavioural checks run

`server/.venv/bin/python3 -m pytest -n auto --no-cov` on the 18 co-management, access, matrix, CSRF, route-table, schema 3 and 4, cascade, detection, live-frame, freeze, suite-guard and browser test files, with `SKYPANE_REQUIRE_BROWSER=1` and the supplied Playwright path: **1991 passed** (includes `test_phase47_freeze.py` and `test_browser_co_managers.py`). `ruff check` passes. `mypy` reports no issues in 28 files. `check_comment_history.py check` exits 0. `check_function_size.py check --max 80 server stub-server` finds no function over 80 lines. I did not run the full suite or the coverage gate.

## Requirements

AUTH-08 (co-managers): code-satisfied per criteria 1 to 4. The checkbox is intentionally left unchecked until the owner's go-live checks (see STATE).

## Anti-patterns

No TBD/FIXME/XXX and no plan or phase IDs in code comments in the changed code (guard passes). No stubs found.

## Human verification

The owner must run the go-live checklist in 60-HANDOFF.md after merge. There is a rollback caveat: the previous release refuses schema 4.

## Gaps

None.
