---
phase: quick-260923-gaf
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - companion/battery.py
  - server/poll_loop.py
  - companion/test_companion_app.py
  - server/test_poll_loop.py
  - companion/test_view_pages.py
  - companion/pages/health_page.py
  - companion/pages/config_page.py
  - companion/test_status_pages.py
  - companion/test_config_page.py
  - companion/test_browser_ux_health_drawings.py
  - .planning/seeds/SEED-006-recalibrate-battery-percentage-constants.md
  - hardware/BATTERY-RUN.md
  - .claude/skills/sketch-findings-skypane/SKILL.md
  - .claude/skills/sketch-findings-skypane/references/data-density.md
autonomous: true
requirements:
  - SEED-006
  - QUICK-260923-gaf
must_haves:
  truths:
    - "A reading at or above 4112 mV (a pack fresh off the charger, including the 4122 mV on-charger plateau) reads 100%, and 2946 mV (the last reading the device ever sent in DEVICE-05) reads 0%. This holds in the companion (Home, Health) and in the battery-low push notification."
    - "A 3500 mV reading reads about 15%, which is what the DEVICE-05 run observed. The old linear estimate said 22%, and the rejected endpoints-only fix would have said about 48%."
    - "companion/battery.py and server/poll_loop.py hold the same knot table and return the same percentage for every whole-millivolt value from 2800 to 4400, and for hostile inputs. A harness check enforces this, and a mutation test shows it can fail."
    - "The Health chart's low-battery line sits at 3540 mV. That is 20% on the new curve, derived by inverting the table rather than typed in, and it stays strictly inside the chart's fixed 3000-4200 range. The device's own 3500/3600 thresholds are unchanged."
    - "The battery-life estimate projects days remaining in state-of-charge space along the same curve, not by straight-line millivolt extrapolation. A falling series whose readings are all above the top of the curve reports the FALLING trend with no day count, and never divides by zero."
    - "SEED-006 is marked fulfilled using SEED-003's convention. hardware/BATTERY-RUN.md calibration item 1 records the outcome, the rejected endpoints-only alternative, and why it was rejected."
  artifacts:
    - path: "companion/battery.py"
      provides: "BATTERY_DISCHARGE_CURVE knot table; BATTERY_FULL_MV/BATTERY_EMPTY_MV derived from it; piecewise battery_fraction()/battery_percent(); LOW_BATTERY_DISPLAY_MV derived by _curve_mv_at_percent(); SoC-space battery_life_estimate()"
      contains: "BATTERY_DISCHARGE_CURVE"
    - path: "server/poll_loop.py"
      provides: "_NOTIFY_BATTERY_DISCHARGE_CURVE (same values as the companion's table) and a piecewise _battery_percent_estimate() that performs the same operations"
      contains: "_NOTIFY_BATTERY_DISCHARGE_CURVE"
    - path: "companion/test_companion_app.py"
      provides: "one-home scan retargeted to the curve; +2 checks (curve well-formedness/anchors, server parity); life-estimate check retargeted; EXPECTED_CHECK_COUNT 319"
      contains: "_NOTIFY_BATTERY_DISCHARGE_CURVE"
  key_links:
    - from: "companion/battery.py battery_fraction()"
      to: "BATTERY_DISCHARGE_CURVE"
      via: "clamp at the end knots, then linear interpolation inside the first segment whose upper millivolt value is at or above the reading"
      pattern: "BATTERY_DISCHARGE_CURVE"
    - from: "companion/battery.py LOW_BATTERY_DISPLAY_MV"
      to: "_curve_mv_at_percent(LOW_BATTERY_DISPLAY_PERCENT)"
      via: "inverse lookup on the same table"
      pattern: "_curve_mv_at_percent\\(LOW_BATTERY_DISPLAY_PERCENT\\)"
    - from: "server/poll_loop.py _notify_battery_transition()"
      to: "_battery_percent_estimate() -> _NOTIFY_BATTERY_DISCHARGE_CURVE"
      via: "notify.BATTERY_LOW_BODY interpolates the percent"
      pattern: "_NOTIFY_BATTERY_DISCHARGE_CURVE"
    - from: "companion/pages/config_page.py wake_battery_observed_text()"
      to: "battery.battery_life_estimate()"
      via: "FALLING + days_remaining None already renders WAKE_BATTERY_UNKNOWN_TEXT (config_page.py ~3749-3757)"
      pattern: "battery_life_estimate"
---

<objective>
Replace the linear 3.3-4.2 V battery-percentage estimate with a piecewise millivolt-to-percent lookup table built from DEVICE-05's measured discharge curve (SEED-006). Change both deliberately duplicated homes (companion/battery.py and server/poll_loop.py, D-27) together, prove they agree, and update every consumer, test and doc that depended on the old linear span.

