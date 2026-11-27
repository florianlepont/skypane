---
phase: 70-private-repository-and-ci
plan: 05
subsystem: ci
tags: [self-hosted-runner, lima, launchd]
requires: [70-06]
provides:
  - two single-use self-hosted runners on the owner's Mac (Lima VMs, launchd loops)
affects: [70.1]
metrics:
  completed: 2026-11-26
---

# Phase 70 Plan 05: Runner on the owner's Mac Summary

Done by the owner on his Mac with the runner kit of plan 70-06; sessions never saw the admin token. The install record is in `70-MEASUREMENTS.md`, section "Runner install" (runners: 2, idle and visible: yes, no collaborators; the two settings on fork pull requests and outside collaborators are left to the owner's check before the switch, row 8 of `70-POSTFLIP.md`).

Real CI was run on the VMs on 2026-11-26 and exposed five faults, all fixed: a RAM `/tmp` filled by test data, too many xdist workers for 5 GiB, no C compiler and no `node` in the VM, a Mac that went to sleep during jobs, and a 20-minute job limit. The kit now installs the tools, wipes the work and temporary folders after every job, and the job limit is 45 minutes when `CI_RUNS_ON` is set.

Result: a full run is green on the Mac (about 50 to 60 minutes with the runners not shared). Per the owner's decision of 2026-11-27 the repository stays public with hosted CI until the close of v1.4; the Mac runner is the setup after the switch (`CI_RUNS_ON` is set again just before it).
