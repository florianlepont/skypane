---
phase: 57-combined-legacy-frame-firmware-release
plan: 06
status: complete
completed: 2026-11-15
requirements: [OTA-04]
---

# Plan 57-06 summary: final regression, no-publication audit, CI compile

## What was done

- **Local audit before sending the code** (2026-11-14, branch rebased on `main`):
  working tree clean; no `fw-v*` tag newer than `fw-v1.0.4`; no change to the
  frozen files (phase 47 and 47.1 files, `hardware/`, `panel.c`, `epd13in3e.c`,
  `wake_telemetry.*`, `wake_record.*`, `test_phase47_freeze.py`,
  `measured_fields_freeze.json`); 15 hardware-free firmware suites green;
  `check_comment_history.py check` exit 0; `check_function_size.py check --max 80
  server stub-server`: 1095 functions, none over 80.
- **Owner go-ahead for the push.** The owner chose to send the code. The remote
  branch of the original name had a different, already merged history and the
  force push was refused by the permission layer, so the code went on a new
  branch and a new draft pull request (#391), as the plan's stop condition allows.
- **CI compile.** The first ESP-IDF compile of the new code failed on a swapped draw
  argument in `state_machine.c`, which host tests cannot see. Fixed in
  `9ab5428c`; `firmware.yml` then passed, including "Build EE02 firmware image"
  (https://github.com/florianlepont/skypane/actions/runs/43580601794/job/132404314410).
  Server, browser and static checks were green on the same head.
- **No publication from this plan.** The tag `fw-v1.1.0` was created and pushed
  later by the owner, on 2026-11-15, after the bench checks B1 to B9; see
  `57-VERIFICATION.md`.

## Deviations

- The plan expected the draft pull request to be reused; it had already been merged,
  so a new one was opened for the code (#391) and the owner merged it.
- The local pytest run with the coverage gate was not possible in the sandbox; CI
  ran it.

## Not done by this plan

Marking the bench checkpoints, the release and the live installation: owner
actions, recorded in `57-BENCH-CHECKLIST.md` and `57-VERIFICATION.md`.
