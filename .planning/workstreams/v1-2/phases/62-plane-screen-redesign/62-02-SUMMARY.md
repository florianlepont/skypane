---
phase: 62-plane-screen-redesign
plan: 02
subsystem: config
tags: [layout, device-config, defaults]
requires: []
provides:
  - server/screen_layouts.py (LAYOUT_IDS, CLASSIC_LAYOUT_ID, DEFAULT_LAYOUT_ID, normalise_layout_id, is_giant_layout)
  - device_config "layout" key (load, save, validate)
affects: [later layout plans, poll cycle explicit layout pass]
key-files:
  created:
    - server/screen_layouts.py
    - server/test_screen_layouts.py
    - server/test_device_config_layout.py
  modified:
    - server/device_config.py
    - server/test_config_history.py
    - server/test_retired_notifications.py
    - companion/test_config_page_02.py
    - pyproject.toml
key-decisions:
  - "Layout follows the timezone precedent: the key is written only when it differs from DEFAULT_LAYOUT_ID, so saving the default removes the key and existing files keep their bytes"
  - "DEFAULT_LAYOUT_ID = b is the single constant; no other module hard-codes it"
requirements-completed: [PSR-01, PSR-06]
duration: short
completed: 2026-11-09
---

# Phase 62 Plan 02: Per-frame layout setting Summary

A typed stdlib leaf `server/screen_layouts.py` holds the layout ids (classic, a, b, c, a_diagonal) and the one default (b); `device_config` loads it normalised, validates it against the allow-list on save and writes it only when it is not the default.

## Tasks

| Task | Commit | Result |
|------|--------|--------|
| 1 Layout registry | a1c4683 | Constants, `normalise_layout_id`, `is_giant_layout`, tests; module and its mypy entry added |
| 2 Persist layout | 193d340 | `layout` key in load/save/merge, `_validate_layout`, golden-bytes test, exact-dict tests updated |

## Deviations from Plan

**1. [Rule 3] pyproject.toml edit.** Added `server/screen_layouts.py` to `[tool.mypy] files` as directed by the orchestrator (plan 01 had deferred it).

**2. [Rule 1] Extra exact-dict tests.** `server/test_retired_notifications.py` (key count 12 to 13) needed updating besides the listed files. `server/test_runway_config.py`, `server/test_detection_spec.py` and `server/test_state_writers.py` needed no change.

**3. Write rule.** The plan says "key written only when explicitly set"; implemented as "written only when not the default" (timezone precedent). An explicit save of `b` is equivalent to unset and removes the key.

## Verification

Full run of server, companion, stub-server and deploy tests: 9210 passed, 2438 skipped (browser/root-permission skips). ruff, mypy (31 files), function-size gate and comment-history guard pass. No golden fixtures, classic render output, Phase 47/47.1 or hardware/ files touched. `state.advance-plan` was not called.

Note for handoff: the layout default b only affects rendering once the poll cycle passes the layout explicitly (a later plan); no rendering behaviour changed here.

## Known Stubs

None.

## Self-Check: PASSED

Files exist; commits a1c4683 and 193d340 present.
