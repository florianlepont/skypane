# Phase 60: Device Co-Management - Research

**Researched:** 2026-11-01
**Domain:** Per-device authorization (second principal class on an ownership gate), fleet.db migration v4, audit, companion UI
**Confidence:** HIGH (every claim below was read from the repository in this session; no external libraries are involved)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** A "Co-managers" card on the frame's own page. Owner and admin get add/remove controls; a co-manager sees it read-only. The admin console may link to it but needs no separate add flow.
- **D-02:** A co-manager can leave a frame ("Leave this frame" button). It is audited as a removal and is the only removal a co-manager can perform; it never touches anyone else.
- **D-03:** When an admin reassigns the owner to a user who is already a co-manager, that co-manager row is deleted in the same transaction and the removal is audited. Other co-managers are kept. A frame owner is never also a co-manager.
- **D-04:** A co-manager sees and assigns only the frame owner's locations (existing rule "a location of another owner is refused"). They create and edit no location on the owner's behalf. No relaxation of `fleet_db` location ownership.
- **D-05:** Any invited, non-disabled user, including one who has not signed in yet; admins are eligible. Excluded: the owner and users already co-managers. Disabled users keep their rows but cannot sign in.
- **D-06:** A co-manager sees the owner's and all co-managers' e-mail addresses on the frame page (read-only).
- **D-07:** The live Orly frame is managed like any other: it may have co-managers. This adds rows to a new table only; owner, MAC, secret, token, file paths, image and wake interval stay byte for byte, and `stub-server/test_phase47_freeze.py` stays green.

### Claude's Discretion
Schema shape (migration v4, expand-only new table with a uniqueness constraint and no row for the owner), function names, audit action names and detail text, wording and French strings, card layout within the sketch-findings design system, Users-page frame counts, behaviour on user demotion or disabling.

### Deferred Ideas (OUT OF SCOPE)
- Notifying a user when added as co-manager.
- Per-co-manager permission levels.

Also out of scope (CONTEXT domain): any production deploy, Phase 47 files and `hardware/`, Phase 55 planning lines, Phase 58 files, view-as-user (AUTH-07), notifications to co-managers.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| AUTH-08 | A frame keeps one primary owner and can have co-managers who change its settings like the owner but cannot retire, reassign or remove it. The owner and an admin can add or remove co-managers among already-invited users, and each change is audited. | Sections "Ownership read sites", "Migration v4", "Route and access design", "Audit", "Location rules", "UI", "Pitfalls", "Validation Architecture" |
</phase_requirements>

## Summary

Ownership is read in exactly five production places, and only three of them gate access or scope the data a user sees: `access.authorized_device_id` (via `Handler._owner_lookup`, `companion/app.py:606`), `device_scope.load_devices_for` (the device list, selector, Account list, Referer redirect), and `detection_actions.subject_for` plus `fleet_db.set_device_location_checked` (location scoping). The other two (`console_locations._viewer_options`, `sign_in._own_frame_summaries`) already do the right thing for co-managers by construction, or need a one-line change. Everything else in the companion keys off the frame id handed over by the gate, so a co-manager who passes the gate gets the owner's full device-page behaviour with no further change. Retire, reassign, reactivate, `/device`, `/update` and `/quick/led` are `ADMIN_ONLY` and so already exclude co-managers.

The design is small: migration v4 adds one table `device_co_managers (device_id, user_id)` with a composite primary key; `access.decide`/`authorized_device_id` get one optional callable (`is_co_manager`) so the existing 4-argument calls and `test_access.py` stay valid; one new access kind (owner-or-admin, not co-manager) is needed for add/remove because the current `Access` vocabulary has only "owner, co-manager (after this phase) or admin" and "admin". The riskiest parts are not the gate but three side effects: (1) `fleet_db.park_retired` and `remove_device` do `DELETE FROM devices`, which will raise an `IntegrityError` under `PRAGMA foreign_keys=ON` as soon as a co-manager row references the frame; (2) `set_device_location_checked` currently compares the location owner to the acting user, which would refuse every co-manager assignment (D-04 needs it compared to the device owner); (3) `device_scope._fleet_rows` swallows every `sqlite3.Error` into `[]`, so a co-manager query placed inside it would silently hide all frames when the table is absent.

**Primary recommendation:** Add table `device_co_managers` in `_migrate_v4` (FK to `devices(id)` and `users(id)`, no cascade, `PRIMARY KEY (device_id, user_id)`), one `fleet_db` module section of small helpers that run inside `BEGIN IMMEDIATE`, inject `is_co_manager` into the gate beside `owner_lookup`, add the three POST routes `co-managers/add|remove|leave` as device-scoped routes with a new owner-or-admin access kind for add/remove, render the card on Home outside every freshness swap selector, and extend `reassign_frame`, `park_retired`/`retire_frame`, `set_device_location_checked`, `subject_for` and `_own_frame_summaries` as listed below.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Who may reach a frame (owner, co-manager, admin) | API / Backend (`companion/access.py`, `app.py` dispatcher) | Database (`fleet_db`) | Default-deny gate runs before any handler; 404 uniformity is a dispatcher property |
| Co-manager membership storage and invariants | Database (`fleet_db` table, PK, FK, trigger) | API (`fleet_db` helpers) | Uniqueness and "never the owner" must hold even under concurrent requests |
| Add / remove / leave actions and audit | API / Backend (new handler module) | Database (one `BEGIN IMMEDIATE` per action) | State change and audit row must commit together (existing pattern) |
| Reassign / retire side effects on membership | API (`server/fleet_ops.py`) | Database | Same transaction as the owner change / device delete (D-03, FK safety) |
| Location scoping for co-managers | API (`detection_actions`, `fleet_db.set_device_location_checked`) | — | Existing owner-of-location rule moves from "acting user" to "device owner" |
| Co-managers card, Account "shared" mark, French strings | Frontend Server (SSR page modules, `i18n_fr`) | — | All UI is server-rendered, bilingual, no client JS needed |

## Standard Stack

No new libraries. Stack is the shipping one: Python stdlib `sqlite3`/`http.server`, existing `companion` modules, pytest, pytest-xdist, pytest-playwright (already in `server/requirements-dev.txt`, hash-locked). [VERIFIED: codebase, `.claude/CLAUDE.md` and `pyproject.toml`]

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| sqlite3 (stdlib) | Python 3.13 locally (`server/.venv`), 3.14 in production | New table, triggers, transactions | Already the fleet store; migrations are index-based |
| pytest 9.1.1 + xdist + cov | installed in `server/.venv` | All tests | Project gate `./scripts/run-all-tests.sh` |
| playwright 1.64.1 (python) | installed | Browser tests for the card | A missing browser fails CI |

**Installation:** none. **Package Legitimacy Audit:** no external package is installed or recommended by this phase, so there is nothing to audit. `slopcheck` was not run (nothing to check).

## Architecture Patterns

### Ownership read sites (complete inventory)

