---
phase: 39-server-architecture-run-once-split-state-store-shared-module
plan: 11
subsystem: server
tags: [poll-cycle, run-once-split, cycle-context, dataclass, mypy-pure-core]

requires:
  - phase: 39-server-architecture-run-once-split-state-store-shared-module
    provides: "39-10: server/poll_cycle.py as a pure library module (run_once, PollBusy, poll_cycle_lock, now_s, the pacing helpers, notify hooks, history recording, panel write and gallery), with a guarded import boundary against poll_loop.py"
provides:
  - "server/poll_cycle.py: a CycleContext(slots=True) dataclass and the poll cycle read as named steps over it - load_cycle_context, decide_hold, run_hold_cycle, detect_flight, load_display_slots, update_battery_low, advance_display_queue, render_and_publish (dispatching to _render_promoted/_render_held/_render_empty, itself delegating to _enrich_current_flight/_resolve_theme), record, persist, log_cycle, cycle_result"
  - "publish_canvas(ctx, canvas): the one render -> pack -> write -> gallery sequence, replacing all four former inline publish copies"
  - "Every function in server/poll_cycle.py is <=57 code lines (was 338 for the single _run_once_locked, now deleted); max cyclomatic complexity in the module is unchanged at 12 (_record_history, an untouched pre-existing function)"
  - "decide_hold, advance_is_due, normalise_pending, enqueue_pending, pop_fresh_pending and CycleContext are type-annotated (the typed pure core of the cycle)"
  - "server/test_poll_cycle_steps.py: unit tests for decide_hold's precedence and publish_canvas's write/gallery contract, plus two step-ordering spy tests (the live path's named call order; the hold path never detects and publishes at most once)"
affects: [39-13]

tech-stack:
  added: []
  patterns:
    - "CycleContext(slots=True) dataclass as the cycle's single mutable state carrier, grouped into inputs/config/state/detection/slots/pacing/outcome sections mirroring the former locals' own groupings - each step function's docstring says which ctx fields it reads and which it writes, in lieu of a type-checked read/write contract (deferred to 39-13's mypy pass)."
    - "One shared publish_canvas(ctx, canvas) -> bool replaces N inline pack/write/gallery copies across branches; every branch calls it at most once and reads the result off ctx.panel_changed rather than threading a local bool through to the final log/result-dict construction."
    - "A shared step (update_battery_low) is called identically from both the hold branch and the live path, once the two branches' battery-low blocks were confirmed byte-identical - proven by diff, not assumed, before extracting."
    - "Step-ordering tests spy by wrapping the real function (monkeypatch.setattr with a wrapper that appends to an order list then calls straight through), never by replacing it with a stub - behaviour keeps running for real while the call sequence is asserted."

key-files:
  created:
    - server/test_poll_cycle_steps.py
  modified:
    - server/poll_cycle.py
    - server/state_store.py
    - server/test_poll_efficiency.py
    - server/test_poll_state_writes.py

key-decisions:
  - "The hold path's battery-low block and the live path's own were confirmed byte-identical before extracting update_battery_low() as a function shared by both (Task 2), rather than a hold-only inline copy - Task 1 kept the hold branch's copy inline (per the task's own 'verbatim' instruction) precisely so Task 2's refactor-to-shared-step change was isolated to its own commit."
  - "The hold-path and live-path poll_state persist orders were kept exactly as they were: hold = record -> silence notify -> one persist_poll_state_if_changed (inside run_hold_cycle); live = publish -> record -> persist_poll_state_if_changed -> silence notify -> persist_poll_state_if_changed-if-changed (inside persist()). These are two different functions with two different bodies - nothing was unified. Pinned by the new hold-path spy test (publishes at most once) plus the pre-existing test_poll_state_writes.py/efficiency-probe write-count suite, all of which stayed green unchanged."
  - "_run_once_locked was deleted rather than kept as a thin wrapper: grepped first for any test that monkeypatches or reads it as an attribute (server/test_poll_efficiency.py and server/test_poll_state_writes.py only mention it in prose module docstrings, and server/state_store.py's own module docstring did too) - none reach it as code, so all three stale prose mentions were updated in place instead of leaving a dead re-export."
  - "decide_hold, advance_is_due, normalise_pending, enqueue_pending, pop_fresh_pending and CycleContext were annotated as part of this plan's own must-have truth, ahead of 39-13's mypy-in-CI wiring for this file - confirmed with a local, ad hoc `mypy --disallow-untyped-defs --check-untyped-defs` run (not yet added to pyproject's typed-files list, which is 39-13's scope) that the five annotated signatures introduce zero errors."

requirements-completed: []

duration: ~50min
completed: 2026-09-27
---

# Phase 39 Plan 11: run_once split into named steps over CycleContext Summary

