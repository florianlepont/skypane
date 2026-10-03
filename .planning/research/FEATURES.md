# Feature Landscape: SkyPane v1.1

**Domain:** Battery-powered e-ink flight frame and its bilingual companion web app
**Milestone:** v1.1 Battery and Companion!
**Researched:** 2026-09-30
**Confidence:** MEDIUM — the product evidence is strong and local, but the second discharge result and the fresh companion walkthrough do not exist yet.

## Scope Boundary

V1.1 is an evidence-to-decision milestone. It must turn the first field discharge result into a defensible operating policy, then remove the highest-value friction found in a fresh companion walkthrough. It is not a second implementation of the frame, a transit-view expansion, or a general companion rewrite.

The baseline is already substantial:

- The first discharge run depleted a nominal 3000 mAh pack after 12.34 days at a configured 300-second sleep interval. It observed 3,252 normal hash-skip cycles and calculated 0.923 mAh per observed cycle.
- That run deliberately cannot say how much of the drain belongs to each wake versus the time spent asleep. Its 3,600-second projection therefore spans 12.34 to 148.08 days.
- The deployed companion already owns wake-interval configuration, quiet hours, battery state, a responsive sidebar/bottom-tab navigation system, bilingual copy, theme choice, and keyboard/no-JavaScript resilience tests.

The required user outcome is consequently precise: the frame should run at a deliberately chosen field cadence on a deliberately retained or replaced pack, and the companion should feel coherent and easy to use in the actual routes and states the owner visits.

## Table Stakes

| Feature | User-facing outcome | Why expected in v1.1 | Complexity | Delivery notes |
|---|---|---|---|---|
| Second controlled field discharge at a meaningfully different cadence | The owner can trust that “wake cost” and “standing drain” are not being confused when deciding how often the frame updates. | One cadence is one equation with two unknowns; the existing 3,600-second projection is too broad to support a purchase or production-cadence decision. | Medium | Reuse the established full-charge, unplugged, server-observed protocol and `history.db` channel. Record the actual sleep value the device received, both battery endpoints, outage/gap evidence, and observed cycle count. A long candidate interval such as 3,600 seconds is appropriate because it separates the time term from the wake term. |
| Decision-ready two-run battery model | The owner receives one documented model with a per-wake term, a time/leakage term, uncertainty, and a plain-language conclusion. | Raw logs and a single mAh/cycle headline are not a usable operating decision. | Low–Medium | Fit the two real run totals only after both runs pass the agreed evidence checks. Carry the first run’s known caveat: its 0.915 nominal coverage reflects roughly 28 seconds of wake overhead, so calculations must use observed cycles and elapsed time, not assume that `sleep_s` equals a complete cycle. Treat image-download/e-paper-refresh cost separately because the first run stayed on the hash-skip path. |
| Production cadence and pack decision record | The owner can answer: “How fresh is the frame, how long will it run, and do I keep the 3000 mAh pack?” | This is the stated milestone outcome and closes the decision SEED-008 was created to preserve. | Low | Define decision criteria before seeing the second result: acceptable freshness for a glanceable flight display, desired autonomy, physical fit, connector/polarity, charge-time acceptability, and the remaining hardware budget. Select one interval inside the existing 60–3,600 second configuration bounds, or explicitly record why a bounds change is necessary. Do not silently leave the development value in place. |
| Applied-policy confirmation in the companion | After saving, the owner can see the configured normal cadence and understand when quiet hours alter it. | A correct decision that is hard to inspect or accidentally overwritten is not a production configuration. | Low | Keep the companion as the control plane. The chosen cadence must round-trip through the Settings form and device poll response; the Home/Health wording must not imply that a quiet-hours hold is a failed check-in. Any new pack-related text must be factual, not a fabricated percentage estimate. |
| Fresh, task-based companion walkthrough | The owner can complete everyday checks and changes without hunting, ambiguity, clipped controls, or contradictory status language. | SEED-010 intentionally declined to invent a defect list before looking at the finished v1.0 companion. | Medium | Walk the authenticated routes — Home, Display, Flights, Airlines, Health, Device, Update — in French and English, desktop and narrow mobile layouts. Include normal, empty, stale/warning, and pending/confirmation states where available. Capture each finding as keep, fix now, or defer, with an observable trigger and evidence. |
| Focused polish of walkthrough findings | The companion becomes clearer while preserving its existing reliable workflows. | A review with no resolved user-visible findings would not improve day-to-day use. | Medium | Prioritize navigation orientation, scan hierarchy, status/state clarity, form labels and save feedback, touch/keyboard operation, responsive spacing, and visual consistency. Make the smallest changes that resolve the confirmed findings; reuse the Phase 40 route/page/template/i18n boundaries and tokenized stylesheet. |
| Bilingual parity for every changed surface | English and French users receive the same action, status, and error meaning. | The companion is intentionally bilingual; v1.0’s stable message IDs prevent English wording changes from silently dropping French. | Low | Put all English source text, code comments, artifacts, and message identifiers in English. Add French translation through the existing catalogues and run the i18n/route tests. French is appropriate for the owner conversation, not for project artifacts. |

