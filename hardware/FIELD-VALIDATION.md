# Field validation record (VAL-01, VAL-02, VAL-03)

This is the single evidence record for the integrated field validation. It is a skeleton: later plans fill the sections below. No result is stated yet.

## Evidence rules

- Tool output is copied verbatim, with the command that produced it.
- Ratings (3000 mAh, 10000 mAh) are ratings, not measurements.
- Owner-reported facts are labelled owner-reported and carry the date.
- The two-run battery model has zero degrees of freedom: two runs, two unknowns. Its figures are consistent with the data but not statistically tested.
- A figure is either copied from a committed document or labelled arithmetic.

## Status

| Requirement | Subject | Status |
|---|---|---|
| VAL-01 | Healthy check-in behaviour at the selected cadence; battery-critical and display-off overrides still win | pending |
| VAL-02 | Final field operating decision, conditional pack change and its validation status | pending |
| VAL-03 | Sleep current against the six-month target of about 1 mA average or less | settled by the voltage trend (outcome (a), 900 s test on the current 3000 mAh pack only; see the caveats in the VAL-03 section) |

## Overrides: battery-critical park

### Real frame, run-two history, 2026-10-10 to 2026-10-12

Label: real frame, run-two history, 2026-10-10 to 2026-10-12. This is history from the committed run-two export (sha256 `540d8f56aeab41b3a2de395a4f5820e069a9b4c1f470e526c0df12fc0557efdb`, the value in `hardware/logs/battery-model.json`), not a new trial. Production had quiet hours off in run two. The window starts at the first reading at or below 3300 mV (2026-10-10T20:33:30+00:00) and ends at the last row of the export (2026-10-12T16:22:02+00:00): 46 rows, 45 gaps.

Commands and the full verbatim output are in `hardware/logs/val01-run2-parked-checkins.txt`. The three commands, all run from the repository root, differ only in `--expect-s` and `--skip-first-gaps`:

`python3 hardware/logtools.py checkin-gaps hardware/logs/battery-run2-export.jsonl --expect-s 3600 --from 2026-10-10T20:33:30+00:00 --to 2026-10-12T16:22:02+00:00 --no-quiet-hours`

What the tool printed, copied from the file:

```
min / median / max gap: 98 / 3582 / 3613 s
median gap vs expected: 3582 s, 0.995 x expected (information only)
gaps within expected to 1.5 x expected: 2.2%
gaps above 3 x expected: 0
PASS coverage is at least 0.95 (judged gaps only)
PASS no gap between consecutive polls exceeds 3 interval(s) (judged gaps only)
cadence verdict: PASS
```

The same window judged against the normal 60 s cadence (`--expect-s 60`) printed `cadence verdict: FAIL` (coverage 0.017, largest gap 60.22 intervals). So the real frame was checking in about hourly while parked and was not running at 60 s.

Reading the numbers plainly:

- 44 of the 45 gaps are between 3573 s and 3613 s. The one outlier is the first gap, 98 s: the interval between the 3300 mV row and the next row, which I infer is the last gap before the park took effect (the first reply after the 3300 mV reading). It is still the old (normal) interval, not a parked gap. Running with `--skip-first-gaps 1` sets it aside (third block of the file): 44 judged gaps, min 3573 s, median 3582 s, max 3613 s, verdict PASS. The plan's literal command passes either way, because a short gap cannot fail the gates.
- The median parked gap is 3582 s, 18 s under the 3600 s expected interval, and the tool prints `gaps within expected to 1.5 x expected: 2.2%` for that reason: almost every gap is a few seconds below 3600. That share counts gaps from 3600 s upward; read it as "gaps are just under the nominal hour", not as a sign of irregular check-ins. No explanation of the 18 s is claimed here.
- The earlier figure of 41 check-ins over 39.8 hours in `hardware/BATTERY-MODEL.md` covers only the span from the voltage peak onward; this window starts earlier, at the 3300 mV crossing, hence 46 rows.

What this shows: with the battery-critical park active, the real frame checked in about every hour and not at the normal 60 s, so the park governed the real frame for about two days.
What it does not show: that the park would still win at the final chosen interval, or that it clears on recovery on the real frame. Run two never recovered.

### Automated precedence tests (server-side, not the real frame)

Label: server-side automated test, not the real frame. Re-run in this plan from the worktree: `pytest stub-server/test_wake_interval_delivery.py server/test_pipeline_e2e.py` gave 60 passed.

