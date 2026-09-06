---
phase: 13-add-an-illustration-for-an-unidentified-flight-from-the-comp
plan: 05
subsystem: api
tags: [python, stdlib-only, poll-loop, enrichment, provenance]

requires:
  - phase: 13-01
    provides: "server/plane/manual_resolutions.py's set_manual_registry_state_dir()/add_entry()/airline_name_for_prefix() (D-01/D-05)"
  - phase: 13-03
    provides: "enrich.py's five-source resolve_route(), the 'manual' source, and clear_resolved_unresolved_prefix() (D-01/D-02/D-14's whole implementation)"
provides:
  - "server/poll_loop.py's run_once() calls manual_resolutions.set_manual_registry_state_dir(state_dir) once per cycle, immediately after illustrations.set_override_state_dir(state_dir) — the call site both D-01/D-02's key_links require"
  - "server/poll_loop.py's run_once() calls enrich.clear_resolved_unresolved_prefix() unconditionally in the unresolved_prefixes block, before the 'miss' branch and before trim_unresolved_prefixes()/the write-back — D-14's cleanup wired into the sole caller"
  - "server/poll_loop.py's two previously-stale 'four source values' comments now describe all five (fresh_hit/cache_hit/airline_only/manual/miss)"
affects: []

tech-stack:
  added: []
  patterns:
    - "Single comment block covering two adjacent process-global setter calls (illustration override + manual registry), extended rather than duplicated, matching this file's existing CFG-01/CFG-12 once-per-cycle-read convention"
    - "D-14's cleanup call placed unconditionally and un-gated on route_source, immediately after the unresolved_prefixes dict is established and before any branch that reads or mutates it further — the ordering the plan's key_links required"

key-files:
  created: []
  modified:
    - server/poll_loop.py
    - server/test_poll_loop.py

key-decisions:
  - "Referred to the D-14 cleanup helper only in prose inside the code comment (never repeating its literal function name a second time on a separate line) so grep -c \"clear_resolved_unresolved_prefix\" server/poll_loop.py stays at exactly 1 (the acceptance criterion), while the actual call site's docstring-equivalent reasoning is still fully spelled out"
  - "Split what the plan describes as two tasks into two atomic commits by temporarily withholding Task 2's two test checks and EXPECTED_CHECK_COUNT bump from Task 1's commit, then re-adding them for Task 2's commit — preserves the plan's own task-by-task commit granularity even though both tasks' checks were drafted together"

requirements-completed: []

coverage:
  - id: D1
    description: "run_once() configures manual_resolutions from THIS cycle's own state_dir (D-01): a seeded prefix resolves after a cycle against its state dir, and a cycle against a different, registry-less state dir leaves it unresolved again"
    verification:
      - kind: unit
        ref: "server/test_poll_loop.py (check 47 of 64 — 'run_once() configures the manual-resolution registry from THIS cycle's own state_dir every cycle')"
        status: pass
    human_judgment: false
  - id: D2
    description: "A detected flight whose callsign carries a manually-registered prefix, with adsbdb returning nothing, is recorded end-to-end with route_source == 'manual' and a route carrying the operator's airline name"
    verification:
      - kind: unit
        ref: "server/test_poll_loop.py (check 48 of 64)"
        status: pass
      - kind: integration
        ref: "server/test_pipeline_e2e.py (6/6); stub-server/test_poll_cycle.py (40/40)"
        status: pass
    human_judgment: false
  - id: D3
    description: "D-14: a cycle detecting a flight whose prefix is now resolvable removes that prefix's entry from unresolved_prefixes and persists the removal, leaving a still-unresolvable prefix's entry byte-identical"
    verification:
      - kind: unit
        ref: "server/test_poll_loop.py (check 49 of 64)"
        status: pass
    human_judgment: false
  - id: D4
    description: "The D-14 cleanup is independent of route_source — it removes a resolved prefix's entry even on a 'fresh_hit' cycle (adsbdb answered), the case a route_source-gated implementation would miss (RESEARCH.md Pitfall 2)"
    verification:
      - kind: unit
        ref: "server/test_poll_loop.py (check 50 of 64)"
        status: pass
    human_judgment: false
  - id: D5
    description: "No comment in run_once() still presents the enrichment sources as a closed set of four; D-09 standing gate and single-writer gate both hold"
    verification:
      - kind: unit
        ref: "grep -c \"fourth\\|four categories\" server/poll_loop.py (0 in the touched block); server/test_illustrations.py (58/58); git diff --stat -- server/plane/illustrations.py (empty); git diff --stat -- companion/ (empty); scripts/run-all-tests.sh (17/17 harnesses, 92% coverage)"
        status: pass
    human_judgment: false

duration: 45min
completed: 2026-09-06
status: complete
---

# Phase 13 Plan 05: Wire the manual-resolution registry into the poll cycle Summary

**`server/poll_loop.py`'s `run_once()` now calls `manual_resolutions.set_manual_registry_state_dir(state_dir)` once per cycle (D-01) and `enrich.clear_resolved_unresolved_prefix()` unconditionally before the miss-recording branch (D-14) — two two-line call sites plus a comment sweep and four new harness checks (60 → 64).**

## Performance

- **Duration:** ~45 min
- **Started:** 2026-09-06T00:00Z (context load)
- **Completed:** 2026-09-06T00:45Z
- **Tasks:** 2/2
- **Files modified:** 2 (`server/poll_loop.py`, `server/test_poll_loop.py`)

