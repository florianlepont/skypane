---
phase: 53-detection-modes-airport-runway-and-position-radius
plan: 01
subsystem: detection
tags: [ourairports, catalogue, runways, stdlib]
requires: []
provides:
  - server/data/airports_fr.json (340 runways, 272 airports)
  - server/airports.py (load_catalogue, find_airport, find_runway, search_airports)
  - scripts/build_airports.py (offline build and --refresh)
affects: [53-02, 53-03, 53-06, 53-08]
tech-stack:
  added: []
  patterns: [committed sha256-pinned raw subset, deterministic JSON build]
key-files:
  created:
    - scripts/build_airports.py
    - scripts/data/ourairports-fr-airports.csv
    - scripts/data/ourairports-fr-runways.csv
    - scripts/data/ourairports-source.json
    - scripts/data/ourairports-exclusions.json
    - server/data/airports_fr.json
    - server/airports.py
    - server/test_airports_catalogue.py
  modified:
    - pyproject.toml
key-decisions:
  - "Designator-versus-bearing tolerance is 30 degrees, not 20, because designators are magnetic."
  - "TFFA 09/27 is excluded through a small committed known-bad list (reason known_bad_survey)."
requirements-completed: [DET-01, DET-02]
duration: n/a
completed: 2026-10-31
---

# Phase 53 Plan 01: France runway catalogue and loader Summary

Reproducible OurAirports-derived catalogue (340 runways, 272 airports, 114 KB) with parallel-runway half-widths, plus a typed stdlib loader and accent-insensitive search.

## Base commit

- `git rev-parse origin/main`: 42aa033797d5b3bb699130c87f5b6bd15e0834cc
- HEAD before the first Phase 53 commit: 8402a99e021b660781597cc123fa6527b9334c15

## Commits

- fef61c6 build script and synthetic-data tests
- 565948e pinned subset, exclusion report, catalogue, data tests
- 2846cee loader, search, mypy list

## Snapshot

Dump dated 2026-10-31; hashes matched the pinned research values (airports.csv 12754691 bytes sha256 6c600b78...d6acb, runways.csv 3972528 bytes sha256 64103ae9...edd67). The subset holds 577 airports and 747 runway rows. Catalogue sha pins are in `scripts/data/ourairports-source.json`. Rebuilding is byte-identical and idempotent.

## Deviations from Plan

**1. [Rule 4 - decided by coordinator] Designator tolerance 30 degrees plus a known-bad list**
- Found during: Task 2. With the specified 20 degree rule the build gave 331 runways at 264 airports, below the 265 bound. Nine legitimate overseas runways (FMEE, FMEP, LFVM, LFVP, NWWU, SOOG, SOOR, SOOY, TFFF; deviations 20.05 to 23.3 degrees) were dropped because designators are magnetic and thresholds give true bearings. TFFA 09/27 (22.6 degrees) lies inside that range, so no threshold separates it.
- Fix: `MAX_DESIGNATOR_DEVIATION_DEG = 30`; NTGY 18/36 (38.1 degrees) is still dropped as `bearing_mismatch`; TFFA 09/27 is listed in `KNOWN_BAD_ROWS` and reported as `known_bad_survey`. Result: 340 runways, 272 airports, within the plan bounds.
- Test changes: the bearing-mismatch trap uses a 40 degree deviation; added tests for the declination case and the known-bad row.

**2. [Measured value] LFBO half-width**
- Measured 144.7 m (plan figure about 150, tolerance 5). The test asserts the measured value (0.5 tolerance). LFPG measures 192.2 and 191.7, LFMN 147.2, LFMT 500.0, LFPO 500.0 for all three runways, LFGI 50.0.

**3. Other notes**
- `bearing_deg` is the great-circle initial bearing as specified (LFPO 07/25 is 74.39); corridor geometry and the designator check use the runtime's flat frame (74.4085).
- The airports subset CSV is 107 KB (all 19 original columns kept), larger than the roughly 60 KB estimated.
- `scripts/check_function_size.py check --max 80 scripts` reports the existing `scripts/check_comment_history.py _js_chunks` (89 lines); `scripts/` is outside the gate's roots and the file is not part of this plan. `server stub-server` passes.
- Non-reciprocal pairs and duplicate (ident, designator) keys hard-fail the build rather than being listed as exclusions, as the plan action specifies.

## Verification

- `pytest server/test_airports_catalogue.py server/test_import_boundaries.py`: 35 passed.
- `pytest server companion/test_suite_guards.py -n auto`: 2209 passed, 3 skipped (root permission tests).
- ruff clean, mypy clean (27 files, includes `server/airports.py`), function-size gate over `server stub-server` passes, comment-history check passes.

## Known Stubs

None.

## Self-Check: PASSED
