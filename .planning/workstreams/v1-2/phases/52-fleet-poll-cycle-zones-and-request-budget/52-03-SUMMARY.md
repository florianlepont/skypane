---
phase: 52-fleet-poll-cycle-zones-and-request-budget
plan: 03
subsystem: poll-budget
tags: [adsbdb, cache, flock, fleet]
requires: []
provides:
  - "server/plane/shared_route_cache.py: SharedRouteTransport, SHARED_CACHE_FILENAME"
affects: [52-04]
tech-stack:
  added: []
  patterns: ["leaf flock never held across network I/O", "cache fault falls back to a direct lookup"]
key-files:
  created:
    - server/plane/shared_route_cache.py
    - server/test_shared_route_cache.py
  modified: []
key-decisions:
  - "The cached body is the parsed JSON value the inner transport returns, stored as JSON, so no encoding layer is needed"
requirements-completed: [FLT-03]
duration: short
completed: 2026-10-30
---

# Phase 52 Plan 03: Shared adsbdb route cache Summary

`SharedRouteTransport(root, inner=None, clock=None)` is a drop-in `transport=` for `enrich.resolve_route`. It shares 404 and 2xx adsbdb answers across devices and processes through `adsbdb_shared_cache.json` in the state root (mode 0600, 300 entries max, 256 KiB body cap, enrich TTLs reused), with the lookup outside the lock. `enrich.py` is unchanged.

## Commits
- 62e1ddd: shared route cache and tests (Task 1)

## Verification
- `pytest server/test_shared_route_cache.py server/test_enrich.py stub-server/test_phase47_freeze.py`: 126 passed
- ruff, mypy (new module), function-size gate and comment-history guard clean

## Deviations from Plan
None. The adsbdb body is already parsed JSON (or None) at the transport seam, so it is stored as a JSON value rather than base64.

## Known Stubs
None.

## Self-Check: PASSED
