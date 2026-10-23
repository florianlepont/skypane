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
| VAL-03 | Sleep current against the six-month target of about 1 mA average or less | pending |

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

To be filled by plan 47-04.

## Healthy check-in cadence at the final interval (VAL-01)

To be filled by plan 47-05.

## Final decision and pack status (VAL-02)

To be filled by plan 47-06. The pack checklist is `hardware/PACK-ACCEPTANCE.md`.

## What stays open

To be filled by plan 47-06.
