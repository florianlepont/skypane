# Phase 48: Fleet Data Model, Roles and Live-Frame Migration - Pattern Map

**Mapped:** 2026-10-28
**Files analyzed:** 17 new/modified
**Analogs found:** 15 / 17

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `server/fleet_db.py` (new) | service/model | CRUD | `server/history_db.py` (`connect`, `connection_scope`, `open_db`) | role-match |
| `server/hardware.py` (new) | utility (registry) | transform | none exact; constants in `server/device_policy.py`, `server/panel_format.py` | partial |
| `server/fleet_migrate.py` (new) | migration/CLI | batch | `stub-server/devices_cli.py` (CLI) + `server/firmware_cli.py` | role-match |
| `stub-server/fleet_cli.py` (new) | CLI | CRUD | `stub-server/devices_cli.py` | exact |
| `stub-server/byos_server.py` (modify: setup, `bearer_ok`, `_resolve_device_id`) | controller | request-response | itself, lines 196-300, 660-680, 877-933 | exact |
| `stub-server/devices_cli.py` (modify: mirror into fleet.db) | CLI | CRUD | itself | exact |
| `deploy/backup/skypane_backup.py` (modify) | utility | batch/file-I/O | itself, lines 55-67, 121-137, 200-228 | exact |
| `deploy/activate.sh` (modify) | config/deploy | batch | itself, "Firmware import" lines 200-223 | exact |
| `pyproject.toml` (modify mypy lists) | config | n/a | existing `[tool.mypy]` `files` and `overrides` | exact |
| `server/test_fleet_db.py` (new) | test | CRUD | `server/test_history_db_scope.py`, `server/test_state_store.py` | role-match |
| `server/test_hardware.py` (new) | test | transform | `server/test_device_policy.py` | role-match |
| `server/test_fleet_migrate.py` (new) | test | batch | `server/test_firmware_cli.py` | role-match |
| `stub-server/test_fleet_auth.py` (new) | test | request-response | `stub-server/test_wake_interval_delivery.py` (`FrameServer`), `stub-server/test_devices_registry.py` | exact |
| `stub-server/test_phase47_freeze.py` (new) | test | request-response | `stub-server/test_wake_interval_delivery.py` | exact |
| `deploy/tests/test_backup.py` (extend) | test | file-I/O | itself (`TestFailureAndCleanupPaths`) | exact |
| `deploy/tests/test_activate.py` + `conftest.py` (extend) | test | batch | `test_firmware_import_failure_blocks_swap_previous_release_still_current`, `_write_fake_firmware_cli` | exact |
| Fixture generator for live-shaped state (new, `test-support/`) | test util | file-I/O | `test-support/skypane_test_support.py`, `skypane_history_helpers.py` | role-match |

## Pattern Assignments

### `server/fleet_db.py` (service, CRUD)

**Analog:** `server/history_db.py`

**Module header and bootstrap** (lines 1-40): leaf-module docstring stating import restrictions (stdlib only, never import companion or poll_loop), then the repo-root bootstrap:
```python
_HERE = os.path.dirname(os.path.abspath(__file__))  # server/
_REPO_ROOT = os.path.dirname(_HERE)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)
HISTORY_DB_FILENAME = "history.db"
```
Use `FLEET_DB_FILENAME = "fleet.db"` and a `fleet_db_path(state_dir)`.

**Connect pattern** (lines 181-208):
```python
os.makedirs(state_dir, exist_ok=True)
conn = sqlite3.connect(path, timeout=timeout, factory=_HistoryConnection)
conn.row_factory = sqlite3.Row
conn.execute("PRAGMA busy_timeout=5000")
...
conn.execute("PRAGMA journal_mode=WAL")
init_schema(conn)
```
Differences for fleet.db: also `PRAGMA foreign_keys=ON` on every connection; use `isolation_level=None` plus explicit `BEGIN IMMEDIATE` / `COMMIT` with `PRAGMA user_version = %d` set inside the same transaction (RESEARCH "Migration step skeleton"). Read-only open (byos auth path, dry-run) via `sqlite3.connect("file:...?mode=ro", uri=True)`.

**Thread scope pattern** (lines 211-264): thread-local `_SCOPE` plus `connection_scope(state_dir)` and `open_db` context managers (close on exit, rollback if `conn.in_transaction`). Copy the shape for byos (ThreadingHTTPServer, one thread per request).

---

