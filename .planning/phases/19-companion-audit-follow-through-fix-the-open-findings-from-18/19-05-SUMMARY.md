---
phase: 19-companion-audit-follow-through-fix-the-open-findings-from-18
plan: 05
subsystem: ui
tags: [companion, health-page, sparkline, staleness, severity, battery]

# Dependency graph
requires:
  - phase: 19-companion-audit-follow-through-fix-the-open-findings-from-18
    provides: "19-01 (wave 1): companion/battery.py's shared battery_percent() estimate, and health_page.py's stat-tile text-verdict idiom this plan's constants/docstrings build on top of"
provides:
  - companion/wake.py — the shared effective-wake-interval resolver (env_sleep_s(), effective_wake_interval_s()) and the derived device-staleness thresholds (device_staleness_thresholds()), a new page-independent companion module
  - Health's battery sparkline plots against a fixed 3000-4200 mV y-range with out-of-range clamping, and its dense-point-suppression threshold is now a pure function of canvas width, not a typed 39 (D-04/A-22)
  - Health's Device tile staleness is derived from the device's own effective wake cadence (3/12 missed wakes, floored at 5/20 minutes), a single battery-reading drop is now a warning rather than a page-level error, and overall_severity()/collect_anomalies() fold the CFG-04 coverage registry and the ADS-B source-fault flag into page severity for the first time (D-05/A-23)
affects: [19-12]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Shared, page-independent companion module (companion/wake.py) modelled on companion/battery.py, owning a cadence resolver and its derived thresholds so health_page.py never re-derives either"
    - "Fixed-range, clamped chart axis (companion/pages/health_page.py's SPARKLINE_Y_MIN_MV/MAX_MV) replacing a per-render min/max auto-scale, matching companion/battery.py's own fixed 3.3-4.2V estimate window"
    - "A geometry rule expressed as a pure function of its own inputs (_sparkline_dense_threshold(canvas_width_px)) rather than a typed magic constant, so it re-derives itself when an underlying measurement changes"
    - "Signature widening with fully-defaulted keyword parameters (overall_severity()/collect_anomalies()/_device_section()) to fold a new signal into an existing precedence table without breaking any of dozens of pinned 4-argument call sites"

key-files:
  created:
    - companion/wake.py
  modified:
    - companion/pages/health_page.py
    - companion/test_status_pages.py

key-decisions:
  - "D-04/A-22: the sparkline's Y-axis is now the single-cell LiPo's whole usable window (3000-4200 mV, the same span companion/battery.py's estimate uses) rather than a per-render min(values)/max(values) auto-scale — a flat series now draws flat instead of pinning to the canvas edge, and a 15mV wiggle now draws small instead of stretching to fill the whole chart"
  - "D-04: the retired typed _SPARKLINE_DENSE_POINT_THRESHOLD = 39 constant is now _sparkline_dense_threshold(_SPARKLINE_NARROWEST_CANVAS_PX) — a pure function of canvas width and dot diameter, honestly documented as still not solving the underlying 'server cannot know the real client width' limitation, only making the rule itself re-derivable"
  - "D-05/A-23: device staleness is now wake.device_staleness_thresholds(wake.effective_wake_interval_s(device_cfg)) — 3 missed wakes for a warning, 12 for an error, each floored at 5/20 minutes — replacing two fixed constants (1h/6h) that were simultaneously too slow for a healthy 30s-cadence device and irrelevant to any other cadence"
  - "D-05: battery_status() demotes a >=100mV inter-reading drop from 'error' to 'warn' — a single sampling artefact must not paint the whole page as an outage; the constant's own name (BATTERY_DROP_WARN_MV) already said 'warn'"
  - "D-05: overall_severity()/collect_anomalies() both gain coverage_state='ok' and source_fault=False as new, fully-defaulted keyword parameters — source_fault wins outright as 'error' (the page's most severe real state), then the three original states, then warn/disagreement_warn/coverage_state=='warn' — superseding this function's own former 'deliberate scope boundary' paragraph that had explicitly deferred this exact fold-in as a future decision"
  - "_read_health_inputs() grows two keys (device_config, registry_rows), partially reopening D-11's original 'registry stays a separate read' boundary for severity's sake — the registry read is wrapped in its own narrow (OSError, ValueError) guard so a registry failure degrades to 'no gaps' rather than taking the page down, while render()'s own registry CARD still degrades independently via its own unchanged fallback"

