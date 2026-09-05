---
phase: 13-add-an-illustration-for-an-unidentified-flight-from-the-comp
plan: 03
subsystem: api
tags: [python, stdlib-only, enrichment, provenance, security]

requires:
  - phase: 13-01
    provides: "server/plane/manual_resolutions.py's public surface (load_manual_resolutions()/set_manual_registry_state_dir()/airline_name_for_prefix()/add_entry(), the T-13-02 write-time allowlist)"
provides:
  - "enrich.airline_source_from_callsign(callsign) -> (name, source) — the provenance-aware seam consulting the static table first, then the runtime manual registry (D-01/D-06)"
  - "enrich.static_airline_name_for_prefix(prefix) -> str|None — the static-table-only accessor for the companion's D-06 supersession check"
  - "enrich.airline_from_callsign(callsign) rewritten as a one-line wrapper over airline_source_from_callsign() — signature and pre-existing behaviour unchanged"
  - "enrich.resolve_route() classifying into five sources (fresh_hit/cache_hit/airline_only/manual/miss) instead of four (D-02)"
  - "enrich.clear_resolved_unresolved_prefix(callsign, registry) -> str|None — D-14's whole implementation, note_unresolved_prefix()'s structural inverse"
affects: [13-05]

tech-stack:
  added: []
  patterns:
    - "Static-table-first, registry-fallback branch order (never a merge/comparison) as the D-06 precedence mechanism — the static lookup returns immediately, so a colliding manual entry can structurally never be consulted"
    - "note_unresolved_prefix()/clear_resolved_unresolved_prefix() written as structural inverses sharing the identical gate order, both derived from the single airline_from_callsign() verdict, so the recorder and its cleanup can never drift apart"

key-files:
  created: []
  modified:
    - server/plane/enrich.py
    - server/test_enrich.py

key-decisions:
  - "clear_resolved_unresolved_prefix()'s resolution test is airline_from_callsign() (either table), never route_source — a resolved prefix can still show fresh_hit/cache_hit on any given cycle since adsbdb wins by construction, so gating cleanup on route_source would leave stale entries uncleaned"
  - "airline_only and manual are kept as two distinct resolve_route() source values rather than merged, because health_page._SOURCE_ROWS's airline_only gloss names the static prefix table specifically — merging would make that sentence false and inflate the apparent static-table resolution rate"

requirements-completed: []

coverage:
  - id: D1
    description: "airline_source_from_callsign() resolves a callsign's ICAO prefix static-first then manual-fallback, returning (name, source); airline_from_callsign() is a one-line wrapper with unchanged signature/behaviour for every pre-existing input"
    verification:
      - kind: unit
        ref: "server/test_enrich.py (checks 51-53, 59/59 total)"
        status: pass
    human_judgment: false
  - id: D2
    description: "D-06 precedence: a prefix present in both the static table and the manual registry always reports the static name/source 'static', never 'manual'"
    verification:
      - kind: unit
        ref: "server/test_enrich.py check 53 (enrich.py) and check 55 (resolve_route())"
        status: pass
    human_judgment: false
  - id: D3
    description: "resolve_route() returns source 'manual' — never 'airline_only' — when the runtime registry, not the static table, resolved the prefix; the route dict shape is unchanged"
    verification:
      - kind: unit
        ref: "server/test_enrich.py checks 54-55; server/test_render.py (134/134); server/test_pipeline_e2e.py (6/6)"
        status: pass
    human_judgment: false
  - id: D4
    description: "clear_resolved_unresolved_prefix() removes a now-resolvable prefix's entry from the unresolved registry, gated on airline_from_callsign() rather than route_source, never-raising for hostile/malformed input"
    verification:
      - kind: unit
        ref: "server/test_enrich.py checks 56-57"
        status: pass
    human_judgment: false
  - id: D5
    description: "_ICAO_AIRLINE_PREFIXES, _AIRLINE_NAME_CORRECTIONS, illustrations.py and the drift guard coupling them remain byte-for-byte untouched; no docstring in enrich.py still claims the fixed-table-only/pure-no-I/O property; no new dependency"
    verification:
      - kind: unit
        ref: "git diff -- server/plane/illustrations.py (empty); server/test_illustrations.py (58/58); grep -c \"Pure, no I/O, no network\" (0); git diff -- server/requirements*.txt (empty); scripts/run-all-tests.sh (17/17 harnesses PASS)"
        status: pass
    human_judgment: false

