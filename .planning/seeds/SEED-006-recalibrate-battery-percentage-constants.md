---
id: SEED-006
status: fulfilled
planted: 2026-09-15
resolved_date: 2026-09-23
planted_during: Phase 5 (05-low-battery-indicator) — DEVICE-05 battery discharge run, Task 3 write-up
trigger_when: when relevant
scope: unknown
---

# SEED-006: Recalibrate the battery-percentage estimate's FULL/EMPTY constants against DEVICE-05's real discharge curve

## Why This Matters

`companion/battery.py` and `server/poll_loop.py` each carry an identical,
deliberately-duplicated (D-27) `BATTERY_FULL_MV = 4200` / `BATTERY_EMPTY_MV
= 3300` pair, linear-interpolated into a 0-100% estimate. Both were
assumptions — a "rough state-of-charge estimate," per the module's own
docstring — because no real discharge curve existed yet.

DEVICE-05's completed discharge run (`hardware/BATTERY-RUN.md`, concluded
2026-09-14) now provides one, and it disagrees with both constants:

- The pack's real charge plateau was **~4122 mV**, never 4200 — so a
  freshly-charged pack currently reads ≈91%, never 100%.
- The device kept polling successfully all the way down to **2946 mV**,
  well past the assumed 3300 mV "0%" floor — for roughly the final 24
  hours of the run, the estimate would have already shown 0% while the
  device was still fully alive and functioning normally.

## When to Surface

**Trigger:** when relevant

This seed will surface during `/gsd-new-milestone` when the milestone scope matches.

## Scope Estimate

**Unknown** — run `/gsd-capture --seed --enrich SEED-006` to estimate effort.

Worth deciding as part of scoping: whether to simply recalibrate the two
endpoint constants (low effort), or replace the linear interpolation with
a piecewise/table-based curve matching the discharge shape this run
actually observed (flat top, gently declining middle, steep cliff near
empty) — a more honest but larger change.

## Breadcrumbs

- `companion/battery.py` — `BATTERY_FULL_MV`/`BATTERY_EMPTY_MV`,
  `battery_percent()`
- `server/poll_loop.py` — `_NOTIFY_BATTERY_FULL_MV`/`_NOTIFY_BATTERY_EMPTY_MV`,
  `_battery_percent_estimate()` (the deliberately duplicated copy, D-27 —
  any fix must touch both files together and keep them byte-identical)
- `hardware/BATTERY-RUN.md` — `## Discharge Trend` (the real curve) and
  `## Calibration & Follow-Up Findings` (this finding's original writeup)

## Notes

Captured 2026-09-15 during DEVICE-05's Task 3 write-up, at the developer's
explicit request to think through what this run's data should change in
the codebase, not just record the measurement itself.

**Fulfilled — status closed 2026-09-23.** Quick task 260923-gaf replaced
the linear estimate in both homes with the 14-knot piecewise curve
derived from `## Discharge Trend`.

The Scope Estimate's open question was decided in favour of the
piecewise curve (user decision, D-SEED006). The endpoints-only
alternative was rejected because 3500 mV would have read about 48%
against about 15% observed.

The follow-on effects: LOW_BATTERY_DISPLAY_MV is now derived as 3540
(20%); the device's 3500/3600 thresholds are unchanged; the life
estimate now projects in state-of-charge space; and a parity check now
enforces the D-27 duplicate.
