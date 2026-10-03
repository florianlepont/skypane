# Requirements: SkyPane

**Defined:** 2026-09-30
**Milestone:** v1.1 Battery and Companion!
**Core Value:** Glancing at the frame tells you, in real time, whether you'll make the next RER — while also being a satisfying ambient piece on the wall.

## v1.1 Requirements

### Battery Evidence

- [ ] **BAT-01**: The owner can run and reproduce a second controlled battery-discharge study at a materially different effective wake cadence while keeping the pack and normal poll workload comparable to the first study.
- [ ] **BAT-02**: The study records its actual cadence, firmware and server baseline, observation window, battery endpoints, raw observation export, continuity evidence, and voltage-validity evidence.
- [ ] **BAT-03**: The owner can derive a two-run model that separates per-wake energy from standing deep-sleep consumption using observed elapsed time and observed cycle counts.
- [ ] **BAT-04**: The model states its assumptions, uncertainty, and the limitation that the baseline workload does not measure image-download or display-refresh energy.

### Field Operating Policy

- [ ] **POL-01**: The owner can choose and document one normal field wake interval from the two-run evidence, including an explicit freshness and autonomy rationale.
- [ ] **POL-02**: The owner can decide to retain the current battery pack or select a replacement using documented 1S chemistry, protection, JST-PH 2.0 polarity, fit, charge-time, budget, and voltage-calibration criteria.
- [ ] **POL-03**: The selected normal wake interval round-trips through the companion Device settings and is returned to a healthy frame as `sleep_s` without bypassing battery-critical or display-off precedence.

### Companion Experience

- [ ] **CMP-01**: The owner can complete a recorded task-based walkthrough of Home, Display, Flights, Airlines, Health, Device, and Update in English and French on desktop and narrow mobile layouts.
- [ ] **CMP-02**: The walkthrough records each observed issue as keep, fix now, or defer, with its user impact and reproducible trigger.
- [x] **CMP-03**: The owner can use every companion flow changed by V1.1 with consistent English/French meaning, responsive layout, semantic controls, visible keyboard focus, and clear saved or error feedback.
- [x] **CMP-04**: The highest-value confirmed walkthrough findings are resolved through the existing route, page-context, template, static-asset, and i18n boundaries without a companion rewrite.

### Integrated Validation

- [ ] **VAL-01**: The owner can confirm on the real frame that the selected field cadence produces the expected healthy check-in behavior and retains battery-critical and display-off safety overrides.
- [ ] **VAL-02**: The project records the final field operating decision, including any conditional battery-pack change and its validation status.

## Future Requirements

### Battery and Frame

- **BAT-05**: A third discharge study is run only if the second study leaves a documented decision-blocking uncertainty.
- **BAT-06**: The companion provides a battery analytics dashboard beyond the existing operational health views.
- **PWR-01**: The frame supports solar charging or wall power after field placement and battery evidence justify it.

### Product Scope

- **RER-01**: The frame shows the next RER trains and leave-by guidance.
- **MSG-01**: The companion sends a short message to the frame.

## Out of Scope

| Feature | Reason |
|---|---|
| New telemetry service, cloud analytics, or browser polling | Existing authenticated device telemetry and SQLite history are sufficient for the experiment. |
| Firmware protocol redesign | Existing battery telemetry and `sleep_s` policy path cover V1.1. |
| Battery-pack purchase before the two-run result | It would confound evidence and may add fit, charging, and calibration work without a user benefit. |
| Companion redesign or new UI framework | V1.1 fixes reproducible walkthrough findings through the established companion architecture. |
| Comment-history guard debt | Explicitly deferred by the owner for a future milestone. |

## Traceability

| Requirement | Phase | Status |
|---|---|---|
| BAT-01 | Phase 45 | Pending |
| BAT-02 | Phase 45 | Pending |
| BAT-03 | Phase 46 | Pending |
| BAT-04 | Phase 46 | Pending |
| POL-01 | Phase 46 | Pending |
| POL-02 | Phase 46 | Pending |
| POL-03 | Phase 46 | Pending |
| CMP-01 | Phase 44 | Pending |
| CMP-02 | Phase 44 | Pending |
| CMP-03 | Phase 44 | Complete |
| CMP-04 | Phase 44 | Complete |
| VAL-01 | Phase 47 | Pending |
| VAL-02 | Phase 47 | Pending |

**Coverage:**
- v1.1 requirements: 13 total
- Mapped to phases: 13
- Unmapped: 0 ✓

---
*Requirements defined: 2026-09-30*
*Last updated: 2026-09-30 after V1.1 roadmap order change*
