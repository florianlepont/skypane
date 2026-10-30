# Phase 52: Fleet Poll Cycle, Zones and Request Budget - Context

**Gathered:** 2026-10-30
**Status:** Ready for planning

<domain>
## Phase Boundary

The poll loop serves the whole fleet while total ADS-B requests stay within 1 per second across every zone and every provider. Devices sharing a zone are served by one upstream request set; the budget is persisted and holds across provider and process boundaries; a provider failure or timeout for one device or zone never delays the others' images.

Requirements: FLT-03, FLT-04. Depends on Phase 51 (per-device directories, config and state).

Not in this phase: airport/runway and position/radius detection and the rounding of coordinates sent to third parties (53), Auth0 and routes (54), pairing and admin console (55), per-hardware rendering (56), presence-adaptive cadence (FLT-05, deferred), production deploy. Phase 47 files and `hardware/` are untouched; the live frame's image, wake interval and state do not change; `stub-server/test_phase47_freeze.py` stays green; expand-only (the previous release still runs on the state this phase produces).

</domain>

<decisions>
## Implementation Decisions

### Owner-fixed (not to be reopened)
- **D-01 (owner):** The global budget is under 1 ADS-B request per second across all zones and all providers (adsb.fi, adsb.lol; airplanes.live is never used for the fleet). This is stricter than today, where two providers run in parallel (~1.8 req/s combined).
- **D-02 (owner):** adsb.fi is personal non-commercial use at 1 req/s and must be cited; adsb.lol is fragile (future API key, dynamic limits). Nothing in this phase may relax either.
- **D-03 (owner):** No production deploy; code, tests and CI only.

### Cost per zone and corroboration (owner choice)
- **D-04:** Every zone is queried on both default providers (adsb.fi then adsb.lol), keeping today's candidate-set corroboration exactly. A zone therefore costs 2 requests and about 2.2 s of budget; about 13 zones fit in a 30 s cycle.
- **D-05:** Spacing is global: at least 1.1 s (the current margin) between any two ADS-B requests, whatever the provider or zone. Requests are sequential, not parallel.

