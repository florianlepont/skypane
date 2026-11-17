---
phase: 57-combined-legacy-frame-firmware-release
plan: 04
subsystem: docs
tags: [vendor-ledger, image-format, release-instructions]
requires: [57-01, 57-02, 57-03]
provides:
  - as-built VENDOR.md and IMAGE-FORMAT.md
  - owner release instructions (unticked preconditions)
key-files:
  created:
    - .planning/workstreams/v1-2/phases/57-combined-legacy-frame-firmware-release/57-RELEASE-INSTRUCTIONS.md
  modified:
    - firmware/VENDOR.md
    - docs/IMAGE-FORMAT.md
requirements-completed: [OTA-04]
completed: 2026-11-14
---

# Phase 57 Plan 04: Documentation and owner release instructions Summary

VENDOR.md and IMAGE-FORMAT.md now describe the image reader as linked and wired, and a single owner document gives the release procedure with every gate left unticked.

## Commits
- 737fb31e: VENDOR.md rows for the changed vendored files (api_client.c/.h, state_machine.c, nvs_schema.h, Kconfig.projbuild, sdkconfig.ee02.defaults, validate.c/.h, fault_screen.c/.h, image_container.c) plus the drift-guard script; the "not linked" wording is gone. IMAGE-FORMAT.md "Adoption notes" replaced by an as-built section (buffer 960256, SHA-256 over all bytes, sticky `imgfmt_bad`, `X-Hw-Type` rule, one extra redraw, auth/enrol screen change).
- Task 2 commit (release instructions and this summary): see git log.

## Verification
- `scripts/check_comment_history.py check`: exit 0.
- The two removed phrases no longer occur; `X-Hw-Type` and `imgfmt_bad` present.
- Instructions: 13 unticked boxes, 0 ticked, `git push origin` appears once, inside Procedure, as an owner action; fw-v1.1.0 stated as a recommendation.
- No command in the instructions was run; no tag, push, publish, schedule or merge happened.

## Deviations from Plan
- The buffer headroom is 256 bytes (960256 - 960000); an early draft said 232 and was corrected before commit.
- Commands I could not confirm from SIGNING.md, the workflows or deploy/README.md are marked as unconfirmed in the document: the exact USB flash sequence for the live frame, how late a schedule cancel still wins, the Update page button labels.

## Known Stubs
None.

## Self-Check: PASSED
