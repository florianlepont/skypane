---
quick_id: 261028-trend
slug: trend-top-of-curve
date: 2026-10-28
type: quick
---

# Quick 261028-trend: summary

## Root cause

`sleep-trend` converts a millivolt fall to charge through the repository curve. Between the
4000 and 4112 mV knots (90 % to 100 %) the curve is about 0.09 % per mV, about 2.7 mAh per
mV on 3000 mAh, and its top knot is a charger-plateau reading, not a point measured on a
falling pack. Run one (`hardware/logs/battery-run-server.log`, 300 s, about 10.1 mA) took
about 15.4 h to fall from a median of 4008 mV to 4000 mV and about 50.3 h to 3982 mV: about
19 mAh per mV. The 900 s export's end points (4022 and 4008 mV) are in that segment, so the
0.39 mA estimate and the band drawn from it were not reliable.

## Fix

- `hardware/logtools.py`: `TREND_CURVE_LIMIT_MV = 4000`; above it (either end-point median)
  the band is `not_applicable` with a "curve not calibrated" sentence, the estimate and the
  charge lines are labelled unreliable, the JSON estimate carries `curve_calibrated`, and
  the 'does not measure' list has a new item. Band keys unchanged; the curve and other
  subcommands untouched.
- `hardware/test_logtools_trend.py`: the synthetic default start fraction moved from 0.92
  to 0.80 so existing cases stay below 4000 mV; new cases for the 4022/4008 situation, one
  end point above, both below (normal band) and the CLI label.
- Corrected outputs saved as `hardware/logs/sleep-trend-900s-output-v2.txt`,
  `...-10000mah-output-v2.txt` and `...-report-v2.json`; the old files are unchanged and
  labelled superseded in `hardware/FIELD-VALIDATION.md`.
- `hardware/FIELD-VALIDATION.md`: VAL-03 is `open`; finding (a) withdrawn with the two facts;
  curve-free comparison (analysis by Claude, rough); raw fall 3.46 mV/day; interval bound
  (a 10000 mAh pack reaches 180 days only at about 13 to 26 minutes or more if wake cost is
  0.49 to 1 mAh and standing draw about zero, not established); re-analysis plan for about
  2026-11-11.
- `hardware/BATTERY-MODEL.md`: point 6 in 'Percentage calibration at the top of the curve'.
- `47-04-SUMMARY.md`: dated correction note; history otherwise untouched.

## Recomputed run-one crossings

Median-of-9 (centred) of X-Battery-Mv, from the first reading below 4060 mV
(2026-09-02T12:58:50Z), first time the smoothed value is at or below the threshold: 4008 mV
after 5.43 h, 4000 mV after 20.86 h, 3982 mV after 55.69 h. Differences 15.43 h and 50.27 h,
matching the quoted 15.5 h and 50 h. If the crossing is instead the point after which the
smoothed value stays at or below the threshold: 19.7 h, 40.6 h, 60.9 h (20.9 h and 41.2 h
differences), so charge per mV is still about 16 to 26 mAh, 6 to 10 times the curve's.

## Verification

`pytest hardware` 144 passed; `ruff check hardware` clean;
`scripts/check_comment_history.py check` exit 0; `python3 hardware/logtools.py selftest` pass.
