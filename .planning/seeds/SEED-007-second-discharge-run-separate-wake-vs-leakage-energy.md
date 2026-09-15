---
id: SEED-007
status: dormant
planted: 2026-09-15
planted_during: Phase 5 (05-low-battery-indicator) — DEVICE-05 battery discharge run, Task 3 write-up
trigger_when: when relevant
scope: unknown
---

# SEED-007: Second discharge run at a different wake interval, to separate per-wake energy from standing deep-sleep leakage

## Why This Matters

DEVICE-05's completed discharge run (`hardware/BATTERY-RUN.md`, concluded
2026-09-14, 12.34 days at a 300s test cadence) is a single equation in two
unknowns: the measured 0.923 mAh/cycle is consistent with a wide range of
splits between "energy cost of waking up" (Wi-Fi, HTTP round trip) and
"energy cost of standing deep-sleep leakage between wakes." A single
cadence cannot separate the two, and the run's own projection band shows
how much that ambiguity costs: at a 3600s candidate interval, the honest
range is 12.34 to 148.08 days depending entirely on the unresolved split.

Resolving it turns two currently-unanswerable questions into informed
decisions:

1. Whether a higher-capacity battery pack is worth buying at all — it
   would help enormously if leakage dominates and barely at all if
   per-wake cost dominates.
2. Whether `PROJECT.md`'s deferred solar-charging question — explicitly
   gated on "real battery life and frame placement... known" — can now be
   revisited with confidence, or still can't.

## When to Surface

**Trigger:** when relevant

This seed will also surface during `/gsd-new-milestone` when the milestone scope matches.

## Scope Estimate

**Unknown** — run `/gsd-capture --seed --enrich SEED-007` to estimate effort.

Likely smaller than DEVICE-05's own protocol: doesn't need the full 21-day
ceiling or a fresh from-scratch pre-registration — a shorter run at a new
candidate interval (e.g. `SKYPANE_SLEEP_S=3600`, now trivially settable via
Phase 11's web-configurable wake interval instead of an SSH edit), cross-
checked against the first run's mAh/cycle figure, would likely suffice to
fit the two-unknowns equation and resolve the split.

## Breadcrumbs

- `hardware/BATTERY-RUN.md` — the completed first run, its `## What This
  Figure Does Not Cover` section (states this exact limitation), and its
  `## Calibration & Follow-Up Findings` section (this seed's original
  writeup)
- `hardware/logtools.py` — `check-battery`'s projection-band computation,
  the `from-history-db` channel this run's protocol settled on
  (`### Observation channel` in `BATTERY-RUN.md`)
- `companion/pages/config_page.py` — Phase 11's wake-interval field, the
  mechanism for setting the new candidate interval without SSH
- `.planning/PROJECT.md` — the solar-charging deferral clause this
  resolution would let the project revisit

## Notes

Captured 2026-09-15 during DEVICE-05's Task 3 write-up, at the developer's
explicit request to think through what this run's data should change
going forward, not just record the measurement itself. Sibling seed
SEED-008 (choosing the real field wake interval) should ideally wait on
or cross-check against this one.
