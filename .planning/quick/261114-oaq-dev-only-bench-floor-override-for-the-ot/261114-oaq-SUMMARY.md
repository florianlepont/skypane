---
quick_id: 261114-oaq
status: complete
---
# Summary

- `build.sh`: `SKYPANE_BENCH_FLOOR` (dev only). A second-profile dev build with `SKYPANE_BENCH_FLOOR=fw-v1.0.8` generates `CONFIG_SKYPANE_OTA_FLOOR_VERSION="fw-v1.0.8"`; a build without it keeps the committed floor.
- `check_bench_floor_option.sh`: refuses the production profile, the default profile, a malformed version and a version with a suffix, each with exit 2 naming the variable. Checked against the previous `build.sh`, which does not exit 2 for these, so the check is not vacuous.
- 20 hardware-free firmware suites plus the new check, the production static check and the comment-history guard pass. Only shell scripts changed, so no firmware source and no legacy production image is affected.
