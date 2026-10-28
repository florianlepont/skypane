# Phase 48: Fleet Data Model, Roles and Live-Frame Migration - Context

**Gathered:** 2026-10-28
**Status:** Ready for planning

<domain>
## Phase Boundary

One fleet database (`fleet.db`) records users, roles, devices (exactly one owner each), hardware types and locations. The live frame is migrated into it with no observable change (same image hash, same wake interval, no reflash, no re-enrolment). The fleet database is backed up with a tested restore, and a test enforces the Phase 47 freeze list.

Requirements: DATA-01..05. Out of scope: OTA registry rewrite (Phase 49), image format (50), per-device directories and poll loop (51-52), detection modes (53), Auth0 and web user management (54-55). Production deploy waits for Phase 47 to close or an explicit owner release.

</domain>

<decisions>
## Implementation Decisions

### Live-frame migration safety
- **D-01:** After migration, byos authenticates the live frame from `fleet.db` (MAC, secret hash, token), and `devices.json` is left untouched and valid, so the previous release still runs on post-migration state (expand-only).
- **D-02:** The migration is an idempotent `fleet_migrate` step run by the deploy script, after an automatic backup, with a `--dry-run` report that changes nothing. Never run at service start; the owner has no manual step.
- **D-03:** If `fleet.db` is absent, unreadable or corrupt at byos start, byos falls back to `devices.json` so the live frame keeps working, and the problem is logged and shown on the health page.
- **D-04:** Proof of "no observable change": a test replays a poll on a copy of the live frame's real state files before and after migration and compares image hash and wake interval; a second test re-runs the migration and asserts no byte changes. The frame's MAC, secret, token and file paths (`state_path = "."`) are kept.

### Hardware profiles
- **D-05:** Hardware types live in a committed, tested code registry (not a DB table). Fields: resolution, palette, image format, battery profile, firmware target. The legacy EE02 is an entry; adding a type is a commit.
- **D-06:** Two simulated types ship, enabled only by environment variable and never in production: a same-geometry clone of EE02, and an 800x480 landscape type.

### Users, roles, locations
- **D-07:** Users are created through a CLI (devices_cli style): email, role `admin`/`user`, disabled flag, unique `(iss, sub)` column ready for Phase 54. The migration creates the owner as `admin` and assigns the current frame to them. Role is stored locally only.
- **D-08:** A location is its own table (name, latitude, longitude, timezone) linked to a device; the current frame gets Orly. Each device has exactly one owner, enforced in the schema.
- **D-09:** The `"default"` device fallback is dropped in byos (research: `_resolve_device_id`).

### Freeze list, backup, restore
- **D-10:** `fleet.db` is backed up with the sqlite3 online backup API into the archive and added to the backup allow-list; a test restores the archive into an empty directory and checks the content.
- **D-11:** A written freeze list names what Phase 47 measures (wake cadence / `sleep_s`, battery telemetry, poll-state fields, image hash). A test compares served responses and those fields before and after migration and fails if any changes.

### Claude's Discretion
- Schema details (column names, `PRAGMA user_version` migration layout), module names (`fleet_db.py`, `hardware.py`, `fleet_migrate.py` per research), CLI verbs, plan split and waves.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Milestone planning
- `.planning/workstreams/v1-2/ROADMAP.md` — Phase 48 goal, success criteria, Phase 47 gate
- `.planning/workstreams/v1-2/REQUIREMENTS.md` — DATA-01..05
- `.planning/workstreams/v1-2/STATE.md` — decisions (registry rewrite is Phase 49; run `scripts/check_comment_history.py check` before this phase and record the result)
- `.planning/workstreams/v1-2/research/SUMMARY.md` — fleet.db / sqlite3 / user_version design, expand-only migration, owner decisions
- `.planning/workstreams/v1-2/research/ARCHITECTURE.md` — single-frame assumptions in code, components
- `.planning/workstreams/v1-2/research/PITFALLS.md` — live-frame migration while Phase 47 is open

### Phase 47 (must stay unaffected)
- `.planning/phases/47-integrated-field-validation-and-decision-record/47-CONTEXT.md` — what Phase 47 measures

### Code
- `stub-server/byos_server.py` — device registry (`devices.json`, `register_device`, `load_registry`, `secret_matches`), `sleep_s`, device resolution
- `stub-server/devices_cli.py` — operator CLI pattern to follow
- `server/device_policy.py`, `server/state_store.py`, `server/device_config.py`, `server/poll_cycle.py`, `server/history_db.py` — state paths and wake policy
- `deploy/backup/skypane_backup.py`, `deploy/backup/backup_gate.py`, `deploy/deploy.sh` — backup allow-list, deploy step
- `.claude/CLAUDE.md` — conventions (stdlib only, no new dependency, English comments, function size ≤ 80, mypy module list)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `devices_cli.py` imports byos_server's registry functions directly so format never drifts; mirror this for the fleet CLI.
- `atomic_io.py` / `_atomic_write`: atomic file writes with mode 0o600.

### Established Patterns
- stdlib + Pillow + requests only; `PRAGMA user_version` for sqlite migrations (already used for history DB); behaviour-over-source tests; comment-history guard.

### Integration Points
- byos device auth and token issue; backup script allow-list; deploy.sh; companion unaffected this phase.

</code_context>

<specifics>
## Specific Ideas

- Owner is French-speaking and not an engineer: anything the owner must do is plain French; repository docs stay English.

</specifics>

<deferred>
## Deferred Ideas

- Web UI for users/devices (Phases 54-55); registry rewrite and `*.pre-fleet` copy (Phase 49); per-device directories (Phase 51).

</deferred>

---

*Phase: 48-fleet-data-model-roles-and-live-frame-migration*
*Context gathered: 2026-10-28*
