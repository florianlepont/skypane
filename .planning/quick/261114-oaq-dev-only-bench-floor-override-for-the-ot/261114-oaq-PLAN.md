---
quick_id: 261114-oaq
status: complete
---
# Plan

The OTA floor refusal (`fail-floor`) can only be shown on a unit whose compiled floor is above a version the server still offers. The floor is a Kconfig value, so a bench unit needs an image built with a raised one.

1. `firmware/build.sh`: a dev-only `SKYPANE_BENCH_FLOOR` writes `CONFIG_SKYPANE_OTA_FLOOR_VERSION` into a defaults fragment in the dev build directory. Refused for the production profile and for a malformed version, before any container starts.
2. `firmware/tests/check_bench_floor_option.sh` (run by `run_host_tests.sh`, so by CI): both refusals.
3. Prove the generated sdkconfig carries the value and the production configuration check still passes.
