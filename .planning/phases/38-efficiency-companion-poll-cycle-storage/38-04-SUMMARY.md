---
phase: 38-efficiency-companion-poll-cycle-storage
plan: 04
subsystem: backend
tags: [concurrent-futures, threading, adsb, rate-limiting, compliance]

# Dependency graph
requires:
  - phase: 38-01
    provides: "test-support/efficiency_probe.py: count_sleeps"
provides:
  - "server/plane/detect.py: poll_current_aircraft(..., last_call_at=None, clock=None, sleep=None) queries DEFAULT_PROVIDER_ORDER providers in parallel via ThreadPoolExecutor, spaced per-provider by the new _spaced_query() helper"
  - "COMPLIANCE.md's runtime-behaviour paragraph accurately describes parallel per-cycle requests and per-provider (not cross-provider) spacing, and adsb.lol's dynamic (not fixed 1 req/s) documented limit"
affects: [38-11]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "_spaced_query(name, center, radius_nm, timeout, last_call_at, lock, clock, sleep): reads/writes a shared {provider: epoch} map under a threading.Lock, but never sleeps while holding it, so one provider's wait never blocks another's read of its own entry"
    - "clock/sleep resolved inside the function body (clock or time.time), not as default parameter values, so a caller-supplied test double (or a future time.sleep patch) is honoured even though the wait happens inside a ThreadPoolExecutor worker thread"
    - "Futures submitted and collected in provider_names order (never as_completed) so completion-order nondeterminism from parallel execution never reaches diagnostics['queried']/['failed'] or the first-provider-wins selection on agreement"

key-files:
  created: []
  modified:
    - server/plane/detect.py
    - server/test_plane_detection.py
    - COMPLIANCE.md

key-decisions:
  - "last_call_at/clock/sleep are opt-in parameters, not required ones: passing none preserves today's single-poll behaviour (no persisted spacing, no sleep, no error), leaving cross-cycle persistence to the poll-loop caller in a later plan (38-11) - detect.py stays a leaf module with no history_db import"
  - "The provider-order test (test_default_poll_queries_adsbfi_then_adsblol) was rewritten to assert the called SET plus diagnostics['queried']'s provider order, rather than call order, since parallel execution makes physical answer order nondeterministic - six new tests cover concurrency, default no-sleep/local-dict behaviour, stable diagnostics order under a deliberately-delayed adsbfi, first-provider-wins-on-agreement, per-provider failure isolation, and injected-clock/sleep spacing"

patterns-established: []

requirements-completed: []

# Metrics
duration: ~20min
completed: 2026-09-26
---

# Phase 38 Plan 04: Parallel provider fan-out with per-provider spacing Summary

**Replaced detect.py's fixed 1.1s sleep between adsb.fi and adsb.lol with a ThreadPoolExecutor fan-out spaced per-provider (via new `last_call_at`/`clock`/`sleep` parameters), and corrected COMPLIANCE.md's runtime-behaviour paragraph to match.**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-09-26 (approx.)
- **Completed:** 2026-09-26T14:13:57Z
- **Tasks:** 2 completed
- **Files modified:** 3

