---
phase: 39-server-architecture-run-once-split-state-store-shared-module
plan: 03
subsystem: server
tags: [dependency-injection, module-globals, illustrations, manual-resolutions, colour-rules, poll-cycle]

requires:
  - phase: 39-server-architecture-run-once-split-state-store-shared-module
    provides: "39-01: scripts/check_function_size.py and 39-ARC-BASELINE.md (the module-global-setter inventory this plan removes); 39-02: server/device_policy.py and server/state_store.py (unwired shared modules, unaffected by this plan)"
provides:
  - "server/plane/colour_rules.py: resolve_effective_theme_id(state, flight, device_cfg, calendar_theme_id=None, rules=None) - no process-wide cache, no setter"
  - "server/plane/manual_resolutions.py: airline_name_for_prefix(prefix, registry=None) - no process-wide cache, no setter"
  - "server/plane/enrich.py: manual_registry=None threaded through airline_source_from_callsign/airline_from_callsign/resolve_route/note_unresolved_prefix/clear_resolved_unresolved_prefix"
  - "server/plane/illustrations.py: override_dir_for_state_dir(state_dir=None) with no process-wide default fallback - the only per-call state_dir=None means vendored-only"
  - "server/plane/render.py: build_canvas(..., state_dir=None) and _build_active_canvas(..., state_dir=None), forwarded to both illustrations.select_illustration() calls"
  - "server/poll_loop.py: _run_once_locked() loads both registries once per cycle (colour_rules.load_colour_rules(state_dir), manual_resolutions.load_manual_resolutions(state_dir)) and passes them (manual_registry=/rules=) plus state_dir=state_dir explicitly down the call chain"
affects: [39-04, 39-05, 39-06, 39-07, 39-08, 39-09, 39-10, 39-13]

tech-stack:
  added: []
  patterns:
    - "Per-cycle input as explicit parameter: a registry the poll cycle needs once per cycle is loaded once at the top of _run_once_locked() and passed down as a keyword argument at every consuming call site, instead of being cached behind a module-global setter."
    - "None-means-empty default: every new keyword parameter (rules=None, registry=None, manual_registry=None, state_dir=None) treats None (or a wrong-shaped value) as the empty/no-override case - byte-identical to a process that never called the deleted setter."

key-files:
  created: []
  modified:
    - server/plane/colour_rules.py
    - server/plane/manual_resolutions.py
    - server/plane/enrich.py
    - server/plane/illustrations.py
    - server/plane/render.py
    - server/poll_loop.py
    - server/test_colour_rules.py
    - server/test_manual_resolutions.py
    - server/test_enrich.py
    - server/test_illustrations.py
    - server/test_poll_loop.py
    - server/test_render.py

key-decisions:
  - "Tasks 1 and 2 are committed together (single commit, not two), exactly as the plan's own acceptance criteria anticipated: Task 1 alone deletes the setters poll_loop.py still calls, which would leave the full suite red between commits. The plan explicitly permits this and asks it to be stated here."
  - "poll_loop.py's `import server.plane.illustrations as illustrations` became unused once the setter call was deleted (state_dir now flows straight through render.build_canvas() instead of being primed into illustrations.py) - removed as a Rule 3 blocking fix (ruff F401)."
  - "test_illustrations.py's `import pytest` became unused once the autouse setter-reset fixture was deleted - removed as a Rule 3 blocking fix (ruff F401)."

requirements-completed: []

duration: ~55min
completed: 2026-09-27
---

# Phase 39 Plan 03: Explicit injection replaces the three module-global setters Summary

**Deleted `illustrations.set_override_state_dir`, `manual_resolutions.set_manual_registry_state_dir` and `colour_rules.set_colour_rules_state_dir` (and their three module-globals); every per-cycle input they used to cache is now an explicit keyword parameter (`state_dir=`, `registry=`/`manual_registry=`, `rules=`) that `poll_loop.py` loads once per cycle and threads down the call chain.**

## Performance

- **Duration:** ~55 min
- **Tasks:** 2/2 completed (committed together - see Deviations)
- **Files modified:** 12 (0 created)

## Accomplishments

