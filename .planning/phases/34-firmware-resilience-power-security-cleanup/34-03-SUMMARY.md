---
phase: 34-firmware-resilience-power-security-cleanup
plan: 03
subsystem: auth
tags: [byos, enrolment, registry, hmac, sha256, devices_cli, stub-server]

# Dependency graph
requires: []
provides:
  - "byos_server.py's POST /device/v1/setup gated by a per-device registry (devices.json), replacing the shared --secret"
  - "registry_path/normalize_mac/load_registry/save_registry/register_device/secret_matches helper functions in stub-server/byos_server.py"
  - "stub-server/devices_cli.py operator CLI (add/remove/list/revoke-token)"
  - "stub-server/test_devices_registry.py, a pytest-compatible contract harness (14 checks)"
  - "deploy/README.md 'Device enrolment (per-device secret)' migration section"
affects: [phase-34-plan-05-provision-script, phase-34-plan-06-firmware-nvs-secret, phase-36, phase-37, phase-39]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Fail-closed registry read (load_registry): missing/corrupt devices.json enrols nobody, the inverse of load_state()'s fail-open contract"
    - "hmac.compare_digest on SHA-256 hex digests for secret comparison, never =="
    - "Registry file written 0600 via os.open + os.fdopen, atomic tmp-write + os.replace"
    - "Accepted-and-ignored CLI flag with a startup stderr warning, so a stale systemd unit cannot crash-loop mid-migration"

key-files:
  created:
    - stub-server/devices_cli.py
    - stub-server/test_devices_registry.py
  modified:
    - stub-server/byos_server.py
    - stub-server/test_poll_cycle.py
    - server/test_pipeline_e2e.py
    - scripts/run_all_tests.py
    - deploy/skypane-byos.service
    - deploy/skypane.env.example
    - deploy/README.md
    - stub-server/README.md
    - stub-server/VENDOR.md

key-decisions:
  - "load_registry() fails CLOSED (missing/corrupt devices.json enrols nobody) - the deliberate opposite of load_state()'s existing fail-open contract"
  - "--secret is retired but still accepted (ignored, with a startup warning) rather than removed from argparse, so an old unit file mid-migration does not crash-loop byos"
  - "devices.json written 0600 via os.open (not chmod after write) so there is no window where the file is briefly world-readable"
  - "devices_cli.py --state-dir has no default - an operator must name the directory explicitly, so a wrong path can never silently edit the wrong registry"

requirements-completed: [FW-08]

# Metrics
duration: 20min
completed: 2026-09-23
---

# Phase 34 Plan 03: Byos per-device enrolment registry Summary

**byos_server.py's POST /device/v1/setup now requires each MAC's own SHA-256-hashed secret from a devices.json registry (hmac.compare_digest, fail-closed), replacing the shared --secret with a devices_cli.py-managed per-device store.**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-09-23T14:20:00Z (approx.)
- **Completed:** 2026-09-23T14:37:53Z
- **Tasks:** 3
- **Files modified:** 10 (2 created, 8 modified)

