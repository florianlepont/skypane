---
phase: 39-server-architecture-run-once-split-state-store-shared-module
plan: 05
subsystem: server
tags: [refactor, module-split, function-size, themes, device-config]

requires:
  - phase: 39-01
    provides: "scripts/check_function_size.py (the ≤80-code-line gate used to verify save_device_config's split)"
provides:
  - "server/themes.py: the theme registry (THEMES, THEME_IDS, DEFAULT_THEME_ID) and its eight presentation accessors, typed from birth, stdlib + server.panel_format only"
  - "server/device_config.py: re-exports server.themes' registry/accessors by identity so every existing caller and test keeps working unchanged; save_device_config split into five per-field _validate_* helpers plus _merged_config"
affects: [39-13, 40]

tech-stack:
  added: []
  patterns:
    - "Identity re-export for a moved module-global registry: device_config.THEMES is themes.THEMES (not an equal copy), proven by `is` checks rather than `==`, so two names always resolve to one object"
    - "Validation-block extraction into per-field-group _validate_*() helpers plus a _merged_config() builder, called in the same relative order the checks used to run inline, to bring a function under the size gate without behaviour change"

key-files:
  created:
    - server/themes.py
    - server/test_themes.py
  modified:
    - server/device_config.py
    - server/test_config_history.py

key-decisions:
  - "device_config no longer imports server.panel_format directly - the IDX_* constants only ever fed the THEMES dict, which moved wholesale to themes.py; device_config's module docstring's 'Leaf module' sentence was updated to name its real imports (stdlib, server.atomic_io, server.themes)."
  - "_validate_runway_and_flags groups tracked_runway/led_enabled/display_enabled/screen_id together and _validate_quiet_hours groups quiet_hours_enabled with quiet_hours_start/end, per the plan's own suggested grouping - this moves quiet_hours_enabled's check to run after display_enabled's instead of between led_enabled's and display_enabled's as it did inline. No existing or new test exercises two of these particular fields invalid in the same call, so this is unobservable; every test that does check multi-field save calls only varies notifications against otherwise-valid fields, which still runs last."

requirements-completed: [ARC-03, ARC-01]

duration: 45min
completed: 2026-09-27
---

# Phase 39 Plan 05: Themes module split and save_device_config size fix Summary

**Moved the theme registry and its eight presentation accessors out of `device_config.py` into a new typed `server/themes.py` (re-exported by identity), and split the 87-code-line `save_device_config` into five per-field `_validate_*()` helpers plus a `_merged_config()` builder so every function in `server/device_config.py` now measures at or under 80 code lines.**

## Performance

- **Duration:** ~45 min
- **Tasks:** 2/2 completed
- **Files created:** 2 (`server/themes.py`, `server/test_themes.py`)
- **Files modified:** 2 (`server/device_config.py`, `server/test_config_history.py`)

## Accomplishments