| # | Site | What it does today | Change for AUTH-08 |
|---|------|-------------------|--------------------|
| 1 | `companion/access.py::authorized_device_id` (called by `decide` for every `device_arg` route) | admin: any existing device; user: `owner == principal.user_id` | Add optional `is_co_manager=None` callable `(device_id, user_id) -> bool`; allow when it returns true. Keep malformed-id refusal before any lookup. `decide()` gets the same optional arg and forwards it. `test_access.py` 4-arg calls stay valid. |
| 2 | `companion/app.py:606 Handler._owner_lookup` and the call at `app.py:1019` | `fleet_db.get_device_owner(self._fleet_conn(), id)` | Add sibling `Handler._co_manager_lookup(device_id, user_id)` using `self._fleet_conn()`; pass it to `access.decide`. `_effective_access` needs no change. |
| 3 | `companion/device_scope.py::load_devices_for` | admin/None: all; user: rows with `owner_user_id == user_id`, no synthetic live fallback | Union with frames where the user is a co-manager. Query in a separate helper with its own try/except returning an empty set (see Pitfall 3). `Device.owner_user_id` is unchanged, so every `device.owner_user_id` consumer keeps meaning "primary owner". |
| 4 | `companion/detection_actions.py::subject_for` (L47-58) and `scope_for` | non-admin: `subject_id = actor_id`; location list = actor's own | If actor is a non-owner co-manager: `subject_id = owner_id` (so the picker lists the owner's locations and `_may_see_location` shows the current one) and mark the subject as not allowed to write locations. `_save_location` refuses with `ERROR_LOCATION_UNAVAILABLE` (existing "location_form" error path) before `_write_location` runs. Add a defaulted field to `detection_page.LocationScope` (it already has `defaults`) so the page can hide the create/edit form. |
| 5 | `server/fleet_db.py::set_device_location_checked` (also called by `console_locations.py:499` for the Display picker) | non-admin must be owner of the device AND owner of the location | Non-admin allowed when owner OR co-manager; location owner must equal the **device owner** (not the actor). Identical behaviour for owners; admins unchanged. One change covers both callers. |
| 6 | `companion/console_locations.py::_viewer_options` (L405-421) | non-admin: `list_locations_for(conn, device.owner_user_id)` | No change: already lists the frame owner's locations, which is D-04. Add a test only. |
| 7 | `companion/sign_in.py::_own_frame_summaries` (L231-254) | iterates `load_devices_for`, then skips `device.owner_user_id != principal.user_id` | Remove the skip for co-managed frames, add `shared=True` to `account_page.FrameSummary` (new defaulted field) and render a "Shared" mark and the owner e-mail (D-06 allows it). |
| 8 | `fleet_db.list_users_with_frame_counts` (`frame_count` = owned) | counts `devices.owner_user_id = u.id` | Discretionary. Recommended: keep `frame_count` as owned and leave the Users page unchanged (smallest change, no new column in a test-pinned shape). Optionally add a second correlated subquery `shared_count`. |
| 9 | `fleet_ops.reassign_frame`, `fleet_ops.retire_frame` / `fleet_db.park_retired`, `fleet_db.remove_device` | owner update; `DELETE FROM devices` | See Pitfalls 1 and 2. |
| 10 | `device_dispatch._user_referring_tab` | uses `current_devices()` | No change; automatically includes co-managed frames. |
| 11 | `console_pairing.py:130`, `console_lifecycle.py:209`, `pages/fleet_page.py` | previous owner / same-owner refusal / owner column | No change. `_reassign_refusal` compares to the primary owner only. |

Nothing in `stub-server/byos_server.py`, the poll cycle or `device_coordinates` reads ownership (grep over `owner_user_id`, `get_device_owner`, `owner_lookup`), so frame behaviour is unaffected by co-managers (D-07).

### Recommended structure
```
server/fleet_db.py              # _migrate_v4 + co-manager helpers (one section)
server/fleet_ops.py             # reassign_frame / retire_frame extended; ACTION_CO_MANAGER_* constants
companion/access.py             # optional is_co_manager arg
companion/co_managers.py        # NEW: handlers add/remove/leave + card view builder (stdlib only)
companion/pages/co_managers_card.py  # NEW: pure markup for the card (takes a view tuple)
companion/routes.py             # declare the 3 POST routes (device-scoped, csrf)
companion/i18n_fr/co_managers.py     # NEW French catalogue (area "co_managers")
test-support/matrix_rows_co_managers.py  # NEW matrix rows, merged in test_access_matrix.py
```
Function-size gate (`scripts/check_function_size.py`, max 80 lines over `server` and `stub-server`) applies to the `fleet_db`/`fleet_ops` code: keep each helper short. mypy runs over a module list in `pyproject.toml`'s `[tool.mypy]`; `server/fleet_db.py` and `fleet_ops.py` are typed (`from __future__ import annotations`), so new helpers there need annotations. [VERIFIED: file headers and CLAUDE.md]

### Migration v4 design (expand-only)

```python
# Source: pattern of server/fleet_db.py _migrate_v3 (read this session)
def _migrate_v4(conn: sqlite3.Connection) -> None:
    # Expand-only: one new table and its index; no existing table changes.
    conn.execute(
        "CREATE TABLE device_co_managers ("
        " device_id TEXT NOT NULL REFERENCES devices(id),"
        " user_id INTEGER NOT NULL REFERENCES users(id),"
        " added_by INTEGER,"            # no FK: the trail must outlive a user row (as audit_log)
        " added_at INTEGER NOT NULL,"
        " PRIMARY KEY (device_id, user_id))"
    )
    conn.execute("CREATE INDEX device_co_managers_user ON device_co_managers (user_id)")
    # Defence in depth for "a frame owner is never also a co-manager":
    conn.execute(
        "CREATE TRIGGER device_co_managers_not_owner BEFORE INSERT ON device_co_managers "
        "WHEN NEW.user_id = (SELECT owner_user_id FROM devices WHERE id = NEW.device_id) "
        "BEGIN SELECT RAISE(ABORT, 'owner cannot be a co-manager'); END"
    )
    conn.execute(
        "CREATE TRIGGER devices_owner_not_co_manager BEFORE UPDATE OF owner_user_id ON devices "
        "WHEN EXISTS (SELECT 1 FROM device_co_managers "
        "WHERE device_id = NEW.id AND user_id = NEW.owner_user_id) "
        "BEGIN SELECT RAISE(ABORT, 'new owner is a co-manager'); END"
    )

MIGRATIONS = (_migrate_v1, _migrate_v2, _migrate_v3, _migrate_v4)   # SCHEMA_VERSION = len(...) follows
```

