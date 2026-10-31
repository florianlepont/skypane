---
phase: 56-per-hardware-rendering-battery-profiles-health-and-credits
plan: 10
subsystem: poll-cycle
tags: [poll_cycle, hardware-profile, landscape, byos]
requires: ["56-04", "56-07", "56-09"]
provides:
  - run_once / load_cycle_context profile keyword, CycleContext.profile
  - profile battery thresholds in the cycle's hysteresis
  - poll_supported based on layout family
  - poll-now passes the device profile (non-live only)
key-files:
  modified:
    - server/poll_cycle.py
    - companion/device_scope.py
    - companion/app.py
    - companion/test_device_scope.py
    - companion/test_device_poll.py
    - companion/test_device_isolation.py
    - companion/test_theme_picker_profile.py
    - stub-server/test_device_fleet.py
  created:
    - server/test_poll_cycle_profile.py
requirements-completed: [HWR-01]
completed: 2026-10-30
---

# Phase 56 Plan 10: Poll-cycle profile seam Summary

`run_once(profile=)` and `load_cycle_context(profile=)` carry the hardware profile on `CycleContext`; all seven `build_canvas` sites pass `profile=ctx.profile`, and the low/critical hysteresis uses `profile.battery` values. `profile=None` passes no override kwargs, so the legacy path is unchanged.

## Commits
- d627177d poll_cycle profile seam and thresholds, server/test_poll_cycle_profile.py
- 23e0f167 poll_supported by layout family, poll-now passes the profile
- Task 3 commit: BYOS raw/container landscape test, theme-picker test scope fix

## Behaviour
- `poll_supported`: true for portrait at 1200x1600 and any registered landscape profile; false for unknown/gated-off types and families without a renderer.
- `_handle_poll_now` passes `profile=device_scope.profile_for(device)` only for non-live devices; the live frame call passes no profile kwarg.
- Landscape `run_once` writes 192000-byte `panel.bin`; BYOS serves it raw and as a container decoding to 800x480; live frame hash and sleep_s unchanged; portrait polling still works afterwards. No BYOS production change was needed.

## Verification
- `./scripts/run-all-tests.sh`: 6138 passed, 566 skipped (Chromium not installed locally), coverage gate ok.
- Golden, Phase 47 freeze and e2e pipeline tests pass untouched. ruff, mypy, function-size (max 80), comment-history clean.

## Deviations from Plan
- [Rule 3 - Blocking] Existing unsupported-hardware tests in `companion/test_device_poll.py` used the landscape device as the unsupported example; with the new rule they now retype that device to an unknown hardware type (fixtures `unsupported_app`, `unsupported_page_app`). The plan's `test_geometry_decides` was renamed `test_layout_family_decides` with extra cases.
- [Rule 3 - Blocking] `companion/test_theme_picker_profile.py` (plan 56-11) leaked a request scope (a SimpleNamespace device) into later tests on the same xdist worker, producing the 18 intermittent browser/page failures also seen in the 56-09 run. Added an autouse reset fixture. Test-only.
- Poll-now test for landscape uses the real app subprocess with fake providers (test_device_isolation.py) plus an in-process spy test asserting the profile argument.

## Known Stubs
None.

## Self-Check: PASSED
