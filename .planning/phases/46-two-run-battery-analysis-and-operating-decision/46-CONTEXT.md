# Phase 46: Two-Run Battery Analysis and Operating Decision - Context

**Gathered:** 2026-10-12
**Status:** Ready for planning
**Mode:** Interactive discussion with the owner (French), 2026-10-12

<domain>
## Phase Boundary

Use the two observed discharge runs (run one: 300 s configured, run two: 60 s configured) to
build a two-run model that separates per-wake energy from standing deep-sleep consumption,
state its assumptions and uncertainty, and let the owner choose and apply ONE normal wake
interval plus a retain-or-replace decision for the battery pack (BAT-03, BAT-04, POL-01,
POL-02, POL-03).

Out of scope: measuring image-download or display-refresh energy; time-of-day dependent
intervals (deferred); real-frame validation of the chosen policy (Phase 47); any new
firmware or server feature.
</domain>

<decisions>
## Implementation Decisions

### Interval criterion (POL-01)
- **D-01** When autonomy and freshness conflict, **autonomy wins**: the normal interval is the longest one that stays acceptable, to recharge as rarely as possible.
- **D-02** The owner gave no maximum acceptable interval. The phase therefore **computes the expected autonomy for 5, 10, 15 and 30 minutes** (each with its uncertainty), and the **owner picks the interval at the end** from those figures. The plan must not pick the interval for the owner.
- **D-03** The documented rationale states both sides explicitly: the autonomy gained and the freshness lost (a train can pass between two updates). Today's production value is 300 s (5 min); the companion setting accepts 60..3600 s.
- **D-04** Only ONE normal interval is chosen. A schedule that varies by time of day is a new feature and is deferred.

### Comparing the two runs (BAT-03, BAT-04)
- **D-05** The headline comparison uses **the same battery level at both ends: run one is also counted up to 3300 mV**, taken from its voltage log, because run two stopped at the BATTERY EMPTY park (3300 mV), not at zero. Cycle counts, elapsed time and observed polls are used, per protocol section 5 ("compare like windows").
- **D-06** Run two figures come from `hardware/logs/battery-run2-report.json` (normal-cadence window, ends 2026-10-10T20:33:30+00:00). Its continuity verdict is FAIL (coverage 0.946, largest gap 5.97 intervals) and that is carried into the uncertainty, not hidden or retuned. Run two has no boot-counter witness.
- **D-07** The model states its assumptions and uncertainty in plain terms, and carries a clearly visible section "What this model does not measure": image-download energy and display-refresh energy are NOT measured by the baseline workload, so the chosen interval is an estimate to be confirmed on the real frame in Phase 47 (BAT-04). The owner chose the visible-section form.
- **D-08** Any "rated capacity" used (3000 mAh) is labelled as rated, not measured. Figures printed by the tool (for run two: 0.488 mAh per cycle, 569.5 mAh per day on the normal window) are inputs, not conclusions.

### Battery pack decision (POL-02)
- **D-09** Criteria that can trigger a replacement, in the owner's words: **autonomy at the chosen interval is insufficient**, and **safety and compatibility**. Any replacement must be 1S with built-in protection, JST-PH 2.0 connector with the right polarity, and fit the enclosure; these are not negotiable.
- **D-10** Budget (hardware total under 300 EUR) and percentage calibration are context, not decision triggers; the document may note them but the decision rests on autonomy and safety/compatibility. Correction (2026-10-12, from research): the percentage curve is `server/device_policy.BATTERY_DISCHARGE_CURVE` (14 knots, 2946 mV = 0 %, 4112 mV = 100 %); 3300 mV is only the BATTERY EMPTY park threshold and sits at about 7 % on that curve. An earlier version of this file said 0 % at 3300 mV; that was wrong.
- **D-11** The pack was inspected after run two and found normal (owner-reported, 2026-10-12). The retain-or-replace decision is written as a recommendation for the owner to accept.

