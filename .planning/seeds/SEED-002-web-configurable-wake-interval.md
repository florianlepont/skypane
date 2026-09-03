---
id: SEED-002
status: dormant
planted: 2026-09-02
planted_during: Phase 5 (05-low-battery-indicator) — DEVICE-05 battery discharge run
trigger_when: "User requested direct promotion to active work, 2026-09-03 — planned alongside sibling SEED-001 (scheduled quiet hours)."
scope: medium
---

# SEED-002: SKYPANE_SLEEP_S should be configurable through the companion web configuration interface

## Why This Matters

The device's wake/poll interval (`SKYPANE_SLEEP_S`) currently lives only as a
VPS-side environment variable in `/opt/skypane/skypane.env`, changed by
editing that file over SSH and restarting `skypane-byos.service`
(`deploy/skypane-byos.service`'s `--sleep ${SKYPANE_SLEEP_S}` argument).
Surfaced live during Phase 5's DEVICE-05 battery discharge run
(2026-09-02), while manually SSHing in to set it to 300 for the
measurement, then restoring it to 30 afterward — a purely mechanical,
SSH-only task with no web-UI path.

A future phase could let the developer change the device's wake cadence
from the companion web interface the same way theme and tracked-runway
are already configurable there (CFG-01/CFG-12 precedent in
`server/device_config.py`'s registries), instead of requiring SSH access
and a service restart every time.

## When to Surface

**Trigger:** Fired directly by developer request (2026-09-03), rather than waiting on a
milestone scan — planned as a companion phase alongside SEED-001 (scheduled quiet
hours), since both extend the same `device_config.py` registry and
`companion/pages/config_page.py` form.

## Scope Estimate

**Medium** — a phase, not a quick task. It touches three layers, not just the web form:

1. **Config data model** — a `wake_interval_s` (or similarly named) field in
   `device_config.py`'s registry, following the existing `normalise_*()` +
   `load_device_config()`/`save_device_config()` pattern used for theme/runway/LED.
2. **Companion UI** — a new field in `companion/pages/config_page.py`'s form, with
   validation (a sane min/max — too short burns battery, too long risks staleness at
   the moment someone glances at the frame).
3. **Delivery to the device** — the real design question: `SKYPANE_SLEEP_S` today is a
   process-start argument to `skypane-byos.service` (`deploy/skypane-byos.service`),
   read once at service start. Making it live-configurable from the web UI means either
   (a) the server passes the current interval back in the poll/`/display` response and
   the device honors it as its *next* sleep duration (no service restart needed, small
   protocol addition), or (b) the config write triggers a service restart server-side
   (simpler code, but a jarring "restart the whole service for one setting" mechanism).
   Option (a) is the more natural fit for how CFG-01/CFG-12 already work (device reads
   its config live on each poll) and avoids service-restart plumbing entirely.

## Breadcrumbs

- `deploy/skypane.env.example` — `SKYPANE_SLEEP_S` and its comment on why the value matters mechanically (poll cadence vs. server refresh cadence)
- `deploy/skypane-byos.service` — `--sleep ${SKYPANE_SLEEP_S}` passed to `stub-server/byos_server.py` at service start
- `server/device_config.py` — the existing `THEMES`/`RUNWAYS` registry pattern CFG-01/CFG-12 already use for web-configurable device settings; the natural home for a new `SKYPANE_SLEEP_S`-equivalent setting
- `companion/pages/config_page.py` — the existing theme/runway picker form this would extend
- `hardware/BATTERY-RUN.md` — DEVICE-05's `### Observation channel` section, which documents `SKYPANE_SLEEP_S=300` as the pre-registered measurement interval and the SSH-only mechanism for setting it

## Notes

Captured via one-shot seed capture during a live conversational session
walking through DEVICE-05's discharge run. Enriched 2026-09-03 — trigger and
scope filled in — after the developer asked to work on this seed directly,
without waiting for a milestone scan.
