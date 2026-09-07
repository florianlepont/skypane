---
phase: 16-calendar-linked-flight-highlighting-a-connected-calendar-sou
plan: 06
subsystem: infra
tags: [calendar, colour-rules, resolver, matching, iata, transavia]

# Dependency graph
requires:
  - phase: 16-calendar-linked-flight-highlighting-a-connected-calendar-sou (waves 1-3, plans 16-01/16-03/16-04)
    provides: parse_ics_events(), the calendar_rules.json registry contract (load/write), select_window_entries(), CALENDAR_REGISTRY_KEYS, CALENDAR_MATCH_TOLERANCE_S, and refresh_calendar_registry()
  - phase: 15-per-direction-themes-per-flight-colour-rules-and-roster-link
    provides: colour_rules.resolve_effective_theme_id()'s three-positional D-13 resolver and its manual-rule precedence order
provides:
  - "calendar_rules.match_calendar_theme(registry, route, render_state, device_cfg, now): D-04's pure matcher - airline (derived at runtime from callsign_iata, no static table) + far-end airport (direction-symmetric) + time window (90 min tolerance, closest-candidate tie-break)"
  - "calendar_rules.DEPARTING_STATE/ARRIVING_STATE, _airline_iata_from_route(), _far_end_iata()/_entry_far_end_iata(), _reference_time() - the matcher's supporting primitives"
  - "colour_rules.resolve_effective_theme_id(state, flight, device_cfg, calendar_theme_id=None): D-02's calendar-first precedence, additive and backward-compatible"