### Provider failure (owner choice)
- **D-06:** After a failure or a 4xx/429 a provider is paused for about 60 s. The pause is persisted and shared by every process that spends budget, so a fleet-wide failure never becomes a retry storm. A failed request still counts against the budget. While a provider is paused the zone proceeds as a single-source, uncorroborated poll (today's behaviour when one provider is down).

### Capacity, priority and inactive devices (owner choice)
- **D-07:** When zones exceed one cycle's capacity, zones that contain the live frame are served first, then the rest oldest-served-first. Unserved zones age; a device whose zone was not served keeps its current image and is flagged stale only through existing semantics.
- **D-08:** A device with no check-in for 7 days is skipped. The live frame and a device created less than 7 days ago with no check-in yet are exempt. A skipped device resumes as soon as it checks in again.
- **D-09:** Held devices (quiet hours, display off, battery critical) contribute no zone and cost no request, as today.

### Poll now (owner choice, 2026-10-30)
- **D-10:** "Poll now" is removed completely: the `POST /poll-now` route, the Home and Device buttons, the cooldown, its FR/EN strings and its tests. FLT-02 is amended: per-device quiet hours and timezone remain, the poll trigger is dropped. The budget therefore has one consumer, the poll process (a new oneshot every 30 s; overlapping runs and the per-device lock must still be safe).
- **D-11:** The removal ships last, in its own commit, after merging `main` right before, because the companion files it touches are also edited by the Phase 55 session.

### Zones and adsbdb (owner choice)
- **D-12:** A zone key is the exact (centre, radius) pair. Devices share a zone only when both are identical; no merging of neighbouring zones, no grid quantisation. Today every device resolves to the Orly geofence zone; Phase 53 plugs its detection modes and rounding into the same key.
- **D-13:** adsbdb stays outside the ADS-B budget. Lookups are deduplicated across devices through the shared cache (one request per callsign). The 30-day positive cache TTL is unchanged here and noted for Phase 56 (credits).

### Technical defaults (recorded from research; to be reported to the owner)
- **D-14:** The persisted ledger is a file in the state root guarded by an exclusive `flock` (separate from `fleet.db`, so no schema migration and the previous release ignores it). It stores last-request time and per-provider pause-until, on wall-clock time with the same clamping against clock steps as the existing spacing code.
- **D-15:** Fetch and select are split: one fetch per zone returns per-provider raw lists; each device selects from the shared result (pure). Corroboration semantics (candidate-set intersection) are unchanged.
- **D-16:** Failure isolation: each device runs in its own try/except; a zone fetch failure marks `source_fault` for that zone's devices only; a per-cycle deadline below the unit's 90 s `TimeoutStartSec` stops starting new zones.
- **D-17:** The live frame is still polled through its root state dir with the same cycle steps; simulated and other devices use their `devices/<id>/` directory. Devices whose hardware the cycle cannot render are skipped (Phase 56).

### Claude's Discretion
- Module and function names, ledger file name and format, plan split and waves, how the fake clock and fake providers are injected, and the shape of the simulated 100-device fleet.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Milestone
- `.planning/workstreams/v1-2/ROADMAP.md` (Phase 52) — goal and three success criteria
- `.planning/workstreams/v1-2/REQUIREMENTS.md` — FLT-03, FLT-04 (and FLT-02, amended by D-10)
- `.planning/workstreams/v1-2/research/ARCHITECTURE.md` — fleet cycle, zones and budget sections (fetch/select split, ledger, failure isolation)
- `.planning/workstreams/v1-2/research/PITFALLS.md` §C15 — budget blown by multiplying devices
- `.planning/workstreams/v1-2/phases/51-per-device-config-image-and-state/51-CONTEXT.md` — per-device directories, locks, hardware gating

### Data-source terms
- `COMPLIANCE.md` — adsb.fi, adsb.lol, airplanes.live, adsbdb terms and citations

### Code
- `server/poll_loop.py`, `server/poll_cycle.py` — cycle steps, lock, provider last-call memory
- `server/plane/detect.py` — providers, `MIN_SECONDS_BETWEEN_CALLS`, `poll_current_aircraft`
- `server/device_dirs.py`, `server/fleet_db.py`, `companion/device_scope.py` — device directories and listing
- `stub-server/test_phase47_freeze.py` — must stay green
- `deploy/skypane-poll.service`, `deploy/skypane-poll.timer` — 30 s oneshot, 90 s timeout

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `poll_cycle.run_once(state_dir=...)` — full per-directory cycle with per-device lock and `reconcile_firmware` switch
- `detect._spaced_query` / `_load_provider_last_calls` — existing per-provider spacing and clamping logic to generalise
- `fleet_db.list_devices`, `device_dirs.resolve_state_dir` — fleet enumeration and safe directory resolution

### Established Patterns
- Pure core with injected clock/sleep (`snapshot=`, `clock=`, `sleep=` seams) for deterministic tests
- Atomic writes through `server/atomic_io.py`; `fcntl` lock already used for the poll lock

### Integration Points
- `poll_loop.main` becomes the fleet entry point; `detect_flight` consumes a zone result instead of fetching
- Companion poll-now removal touches `companion/app.py`, `routes.py`, `flash.py`, `device_scope.py`, i18n and tests

</code_context>

<specifics>
## Specific Ideas

- Fleet test: 100 simulated devices, several zones, fake clock and fake providers, asserting at most 1 request in any 1-second window and failure isolation.

</specifics>

<deferred>
## Deferred Ideas

- Presence-adaptive cadence and per-user device caps (FLT-05).
- Grid-merged zones with a maximum radius (after Phase 53 rounding exists).
- Reviewing adsbdb's 30-day cache TTL (Phase 56 credits).
- Per-device priority setting.

</deferred>

---

*Phase: 52-Fleet Poll Cycle, Zones and Request Budget*
*Context gathered: 2026-10-30*
