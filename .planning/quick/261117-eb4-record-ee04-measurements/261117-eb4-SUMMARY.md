---
quick_id: 261117-eb4
date: 2026-11-17
status: complete
---

# Quick 261117-eb4: record the EE04 measurements (Phase 64 criterion 7)

Recorded the owner's bench readings of 2026-11-17 on the EE04 unit
(84:c7:bb:70:b2:7c as reported by the owner; the build did not print the MAC).

- Busy waits (n=5, min / median / max): after init 0.17 / 0.17 / 0.17 s, after the
  refresh command 30.35 / 30.36 / 30.62 s, after power-off 0.15 / 0.15 / 0.15 s.
- LED GPIO21, active low; KEY0 = GPIO5, KEY1 = GPIO3, KEY2 = GPIO2, idle high,
  pressed low. All equal the repository values.
- Criterion 7 stays OPEN (owner decides). Still open: battery sense and divider,
  ADC enable, discharge profile (items 6, 7, 10), the 190 s blit stage and 700 s wake
  budget (not measured as a full wake), `FP_MIN_REFRESH_SPACING_S` not set.
- No firmware value changed; applying or tightening any is a separate firmware
  decision (new release).
- Stale wording fixed: "Phase 65 validates the battery curves" replaced by "battery
  values come from production use, carried to SEED-019 (v1.4)" in the 64
  VERIFICATION and WALKTHROUGH, the ROADMAP, the v1-2 STATE, the 58-04 summary and
  `hardware/SECOND-HARDWARE-BATTERY.md`.

Files: `hardware/SECOND-HARDWARE-MEASUREMENTS.md`,
`hardware/SECOND-HARDWARE-BATTERY.md`, the Phase 64 VERIFICATION and WALKTHROUGH,
`.planning/workstreams/v1-2/ROADMAP.md` and `STATE.md`, `58-04-SUMMARY.md`.