Mechanics (all verified in `fleet_db.py`):
- `migrate_schema` applies each step in `BEGIN IMMEDIATE` together with `PRAGMA user_version`, re-reads the version inside the lock (concurrent upgraders are safe), and `SCHEMA_VERSION = len(MIGRATIONS)`. Appending one function is the whole mechanism. The `fleet_migrate` plan and `activate.sh` dry-run print `upgrade fleet.db schema 3 -> 4` automatically (`fleet_migrate.py:201`).
- No `ALTER`, no write to `devices`, `users`, `locations`: D-07 holds (owner, MAC, secret, token, `state_path`, files untouched). The two triggers only fire on future writes.
- `PRAGMA foreign_keys=ON` is set per connection in `_apply_pragmas`, so the FKs are enforced everywhere `connect()` is used. Nothing cascades by project invariant, therefore deletes of devices must delete membership rows explicitly (Pitfall 1).
- "Previous release still works on migrated state" needs an honest reading: the previous release (SCHEMA_VERSION 3) **refuses** a schema-4 file (`FleetDbTooNew`, `_refuse_if_too_new`) and falls back to the legacy files, exactly as the README documents for v2 and v3 (`deploy/README.md` "Schema v3 and rollback"). The migration is expand-only (old code that could open it would still read every old table unchanged), and the frame in production keeps working from the legacy files, which is what `test_previous_release_readers_still_accept_the_migrated_state` in the freeze test actually proves (it uses the byos legacy loaders). Co-managers lose access while rolled back (they cannot reach the companion fleet store). Add a "Schema v4 and rollback" paragraph to `deploy/README.md` mirroring the v3 one. [VERIFIED: codebase]

Tests that hard-code schema 3 and WILL break and must be edited (not Phase 47 files): in `server/test_fleet_schema3.py` `test_fresh_database_is_at_schema_3_with_new_objects` (`SCHEMA_VERSION == 3`), `test_concurrent_upgraders_end_at_schema_3` (`versions == [3, 3, 3]`), and `test_schema_4_is_refused` (sets `user_version = 4`, which is now valid). Change them to `SCHEMA_VERSION`-relative checks (`>= 3`, `SCHEMA_VERSION + 1` for the too-new case; `stub-server/test_fleet_auth.py:170` and `server/test_fleet_db.py:458` already use `SCHEMA_VERSION + 1`). Extend the `start` parametrization of the upgrade-in-place test to include 3. Put new v4 tests in a new `server/test_fleet_schema4.py` following `test_fleet_schema3.py` (`_make_old(state_dir, upto)` helper builds an older database with `MIGRATIONS[:upto]`).

The freeze test file `stub-server/test_phase47_freeze.py` is a Phase 47 file: do not edit it. It needs no edit to stay green (its migration step runs `fleet_db`/`fleet_migrate` at the current `SCHEMA_VERSION`; it checks `devices` row columns and legacy files). To prove D-07 add a **new** test (suggested `stub-server/test_co_manager_live_frame.py`) that uses `seed_live_like_state`, `FrameServer`, `snapshot_dir` from `test-support/`, migrates, inserts a co-manager on the live frame, and asserts the poll response (image hash, `sleep_s`), the legacy files, and the `devices` row (owner, MAC, secret, token, `state_path`) are identical before and after. Do not import from `test_phase47_freeze.py` (shared logic would need copying or a `*_helpers` module; note G12 forbids test-module imports in `companion/`).

### Co-manager helpers in `fleet_db` (names are discretionary)

All run in the caller's transaction via `_atomic(conn)` (existing helper that joins or opens `BEGIN IMMEDIATE`):
- `is_co_manager(conn, device_id, user_id) -> bool` (PK lookup; used by the gate on every request).
- `list_co_managers(conn, device_id) -> list[Row]` (id, email, disabled, added_at; ORDER BY email).
- `co_managed_device_ids(conn, user_id) -> set[str]`.
- `add_co_manager(conn, device_id, user_id, added_by, now=None)`: inside `_atomic` re-check device exists, user exists and `disabled = 0`, user is not `devices.owner_user_id`, then `INSERT`. Raise typed errors (`UnknownDevice`, `IneligibleUser`, `AlreadyCoManager` mapped from `IntegrityError`) so the handler can flash a specific message. Never trust a candidate id from the form without this re-check (TOCTOU between rendering the list and POST).
- `remove_co_manager(conn, device_id, user_id) -> bool` (rowcount).
- `clear_co_managers(conn, device_id) -> list[int]` returning removed ids (used by retire, device delete).
- `eligible_co_manager_candidates(conn, device_id)`: invited, `disabled = 0`, not the owner, not already a co-manager; admins included (D-05). `SELECT ... FROM users u WHERE disabled=0 AND id != owner AND NOT EXISTS (...)`.

### Route and access design

The current `Access(min_role, device_arg)` vocabulary has two device-scoped policies: `OWNER_DEVICE` (`Access(USER, "device")`) and the un-prefixed admin-only form. After this phase, `OWNER_DEVICE` means "owner, co-manager or admin" with no change to its declaration, which is exactly "co-manager is like the owner" for every existing route (14 GET, 14 POST device-scoped routes keep `OWNER_DEVICE`; `/device`, `/update`, `/quick/led` stay `ADMIN_ONLY`). [VERIFIED: `routes.py`]

Owner-only POST routes: **none exist today**. Calendar connect/disconnect, rules, airline rename, illustration replace, detection and settings are all `OWNER_DEVICE`; the task says co-managers change settings "like the owner", so leave them. The only new owner/admin-restricted routes are the two management actions, so the gate needs one more kind. Recommended: a second `device_arg` value, e.g. `OWNER_ONLY_DEVICE = Access(USER, "device-owner")` in `route_types.py`. `authorized_device_id` then takes the kind: for `"device-owner"` it skips the co-manager lookup. `Route.__new__` validates only `min_role`, so no constructor change is needed; update `route_types` docstring. `decide()` already distinguishes only `device_arg is None`, so it must pass `access.device_arg` through (small signature change: add `allow_co_manager` or pass the arg name).

Routes to add (declare in `routes.py` `_POST_ROUTES`, add keys to `_ACTION_KEYS` so `_DEVICE_SCOPED_KEYS` includes them, and `csrf=True` on each `Route`; `ROUTES` rebuild keeps `route.csrf or ...`):

| Route | Access | Handler rule |
|-------|--------|--------------|
| `POST /co-managers/add` | `OWNER_ONLY_DEVICE` (owner or admin) | form `user_id`; digits-only regex like `console_users._USER_ID_RE`; re-validate eligibility in the transaction |
| `POST /co-managers/remove` | `OWNER_ONLY_DEVICE` | form `user_id`; removes any co-manager row of this frame |
| `POST /co-managers/leave` | `OWNER_DEVICE` | acts only on the actor's own row (`user_id` never read from the form); if the actor has no row (owner, admin non-member) flash a neutral refusal, change nothing |

Prefixed form: `/devices/<id>/co-managers/add` etc. The un-prefixed form is admin-only (acts on the live frame, `_effective_access` returns `ADMIN_ONLY`), consistent with every other device-scoped route, and gets matrix rows via `DEVICE_SCOPED`. Declare them from a new module `companion/co_managers.py` imported by `routes.py` (it must use `route_types`, never import `routes`, like `console_*`), or inline in `routes.py` with lambdas like existing routes; either way the key must be in `_ACTION_KEYS`.

Handlers receive `m.device` after the gate; use `m.device.id`, never a form-supplied frame id. After a successful change redirect back to Home of that frame via `device_scope.scoped("/")`. Flash: device pages use the **query-string** mechanism (`flash.FLASH_MESSAGES`/`FLASH_TONES`, `?flash=<key>`, `page_context.py:339`), not the console cookie flash (`console_flash.take_flash` is only called by `_console_page`). Register new keys in `companion/flash.py` tables from constants in the new page module (same pattern as `FLASH_KEY_DETECTION_SAVED`). The flash key list is fixed (an unknown key renders nothing), so no user value reaches the toast via the query string. Do not put the other user's e-mail in a flash param if using the query-string mechanism (it would be attacker-settable text in the URL: not applicable because the registry text has no placeholders for that mechanism; use generic wording).

