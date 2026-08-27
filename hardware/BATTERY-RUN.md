# SkyPane — Phase 1 Battery Discharge Run (DEVICE-05)

This file is the recorded DEVICE-05 verdict for the SkyPane device: whether
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

**Server sleep value:** the run is served by `skypane-byos.service` on
the VPS (the same `stub-server/byos_server.py` file the local stub is,
run under systemd — see the observation channel subsection below), whose
sleep is `SKYPANE_SLEEP_S` in `/opt/skypane/skypane.env`, 30 in normal
production operation. This matters mechanically, not just as trivia:
`check-battery`'s nominal poll count is the elapsed span divided by
`--interval-s`, so an interval that does not match what the server
actually returned inflates coverage, shrinks every gap measured in
intervals, and lets a damaged run pass all four gates. The interval is
therefore set on the VPS at the start of the run rather than assumed —
300 remains the pre-registered value for it, so a depletion result
arrives in days rather than months, and the value actually in force is
recorded in `## Measured Inputs` as `interval_s` and is what the checker
is always given, never a remembered constant. The production value
(30) must be restored after the run — a 300-second sleep left in place
leaves the deployed frame refreshing far less often than the server
updates it.

**Validity thresholds this run is judged by** (the exact `check-battery`
defaults, pre-registered here so they cannot be tuned after the fact):

| Threshold | Value | Gate it enforces |
|---|---|---|
| `--min-coverage` | 0.95 | observed polls / nominal polls — catches polls that did not arrive, for any reason |
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

**Physical preconditions this amendment does not touch.** This
amendment moves the observation channel only. Three things about the
pack itself remain exactly as required, performed in 05-01's Task 2:
the pack is fully charged before the run starts, its polarity is
re-checked against `hardware/BOM.md` immediately before connection, and
it must have a confirmed integrated protection circuit — this run
deliberately empties a lithium cell, and an unprotected one taken below
its safe floor is a fire risk on the next recharge, not merely a dead
pack.

### Observation channel

The observation channel for this run is `skypane-byos.service`, already
running on the OVH VPS. This protocol does not start it — it is already
on before the run begins and stays on after it ends. It is the same
`stub-server/byos_server.py` file the local stub is, run under systemd
with `Restart=always`, and its `log_telemetry()` print of
`X-Battery-Mv` is captured by journald on every poll.

The developer's machine plays no part in the run. It is not the
device's peer, nothing on it must stay awake, and it may sleep, change
network, or be closed for the entire run.

The daily record is produced by piping
`journalctl -u skypane-byos.service --since '<disconnect time>' -o
short-iso --no-pager` over SSH into `python3 hardware/logtools.py
from-journal`, redirected over `hardware/logs/battery-run-server.log`.
The redirect regenerates the whole window every time, rather than
appending — an append across overlapping `--since` windows would
duplicate polls, and duplicated polls inflate the observed count and
therefore coverage, which is the one number a reader would trust least
to be wrong.

Regeneration carries its own risk: if journald ever rotates the
earliest entries out of the window, the regenerated file starts later
than the run did. The mitigation is that the file is committed after
every check-in, so git holds the earlier content, and `check-battery`
already accepts several log paths concatenated in the order given —
which is the repair path.

## Protocol Amendment

**Date:** 2026-08-27.

This amendment was made before the battery pack was ever connected to
the board and before any measurement existed — no threshold could have
been chosen with the answer already in hand.

**What changed:** the observation channel only. It moves from a stub
server run by hand on a laptop, which required that laptop to stay
awake, on one network address, for up to 21 days, to the production
deployment (`skypane-byos.service`) that already runs the identical
server code, always on.

**What did not change:** the four validity thresholds, the 21-day
ceiling, the exact division being performed, and every physical
handling step for the pack — full charge, polarity re-check, protection
circuit confirmation, and the reading of `boot_count=` off the wake
line before the cable comes out. None of that moves.

## Daily Check-Ins

*Filled in by Task 2, one row per calendar day of the run. Each row
comes from regenerating `hardware/logs/battery-run-server.log` via the
`journalctl -u skypane-byos.service | from-journal` pipe over SSH,
followed by the `check-battery --status` daily check-in command.*

## Measured Inputs

*Filled in by Task 2/3: `capacity_mah` and `interval_s` (the
`SKYPANE_SLEEP_S` value read off the VPS at the start of the run, not a
remembered constant), `boot_count_start` and `boot_count_end`, each as
a `key: value` list item, plus the wall-clock disconnect time, the
timestamp of the last poll, and the elapsed span.*

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

*Filled in by Task 3: the public host the frame was pointed at, the
`SKYPANE_SLEEP_S` in force during the run and the value restored
afterwards, whether `skypane-byos.service` stayed active throughout and
whether it restarted, whether journald retention covered the whole
window, any home-network or internet outage noticed, charge/recharge
times, the pack's post-depletion physical condition, and any
interruption or anomaly from the check-in table.*