### `stub-server/byos_server.py` (controller, request-response)

**Analog:** itself. These are the seams to edit; extract helpers so `do_POST` does not grow (80-line gate).

**Legacy file I/O to keep and mirror** (lines 196-205, 236-282):
```python
def load_state(state_dir):
    try:
        with open(state_path(state_dir)) as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {"tokens": {}}

def save_state(state_dir, state):
    _atomic_write(state_path(state_dir), json.dumps(state, indent=1))

def register_device(state_dir, mac, secret_sha256, replace=False):
    normalized = normalize_mac(mac)
    ...
    registry["devices"][normalized] = {"secret_sha256": secret_sha256}
    save_registry(state_dir, registry)
    return normalized
```
`load_registry` (236-250) fails closed to an empty registry on any error; the migration must not rely on that (abort on a malformed non-empty file).

**Secret compare** (lines 285-300): `secret_matches(registry, mac, presented)` uses `re.fullmatch(r"[0-9a-f]{64}", ...)`, `hashlib.sha256(...).hexdigest()`, `hmac.compare_digest`. Reuse it for the fleet.db lookup by building a `{"devices": {mac: {"secret_sha256": ...}}}` view so there is one definition.

**Token compare without early exit** (`bearer_ok`, lines 887-896):
```python
presented = auth[len("Bearer "):].encode("utf-8", "surrogateescape")
matched = False
for stored in list(self.state["tokens"].values()):
    stored_bytes = stored.encode("utf-8", "surrogateescape")
    if hmac.compare_digest(presented, stored_bytes):
        matched = True
return matched
```
Keep this loop; change only the candidate source (fleet.db rows first, then legacy `self.state["tokens"]` on fleet.db error).

**Default fallback to drop** (`_resolve_device_id`, lines 668-680): both `return "default"` sites (669 and 680) become `None`. Leave `device_report.json` untouched; test a file containing a `"default"` key.

**Setup / enrolment with dual-write** (`do_POST`, lines 913-933):
```python
mac = normalize_mac(body.get("mac")) if isinstance(body, dict) else None
...
registry = load_registry(self.args.state_dir)
if mac not in registry["devices"]:
    return self.send_json(403, {"detail": "device not registered"})
if not secret_matches(registry, mac, body.get("provision_secret")):
    return self.send_json(401, {"detail": "bad secret"})
token = secrets.token_hex(32)
self.state["tokens"][mac] = token
save_state(self.args.state_dir, self.state)
```
New code writes the token to fleet.db AND `save_state` (rollback guarantee). Registry lookup order: fleet.db, then `load_registry` on `except (sqlite3.Error, OSError)`; log once, set module-level `fleet_db_status`.

---

### `stub-server/fleet_cli.py` (CLI, CRUD)

**Analog:** `stub-server/devices_cli.py` (exact)

**Imports and bootstrap** (lines 27-32):
```python
import argparse, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import byos_server  # noqa: E402 - the sys.path bootstrap above must run first
```
Also import `server.fleet_db` and `server.hardware` (repo root on sys.path as byos does for `from server import ...`).

**Command shape** (lines 35-43): `cmd_*(args)` returns an int exit code; `ValueError` from the helper becomes `print("error: %s" % exc, file=sys.stderr); return 2`; not-found returns 1; success prints a one-line confirmation.

**List output, no secrets** (lines 61-72): print only a hash prefix (`secret_hash[:12] + "…"`), never the full hash or token.

**Parser** (lines 95-123): required `--state-dir` with no default ("never guess which registry to edit"), `add_subparsers(dest="command", required=True)`, `set_defaults(func=cmd_x)`; `main()` is `args = build_parser().parse_args(); return args.func(args)`; `sys.exit(main())`. Docstring documents exit codes 0/2/1. Verbs: users add/list/disable, devices add/assign, hardware list. `devices add` also calls `byos_server.register_device` (dual-write).

---

### `server/fleet_migrate.py` (migration CLI, batch)

**Analog:** `stub-server/devices_cli.py` for argparse/exit codes; `deploy/activate.sh` invokes it as `python3 -m server.fleet_migrate` like `server.firmware_cli` (`cd ${RELEASE_DIR}`). Read-only legacy inputs via `byos_server.load_state` and `byos_server.normalize_mac`. Must support `--dry-run`, `--state-dir`, `--owner-email`. Idempotence via a `meta('migrated_v1')` marker checked read-only first; never writes any legacy file. No in-repo analog for the dry-run in-memory DB; use RESEARCH Pattern 2.

