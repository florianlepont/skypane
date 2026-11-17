# 58-05 Task 1 Summary: evaluation unit profile behind the gate, BYOS path proven

Scope: server side only (Task 1 of 58-05). No firmware, no hardware/ file, no flash, no deploy, no push.

## What changed
- `server/hardware.py`: `EVALUATION_KEY = "seeed-ee04-7in3-spectra6"`; new `HardwareProfile.gated` field (default False); `available_types` shows a profile when `SKYPANE_SIM_HARDWARE == "1"` or when it is neither simulated nor gated; new `_EVALUATION` profile (landscape 800x480, `max_image_bytes` 192000, `simulated=False`, `gated=True`, battery values copied from legacy, every provenance entry provisional with source "copied from the legacy profile until the evaluation unit is measured; not a measurement"); `PLANNED_BATTERY_SLOTS` keyed by the constant, note text updated, values still None.
- `server/test_hardware.py`: gate-off exclusion asserted in the other-values test, the production-config test and a dedicated test; geometry/firmware, battery provenance, `registry_problems() == []`, and the slot/registry consistency rule (replaces the old "slot not in REGISTRY" assertion).
- `test-support/skypane_two_device_fleet.py`: `seed_two_device_fleet(..., landscape_type=SIM_LANDSCAPE_KEY)`.
- `stub-server/test_evaluation_unit_image.py` (new): real BYOS subprocess; the unit gets a 192000-byte body equal to its panel file with `image_hash == sha256(body)`, the legacy frame's hash and 960000-byte body are unchanged and byte-identical to its panel file; with `SKYPANE_SIM_HARDWARE=0` the unit gets 503 without `image_url` and the legacy frame still gets 200.
- `byos_server.py`, `poll_cycle.py`, everything under `hardware/` and firmware untouched.

## Evidence
- Red first: 12 failed, 2 errors before the implementation.
- Plan verify subset (`test_hardware`, `test_evaluation_unit_image`, `test_device_fleet`, `test_phase47_freeze`, `-n 0`): 91 passed.
- Gate-on whole suite (`SKYPANE_SIM_HARDWARE=1 ... server stub-server companion -n auto`): 10807 passed, 3649 skipped (Chromium not installed here, root-permission skips). No test hard-coded the type list beyond the ones edited above.
- Gate-off whole suite (same command, variable unset): 10807 passed, 3649 skipped (identical count and timing to the gate-on line in the captured output; the tests that need the gate set it themselves, but treat the identical timing with some caution).
- ruff on changed files: all checks passed. mypy: no issues in 45 source files. `check_function_size.py check --max 80 server stub-server`: none over 80. `check_comment_history.py check`: rc 0.

## Deviations
None. (Plan's coverage-gated `./scripts/run-all-tests.sh` was replaced by the equivalent pytest command from the task brief, `--no-cov`.)

## Unresolved
- Playwright browser tests are skipped in this sandbox (no Chromium); unrelated to this change.
