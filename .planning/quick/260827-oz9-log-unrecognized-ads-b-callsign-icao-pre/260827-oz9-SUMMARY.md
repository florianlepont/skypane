---
phase: 05-low-battery-indicator
plan: 260827-oz9
subsystem: infra
tags: [enrichment, adsbdb, poll_loop, observability, icao-prefix, poll_state.json]

requires:
  - phase: 03.1-procedural-per-airline-livery-rendering
    provides: "airline_from_callsign()/_ICAO_AIRLINE_PREFIXES static prefix table and resolve_route()'s four-way source classification"
provides:
  - "enrich.note_unresolved_prefix()/trim_unresolved_prefixes(): a pure, bounded, hostile-input-proof recorder for callsign prefixes resolve_route() classifies as \"miss\""
  - "poll_loop.py persists the registry into poll_state.json's unresolved_prefixes key on every miss cycle, alongside enrichment_cache"
  - "the poll_loop: log line's new unknown_prefix= field, plus a runbook recipe (journald grep + python3 one-liner) for reading the registry"
affects: [enrich.py, poll_loop.py, deployment-runbook]

tech-stack:
  added: []
  patterns:
    - "Registry stored in poll_state.json under its own key (unresolved_prefixes), mirroring enrichment_cache's persistence pattern (tmp-write-then-os.replace, bounded entry count)"
    - "Recorder derives its record/skip decision from a single existing seam (airline_from_callsign()) rather than a second parallel table lookup, so it cannot drift from resolve_route()'s classification as the table grows"

key-files:
  created: []
  modified:
    - server/plane/enrich.py
    - server/test_enrich.py
    - server/poll_loop.py
    - server/test_poll_loop.py
    - ARCHITECTURE.md
    - deploy/README.md
    - README.md

key-decisions:
  - "Eviction policy is lowest-count-then-oldest-last-seen-then-lexicographic-prefix, deliberately NOT trim_cache()'s insertion-order eviction, so a recurring coverage gap survives a flood of one-off/spoofed prefixes (QT-oz9-D-04)"
  - "The runbook's durable-record command pipes `cat <path>` through `python3 -c` (both quoted with single quotes for python strings) rather than embedding the path inside python's own open() call, so the command survives an ssh paste without nested-quote escaping and stays a single self-contained shell line"

requirements-completed: [PLANE-01, PLANE-02]

coverage:
  - id: D1
    description: "note_unresolved_prefix()/trim_unresolved_prefixes() record a shape-valid unrecognized ICAO prefix, bounded by entry count and example-callsign length, evicting by recurrence not recency"
    requirement: "PLANE-01"
    verification:
      - kind: unit
        ref: "server/test_enrich.py#checks 40-45"
        status: pass
    human_judgment: false
  - id: D2
    description: "poll_loop.py persists the registry across process boundaries in poll_state.json and names the prefix in the poll_loop: log line"
    requirement: "PLANE-02"
    verification:
      - kind: unit
        ref: "server/test_poll_loop.py#checks 6-8"
        status: pass
    human_judgment: false
  - id: D3
    description: "ARCHITECTURE.md/deploy/README.md/README.md document the mechanism and a working production inspection recipe"
    verification:
      - kind: unit
        ref: "inline verify scripts against ARCHITECTURE.md/deploy/README.md/README.md content, including live execution of the documented python3 one-liner"
        status: pass
    human_judgment: false

duration: 25min
completed: 2026-08-27
status: complete
---

# Phase 05 Quick Task 260827-oz9: Log unrecognized ADS-B callsign ICAO prefixes Summary

**A pure, bounded, eviction-by-recurrence recorder in `enrich.py` that turns `resolve_route()`'s existing "miss" classification into a durable `poll_state.json` registry and a `poll_loop:` log field, plus a working runbook command to read it back.**

## Performance

- **Duration:** 25 min
- **Started:** 2026-08-27T16:18:00Z (approx.)
- **Completed:** 2026-08-27T16:43:51Z
- **Tasks:** 3
- **Files modified:** 7

## Accomplishments
- `enrich.note_unresolved_prefix()`/`trim_unresolved_prefixes()`: records a shape-valid callsign's 3-letter ICAO prefix only when its prefix is genuinely absent from `_ICAO_AIRLINE_PREFIXES` (derived from the same `airline_from_callsign()` call `resolve_route()` uses, so the two can never drift), bounded by `UNRESOLVED_PREFIX_MAX_ENTRIES`/`UNRESOLVED_EXAMPLE_MAX_LEN`, with recurrence-favouring eviction (lowest count, then oldest last-seen, then lexicographic prefix) — deliberately the opposite of `trim_cache()`'s insertion-order policy.
- `poll_loop.py` persists the registry into `poll_state.json`'s `unresolved_prefixes` key on the same `save_poll_state()` call as `enrichment_cache`/`last_flight`, and adds an `unknown_prefix=%s` field to the existing single `poll_loop:` log line, positioned right after `route_source=`.
- `ARCHITECTURE.md`'s Enrichment section, `deploy/README.md`'s Reading Logs section (a journald grep plus a live-tested `python3` one-liner), and `README.md`'s Tests section (checks total recomputed to 212) document the mechanism and its production inspection recipe.

## Task Commits

Each task was committed atomically:

