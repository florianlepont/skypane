---
id: SEED-002
status: dormant
planted: 2026-09-02
planted_during: Phase 5 (05-low-battery-indicator) — DEVICE-05 battery discharge run
trigger_when: when relevant
scope: unknown
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

**Trigger:** when relevant

This seed will surface during `/gsd-new-milestone` when the milestone scope matches.

## Scope Estimate

**Unknown** — run `/gsd-capture --seed --enrich SEED-002` to estimate effort.

## Breadcrumbs

- `deploy/skypane.env.example` — `SKYPANE_SLEEP_S` and its comment on why the value matters mechanically (poll cadence vs. server refresh cadence)
- `deploy/skypane-byos.service` — `--sleep ${SKYPANE_SLEEP_S}` passed to `stub-server/byos_server.py` at service start
- `server/device_config.py` — the existing `THEMES`/`RUNWAYS` registry pattern CFG-01/CFG-12 already use for web-configurable device settings; the natural home for a new `SKYPANE_SLEEP_S`-equivalent setting
- `companion/pages/config_page.py` — the existing theme/runway picker form this would extend
- `hardware/BATTERY-RUN.md` — DEVICE-05's `### Observation channel` section, which documents `SKYPANE_SLEEP_S=300` as the pre-registered measurement interval and the SSH-only mechanism for setting it

## Notes

Captured via one-shot seed capture during a live conversational session
walking through DEVICE-05's discharge run. Enrich with trigger, why, and
scope at your convenience.
