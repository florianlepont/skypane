---
phase: 64-second-hardware-in-production-build-release-deploy-and-parit
plan: 11
subsystem: docs
tags: [docs, release, signing, runbook, hw2]
requirements: [HW2-05]
key-files:
  created: [hardware/SECOND-HARDWARE-SUPPORT.md]
  modified: [deploy/README.md, firmware/SIGNING.md, firmware/VENDOR.md, README.md, deploy/tests/test_docs.py]
completed: 2026-11-14
---

# Phase 64 Plan 11: Documents for both boards Summary

The deploy README, SIGNING.md, VENDOR.md, README.md and a new second-board support guide now describe both boards, the typed release contract, and an owner-only lift runbook; no document claims a typed release is published or the switch lifted.

## Commits
- 8433b88 docs: typed release layout, switch forwarding, skip notice, lift runbook (owner only, written confirmation, hand edit of /opt/skypane/skypane.env, restart, then workflow_dispatch of ci.yml so earlier typed releases are imported), per-type signing section; 4 doc-claim tests added first (RED 4 failed) then green.
- 8499b31 docs: VENDOR.md panel drivers and panel-diff pins, README second-board section, hardware/SECOND-HARDWARE-SUPPORT.md (build and size gate, guarded flash and provisioning with the declared-port/MAC limit and unsetting as the deliberate override, enrolment, OTA, measured-versus-provisional table).

## Tests
- deploy/tests/test_docs.py: 19 passed. `pytest deploy/tests/test_docs.py hardware`: 193 passed.
- scripts/check_comment_history.py check: clean.

## Deviations from Plan
- The production env file path in the runbook is /opt/skypane/skypane.env (what deploy/README.md already uses), not /etc/skypane.
- The support guide's refresh-spacing row cites the firmware Kconfig default of 60 s; no server-side spacing value exists to cite.
- SECOND-HARDWARE*.md records, Phase 47/47.1 files and firmware-release.yml were not touched.

## Known Stubs
None.

## Self-Check: PASSED
