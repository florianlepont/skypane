---
phase: 42-remote-firmware-update-over-the-air-ota-promoted-from-seed-0
plan: 01
subsystem: server
tags: [ota, firmware, registry, atomic-io, stdlib]

# Dependency graph
requires:
  - phase: 41-docs-repository-hygiene-and-closing-re-audit
    provides: "G-41 gate -- Phase 41 complete on main, Phase 36's atomic_write/exclusive_lock helpers present in server/atomic_io.py"
provides:
  - "server/firmware_registry.py: the single release registry module (storage, publish/schedule/cancel, and the pure offer/reconcile/view functions)"
  - "The registry.json / device_report.json / firmware/<sha>.bin storage layout under state_dir, defined and locked here for every later OTA surface to share"
affects: [byos-offer-route, poll-loop-reconcile, companion-update-page, ci-deploy-import]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Tolerant field-by-field JSON document loading (load_registry/load_device_report), matching server/device_config.py's load_device_config() contract: never raises, degrades to documented defaults"
    - "Every registry write goes through server.atomic_io.atomic_write under server.atomic_io.exclusive_lock -- no hand-rolled temp-file-then-rename, no second lock implementation"
    - "Pure decision functions (compute_offer, reconcile, update_view) take every timestamp as a parameter -- no clock reads, no I/O -- so device state derivation is testable without a filesystem"

key-files:
  created:
    - server/firmware_registry.py
    - server/test_firmware_registry.py
  modified: []

key-decisions:
  - "Filesystem-shape validation in the tolerant loaders is field-by-field (a malformed release/schedule/event entry is dropped or degraded individually), not document-wide fail-to-default -- matches the project's existing device_config.py tolerance contract and keeps one hostile field from discarding an otherwise-valid registry"
  - "compute_offer counts unreconciled counted-failure events from the requesting device's own event list (passed in as device_entry), so a third failure reported in the same poll that would grant a fourth attempt is caught before apply_reconcile ever runs"
  - "acknowledged() is shared verbatim by schedule_release, cancel_schedule and update_view (via a private _newest_event_for_schedule helper) so 'has the device started' has exactly one implementation"

requirements-completed: []  # OTA-01/05/06/10 are listed in this plan's frontmatter but are each shared across
                            # several plans in this phase (OTA-06 alone spans 6 plans, OTA-10 spans 6);
                            # REQUIREMENTS.md is left Pending here per this project's established convention
                            # (see Phase 39/40's ARC-*/CMP-* precedent) -- only the phase's own close-out plan
                            # flips these to Complete once byos/device/CI actually satisfy each clause.

coverage:
  - id: D1
    description: "Registry storage: tolerant load_registry/load_device_report, firmware/ directory layout, firmware_image_path, version floor helpers (parse_version, at_or_above_floor)"
    requirement: "OTA-10"
    verification:
      - kind: unit
        ref: "server/test_firmware_registry.py -- load_registry/load_device_report/parse_version/at_or_above_floor/firmware_image_path tests"
        status: pass
    human_judgment: false
  - id: D2
    description: "publish_release: SHA-256/size verified against the manifest, idempotent republish, refuses a different sha under the same version, never deletes anything"
    requirement: "OTA-10"
    verification:
      - kind: unit
        ref: "server/test_firmware_registry.py -- test_publish_release_* (12 tests)"
        status: pass
    human_judgment: false
  - id: D3
    description: "schedule_release / cancel_schedule / acknowledged: any published release at or above the floor whose version differs from running can be scheduled (older included); cancellable only until the device has acknowledged the offer"
    requirement: "OTA-05"
    verification:
      - kind: unit
        ref: "server/test_firmware_registry.py -- test_schedule_release_*, test_cancel_schedule_*, test_acknowledged_* (16 tests)"
        status: pass
    human_judgment: false
  - id: D4
    description: "Two-process concurrent publish_release/schedule_release loses no update -- every write goes through the same registry_lock"
    requirement: "OTA-10"
    verification:
      - kind: unit
        ref: "server/test_firmware_registry.py::test_concurrent_publish_and_schedule_loses_no_update"
        status: pass
    human_judgment: false
  - id: D5
    description: "compute_offer: the device offer gate (battery-low, no/failed schedule, version equals running, below floor, three counted failures, missing release all withhold it); no quiet-hours/display-off input exists on the function"
    requirement: "OTA-01"
    verification:
      - kind: unit
        ref: "server/test_firmware_registry.py -- test_compute_offer_* (11 tests, parametrized none-conditions)"
        status: pass
    human_judgment: false
  - id: D6
    description: "reconcile/apply_reconcile: device report events turned into installed/rollback/failed outcomes and notifications, exactly once per event, never mutating inputs, replay-safe"
    requirement: "OTA-06"
    verification:
      - kind: unit
        ref: "server/test_firmware_registry.py -- test_reconcile_*, test_apply_reconcile_writes_only_when_changed (11 tests)"
        status: pass
    human_judgment: false
  - id: D7
    description: "update_view: running_version/reported_at, state derivation (available/scheduled/in_progress/failed/installed) with timestamp, cancellable, rollback warning, releases history with installable/installed_at"
    requirement: "OTA-01"
    verification:
      - kind: unit
        ref: "server/test_firmware_registry.py -- test_update_view_* (8 tests)"
        status: pass
    human_judgment: false