- `colour_rules.py` and `manual_resolutions.py` no longer hold any process-wide cache: `resolve_effective_theme_id(..., rules=None)` and `airline_name_for_prefix(prefix, registry=None)` read only their own arguments, `None` (or a wrong-shaped value) meaning the empty registry - identical behaviour to a process that never called the deleted setter.
- `illustrations.py`'s `override_dir_for_state_dir(state_dir=None)` lost its process-wide default fallback; a falsy `state_dir` now always means vendored-only, with no global to consult.
- `enrich.py` grew a `manual_registry=None` keyword on `airline_source_from_callsign`, `airline_from_callsign`, `resolve_route`, `note_unresolved_prefix` and `clear_resolved_unresolved_prefix`, forwarded through to `manual_resolutions.airline_name_for_prefix(prefix, manual_registry)` - positional parameters and every return value unchanged.
- `render.py`'s `build_canvas`/`_build_active_canvas` gained `state_dir=None`, forwarded to both `illustrations.select_illustration()` calls (main and previous card); the hold-screen builders (`_build_battery_empty_canvas`/`_build_display_off_canvas`/`_build_quiet_hours_canvas`/`_build_empty_canvas`) never consult it, since they draw no illustration.
- `poll_loop.py`'s `_run_once_locked()` replaced the three setter calls with two loads right after `os.makedirs` (`manual_registry = manual_resolutions.load_manual_resolutions(state_dir)`, `colour_rules_registry = colour_rules.load_colour_rules(state_dir)`), then passes `manual_registry=` to every `enrich.resolve_route`/`note_unresolved_prefix`/`clear_resolved_unresolved_prefix` call, `rules=colour_rules_registry` to both `colour_rules.resolve_effective_theme_id` calls, and `state_dir=state_dir` to all 5 `render.build_canvas` calls in the live path (the confirmed-state-None empty branch, the promoted branch, both branches of the held-repaint block, and the never-detected-empty branch). The 2 hold-kind calls (quiet hours/display off/battery empty) are unchanged, since hold screens draw no illustration.
- 337 tests pass across the five Task-1 test files plus a full-suite run of 2952 passed/139 skipped at 94% coverage (`./scripts/run-all-tests.sh`, exit 0); ruff and the comment-history guard are clean across the whole repo.

## Task Commits

Tasks 1 and 2 are committed together in a single commit (see Deviations for why):

1. **Tasks 1+2: explicit injection replaces the three module-global setters, poll_loop wired** - `8af4af3` (feat)

## Files Created/Modified

- `server/plane/colour_rules.py` - deleted `_cached_rules`/`set_colour_rules_state_dir`; `resolve_effective_theme_id(..., rules=None)`
- `server/plane/manual_resolutions.py` - deleted `_cached_registry`/`set_manual_registry_state_dir`; `airline_name_for_prefix(prefix, registry=None)`
- `server/plane/enrich.py` - `manual_registry=None` keyword threaded through 5 functions
- `server/plane/illustrations.py` - deleted `_override_state_dir`/`set_override_state_dir`; `override_dir_for_state_dir(state_dir=None)` with no global fallback
- `server/plane/render.py` - `build_canvas`/`_build_active_canvas` gained `state_dir=None`, forwarded to both `select_illustration()` calls
- `server/poll_loop.py` - the setter block replaced with two per-cycle loads; `manual_registry=`/`rules=`/`state_dir=` threaded to every consuming call site in the live path; removed the now-unused `illustrations` import
- `server/test_colour_rules.py` - every setter call retargeted to a `rules=` argument (via `load_colour_rules()` or a direct dict, including the tampered-cache test); added a hasattr-absence test
- `server/test_manual_resolutions.py` - retargeted the cache round-trip test to `airline_name_for_prefix(prefix, registry)` vs. no argument; added a hasattr-absence test
- `server/test_enrich.py` - deleted the autouse setter-reset fixture; every setter call retargeted to `manual_registry=manual_resolutions.load_manual_resolutions(tmp)`
- `server/test_illustrations.py` - deleted the autouse setter-reset fixture; retargeted the round-trip test to `select_illustration(..., state_dir=tmp)` vs. no argument; added a hasattr-absence test; removed the now-unused `pytest` import
- `server/test_poll_loop.py` - removed every setter call and `finally:` reset; extended the illustration-selection fakes' signatures with `state_dir=None`; retargeted `test_manual_registry_loaded_once_per_cycle_from_its_own_state_dir` to assert through cycle output (`route_source`/`last_route`) instead of the deleted global; added a new illustration-override end-to-end test
- `server/test_render.py` - extended `_SelectIllustrationSpy`/`_forced_illustration_pair`/`_forced_illustration`'s fake signatures to accept `state_dir=None`; added a new override-vs-vendored `build_canvas(..., state_dir=)` test

## Decisions Made

