# Phase 51: Per-Device Config, Image and State - Context

**Gathered:** 2026-10-30
**Status:** Ready for planning

<domain>
## Phase Boundary

Each device has its own config, image, poll state, history and health, and the BYOS serves each frame its own image from its own directory. The owner can trigger a poll for one device and set its quiet hours and timezone without touching any other device. There is no fallback to a shared "default" device.

Requirements: FLT-01, FLT-02. Depends on Phase 48 (fleet.db, `devices.state_path`) and Phase 50 (image negotiation, which must keep working per device).

Not in this phase: the fleet-wide poll loop, zones and request budget (52), detection modes (53), Auth0 and route enforcement (54), pairing and admin console (55), per-hardware rendering (56), production deploy. Phase 47 files and `hardware/` are untouched.

</domain>

<decisions>
## Implementation Decisions

### Owner-fixed (not to be reopened)
- **D-01 (owner):** The live frame keeps its MAC, secret, token, file paths (`state_path = "."`), current raw image and wake interval byte for byte. `stub-server/test_phase47_freeze.py` stays green.
- **D-02 (owner):** Expand-only: the previous release still runs on the state this phase produces.
- **D-03 (owner):** A frame that does not announce the container still receives the raw image (Phase 50 negotiation applies per device).
- **D-04 (owner):** No production deploy.

### Directory layout (owner choice, 2026-10-30)
- **D-05:** New devices live in `<state_dir>/devices/<id>/`, `<id>` being the numeric `devices.id` of fleet.db. The path is stored in `devices.state_path`. No MAC in paths.
- **D-06:** The live frame stays at the root of the state dir (`state_path = "."`); it is never moved. Each device directory holds the same file set a state dir holds today (`device_config.json`, `poll_state.json`, `panel.bin`, history DB, `img/`, battery state).
- **D-07:** The BYOS resolves the presented token or MAC to its device and reads/writes only that device's directory. `--image` remains the live frame's image only; no other device ever falls back to it, and the `"default"` device fallback is gone (an unresolved token is a 401).

### Companion navigation (owner choice)
- **D-08:** A device selector at the top of the companion. Existing pages (home, health, history, settings) show the selected device; the live frame is selected by default and its current URLs keep working unchanged.
- **D-09:** Per-device routes use a `/devices/<id>/...` prefix and are declared in the route table so Phase 54 can annotate each with a minimum role and ownership check without restructuring. All device-scoped handlers take an explicit device argument; none reads a global state dir.
- **D-10:** Bilingual UI (strings in `companion/i18n_fr/`), design per `sketch-findings-skypane`.

### Single-device poll (owner choice)
- **D-11:** "Poll now" for a device runs the existing cycle (same Orly runway-3 detection) against that device's directory only: image, poll state, history and health are written there and nowhere else. Fleet-wide polling and zone sharing are Phase 52.
- **D-12:** The poll lock is per device, so polling one device never blocks or alters another.

### Quiet hours and timezone (owner choice)
- **D-13:** The timezone is a validated IANA field in each device's own `device_config.json`, next to quiet hours. Default `Europe/Paris`, so the live frame's behaviour does not change. The fixed `QUIET_HOURS_TZ` constant becomes the default, not the only value.
- **D-14:** Setting quiet hours or timezone for one device writes that device's config only; a test proves other devices' files are byte-identical.

### Claude's Discretion
- Module and function names, the device-resolution helper, test layout, plan split and waves, how simulated devices get their initial image/config, and the migration of nothing for the live frame (none is needed).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

- `.planning/workstreams/v1-2/ROADMAP.md` — Phase 51 goal and success criteria
- `.planning/workstreams/v1-2/REQUIREMENTS.md` — FLT-01, FLT-02
- `.planning/workstreams/v1-2/STATE.md` — edit only Phase 51 lines
- `.planning/workstreams/v1-2/phases/48-fleet-data-model-roles-and-live-frame-migration/48-CONTEXT.md` — freeze list, `state_path`, D-09 default-device drop
- `.planning/workstreams/v1-2/phases/50-common-image-format/50-CONTEXT.md` — negotiation per request, hash semantics
- `.planning/workstreams/v1-2/research/ARCHITECTURE.md`, `SUMMARY.md`, `PITFALLS.md` — single-frame assumptions
- `stub-server/byos_server.py` — `_resolve_device_id`, device_config readers, display handler, `--image`
- `stub-server/test_phase47_freeze.py`, `stub-server/measured_fields_freeze.json` — freeze test
- `server/device_config.py`, `server/state_store.py`, `server/device_policy.py`, `server/poll_cycle.py`, `server/history_db.py`, `server/fleet_db.py`
- `companion/routes.py`, `companion/post_actions.py`, `companion/settings/quiet_hours.py`, `companion/pages/`
- `.claude/CLAUDE.md`, `.claude/skills/sketch-findings-skypane/` — conventions and design system

</canonical_refs>

<code_context>
## Existing Code Insights

- `devices.state_path` already exists in fleet.db; the live frame has `"."`.
- `device_config.json`, `poll_state.json`, `byos_state.json`, `battery_state.json` and `img/` are all keyed by a single `state_dir` argument, so a per-device directory can reuse the same code by passing a different `state_dir`.
- `device_policy.QUIET_HOURS_TZ` is hardcoded `Europe/Paris`.
- Companion `/poll-now` and settings handlers use one state dir today.

</code_context>

<specifics>
## Specific Ideas

- Owner is French-speaking and not an engineer: anything the owner must do is plain French; repository docs stay English.
- Final report must list exactly which device-scoped routes Phase 54 must annotate.

</specifics>

<deferred>
## Deferred Ideas

- Fleet poll loop, shared zones, request budget — Phase 52.
- Per-device location/detection mode — Phase 53.
- Role and ownership enforcement on device routes — Phase 54.
- Device creation UI and pairing — Phase 55.

</deferred>

---

*Phase: 51-per-device-config-image-and-state*
*Context gathered: 2026-10-30*
