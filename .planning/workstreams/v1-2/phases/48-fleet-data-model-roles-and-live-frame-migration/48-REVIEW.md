---
phase: 48-fleet-data-model-roles-and-live-frame-migration
reviewed: 2026-10-29T00:00:00Z
depth: standard
files_reviewed: 17
files_reviewed_list:
  - companion/health_signals.py
  - companion/i18n_fr/health.py
  - deploy/activate.sh
  - deploy/backup/skypane_backup.py
  - server/fleet_db.py
  - server/fleet_migrate.py
  - server/hardware.py
  - stub-server/byos_server.py
  - stub-server/devices_cli.py
  - stub-server/fleet_cli.py
  - test-support/skypane_frame_server.py
  - test-support/skypane_live_state.py
  - stub-server/test_fleet_auth.py
  - stub-server/test_phase47_freeze.py
  - server/test_fleet_migrate.py
  - deploy/tests/test_activate.py
  - deploy/tests/test_backup.py
findings:
  critical: 1
  warning: 7
  info: 3
  total: 11
status: issues_found
---

# Phase 48: Code Review Report

**Reviewed:** 2026-10-29
**Depth:** standard
**Files Reviewed:** 17 (the four test files were not read in full; the review covers the 13 source and support files)

## Summary

No SQL injection (all values are bound; the two interpolated PRAGMAs take constants or an int). No shell injection in activate.sh (`.env` is parsed with an anchored sed, never sourced, and the email is allow-listed and passed as one quoted array element). Migration is transactional and idempotent by design, and output names MACs and counts only. The auth bridge in byos_server.py never degrades to allow-all.

The real problems are at the seams between the legacy files and fleet.db. Removal and revocation do not stay in step across the two stores, which leaves tokens valid and can wedge the deploy. The "dry-run" does not prove what activate.sh says it proves.

## Structural Findings (fallow)

None provided.

## Narrative Findings (AI reviewer)

## Critical Issues

### CR-01: `devices_cli remove` leaves the bearer token behind; the token stays valid and then aborts the migration

**File:** `stub-server/devices_cli.py:65-77`, `server/fleet_migrate.py:140-141`, `stub-server/byos_server.py:1047-1057`
**Issue:** `cmd_remove` deletes the MAC from `devices.json` but never touches `byos_state.json`. The orphan token has two effects.
1. `bearer_ok()` checks tokens only. It never checks registry membership, so the removed device keeps authenticating in legacy mode. That includes the fallback taken when fleet.db is corrupt or too new.
2. `fleet_migrate._read_tokens` raises `LegacyStateError("... token for unregistered device")` for any token whose MAC is not in the registry. Both the dry-run and the real run in activate.sh then exit 2, so every later deploy fails ("not swapping") until someone hand-edits `byos_state.json`. The "Action requise" hint is not printed in that case because it fires only when the email is unset.

**Fix:** Delete the token in `cmd_remove` as `fleet_cli._mirror_remove` already does. Also make the migration tolerate orphan tokens by skipping them (count them in the report) rather than aborting:
```python
# devices_cli.cmd_remove, after save_registry
state = byos_server.load_state(args.state_dir)
if state["tokens"].pop(mac, None) is not None:
    byos_server.save_state(args.state_dir, state)
# fleet_migrate._read_tokens: `continue` for unregistered MACs instead of raising
```

## Warnings

### WR-01: Dry-run does not exercise the apply path, but activate.sh claims it proves the migration on a throwaway copy

**File:** `deploy/activate.sh:238-240`, `server/fleet_migrate.py:340-341`
**Issue:** `--dry-run` only calls `plan_migration` against a read-only snapshot. Failures that appear only at apply time are not caught: `_resolve_owner` raising "no recorded bootstrap owner", FK or UNIQUE violations, a hardware gate rejection, a too-new schema (`FleetDbTooNew`). The comment promises "a throwaway copy", and `fleet_db.connect_memory()` exists but nothing uses it. The real run then fails after the dry-run passed. Nothing is half-applied, because the transaction rolls back.
**Fix:** In dry-run, copy fleet.db (via the sqlite backup API) into a temp dir and run `_apply` there, or at least run the apply logic against `connect_memory()` seeded from the snapshot. Otherwise correct the comment.

### WR-02: `issue_token` can leave a token in fleet.db only, and can 500

**File:** `stub-server/byos_server.py:379-393`
**Issue:** The fleet.db transaction commits before `save_state()`. If the legacy write raises `OSError` (disk full, read-only), the exception is not caught in `issue_token` or `_enrol`. The client gets a 500, `state["tokens"][mac]` is already mutated in memory, and the DB holds a token the device never received. The docstring says "no token is known to only one store", which is false in this path.
**Fix:** Wrap the legacy write: on `OSError`, roll the DB token back (`set_device_token(conn, mac, None)` or the previous value), restore `state["tokens"]`, and return `None` so `_enrol` answers 503.

### WR-03: A revoked or removed token can be resurrected from byos's in-memory state

