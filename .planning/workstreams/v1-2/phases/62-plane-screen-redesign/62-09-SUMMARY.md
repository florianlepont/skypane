---
phase: 62-plane-screen-redesign
plan: 09
subsystem: firmware-masks
tags: [firmware, ink-masks, no-connection, updating]
requires: [62-08]
provides:
  - "fault_screen_mask.h and updating_screen_mask.h regenerated from giant.status build_status(flat=True)"
key-files:
  modified:
    - firmware/tools/gen_fault_screen.py
    - firmware/main/fault_screen_mask.h
    - firmware/main/updating_screen_mask.h
    - firmware/tests/test_fault_screen.c
    - server/test_fault_screen_mask.py
    - server/test_updating_screen_mask.py
requirements-completed: [PSR-07]
completed: 2026-11-09
---

# Phase 62 Plan 09: Firmware ink masks from the calm layout Summary

Both hold-screen masks (no connection, updating) are cut from the calm status canvases at 1200x1600 (flat, two colours). The generator, headers, drift tests and the fault host test are consistent; nothing else in firmware/ changed and nothing was built, signed, tagged or pushed.

## Tasks

| Task | Commit | Result |
|------|--------|--------|
| 1 Repoint generator, regenerate headers | 91e4723 | `_SCREENS` flat and preview builders now call `giant.status.build_status`; legacy `_build_*_canvas` untouched; two-colour assertions added to both mask tests |
| 2 Host tests | c5a6b9d | dither-field rows moved below the mask box; new golden digest 0x507fb0b85c6e7b20 |

## Mask sizes and flash budget

- Bounding box for both masks: x=110, y=120, w=978, h=1275, stride 123, **156,825 bytes of bits each** (313,650 total). Previously 564x340 (24,140 B) and 666x340 (28,560 B): 52,700 B total.
- Flash growth: **+260,950 B (about 255 KB)**.
- Committed header text: 833,826 B and 833,872 B (was 128,919 and 152,445).
- OTA slot (partitions.csv): 0x250000 = 2,424,832 B. A 10% margin needs the baseline app plus growth to stay under 2,182,349 B, i.e. a current app of at most about 1,921,399 B.
- **The current app size could not be measured:** no build output exists in the repo and the Docker daemon is unavailable, and building was out of scope. No size is recorded in earlier summaries. The growth alone is 10.8% of the slot, so the 10% margin check is not provable here. A flightportrait-class ESP32-S3 image is expected to be well under 1.9 MB, but this is an assumption. **CI must still run the `firmware.yml` build and `check_production_config.sh built`, and the owner should read the resulting image size before the next release (Phase 57).** If it is tight, the fallbacks are a smaller body text or icon (single rectangle must stay).

## Deviations from Plan

**1. [Rule 3 - Blocking] Generator plausibility guard raised.** `gen_fault_screen.py` refused any bbox over 100 KB of bits; the calm layout needs 156,825 B. The guard is now 200 KB (still a tripwire against a bloated canvas).

**2. Preview builders also repointed** to the calm canvases so the side-by-side preview matches the masks. The generator docstring and the mask-test docstrings were updated; `test_updating_screen.c` needed no change (passes as is).

## Verification

- Drift tests, `test_golden_render.py`, `test_render.py`: 175 passed. Two-colour assertions green.
- `firmware/tests/run_host_tests.sh`: all 15 suites pass (gcc available), including panel diff.
- ruff, function-size gate (1059 functions, none over 80), comment-history guard: clean. mypy list unaffected (no listed module changed).
- Files changed in firmware/: only the two headers, `tools/gen_fault_screen.py` and `tests/test_fault_screen.c`. No golden fixtures, Phase 47/47.1, hardware/, signing, workflow, tag or version changed.
- Mask drift depends on the Pillow/libraqm text rendering of the CI environment; CI is the final check.

## Known Stubs

None.

## Self-Check: PASSED

Commits 91e4723 and c5a6b9d present; changed files listed above exist.