---

### `deploy/backup/skypane_backup.py` (modify)

**Analog:** itself.

**Exclusion list** (lines 55-67): add `"fleet.db-wal"`, `"fleet.db-shm"` next to the `history.db*` entries. Keep `"fleet.db"` out of `KNOWN_EXCLUDED` if you want it handled as snapshot (history.db is in KNOWN_EXCLUDED and in `known` set, so the dir walk never archives it raw); mirror history.db exactly.

**Snapshot** (lines 121-137): generalise the hard-coded message:
```python
src = sqlite3.connect(src_path, timeout=30)
dst = sqlite3.connect(dst_path)
try:
    src.backup(dst)
    row = dst.execute("PRAGMA integrity_check").fetchone()
    if row is None or row[0] != "ok":
        raise RuntimeError("history.db backup failed integrity_check")  # -> use basename
```

**Archive step** (lines 200-207) and drift set (line 228): loop `for db_name in ("history.db", "fleet.db")` with `tmp_dir`, `snapshot_db`, `tar.add(snap_path, arcname=db_name, filter=_no_symlinks)`; `known = set(INCLUDE_FILES) | set(INCLUDE_DIRS) | {"history.db", "fleet.db"}`. Failure semantics: exception inside the tar block removes the partial and returns 1 with `snapshot failed: ...`.

---

### `deploy/activate.sh` (modify)

**Analog:** "Firmware import" block (lines 211-223):
```bash
IMPORT_RC=0
( cd "${RELEASE_DIR}" \
    && runuser -u skypane -- "${VENV}/bin/python3" -m server.firmware_cli \
        --state-dir "${STATE_DIR}" import-dir "${FIRMWARE_RELEASES_DIR}" ) || IMPORT_RC=$?
if [ "${IMPORT_RC}" -ne 0 ]; then
    echo "activate.sh: firmware import failed for ${SHA} - not swapping" >&2
    exit 1
fi
```
Insert after this block (before the Caddy rendering at ~line 225-262): `echo "==> Fleet migration"`, backup via `runuser -u skypane -- ... skypane_backup.py --state-dir ... --archive-dir ${BACKUP_ROOT}/archives --keep 14`, then `fleet_migrate --dry-run`, then `fleet_migrate`; each non-zero rc prints `activate.sh: ... - not swapping` to stderr and `exit 1`. Add `fleet_migrate --help` to the smoke list.

---

### `deploy/tests/conftest.py` + `test_activate.py` (extend)

**Analog:** `_write_fake_firmware_cli` (conftest lines 34-73) and `test_firmware_import_failure_blocks_swap_previous_release_still_current` (test_activate lines 537-550).

Fake CLI logs `'<name> ' + ' '.join(_args) + ' current=' + _current` to a call log and exits with an env-controlled rc (`FAKE_FIRMWARE_IMPORT_RC`); build `_write_fake_fleet_migrate` the same way (`FAKE_FLEET_MIGRATE_RC`, record `--dry-run`, record `current=` to prove it ran before the swap). Failure test shape:
```python
fake_release("f00d004"); r1 = run_activate("f00d004"); assert r1.returncode == 0, r1.stderr
fake_release("f00d005")
r2 = run_activate("f00d005", FAKE_FIRMWARE_IMPORT_RC="1")
assert r2.returncode != 0
assert "firmware import failed" in r2.stderr
assert os.readlink(fake_root.current_link) == "releases/f00d004"
```
Order assertion reads `fake_root.call_log.read_text()` lines (see lines 530-533).

---

### `stub-server/test_fleet_auth.py` and `stub-server/test_phase47_freeze.py` (test, request-response)

**Analog:** `stub-server/test_wake_interval_delivery.py` (exact)

**Imports/constants** (lines 13-52): `REPO_ROOT` on `sys.path`, `test-support` on `sys.path`, `from skypane_test_support import child_env`, `IMAGE_BYTES = 960000`, `ENROL_SECRET = "5" * 64`, `TEST_MAC`.

