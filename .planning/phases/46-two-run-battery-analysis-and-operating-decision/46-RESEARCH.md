# Phase 46: Two-Run Battery Analysis and Operating Decision - Research

**Researched:** 2026-10-12
**Domain:** battery-life modelling from two discharge runs (stdlib Python tooling in `hardware/`), policy application through the existing companion -> server -> frame path, and a documented retain-or-replace pack decision
**Confidence:** MEDIUM (inputs and code paths are verified in the repo; the two-run model is only partly identifiable, see Summary)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01** When autonomy and freshness conflict, **autonomy wins**: the normal interval is the longest one that stays acceptable, to recharge as rarely as possible.
- **D-02** The owner gave no maximum acceptable interval. The phase therefore **computes the expected autonomy for 5, 10, 15 and 30 minutes** (each with its uncertainty), and the **owner picks the interval at the end** from those figures. The plan must not pick the interval for the owner.
- **D-03** The documented rationale states both sides explicitly: the autonomy gained and the freshness lost (a train can pass between two updates). Today's production value is 300 s (5 min); the companion setting accepts 60..3600 s.
- **D-04** Only ONE normal interval is chosen. A schedule that varies by time of day is a new feature and is deferred.
- **D-05** The headline comparison uses **the same battery level at both ends: run one is also counted up to 3300 mV**, taken from its voltage log, because run two stopped at the BATTERY EMPTY park (3300 mV), not at zero. Cycle counts, elapsed time and observed polls are used, per protocol section 5 ("compare like windows").
- **D-06** Run two figures come from `hardware/logs/battery-run2-report.json` (normal-cadence window, ends 2026-10-10T20:33:30+00:00). Its continuity verdict is FAIL (coverage 0.946, largest gap 5.97 intervals) and that is carried into the uncertainty, not hidden or retuned. Run two has no boot-counter witness.
- **D-07** The model states its assumptions and uncertainty in plain terms, and carries a clearly visible section "What this model does not measure": image-download energy and display-refresh energy are NOT measured by the baseline workload, so the chosen interval is an estimate to be confirmed on the real frame in Phase 47 (BAT-04). The owner chose the visible-section form.
- **D-08** Any "rated capacity" used (3000 mAh) is labelled as rated, not measured. Figures printed by the tool (for run two: 0.488 mAh per cycle, 569.5 mAh per day on the normal window) are inputs, not conclusions.
- **D-09** Criteria that can trigger a replacement, in the owner's words: **autonomy at the chosen interval is insufficient**, and **safety and compatibility**. Any replacement must be 1S with built-in protection, JST-PH 2.0 connector with the right polarity, and fit the enclosure; these are not negotiable.
- **D-10** Budget (hardware total under 300 EUR) and percentage calibration (0 % assumed at 3300 mV) are context, not decision triggers; the document may note them but the decision rests on autonomy and safety/compatibility.
- **D-11** The pack was inspected after run two and found normal (owner-reported, 2026-10-12). The retain-or-replace decision is written as a recommendation for the owner to accept.
- **D-12** The selected interval is saved through the companion Device settings and must reach a healthy frame as `sleep_s`; battery-critical (3300 mV, hourly) and display-off (300 s) policies keep precedence, as in `server/wake.py effective_wake_interval_s`.
- **D-13** Checking that a healthy frame receives the value, and that the safety overrides still win, is automated server-side where possible; the on-device confirmation belongs to Phase 47.

### Claude's Discretion
- Exact model form, fitting method and uncertainty method (the owner asked for plain-language results), table layout, and file organisation of the analysis.
- Whether the analysis lives in `hardware/BATTERY-RUN.md` or a new document, and whether a small `logtools.py` subcommand is added to reproduce it (reproducibility is required by the success criteria).

### Deferred Ideas (OUT OF SCOPE)
- Time-of-day dependent wake interval (frequent at commuting hours, rare otherwise): new capability, its own phase.
- A separate fix for two load-dependent companion tests (airline-sheet hit-area 43/44 px, toast auto-hide focus): not part of this phase.

Out of scope (domain boundary): measuring image-download or display-refresh energy; real-frame validation (Phase 47); any new firmware or server feature.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| BAT-03 | Two-run model separating per-wake energy from standing deep-sleep consumption from observed elapsed time and cycle counts | Model form, exact inputs and computed values in "Two-Run Model" below; reproducible `logtools.py battery-model` subcommand |
| BAT-04 | Model states assumptions, uncertainty, and the no-download/no-refresh limitation | "Assumptions and Uncertainty", scenario envelope, mandatory "What this model does not measure" section |
| POL-01 | Owner chooses and documents one normal wake interval with freshness and autonomy rationale | Autonomy table for 5/10/15/30 min with spread; owner picks (D-02); document template in Architecture Patterns |
| POL-02 | Retain-or-replace decision with documented criteria | "POL-02 criteria" table: what repo already documents vs what the owner must verify |
| POL-03 | Selected interval round-trips through companion Device settings to `sleep_s` without bypassing battery-critical or display-off precedence | "POL-03 path" trace, existing tests, one real gap (no chained save -> HTTP `sleep_s` test) |
</phase_requirements>

## Summary

The two runs can be put on a like-for-like basis (both counted from the full-charge plateau to the first reading at or below 3300 mV) and give two equations, but they do **not** identify per-wake energy and standing consumption robustly. The model `charge per cycle = E_wake + P_sleep x gap` has three unknowns once the pack's usable capacity is included. Two facts make it workable: (1) if both runs consume the same charge Q between the same two voltage endpoints, `Q` cancels out of the wake-to-standing ratio `E/P = (T1 - T2)/(N2 - N1)`, and the autonomy at any interval `L(g) = (N1*r + T1) * g/(r + g)` (with `r = E/P`) then depends only on observed cycles and elapsed time, not on the 3000 mAh rating. The rating only converts the result to mA and mAh. (2) The identification rests on the assumption that per-wake energy `E` is the same in both runs, and the repo already documents that it is not guaranteed (run one is pre-Phase-34 firmware, 28 s of wake overhead versus about 14 s in run two). That single assumption dominates the spread at long intervals.

