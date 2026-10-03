# Project Research Summary

**Project:** SkyPane
**Domain:** Battery-powered e-ink flight frame and bilingual companion web application
**Milestone:** v1.1 Battery and Companion!
**Researched:** 2026-09-30
**Confidence:** MEDIUM

## Executive Summary

V1.1 is an evidence-to-decision milestone. SkyPane already has the telemetry,
durable history, configuration path, and companion architecture it needs: the
frame reports battery voltage during its authenticated poll, the server stores
the observations in SQLite, and the companion persists the normal wake
interval returned to the device as `sleep_s`. The recommended approach is to
reuse those seams for one controlled second discharge study, model the two
runs from observed time and cycles, then make and validate one operational
cadence and battery-pack decision.

The main technical risk is false certainty. The first 300-second, hash-skip
run measured 12.34 days and 0.923 mAh per observed cycle, but cannot separate
active wake cost from standing deep-sleep drain. The second run must keep the
same pack and workload, use a materially different cadence, retain raw data,
and report uncertainty and the unmeasured display-refresh cost. A larger pack
is warranted only if the resulting autonomy/freshness policy misses agreed
targets after connector, fit, charging, and voltage-curve constraints are
checked.

Companion polish should proceed as a task-based discovery and focused repair
effort, not as a redesign. Walk the owner journeys on every authenticated
route, in English and French, at desktop and narrow-mobile widths; rank each
finding as keep, fix now, or defer. Implement only reproducible high-value
findings through the Phase 40 route, page-context, template, CSS, JavaScript,
and stable-i18n boundaries, with accessibility and responsive regression
coverage.

## Key Findings

### Recommended Stack

No new runtime framework, cloud service, telemetry store, firmware protocol,
or companion dependency is needed. Existing whole-device field evidence is
more useful than attempting to infer the product's battery life from component
datasheets or a development-board ammeter. If the current tools cannot express
the calculation reproducibly, add only a pure, fixture-tested two-run analysis
command to `hardware/logtools.py`.

**Core technologies:**

- Firmware `X-Battery-Mv` telemetry — comparable pre-Wi-Fi battery samples on every poll.
- Caddy access logs and `history.db.device_health` — the sole durable observation channel.
- `hardware/logtools.py` and `hardware/BATTERY-RUN.md` — raw-data normalization, experiment gates, model, and evidence record.
- `wake_interval_s`, `wake.effective_wake_interval_s()`, and response `sleep_s` — the existing reversible normal-cadence control plane.
- Companion route table, typed page context, named templates, tokenized CSS, stable i18n IDs, and Playwright coverage — seams for narrow UI changes.

### Expected Features

**Must have (table stakes):**

- A second controlled discharge run at a materially different effective cadence.
- A two-run wake-cost versus standing-drain model using observed elapsed time and cycle count.
- A documented production cadence and retain-or-replace battery-pack decision.
- Confirmation that the applied cadence round-trips through companion settings and a healthy device poll.
- A fresh task-based companion walkthrough followed by focused, bilingual fixes.

**Should have (differentiators):**

- A transparent autonomy/freshness policy with explicit assumptions and uncertainty.
- A calm, coherent companion experience whose improvements are tied to real owner journeys.
- An evidence-backed decision to keep the current 3000 mAh pack when it meets the target.

**Defer (v2+):**

- A third discharge run unless the second run leaves a documented decision-blocking uncertainty.
- A battery analytics dashboard, parallel telemetry, or cloud analytics.
- Solar or wall power, RER and additional panel views, on-device settings, phone notifications, and the comment-history guard.

### Architecture Approach

The device remains poll-only. The companion writes `wake_interval_s` to the
existing device configuration; `wake.effective_wake_interval_s()` applies the
normal policy underneath battery-critical and display-off overrides; the next
poll delivers `sleep_s`; firmware validates it before deep sleep. The second
experiment should be an operational artifact beside the existing battery-run
record, not a new subsystem. Companion changes must remain in their owning
modules and preserve shared state, refresh, and accessibility contracts.

**Major components:**

1. Firmware battery and API client — sample before Wi-Fi and emit comparable telemetry.
2. Device API, Caddy, poll cycle, and SQLite history — persist idempotent field observations.
3. `hardware/logtools.py` and battery evidence files — validate runs and derive reproducible analysis.
4. Device configuration and wake policy — save the chosen normal interval while preserving safety precedence.
5. Companion routes, pages, layout, assets, and i18n — host walkthrough-backed usability improvements.

### Critical Pitfalls

1. **Changing pack and cadence together** — keep the charged 3000 mAh pack and hash-skip workload fixed across the two runs.
2. **Using requested sleep as full-cycle duration** — compute from actual timestamps and observed check-ins; wake work is measurable overhead.
3. **Treating missing voltage as a missed wake** — use all health rows for continuity and validate voltage separately.
4. **Claiming exact autonomy from two noisy runs** — publish assumptions, uncertainty, and the hash-skip limitation; validate the selected policy in normal use.
5. **Bypassing cadence precedence or redesigning on taste** — use the stored setting and safety order; make only walkthrough-proven, bilingual, accessible fixes.

## Implications for Roadmap

### Phase 1: Battery Experiment Protocol and Second Discharge Study

**Rationale:** The production policy cannot be credible until the two unknown
consumption terms are separated with comparable evidence.

**Delivers:** A pre-registered alternate cadence, frozen comparable conditions,
effective `sleep_s` confirmation, bounded raw export, and completed second-run
continuity, voltage, and depletion gates.

**Addresses:** Controlled second discharge and reproducible evidence.

