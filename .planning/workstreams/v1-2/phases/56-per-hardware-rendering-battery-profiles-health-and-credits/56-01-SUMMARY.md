---
phase: 56-per-hardware-rendering-battery-profiles-health-and-credits
plan: 01
subsystem: testing
tags: [golden-image, render, sha256, regression]
requires: []
provides:
  - golden SHA-256 baseline of the legacy 1200x1600 render (43 cases)
affects: [56-02, 56-03, 56-04, 56-05]
key-files:
  created:
    - server/test_golden_render.py
    - server/fixtures/golden/legacy_render_baseline.json
  modified:
    - server/fixtures/README.md
requirements-completed: [HWR-01]
completed: 2026-10-30
---

# Phase 56 Plan 01: Golden render baseline Summary

43-case SHA-256 manifest of the packed legacy panel, generated from a clean worktree of cc7c1568 (no renderer change), guarding the live frame for the rest of the phase.

## Commits
- 731f29a8 golden test module
- b2dd5be7 manifest and fixtures README
- 7efa4690 generator exposed as a function (see deviation)

## Cases
16 themes departing, 4 arriving+previous, overlays on both active states, empty (2 runways, overlays), quiet hours (3), display off (2), battery empty, long names (2), flat no-connection and updating canvases, and one run_once cycle hashing panel.bin (route resolution stubbed, log line swallowed). Manifest records pillow_version 13.0.0; every case is 960000 bytes. Generation was run twice with identical output.

## Deviations from Plan
**[Rule 3 - Blocking] __main__ entry replaced by `print_manifest()`.** `companion/test_suite_guards.py::test_no_legacy_runner_anywhere` forbids `if __name__ == "__main__"` in test modules. Regenerate with `python -c "import server.test_golden_render as g; g.print_manifest()"`; output is byte-identical to the committed manifest.

## Verification
- golden + freeze tests pass; full `./scripts/run-all-tests.sh`: 5905 passed, 566 skipped (no Chromium installed locally), 1 failed = the guard above, fixed afterwards and re-run green.
- ruff, mypy, function-size, comment-history clean.

## Self-Check: PASSED
