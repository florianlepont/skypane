# Phase 48: Fleet Data Model, Roles and Live-Frame Migration - Research

**Researched:** 2026-10-28
**Domain:** stdlib sqlite3 identity store, expand-only data migration of a live device, backup/restore, behaviour-freeze testing (Python, bash deploy)
**Confidence:** HIGH (codebase read directly; no new dependency, no external library to verify)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** After migration, byos authenticates the live frame from `fleet.db` (MAC, secret hash, token), and `devices.json` is left untouched and valid, so the previous release still runs on post-migration state (expand-only).
- **D-02:** The migration is an idempotent `fleet_migrate` step run by the deploy script, after an automatic backup, with a `--dry-run` report that changes nothing. Never run at service start; the owner has no manual step.
- **D-03:** If `fleet.db` is absent, unreadable or corrupt at byos start, byos falls back to `devices.json` so the live frame keeps working, and the problem is logged and shown on the health page.
- **D-04:** Proof of "no observable change": a test replays a poll on a copy of the live frame's real state files before and after migration and compares image hash and wake interval; a second test re-runs the migration and asserts no byte changes. The frame's MAC, secret, token and file paths (`state_path = "."`) are kept.
- **D-05:** Hardware types live in a committed, tested code registry (not a DB table). Fields: resolution, palette, image format, battery profile, firmware target. The legacy EE02 is an entry; adding a type is a commit.
- **D-06:** Two simulated types ship, enabled only by environment variable and never in production: a same-geometry clone of EE02, and an 800x480 landscape type.
- **D-07:** Users are created through a CLI (devices_cli style): email, role `admin`/`user`, disabled flag, unique `(iss, sub)` column ready for Phase 54. The migration creates the owner as `admin` and assigns the current frame to them. Role is stored locally only.
- **D-08:** A location is its own table (name, latitude, longitude, timezone) linked to a device; the current frame gets Orly. Each device has exactly one owner, enforced in the schema.
- **D-09:** The `"default"` device fallback is dropped in byos (research: `_resolve_device_id`).
- **D-10:** `fleet.db` is backed up with the sqlite3 online backup API into the archive and added to the backup allow-list; a test restores the archive into an empty directory and checks the content.
- **D-11:** A written freeze list names what Phase 47 measures (wake cadence / `sleep_s`, battery telemetry, poll-state fields, image hash). A test compares served responses and those fields before and after migration and fails if any changes.

### Claude's Discretion
- Schema details (column names, `PRAGMA user_version` migration layout), module names (`fleet_db.py`, `hardware.py`, `fleet_migrate.py` per research), CLI verbs, plan split and waves.

### Deferred Ideas (OUT OF SCOPE)
- Web UI for users/devices (Phases 54-55); registry rewrite and `*.pre-fleet` copy (Phase 49); per-device directories (Phase 51).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DATA-01 | Users, devices, hardware types, locations in one fleet DB, exactly one owner per device | Schema section: `owner_user_id INTEGER NOT NULL REFERENCES users(id)` on `devices` (NOT NULL is what enforces "exactly one"); `PRAGMA foreign_keys=ON` per connection; hardware type is a code registry key validated in Python |
| DATA-02 | Live frame migrated keeping MAC/secret/token; same image hash and sleep_s | Migration section: import `devices.json` + `byos_state.json` tokens into `fleet.db`, touch no other file; D-04 replay test with a fixture copy of the live state; dual-write of new tokens/secrets so the previous release keeps working |
| DATA-03 | Role admin/user stored locally | `users.role CHECK(role IN ('admin','user'))`; no code path reads a role from a token claim; test asserts role only comes from the row |
| DATA-04 | Hardware profiles incl. simulated | `server/hardware.py` frozen-dataclass registry; `SKYPANE_SIM_HARDWARE=1` env gate; test that production unit/env never enables it |
| DATA-05 | Fleet DB in backup with tested restore; freeze-list test | Backup section (generalise `snapshot_db`) and Freeze-list section |
</phase_requirements>

## Summary

