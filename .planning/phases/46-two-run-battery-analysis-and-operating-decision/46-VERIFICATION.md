---
phase: 46-two-run-battery-analysis-and-operating-decision
verified: 2026-10-23T00:00:00Z
status: human_needed
score: 2/4 success criteria fully verified, 2/4 partial (owner input outstanding); 0 blockers, 6 documentation warnings
overrides_applied: 0
gaps:
  - truth: "BATTERY-MODEL.md is internally consistent and labels every non-tool figure (BAT-04 honesty, document's own provenance rule)"
    status: partial
    reason: "Later 'Evidence from the parked phase' section contradicts or outdates earlier statements; two figures are mislabelled or unlabelled"
    artifacts:
      - path: "hardware/BATTERY-MODEL.md"
        issue: "see Warnings W1-W6"
    missing:
      - "Fix W1-W6 (small doc edits, no tool or code change)"
human_verification:
  - test: "Read the interval back on the live Device page (Companion > Device) and state the stored value"
    expected: "300 (or whatever is stored); recorded in BATTERY-MODEL.md '## Owner decision' read-back row"
    why_human: "Live production state. Owner said 'Done c'est bon' but the value was never stated."
  - test: "Accept 300 s as provisional and decide when the interval is revisited with the new pack"
    expected: "Explicit owner statement that 300 s provisional satisfies POL-01 for Phase 46, final value deferred to Phase 47 (VAL-03/VAL-01)"
    why_human: "Owner decision. The plan required a rationale 'against the autonomy table'. The recorded rationale is only 'waiting for the replacement battery'."
  - test: "Accept 'replace, Soldered 333290' as the POL-02 decision although the criteria checks are open"
    expected: "Owner accepts, or completes: protection circuit, polarity by multimeter, charge current vs 10000 mAh, free area for 60 x 100 mm, delivery and the reference printed on the pack"
    why_human: "Pack not received. No criterion-by-criterion reason was recorded. Physical checks."
---

# Phase 46 Verification Report

**Phase goal:** The owner can use two observed battery runs to choose and apply one defensible field operating policy.
**Branch/commit verified:** claude/verify-phase46 on origin/main 701440b1
**Status:** human_needed. The machinery and evidence are real and reproducible. The decisions are owner-reported and partly open, and the main document has stale or contradicted statements to fix.
**Re-verification:** No, initial.

## Success criteria

| # | Criterion | Status | Evidence |
|---|---|---|---|
| 1 | Reproducible two-run model separating per-wake and standing energy | VERIFIED | The re-run (command from the doc, `--out` under scratchpad) exited 0 and the output is `cmp`-identical to `hardware/logs/battery-model.json`. Input sha256 values match the table in BATTERY-MODEL.md. `test_committed_model_json_is_reproduced` is in the passing suite. Central fit: wake 0.3378 mAh, standing 7.3045 mA, ratio 166.4626 s. |
| 2 | Assumptions, uncertainty, "does not measure image download / display refresh" | VERIFIED | Tool stdout and JSON carry the assumptions, 108-scenario envelope (14 non-positive), run-two continuity FAIL (coverage 0.946, max gap 5.97 intervals, disclosed not hidden), run-one single-sample dip with median-5/49 sensitivity, and the mandatory "does not measure" block. Doc sections 'Assumptions', 'Uncertainty', 'What this model does not measure' mirror them. |
| 3 | One normal interval with freshness and autonomy rationale, plus retain/replace pack decision against compatibility and calibration criteria | PARTIAL, needs owner | Interval 300 s recorded with the autonomy (11.1843 / 11.1692 d) and freshness (314.0402 s) figures copied correctly. The rationale is only "waiting for battery replacement" and is explicitly provisional. Pack: "replace, Soldered 333290, ordered 2026-10-22" is recorded, but the entry says no reason against the criteria was given. Protection, polarity, charge current and free-area checks are unchecked and the pack is not received. The decision exists but is not shown to be made against the criteria. |
| 4 | Interval saves through Device settings, reaches a healthy frame as `sleep_s`, with battery-critical and display-off precedence | PARTIAL (automated VERIFIED, live apply unconfirmed) | `stub-server/test_wake_interval_delivery.py`: parametrised 60/300/600/900/1800/3600 save -> HTTP `sleep_s`, fallback, re-save, quiet hours never shorten, `test_safety_pins_win_over_saved_interval`, wake.py mirror parity. `server/test_pipeline_e2e.py` asserts exact 3600 while parked and exact 300 on the recovery reply. All pass. The live Device-page save was reported by the owner ("Done c'est bon"); the read-back value was not stated. |

