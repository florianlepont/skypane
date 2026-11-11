# Requirements: SkyPane

**Defined:** 2026-09-30
**Milestone:** v1.1 Battery and Companion!
**Core Value:** Glancing at the frame tells you, in real time, which plane is taking off or landing right now — while also being a satisfying ambient piece on the wall.

## v1.1 Requirements

### Battery Evidence

- [x] **BAT-01**: The owner can run and reproduce a second controlled battery-discharge study at a materially different effective wake cadence while keeping the pack and normal poll workload comparable to the first study.
- [x] **BAT-02**: The study records its actual cadence, firmware and server baseline, observation window, battery endpoints, raw observation export, continuity evidence, and voltage-validity evidence.
- [x] **BAT-03**: The owner can derive a two-run model that separates per-wake energy from standing deep-sleep consumption using observed elapsed time and observed cycle counts.
- [x] **BAT-04**: The model states its assumptions, uncertainty, and the limitation that the baseline workload does not measure image-download or display-refresh energy.

### Field Operating Policy

- [x] **POL-01**: The owner can choose and document one normal field wake interval from the two-run evidence, including an explicit freshness and autonomy rationale.
- [x] **POL-02**: The owner can decide to retain the current battery pack or select a replacement using documented 1S chemistry, protection, JST-PH 2.0 polarity, fit, charge-time, budget, and voltage-calibration criteria.
- [x] **POL-03**: The selected normal wake interval round-trips through the companion Device settings and is returned to a healthy frame as `sleep_s` without bypassing battery-critical or display-off precedence.

### Companion Experience

- [x] **CMP-01**: The owner can complete a recorded task-based walkthrough of Home, Display, Flights, Airlines, Health, Device, and Update in English and French on desktop and narrow mobile layouts.
- [x] **CMP-02**: The walkthrough records each observed issue as keep, fix now, or defer, with its user impact and reproducible trigger.
- [x] **CMP-03**: The owner can use every companion flow changed by V1.1 with consistent English/French meaning, responsive layout, semantic controls, visible keyboard focus, and clear saved or error feedback.
- [x] **CMP-04**: The highest-value confirmed walkthrough findings are resolved through the existing route, page-context, template, static-asset, and i18n boundaries without a companion rewrite.

### Integrated Validation

- [ ] **VAL-01**: The owner can confirm on the real frame that the selected field cadence produces the expected healthy check-in behavior and retains battery-critical and display-off safety overrides.
- [ ] **VAL-02**: The project records the final field operating decision, including any conditional battery-pack change and its validation status.
- [ ] **VAL-03**: The owner can establish the frame's sleep current against the six-month autonomy target (average current of about 1 mA or less), by direct measurement or, when the series measurement is declined, estimated from the long-interval battery-voltage trend, with the finding of where any excess standing draw comes from or an explicit statement that the measurement settles the question.

### Wake Energy

- [ ] **WAKE-01**: Every wake of the frame reports how long it was awake and what it did (boot, Wi-Fi connection and attempts, download, whether the screen was redrawn, total awake time), the server stores it with the battery reading, and the read-only export returns it.
- [ ] **WAKE-02**: A reproducible, tested tool fits the energy of a wake without redraw, of a wake with redraw, and the standing draw from the stored history and the voltage trend, and prints the result with its uncertainty and its assumptions; it never presents a figure as a current measurement.
- [ ] **WAKE-03**: The energy of a wake that redraws the screen, the dominant cost, is reduced by a measured amount against a baseline recorded before the change, through a shorter redraw wake (image download, panel wait) and any other measured lever, without changing what the frame shows when the image changes, the hash-skip behaviour, quiet hours, display-off or battery-critical overrides.
- [ ] **WAKE-04**: The model is checked on the replacement pack: the pack's discharge curve is derived from the calibrated per-wake cost and the predicted autonomy at the chosen interval is stated with its range.

> Phase split of 2026-11-03: WAKE-01 and WAKE-02 belong to Phase 47.1; WAKE-03 and WAKE-04 belong to Phase 47.2. Agreed by the owner on 2026-11-03 (owner-reported): WAKE-02 is satisfied inside 47.1 when the tool is committed and tested and, run on the recorded baseline, either prints a fit with its ranges or refuses naming the exact missing data (both outcomes recorded). WAKE-03 is satisfied when each reduction the owner chooses is built, measured before and after under a pre-fixed claim rule and recorded as demonstrated or not demonstrated, only demonstrated ones staying on (a duration-only claim on device-reported seconds per redraw wake satisfies it when the energy fit refuses). WAKE-04 is satisfied when the pack's curve and the predicted autonomy at the chosen interval are stated with their range once data exist; the phase may close with WAKE-04 recorded as pending data, with the reason. These closure rules replace the wording above.

## Future Requirements

### Battery and Frame

- **BAT-05**: A third discharge study is run only if the second study leaves a documented decision-blocking uncertainty.
- **BAT-06**: The companion provides a battery analytics dashboard beyond the existing operational health views.
- **PWR-01**: The frame supports solar charging or wall power after field placement and battery evidence justify it.

### Product Scope

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
| BAT-01 | Phase 45 | Complete |
| BAT-02 | Phase 45 | Complete |
| BAT-03 | Phase 46 | Complete |
| BAT-04 | Phase 46 | Complete |
| POL-01 | Phase 46 | Complete |
| POL-02 | Phase 46 | Complete |
| POL-03 | Phase 46 | Complete |
| CMP-01 | Phase 44 | Complete |
| CMP-02 | Phase 44 | Complete |
| CMP-03 | Phase 44 | Complete |
| CMP-04 | Phase 44 | Complete |
| VAL-01 | Phase 47 | Pending |
| VAL-02 | Phase 47 | Pending |
| VAL-03 | Phase 47 | Pending |
| WAKE-01 | Phase 47.1 | Pending |
| WAKE-02 | Phase 47.1 | Pending |
| WAKE-03 | Phase 47.2 | Pending |
| WAKE-04 | Phase 47.2 | Pending |

**Coverage:**
- v1.1 requirements: 18 total
- Mapped to phases: 18
- Unmapped: 0 ✓

---
*Requirements defined: 2026-09-30*
*Last updated: 2026-11-11 after the Phase 47 closing record (VAL-03 wording aligned with the voltage-trend route)*