## Accomplishments
- `POST /device/v1/setup` is gated by a per-device registry (`devices.json`): a registered MAC presenting its own secret gets a fresh token that revokes its previous one; a wrong secret (including the retired shared one, or another device's) is refused with the existing token untouched; an unregistered MAC is refused outright; a missing or corrupt registry refuses everyone (fail closed)
- `stub-server/devices_cli.py`, a new stdlib operator CLI, manages the registry (`add`/`remove`/`list`/`revoke-token`) by importing byos_server.py's own functions, so the on-disk format never drifts between the two
- `stub-server/test_devices_registry.py` proves all of D-34-01's rules over real HTTP (14/14 checks); confirmed RED (1/14) against the unmodified shared-secret handler before implementing
- The two pre-existing enrolment harnesses (`stub-server/test_poll_cycle.py`, `server/test_pipeline_e2e.py`) now seed the registry before enrolling and keep their exact prior check counts (46/46, 7/7)
- `deploy/README.md`, `deploy/skypane.env.example`, `stub-server/README.md`, and `stub-server/VENDOR.md` document the registry and a no-crash-loop migration path off the shared secret

## Task Commits

Each task was committed atomically (Task 1 split into TDD RED/GREEN commits per the plan's `tdd="true"` marker):

1. **Task 1a: RED - failing registry contract test** - `d2319af` (test)
2. **Task 1b: GREEN - registry helpers, gated setup handler, devices_cli.py** - `89f56a8` (feat)
3. **Task 2: seed the registry in the two existing enrolment harnesses** - `b4b365e` (test)
4. **Task 3: deploy migration docs (unit file, env example, READMEs, VENDOR.md)** - `18f795b` (docs)

**Plan metadata:** committed in this same response, immediately after this file (docs: complete plan)

## Files Created/Modified
- `stub-server/byos_server.py` - added `registry_path`/`normalize_mac`/`load_registry`/`save_registry`/`register_device`/`secret_matches`; rewrote the `/device/v1/setup` branch of `do_POST` to gate on the registry; `--secret` retired (accepted, ignored, warns)
- `stub-server/devices_cli.py` - new operator CLI: `add --mac --secret-sha256 [--replace]`, `remove --mac`, `list`, `revoke-token --mac`; `--state-dir` required, no default
- `stub-server/test_devices_registry.py` - new pytest-compatible (`test_*` + plain `assert`) contract harness, 14 checks, plus a `__main__` runner printing `PASS`/`FAIL` and `devices-registry: N/N checks pass`
- `stub-server/test_poll_cycle.py` - `Harness.start_server()` registers both fixture MACs before the subprocess starts; the two positive setup calls send `provision_secret`; `EXPECTED_CHECK_COUNT` (46) untouched
- `server/test_pipeline_e2e.py` - `BYOSHarness.start()` registers all three fixture MACs (idempotent across the two harness instances sharing one state_dir); the three setup calls send `provision_secret`
- `scripts/run_all_tests.py` - registered `stub-server/test_devices_registry.py` next to `stub-server/test_poll_cycle.py` in both `HARNESSES` and `EXPECTED_SLOWEST`; corrected stale harness-count comments (24 -> 25)
- `deploy/skypane-byos.service` - dropped the `--secret ${SKYPANE_BYOS_SECRET}` ExecStart line
- `deploy/skypane.env.example` - removed `SKYPANE_BYOS_SECRET`; documented the registry; companion-password paragraph no longer cross-references it
- `deploy/README.md` - new "Device enrolment (per-device secret)" section (provision, register, list/remove, revoke-token, migration checklist); "Write the real env file" and "Secrets discipline" updated
- `stub-server/README.md` - new "Enrol a device" section with the local `devices_cli.py` registration command
- `stub-server/VENDOR.md` - ninth local-modification entry for the registry; corrected the "everything else is verbatim" list and the re-pinning checklist's modification count (eight -> nine)

## Decisions Made
- `load_registry()` fails CLOSED, the deliberate opposite of `load_state()`'s existing fail-open contract in the same file — a missing or corrupt `devices.json` must enrol nobody, never fall back to accepting everyone
- `--secret` stays in argparse, accepted and ignored with a startup warning, rather than being removed — this is what lets a systemd unit still passing it (mid-migration, before `provision.sh` reinstalls the unit file) start cleanly instead of crash-looping on an unrecognized argument
- `devices.json` is created 0600 via `os.open(..., 0o600)` before the first write, not `chmod`ed after — there is no window where the file is briefly world-readable
- `devices_cli.py --state-dir` has no default, unlike `byos_server.py`'s own `--state-dir` (which defaults to the script's directory) — an operator managing a live registry must always name the directory explicitly

## Deviations from Plan

None — plan executed exactly as written. One note on an acceptance-criterion command that reads misleadingly rather than a deviation: `git diff stub-server/test_poll_cycle.py | grep -c EXPECTED_CHECK_COUNT` returns 1, not the literal 0 the plan's acceptance criteria text names, because the `HARNESS_ENROL_SECRET` constant was inserted two lines above `EXPECTED_CHECK_COUNT`'s definition and git's default 3-line diff context pulls that line into the same hunk as unchanged context (no leading `+`/`-`). Verified directly: `git diff ... | grep -E "^[+-].*EXPECTED_CHECK_COUNT"` returns nothing, and the harness still reports `poll-cycle: 46/46 checks pass` — the value the criterion actually cares about is unchanged.

## Issues Encountered
None.

## User Setup Required
None — no external service configuration required. The live VPS migration itself (registering real devices, deleting the stale env line) is an operator action documented in `deploy/README.md`, not something this plan performs.

## Next Phase Readiness

- Server-side FW-08 (D-34-01) is complete and tested. Plan 34-05 (provisioning script) and plan 34-06 (firmware NVS secret read) are unblocked to build against this registry's contract: `provision_secret` is a 64-lowercase-hex secret; `secret_sha256 = hashlib.sha256(secret_hex.encode("ascii")).hexdigest()`; `devices_cli.py add --mac <mac> --secret-sha256 <hash>` is the registration command.
- **Note for Phase 37 (SEC-07, "byos secret via env"):** this plan retires the shared-secret half of SEC-07 outright — there is no more `SKYPANE_BYOS_SECRET` to move into an env var, since byos no longer has one operator-wide secret at all. The **live** VPS env file will still carry a stale `SKYPANE_BYOS_SECRET=...` line until an operator deletes it by hand (harmless — `byos_server.py` no longer reads it); phase 37's own plan 37-11 (already merged on `main`, ahead of this branch) already accounts for this shape: it removes the stale line from the unit/`skypane.env.example` at CP-11, expects `def load_registry` in `byos_server.py`, `devices.json` in the state dir, and `--secret` retired-but-accepted with no `SKYPANE_BYOS_SECRET` anywhere in `byos_server.py`, the unit file, or `skypane.env.example` — this plan's implementation matches that shape.
- **Note for future backup/ops tooling:** `devices.json` (per-device secret hashes) must be backed up alongside `byos_state.json` — losing it without a re-provisioning path forces every frame to be re-enrolled by hand. Phase 37's plan 37-04 already lists `devices.json` in its backup scope.
- No blockers. Ready for phases 36, 37, 39 to continue editing `byos_server.py` — this plan's changes were kept confined to the module docstring, the import block, the new helper block after `save_state`, the `/device/v1/setup` branch of `do_POST`, and `main()`'s `--secret` handling, exactly as the plan's scope rule required.

---
*Phase: 34-firmware-resilience-power-security-cleanup*
*Completed: 2026-09-23*

## Self-Check: PASSED

All 11 created/modified files confirmed present on disk; all 4 task commit
hashes (`d2319af`, `89f56a8`, `b4b365e`, `18f795b`) confirmed in `git log`.