**Avoids:** Pack/cadence confounding, nominal-cycle arithmetic, and hidden
missing-header failures.

### Phase 2: Two-Run Analysis and Field Operating Decision

**Rationale:** The run is input, not the outcome. The model must drive one
explicit freshness/autonomy/pack decision before configuration or procurement.

**Delivers:** A documented wake-energy and standing-drain model with
assumptions and uncertainty; selected normal wake interval; retain-current-pack
or compatible-pack rationale; applied-policy verification through the
companion and device response.

**Uses:** `hardware/logtools.py`, `hardware/BATTERY-RUN.md`, `hardware/BOM.md`,
and the existing `wake_interval_s` to `sleep_s` path.

**Avoids:** Precision theater, premature battery procurement, and bypassing
battery-critical or display-off precedence.

### Phase 3: Companion Walkthrough and Focused Polish

**Rationale:** Discovery can run while the battery study observes, but UI
implementation should follow a ranked finding log and the final battery
decision where Device or Health copy depends on it.

**Delivers:** An English walkthrough finding log covering Home, Display,
Flights, Airlines, Health, Device, and Update; targeted fixes for confirmed
friction; English/French parity; responsive, keyboard, and browser validation.

**Implements:** Phase 40's route, page context, template, stylesheet,
per-page-script, and stable-i18n boundaries.

**Avoids:** A wholesale redesign, duplicate state reads, stale French copy,
lost keyboard focus, and mobile layout regressions.

### Phase 4: Integrated Field Validation and Decision Record

**Rationale:** The selected cadence only becomes a production policy once it
is observed on glass and documented as the current operating baseline.

**Delivers:** Frame check-in confirmation, expected `sleep_s`, safety override
checks, companion state clarity, and final decision/BOM documentation.

**Avoids:** Leaving a development environment default in production or
presenting a pack percentage curve as valid after an unverified pack change.

### Phase Ordering Rationale

- Phase 1 precedes Phase 2 because one cadence cannot separate per-wake cost from time-based drain.
- Phase 3 discovery may overlap the long-running measurement, but only ranked findings should become implementation work.
- The final decision must use the existing stored setting so it remains visible in the companion and yields to safety overrides.
- A pack replacement is conditional after the model; if it is selected, its fit, connector polarity, charge time, budget, and voltage curve need validation before final field confirmation.

### Research Flags

Phases likely needing deeper research during planning:

- **Phase 1:** Confirm the concrete run protocol, target alternative cadence, evidence gates, and current device/server observation state before disconnecting USB.
- **Phase 2:** Validate the two-run inference, uncertainty treatment, and replacement-pack constraints against actual second-run data.
- **Phase 3:** Perform the prescribed UX walkthrough before planning fixes; its finding log is the scope source of truth.

Phases with standard patterns:

- **Phase 4:** Existing poll, Device settings, safety precedence, browser-test, and bilingual-i18n patterns are established; use targeted verification rather than exploratory architecture work.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Existing integration seams and current protocol are directly verified in the repository. |
| Features | MEDIUM | Scope is clear, but the second-run result and walkthrough findings do not yet exist. |
| Architecture | HIGH | The telemetry, configuration, and Phase 40 companion boundaries are documented and implemented. |
| Pitfalls | HIGH | Risks derive from the measured first-run limitations and established accessibility/configuration contracts. |

**Overall confidence:** MEDIUM

### Gaps to Address

- **Second-run data:** Do not choose a production cadence or procure a pack until comparable actual observations are available.
- **Decision thresholds:** State acceptable display freshness, target autonomy, and replacement-pack constraints before interpreting the model.
- **Display-refresh energy:** The first run used a hash-skip workload; label the resulting model as baseline wake/leakage evidence rather than universal display-update lifetime.
- **Companion findings:** Do not infer a defect list from architecture review. The fresh English/French, desktop/mobile, keyboard task walkthrough determines what qualifies for V1.1 polish.
- **Pack substitution:** If selected, verify the replacement's 1S chemistry, protection, JST-PH 2.0 polarity, physical fit, charge time, budget, and voltage-to-percentage calibration before treating it as production-ready.

## Sources

### Primary (HIGH confidence)

- `hardware/BATTERY-RUN.md` — first-run protocol, measurements, limitations, and follow-up boundary.
- `hardware/BOM.md` — current pack and replacement constraints.
- `.planning/seeds/SEED-007-second-discharge-run-separate-wake-vs-leakage-energy.md`, `SEED-008-choose-real-field-wake-interval.md`, and `SEED-010-companion-interface-polish.md` — V1.1 scope.
- `firmware/main/battery.c`, `api_client.c`, `sleep_decision.c`, `server/history_db.py`, `poll_cycle.py`, `device_config.py`, and `wake.py` — telemetry and cadence contracts.
- `companion/routes.py`, `page_context.py`, `pages/config_page.py`, `pages/health_page.py`, and Phase 40 artifacts — companion boundaries.

### Secondary (MEDIUM confidence)

- [Espressif current-consumption measurement guidance](https://docs.espressif.com/projects/esp-idf/en/v5.2/esp32s3/api-guides/current-consumption-measurement-modules.html) — separate active and deep-sleep measurement rationale.
- [W3C WCAG 2.2](https://www.w3.org/TR/wcag/) and [MDN keyboard accessibility guidance](https://developer.mozilla.org/en-US/docs/Web/Accessibility/Guides/Understanding_WCAG/Operable) — visible focus and operable companion controls.

---
*Research completed: 2026-09-30*
*Ready for roadmap: yes*
