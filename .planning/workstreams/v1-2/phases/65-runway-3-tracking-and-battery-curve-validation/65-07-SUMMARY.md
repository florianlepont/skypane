---
phase: 65-runway-3-tracking-and-battery-curve-validation
plan: 07
status: partial
requirements: [TRK-02]
key-files:
  created:
    - .planning/workstreams/v1-2/phases/65-runway-3-tracking-and-battery-curve-validation/65-TRACKING-MULTI-FEASIBILITY.md
    - .planning/workstreams/v1-2/phases/65-runway-3-tracking-and-battery-curve-validation/data/status_baseline_trk02.json
---

# Phase 65 Plan 07: TRK-02 multi-device feasibility (partial)

Task 1 is done; the plan is stopped at the owner decision checkpoint (Task 2 not run). The owner decision between options A to D is pending.

## Result of Task 1

- Q1 to Q5 answered with file and function evidence in 65-TRACKING-MULTI-FEASIBILITY.md.
- Existing code serves several simulated airports from a scratch state root with no server change (local proof with injected fetcher and runner: 4 zones, 3 simulated devices plus the live frame served, each in its own `devices/<id>` directory; without the simulation flag the simulated devices are skipped as `unsupported_hardware`).
- The export API reads only `args.state_dir` (the live frame), so a simulated device's history can only be read straight from its own `history.db`.
- Production would need the `SKYPANE_SIM_HARDWARE=1` setting and a per-device export route (option C), which this phase does not do.
- adsb.fi, adsb.lol (one attempt) and adsbdb answered from this environment.
- Live-frame status baseline saved to data/status_baseline_trk02.json.
- Recommendation: option A, run here.

## Pending

Options: A scratch-local, B scratch-vps, C production-fleet, D no-live-sessions. Task 2 records the choice and its consequence for plans 08 to 14.

## Deviations

None. No file under server, stub-server, companion, deploy or firmware was changed.
