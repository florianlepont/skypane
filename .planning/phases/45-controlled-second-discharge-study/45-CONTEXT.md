# Phase 45: Controlled Second Discharge Study - Context

**Gathered:** 2026-10-03
**Status:** Ready for planning — decisions marked **PROPOSED** need owner confirmation before the physical run starts
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

### PROPOSED — owner to confirm before the run
- **D-05 Cadence: 900 s** (3x run one). Per-cycle cost is E_wake + I_sleep x T, so a wake-dominated pack lasts about 3250 cycles whatever T is (about 34 days at 900 s) and a leakage-dominated one about 11 days; both outcomes are separable from run one. 1800 s was considered and rejected as default: it could last about 67 days if wake-dominated.
- **D-06 Ceiling: 45 days** instead of run one's 21, because a 900 s run that is wake-dominated would otherwise end undepleted and yield only a bound. An undepleted run at the ceiling is still a valid (bound) result, as in run one.
- **D-07** Post-Phase-34 firmware (DHCP, TLS reuse, battery sampling) is the baseline; the firmware version and server revision are recorded at start. If firmware changes mid-run the run is invalid and restarts.
- **D-08** Cycle count is reconciled three ways as in run one: nominal from elapsed span, observed polls in the server log, and the device NVS boot-counter delta.
- **D-09** After the run the production wake interval is restored to the value in force before the study, and the restore is recorded.

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
</deferred>
