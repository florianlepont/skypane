# Roadmap: SkyPane

## Milestones

- [x] **v1.0 — MVP** — shipped and archived on 2026-09-30. The complete phase plan and its evidence are in [milestones/v1.0-ROADMAP.md](milestones/v1.0-ROADMAP.md), [milestones/v1.0-REQUIREMENTS.md](milestones/v1.0-REQUIREMENTS.md), and [milestones/v1.0-MILESTONE-AUDIT.md](milestones/v1.0-MILESTONE-AUDIT.md).
- [ ] **v1.1 — Battery and Companion!** — Phases 44–47. Measure real battery behaviour, set a field operating policy, polish the companion from observed use, and validate the result on the frame.

## Overview

V1.1 begins by improving the companion through a task-based bilingual usability review and only the highest-value confirmed fixes. In parallel with that product work, a second controlled discharge study provides the missing evidence to separate wake consumption from deep-sleep leakage; the two-run analysis then determines the normal wake interval and whether the current battery pack remains appropriate. The milestone closes when the selected policy is observed on the real frame and recorded as the new operating baseline.

## Phases

**Phase Numbering:**
- Integer phases are planned milestone work.
- Decimal phases are urgent insertions created only when needed.

- [x] **Phase 44: Companion Walkthrough and Focused Bilingual Polish** - Resolve the highest-value observed companion friction without a redesign. (completed 2026-10-04, owner-validated)
- [x] **Phase 45: Controlled Second Discharge Study** - Produce reproducible, comparable alternate-cadence battery evidence.
- [x] **Phase 46: Two-Run Battery Analysis and Operating Decision** - Derive the model and select the field cadence and pack policy.
- [x] **Phase 47: Integrated Field Validation and Decision Record** - Confirm the policy on the real frame and publish the operating baseline. Closed 2026-11-11: VAL-01 validated, VAL-02 recorded with the pack validation open, VAL-03 open on purpose.

## Phase Details

### Phase 44: Companion Walkthrough and Focused Bilingual Polish
**Goal**: The owner can complete the companion's daily flows with walkthrough-proven usability fixes in English and French.
**Depends on**: Phase 43
**Requirements**: CMP-01, CMP-02, CMP-03, CMP-04
**Success Criteria** (what must be TRUE):
  1. The owner can complete and review a recorded task-based walkthrough of Home, Display, Flights, Airlines, Health, Device, and Update in English and French at desktop and narrow-mobile widths.
  2. Every observed walkthrough issue has a reproducible trigger, user-impact assessment, and a recorded keep, fix-now, or defer decision.
  3. The owner can use every V1.1-changed companion flow with matching English and French meaning, responsive layout, semantic controls, visible keyboard focus, and clear saved or error feedback.
  4. Confirmed high-value findings are resolved through the established route, page-context, template, static-asset, and i18n boundaries.
**Plans**: 12/12 plans complete (completed 2026-10-04: automated evidence green, owner validated the deployed companion by their own statement)
**UI hint**: yes

### Phase 45: Controlled Second Discharge Study
**Goal**: The owner can reproduce a second battery-discharge study whose evidence is comparable to the first study and usable for a two-run model.
**Depends on**: Phase 43
**Requirements**: BAT-01, BAT-02
**Success Criteria** (what must be TRUE):
  1. The owner can run the current pack through a second controlled discharge at a materially different effective wake cadence while retaining a comparable normal poll workload.
  2. The recorded study identifies its actual cadence, firmware and server baseline, observation window, battery endpoints, and raw observation export.
  3. The owner can inspect separate continuity and voltage-validity evidence for the completed observation window.
**Plans**: 4 plans

Plans:
- [x] 45-01-PLAN.md — Run 2 Protocol pre-registered and CONFIRMED by the owner 2026-10-05 (60 s cadence, 21-day ceiling, park-window rule); the reference interval for the continuity gates (D-11) also CONFIRMED 2026-10-05
- [x] 45-02-PLAN.md — logtools `run-report`: raw export, separate continuity / voltage-validity / baseline verdicts, three-way cycle reconciliation, with tests
- [x] 45-03-PLAN.md — Owner ran the physical discharge (disconnect 2026-10-05T14:08Z, 60 s cadence); start values, the 48 h reference-interval freeze (70 s, 2026-10-08) and the end/restore record are in `hardware/BATTERY-RUN.md`. Stopped by the owner at the BATTERY EMPTY park on 2026-10-12, not at 0 %; production interval 300 s and quiet hours 23:30-06:00 restored
- [x] 45-04-PLAN.md — `run-report` run on the owner-supplied export; `## Run 2 Results` recorded from its output. Continuity FAIL (coverage 0.946, largest gap 5.97 intervals; diagnosed, thresholds not retuned), voltage validity PASS, baseline PASS

