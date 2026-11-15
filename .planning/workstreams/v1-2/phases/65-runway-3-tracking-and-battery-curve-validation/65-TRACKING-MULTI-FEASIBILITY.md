# Phase 65: TRK-02 multi-device feasibility (read-only)

**Date:** 2026-11-15 | **Plan:** 65-07 | **Status:** owner decision recorded (option A, scratch-local)

Evidence tags: [observed] = read in code or run here; [hypothesis] = inferred, not run.
Nothing under server/, stub-server/, companion/, deploy/ or firmware/ was edited. The spike ran in a scratchpad directory and never touched the repository state or production.

## Q1 What is polled for several devices

- `server/poll_loop.py` `main()` calls `run_fleet(args.state_dir, args.geofence, args.caddy_log, runner=run_once)` once per systemd oneshot. [observed]
- `fleet_cycle.load_fleet` reads fleet.db read-only (`_fleet_rows`, `fleet_db.connect_readonly`, `list_devices`, `device_coordinates`), puts the live row first and the others after; it falls back to the live frame alone when fleet.db is absent, unmigrated or unreadable. A non-live row whose `devices/<id>` directory is missing is skipped (`_device_from_row`). [observed]
- `fleet_cycle.runnable_devices` always keeps the live frame; every other device is dropped as `unsupported_hardware` when `_renders_here` is false and as `inactive` when `fleet_zones.device_is_active` is false (no check-in and created more than `INACTIVE_AFTER_S` ago). `_renders_here` calls `hardware.get_profile(type, os.environ or environ)`, and `hardware.available_types` only lists simulated types when `SKYPANE_SIM_HARDWARE == "1"` exactly (`hardware._sim_enabled`, `_flag_enabled`). [observed]
- `grep -rn SKYPANE_SIM deploy/` finds nothing: neither `deploy/skypane-poll.service`, `deploy/skypane.env.example` nor any other unit or template sets the flag. The poll unit only has `EnvironmentFile=/opt/skypane/skypane.env`. So on production a simulated device is skipped as `unsupported_hardware` unless the owner adds the flag to that env file. [observed]
- Simulated types in `hardware.REGISTRY`: `sim-ee02-clone` (1200x1600 portrait, same size as the live panel) and `sim-landscape-800x480`. Both pass `_renders_here` on this server (portrait at panel size, or landscape). `seeed-ee04-7in3-spectra6` is gated, not simulated. [observed]
- Zones: `fleet_cycle.detection_resolver` builds each device's `detection.spec_for(cfg, device.location)`; `plan_zones` groups non-held devices by exact `zone.key`. Devices of one airport on different runways share one zone and one fetch; held devices (battery, display off, quiet hours) and position-mode devices without a location join no zone and cost no request. `serve_zone` fetches once per zone (`zone_fetch.fetch_zone`, providers in `detect.DEFAULT_PROVIDER_ORDER`, sequential), then runs each device with the same `ZoneFetch`. [observed]
- Budget and deadline: `FLEET_START_DEADLINE_S = 25.0` stops new zones and devices after 25 s, but the live frame is never deferred (`serve_zone`: `self.expired() and not device.is_live`). Zones holding the live frame go first, others oldest-served first (`ordered_groups`, `fleet_zones.order_zones`). The shared ledger (`request_budget.RequestLedger`, rooted at the state root, `MIN_SPACING_S = 1.1` s between any two requests of any provider, `PROVIDER_PAUSE_S = 60`) spaces requests globally. [observed]
- Cost of a new zone: up to 2 provider requests (adsb.fi, adsb.lol) per cycle, each at least 1.1 s apart. Two extra airports add about 4 requests and at least 4.4 s of spacing to each 30 s cycle. The poll unit has `TimeoutStartSec=90s`. Whether this starves the live frame is unlikely (live zone goes first) but the fleet fetches share the single 1 req/s budget. [hypothesis for the timing; the mechanism is observed]
- Each device cycle (`poll_cycle.run_once`, called from `_FleetRun.run_device` with `ledger_root=self.root`) writes into its own `state_dir` (`history.db`, poll_state.json, panel files); `poll_cycle._ledger_root_for` maps `<root>/devices/<id>` to the root so all devices spend one ledger. [observed]