Computed from the repo data (reproduced with stdlib, see "Verified Inputs"): with run one cut at its first reading at or below 3300 mV (2992 polls, 11.348 d) and run two's normal window (6148 polls, 5.268 d), the equal-wake-energy fit gives `E/P` about 166 s, `P_standing` about 7.3 mA, `E_wake` about 0.338 mAh (rated-capacity basis), and an autonomy ceiling `Q/P` of about 17.1 days however long the interval. A standing draw of about 7 mA is far above an ESP32-S3 deep-sleep figure; it is whatever is not proportional to wake count, and may be hardware (driver board, regulator, panel leakage) or an artefact of the equal-E assumption. If run one's wake energy was 1.5x run two's, the fitted standing draw falls to about 4.5 mA and the ceiling rises to about 28 days; at 2x it is about 0.5 mA and the ceiling is unbounded in practice. So the 10, 15 and 30 minute autonomies are only bounded from below with confidence (about 13, 14 and 15 days with the equal-E fit); the upper side is open. 5 minutes is close to an observed point (run one, 11.3 d to 3300 mV on older firmware).

**Primary recommendation:** Add a stdlib `battery-model` subcommand to `hardware/logtools.py` (reusing `load_battery_polls` and the run-two report/export) that prints the like-for-like inputs, the equal-E fit, and a scenario envelope (run-one cut rule, run-two cycle count, wake-energy ratio k, usable-capacity ratio, awake overhead) for 5/10/15/30 min; present the **lower bound (k = 1) as the planning figure** and the upper side as "open until Phase 47 measures a wake"; record the result in a new `hardware/BATTERY-MODEL.md`; do not pick the interval or the pack.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Two-run model computation | Offline dev tooling (`hardware/logtools.py`) | Docs (`hardware/BATTERY-MODEL.md`) | Reads committed logs/exports; no runtime component; stdlib only |
| Interval storage | Companion Device settings page (`companion/pages/config_page.py`) | `server/device_config.py` (validation + persistence in `device_config.json`) | Operator setting, bounds 60..3600 |
| `sleep_s` delivery to frame | API/backend `stub-server/byos_server.py` GET `/device/v1/display` | `server/device_policy.py` (constants, hysteresis) | The frame obtains its sleep only from this response |
| Safety precedence (park, display-off, quiet hours) | API/backend (`byos_server` chain) | `server/poll_cycle.py` (latch writer), `server/wake.py` (companion-side mirror) | `wake.effective_wake_interval_s` is a read-side mirror for display; the frame-facing chain is in `byos_server.py` |
| Battery-pack decision | Document (owner decision) | Existing `hardware/BOM.md` | No code |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python stdlib (`json`, `datetime`, `argparse`, `statistics`, `hashlib`) | 3.11.15 in `server/.venv` and `/usr/bin/python3` [VERIFIED: `server/.venv/bin/python3 --version`] | Model subcommand | Project rule: hardware/server tooling is stdlib-only (CLAUDE.md) |
| `hardware/logtools.py` existing helpers | in repo | `load_battery_polls`, `parse_battery_lines`, `BatteryPoll`, `_rows_to_ordered_polls`, `compute_battery_stats`, `compute_reference_interval`, `cmd_selftest` | Reuse; do not re-parse logs |
| pytest (+ xdist, cov) | project venv | Tests in `hardware/test_logtools_*.py` | `testpaths` in `pyproject.toml` already includes `hardware` [VERIFIED: pyproject.toml line 57]; `server/.venv/bin/python3 -m pytest hardware` gives 62 passed in 7 s |

### Supporting / Alternatives
None needed. No numpy/scipy (not in `server/requirements.txt`; would break the stdlib-only rule). No new packages are installed, so the Package Legitimacy Gate does not apply.

## Package Legitimacy Audit

No external packages are recommended or installed by this phase. Packages removed: none. Packages flagged: none. (slopcheck not run: nothing to check.)

## Verified Inputs (reproduced in this session from the committed files)

### Run one (`hardware/logs/battery-run-server.log`, 3252 lines, bracketed `[ISO ts]   telemetry: ... X-Battery-Mv=NNNN`)
Parsed with `logtools.load_battery_polls([...])` [VERIFIED: ran it]. First poll 2026-09-02T12:55:47+00:00 (4112 mV), last 2026-09-14T21:05:53+00:00 (2946 mV).

