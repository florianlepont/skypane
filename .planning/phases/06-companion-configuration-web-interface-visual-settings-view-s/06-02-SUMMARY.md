---
phase: 06-companion-configuration-web-interface-visual-settings-view-s
plan: 02
subsystem: detection
tags: [python, ads-b, geofencing, runway-detection, cfg-12, cfg-05]

# Dependency graph
requires:
  - phase: 06-companion-configuration-web-interface-visual-settings-view-s (plan 01)
    provides: device_config.py's RUNWAYS registry contract (id-set agreement asserted here, verified in plan 06-10)
provides:
  - "adsb-test/runway3.json's runways block (ids '3', '06-24', '02-20') carrying per-runway threshold + corridor geometry"
  - "server/plane/detect.py generalised to select_aircraft_for_runway(aircraft, geofence, runway_id=...), with select_runway3_aircraft() as a byte-compatible thin wrapper"
  - "poll_current_aircraft()'s diagnostics dict distinguishing an all-providers-failed poll from a no-aircraft poll"
  - "--runway CLI flag on detect.py, validated against the geofence's own runway_ids()"
affects: [companion-config-form, poll_loop, render, device-health-fault-icon]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "runway_block()/runway_ids() resolve a runway id against geofence['runways'], falling back to the legacy flat runway/corridor keys for any unrecognised id - never raises, never widens a gate (T-06-02-01)"
    - "Deprecated-tag preservation: on_runway3 kept as an alias of the new on_runway tag rather than removed, so every pre-existing caller reading the old tag name keeps working"

key-files:
  created: []
  modified:
    - adsb-test/runway3.json
    - server/plane/detect.py
    - server/test_plane_detection.py

key-decisions:
  - "runways_source (the provenance note for the new runways block) is a sibling key of runways, not nested inside it, so runways itself stays exactly the three runway-id keys server/plane/detect.py's runway_ids() enumerates - the plan's literal Task 1 acceptance criterion (sorted(d['runways']) prints exactly the three ids) would otherwise fail"
  - "runway_block()'s legacy-fallback branch returns a synthetic {runway, corridor} dict built from the flat top-level keys, so runway_axis()/corridor_params() never need a second code path for the old-shape geofence file"
  - "poll_current_aircraft()'s diagnostics dict is populated unconditionally in-place (never returned) so its default (diagnostics=None) leaves every pre-CFG-12 caller's behaviour, return value, and stderr output completely unchanged"

patterns-established:
  - "Pattern 7 (06-RESEARCH.md) RUNWAY_CONFIGS-style parameterisation, implemented per its sketch: runway_id keyword threaded through the whole geometry chain (runway_axis -> corridor_params -> along_cross_track_m/track_axis_deviation_deg -> filter_in_geofence -> select_aircraft_for_runway -> poll_current_aircraft)"

requirements-completed: [CFG-05, CFG-12]

