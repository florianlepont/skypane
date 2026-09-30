# Technical Stack: SkyPane v1.1

**Researched:** 2026-09-30  
**Confidence:** High for existing integration; medium for field-autonomy estimates until the second run completes.

## Recommendation

V1.1 needs no new runtime framework, cloud service, firmware protocol, or
companion dependency. It should use the existing authenticated poll telemetry,
SQLite history, `hardware/logtools.py`, device configuration and companion page
boundaries. The only likely code addition is a pure two-run analysis command in
`hardware/logtools.py`, and only if the existing tools cannot express the
calculation reproducibly.

| Need | Reuse | Change only if needed | Do not add |
|---|---|---|---|
| Field experiment | `X-Battery-Mv`, Caddy access log, `history.db.device_health` | A documented two-run analysis command | Browser polling, a second telemetry database, cloud analytics |
| Cadence policy | `wake_interval_s`, `wake.effective_wake_interval_s()`, response `sleep_s` | A short explanation in the Device settings page | A firmware-only cadence or a second configuration key |
| Battery-pack decision | `hardware/BOM.md`, `hardware/BATTERY-RUN.md`, `logtools.py --capacity-mah` | BOM, analysis assumption and voltage-curve validation after a pack change | Procurement before the two-cadence model supports it |
| Companion polish | Route table, page context, templates, i18n, tokenized CSS and existing Playwright tests | Narrow walkthrough-backed UI fixes | A UI framework, a wholesale rewrite, duplicated page state |

## Measurement Guidance

The ESP32-S3 alternates microamp deep-sleep current and milliamp active work;
Espressif cautions that a development board carries extra consumption and that
ordinary ammeters can distort a high-dynamic-range measurement. SkyPane's
field method therefore remains the product-level evidence: same frame, pack,
firmware, server workload and durable check-in channel across two materially
different cadences. The two values must use observed elapsed time and observed
cycle count, rather than treating requested sleep time as the complete cycle.

The model should state its assumptions explicitly:

`daily consumption = energy per wake × wakes per day + deep-sleep leakage per day`

The first experiment's hash-skip workload excludes display-refresh energy, so a
decision must name that limitation rather than presenting the result as a
universal battery forecast.

## Integration Points

- `firmware/main/battery.c` and `api_client.c` sample and transmit battery
  voltage before Wi-Fi; retain this sequence for comparability.
- `server/history_db.py` and the poll cycle persist check-ins; retain their
  idempotent history as the sole observation channel.
- `hardware/logtools.py` owns parsing and reporting. Any model code should be
  pure and fixture-tested, with raw-data validation kept separate from the
  inference.
- `server/wake.py` preserves safety precedence: battery-critical and
  display-off cadence override the stored normal cadence.
- `companion/pages/config_page.py` is the existing normal-cadence control
  plane. Phase-40 page, route, layout, static and i18n seams contain polish.

## Sources

- [Espressif current-consumption measurement guidance](https://docs.espressif.com/projects/esp-idf/en/v5.2/esp32s3/api-guides/current-consumption-measurement-modules.html)
- [Espressif ESP32-S3 sleep modes](https://docs.espressif.com/projects/esp-idf/en/latest/esp32s3/api-reference/system/sleep_modes.html)
- Local sources: `hardware/BATTERY-RUN.md`, `hardware/logtools.py`,
  `server/wake.py`, `server/history_db.py`, and `companion/pages/config_page.py`.