duration: 35min
completed: 2026-09-06
status: complete
---

# Phase 13 Plan 03: Thread the manual-resolution registry into the enrichment seam Summary

**`enrich.airline_source_from_callsign()` — static-table-first, manual-registry-fallback provenance seam; `airline_from_callsign()` reduced to its one-line wrapper; `resolve_route()`'s fifth `"manual"` source; `clear_resolved_unresolved_prefix()` as D-14's whole implementation — all four changes to `server/plane/enrich.py` and its test harness only.**

## Performance

- **Duration:** ~35 min
- **Started:** 2026-09-05T23:00Z (context load)
- **Completed:** 2026-09-05T23:35Z
- **Tasks:** 3/3
- **Files modified:** 2 (`server/plane/enrich.py`, `server/test_enrich.py`)

## Accomplishments
- `airline_source_from_callsign(callsign)` added: the security-relevant branch order (shape gate → static table → manual registry) is exactly D-06's precedence mechanism — the static lookup returns immediately on a hit, so a colliding manual entry can never be consulted, by construction rather than by comparison.
- `static_airline_name_for_prefix(prefix)` added for the companion's D-06 supersession check — deliberately static-table-only, documented as such.
- `airline_from_callsign()` rewritten to a single-line wrapper (`return airline_source_from_callsign(callsign)[0]`); its ~10 existing call sites and 19 pre-existing tests (checks 17-19, 26-27, 36-38) see identical behaviour for every static-table input, verified unchanged.
- Its docstring rewritten precisely: the stale "Pure, no I/O, no network" / "only ever fixed table values or None" claims are gone, replaced with an accurate statement of what changed (T-13-02) and where the write-time allowlist invariant now lives (`manual_resolutions.add_entry()`/`load_manual_resolutions()`).
- `resolve_route()` extended to a fifth `"manual"` source without touching `airline_only_route()`'s construction site — the route dict shape is byte-identical, so `render.py`/`illustrations.py`/`city_for_state()` are unaffected (`test_render.py` 134/134, `test_pipeline_e2e.py` 6/6 both pass unmodified).
- `clear_resolved_unresolved_prefix()` added as `note_unresolved_prefix()`'s structural inverse, gated on `airline_from_callsign()` rather than `route_source` — the fix RESEARCH.md's Pitfall 2 warns against.
- `server/test_enrich.py` grew from 52 to 59 checks (7 new: 3 for Task 1, 2 for Task 2, 2 for Task 3), `EXPECTED_CHECK_COUNT` moved in the same edit as each task's checks, per plan instruction.
- Full suite verified: `scripts/run-all-tests.sh` — 17/17 harnesses PASS, 92% overall coverage.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add airline_source_from_callsign() and static_airline_name_for_prefix(); make airline_from_callsign() their wrapper (D-01, D-06)** — `893fbc6` (feat)
2. **Task 2: Extend resolve_route() to the fifth "manual" source (D-02)** — `1348948` (feat)
3. **Task 3: Add clear_resolved_unresolved_prefix() — D-14's whole implementation** — `9964440` (feat)

**Plan metadata:** committed as part of this summary's own commit.

## Files Created/Modified
- `server/plane/enrich.py` — `airline_source_from_callsign()`, `static_airline_name_for_prefix()`, `clear_resolved_unresolved_prefix()` added; `airline_from_callsign()` rewritten as a wrapper; `resolve_route()` extended to five sources; module docstring and `note_unresolved_prefix()`'s docstring/comment updated for accuracy after D-01
- `server/test_enrich.py` — 7 new checks (51-57 in Task order across the three commits, final total 59), `EXPECTED_CHECK_COUNT` moved 52 → 55 → 57 → 59 across the three task commits