requirements-completed: [CFG-03]

# Metrics
duration: 25min
completed: 2026-09-11
---

# Phase 19 Plan 05: Health sparkline fix + wake-derived staleness + widened severity Summary

**New companion/wake.py resolves the device's real wake cadence; Health's battery sparkline now plots a fixed 3000-4200mV range with a width-derived density rule, device staleness is measured against that same cadence (floored at 5/20 minutes), a single battery dip is a warning not an outage, and page severity now also reflects the CFG-04 coverage registry and ADS-B source-fault flag.**

## Performance

- **Duration:** 25 min (2026-09-11T07:19:48Z first commit → 2026-09-11T07:35:37Z last task commit)
- **Started:** 2026-09-11T07:19:48Z (Task 1 commit)
- **Completed:** 2026-09-11T07:35:37Z
- **Tasks:** 3/3 complete
- **Files modified:** 3 (1 new: companion/wake.py)

## Accomplishments
- Closed A-22 (D-04): the battery sparkline's Y-axis is a fixed 3000-4200mV range (clamped, never auto-scaled), so a flat series draws flat and a 15mV wiggle draws as a small movement instead of a cliff; the dense-point-suppression threshold is now `_sparkline_dense_threshold(canvas_width_px)`, a pure function, not a typed 39.
- Closed A-23 (D-05): Device tile staleness now derives from the device's own effective wake cadence via new `companion/wake.py` (3 missed wakes = warn, 12 = error, floored at 5/20 minutes) instead of two fixed constants (1h/6h) that were simultaneously too generous for a healthy device and irrelevant to any other cadence; a single battery-reading drop is now a "warn", not a page-level "error"; and `overall_severity()`/`collect_anomalies()` now also read the CFG-04 unresolved-prefix registry's coverage state and the ADS-B source-fault flag, closing the gap where a real coverage gap or a real source outage was invisible to the page's own severity.
- New shared module `companion/wake.py`, modelled on `companion/battery.py`: three tested pure functions (`env_sleep_s()`, `effective_wake_interval_s()`, `device_staleness_thresholds()`), imported only by `health_page.py` this plan (its second consumer, plan 19-12, is out of scope here).

## Task Commits

Each task was committed atomically:

1. **Task 1: Create companion/wake.py — the effective wake interval and the derived staleness thresholds** - `4e2c382` (feat)
2. **Task 2: Fix the sparkline's y-range and make the density rule width-derived (D-04)** - `5a36d3a` (feat)
3. **Task 3: Derive device staleness from the wake cadence and widen overall_severity (D-05)** - `bcff367` (feat)

_No plan-metadata commit yet — SUMMARY.md and this plan's metadata commit follow this file's own creation, per worktree-mode instructions._

## Files Created/Modified
- `companion/wake.py` - New shared, page-independent module: `SLEEP_ENV_VAR`, `MISSED_WAKES_WARN`/`MISSED_WAKES_ERROR`, `STALE_WARN_FLOOR_S`/`STALE_ERROR_FLOOR_S`, `env_sleep_s()`, `effective_wake_interval_s()`, `device_staleness_thresholds()`
- `companion/pages/health_page.py` - `SPARKLINE_Y_MIN_MV`/`SPARKLINE_Y_MAX_MV` fixed-range constants + clamped `_point_y()`; `_sparkline_dense_threshold()` pure function replacing the typed `_SPARKLINE_DENSE_POINT_THRESHOLD = 39`; `STALE_DEVICE_WARN_S`/`STALE_DEVICE_ERROR_S` retired; `_device_section()` widened with `warn_s=None, error_s=None`; `battery_status()` returns `"warn"` not `"error"`; `overall_severity()`/`collect_anomalies()` widened with `coverage_state="ok", source_fault=False`; `_read_health_inputs()` grows `device_config`/`registry_rows` keys; `compute_health_state()` wires the new inputs through; `render()` reuses `state["registry_rows"]` with a fallback
- `companion/test_status_pages.py` - 5 new checks for `companion/wake.py` (Task 1), 4 new + 1 retargeted for the sparkline fix (Task 2), 5 new + 3 retargeted for the widened severity model (Task 3); `EXPECTED_CHECK_COUNT` 171 → 176 → 180 → 185