## Requirements

| Req | Status | Note |
|---|---|---|
| BAT-03 | SATISFIED | Tool, committed JSON, byte-identical reproduction, tests. |
| BAT-04 | SATISFIED for the tool and the committed JSON. The doc's later sections weaken consistency (W1-W6). |
| POL-01 | PARTIAL | One interval documented (300 s) with figures. Rationale is provisional and not an autonomy/freshness argument. Needs owner acceptance. |
| POL-02 | PARTIAL | Decision recorded (replace). Criteria table exists, but the decision is not mapped to the criteria and every check is open. Needs owner. |
| POL-03 | Automated half SATISFIED. The live half (read-back) is owner-reported without a value. Needs owner. |

An owner-accepted partial state should be `human_needed`, not `passed`. The test, tool and code halves are done. POL-01..03 close only on an explicit owner statement. 46-04 has no SUMMARY and no checkpoint trail. This is a process gap only. The chat record in '## Owner decision' is acceptable evidence if the owner confirms it.

## Commands run

| Check | Result |
|---|---|
| battery-model re-run to scratchpad | exit 0, byte-identical to committed JSON |
| `server/.venv/bin/python3 -m pytest hardware stub-server/test_wake_interval_delivery.py server/test_pipeline_e2e.py -q --no-cov -n0` | 149 passed |
| `ruff check hardware stub-server server` | All checks passed |
| `python3 scripts/check_comment_history.py check` | exit 0 |
| Autonomy table (4 rows), freshness table, k sweep, d sweep, central fit, run inputs in the doc vs JSON | All match |
| `--intervals 60,300` run | 60 s: 5.2682 / 5.0174 / 6.8385; 300 s: 11.1843 / 11.1692 / 22.5832, as quoted |

## Independent re-derivation of the parked phase

From `battery-run2-export.jsonl` with `server.device_policy.battery_fraction`:

- Peak 3318 mV at 2026-10-11T00:34:20, last 3296 mV at 2026-10-12T16:22:02: HOLDS.
- Span 39.795 h. Fraction 0.06230 to 0.05861. Drop x 3000 = 11.05 mAh, 0.278 mA: HOLDS. The counterfactual 7.3045 mA over that span is 290.7 mAh, 9.7 %: HOLDS.
- "41 wakes": 41 records from the peak to the last, inclusive; that is 40 intervals. The 0.49 mA expected from the wakes alone is 0.490 (40) or 0.503 (41). Immaterial.
- 0.48796 mAh = 3000 / 6148. 0.923 mAh = 3000 / 3252 (BATTERY-RUN.md whole-run figure). Ratio 1.8915, awake ratio 1.9808, 119.5 mA and 125.1 mA: arithmetic holds, but see W2.
- 180 d: 10000 / 4320 = 2.315 mA. Scaled autonomy x 10000/3000: 17.6 / 16.7 / 22.8 and 37.3 / 37.2 / 75.3 d: HOLD. Wake-only averages 5.59 / 2.86 / 1.92 / 0.97 mA and 74 / 146 / 217 / 430 d: HOLD. Break-even for 180 d is about 746 s (12.4 min); "12 to 14 minutes" is loose but safe.
- Six-month currents 0.69 / 1.16 / 1.39 mA and today's 11.2 mA: HOLD.

## Warnings (documentation, BATTERY-MODEL.md)

