---
phase: 64-second-hardware-in-production-build-release-deploy-and-parit
plan: 03
subsystem: firmware
tags: [provision, guard, shell, hw2]
requirements: [HW2-05]
key-files:
  modified:
    - firmware/provision.sh
    - firmware/tests/run_host_tests.sh
  created:
    - firmware/tests/check_provision_guard.sh
decisions:
  - "Live-frame identity is the owner-declared SKYPANE_LIVE_FRAME_PORT / SKYPANE_LIVE_FRAME_MAC (as flash-second.sh); the typed MAC is always required outside --dry-run"
metrics:
  tasks: 2
  completed: 2026-11-14
---

# Phase 64 Plan 03: provision.sh typed live-frame guard Summary

provision.sh now refuses a declared live-frame port or MAC (exit 3) and requires the chip MAC typed back, mirroring flash-second.sh.

## Commits
- a7ac357 test(64-03): failing guard test (RED: 6 of 9 cases failed against the unmodified script)
- c081e74 feat(64-03): guard implementation (GREEN, all 9 cases pass)

## Behaviour
- Port refusal runs right after argument validation, before the Wi-Fi prompt and any esptool call.
- MAC read, printed, live-MAC refusal (case-insensitive), then typed confirmation; all before the work dir, Docker and any write.
- --dry-run applies only the live-MAC refusal; no prompt, no hardware.
- Limit documented in the script header: unset variables leave only the typed MAC; unsetting is the deliberate override.

## Verification
- check_provision_guard.sh: 9/9 PASS
- run_host_tests.sh: 22 suites pass; check_panel_diff PASS
- pytest deploy/tests/test_provision.py: 14 passed
- sh -n clean; shellcheck not installed locally (not run)

## Deviations from Plan
None. The docker stub has a "generate" mode (writes a zero-filled secret.bin) so the dry-run success case can reach exit 0, since dry-run still runs the container step.

## Self-Check: PASSED
