# Phase 47: Integrated Field Validation and Decision Record - Context

**Gathered:** 2026-10-23
**Status:** Ready for planning
**Source:** Decisions taken in the owner conversation of 2026-10-12 to 2026-10-23 (no separate discuss-phase session; every item below was said or accepted by the owner, or is a fact recorded in the repository)

<domain>
## Phase Boundary

Confirm on the real frame that the chosen field policy works, and record it as the operating baseline.

Requirements: VAL-01 (healthy check-in behaviour at the selected cadence, and the battery-critical and display-off overrides still win), VAL-02 (final field operating decision, with any conditional battery-pack change and its validation status), VAL-03 (the frame's sleep current against the six-month target of about 1 mA average or less, with where any excess standing draw comes from, or an explicit statement that the measurement settles it).

Out of scope: new firmware features, a new discharge study, solar, an enclosure design, changes to the companion UI.
</domain>

<decisions>
## Implementation Decisions

### Owner facts and choices (locked)
- Owner is a French speaker and not an engineer. Anything the owner must do is written in plain French, step by step, with what to write down. Repository documents stay in English.
- The owner refused the multimeter-in-series measurement ("je refuse de faire cette manipulation"). `hardware/SLEEP-CURRENT.md` stays as an optional procedure; VAL-03 must be satisfiable without it.
- The substitute for VAL-03 is a long-interval run read from the voltage trend. The owner started a 900 s test on 2026-10-23 at about 06:25 Paris time, pack charged overnight, first reading 4058 mV, USB unplugged. Planned review about 2026-10-28 19:00 Paris time. Quiet hours 23:30-06:00 are on in production (they lengthen wakes at night). The first 24 hours are to be ignored, use medians, and compare the measured average current with the favourable hypothesis (about 1.9 mA at 900 s, 3000 mAh pack) and the central fit (about 8.6 mA).
- Autonomy wins over freshness when they conflict (Phase 46 D-01). Six months between charges is the owner's goal ("je cherche 6 mois").
- Interval: 300 s is provisional while waiting for the replacement pack. The final interval is decided in this phase, from the evidence.
- Replacement pack: Soldered 333290, Li-Po 10000 mAh 3.7 V, 11 x 60 x 100 mm, JST-PH 2 mm, protection stated by the vendor. Ordered 2026-10-22, not yet received. Free depth behind the screen in the IKEA RODALM 30 x 40 cm frame is 18 mm (owner-reported).
- Physical checks owed on receipt (owner): wire polarity by multimeter before the first connection (page does not state it; this is a polarity check, not the refused current measurement), charge current of the board against a 10000 mAh pack, free area for 60 x 100 mm, reference printed on the pack.
- The battery curve is `server/device_policy.BATTERY_DISCHARGE_CURVE` (2946 mV = 0 %, 4112 mV = 100 %; 3300 mV is about 6 %). BATTERY_CRITICAL_MV = 3300 (hourly park, sleep 3600 s), display-off cadence 300 s, wake interval range 60 to 3600 s.
- No production deploy is needed for any evidence work. Never approve or run a production deploy on the owner's behalf.

### Evidence rules (carried from Phases 45 and 46)
- Figures are produced by committed, tested tools or labelled as arithmetic by Claude. Ratings (3000 mAh, 10000 mAh) are not measurements; say so.
- Owner-reported facts are labelled owner-reported with the date.
- Honest uncertainty: the two runs have zero degrees of freedom; the average-current estimate from a voltage trend has known biases (rest-voltage creep, curve and capacity are ratings). The tool and the record must print those caveats.

### Claude's Discretion
- How many plans, their order and waves; the file layout of the evidence under `hardware/`; the exact CLI name of any new `hardware/logtools.py` subcommand.
- Whether the real-frame validation of the overrides (VAL-01 part two) is shown from existing history plus one owner-run check, or by a small scripted check against the stub server, provided the evidence is honest about what ran on the real frame and what did not.
</decisions>

<canonical_refs>
## Canonical References

- `hardware/BATTERY-MODEL.md` - two-run model, owner decision table, six-month target, chosen pack, evidence from the parked phase, "How to check without opening the frame"
- `hardware/SLEEP-CURRENT.md` - optional multimeter procedure and thresholds
- `hardware/BATTERY-RUN.md` - run protocol, run results, continuity gates
- `hardware/logtools.py`, `hardware/test_logtools_model.py`, `hardware/logs/battery-run2-*.json*` - existing analysis tool, tests and committed run data
- `hardware/BOM.md` - battery connector and polarity verification, budget
- `server/device_policy.py` - curve, critical threshold, display-off cadence, quiet hours
- `stub-server/byos_server.py`, `stub-server/test_wake_interval_delivery.py` - how `sleep_s` is computed and tested
- `.planning/phases/46-two-run-battery-analysis-and-operating-decision/46-CONTEXT.md`, `46-VERIFICATION.md`, `46-04-SUMMARY.md`
- `.planning/ROADMAP.md` (Phase 47), `.planning/REQUIREMENTS.md` (VAL-01..03)
</canonical_refs>

<specifics>
## Specific Ideas

- A read-only analysis step over an owner export: average current from the voltage fall over a chosen window, medians, first 24 h ignored, quiet hours handled, printed against the 1.9 mA and 8.6 mA hypotheses and against the 180-day allowances (10000 mAh: 2.31 mA).
- Check-in cadence at the chosen interval measured with the same continuity gates Phase 45 used for run two.
- Owner checkpoints are the long waits: the 900 s data (about 2026-10-28), the pack arrival, and any final interval trial. Plans that wait on them are not autonomous.
- The final record names the interval, the rationale from the evidence, the pack validation status, and what stays open.
</specifics>

<deferred>
## Deferred Ideas

- Solar or wall power; an enclosure; firmware changes to cut the awake time (14.04 s per wake) or the wake count; a third controlled discharge on the new pack (a candidate follow-up if the trend shows the standing draw is low).
</deferred>

---

*Phase: 47-integrated-field-validation-and-decision-record*
*Context gathered: 2026-10-23*
