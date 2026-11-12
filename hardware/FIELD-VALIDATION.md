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
| VAL-01 | Healthy check-in behaviour at the selected cadence; battery-critical and display-off overrides still win | validated on 2026-11-11 (900 s cadence PASS, display-off PASS on the real frame, park override from run-two history), see the two sections below |
| VAL-02 | Final field operating decision, conditional pack change and its validation status | recorded, pack validation open: interval 900 s chosen by the owner on 2026-11-11; the replacement pack is received with checks pending (`hardware/PACK-ACCEPTANCE.md`) |
| VAL-03 | Sleep current against the six-month target of about 1 mA average or less | open on purpose (outcome (c)): about 1.29 mA average at 3600 s from the voltage trend (rated capacity, rough curve), the tool's band is not applicable; the multimeter route stays optional. See "Final reading of the 3600 s test, 2026-11-11" below |

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

## Display-off on the real frame

Label: real frame, owner export. Before 2026-11-11 the only evidence was the server-side automated test `stub-server/test_wake_interval_delivery.py::test_safety_pins_win_over_saved_interval` (case `display-off`: 300 s regardless of the saved interval; case `display-off-and-latched`: the park wins), and the run-two history contained no period with the display off.

Owner-reported, 2026-11-11, Paris time: the frame was at 900 s; the owner switched the display off at 17:23 (T0, first given as 18:23 and corrected by the owner to 17:23) and back on at 18:08. The last check-in before T0 was 17:17:08 (T-1, read in the export). The first check-in after T0 was 17:32:42 (T1, read in the export), still at the old interval; the owner did not watch the Health page, Claude read the export.

Command, run on `hardware/logs/val01-display-off-export.jsonl` (sha256 `b0155f2717b2f1a87f82ebf6d8c4d7ab5458ca46dce733fe8227d2ba499b7407`, committed as received), output saved verbatim in `hardware/logs/val01-display-off-cadence.txt`:

`python3 hardware/logtools.py checkin-gaps hardware/logs/val01-display-off-export.jsonl --expect-s 300 --from 2026-11-11T16:17:08+00:00 --skip-first-gaps 1 --no-quiet-hours`

Printed lines: first gap set aside 934 s (the old 900 s interval from T-1 to T1, set aside on purpose); 7 judged gaps; min / median / max gap 299 / 300 / 338 s; median 1.000 times the expected 300 s; gaps above 3 times the expected: 0; `cadence verdict: PASS`. `--no-quiet-hours` is correct because the whole window is between 17:17 and 18:08 Paris time, outside 23:30 to 06:00.

Because the normal interval was 900 s, a 300 s cadence cannot come from the normal setting: the display-off override is seen to take precedence on the real frame. One export row at 17:43:22 Paris time carries no battery reading and no other field, three seconds after the 17:43:19 check-in; it is ignored by the tool and its cause is not known.

Status: PASS, not a pass of the whole of VAL-01 by itself.

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

### Interim state, 2026-11-01

Facts first. The test went on after 2026-10-28: the first reading at or below 3999 mV is stamped 2026-10-29T09:38:00+00:00 (UTC) and the voltage then fell faster, as the curve predicts once it leaves its flat top. Median of the non-quiet polls per 12 h window (arithmetic by Claude from the export): 4006 mV (2026-10-28 evening), 3994 mV (2026-10-29 evening), 3974 mV (2026-10-30 evening), 3966 mV (2026-10-31 morning), 3950 mV (2026-11-01 midday). The owner switched the interval from 900 s to 3600 s at 12:02 Paris time on 2026-10-31 (11:02 UTC, owner-reported); the history then shows gaps of about 3620 s, longer at night (quiet hours), from the first wake after that time.

The export was fetched through the read-only export route of the companion (`hardware/logs/oldpack-test-export-2026-11-01.jsonl`, 620 lines to 2026-11-01T17:02:08Z, sha256 `26300f53...e2288`, unmodified; its first 395 lines are identical to the 2026-10-28 export). The verbatim tool output for the window 2026-10-28T12:00Z onward is in `hardware/logs/oldpack-test-trend-900s-2026-10-28-to-31-output.txt` with its JSON next to it. Read it with care: the tool labels it unreliable because the start point (4006 mV) is above 4000 mV, so its band is `not_applicable`, and the window of that file ends on 2026-11-01 and therefore spans both cadences, so its 5.29 mA is a mixed figure, not an estimate at one interval. A run on the export fetched on 2026-10-31 (not committed; the tool has no end-of-window option, so it cannot be repeated on this file) covered only the 900 s part, 4006 mV to 3966 mV over 59.1 h, and printed 6.80 mA, also marked unreliable for the same reason; it is quoted here only as an order of magnitude.

