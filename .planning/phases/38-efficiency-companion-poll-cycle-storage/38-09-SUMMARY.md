---
phase: 38-efficiency-companion-poll-cycle-storage
plan: 09
subsystem: backend
tags: [json, atomic-io, poll-cycle, storage-efficiency]

# Dependency graph
requires:
  - phase: 38-07
    provides: "server/poll_loop.py's run_once() scope shape and _run_once_locked()'s current save-site layout - this plan changes only when/how those sites persist, not the connection/transaction wiring 38-07 added"
provides:
  - "server/poll_loop.py: _serialize_poll_state(state) - compact JSON encoding (separators=(\",\", \":\")), used by both save_poll_state() and _persist_poll_state()"
  - "server/poll_loop.py: _persist_poll_state(state_dir, poll_state, baseline) - the cycle's single end-of-cycle save, called only from _run_once_locked()'s two exits (the hold-branch return, the shared tail), writing only when the current serialisation differs from the baseline snapshot taken right after load_poll_state()"
  - "server/poll_loop.py: save_poll_state() stays the always-write public seed seam every other test module uses, now compact instead of indent=1"
  - "server/test_poll_state_writes.py: 8 tests proving at-most-one write per cycle, zero writes on an unchanged repeat, write ordering against panel.bin, a persisted notification mutation, compact round-tripping format, and old-format migration"
affects: [39]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "A load-time string baseline (_serialize_poll_state(poll_state) taken immediately after load_poll_state(), before any branch mutates the dict) is the cheapest way to answer \"did anything change this cycle?\" without a deep-diff or a second in-memory copy of the dict - the mutated dict can't serve as its own baseline, but a frozen string snapshot of its pre-mutation form can."
    - "Every branch that used to save mid-cycle now only ever mutates poll_state in place; the actual write is deferred to one of exactly two call sites (the hold-branch's own early return, and the shared tail after the three main branches), each guarded by the same diff-against-baseline check inside _persist_poll_state()."

key-files:
  created:
    - server/test_poll_state_writes.py
  modified:
    - server/poll_loop.py

key-decisions:
  - "Kept save_poll_state(state_dir, state) as an unconditional public seam (per the plan's own interfaces block) rather than folding it into _persist_poll_state() - roughly 15 other test call sites across the suite use it to seed a poll_state.json directly, and none of them needed to change."
  - "The migration test seeds an indent=1 file missing the two hysteresis-latch keys (battery_critical_active, battery_low_active) rather than a value that would flip regardless of format, since _persist_poll_state()'s diff compares the freshly re-serialised dict against a compact baseline taken at load time - it never compares against the raw on-disk bytes. A real production poll_state.json predating this deploy will, in practice, write once on its next cycle for the same reason: some field it's missing gets added."

requirements-completed: [EFF-05]

# Metrics
duration: ~40min
completed: 2026-09-26
---

# Phase 38 Plan 09: Write-once, only-if-changed, compact poll_state Summary

**`server/poll_loop.py` now saves `poll_state.json` at most once per cycle, only when its contents actually changed since load, in compact JSON instead of `indent=1`.**

## Performance

- **Duration:** ~40 min
- **Started:** 2026-09-26T18:20Z (approx.)
- **Completed:** 2026-09-26T19:05Z (approx.)
- **Tasks:** 1 completed (TDD: RED then GREEN)
- **Files modified:** 2 (1 created, 1 modified)

