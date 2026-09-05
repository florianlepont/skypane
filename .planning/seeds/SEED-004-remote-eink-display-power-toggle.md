---
id: SEED-004
status: dormant
planted: 2026-09-04
planted_during: "Phase 06.6.4.1 (companion page-by-page IA consolidation)"
trigger_when: "When the companion Settings page's control set is next revisited — this belongs beside the four toggles already there (theme, runway, LED, quiet hours, wake interval), and is small enough that it is worth folding into any phase that already opens `companion/pages/config_page.py` and `server/device_config.py` together. No hardware or battery-verdict dependency, unlike its siblings."
scope: small
---

# SEED-004: Turn the e-ink panel off and back on remotely, from the companion web interface

## Why This Matters

Every other user-facing behaviour of the frame is now controllable from the
companion interface — theme (CFG-01), tracked runway (CFG-12), the bring-up
LED (Phase 06.2), quiet hours (Phase 10) and the wake interval (Phase 11) —
with one gap: there is no way to simply turn the display *off* right now and
back on later. Quiet hours covers the scheduled case ("dark every night
between 23:00 and 07:00"), but not the unscheduled one: leaving for a week,
a guest sleeping in the room, or just wanting the wall blank today. Today
the only ways to get there are editing the quiet-hours window into something
it was not designed for, or physically unplugging the frame.

This is deliberately the *manual, immediate* sibling of two existing seeds:
`SEED-001` (now fulfilled as Phase 10) was the declarative schedule, and
`presence-adaptive-poll-cadence.md` is the automatic sensor-driven version.
This one is the plain switch, and it is the cheapest of the three because
Phase 10 already built almost all of the machinery it needs.

## When to Surface

**Trigger:** when the companion Settings page's control set is next
revisited. Unlike its two siblings, this seed has no dependency on the
DEVICE-05 battery verdict or on new hardware — it could be picked up at any
time.

This seed will also surface during `/gsd-new-milestone` when the milestone
scope matches.

## Scope Estimate

**Small** — most of the hard parts already shipped in Phase 10, and this is
largely a matter of reaching them from a manual switch instead of a clock.
Phase 10 already answered the two questions that would otherwise make this
big:

1. **What "off" means on e-ink** — already solved. Phase 10's `10-02` built
   a dedicated "QUIET HOURS / Back at HH:MM" render state rather than
   blanking the panel, precisely because e-ink holds its last image for
   free. A manual off-switch wants the same treatment with different copy
   (there is no "back at" time to promise when the switch is manual — the
   copy question is the one real design decision here).
2. **How the device stops working while off** — already solved. Phase 10's
   `10-03` extends `sleep_s` on `GET /device/v1/display` so the device
   sleeps *through* the window, and `10-04` gates `run_once()`'s render
   pipeline and repaints the live board on exit. A manual toggle needs the
   same gate with an open-ended end condition instead of a computed window
   exit — which is the one genuinely new piece of logic, since `sleep_s`
   cannot be infinite and the device must still wake periodically to learn
   that it has been switched back on.

What is left, then:

- A `display_enabled` boolean in `server/device_config.py`'s registry,
  following `normalise_led_enabled()`'s exact pattern (this is the closest
  precedent — same shape, same never-raising discipline).
- A Settings-page toggle in `companion/pages/config_page.py`, following
  `led_group()` / `quiet_hours_group()` and reusing the shared
  `settings-checkbox` label class (introduced by quick task `260901-qif`,
  which renamed the LED group's original class to serve both).
- The gate itself: reuse Phase 10's quiet-hours gate in `server/poll_loop.py`
  and its `sleep_s` extension in `stub-server/byos_server.py`, with a
  bounded poll interval while off (so toggling back on is picked up within
  one interval rather than never) — decide that interval against
  `wake_interval_s`'s existing 60-3600s bounds from Phase 11.
- Copy for the off-state panel, per point 1 above.

**Watch for:** the interaction between this switch and quiet hours. If both
are active the precedence needs to be explicit and testable ("off wins,
always" is the obvious answer) rather than emergent from whichever gate the
poll loop happens to evaluate first.

## Breadcrumbs

- `server/device_config.py` — `DEFAULT_LED_ENABLED` / `normalise_led_enabled()`
  is the direct pattern to copy for a `display_enabled` field; the
  quiet-hours fields added by `10-01` sit here too
- `server/plane/render.py` — `_build_quiet_hours_canvas()` plus
  `QUIET_HOURS_HEADING_TEXT` / `QUIET_HOURS_BODY_TEMPLATE` (`"Back at %s"`)
  from `10-02` are the precedent for an off-state panel and its copy
- `server/poll_loop.py` — `10-04`'s quiet-hours gate (render once at entry,
  hold, repaint the live board at exit) is the exact control flow to extend
- `stub-server/byos_server.py` — `quiet_hours_sleep_s()` from `10-03` and
  `read_wake_interval_s()` from `11-02` are where an extended `sleep_s`
  for the off state would land
- `companion/pages/config_page.py` — the LED and quiet-hours groups are the
  two UI patterns to mirror, including `10-05`'s shared checkbox class
- `.planning/seeds/presence-adaptive-poll-cadence.md` — sibling seed, the
  automatic version of the same "should the frame be showing anything right
  now?" question

## Notes

Captured 2026-09-04 during a seed-inventory review, from the user's own
one-line description ("éteindre et allumer à distance l'écran e-ink"). No
design conversation behind it yet — the scope breakdown above is derived
from what Phases 10 and 11 already shipped, not from a discussed design.
Confirmed not already covered: no `display_enabled`-style flag or manual
off-switch exists anywhere in the tree as of `b0cc887`.