## Differentiators

| Feature | Value proposition | Complexity | Notes |
|---|---|---|---|
| Measured autonomy–freshness policy, rather than a guessed interval | SkyPane’s ambient value remains useful without turning the device into a frequently-charged gadget. | Medium | The policy should present the selected cadence as a product choice backed by field data, not as an engineering default. A longer cadence is valuable only if it still meets the owner’s real “glance before leaving” need. |
| Transparent model assumptions | Future changes can distinguish normal drift from a change in real power behavior. | Low | Record capacity assumption, run dates, cadence, cycle/wall-clock interpretation, hash-skip limitation, and confidence interval. This is a project decision artifact, not necessarily a permanent customer-facing dashboard. |
| Companion polish driven by a complete owner journey | The app preserves its hand-built, calm identity while feeling deliberately finished rather than uniformly “redesigned.” | Medium | The companion already has responsive navigation, status dots, live relative times, dark/light themes, and strong no-JS/keyboard tests. V1.1 should make their behavior more immediately legible, not replace them with a framework or a generic dashboard. |
| Evidence-backed acceptance of the current pack | “Keep the 3000 mAh pack” is a successful outcome if it meets the agreed service target. | Low | Avoid equating more capacity with a better product. A larger pack adds fit, charge-time, and chemistry/percentage-calibration work and must buy a meaningful user benefit. |

## Companion Walkthrough Coverage

The walkthrough is a discovery feature with a fixed method, not a vague visual pass. It should produce an English finding log that gives the planner a concrete, bounded implementation list.

| Journey | What to inspect | Evidence of success |
|---|---|---|
| Orient and inspect | Sign in, identify the current frame state, current picture, next expected check-in, battery state, and the route to details. | Home presents one clear answer to “is the frame healthy and what is it showing?” without requiring a second page to decode an ordinary status. |
| Change an operating setting | Locate wake interval/quiet hours, understand valid limits and consequences, make a safe change, and verify the saved result. | Labels, constraints, confirmation, dirty-state behavior, and the resulting device behavior agree in both languages. |
| Diagnose an exception | Follow a warning from the navigation or Home to Health/Device and identify the next action. | Warnings are distinct from intentional quiet-hours sleep; a stale value includes a clear time and an actionable destination. |
| Review data | Scan Flights and Airlines, use filtering/reveals where present, and return to the current frame. | Long lists, cards/tables, empty states, and mobile equivalents remain understandable without hidden navigation or layout collision. |
| Maintain the device | Visit Device and Update, inspect a pending action, cancel or confirm it safely, and recover after refresh/navigation. | Destructive or long-running actions communicate their state, do not double-submit, and preserve focus and form state. |
| Use the companion on a phone and keyboard | Repeat the high-frequency Home, Settings, and Health journeys at the supported narrow width and without pointer-only assumptions. | Bottom navigation and More sheet expose every route; controls have usable targets, visible focus, no clipping/overlap, and no duplicate landmarks. |

The walkthrough must retain findings that say **keep**: a stable part of the v1.0 interface is evidence against unnecessary redesign. It must also separate a visual preference from a reproducible problem. A “fix now” finding needs its affected route/state/viewport, user consequence, proposed acceptance criterion, and whether it is a translation, markup, CSS, or behavior issue.

## Anti-Features

| Anti-feature | Why avoid it | Do instead |
|---|---|---|
| A third battery test before analysing the second | It postpones the decision while accumulating data with no stated discrimination purpose. | Pre-register the second cadence and decision thresholds; fit and review the two-run model before adding more measurement. Add another run only to resolve a documented uncertainty, such as image-refresh energy. |
| Declaring an exact lifetime from datasheet or nominal interval alone | Board peripherals, Wi-Fi, wake duration, protected-cell cutoff, and real wall-clock wake overhead make chip-level figures insufficient. | Use SkyPane’s whole-device field runs and express a range/confidence where uncertainty remains. Espressif’s measurement guidance likewise distinguishes deep-sleep and active consumption rather than treating them as one value. |
| Buying a larger pack before the model and target are defined | It may add size and charging friction while failing to improve the update cadence that matters. | Keep the current protected 3.7 V 1S JST-PH 2.0 mm pack unless measured projections miss the agreed target. Evaluate replacements against connector polarity, physical fit, charge time, budget, and percentage-curve validity. |
| Turning the companion into a battery analytics product | Permanent dashboards, arbitrary reports, and manual calibration controls distract from the one owner decision. | Keep the decision report in planning/hardware artifacts and add companion UI only where it makes the applied configuration or immediate state clearer. |
| A wholesale visual redesign | Phase 40 deliberately consolidated route, page, template, i18n, and stylesheet boundaries; a redesign without specific findings risks regressions in tested workflows. | Use the walkthrough to target high-frequency friction and preserve the established design tokens, navigation, themes, and accessible semantic controls. |
| Adding routes, data domains, notifications, or an on-device menu | RER, additional widgets, phone notifications, and gadget-like device controls are already out of scope and would obscure the battery and polish decisions. | Keep V1.1 to the existing single flight view, battery field policy, and companion clarity. |
| Treating French text as an afterthought | A language switch that changes meaning or leaves untranslated new UI destroys trust in a private companion. | Use existing stable message IDs and complete the English/French pair in the same change. |

