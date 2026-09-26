---
phase: 38-efficiency-companion-poll-cycle-storage
plan: 01
subsystem: testing
tags: [pytest, sqlite, http-caching, poll-loop, adsb, stdlib]

# Dependency graph
requires: []
provides:
  - "test-support/efficiency_probe.py: count_db, count_sleeps, count_poll_state_writes, fake_provider_latency, seed_history, route_weight, cycle_probe"
  - "scripts/measure_efficiency.py: offline CLI printing the phase's markdown measurement tables"
  - "38-EFF-BASELINE.md: committed Before section for every EFF-01..EFF-06 metric"
affects: [38-02, 38-03, 38-04, 38-05, 38-06, 38-07, 38-08, 38-09, 38-10, 38-11, 38-12, 38-13]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "_patched(obj, name, value): a self-restoring attribute-swap context manager, the one seam every counter/fake in efficiency_probe.py is built on"
    - "Counters wrap production seams (sqlite3.connect, history_db.init_schema, atomic_io.atomic_write, detect.query_provider, enrich.default_transport) rather than adding new instrumentation hooks to production code"

key-files:
  created:
    - test-support/efficiency_probe.py
    - test-support/test_efficiency_probe.py
    - scripts/measure_efficiency.py
    - .planning/phases/38-efficiency-companion-poll-cycle-storage/38-EFF-BASELINE.md
  modified: []

key-decisions:
  - "Poll-cycle branches reuse one state_dir sequentially (empty sky first/repeat, flight detected, same flight again, nothing new, then two display_off hold branches) so each branch's poll_state.json is exactly what the prior branch persisted, matching the research's seven-branch definition without extra bookkeeping"
  - "measure_efficiency.py globally replaces detect.query_provider and enrich.default_transport with offline fakes for its whole run (not just during cycle_probe), and installs the DNS resolver guard directly since the script runs outside pytest-socket"
  - "38-EFF-BASELINE.md's Before section captures only the script's own markdown output (from '## Measurement' onward), not companion/app.py's per-request 'GET /path' access-log lines it also prints to stdout"

patterns-established:
  - "A test-support instrument used by both pytest and a standalone CLI script must have no pytest import at module scope, restore every patch itself, and accept latency/records as plain arguments - no monkeypatch fixture dependency"

requirements-completed: [EFF-01, EFF-02, EFF-03, EFF-04, EFF-05, EFF-06]

# Metrics
duration: 20min
completed: 2026-09-26
---

# Phase 38 Plan 01: Efficiency instruments and Before baseline Summary

**Built the shared SQLite/sleep/poll-state/HTTP-weight probe module, a stdlib CLI that prints it as markdown, and committed the unmodified tree's Before numbers for every EFF-01..EFF-06 metric ahead of any production change.**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-09-26T13:00Z (approx.)
- **Completed:** 2026-09-26T13:09:40Z
- **Tasks:** 2 completed
- **Files modified:** 4 (all created, 0 modified)

## Accomplishments
- `test-support/efficiency_probe.py`: one self-restoring `_patched()` seam behind `count_db`, `count_sleeps`, `count_poll_state_writes`, `fake_provider_latency`, `seed_history`, `route_weight` and `cycle_probe` - no production code touched, every counter wraps an existing attribute.
- `test-support/test_efficiency_probe.py`: 9 tests proving the probe mechanics (connection/schema/commit counting, cross-thread counting, patch restoration, sleep recording scoped to its own `with` block, poll_state-only write filtering, provider-latency faking and logging, route byte/time weight over a seeded `InProcessAppServer`, and `cycle_probe`'s returned key set) - never asserting today's inefficiency numbers, so they stay green through every later plan.
- `scripts/measure_efficiency.py`: an offline, stdlib-only CLI (network-guarded via `skypane_test_support.guarded_resolvers()`, offline `enrich.default_transport`/`detect.query_provider` fakes) that prints five markdown tables (Routes, First-load weight, Static revalidation, Freshness tick, Poll cycle) plus a header and an extra empty-sky-at-zero-latency line.
- `38-EFF-BASELINE.md`: the committed Before section from a real unmodified-tree run, cross-checked against `38-RESEARCH.md`'s own baseline table (every static byte count matches exactly; no route or poll-cycle value differs by more than 20%), plus placeholder `## After` and `## Live compression (VPS)` sections for the phase's later plans and final checkpoint.

## Task Commits

Each task was committed atomically:

1. **Task 1: Probe module test-support/efficiency_probe.py and its self-test** - `2b1d7fd` (test)
2. **Task 2: scripts/measure_efficiency.py and the BEFORE section of 38-EFF-BASELINE.md** - `9b991fb` (docs)

_Note: this plan's `<output>` block is delivered by this SUMMARY.md itself; no separate plan-metadata commit was needed beyond the two task commits above._

## Files Created/Modified
- `test-support/efficiency_probe.py` - counters/fakes for SQLite activity, sleeps, poll_state writes, provider latency, route byte/time weight, and a faked poll cycle
- `test-support/test_efficiency_probe.py` - 9 self-tests of the probe mechanics
- `scripts/measure_efficiency.py` - offline CLI printing the markdown measurement tables
- `.planning/phases/38-efficiency-companion-poll-cycle-storage/38-EFF-BASELINE.md` - committed Before section, placeholder After/live-compression sections

## Decisions Made
- Poll-cycle branches run sequentially against one shared state_dir (rather than seeding an independent `poll_state.json` per branch), so "repeat"/"held"/"hold entry"/"hold repeat" arise naturally from real cross-cycle state, exactly matching the research's seven-branch definition.
- The CLI patches `detect.query_provider`/`enrich.default_transport` globally for its whole run (defense in depth beyond `cycle_probe`'s own scoped patch), since a companion page render could in principle call either seam.
- `38-EFF-BASELINE.md`'s Before section keeps only the script's own markdown (starting at `## Measurement`), dropping the interleaved `GET /path`/`poll_loop: ...` stdout lines companion/app.py and poll_loop.py print during measurement - those are real production log lines, not part of the measurement record.

## Deviations from Plan

None - plan executed exactly as written. Every measured value matched (within normal seed-content variance, all under the plan's own 20% cross-check threshold) the research table's own baseline numbers, confirming the instruments measure the same things the research script did.

## Issues Encountered
One ruff finding (`F401` on an unused `gzip` import in `scripts/measure_efficiency.py`, left over from an early draft where the CLI computed gzip bytes itself instead of delegating to `efficiency_probe.route_weight()`) was caught and fixed before the Task 2 commit - not a deviation, just draft cleanup.

## User Setup Required

None - no external service configuration required. The `## Live compression (VPS)` table in `38-EFF-BASELINE.md` is an intentional placeholder: VPS access is developer-only (see `38-RESEARCH.md`'s Environment Availability table), and the plan defers filling it to the phase's final checkpoint.

## Next Phase Readiness

The Before baseline is committed and reproducible with one command
(`server/.venv/bin/python scripts/measure_efficiency.py --label before`).
Plans 38-02 through 38-13 can now implement EFF-01..EFF-06 behind
`efficiency_probe.py`'s counters, and the final plan reruns the same CLI
with `--label after` to fill in `38-EFF-BASELINE.md`'s `## After` section
for direct comparison. No blockers.

---
*Phase: 38-efficiency-companion-poll-cycle-storage*
*Completed: 2026-09-26*