## Decisions Made
- `env_sleep_s()` deliberately does NOT apply `app.py`'s `[WAKE_INTERVAL_MIN_S, WAKE_INTERVAL_MAX_S]` clamp — that clamp exists solely so a value can be rendered into an HTML5 `min="60"` numeric input without failing constraint validation, and applying it here would measure the shipped `SKYPANE_SLEEP_S=30` deployment against a number the device was never actually configured to use.
- `_sparkline_dense_threshold()` is honestly documented as NOT solving the sparkline's underlying "no viewBox, server can't know the real client width" limitation — it only promotes the existing hand-derived arithmetic into a re-derivable function, using the narrowest measured canvas width as a deliberately conservative input.
- `overall_severity()`'s own former "deliberate scope boundary" docstring paragraph (which explicitly said folding source-fault/coverage in would be "a new decision, not an oversight") was rewritten in place rather than left standing beside contradicting code — it now records that D-05 IS that decision.
- `_read_health_inputs()`'s registry read is wrapped in its own `(OSError, ValueError)` guard, distinct from every other key's `_safe_query()`/SQLite guard, preserving the documented filesystem-vs-SQLite failure-mode split while still letting a registry failure degrade (to "no gaps") rather than raise.

## Deviations from Plan

None - plan executed exactly as written. All three tasks' acceptance criteria (shell commands and pinned harness checks) pass as specified in 19-05-PLAN.md.

## Issues Encountered

- The plan's own D-05 test-fixture guidance ("a device last seen 400 seconds ago is warn at a 30s cadence but ok at a 3600s cadence") did not specify how to deploy a 30s cadence through `compute_health_state()`'s real pipeline: `device_config.save_device_config()`'s own `wake_interval_s` validation enforces `[WAKE_INTERVAL_MIN_S=60, WAKE_INTERVAL_MAX_S=3600]`, so 30 cannot be saved through that path. Resolved by seeding the 30s case via `SKYPANE_SLEEP_S` (the `env_sleep_s()` fallback path `wake.effective_wake_interval_s()` already documents as the one place an un-clamped 30 legitimately reaches this codebase, matching the real shipped deployment) and the 3600s case via `device_config.save_device_config()` at the top of its valid range — both restored/cleaned up in a `finally` block. No code change; test-fixture-only.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `companion/wake.py` is a fully independent, tested module (`env_sleep_s()`, `effective_wake_interval_s()`, `device_staleness_thresholds()`) ready for plan 19-12's second consumer (retargeting `companion/app.py`'s `env_wake_interval_default()`-adjacent Settings pre-fill code to delegate to it) without any further groundwork.
- `overall_severity()`/`collect_anomalies()`'s widened 6-parameter signatures are fully backward compatible (every pre-existing 4-argument call site is unaffected) — any future signal that should feed page severity can follow the identical pattern.
- No blockers. `scripts/run-all-tests.sh` run in full: only the five documented pre-existing root-sandbox failures (2 in `companion/test_companion_app.py`, 2 in `server/test_manual_resolutions.py`, 1 in `companion/test_status_pages.py` — all read-only-directory/`anomaly_active()` cases that fail identically on untouched main because this sandbox runs as root) appear; zero new failures.

## Self-Check: PASSED

All created/modified files verified present on disk (companion/wake.py, companion/pages/health_page.py, companion/test_status_pages.py, this SUMMARY.md); all three task commits (4e2c382, 5a36d3a, bcff367) verified present in git log.

---
*Phase: 19-companion-audit-follow-through-fix-the-open-findings-from-18*
*Completed: 2026-09-11*