**Server harness** (lines 85-176): `FrameServer(state_dir)` writes `panel.bin` (`bytes(IMAGE_BYTES)`), calls `load_byos_module().register_device(...)` (module loaded by `importlib.util.spec_from_file_location`), launches `byos_server.py --image --port --sleep --state-dir` via `subprocess.Popen` with `child_env()` and `PYTHONUNBUFFERED=1`, waits for the `serving` line on stdout, retries on "Address already in use", then POSTs `/device/v1/setup` with `{"mac", "hw_rev", "provision_secret"}` to obtain the token; `display(battery_mv)` GETs `/device/v1/display` with `Authorization: Bearer` and `X-Battery-Mv`. Reuse or lift into a shared helper under `test-support/` for the before/after replay (start byos, poll, run migrate, restart byos on same dir, poll again, compare `image_hash`, `sleep_s`, other keys). Freeze test asserts on served JSON keys and `battery_state.json` / `poll_state.json` key sets from running code, never source text (companion/test_suite_guards.py rule).

---

### `deploy/tests/test_backup.py` (extend)

**Analog:** `TestFailureAndCleanupPaths` (lines 321-343). Restore test pattern: seed with `_seed_minimal_state(state_dir)`, create `fleet.db`, `skypane_backup.backup(str(state_dir), str(archive_dir), keep=3) == 0`, `(name,) = _archive_names(archive_dir)`, `_members(archive_dir / name)`, extract to an empty dir and open the DB. Corrupt-db case copies line 340: `(state_dir / "fleet.db").write_bytes(b"this is not a sqlite database" * 100)` then expect return 1, `"snapshot failed"` in `capsys.readouterr().out`, and empty archive dir.

---

### `pyproject.toml` (modify)

**Analog:** `[tool.mypy]` `files = [...]` (line 133) and `[[tool.mypy.overrides]] module = [...]` (line 156); entries like `"server/device_policy.py"` and `"server.device_policy"`. Add `server/fleet_db.py`, `server/hardware.py`, `server/fleet_migrate.py` (and `server.*` names) to both lists; annotate end to end, no PEP 695 syntax.

## Shared Patterns

### Atomic, private file writes
**Source:** `stub-server/byos_server.py` `_atomic_write(path, data, mode=None)` (line 132); `server/atomic_io.py`
**Apply to:** any legacy-file mirror write, any status file for the health signal (`save_registry` uses `mode=0o600`).

### Fail closed on identity, fail back on fleet.db
**Source:** `load_registry` docstring (lines 236-242) and RESEARCH Pattern 3
**Apply to:** byos auth. Corrupt fleet.db falls back to legacy files only, never to "allow all".

### Secret and token handling
**Source:** `secret_matches` (285-300), `bearer_ok` (887-896), `devices_cli.cmd_list` (68-71)
**Apply to:** fleet_db lookups, CLI output. `hmac.compare_digest` always, no early exit, hash prefix only in output, parameterised `?` SQL only.

### Single definitions
`byos_server.normalize_mac`, `register_device`, `skypane_backup.snapshot_db`, `history_db.connection_scope` shape. Do not retype.

### Conventions
Comments describe invariants only: no "Phase 48", "D-0x" or plan IDs (`scripts/check_comment_history.py check`). Functions at most 80 lines (`scripts/check_function_size.py`). English code and comments; no new dependency. Tests assert behaviour (served responses, restored archive), not source text.

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `server/hardware.py` | registry | transform | No existing profile registry. Build a frozen dataclass; pull values from `server/device_policy.py` (`BATTERY_DISCHARGE_CURVE`, `BATTERY_CRITICAL_MV`), `server/panel_format.py` (palette, packing) and byos `IMAGE_BYTES = 960000`; add a drift test that the legacy entry equals those constants. Env gate read at call time via `available_types(environ=os.environ)`. |
| Dry-run read-only/in-memory DB path in `fleet_migrate.py` | migration | batch | No read-only sqlite use exists; use RESEARCH Pattern 2 step 6. |
| Fleet status signal for the health page | status | pub-sub | Companion is out of scope; open question 3 in RESEARCH (status file written by byos vs `health_signals.py` row). Planner decides. |

## Metadata

**Analog search scope:** `server/`, `stub-server/`, `deploy/` (activate.sh, backup, tests), `test-support/`, `pyproject.toml`
**Files read:** `history_db.py` (targeted), `skypane_backup.py`, `devices_cli.py`, `byos_server.py` (targeted), `activate.sh` (targeted), `deploy/tests/conftest.py`, `test_activate.py`, `test_backup.py` (targeted), `test_wake_interval_delivery.py`
**Pattern extraction date:** 2026-10-28
