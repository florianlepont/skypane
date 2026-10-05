---
quick_id: 261006-charging-pill
status: complete
---

# 261006-charging-pill summary

An ESTIMATED "Probablement en charge" / "Probably charging" pill (bolt icon, ok tone, no accent)
on Home's battery dial and in Health's Battery row. Companion only: no firmware, telemetry,
schema or e-ink change. Only ONE real charge transition exists in the data (the unplug at the end
of run one), so the thresholds are calibrated on discharge noise plus that documented USB
plateau; the charging ramp used for detection latency is synthetic.

## The rule (`companion.battery.charging_estimate`)

Counted in wakes, over the newest 12 readings sorted by time. Likely charging when any of:

- plateau: the last 3 readings are all >= 4090 mV;
- step: median of the last 3 minus median of the 3 before >= 75 mV (the plug-in level shift);
- ramp: three blocks of 4 readings whose medians each rise >= 8 mV and together >= 60 mV;

and, for step and ramp, the latest reading is within 20 mV of the highest of the last 3 (so an
unplug ends the estimate on the first reading after it). Fewer than 3 usable readings, a latest
reading older than 2 x the effective cadence + 60 s (or from the future) and an undetermined
cadence are UNKNOWN and render nothing. Medians, because the panel refresh load makes single
readings sag and recover by up to ~100 mV.

## Calibration numbers (run-one data, 3248 discharge readings at ~342 s)

- Discharge false positives: 0 firings over every window ending at every reading, at the run's
  own cadence and sub-sampled to ~684, 1026, 1710, 3420 and 4104 s (all offsets). Margins: the
  highest discharge reading is 4040 mV (plateau 4090, USB showed 4112-4126); the largest 3-vs-3
  median rise is 60 mV (threshold 75; 2 firings at 60, 0 at 65); the closest ramp reaches 50 mV
  total (threshold 60; at 50 the sweep fired 0 times, at 40 once). The raw data are noisier than
  the percentage suggests: 588 of 3252 steps rise by >= 10 mV and the largest single step is
  +98 mV (a refresh sag followed by recovery), so a rule on endpoints or single steps would fire
  constantly; the real worst windows are pinned as test fixtures.
- Detection latency (synthetic, 200 trials per cell, wakes after plug-in, median): a plug step of
  84 mV or more is seen on the 2nd reading at every ramp rate; a 60 mV step plus a 2.5 mV/wake
  ramp in 6; no step and 10 mV/wake in 9 (15 mV/wake in 7). The plateau rule fires on the 3rd
  reading on the real USB readings. Limit, stated plainly: with no plug-in step and a ramp
  below about 7.5 mV per wake (for example a gentle charge sampled every 60 s) nothing fires
  until the plateau; the window is in wakes, so sensitivity per second is higher at slow cadences.
- After unplugging: the real 4122 -> 4038 mV step ends the estimate on the FIRST on-battery
  reading (plateau gone; step and ramp blocked by the latest-reading guard). Synthetic unplugs
  from a plateau at 4122/4126 and from ramps ending at 4000/3950: first "not charging" after 1
  wake in all 800 trials.
- `battery_status()` (the Battery row's "dropping faster than expected", threshold 100 mV): the
  real unplug step is 84 mV (88 mV from the 4126 USB peak), and the largest single step of the
  whole discharge run is -94 mV, so nothing fires on any real data. NOT changed (not clearly
  warranted on the evidence), pinned by a test on the real step. Residual risk for the owner:
  an unplug from the middle of a fast charge could read more than 100 mV higher on USB than on
  battery and would raise that warning for the next 20 readings.

## Display and wiring

- Home: the pill sits in its own row under the arc (clear of the "Faible"/"Très faible" word) and
  extends the dial's accessible name ("Batterie à environ 56 %, probablement en charge").
- Health: in the Battery row's closed summary, wrapping under the value on a phone.
- Both pages and the freshness token resolve the cadence through
  `health_signals.charging_likely` (hold-aware, parked cadence included). Both regions are in the
  refresh loop's swap lists; the verdict is also a Home/Health token input, because the pill ends
  by the clock with no new reading to move the database watermark (a browser test proves the
  loop removes it with no reload).
- `icon-bolt` added to the sprite (ICON_IDS 40 -> 41). Render baseline regenerated: 36 pages differ
  only by that symbol, the 4 login pages are identical, and the 8 Home/Health entries differ by
  the symbol plus the pill (the seeded newest readings sit at 4194-4200 mV, which is a plateau).
- French: "Probablement en charge"; title "La tension monte : le cadre est probablement branché".
  No cognate-list change needed (the two languages differ).

## Not verified

- Any real charge. Thresholds for the ramp and the plug-in step assume a similar pack and charger
  to the one unplug on record. A different charger/cable could change the on-USB level.
- A pack that rests above 4090 mV on battery (not seen: the run's highest discharge reading is
  4040) would read as charging until it falls below.
