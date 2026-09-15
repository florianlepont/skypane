---
id: SEED-008
status: dormant
planted: 2026-09-15
planted_during: Phase 5 (05-low-battery-indicator) — DEVICE-05 battery discharge run, Task 3 write-up
trigger_when: when relevant
scope: unknown
---

# SEED-008: Choose a realistic production wake interval for real field battery-only deployment

## Why This Matters

The device's current "production" default, `SKYPANE_SLEEP_S = 30`
(`deploy/skypane.env.example`), is a development/testing value — chosen
for a responsive dev-loop, never intended as the real cadence for a
battery-only field deployment. Extrapolating DEVICE-05's measured 0.923
mAh/cycle (`hardware/BATTERY-RUN.md`, concluded 2026-09-14, 12.34 days at
a 300s test cadence): running at 30s as-is would give roughly *one day* of
battery life on a 3000 mAh pack — nowhere near viable for the "glance at
the wall, know if you'll make the RER" use case.

Phase 11 already made this setting web-configurable (no more SSH edit
needed), so choosing a real value is a free lever sitting unused. A real
field interval likely belongs somewhere in the 15-60 minute range for a
departure-board use case, but the exact number should be grounded in
data, not guessed.

## When to Surface

**Trigger:** When SEED-007's second discharge measurement (separating
per-wake energy from standing leakage) lands, or at the next milestone
scan regardless — the two are related but this one can proceed on
DEVICE-05's existing data alone if SEED-007 hasn't been picked up yet.

This seed will also surface during `/gsd-new-milestone` when the milestone scope matches.

## Scope Estimate

**Unknown** — run `/gsd-capture --seed --enrich SEED-008` to estimate effort.

Likely small — a config decision plus setting the value via the Phase 11
web form — once the data question (SEED-007) is either resolved or
deliberately set aside.

## Breadcrumbs

- `deploy/skypane.env.example` — `SKYPANE_SLEEP_S`'s current default and
  its comment on why the value matters mechanically
- `hardware/BATTERY-RUN.md` — the measured 0.923 mAh/cycle figure and its
  projection band, the basis for any interval decision
- `companion/pages/config_page.py` / Phase 11 (`.planning/phases/
  11-web-configurable-wake-interval/`) — where the chosen value actually
  gets set, without SSH

## Notes

Captured 2026-09-15 during DEVICE-05's Task 3 write-up, at the developer's
explicit request to think through what this run's data should change
going forward. Sibling seed SEED-007 (separating per-wake cost from
standing leakage via a second measurement) should ideally inform this
choice rather than being skipped.