## Q2 What the export API returns per device

- Every export route reads one directory: `companion/export_api.py` `_serve_status` calls `status_snapshot(self.args.state_dir, time.time())` (line 241) and `_serve_export` calls `reader(self.args.state_dir, since, MAX_ROWS)` (line 252), where each reader is `history_db.export_table_rows(state_dir, table, since, max_rows)` (line 80). `args.state_dir` is the one state root passed to the companion process, i.e. the live frame's directory (`state_path "."`). [observed]
- The routes take only `since` (and `status` takes no parameter at all: `_serve_status` answers 400 when a query is present). There is no device parameter and no per-device route. A request cannot name a `devices/<id>` directory. [observed]
- A non-live device's `runway_events` and `poll_cycles` rows are written by its own cycle into `<root>/devices/<id>/history.db` (`history_db.open_db(state_dir)` inside `run_once`, `history_db.history_db_path(state_dir)`). No route exposes them. They are readable only by opening that file directly: `history_db._open_read_only` (mode=ro, `query_only=ON`) via `export_table_rows(state_dir, table, since, max_rows)`. [observed]

## Q3 How a simulated device's airport and runway are set

- `fleet_db.add_device(conn, mac, secret_sha256, hardware_type, owner_user_id, location_id=None, state_path="auto", environ=...)`: the owner is mandatory (IntegrityError otherwise), `hardware.get_profile(hardware_type, environ)` enforces the simulation gate (raises UnknownHardwareType without the flag), `state_path="auto"` stores `devices/<id>`; only one row may use "." (the live frame). The caller creates the `devices/<id>` directory (`_device_from_row` skips a row with no directory). `meta_set(conn, META_MIGRATED, ...)` makes the fleet readable by `_fleet_rows`. [observed; the migrated flag was set explicitly in the spike]
- `detection.apply_runway_selection(state_dir, icao, designator)` validates against `airports` (272 airports in the catalogue) and writes the device's `device_config.json`. The three Orly runways keep the legacy `tracked_runway` ids through `LEGACY_RUNWAY_MAP` (`"3"` is LFPO 07/25, `"06-24"`, `"02-20"`) and clear the detection object; every other runway stores `detection = {mode: runway, airport, runway}`. `apply_position_selection(state_dir, radius_km)` stores a position-mode object; its centre is the device's `locations` row (`fleet_db.add_location`, `location_id` on the device; `device_coordinates` feeds `FleetDevice.location`). [observed]
- Catalogue examples: LFPG has four parallel runways (08L/26R, 08R/26L, 09L/27R, 09R/27L); LFBO and LFLL have two; 162 LF airports have exactly one runway (for instance LFBE 09/27, LFBF 12/30). The owner still names the two airports (D-07). [observed]

## Q4 What production state would be touched if the devices were put in production

| Item | Evidence | Verdict |
|------|----------|---------|
| Production fleet.db rows (devices, locations, a user) | `fleet_db.add_device`, `add_location` | data only (rows added through existing code), but it is a production data change |
| Simulation flag `SKYPANE_SIM_HARDWARE=1` in the poll process environment | `deploy/skypane-poll.service` reads `/opt/skypane/skypane.env`; no deploy file sets the flag | needs a code or setting change (production env file on the VPS; also exposes simulated types in the companion add-device list, since `available_types` is process-wide) |
| Per-device export route | `export_api.py` lines 241 and 252 read only `args.state_dir` | needs a code or setting change (new route or parameter in companion/) |
| Shared request ledger and 1 req/s poll budget | `request_budget.RequestLedger`, `_ledger_root_for` | data only in effect, but the extra zones are spent from the live frame's budget and shared state (`request_ledger.json`) |
| Backups that include fleet.db and `devices/<id>/` | `deploy/README.md` (backup allow-list includes fleet.db; each `devices/<id>/` archived) | data only (the rows and directories would be archived automatically) |
| Companion lists (admin device list, users) | fleet.db rows | data only; test rows would be visible to the owner |
| Poll duration and provider traffic | `FLEET_START_DEADLINE_S = 25`, `TimeoutStartSec=90s`, up to 2 requests per new zone | data only, but adds provider load on the production address (`COMPLIANCE.md`: adsb.fi 1 request per second, counts 4xx) |