CSRF: POST routes with `csrf=True` are checked by the dispatcher after the access decision (`app.py:1031`) against the session-bound token via `auth.csrf_ok`; the form needs `<input type="hidden" name="csrf_token" value="...">` (look at how `users_page.py`/`fleet_page.py` emit it; reuse the same helper). The dispatcher also has the Origin/Sec-Fetch-Site gate for all POSTs. Tests use `fx.post(...)` / `with_csrf` from `test-support`.

### Atomicity pattern (copy from `console_users._run_action`)

```python
# Source: companion/console_users.py::_run_action and companion/audit.py (read this session)
conn = fleet_db.connect(h.args.state_dir)
try:
    with fleet_db.transaction(conn):                       # BEGIN IMMEDIATE ... COMMIT
        fleet_db.add_co_manager(conn, device.id, user_id, actor_id)   # re-checks inside the lock
        audit.record_in(h, conn, ACTION_CO_MANAGER_ADD, "device", device.id, "ok",
                        {"co_manager_user_id": user_id, "via": "owner"})
except fleet_db.IneligibleUser:
    audit.record_standalone(h, ACTION_CO_MANAGER_ADD, "device", device.id, "denied",
                            {"reason": "ineligible"})     # optional; written after rollback
    ...
finally:
    conn.close()
```
`audit.record_in` shares the transaction; `record_standalone` is for denied/failed attempts after rollback. A fleet.db opened through `connect_readonly_fallback` is read-only: catch `sqlite3.Error` on writes and flash a failure (existing handlers do this).

### Audit

- Actions: `device.co_manager_add` and `device.co_manager_remove`. Prefix `device.` already falls in the `frames` chip (`fleet_db.AUDIT_CATEGORIES["frames"] = ("frame.", "device.")`); no category change needed. [VERIFIED]
- `audit_log.action` and `target_type` have no CHECK; only `outcome IN ('ok','failed','denied')`. Detail is JSON, truncated to 1000 chars, never rendered by the audit page.
- Add the two labels to `companion/pages/audit_page.py::ACTION_LABELS` (the "action label table"; `console_lifecycle.py` only builds `AuditEvent` from it) with `i18n.msg("admin_lifecycle.action_device_co_manager_add", "Co-manager added")` and the remove twin, and the French in `companion/i18n_fr/admin_lifecycle.py`. An action with no label renders as "Other action" (`_ACTION_OTHER`), so the label is not optional for UX but never crashes.
- Detail keys: `{"co_manager_user_id": N, "via": "owner" | "admin" | "self" | "reassign" | "retire"}`. Target: `device` + frame id (consistent with `device.reassign`/`device.retire`; the audit page resolves the frame name via `_target_name`). The co-manager's e-mail is not shown by the page; optional polish: in `console_lifecycle._event`, for these two actions resolve `target_primary` as `"<frame name> · <email>"` by parsing the id from `detail`. Not required by AUTH-08.
- Every removal path audits one row per removed user: remove, leave (`via: self`), reassign-to-co-manager (D-03, `via: reassign`), retire cascade (`via: retire`, one row per cleared co-manager), and CLI hard delete.
- `fleet_cli devices assign` calls `fleet_ops.reassign_frame` with `CLI_ACTOR`, so D-03 logic placed in `reassign_frame` covers console and CLI. No new CLI verbs are needed (out of scope).

### Reassign (D-03) and retire changes in `fleet_ops`

`reassign_frame` runs inside `_transaction_keeping_directory` (BEGIN IMMEDIATE) after `_require_owner`. Inside that block, **before** the `UPDATE devices SET owner_user_id`, do `DELETE FROM device_co_managers WHERE device_id = ? AND user_id = ?` for the new owner and, when `rowcount == 1`, `fleet_db.audit_append(... ACTION_CO_MANAGER_REMOVE ... via "reassign")`. The order matters because the `devices_owner_not_co_manager` trigger aborts otherwise. Other co-managers are kept (locked). Note for the planner: the non-live reassign wipes the previous owner's data, location and name, yet keeps co-managers; that is what D-03 locks, but surface it in the plan as a visible consequence (the kept co-managers now manage the new owner's fresh frame).

`retire_frame`: `fleet_db.park_retired` does `DELETE FROM devices WHERE id = ?`. With the FK, SQLite raises `IntegrityError` while a co-manager row exists. Fix inside the same `BEGIN IMMEDIATE`: in `retire_frame`, call `clear_co_managers` (returning ids) before `park_retired` and write one audit row per id, or put the delete inside `park_retired` (it is also called directly by test helpers such as `fleet_console_support.seed_fleet`) and have `retire_frame` list ids first. Recommended: `park_retired` does the delete (single safe place), `retire_frame` reads ids before and audits after, all within its existing `with fleet_db.transaction(conn)`. A re-activated frame gets a fresh `d_` id on the next claim, so no membership survives retirement (correct: new owner, wiped directory). `fleet_db.remove_device(conn, mac)` (CLI hard delete) must also clear the rows first.

### Location rules (D-04) in `fleet_db.set_device_location_checked`

```python
# Source: server/fleet_db.py (current code read this session), proposed shape
device = SELECT owner_user_id FROM devices WHERE id = ?
if not is_admin:
    is_owner = actor_user_id is not None and device["owner_user_id"] == actor_user_id
    if not (is_owner or (actor_user_id is not None and is_co_manager(conn, device_id, actor_user_id))):
        raise PermissionError("device is not managed by the acting user")
if location_id is not None:
    loc = get_location(conn, location_id)
    ... unknown -> PermissionError for non-admin / ValueError for admin (unchanged)
    if not is_admin and (loc["owner_user_id"] is None or loc["owner_user_id"] != device["owner_user_id"]):
        raise PermissionError("location is not owned by the device owner")
    (existing admin/owner-mismatch rule unchanged)
```
For an owner this is byte-equivalent to today (location owner must equal the actor, who is the device owner). Clearing the location (`location_id=None`) is allowed for a co-manager (it is a setting change). A co-manager cannot create or edit a location: `detection_actions._save_location` must refuse, and `console_locations` write routes (`/locations/...`) use `_may_act` (location owned by the principal or admin), which already refuses a co-manager for the owner's locations; no change needed there, add a test.

### UI: the Co-managers card

Placement (D-01 leaves the page to discretion, "the frame's own page"): recommended **Home** (`/devices/<id>/`), as its own `<section aria-labelledby="home-co-managers">` after `.home-facts` in `home_page.render`. Reason: it is the page every user and admin has for a frame, is not inside the settings `<form>` (Display has a single form plus a dirty bar and `quick_led_html` after `</form>`; nested forms are invalid HTML), and freshness swapping on Home only replaces `.page-header__freshness`, `figure.preview-frame`, `section[aria-labelledby="home-flights"]`, `section[aria-labelledby="home-frame-state"]` and `.home-facts` (`ui_nav.py::REFRESH_SWAP_SELECTORS_BY_PAGE`), so a separate section is not clobbered while someone picks a candidate. Do not put the card inside `.home-facts`. The freshness token (`freshness._page_freshness_token`) must not need to change: the card is not part of the swap, but a changed membership will not trigger a refresh; acceptable (the redirect after POST is a full navigation).

