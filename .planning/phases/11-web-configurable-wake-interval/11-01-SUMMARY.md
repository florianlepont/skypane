---
phase: 11-web-configurable-wake-interval
plan: 01
subsystem: config
tags: [python, json, config-registry, validation]

# Dependency graph
requires:
  - phase: 10-quiet-hours
    provides: server/device_config.py's normalise_*()/load_device_config()/save_device_config() precedent shape (constants, normaliser, load key, save guard) this plan extends
provides:
  - "server/device_config.py: WAKE_INTERVAL_MIN_S=60/WAKE_INTERVAL_MAX_S=3600 (D-02)"
  - "server/device_config.py: normalise_wake_interval_s() - bounded-int read-path helper with the bool-is-an-int exclusion, degrading every hostile value to None"
  - "server/device_config.py: load_device_config()'s seventh key wake_interval_s, whose valid value set includes None (never-explicitly-set, D-07)"
  - "server/device_config.py: save_device_config()'s wake_interval_s keyword argument with a strict pre-write ValueError gate"
  - "server/test_config_history.py: 5 new checks proving the bounded-int contract, the bool-is-an-int regression guard, byte-identical-on-rejection, and carry-forward"
affects: [11-02-byos-server-wake-interval, 11-03-config-page-wake-interval-form, 11-04-companion-env-prefill]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "None-as-never-explicitly-set sentinel: the one registry field in device_config.py with no DEFAULT_* constant, distinct from every sibling field's degrade-to-default contract"

key-files:
  created: []
  modified:
    - server/device_config.py
    - server/test_config_history.py

key-decisions:
  - "wake_interval_s's unset state is None, not a hardcoded default - the true fallback (SKYPANE_SLEEP_S / --sleep) lives in a different OS process's argparse namespace and is not knowable in this module (D-07)"
  - "save_device_config() has no way to clear an already-set wake_interval_s back to unset - an empty numeric input means 'leave unchanged', never 'reject the save' (resolves 11-RESEARCH.md Open Question 2)"

patterns-established:
  - "Bounded-int registry field: constants + never-raising normaliser (degrade to None/default) + strict pre-write ValueError guard, with isinstance(value, int) and not isinstance(value, bool) as the mandatory bool-exclusion idiom"

requirements-completed: []  # this plan's own frontmatter declares requirements: [] (unmapped backlog phase promoted from SEED-002, per 11-RESEARCH.md <phase_requirements>)

coverage:
  - id: D1
    description: "load_device_config() returns a seventh wake_interval_s key, None until explicitly set, and every hostile on-disk value (bool, string, float, 30, 59, 3601) degrades to None"
    verification:
      - kind: unit
        ref: "server/test_config_history.py#_hand_written_hostile_wake_interval_s_yields_none"
        status: pass
      - kind: unit
        ref: "server/test_config_history.py#_normalise_wake_interval_s_bounds_and_bool_gotcha"
        status: pass
    human_judgment: false
  - id: D2
    description: "save_device_config() accepts exactly the inclusive range 60..3600, rejects everything else (including bools) with ValueError before touching the file, and leaves a pre-existing file byte-identical on every rejection"
    verification:
      - kind: unit
        ref: "server/test_config_history.py#_save_wake_interval_s_rejects_out_of_bounds_and_bools"
        status: pass
    human_judgment: false
  - id: D3
    description: "A save that supplies no wake_interval_s carries the stored value forward unchanged"
    verification:
      - kind: unit
        ref: "server/test_config_history.py#_wake_interval_s_carries_forward_on_unrelated_save"
        status: pass
    human_judgment: false

duration: 17min
completed: 2026-09-04
status: complete
---

# Phase 11 Plan 01: Wake-interval registry field Summary

**Added the `wake_interval_s` bounded-int field (60-3600s) to `server/device_config.py`'s config registry, with a deliberate `None` "never-explicitly-set" sentinel and a strict write-path gate that rejects bools via the `isinstance(value, int) and not isinstance(value, bool)` idiom.**

## Performance

- **Duration:** 17 min
- **Started:** 2026-09-04T07:33:33+02:00
- **Completed:** 2026-09-04T07:49:54+02:00
- **Tasks:** 2 completed
- **Files modified:** 2

## Accomplishments
- `WAKE_INTERVAL_MIN_S`/`WAKE_INTERVAL_MAX_S` constants (60/3600), grounded against `firmware/main/Kconfig.projbuild`'s `FP_MIN_REFRESH_SPACING_S` and the developer-confirmed one-hour ceiling
- `normalise_wake_interval_s()` — never-raising, degrades every hostile value (including a bool, per Python's `isinstance(True, int) is True` gotcha) to `None`
- `load_device_config()` now returns a seventh key, `wake_interval_s`, the single field whose valid value set includes `None`
- `save_device_config()` now accepts a `wake_interval_s` keyword, validated before the file is ever opened, carrying `None` forward from the current on-disk value like every other field
- Repaired all 7 full-document equality assertions in `server/test_config_history.py` the widened dict breaks by construction
- Added 5 new checks: bounds + bool-gotcha, hostile-on-disk-value degradation, save round-trip, save-rejects-with-byte-identity, and carry-forward — `EXPECTED_CHECK_COUNT` 39 → 44

## Task Commits

Each task was committed atomically:

1. **Task 1: Add the wake_interval_s registry field to device_config.py** - `330d2f9` (feat)
2. **Task 2: Add wake_interval_s coverage to test_config_history.py** - `b8c4525` (test)

**Plan metadata:** pending (docs: complete plan)

## Files Created/Modified
- `server/device_config.py` - two bound constants, `normalise_wake_interval_s()`, the seventh `load_device_config()` key, the `save_device_config()` write-path gate and carry-forward
- `server/test_config_history.py` - 7 repaired full-document equality literals, 5 new checks, bumped `EXPECTED_CHECK_COUNT`

## Decisions Made
- `wake_interval_s`'s unset state is `None`, not a `DEFAULT_*` constant — the one deliberate exception to this module's otherwise-universal "always return a concrete value" contract (D-07)
- No path exists to clear an already-set `wake_interval_s` back to unset through `save_device_config()` — resolves 11-RESEARCH.md's Open Question 2 in favor of "empty input means leave unchanged"

## Deviations from Plan

None - plan executed exactly as written. All acceptance criteria (module import checks, ruff, exact `git diff --name-only` per task, and the bumped harness count) verified as specified.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- The registry contract (`WAKE_INTERVAL_MIN_S`/`WAKE_INTERVAL_MAX_S`, `normalise_wake_interval_s()`, the seventh `load_device_config()` key, `save_device_config()`'s new keyword) is in place and covered by the 44/44 harness — Wave 2's plans 11-02 (`stub-server/byos_server.py`) and 11-03 (`companion/pages/config_page.py`) can now proceed independently
- `server/test_poll_loop.py` confirmed green (51/51) with no digest-mismatch regression; `server/requirements.txt` unchanged

---
*Phase: 11-web-configurable-wake-interval*
*Completed: 2026-09-04*