- Tasks 1 and 2 are one commit, not two - the plan itself anticipated this ("commit Tasks 1 and 2 together if the executor's per-task commit would otherwise be red, and say so in the SUMMARY"), since `poll_loop.py` still called all three deleted setters until Task 2's edits landed.
- Removed poll_loop.py's now-unused `illustrations` import and test_illustrations.py's now-unused `pytest` import (Rule 3 blocking fixes - ruff F401 - both are direct, mechanical consequences of deleting the setter call sites/autouse fixture the plan's own action already specified).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Removed poll_loop.py's now-unused `illustrations` import**
- **Found during:** Task 2's verify step (`ruff check .`)
- **Issue:** Deleting `illustrations.set_override_state_dir(state_dir)` left `import server.plane.illustrations as illustrations` with no remaining reference in `poll_loop.py` - state_dir now flows straight through `render.build_canvas()` instead of being primed into `illustrations.py` via a module-level default.
- **Fix:** Removed the import line.
- **Files modified:** `server/poll_loop.py`
- **Verification:** `ruff check .` exits clean; full suite still 2952 passed.
- **Committed in:** `8af4af3`

**2. [Rule 3 - Blocking] Removed test_illustrations.py's now-unused `pytest` import**
- **Found during:** Task 1's verify step (`ruff check server`)
- **Issue:** Deleting the `@pytest.fixture(autouse=True)` setter-reset fixture left `import pytest` with no remaining reference in the file.
- **Fix:** Removed the import line.
- **Files modified:** `server/test_illustrations.py`
- **Verification:** `ruff check server` exits clean; `server/test_illustrations.py` still passes in full.
- **Committed in:** `8af4af3`

**3. [Rule 3 - Blocking] Removed `(ARC-04)`/`(ARC-04, ...)` parentheticals from six new test docstrings**
- **Found during:** Task 2's verify step (`scripts/check_comment_history.py check`)
- **Issue:** The new hasattr-absence tests and the two new state_dir-threading tests each named the requirement ID in their docstring, violating the project's "no plan/decision/requirement IDs in comments" rule.
- **Fix:** Reworded each docstring to state the same fact without the ID (e.g. "exposes no module-global setter and no process-scoped cache" with no trailing parenthetical).
- **Files modified:** `server/test_colour_rules.py`, `server/test_illustrations.py`, `server/test_manual_resolutions.py`, `server/test_poll_loop.py` (2 docstrings), `server/test_render.py`
- **Verification:** `scripts/check_comment_history.py check` exits 0 with no output; full suite still 2952 passed.
- **Committed in:** `8af4af3`

---

**Total deviations:** 3 auto-fixed, all Rule 3 (blocking - required for a clean `ruff check` and comment-history guard).
**Impact on plan:** All three are mechanical cleanups directly caused by this plan's own deletions/additions, not scope creep. No behaviour changed by any of them.

## Issues Encountered

**Acceptance-criteria grep self-reference:** Task 2's acceptance criterion `grep -rn "set_override_state_dir\|set_manual_registry_state_dir\|set_colour_rules_state_dir" server companion stub-server test-support scripts --include=*.py` returns nothing does NOT hold literally: it matches three lines, one in each of `server/test_colour_rules.py`, `server/test_illustrations.py` and `server/test_manual_resolutions.py` - the hasattr-absence tests Task 1's own `<action>` explicitly required ("Add one test per module asserting the removed names are absent (`not hasattr(module, name)`)"). These are string literals proving the names are gone, not live call sites. A call-site-specific check confirms zero actual invocations remain anywhere in the repo:
```
grep -rn "set_override_state_dir(\|set_manual_registry_state_dir(\|set_colour_rules_state_dir(" server companion stub-server test-support scripts --include=*.py
```
returns nothing. Documented here rather than silently declared "passing" against the letter of the acceptance criterion.

## User Setup Required

None - no external service configuration required.

## Behaviour changes

- **D-5 (accepted, developer-decided):** the companion theme preview, which never passes a `state_dir` to `illustrations.select_illustration()`, now renders vendored illustrations only. Before this plan, an in-process `/poll-now` trigger left the module-global `_override_state_dir` set to the last-used state dir, which the preview's bare `select_illustration()` call happened to inherit; ARC-04's removal of that global is exactly what closes this leak. No companion file was edited by this plan - the behaviour change is a pure consequence of deleting `illustrations.set_override_state_dir`/`_override_state_dir`.
- **Retargeted manual-registry test:** `test_manual_registry_loaded_once_per_cycle_from_its_own_state_dir` (server/test_poll_loop.py) no longer calls `enrich.airline_from_callsign()` after `run_once()` returns (that relied on the deleted global surviving past the cycle). It now captures each cycle's own stdout log line and persisted `poll_state.json` state, asserting `route_source=manual` and `last_route["airline_name"] == "Zephyr Air"` for the seeded state dir, and their absence for a second cycle against an empty, different state dir with the same callsign prefix. The invariant under test (the registry is reloaded fresh from THIS cycle's own `state_dir`, never carried over from the previous cycle's) is unchanged; only the assertion mechanism moved from an inspectable global to the cycle's own observable output.

## Known Stubs

None.

## Threat Flags

None - `T-39-05` (override path resolution keeps its `_UNSAFE_KEY_RE` gate, only the state-dir source moved from a global to an explicit argument) and `T-39-06` (the theme-preview behaviour change above) are both already named in this plan's own threat register, not new undocumented surface.

## Next Phase Readiness

Every per-cycle input the three deleted setters used to hide is now a visible parameter on the functions that need it, and `poll_loop.py` loads each registry exactly once per cycle and threads it down explicitly - the shape the later `run_once` split (ARC-01) needs to lift these same values onto `CycleContext` fields with no further call-site rewiring. Full suite green (2952 passed/139 skipped, 94% coverage), ruff and the comment-history guard clean, companion untouched. No blockers.

## Self-Check: PASSED

- FOUND: server/plane/colour_rules.py
- FOUND: server/plane/manual_resolutions.py
- FOUND: server/plane/enrich.py
- FOUND: server/plane/illustrations.py
- FOUND: server/plane/render.py
- FOUND: server/poll_loop.py
- FOUND commit: 8af4af3

---
*Phase: 39-server-architecture-run-once-split-state-store-shared-module*
*Completed: 2026-09-27*