## Accomplishments
- New `_serialize_poll_state(state)` returns `json.dumps(state, separators=(",", ":"))`. `save_poll_state()` now uses it (still an unconditional write - the public seed seam ~15 other test modules rely on to seed a `poll_state.json` directly, untouched otherwise).
- New `_persist_poll_state(state_dir, poll_state, baseline)`: re-serialises `poll_state` and writes through the same atomic path only when that serialisation differs from `baseline`. `_run_once_locked()` now captures `poll_state_baseline = _serialize_poll_state(poll_state)` immediately after `load_poll_state()`, before any branch mutates the dict in place.
- Every one of the five mid-branch/unconditional `save_poll_state()` call sites the research (`38-RESEARCH.md` §EFF-05) identified is gone: the hold branch's conditional entry save and its own unconditional tail save; the flight-detected branch's unconditional save; the held-flight and empty branches' conditional saves; the shared final unconditional save. In their place, exactly two `_persist_poll_state()` calls remain - the hold branch's own early return (after its own `_notify_silence_transition()` call), and the shared tail after the three main branches (after the shared `_notify_silence_transition()` call) - so the file is written at most once per cycle, and always strictly after `panel.bin` (the save moved later than it used to be, never earlier).
- Removed the now-dead `battery_critical_changed` local (it existed solely to feed the hold branch's old conditional-save guard) and reworded every comment that used to justify a specific mid-branch save into a comment pointing at the shared end-of-cycle persist instead.
- New `server/test_poll_state_writes.py` (8 tests): at most one write across the research's seven poll-cycle branches; zero writes, with byte-for-byte and mtime-identical files, on both the empty-sky repeat and the held-hold repeat; exactly one write on a flight-detected cycle, proven (via a wrapped `atomic_io.atomic_write`) to land strictly after `panel.bin`; exactly one write for a frame-silent notification transition on an otherwise unchanged cycle, with the persisted `notifications["last_silent_sent"]` mutation verified on disk afterward; the written file compact (`"\n"` and `": "` both absent), round-tripping through `json.loads` back to the in-memory state, and never longer than the equivalent `indent=1` encoding; `save_poll_state()` itself still writing unconditionally given the identical state twice in a row; and a pre-existing `indent=1` file rewritten once, compact, on the first cycle that actually adds a value, then a following unchanged repeat writing zero.

## Task Commits

Task 1 ran RED then GREEN, per its TDD gate:

1. **Task 1: Write-once, only-if-changed, compact poll_state**
   - `9299255` (test, RED): `server/test_poll_state_writes.py`, verified failing (7 of 8 tests genuinely fail) against the pre-change `server/poll_loop.py` via `git stash push -- server/poll_loop.py` before committing the implementation
   - `5079f70` (feat, GREEN): `_serialize_poll_state`/`_persist_poll_state`, both `_run_once_locked()` exits switched to it, every mid-branch save site removed

**Plan metadata:** commit pending (this SUMMARY + STATE.md/ROADMAP.md/REQUIREMENTS.md)

## Files Created/Modified
- `server/test_poll_state_writes.py` - 8 behaviour tests: per-branch write counts, unchanged-repeat byte/mtime stability, panel-then-poll_state ordering, a persisted notification mutation, compact round-tripping, `save_poll_state()`'s unconditional write, old-format migration
- `server/poll_loop.py` - `_serialize_poll_state`, `_persist_poll_state`, compact `save_poll_state`, every mid-branch/unconditional save site in `_run_once_locked()` collapsed to the two `_persist_poll_state()` calls at its exits

## Decisions Made
- Confirmed the fix by literally reverting `server/poll_loop.py` (via `git stash push -- server/poll_loop.py`, keeping the new test file staged) and re-running `server/test_poll_state_writes.py` before ever committing the implementation - 7 of the 8 new tests genuinely failed against the unmodified code (multiple writes per cycle, `indent=1` output, no byte/mtime stability on a repeat, wrong migration behaviour); only the silence-transition test happened to pass unchanged, since that specific scenario already wrote exactly once under the old code too. This proves the other 7 tests exercise the change, not just pass by construction.
- `save_poll_state()` stays a distinct, always-write function rather than folding into `_persist_poll_state()` - the plan's own interfaces block calls this out explicitly, and roughly 15 other test call sites across the suite (`test_poll_loop.py`, `test_pipeline_e2e.py`, etc.) use it to seed a `poll_state.json` directly; none needed to change.
- The migration test seeds an `indent=1` file that is missing two hysteresis-latch keys (`battery_critical_active`, `battery_low_active`) rather than relying on the raw on-disk bytes' format to trigger a rewrite - `_persist_poll_state()`'s diff only ever compares the freshly re-serialised dict against a baseline taken at load time, never against the file's actual on-disk bytes, so a value-for-value-identical old file (however it was formatted) would legitimately write zero times on its first post-deploy cycle. In practice a real pre-existing `poll_state.json` will almost always be missing at least one newly-tracked field and so will write once regardless.

## Deviations from Plan

None - plan executed exactly as written. The interfaces block's save-site inventory (hold branch's conditional entry save + unconditional tail save; flight-detected branch's unconditional save; held-flight branch's conditional save; empty branch's conditional save; final unconditional save) matched the code exactly, and every one was replaced as specified.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

EFF-05 is now fully closed. `_persist_poll_state()`'s single end-of-cycle save is a narrow, self-contained change - Phase 39's planned `state_store` module (ARC-02) can wrap or relocate this same write-once-only-if-changed logic without needing to touch `_run_once_locked()`'s branch structure again. No blockers. Phase 38 continues with 38-10 through 38-13 (EFF-04, EFF-06, and the closing verification/gap-closure plans).

---
*Phase: 38-efficiency-companion-poll-cycle-storage*
*Completed: 2026-09-26*

## Self-Check: PASSED

All created/modified files (`server/test_poll_state_writes.py`, `server/poll_loop.py`) and both task commits (`9299255`, `5079f70`) verified present.