Summary: the fleet database rows, directories and runway settings are data only; the simulation flag and a per-device export route are what need a setting or code change. Without the flag no simulated device is polled on production; without a per-device route the export of a simulated device cannot be read through the API.

## Q5 Local proof and provider reachability

Spike script (outside the repository): `/tmp/claude-0/-home-user-skypane/e7b2962d-137b-5976-bbb9-b2fc84099ae6/scratchpad/spike65_07/spike.py`, run with `server/.venv/bin/python3`, scratch root `/tmp/claude-0/-home-user-skypane/e7b2962d-137b-5976-bbb9-b2fc84099ae6/scratchpad/spike65_07/root`. It builds fleet.db (one admin owner, a legacy live row with state_path ".", and three simulated devices: `sim-ee02-clone` on LFPG 08L/26R, `sim-landscape-800x480` on LFBE 09/27, `sim-ee02-clone` in position mode with a location row), then calls `fleet_cycle.run_fleet` with an injected fake fetcher and a fake runner. No network. [observed]

```
devices: live=d_c5ba64fc A=d_ac987ef7(LFPG 08L/26R) B=d_1ebb73eb(LFBE 09/27) C=d_7d1b54bd(position 10 km)
--- run_fleet, SIM flag set (environ=None)
zone_fetches=4 requests=4
  fetch lat/lon/radius_nm: (48.7233, 2.3794, 5.0)
  fetch lat/lon/radius_nm: (44.8253, 0.5186, 5.0)
  fetch lat/lon/radius_nm: (44.83, 0.52, 5.4)
  fetch lat/lon/radius_nm: (49.009, 2.5541, 5.0)
  outcome d_c5ba64fc live ok
  outcome d_1ebb73eb sim ok
  outcome d_7d1b54bd sim ok
  outcome d_ac987ef7 sim ok
  runner state_dir=. zone=48.7233|2.3794|5.0 profile=None location=None reconcile_fw=True
  runner state_dir=devices/d_1ebb73eb zone=44.8253|0.5186|5.0 profile=sim-landscape-800x480 location=None reconcile_fw=False
  runner state_dir=devices/d_7d1b54bd zone=44.83|0.52|5.4 profile=sim-ee02-clone location=(44.83, 0.52) reconcile_fw=False
  runner state_dir=devices/d_ac987ef7 zone=49.009|2.5541|5.0 profile=sim-ee02-clone location=None reconcile_fw=False
--- run_fleet, SIM flag unset (environ={})
zone_fetches=1 requests=1
  fetch lat/lon/radius_nm: (48.7233, 2.3794, 5.0)
  outcome d_1ebb73eb sim skipped unsupported_hardware
  outcome d_7d1b54bd sim skipped unsupported_hardware
  outcome d_ac987ef7 sim skipped unsupported_hardware
  outcome d_c5ba64fc live ok
--- directories/files written under scratch root
   fleet.db (+ -shm, -wal), request_ledger.json, request_ledger.lock, spike_marker.txt
   devices/d_1ebb73eb/{device_config.json, device_config.lock, spike_marker.txt}
   devices/d_7d1b54bd/{device_config.json, device_config.lock, spike_marker.txt}
   devices/d_ac987ef7/{device_config.json, device_config.lock, spike_marker.txt}
```

Reading: each simulated device gets its own zone (own airport, own fetch) and its own directory; the live frame is served first from the root with the legacy path and `reconcile_fw=True`, simulated ones with a profile and `reconcile_fw=False`; without the flag the same fleet.db skips every simulated device while the live frame still runs. The ledger and all writes stayed inside the scratch root. The real `run_once` was not run (it would need the full render stack and network); the injected runner only proves planning and routing. [observed; real-cycle behaviour is a hypothesis until plan 08]

Provider reachability from this environment (one GET each, no retry, COMPLIANCE.md read first: adsb.fi 1 req/s, adsb.lol dynamic limits, airplanes.live opt-in only so not queried):

