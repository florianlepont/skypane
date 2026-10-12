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
- [ ] **Phase 46: Two-Run Battery Analysis and Operating Decision** - Derive the model and select the field cadence and pack policy.
- [ ] **Phase 47: Integrated Field Validation and Decision Record** - Confirm the policy on the real frame and publish the operating baseline.

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
- [ ] 46-04-PLAN.md — Owner chooses the interval and the pack, applies the interval on the live Device page; decisions recorded (wave 3, owner checkpoints)

### Phase 47: Integrated Field Validation and Decision Record
**Goal**: The selected field policy is confirmed on the real frame and recorded as the current operating baseline.
**Depends on**: Phase 44, Phase 46
**Requirements**: VAL-01, VAL-02
**Success Criteria** (what must be TRUE):
  1. The owner can confirm on the real frame that the selected cadence produces the expected healthy check-in behaviour.
  2. The real-frame validation confirms that battery-critical and display-off safety overrides still take precedence over the normal cadence.
  3. The project records the final wake-interval decision, its evidence-based rationale, and the validation status of any battery-pack change.
**Plans**: TBD

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 44. Companion Walkthrough and Focused Bilingual Polish | v1.1 | 12/12 | Complete | 2026-10-04 |
| 45. Controlled Second Discharge Study | v1.1 | 4/4 | Complete | 2026-10-12 |
| 46. Two-Run Battery Analysis and Operating Decision | v1.1 | 3/4 | In Progress (46-04 owner decisions pending) | - |
| 47. Integrated Field Validation and Decision Record | v1.1 | 0/TBD | Not started | - |
