# Pitfalls: SkyPane v1.1

**Researched:** 2026-09-30

| Risk | Why it matters | Prevention | Roadmap point |
|---|---|---|---|
| Changing pack and cadence in the same experiment | The result cannot attribute a consumption change to either variable. | Keep the same charged 3000 mAh pack and comparable hash-skip workload for both cadence runs. | Measurement phase |
| Using nominal sleep as the cycle duration | Wake work creates a measurable gap between requested sleep and observed poll cadence. | Derive both runs from elapsed timestamps and observed checks, and retain the raw export. | Measurement analysis |
| Treating a missing voltage header as a missed wake | A real check-in can have an unparseable or absent battery value. | Use all `device_health` rows for continuity, then classify voltage validity separately. | Measurement analysis |
| Declaring a precise autonomy prediction from two noisy runs | Battery temperature, voltage curve, workload and capacity uncertainty remain. | Publish a bounded estimate, its assumptions and a decision threshold; validate the selected policy in normal use. | Decision phase |
| Replacing the pack before the model says it is useful | Larger capacity can add fit, connector, charge-time and voltage-calibration work without meaningful freshness benefit. | Decide only after the comparison; verify 1S chemistry, protection, JST-PH 2.0 polarity, physical fit, budget and charge time. | Decision phase |
| Bypassing cadence precedence | A firmware or environment override can make the companion misleading and defeat battery-critical/display-off safeguards. | Set the normal cadence through `wake_interval_s`; keep `wake.effective_wake_interval_s()` precedence unchanged. | Applied-policy validation |
| Making a visual companion rewrite without evidence | It can regress bilingual copy, mobile layouts, refresh behavior and keyboard flow while solving no known friction. | Start with a task-based walkthrough, rank findings, and make the smallest change in each owning module. | Companion polish |
| Losing bilingual parity or keyboard focus | A changed English message or custom control can leave French stale or keyboard users without a visible action location. | Use stable i18n keys, test both locales, preserve semantic controls and visible focus. | Companion polish |

## Release Gates

1. The second run has an explicit cadence, a recorded effective `sleep_s`, a
   bounded observation window, raw evidence and the same battery/workload
   conditions as the first run.
2. The resulting model reports uncertainty and does not conceal its
   hash-skip-only limitation.
3. The selected normal cadence round-trips through the companion and device
   response while battery-critical and display-off behavior still wins.
4. Every companion change has English and French coverage plus relevant
   browser, responsive and keyboard verification.

## Sources

- [Espressif low-power measurement guidance](https://docs.espressif.com/projects/esp-idf/en/v5.2/esp32s3/api-guides/current-consumption-measurement-modules.html)
- [MDN guidance on visible keyboard focus](https://developer.mozilla.org/en-US/docs/Web/Accessibility/Guides/Understanding_WCAG/Operable)
- Local sources: `hardware/BATTERY-RUN.md`, `hardware/BOM.md`,
  `server/wake.py`, and the companion test suite.
