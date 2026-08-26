# Ink Frame — Phase 1 Battery Discharge Run (DEVICE-05)

This file is the recorded DEVICE-05 verdict for the Ink Frame device: whether
it completes many consecutive wake, poll and sleep cycles on battery power
alone, and the measured mAh-per-cycle figure that follows from that run.

## Run Protocol (pre-registered)

Written by Task 1, **before the battery pack was ever connected to the
board** — this is the point of writing it now rather than after the run:
a threshold chosen once the answer is known is not a threshold.

**Method (D-07):** Charge the pack fully, connect it, take the USB cable
out, let the device run its normal wake/poll/sleep cycle completely
untouched, check in on it once a day, and note how long it runs. The user
explicitly rejected an inline USB power meter as unnecessary extra
hardware/technical setup — this run adds no instrumentation beyond what
D-07 specifies.

**Pack rated capacity:** 3000 mAh — transcribed from `hardware/BOM.md`
(`## Required Now`, "LiPo battery pack, 3.7V, JST-PH 2.0mm 2-pin,
protected", Kubii "Batterie 3000mAh Li-Po").

**Server sleep value:** 300 seconds — `stub-server/README.md`'s
`## Run the server` section names this as the value chosen for both
plan 01-06's repeatability run and this run specifically, so a depletion
result arrives in days rather than months.

**Validity thresholds this run is judged by** (the exact `check-battery`
defaults, pre-registered here so they cannot be tuned after the fact):

| Threshold | Value | Gate it enforces |
|---|---|---|
| `--min-coverage` | 0.95 | observed polls / nominal polls — the sleeping-host gate |
| `--max-gap-intervals` | 3 | no single gap between consecutive polls may exceed 3 intervals |
| `--min-mv-drop` | 100 mV | drop between the opening and closing millivolt windows — the phantom-USB-power gate |
| `--cutoff-mv` | 3400 mV | with `--expect-depleted`, the last reading must be at or below this to count as a genuine depletion |

**Ceiling:** 21 days. After 21 elapsed days the developer may end the run
even if the device is still alive.

**The exact division being performed, per D-07:** rated capacity (mAh)
÷ counted cycles = milliamp-hours per cycle. The cycle count itself is
reconciled three ways in Task 3 (nominal from elapsed span, observed
polls in the server log, and the device's own NVS boot-counter delta).

**Both possible outcomes are results, and neither is a failure.** A run
that empties the pack inside the 21-day ceiling gives a measured
mAh-per-cycle figure directly. A run still alive at the 21-day ceiling
gives an upper bound on per-cycle consumption and, therefore, a lower
bound on battery life — which is the direction that matters for planning
a wake interval: a bound that overstates consumption is a plan that does
not run out of battery earlier than it promised.

## Daily Check-Ins

*Filled in by Task 2, one row per calendar day of the run, from the
`check-battery --status` daily check-in command.*

## Measured Inputs

*Filled in by Task 3: `capacity_mah`, `interval_s`, `boot_count_start`
and `boot_count_end`, each as a `key: value` list item, plus the
wall-clock disconnect time, the timestamp of the last poll, and the
elapsed span.*

## Verdict

*Filled in by Task 3: `**Verdict:** MEASURED` or `**Verdict:** CENSORED`,
the date, the exact `check-battery` command with its real argument
values, and the headline mAh-per-cycle and mAh-per-day figures.*

## Cycle Count Reconciliation

*Filled in by Task 3: the nominal, observed and device boot-counter-delta
cycle counts, the coverage figure, and which count the headline division
used.*

## Discharge Trend

*Filled in by Task 3: the opening/closing millivolt window means, the
drop, the last observed value, and a short table sampling the millivolts
across the run.*

## What This Figure Does Not Cover

*Filled in by Task 3: the hash-skip-only nature of the measured cycles
(no download, no panel refresh), the single-cadence projection-band
limitation, and the absence of any inline current instrumentation.*

## Checker Output

*Filled in by Task 3: the full, verbatim output of the final
`check-battery` analysis run, including the summary line and the
projection band.*

## Run Conditions

*Filled in by Task 3: the laptop's LAN address at the start and end of
the run, whether a DHCP reservation was used, charge/recharge times, the
pack's post-depletion physical condition, and any interruption or
anomaly from the check-in table.*