Render rules (pure module, takes a view, reads nothing, escapes everything with `escape_html`; follow `account_page.py`):
- Always: heading "Co-managers", Owner e-mail, list of co-manager e-mails (D-06), empty state "No co-managers yet" via `layout.empty_state(..., compact=True)`.
- Owner or admin (not a co-manager): per-row Remove button and an Add form: `<select name="user_id">` of eligible candidates (label = e-mail) plus submit. No candidates: hide the form and say so. The page computes `can_manage` from the already-authorised principal: `principal.role == admin` or `device.owner_user_id == principal.user_id`.
- Co-manager (non-owner, non-admin member): read-only list and a "Leave this frame" button (a `<details>` confirm pattern is already used on Fleet: `details.fleet-confirm`, 44 px touch target is asserted by `test_browser_fleet_page.py`; reuse the pattern).
- Admin who is also a co-manager: management controls; leave not offered (an admin keeps access anyway). Optional.
- Only render for a frame with a fleet row; the synthetic live fallback (`device.id == "live"`) and a missing/unreadable fleet.db render nothing (mirror `console_locations.display_picker_html`'s guards).
- Styling: use the existing tokens/classes from the sketch skill and `style.css` (cards, `text-heading`, `page-section`, data lists); do not add new design tokens. Contrast and tap-target rules are enforced by `test_contrast_check.py` and the browser tests.

French: all user-facing strings via `i18n.msg("co_managers.<slug>", "English")` and a new `companion/i18n_fr/co_managers.py` `MESSAGES` dict (the package merges modules by `pkgutil`; a duplicate id raises at import). `test_i18n.py::test_every_message_id_has_english_and_french` fails on a missing or orphan French string, and `test_i18n.py` also requires the area prefix to match an `i18n_fr` module name (`i18n_fr_areas` check at lines ~150-156: area = module name, so use area `co_managers` with file `co_managers.py`, or reuse an existing area such as `home` and add French to `home.py`). Id format is `<area>.<slug>` lowercase with underscores; `test-support/i18n_ids.py::slug_for` is the rule used by migration tooling (not required for hand-written ids, but keep slugs <= 48 chars). The same English text with a different id in the same `i18n.msg` raises, so share constants.

Account page (`account_page.render` + `sign_in._own_frame_summaries`): add `shared: bool = False` (and optionally `owner_email`) to `FrameSummary` (a NamedTuple; give defaults so existing constructors in tests stay valid), render a small "Shared with you" label. The page copy "Once an administrator pairs a frame to your account..." stays. Heading "Your frames" can stay.

Users page: keep as is (recommended). If a shared count is wanted add a column or text on the row; every `UserRow(...)` constructor in tests must then get the field defaulted.

Behaviour on user changes (Claude's discretion; recommended):
- **Disable:** rows kept (locked in D-05). `set_user_disabled_guarded` already deletes sessions, so the user cannot act; `load_devices_for` for a disabled principal is unreachable. The card should show disabled co-managers with a "disabled" badge to the owner/admin so they can remove them; eligible-candidate query excludes disabled users. Re-enable restores access without re-adding.
- **Demote admin to user / promote user to admin:** no effect on rows. A promoted co-manager keeps the row (harmless). No action needed; document and test one case.
- **Delete:** there is no user-delete API (module docstring: "Nothing cascades and there is no user-delete API"); the FK on `user_id` keeps it that way.
- **Unlink identity:** no effect.

### Anti-Patterns to Avoid
- **Reading co-membership inside `device_scope._fleet_rows`:** its blanket `except sqlite3.Error: return []` hides every frame on any failure. Use a separate guarded helper.
- **Using `access.authorized_device_id` result for "is owner":** it now returns the id for co-managers too. Management-permission decisions (card controls, add/remove routes) must be computed from `device.owner_user_id`/role, never from "gate passed".
- **Accepting `device_id` or `user_id` for `leave` from the form:** use `m.device.id` and the principal's `user_id`.
- **A second ownership column or a role flag on `devices`:** violates the one-primary-owner invariant and the expand-only migration.
- **Putting co-managers into `Device.owner_user_id`:** every consumer treats it as the single primary owner.
- **Writing e-mails or ids of other users into the flash query string or comments with plan/phase IDs:** `scripts/check_comment_history.py` rejects plan/phase/ticket/decision IDs in comments (write "co-manager" invariants, not "D-03").

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Transactions with audit | custom locking | `fleet_db.transaction` / `_atomic` + `audit.record_in` / `record_standalone` | `BEGIN IMMEDIATE` serialises add/remove/reassign/retire; audit commits atomically |
| Uniqueness / no-owner invariant | Python-only checks | `PRIMARY KEY (device_id, user_id)` + triggers + in-transaction re-check | Races between two admins or owner and admin |
| 404 uniformity | per-route checks | the dispatcher's `access.decide` returning `NOT_FOUND` (same body as unknown path) | Matrix tests assert the body equals the unknown-path 404 |
| CSRF | new token code | `Route(..., csrf=True)` + `routes.CSRF_FIELD` | Already enforced by the dispatcher |
| Flash | new cookie scheme | `flash.FLASH_MESSAGES` registry (device pages) | Fixed key to text map, never echoes request text |
| i18n | inline French strings | `i18n.msg` + `i18n_fr/<area>.py` | CI sweeps for missing/orphan ids |
| Migrations | ad-hoc `CREATE IF NOT EXISTS` at connect | append to `MIGRATIONS` | Atomic with version bump, concurrency-tested |

## Runtime State Inventory

This is an additive feature, not a rename/refactor. Answers for completeness:
- **Stored data:** production `fleet.db` (schema 3) gains one empty table plus two triggers at deploy; no existing row changes. The live Orly frame's row is untouched (D-07).
- **Live service config:** none. **OS-registered state:** none (systemd units unchanged). **Secrets/env vars:** none. **Build artifacts:** none.
- Backups: `deploy/tests/test_backup.py` compares `CREATE TRIGGER` statements source vs copy and asserts `schema_version == SCHEMA_VERSION`; new triggers are covered by those assertions without edits, but run that file.

## Common Pitfalls

### Pitfall 1: Retiring a frame with co-managers raises `IntegrityError`
**What goes wrong:** `park_retired` deletes the `devices` row; FK from `device_co_managers.device_id` blocks it (foreign keys are ON per connection). Console retire flashes "Action failed", CLI retire traceback.
**How to avoid:** clear membership in the same transaction (see Reassign/retire section); audit each removal (`via: retire`); same for `remove_device`. Test: retire a frame that has two co-managers; assert frame parked, rows gone, two audit rows plus the retire row, `previous_owner_user_id` intact.
**Warning signs:** `FOREIGN KEY constraint failed` in `fleet_ops` tests.

### Pitfall 2: Reassigning to an existing co-manager aborts or leaves an owner-also-co-manager
**What goes wrong:** With the trigger, the `UPDATE` aborts if the row still exists; without the trigger an owner who is also a co-manager makes the card and the candidate list inconsistent.
**How to avoid:** delete the row first, inside the existing reassign transaction, then update the owner, then audit. `_reassign_refusal` (same-owner check) is unchanged. Test: reassign to a co-manager (row gone, removal audited, other co-managers kept, old owner now has no access, new owner has); reassign to a non-co-manager; failure rollback restores the row (`_transaction_keeping_directory` rolls back the database).

### Pitfall 3: `_fleet_rows` hides all frames when the co-manager query fails
**What goes wrong:** `connect_readonly` never migrates; a database still at schema 3 (or any `sqlite3.Error`) makes a naive join return `[]`, and a plain user sees no frames at all, including their own.
**How to avoid:** query co-managed ids in a separate try/except that fails closed to an empty set, so owned frames still list. Test with a schema-3 database.

### Pitfall 4: `set_device_location_checked` refuses every co-manager
**What goes wrong:** the existing rule compares the location owner to the actor; a co-manager is never that. Display picker save shows "location unavailable".
**How to avoid:** compare to the device owner (see Location rules). Tests: owner unchanged; co-manager can assign owner's location and clear it; co-manager cannot assign their own or another user's location; admin rules unchanged.

### Pitfall 5: Detection page lets a co-manager create locations under their own id
**What goes wrong:** `subject_for` sets `subject_id = actor_id` for non-admins, and `_write_location` creates `owner_user_id=subject.subject_id`: a co-manager would silently create their own location, which could never be assigned (refused by the owner rule) and breaks D-04.
**How to avoid:** co-manager subject: list owner's locations, `may_write` false, `_save_location` returns the `location_form` error, and the page hides the form.

### Pitfall 6: Management controls keyed off "gate passed"
**What goes wrong:** a co-manager gets Add/Remove buttons or a working POST.
**How to avoid:** add/remove routes use the owner-only access kind (404 for co-manager, matrix-tested) and the card computes `can_manage` from role/owner.

### Pitfall 7: Adding an ineligible or stale candidate (race)
**What goes wrong:** between render and POST the candidate was disabled, became the owner via reassign, or was already added by a second admin.
**How to avoid:** re-check inside `BEGIN IMMEDIATE`; map `IntegrityError` to an "already a co-manager" flash. Candidate id: digits-only, length-capped (<10 chars) before any query; unknown id flashes "not found", never a 500.

### Pitfall 8: Leave by a non-member, by the owner, or with a crafted `user_id`
**How to avoid:** `leave` ignores the form entirely; no row for the actor means no change and a neutral flash. Owner cannot remove themselves (they have no row, nothing to delete).

### Pitfall 9: Schema-number tests and README
Three tests in `server/test_fleet_schema3.py` assert schema 3 (listed above). `deploy/README.md` needs a v4 rollback paragraph. Forgetting either breaks CI or leaves operators without the rollback fact.

### Pitfall 10: 404 uniformity regressions
A co-manager's access to frame A must not leak to frame B, and an outsider must see the identical 404 body. Gate is per device id; the matrix HTTP layer asserts `body == unknown-path 404`. Also: after removal (or leave) the former co-manager's next request is 404 (membership is read per request, no cache). Test explicitly with the same session cookie before/after.

### Pitfall 11: Account page and selector for admins
`load_devices_for` returns all frames for admins; `_own_frame_summaries` must keep showing an admin only frames they own **or co-manage**, not every frame. Test with an admin who co-manages one frame.

## Code Examples

### Gate injection (minimal diff)
```python
# Source: companion/access.py (current) with the proposed optional argument
def authorized_device_id(principal, device_id, owner_lookup, is_co_manager=None):
    if principal is None or not _valid_device_id(device_id):
        return None
    owner = owner_lookup(device_id)
    if owner is None:
        return None
    if principal.role == ADMIN:
        return device_id
    if principal.user_id is None:
        return None
    if owner == principal.user_id:
        return device_id
    if is_co_manager is not None and is_co_manager(device_id, principal.user_id):
        return device_id
    return None
```
For the owner-only kind, a sibling or a flag skips the last branch. `decide()` forwards the optional callable; `Handler._dispatch` passes `self._co_manager_lookup`.

### Matrix extension (see next section)

## Access matrix and test structure

Structure (read this session): `companion/test_access_matrix.py` has a hand-written `ROUTE_POLICY` (route key -> kind), `OUTCOMES[kind][principal]`, `UNPREFIXED_OUTCOMES[principal]`, `PRINCIPAL_NAMES = ("anonymous", "owner", "other", "admin")`, `DEVICE_SCOPED`, `SAMPLE_MIDDLE`, plus console rows merged from `test-support/matrix_rows_*.py` (`ROWS`: key -> kind name string, `SAMPLES`: template -> middle). Cells are generated as routes x `PRINCIPAL_NAMES` in a pure layer (`access.decide` with `_owner_one`) and an HTTP layer (module-scoped `rig` with real Auth0-fake sign-in per principal; handlers replaced by recording stubs).

Changes:
1. Add kind `OWNER_ONLY = "owner-only-device"` with `OUTCOMES`: anonymous login, owner allow, other not-found, admin allow, co-manager not-found. `_MIN_ROLE_OF_KIND[OWNER_ONLY] = USER`; the test `test_a_prefixed_route_never_has_less_access_than_its_base_route` computes `expected_arg = "device" if OWNER_DEVICE else None`: extend to `"device-owner"` for the new kind.
2. Add principal `"co-manager"` to `PRINCIPAL_NAMES` and a column to every `OUTCOMES` kind and to `UNPREFIXED_OUTCOMES`: PUBLIC allow, SIGNED_IN allow, ADMIN_ONLY not-found, OWNER_DEVICE allow, OWNER_ONLY not-found, un-prefixed not-found. Pure layer: add `"co-manager"` to `_PRINCIPALS` (user id 4) and make `_owner_one`'s companion lookup return true for (`_PURE_DEVICE`, 4); pass it to `access.decide`. This automatically puts every existing route (including the ADMIN_ONLY retire/reassign/reactivate/audit/users rows) under a co-manager check: success criterion 3.
3. HTTP layer: in the module `rig` fixture create a fourth user (e.g. `comanager@example.test`), sign in as `"co-manager"`, and insert the membership row for `owner_device` through `fleet_db` helpers (do this in the fixture, not in the shared `seed_matrix_fleet`, so `test_device_scope_owner.py` and other users of `access_matrix_support` are unaffected). Update the loops that enumerate `("owner", "other", "admin")` (`test_an_unknown_device_id...`, malformed ids, poll-now) to include the co-manager where meaningful.
4. New rows: `test-support/matrix_rows_co_managers.py` with `ROWS = {("POST", "/co-managers/add"): "owner-only-device", ("POST", "/co-managers/remove"): "owner-only-device", ("POST", "/co-managers/leave"): "owner-device"}`, `SAMPLES = {}`; import and add to the two merge loops in `test_access_matrix.py` (`for _rows in (...)` and `test_the_console_row_modules_are_merged_into_the_matrix`). Because the routes are device-scoped they must also be added to the hand-written `DEVICE_SCOPED` frozenset (the test `test_the_device_scoped_set_is_exactly_the_hand_written_one` pins it) and to `ROUTE_POLICY` (completeness test names any missing route). The module docstring and the "14 GET and 15 POST" comment in `routes.py` need an update.
5. Unit tests in `companion/test_access.py` for the new argument (co-manager allowed on own device only; malformed id never calls the lookup; owner-only kind refuses co-manager; admin unchanged).

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.1.1 (+ xdist, cov), pytest-playwright 1.64.1; Python 3.13 in `server/.venv` |
| Config file | `pyproject.toml` (`testpaths = server, stub-server, companion, test-support, deploy, hardware`; `--strict-markers`; marker `browser`) |
| Quick run command | `server/.venv/bin/python3 -m pytest server/test_fleet_schema4.py companion/test_access.py companion/test_access_matrix.py companion/test_co_managers.py -x -q` |
| Full suite command | `./scripts/run-all-tests.sh` (CI form; includes coverage floor, ruff and mypy are separate CI steps) |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| AUTH-08 | v4 creates table; upgrade from v1/v2/v3 keeps rows; re-run is a no-op; concurrent upgraders end at 4; PK rejects duplicates; trigger rejects owner row and owner-becomes-co-manager update | unit | `pytest server/test_fleet_schema4.py -x` | no, Wave 0 |
| AUTH-08 | Existing schema tests adjusted to `SCHEMA_VERSION` | unit | `pytest server/test_fleet_schema3.py server/test_fleet_db.py -x` | yes (edit) |
| AUTH-08 | Gate allows co-manager on that frame only; owner-only kind refuses co-manager; malformed ids make no lookup | unit | `pytest companion/test_access.py -x` | yes (extend) |
| AUTH-08 | Route x role x owner matrix with co-manager column and the 3 new rows; 404 body identical to unknown path | integration | `pytest companion/test_access_matrix.py -x` | yes (extend) |
| AUTH-08 | Co-manager reaches every OWNER_DEVICE page and POST of the shared frame (display, detection, flights, health, airlines, settings, quick toggles, calendar, rules) and gets 404 for `/device`, `/update`, console retire/reassign/reactivate/users/audit | integration | `pytest companion/test_co_managers.py -x` | no, Wave 0 |
| AUTH-08 | Add/remove/leave over HTTP with CSRF: eligible only (invited, not disabled, not owner, not duplicate), co-manager cannot add or remove others, leave removes only self, outsider 404, removed user 404 on next request | integration | same | no, Wave 0 |
| AUTH-08 | Audit rows: add, remove, leave, reassign-to-co-manager, retire cascade (one per user, `ok`, actor and `via`) and labels in the audit page | integration | `pytest companion/test_co_managers.py companion/test_console_lifecycle.py -x` | partly |
| AUTH-08 | `reassign_frame`: co-manager row deleted atomically (D-03), others kept, rollback restores; `retire_frame`/`park_retired`/`remove_device` with co-managers | unit | `pytest server/test_fleet_ops.py -x` | yes (extend) |
| AUTH-08 | Locations: co-manager assigns owner's location and clears it; refused for own/other's; cannot create/edit location on Detection; `/locations` write routes refuse | unit+integration | `pytest server/test_fleet_schema4.py companion/test_console_locations.py companion/test_detection_page.py -x` | yes (extend) |
| AUTH-08 | `load_devices_for`: co-managed frames listed for user; admin who co-manages sees all; schema-3 database fails closed to owned frames | unit | `pytest companion/test_device_scope_owner.py -x` | yes (extend) |
| AUTH-08 | Account page marks shared frames; Home card for owner (controls), co-manager (read-only + Leave), admin (controls); French render | integration | `pytest companion/test_account_page.py companion/test_co_managers.py -x` | yes (extend) / no |
| AUTH-08 | Card layout: no sideways scroll at min phone width, 44 px tap targets, not clobbered by freshness refresh | browser | `SKYPANE_REQUIRE_BROWSER=1 pytest companion/test_browser_co_managers.py -x` | no, Wave 0 |
| AUTH-08 / D-07 | Co-manager on the live frame leaves poll response, legacy files and `devices` row identical | integration | `pytest stub-server/test_co_manager_live_frame.py stub-server/test_phase47_freeze.py -x` | new file; freeze test stays unedited |
| AUTH-08 | i18n completeness and comment/function-size/mypy gates | static | `pytest companion/test_i18n.py -x`; `server/.venv/bin/python3 scripts/check_comment_history.py check`; `scripts/check_function_size.py`; mypy per CI | yes |
| AUTH-08 | Backup/restore at schema 4 and activate dry-run | integration | `pytest deploy/tests/test_backup.py deploy/tests/test_activate.py -x` | yes (run) |

### Sampling Rate
- **Per task commit:** the quick command plus the single test file touched.
- **Per wave merge:** `./scripts/run-all-tests.sh -- companion server stub-server -x` (extra args disable the coverage floor automatically).
- **Phase gate:** `./scripts/run-all-tests.sh` green before `/gsd:verify-work`. Playwright tests need the headless shell (`playwright install --only-shell chromium`); use `SKYPANE_REQUIRE_BROWSER=1`.

### Wave 0 Gaps
- [ ] `server/test_fleet_schema4.py` (migration, constraints, helpers, location rule, reassign/retire/remove cascade).
- [ ] `companion/test_co_managers.py` (HTTP behaviour; seeds via `fleet_console_support` plus a helper that inserts membership rows; use `app_server_in_process`, `fx.user_cookie`/`fx.admin_cookie`, `fx.post`, `fx.audit_rows`).
- [ ] `companion/test_browser_co_managers.py` (follow `test_browser_fleet_page.py`: `new_context`, `_login` helper from `companion/test_browser_ux_helpers.py`, `VIEWPORT_MIN_SUPPORTED`).
- [ ] `test-support/matrix_rows_co_managers.py` and edits in `companion/test_access_matrix.py`.
- [ ] `stub-server/test_co_manager_live_frame.py` for D-07.
- [ ] Edit three schema-3 assertions in `server/test_fleet_schema3.py`.
- [ ] `fleet_console_support.py` helper to seed a co-manager (optional; note `user_cookie` takes an e-mail and role, existing users `plain@example.test` and `owner@example.test` can serve as co-manager and owner; `seed_fleet` frame "Kitchen" is owned by `owner`).
- Behaviour-over-source rule (`companion/test_suite_guards.py`): tests assert served HTML or browser state, never source text or `.planning/`; no test module imports another test module.

## Security Domain

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no (Auth0 sign-in unchanged) | existing |
| V3 Session Management | indirectly (disable deletes sessions; removed co-manager is evaluated per request) | existing `fleet_sessions` |
| V4 Access Control | **yes, central** | default-deny `access.decide`; owner-only kind; uniform 404; membership read per request |
| V5 Input Validation | yes | digits-only capped `user_id`, `DEVICE_ID_RE` before any lookup, parameterised SQL only |
| V6 Cryptography | no | none |
| V13/V14 CSRF and headers | yes | `csrf=True` routes, Origin/Sec-Fetch-Site gate, CSP unchanged |

### Known Threat Patterns
| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Co-manager escalates by adding/removing others or removing the owner | Elevation of privilege | owner-only access kind (404), `leave` ignores the form, no route can touch `devices.owner_user_id` except admin reassign |
| IDOR on `user_id`/frame id in forms | Tampering | frame id from the gate (`m.device`), `user_id` validated and re-checked in-transaction |
| Enumeration of frames or users via differing responses | Information disclosure | same 404 body as unknown path; add form never echoes whether an e-mail exists beyond the eligible list the viewer is allowed to see |
| E-mail disclosure | Information disclosure | only owner and co-manager e-mails of a frame the viewer may reach (D-06); candidates list shown to owner/admin only (invited users' e-mails; owner already can see only users they pick: note that exposing all invited e-mails to every owner is a privacy decision, see Open Question 1) |
| CSRF on add/remove/leave | Tampering | token required |
| Race / double submit | Tampering | `BEGIN IMMEDIATE`, PK uniqueness |
| Stale access after removal/disable | Elevation of privilege | no caching; sessions deleted on disable |
| Audit gaps | Repudiation | audit row in the same transaction for every add and remove path, including cascades |

## Open Questions

1. **Who may see the candidate list?** D-05 makes any invited non-disabled user eligible, and the add control needs to list them. For a plain-user owner this exposes the e-mail addresses of all invited users (the Users page is admin-only today). What we know: CONTEXT locks eligibility, not the picker's mechanics. What's unclear: whether the owner should pick from a list or type an e-mail. Recommendation: owner and admin choose from a `<select>` of eligible users (simplest, matches the Fleet "Pair a frame" owner select), but flag this privacy trade-off to the user at plan time; the lower-disclosure alternative is a typed-e-mail field that resolves against invited users and answers with one generic "not invited or not eligible" message for all failures. Either fits D-05; the planner should pick one and note the choice. [ASSUMED: privacy preference]
2. **Card page** (Home vs Display). Recommendation Home (see UI). Needs no user decision but a browser test on freshness refresh.
3. **Do kept co-managers survive a reassign that wipes the frame?** D-03 locks yes; confirm in the plan text that this is intended.
4. **Audit target presentation** (frame vs frame plus e-mail). Recommendation frame target, optional label polish.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The owner is comfortable with owners seeing the e-mails of all invited users in the add control (Open Question 1) | Open Questions, Security | Privacy regression; switch to typed-e-mail resolution |
| A2 | Home is the right "frame's own page" for the card | UI | Cosmetic; card could move to Display |
| A3 | Shipping triggers in the migration is acceptable (defence in depth; the `deploy/tests/test_backup.py` trigger comparison covers them) | Migration v4 | If undesired, drop the two triggers and rely on in-transaction checks only |
| A4 | Roll-back semantics: previous release refuses schema 4 and falls back to legacy files (verified in code), consistent with the earlier v2/v3 README statements; the owner accepts it for v4 as for v3 | Migration v4 | Owner expects true downgrade compatibility; that would need a different design and is not what the code base does for any migration |

All other claims are `[VERIFIED: codebase]` (read from the cited files in this session).

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python venv `server/.venv` | all tests | yes | 3.13.18 | — |
| pytest | tests | yes | 9.1.1 | — |
| playwright (python) | browser tests | yes (package); browser binary not probed | 1.64.1 | `playwright install --only-shell chromium`; CI fails if absent |
| SQLite (stdlib) | schema, triggers | yes | bundled | — |

No external services needed. The phase must not deploy anything (out of scope).

## Sources

### Primary (HIGH confidence, repository files read this session)
- `companion/access.py`, `companion/route_types.py`, `companion/routes.py`, `companion/app.py` (`_effective_access`, `_dispatch`, `_owner_lookup`, `_fleet_conn`, `_render_tab`, `_console_page`, `_page_shell_for`)
- `companion/device_scope.py`, `companion/device_dispatch.py`, `companion/sign_in.py`, `companion/detection_actions.py`, `companion/console_locations.py`, `companion/console_lifecycle.py`, `companion/console_users.py`, `companion/audit.py`, `companion/flash.py`, `companion/console_flash.py`, `companion/user_view.py`, `companion/pages/{audit_page,account_page,home_page,detection_page,users_page,fleet_page}.py`, `companion/ui_nav.py` (swap selectors)
- `server/fleet_db.py` (migrations v1-v3, `migrate_schema`, `transaction`, `_atomic`, `set_device_location_checked`, `park_retired`, `remove_device`, `audit_*`), `server/fleet_ops.py`, `server/fleet_migrate.py`, `stub-server/fleet_cli.py`
- Tests: `companion/test_access_matrix.py`, `companion/test_access.py`, `test-support/access_matrix_support.py`, `test-support/matrix_rows_lifecycle.py`, `test-support/fleet_console_support.py`, `server/test_fleet_schema3.py`, `stub-server/test_phase47_freeze.py`, `companion/test_console_lifecycle.py`, `companion/test_browser_fleet_page.py`, `companion/conftest.py`, `companion/test_i18n.py`
- `deploy/README.md` (Schema v3 and rollback), `.claude/CLAUDE.md`, `55-HANDOFF.md` section B, `60-CONTEXT.md`, ROADMAP Phase 60, REQUIREMENTS AUTH-08

### Secondary / Tertiary
- None. No web research was needed: the phase uses no external library or service.

## Project Constraints (from CLAUDE.md)
- English for code, comments, docstrings, docs and commit messages; companion UI bilingual (strings in `companion/i18n_fr/`, every user-facing literal).
- Comments state what/why (invariants, units); **no plan, ticket, decision, review or phase IDs in comments** (`scripts/check_comment_history.py check` in CI).
- Stack: stdlib + Pillow + requests only on the server; no new dependency. Python files in `server`/`stub-server` obey the 80-line function cap (`scripts/check_function_size.py`); mypy module list in `pyproject.toml`; ruff.
- Tests: pytest, `./scripts/run-all-tests.sh`; behaviour-over-source rule (`companion/test_suite_guards.py`); browser tests use the guarded `new_context`/`page` fixtures; coverage gate at measured floor; no non-loopback network.
- UI follows `sketch-findings-skypane` (existing tokens, cards, control density, contrast, 44 px targets); no new design tokens.
- GSD workflow: repo edits go through a GSD command; this phase is planned and executed via `/gsd:plan-phase` and `/gsd:execute-phase`. Out of scope per CONTEXT: production deploys, Phase 47 files and `hardware/`, Phase 55 planning lines, Phase 58 files.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH, nothing new.
- Architecture (ownership sites, access change, migration): HIGH, read from code; behaviour under FK and triggers reasoned from SQLite semantics and the existing `PRAGMA foreign_keys=ON` setting (not executed in this session since code must not change).
- Pitfalls: HIGH for 1-5 and 9 (direct code evidence), MEDIUM for UI placement (Home vs Display) and the freshness interaction (reasoned from `REFRESH_SWAP_SELECTORS_BY_PAGE`, to be confirmed by the browser test).

**Research date:** 2026-11-01
**Valid until:** 2026-12-01 (stable code base; re-check if Phase 58 or 57 touch `fleet_db` migrations first: migration index 4 would then be taken)
