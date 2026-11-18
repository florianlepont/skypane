---
quick_id: 261118-bat
date: 2026-11-18
status: complete
---

# Quick 261118-bat: record the first EE04 battery reading (Phase 64 criterion 7)

Owner reading of 2026-11-18 on the EE04 unit (84:c7:bb:70:b2:7c as reported by the
owner): fully charged LiPo (about 3000 mAh, owner's figure from memory), USB unplugged,
rested 10 to 30 minutes. Multimeter 4.12 V at the connector (11:07 Europe/Paris);
after one RESET the wake reported `X-Battery-Mv` 4098 mV (read in the companion
console; minute not noted). Difference -22 mV (-0.5 %), ratio 0.995.

- Row 6 recorded as `provisional, first reading, 1 of 3 levels`; two levels remain
  (about 3.9 V, about 3.7 V).
- Row 7 (ADC enable GPIO6) not measured directly; only indirect evidence (floating
  with no cell, stable and within 0.5 % with the cell), written as such. Row stays empty.
- Criterion 7 stays OPEN. Discharge profile (item 10) still unmeasured.
- No firmware value changed.

Files: `hardware/SECOND-HARDWARE-MEASUREMENTS.md`,
`hardware/SECOND-HARDWARE-BATTERY.md`, the Phase 64 VERIFICATION, root `STATE.md`.
