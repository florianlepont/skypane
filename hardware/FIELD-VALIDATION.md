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
| VAL-03 | Sleep current against the six-month target of about 1 mA average or less | open: the 2026-10-28 finding (a) is withdrawn because both end points were above 4000 mV, where the curve is not calibrated against a discharge, and the run-one data show about 7 times more charge per mV there than the curve assumes; re-analysis with end medians below 4000 mV about 2026-11-11 |

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

Status: open. The finding (a) recorded on 2026-10-28 is withdrawn; see "Withdrawn finding" below.

Scope: this covers only the 900 s test on the current 3000 mAh pack. It says nothing about the replacement 10000 mAh pack, which has not been in the frame. The multimeter-in-series procedure (`hardware/SLEEP-CURRENT.md`) stays optional; the owner declined it between 2026-10-12 and 2026-10-23 and it is still not required.

Closing rule: outcomes (a) and (b) settle the question and the row would read `settled by the voltage trend`; outcome (c) satisfies neither closing form of VAL-03 (neither a located excess draw nor an explicit statement that the measurement settles the question), so the row stays `open`. The outcome is chosen only from the `band:` key the tool printed, with the fixed mapping `at_or_below_allowance` and `between_allowance_and_favourable` give (a), `between_favourable_and_central` and `not_applicable` give (c), `above_central` gives (b). The corrected tool prints `not_applicable` whenever an end-point median is above 4000 mV, so such a run gives (c).

### Withdrawn finding

On 2026-10-28 the 900 s test export was run through `sleep-trend`: end medians 4022 mV and 4008 mV, estimate 0.39 mA, band `at_or_below_allowance`, recorded as outcome (a). That finding is withdrawn, for two reasons that come from the repository's own data:

1. Both end points sit in the curve's top segment, between the 4000 mV and 4112 mV knots (90 % to 100 %), where the curve gives about 0.09 % per mV, about 2.7 mAh per mV on 3000 mAh (arithmetic by Claude from `BATTERY_DISCHARGE_CURVE`). That segment's top knot is a charger-plateau reading, not a point measured on a falling pack (`hardware/BATTERY-MODEL.md`, 'Percentage calibration at the top of the curve').
2. Run one itself (`hardware/logs/battery-run-server.log`, 300 s cadence, about 10.1 mA from 243.10 mAh per day in `hardware/BATTERY-RUN.md`) went from a median of 4008 mV to 4000 mV in about 15.4 h and from 4008 mV to 3982 mV in about 50.3 h. That is about 154 mAh over 8 mV and about 507 mAh over 26 mV, about 19 mAh per mV, roughly 7 times the charge per mV that the curve assumes at the top (arithmetic by Claude). The curve therefore understates the charge behind each millivolt there, and the 0.39 mA figure is too low by a large factor that cannot be stated from this data.

The earlier tool output is kept unchanged as what the tool printed before the correction, and is superseded by the `-v2` files below.

### Method

`python3 hardware/logtools.py sleep-trend` reads the owner's export, drops everything before the stated start, ignores the first 24 h after the first kept poll, takes the median millivolts and the median time over the first and the last 12 h of polls (polls in quiet hours 23:30-06:00 Paris time are left out of both end points), converts the two medians to a charge fraction with the curve `server/device_policy.BATTERY_DISCHARGE_CURVE` and multiplies the fall by the rated capacity, 3000 mAh (a rating, not a measurement), then divides by the elapsed hours. Since the correction, when either end-point median is above 4000 mV the band is `not_applicable`, the estimate is printed labelled unreliable, and the 'does not measure' list names the reason.

### Conditions

- Owner-reported, 2026-10-28: the test started at about 2026-10-23 06:25 Paris time (04:25Z) with the first reading 4058 mV and USB unplugged. On 2026-10-28 the owner read 4006 mV at 19:30 Paris time on the Health page. The owner said no USB cable was plugged in and no setting was changed since the start. These statements are not verifiable from the export; the export shows no rise in voltage that would suggest charging, and the tool did not refuse the run.
- The owner exported the history rows themselves on 2026-10-28 with the pinned route and attached the file. It is committed unmodified as `hardware/logs/sleep-trend-900s-export.jsonl`, 395 lines, sha256 `507e8cf70b75d9c8385813b75d5806d3fe6de981fdc084413d6f1643aaaf5980`.
- Properties of the export noted by Claude: two rows have a null battery reading (2026-10-23T05:46:36 and 06:30:06 UTC), which the tool tolerates; the median gap is 934 s; five gaps exceed 2700 s (quiet hours at night). Nothing was cut: the tool reported 0 rows before the start instant.
- Owner decision, 2026-10-28: the interval stays at 900 s so that the voltage keeps falling into the steeper part of the curve, below about 3980 mV, where the estimate becomes precise. The test continues on the old 3000 mAh pack.