Everything this phase needs is stdlib. The repo already has the three patterns to copy: `history_db.py` (sqlite3 connect/WAL/`busy_timeout`/thread-scoped connection), `skypane_backup.snapshot_db()` (online backup API plus `PRAGMA integrity_check` on the copy), and `devices_cli.py` (imports byos_server's own functions so the format never drifts). No new package, so the Package Legitimacy Gate does not apply.

The central risk is not the schema, it is rollback safety. Today the frame's identity is spread over three files: `devices.json` (MAC to secret SHA-256, written by `register_device`), `byos_state.json` (MAC to plaintext bearer token, written in `do_POST /device/v1/setup`, loaded once into `Handler.state` at process start), and `device_report.json` (keyed by MAC or the literal `"default"`). The previous release only reads these files. "Expand-only" therefore means: the migration reads them and writes only `fleet.db`; and from the moment byos reads from `fleet.db`, every subsequent identity write (new enrolment token, `devices_cli add/remove/revoke-token`) must still be mirrored into the legacy files, or a rollback strands the frame (stale token) or a freshly added device (unknown MAC). This dual-write is the single most important design point and is not spelled out in CONTEXT.md.

The `sleep_s` and image hash do not depend on any identity data (`read_wake_interval_s`, `quiet_hours_sleep_s`, `battery_critical_sleep_s` read `device_config.json`/`poll_state.json` in the state dir; the hash is sha256 of `--image`). So "no observable change" is naturally preserved as long as the phase does not touch those code paths; the freeze test's job is to pin that.

**Primary recommendation:** Add `server/fleet_db.py` (schema + `user_version` migrations), `server/hardware.py`, `server/fleet_migrate.py` (CLI with `--dry-run`), a `fleet_cli.py` next to `devices_cli.py`; change byos to authenticate from `fleet.db` with a fail-back to the legacy files and dual-write on enrolment; run `fleet_migrate` from `deploy/activate.sh` (not `deploy.sh`) after a backup and before the swap; extend `skypane_backup.py` to snapshot `fleet.db` via `snapshot_db`; pin everything with a before/after byos subprocess replay test.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Identity/ownership/location storage | Database / Storage (`fleet.db`) | API/Backend (`fleet_db.py`) | Relational, needs transactions and constraints |
| Hardware profiles | API/Backend (code registry `hardware.py`) | — | D-05: committed code, not a table |
| Device authentication (MAC/secret/token) | API/Backend (byos) | Database (`fleet.db`), legacy JSON as fallback | Frames never talk to Auth0 (AUTH-06) |
| Migration | Deploy tooling (`activate.sh` calling `fleet_migrate`) | Database | Must run once, after backup, never at service start |
| Backup/restore | Deploy tooling (`skypane_backup.py`) | Database | sqlite online backup API |
| Role storage | Database (`users.role`) | — | DATA-03: never from IdP |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `sqlite3` (stdlib) | SQLite 3.45.1 in local venv (Python 3.13.17); prod Python 3.14 | fleet.db | Already used by `history_db.py` and the backup job; CLAUDE.md forbids new dependencies [VERIFIED: local `python -c`] |
| `argparse`, `hashlib`, `hmac`, `secrets`, `json`, `dataclasses` (stdlib) | — | CLIs, secret compare, hardware profiles | Same as byos/devices_cli |
| pytest 9.1 + xdist + cov | 9.1.1 in `server/.venv` | tests | Project standard [VERIFIED: `server/.venv/bin/python3 -m pytest --version`] |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| code registry for hardware | DB table | Rejected by D-05 |
| SQLAlchemy/alembic | — | Forbidden (stdlib only); `PRAGMA user_version` is enough |

**Installation:** none.

## Package Legitimacy Audit

No external packages are installed by this phase. Audit not applicable. Packages removed: none. Packages flagged: none.

## Architecture Patterns

### System Architecture Diagram

```
 deploy.sh (laptop/CI) --ssh--> activate.sh (VPS, root)
        |                              |
        |                  stage release, import firmware
        |                              |
        |                 [1] runuser skypane: skypane_backup.py  --> archive (incl. fleet.db if present)
        |                 [2] runuser skypane: fleet_migrate.py --dry-run  (report only)
        |                 [3] runuser skypane: fleet_migrate.py            (idempotent)
        |                              |   reads: devices.json, byos_state.json, device_config.json
        |                              |   writes: fleet.db ONLY (+ meta marker)
        |                              v
        |                      swap current -> restart byos/companion/poll -> probe

 frame --GET/POST /device/v1/*--> byos_server.py
        token/secret check:  fleet.db (read)  --fail/absent/corrupt--> devices.json + byos_state.json (D-03)
        setup (new token):   write fleet.db AND byos_state.json (dual-write)
        display response:    image sha256, sleep_s from device_config/poll_state (UNCHANGED code path)

 owner --ssh--> fleet_cli.py (users add/list/disable, devices add/assign, hardware list)
        writes fleet.db; devices add also mirrors devices.json (dual-write)

 nightly: skypane_backup.py --> snapshot_db(fleet.db) + history.db + allow-listed files --> tar.gz
```

### Recommended Project Structure
```
server/fleet_db.py        # connect(), schema, MIGRATIONS list, user_version, CRUD helpers (typed; add to mypy list)
server/hardware.py        # HardwareProfile dataclass, REGISTRY, sim gate (typed)
server/fleet_migrate.py   # migrate(state_dir, dry_run) + main(); idempotent
stub-server/fleet_cli.py  # operator CLI (imports byos_server + server.fleet_db like devices_cli)
server/test_fleet_db.py, test_hardware.py, test_fleet_migrate.py
stub-server/test_fleet_auth.py, test_phase47_freeze.py
deploy/tests/test_backup.py (extend), deploy/tests/test_activate.py (extend)
```
Note `server/` has no `__init__.py`; byos already does `from server import ...` (line 82), so byos can import `server.fleet_db` and `server.hardware`. `server/test_import_boundaries.py` guards import directions: keep `fleet_db` free of companion/poll_loop imports.

### Pattern 1: Schema with `user_version` migrations
**What:** Ordered list of SQL/callable steps; `connect()` reads `PRAGMA user_version`, applies steps `> current` in one `BEGIN IMMEDIATE` transaction each, sets `user_version` last. `PRAGMA foreign_keys=ON`, `journal_mode=WAL`, `busy_timeout=5000` on every connection (foreign_keys is per-connection, not persisted).
**Recommended v1 schema** (names are discretionary; shape follows research ARCHITECTURE section 3.1, trimmed to this phase):
```sql
users(id INTEGER PRIMARY KEY, email TEXT NOT NULL UNIQUE COLLATE NOCASE,
      role TEXT NOT NULL CHECK(role IN ('admin','user')),
      disabled INTEGER NOT NULL DEFAULT 0 CHECK(disabled IN (0,1)),
      iss TEXT, sub TEXT, created_at TEXT NOT NULL,
      UNIQUE(iss, sub));            -- NULLs are distinct in SQLite UNIQUE: many unlinked users allowed
locations(id INTEGER PRIMARY KEY, name TEXT NOT NULL,
          latitude REAL NOT NULL CHECK(latitude BETWEEN -90 AND 90),
          longitude REAL NOT NULL CHECK(longitude BETWEEN -180 AND 180),
          timezone TEXT NOT NULL);
devices(id TEXT PRIMARY KEY,               -- opaque 'd_'+8 hex, never the MAC
        mac TEXT NOT NULL UNIQUE, secret_sha256 TEXT NOT NULL,
        token TEXT,                         -- see Open Question 2
        hardware_type TEXT NOT NULL,        -- validated in Python against hardware.REGISTRY
        owner_user_id INTEGER NOT NULL REFERENCES users(id),
        location_id INTEGER REFERENCES locations(id),
        name TEXT, state_path TEXT NOT NULL DEFAULT '.', created_at TEXT NOT NULL);
meta(key TEXT PRIMARY KEY, value TEXT NOT NULL);
```
`owner_user_id NOT NULL` + FK is what makes "exactly one owner" a schema fact (DATA-01); add a test that inserting a device with NULL or unknown owner raises `sqlite3.IntegrityError`. Disabling a user must not orphan devices (no cascade delete). Hardware-type validation cannot be a CHECK against a code registry; enforce in `fleet_db.add_device()` and test it. (The research draft's `owner NULL = unclaimed` is deliberately NOT used here: pairing is Phase 55.)

### Pattern 2: Expand-only migration
`fleet_migrate.migrate(state_dir, dry_run)`:
1. Read `devices.json` via `byos_server.load_registry` semantic (but note it fails closed to empty on corruption; the migration must instead *abort* on a malformed non-empty file rather than migrate "nothing").
2. Read `byos_state.json` tokens (MAC to token).
3. In one transaction: create schema, insert owner admin user (email from an explicit `--owner-email` argument or `SKYPANE_BOOTSTRAP_ADMIN_EMAIL`; fail loudly if absent rather than inventing one), Orly location (LFPO; coordinates: take from a committed constant or `adsb-test/runway3.json`, planner to confirm), one device per registry MAC with same `secret_sha256`, token, `hardware_type='xiao-ee02-13in3-spectra6'` (name discretionary), `state_path='.'`, owner = admin.
4. Idempotence: `INSERT ... ON CONFLICT(mac) DO NOTHING` plus a `meta('migrated_v1')` marker; a second run must report "nothing to do" and leave `fleet.db` byte-identical. NOTE: a SQLite file is not byte-stable if you merely open it in WAL mode (WAL/-shm files, header change counter). The "no byte changes" test (D-04) should hash `fleet.db` after a checkpoint, or assert logical equality of a full table dump plus unchanged mtime of every legacy file. Decide which and state it in the plan; the legacy JSON files are the ones that must be byte-identical (sha256 before/after).
5. Never write to `devices.json`, `byos_state.json`, `device_config.json`, `poll_state.json`, `panel.bin`, `firmware/`.
6. `--dry-run`: open nothing for write (use `sqlite3.connect("file:...?mode=ro", uri=True)` if `fleet.db` exists, otherwise an in-memory DB), print what it would insert, exit 0, and a test asserts no file in the state dir changed (sha256 + mtime snapshot of the whole directory).

### Pattern 3: byos authentication from fleet.db with fallback (D-01, D-03, D-09)
Seams in `stub-server/byos_server.py`:
- `do_POST /device/v1/setup` (lines 908-933): `load_registry` + `secret_matches` then token issue + `save_state`. Replace with a small `identity` lookup function returning `(secret_sha256 | None)`; source order `fleet.db` then legacy.
- `bearer_ok()` (877-896) and `_resolve_device_id()` (660-680) both iterate `self.state["tokens"]` (in memory, loaded once at start). Tokens issued while running are in memory; a token written by the migration (fleet.db) is NOT in `Handler.state` unless loaded. Build the token map from `fleet.db` at lookup time (cheap, one row per device) or reload at start; keep `compare_digest` over all candidates with no early exit.
- Drop `"default"` (D-09): `_resolve_device_id` returns `None` for an unknown token; `_record_device_report_and_offer` is only reached after `bearer_ok()` so a valid token always resolves. Beware: `device_report.json` is keyed by MAC today and the legacy `"default"` bucket may exist in the live file; Phase 48 must not rewrite it (registry rewrite is Phase 49). Test with a `device_report.json` containing a `"default"` entry: it is left alone, not crashed on. Also check `firmware_registry` readers tolerate a key that no code writes any more.
- Fallback (D-03): wrap the `fleet_db` read in `except (sqlite3.Error, OSError)`; on failure log once (rate-limited), set a module-level `fleet_db_status` that the health page can read, and use the legacy path. Absent `fleet.db` (pre-migration) is the normal pre-deploy state: fall back silently without an alarm, but distinguish "absent" from "corrupt/unreadable" (the latter is logged as an error). Health page: the companion is out of scope this phase, but "shown on the health page" needs a status the companion can read; simplest is byos writing `fleet_status.json` (atomic, 0600/0640) or the health page calling `fleet_db.check()` itself. Planner decision; flag as Open Question 3.
- Dual-write on enrolment and CLI (the key rollback guarantee): `setup` writes the new token to `fleet.db` AND `byos_state.json`; `fleet_cli devices add` writes `fleet.db` AND `devices.json` (via `byos_server.register_device`); `devices_cli.py` (legacy) keeps working and should also mirror into fleet.db if present, or be documented as legacy-only. A test: enrol under new code, then run the *old* code path (current `load_registry`/`bearer_ok` against the same dir) and assert the token still authenticates.
- Fail closed for identity as today: corrupt legacy file AND no fleet.db means nobody enrols. But a corrupt `fleet.db` with a good `devices.json` must still authenticate the live frame (D-03). Note the subtle case: a *stale* `devices.json` after the owner removed a device via `fleet_cli` (dual-write removes both, so it is consistent as long as both writes happen; use fleet.db first, then legacy, and report partial failure).

### Pattern 4: Deploy placement (D-02)
`deploy.sh` only streams the tree and calls `activate.sh` over ssh; all VPS-side steps live in `activate.sh`. Add the steps there, between "Firmware import" and "Rendering Caddy": backup (`runuser -u skypane -- ... skypane_backup.py --state-dir ... --archive-dir ${BACKUP_ROOT}/archives --keep 14`), then `fleet_migrate --dry-run` (logged), then `fleet_migrate`. Any non-zero exit aborts before the swap, same as the firmware import failure path (`test_firmware_import_failure_blocks_swap_previous_release_still_current` is the model). Use `runuser -u skypane` so `fleet.db` is owned by `skypane` with mode 0600 or 0640 (units run with `UMask=0027`; byos has `ReadWritePaths=/opt/skypane/state`, so WAL `-wal/-shm` files can be created). Run from the new release dir (`cd ${RELEASE_DIR} && ... -m server.fleet_migrate`), like `server.firmware_cli`. Add `fleet_migrate` `--help` to the smoke test list. Redeploy of the same sha must be a no-op (activate.sh is idempotent already; the migration is too). The backup-before-migrate step should only run when a migration is pending, or always; always is simpler and safe (archive pruning keeps 14). The `deploy/tests` harness stubs `runuser` and the firmware CLI via `_write_fake_firmware_cli`; add an equivalent fake for the new calls and assert ordering (backup, dry-run, migrate, swap) from the call log.

Do NOT run a production deploy: STATE.md says production deploy waits for Phase 47 or an explicit owner release. All verification in this phase is local/CI.

### Pattern 5: Hardware registry (D-05, D-06)
`server/hardware.py`: `@dataclass(frozen=True) class HardwareProfile` with `key, label, width, height, palette, image_format, battery (curve/low/critical/recover mv), firmware_target (idf_target, project_name, max_image_bytes), simulated: bool`. Legacy entry values must come from existing constants, not retyped numbers: 1200x1600, Spectra 6 palette (see `server/panel_format.py`), `IMAGE_BYTES = 960000` in byos, `device_policy.BATTERY_DISCHARGE_CURVE`/`BATTERY_CRITICAL_MV = 3300`, firmware project name `"skypane"` (`firmware/main/ota_policy.c`). Add a test asserting the legacy profile equals those constants so drift fails CI. Do not make `device_policy`/`panel_format` read from the registry yet (Phase 56); the registry only mirrors them. Simulated types: `SKYPANE_SIM_HARDWARE=1` (name discretionary) read at call time via a function `available_types(environ=os.environ)`, not import time, so tests can toggle it; production gate: `deploy/skypane.env.example` must not contain it and a deploy test greps the rendered unit/env example behaviourally (assert `hardware.available_types({})` lacks sim types, and that `fleet_db.add_device(hardware_type='sim-...')` raises without the env var). Same-geometry clone: 1200x1600 same palette; landscape: 800x480 with its own `max_image_bytes` computed from `panel_format` packing, not guessed (verify pixel packing in `server/panel_format.py` when writing it). DB rows with a sim type opened on a box where the gate is off must not crash byos auth (treat as unknown type for rendering, still authenticate), test it.

### Anti-Patterns to Avoid
- **Running migration at service start** (D-02 forbids): a crash loop would take the live frame down.
- **Moving or renaming any legacy file / changing `state_path`** (frame keeps `state_path = "."`).
- **Reading role or `is_admin` from any request header or token** (DATA-03): role lookups only via `fleet_db.get_user_role(user_id)`.
- **`PRAGMA user_version` bump before DDL commits**: do the version set inside the same transaction (SQLite DDL is transactional).
- **Silent fail-open on identity** beyond what D-03 allows.
- **Typing device IDs as the MAC or using them as path components.**
- **Comments naming plans/phases/decision IDs** (comment-history guard): do not write "D-03" or "Phase 48" in code comments or docstrings; describe the invariant instead. Tests may mention requirement behaviour but not IDs in comments. Run `scripts/check_comment_history.py check`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Consistent copy of a live DB | `shutil.copy` / tar of `fleet.db` | `skypane_backup.snapshot_db()` (sqlite online backup + `integrity_check`) | WAL torn copies |
| Atomic JSON writes for legacy mirroring | new temp-file code | `byos_server._atomic_write` (mode 0o600) / `server.atomic_io` | already pinned by parity test |
| Secret comparison | `==` | `hmac.compare_digest` (existing `secret_matches`) | timing |
| Schema versioning | ad hoc `IF NOT EXISTS` only | `PRAGMA user_version` steps | identity needs column changes (research) |
| Per-thread connection scope | new pattern | copy `history_db.connection_scope` shape | byos is a ThreadingHTTPServer |
| MAC validation | new regex | `byos_server.normalize_mac` | single definition |
| Operator CLI | new framework | `devices_cli.py` pattern, importing the server module | format never drifts |

## Runtime State Inventory

(Migration phase: what runtime state carries the frame's identity.)

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | `devices.json` (MAC to secret sha256), `byos_state.json` (MAC to plaintext token), `device_report.json` (keys MAC or `"default"`), `battery_state.json`, `poll_state.json`, `device_config.json`, `history.db` | Data migration into `fleet.db` for the first two only; all others untouched (code edit only for dropping `"default"` lookups). `device_report.json` untouched until Phase 49 |
| Live service config | `skypane-byos.service` args (`--image`, `--sleep`, `--state-dir`); `skypane.env` (`SKYPANE_STATE_DIR`, `SKYPANE_SLEEP_S`) | None; do not add required flags. Optional new env var (sim gate) defaults off |
| OS-registered state | systemd units (6) | None; no unit file change needed (byos already has `ReadWritePaths=/opt/skypane/state`) |
| Secrets/env vars | Frame NVS holds token and enrolment secret (never changes); `skypane.env` holds no frame secret. Owner email for bootstrap admin: new input needed | Owner email must be supplied (see Open Question 1); nothing else |
| Build artifacts | `__pycache__` precompiled by `activate.sh` compileall (new modules covered automatically); mypy file list in `pyproject.toml` | Add typed modules to `[tool.mypy] files` and the strict `overrides` module list |

**Canonical question answered:** after every repo file is updated, the live frame's token and secret still live in `byos_state.json`/`devices.json` on the VPS and in the frame's NVS; they are copied (not moved) into `fleet.db`.

## Common Pitfalls

### Pitfall 1: Rollback strands a frame enrolled under new code
**What goes wrong:** after migration byos reads tokens from `fleet.db`; a re-enrolment writes the token only there; the old release (reading `byos_state.json`) 401s the frame, which (per project notes on NVS) will not self-heal without a re-enrol.
**How to avoid:** dual-write token and secret hash to the legacy files; test "enrol with new code, authenticate with old-style readers".
**Warning signs:** a test that only checks migration output, never a post-migration enrolment.

### Pitfall 2: In-memory token cache vs `fleet.db`
`Handler.state` is loaded once at start; `devices_cli revoke-token` already warns about this. If byos authenticates from `fleet.db` reads at request time and ALSO keeps `self.state`, revocation semantics diverge. Pick one source per request (fleet.db first, legacy second) and test revoke.

### Pitfall 3: "Byte-identical" for SQLite
Opening in WAL mode creates `-wal/-shm`, changes header counters, and a no-op re-run can still touch the file. Define the assertion as: legacy JSON files byte-identical; `fleet.db` logical dump identical (`iterdump()` equality) and `meta` marker unchanged; and the second run opens no write transaction when nothing is pending (check marker first, read-only).

### Pitfall 4: Backup silently omitting or breaking on fleet.db
`skypane_backup.backup()` prints a drift line for any unknown top-level entry (`fleet.db`, `fleet.db-wal`, `fleet.db-shm`). Add `fleet.db` to the `known` set and the `-wal/-shm` names to `KNOWN_EXCLUDED` (mirror `history.db*`), and snapshot it with `snapshot_db`. Also the backup runs under `PrivateNetwork`, `ReadWritePaths=/opt/skypane/state`: reading a WAL DB needs write on `-shm`; already granted. If `fleet.db` fails `integrity_check` the whole backup fails (existing semantics for history.db): decide whether a corrupt fleet.db should fail the nightly job (recommended: yes, loud, but still archive the rest? current code deletes the partial and returns 1; keep consistent). Restore test: extract the tarball into an empty dir, open `fleet.db`, assert `integrity_check`, `user_version`, table row counts and a known device row. Also confirm `deploy/backup/backup_gate.py` and the Mac pull script do not enumerate file names (grep found no `fleet`/allow-list; `deploy/tests/test_mac_pull.py` and `test_backup_gate.py` should be run, not edited).

### Pitfall 5: Phase 47 measurement contamination
Do not change header names parsed (`X-Battery-Mv`, `X-Fw-Version`, `X-Boot-Reason`, `X-Rssi`, `X-Ota-Result`), `save_battery_state` format (`{"battery_mv", "received_at"}`), the `/device/v1/display` JSON keys (`image_url`, `image_hash`, `sleep_s`, `firmware`, `reset`, `led_enabled`), or `poll_state` keys. New byos DB writes (e.g. `last_seen_at`) are out of scope here: the research suggests them but they would add write contention and are not required; do not add.

### Pitfall 6: Function-size gate and mypy
`scripts/check_function_size.py` caps functions at 80 lines over `server`/`stub-server`; `do_POST`/`do_GET` in byos are already large, so extract the identity logic into small helper functions (do not grow `do_POST`). New typed modules must be annotated end to end and added to both mypy lists in `pyproject.toml`.

### Pitfall 7: "Real state files" are not in the repo
D-04 asks to replay against a copy of the live frame's real state files. They live only on the VPS (`/opt/skypane/state`; not present here). Without owner action the test uses a synthetic fixture shaped like production. See Open Question 4.

## Code Examples

### Online backup of fleet.db (reuse, source: `deploy/backup/skypane_backup.py`)
```python
# in backup(): alongside the history.db block, inside the same tarfile context
for db_name in ("history.db", "fleet.db"):
    src = os.path.join(state_dir, db_name)
    if os.path.exists(src):
        snap = os.path.join(tmp_dir, db_name)
        snapshot_db(src, snap)          # backup API + integrity_check on the copy
        tar.add(snap, arcname=db_name, filter=_no_symlinks)
# known = ... | {"history.db", "fleet.db"}; KNOWN_EXCLUDED += "fleet.db-wal", "fleet.db-shm"
```
Generalise the message in `snapshot_db` ("history.db backup failed integrity_check") to use the file name.

### Migration step skeleton (user_version)
```python
MIGRATIONS = (_v1_initial_schema,)   # each takes a connection, runs DDL

def migrate_schema(conn):
    current = conn.execute("PRAGMA user_version").fetchone()[0]
    if current > len(MIGRATIONS):
        raise RuntimeError("fleet.db is newer than this release")   # old code on newer DB: fail to fallback, never write
    for version, step in enumerate(MIGRATIONS, start=1):
        if version <= current:
            continue
        conn.execute("BEGIN IMMEDIATE")
        step(conn)
        conn.execute("PRAGMA user_version = %d" % version)   # integer literal, not parameterisable
        conn.execute("COMMIT")
```
Note Python's sqlite3 legacy transaction control auto-commits before DDL in some modes; set `isolation_level=None` on the connection and issue explicit BEGIN/COMMIT to get atomic DDL. [ASSUMED: behaviour is stable on 3.13/3.14; verify with a test that kills a migration mid-way]

### Before/after replay test shape (D-04, D-11)
```python
# stub-server/test_phase47_freeze.py (pattern: stub-server/test_wake_interval_delivery.py harness)
def test_poll_response_identical_before_and_after_migration(tmp_path):
    state = seed_live_like_state(tmp_path / "state")   # devices.json, byos_state.json, device_config.json, poll_state.json, battery_state.json, panel.bin
    before = poll(start_byos(state), headers={"X-Battery-Mv": "3900", ...})
    run_fleet_migrate(state)
    after = poll(start_byos(state), ...)               # new byos process, same token
    assert normalise(after) == normalise(before)       # image_hash, sleep_s, firmware, reset, led_enabled, image_url path
    assert battery_state_keys(state) == FROZEN_BATTERY_KEYS
```
Freeze list: commit it as data (a small module or JSON next to the test: response keys, parsed header names, `battery_state.json` keys, the `poll_state.json` key set written by a representative poll cycle using existing fixtures in `server/test_poll_cycle_steps.py`/`stub-server/test_poll_cycle.py`, wake bounds `WAKE_INTERVAL_MIN_S/MAX_S`, `BATTERY_CRITICAL_MV`, `DISPLAY_OFF_SLEEP_S`, `BATTERY_CRITICAL_SLEEP_S`). The test fails if any differs from the committed list, with a message telling the author that Phase 47 measures it. Per the repo's behaviour-over-source rule, the test must exercise running code, not grep source.

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|------------------|--------|
| `devices.json` registry | `fleet.db` primary, JSON kept in sync | rollback-safe expand step; contract step is a later phase |
| `"default"` device fallback | unknown token is a 401 / no device | closes a shared-bucket hazard |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Python sqlite3 explicit `BEGIN`/`isolation_level=None` gives atomic DDL + `user_version` on 3.13/3.14 | Code Examples | A half-applied schema; mitigated by a crash test |
| A2 | Orly location coordinates/timezone can be taken from a committed constant or `adsb-test/runway3.json` (not verified which file holds the airport reference point) | Pattern 2 | Wrong coordinates stored; no behaviour impact this phase since nothing reads them yet |
| A3 | Storing the token plaintext in `fleet.db` (0600) is acceptable because `byos_state.json` already does | Schema | If owner wants hashed tokens, `bearer_ok` must hash the presented token; small change but affects dual-write (JSON still needs plaintext for the old release) |
| A4 | A `meta` marker plus `ON CONFLICT DO NOTHING` is sufficient idempotence even if the owner later edits the device in `fleet.db` | Pattern 2 | Re-run could resurrect deleted rows; guard with marker, not row existence |
| A5 | The legacy `device_report.json` on the VPS may contain a `"default"` key | Pattern 3 | Only matters for the "tolerates it" test; cannot be checked locally |

## Open Questions (RESOLVED)

1. **Owner identity for the admin row.** CONTEXT.md says the migration creates the owner as `admin` but no email is in the repo (the user's email in the session is a hint, not a recorded decision). Recommendation: `fleet_migrate --owner-email` required argument, fed in `activate.sh` from a new optional `SKYPANE_BOOTSTRAP_ADMIN_EMAIL` in `skypane.env` (the owner already has to touch that file at provisioning; the CONTEXT rule "no manual step" means this must be set once by Claude/CI-side docs, in plain French for the owner). If unset, migration should abort before any write with a clear message. RESOLVED: settled in 48-03 (`--owner-email` required, abort before any write) and 48-05 (`SKYPANE_BOOTSTRAP_ADMIN_EMAIL` read by activate.sh, plain-French action line when unset). Owner-confirmable: the one-time env line in `skypane.env` is the single owner-side step and is the only deviation from "no manual step"; the owner confirms the address to use.
2. **Token storage form.** Plaintext (matches today) vs hash. Recommendation: plaintext with 0600/0640 file mode now (A3); revisit at Phase 54. RESOLVED: plaintext, 0600/0640, in 48-02/48-04.
3. **Health-page signal for the D-03 fallback.** Companion is "unaffected this phase" per code_context, but D-03 wants it shown. Smallest change: byos writes a tiny status file the existing health sections read, or `health_signals.py` gets one new row. Planner to size; keep out of freeze list. RESOLVED: 48-07 adds the health-page signal outside the freeze list (owner-confirmable).
4. **Real state files for the D-04 replay.** The test can only use a synthetic copy unless the owner exports `/opt/skypane/state` (minus secrets) from the VPS. Recommendation: build the fixture generator to mirror production file shapes (read `devices.json`, `byos_state.json`, `device_config.json`, `poll_state.json`, `battery_state.json`, `device_report.json` formats in code), commit a sanitised fixture, and add a post-deploy manual check (owner-run, plain French) only if Phase 47 allows a deploy. RESOLVED: synthetic fixture in 48-03/48-06, plus optional `SKYPANE_LIVE_STATE_COPY` hook so an owner-exported sanitised copy is replayed; the real-state proof is recorded as outstanding in the 48-06 summary.
5. **Does legacy `devices_cli.py` stay?** Recommend it stays working and mirrors into `fleet.db` when present, so the owner's existing muscle memory and docs (`deploy/README.md` lines ~243, 379, 571, 594) stay valid; update README accordingly. RESOLVED: legacy `devices_cli.py` stays and mirrors (48-03 fleet_cli, 48-05 docs).

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python + sqlite3 | everything | yes | 3.13.17 / SQLite 3.45.1 (venv `server/.venv`); prod 3.14 | — |
| pytest, xdist, cov | tests | yes | pytest 9.1.1 in `server/.venv` (system python3 has none) | use `server/.venv/bin/python3 -m pytest` |
| shellcheck, bash | activate.sh edits | not checked | — | deploy tests run bash with stubs |
| VPS access / real state | D-04 real-state replay | no (`/opt/skypane` absent) | — | synthetic fixture (Open Question 4) |

Step status: `scripts/check_comment_history.py check` run before this phase returns exit code 0 with no output (clean) as of 2026-10-28 [VERIFIED: ran locally]. STATE.md asks to record this for Phase 59; record it in the plan summary.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.1.1 (+ xdist, cov, pytest-socket loopback guard) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` (testpaths include server, stub-server, deploy; `pythonpath = [".", "test-support"]`; coverage `fail_under = 93`) |
| Quick run command | `server/.venv/bin/python3 -m pytest server/test_fleet_db.py server/test_hardware.py server/test_fleet_migrate.py stub-server/test_fleet_auth.py stub-server/test_phase47_freeze.py deploy/tests/test_backup.py deploy/tests/test_activate.py -x -q --cov-fail-under=0` |
| Full suite command | `./scripts/run-all-tests.sh` |
| Lint/type gates | `ruff check`, `mypy` (module list), `python3 scripts/check_function_size.py`, `python3 scripts/check_comment_history.py check` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DATA-01 | Device without owner / unknown owner rejected; two users cannot own one device; FK on | unit | `pytest server/test_fleet_db.py -x` | Wave 0 |
| DATA-01 | `user_version` migration idempotent, newer-DB refused, crash mid-migration leaves v0 | unit | `pytest server/test_fleet_db.py -x` | Wave 0 |
| DATA-02 | Poll before/after migration: same `image_hash`, `sleep_s`, other response fields; same token works | integration (byos subprocess) | `pytest stub-server/test_phase47_freeze.py -x` | Wave 0 |
| DATA-02 | Re-run migration changes nothing (legacy files sha256 equal, logical dump equal); dry-run changes nothing | unit | `pytest server/test_fleet_migrate.py -x` | Wave 0 |
| DATA-02 | Old-style readers authenticate after new-code enrolment; corrupt/absent `fleet.db` falls back to legacy | integration | `pytest stub-server/test_fleet_auth.py -x` | Wave 0 |
| DATA-02 | Unknown token is 401 and no `"default"` bucket; existing `"default"` in device_report tolerated | integration | `pytest stub-server/test_fleet_auth.py -x` | Wave 0 |
| DATA-02 | activate.sh order: backup, dry-run, migrate, swap; failure blocks swap | deploy | `pytest deploy/tests/test_activate.py -x` | extend |
| DATA-03 | role CHECK constraint; no role derived from `iss/sub` or headers; disabled user flag; unique `(iss, sub)` with multiple NULLs allowed | unit | `pytest server/test_fleet_db.py -x` | Wave 0 |
| DATA-04 | legacy profile equals existing constants; sim types absent without env, present with; landscape size consistent | unit | `pytest server/test_hardware.py -x` | Wave 0 |
| DATA-05 | `fleet.db` in archive; restore into empty dir passes integrity and content; drift line absent; `-wal/-shm` excluded | integration | `pytest deploy/tests/test_backup.py -x` | extend |
| DATA-05 | Freeze list: header names, response keys, battery_state keys, poll_state keys, wake bounds fail on change | integration | `pytest stub-server/test_phase47_freeze.py -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** the quick run command for the touched area
- **Per wave merge:** `./scripts/run-all-tests.sh`
- **Phase gate:** full suite green plus ruff, mypy, function-size and comment-history checks before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `server/test_fleet_db.py`, `server/test_hardware.py`, `server/test_fleet_migrate.py`
- [ ] `stub-server/test_fleet_auth.py`, `stub-server/test_phase47_freeze.py`
- [ ] A sanitised live-shaped state fixture generator (shared helper under `test-support/` or `stub-server/`)
- [ ] Extend `deploy/tests/conftest.py` fake release/stubs with a fake `fleet_migrate` call logger
- [ ] Add new typed modules to `pyproject.toml` mypy lists
- Framework install: none needed

## Security Domain

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes (device auth) | per-device secret hash + `hmac.compare_digest`, unchanged semantics |
| V3 Session Management | no (Phase 54) | — |
| V4 Access Control | partly | role stored locally, CHECK constraint; enforcement of routes is Phase 54 |
| V5 Input Validation | yes | `normalize_mac`, email lowercase/format check, lat/lon range, hardware type from registry, parameterised SQL only |
| V6 Cryptography | no new | SHA-256 via hashlib, tokens via `secrets.token_hex(32)` as today |
| V8 Data protection | yes | `fleet.db` mode 0600/0640, tokens/hashes never logged or printed (CLI prints hash prefix only, as `devices_cli list`) |

### Known Threat Patterns
| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| SQL injection via CLI args | Tampering | `?` placeholders; `user_version` literal built from an int |
| Role escalation via IdP claim | Elevation | role read only from `users.role` |
| Fail-open auth on corrupt DB | Spoofing | fall back to legacy files only (never to "allow all") |
| Token/secret leakage in logs/backup | Info disclosure | no secrets in migration report; archives already 0027 and off-box via gate |
| Sim hardware enabled in production | Tampering | env gate, not in `skypane.env.example`, test |
| Timing leak on token compare | Info disclosure | compare against all candidates with `compare_digest`, no early exit |

## Sources

### Primary (HIGH confidence) - read directly in this repo
- `stub-server/byos_server.py` (registry lines 208-300, `_resolve_device_id` 660-680, `_record_device_report_and_offer` 698-812, Handler 831-1051, main 1102-1152)
- `stub-server/devices_cli.py`, `server/state_store.py`, `server/history_db.py` (connect/scope), `deploy/backup/skypane_backup.py`, `deploy/deploy.sh`, `deploy/activate.sh`, `deploy/skypane-byos.service`, `deploy/skypane-backup.service`
- `.planning/workstreams/v1-2/research/ARCHITECTURE.md` (sections 1, 3.1, 6), `PITFALLS.md` (C13, C14), `SUMMARY.md`, Phase 47 CONTEXT
- `pyproject.toml` (pytest, coverage, mypy), `deploy/tests/test_activate.py` / `conftest.py` structure, `stub-server/test_wake_interval_delivery.py` harness

### Secondary / Tertiary
- SQLite behaviours (UNIQUE with NULLs distinct, `foreign_keys` per connection, `user_version` pragma, transactional DDL, WAL files) from training knowledge: [ASSUMED], standard and low risk; each is covered by a planned test.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH, stdlib only, matches existing code
- Architecture: HIGH for seams (read from code); MEDIUM for dual-write detail (design recommendation, not yet validated against Phase 47 constraints by the owner)
- Pitfalls: HIGH, derived from the actual code paths

**Research date:** 2026-10-28
**Valid until:** 2026-11-27 (stable codebase; re-check if Phase 47 hotfixes touch `byos_server.py`)
