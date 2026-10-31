---
phase: 53-detection-modes-airport-runway-and-position-radius
plan: 02
subsystem: detection
tags: [runway-mode, geofence-document, replay, sweep]
requires: [53-01]
provides:
  - server/detection.py (DetectionSpec, spec_for, runway_geofence_doc, legacy_orly_spec, LEGACY_RUNWAY_MAP, LEGACY_GEOFENCE_ENV, tag_text, empty_heading)
  - test-support/detection_sweep.py (deterministic sweep_cells, compare, compare_selections)
affects: [53-05]
key-files:
  created:
    - server/detection.py
    - server/test_detection_spec.py
    - server/test_orly_replay.py
    - test-support/detection_sweep.py
  modified:
    - pyproject.toml
key-decisions:
  - "Legacy ids carry the frozen bbox, centre, radius and ceiling; the replay proves identity, so LEGACY_ORLY_DEFAULT_TO_FILE stays False."
  - "A catalogue selection of LFPO 07/25, 06/24 or 02/20 resolves to the legacy id (one representation, same zone key)."
requirements-completed: [DET-01, DET-02]
completed: 2026-10-31
---

# Phase 53 Plan 02: Runway-mode detection spec and Orly replay proof Summary

`server/detection.py` turns a device config into a zone plus a geofence-shaped document consumed unchanged by `detect.py`; the Orly ids are proven decision-identical to the hand-tuned geofence over fixtures and a deterministic edge-band sweep.

## Commits

- cdb8967 feat: runway-mode detection spec with frozen Orly override
- 1ffd327 test: replay proof, sweep, drift, zone, kill switch, parallel isolation

## Replay result

No differing decision. Cells swept per id: 238,248 (id 3), 240,840 (06-24), 230,472 (02-20), a 40 x 70 lattice over the generic corridor bbox plus 0.001 degrees, crossed with 6 tracks and 6 altitudes, plus bands at cross-track 499/500/501 and 74/75/76 m, along-track -2501..-2499, length+2499..+2501 and the pavement margins, corridor tips, and both bboxes' edges (plus or minus 1e-5 degrees). Candidate sets with full tagged geometry and normalised selections (all keys but seen_pos; single-provider and two-provider in both orders) are equal. Fixture records (14 plus 3 track points, pavement pair in both orders) are equal. The evidence test shows the unclipped generic bbox does change at least one decision, justifying the override. Fallback constant `LEGACY_ORLY_DEFAULT_TO_FILE` remains False.

## Verification

- `pytest server/test_orly_replay.py server/test_detection_spec.py server/test_plane_detection.py stub-server/test_phase47_freeze.py`: 143 passed (replay about 16 s).
- ruff clean, mypy clean (28 files, includes `server/detection.py`), function-size gate passes, comment-history check passes.
- Parallel isolation tested for LFPG 08L/26R vs 08R/26L, 09L/27R vs 09R/27L, LFMN 04L/22R vs 04R/22L, LFBO 14L/32R vs 14R/32L; two devices share one zone and select their own runway.

## Deviations from Plan

None. Notes: `spec_for` reports `fail_safe` True for an unknown non-empty `tracked_runway` string as well as for bad `detection` objects; a position-mode object takes the fail-safe path until the position plan adds it. `detection` is in both the mypy files list and the strict override list.

## Known Stubs

None.

## Self-Check: PASSED
