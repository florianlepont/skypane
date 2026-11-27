---
phase: 67-project-and-code-optimisation
plan: 06
subsystem: companion
tags: [dead-code, cleanup]
requires: [67-01]
provides: [nine zero-reference companion functions removed]
affects: [companion]
key-files:
  modified:
    - companion/console_fleet_view.py
    - companion/detection_actions.py
    - companion/detection_summary.py
    - companion/device_scope.py
    - companion/frame_state.py
    - companion/health_signals.py
    - companion/illustration_normalize.py
    - companion/pages/airlines_page.py
    - companion/resolve_dialog.py
decisions:
  - Tested-but-unused API kept as test seams; only zero-reference functions deleted.
metrics:
  completed: 2026-11-27
---

# Phase 67 Plan 06: Dead code deletion Summary

Nine functions with no reference in any tracked file (code, tests, units, deploy, docs) deleted from the companion; no behaviour change.

## Commits

- 7cd6f0c: `_cards_block`, `location_scope`, `summary_values`, `viewer_may_rename_current`, `is_long_overdue` (batch A)
- 74838b6: `battery_both_sentences`, `cached_normalized_png_bytes`, `_gap_trigger_attrs_html`, `trigger_attrs_html`, unused `type_title` parameter (batch B)

## Proof

Word-boundary search of each name over all tracked files outside `.planning` returned only its own definition before deletion, and nothing after. Imports made unused (`ui_components` in `detection_summary.py`) were removed. No test file was touched.

## Checks

- ruff clean; mypy: no issues in 51 source files.
- i18n, suite-guard, access-matrix (1961), freeze and golden render tests pass; `companion` suite 7451 passed, 12 skipped (Chromium and root-permission skips only).
- Collected ids: 17599 after; every id of the available baseline is present (`comm -23` empty). The baseline file held only 32 lines (truncated), so the strong check is that no test file changed.
- Render baselines and golden fixtures untouched.

## Deviations from Plan

**1. [Rule 1 - Deviation] `type_title` is a parameter, not a local.** In `airlines_page.py` it is an unused parameter of private `_type_fields` (single caller, no tests). Dropped the parameter and the argument at the call site; the `title` local in the caller is still used elsewhere.

## Kept (not deleted)

- `fmt_args` in `log_message` overrides (signature).
- All tested-but-unused API listed in the research (fleet_db, hardware, draw, giant render helpers and others) and all constants (i18n scan and reflection risk). `LONG_OVERDUE_INTERVALS` in `frame_state.py` stays (constant; now unreferenced by code).

## Self-Check: PASSED
