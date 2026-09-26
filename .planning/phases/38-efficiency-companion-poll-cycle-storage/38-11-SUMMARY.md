---
phase: 38-efficiency-companion-poll-cycle-storage
plan: 11
subsystem: backend
tags: [sqlite, rate-limiting, adsb, poll-cycle, history-db]

# Dependency graph
requires:
  - phase: 38-04
    provides: "server/plane/detect.py's poll_current_aircraft(..., last_call_at=None, clock=None, sleep=None) - the caller-suppliable {provider: epoch} map this plan is the caller for"
  - phase: 38-09
    provides: "server/poll_loop.py's _persist_poll_state()/poll_state_baseline shape, which this plan must not perturb - the provider bookkeeping lives in history.db meta specifically so it never flips poll_state's own diff"
provides:
  - "server/history_db.py: META_PROVIDER_LAST_CALL_PREFIX - one meta key per provider (\"provider_last_call:<name>\"), holding that provider's last-call epoch as a float string"
  - "server/poll_loop.py: _load_provider_last_calls(state_dir, provider_names) - reads those keys through the cycle's own scoped connection before the live detection call, tolerant of a missing/unparsable value or a database failure"
  - "server/poll_loop.py: _record_history(..., provider_last_calls=None) - writes the updated map into the same write_batch as every other per-cycle signal, only on the live path"
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Cross-process rate-limit bookkeeping lives in history.db meta, never poll_state.json - the same per-cycle write_batch already used for META_LAST_PIPELINE_RUN etc. absorbs one more fixed-size row per provider without adding a second writer or a second transaction"
    - "The live/injected-snapshot fork decides once, near the top of _run_once_locked(), whether provider_last_calls stays None for the rest of the cycle - every _record_history() call downstream just passes that one variable through, rather than each of the three post-detection branches re-deriving 'is this a live cycle?' on its own"

key-files:
  created:
    - server/test_provider_rate.py
  modified:
    - server/history_db.py
    - server/poll_loop.py
    - server/test_poll_loop.py

key-decisions:
  - "provider_last_calls is decided once (None on the injected-snapshot path, the loaded-then-mutated dict on the live path) right where flight/diagnostics are resolved, then threaded unchanged through all three post-detection _record_history() call sites (flight-detected, held, nothing-detected) - so the hold branch's own early-return _record_history() call (which never reaches this code at all) and the injected-snapshot path both naturally pass nothing, with no extra conditional needed at each call site"
  - "_load_provider_last_calls() is a plain SELECT with no transaction, run through the cycle's already-open history_db.open_db(state_dir) - inside the cycle's one connection_scope, so it never adds a second SQLite connection or a second commit; verified directly by server/test_provider_rate.py's connection/commit-count test"
  - "Four pre-existing server/test_poll_loop.py fakes that replace detect.poll_current_aircraft with a fixed-signature stand-in (missing **kwargs) needed a last_call_at=None parameter added, since the live branch now always passes that keyword - a Rule 1 fix for a break this plan's own call-site change caused, verified by re-running the affected tests before and after"

patterns-established: []

requirements-completed: [EFF-06]

# Metrics
duration: ~35min
completed: 2026-09-26
---

# Phase 38 Plan 11: Cross-cycle provider rate-limit spacing via history.db meta Summary

**`server/poll_loop.py` now keeps each ADS-B provider's own `MIN_SECONDS_BETWEEN_CALLS` spacing across back-to-back poll cycles - including a timer cycle immediately followed by the companion's `/poll-now` - by persisting per-provider last-call epochs in `history.db`'s meta table, never `poll_state.json`.**

## Performance

- **Duration:** ~35 min
- **Started:** 2026-09-26 (approx.)
- **Completed:** 2026-09-26T20:45:00Z (approx.)
- **Tasks:** 1 completed (TDD: RED then GREEN)
- **Files modified:** 3 (1 created, 2 modified)

