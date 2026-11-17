---
phase: 57-combined-legacy-frame-firmware-release
plan: 05
subsystem: firmware-release
tags: [bench, checklist, ota]
requires: [57-03]
provides: [57-BENCH-CHECKLIST.md]
affects: [57-06]
key-files:
  created:
    - .planning/workstreams/v1-2/phases/57-combined-legacy-frame-firmware-release/57-BENCH-CHECKLIST.md
requirements-completed: [OTA-04]
metrics:
  completed: 2026-11-14
---

# Phase 57 Plan 05: EE04 bench checklist Summary

One runnable owner checklist of nine unticked EE04 bench checkpoints (B1 to B9), with procedure, expected observation and empty result and date fields.

## What was done

- B1 references the SIGNING.md bench procedure instead of restating it; B2 covers the `SKYPANE_FAULT=nvs` and `slow_wake` rollback; B3 to B8 cover container wake, legacy fallback, hardware claim, 401 loop, sticky `imgfmt_bad` fallback, size and wake time; B9 is the owner sign-off gating `57-RELEASE-INSTRUCTIONS.md`.
- The document states that no automated agent may tick a box, names the dependency on the Phase 58 unit and an unverified EE02-image-on-EE04 question, and keeps all fault builds on the bench unit with a bench key.
- Verification: 9 lines match `^- \[ \]`, 0 ticked boxes, `scripts/check_comment_history.py check` clean.

## Deviations from Plan

The plan text says the log shows `fp_diag image fmt=container`. The as-built log line (`firmware/main/state_machine.c`) is `fp_diag image format=<container|legacy> status=<n> crc_ms=<n>`, so the checklist uses that wording. No other deviations.

## Notes

- `57-RELEASE-INSTRUCTIONS.md` is referenced by B9 and is produced by another plan; it did not exist when this was written.
- No bench result was observed; every Result field is empty.
