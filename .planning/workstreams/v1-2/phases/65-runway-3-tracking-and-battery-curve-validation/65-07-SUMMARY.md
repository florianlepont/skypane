---
phase: 65-runway-3-tracking-and-battery-curve-validation
plan: 07
subsystem: tracking-validation
tags: [trk-02, feasibility, scratch-fleet, owner-decision]
requires: []
provides:
  - "Read-only feasibility answers Q1 to Q5 for running TRK-02 on simulated devices"
  - "Owner decision: option A, scratch state root outside production"
  - "Live-frame status baseline for the end-of-phase comparison"
affects: [65-08, 65-09, 65-10, 65-11, 65-12, 65-13, 65-14]
key-files:
  created:
    - .planning/workstreams/v1-2/phases/65-runway-3-tracking-and-battery-curve-validation/65-TRACKING-MULTI-FEASIBILITY.md
    - .planning/workstreams/v1-2/phases/65-runway-3-tracking-and-battery-curve-validation/data/status_baseline_trk02.json
decisions:
  - "TRK-02 simulated devices run in a scratch state root outside production (option A), in this cloud environment, falling back to the owner's machine (still option A) if the sandbox or a provider fails during a session"
requirements: [TRK-02]
status: complete
completed: 2026-11-15
---

# Phase 65 Plan 07: TRK-02 multi-device feasibility Summary

Existing code serves several simulated airports from a scratch state root with no server change; the owner chose to run the TRK-02 sessions that way (option A), so plans 08 to 14 all run.

## Tasks

1. Read-only feasibility check: done earlier (commit 6a3d511d). Five answers with file and function evidence, a local proof with injected fetcher and runner (4 zones, 3 simulated devices plus the live frame served, each in its own `devices/<id>` directory; without the simulation flag the simulated devices are skipped as `unsupported_hardware`), provider reachability from this environment (adsb.fi, adsb.lol on one attempt, adsbdb), the live-frame status baseline in data/status_baseline_trk02.json, and options A to D.
2. Owner decision recorded: option A, quoted in the `## Owner decision` section of 65-TRACKING-MULTI-FEASIBILITY.md, with a `## Consequence` section naming every plan from 08 to 14 as run (none skipped, none blocked).

## Owner decision

Given by the owner on 2026-11-15 in chat: "option A, scratch state root outside production, run in this cloud environment (fall back to the owner's machine, still option A, if the sandbox or a provider fails during a session)."

## Consequence

| Plan | Outcome |
|------|---------|
| 08 | runs (tooling in scripts/ only) |
| 09 | runs; needs the owner's choice of two airports |
| 10, 11 | run as sessions here, fallback to the owner's machine |
| 12, 13 | run |
| 14 | runs, limited to findings the owner agrees in plan 13 |

Options B (VPS) and C (production fleet) are not used; nothing in this phase starts a server or production change.

## Deviations from Plan

None - plan executed as written. No file under server, stub-server, companion, deploy or firmware changed.

## Self-Check: PASSED

The feasibility file has exactly one `## Owner decision` and one `## Consequence` heading and the baseline file exists.