| Cut rule | Cut poll (UTC) | mV | Polls to cut | Elapsed to cut |
|---|---|---|---|---|
| First reading <= 3300 mV (same rule as run two's `normal_window_end_ts`) | 2026-09-13T21:17:08 | 3292 | 2992 | 11.348 d (980,482 s) |
| Rolling median of 5 <= 3300 | 2026-09-14T08:14:36 | - | 3116 | 11.805 d |
| Rolling median of 11 <= 3300 | 2026-09-14T08:31:08 | - | 3119 | 11.816 d |
| Rolling median of 49 <= 3300 | 2026-09-14T10:24:56 | - | 3139 | 11.895 d |
| Whole run (to 2946 mV, not like-for-like) | 2026-09-14T21:05:53 | 2946 | 3252 | 12.340 d |

**Critical finding (not in CONTEXT.md):** run one's first reading at or below 3300 mV is a single-sample dip. The neighbours are 3366, 3372, 3368, **3292**, 3368, 3372, 3366 (readings 21:01 to 21:32 on 2026-09-13), and 140 readings are <= 3300 overall. A raw "first <= 3300" rule therefore cuts run one about 0.45 to 0.55 day (about 124 to 147 polls) earlier than any smoothed rule. Run two's crossing is clean and monotone (... 3306, 3308, 3304, 3304, **3300**, 3296, then 3312 once parked and unloaded). The park latch (`apply_battery_critical_hysteresis`, `<= 3300`) itself fires on one reading. Recommendation: headline = the same single-reading rule as run two (D-05, symmetric with `run-report`), and carry the smoothed cut as a named sensitivity in the envelope; state this plainly.

Other run-one facts: mean gap whole run 328.0 s (BATTERY-RUN.md); mean gap to the raw 3300 cut 327.8 s; the first readings 4122/4126/4122 mV at 12:56 to 12:58 are on-charger, the pack went on battery about 12:58:50 (a 3 minute, 0.02 % effect on elapsed time, negligible). Firmware `0.1.0-p1` (pre-Phase-34).

### Run two (`hardware/logs/battery-run2-report.json`, export 6193 usable rows, 1 row with `battery_mv` null)
- Normal window: 2026-10-05T14:08:05 to 2026-10-10T20:33:30+00:00 = 5.2677 d (455,125 s), **6148** observed polls, mean gap 74.04 s, configured 60 s, reference 70 s, firmware `fw-v1.0.2` only.
- 0.488 mAh/cycle and 569.5 mAh/day (normal window, 3000 mAh basis) are the tool's inputs (D-08), not conclusions.
- Nominal cycles 6501.8 (against 70 s); observed 6148 (-5.4 %). The 354-cycle shortfall is the continuity FAIL (coverage 0.946). 22 gaps above 210 s, all 381 to 418 s (diagnosis in BATTERY-RUN.md, hypothesis only). Whether those are lost telemetry (real wakes, energy spent, polls unrecorded) or slow wakes is unknown, so the true cycle count lies between 6148 and about 6502. The tool also notes that if the true mean gap is 74 s the nominal-at-70 s count overstates; the envelope should use 6148 (observed, headline) and 6502 (upper) as the two values.
- No boot-counter witness for either run.

### Voltage endpoints
Both runs start at the full-charge plateau (run one about 4122 mV on charger, 4112 first on battery; run two 4110 mV owner-read, 4106 first row). Both are counted to the first reading <= 3300 mV. That identifies "same depth of discharge" only if the voltage under load at wake maps to the same state of charge in both runs; it is an assumption, not an observation (load history, temperature, and an already-cycled pack in run two can shift it).

## Two-Run Model

### Form and exact inputs
Per cycle: `q = E + P * g`, where `g` is the real mean cycle period (configured sleep plus awake overhead), `E` is mAh per wake net of standing, `P` is standing current (mAh per second, shown in mA).

For each run, `Q_run = N_run * E + P * T_run` with:
- `N` = observed polls in the window (the tool's convention), `T` = elapsed seconds first poll to cut poll.
- Run one: `N1 = 2992`, `T1 = 980,482 s` (raw cut).
- Run two: `N2 = 6148`, `T2 = 455,125 s` (report window).
- Unknown `Q` (charge between plateau and 3300 mV), `E`, `P`.

### What is observed versus assumed
| Quantity | Status |
|---|---|
| N1, T1, N2, T2 | Observed (with the cut-rule and continuity uncertainty above) |
| Same Q in both runs (same pack, same endpoints) | Assumed. Plausible: same pack, same cut rule. Risk: second cycle on the pack, temperature, sag at different load history |
| Same E in both runs | Assumed, and the repo itself warns it may be false (firmware changed 2026-09-25, refresh share unknown) |
| Q = 3000 mAh | Rated, not measured; needed only to express E and P in mAh/mA |
| Download and refresh energy | Not measured by the baseline workload (the whole of E is "whatever a poll wake costs on this workload") |

### Solution under the assumptions (equal Q, equal E)
Subtracting the two equations eliminates Q: `E/P = r = (T1 - T2)/(N2 - N1)`. With the headline inputs: `r = 525,357 / 3156 = 166.5 s`. Then `Q/P = N1*r + T1 = 1,478,700 s = 17.11 d`, which is observed-only. With Q = 3000 mAh (rated): `P = 7.31 mA` (0.2 mAh per 100 s), `E = 0.338 mAh`. Check: `6148*0.338 + 7.31*126.4 h = 2078 + 924 = 3002 mAh`. Autonomy to 3300 mV at mean period `g`:

`L(g) = (Q/P) * g / (r + g)` days, with `g = configured + overhead`.

Property worth stating to the owner: **L(g) does not depend on the 3000 mAh rating**, and has a ceiling `Q/P` as g grows. The 3000 mAh sensitivity only scales E and P (and the ceiling is unchanged if the rating is wrong but equal in both runs); an unequal usable Q between runs shifts the ceiling (sweep below).

### Why two runs cannot identify everything
- Two equations, three unknowns (E, P, Q). Equal-Q removes Q only from the ratio; absolute mA needs the rating.
- Identification of `r` is a difference of two similar quantities, `(T1 - T2)/(N2 - N1)`, so small errors in the cut rule or N2 move it a lot (r from 150 to 187 s over the grid below).
- The equal-E assumption is the dominant, non-statistical uncertainty; it cannot be tested with two runs.
- There is no residual to test the model (zero degrees of freedom). Do not report a fit standard error: it would be false precision.

### Honest uncertainty method (simple, reproducible, stdlib)
A **scenario envelope**, not a probabilistic interval: enumerate a small explicit grid, solve the 2x2 system for each combination, report the minimum, central and maximum of `L(g)`. Axes (verified numerically in this session, 108 combinations):
- Run-one cut: raw first <= 3300 (N1 2992) / rolling median 5 (3116) / rolling median 49 (3139), each with its own T1.
- Run-two cycles: 6148 observed / 6501.8 nominal.
- Wake-energy ratio `k = E_run1 / E_run2`: 1.0, 1.5, 2.0 (assumption; Phase 34 documents the no-change wake falling from about 6.3 s to 1.65 s awake). Generalised solve: `N1*k*E + P*T1 = Q`, `N2*E + P*T2 = Q*(1+d)`.
- Usable capacity ratio `d = Q2/Q1 - 1`: -5 %, 0, +5 %.
- Awake overhead added to the configured sleep: 14 s (run two) / 28 s (run one).
A combination whose solution has `P <= 0` (physically impossible; happens when k approaches N2/N1 = 2.05 or more) is reported as "standing draw not distinguishable from zero", not dropped silently (14 of 108 combinations).
Because the mapping of k > 1 raises long-interval autonomy, the minimum of the envelope is attained at k = 1 and is the conservative planning bound; say so, and state that k < 1 (run two's wake costing more than run one's) is not covered because Phase 34 shortened the wake. [ASSUMED: k >= 1]

### Autonomy table (to be regenerated by the tool and copied from its output, never typed)
Values below were computed in this session with the grid above; the plan must regenerate them from the tool. Days to the first reading <= 3300 mV (the park), mean period = configured + overhead.

| Configured interval | Central (k=1, raw cut, N2=6148, d=0) | Envelope min | Envelope max (incl. k=2) | Relation to observed range |
|---|---|---|---|---|
| 5 min (300 s) | 11.2 to 11.4 d (run one itself observed 11.35 d on old firmware) | 11.2 d | 22.6 d | Inside observed gaps (74 s to 328 s) |
| 10 min (600 s) | 13.5 d | 13.1 d | 39.5 d | Outside the observed gap range |
| 15 min (900 s) | 14.5 d | 13.9 d | 53.7 d | Outside |
| 30 min (1800 s) | 15.7 d | 14.8 d | 85.4 d | Outside (about 5.5x the longest observed gap) |

Capacity sweep at k = 1 (d = -10 %, 0, +10 %): ceiling Q/P 15.6 / 17.1 / 18.9 d; autonomy at 30 min 14.6 / 15.7 / 16.9 d. Wake-energy ratio sweep (raw cut): k = 1.0, 1.25, 1.5, 1.75, 2.0 gives P = 7.3, 6.0, 4.5, 2.7, 0.5 mA and ceiling 17, 21, 28, 46, 233 d.

Reading for the owner: going from 5 to 10 minutes adds about 2 days in the cautious reading (the standing draw dominates), and further lengthening buys little (15.7 d at 30 min versus 14.5 d at 15 min) unless the standing draw is actually small, in which case the gain is large. Which of these is true cannot be settled by the two runs; Phase 47 (a real wake on the real frame, ideally with a different interval) or a measured wake current would settle it. Extrapolation beyond 328 s is outside the observed range and the doc must say so.

Autonomy to the park is not autonomy to a dead pack: run one shows about 1 more day between 3300 mV and silence at 2946 mV (11.35 d to 12.34 d total). The park pins the sleep at 3600 s (45 hourly parked polls in run two). The planning figure should be "days to BATTERY EMPTY park" (what the owner will see), labelled as such.

### Field effects not in either run
- **Quiet hours**: production has quiet hours enabled 23:30 to 06:00 (owner-reported; restored after run two). Run two had quiet hours disabled; run one predates or did not record them. During the window the server returns a long `sleep_s` (`quiet_hours_sleep_s`), so about 27 % of the day has no wakes; field autonomy should be somewhat better than the model. This can be added as one formula line (wakes/day = (24 h - 6.5 h)/g) but is a new assumption; keep it as a note unless the owner wants it in the table.
- **Refresh share**: the share of panel-refresh wakes depends on the departure data changing, which is not recorded; a longer interval changes it.
- **Temperature and pack ageing**: unmeasured.

## Architecture Patterns

### Recommended structure
```
hardware/
├── logtools.py              # + battery-model subcommand (+ selftest case)
├── test_logtools_model.py   # new, same pattern as test_logtools_run2.py
├── BATTERY-MODEL.md         # new: reproduction command, inputs, table, "What this model does not measure", interval and pack decisions
├── BATTERY-RUN.md           # unchanged evidence; link to the model doc
└── logs/battery-model.json  # optional machine output committed verbatim (like battery-run2-report.json)
```

### Pattern: a subcommand that reproduces the analysis (follows existing code)
- Parser: add in `_add_run_report_parsers` style (`sub.add_parser("battery-model", ...)`) with positionals/options: run-one log path, `--run2-export`, `--run2-report` (reads `window.normal_window_end_ts`, `reconciliation.observed_normal`, `cadence`), `--cut-mv 3300`, `--capacity-mah 3000` (labelled rated), `--out` JSON, scenario grid defaults as constants, `--intervals 300,600,900,1800`.
- Reuse: `load_battery_polls` for run one; `_rows_to_ordered_polls`/`_load_export_rows` for run two (note the null `battery_mv` row is dropped by the existing loader: 6194 lines, 6193 usable); `RunReportError` and the exit-code convention (0 ok, 2 refused). Exit 2 on: fewer polls than needed, run one never reaching the cut, cut times not after start, `N2 <= N1` (division by zero; the fit needs the faster run to have more cycles).
- Pure functions for the solve (`fit_two_runs(N1, T1, N2, T2, k, d)`), the cut rules (`first_at_or_below`, `rolling_median_cut`) and the envelope, each testable on synthetic numbers with a known answer: generate N and T from chosen E, P, Q and check the solver recovers them (self-consistency), and check `P <= 0` handling.
- Output: plain text table first (owner asked for plain language) and a JSON via `--out`; print sha256 of the inputs as `reference-interval` does; print the assumptions block and the "does not measure" block from constants so they cannot be omitted (test asserts they are printed).
- Keep functions short (the 80-line gate covers only `server`/`stub-server`, but follow it). No plan/phase IDs in comments (`scripts/check_comment_history.py`). Code and docs in English.

### Anti-patterns
- Typing figures into the document from memory (project rule: copy tool output).
- Retuning the run-two continuity gates or hiding the FAIL (D-06).
- Reporting the 17.1 d ceiling or the table as a prediction without the envelope.
- Choosing the interval or pack in the document: leave an owner-decision block with the numbers and a recommendation marked as such (D-02, D-11).
- Treating `Q = 3000` as measured, or presenting P = 7.3 mA as a hardware fact.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Parsing run-one log | New regex | `logtools.load_battery_polls` / `parse_battery_lines` | Existing, tested, handles timestamps/timezone checks |
| Parsing run-two export | New JSON reader | `_load_export_rows` / `_rows_to_ordered_polls` | Handles the null-voltage row and ordering |
| Run-two window and counts | Re-deriving | `battery-run2-report.json` fields | Verbatim tool output, hash-pinned |
| Curve fitting / regression | scipy-style least squares | 2x2 closed-form solve + scenario grid | Zero degrees of freedom; regression would add false precision; stdlib only |
| SoC from mV | New table | `server/device_policy.BATTERY_DISCHARGE_CURVE` if a percentage is needed | Single shared curve |

## Common Pitfalls

### Pitfall 1: Run one's raw 3300 mV cut is a noise dip
Single reading 3292 among 3366-3372. The cut lands about 0.5 day early versus a smoothed cut. Carry both; do not silently pick the more favourable one. Warning sign: cut poll's neighbours more than 50 mV higher.

### Pitfall 2: Treating the equal-E assumption as a fact
Firmware differs between runs (wake overhead 28 s versus about 14 s). At k = 2 the fitted standing draw is about zero. Warning sign: a fitted P outside a plausible range for the hardware, or `P <= 0`.

### Pitfall 3: Mixing windows
Run two's full window (to 16:22 on 2026-10-12, 6193 polls, includes 45 parked hourly polls) must not be combined with run one's. Use the normal window (6148 polls to 2026-10-10T20:33:30) and run one to its own 3300 cut (BATTERY-RUN.md section 5).

### Pitfall 4: Off-by-one and endpoint conventions
N is polls (tool convention), T is first-poll-to-cut-poll seconds. Document the convention; the effect is under 0.05 % but undocumented conventions break reproducibility.

### Pitfall 5: Confusing the two precedence implementations
`server/wake.py effective_wake_interval_s` is the companion's read-side mirror (Home headline, next-wake countdown). The frame's `sleep_s` is computed in `stub-server/byos_server.py` (chain below). A POL-03 test that only exercises `wake.py` does not prove what the frame receives.

### Pitfall 6: Configured interval is not the cadence
Real gap = configured + overhead (14 to 28 s here). Quote both: "5 min (about 5.2 to 5.5 min between polls)".

### Pitfall 7: Quiet hours restored in production
Production interval was restored to 300 s with quiet hours 23:30 to 06:00. Applying a new interval must not disturb quiet hours; the Device form saves several fields (check that a POST of only `wake_interval_s` carries the others forward; `save_device_config` documents `None` carries forward, and `test_wake_interval_s_carries_forward_on_unrelated_save` exists).

## POL-03: path from companion save to the frame's `sleep_s` (verified in code)

1. **Save**: companion Device settings page `companion/pages/config_page.py` (`handle_post`, values["wake_interval_s"] around lines 479 to 574) converts the string to int and calls `server/device_config.save_device_config(state_dir, wake_interval_s=...)`, which validates against `WAKE_INTERVAL_MIN_S = 60` / `WAKE_INTERVAL_MAX_S = 3600` (`server/device_policy.py` lines 164 to 169, inclusive) and atomically writes `device_config.json` under a thread lock plus cross-process `exclusive_lock`. Empty or absent field leaves the stored value unchanged; out-of-range or non-numeric is rejected with `ERROR_WAKE_INTERVAL_RANGE` and nothing is written.
2. **Frame response**: `stub-server/byos_server.py` GET `/device/v1/display` (line about 997) returns
   `sleep_s = quiet_hours_sleep_s( battery_critical_sleep_s( display_off_sleep_s( read_wake_interval_s(state_dir, --sleep), state_dir), state_dir, X-Battery-Mv), state_dir)`.
   - `read_wake_interval_s` reads `device_config.json` fresh each request; bool/string/float/out-of-range/missing/corrupt degrade to the `--sleep` default (`SKYPANE_SLEEP_S`, 30 in `deploy/skypane.env.example`).
   - `display_off_sleep_s`: flat `DISPLAY_OFF_SLEEP_S = 300` when `display_enabled` is false (replaces, does not bound, the configured value).
   - `battery_critical_sleep_s`: flat `BATTERY_CRITICAL_SLEEP_S = 3600` while the latch `battery_critical_active` in `poll_state.json` is set (latch at <= 3300 mV, release at >= 3700 mV; this request's own `X-Battery-Mv` >= 3700 anticipates recovery). Outranks display-off.
   - `quiet_hours_sleep_s`: `max(base, remaining)` inside the quiet-hours window; never shorter than the base.
3. **Mirror (display only)**: `server/wake.effective_wake_interval_s(device_cfg, battery_critical)`: battery_critical -> 3600; `display_enabled is False` -> 300; positive-int `wake_interval_s` -> value; else `env_sleep_s()`; else None. Note `wake.py` does not clamp to 60..3600 whereas `read_wake_interval_s` does; this difference only matters for hand-edited out-of-range files (the Home countdown could show a value the frame does not use).

### Existing tests (VERIFIED by grep; run them to confirm)
| Behaviour | Test |
|---|---|
| String -> int save, rejection paths, empty/absent leaves unchanged | `companion/test_config_page_02.py` (`test_handle_post_wake_interval_*`, line 2103+), `companion/test_config_page_03.py` (lines 68 to 109) |
| Persist bounds, round trip, carry-forward on unrelated save | `server/test_config_history.py` (`test_save_wake_interval_s_round_trips`, `..._rejects_out_of_bounds_and_bools`, `test_wake_interval_s_carries_forward_on_unrelated_save`, `test_normalise_wake_interval_s_bounds_and_bool_gotcha`) |
| Companion form shows stored value over env | `companion/test_companion_app_04b.py` line 288 ff |
| Browser: type value in the Device page and the stored value changes | `companion/test_browser_ux_01.py` lines 372 to 491 (reads `device_config.load_device_config`) |
| Server reads stored value, bounds inclusive, fail-open | `stub-server/test_poll_cycle.py` `test_read_wake_interval_s_happy_path` (60, 120, 3600), `..._fail_open_never_raises` |
| Display-off flat 300 for bases 60, 300, 900, 3600 | `stub-server/test_poll_cycle.py::test_display_off_flat_pin_is_300_regardless_of_base` |
| Battery-critical unit + composed chain (park beats display-off; quiet-hours longer pin wins) | `test_battery_critical_sleep_s_unit`, `test_battery_critical_composed_chain`, constant-parity tests |
| HTTP: 3290 mV check-in parks, GET returns `sleep_s == 3600`; 4100 mV reply is not 3600 | `server/test_pipeline_e2e.py` (lines 395 to 443) |
| `wake.effective_wake_interval_s` / `next_wake_status` precedence | `server/test_config_history.py::test_effective_wake_interval_s_battery_critical_pins_and_wins`, `test_next_wake_status_battery_critical_pins_3600s`; `companion/test_view_pages_04.py` 757 to 855 |
| Decide-hold precedence (poll cycle) | `server/test_poll_cycle_steps.py::test_decide_hold_*` |

### Gaps that need a new test (D-13)
1. **No single test chains the companion save to the HTTP reply.** The pieces are proven separately (save writes `device_config.json`; the server reads a hand-written JSON). Add one server-side test that saves the chosen value through the real save path (`device_config.save_device_config` or `config_page.handle_post`), then does a real GET `/device/v1/display` (use the existing `byos_server_factory`/`park_harness` fixtures in `server/test_pipeline_e2e.py` or the `byos_module` in `stub-server/test_poll_cycle.py`) and asserts `sleep_s` equals the saved value. Parametrise over the candidate set the owner may choose (300, 600, 900, 1800) plus both bounds (60, 3600).
2. **Precedence over the chosen interval via HTTP**: with the same saved value, assert (a) `X-Battery-Mv` 3290 with the latch set gives 3600, (b) `display_enabled=False` gives 300, (c) display-off plus latch gives 3600, (d) the latch does not apply once the same request reports >= 3700 mV and the reply equals the configured value (the existing e2e only asserts `!= 3600`). Use the existing unit-level chain as the model.
3. **Parity**: one test that, for the same matrix of (config, latch), asserts `wake.effective_wake_interval_s(...)` equals the HTTP `sleep_s` outside quiet hours, so the two implementations cannot drift (they currently live in two files).
4. On-device confirmation that the frame took the value stays in Phase 47 (use the poll-to-poll gap check described in BATTERY-RUN.md protocol section 2).

Applying the value in production is an owner action on the live Device page (no code change): type the value, save, read it back; record the read-back in the decision document. The plan must not edit production config itself.

## POL-02: pack decision criteria

What the repo already documents (cite, do not restate as new facts):

| Criterion | Where documented | State |
|---|---|---|
| Chemistry / voltage | `hardware/BOM.md`: "LiPo battery pack, 3.7V, JST-PH 2.0mm 2-pin, protected", Kubii "Batterie 3000mAh Li-Po" | Current pack is 1S LiPo, rated 3000 mAh; price 7.13 EUR HT / 8.55 TTC (looked up 2026-08-04) |
| Protection circuit | BOM title says "protected"; BATTERY-RUN.md protocol required confirmation before run one | The run one last reading 2946 mV is above typical protection cutoffs; whether a protection IC exists was a protocol precondition, not an independent measurement. Owner to confirm |
| Connector and polarity | BOM.md: board JST 2.0 mm, negative pin nearest USB-C, positive farthest; pack JST-PH 2.0 female, red + / black -; gotronic JST-SYP 2.54 rejected; visual/multimeter check before first connection | Documented; a replacement must repeat the check |
| Fit / enclosure | BOM.md: no enclosure exists yet ("Deliberately Not In Phase 1") | **Not documented anywhere**: pack dimensions and enclosure volume must be verified by the owner |
| Charge time | BATTERY-RUN.md run one conditions: about 2 h 50 min to a stable plateau on the board's USB-C charge, USB left connected (source not documented; a wall charger versus power bank assumption is flagged unverified there) | Observed once for 3000 mAh |
| Budget | BOM.md total 207.08 EUR against the 300 EUR ceiling; 92.92 EUR headroom (pack priced inside the ceiling) | Context only (D-10) |
| Voltage calibration | `server/device_policy.py` `BATTERY_DISCHARGE_CURVE`: **14-knot piecewise curve, 2946 mV = 0 %, 4112 mV = 100 %**; low badge 3500 mV (hysteresis 3600), BATTERY EMPTY park 3300 mV (recover 3700) | **Correction to CONTEXT.md/the task brief**: the "0 % at 3300, 100 % at 4200" linear calibration was replaced on 2026-09-23 (quick 260923-gaf); the park threshold is the only 3300 mV constant. The document should state the curve as it is, and that the park (3300) now sits at about 7 % on that curve |

Documented gap list for the owner to verify (do not invent specs or prices): the candidate pack's protection IC (overcharge/over-discharge/short-circuit) and datasheet capacity; connector pitch and housing keying and wire polarity (multimeter); physical dimensions versus the enclosure; recommended and maximum charge current versus the board's charger (the board charge current is not documented in the repo); price and availability at decision time; whether a larger pack changes autonomy more than the interval does (use the table: with a standing-dominated model, capacity scales Q/P linearly, so a 2x pack roughly doubles every autonomy figure; this is arithmetic on the model, not a product claim).

Decision logic (D-09, D-11): retain if the autonomy at the interval the owner picks is acceptable to them using the lower-bound column; otherwise replace subject to the non-negotiables. The inspection result (normal, owner-reported 2026-10-12) supports retain on safety. Write it as a recommendation block "owner to accept". A pack replacement is a purchase and physical action, so the plan should produce a decision record, not an order.

## Code Examples

### Closed-form two-run solve (tested pattern)
```python
# E: mAh-equivalent per wake in units of Q1; P: per second in units of Q1
def fit_two_runs(n1, t1, n2, t2, k=1.0, d=0.0):
    a, b = n1 * k, t1          # a*E2 + b*P = 1
    e, f = n2, t2              # e*E2 + f*P = 1 + d
    det = a * f - b * e
    wake = (f - b * (1.0 + d)) / det
    standing = (a * (1.0 + d) - e) / det
    return wake, standing

def autonomy_days(wake, standing, period_s):
    return period_s / (wake + standing * period_s) / 86400.0
```
Verified in this session against the numbers in this document (k=1, d=0 gives P = 7.30 mA at Q = 3000 mAh and 15.7 d at a 1814 s period). Multiply by the rated capacity only when printing mA or mAh.

### Reproduction commands
```bash
python3 hardware/logtools.py check-battery hardware/logs/battery-run-server.log \
  --interval-s 300 --capacity-mah 3000 --expect-depleted          # run one record
python3 hardware/logtools.py battery-model hardware/logs/battery-run-server.log \
  --run2-export hardware/logs/battery-run2-export.jsonl \
  --run2-report hardware/logs/battery-run2-report.json --out hardware/logs/battery-model.json   # new
```

## State of the Art

| Old approach | Current approach | Impact |
|---|---|---|
| One-run projection band (BATTERY-RUN.md: 12.34-148.08 d at 3600 s) | Two-run equal-E fit with a scenario envelope | Narrows the lower side (about 13 to 16 d for 10 to 30 min) but leaves the upper side open because E equality is untestable |
| Linear 3300/4200 calibration | 14-knot piecewise curve from run one | Percent displays differ from what CONTEXT.md states |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Same usable charge Q between plateau and first <= 3300 mV in both runs | Two-Run Model | Shifts the autonomy ceiling (about +/-1 d per 5 % at 30 min) |
| A2 | Run one's wake energy >= run two's (k >= 1) because Phase 34 shortened the wake | Uncertainty method | If k < 1 the envelope minimum is not a lower bound |
| A3 | Standing consumption is constant with interval (no dependence on gap length, temperature) | Model | Long-interval extrapolation outside observed 74 to 328 s gaps may fail |
| A4 | The gap overhead for long intervals is 14 to 28 s | Autonomy table | Small effect (under 2 % at 30 min) |
| A5 | Production quiet hours (23:30 to 06:00) improve field autonomy; no run had them active | Field effects | Direction only; magnitude not computed |
| A6 | The unrecorded run-two polls (354 vs nominal) were real wakes, so true N2 is 6148 to 6502 | Verified Inputs | If they were not wakes, N2 = 6148 is right and the upper scenario is unneeded |
| A7 | The current pack's protection circuit exists as the BOM states | POL-02 | Safety criterion unverified beyond the listing; owner to confirm |

## Open Questions

1. **Run-one cut rule for the headline.**
   - Known: raw first-<=3300 is a noise dip (cut at 11.35 d); smoothed cuts give 11.80 to 11.90 d.
   - Unclear: which the owner prefers as the headline.
   - Recommendation: raw (symmetric with run two) headline, smoothed in the envelope, both shown.
2. **Is E equal across runs?** Not answerable from the two runs. Recommendation: label the 10/15/30 min upper values "open until Phase 47"; suggest Phase 47 record one extra interval or a current measurement. Do not extend scope here.
3. **Quiet-hours adjustment in the table?** Keep as a note unless the owner asks.
4. **Does the owner want one deliverable or two** (`BATTERY-MODEL.md` plus a decision section)? Recommend one document with an "Owner decision" block left blank for the interval and the pack, completed at the end of the phase after the owner picks.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3 | tool, tests | yes | 3.11.15 (`server/.venv` and system) | - |
| pytest | tests | yes in `server/.venv` only (system python has none) | `server/.venv/bin/python3 -m pytest hardware` -> 62 passed | use `./scripts/run-all-tests.sh` |
| Committed logs/exports | analysis | yes | `battery-run-server.log` (3252 lines), `battery-run2-export.jsonl` (6194 lines), `battery-run2-report.json` | - |
| VPS / frame | none needed | n/a | - | Applying the interval on production is an owner action |

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (+ xdist, cov), Python 3.11 in `server/.venv`; `hardware/` already in `testpaths` |
| Config file | `pyproject.toml` (`[tool.pytest.ini_options]`, `[tool.mypy]` file list, `[tool.coverage.report] fail_under`) |
| Quick run command | `server/.venv/bin/python3 -m pytest hardware -q --no-cov -n0` (7 s) |
| Full suite command | `./scripts/run-all-tests.sh` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| BAT-03 | Solver recovers known E, P, Q from synthetic N, T; Q cancels in ratio; autonomy ceiling = N1*r + T1; `P <= 0` reported not dropped | unit (subprocess or import) | `pytest hardware/test_logtools_model.py -q --no-cov -n0` | No - Wave 0 |
| BAT-03 | Run-one cut: raw rule finds the first <= 3300 reading, smoothed rule differs on a synthetic dip; run never reaching cut exits 2 | unit | same file | No - Wave 0 |
| BAT-03 | Run-two inputs read from the report/export (6148 polls, 455,125 s) and refuse on `N2 <= N1`; reproduces the committed figures from `hardware/logs` | integration on committed logs | same file, marked as reading `hardware/logs` read-only | No - Wave 0 |
| BAT-04 | Output always prints the assumptions block, the rated-not-measured label, the continuity FAIL carry-over, and "What this model does not measure"; table covers 300/600/900/1800 s with min/central/max | CLI output assertion | same file | No - Wave 0 |
| BAT-04 | `BATTERY-MODEL.md` figures equal the tool's JSON (copy, not typed): a check that the committed `battery-model.json` is reproduced exactly by the command | reproducibility test | same file | No - Wave 0 |
| POL-01 | Document contains the 4 intervals with spread and an owner-decision block; no interval pre-selected | behaviour: render/inspect document is a manual review; the tool test above covers the figures | manual (document review) + the tool test | Manual - justify: choice is the owner's |
| POL-02 | Document lists each criterion with source or "owner to verify" | manual document review | manual | Manual |
| POL-03 | Saved interval reaches HTTP `sleep_s`; park/display-off/quiet-hours precedence over it; wake.py parity | integration (real HTTP handler) | `pytest stub-server/test_poll_cycle.py server/test_pipeline_e2e.py -q --no-cov -n0 -k "wake_interval or sleep_s"` | Partial - new chained test needed (Wave 0) |
| All | Hygiene gates | lint/guards | `python3 scripts/check_comment_history.py check`; `ruff check`; mypy per pyproject (add new modules only if hardware is in the mypy list) | existing |

### Sampling Rate
- **Per task commit:** `server/.venv/bin/python3 -m pytest hardware -q --no-cov -n0` plus the touched POL-03 test file
- **Per wave merge:** `./scripts/run-all-tests.sh`
- **Phase gate:** full suite green; `python3 hardware/logtools.py selftest` passes; the committed `battery-model.json` is regenerated byte-identically from the committed inputs

### Wave 0 Gaps
- [ ] `hardware/test_logtools_model.py` covering BAT-03/BAT-04 (synthetic known-answer data + committed-log reproduction)
- [ ] A chained save -> HTTP `sleep_s` test (and precedence matrix and wake.py parity) in `stub-server/` or `server/` (POL-03)
- [ ] Decide whether `hardware/logtools.py` is in the mypy file list (it is currently untyped; do not add it)
- Framework install: none

## Security Domain

`security_enforcement` is true (`.planning/config.json`). Mostly not applicable: no network, auth or new input surface is added.

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | - (companion shared-password auth unchanged) |
| V3 Session Management | no | - |
| V4 Access Control | no | Production config edit stays an owner action in the authenticated companion |
| V5 Input Validation | yes (small) | The new subcommand reads local files only; reject malformed rows with exit 2 (existing `RunReportError` pattern); interval bounds already enforced by `device_config` (60..3600) |
| V6 Cryptography | no | sha256 of inputs via `hashlib`, as `reference-interval` does |

| Threat pattern | STRIDE | Mitigation |
|---|---|---|
| Hostile or corrupt `device_config.json` yielding an unbounded sleep | Tampering / DoS | `read_wake_interval_s` already degrades to default for non-int/bool/out-of-range; keep the test |
| Battery safety (deep discharge, reversed polarity, unprotected cell) | Safety | The park at 3300 mV stays above the cell floor; replacement pack must be protected 1S with a polarity check (BOM.md) |
| Committing the real public host or credentials in docs | Information disclosure | Run one's runs deliberately kept the host out of the repo; keep it so |

## Sources

### Primary (HIGH confidence, files read and numerics re-run in this session)
- `hardware/BATTERY-RUN.md` (run one record, Run 2 Protocol incl. sections 1, 4a, 5, 8, 9, Known limitations, Run 2 Results, Run Conditions)
- `hardware/logs/battery-run2-report.json`, `battery-run2-params.json`, `battery-run-server.log`, `battery-run2-export.jsonl`
- `hardware/logtools.py` (parsers lines 420 to 509, run-report 1268+, reference-interval, parser setup 1638+), `hardware/test_logtools_run2.py`
- `server/wake.py`, `server/device_policy.py`, `stub-server/byos_server.py` (lines 358 to 477, 997 to 1015), `server/device_config.py`
- Test files named in the POL-03 table; `pyproject.toml`; `.planning/config.json`; `hardware/BOM.md`
### Secondary / Tertiary
- None. No web or Context7 sources were needed; the phase is internal arithmetic and policy. No manufacturer specifications were looked up (project rule: do not invent specs or prices).

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH (stdlib; existing helpers verified)
- Inputs and code paths: HIGH (read and re-run)
- Model identifiability and spread: MEDIUM (arithmetic verified; E-equality and capacity-equality are assumptions)
- Pack criteria: MEDIUM (repo-documented items verified; enclosure, protection IC and charge current are owner-to-verify)

**Research date:** 2026-10-12
**Valid until:** stable; revisit if new runs or firmware changes land