## Feature Dependencies

```text
Second field discharge run
  -> comparable observed-cycle and elapsed-time evidence
  -> two-run wake-versus-standing-drain model
  -> agreed freshness and autonomy targets
  -> production cadence decision
  -> retain current pack OR assess compatible larger pack
  -> apply and verify production configuration in companion/device poll

Fresh companion walkthrough
  -> evidence-tagged finding log (keep / fix now / defer)
  -> scoped polish requirements
  -> English source copy + French catalogue parity
  -> route, browser, accessibility, and responsive regression checks
```

### Dependency Notes

- The cadence decision depends on the model, not merely on a successful second run. The model must preserve observed wake overhead and distinguish the unmeasured image-download/e-paper-refresh cost from the hash-skip baseline.
- A pack substitution depends on the decision criteria and hardware verification. The existing voltage-to-percentage curve was fitted to the 3000 mAh pack; a different chemistry or discharge curve requires a review before its percentage is presented as truthful.
- The walkthrough can begin before the battery run finishes, but implementation should wait until its findings are ranked. This allows interface polish and the long-running discharge observation to proceed independently without inventing UX scope.
- Companion polish depends on the Phase 40 architecture remaining intact: routes dispatch through the route table, pages receive typed context, templates are named, and all strings pass stable i18n IDs.

## MVP Recommendation

Prioritize the milestone in this order:

1. **Run the second, pre-registered discharge study.** It addresses the only uncertainty that prevents an honest production policy.
2. **Produce and approve the operating decision.** Select the normal wake interval and retain or replace the pack against explicit freshness/autonomy/fit criteria; apply and verify the selected setting.
3. **Perform the companion walkthrough and implement its bounded findings.** Start the review while the battery run is observing, then ship only reproducible, high-value improvements with bilingual parity.

Defer:

- A third run unless the two-run analysis names a remaining decision-blocking uncertainty.
- A general telemetry or battery-analytics interface.
- Solar, wall power, additional display views, RER work, on-device settings, phone alerts, and the deferred comment-history guard.

## Sources

### Project evidence (HIGH confidence)

- `hardware/BATTERY-RUN.md` — first run protocol, verdict, 0.923 mAh/cycle result, 3,600-second projection band, real wake-overhead diagnosis, hash-skip limitation, current-pack charge observations, and follow-up decision boundary.
- `hardware/BOM.md` — 3000 mAh pack, 3.7 V 1S protection, JST-PH 2.0 mm connector/polarity, budget ceiling, and replacement constraints.
- `.planning/seeds/SEED-007-second-discharge-run-separate-wake-vs-leakage-energy.md` and `SEED-008-choose-real-field-wake-interval.md` — intended measurement and decision scope.
- `.planning/seeds/SEED-010-companion-interface-polish.md`, `companion/ui_base.py`, `companion/ui_nav.py`, `companion/pages/home_page.py`, and `companion/static/style.css` — current companion scope and its existing navigation, accessibility, i18n, and token-system contracts.

### External references (MEDIUM confidence)

- [Espressif current-consumption measurement guidance](https://docs.espressif.com/projects/esp-idf/en/stable/esp32h2/api-guides/current-consumption-measurement-modules.html) — active and deep-sleep consumption are distinct measurements; used here for method rationale, not as an ESP32-S3 board-level power claim.
- [W3C WCAG 2.2](https://www.w3.org/TR/wcag/) and [W3C focus-appearance guidance](https://www.w3.org/WAI/WCAG22/Understanding/focus-appearance) — visible, sufficiently distinct focus and operable controls inform the companion walkthrough criteria.
- [Seeed XIAO ESP32-S3 series battery documentation](https://wiki.seeedstudio.com/xiao_esp32s3_getting_started/) — battery operation and USB charging context; exact replacement compatibility remains governed by the verified SkyPane BOM.
