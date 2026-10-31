---
phase: 52-fleet-poll-cycle-zones-and-request-budget
plan: 04
subsystem: poll-budget
tags: [poll-cycle, zones, request-ledger, hold-peek]
requires: ["52-01", "52-02", "52-03"]
provides:
  - "server/poll_cycle.py: run_once(zone_fetch=, route_transport=, ledger_root=), peek_hold(state_dir, now=None)"
affects: [52-05]
key-files:
  modified:
    - server/poll_cycle.py
    - server/test_poll_cycle_steps.py
    - server/test_provider_rate.py
    - server/test_poll_loop.py
    - conftest.py
requirements-completed: [FLT-03, FLT-04]
completed: 2026-10-30
---

# Phase 52 Plan 04: Per-device cycle over a shared zone result Summary

`run_once` now selects from a shared `ZoneFetch` (same corroboration, per-device source fault), every standalone live fetch goes through the persisted `RequestLedger` in the state root, the `history.db` `provider_last_call:*` bookkeeping is gone, `peek_hold` gives the fleet loop a free read-only hold check, and adsbdb lookups can go through a shared transport.

## Commits
- 8b379d9: ZoneFetch selection, ledger-only standalone fetch, bookkeeping removed (Task 1)
- 07ccf91: `peek_hold` and `route_transport` (Task 2)

## What changed
- `detect_flight`: snapshot branch unchanged; otherwise `_select_from_zone` uses `ctx.zone_fetch` or `_fetch_standalone` (a `RequestLedger` under `ledger_root`, else `_ledger_root_for(state_dir)`: grandparent of `<root>/devices/<id>`, otherwise the directory itself), then `detect.select_from_provider_results`.
- Removed `_load_provider_last_calls`, the `provider_last_calls` field and `_record_history` parameter and its isolated meta write. `history_db.META_PROVIDER_LAST_CALL_PREFIX` is kept.
- `peek_hold`: read-only loads only, no mkdir, no lock, tolerant (`OSError/ValueError/KeyError/TypeError` -> None).
- `_enrich_current_flight` passes `transport=ctx.route_transport` to `enrich.resolve_route`.

## Verification
- `pytest server stub-server/test_phase47_freeze.py -n auto`: 1596 passed, 3 skipped (root ignores permission bits)
- ruff (whole repo), mypy (19 files), function-size gate (698 functions, none over 80) and comment-history guard clean

## Deviations from Plan
**1. [Rule 3 - Blocking] Existing tests adapted to removed names**
- `test_poll_loop.py`: tests that patched `detect.poll_current_aircraft` now pass a `ZoneFetch` (or patch `zone_fetch.fetch_zone` for the "never fetches on a hold" tests); the two tests of the deleted `_load_provider_last_calls` and of the provider meta write were removed. No pinned-panel or golden assertion was edited.
- `test_provider_rate.py` rewritten onto the ledger as planned.

**2. [Rule 3 - Blocking] `conftest.py` `fake_providers` fixture zeroes ledger spacing**
- Standalone cycles now spend the ledger's 1.1 s spacing; the fixture replaces the constructor default (bound at definition time) with 0 so live-path tests stay fast. Test-only change.

**3.** The test-count/step-test bullets of Task 1 (ZoneFetch branches, ledger-root derivation) and Task 2 live in `test_poll_cycle_steps.py`; the Task 2 commit only adds the peek and transport hook plus their tests.

## Known Stubs
None.

## Self-Check: PASSED