| Provider | Request | Result |
|----------|---------|--------|
| adsb.fi (https://adsb.fi, cited per COMPLIANCE.md) | `/api/v2/lat/48.7233/lon/2.3794/dist/5` | HTTP 200, 1 472 bytes, one aircraft [observed] |
| adsb.lol | `/v2/point/48.7233/2.3794/5` | HTTP 200 on this single attempt (the caller had reported connection resets; they may be intermittent) [observed] |
| adsbdb.com | `/v0/callsign/AFR1234` | HTTP 200, 658 bytes, route JSON [observed] |

Providers and adsbdb are therefore reachable from here at the time of writing; flight-tracking sites were not (65-TRACKING-EXTERNAL.md).

## Live-frame baseline

`GET https://skypane.algernon.is/api/export/status` fetched once (HTTP 200, valid JSON, no credential read, written or logged; the proxy injects the token as in `scripts/export_snapshot.py`). Saved as `data/status_baseline_trk02.json`. At 2026-11-15T21:26:10Z it shows `device.tracked_runway = "3"`, `wake_interval_s = 300`, `display_enabled = true`, quiet hours 23:30 to 06:00 (Europe/Paris), `check_interval_experiment` 60 s, and `shown` EJU87WP (A320, arriving). The end-of-phase comparison should check the `device` object (the configuration) is unchanged.

## Options for the owner

A. **Scratch state root outside production** (this environment while the providers stay reachable, otherwise the owner's machine): its own fleet.db, ledger and history, `SKYPANE_SIM_HARDWARE=1` set only for that process, no production file or setting touched, no server change. Each device's export is read straight from its own `history.db` by a script (plan 08).
B. **Scratch state root on the VPS** under a separate directory, as a separate process started by the owner by hand: no production unit or setting changed, but it runs on the production host and shares its outbound address and provider limits (the scratch ledger does not coordinate with the production ledger, so combined traffic could exceed 1 req/s per provider [hypothesis]).
C. **Simulated devices in the production fleet**: needs the simulation flag in the production poll environment and a per-device export route, that is a server and deploy change plus a production data change; not covered by this phase without the owner's separate approval.
D. **No live multi-site sessions**: TRK-02 is recorded as not met, with the cause.

## Recommendation

Option A, running here. The proof shows the existing code already plans and serves several simulated airports from a scratch root with no server change, the providers and adsbdb answered from this environment, and the scratch history.db files can be read with the existing read-only helper. Caveats: this sandbox may go down between sessions, and adsb.lol reachability looked intermittent; if either fails during a session, fall back to the owner's machine (still option A) rather than B or C.

## Owner decision

**Date:** 2026-11-15 (given by the owner in chat)
**Option:** A, scratch-local (scratch state root outside production).

The owner's decision, quoted: "option A, scratch state root outside production, run in this cloud environment (fall back to the owner's machine, still option A, if the sandbox or a provider fails during a session)."

## Consequence

Option A needs no server, deploy or production change, so every later plan of the phase runs as written; none is skipped or blocked.

| Plan | Outcome | Note |
|------|---------|------|
| 08 | runs | tooling only: scripts/multi_site_setup.py, multi_site_run.py, multi_site_export.py with tests |
| 09 | runs | the owner names the two airports from the catalogue; the scratch fleet is created in a root under the scratchpad (this environment) |
| 10 | runs | Orly 06/24 and 02/20 sessions on simulated devices, run here |
| 11 | runs | sessions at the two airports the owner named, run here |
| 12 | runs | replay of the recorded payloads and re-examination of every TRK-02 mismatch |
| 13 | runs | finding register and the owner's decision per proposed change |
| 14 | runs | applies only the findings the owner agreed in plan 13; if none, no source file changes |

Conditions that stay in force:
- Scratch roots live outside production and outside the repository; `SKYPANE_SIM_HARDWARE=1` is set only in the session process.
- If the sandbox or a provider fails during a session, the session continues on the owner's machine with the same scripts, still option A. Option B (VPS) and option C (production fleet) are not used.
- Each device's export is read from its own `history.db` with scripts/multi_site_export.py; the production export API is not used for simulated devices.

