---
id: SEED-001
status: fulfilled
planted: 2026-09-01
resolved_date: 2026-09-04
planted_during: "Phase 5: Battery Life & Low-Battery Indicator"
trigger_when: "Once Phase 5's real multi-day discharge run (05-01 Tasks 2-3, DEVICE-05) produces an actual battery-life verdict — same trigger as the sibling seed presence-adaptive-poll-cadence.md, since this is the other lever for cutting battery spend during hours nobody is looking. Also revisit whenever the companion web interface's config surface (device_config.py / companion/pages/config_page.py) is next extended, since a quiet-hours schedule fits naturally alongside the existing theme/runway/LED toggles."
scope: medium
---

# SEED-001: Scheduled quiet hours — pause the frame's wake/poll/display cycle during set windows (e.g. a curfew), configurable via the companion web interface

## Fulfilled 2026-09-04

This seed shipped in full as Phase 10, `.planning/phases/10-scheduled-quiet-hours/`, plans `10-01` through `10-05`, completed 2026-09-03 — the seed is closed.

Each layer delivered concretely: `server/device_config.py` gained the three registry fields (`quiet_hours_enabled`, `quiet_hours_start`, `quiet_hours_end`), the never-raising read-path normalisers, a strict pre-write gate in `save_device_config()`, and the DST-safe Europe/Paris window arithmetic `seconds_until_quiet_hours_end()` plus its epoch wrapper `quiet_hours_status()` (`10-01`); `server/plane/render.py` gained `_build_quiet_hours_canvas()`, dispatched ahead of the empty-state branch (`10-02`); `stub-server/byos_server.py` gained `read_quiet_hours()`/`quiet_hours_sleep_s()` extending `GET /device/v1/display`'s `sleep_s`, as a vendored duplicate pinned by an automated drift guard (`10-03`); `server/poll_loop.py`'s `run_once()` gained the render-once-at-entry / hold-silently / repaint-once-on-exit gate (`10-04`); and `companion/pages/config_page.py` gained `quiet_hours_group()`, the Settings page's fourth group (`10-05`).

The evidence of record is the phase's own completed gates: `10-VERIFICATION.md` (`status: passed`, 27/28 must-haves verified, no gaps found), `10-UAT.md` (`status: complete`, 2/2 tests passed, 0 issues), and `10-SECURITY.md` (`status: verified`, 0 threats open). This is a human-signed-off result, not a code-only claim.

Answering this seed's own open questions, including two divergences from what it predicted: the central design question (item 3, option (a) stop waking entirely vs. option (b) wake but skip the refresh) resolved as (a) — but the seed's stated reason for hesitating about (a), that it would need "a bigger change to `state_machine.c`/`app_main.c`'s sleep-duration logic," was wrong: `sleep_s` was already a per-response, fully server-controlled value, so extending it needed zero firmware change. The display-during-quiet-hours question (item 4) resolved as a dedicated one-time "QUIET HOURS / Back at HH:MM" screen rendered once at entry, held for the rest of the window, with no symmetric screen at exit — not a blank panel and not a held previous image. The seed's own trigger (waiting on Phase 5's multi-day discharge verdict) never fired as written: the phase was promoted at the developer's direct request on 2026-09-02 instead. And the `CFG-13`-style requirement entry this seed's Notes anticipated on promotion was never created — Phase 10 shipped as an unmapped backlog phase, and `REQUIREMENTS.md` still has no quiet-hours entry.

Two non-blocking WARNING-level code-review findings (zero critical) remain open; `10-REVIEW.md` is their authoritative home.

Everything below is the original 2026-09-01 record, retained unchanged as history.

## Why This Matters

The device currently wakes and polls on a fixed cadence with no concept of "do not disturb" hours — a curfew window (couvre-feu), a bedroom placement where the user wants it dark at night, or simply "nobody's home right now" all still trigger the full wake → HTTPS poll → download → display → deep-sleep cycle, spending battery and airtime for no one to see. This is a second, complementary lever to the presence-adaptive-poll-cadence seed: that one reacts to real-time presence via a PIR sensor, this one is a simple, predictable, user-declared schedule — arguably much cheaper to build (no new hardware, pure config + firmware/server logic) and useful even before Phase 5's real battery numbers exist, since some users want the frame dark on principle during certain hours regardless of power impact.

## When to Surface

**Trigger:** Once Phase 5's real multi-day discharge run (05-01 Tasks 2-3, DEVICE-05) produces an actual battery-life verdict — same trigger as the sibling seed `presence-adaptive-poll-cadence.md`. Also revisit whenever the companion web interface's config surface is next extended.

This seed will also surface during `/gsd-new-milestone` when the milestone scope matches.

## Scope Estimate

**Medium** — needs a phase, not a quick task. Rough shape:

1. **Config data model** — a `quiet_hours` block (start/end time, and whether it's a daily-recurring window or day-specific) alongside `device_config.py`'s existing `theme`/`tracked_runway`/`led_enabled` registry, following the same `normalise_*()` + `load_device_config()`/`save_device_config()` validation pattern.
2. **Companion UI** — a new Config-page section (`companion/pages/config_page.py`) to set/edit the window, mirroring the existing theme/runway/LED fieldsets.
3. **Behavior decision (the real design question)**: does "quiet hours" mean —
   - (a) the device stops waking entirely during the window (biggest battery win, but needs the firmware to compute an extended `sleep_s` that spans past the window boundary rather than the normal short interval — bigger change to `state_machine.c`/`app_main.c`'s sleep-duration logic), or
   - (b) the device still wakes on the normal cadence but the server tells it to skip the display refresh (simpler: server-side check in the poll response, no device-side clock/schedule logic needed, smaller battery win since Wi-Fi connect + HTTPS round-trip still happens every cycle)?
   Option (a) needs the device to know the time reliably across the window (it already does SNTP sync per wake, per `firmware/VENDOR.md`'s `wifi.c` notes) and needs a decision on what happens if the window boundary is crossed mid-sleep. Option (b) is a much smaller change but bank a lot less battery.
4. **Display state during quiet hours** — does the panel go fully blank/black, hold the last image, or show a small "quiet hours" indicator? Interacts with the e-ink "don't refresh needlessly" ethos already baked into the hash-skip logic.

## Breadcrumbs

- `server/device_config.py` — existing config registry pattern to extend (`normalise_led_enabled()`, `load_device_config()`, `save_device_config()`, lines ~113-210)
- `companion/pages/config_page.py` — companion UI page where a new quiet-hours fieldset would live, alongside the existing theme/runway/LED sections
- `firmware/main/app_main.c` / `firmware/main/state_machine.c` — device-side wake/sleep state machine; option (a) above would touch the sleep-duration computation here
- `server/poll_loop.py` — server-side poll/render loop; option (b) above would touch the `/display` response logic here
- `.planning/seeds/presence-adaptive-poll-cadence.md` — sibling seed, same trigger condition (Phase 5's real discharge-run verdict), complementary mechanism (reactive/sensor-based vs. scheduled/declarative)
- `.planning/REQUIREMENTS.md` — CFG-01..12 (Companion Configuration Web Interface) is the natural home for a new CFG-13-style requirement if this gets promoted

## Notes

Captured 2026-09-01, mid-conversation, prompted by the user's mention of wanting the frame off during curfew hours. Not yet scoped against CFG-13/a new requirement ID — REQUIREMENTS.md's v1 list currently ends at CFG-12; a promotion would add a new CFG entry there.
