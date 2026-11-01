# Phase 60 handoff

Phase 60 delivers device co-management. It is complete in code on branch
`milestone/v1.2-phase-60-co-management` (PR #276). Nothing was deployed and
nothing was merged: CI deploys on merge to main, so the merge is the owner's
decision. No real Auth0 tenant, secret or address is used in the repository.

Related: [`deploy/README.md`](../../../../../deploy/README.md) section
"Schema v4 and rollback", [`60-CONTEXT.md`](60-CONTEXT.md),
[`60-UI-SPEC.md`](60-UI-SPEC.md), [`60-VALIDATION.md`](60-VALIDATION.md).

## A. What was built

| Plan | Result | Names |
|------|--------|-------|
| [60-01](60-01-SUMMARY.md) | fleet.db schema 4: expand-only table `device_co_managers`, one index, two owner-exclusion triggers; co-manager API with in-transaction eligibility | `server/fleet_db.py` (migration 4, co-manager helpers, typed errors, audit action names) |
| [60-02](60-02-SUMMARY.md) | reassign, retire, hard delete and the legacy-registry mirror clear co-manager rows in the same transaction and audit one `device.co_manager_remove` per user; a co-manager can assign only the owner's location | `fleet_ops.reassign_frame`, `fleet_ops.retire_frame`, `fleet_db.park_retired`, `fleet_db.remove_device`, `fleet_db.set_device_location_checked` |
| [60-03](60-03-SUMMARY.md) | ownership gate admits a co-manager; new `OWNER_ONLY_DEVICE` kind; per-request, uncached, fail-closed membership lookup | `companion/access.py`, `route_types.OWNER_ONLY_DEVICE`, `Handler._co_manager_lookup` |
| [60-04](60-04-SUMMARY.md) | device list includes co-managed frames; Detection scoped to the owner's locations with no location writes; HTTP proof of reach and exclusion | `device_scope._co_managed_ids`, `detection_actions.Subject.may_write`, `LocationScope.may_edit` |
| [60-05](60-05-SUMMARY.md) | `POST /co-managers/add`, `/co-managers/remove`, `/co-managers/leave` with CSRF, one uniform add refusal, audit rows, flash keys and labels (EN/FR) | `companion/co_managers.py`, `companion/pages/co_managers_card.py`, `companion/i18n_fr/co_managers.py` |
| [60-06](60-06-SUMMARY.md) | Co-managers card on Home (manage, read-only, leave shapes), Account "Shared" pill with the owner's address, own-and-co-managed filter, leave toast | `home_page.render(co_managers_html=)`, `account_page.FrameSummary.shared`, `sign_in._own_frame_summaries` |
| [60-07](60-07-SUMMARY.md) | co-manager column and owner-only kind in the route x role x owner matrix; live-frame immutability proof | `test-support/matrix_rows_co_managers.py`, `stub-server/test_co_manager_live_frame.py` |
| [60-08](60-08-SUMMARY.md) | 19 real-browser tests at 360 px (EN/FR, both themes); one layout defect fixed with one CSS rule | `companion/test_browser_co_managers.py`, `#co-manager-person { max-width: 100%; }` |

## B. This phase touches Phase 55 code

The list is computed, not hard-coded: the intersection of
`git diff --name-only origin/main...HEAD` (66 files) and the files changed by
the commits matching `Phase 55` (`git log --grep="Phase 55"`, then
`git show --name-only --format=`), planning files excluded. The base is
`origin/main` (`aa1fdced`), not the local `main` ref: the local `main` is stale
(`42aa0337`, before PRs #259 to #274), so `main...HEAD` would also list all the
already merged Phase 55 work. The result matches the files the plan SUMMARYs
name (`server/fleet_db.py`, `server/fleet_ops.py`, `companion/app.py`,
`companion/route_types.py`, `companion/device_scope.py`, `companion/routes.py`,
`companion/pages/home_page.py`, `companion/static/style.css`,
`companion/pages/audit_page.py`, `companion/pages/account_page.py`,
`companion/sign_in.py`, `companion/i18n_fr/admin_lifecycle.py`,
`companion/i18n_fr/account.py`, `deploy/README.md`); the rest of the list is
test and test-support files. No mismatch.

Code files:

| File | Minimal change | Plan |
|------|----------------|------|
| `server/fleet_db.py` | migration 4 and co-manager helpers; `park_retired` calls `clear_co_managers`; `remove_device` gains an optional `actor`; location permission block | 60-01, 60-02 |
| `server/fleet_ops.py` | `reassign_frame` deletes and audits the new owner's membership; `retire_frame` audits one removal per co-manager | 60-02 |
| `companion/app.py` | `_dispatch` passes the extra argument to `access.decide`; `Handler._co_manager_lookup` | 60-03 |
| `companion/route_types.py` | new `OWNER_ONLY_DEVICE`; `OWNER_DEVICE` uses `access.DEVICE_ARG` | 60-03 |
| `companion/device_scope.py` | private `_co_managed_ids`; the user branch of `load_devices_for` keeps owned or co-managed rows | 60-04 |
| `companion/routes.py` | three Route entries, three `_ACTION_KEYS`, the `OWNER_ONLY_DEVICE` export, the Home route entry | 60-05, 60-06 |
| `companion/pages/audit_page.py` | two `ACTION_LABELS` entries | 60-05 |
| `companion/i18n_fr/admin_lifecycle.py` | two French strings | 60-05 |
| `companion/pages/home_page.py` | optional `co_managers_html` argument (default empty, output byte-identical) | 60-06 |
| `companion/static/style.css` | appended `.co-manager__*` block and `#co-manager-person { max-width: 100%; }` | 60-06, 60-08 |
| `companion/pages/account_page.py` | defaulted `shared` and `owner_email`; Shared pill | 60-06 |
| `companion/sign_in.py` | own-and-co-managed frame filter; leave toast | 60-06 |
| `companion/i18n_fr/account.py` | two French strings | 60-06 |
| `deploy/README.md` | new "Schema v4 and rollback" section | 60-01 |

Test and test-support files (co-manager cases and rows added, no assertion
weakened): `companion/test_access_matrix.py`, `companion/test_console_locations.py`,
`companion/test_csrf.py`, `companion/test_device_scope_owner.py`,
`companion/test_route_table.py`, `companion/testdata/render_baseline.json`,
`server/test_fleet_migrate.py` (the downgrade helper also drops the v4 objects),
`server/test_fleet_schema3.py` (version-relative),
`test-support/companion_render_snapshot.py` (three co-manager routes in the
capture list).

## C. Verification evidence

Run on the final tree with the real browser (`SKYPANE_REQUIRE_BROWSER=1`, the
Chromium 1243 builds linked under the names Playwright 1.64.1 expects through
`PLAYWRIGHT_BROWSERS_PATH`; no install, nothing in the repository changed).

- `./scripts/run-all-tests.sh`: exit 0, 8683 passed, 8 skipped, 0 failed;
  coverage 96.21 percent against the 93.0 percent floor (unchanged). The 8
  skips are 7 "root ignores permission bits" tests and 1 "openssl could not
  backdate a certificate"; none is a browser test. An earlier run of the same
  command had one failure, `companion/test_browser_airline_sheet.py::test_a_refused_name_reopens_the_sheet_with_the_error`
  (a file this phase does not touch); the module passed 3 of 3 alone (20 tests
  each) and the full rerun passed, so it is load flakiness under `pytest -n auto`,
  not a defect of this phase. It is worth watching.
- `ruff check .`: clean. `mypy` (CI invocation): no issues in 28 source files.
  `check_function_size.py check --max 80 server stub-server`: 921 functions,
  none over 80. `check_comment_history.py check`: clean.
- `pytest companion/test_i18n.py companion/test_suite_guards.py deploy/tests/test_backup.py deploy/tests/test_activate.py stub-server/test_phase47_freeze.py`: 307 passed.
- The dry-run text "upgrade fleet.db schema 3 -> 4" is emitted by
  `server/fleet_migrate.py` and asserted version-relative in
  `server/test_fleet_migrate.py` (`would upgrade fleet.db schema 1 -> SCHEMA_VERSION`);
  `deploy/tests/test_activate.py` only checks that `activate.sh` runs the dry run
  before the real migration. The literal "3 -> 4" line is for the owner to see on
  the real server (section E).
- No floor decrease, no test deleted, no guard weakened in `git diff`.

Constraint diff guard (change list = `git diff --name-only origin/main...HEAD`,
`git diff HEAD --name-only` and `git ls-files -o --exclude-standard`, so
untracked directories and renames are read at their new path): non-empty;
contains the ROADMAP.md edit, `60-HANDOFF.md`, `server/fleet_db.py` and
`companion/routes.py`; no path under `hardware/` or `firmware/`; none under the
Phase 47, 55 or 58 planning directories; `stub-server/test_phase47_freeze.py`
and `stub-server/byos_server.py` unchanged; ROADMAP.md and STATE.md hunks (also
from `git diff HEAD`) carry only Phase 60 lines (the phase-list entry, the nine
plan checkboxes, the progress row, one STATE line); REQUIREMENTS.md unchanged;
no merge commit in `origin/main..HEAD`; nothing pushed. The secret-pattern grep
over added lines shows identifiers and test fixtures only. Result: exit 0.

## D. Visible consequence of the one-owner rule

A non-live reassign wipes the previous owner's data, location and name but
keeps the other co-managers, who then manage the new owner's fresh frame. The
new owner's own membership row, if any, is removed at the same time and audited.
Retire and hard delete remove every co-manager row and audit one removal per user.

## E. What stays with the owner

- Nothing was deployed or merged. PR #276 is for the owner to merge; CI deploys
  on merge to main.
- Run the `activate.sh` dry run and confirm it prints
  `upgrade fleet.db schema 3 -> 4`.
- Accept or reject the rollback behaviour in `deploy/README.md` "Schema v4 and
  rollback": the previous release refuses schema 4 and falls back to the legacy
  files, so co-managers lose companion access while rolled back.
- Restore a schema-4 backup into a scratch directory and open it.
- On the live Orly frame, check on a real phone that adding a co-manager leaves
  the poll and the image unchanged (the automated proof is
  `stub-server/test_co_manager_live_frame.py`).
- Production trials of the owner and admin flows on real accounts.
- Confirm the privacy choice: owners type an address and never see the invited
  list; admins pick from the list of eligible people.
- Confirm the French wording ("co-gestionnaire", the frame noun "cadre").
- Auth0 invitations still happen outside this feature.
- AUTH-08 in `REQUIREMENTS.md` is not ticked: mark it complete after the checks
  above.
- The D-03 consequence in section D is accepted as designed.

## F. Deferred and out of scope, unchanged

Notifications to co-managers, per-co-manager permission levels, view-as-user.

## Frozen paths

Phase 47 files, `hardware/` and `firmware/` were not touched, nor Phase 58 files
or any Phase 55 planning file.