- **W1. Contradicted by the later section.** 'Six-month target': "above all a much lower standing draw (roughly 1 mA or less)". 'Recommendation for Phase 47': standing draw listed first as the biggest saving. 'Method' presents 7.3045 mA as the central standing figure. The 'Evidence from the parked phase' section argues the standing draw is probably about 0.3 mA or below and that the interval is the lever. The doc needs one reconciled statement. The honest position: the central fit gives 7.3 mA and the parked-phase data point the other way (k near 2.0 in the envelope), and only a measurement settles it (VAL-03).
- **W2. Mislabelled and mismatched figures.** The evidence section calls 0.48796 mAh a "tool figure". No tool output or JSON contains it (it is 3000/6148 typed by hand). 0.923 is unlabelled and comes from BATTERY-RUN.md (whole run to 2946 mV, 3252 polls). It is not like-for-like with run two (to 3300 mV). On the model's own like-for-like basis run one is 3000/2992 = 1.0027 mAh per wake, ratio 2.055 against awake ratio 1.981, so the "scale with awake time" conclusion survives, but the stated ratio 1.892 does not. The doc's preface says every non-labelled figure comes from the JSON, so these two must be labelled "arithmetic by Claude" and the like-for-like value shown.
- **W3. Stale status and preface.** Line 3 "interval and pack decisions pending the owner" and line 5 "does not choose the interval ... those choices are yours" are outdated, since the Owner decision block is filled.
- **W4. Stale recommendation.** 'Recommendation for the owner to accept' ("Retain the current pack if ...") is superseded by the replace decision and is not marked as such.
- **W5. Overstated.** 'Evidence' point 3 says the upper side "is more likely than the central fit". This rests on one parked-phase span with a rest-voltage creep the doc itself says hides drain, on a parked wake profile that is not a normal one, and on a 0.28 versus 0.49 mA mismatch. Say "suggests" and keep the central fit as the committed model output.
- **W6. Minor.** "41 wakes" should read 40 intervals / 41 check-ins. 'Owner decision' says the live apply is "300 is the value the owner restored after run two" (BATTERY-RUN.md records this) but no read-back exists.

No hand-typed figure was found in the autonomy or freshness tables. The 'Six-month target', 'Chosen replacement pack' scaled autonomy and 'Evidence' sections carry the "by Claude" label (the W2 exception aside).

## Planning-file consistency (not edited here)

- ROADMAP: Phase 46 progress row 3/4 "In Progress" and the unchecked 46-04 box are accurate to the files. They should stay so until the owner confirms the items above. Plan 46-04 needs a SUMMARY (or an explicit note that it was handled in chat) before closure.
- REQUIREMENTS: BAT-03 and BAT-04 can move to Complete now. POL-01..POL-03 stay Pending until owner confirmation. VAL-03 is correctly listed under Phase 47 and ROADMAP Phase 47 SC4 matches it.
- STATE.md `stopped_at` and "Status: waiting on the owner for 46-04" are accurate but do not mention the 2026-10-22 pack order. Update with it.
- Phase 47 should inherit: the final interval, the new pack's calibration, the sleep-current measurement.

## Could not verify

- That the owner actually saved the interval on the live Device page, and the stored value (no production access, value never stated).
- Pack identity, protection, polarity, charge current, fit and delivery (pack not received; vendor facts are web-sourced by Claude and not independently checked).
- Real standing current (VAL-03). 7.3 mA versus about 0.3 mA is unresolved.
- Run-one firmware version (the doc says "not recorded").
- Whether Run 2's parked behaviour matches normal wakes.

_Verifier: Claude (gsd-verifier)_

## Documentation warnings W1 to W6 (resolved 2026-10-23)
The six warnings on `hardware/BATTERY-MODEL.md` were fixed after this report: reconciled the standing-draw statements (W1), relabelled the 0.48796 mAh figure as the `run-report` figure and recomputed run one like for like (1.0027 mAh, energy ratio 2.055, awake current about 129.8 mA against 125.1 mA) (W2), updated the status lines (W3), marked the retain recommendation as superseded (W4), softened "more likely" to "may be more likely" (W5), and corrected the wake count to 41 check-ins and 40 intervals (W6). The status stays `human_needed` until the owner items above are answered.