**File:** `stub-server/byos_server.py:391-392`, `stub-server/fleet_cli.py:226-251`
**Issue:** `Handler.state` is loaded once at startup. `issue_token` rewrites the whole `byos_state.json` from that copy. If the operator revokes a token with the CLI while byos runs (the CLI only prints a warning), the next enrolment of any device writes the revoked token back to the legacy file. In normal fleet mode the DB is authoritative, so this is harmless. It becomes a live credential again as soon as the fleet.db fallback triggers.
**Fix:** In `issue_token`, re-read the legacy file under a lock, merge only the new MAC, and write. Do not persist the startup snapshot.

### WR-04: A freshly created, still-empty fleet.db reports as "fault"

**File:** `server/fleet_db.py:183-185`, `stub-server/byos_server.py:337-361`
**Issue:** `connect()` creates a zero-byte file before migrating. `_fleet_view` opens it read-only, and `meta_get` hits a missing `meta` table. That raises `sqlite3.OperationalError`, which is recorded as `STATUS_FAULT` and surfaces as a Health warning. The window is brief. A crash between create and migrate makes it persistent. In `fleet_migrate`, `_snapshot_from` handles `schema_version == 0` correctly, but `_fleet_view` does not.
**Fix:** In `_fleet_view`, treat `schema_version(conn) == 0` as `STATUS_ABSENT`.

### WR-05: Pre-migration backup aborts every deploy if fleet.db fails `integrity_check`, and each deploy consumes a retention slot

**File:** `deploy/activate.sh:244-249`, `deploy/backup/skypane_backup.py:129-150, 207-208`
**Issue:** Two problems.
1. `snapshot_db` raises on a corrupt fleet.db, so `backup()` returns 1 and activate.sh stops. A corrupt fleet.db blocks the deploy that could ship the fix, with no override.
2. activate.sh runs the backup with `--keep 14`, the same pool as the nightly archives. Several deploys in a day evict nightly archives, and the off-box pull still expects them. The archive name has one-second granularity, so two runs in the same second overwrite each other.

**Fix:** Give the pre-deploy backup its own archive subdirectory or prefix with its own retention. Allow an explicit break-glass skip env var for the corrupt-DB case.

### WR-06: fleet.db and its token column go into archives whose mode is umask-dependent

**File:** `deploy/backup/skypane_backup.py:205-214, 220`
**Issue:** `fleet.db` now holds device bearer tokens in plaintext (`devices.token`). `fleet_db` carefully creates the DB at 0600, but the archive is opened with `tarfile.open(partial_path)` and gets `0666 & ~umask`. `os.makedirs(archive_dir)` uses the default mode too. If the service umask is 022, the tokens are readable by every local user through the archive. `byos_state.json` already had this exposure; the new DB widens it.
**Fix:** Create the partial file with `os.open(..., 0o600)` and `tarfile.open(fileobj=...)`, or `os.fchmod`/`umask(0o077)` at the start of `backup()`. Do the same for `.sha256`.

### WR-07: Bootstrap owner may not be an admin, and the dry-run output says otherwise

**File:** `server/fleet_migrate.py:230-234, 310`
**Issue:** `_ensure_owner` returns an existing user as-is. If that user was created earlier with `fleet_cli users add --role user`, or is disabled, the migration reports "create the owner as admin" but the owner is not an admin. In that case the fleet has no admin and ownership of the live frame sits with a plain or disabled user.
**Fix:** In `_ensure_owner`, check the existing row's role and disabled flag and raise `MigrationError` if the user is not an enabled admin. Alternatively, word the output as "ensure".

## Info

### IN-01: `FleetDbError` (too-new schema) is not caught by `fleet_migrate.main`

**File:** `server/fleet_migrate.py:359-371`
**Issue:** `FleetDbTooNew` is raised from `fleet_db.connect` inside `_apply`. It is not a `MigrationError` or `sqlite3.Error`, so the CLI exits with a traceback instead of `error: ...` and rc 2. Add `fleet_db.FleetDbError` to the first `except`.

### IN-02: The activate.sh hint is shown for any dry-run exit code 2

**File:** `deploy/activate.sh:262-264`
**Issue:** rc 2 also covers `LegacyStateError`, a bad email, and others. When `SKYPANE_BOOTSTRAP_ADMIN_EMAIL` is unset, the "Action requise" hint is printed even when the real cause is a malformed legacy file. Print the migrator's own stderr, or distinguish the cause with a dedicated exit code.

### IN-03: A legacy-file mutation inside the SQLite transaction is not atomic with COMMIT

**File:** `stub-server/fleet_cli.py:145-149, 215-218, 243-246`
**Issue:** The legacy write happens inside the DB transaction, but `COMMIT` comes after it. If `COMMIT` fails (busy or disk error), the legacy file has already changed while the DB has not. This is rare and recoverable by re-running the migration, but the "stores stay equal" comment overstates it. Also, `transaction()` in `fleet_db.py` does not wrap a failed `COMMIT` in a `ROLLBACK`.

---

_Reviewed: 2026-10-29_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