coverage:
  - id: D1
    description: "adsb-test/runway3.json carries positive-tracking geometry (thresholds + corridor) for all three Orly runways (3, 06-24, 02-20), additive-only over the legacy flat runway/corridor blocks"
    requirement: CFG-12
    verification:
      - kind: unit
        ref: "server/test_plane_detection.py#runways['3'] duplicates the legacy runway/corridor blocks exactly (drift guard)"
        status: pass
      - kind: unit
        ref: "server/test_plane_detection.py#runway_axis: 06-24/02-20 computed bearings match their published true headings"
        status: pass
    human_judgment: false
  - id: D2
    description: "detect.py's corridor + track-alignment gate is parameterised by runway_id; select_aircraft_for_runway() positively tracks 06-24/02-20 on their own centrelines and exclusively rejects the real runway-3 fixture from 06-24's gate"
    requirement: CFG-12
    verification:
      - kind: unit
        ref: "server/test_plane_detection.py#select_aircraft_for_runway positively tracks 06-24 and 02-20 on their own centrelines"
        status: pass
      - kind: unit
        ref: "server/test_plane_detection.py#the real runway-3 fixture is excluded from runway 06-24's gate (exclusive both ways)"
        status: pass
    human_judgment: false
  - id: D3
    description: "An unrecognised or malformed runway_id degrades to the default runway's geometry via runway_block(), never raises, never widens the corridor/axis-tolerance gate (T-06-02-01)"
    requirement: CFG-12
    verification:
      - kind: unit
        ref: "server/test_plane_detection.py#runway_axis(runway_id='totally-unknown') falls back to the default runway's axis (T-06-02-01)"
        status: pass
      - kind: unit
        ref: "server/test_plane_detection.py#corridor_params(runway_id='02-20') matches the file, negative entries fall back to the default"
        status: pass
    human_judgment: false
  - id: D4
    description: "poll_current_aircraft()'s diagnostics dict makes an all-providers-failed poll distinguishable from a no-aircraft poll, without changing any pre-existing return value or stderr line"
    requirement: CFG-05
    verification:
      - kind: unit
        ref: "server/test_plane_detection.py#poll_current_aircraft diagnostics distinguishes all-providers-failed from a real selection"
        status: pass
    human_judgment: false
  - id: D5
    description: "The runway-3 default path is byte-compatible: all 28 pre-existing checks pass unmodified, select_runway3_aircraft() remains a single-delegation wrapper, detect.py stays repo-dependency-free"
    verification:
      - kind: unit
        ref: "server/test_plane_detection.py (checks 1-28, unmodified)"
        status: pass
      - kind: integration
        ref: "scripts/run-all-tests.sh (all 9 harnesses, incl. test_pipeline_e2e.py / test_poll_loop.py which exercise select_runway3_aircraft() through poll_loop.run_once())"
        status: pass
    human_judgment: false

# Metrics
duration: ~15min
completed: 2026-08-27
status: complete
---

# Phase 6 Plan 02: Runway-Parameterised Detection Summary

**Generalised `server/plane/detect.py` from a runway-3-only detector to a runway-parameterised one (D-26/D-27/D-28), byte-compatible with every existing caller, plus a diagnostics signal that makes an all-providers-failed poll observable for CFG-05's fault icon.**

## Performance

- **Duration:** ~15 min
- **Completed:** 2026-08-27
- **Tasks:** 3/3
- **Files modified:** 3

## Accomplishments