## Accomplishments
- `server/history_db.py` gained `META_PROVIDER_LAST_CALL_PREFIX = "provider_last_call:"`, alongside the module's other fixed-size `META_*` keys - one row per provider, updated in place, never appended.
- `server/poll_loop.py`'s new `_load_provider_last_calls(state_dir, provider_names)` reads those keys through the cycle's own scoped connection (a plain `SELECT` via `history_db.get_meta`, no transaction) before the live detection call. A missing or unparsable value for one provider is treated as "no previous call" for that provider alone (never an exception); a database/filesystem failure logs one line and returns an empty map, so the cycle still polls.
- The live branch of `_run_once_locked()` (the `snapshot is None` path) now builds this map from `detect.DEFAULT_PROVIDER_ORDER` and passes it as `last_call_at=` to `detect.poll_current_aircraft()`, which mutates it in place (per plan 04's own contract) as each provider is actually queried.
- `_record_history()` gained a `provider_last_calls=None` keyword: when given a non-empty dict, it writes one `set_meta()` call per provider inside the exact same `history_db.write_batch(conn)` every other per-cycle signal already uses - no new connection, no new transaction. Every one of the three post-detection `_record_history()` call sites (flight-detected, held-with-a-flight-on-screen, nothing-ever-detected) now passes the cycle's `provider_last_calls` variable through; the hold branch's own early-return call and the injected-snapshot path both pass nothing, since `provider_last_calls` stays `None` on both (the hold branch never reaches this code at all; the injected-snapshot branch sets it to `None` explicitly and never calls `_load_provider_last_calls()`).
- New `server/test_provider_rate.py` (7 tests): back-to-back spacing across two live cycles (using real recorded `time.time()` timestamps from `efficiency_probe.fake_provider_latency()`'s own call log, never a wall-clock assertion on the test itself); cross-cycle persistence in meta as parsable float strings, honoured by a second, independent `run_once()` call with no in-process structure carried over; a cycle with no prior meta sleeping zero times while still opening exactly one connection and committing exactly once; an unchanged live repeat still writing `poll_state.json` zero times; an unparsable stored value causing no exception and no sleep (proven against a restored 1.1s default spacing, so the test can't pass by the spacing already being zeroed); a hold cycle and an injected-snapshot cycle leaving the provider meta keys byte-for-byte unchanged; and a `history_db.set_meta()` failure still returning the cycle's normal result dict with the provider map present.

## Task Commits

Task 1 ran RED then GREEN, per its TDD gate:

1. **Task 1: Persist per-provider last-call times in meta and pass them to detection**
   - `4669b77` (test, RED): `server/test_provider_rate.py`, verified failing (4 of 7 tests genuinely fail against the pre-change `poll_loop.py`/`history_db.py` via `git stash push` on those two files before committing the implementation)
   - `38c3131` (feat, GREEN): `META_PROVIDER_LAST_CALL_PREFIX`, `_load_provider_last_calls()`, the live branch's `last_call_at=` wiring, `_record_history()`'s `provider_last_calls=` keyword and its three call-site updates, plus the `server/test_poll_loop.py` fake-signature fix

## Files Created/Modified
- `server/test_provider_rate.py` - 7 behaviour tests: back-to-back spacing, cross-cycle meta persistence, no-prior-meta sleep/connection/commit counts, unchanged-repeat poll_state write count, a corrupt stored value, hold/injected-snapshot meta isolation, a contained history-write failure
- `server/history_db.py` - `META_PROVIDER_LAST_CALL_PREFIX` constant
- `server/poll_loop.py` - `_load_provider_last_calls()`; the live branch's `provider_last_calls`/`last_call_at=` wiring; `_record_history()`'s `provider_last_calls=` keyword, its write inside the existing batch, and its three call-site updates
- `server/test_poll_loop.py` - four pre-existing `poll_current_aircraft()` fakes with a fixed keyword signature gained `last_call_at=None`, so they still accept the keyword the live branch now always passes

## Decisions Made
- Confirmed the RED gate by reverting `server/history_db.py` and `server/poll_loop.py` alone (`git stash push -- server/history_db.py server/poll_loop.py`, keeping the new test file in place) and re-running `server/test_provider_rate.py` before ever committing the implementation - 4 of the 7 new tests genuinely failed against the unmodified code (an `AttributeError` on the not-yet-added `META_PROVIDER_LAST_CALL_PREFIX`, and no spacing enforced across two live cycles), proving those tests exercise the change rather than passing by construction.
- `provider_last_calls` is resolved exactly once, right where `flight`/`diagnostics` are resolved (the live-vs-injected-snapshot fork), rather than re-derived at each of the three downstream `_record_history()` call sites - keeping "is this a live cycle?" a single decision point instead of three.
- Kept the four `server/test_poll_loop.py` fakes' fix minimal (`last_call_at=None` added to each fixed signature) rather than switching them to `**kwargs`, matching the exact keyword the real function now always receives on the live path and leaving every other pre-existing test in that file untouched.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Four pre-existing `test_poll_loop.py` fakes broke against the new `last_call_at=` keyword**
- **Found during:** Task 1, first full verification run (`server/test_poll_loop.py`).
- **Issue:** `test_non_default_runway_reaches_poll_current_aircraft`, `test_all_failed_diagnostics_yields_true_fault_flag`, `test_successful_query_no_selection_yields_false_fault_flag`, and `test_fault_transition_gated_not_value` each replace `detect.poll_current_aircraft` with a fixed-signature fake (`def _fake_poll(geofence, timeout=10.0, providers=None, runway_id=..., diagnostics=None)`, no `**kwargs`). The live branch's new, unconditional `last_call_at=provider_last_calls` keyword argument raised `TypeError: got an unexpected keyword argument 'last_call_at'` against all four.
- **Fix:** Added `last_call_at=None` to each of the four fake signatures - the minimal change matching the real function's new keyword; every other pre-existing behaviour in those tests is untouched.
- **Files modified:** `server/test_poll_loop.py`.
- **Commit:** `38c3131` (part of the Task 1 GREEN commit).

---

**Total deviations:** 1 auto-fixed (1 bug).
**Impact on plan:** Test-compatibility fix only; no production behaviour changed beyond what the plan specified.

## Issues Encountered

None beyond the item above, resolved before the GREEN commit.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

EFF-06 is now fully closed (parallel provider fan-out from `38-04`, plus this plan's cross-cycle spacing persistence). This was Phase 38's last EFF item requiring new production code; `38-12`/`38-13` (per the phase's own plan numbering) are the closing verification/gap-closure plans. No blockers.

---
*Phase: 38-efficiency-companion-poll-cycle-storage*
*Completed: 2026-09-26*

## Self-Check: PASSED

All created/modified files (`server/test_provider_rate.py`, `server/history_db.py`, `server/poll_loop.py`, `server/test_poll_loop.py`) and both task commits (`4669b77`, `38c3131`) verified present in `git log` and on disk.
