# Phase 45: Controlled Second Discharge Study - Context

**Gathered:** 2026-10-03
**Status:** Cadence, ceiling, rules and the reference-interval rule for the continuity gates (D-11) CONFIRMED by the owner 2026-10-05; comparability limitations accepted (D-12); nothing is open before the physical run starts
**Mode:** Drafted from SEED-007, SEED-008, `hardware/BATTERY-RUN.md` and REQUIREMENTS BAT-01/BAT-02 (no interactive discussion was held)

<domain>
## Phase Boundary

Produce a second, controlled battery-discharge study of the **same pack** at a materially
different effective wake cadence than the first study (12.34 days at a 300 s cadence,
0.923 mAh/cycle), with comparable normal poll workload, so Phase 46 can fit a two-run model
(per-wake energy vs standing deep-sleep consumption).

This phase delivers the pre-registered protocol, the tooling and checks needed to run and
judge the study, and the recorded evidence once the owner has run it. The discharge itself is
a physical, multi-week owner action; the phase cannot be completed by code alone.

Out of scope: the two-run model and the interval/pack decision (Phase 46), production cadence
changes, image-download/display-refresh energy measurement.
</domain>

<decisions>
## Implementation Decisions

### Locked by requirements
- **D-01** Same pack as run one (Kubii 3000 mAh 1S LiPo), same firmware family and server poll workload; only the effective wake cadence differs materially (BAT-01).
- **D-02** Evidence recorded per BAT-02: actual cadence, firmware and server baseline, observation window, battery endpoints, raw observation export, continuity evidence and voltage-validity evidence as **separate** checks.
- **D-03** Reuse run one's observation channel (`history.db`, `hardware/logtools.py check-battery`, `from-history-db`) and its validity gates (`--min-coverage 0.95`, `--max-gap-intervals 3`, `--min-mv-drop 100`, `--cutoff-mv 3400`), pre-registered before the pack is connected.
- **D-04** The interval is set through the companion Device wake-interval setting (no SSH edit); the value actually in force is recorded and is what the checker is given.

### CONFIRMED by the owner on 2026-10-05 (in chat)
- **D-05 Cadence: 60 s** (CONFIRMED 2026-10-05). Changed from the proposed 900 s. Rationale (owner): the real field wake interval is close to 60 s or even 30 s, so the second run must sit near real use, in the wake-dominated regime, not far from it. The two-run fit then interpolates toward the field interval instead of extrapolating from 300 s and 900 s. Alternatives considered: 900 s (the original proposal: far from the field interval, and a 34-day run), 1800 s (rejected: could last about 67 days if wake-dominated), 600 s (between the two, still far from the field interval), 30 s (left out, see Deferred). 60 s is the minimum the Device setting accepts (`WAKE_INTERVAL_MIN_S`). The effective cadence is the measured mean poll-to-poll gap, not 60 s: the wake itself adds time (see the Run 2 Protocol, section 2).
- **D-06 Ceiling: 21 days** (CONFIRMED 2026-10-05), the same as run one. Changed from the proposed 45 days. An undepleted run at the ceiling is still a valid bound result. At 60 s a depletion is expected well inside the ceiling under every hypothesis (see the Protocol predictions).
- **D-07** (CONFIRMED 2026-10-05) Post-Phase-34 firmware (DHCP, TLS reuse, battery sampling) is the baseline; firmware version and server revision are recorded at start. The firmware is frozen during the run; if it changes the run is invalid and restarts. Same pack and firmware family as run one.
- **D-08** (CONFIRMED 2026-10-05) Cycle count is reconciled three ways as in run one: nominal from elapsed span, observed polls in the server log, and the device NVS boot-counter delta. `boot_count_start` is recorded before the cable comes out.
- **D-09** (CONFIRMED 2026-10-05) After the run the production wake interval is restored to the value in force before the study, and the restore is recorded. The display stays enabled with no quiet hours during the run.
- **D-10 Park-window rule** (CONFIRMED 2026-10-05, raised by the planner). The BATTERY EMPTY park at 3300 mV changes the real cadence to hourly. Continuity and coverage are judged on the normal-cadence window, which ends at the first reading at or below 3300 mV; the full window is reported as informational; the boot-counter witness covers the full window.
- Thresholds unchanged (D-03): 0.95 / 3 / 100 mV / 3400 mV.
- **D-11 Reference interval for the continuity gates** (CONFIRMED 2026-10-05, was O-1). The coverage and largest-gap gates are judged against `reference_interval_s`: the configured interval plus the wake overhead measured over the FIRST 48 HOURS of the run, i.e. the mean poll-to-poll gap over those 48 h excluding gaps above 3x the configured interval, rounded to whole seconds. It is frozen in the params file (with a source note) and committed BEFORE any continuity verdict is computed; coverage against the configured 60 s is still reported, as information only. Only the denominator and gap unit move; the thresholds stay as above. Implemented by `logtools.py reference-interval` and the optional `reference_interval_s` params field of `run-report` (Protocol section 4a).
- **D-12 Accepted comparability limitations** (owner, 2026-10-05). Run two uses post-Phase-34 firmware while run one predates it, and the share of panel-refresh wakes is unknown and may differ from run one; no static-image workaround. Both are recorded in the Protocol under "Known limitations carried to Phase 46" and Phase 46 must carry them into the model, not hide them.

### RESOLVED - was open before the pack could be connected
- **O-1 Reference interval for the continuity gates** is answered: see D-11. At 60 s the wake overhead makes the real gap about 62 to 100 s, so coverage against the bare 60 s would have failed the 0.95 gate structurally, whatever the pack does; the frozen reference interval removes that without touching a threshold.

### Claude's discretion
- Shape of the evidence export and any helper added to `hardware/logtools.py`, provided the three reconciliations and separate continuity / voltage-validity verdicts are produced from the raw export.
</decisions>

<canonical_refs>
## Canonical References

- `hardware/BATTERY-RUN.md` — run one: protocol, thresholds, observation channel, "What This Figure Does Not Cover", calibration findings
- `hardware/logtools.py` — `check-battery`, projection band, `from-history-db`
- `hardware/BOM.md` — pack, connector and budget constraints
- `.planning/seeds/SEED-007-second-discharge-run-separate-wake-vs-leakage-energy.md`
- `.planning/seeds/SEED-008-choose-real-field-wake-interval.md`
- `.planning/REQUIREMENTS.md` — BAT-01, BAT-02
- `companion/settings/wake_interval.py` — web-configurable wake interval
</canonical_refs>

<specifics>
## Specific Ideas

- Pre-register the protocol (cadence, ceiling, thresholds, expected outcomes under both hypotheses) in a new `## Run 2 Protocol` section **before** the pack is connected, as run one did.
- Physical preconditions unchanged: pack fully charged, polarity checked, protection circuit confirmed.
</specifics>

<deferred>
## Deferred Ideas

- Solar-charging reconsideration (gated on Phase 46's result).
- Measuring image-download / display-refresh energy (explicit limitation of the baseline workload, BAT-04).
- **A 30 s cadence run.** The owner named 30 s as possibly the true field interval. It is left out of this phase: the Device wake-interval setting's minimum is 60 s (`WAKE_INTERVAL_MIN_S` in `server/device_policy.py`), and lowering it is a production cadence change outside this phase. At 30 s the device would also be awake almost permanently, given about 28 s of wake overhead measured in run one. The reasoning that makes this acceptable: the two-run fit (Phase 46) is a model of per-wake energy plus standing consumption, so a 60 s run and a 300 s run constrain it at the field interval by interpolation, and 30 s is a short extrapolation beyond the 60 s end, not a leap.
</deferred>