- `stub-server/test_wake_interval_delivery.py::test_safety_pins_win_over_saved_interval` (cases at saved intervals 300, 900 and 1800 s): the park pins 3600 s, display-off pins 300 s, park beats display-off (`display-off-and-latched`), and a recovery reading (`latched-recovering`) restores the saved interval.
- `stub-server/test_wake_interval_delivery.py::test_quiet_hours_never_shortens_saved_interval`: quiet hours never shorten a saved interval.
- `stub-server/test_wake_interval_delivery.py::test_wake_mirror_matches_frame_sleep_s`: the companion's mirror of the wake interval agrees with the frame-facing reply for every precedence case.
- `server/test_pipeline_e2e.py::test_full_pipeline_end_to_end_through_the_real_device_protocol`: through the real device protocol, a 3290 mV check-in latches BATTERY EMPTY with `sleep_s` 3600, and a 4100 mV check-in's own reply already carries the unparked interval before the park clears.

## Display-off: no real-frame evidence yet

The run-two history contains no period with the display switched off, so there is no real-frame evidence that display-off wins over the normal cadence. The only evidence today is the server-side automated test `stub-server/test_wake_interval_delivery.py::test_safety_pins_win_over_saved_interval` (case `display-off`: 300 s regardless of the saved interval; case `display-off-and-latched`: the park wins). The real-frame check is the owner check in plan 47-05, to be filled there.

## Sleep current from the voltage trend (VAL-03)

Scope: this covers only the 900 s test on the current 3000 mAh pack. It says nothing about the replacement 10000 mAh pack, which has not been in the frame. The multimeter-in-series procedure (`hardware/SLEEP-CURRENT.md`) stays optional; the owner declined it between 2026-10-12 and 2026-10-23 and it is not needed here.

Closing rule used: outcomes (a) and (b) both settle the question and the row reads `settled by the voltage trend`; outcome (c) satisfies neither closing form of VAL-03 (neither a located excess draw nor an explicit statement that the measurement settles the question), so the row would be `open` and plan 47-06 would close it as open with the reason. The outcome is chosen only from the `band:` key the tool printed, with the fixed mapping `at_or_below_allowance` and `between_allowance_and_favourable` give (a), `between_favourable_and_central` and `not_applicable` give (c), `above_central` gives (b).

### Method

`python3 hardware/logtools.py sleep-trend` reads the owner's export, drops everything before the stated start, ignores the first 24 h after the first kept poll, takes the median millivolts and the median time over the first and the last 12 h of polls (polls in quiet hours 23:30-06:00 Paris time are left out of both end points), converts the two medians to a charge fraction with the curve `server/device_policy.BATTERY_DISCHARGE_CURVE` and multiplies the fall by the rated capacity, 3000 mAh (a rating, not a measurement), then divides by the elapsed hours.

### Conditions

- Owner-reported, 2026-10-28: the test started at about 2026-10-23 06:25 Paris time (04:25Z) with the first reading 4058 mV and USB unplugged. On 2026-10-28 the owner read 4006 mV at 19:30 Paris time on the Health page. The owner said no USB cable was plugged in and no setting was changed since the start. These statements are not verifiable from the export; the export shows no rise in voltage that would suggest charging, and the tool did not refuse the run.
- The owner exported the history rows themselves on 2026-10-28 with the pinned route and attached the file. It is committed unmodified as `hardware/logs/sleep-trend-900s-export.jsonl`, 395 lines, sha256 `507e8cf70b75d9c8385813b75d5806d3fe6de981fdc084413d6f1643aaaf5980` (identical for the original and the committed copy; the tool prints and stores the same value in the JSON).
- Properties of the export noted by Claude: two rows have a null battery reading (2026-10-23T05:46:36 and 06:30:06 UTC), which the tool tolerates; the median gap is 934 s; five gaps exceed 2700 s (quiet hours at night). Nothing was cut: the tool reported 0 rows before the start instant.

### Commands and numbers (copied from the tool output)

Commands, run from the repository root:

`python3 hardware/logtools.py sleep-trend hardware/logs/sleep-trend-900s-export.jsonl --capacity-mah 3000 --interval-s 900 --start-utc 2026-10-23T04:25:00Z --out hardware/logs/sleep-trend-900s-report.json`

The 10000 mAh run is the same command with `--capacity-mah 10000` and no `--out`. It exists only to print the 10000 mAh allowance; its estimate (1.29 mA, `not_applicable`) is not used, because the 10000 mAh pack was not in the frame. The current drawn from a voltage fall scales with the capacity that was in the frame, which is the 3000 mAh pack, so the 3000 mAh run is the estimate.

Verbatim output files: `hardware/logs/sleep-trend-900s-output.txt` (3000 mAh), `hardware/logs/sleep-trend-900s-10000mah-output.txt` (allowance only), JSON `hardware/logs/sleep-trend-900s-report.json`. Figures from the 3000 mAh output:

