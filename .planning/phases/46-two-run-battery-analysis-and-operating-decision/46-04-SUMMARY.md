---
phase: 46-two-run-battery-analysis-and-operating-decision
plan: 04
subsystem: owner-decisions
tags: [battery, interval, pack, owner-action]
requires: ["46-02", "46-03"]
provides:
  - "Owner decisions recorded in hardware/BATTERY-MODEL.md (## Owner decision, ## Chosen replacement pack)"
affects: [47]
requirements-completed: []
completed: partial (2026-10-22)
---

# Phase 46 Plan 04: Owner decisions Summary (partial)

This plan was handled in chat with the owner, not through its checkpoint flow, and it is not complete.

Recorded, owner-reported:
- Interval: 300 s (the owner wrote "5 minutes"), provisional "en attendant le remplacement de la batterie" (2026-10-12).
- Pack: replace. The owner chose the Soldered 333290 (Li-Po 10000 mAh, 11 x 60 x 100 mm, JST-PH 2 mm) and ordered it on 2026-10-22 (free depth behind the screen measured by the owner: 18 mm).
- The interval was saved on the live Device page ("Done c'est bon"); the read-back value was not stated.
- On 2026-10-23 the owner started a 900 s test (battery charged overnight, 4058 mV at the start) to check the standing draw by the voltage trend; the result is due about 2026-10-28.

Still open: the read-back value of the stored interval; acceptance of 300 s as provisional with the final value deferred to Phase 47; the pack checks (wire polarity, charge current, free area, the reference printed on the pack); real-frame confirmation (Phase 47).

No numbers are written here: figures live in BATTERY-MODEL.md.
