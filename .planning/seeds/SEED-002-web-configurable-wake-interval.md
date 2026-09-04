---
id: SEED-002
status: fulfilled
planted: 2026-09-02
resolved_date: 2026-09-04
planted_during: Phase 5 (05-low-battery-indicator) — DEVICE-05 battery discharge run
trigger_when: "User requested direct promotion to active work, 2026-09-03 — planned alongside sibling SEED-001 (scheduled quiet hours)."
scope: medium
---

# SEED-002: SKYPANE_SLEEP_S should be configurable through the companion web configuration interface

## Fulfilled 2026-09-04

This seed shipped in full as Phase 11, `.planning/phases/11-web-configurable-wake-interval/`, plans `11-01` through `11-04`, completed 2026-09-04 — the seed is closed.

Each layer delivered concretely: `server/device_config.py` gained `WAKE_INTERVAL_MIN_S = 60` / `WAKE_INTERVAL_MAX_S = 3600`, the never-raising `normalise_wake_interval_s()`, the seventh `load_device_config()` key `wake_interval_s`, and a strict pre-write gate in `save_device_config()` (`11-01`); `stub-server/byos_server.py` gained the fail-open `read_wake_interval_s()`, feeding `GET /device/v1/display`'s `sleep_s` as the base value that Phase 10's `quiet_hours_sleep_s()` extends (`11-02`); `companion/pages/config_page.py` gained `wake_interval_group()`, the Settings page's fifth group and this codebase's first native `<input type="number" min="60" max="3600">`, wired through an explicit string-to-`int()` conversion gate into the page's single existing `save_device_config()` call (`11-03`); and `companion/app.py` gained the fail-open `env_wake_interval_default()`, threading the deployed `SKYPANE_SLEEP_S` into the page context as `wake_interval_env_default` so the field pre-fills, degrading to a "Uses server default" placeholder when that value is absent or out of bounds (`11-04`).

The evidence of record is the phase's own completed gates: `11-VERIFICATION.md` (`status: passed`, 22/22 must-haves verified, no gaps), `11-UAT.md` (`status: complete`, 1/1 test passed, 0 issues), and `11-SECURITY.md` (`status: verified`, 0 threats open).

Answering this seed's own open questions and their divergences: the delivery design question (item 3, option (a) server returns the interval in the poll response vs. option (b) a config-write service restart) resolved as (a), exactly as this seed itself predicted was "the more natural fit" — a saved value reaches the device as `sleep_s` on its very next poll, with no service restart and `deploy/skypane-byos.service` untouched. The "sane min/max" question (item 2) resolved as 60-3600 seconds, the floor grounded in `firmware/main/Kconfig.projbuild`'s own `FP_MIN_REFRESH_SPACING_S` default and the one-hour ceiling developer-confirmed. The one place the seed's prediction did not hold: it expected the field to follow the existing `normalise_*()`/`load_device_config()`/`save_device_config()` pattern "used for theme/runway/LED" exactly, but `wake_interval_s` is the only field in that registry whose unset state is `None` rather than a `DEFAULT_*` constant, because the true fallback (`SKYPANE_SLEEP_S` / `--sleep`) lives in a different OS process's argparse namespace and is not knowable from `device_config.py`.

One thing shipped beyond this seed's own scope: the environment-default pre-fill, plus a corrected comment in `deploy/skypane.env.example` — a file this seed itself listed as a breadcrumb — with no change to that file's shipped value and no change to either systemd unit file. `REQUIREMENTS.md` was not extended; like Phase 10, this shipped as an unmapped backlog phase.

One cosmetic observation from UAT was accepted rather than fixed: the "Uses server default" placeholder renders visually truncated to "Uses" at the tested viewport widths because the native number input sizes to roughly 74px with no explicit width; the developer reviewed screenshots and explicitly accepted it as-is rather than filing a gap. `11-UAT.md` is where that detail lives.

Two non-blocking WARNING-level code-review findings (zero critical) remain open; `11-REVIEW.md` is their authoritative home.

Everything below is the original 2026-09-02 record, retained unchanged as history.

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