### Phase 46: Two-Run Battery Analysis and Operating Decision
**Goal**: The owner can use two observed battery runs to choose and apply one defensible field operating policy.
**Depends on**: Phase 45
**Requirements**: BAT-03, BAT-04, POL-01, POL-02, POL-03
**Success Criteria** (what must be TRUE):
  1. The owner can reproduce a two-run model from observed elapsed time and cycle counts that separates per-wake energy from standing deep-sleep consumption.
  2. The model states its assumptions, uncertainty, and the fact that the baseline workload does not measure image-download or display-refresh energy.
  3. The owner can document one normal wake interval with its freshness and autonomy rationale, plus a retain-or-replace battery-pack decision against compatibility and calibration criteria.
  4. The selected interval saves through Companion Device settings and reaches a healthy frame as `sleep_s` while battery-critical and display-off safety policies retain precedence.
**Plans**: 4 plans

Plans:
- [x] 46-01-PLAN.md — `logtools.py battery-model`: like-for-like two-run solve (both runs to the first reading at or below 3300 mV), 108-scenario envelope, autonomy for 300/600/900/1800 s, mandatory assumptions / continuity-FAIL / "does not measure" blocks, refusals, tests (wave 1)
- [x] 46-02-PLAN.md — POL-03 tests: companion save -> HTTP `sleep_s` for 60..3600 candidates, park/display-off precedence over HTTP, exact recovery value, `wake.py` parity (wave 1)
- [x] 46-03-PLAN.md — Committed `battery-model.json` with byte-identical reproduction test; `hardware/BATTERY-MODEL.md` with autonomy table, uncertainty, limitations, pack criteria and a blank owner-decision block (wave 2)
- [x] 46-04-PLAN.md — Owner chooses the interval and the pack, applies the interval on the live Device page; decisions recorded (wave 3, owner checkpoints). Done 2026-10-23: interval 300 s accepted as provisional, live Device page read back as 900 s (the value set for the 900 s test), pack Soldered 333290 accepted (ordered 2026-10-22); the pack's physical checks move to Phase 47

### Phase 47: Integrated Field Validation and Decision Record
**Goal**: The selected field policy is confirmed on the real frame and recorded as the current operating baseline.
**Depends on**: Phase 44, Phase 46
**Requirements**: VAL-01, VAL-02, VAL-03
**Success Criteria** (what must be TRUE):
  1. The owner can confirm on the real frame that the selected cadence produces the expected healthy check-in behaviour.
  2. The real-frame validation confirms that battery-critical and display-off safety overrides still take precedence over the normal cadence.
  3. The project records the final wake-interval decision, its evidence-based rationale, and the validation status of any battery-pack change.
  4. The sleeping frame's current is estimated from the battery-voltage trend of a long-interval run on the real frame and recorded against the six-month autonomy target (about 1 mA or less on average); the record says whether the standing draw is near the modelled 7 mA or far lower, and what that means for reaching six months. This criterion is satisfied only by outcome (a) (estimate at or below the favourable hypothesis) or (b) (estimate above the central hypothesis), where the trend settles the question; under outcome (c) (estimate between the two hypotheses, or the estimate not applicable) the finding is recorded plainly and VAL-03 stays open on purpose. The multimeter procedure in `hardware/SLEEP-CURRENT.md` stays optional (the owner declined it on 2026-10-23). See `hardware/BATTERY-MODEL.md`, section "Six-month target".
**Plans**: 6 plans

Plans:
- [x] 47-01-PLAN.md — `logtools.py sleep-trend`: average current from the voltage fall of an owner export (first 24 h ignored, medians, quiet hours handled), printed against the 1.9 mA and 8.6 mA hypotheses and the 180-day allowances, fixed band keys, mandatory bias caveats, refusals, synthetic-data tests (wave 1)
- [x] 47-02-PLAN.md — `logtools.py checkin-gaps`: healthy cadence against an expected interval with the Phase 45 gates, quiet-hours gaps set aside, `--skip-first-gaps` for display-off; battery-critical park evidence from run-two history and the existing precedence tests (wave 2)
- [x] 47-03-PLAN.md — `hardware/PACK-ACCEPTANCE.md` (status NOT RECEIVED), `hardware/FIELD-VALIDATION.md` evidence skeleton, plain-French owner steps with one pinned export route (wave 1)
- [x] 47-04-PLAN.md — Owner's 900 s export run through `sleep-trend`; VAL-03 finding recorded by the fixed band mapping (wave 3, owner checkpoint, due about 2026-10-28)
- [x] 47-05-PLAN.md — Owner chooses the final interval; 24 h cadence trial and display-off window measured with `checkin-gaps` (wave 4, owner checkpoints)
- [x] 47-06-PLAN.md — Final decision, pack validation status and per-requirement closing record; final interval in the precedence-test tuples; roadmap criterion and VAL-03 wording amended (wave 5, owner checkpoint)

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 44. Companion Walkthrough and Focused Bilingual Polish | v1.1 | 12/12 | Complete | 2026-10-04 |
| 45. Controlled Second Discharge Study | v1.1 | 4/4 | Complete | 2026-10-12 |
| 46. Two-Run Battery Analysis and Operating Decision | v1.1 | 4/4 | Complete | 2026-10-23 |
| 47. Integrated Field Validation and Decision Record | v1.1 | 6/6 | Complete 2026-11-11 (pack validation and VAL-03 open on purpose, see hardware/FIELD-VALIDATION.md) | 2026-11-11 |
| 47.1. Wake-energy instrumentation and awake-time reduction | v1.1 | 7/9 | In Progress|  |
| 47.2. Redraw-wake energy reduction and replacement-pack check | v1.1 | 0/TBD | Not planned (plans written after the 47.1 baseline) | - |

