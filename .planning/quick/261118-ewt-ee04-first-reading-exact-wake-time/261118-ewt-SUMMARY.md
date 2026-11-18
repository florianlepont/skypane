---
quick_id: 261118-ewt
date: 2026-11-18
status: complete
---

# Quick 261118-ewt: exact wake time of the first EE04 battery reading

The battery-history export of the frame (`device=d_3d94b8f5`, read-only, taken by the
assistant on 2026-11-18) shows the wake after the owner's RESET: `boot_reason`
`power-on` at 2026-11-18T10:07:40+00:00 (11:07:40 Paris), `battery_mv` 4098. The
multimeter reading was 4.12 V at 11:07 Paris, so both readings are in the same minute.
Difference stays -22 mV (-0.5 %), ratio 0.995. Neighbouring `rtc` wakes (about every
31 s) read 4098 mV at 10:07:27 and 10:08:11, then 4094 to 4098 mV for 20 minutes
(stable to about +/-2 mV). Inference, not a measurement: the step from 4104-4110 mV
to 4096 mV at 10:05:52 UTC most likely matches the owner unplugging USB.

- The "minute not noted" caveat is removed from row 6 and its notes.
- Row 6 stays `provisional, first reading, 1 of 3 levels`; criterion 7 stays OPEN.
- No firmware value changed.

Files: `hardware/SECOND-HARDWARE-MEASUREMENTS.md`,
`hardware/SECOND-HARDWARE-BATTERY.md`, the Phase 64 VERIFICATION, root `STATE.md`.
