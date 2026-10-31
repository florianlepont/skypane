---
phase: 53-detection-modes-airport-runway-and-position-radius
verified: 2026-10-31T00:00:00Z
status: human_needed
score: 3/3 success criteria, 3/3 requirements, all owner constraints verified in code; owner-only checks remain
branch: milestone/v1.2-phase-53-detection-modes (HEAD 5d8d7d85, includes merge 2980cbea of main 9b9dc101)
gaps: []
human_verification:
  - test: "Physical Spectra 6 panel: NEARBY and runway tags, 'SET A LOCATION' screen, CDG-style tag text"
    expected: "Readable, no clipping, correct colours"
    why_human: "Visual appearance on e-ink hardware"
  - test: "Policy numbers: 50 m corridor floor, 5 degree parallel threshold, France bounding box (lat 41.30..51.15, lon -5.20..9.60), radius 4..28 km, 10,000 ft ceiling"
    expected: "Owner accepts them (box admits Geneva/Brussels by decision D-26)"
    why_human: "Product policy"
  - test: "Real tenant: set a non-Orly runway and a position on a real paired device, wait for a poll"
    expected: "Device follows it; adsb.fi budget stays within 1 req/s"
    why_human: "Real data, real tenant, no deploy performed"
  - test: "Decide when to deploy and whether to flip SKYPANE_LEGACY_ORLY_GEOFENCE for the live Orly frame"
    expected: "Owner decision"
    why_human: "Deploy is out of scope (D-03, D-09)"
---

# Phase 53 Verification: Detection Modes (airport/runway and position/radius)

**Goal:** a device can follow traffic on any French runway, or any aircraft around a chosen position, in addition to the Orly runway 3 behaviour (DET-01, DET-02, DET-03).

**Verdict:** the goal is achieved in code. No gap found. Status is `human_needed` only because of the owner-only items above (physical panel, policy numbers, real tenant).

## Commands run (this session)

| Check | Command | Result |
|---|---|---|
| Full suite incl. browser tests | `PLAYWRIGHT_BROWSERS_PATH=<scratch>/pw server/.venv/bin/python3 -m pytest -n auto -q --no-cov server stub-server companion test-support` | 7737 passed, 7 skipped (all skips are "root ignores permission bits") |
| Phase 47 freeze | `pytest stub-server/test_phase47_freeze.py` | 21 passed |
| Comment-history gate | `scripts/check_comment_history.py check` | exit 0 |
| Function-size gate | `scripts/check_function_size.py check --max 80 server stub-server` | 916 functions, none over 80 |
| ruff / mypy | `ruff check .`, `mypy` | all checks passed / no issues in 28 files |
| Catalogue reproducible | `scripts/build_airports.py --catalogue T/cat.json --exclusions T/excl.json`, then `cmp` | byte-identical to `server/data/airports_fr.json` and `scripts/data/ourairports-exclusions.json`; git tree clean afterwards |

## Success criteria

| # | Criterion | Status | Evidence |
|---|---|---|---|
| 1 | Owner picks airport and runway from the committed France catalogue (real designators, rows without both thresholds absent); device follows it | VERIFIED | `server/data/airports_fr.json` has 272 airports with real designators (e.g. LFPO "02/20", "06/24", "07/25"; every runway has two thresholds). `scripts/build_airports.py` drops rows without both thresholds into the exclusions report, and the rebuild is byte-identical. `server/detection.py:407` `spec_for` -> `_catalogue_spec:387` -> `runway_geofence_doc:138`. `apply_runway_selection:459` persists the choice. `/detection` route in `companion/routes.py:150,220`. `server/test_airports_catalogue.py`, `companion/test_detection_page.py`, `companion/test_browser_detection.py` pass. |
| 2 | Recorded Orly traffic through the new runway logic gives the same decisions as the runway-3 geofence; at least one parallel-runway airport tested | VERIFIED | `server/test_orly_replay.py`: strict-equality replay of the committed `geofence_*.json` and `track_arrival_440cb1` fixtures for ids 3, 06-24 and 02-20 (:66, :81), a swept grid with dense bands at every gate edge (:101-:128), zone-key equality (:169), kill-switch replay (:177). The generic bbox is shown to differ at the corridor tips, so D-20 pins the frozen legacy bbox (`detection.py:47-58`). Parallel runways: LFPG 08L/08R and 09L/09R, LFMN 04L/04R, LFBO 14L/14R, plus the lone-runway case (`test_orly_replay.py:205-233`). All pass. |
| 3 | Device set to a position and radius inside France shows aircraft around it; radius and country bounds enforced; coordinates sent to third parties rounded | VERIFIED | `detection.py:210` `validate_position` (radius 4..28 km int, finite coordinates, France box via `inside_france:194` on rounded values). `position_zone:227` rounds to 2 decimals before `Zone` exists, so provider URLs carry only rounded values. `server/test_position_rounding.py` URL-guards the provider URLs and the adsbdb URL, and checks that two devices share one zone. `companion/test_detection_position.py` covers the page and server-side rejection, including a stored location outside France. D-28: a position device without a usable location joins no zone and shows "SET A LOCATION" (`detection.py:265`), it does not fall back to Orly. |

## Requirements