```
start end point: median 4022.0 mV at 2026-10-24T10:42:51+00:00 (47 polls, 92.0% on the curve)
end end point: median 4008.0 mV at 2026-10-28T11:41:43+00:00 (47 polls, 90.7% on the curve)
elapsed between end points: 97.0 h
charge drawn: 37.5 mAh (curve fraction fall x rated capacity)
average current: 0.39 mA
sensitivity: 0.28 mA per 10 mV of error at the start end point, 0.28 mA at the end one

Reference values at 900 s:
  favourable hypothesis: 1.95 mA
  central hypothesis:    8.66 mA
  180-day allowance for 3000 mAh (rated): 0.69 mA

band: at_or_below_allowance
The estimate 0.39 mA is at or below the 0.69 mA 180-day allowance.
```

The 180-day allowance for 10000 mAh (rated), copied from the 10000 mAh output file, is 2.31 mA.

The tool's printed biases (verbatim from the output file):

- Rest-voltage creep after a full charge: the voltage keeps settling for days, which lowers the apparent draw early in the run.
- The curve shape and the 3000 or 10000 mAh figure are ratings; a real pack differs and the voltage-to-charge mapping is not a measurement.
- 1 mV quantisation of the reading and the sensitivity above: a few mV of end-point error moves the estimate by the amounts printed.
- Quiet-hours wakes are longer, so the field average over a day is below a daytime-rate hypothesis; the end points leave quiet-hours polls out.
- The figure is an average over the window, not the instantaneous sleep current.
- It cannot separate the standing draw from the wake energy at a single interval.

### Finding

Printed band key: `at_or_below_allowance`. Printed band sentence: "The estimate 0.39 mA is at or below the 0.69 mA 180-day allowance." By the fixed mapping this is outcome (a), and the VAL-03 row reads settled by the voltage trend. The estimate (0.39 mA) is lower than the favourable hypothesis (1.95 mA), which is the wake cost alone at run two's 0.48796 mAh per wake and one wake per 900 s. So the data do not support the modelled 7 mA standing draw, and they also do not match the wake-cost-only figure. Two readings are possible and this test cannot tell them apart: a wake at 900 s costs less than in run two, or the curve and the rated 3000 mAh overstate the charge per millivolt (the top of the curve is its least reliable part). Arithmetic by Claude, not tool output, ignoring quiet hours and the pack rating: at face value 0.39 mA would last about 320 days on 3000 mAh; if instead the wake cost of run two holds, the interval at which the wake cost alone meets the 2.31 mA allowance of a 10000 mAh pack is 0.48796 mAh per wake x 3600 s / 2.31 mA, about 759 s. Both lines are context for the interval decision in 47-05; neither is that decision.

### Caveats the finding must be read with

- The discharge curve and the 3000 mAh are ratings, not measurements. The top of the curve is the least reliable part of the voltage-to-charge mapping, and both end points (4022 mV and 4008 mV, 92.0 % and 90.7 % on the curve) sit at the top. The cross-reference to `hardware/BATTERY-MODEL.md` that the owner request named, a section titled 'Percentage calibration at the top of the curve', does not exist in that file at this commit; no such section is cited as support here.
- The estimate rests on a 14 mV fall between the two end points (4022 to 4008 mV), about 3.46 mV per day over the 96.98 h between them (arithmetic by Claude; the elapsed time is in the JSON). The sensitivity is 0.28 mA per 10 mV, so an error of 14 mV in the fall would move the estimate by about as much as the estimate itself (arithmetic by Claude: 1.4 x 0.28 = 0.39 mA).
- Analysis by Claude, not tool output: the central model (about 8.66 mA at 900 s) would imply a much larger fall than observed. At 8.66 mA over 96.98 h the charge drawn would be about 839 mAh, 28 % of 3000 mAh, which at the curve's average slope (1166 mV per 100 %) is a fall of roughly 326 mV, against 14 mV observed. The data do not support the central model.
- The favourable hypothesis (about 1.95 mA) is not matched exactly either. The estimate, 0.39 mA, is lower than it, and lower than the 0.49 mA that the wakes alone were expected to cost in the parked phase of run two. This record states the gap and does not explain it away. Rest-voltage creep (a printed bias) would push the apparent draw down; whether it accounts for all of it is not known.
- Taken at face value, 0.39 mA would give about 323 days on a 3000 mAh pack (arithmetic by Claude), which is longer than the six months. This record does not rely on that: a 14 mV fall on ratings is not enough to support it, and the owner decision on the pack stays with 47-05 and 47-06.
- The 4058 mV first reading and the 4006 mV owner reading of 2026-10-28 19:30 Paris time are not tool inputs. The end of the export is the 4008 mV median at 11:41Z; the 4006 mV reading is later and consistent with it.
- Only the 900 s test on the current 3000 mAh pack is covered. Nothing here concerns the new pack.

## Healthy check-in cadence at the final interval (VAL-01)

To be filled by plan 47-05.

## Final decision and pack status (VAL-02)

To be filled by plan 47-06. The pack checklist is `hardware/PACK-ACCEPTANCE.md`.

## What stays open

To be filled by plan 47-06.
