---
id: SEED-019
status: dormant
planted: 2026-11-15
planted_during: "v1.2, Phase 65 discuss: the owner moved all battery discharge work out of Phase 65 into a dedicated phase."
trigger_when: "Milestone v1.4, set by the owner on 2026-11-15; surface it at /gsd-new-milestone."
target_milestone: v1.4
scope: medium
requirement: BAT-01 (moved from Phase 65)
---

# SEED-019: Battery discharge and curve validation (both frames)

## Why This Matters

The percentage shown on the frame and in the companion rests on a curve calibrated once on the old 3000 mAh pack of the live frame. Nothing measured shows that the curve, the low-battery threshold and the battery tests are right for the two packs now in use. The owner wants full discharges, in a dedicated phase, not mixed with the runway 3 tracking check.

## Scope

- Full discharge of the live frame's new pack (Soldered 333290, 10000 mAh, connected 2026-11-11). The owner decides whether it may go below the 3300 mV BATTERY EMPTY park.
- Full discharge of the second frame (EE04, 7.3 inch). The owner runs the measurements: log, capacity, shutdown time. Sheet and capture method: `hardware/SECOND-HARDWARE-BATTERY.md`.
- Review of what the battery tests prove and do not prove: `hardware/BATTERY-MODEL.md`, SEED-006, the Phase 56 profiles, the Phase 47.1 wake-energy work.
- Check the voltage-to-percentage curve and the low-battery threshold of each battery against its measured discharge. Unmeasured values stay provisional, with the gap listed.
- The companion shows the same percentage as the frame's profile for each type.

## Known facts

- Old pack, run one: discharged to 2946 mV (the 0 % knot). Run two stopped at the 3300 mV park (6 % on the curve).
- The top segment (4000 to 4112 mV) is not calibrated against a discharge; 100 % means a reading on the charger.
- A resting pack reads about 4.03 to 4.06 V. Whether the ADC reads about 100 mV low or the charger stops below 4.2 V is open; only a multimeter reading across the pack connector settles it.
- Capacities are vendor ratings, never measured.
- Recorded telemetry: `GET /api/export/battery-history` (2026-11-01 to 11-15 held 2 865 readings, 3886 to 4180 mV, packs not told apart).

## Must not break

Golden hashes of the legacy render, `stub-server/test_phase47_freeze.py`, and the live frame's battery display until a corrected curve is agreed with the owner. Do not edit Phase 47, 47.1 or 58 files.

## Breadcrumbs

`hardware/BATTERY-MODEL.md`, `hardware/SECOND-HARDWARE-BATTERY.md`, `server/hardware.py`, `server/device_policy.py`, `companion/battery.py`, `hardware/PACK-ACCEPTANCE.md`.

SEED-007 (a second discharge run at another wake interval, to separate per-wake energy from standing leakage) was deleted by the owner on 2026-11-18 because this seed covers it; the wake-energy side stays with Phase 47.1 and 47.2.
