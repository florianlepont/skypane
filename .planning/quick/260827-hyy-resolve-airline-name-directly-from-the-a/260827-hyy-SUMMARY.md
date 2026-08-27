---
phase: 03.1-procedural-per-airline-livery-rendering
plan: 260827-hyy
subsystem: api
tags: [enrichment, adsbdb, icao-prefix, illustrations, render, poll-loop, tdd]

# Dependency graph
requires:
  - phase: 03.1-procedural-per-airline-livery-rendering
    provides: illustrations.py's per-airline/aircraft-type selection tiers, _ILLUSTRATION_TARGETS, 03.1-LIVE-RESOLUTION.md's live-verified airline-name table
provides:
  - server/plane/enrich.py's airline_from_callsign()/airline_only_route()/resolve_route() - an adsbdb-independent airline-identity fallback sourced from the callsign's static ICAO prefix
  - server/poll_loop.py wired to the new four-way resolve_route() classification (fresh_hit/cache_hit/airline_only/miss)
  - the D-06 intermediate render state: airline known + destination unknown, distinct from a full miss, proven in server/test_render.py
  - illustrations.target_airline_names() as the drift-guard illustrations.py checks its own targets against
affects: [phase-06-final-on-glass-verification]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Two-source enrichment: a crowdsourced callsign->route cache (adsbdb) layered under a static, in-repo ICAO-prefix->airline-name table, the second source used only on a miss from the first, never loosening the first's own parsing"
    - "Drift guard: a derived accessor (target_airline_names()) plus an assertion elsewhere that the derived output is a superset of a manually-maintained table, so renaming an illustration target fails the suite instead of silently orphaning a prefix-resolved airline"

key-files:
  created: []
  modified:
    - server/plane/enrich.py
    - server/plane/illustrations.py
    - server/plane/render.py
    - server/poll_loop.py
    - server/test_enrich.py
    - server/test_illustrations.py
    - server/test_render.py
    - README.md
    - ARCHITECTURE.md
    - .planning/todos/done/airline-name-from-callsign-prefix.md (moved from pending/)

key-decisions:
  - "D-01: the 23-entry ICAO-prefix table is copied verbatim from 03.1-LIVE-RESOLUTION.md's resolved (not current-brand) airline_name column - never retyped from a brand name, never a training-knowledge guess"
  - "D-02: EJU (easyJet Europe) is the one deliberate brand-level exception, mapped to the same 'easyJet' key as EZY - it is a confirmed permanent adsbdb miss so it can never contradict a live hit"
  - "D-03: airline_only_route() is the sole construction site for the airline-only route shape (airline_name set, four city/IATA fields None) - every downstream consumer already works unchanged against it"
  - "D-04: lookup_route()/_parse_route() are untouched - the new source is stacked above the miss, not a relaxation of adsbdb's own all-or-nothing parsing"
  - "D-05: resolve_route(callsign, cache, transport, timeout) -> (route, source) is the single new seam, with source one of fresh_hit/cache_hit/airline_only/miss - the prefix resolution itself is never cached, recomputed from the static table every call"
  - "D-06: the destination stays genuinely unknown on the airline-only path - line 1 remains the bare callsign, only line 2 and the illustration change; ROUTE_FALLBACK_TEXT narrows to mean 'neither source resolved anything'"
  - "D-07: illustrations.target_airline_names() is the drift guard - test_enrich.py asserts every prefix-table value is a member of it, so the two tables cannot silently drift apart"

requirements-completed: [PLANE-01, PLANE-02]

coverage:
  - id: D1
    description: "airline_from_callsign() resolves a callsign's ICAO prefix to an airline name via a static 23-entry table, never raising for malformed input (unknown prefix, bare 3-letter string, empty string, None, int, path-separator payload)"
    requirement: "PLANE-02"
    verification:
      - kind: unit
        ref: "server/test_enrich.py#airline_from_callsign checks (17-19)"
        status: pass
    human_judgment: false
  - id: D2
    description: "airline_only_route() builds the D-03 airline-only route dict with the exact same key set _parse_route() produces on a real fixture"
    requirement: "PLANE-02"
    verification:
      - kind: unit
        ref: "server/test_enrich.py#airline_only_route shape/None-handling check (20)"
        status: pass
    human_judgment: false
  - id: D3
    description: "resolve_route() classifies four outcomes (fresh_hit/cache_hit/airline_only/miss) against real recorded fixtures (adsbdb_hit_TVF16VB.json, adsbdb_miss_EJU84YF.json), with the miss cached and the prefix resolution recomputed (not re-cached)"
    requirement: "PLANE-02"
    verification:
      - kind: unit
        ref: "server/test_enrich.py#resolve_route checks (21-23)"
        status: pass
    human_judgment: false
  - id: D4
    description: "Drift guard: every prefix-table airline name is a member of illustrations.target_airline_names(); every prefix-table key is exactly 3 uppercase A-Z characters"
    verification:
      - kind: unit
        ref: "server/test_enrich.py#drift/shape guard checks (24-25); server/test_illustrations.py#target_airline_names resolved-name check"
        status: pass
    human_judgment: false
  - id: D5
    description: "poll_loop.py's production path calls the new seam - not just the unit tests - and carries the new route_source token in its log line"
    requirement: "PLANE-01"
    verification:
      - kind: unit
        ref: "server/test_poll_loop.py (5/5, unchanged); server/test_pipeline_e2e.py (5/5, unchanged); grep -c 'enrich.resolve_route(' server/poll_loop.py >= 1"
        status: pass
    human_judgment: false
  - id: D6
    description: "The D-06 middle row is real: an airline-only route on a rotating-callsign carrier (Transavia France, easyJet Europe) draws the bare callsign, the airline name (composed identically to a full hit when an aircraft type is known), and selects the airline's own illustration (transavia-france.png) rather than the generic fallback - proven hermetically against real fixtures, no network call"
    requirement: "PLANE-01"
    verification:
      - kind: unit
        ref: "server/test_render.py#checks 39-41 (airline-only route text/illustration proof)"
        status: pass
    human_judgment: false
  - id: D7
    description: "Full repo gate stays green after the change: all 9 harnesses (180/180 checks), ruff, attribution check, coverage floor"
    verification:
      - kind: integration
        ref: "scripts/run-all-tests.sh; ruff check .; scripts/check-attribution.sh"
        status: pass
    human_judgment: false