## Decisions Made
- `clear_resolved_unresolved_prefix()`'s resolution test is `airline_from_callsign()` (either table), never `route_source` — a resolved prefix can still show `fresh_hit`/`cache_hit` on any given cycle (adsbdb wins by construction), so gating cleanup on `route_source` would leave stale entries uncleaned whenever adsbdb happened to answer. This is the plan's own explicit instruction (RESEARCH.md Pitfall 2), followed exactly.
- `"airline_only"` and `"manual"` stay two distinct `resolve_route()` source values rather than being merged, because `health_page._SOURCE_ROWS`'s `"airline_only"` gloss names the static prefix table specifically (D-02, plan's own instruction).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Stale documentation] Fixed a second, previously-unlisted stale claim in the unresolved-prefix recorder's observability comment**
- **Found during:** Task 2, while verifying the `grep -c "fourth outcome\|four sources\|one of four"` acceptance criterion.
- **Issue:** The module docstring's original phrase "as a fourth outcome" (describing `airline_only`'s 2026-08-27 addition) and the observability comment block above `note_unresolved_prefix()` ("does not change `resolve_route()`'s contract, its four source values...") both predate phase 13 and became literally false once `resolve_route()` grew a fifth source — and the module docstring phrase would have failed the plan's own acceptance-criteria grep verbatim.
- **Fix:** Reworded both without softening their historical accuracy: the module docstring now says "an additional outcome" for the historical 260827-hyy addition and separately describes phase 13's fifth source; the observability comment now says "its five source values" and clarifies that `airline_from_callsign()` is the single seam whose verdict decides both `resolve_route()`'s `airline_only`/`manual` split AND the recorder's gate (tying the two together, matching Task 3's own point about the seam being more load-bearing after D-01).
- **Files modified:** `server/plane/enrich.py` (same file, same commits as Task 1/Task 2 — no separate commit).
- **Verification:** `grep -c "fourth outcome\|four sources\|one of four" server/plane/enrich.py` returns `0`; full 57/57 then 59/59 suite passes.
- **Committed in:** `1348948` (Task 2 commit).

---

**Total deviations:** 1 auto-fixed (Rule 1, documentation accuracy, required to pass the plan's own acceptance criteria).
**Impact on plan:** No behavioural change; purely a docstring/comment accuracy fix co-located with the acceptance-criteria grep it was required to satisfy.

## Out-of-scope stale-enumeration occurrence (recorded per Task 2 instruction, not fixed here)

Task 2's `<action>` explicitly instructs recording (not fixing) any occurrence of the pre-existing four-way `route_source` enumeration found outside the files this plan owns. Confirmed present and left untouched, as instructed:

- `server/poll_loop.py` line ~1025 ("a single seam now classifies four categories, not three...") and line ~1042 ("Never called for 'airline_only'/'fresh_hit'/'cache_hit'...") — both belong to plan 13-05 (the `run_once()` wiring of `set_manual_registry_state_dir()` and `clear_resolved_unresolved_prefix()`), which will update these comments when it threads the `"manual"` source and the D-14 cleanup call into the poll cycle.

No other occurrence of an exhaustive four-way `route_source`/source enumeration was found elsewhere in the repository (`grep -rn "fresh_hit"` across `.py` files turned up only test fixtures/data using the string as a literal value, plus `companion/pages/health_page.py`'s `_SOURCE_ROWS`, which plan 13-02 already updated to five rows).

## Issues Encountered
None beyond the deviation above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- `enrich.py`'s full new surface (`airline_source_from_callsign()`, `static_airline_name_for_prefix()`, `clear_resolved_unresolved_prefix()`, the five-source `resolve_route()`) is available for plan 13-05 (`poll_loop.run_once()` wiring: calling `manual_resolutions.set_manual_registry_state_dir()` once per cycle beside the existing `illustrations.set_override_state_dir()` call, and calling `clear_resolved_unresolved_prefix()` before `trim_unresolved_prefixes()`/the `unresolved_prefixes` write-back, per this plan's own docstring's stated ordering requirement).
- `server/poll_loop.py` lines ~1025 and ~1042 still describe the pre-phase-13 four-way classification and must be updated by 13-05 when it wires the new sources in — flagged above, not fixed here (out of this plan's file scope).
- No blockers. `server/plane/illustrations.py` is untouched; the D-09 standing gate (58/58 `test_illustrations.py` checks, byte-identical file) holds. `_ICAO_AIRLINE_PREFIXES`/`_AIRLINE_NAME_CORRECTIONS` are byte-for-byte unchanged (confirmed via `git diff -- server/plane/enrich.py | grep -c "^[-+].*_ICAO_AIRLINE_PREFIXES = \|^[-+].*_AIRLINE_NAME_CORRECTIONS = "` = 0). No new dependency (`git diff -- server/requirements*.txt` empty).

---
*Phase: 13-add-an-illustration-for-an-unidentified-flight-from-the-comp*
*Plan: 03*
*Completed: 2026-09-06*
