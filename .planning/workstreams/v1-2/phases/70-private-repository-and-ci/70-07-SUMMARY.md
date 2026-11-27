---
phase: 70-private-repository-and-ci
plan: 07
subsystem: ci
tags: [measurements, decision]
requires: [70-06]
provides:
  - measured CI minutes before and after, and the recorded choice of where CI runs
affects: [70.1]
metrics:
  completed: 2026-11-27
---

# Phase 70 Plan 07: CI measurements and decision Summary

`70-MEASUREMENTS.md` has the numbers: baseline 60 billable hosted minutes per run (run 45337958006); the Mac runner at 50 to 60 minutes of wall-clock per run (57 measured once, 67 shared) with 2 runners; the hosted fallback at about 10 minutes (about 60 billable minutes per run if private, an estimate because the repository is public); test speed work (`70-TEST-AUDIT.md`, merged 2026-11-26) that cut the test jobs' runner time by about 20 percent; coverage measured only on `main`; 8 test jobs. Gate numbers: skipped 0, 17,552 test items collected against the executed floor of 12,821, 6 browser shards.

Charge watch (2026-11-27): the announced per-minute charge for self-hosted runners is postponed with no new date; self-hosted minutes are free.

Decision (owner, 2026-11-27): the repository stays public with CI on hosted runners (free while public) until the close of v1.4; after the switch CI runs on the owner's Mac. A mini PC with four runners was recommended and not chosen for now.

Not measured: hosted minutes on a private repository, and a solo run of the final layout on the Mac (the runners were always shared).
