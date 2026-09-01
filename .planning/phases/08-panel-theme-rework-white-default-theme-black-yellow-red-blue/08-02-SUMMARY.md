---
phase: 08-panel-theme-rework-white-default-theme-black-yellow-red-blue
plan: 02
subsystem: enrichment
tags: [enrich, adsbdb, callsign_iata, cache, data-fix]

# Dependency graph
requires:
  - phase: 08-panel-theme-rework-white-default-theme-black-yellow-red-blue
    plan: 01
    provides: five-entry THEMES registry (no direct code dependency, same-wave sibling)
provides:
  - "server.plane.enrich._parse_route()/_route_from_entry()/airline_only_route() all agreeing on a six-key route shape, the sixth key being callsign_iata"
  - "callsign_iata: optional field, None whenever adsbdb supplied nothing usable, never route-fatal, survives a cache round-trip and the airline-name-correction seam"
affects: [08-04]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Optional-field threading through a three-leg chain (parse -> cache-write -> cache-read): normalise defensively at the parse boundary (never-trust-the-payload), never add the optional field to the required-non-empty validation loop, and confirm the two shallow-copy seams (lookup_route()'s cache write, apply_airline_name_correction()) carry it for free without editing them."

key-files:
  created: []
  modified:
    - server/plane/enrich.py
    - server/test_enrich.py

key-decisions:
  - "callsign_iata is read from flightroute's top level (a sibling of airline/origin/destination), not nested under any of those three, per the real fixture shape."
  - "callsign_iata is deliberately excluded from _parse_route()'s required-non-empty validation loop - it degrades to None on any hostile/absent value rather than turning a resolvable route into a miss (D-09's explicit warning, T-08-02-01)."
  - "lookup_route() and apply_airline_name_correction() needed zero edits - both build shallow dict(route) copies and therefore carry the new key for free. Read and confirmed, not assumed (git diff --stat proves only server/plane/enrich.py's three target functions changed)."

requirements-completed: [D-09]

coverage:
  - id: D9
    description: "adsbdb's callsign_iata field is threaded through _parse_route()'s returned dict, lookup_route()'s cache-write path, and _route_from_entry()'s cache-hit reconstruction, under the exact key name the renderer will read, with the field optional everywhere and a cache round-trip preserving it"
    requirement: "D-09"
    verification:
      - kind: unit
        ref: "server/test_enrich.py#_callsign_iata_parsed_from_real_hits"
        status: pass
      - kind: unit
        ref: "server/test_enrich.py#_callsign_iata_optional_never_route_fatal"
        status: pass
      - kind: unit
        ref: "server/test_enrich.py#_callsign_iata_cache_round_trip_parity"
        status: pass
      - kind: unit
        ref: "server/test_enrich.py#_shape_parity_across_all_three_builders"
        status: pass
      - kind: unit
        ref: "server/test_enrich.py#_raw_icao_callsign_never_smuggled_in"
        status: pass
      - kind: other
        ref: "deliberate required-field demonstration (added callsign_iata to _parse_route()'s validation loop, ran the suite, observed 2 failures, reverted via git checkout -- server/plane/enrich.py) - see below for the observed failure output"
        status: pass
    human_judgment: false

# Metrics
duration: ~15min
completed: 2026-08-31
status: complete
---

# Phase 8 Plan 02: Thread callsign_iata through enrich.py Summary

**adsbdb's already-fetched `callsign_iata` field (its IATA-formatted flight identifier) is now captured instead of discarded, added as a sixth optional key to `_parse_route()`/`_route_from_entry()`/`airline_only_route()`'s agreed six-key route shape, with `lookup_route()` and `apply_airline_name_correction()` confirmed to need zero edits because both already copy the route dict generically.**

## Performance

- **Duration:** ~15min (commit span)
- **Tasks:** 2
- **Files modified:** 2 (`server/plane/enrich.py`, `server/test_enrich.py` - exactly the plan's stated `files_modified`)

## Accomplishments

- `_parse_route()` reads `callsign_iata` from `flightroute`'s top level (a sibling of `airline`/`origin`/`destination`, confirmed against both real fixtures), appends it as a sixth key, normalises any non-empty-string value to `None`, and is explicitly NOT added to the five-member required-non-empty validation loop - a route with every other field but no IATA identifier still resolves.
- `_route_from_entry()` gained a sixth `entry.get("callsign_iata")` line, so a process restart followed by a cache-hit reconstruction cannot silently drop the field.
- `airline_only_route()` gained `callsign_iata: None` as its sixth key, keeping the shape-parity invariant its own docstring promises and `test_enrich.py`'s pre-existing key-set-parity check (unmodified) already relies on.
- `lookup_route()` and `apply_airline_name_correction()` were read in full and confirmed to need zero edits: `lookup_route()`'s cache write is a generic `dict(route)` copy, and `apply_airline_name_correction()`'s correction path is a generic shallow `dict(route)` copy with one key replaced. `git diff --stat` across both commits confirms neither function's body changed.
- `server/test_enrich.py` grew from 45 to 50 checks: two real fixtures parsed by name (not one, ruling out a hardcoded-value false pass), the optional/never-route-fatal guarantee (absent, empty, whitespace, non-string, list, dict all degrade to `None`), cache round-trip parity on both the plain-hit path and the airline-name-correction path (AIA6412: adsbdb misattributes it to "Avies", corrected to "Amelia" - the shallow-copy correction seam still carries the field), shape parity across all three builders (keys derived from a real `_parse_route()` result, not hardcoded, so a future seventh field is caught automatically), and a structural D-08 guard asserting no `callsign`/`callsign_icao` key and no value equal to the raw ICAO callsign string.
- The optional-field guard was demonstrated, not assumed: `callsign_iata` was temporarily added to `_parse_route()`'s required-non-empty loop, the suite was run and confirmed to fail (2 of 50 checks - see below for the exact observed output), then reverted via `git checkout -- server/plane/enrich.py` and the suite re-confirmed green at 50/50.

## Task Commits

Each task was committed atomically:

1. **Task 1: Thread callsign_iata through _parse_route, _route_from_entry and airline_only_route** - `ef49019` (feat)
2. **Task 2: Pin the new field's contract in test_enrich.py** - `0db4d5d` (test)

## Files Created/Modified

- `server/plane/enrich.py` - `_parse_route()` reads/normalises `callsign_iata`, extended docstring names which five fields are required and which one is optional and why; `_route_from_entry()` reconstructs it from the cache; `airline_only_route()` carries it as a sixth `None` key with an updated docstring ("same five keys" instead of "same four keys", since the function now emits `airline_name` plus five `None` fields)
- `server/test_enrich.py` - five new checks (46-50) pinning presence/optionality/cache-round-trip/shape-parity/D-08-absence; `EXPECTED_CHECK_COUNT` 45->50

## Decisions Made

- `EXPECTED_CHECK_COUNT`'s real on-disk baseline was **45**, matching the plan's own stated planning-time value exactly - no drift correction was needed here (unlike several prior 06.x-era plans in this project's history where the baseline had moved between planning and execution).
- The callsign chosen for the airline-name-correction round-trip check is **AIA6412** (Avies -> Amelia), because it is the one correction-table row already backed by a real recorded fixture (`server/fixtures/adsbdb_hit_AIA6412.json`) with its own real `callsign_iata` value (`"U36412"`) - reusing an existing fixture rather than hand-building a stubbed body for this specific check keeps the check honest against real upstream data shape, matching the same-file precedent check 30 already establishes for the plain correction-seam round-trip.
- The plan's own `<verify>`/`<acceptance_criteria>` scripts assumed both fixture files share `adsbdb_hit_AIA6412.json`'s `{"http_status", "body": {...}}` wrapper shape. Reading both fixtures confirmed `adsbdb_hit_TVF16VB.json` has no such wrapper - it IS the body directly (`{"response": {...}}`), matching how `server/test_enrich.py`'s own pre-existing `hit_body = load_fixture("adsbdb_hit_TVF16VB.json")` already uses it unwrapped. The plan's literal `f['body']` in its `<verify>` command was adjusted to `f` (the fixture itself) when running that verification locally - a Rule 3 correction to the plan's own verification script, not to any acceptance intent; the underlying assertions (six-key shape, real IATA value, optional/None-degradation battery) all ran and passed exactly as specified.

## Deviations from Plan

### Auto-fixed Issues

None requiring code changes - see "Decisions Made" above for the one verification-script literal (`f['body']` -> `f`) that needed adjusting to match the real, pre-existing fixture shape; this did not require any change to `server/plane/enrich.py` or `server/test_enrich.py` beyond what the plan's action text already specified.

**Total deviations:** 0 code deviations (1 verification-script literal corrected against the real on-disk fixture shape, documented above).

## Observed Failure Output (Task 2's deliberate required-field demonstration)

Temporarily changing `_parse_route()`'s validation loop to:
```python
for value in (airline_name, origin_iata, origin_city_raw, destination_iata, destination_city_raw, flightroute.get('callsign_iata')):
```
and running `server/.venv/bin/python3 server/test_enrich.py` produced:

```
FAIL resolve_route() corrects all three stale-brand carriers under their own prefix and leaves the same string
untouched under an unrelated prefix; the corrected Air Corsica route selects the renamed air-corsica.png/
air-corsica-atr72.png files (260827-kih) - resolve_route('FPO701', ...) = ({'airline_name': 'ASL Airlines France',
'origin_iata': None, 'origin_city': None, 'destination_iata': None, 'destination_city': None,
'callsign_iata': None}, 'airline_only'), expected airline_name 'ASL Airlines France', source 'fresh_hit'
FAIL callsign_iata is optional and never route-fatal: absent/empty/whitespace/non-string values all still resolve
a full route with callsign_iata degraded to None (D-09, T-08-02-01/T-08-02-02) - a body with callsign_iata absent
must still resolve a full route, got None
enrich: 48/50 checks pass
```

Two failures, not one: the new check written specifically to catch this class of mistake (`_callsign_iata_optional_never_route_fatal`) failed as designed, and a pre-existing, unrelated check (`_resolve_route_and_selection_for_three_stale_brand_carriers`, check 35 - its stubbed FPO701 body has no `callsign_iata` key at all) also failed as an incidental second signal, since making the field required turned that stubbed fresh-hit into a miss that then fell through to the `"airline_only"` fallback path instead. Reverted via `git checkout -- server/plane/enrich.py`; re-ran the suite and confirmed 50/50 pass again before proceeding to Task 2's commit.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- The `callsign_iata` field now exists on every route dict `resolve_route()` can return (`_parse_route()`'s live path, `_route_from_entry()`'s cache-hit path, and `airline_only_route()`'s fallback path, where it is always `None`), under the exact key name plan 08-04's renderer is expected to read (`route.get("callsign_iata")`).
- `server/plane/render.py` was not touched - confirmed via `git diff --stat` across both commits (only `server/plane/enrich.py` and `server/test_enrich.py` appear). Plan 08-04 is the consumer half: it builds the 4-tier content ladder (D-10) that decides when this field is actually displayed, and depends on this plan's shape being final.
- No companion-side file was touched, matching `08-CONTEXT.md`'s Phase Boundary (the companion web app is out of scope for this phase).

---
*Phase: 08-panel-theme-rework-white-default-theme-black-yellow-red-blue*
*Completed: 2026-08-31*

## Self-Check: PASSED

Both modified files confirmed present on disk; both task commit hashes (ef49019, 0db4d5d) confirmed in `git log`.