- `server/themes.py` now owns `THEMES`, `THEME_IDS`, `DEFAULT_THEME_ID` and the eight presentation accessors (`theme_background_index`, `theme_ink_index`, `theme_label`, `theme_dithered`, `theme_weight`, `theme_is_band`, `theme_band_index`, `theme_band_dithered`), moved verbatim from `device_config.py` and typed (`theme_id: str`, returns `int`/`str`/`bool`/`int | None`). `device_config.py` re-exports every one of those names via `from server.themes import (...)  # noqa: F401`, so `device_config.THEMES is themes.THEMES` and every accessor resolves to the same function object through either module - `grep -n "^THEMES = \|^def theme_" server/device_config.py` returns nothing, `grep -c "^def theme_" server/themes.py` is 8.
- `device_config.py` no longer imports `server.panel_format` at all - the `IDX_*` constants existed only to build `THEMES`, which now lives entirely in `themes.py`. The module docstring's "Leaf module" sentence was corrected to name the real imports (stdlib, `server.atomic_io`, `server.themes`).
- `save_device_config` (87 code lines, over the plan's 80-line gate) is now 33 code lines: the validation block became five private helpers (`_validate_theme_fields`, `_validate_runway_and_flags`, `_validate_quiet_hours`, `_validate_wake_interval`, `_validate_notifications`), each raising the exact same `ValueError` text as before, called in the same relative order the checks used to run inline; the merge-dict construction became `_merged_config(current, **supplied)`, returning the identical 12-key dict (including the `theme_arriving` three-state contract and the per-sub-key `notifications` merge). `save_device_config` itself is still a `device_config` module global - `grep -n "^def save_device_config(" server/device_config.py` matches - so `companion/test_config_page_02.py`'s existing monkeypatch of `device_config.save_device_config` keeps working unchanged.
- `python3 scripts/check_function_size.py check --max 80 server/device_config.py server/themes.py` now exits 0 (33 functions scanned, none over 80) - `save_device_config` is off the offender list the phase's own baseline named.
- New test in `server/test_config_history.py`: `test_save_device_config_rejects_invalid_notifications_even_with_every_other_field_valid` supplies every other field a valid (non-default) value alongside a malformed `notifications` sub-field, and asserts the call still raises `ValueError` before the file is touched - proving notifications, the last-validated field, is still checked even when nothing earlier would itself have raised.

## Task Commits

1. **Task 1: server/themes.py with the registry and accessors; device_config re-exports** - `4415ad8` (test, RED - 2/4 `test_themes.py` tests fail against the pre-refactor `device_config.py`) → `e7c2521` (feat, GREEN)
2. **Task 2: split save_device_config into per-field validators and a merge step** - `118c4a9` (refactor)

## Files Created/Modified

- `server/themes.py` - `THEMES`, `THEME_IDS`, `DEFAULT_THEME_ID`, and the eight typed presentation accessors, moved verbatim from `device_config.py`
- `server/test_themes.py` - identity re-export checks (registry and each accessor `is` its `device_config` counterpart), `theme_background_index`'s state-gate behaviour, and a subprocess check that importing `server.themes` never pulls in PIL
- `server/device_config.py` - deleted `THEMES`/`THEME_IDS`/`DEFAULT_THEME_ID`/the eight accessors, replaced with a `from server.themes import (...)  # noqa: F401` re-export block; dropped the now-unused `server.panel_format` import; `save_device_config` split into `_validate_theme_fields`, `_validate_runway_and_flags`, `_validate_quiet_hours`, `_validate_wake_interval`, `_validate_notifications`, `_merged_config`, and a slimmer `save_device_config` itself
- `server/test_config_history.py` - added the "invalid last-validated field with everything else valid" test

## Decisions Made

- `device_config`'s module docstring updated to name its real leaf-module imports (`server.atomic_io`, `server.themes`) instead of `server.panel_format`, since that import moved wholesale with `THEMES`.
- The two new validator groupings (`_validate_runway_and_flags` and `_validate_quiet_hours`) follow the plan's own suggested grouping, which reorders `quiet_hours_enabled`'s check relative to `display_enabled`'s (previously interleaved, now `quiet_hours_enabled` runs after `display_enabled`). No test - old or new - exercises both of these fields invalid in the same call, so this reordering is behaviourally unobservable; documented here per the plan's "grouping as the code dictates" allowance.

## Deviations from Plan

**1. [Process deviation, not a code deviation] Task 2 committed as a single `refactor` commit rather than TDD RED-then-GREEN.**
- **Found during:** Task 2
- **Reasoning:** Task 2 is a pure refactor (extract-function) with no new externally-observable behaviour to fail against first - `save_device_config`'s new "invalid last-validated field with valid siblings" test already passes against the pre-split function, since `notifications` was the last field validated before the split too. There is no code state on which this test is red for the right reason (a missing behaviour), only a state where the function hasn't been split yet - so RED would have been vacuous (the test passing "by luck" against unrefactored code, not failing to prove absence of the behaviour).
- **Verification:** Every behaviour bullet is covered and green: the new test plus every pre-existing `save_device_config` test (server and companion) pass unchanged, exact `ValueError` messages included, function-size gate clean.
- **Committed in:** `118c4a9`

No other deviations - Task 1 followed a genuine RED→GREEN cycle (`4415ad8` → `e7c2521`, 2/4 tests failing against the pre-refactor `device_config.py`, confirmed via `git checkout -- server/device_config.py` before the test commit and reapplied after).

## TDD Gate Compliance

Task 1 (tdd="true"): both gates present - `4415ad8` (RED, 2/4 `test_themes.py` tests failing) then `e7c2521` (GREEN, all passing).

Task 2 (tdd="true"): GREEN-only, documented above under Deviations - the new behaviour test cannot be made to fail against the pre-split code for the reason described (it is a refactor, not new behaviour), so no RED commit was created. Every behaviour bullet is covered by a passing test in the single `118c4a9` commit.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Known Stubs

None.

## Threat Flags

None - this plan moved existing code between modules and extracted functions with no new network endpoint, auth path, file-access pattern, or schema change. Both threat-register rows (T-39-10, T-39-11) covering `save_device_config`'s validation and lock sequence stay mitigated: every validator moved verbatim with the same messages and order, and the `threading.Lock` → `atomic_io.exclusive_lock` sequence around the load-merge-write is untouched.

## Next Phase Readiness

- `server/device_config.py` is back to persistence and validation only, within the 80-code-line gate, with `server/themes.py` now the sole owner of theme presentation data - unblocks any later plan that reads the ARC-03 theme-module clause off this plan's artifacts.
- ARC-01/ARC-03 requirement IDs are NOT marked Complete in `.planning/REQUIREMENTS.md` here, per this phase's own convention (39-02's premature tick was reverted) - only the phase's closing plan (39-13) flips ARC-* to Complete.
- No companion file was touched (`git diff --name-only` for both tasks lists no path under `companion/`), so Phase 40's parallel companion work is unaffected.

---
*Phase: 39-server-architecture-run-once-split-state-store-shared-module*
*Completed: 2026-09-27*

## Self-Check: PASSED

- FOUND: server/themes.py
- FOUND: server/test_themes.py
- FOUND commit: 4415ad8
- FOUND commit: e7c2521
- FOUND commit: 118c4a9