## Accomplishments
- `manual_resolutions.set_manual_registry_state_dir(state_dir)` added immediately after `illustrations.set_override_state_dir(state_dir)` inside `run_once()` — the single existing comment block above both calls now covers the shared placement reasoning (single entry point for both the systemd oneshot and the companion's in-process `POST /poll-now` trigger), the once-per-cycle reload reasoning (mirroring the `device_cfg` CFG-01/CFG-12 rule), and the operator-facing latency contract (a manual resolution reaches the glass at the next wake, never instantly).
- `enrich.clear_resolved_unresolved_prefix(current_flight.get("callsign"), unresolved_prefixes)` added unconditionally in the `unresolved_prefixes` block, immediately after the dict is established and before the `if route_source == "miss":` branch, `trim_unresolved_prefixes()`, and the `poll_state["unresolved_prefixes"] = unresolved_prefixes` write-back — confirmed by reading the block (not just grep) that the call sits at the same indentation level as the `unresolved_prefixes` retrieval, not nested inside the miss branch.
- Both stale "four source values" comments (the one describing the airline-only category, the one naming which sources `note_unresolved_prefix()` is never called for) rewritten to name all five sources including `"manual"`, preserving the D-02 distinction between `"airline_only"` (static table) and `"manual"` (runtime registry).
- `server/test_poll_loop.py` grew from 60 to 64 checks: two for the per-cycle-load/end-to-end-manual-source behavior (Task 1), two for the D-14 cleanup — one proving the removal itself, one proving it fires even on a `"fresh_hit"` cycle where a `route_source`-gated implementation would fail (Task 2, RESEARCH.md Pitfall 2 made executable).
- Full suite verified: `scripts/run-all-tests.sh` — 17/17 harnesses PASS, 92% overall coverage. `server/test_pipeline_e2e.py` (6/6) and `stub-server/test_poll_cycle.py` (40/40) both green. `server/test_illustrations.py` still 58/58, `server/plane/illustrations.py` and `companion/` both byte-for-byte untouched (D-09 standing gate, single-writer gate).

## Task Commits

Each task was committed atomically:

1. **Task 1: Load the manual-resolution registry once per cycle inside run_once() (D-01)** — `9b55ba9` (feat)
2. **Task 2: Remove a now-covered prefix from the gap registry each cycle (D-14)** — `6c23a58` (feat)

**Plan metadata:** committed as part of this summary's own commit.

_Note: both tasks were TDD-flagged in the plan; each commit above bundles the harness checks with the implementation because the plan's own `<action>` blocks specify "add checks in this same edit, moving EXPECTED_CHECK_COUNT" rather than a separate RED commit — matching this file's established one-commit-per-task convention (13-01 through 13-04 do the same)._

## Files Created/Modified
- `server/poll_loop.py` — added the `manual_resolutions` import; added `manual_resolutions.set_manual_registry_state_dir(state_dir)` beside `illustrations.set_override_state_dir(state_dir)`; extended that comment block; added the unconditional `enrich.clear_resolved_unresolved_prefix()` call before the miss-recording branch; rewrote the two stale four-source comments to five
- `server/test_poll_loop.py` — added checks 47-50 (per-cycle registry reload, end-to-end `route_source=="manual"`, D-14 cleanup removal, D-14 cleanup independence from `route_source`); `EXPECTED_CHECK_COUNT` moved 60 → 62 → 64 across the two task commits

## Decisions Made
- Worded the D-14 cleanup's code comment so it never repeats the literal string `clear_resolved_unresolved_prefix` a second time on its own line — the plan's own acceptance criterion requires `grep -c "clear_resolved_unresolved_prefix" server/poll_loop.py` to return exactly `1` (the call site itself), and an earlier draft comment mentioning the function by name would have made it `2`.
- Committed Task 1 and Task 2 as two separate atomic commits even though both tasks' test checks were drafted in the same editing pass, by temporarily withholding Task 2's two checks and its `EXPECTED_CHECK_COUNT` bump until Task 2's own commit — preserving the plan's task-by-task commit granularity (this plan's own explicit requirement) without losing any of the up-front analysis.

## Deviations from Plan

None - plan executed exactly as written. The one wording choice above (avoiding a second literal mention of the helper's name in the comment) was required to satisfy the plan's own acceptance criterion, not a deviation from it.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- The D-01/D-14 wiring this plan's `key_links` specified is complete: a manual resolution saved from the companion reaches the frame on the device's very next wake (via `set_manual_registry_state_dir()` reloading once per cycle from `run_once()`), and a prefix that becomes resolvable disappears from `poll_state.json`'s `unresolved_prefixes` on the next cycle that observes it, regardless of that cycle's own `route_source` (D-14).
- `server/poll_loop.py`'s `run_once()` is now phase 13's single, complete wiring point — no sibling plan needs to touch this file further for D-01/D-02/D-14.
- No blockers. `server/plane/illustrations.py` remains byte-for-byte untouched (D-09 standing gate, 58/58); `companion/` gained no write path to `poll_state.json` (`git diff --stat -- companion/` empty, single-writer gate holds); no new dependency.

---
*Phase: 13-add-an-illustration-for-an-unidentified-flight-from-the-comp*
*Plan: 05*
*Completed: 2026-09-06*

## Self-Check: PASSED

All modified files (`server/poll_loop.py`, `server/test_poll_loop.py`) and both task commit hashes (`9b55ba9`, `6c23a58`) verified present on disk / in git log.