Purpose: the linear estimate is measurably wrong. A full pack reads about 91%. The frame spent its last day alive pinned at 0%. Across the long middle of the discharge, it overstated the remaining charge. The user chose the piecewise curve in chat after seeing the data (LOCKED DECISION, referred to below as D-SEED006). An endpoints-only recalibration was rejected because it still overstates charge mid-curve: 3500 mV would read about 48% when roughly 15% is left.

Output: a curve-based estimate in both homes, a parity check between them, retargeted tests, comments that are true again, and closed-out SEED-006 / BATTERY-RUN.md records.
</objective>

<execution_context>
@$HOME/.claude/gsd-core/workflows/execute-plan.md
@$HOME/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@./.claude/CLAUDE.md
@.planning/seeds/SEED-006-recalibrate-battery-percentage-constants.md
@hardware/BATTERY-RUN.md
@companion/battery.py

Executor notes:
- Runs on the current branch without worktree isolation. Commit per task. Do not stash; see the environment rules.
- Harnesses run from the repo root as `server/.venv/bin/python3 <harness>`. For example, `import server.poll_loop` works from the repo root because `server` is a namespace package.
- Large files: companion/test_companion_app.py (~12k lines), test_view_pages.py, test_status_pages.py, test_config_page.py and health_page.py. Grep for the line numbers cited below and read only the regions around them.

## The knot table (D-SEED006) — authoritative values

Source: hardware/BATTERY-RUN.md `## Discharge Trend` (DEVICE-05, 2026-09-02 12:55 to 2026-09-14 21:05 UTC, 12.340 days, constant 300 s cadence).

Percent = the share of the run's total runtime still ahead at that reading, rounded to an integer. The load was constant, so remaining runtime equals remaining charge.

The planner recomputed these from the timestamps (remaining/total runtime):
93.06, 85.98, 78.84, 71.68, 64.60, 57.45, 50.27, 43.10, 35.98, 28.85, 21.73, 14.52, 7.29, 0.10, 0.00.

| mV   | %   | Source row / note |
|------|-----|-------------------|
| 2946 | 0   | 09-14 21:05, the last reading the device ever sent. 2960 mV at 09-14 20:48 was 0.10% and is merged into this single bottom knot. |
| 3364 | 7   | 09-13 23:29 |
| 3500 | 15  | 09-13 02:04 |
| 3556 | 22  | 09-12 04:44 |
| 3652 | 29  | 09-11 07:39 |
| 3734 | 36  | 09-10 10:32 |
| 3784 | 43  | 09-09 13:26 |
| 3814 | 50  | 09-08 16:12 |
| 3836 | 57  | 09-07 18:56 |
| 3892 | 65  | 09-06 21:46 |
| 3922 | 72  | 09-06 00:48 |
| 3982 | 79  | 09-05 03:36 |
| 4000 | 90  | Plateau: 4000 mV was logged at both 93% (09-03) and 86% (09-04). They are merged into one knot at the midpoint (89.5, rounded to 90) so the table is strictly increasing in millivolts. The error at the plateau is at most about 4 points either way. |
| 4112 | 100 | 09-02 12:55, the first logged reading. The 4122 mV on-charger plateau (Measured Inputs) clamps to 100 as well. |

Both columns are strictly increasing, and the table stays in ascending millivolt order. The millivolt values are the observed readings exactly and are not rounded, so every knot can be traced back to one table row.

## Derived values the planner computed (use them as test anchors)

- Percentages: 4200 → 100, 4112 → 100, 4050 → 94, 4020 → 92, 4000 → 90, 3900 → 67, 3800 → 47, 3750 → 38, 3690 → 32, 3600 → 25, 3540 → 20, 3500 → 15, 3400 → 9, 3300 → 6, 3200 → 4, 3100 → 3, 3000 → 1, 2946 → 0, 2900 → 0.
- LOW_BATTERY_DISPLAY_MV at 20%: 3500 + (5/7)·56 = 3540. Round trip: percent(3540) = 20.
- Life estimate, falling fixture 4020 → 3900 over 6 days, in SoC space: 16 days. Two config_page fixtures keep their current answers: 4100 → 3800 → 3600 over 6 days gives 2 days, and 3600 → 3400 over 2 days gives 1 day.
- Validation against DEVICE-05, from the 3922 mV reading (09-06 00:48) to the 3814 mV reading (09-08 16:12), a 2.64-day window. The SoC projection says 6.0 days left and 6.2 days actually remained. Straight-line millivolt extrapolation to the curve's bottom knot says about 21 days, and to the old linear floor about 12.6 days.