1. **Task 1: A pure, bounded, hostile-input-proof unrecognized-prefix recorder in enrich.py** - `1d03c76` (feat)
2. **Task 2: Persist the registry across poll cycles and name the prefix in the journal** - `94de015` (feat)
3. **Task 3: Document the mechanism in ARCHITECTURE.md and the production inspection recipe in the deployment runbook** - `b453092` (docs)

## Files Created/Modified
- `server/plane/enrich.py` - `note_unresolved_prefix()`, `trim_unresolved_prefixes()`, `_unresolved_prefix_sort_key()`, `UNRESOLVED_PREFIX_MAX_ENTRIES` (200), `UNRESOLVED_EXAMPLE_MAX_LEN` (16)
- `server/test_enrich.py` - checks 40-45, `EXPECTED_CHECK_COUNT` 39 -> 45
- `server/poll_loop.py` - `unknown_prefix` initialised before branching, recorded/trimmed/saved inside the flight-detected branch, added to the log line and module docstring
- `server/test_poll_loop.py` - checks 6-8 (stub `enrich.default_transport` in a try/finally), `EXPECTED_CHECK_COUNT` 5 -> 8, module docstring extended
- `ARCHITECTURE.md` - one new paragraph in the Enrichment subsection
- `deploy/README.md` - two new commands in Reading Logs plus explanatory prose
- `README.md` - Tests section check total 203 -> 212

## Decisions Made
- Followed the plan's fixed naming table (QT-oz9-D-10) exactly: `note_unresolved_prefix`, `trim_unresolved_prefixes`, `UNRESOLVED_PREFIX_MAX_ENTRIES`, `UNRESOLVED_EXAMPLE_MAX_LEN`, `unresolved_prefixes`, `unknown_prefix`.
- Chose `UNRESOLVED_PREFIX_MAX_ENTRIES = 200` (comfortably above the ~29-row `_ICAO_AIRLINE_PREFIXES` table, same order of magnitude as the existing 300-entry `enrichment_cache`) and `UNRESOLVED_EXAMPLE_MAX_LEN = 16` (real ICAO callsigns are at most 8 characters; doubled for margin against a spoofed field).
- For the runbook's durable-record command, used `ssh root@<vps-ip> cat <path> | python3 -c "..."` (python string literals in single quotes, shell `-c` argument in double quotes) instead of embedding the path inside python's own `open()` call — this keeps the path an isolated, unquoted shell word so it substitutes cleanly, avoids any nested-quote escaping across the ssh hop, and was proven to execute correctly both locally and via the plan's own verify script.

## Deviations from Plan

### Auto-fixed Issues

None - the implementation followed the plan's design decisions, task actions, and fixed naming table exactly.

### Noted Verify-Script Discrepancy (not a code deviation)

Task 2's plan-provided automated verify included:
```python
assert src.count('print(') == 1, 'run_once() must keep exactly one print statement (QT-oz9-D-07), found %d' % src.count('print(')
```
This counts literal `print(` occurrences across the *entire* `server/poll_loop.py` file. `main()`'s existing exception handler (`print("poll_loop: cycle failed: ...")`) already contributed a second occurrence **before this quick task began** (confirmed via `git show HEAD~1:server/poll_loop.py`), so this exact assertion was already unsatisfiable at baseline, independent of anything this plan added. The actual invariant QT-oz9-D-07 cares about — that `run_once()` itself has exactly one `print()` call, with no second print statement added for the new field — was confirmed directly via AST inspection (`ast.walk` over the `run_once` FunctionDef found exactly 1 `print` call). No code change was made in response to this; it is a pre-existing property of the verify script's literal-substring approach, not a defect this plan introduced or needs to fix (out of scope: `main()`'s error-handling print is unrelated to this plan's files-modified list in spirit, and modifying it was never part of the task).

---

**Total deviations:** 0 auto-fixed. One noted verify-script discrepancy, documented above and not requiring a code change.
**Impact on plan:** None - all `<done>` criteria and the plan's `<verification>`/`<success_criteria>` sections are satisfied; the full suite (212/212 across 9 harnesses) and ruff both pass.

## Issues Encountered
- `server/.venv` did not exist in this worktree; created it with `python3.11 -m venv server/.venv` and installed `server/requirements.txt`/`server/requirements-dev.txt` (pip resolved through a local mirror after DNS failures against an internal Nexus proxy — not a project change, just local environment setup).
- Constructing the deploy/README.md runbook one-liner required working through ssh's argument-flattening behavior (locally-stripped quotes don't survive the ssh hop as structural boundaries) to arrive at a `cat | python3 -c "..."` form that both (a) works when a developer actually pastes it after `ssh root@<vps-ip>`, and (b) survives the plan's own verify script, which strips only the `ssh <host> ` prefix and executes the remainder directly. Confirmed both properties by running the exact command locally against a synthetic state file before committing it.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- The recorder, persistence, log field, and runbook are all live and covered by the full test suite; no further work is required for this quick task's stated objective.
- A recorded prefix's remediation path (live-verify against adsbdb, add a row to `_ICAO_AIRLINE_PREFIXES`) is unchanged from the existing manual process this task made discoverable — no new tooling is implied for that step.

---
*Phase: 05-low-battery-indicator (quick task)*
*Completed: 2026-08-27*

## Self-Check: PASSED

All claimed files exist on disk (server/plane/enrich.py, server/test_enrich.py, server/poll_loop.py, server/test_poll_loop.py, ARCHITECTURE.md, deploy/README.md, README.md, this SUMMARY.md) and all three task commits (1d03c76, 94de015, b453092) are present in `git log --oneline --all`.