# Metrics
duration: ~25min
completed: 2026-09-28
status: complete
---

# Phase 42 Plan 01: Firmware release registry Summary

**server/firmware_registry.py: the release registry storage, publish/schedule/cancel, and the pure offer/reconcile/view functions every OTA surface (byos, poll loop, companion, CI import) will share -- 88 tests, 99% coverage.**

## Performance

- **Duration:** ~25 min
- **Completed:** 2026-09-28
- **Tasks:** 3 (Task 1: G-41 gate check; Task 2: storage/publish/schedule/cancel; Task 3: pure offer/reconcile/view)
- **Files modified:** 2 (both new)

## Accomplishments

- Confirmed G-41 (Phase 41 complete on `origin/main`, Phase 36's `atomic_write`/`exclusive_lock` present) via the plan's own automated checks (a)-(d), all passing, before any edit
- `server/firmware_registry.py`: the `firmware/registry.json` / `firmware/device_report.json` / `firmware/<sha>.bin` storage layout, tolerant field-by-field loaders, `publish_release` (SHA-256/size verified, idempotent, never rebinds a version to a different sha), `schedule_release`/`cancel_schedule`/`acknowledged` (D-05's "cancellable only until the device starts" rule, shared by three call sites), `compute_offer` (the battery/schedule/floor/attempts/release gate with no quiet-hours input), `reconcile`/`apply_reconcile` (device report events to installed/rollback/failed outcomes and notifications, exactly once per event), and `update_view` (the Update page's state/cancellable/rollback/history view model)
- 88 passing tests in `server/test_firmware_registry.py`, including a two-process `multiprocessing` concurrency test proving no lost update under `registry_lock`, and a replay test proving `reconcile` produces no new notification on unchanged input
- 99% statement coverage on `server/firmware_registry.py` (required: 95%)

## Task Commits

Each task was committed atomically:

1. **Task 1: Gate G-41** - read-only, no files changed, no commit (verified via the plan's automated check, all four sub-checks passed)
2. **Task 2: Registry storage, publish, schedule and cancel** - `7b7aae28` (feat)
3. **Task 3: Pure offer, reconcile and view functions** - `2096c009` (feat)

**Plan metadata:** committed as part of this final docs commit (STATE.md/ROADMAP.md/REQUIREMENTS.md).

_Note: both feature tasks used `tdd="true"`; tests and implementation were authored and verified together against the plan's `<behavior>` contract rather than via two separately-committed RED/GREEN passes (see Deviations)._

## Files Created/Modified

- `server/firmware_registry.py` - the release registry module (storage, publish/schedule/cancel, pure offer/reconcile/view functions)
- `server/test_firmware_registry.py` - 88 behaviour tests for every exported function

## Decisions Made

- Tolerant loaders (`load_registry`, `load_device_report`) validate field-by-field and drop/degrade individually malformed entries rather than discarding the whole document on any single defect -- consistent with `server/device_config.py`'s existing `load_device_config()` contract, and defensively re-caps device events at 50 per device even though byos (a later plan) is the one that writes that file.
- `compute_offer` reads the *requesting device's own* unreconciled result events (via its `device_entry` parameter) to count attempts, so a third counted failure reported in the very poll that would otherwise grant a fourth attempt is caught before `apply_reconcile` (the poll loop's later, separately-timed reconciliation step) has run.
- Dropped the plan's literal `os.replace()`/`mkstemp()` phrasing from the module docstring (rewritten as "temp-file-then-rename") after the acceptance-criteria grep for hand-rolled atomic writes matched the docstring's own prose, not code -- reworded rather than suppressed, since the check is a legitimate proxy for "no second atomic-write implementation."
- Removed a defensive `not isinstance(device_id, str)` guard from `_normalise_device_report` (unreachable: `json.load()` always yields `str` dict keys) rather than adding a synthetic test to satisfy 100% coverage on dead code.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Decision-ID citations (D-01, D-05, D-06, D-08, D-11, D-13, D-15) left in code comments/docstrings violated the project's comment-history rule**
- **Found during:** Task 3, running `scripts/check_comment_history.py check` as required by every commit touching source files
- **Issue:** Several docstrings cited decision IDs from `42-CONTEXT.md` (e.g. "(D-05)", "(D-13)") and one cited the requirement ID "OTA-01" -- `CLAUDE.md` and the project rules explicitly forbid plan/ticket/decision/review/phase IDs in source comments, enforced in CI by this script
- **Fix:** Reworded every flagged docstring/comment to keep the *rationale* in plain English (e.g. "the function takes exactly these four inputs, so quiet hours and display-off structurally cannot influence the offer") without the ID citation
- **Files modified:** `server/firmware_registry.py`, `server/test_firmware_registry.py`
- **Verification:** `scripts/check_comment_history.py check` exits 0 with no findings; full test suite and ruff re-run clean afterward
- **Committed in:** `2096c009` (Task 3 commit, before it was made)

**2. [Rule 3 - Blocking] Coverage gap below the plan's own 95% acceptance bar on first pass**
- **Found during:** Task 3, running the plan's own coverage verification command
- **Issue:** The first full test pass measured 92% on `server/firmware_registry.py`, short of the 95% floor Task 3's acceptance criteria require, missing mostly defensive-degrade branches in the tolerant loaders and a few skip/continue branches in `compute_offer`/`reconcile`
- **Fix:** Added 28 targeted tests exercising each individually-malformed-field branch (release/schedule/last_outcome/event validation), `acknowledged()`'s None-schedule and unknown-kind paths, `publish_release`'s remaining manifest-field rejections, and `compute_offer`/`reconcile`'s skip/continue branches
- **Files modified:** `server/test_firmware_registry.py`
- **Verification:** Coverage rose to 99% (466 statements, 1 miss); full suite still 88/88 passing
- **Committed in:** `2096c009` (Task 3 commit)

---

**Total deviations:** 2 auto-fixed (1 comment-history compliance fix, 1 coverage gap closed by additional tests)
**Impact on plan:** Both fixes were required by the plan's own stated verification commands and acceptance criteria; no scope creep beyond what Task 3 already specified.

## Issues Encountered

None beyond the two auto-fixed items above.

## User Setup Required

None - no external service configuration required. This plan is server-side, stdlib-only, and touches no deployment or secrets configuration.

## Next Phase Readiness

- `server/firmware_registry.py` exports every name the interfaces block promised (`load_registry`, `load_device_report`, `publish_release`, `schedule_release`, `cancel_schedule`, `acknowledged`, `compute_offer`, `reconcile`, `apply_reconcile`, `update_view`, `parse_version`, `at_or_above_floor`, `firmware_image_path`, `registry_lock`) -- later plans in this phase (byos's offer route, the poll loop's reconcile call, the companion Update page, the CI deploy import) can build against these names as documented, unchanged.
- No blockers. The storage layout (`firmware/registry.json`, `firmware/device_report.json`, `firmware/<sha>.bin`) is defined and locked; `device_report.json` itself is still byos-owned and does not yet exist on disk in production until byos's own plan lands -- `load_device_report`'s tolerant-missing-file default already covers that gap.
- `REQUIREMENTS.md` was deliberately left untouched: OTA-01/05/06/10 are each shared across several later plans in this phase (byos, poll loop, firmware, CI), so this plan does not call `requirements mark-complete` for them -- matching this project's established convention of only flipping a shared requirement ID at the phase's own close-out plan.

---

*Phase: 42-remote-firmware-update-over-the-air-ota-promoted-from-seed-0*
*Completed: 2026-09-28*

## Self-Check: PASSED

- FOUND: server/firmware_registry.py
- FOUND: server/test_firmware_registry.py
- FOUND: .planning/phases/42-remote-firmware-update-over-the-air-ota-promoted-from-seed-0/42-01-SUMMARY.md
- FOUND: 7b7aae28 (feat: registry storage, publish, schedule, cancel)
- FOUND: 2096c009 (feat: pure offer, reconcile, view)