- `adsb-test/runway3.json` gained a `runways` block (ids `3`, `06-24`, `02-20`) carrying per-runway threshold and corridor geometry, additive-only over the legacy flat `runway`/`corridor` blocks, which stay byte-for-byte untouched as the historical record and legacy-fallback source.
- `server/plane/detect.py`'s whole geometry chain — `runway_axis()`, `corridor_params()`, `along_cross_track_m()`, `track_axis_deviation_deg()`, `filter_in_geofence()` — now takes a `runway_id` keyword, resolved through the new `runway_block()`/`runway_ids()` helpers. `select_runway3_aircraft()` is preserved as a single-delegation, byte-compatible wrapper around the new `select_aircraft_for_runway()`.
- `poll_current_aircraft()` gained `runway_id` and `diagnostics` keyword parameters; when `diagnostics` is a dict, it's populated with `queried`/`failed`/`selected`/`disagreement`/`runway_id`, the sole signal that distinguishes "every ADS-B source is down" from "nothing on the runway right now" (T-06-02-03) — both previously returned `None` indistinguishably.
- An unrecognised `runway_id` degrades to the default runway's geometry via `runway_block()`'s legacy-fallback branch — never raises, never widens the gate (T-06-02-01), verified by a deliberate revert-and-restore of that branch failing the guard check.
- `server/test_plane_detection.py` grew from 28 to 38 checks, all 28 originals unmodified: positive tracking on 06-24/02-20 (synthetic records derived arithmetically from `runway3.json`'s own thresholds, no new coordinate literals), reverse-exclusivity of the real runway-3 fixture from 06-24's gate, the unknown-id fallback, and the diagnostics signal.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add a `runways` block to adsb-test/runway3.json covering all three Orly runways** - `2adc9ee` (feat)
2. **Task 2: Parameterise detect.py by runway id, keep the runway-3 entry point unchanged, and expose an all-providers-failed signal** - `0c685d8` (feat)
3. **Task 3: Extend server/test_plane_detection.py with positive-tracking checks for all three runways** - `c93cb98` (test)

**Plan metadata:** commit pending (this file + STATE.md/ROADMAP.md/REQUIREMENTS.md update)

## Files Created/Modified

- `adsb-test/runway3.json` - new additive `runways` block (ids `3`/`06-24`/`02-20`) and sibling `runways_source` provenance note; legacy `runway`/`corridor`/`bbox` blocks untouched
- `server/plane/detect.py` - `DEFAULT_RUNWAY_ID`, `runway_ids()`, `_effective_runway_id()`, `runway_block()` added; `runway_id` keyword threaded through the geometry chain; `select_aircraft_for_runway()` added, `select_runway3_aircraft()` reduced to a thin wrapper; `poll_current_aircraft()` gained `runway_id`/`diagnostics`; `--runway` CLI flag added, validated in `main()`
- `server/test_plane_detection.py` - 10 new checks (29-38, `EXPECTED_CHECK_COUNT` 28 -> 38)

## Decisions Made

- `runways_source` kept as a sibling key of `runways` rather than nested inside it, so `runways` stays exactly the three runway-id keys `runway_ids()` enumerates — required by Task 1's literal acceptance criterion (`sorted(d['runways'])` prints exactly the three ids) and by `runway_ids()`'s own "return the runways dict's keys" contract; a `source` key living alongside the ids would otherwise be misread as a fourth runway id everywhere `runway_ids()` is consulted (CLI validation, plan 06-10's harness, `runway_block()`'s membership check).
- `runway_block()`'s legacy-fallback branch returns a synthetic `{runway, corridor}` dict built from the flat top-level keys rather than special-casing "old-shape geofence" throughout the module — every downstream function (`runway_axis()`, `corridor_params()`) only ever needs to handle one block shape.
- `poll_current_aircraft()`'s `diagnostics` dict is populated strictly in-place and only when a dict is passed; the default (`diagnostics=None`) is a complete no-op on the function's existing return value and stderr output, so no pre-CFG-12 caller (including `poll_loop.py`, unchanged by this plan) observes any behaviour change.

## Deviations from Plan

None - plan executed exactly as written. The `runways_source` placement (documented above under Decisions Made) is a resolution of an internal tension in the plan's own text (Task 1's action prose said "on the new runways object" while its acceptance criteria required `runways` to contain exactly the three ids) rather than a deviation from the plan's actual intent — the acceptance criteria's literal, mechanically-checked wording took precedence.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- The `runway_ids()`/`geofence['runways']` key set (`3`, `06-24`, `02-20`) is now available for plan 06-10's harness to assert against `device_config.RUNWAYS`.
- `poll_current_aircraft(diagnostics=...)` is ready for `poll_loop.py` (a future plan, not this one) to wire into CFG-05's fault icon.
- `select_aircraft_for_runway(runway_id=...)` is ready for `poll_loop.py` to thread `device_config.json`'s `tracked_runway` setting through, once that wiring plan runs.
- **Carried-forward open item (06-RESEARCH.md Assumption A1, not closed by this plan):** the 06-24 and 02-20 corridor thresholds are copied placeholders from runway 3's measured derivation, explicitly documented as such in `runway3.json` itself (`corridor.threshold_status`) and in `detect.py`'s docstrings. Plan 06-12 is the live-capture pass that confirms or replaces them - this plan deliberately does not attempt that validation.
- `render.py`'s `TOP_RIGHT_TAG_TEXT` runway-label constant (noted in 06-RESEARCH.md Pattern 7 as "a small, additional, currently-unlisted code touch") is out of this plan's `files_modified` scope and remains for whichever later plan wires runway selection into the render path.

---

*Phase: 06-companion-configuration-web-interface-visual-settings-view-s*
*Completed: 2026-08-27*

## Self-Check: PASSED