### Applying the interval (POL-03)
- **D-12** The selected interval is saved through the companion Device settings and must reach a healthy frame as `sleep_s`; battery-critical (3300 mV, hourly) and display-off (300 s) policies keep precedence, as in `server/wake.py effective_wake_interval_s`.
- **D-13** Checking that a healthy frame receives the value, and that the safety overrides still win, is automated server-side where possible; the on-device confirmation belongs to Phase 47.

### Claude's Discretion
- Exact model form, fitting method and uncertainty method (the owner asked for plain-language results), table layout, and file organisation of the analysis.
- Whether the analysis lives in `hardware/BATTERY-RUN.md` or a new document, and whether a small `logtools.py` subcommand is added to reproduce it (reproducibility is required by the success criteria).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Battery evidence
- `hardware/BATTERY-RUN.md` — run one record and verdict; `## Run 2 Protocol` (section 5 park-window rule, "Known limitations carried to Phase 46"); `## Run 2 Results`; `## Run 2 Run Conditions`.
- `hardware/logs/battery-run2-report.json` — machine-generated run two report.
- `hardware/logs/battery-run2-export.jsonl` — raw run two export (sha256 540d8f56aeab41b3a2de395a4f5820e069a9b4c1f470e526c0df12fc0557efdb).
- `hardware/logs/battery-run2-params.json` — run two parameters.
- `hardware/logs/battery-run-server.log` — run one voltage log (needed for the 3300 mV cut in D-05).
- `hardware/logtools.py` — `run-report`, `check-battery`, `from-history-db`, `reference-interval`.

### Phase 45 and requirements
- `.planning/phases/45-controlled-second-discharge-study/45-VERIFICATION.md` — run two verified; owner accepted the park end.
- `.planning/phases/45-controlled-second-discharge-study/45-CONTEXT.md` — D-01..D-13, comparability limitations.
- `.planning/REQUIREMENTS.md` — BAT-03, BAT-04, POL-01, POL-02, POL-03.
- `.planning/ROADMAP.md` — Phase 46 and Phase 47 goals and success criteria.

### Policy code
- `server/wake.py` — `effective_wake_interval_s` precedence (battery-critical park, display-off cadence, configured interval, default).
- `server/device_policy.py` — quiet hours and wake-interval bounds.
- `companion/battery.py`, `companion/health_signals.py`, `server/device_policy.py` `BATTERY_DISCHARGE_CURVE` — battery presentation and calibration (0 % at 2946 mV, 100 % at 4112 mV, 14-knot curve).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `hardware/logtools.py`: stdlib tooling already parses `device_health` rows and computes cadence and cycle counts; a model subcommand can reuse its parsers.
- `hardware/test_logtools_run2.py`: pattern for testing a subcommand with synthetic rows.

### Established Patterns
- Figures in evidence documents are copied from tool output, never typed from memory; failed gates are reported and diagnosed, never retuned.
- Hypotheses are labelled predictions before data, results afterwards.

### Integration Points
- Companion Device settings page and `server/device_policy.py` carry the configured interval; `server/wake.py` turns it into the `sleep_s` the frame receives.
</code_context>

<specifics>
## Specific Ideas

- The owner wants to see numbers (autonomy for 5, 10, 15, 30 minutes with uncertainty) before deciding.
- Measured so far, as raw inputs only: run one about 328 s mean gap and about 12.3 days; run two about 74 s mean gap and 6148 normal-window polls (about 5.3 days to the park). They are not yet on a like-for-like basis (D-05).

</specifics>

<deferred>
## Deferred Ideas

- Time-of-day dependent wake interval (frequent at commuting hours, rare otherwise): new capability, its own phase.
- A separate fix for two load-dependent companion tests (airline-sheet hit-area 43/44 px, toast auto-hide focus): not part of this phase.

</deferred>

---

*Phase: 46-Two-Run Battery Analysis and Operating Decision*
*Context gathered: 2026-10-12*