## Existing contracts to preserve
- server/poll_loop.py BATTERY_LOW_THRESHOLD_MV = 3500 and BATTERY_LOW_CLEAR_MV = 3600 must not change. They are the device-side hysteresis.
- health_page.SPARKLINE_Y_MIN_MV = 3000 and SPARKLINE_Y_MAX_MV = 4200 stay as they are. This plan does not change the display window.
- companion/test_companion_app.py `_battery_estimate_has_exactly_one_home` (~line 4054-4133) treats any `def` whose name contains `battery_percent` or `battery_fraction` outside the allow-list as a second estimate. New helper names must avoid those substrings.
- companion/test_status_pages.py (~3209) fails if the literal value of battery.LOW_BATTERY_DISPLAY_MV appears anywhere in health_page.py's raw source, comments included. Never write the new display millivolt value into health_page.py.
- companion/test_config_page.py (~12889) bans the identifiers BATTERY_EMPTY_MV and BATTERY_FULL_MV (and, after Task 2, BATTERY_DISCHARGE_CURVE) from companion/pages code. Comments and docstrings are stripped before that scan.
- Rings draw `battery_percent(mv) / 100` (home_page ~462, health_page ~2896). That is unchanged, so the drawn fraction equals the printed percentage over 100.
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Piecewise curve in both homes, SoC-space life estimate, parity checks, and retargeted value tests</name>
  <files>companion/battery.py, server/poll_loop.py, companion/test_companion_app.py, server/test_poll_loop.py, companion/test_view_pages.py</files>
  <read_first>
    - companion/battery.py (whole file, 340 lines)
    - server/poll_loop.py lines 412-455 (the D-27 duplicated estimate) and 3620-3650 of server/test_poll_loop.py (check #68)
    - companion/test_companion_app.py: 4045-4133 (one-home scan), 6812-7030 (life-estimate check), 880-896 (EXPECTED_CHECK_COUNT convention)
    - companion/test_view_pages.py: 6540-6550, 6588-6650, 7570-7585, 8460-8475
  </read_first>
  <behavior>
    - battery_percent returns each knot's own percent at its millivolt value (all 14 knots).
    - Clamps: battery_percent(4200) == 100 and battery_percent(2900) == 0. battery_fraction(BATTERY_FULL_MV) is exactly 1.0 and battery_fraction(BATTERY_EMPTY_MV) is exactly 0.0.
    - Anchors: 3300 → 6 (the old linear "empty" point, proving the SEED-006 finding is fixed), 3400 → 9, 3500 → 15, 3800 → 47, 4000 → 90, 3750 → 38, 3690 → 32.
    - The refusal domain is unchanged: None, "x", 0 and -1 all give None. NaN now also gives None.
    - LOW_BATTERY_DISPLAY_MV == 3540, battery_percent(LOW_BATTERY_DISPLAY_MV) == LOW_BATTERY_DISPLAY_PERCENT, and health_page.SPARKLINE_Y_MIN_MV < LOW_BATTERY_DISPLAY_MV < health_page.SPARKLINE_Y_MAX_MV. Also poll_loop.BATTERY_LOW_THRESHOLD_MV < LOW_BATTERY_DISPLAY_MV, which pins the relationship the comment states.
    - Parity: battery.BATTERY_DISCHARGE_CURVE == poll_loop._NOTIFY_BATTERY_DISCHARGE_CURVE, and the FULL/EMPTY pairs are equal. battery.battery_percent(x) == poll_loop._battery_percent_estimate(x) for every int x in range(2800, 4401), for a few non-integer floats (3540.5, 3999.9, 4111.99), and for the hostile set (None, "x", "", "3700", 0, -1, True, NaN, inf, -inf).
    - Life estimate, falling fixture 4020 → 3900 over 6 days: days_remaining recomputed inside the test through battery_fraction equals 16. A floor fixture of 3100 → 2900 gives 0. An above-curve fixture of 4200 (oldest) → 4150 (newest) over 6 days gives trend FALLING and days_remaining None.
    - Server check #68 (extended in place): the battery-low body for 3400 mV contains "(≈ 9%)", and poll_loop._battery_percent_estimate(3400) == 9.
  </behavior>
  <action>
RED first. Write or retarget the test expectations below, run the affected harnesses, and confirm the new and retargeted checks fail against the current linear code. Then implement.

companion/battery.py (D-SEED006):
(1) Replace the typed linear FULL/EMPTY pair with a module constant BATTERY_DISCHARGE_CURVE. It is a tuple of the 14 (millivolts, percent) int pairs from the context table, in ascending millivolt order, one pair per line.
- Above the table, write a provenance comment. It should cover: the source section of hardware/BATTERY-RUN.md, the run window, and the constant 300 s cadence; the method (percent is the share of runtime still ahead, and under constant load that equals remaining charge); both merges (the 4000 mV plateau taken at its midpoint, and the tail merged into the 2946 bottom knot); that the 4122 on-charger plateau clamps to 100; and the caveats (one pack, one run, single readings rather than averages, one ambient temperature, so the result is still an estimate and still labelled ≈).
- Also state why the endpoints were not simply moved, per the user's decision: an endpoints-only linear fit on 4112/2946 would read 3500 mV as about 48% when about 15% remained.
- Then define BATTERY_FULL_MV and BATTERY_EMPTY_MV as the last and first knots' millivolt values, indexed from the table and not typed as integers. Keep both names, because callers and the one-home scan use them.

(2) battery_fraction keeps its exact refusal domain, and additionally returns None for NaN (a value not equal to itself) because it is not a number. After that: return 0.0 at or below BATTERY_EMPTY_MV, and 1.0 at or above BATTERY_FULL_MV. Otherwise walk adjacent knot pairs and, in the first segment whose upper millivolt value is at or above the reading, linearly interpolate the percent (lower percent + (value - lower mV) × (upper percent - lower percent) / float(upper mV - lower mV)). Return that percent / 100.0.
- Rewrite its docstring: exact 0.0 and 1.0 at the end knots, every interior knot returns its own percent exactly, and never raises.
- battery_percent keeps its body. Replace the docstring's claim that every earlier input returns byte-identically, which is no longer true. Say instead that SEED-006 changed the underlying curve and the rounding step is unchanged.

(3) Add a private helper _curve_mv_at_percent(percent). The name must not contain the two restricted substrings from the context notes. It inverts the table: find the segment whose percent range contains the target, interpolate millivolts, and return int(round(...)). Raise ValueError outside 0..100; that is an import-time programming error and never user input.
- Set LOW_BATTERY_DISPLAY_MV = _curve_mv_at_percent(LOW_BATTERY_DISPLAY_PERCENT). This yields 3540. Keep LOW_BATTERY_DISPLAY_PERCENT = 20.
- Rewrite the explanatory comment block so every number in it is true. The derived value is 3540 mV, which is 20% on the DEVICE-05 curve.
- The relationship to the device has now flipped. The device's 3500 mV warning point reads about 15% on the curve and sits BELOW the companion's line, so a plotted series crosses the companion's display mark first: about 40 mV earlier, roughly 15 hours at the late-run rate DEVICE-05 observed (3556 → 3500 in about 21 h). Unifying the two thresholds is still a decision nobody has taken, and BATTERY_LOW_THRESHOLD_MV / BATTERY_LOW_CLEAR_MV are untouched.
- The floor constraint: 3540 sits 540 mV above health_page's SPARKLINE_Y_MIN_MV of 3000.
- Remove every mention of the old derived display figure and of the old linear span from this file.

(4) battery_life_estimate keeps its return shape, its five trends, and its millivolt-based RISING/FLAT decisions (LIFE_MIN_OBSERVED_SPAN_DAYS and LIFE_MIN_OBSERVED_DROP_MV unchanged). mv_per_day is still the millivolt slope. For the FALLING branch, replace the millivolt distance-to-empty division with a state-of-charge projection:
- Compute newest and oldest fractions via battery_fraction.
- If the newest fraction is 0.0, days_remaining = 0 (the same floor as before).
- Else if the oldest fraction minus the newest is not positive, days_remaining = None. This happens when both readings sit above the top knot, so no state-of-charge drop is measurable; the trend stays FALLING, and config_page already renders the unknown sentence for that combination.
- Else days_remaining = int(round(newest fraction / ((oldest - newest) / span_days))).
- Add a comment explaining why: the curve's percent is remaining runtime under constant load, so state of charge falls roughly linearly in time while millivolts do not (flat top, cliff at the end). Cite the DEVICE-05 validation numbers from the context (6.0 projected vs 6.2 actual, against about 21 for millivolt extrapolation to the bottom knot).
- Update the docstring. Point 1: DEVICE-05 has run, measured a single cadence, and left the per-wake versus standing-leakage split unresolved, so no per-wake cost is assumed. Update the "None in four of the five states" sentence to cover FALLING with no measurable state-of-charge drop.
- Update the module docstring's "still deferred" sentence: DEVICE-05 completed on 2026-09-14 and is the curve's source.
- Update the LIFE_MIN_OBSERVED_DROP_MV comment's span arithmetic: the curve spans 1166 mV, so 10 mV is under 1% of it.

server/poll_loop.py (D-27 copy, D-SEED006):
- Replace the typed pair with _NOTIFY_BATTERY_DISCHARGE_CURVE. Its pair lines must be textually identical to the companion's (same values, order and formatting).
- Define _NOTIFY_BATTERY_FULL_MV and _NOTIFY_BATTERY_EMPTY_MV by indexing it.
- Rewrite _battery_percent_estimate to perform the same operations in the same order as battery_fraction followed by battery_percent (refusals including NaN, the two clamps, the same segment walk and interpolation expression, then int(round(fraction × 100))). The float results must be identical, not merely close.
- Update the D-27 comment above it: it is now a small knot table plus one clamped piecewise-linear lookup, sourced from hardware/BATTERY-RUN.md, and companion/test_companion_app.py enforces table equality and output parity from 2800 to 4400 mV.
- Do not touch BATTERY_LOW_THRESHOLD_MV or BATTERY_LOW_CLEAR_MV. This module must still import nothing from companion.

companion/test_companion_app.py:
(a) In the one-home scan, add BATTERY_DISCHARGE_CURVE and _NOTIFY_BATTERY_DISCHARGE_CURVE to the two _BATTERY_CONSTANT_HOMES entries, and widen constant_tail so names ending in BATTERY_DISCHARGE_CURVE are also governed, so that a third curve copy fails.
- Keep the third net's legacy 4200+3300 pair. Add the new curve's endpoint pair: the strings 4112 and 2946 appearing together in comment-stripped code outside the two homes also fails. The planner confirmed no non-test companion/server module has both today.
- Update the net's comment and failure text to match. 4200 alone is still innocent (SPARKLINE_Y_MAX_MV).

(b) Directly after that check, add two checks in the harness's own check(label, fn) idiom:
- A curve check covering strict monotonicity of both columns, a first percent of 0 and a last of 100, every knot round-tripping, the clamps, exact 0.0/1.0 at the end knots, the anchors, NaN → None, and the LOW_BATTERY_DISPLAY_MV relations from the behavior list.
- A parity check covering table equality, FULL/EMPTY equality, and the full sweep plus hostile set from the behavior list. Its failure message must name the first differing input and both outputs. poll_loop is already imported at module top as `poll_loop` (line ~73), and health_page is imported too.

(c) Retarget the life-estimate check in place, with no new check() call.
- The falling case recomputes expected days through battery_module.battery_fraction in SoC space (and also asserts that the result equals 16). Update its comment and failure text away from "mV above empty".
- Move the floor fixture to 3100 (oldest) → 2900 (newest), expecting 0.
- Add the above-curve FALLING/None case.

(d) Append an EXPECTED_CHECK_COUNT block after the existing 317 assignment, in the file's convention: a comment naming quick 260923-gaf / SEED-006 (+2: curve well-formedness, server parity), with 317 + 2 = 319 re-derived by running the harness.

server/test_poll_loop.py:
- Extend check #68 (_battery_low_transition_sends_once_with_mv) in place. Assert that the body contains the curve percentage "(≈ 9%)" and that _battery_percent_estimate(3400) == 9. The hand derivation belongs in a comment: 3400 lies between the 3364→7 and 3500→15 knots, so 7 + 8×36/136 = 9.1.
- Update the check label to mention the percentage. EXPECTED_CHECK_COUNT stays 99.

companion/test_view_pages.py, values only (EXPECTED_CHECK_COUNT unchanged):
- The Home render needle for the 3750 mV reading becomes "≈ 38%".
- The ring test's 3690 mV needle becomes "≈ 32%", its 0.43 tolerance anchor becomes 0.32, and its message text and the comment above it (~6593) say 32% of the DEVICE-05 discharge curve.
- The clamp line (~7578) asserts battery_percent(battery.BATTERY_FULL_MV) == 100, battery_percent(4200) == 100, battery_percent(battery.BATTERY_EMPTY_MV) == 0 and battery_percent(2900) == 0, with the message updated.
- Add "BATTERY_DISCHARGE_CURVE", "4112" and "2946" to the home_page banned-token tuple (~8469). home_page.py currently contains none of them.

Mutation proof (do not commit): temporarily change one percent in the server's table by +1, run companion/test_companion_app.py, and confirm the parity check fails and names an input. Restore the value and re-run until green. Record this in the SUMMARY.
  </action>
  <verify>
    <automated>cd /Users/florian/Projects/skypane/.claude/worktrees/airplanes-api-sustainability-a4b703 && server/.venv/bin/python3 -c "from companion import battery as b; import server.poll_loop as p; assert b.BATTERY_DISCHARGE_CURVE == p._NOTIFY_BATTERY_DISCHARGE_CURVE; assert (b.battery_percent(3500), b.battery_percent(3300), b.battery_percent(4112), b.battery_percent(2946), b.LOW_BATTERY_DISPLAY_MV) == (15, 6, 100, 0, 3540); assert all(b.battery_percent(m) == p._battery_percent_estimate(m) for m in range(2800, 4401)); assert b.battery_fraction(float('nan')) is None; assert (p.BATTERY_LOW_THRESHOLD_MV, p.BATTERY_LOW_CLEAR_MV) == (3500, 3600); print('ok')" && server/.venv/bin/python3 companion/test_companion_app.py | tail -3 && server/.venv/bin/python3 server/test_poll_loop.py | tail -2 && server/.venv/bin/python3 companion/test_view_pages.py | tail -2</automated>
  </verify>
  <acceptance_criteria>
    - The one-liner prints ok. companion/test_companion_app.py reports 319/319, server/test_poll_loop.py 99/99, and companion/test_view_pages.py 169/169.
    - `grep -cE '^(_NOTIFY_)?BATTERY_(FULL|EMPTY)_MV = [0-9]' companion/battery.py server/poll_loop.py` returns 0 for both files, because the endpoints are indexed from the table.
    - Stale numbers are gone from the comments too. The comments are what this gate targets, so it deliberately does not filter them out: `grep -cE '3480|3300-4200' companion/battery.py` returns 0. Neither string has any legitimate place in the new file.
    - `grep -c '_curve_mv_at_percent(LOW_BATTERY_DISPLAY_PERCENT)' companion/battery.py` returns 1.
    - `git diff main -- server/poll_loop.py | grep -E '^[-+]BATTERY_LOW_(THRESHOLD|CLEAR)_MV'` prints nothing.
    - The mutation proof is recorded in the SUMMARY: the parity check failed with the perturbed table and passed after restoring it.
  </acceptance_criteria>
  <done>Both homes run the same 14-knot curve and agree exactly. The display threshold is derived as 3540. The life estimate projects in SoC space. The three harnesses pass at their stated counts, and the parity check is shown not to be vacuous.</done>
</task>

<task type="auto">
  <name>Task 2: Make downstream comments true again, extend the pages ban, run the full suite</name>
  <files>companion/pages/health_page.py, companion/pages/config_page.py, companion/test_status_pages.py, companion/test_config_page.py, companion/test_browser_ux_health_drawings.py</files>
  <read_first>
    - companion/pages/health_page.py lines 1068-1090 (the fixed Y-range comment and SPARKLINE_Y_MIN_MV/MAX_MV)
    - companion/pages/config_page.py lines 706-722
    - companion/test_status_pages.py lines 1658-1668
    - companion/test_config_page.py lines 12876-12950
    - companion/test_browser_ux_health_drawings.py lines 500-512
  </read_first>
  <action>
All edits in this task are comments, docstrings and one test ban list. No production behaviour changes (D-SEED006 follow-through).

companion/pages/health_page.py:
- Rewrite the D-04 (A-22) comment above SPARKLINE_Y_MIN_MV. Today it claims the fixed range is the same span the battery estimate uses, and that the axis agrees with the percentage by construction. Neither is true since SEED-006.
- New content: the 3000-4200 range stays a fixed DISPLAY window (19-05's reasons for fixing it still hold). The percentage printed beside the chart now comes from companion/battery.py's BATTERY_DISCHARGE_CURVE, the DEVICE-05 piecewise curve spanning 2946-4112 mV. Equal vertical distances on this chart are therefore not equal percentages, because the curve is flat near the top and steep near the bottom. Readings below 3000 mV, which happen only in the final hours of a discharge, clamp to the chart floor.
- Leave the constants' values unchanged. Do not write the derived display millivolt value anywhere in this file (test_status_pages source scan). Do not add identifiers; the name BATTERY_DISCHARGE_CURVE may appear only inside the comment.
- The "~3000-4200mV is always 4 digits" label-width comment (~1125) remains true because 2946 is also 4 digits. Leave it.

companion/pages/config_page.py (~712-714):
- Replace the clause claiming DEVICE-05 has not run yet. DEVICE-05 ran (hardware/BATTERY-RUN.md) but measured a single cadence and left the per-wake versus standing-leakage split unresolved, so this project still has no per-wake energy cost. The rest of that comment's argument stands.
- Comment-only. Do not introduce the identifiers test_config_page bans.

companion/test_status_pages.py (~1663-1666): update the health-ring fixture comment. 3690 mV now lands on 32% of the DEVICE-05 curve, which is still not a round fraction, so the fixture's purpose holds. The assertion code is value-agnostic; do not change it.

companion/test_config_page.py (~12889): add "BATTERY_DISCHARGE_CURVE" to the banned identifiers tuple, so a page module that reaches into the curve directly counts as a second estimate. Extend the check's docstring and label wording to mention the curve. EXPECTED_CHECK_COUNT is unchanged.

companion/test_browser_ux_health_drawings.py (~506): update the example French legend in the comment to the new derived millivolt value, "Batterie faible — 3540 mV (≈ 20 %)". It is the same length, so the 360px reasoning it supports still holds.

Then run the whole gate: the full suite via ./scripts/run-all-tests.sh (it enforces the coverage fail_under = 83 gate), plus ruff over the repo exactly as CI does.
- If a Playwright browser harness fails, re-run that harness alone. If it still fails, check whether the same check fails on a clean checkout of main before attributing it to this change. Record the outcome either way in the SUMMARY; never dismiss a failure unexamined.
- Finally grep the repo (excluding .planning/phases, .planning/milestones, .planning/quick and .venv) for any remaining non-historical claim of the old linear span, and fix or list each one in the SUMMARY. The SEED-006, BATTERY-RUN and skill docs are Task 3's.
  </action>
  <verify>
    <automated>cd /Users/florian/Projects/skypane/.claude/worktrees/airplanes-api-sustainability-a4b703 && server/.venv/bin/python3 companion/test_status_pages.py | tail -2 && server/.venv/bin/python3 companion/test_config_page.py | tail -2 && server/.venv/bin/ruff check . && ./scripts/run-all-tests.sh 2>&1 | tail -25</automated>
  </verify>
  <acceptance_criteria>
    - test_status_pages reports 316/316 and test_config_page reports all checks passing at its unchanged count. `ruff check .` is clean. run-all-tests.sh exits 0, with the coverage gate passing. Any browser-harness failure is investigated as described and recorded.
    - `grep -c '3.3-4.2V' companion/pages/health_page.py` returns 0.
    - `grep -c 'BATTERY_DISCHARGE_CURVE' companion/test_config_page.py` returns at least 1.
    - `grep -c '3480' companion/test_browser_ux_health_drawings.py` returns 0.
    - `grep -c 'multi-day discharge run is still' companion/pages/config_page.py` returns 0, and `grep -c 'DEVICE-05' companion/pages/config_page.py` returns at least 1 (the rewritten clause still cites the run).
  </acceptance_criteria>
  <done>No comment in the companion or server code still describes the linear span as the estimate. The pages ban covers the curve. The full suite, ruff and coverage are green, or any browser flake is diagnosed and recorded.</done>
</task>

<task type="auto">
  <name>Task 3: Close SEED-006, annotate BATTERY-RUN.md, and refresh the design-system skill's estimator facts</name>
  <files>.planning/seeds/SEED-006-recalibrate-battery-percentage-constants.md, hardware/BATTERY-RUN.md, .claude/skills/sketch-findings-skypane/SKILL.md, .claude/skills/sketch-findings-skypane/references/data-density.md</files>
  <read_first>
    - .planning/seeds/SEED-006-recalibrate-battery-percentage-constants.md (whole file)
    - `git show 6565155 -- .planning/seeds/` for the SEED-003 fulfilled convention
    - hardware/BATTERY-RUN.md lines 510-535
    - .claude/skills/sketch-findings-skypane/references/data-density.md lines 188-206
    - .claude/skills/sketch-findings-skypane/SKILL.md lines 96-98
  </read_first>
  <action>
SEED-006, following SEED-003's convention from commit 6565155: in the frontmatter, change `status: dormant` to `status: fulfilled` and add `resolved_date: 2026-09-23` directly after `planted:`. Append a closing paragraph starting "**Fulfilled — status closed 2026-09-23.**". It should say:
- Quick task 260923-gaf replaced the linear estimate in both homes with the 14-knot piecewise curve derived from `## Discharge Trend`.
- The Scope Estimate's open question was decided in favour of the piecewise curve (user decision, D-SEED006). The endpoints-only alternative was rejected because 3500 mV would have read about 48% against about 15% observed.
- The follow-on effects: LOW_BATTERY_DISPLAY_MV is now derived as 3540 (20%); the device's 3500/3600 thresholds are unchanged; the life estimate now projects in state-of-charge space; and a parity check now enforces the D-27 duplicate.

hardware/BATTERY-RUN.md, `## Calibration & Follow-Up Findings` item 1:
- Fix the dangling placeholder that says the seed is "to be planted" so that it names SEED-006.
- Append an outcome paragraph to item 1, starting "**Outcome (2026-09-23, quick 260923-gaf):**". It should state:
  - The estimate is now a piecewise millivolt-to-percent table (14 knots) built from this section's own Discharge Trend rows. Percent is the share of this run's runtime still ahead, with the 4000 mV plateau merged at its midpoint and the 2960/2946 tail merged into a single 0% knot at 2946.
  - Readings at or above 4112 mV, including the 4122 mV on-charger plateau, now read 100%, and 2946 mV reads 0%.
  - The rejected alternative was recalibrating only the two linear endpoints to 4112/2946. It was rejected because a straight line cannot follow this curve's flat top and end-of-run cliff: 3500 mV would read about 48% when this run shows about 15% remained.
  - The companion's chart line is now derived at 3540 mV (20%) and sits above the device's unchanged 3500 mV warning point (about 15%).
- Leave the pre-registered protocol sections, item 2 and item 3 untouched.

.claude/skills/sketch-findings-skypane/references/data-density.md (~190-205) and SKILL.md (~96-98). The skill is maintained continuously, so bring its estimator facts up to date and leave the surrounding prose alone:
- The estimator's home now holds BATTERY_DISCHARGE_CURVE, with BATTERY_FULL_MV/BATTERY_EMPTY_MV indexed from it (4112/2946).
- LOW_BATTERY_DISPLAY_MV is derived by inverse lookup (3540, and battery_percent(3540) == 20).
- server/poll_loop.py's private copy is _NOTIFY_BATTERY_DISCHARGE_CURVE, and a parity check now enforces it.
- The one-home scan's strongest net now fails on either endpoint pair together in one module: the legacy linear pair, and 4112 with 2946.
- In SKILL.md's ring bullet, the fraction-versus-printed disagreement is now 0.0024 at the 3690 mV fixture, where it was 0.0033 under the pre-SEED-006 linear estimate.

Do not edit .planning/REQUIREMENTS.md or anything under .planning/phases/. They are historical records of what was verified at the time.
  </action>
  <verify>
    <automated>cd /Users/florian/Projects/skypane/.claude/worktrees/airplanes-api-sustainability-a4b703 && grep -c '^status: fulfilled$' .planning/seeds/SEED-006-recalibrate-battery-percentage-constants.md && grep -c '^resolved_date: 2026-09-23$' .planning/seeds/SEED-006-recalibrate-battery-percentage-constants.md && grep -c 'Outcome (2026-09-23, quick 260923-gaf)' hardware/BATTERY-RUN.md && grep -c 'SEED-006' hardware/BATTERY-RUN.md && grep -c 'BATTERY_DISCHARGE_CURVE' .claude/skills/sketch-findings-skypane/references/data-density.md</automated>
  </verify>
  <acceptance_criteria>
    - Each grep above prints at least 1.
    - `grep -c 'SEED-\` (to be planted)' hardware/BATTERY-RUN.md` returns 0.
    - `grep -c '3480' .claude/skills/sketch-findings-skypane/references/data-density.md` returns 0.
    - The BATTERY-RUN.md outcome paragraph names the rejected endpoints-only alternative and the 48%-versus-15% reason.
    - `git diff --stat -- .planning/REQUIREMENTS.md .planning/phases` is empty.
  </acceptance_criteria>
  <done>SEED-006 is closed using the project's convention, the BATTERY-RUN.md finding records its outcome and the rejected alternative, and the design-system skill describes the estimator that actually ships.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| device → server (battery_mv) | The millivolt reading arrives from the frame over the BYOS protocol and is also tailed from Caddy logs. It is untrusted and may be non-numeric, NaN, infinite or hostile. |
| server estimate ↔ companion estimate | Two independently maintained copies (D-27) must never show two different percentages for one reading. |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-gaf-01 | Denial of Service | battery_fraction / _battery_percent_estimate lookup | low | mitigate | The refusal domain covers non-numeric, non-positive and NaN inputs. Infinities clamp at the end knots. The segment walk always terminates. Both functions never raise, and the parity check's hostile set (None, "", "x", True, NaN, ±inf) exercises this in both copies. |
| T-gaf-02 | Tampering (integrity drift) | D-27 duplicated curve in server/poll_loop.py | medium | mitigate | A new harness check asserts table equality and exact output parity for every millivolt value from 2800 to 4400. The one-home scan now also governs *_DISCHARGE_CURVE names and the 4112+2946 literal pair. The mutation proof shows the parity check fails on a one-point drift. |
| T-gaf-03 | Denial of Service | battery_life_estimate SoC projection | low | mitigate | The division only runs when the state-of-charge drop is strictly positive. Otherwise days_remaining is 0 (at or below the bottom knot) or None (no measurable drop above the top knot). Both are covered by the retargeted life-estimate check. |
| T-gaf-04 | Information disclosure | notification body / pages | low | accept | Only the percentage figure changes. The data, recipients and channels are the same, and no new data leaves the system. |
</threat_model>

<verification>
- Both homes run the same 14-knot table and return identical percentages. This is enforced by the new parity check and shown to be non-vacuous by the mutation proof.
- Anchor values hold: 4112 → 100, 3500 → 15, 3300 → 6, 2946 → 0. LOW_BATTERY_DISPLAY_MV is 3540 and sits strictly inside 3000..4200.
- BATTERY_LOW_THRESHOLD_MV and BATTERY_LOW_CLEAR_MV are byte-unchanged at 3500 and 3600.
- ./scripts/run-all-tests.sh passes, including the coverage gate, and `ruff check .` is clean.
- SEED-006 is fulfilled, and BATTERY-RUN.md item 1 carries the outcome and the rejected alternative.
</verification>

<success_criteria>
- D-SEED006 is delivered as a piecewise curve, not an endpoint recalibration, in both companion/battery.py and server/poll_loop.py.
- Every consumer (Home and Health readouts and rings, the chart threshold, the battery-low notification, the battery-life estimate and the config battery sentence) takes its number from the new curve, and the tests assert the new values.
- No comment in the shipped code still claims the linear span or the old derived threshold.
- companion/test_companion_app.py reports 319/319, and the other harnesses report their existing counts.
</success_criteria>

<output>
Create `.planning/quick/260923-gaf-seed-006-piecewise-battery-percentage-cu/260923-gaf-SUMMARY.md` when done. Include the mutation-proof result, the final check counts per harness, and any browser-harness flake diagnosis.
</output>
