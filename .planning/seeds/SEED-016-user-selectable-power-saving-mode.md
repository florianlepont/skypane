---
id: SEED-016
status: dormant
planted: 2026-11-15
planted_during: "v1.2, owner's roadmap discussion (idea forgotten from the v1.3 and v1.4 planning of 2026-11-14)"
trigger_when: "Milestone v1.3, set by the owner on 2026-11-15 when v1.3 and v1.4 were split; it follows the wake interval per mode of photo mode; surface it at /gsd-new-milestone."
target_milestone: v1.3
scope: small
---

# SEED-016: A power-saving mode the user can choose

## Why This Matters

The owner wants each user to be able to choose a **power-saving mode** for a
frame, in which the frame checks the server less often. A battery-only frame
spends most of its energy waking up, so fewer wake-ups means a longer time
between charges, at the price of a less fresh display. Today the wake rhythm is
set by the owner, not by the user.

## When to Surface

**Trigger:** milestone v1.3 (confirmed by the owner on 2026-11-15), because
photo mode (SEED-013) already needs a wake interval per mode. Do not start
before Phase 47.1 has produced its wake-energy measurements: the saving of
each setting has to be shown with real numbers, not guessed.

## Scope Estimate

**Small to medium, mostly server and companion.** Points to settle:

- **Where it is set:** a per-frame setting in the companion, visible to the
  owner and co-managers, with two or three named levels (for example normal and
  power saving) rather than a free number.
- **What changes:** the check interval (how often the frame wakes and asks the
  server) gets longer. The panel redraw rule stays as it is.
- **What the user is told:** the expected battery life and the expected delay
  before a change appears, per level, using `hardware/BATTERY-MODEL.md` and the
  measured figures of Phase 47.1.
- **Detection impact:** with fewer checks, a short event (a take-off seen once)
  can be missed or shown late. Say so in the interface. Check how it interacts
  with runway detection and the hold state.
- **Interaction with other settings:** quiet hours (SEED-001, done), the
  display power toggle, the low-battery behaviour (the frame may switch itself
  to power saving below a threshold), and photo mode, where a still picture
  already needs few wakes.
- **Firmware:** the server already controls the sleep length it sends, so a
  firmware change should not be needed. To confirm at planning time.

## Breadcrumbs

- `server/check_interval.py` (opt-in experiment separating check interval from redraw interval)
- `server/device_config.py`, `server/device_policy.py`, `server/wake.py` (wake interval and policy per device)
- `.planning/seeds/SEED-002-web-configurable-wake-interval.md`, `SEED-008-choose-real-field-wake-interval.md` (earlier wake-interval work)
- `.planning/seeds/presence-adaptive-poll-cadence.md` (another way to save battery)
- `.planning/seeds/SEED-013-photo-display-mode.md` (wake interval per mode)
- `hardware/BATTERY-MODEL.md` (energy figures)

## Notes

Not a replacement for a good default: the numbers of Phase 47.1 decide what the
levels are called and what they promise.