affects: [16-07 (poll_loop.py wiring - both resolve_effective_theme_id() call sites gain the computed calendar_theme_id argument)]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Airline half of a cross-system match key derived at runtime from an already-present field (route[\"callsign_iata\"]'s leading two characters) rather than a static lookup table, closing 16-RESEARCH.md's own flagged 'most important open question' via its own CORRECTION 1"
    - "An enrichment-provenance restriction (fresh_hit/cache_hit only) encoded as a field-presence test on the consuming function's own input shape, rather than a source-string parameter, so the same test is correct at every call site including one where the source label is stale"
    - "Same-candidate-set ambiguity resolved by (abs_time_diff, reference_time, field-tuple) tuple comparison - deterministic regardless of iteration order, no reliance on dict/list ordering"
    - "A downstream resolver's precedence extended via one optional, defaulted, membership-guarded keyword argument, checked first, in the exact isinstance()+THEMES idiom the function already used three times - zero new imports, leaf-import contract intact"

key-files:
  created: []
  modified:
    - server/plane/calendar_rules.py
    - server/plane/colour_rules.py
    - server/test_calendar_rules.py
    - server/test_colour_rules.py

key-decisions:
  - "Implemented CORRECTION 1 literally as written in 16-RESEARCH.md's addendum: no static IATA<->ICAO or IATA<->airline-name table was added anywhere - _airline_iata_from_route() derives the airline from route[\"callsign_iata\"] at runtime, verified in the harness against a two-letter designator ('ZQ') absent from every table in this codebase"
  - "match_calendar_theme()'s field-presence test (all three of origin_iata/destination_iata/callsign_iata present and shape-valid) is the sole enforcement of the fresh_hit/cache_hit restriction - route_source is not a parameter and does not appear anywhere in the function's source (verified by an AST/source-text acceptance check), so the same test works correctly at poll_loop.py's held/repaint call site where the source label would read 'held'"
  - "colour_rules.py's module docstring now names server.plane.calendar_rules in its forbidden-import list; the reverse import direction (calendar_rules -> colour_rules) remains and stays forbidden - the calendar value crosses the boundary only as a plain argument, per D-02"
  - "calendar_rules.py gained one new import - server.device_config - solely for the THEMES membership test match_calendar_theme() needs; this mirrors the identical single-module exception colour_rules.py already carries, since device_config.py is itself a confirmed leaf"
  - "Provisioned a server/.venv symlink to the main checkout's already-built venv (this worktree's own .venv/ was absent, matching the documented phase-14-01 network-free bootstrap pattern) - untracked and gitignored, not part of any commit"

requirements-completed: []

coverage:
  - id: D1
    description: "match_calendar_theme() implements D-04's three-part key (airline + far-end airport + time window), each condition independently falsifiable, with direction-symmetric far-end comparison (destination-vs-destination for a departure, origin-vs-origin for an arrival) pinned by a mutation-tested check"
    verification:
      - kind: unit
        ref: "server/test_calendar_rules.py#match truth table + direction-symmetry checks (56-63)"
        status: pass
    human_judgment: false
  - id: D2
    description: "The airline half is derived at runtime from route[\"callsign_iata\"] with no static IATA table anywhere in the module - proved by a match on a designator ('ZQ') no table could contain, and by a module-scan acceptance check finding no two-letter-keyed dict"
    verification:
      - kind: unit
        ref: "server/test_calendar_rules.py#_airline_derived_not_tabulated (64)"
        status: pass
    human_judgment: false
  - id: D3
    description: "A calendar match cannot fire on an airline_only, manual or miss enrichment - enforced by a field-presence test (not a route_source string), so it also holds at poll_loop's held/repaint call site"
    verification:
      - kind: unit
        ref: "server/test_calendar_rules.py#_airline_only_shaped_route_never_matches, _manual_shaped_route_never_matches, _none_route_never_matches (65-67)"
        status: pass
    human_judgment: false
  - id: D4
    description: "A same-route ambiguity (the committed fixture's own BBB-ORY pair, ~8.5h apart) resolves to the single closest-in-time candidate, deterministically regardless of entry list order"
    verification:
      - kind: unit
        ref: "server/test_calendar_rules.py#ambiguity checks using FIXTURE_ICS (68-71)"
        status: pass
    human_judgment: false
  - id: D5
    description: "resolve_effective_theme_id() gains an additive calendar_theme_id keyword, checked first, beating even an exact-callsign rule (D-02's accepted consequence) and the arrivals override, while every three-positional call remains byte-for-byte identical"
    verification:
      - kind: unit
        ref: "server/test_colour_rules.py#D-02 precedence + backward-compatibility checks (28-32)"
        status: pass
    human_judgment: false
  - id: D6
    description: "A calendar_theme_id that is not a member of device_config.THEMES is membership-tested away at both the matcher and the resolver, never reaching render.build_canvas() (T-16-TAMPER)"
    verification:
      - kind: unit
        ref: "server/test_calendar_rules.py#_tampered_calendar_theme_id_never_returned (73); server/test_colour_rules.py#_tampered_calendar_theme_id_ignored (33)"
        status: pass
    human_judgment: false

# Metrics
duration: ~30min
completed: 2026-09-07
status: complete
---

# Phase 16 Plan 06: Calendar match + resolver precedence Summary

**`match_calendar_theme()` implements D-04's airline+far-end+time key with the airline derived at runtime from `callsign_iata` (no static table), and `resolve_effective_theme_id()` gains an additive `calendar_theme_id` keyword that beats every manual rule (D-02)**

## Performance

- **Duration:** ~30 min
- **Started:** 2026-09-07 (session start)
- **Completed:** 2026-09-07T23:02:28Z
- **Tasks:** 3
- **Files modified:** 4

## Accomplishments
- `server/plane/calendar_rules.py` gained `match_calendar_theme()` and its four supporting primitives (`DEPARTING_STATE`/`ARRIVING_STATE`, `_airline_iata_from_route()`, `_far_end_iata()`/`_entry_far_end_iata()`, `_reference_time()`), implementing D-04's three-part match key with the airline derived at runtime per 16-RESEARCH.md CORRECTION 1 - no static IATA table was built anywhere.
- `server/plane/colour_rules.py`'s `resolve_effective_theme_id()` gained a fourth, optional, defaulted `calendar_theme_id` keyword, checked first per D-02, with zero new imports and the leaf-import contract intact (now naming `calendar_rules` explicitly in its forbidden-import docstring clause).
- Both harnesses extended in place: `server/test_calendar_rules.py` (55 -> 74 checks) and `server/test_colour_rules.py` (27 -> 33 checks), covering the match truth table, direction symmetry, the runtime-derived-airline proof, the airline_only/manual/miss narrowing, fixture-driven ambiguity resolution, D-02's precedence (including beating an exact-callsign rule), backward compatibility, and tamper resistance on both sides of the seam.
- Verified two of the harness's checks are genuinely load-bearing (not vacuous) by temporarily reintroducing the exact bugs they guard against - moving the resolver's calendar guard after the rule lookups, and making `_entry_far_end_iata()` return the destination for both render states - confirming each mutation produces the specifically-named failing check, then restoring the source.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add match_calendar_theme() - D-04's airline + far-end + time-window rule** - `f8ffa1b` (feat)
2. **Task 2: Extend colour_rules.resolve_effective_theme_id() with the calendar_theme_id keyword (D-02)** - `e24c1c6` (feat)
3. **Task 3: Extend both harnesses with the match truth table and the precedence checks** - `8af97cb` (test)

_No plan-metadata commit: the orchestrator (not this executor) owns STATE.md/ROADMAP.md and their commit, per this plan's own instructions._

## Files Created/Modified
- `server/plane/calendar_rules.py` - Adds `match_calendar_theme()` and its supporting primitives; adds one `server.device_config` import for the THEMES membership test
- `server/plane/colour_rules.py` - Adds the `calendar_theme_id=None` keyword to `resolve_effective_theme_id()`, checked first; extends the module/function docstrings
- `server/test_calendar_rules.py` - Adds 19 checks (56-74) covering the matcher; raises `EXPECTED_CHECK_COUNT` to 74
- `server/test_colour_rules.py` - Adds 6 checks (28-33) covering D-02's precedence, backward compatibility and tampering; raises `EXPECTED_CHECK_COUNT` to 33

## Decisions Made
- No static IATA<->ICAO table anywhere, per CORRECTION 1: the airline is derived at runtime from `route["callsign_iata"]`'s leading two characters, and a module-scan acceptance check confirms no two-letter-keyed dict was introduced.
- The `fresh_hit`/`cache_hit` restriction is enforced by a field-presence test on `route`'s own shape (`origin_iata`/`destination_iata`/`callsign_iata` all present and shape-valid), never by a `route_source` string - `route_source` is not a parameter of `match_calendar_theme()` and does not appear anywhere in its source, verified by an explicit acceptance check, so the restriction holds correctly at both of `poll_loop.py`'s call sites including the held/repaint one where the source label is stale.
- `calendar_rules.py` gained exactly one new import (`server.device_config`) to perform its own THEMES membership check before any comparison work - the identical single-module exception `colour_rules.py` already documents, since `device_config.py` is itself a confirmed leaf.
- `resolve_effective_theme_id()`'s calendar check is the first statement of the function body, using the identical `isinstance(..., str) and ... in device_config.THEMES` guard shape already used three times elsewhere in the same function - no new helper, no new pattern.
- Same-route ambiguity resolves via a `(abs_time_diff, reference_time, field_tuple)` comparison, picking the smallest tuple - deterministic regardless of registry iteration order, verified against the committed fixture's own BBB-ORY pair (~8.5h apart) with both forward and reversed entry-list orderings producing the identical result.
- The docstring language avoids the literal substring `route_source` (required by the plan's own acceptance criterion, which greps the function's source for it) while still explaining the exclusion in full - referring to "the enrichment-provenance label" / "the held/repaint branch reports the value `\"held\"`" instead.
- Provisioned `server/.venv` in this worktree as a symlink to the main checkout's already-built venv, since this worktree had no venv of its own - untracked, gitignored, matching the pre-existing phase-14-01 documented pattern for exactly this situation.

## Deviations from Plan

None - plan executed exactly as written. The only adjustment was cosmetic: the function's docstring initially used the literal string "route_source" to explain why that value is excluded from the parameter list, which collided with the plan's own acceptance criterion asserting that exact substring is absent from the function's source; reworded to convey the identical meaning without the literal substring, verified against the acceptance command itself.

## Issues Encountered
- A stale `__pycache__/colour_rules.cpython-311.pyc` briefly made a deliberate mutation-test appear to still be failing after the source file had already been restored from backup (byte-identical per `diff`). Cleared all `__pycache__` directories under `server/` and re-ran; the harness immediately reported 33/33 again, confirming the restore had in fact succeeded and the stale bytecode was the sole cause. No source change was needed.

## User Setup Required
None - no external service configuration required. This plan touches only pure functions; no environment variable, dependency, or deployment step changes.

## Next Phase Readiness
- `calendar_rules.match_calendar_theme()` and `colour_rules.resolve_effective_theme_id(..., calendar_theme_id=...)` are both ready for plan 16-07 to wire together at `poll_loop.py`'s two `resolve_effective_theme_id()` call sites, computing the calendar argument identically at both per the both-branches invariant.
- `server/plane/render.py`, `server/poll_loop.py`, `server/device_config.py` and `companion/` remain untouched by this plan, confirmed by `git diff --stat`, consistent with this plan's own prohibitions.
- Full suite (`scripts/run-all-tests.sh`) exits 0 at 92% coverage; `ruff check .` is clean.

---
*Phase: 16-calendar-linked-flight-highlighting-a-connected-calendar-sou*
*Completed: 2026-09-07*

## Self-Check: PASSED

- FOUND: server/plane/calendar_rules.py
- FOUND: server/plane/colour_rules.py
- FOUND: server/test_calendar_rules.py
- FOUND: server/test_colour_rules.py
- FOUND: .planning/phases/16-calendar-linked-flight-highlighting-a-connected-calendar-sou/16-06-SUMMARY.md
- FOUND commit: f8ffa1b (Task 1)
- FOUND commit: e24c1c6 (Task 2)
- FOUND commit: 8af97cb (Task 3)
