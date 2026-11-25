---
id: SEED-018
status: dormant
planted: 2026-11-15
planted_during: "v1.2, owner's question of 2026-11-15: how is a firmware update managed, offered to the user or pushed by the admin?"
trigger_when: "Milestone v1.3, set by the owner on 2026-11-15 when v1.4 and v1.3 were split; it becomes critical once frames sit in other homes; surface it at /gsd-new-milestone."
target_milestone: v1.3
scope: medium
---

# SEED-018: Firmware update policy (user choice, admin override)

## Why This Matters

Once frames sit in several homes, the owner needs a clear rule for who decides
when a frame is updated. Today an update is manual and per frame: the owner of
the frame picks a published release in the companion (`companion/pages/update_page.py`),
schedules it, and it installs at the next wake, held back by quiet hours. A
frame that fails an update stays on its previous firmware. There is no
automatic update, no offer to the user and no push by the administrator.

## Decision of 2026-11-15 (owner)

**Mixed model.** Each frame has an update mode chosen by its owner:

- **Automatic** (the default): a new release is installed on the frame without
  action.
- **Ask me**: the companion shows "update available" and the owner accepts.
- **Administrator override**: the administrator can force an update that is
  critical (for example a security fix), whatever the frame's mode.

**Rollout: all frames at the same time.** No staged rollout and no test group,
by the owner's choice. The safety net is therefore the device side (below), not
a gradual release.

## Safety rules to keep (from the discussion)

- No update starts when the battery is low (the threshold to be set from the
  Phase 47.1 and Phase 56 battery figures).
- Quiet hours are respected, except for an administrator override, to be decided.
- A failed installation leaves the frame on its previous firmware, reports the
  result (`X-Ota-Result`), and shows on the health page.
- Updates stay signed and verified (`firmware/SIGNING.md`).

## Open questions

1. **Can a user refuse or only postpone** an update in "ask me" mode? Not
   answered yet. A frame that never updates means several firmware versions to
   support, and the override needs a rule for it.
2. Does "automatic" apply at once at the next wake, or inside a time window
   (night) to avoid a slow first redraw during the day?
3. Who gets a notice when an update is installed or fails: the owner only, or
   co-managers too?
4. Because every frame updates together, how is a bad release stopped: a pause
   switch on the administrator side that withdraws the offer, and a rule to
   avoid installing on a release that fails its first check-in.
5. Interaction with the Wi-Fi setup (SEED-013, item 6) and the diagnostic
   telemetry (SEED-017), which are the first releases to travel this way, and
   with the second hardware type (Phase 64), whose releases are per type.

## Breadcrumbs

- `companion/pages/update_page.py` (the update page, schedule and quiet-hours wording)
- `.planning/workstreams/v1-2/phases/49-per-hardware-ota-registry/` (per-hardware release registry)
- `firmware/SIGNING.md` (signing and verification)
- `.planning/seeds/SEED-009-remote-firmware-update-ota.md` (the original OTA work, promoted)
- `.planning/seeds/SEED-017-remote-diagnostic-telemetry.md`, `SEED-013-photo-display-mode.md`
