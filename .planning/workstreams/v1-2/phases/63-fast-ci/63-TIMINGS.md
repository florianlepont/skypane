# Phase 63: Fast CI - Timings

Measured with `scripts/ci_run_timing.py` (REST API only). All numbers are
wall-clock seconds unless stated.

## Baseline (before any change)

Run 42770577886 (pull request, 2026-11-10, unsplit workflow, one test job).
The runner uses 4 xdist workers (`created: 4/4 workers`).

| Step | Seconds |
|---|---|
| Check out repository | 4 |
| Set up Python | 4 |
| Create virtualenv and install dependencies (hash-enforced) | 9 |
| Cache Playwright browsers | 3 |
| Download the Chromium headless shell | 25 |
| Lint, comment-history guard, mypy, function-size gate, shellcheck, systemd scoring | 7 together |
| Run full test suite with coverage threshold | 1588 (26 min 28 s) |
| Check vendored-asset attribution completeness | 1 |
| **Job total** | **1647 (27.4 min)** |

Pytest summary line, verbatim:

```
12821 passed, 182 warnings in 1585.99s (0:26:25)
```

- Executed tests: 12,821 passed, 0 skipped, 0 failed, 0 deselected.
- Coverage: `TOTAL 24691 931 96%`; `Required test coverage of 93.0% reached. Total coverage: 96.23%`.

Slowest tests in that run (`--durations=15`), seconds:

| s | Test |
|---|---|
| 52.81 | deploy/tests/test_release_manifest.py::test_image_at_the_bound_passes_and_one_byte_over_fails[2424833-2] |
| 50.13 | server/test_firmware_registry.py::test_legacy_size_bound_is_unchanged |
| 47.42 | server/test_firmware_image.py::test_size_bound_defaults_to_the_ota_slot_not_the_display_bound |
| 39.02 | companion/test_browser_airline_table.py::test_the_menu_deletes_an_uploaded_artwork_and_stars_the_default_type[chromium] |
| 27.93 | companion/test_browser_airline_table.py::test_a_type_row_is_customised_then_deleted_back_to_the_default[chromium-360] |
| 27.36 | companion/test_browser_airline_table.py::test_a_type_row_is_customised_then_deleted_back_to_the_default[chromium-1280] |
| 26.33 | companion/test_browser_airline_table.py::test_renaming_saves_on_change_and_the_menu_resets_it[chromium] |
| 23.41 | companion/test_browser_ux_04.py::test_a_row_expands_to_its_types_and_each_type_has_its_own_replace[chromium] |
| 15.89 | companion/test_browser_personalisation.py::test_the_floating_save_bar_saves_the_look[chromium] |

The executed count matches the 12,821 floor in the phase context.

## Analysis-machine measurements (4 cores, same count of workers as CI)

- Whole suite on that machine: 10,855 passed, 8 skipped, 2,713 errors in 9 min 40 s;
  the errors are the browser tests, which could not launch the Chromium build
  installed there (version mismatch). The 8 skips were not investigated.
- Browser tests alone: 2,825 passed in 17 min 47 s.
- xdist scaling on a 3,757-test subset: 478 s (1 worker), 244 s (2), 134 s (4),
  120 s (8). Coverage overhead: 134 s without, 136 s with (server tests);
  63 s without, 71 s with (88 browser tests).