## Accomplishments
- `server/plane/detect.py`'s `poll_current_aircraft()` now queries `DEFAULT_PROVIDER_ORDER` (and any explicit `providers=` list) through a `concurrent.futures.ThreadPoolExecutor`, one worker per provider, instead of a sequential loop with `time.sleep(MIN_SECONDS_BETWEEN_CALLS)` between different providers — the fixed sleep the research measured at ~90% of a no-network poll cycle.
- New private `_spaced_query()` helper enforces `MIN_SECONDS_BETWEEN_CALLS` per provider against a shared `last_call_at` map (read/write under a `threading.Lock`, but the actual `sleep()` call happens outside the lock so one provider's wait can never block another's), so a provider is never called sooner than 1.1s after its own previous call — including a future caller (the poll loop, `38-11`) persisting that map across cycles.
- Futures are submitted and collected in provider order (never `as_completed`), so `diagnostics["queried"]`, `diagnostics["failed"]`, and the first-provider-wins selection on agreement are all unaffected by which provider physically answers first — proven by a dedicated test with a deliberately-delayed adsbfi fake.
- `COMPLIANCE.md`'s "Poll cadence" bullet now describes the parallel request pattern, the per-provider (not cross-provider) spacing guarantee including across back-to-back cycles, and corrects adsb.lol's documented limit from "1 request/second" (inaccurate) to "dynamic."
- `server/test_plane_detection.py` gained 6 new/rewritten tests: concurrency (a `threading.Event` handshake a sequential loop could never pass), default local-dict/no-sleep behaviour, stable `diagnostics["queried"]` order under a deliberately-delayed adsbfi, first-provider-wins-on-agreement, per-provider `ConnectionError` isolation, and injected-clock/sleep spacing math.

## Task Commits

Each task was committed atomically, following the TDD RED/GREEN gate sequence for Task 1:

1. **Task 1 (RED): failing tests for parallel provider fan-out** - `1bf4a90` (test)
2. **Task 1 (GREEN): parallel provider fan-out with per-provider spacing** - `3963415` (feat)
3. **Task 2: correct COMPLIANCE.md's runtime-behaviour paragraph** - `65b9611` (docs)

_Note: this plan's `<output>` block is delivered by this SUMMARY.md itself; the plan-metadata commit below wraps STATE.md/ROADMAP.md updates._

## Files Created/Modified
- `server/plane/detect.py` - `_spaced_query()` helper; `poll_current_aircraft(..., last_call_at=None, clock=None, sleep=None)` fans out through a `ThreadPoolExecutor`; updated constant comments (`MIN_SECONDS_BETWEEN_CALLS` is now per-provider spacing, not cross-provider; the per-cycle provider budget is one deadline + one read timeout in parallel, not two calls in series)
- `server/test_plane_detection.py` - rewrote the provider-order test to assert the call set + `diagnostics["queried"]` order; added tests for concurrency, default no-sleep behaviour, stable diagnostics order under delayed answers, first-provider-wins-on-agreement, per-provider failure isolation, and injected-clock/sleep spacing
- `COMPLIANCE.md` - rewrote the "Poll cadence" bullet under "Runtime behaviour vs. the aggregators' constraints" (only that bullet changed)

## Decisions Made
- `last_call_at`/`clock`/`sleep` are additive, backward-compatible parameters: `server/poll_loop.py`'s existing call site (`detect.poll_current_aircraft(geofence_data, runway_id=tracked_runway_id, diagnostics=diagnostics)`) needed no change and still passes; persisting `last_call_at` across cycles via `history_db` meta is `38-11`'s job, not this plan's — `detect.py` never imports `history_db`.
- Kept the per-provider exception handling (`except (requests.RequestException, ValueError)`) exactly where it was, just around `future.result()` instead of the direct call, so an exception raised inside a worker thread is still caught in the calling thread with identical stderr output and `diagnostics["failed"]` behaviour.

## Deviations from Plan

None - plan executed as written. The `tdd="true"` task was executed with an explicit RED (failing-test) commit followed by a GREEN (implementation) commit, per the TDD execution flow, even though the plan's own task list did not spell out separate commits.

## Issues Encountered

None.

## User Setup Required

None.

## Next Phase Readiness

`poll_current_aircraft()` is ready for a caller to persist `last_call_at` across cycles; `EFF-06` stays open (spans this plan and `38-11`, per the phase's coordination notes) until `38-11` wires `history_db` meta storage into `server/poll_loop.py`'s call site. No blockers.

---
*Phase: 38-efficiency-companion-poll-cycle-storage*
*Completed: 2026-09-26*

## Self-Check: PASSED

All created/modified files found on disk; all three task commits (`1bf4a90`, `3963415`, `65b9611`) found in `git log`.
