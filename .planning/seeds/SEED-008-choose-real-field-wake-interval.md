---
id: SEED-008
status: dormant
planted: 2026-09-15
planted_during: Phase 5 (05-low-battery-indicator) — DEVICE-05 battery discharge run, Task 3 write-up
trigger_when: "Milestone v1.1 — earmarked by the developer on 2026-09-24, together with SEED-007, SEED-008 and SEED-009."
target_milestone: v1.1
scope: unknown
---

# SEED-008: Choose a realistic production wake interval for real field battery-only deployment — and whether to move to a bigger battery pack

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

## Second lever: a bigger battery pack (added 2026-09-24)

At the developer's request, this decision is no longer "which interval"
alone: it is **interval × pack capacity**. Battery life scales with the
pack's capacity for a given cadence, so a larger pack can buy the same
autonomy at a shorter, fresher interval — or more autonomy at the same
one. The choice to make, together:

1. **Keep the current pack** (Kubii "Batterie 3000mAh Li-Po", 3.7 V 1S,
   JST-PH 2.0 mm, `hardware/BOM.md`) and pick the interval that meets the
   autonomy target on it; or
2. **Switch to a higher-capacity pack** and pick the interval against the
   new capacity.

Hard constraints any replacement pack must meet (all from
`hardware/BOM.md`'s "Battery Connector Verification"):

- 3.7 V single-cell (1S) LiPo/Li-ion with a protection circuit;
- **JST-PH 2.0 mm, 2-pin**, with the board's polarity (negative on the
  side closest to the USB port) — the 2.54 mm JST-SYP trap applies;
- physically fits behind the 13.3" panel in the chosen frame;
- charge time through the XIAO's on-board charger stays acceptable
  (a bigger pack charges proportionally longer — measure, don't assume);
- fits the remaining hardware budget: the BOM total was ≈ €207 against
  the €300 ceiling, ≈ €93 headroom.

How much a bigger pack actually buys depends on SEED-007's open question:
the measured 0.923 mAh/cycle does not yet separate per-wake energy from
standing deep-sleep leakage. Capacity helps either way (autonomy ≈
capacity ÷ daily consumption), but the *interval* that makes the pack
worth it cannot be chosen honestly until that split is known or
deliberately bounded. Phase 34's firmware power work (FW-09..FW-12:
DHCP, TLS reuse, battery sampling, memtest) also changes the per-wake
cost, so any projection should use post-Phase-34 measurements.

Knock-on work if the pack changes: `hardware/BOM.md` (new line, budget
recomputed), `hardware/logtools.py`'s `--capacity-mah` for any new
discharge run, and a check that the SEED-006 voltage→percent curve (fit
on the 3000 mAh pack) still holds for the new cell chemistry.

## When to Surface

**Trigger:** milestone v1.1 (earmarked 2026-09-24 with SEED-007, SEED-008 and SEED-009). Originally: When SEED-007's second discharge measurement (separating
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
- `hardware/BOM.md` — current pack, connector/polarity constraints, budget headroom

## Notes

Captured 2026-09-15 during DEVICE-05's Task 3 write-up, at the developer's
explicit request to think through what this run's data should change
going forward. Sibling seed SEED-007 (separating per-wake cost from
standing leakage via a second measurement) should ideally inform this
choice rather than being skipped.
