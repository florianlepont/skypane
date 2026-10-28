---
quick_id: 261028-trend
slug: trend-top-of-curve
date: 2026-10-28
type: quick
---

# Quick 261028-trend: sleep-trend draws no band above the curve's calibrated range

The 2026-10-28 run of `sleep-trend` on the 900 s export (end medians 4022 and 4008 mV,
0.39 mA, `at_or_below_allowance`) was recorded as VAL-03 outcome (a). Both end points lie
between the curve's 4000 and 4112 mV knots, which was never calibrated against a discharge,
and run one's own readings show about 19 mAh per mV there against about 2.7 mAh per mV on
the curve. The finding is unreliable.

## Tasks

1. Test-first, `hardware/logtools.py` `sleep-trend`: when either end-point median is above
   `TREND_CURVE_LIMIT_MV` (4000) the band is `not_applicable` with a sentence saying the
   curve is not calibrated there; the estimate is printed labelled unreliable; the
   'does not measure' list gains an item. JSON band keys and the 47-04 mapping unchanged.
   Synthetic cases only, including the 4022/4008 situation and a case below 4000 mV.
2. Re-run the corrected tool on the committed export; save verbatim outputs as `-v2`
   files; keep the old outputs and label them superseded.
3. Rewrite the VAL-03 status row and section of `hardware/FIELD-VALIDATION.md`: open,
   finding (a) withdrawn, curve-free comparison labelled as analysis, honest interval bounds.
4. Add the run-one comparison as point 6 of 'Percentage calibration at the top of the
   curve' in `hardware/BATTERY-MODEL.md`.
5. Dated correction note at the top of `47-04-SUMMARY.md`.

Out of scope: the curve, other subcommands, the plan 47-04 files other than the note.

## Verification

`pytest hardware`, `ruff check`, `scripts/check_comment_history.py check`,
`python3 hardware/logtools.py selftest`; run-one crossing times recomputed from the log.