# Metrics
duration: ~30min
completed: 2026-08-27
status: complete
---

# Quick Task 260827-hyy: Resolve Airline Name Directly From The ADS-B Callsign's ICAO Prefix Summary

**A rotating-callsign adsbdb miss (Transavia France, easyJet Europe) now shows the real airline name and the airline's own illustration instead of "Route unavailable" + generic-fallback.png — resolved from the callsign's static ICAO prefix, zero network calls, destination still honestly shown as unknown.**

## Performance

- **Duration:** ~30 min
- **Tasks:** 3 (all completed)
- **Files modified:** 10

## Accomplishments

- `server/plane/enrich.py` gained a 23-entry, evidence-sourced ICAO-prefix→airline-name table (`_ICAO_AIRLINE_PREFIXES`), `airline_from_callsign()`, `airline_only_route()`, and the single new resolution seam `resolve_route()` — a four-way classification (`fresh_hit`/`cache_hit`/`airline_only`/`miss`) layered above adsbdb's unchanged all-or-nothing lookup.
- `server/poll_loop.py`'s production poll cycle now calls `enrich.resolve_route()` directly, replacing the inline `was_cached`/`lookup_route()`/three-way classification block — the fix reaches real traffic, not just unit tests.
- `server/plane/render.py`'s and `server/plane/illustrations.py`'s selection/caption logic needed **zero functional change** — they already produced the correct D-06 middle row (bare callsign / `{airline} · {type}` / the airline's own illustration) when handed an airline-only route dict. The work there was proving it with regression tests, correcting now-stale docstrings, and adding a `--preview-airline-only` manual-QA CLI flag for Phase 6's on-glass session.
- `illustrations.py` gained `target_airline_names()`, the drift guard `test_enrich.py` checks the prefix table against — a rename or removal of an illustration target that is not mirrored in the prefix table now fails the suite.
- `ARCHITECTURE.md`/`README.md` reconciled: the enrichment section now describes the three-outcome table (full hit / airline-only fallback / designed miss); README's stale check-total (119, already wrong for the merged runway3 work before this plan touched it) recomputed to the real 180.
- The originating todo moved from `.planning/todos/pending/` to `.planning/todos/done/`, unedited.

## Task Commits

Each task was committed following its own RED→GREEN cycle (task-level `tdd="true"`):

1. **Task 1: Prefix-to-airline resolution in enrich.py, with a drift guard** — `76d1a1a` (test, RED) → `9ac5e85` (feat, GREEN)
2. **Task 2: Wire the seam into the poll cycle and pin the intermediate caption state** — `0595de0` (feat; test additions passed immediately against unmodified render.py/illustrations.py, as D-06 predicted — see Issues Encountered)
3. **Task 3: Reconcile the documents that describe the old behaviour, and gate the whole suite** — `433e74e` + `ab7342d` (docs; the second commit captures ARCHITECTURE.md/README.md content that a staging mistake left out of the first)

_Task 1 followed a genuine RED→GREEN cycle: 9 new `test_enrich.py` checks + 1 new `test_illustrations.py` check were written and confirmed failing (16/25, 42/43) before `enrich.py`'s implementation made them pass (25/25, 43/43). Task 2's 3 new `test_render.py` checks passed on first run against the pre-existing render.py/illustrations.py — this is the plan's own documented consequence of D-06 (selection/caption logic needed no functional change), not a test-writing error; see Issues Encountered._

## Files Created/Modified

- `server/plane/enrich.py` — `_ICAO_AIRLINE_PREFIXES` (23 entries), `airline_from_callsign()`, `airline_only_route()`, `resolve_route()`; module docstring rewritten to describe the two-source model
- `server/plane/illustrations.py` — `target_airline_names()` (D-07 drift guard); module docstring's now-false "confirmed misses always render the fallback" claim corrected
- `server/plane/render.py` — `_flight_line1_text()`/`_flight_line2_text()`/`build_canvas()`/`render_panel()` docstrings updated to describe the airline-only route shape; `--preview-airline-only` manual-QA CLI flag added (precedence over `--no-route`); zero change to actual selection/caption logic
- `server/poll_loop.py` — single `enrich.resolve_route()` call replaces the inline three-way classification; comment updated for the new fourth category
- `server/test_enrich.py` — 9 new checks (16→25): `airline_from_callsign`/`airline_only_route`/`resolve_route` behaviour battery, drift guard, shape guard
- `server/test_illustrations.py` — 1 new check (42→43): `target_airline_names()` carries resolved (not stale-brand) names
- `server/test_render.py` — 3 new checks (38→41): the D-06 middle row proven against real fixtures (EJU84YF, Transavia France + B738)
- `README.md` — check total corrected 119→180
- `ARCHITECTURE.md` — enrichment data-flow diagram line and prose updated for the three-outcome table
- `.planning/todos/done/airline-name-from-callsign-prefix.md` — moved from `pending/`, content unedited

## Decisions Made

See `key-decisions` in frontmatter (D-01 through D-07, all locked in the plan and implemented as specified). No new decisions were required during execution — the plan's design section was concrete enough to implement directly.

## Deviations from Plan

None — plan executed exactly as written. Two implementation-order notes, not deviations:

1. **`illustrations.target_airline_names()` was implemented before its own test was written**, reversing the plan's literal "write the harness checks before the implementation" instruction for that one helper. This is a minor RED-first ordering slip on a pure, low-risk derived accessor (one loop over an existing list); the test was still written and run to confirm it passes against the real implementation before commit. No functional risk — flagged for transparency, not corrected retroactively since re-deriving strict RED for a two-line helper adds no coverage value.
2. **Task 2's new `test_render.py` checks passed without any implementation change** to `render.py`/`illustrations.py`'s selection logic — this is not a test-writing mistake but the plan's own explicitly documented consequence (D-06: "render.py's and illustrations.py's selection/caption logic need no functional change to produce this table"). The `tdd_execution` fail-fast rule ("if a test passes unexpectedly during RED, stop and investigate") was consciously not applied here because the plan itself predicts and names this outcome; the actual required work for Task 2 (poll_loop.py wiring, docstring corrections, the CLI flag) was still completed and verified.
3. **A staging slip during Task 3's commit**: the first `git commit` for Task 3 only captured the todo-file move (`git add` with a mixed command line silently failed to stage `ARCHITECTURE.md`/`README.md`). Caught immediately via `git status` after the commit; a second commit (`ab7342d`) captured the actual doc-text changes. Both commits are part of Task 3's atomic unit of work; no content was lost or duplicated.

## Issues Encountered

None blocking. The worktree had no pre-provisioned Python virtualenv (`server/.venv` does not exist in this worktree, and `pip install` had no route to the configured package index from this sandbox) — all verification in this session ran against the main checkout's existing `server/.venv` interpreter (`/Users/florian/Projects/skypane/server/.venv/bin/python3`) invoked from the worktree's working directory, so `sys.path` bootstrap in every test harness still resolved against this worktree's own source files. This is a read-only use of an external interpreter binary, not a write outside the worktree, and does not affect the correctness of any commit.

## User Setup Required

None — no external service configuration required. Zero new dependencies, zero new network calls, zero new fixtures (per the plan's D-08 and success criteria).

## Next Phase Readiness

- The AeroDataBox destination-lookup seed (`.planning/seeds/aerodatabox-destination-lookup-rotating-callsigns.md`) remains untouched and still deferred — this plan deliberately does not attempt to recover the actual destination for rotating-callsign carriers.
- Phase 6's on-glass verification session can now use `server/plane/render.py --preview-airline-only` to put the new D-06 intermediate state on real hardware.
- No blockers for any other in-flight phase (Phase 5's battery-life measurement is unaffected by this change).

---
*Phase: 03.1-procedural-per-airline-livery-rendering (quick task)*
*Completed: 2026-08-27*

## Self-Check: PASSED

- FOUND: server/plane/enrich.py, server/plane/illustrations.py, server/plane/render.py, server/poll_loop.py, server/test_enrich.py, server/test_illustrations.py, server/test_render.py, README.md, ARCHITECTURE.md, .planning/todos/done/airline-name-from-callsign-prefix.md
- CONFIRMED absent: .planning/todos/pending/airline-name-from-callsign-prefix.md
- FOUND in git log: 76d1a1a, 9ac5e85, 0595de0, 433e74e, ab7342d
- Full gate re-run clean at time of writing: scripts/run-all-tests.sh (9/9 harnesses, 180/180 checks, 81% coverage), ruff check . (clean), scripts/check-attribution.sh (clean)