What this changes in the record: the 0.39 mA figure stays withdrawn, the favourable hypothesis (1.95 mA at 900 s) is not supported by the interim readings, and the order of magnitude at 900 s is several mA, between 5 and 10 on the two rough methods (the tool's curve conversion and the run-one comparison). Nothing here separates the standing draw from the wake cost; that needs two cadences, which is the point of the switch to 3600 s. VAL-03 stays `open`.

### Two-cadence analysis, 2026-11-03

Inputs: the `device_health` history of the test fetched through the read-only export route (`hardware/logs/oldpack-test-export-2026-11-03.jsonl`, 664 lines, last reading 2026-11-03T15:01:14Z, sha256 `ebd2bc09...a5a`, unmodified; its first 620 lines are identical to the 2026-11-01 export; 27 lines carry no telemetry fields and are not frame wakes, they are left out of every figure). The 3600 s segment was measured with the corrected tool, verbatim output in `hardware/logs/oldpack-test-trend-3600s-2026-10-31-to-11-03-output.txt` (and `.json`); the 900 s segment and the curve-free comparison with run one come from `hardware/oldpack_two_cadence.py` (arithmetic by Claude, not the tool of record), verbatim output in `hardware/logs/oldpack-two-cadence-2026-11-03-output.txt`. The script is stdlib only and reproduces the output from the two committed inputs (the export and `hardware/logs/battery-run-server.log`).

| Interval | Segment | End-point medians | Curve-based current | Curve-free comparison with run one |
|---|---|---|---|---|
| 900 s | first reading at or below 3999 mV (2026-10-29T09:38Z) to the switch (2026-10-31T11:10Z), 40.5 h | 3998 to 3966 mV, 0.79 mV/h | 8.63 mA | 5.8 to 9.6 mA (the two crossing definitions) |
| 3600 s | switch plus 3 h to the last reading, 63.8 h | 3954 to 3936 mV, 0.28 mV/h | 0.99 mA | about 0.6 mA |

The corrected tool on the 3600 s segment: both end points are below 4000 mV, estimate 0.98 mA, sensitivity 0.54 mA per 10 mV of error at each end point (so about 1 mA with an uncertainty of the same order), and its band is `not_applicable` only because at 3600 s the 180-day allowance, the favourable and the central values are not in increasing order (0.69, 0.49, 7.64 mA), which the tool cannot rank. Reference values at 3600 s: favourable 0.49 mA, central 7.64 mA.

What the two cadences show, by reading of Claude (arithmetic and judgement, not a tool verdict):
- The central fit, whose standing draw of 7.30 mA would give about 7.6 mA at 3600 s, is not supported: the measured average at 3600 s is about 1 mA. The standing draw is at most about 1 mA (possibly near zero, within the uncertainty).
- The favourable hypothesis at 3600 s (0.49 mA) is within the uncertainty of the measurement and is not excluded.
- From 900 s to 3600 s the average current falls by a factor of about 6 to 9, while the wake count falls by 4. With I = s + w x 3600 / T this would need a negative standing draw, so the cost of a wake is not constant: it appears higher at 900 s than at 3600 s. The gaps between wakes point the same way (a median overhead of about 34 s over the configured sleep at 900 s, about 20 s at 3600 s), but this record does not explain the difference and the values of s and w are not separated here.
- No estimate exists for intervals between the two (1800 s, for example); anything quoted for them is an interpolation.

Consequences, arithmetic by Claude, rated capacities, no self-discharge or ageing: at about 1 mA a 3000 mAh pack lasts about 125 days and a 10000 mAh pack about 415 days; the 180-day allowance for 10000 mAh is 2.31 mA. At 900 s the several-mA figure does not reach six months on any pack in this range. Six months with the new pack is therefore plausible at hourly wakes and not at 900 s or shorter; the intermediate intervals are not measured.

VAL-03 stays `open`. This is a second measurement on the old pack with a rough curve and 64 hours at 3600 s; the figure at 3600 s will tighten with more days of data and has not been measured on the new pack at all. The multimeter route stays optional.

### Quiet hours differ between the studies (added 2026-11-05)

Label: arithmetic by Claude on the committed exports and logs, rated capacity, rough. The owner raised the point; the data below checks it.

| Study | Wake interval | Quiet hours | Evidence |
|---|---|---|---|
| Run one | 300 s | off | `hardware/logs/battery-run-server.log`: 3252 readings, every Paris hour populated, no gap above 3000 s |
| Run two | 60 s | off | documented in `hardware/BATTERY-RUN.md`; `battery-run2-export.jsonl` has check-ins in every hour |
| Old-pack test | 900 s, then 3600 s | on (23:30 to 06:00 Paris) | `oldpack-test-export-2026-11-03.jsonl`: a gap of about 5.7 to 7.4 h every night from 2026-10-23 |

Effect on the figures. The average currents (8.63 mA at 900 s, 0.99 mA at 3600 s) are unchanged: they come from the voltage fall over elapsed time, nights included, and the tool takes its end points from daytime polls only. The cost of a wake changes, because it must be computed on the wakes that happened, not on elapsed time divided by the interval. The wake counts come from the export rows, so a wake that never reached the server is not counted.

| Per-wake cost (mAh) | Elapsed time / interval | Wakes counted in the export |
|---|---|---|
| Test at 900 s (49.5 h window: 198 expected wakes, 157 counted) | about 2.16 | about 2.72 |
| Test at 3600 s (73.3 h window: 73 expected wakes, 68 counted) | about 0.99 | about 1.07 |
| Run one (300 s, quiet hours off) | about 1.0 | about 1.0 |
| Run two (60 s, quiet hours off) | about 0.49 | about 0.49 |

Reading. The higher counted-wake cost at 900 s widens the gap with run one and run two instead of narrowing it, so quiet hours do not explain why the cost of a wake is not constant. Limits: the 49.5 h window used for the counts is not the 40.5 h edge-median window of the tool; the currents are rough; the runs do not share a firmware (run one predates the Phase 34 work). The daytime-only mean at 900 s is higher than 8.63 mA because about 6.5 h of each day are spent asleep; it is not computed here.

### Final reading of the 3600 s test, 2026-11-11

Label: arithmetic by Claude with `hardware/logtools.py sleep-trend` on an export read on 2026-11-11 (last reading 16:01 UTC, 3892 mV), rated capacity 3000 mAh, rough curve; nothing here is a current measurement.

- Window: from the first wake at 3600 s (2026-10-31, about 12:10 Paris) to the last reading, about 241 h, 242 wakes counted for 241 expected; 52 of those rows carry no battery reading and the cause was not looked into.
- Average current from 2026-11-01 17:00 UTC to the last reading (233.5 h between end points, 3948 to 3892 mV): 1.29 mA, sensitivity 0.15 mA per 10 mV at the start end point and 0.30 mA at the end one. The later 119.5 h alone also gives 1.29 mA, with a wider sensitivity (about 0.5 mA per 10 mV), so the two windows agree.
- Cost per counted wake, standing draw included: about 1.28 mAh.
- Consequence (rated capacities, no self-discharge or ageing): about 97 days on the 3000 mAh pack and about 323 days on a 10000 mAh pack at 3600 s, against the 180-day allowance of 2.31 mA for 10000 mAh. This is the only interval measured that clears six months; intervals between 900 s and 3600 s were not measured.
- What it does not establish: the new pack was not measured; the 1.29 mA includes this display's redraw cost, so it does not carry over to a smaller screen; the model with one fixed cost per wake still does not fit the 900 s and 3600 s results together (see the two-cadence analysis). Separating the standing draw from the wake energy needs the awake time per wake that Phase 47.1 records.

Owner-reported (2026-11-11): the same small pack is likely to be reused on later frames with much smaller screens. That use is not covered by any figure in this document.

### Caveats

- The discharge curve and the 3000 mAh are ratings, not measurements, and the top of the curve is its least reliable part.
- The 4058 mV first reading and the 4006 mV owner reading of 2026-10-28 19:30 Paris time are not tool inputs; the latter is consistent with the 4008 mV end median.
- Rest-voltage creep after a full charge lowers the apparent draw early in a run (a printed bias).
- Only the 900 s and 3600 s tests on the current 3000 mAh pack are covered. Nothing here concerns the new pack.

## Healthy check-in cadence at the final interval (VAL-01)

Label: real frame, owner export. Interval: 900 s, the final interval chosen by the owner on 2026-11-11.

No new 24 h trial was run after the interval was applied. The cadence is judged on the earlier 900 s test of the old pack, from 2026-10-23 to 2026-10-31 12:02 Paris time (about 8 days on the real frame at 900 s, owner-reported start and end), read from `hardware/logs/val01-final-interval-export.jsonl` (sha256 `c9e29a9115561c30220782023c07d4c1d88c0e4487dd7c1096da45f4da961018`, committed as received). This is a deviation from plan 47-05, which asks for 24 h after the application; the data of the test were judged equivalent by Claude and the owner was told on 2026-11-11.

Command, output saved verbatim in `hardware/logs/val01-final-interval-cadence.txt`:

`python3 hardware/logtools.py checkin-gaps hardware/logs/val01-final-interval-export.jsonl --expect-s 900 --from 2026-10-23T05:00:00+00:00 --to 2026-10-31T11:00:00+00:00 --quiet-start 23:30 --quiet-end 06:00`

Printed lines: 16 quiet-hours gaps set aside; 555 judged gaps; min / median / max gap 301 / 934 / 1253 s; median 934 s, 1.038 times the expected 900 s; gaps within expected to 1.5 times expected 95.7%; gaps above 3 times the expected: 0; `cadence verdict: PASS`.

Two-sided check of plan 47-05: the median is not below the expected interval, so there is no fast-side failure. It is above expected plus 20 s (934 s against 920 s); that is not a failure, it is judged by the printed verdict. The smallest gap of 301 s is the moment the interval changed from 300 s to 900 s at the start of the test, and it is included in the judged gaps.

Battery-critical park: evidence from the run-two history and the automated precedence tests, recorded in the section "Overrides: battery-critical park" above; nothing new was run on the real frame.

Status: PASS at 900 s, with the deviation named above.

## Final decision and pack status (VAL-02)

Owner-reported, 2026-11-11 (chat): final wake interval 900 s ("900 s", chosen from the options 3600 s, 900 s, 300 s, other). Claude recommended 3600 s as the only interval measured to clear six months; the owner chose 900 s. The owner also reported having set the frame to 900 s on the live Device page; no read-back value was reported, and the cadence of 933 s observed at 17:17 Paris time in the export confirms the frame runs at about 15 minutes.

Rationale, as far as it was given: none beyond the choice. Evidence, labelled arithmetic by Claude (rated capacity, rough curve): about 8.63 mA at 900 s from the old-pack test, so about 48 days on a 10000 mAh pack; about 1.29 mA at 3600 s, so about 323 days. 900 s does not reach the six-month target of 180 days on any pack of this range; 3600 s is the only measured interval that does. The worst-case data age at 900 s is about the interval plus the awake time (median gap measured 934 s). The owner knows this.

No value for after the new pack was named. Owner-reported, 2026-11-11 (chat, after the display-off check): "On garde 900": the frame stays at 900 s on the old pack. Labelled arithmetic by Claude (rated 3000 mAh, curve fraction 0.647 at 3890 mV and 0.059 at 3300 mV, about 1764 mAh to the BATTERY EMPTY park, 7.7 to 12.7 days at 9.6 to 5.8 mA, 8.5 days at 8.63 mA): the old pack is expected to reach the park about one to two weeks after 2026-11-11, after which the frame checks in hourly until the new pack is fitted or the pack is recharged.

Pack status: RECEIVED, CHECKS PENDING (`hardware/PACK-ACCEPTANCE.md`; check 4, the first charge, is in progress and not complete). Owner-reported, 2026-11-11: check 1 passed on a photograph, check 2 passed by effect, check 3 passed (the pack lies flat); the pack has been connected since 22:55 Paris time with the old pack disconnected, and check 4, the first charge, is in progress: on 2026-11-12 the LED was steady green (charging, per the EE02 wiki), the Health page read 4088 mV with the USB plugged, nothing was warm; a full charge is not shown. The old-pack measurement ended at about 3886 mV (last reading 22:53).

## What stays open

- Pack acceptance: the polarity match with the board, the free area, and the first charge. Nothing is connected until they pass.
- The interval after the new pack is fitted (900 s is kept on the old pack, owner-reported 2026-11-11, and reaches the park in about one to two weeks, arithmetic).
- The six-month target is not met at 900 s (about 48 days on 10000 mAh, estimate); it is met only at 3600 s in the estimates. The owner chose 900 s.
- VAL-03: open on purpose; the multimeter measurement stays optional (declined 2026-10-23).
- A third controlled discharge on the new pack (deferred), and a measurement with the instrumentation firmware of Phase 47.1, which will separate the standing draw from the wake energy.
- The cause of the row without data at 17:43:22 on 2026-11-11 and of the rows without battery reading in the exports.