| Req | Status | Evidence |
|---|---|---|
| DET-01 (airport/runway from the catalogue) | SATISFIED | Criterion 1 |
| DET-02 (Orly parity, parallel runways) | SATISFIED | Criterion 2 |
| DET-03 (position/radius, bounds, rounding) | SATISFIED | Criterion 3 |

## Owner constraints

| Constraint | Status | Evidence |
|---|---|---|
| `test_phase47_freeze.py` unmodified and green | OK | 21 passed. `git diff 9b9dc101 HEAD -- stub-server` is empty. |
| Nothing changed under hardware/, deploy/, stub-server/, Phase 47 files | OK | `git diff <main 9b9dc101> HEAD --stat -- hardware deploy stub-server` is empty. `deploy/README.md` (+50 lines) differs only against the older merge-base and comes from the Phase 55 commit on main. |
| Requirements files unchanged | OK | No diff of `*requirements*` against main. Python code uses stdlib only for the new modules. |
| Live Orly frame identical between generic and kill-switch paths | OK | `server/test_detection_kill_switch.py:156`, `test_orly_replay.py:177`. Default `LEGACY_ORLY_DEFAULT_TO_FILE = False`, env `SKYPANE_LEGACY_ORLY_GEOFENCE=1` reverts (`detection.py:36-40,372`). |
| Expand-only storage | OK | `apply_runway_selection:459` writes only `tracked_runway` for legacy ids and clears `detection`. Other runways write one `detection` object and leave `tracked_runway`. `test_detection_kill_switch.py:189` (config bytes unchanged) passes. |
| No deploy performed | OK | No deploy workflow or unit changes in the diff. |
| Phase 55 files not edited | OK | `companion/console_*.py`, `companion/pages/locations_page.py`, `test_console_*` show no diff against merged main. |
| Gates | OK | Comment-history and function-size pass (above). |
| OurAirports on credits page and COMPLIANCE.md | OK | `companion/credits.json:38-40`, `COMPLIANCE.md:179-203` (build-time only). `companion/test_compliance_credits.py` passes. |
| Catalogue never fetched at runtime | OK | No `requests`, `urllib`, `socket` or URL in `server/airports.py` or `server/detection.py` (grep empty). `build_airports.py` never downloads: `--refresh DIR` reads a caller-supplied directory. |

## UI-SPEC and access matrix cross-check

- No "nm" text on the page in EN or FR (`test_detection_page.py:448`, `test_detection_position.py:445`). The form field is `radius_km` and the radius is in km.
- No `required` on the panel controls: `test_detection_position.py:280` strips the location-form disclosure and asserts no `required` remains. The only `required` attributes are on the location create/edit fields in `detection_page.py:701`, which UI-SPEC lines 213-214 specify. The form is `novalidate`, and the hidden-panel browser tests (`test_browser_detection.py:118,139`) pass.
- French page and runway cards: `test_detection_page.py:425,436`, `test_detection_position.py:453`. Mode segments wrap without clipping in FR (`test_browser_detection.py:230`).
- Access: `GET` and `POST /detection` are `OWNER_DEVICE` (`companion/test_access_matrix.py:67,81`). Another user's device, an unknown id or a malformed id returns 404 on GET and POST with nothing written (`test_detection_page.py:396,409`). Location owner scope returns 404 for others (`test_detection_position.py:378`). Matrix rows are in `test-support/matrix_rows_*.py`.

## Deviations from the plans (recorded in CONTEXT)

- D-18: corridor half-width floor of 50 m instead of the literal D-07 formula. `ground_half_width = min(75, half_width)`. Designators ending in G or H are excluded.
- D-19: the Display page Runway card is removed for every device, including Orly.
- D-20: legacy ids keep the frozen hand-tuned bbox, centre, radius and ceiling in the generic logic, because the pure generic bbox differs at the corridor tips (13,232 of 963,603 swept cells).
- D-24: radius entered in whole km (4 to 28), converted to NM server side. This amends the D-11 wording (2 to 15 NM).
- D-28: a position device without a usable location gets a dedicated "Set a location" screen rather than a fallback to Orly (review MD-01 fix).
- D-17 and D-25: minimal location create and edit added to the detection page, with admin scope for the device owner.

## Residual risks

- The France box is coarse. Geneva and Brussels pass (D-26, accepted).
- A catalogue warning remains at rebuild: NTGV 01/19 stated heading 197 disagrees with its thresholds. It is non-blocking, and the geometry comes from the thresholds.
- Review LW-01 (dead `fail_safe` field), LW-03 (mid-cycle config change can pair a device with another zone's fetch), LW-04 (an admin can attach user A's location to user B's device) and LW-06 (POST relies on SameSite and Origin only) were reported as low. I did not re-verify whether they were fixed. MD-01, MD-02, LW-02, LW-05 and LW-07 are marked fixed.
- Replay parity is proven against the committed fixtures and a synthetic sweep, not against live traffic. The kill switch is the rollback.
- The suite ran with `--no-cov`, so the coverage floor was not re-measured.
- 7 tests skip under root (permission bits), so they were not exercised here.
- The local `main` ref is stale relative to the merged main (9b9dc101). Use that SHA as the comparison base.