**`_run_once_locked` (338 code lines, McCabe CC 53, the phase's last ARC-01 size-gate offender) is gone: the poll cycle now reads as `load_cycle_context` / `decide_hold` / `run_hold_cycle` or eight live steps (`detect_flight`, `load_display_slots`, `update_battery_low`, `advance_display_queue`, `render_and_publish`, `record`, `persist`, `log_cycle`) over one `CycleContext` dataclass, with a single shared `publish_canvas()` replacing four former inline pack/write/gallery copies and both persist orders preserved exactly.**

## Performance

- **Duration:** ~50 min
- **Tasks:** 2/2 completed (plus one small addendum commit annotating the five pure helpers the plan's own must-have truths call out)
- **Files modified:** 5 (1 created: server/test_poll_cycle_steps.py; 4 modified)

## Accomplishments

- **Task 1 (`a8a7836`, feat):** Added `CycleContext` (`@dataclass(slots=True)`, `from __future__ import annotations`), `load_cycle_context()` (makedirs, the manual-resolution/colour-rule registry loads, the calendar refresh, and the device_cfg/poll_state/battery_state read - verbatim from the former opening segment), `decide_hold()` (pure `battery_empty > display_off > quiet_hours` precedence), `publish_canvas()` (the one render -> pack -> write -> gallery sequence), and `run_hold_cycle()` (the hold branch, kept verbatim over `ctx` per the task's own instruction, calling `publish_canvas`, `_record_history`, the silence notify, and one `persist_poll_state_if_changed`). `_run_once_locked` now dispatches through these and binds locals from `ctx` for the still-untouched live path; all four former publish copies (hold + 3 live branches) now call `publish_canvas(ctx, ...)` - confirmed by grep (`_save_to_gallery(` appears exactly twice: its own definition and the one call inside `publish_canvas`). Added `server/test_poll_cycle_steps.py` with `decide_hold`'s five precedence cases and `publish_canvas`'s first-write/unchanged-repeat/later-changed gallery-entry contract.
- **Task 2 (`dc54090`, feat):** Extracted the live path's remaining body into `detect_flight`, `load_display_slots`, `update_battery_low` (now shared with `run_hold_cycle`, which had carried its own byte-identical copy since Task 1 - confirmed identical by diff before refactoring), `advance_display_queue`, `render_and_publish` (dispatching to `_render_promoted`/`_render_held`/`_render_empty`; `_render_promoted` further delegates enrichment to `_enrich_current_flight` and theme resolution to `_resolve_theme` to stay well under the line cap), `record`, `persist`, `log_cycle` and `cycle_result`. `run_once()` now calls the eight live steps in order (or `run_hold_cycle` on a decided hold) inside its existing lock + `history_db.connection_scope`; `_run_once_locked` is deleted. Added the two step-ordering spy tests: the live path's exact 8-step call order (wrapping the real functions so behaviour still runs), and the hold path's restricted call surface (never calls `detect_flight`; publishes at most once across an entry+repeat pair). Updated three now-stale `_run_once_locked` prose mentions in comments (`server/state_store.py`, `server/test_poll_efficiency.py`, `server/test_poll_state_writes.py`) - grepped first to confirm no test reaches the deleted name as an attribute or monkeypatch target.
- **Addendum (`67619c2`, feat):** Annotated `decide_hold`, `advance_is_due`, `normalise_pending`, `enqueue_pending` and `pop_fresh_pending` (`CycleContext` was already annotated via its dataclass field declarations) - the plan's own must-have truth calls these out by name as "the typed pure core of the cycle". Confirmed zero new errors with a local `mypy --disallow-untyped-defs --check-untyped-defs` pass over the file (not yet in pyproject's typed-files list or CI - that wiring is 39-13's scope).

## Task Commits

1. **Task 1: CycleContext, load_cycle_context, decide_hold, publish_canvas and the hold path** - `a8a7836` (feat)
2. **Task 2: live-path steps; _run_once_locked removed; every function within 80 code lines** - `dc54090` (feat)
3. **Addendum: annotate the plan's five pure-core helper functions** - `67619c2` (feat)

## Function size and complexity (server/poll_cycle.py, after)

Every function in the module is now well under the 80-code-line gate; the largest is `run_hold_cycle` at 57 (the hold branch is inherently larger than any single live step because it must resolve battery-low, decide whether to repaint, record, notify and persist all in one early-return path). Max cyclomatic complexity in the module is 12, in `_record_history` - a pre-existing function this plan did not touch.

| Code lines | CC (radon) | Function |
|---|---|---|
| 57 | B (6) | `run_hold_cycle` |
| 37 | B (10) | `advance_display_queue` |
| 37 | A (2) | `_render_promoted` |
| 29 | A (2) | `load_cycle_context` |
| 29 | B (9) | `log_cycle` |
| 28 | B (7) | `_render_held` |
| 26 | A (4) | `_enrich_current_flight` |
| 23 | A (5) | `load_display_slots` |
| 23 | A (3) | `record` |
| 19 | A (2) | `detect_flight` |
| 17 | A (3) | `run_once` |
| 11 | A (1) | `_render_empty` |
| 11 | A (2) | `persist` |
| 11 | A (1) | `cycle_result` |
| 8 | A (4) | `decide_hold` |
| 8 | A (2) | `update_battery_low` |
| 7 | A (2) | `publish_canvas` |
| 7 | A (1) | `_resolve_theme` |
| 7 | A (4) | `render_and_publish` |
| 1 | A (1) | `CycleContext` (class) |

For comparison: before this plan, `_run_once_locked` alone was 338 code lines at McCabe CC 53 (radon grade F), the last ARC-01 size-gate offender in `server/` (per `39-ARC-BASELINE.md` and `39-10-SUMMARY.md`'s own handoff note). Full `scripts/check_function_size.py check --max 80 server/poll_cycle.py` and `uv run --no-project --with radon==6.0.1 radon cc -s server/poll_cycle.py` outputs (45 functions total) are in this plan's execution transcript; every one of the 45 is grade A or B, none above grade C.

## Files Created/Modified

- `server/poll_cycle.py` - `CycleContext` dataclass; `load_cycle_context`, `decide_hold`, `publish_canvas`, `run_hold_cycle`, `update_battery_low`, `detect_flight`, `load_display_slots`, `advance_display_queue`, `_enrich_current_flight`, `_resolve_theme`, `_render_promoted`, `_render_held`, `_render_empty`, `render_and_publish`, `record`, `persist`, `log_cycle`, `cycle_result`; `run_once` now calls the named steps directly; `_run_once_locked` deleted
- `server/test_poll_cycle_steps.py` - new: `decide_hold` precedence table, `publish_canvas` write/gallery contract, live-path step-order spy, hold-path restricted-call-surface spy
- `server/state_store.py`, `server/test_poll_efficiency.py`, `server/test_poll_state_writes.py` - stale `_run_once_locked` prose mentions (module docstrings/comments only) updated to name the functions that now own that behaviour

## Decisions Made

See `key-decisions` in the frontmatter above: `update_battery_low` shared only after confirming byte-identical bodies; the hold/live persist orders were kept as two distinct function bodies, never unified; `_run_once_locked` deleted (not kept as a wrapper) after grepping for any test coupling; the five pure-core helpers annotated per the plan's own must-have truth, ahead of 39-13's CI wiring.

## Deviations from Plan

**None** - plan executed as written, with one addendum: the plan's frontmatter `must_haves.truths` explicitly names `decide_hold`, `advance_is_due`, `normalise_pending`, `enqueue_pending`, `pop_fresh_pending` and `CycleContext` as needing type annotations "(the typed pure core of the cycle)". Task 2's own action text focused on the size-gate split and did not call out annotating the three pacing helpers this plan did not otherwise touch, so this was completed as a small, separately-committed addendum after Task 2 rather than folded into either task's commit - not a Rule 1-4 deviation (nothing was broken or missing for correctness/security), just a must-have the task text under-specified relative to the plan's own truths list.

## Issues Encountered

None. The riskiest step named in the plan and research (preserving the hold-path vs. live-path persist-order difference exactly) was mitigated by keeping `run_hold_cycle` and `persist` as two entirely separate function bodies with their own docstrings cross-referencing the other's existence and the "never unify" rule, plus the new hold-path spy test and the pre-existing `test_poll_state_writes.py`/efficiency-probe write-count suite, all of which passed unchanged throughout.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

`server/poll_cycle.py` now satisfies ARC-01's structural and size criteria in full: named steps over one `CycleContext`, one publish path, no function over 80 code lines, and the typed pure core annotated. 39-13 (phase close) can now: make the function-size gate blocking in CI; add `server/poll_cycle.py`'s pure helpers and `CycleContext` to the mypy typed-files list and confirm it stays green; and write the baseline "After" section into `39-ARC-BASELINE.md` using this plan's own before/after numbers (338 code lines / CC 53 -> 45 functions, largest 57 code lines, max CC 12). No blockers.

---
*Phase: 39-server-architecture-run-once-split-state-store-shared-module*
*Completed: 2026-09-27*

## Self-Check: PASSED

- FOUND: server/poll_cycle.py
- FOUND: server/test_poll_cycle_steps.py
- FOUND: server/state_store.py
- FOUND: server/test_poll_efficiency.py
- FOUND: server/test_poll_state_writes.py
- FOUND: .planning/phases/39-server-architecture-run-once-split-state-store-shared-module/39-11-SUMMARY.md
- FOUND commit: a8a7836 (Task 1)
- FOUND commit: dc54090 (Task 2)
- FOUND commit: 67619c2 (Addendum)