### Commands and numbers

Commands, run from the repository root:

`python3 hardware/logtools.py sleep-trend --capacity-mah 3000 --interval-s 900 --start-utc 2026-10-23T04:25:00Z hardware/logs/sleep-trend-900s-export.jsonl`

with `--out hardware/logs/sleep-trend-900s-report-v2.json` for the JSON. The 10000 mAh run is the same command with `--capacity-mah 10000` and no `--out`; it exists only to print the 10000 mAh allowance (2.31 mA, rated), because the 10000 mAh pack was not in the frame.

Corrected output (verbatim files): `hardware/logs/sleep-trend-900s-output-v2.txt` (3000 mAh), `hardware/logs/sleep-trend-900s-10000mah-output-v2.txt`, JSON `hardware/logs/sleep-trend-900s-report-v2.json`. Figures from the 3000 mAh output:

```
start end point: median 4022.0 mV at 2026-10-24T10:42:51+00:00 (47 polls, 92.0% on the curve)
end end point: median 4008.0 mV at 2026-10-28T11:41:43+00:00 (47 polls, 90.7% on the curve)
elapsed between end points: 97.0 h
average current: 0.39 mA (unreliable: the curve is not calibrated above 4000 mV)

band: not_applicable
The curve is not calibrated at this voltage (end points 4022 mV and 4008 mV; limit 4000 mV), so no band and no finding letter can be drawn from the 0.39 mA estimate.
```

Superseded files, what the tool printed before the correction (kept, not deleted, and not to be relied on): `hardware/logs/sleep-trend-900s-output.txt`, `hardware/logs/sleep-trend-900s-10000mah-output.txt`, `hardware/logs/sleep-trend-900s-report.json` (band `at_or_below_allowance`).

### Raw fall and the curve-free comparison

Raw fall of the test, no curve involved (arithmetic by Claude from the tool's end points): 14 mV (4022 to 4008) in 96.98 h, 0.144 mV/h, 3.46 mV per day.

Curve-free comparison, analysis by Claude, not tool output, rough: run one's server log, median-of-9 smoothing of the X-Battery-Mv readings counted from the first reading below 4060 mV (2026-09-02T12:58:50Z), first crossings at 4008 mV after 5.4 h, at 4000 mV after 20.9 h and at 3982 mV after 55.7 h. That is a fall of about 0.5 mV/h (about 12.5 mV per day) near 4010 mV at about 10 mA, against 0.14 to 0.16 mV/h for the test. The ratio is about 0.3 to 0.4, which gives roughly 3 to 4 mA at 900 s. This is consistent with run one's wake cost scaled by the wake count (a third of the wakes at 900 s) and lies between the favourable (1.95 mA) and central (8.66 mA) hypotheses, the band that maps to outcome (c). It is not a measurement and settles nothing: run-one readings near the top are noisy by about 15 mV, and the slope depends on how the crossings are chosen (taking the point after which the smoothed value stays at or below the threshold gives 0.38 to 0.63 mV/h; straight-line fits over different windows near 4000 mV give 0.16 to 0.46 mV/h).

Bound on intervals, arithmetic by Claude: if the wake cost is 0.49 to 1 mAh and the standing draw is about zero (not established), a 10000 mAh pack reaches 180 days (2.31 mA allowance) only at intervals of roughly 13 to 26 minutes or more (0.49 mAh x 3600 s / 2.31 mA is about 760 s, 1 mAh gives about 1560 s). Nothing in this record shows that six months is reachable at 900 s.

### Re-analysis, about 2026-11-11

The 900 s test continues on the old 3000 mAh pack until about 2026-11-11. The re-analysis will use: the end-point medians below 4000 mV (a run whose end points are still above 4000 mV stays `not_applicable`); the corrected tool, reading its band as before; then the curve-free comparison against run one, if the tool alone still leaves the question open. The multimeter route stays optional.

### Caveats

- The discharge curve and the 3000 mAh are ratings, not measurements, and the top of the curve is its least reliable part.
- The 4058 mV first reading and the 4006 mV owner reading of 2026-10-28 19:30 Paris time are not tool inputs; the latter is consistent with the 4008 mV end median.
- Rest-voltage creep after a full charge lowers the apparent draw early in a run (a printed bias).
- Only the 900 s test on the current 3000 mAh pack is covered. Nothing here concerns the new pack.

## Healthy check-in cadence at the final interval (VAL-01)

To be filled by plan 47-05.

## Final decision and pack status (VAL-02)

To be filled by plan 47-06. The pack checklist is `hardware/PACK-ACCEPTANCE.md`.

## What stays open

To be filled by plan 47-06.