### Phase 47.1: Wake-energy instrumentation and awake-time reduction (INSERTED)

**Goal**: The owner can see what every wake of the frame costs and why: every wake reports its phases, the server stores and exports them, a reproducible tool fits the per-wake energy model with its uncertainty or refuses naming the missing data, and the pre-reduction baseline is recorded from the instrumented frame.
**Depends on**: Phase 47 (its two-cadence finding on the old 3000 mAh pack: the standing draw is at most about 1 mA, the cost of a wake is not constant, 0.5 to 2 mAh)
**Requirements**: WAKE-01, WAKE-02
**Success Criteria** (what must be TRUE):
  1. Every wake reports how long the frame was awake and what it did (boot, Wi-Fi connection and attempts, download, whether the screen was redrawn, total awake time), the server stores it next to the battery reading, and the read-only export returns it.
  2. A committed, tested tool fits the per-wake energy of a wake without redraw, of a wake with redraw, and the standing draw (reported as an upper bound) from the stored history and the voltage trend, and prints the result with its uncertainty and the assumptions it rests on (rated capacity, discharge curve); no figure is presented as a current measurement. Run on the recorded baseline it either prints a fit with its ranges or refuses naming the exact missing data; both outcomes are recorded. (wording of the criterion after the phase split; agreed by the owner on 2026-11-03, owner-reported.)
  3. The instrumentation-only firmware is released by the owner's own action after the Phase 47 bilan of 2026-11-07 (or the owner has chosen to wait and that is recorded), and the baseline window (at least 14 days at one interval, probably plus a second interval) is recorded from device data with the gap-versus-awake hypothesis decided. If the owner answers "not now" or "later" at the release gate, or the baseline takes owner-controlled wall time that has not elapsed, the criterion closes as "release and baseline pending the owner's decision, recorded with the reason" (closure rule agreed by the owner on 2026-11-03, owner-reported).
**Plans**: 9 plans

Plans:
- [x] 47.1-01-PLAN.md - decision record and telemetry contract (docs only): header grammar, schema route, owner decisions, baseline window rule
- [x] 47.1-02-PLAN.md - server: strict X-Wake-Stats parser, race-tolerant guarded ALTER migration, tailer, export with fallback, export documents
- [x] 47.1-03-PLAN.md - fleet path, freeze-list amendment (probed on a fleet device), owner agreement quoted in the PR text
- [x] 47.1-04-PLAN.md - firmware: pure telemetry module and RTC carry-forward record, host-tested
- [x] 47.1-05-PLAN.md - firmware: wake-path timings and the RTC record at the single sleep exit
- [x] 47.1-06-PLAN.md - firmware: header, SPI timing with a checked timer-reads-only diff, build (no release)
- [x] 47.1-07-PLAN.md - model tool, non-negative fit that fits or refuses (WAKE-02)
- [ ] 47.1-08-PLAN.md - owner-gated instrumentation release after the 2026-11-07 bilan
- [ ] 47.1-09-PLAN.md - baseline from device data, gap hypothesis decided, fit or refusal recorded

### Phase 47.2: Redraw-wake energy reduction and replacement-pack check (INSERTED)

**Goal**: The energy of a redraw wake is reduced where the measured baseline supports it, without changing what the frame shows or any safety override, and the model is checked on the replacement pack.
**Depends on**: Phase 47.1 (baseline recorded, model tool committed); WAKE-04 additionally depends on Phase 47's acceptance and connection of the replacement pack
**Requirements**: WAKE-03, WAKE-04
**Success Criteria** (what must be TRUE) (closure rules agreed by the owner on 2026-11-03, owner-reported):
  1. Each reduction the owner chooses is built, measured before and after under a claim rule fixed before the change, and recorded as demonstrated or not demonstrated; only demonstrated reductions stay on. A duration-only claim on device-reported seconds per redraw wake satisfies this when the energy fit refuses. The image shown, the hash-skip behaviour, quiet hours, display-off and battery-critical overrides are unchanged.
  2. The replacement pack's discharge curve and the predicted autonomy at the chosen interval are stated with their range once data exist; the phase may close with WAKE-04 recorded as pending data, with the reason.
**Plans**: 0 plans (detailed plans are written just in time after the 47.1 baseline; the design notes salvaged from the 47.1 planning are in `.planning/phases/47.2-redraw-wake-energy-reduction-and-replacement-pack-check/drafts/`)

Plans:
- [ ] TBD (run /gsd-plan-phase 47.2 after the 47.1 baseline is recorded)
