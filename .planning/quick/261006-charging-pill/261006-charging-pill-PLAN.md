---
quick_id: 261006-charging-pill
type: quick
autonomous: true
branch: claude/charging-pill
---

# 261006-charging-pill: an estimated "Probably charging" status in the companion

## Objective

The frame reports only a battery voltage at each wake, and the EE02 board exposes no readable
charge-state signal (the charger drives only a status LED). The owner chose a voltage-trend
ESTIMATE shown in the companion only: no firmware change, no new telemetry, nothing drawn on the
e-ink picture. The wording must stay honest ("Probablement en charge" / "Probably charging").

## Tasks

1. `companion/battery.py`: a pure `charging_estimate(rows, now, wake_interval_s)` returning
   `CHARGE_LIKELY` / `CHARGE_NOT_CHARGING` / `CHARGE_UNKNOWN`, windows counted in wakes, a
   freshness limit of 2 wakes + 60 s. Calibrate and measure false positives on the real discharge
   run (`hardware/logs/battery-run-server.log`), the one real unplug, and synthetic charge ramps.
2. One shared pill builder (`ui_components.battery_charging_pill_html`), a new `icon-bolt`, FR
   strings in `i18n_fr/common.py`, one `.charging-pill` rule in the ok tone (no accent).
3. Show it on Home's battery dial (and its accessible name) and in Health's Battery row summary.
   Resolve the cadence in one place (`health_signals.charging_likely`) shared by both pages and
   by the freshness token, so a stale pill is removed by the refresh loop without a new reading.
4. Check `battery_status()` against the observed unplug step; change it only if warranted.
5. Tests: unit (estimate), served HTML (both pages, both languages), contrast, freshness token,
   real-browser fit at 360/390/1280 in both themes plus a live refresh-loop removal. Regenerate
   the render baseline and verify the page-level diff.
