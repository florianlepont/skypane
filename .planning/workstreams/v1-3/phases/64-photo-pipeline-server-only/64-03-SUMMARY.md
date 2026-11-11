---
phase: 64-photo-pipeline-server-only
plan: 03
subsystem: photo
tags: [trial, skin-tone, cli, docs]
requires: ["64-02"]
provides:
  - "server.photo.trial: run_grid, render_file, check_out_dir, param_sets, measures, contact sheets"
  - "python -m server.photo (--in FILE | --synthetic) --out DIR"
  - "docs/PHOTO-RENDERING.md skeleton (parameters NOT FROZEN)"
affects: [64-04, 64-05]
key-files:
  created:
    - server/photo/trial.py
    - server/photo/__main__.py
    - server/test_photo_trial.py
    - docs/PHOTO-RENDERING.md
  modified:
    - test-support/photo_scenes.py
    - pyproject.toml
key-decisions:
  - "Scene builders live in server/photo/trial.py; test-support re-exports them"
  - "Output directories inside the repo root are refused with ValueError; default output is mkdtemp"
requirements-completed: [PHOTO-04]
duration: 25min
completed: 2026-11-10
---

# Phase 64 Plan 03: Skin-tone trial tooling Summary

A repeatable skin-tone trial: a procedural tone I-VI grid (full-range and dull scenes, both panels, fill and bands, one-factor-at-a-time parameter variations) yields one contact sheet per tone plus a table of measures, and `python -m server.photo --in FILE` previews an owner file through the real normaliser, writing only outside the repository.

## Tasks

1. Trial library, measures, contact sheets, builder move - commit d7a2080
2. CLI, docs skeleton, mypy registration - see git log (`feat(64-03): add photo trial CLI...`)

## Verification

- `pytest server/test_photo_trial.py` 10 passed; with photo prep/render/boundaries/normalize tests: 116 passed
- `python -m server.photo --synthetic --out $(mktemp -d)` exits 0 and prints the table and six sheet paths (about 50 s for the full 384-render grid)
- ruff clean, mypy clean (50 files), function-size gate (1112 functions, none over 80), comment-history gate rc=0
- `git diff` on server/fixtures/golden, server/plane, server/panel_format.py, hardware, firmware: empty

## Deviations from Plan

- Param sets: strength 0.8 equals the default, so duplicates are dropped; the grid uses 8 sets (default, sat 1.0/1.15/1.3, str 0.5/1.0, cut 0.5/2.0). Saturation 1.3 sits at the validator ceiling.
- Task 1's commit holds the library and builder move; the test file (which also covers the CLI) was committed with Task 2 because it imports `__main__`.
- Tests were written together with the implementation, not red-first.
- `render_file` lets `PhotoRejected` propagate (it carries `reason`); the CLI turns it into one line `rejected: <reason>` with exit 2.

## Issues for the caller

- `gsd-sdk state.advance-plan` known parse failure: not attempted by hand; STATE.md/ROADMAP.md untouched per instructions.

## Known Stubs

None. The parameter table in docs is intentionally marked NOT FROZEN; Results/verdict/limits headings are empty until the review is done.

## Threat Flags

None. T-64-12 (repo-internal output refused, temp default, tests under tmp_path), T-64-13 (sanitised stem plus fixed suffix) covered by tests.

## Self-Check: PASSED
