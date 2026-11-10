---
phase: 64-photo-pipeline-server-only
plan: 05
subsystem: photo-pipeline
tags: [photo, rendering, docs, skin-tone-review]
requires: [64-03, 64-04]
provides:
  - "Recorded skin-tone trial results, owner outcome and limits in docs/PHOTO-RENDERING.md"
affects: [docs/PHOTO-RENDERING.md, server/photo/prep.py]
key-files:
  modified:
    - docs/PHOTO-RENDERING.md
    - server/photo/prep.py
key-decisions:
  - "Defaults kept unchanged (cutoff 1.0, strength 0.8, saturation 1.2): the owner could not judge the synthetic sheets; no real faces tried"
requirements-completed: [PHOTO-04]
metrics:
  completed: 2026-11-10
---

# Phase 64 Plan 05: Record defaults and run the gate Summary

The rendering defaults are kept as they were, and the doc records honestly that the owner could not judge the synthetic contact sheets and that real faces were not tried.

## What was done

- `DEFAULT_PREP` is unchanged (1.0, 0.8, 1.2); its comment now says the defaults were kept after the review and should be revisited with real portraits. The existing pinned-literal test still spells those values.
- `docs/PHOTO-RENDERING.md`: "NOT FROZEN" replaced by "defaults kept; real faces not tried (2026-11-10)"; parameter table with ranges tried; results per tone and panel size from the measures (default parameters, fill fit, 24 rows); verdict section quoting "I don't know" and what was and was not looked at; known limits; not tried; how to re-run; follow-ups retained.
- No image was copied into the repository.

## PHOTO-04 honesty note

Satisfied as "tried on synthetic samples, result and limits recorded". It is not a judgement of how real skin renders.

## Deviations

- The owner-facing instruction said hue drift was "under 4 degrees in the grid". The measures show at most 2.8 degrees for portrait (both fits) and landscape bands, but up to 8.8 degrees for landscape fill (tones II to IV). The doc records the measured figures; the cause was not investigated.
- No source change beyond a comment, so the TDD red/green cycle did not apply.

## Gate

- `scripts/run-all-tests.sh`: 11247 passed, 2751 skipped (Chromium not installed in this environment, root ignores permission bits, one openssl case). Browser tests did not run here.
- ruff (server/photo, test-support, server/test_photo_*.py), mypy (50 files), function-size (1112 scanned, none over 80), comment-history: all pass.
- Diff since the first phase commit over server/fixtures/golden, server/plane, server/panel_format.py, hardware, firmware, root STATE.md and ROADMAP.md: empty. No image files in the diff.
- Doc checklist: all sections present; frozen values equal DEFAULT_PREP; upload limits (12 MiB, 50 MP, 200 px, 2048 px, 1,000,000 bytes) equal the constants in `server/photo/normalize.py`.

## Follow-ups (not built)

- Server-rendered preview using `preview_png`.
- Bounded concurrent normalisation, with the body byte cap applied while reading.
- JPEG/PNG/WebP-only file input accept list with a clear HEIC message.
- Try real portraits (`python -m server.photo --in`) and revisit the defaults.
- Investigate the larger landscape-fill hue drift.

## Self-Check: PASSED
