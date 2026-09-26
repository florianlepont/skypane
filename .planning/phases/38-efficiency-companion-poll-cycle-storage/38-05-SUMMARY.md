---
phase: 38-efficiency-companion-poll-cycle-storage
plan: 05
subsystem: companion
tags: [health-page, severity, python, pytest]

# Dependency graph
requires:
  - phase: 38-efficiency-companion-poll-cycle-storage
    provides: "38-01's efficiency probe/baseline instruments (no direct code dependency for this plan, but the phase's instruments-first rule)"
provides:
  - "health_signals(state_dir, now) — every Health severity/anomaly/state signal, no markup built"
  - "safe_health_signals(state_dir, now) — fail-closed wrapper mirroring safe_health_state()"
  - "health_state_from_signals(signals) — the markup step that renders exactly compute_health_state()'s historical dict from one signals snapshot"
  - "compute_health_state() re-expressed as health_state_from_signals(health_signals(...)), same public contract"
  - "_device_state/_pipeline_state/_battery_state/_disagreement_warn state-only siblings each _x_section() builder now calls for its own state"
affects: ["38-10 (lazy page_context)", "38-12 (freshness token)"]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "State/markup split via a snapshot dict: health_signals() computes every state once; health_state_from_signals() renders markup from that snapshot's inputs and copies (never recomputes) its states/severity/anomalies"
    - "Each markup builder (_device_section/_pipeline_section/_battery_section/_corroboration_section) delegates its own state computation to a state-only sibling function, so the two paths cannot diverge even when called independently"

key-files:
  created:
    - companion/test_health_signals.py
  modified:
    - companion/pages/health_page.py

key-decisions:
  - "health_state_from_signals() still calls each _x_section() builder for markup but discards that call's own returned state, using the signals snapshot's state instead — satisfying the plan's 'states/severity/anomalies copied from the signals, never recomputed' requirement while keeping every builder's pinned return shape (the _battery_section() 2-tuple included) unchanged."
  - "_device_state()/_pipeline_state()/_battery_state()/_disagreement_warn() reuse the exact inline logic the builders used to carry, including their own early-exit cases (_DB_UNAVAILABLE, empty rows, never-ran pipeline) — no behavioural change, only extraction."

requirements-completed: []  # EFF-04 spans 38-05/10/12; not marked complete here per phase coordination note.

# Metrics
duration: ~25min
completed: 2026-09-26
---

# Phase 38 Plan 05: Health severity split from markup Summary

**`health_signals()`/`health_state_from_signals()` split Health's severity computation from its HTML rendering, so `compute_health_state()` is now their composition and the nav-tab dot can never diverge from the page's own banner.**

## Performance

- **Duration:** ~25 min
- **Completed:** 2026-09-26T16:31:00Z
- **Tasks:** 1
- **Files modified:** 2 (1 created)

## Accomplishments
- `health_signals(state_dir, now)` computes every Health state (device, pipeline, battery, disagreement, coverage, source_fault, offbox), `severity` and `anomalies` from one `_read_health_inputs()` read, building no markup at all.
- `health_state_from_signals(signals)` builds every `*_html` value and `battery_caption` from that snapshot's raw inputs, copying (never recomputing) the snapshot's states/severity/anomalies — `compute_health_state()` is now exactly this composition, with its historical 18-key return contract unchanged.
- `safe_health_signals()` mirrors `safe_health_state()`'s fail-closed broad `except Exception` catch, so a lazy page context (a later plan) can read severity alone without risking a 500.
- Four new state-only siblings (`_device_state`, `_pipeline_state`, `_battery_state`, `_disagreement_warn`, plus the small `_device_resolved_state` helper) hold the exact state logic the four `_x_section()` markup builders used to compute inline; each builder now calls its own sibling for its state, so a caller of either path always sees the same verdict.

## Task Commits

Each task was committed atomically:

1. **Task 1: health_signals + health_state_from_signals, compute_health_state as their composition** - `68bd4a1` (feat)

**Plan metadata:** (this commit) - `docs(38-05): complete Health severity/markup split plan`

## Files Created/Modified
- `companion/pages/health_page.py` - Added `_device_resolved_state`, `_device_state`, `_pipeline_state`, `_battery_state`, `_disagreement_warn` state-only helpers; `_device_section`/`_pipeline_section`/`_battery_section`/`_corroboration_section` now call their sibling for their own state instead of computing it inline; added `health_signals`, `safe_health_signals`, `health_state_from_signals`; `compute_health_state` is now `health_state_from_signals(health_signals(state_dir, now))`.
- `companion/test_health_signals.py` - New: 8 parametrised severity/anomaly-equivalence scenarios (fresh ok, stale device, stale pipeline, source fault, battery drop, disagreement, unresolved registry, database unavailable), a no-markup guarantee test (every `_x_section`/`*_timestamp_only` helper monkeypatched to raise), a key-set + `health_state_from_signals(health_signals(...))` composition-equality test, a `safe_health_signals()` fail-closed test, and a next-wake-triple exposure test (14 tests total).

## Decisions Made
- `health_state_from_signals()` calls each `_x_section()` builder for markup but discards that call's own returned state in favour of the signals snapshot's value, so the "never recomputed" requirement holds exactly while every builder's pinned tuple return shape stays untouched (nothing in the existing test suite that unpacks `_battery_section()`'s 2-tuple, or calls the other builders directly, needed to change).
- The composition-equality test (`compute_health_state() == health_state_from_signals(health_signals(...))`) runs against an unseeded `tmp_path`, deliberately avoiding any battery reading: `_battery_section()` computes its own wall-clock `now` internally (a pre-existing, documented behaviour, unrelated to this plan), so a seeded battery reading's rendered relative-age text could in principle differ by a few milliseconds between two independent top-level calls. The empty-state path sidesteps that pre-existing flakiness source entirely while still proving the composition.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- 38-10 (lazy `page_context`) and 38-12 (the D-2 freshness token) can now call `safe_health_signals()`/`health_signals()` directly wherever they need severity, the anomaly list, or the next-wake triple without paying for markup — exactly the interface EFF-04 needs from this plan.
- `render()`'s markup path is untouched (still reads `ctx.get("health_state")` or falls back to `compute_health_state()`), so Home/Health render identically to before this plan.
- No blockers.

---
*Phase: 38-efficiency-companion-poll-cycle-storage*
*Completed: 2026-09-26*

## Self-Check: PASSED

- FOUND: companion/pages/health_page.py
- FOUND: companion/test_health_signals.py
- FOUND: .planning/phases/38-efficiency-companion-poll-cycle-storage/38-05-SUMMARY.md
- FOUND: 68bd4a1
