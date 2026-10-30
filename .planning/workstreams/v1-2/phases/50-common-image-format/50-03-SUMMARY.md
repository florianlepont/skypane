---
phase: 50-common-image-format
plan: 03
subsystem: firmware
tags: [image-format, container, c-reader, host-tests]
requires: [50-02]
provides:
  - firmware/main/image_container.[ch] (imgc_parse, imgc_crc32)
  - host test over the shared golden fixtures
affects: [50-04]
key-files:
  created:
    - firmware/main/image_container.h
    - firmware/main/image_container.c
    - firmware/tests/test_image_container.c
  modified:
    - firmware/tests/run_host_tests.sh
    - firmware/VENDOR.md
requirements-completed: [IMG-03]
metrics:
  tasks: 2
  files: 5
completed: 2026-10-30
---

# Phase 50 Plan 03: C reference reader Summary

Pure-C `imgc_parse` validates a body against the panel size using 64-bit length arithmetic and agrees with the Python decoder on every shared fixture; a table-free CRC-32 matches zlib.

## Tasks and commits

1. `b69632f` feat: image_container.[ch], libc-subset only, `-Wall -Wextra -Werror -std=c11 -pedantic` clean, referenced by no production source.
2. `611c601` test: test_image_container.c, additive `FIXTURE_DIR` export in run_host_tests.sh, VENDOR.md entries.

## Deviations from Plan

None. No existing firmware source or CMakeLists.txt was edited.

## Verification

- `./firmware/tests/run_host_tests.sh`: 14 suites pass, including `test_image_container`.
- ASan+UBSan build of the new test: exit 0; with FIXTURE_DIR unset it exits 1 with a message.
- check_comment_history: clean.
- IDF build (`firmware/build.sh`): UNVERIFIED, Docker daemon unusable here; CI's firmware build job is the proof. Nothing published or flashed.

## Self-Check: PASSED
