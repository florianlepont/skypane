# Architecture Patterns: SkyPane v1.2 Fleet Platform

**Domain:** multi-user / multi-device / multi-hardware e-ink "BYOS" fleet on one small VPS
**Researched:** 2026-10-28
**Confidence:** HIGH on integration points and seams (read from the code in this repo); MEDIUM on Auth0 specifics and image-header layout (design proposals, not verified against external docs in this pass); LOW on firmware-side details for the second hardware (not chosen).

Scope: how the v1.2 features attach to the code that ships today. Everything marked "verified" was read in the file named. Nothing here has been run.

---

## 1. What the code does today (verified single-frame assumptions)

| Assumption baked in | Where (verified) | Consequence for v1.2 |
|---|---|---|
| One global OTA registry: `releases[]`, one `floor_version`, ONE `schedule`; no hardware key anywhere | `server/firmware_registry.py` (`_default_registry`, `schedule_release`, `compute_offer`) | A second hardware type would be offered the first type's image. Highest-severity seam (brick risk). |
| `acknowledged()`, `reconcile()`, `_newest_event_for_schedule()` scan events **across every device**; `_most_recent_device_entry()` picks "one frame" for the Update page | same file | One schedule's attempts/acks get mixed across devices. Schedules must become per-device. |
| Firmware accepts any image whose `esp_app_desc_t.project_name == "skypane"` | `firmware/main/ota_policy.c` (`FP_OTA_PROJECT_NAME`), `ota.c` (`fp_ota_image_check`) | Device-side check is hardware-blind: it is NOT a second line of defence against a wrong-hardware image today. |
| byos serves ONE file for all devices (`--image`, fixed `IMAGE_BYTES = 960000`) | `stub-server/byos_server.py` (`do_GET`, `main`) | Per-device image, per-profile size gate needed. |
| Device identity = token -> MAC via `_resolve_device_id`, which falls back to the literal `"default"` | `byos_server.py` | The `"default"` fallback must go; unknown token is a 401, never a shared bucket. |
| `/img/<sha>.bin` store is global, pruned to the newest `IMG_KEEP = 8` | `byos_server.py` (`_publish_image`, `_prune_images`) | With N devices, one device's publish evicts another's current image -> 404 on download. Store must be per device. |
| Config, state, panel, history are single files under one `state_dir` | `server/device_config.py`, `server/state_store.py`, `poll_cycle.write_panel_atomic`, `server/history_db.py` | All of these already take `state_dir` as a parameter. This is the key leverage point (see 3.2). |
| Battery telemetry reaches `history.db` by tailing Caddy's access log, which carries no device identity (Authorization is redacted) | `server/history_db.py` (`tail_caddy_battery_log`), `deploy/Caddyfile` | Cannot attribute rows to a device. byos must write `device_health` itself per authenticated poll. |
| `detect.py` hard-wired: `DEFAULT_RUNWAY_ID="3"`, `DEFAULT_GEOFENCE=adsb-test/runway3.json` (LFPO only, 3 runways), `poll_current_aircraft()` does fetch + select + corroborate in one call | `server/plane/detect.py`, `server/device_config.py` (`RUNWAYS`) | Needs fetch/select split to share one fetch among devices. |
| `run_once()` = one process cycle holding one lock on one `state_dir`; `snapshot=` seam already exists | `server/poll_cycle.py` | Reuse as the per-device pipeline; add an outer fleet loop. |
| `screens.current_screen_id(ctx)` returns a constant; registry was built "so pages render per screen type" | `companion/screens.py` | Natural hook for hardware-aware settings pages. |
| Companion auth = one shared password, stateless HMAC cookie keyed from password + per-process salt, in-memory revocation set; route table has only `auth_required: bool` | `companion/auth.py`, `companion/routes.py` | No identity, no roles, no ownership. `Route` needs an access level; sessions need a user id. |
| Backup allow-list names individual state files | `deploy/backup/skypane_backup.py` | New `fleet.db` and `devices/` must be added or backups silently omit the fleet. |

---

## 2. Recommended Architecture

### 2.1 Target shape (same processes, same units; no new daemons)

```
                  ADS-B aggregators (adsb.fi, adsb.lol)       adsbdb.com
                         ^  (global budget <= 1 req/s)            ^
                         |                                         |
 systemd timer (30 s)    |                                         |
 server/poll_loop.py --> server/fleet_cycle.py [NEW]  ------------+
   (oneshot, global      1. open fleet.db, list active devices
    fleet lock)          2. per device: decide_hold (no fetch if held)
                         3. group remaining devices into ZONES  [NEW zones.py]
                         4. per zone: ONE fetch via budget gate  [detect.fetch_zone]
                         5. per device: select -> enrich -> render(profile)
                            -> publish into <state>/devices/<id>/   [poll_cycle.run_once, modified]
                         6. reconcile OTA outcomes (per device)
          state/
           fleet.db                 [NEW] identity, ownership, hardware, detection placement, audit
           provider_calls.json      [NEW] global ADS-B spacing ledger (shared across zones/runs)
           firmware/registry.json   [MODIFIED schema 2: per-hardware releases + per-device schedules]
           firmware/device_report.json  [MODIFIED: keyed by device_id]
           (shared registries: manual_resolutions, name_overrides, illustrations, adsbdb cache)  [unchanged location]
           devices/<id>/            [NEW] one dir per device = a complete legacy "state_dir"
              device_config.json, poll_state.json, battery_state.json,
              panel.bin, img/, gallery/, history.db, calendar/colour rules
                         |
 skypane-byos.service    |  stub-server/byos_server.py [MODIFIED]
   token -> device row -> hardware profile -> device dir
   GET /device/v1/display: that device's image, sleep_s, offer(hardware, device)
   GET /img/<device_id>/<sha>.bin, GET /fw/<sha>.bin
                         |
 skypane-companion.service  companion/app.py [MODIFIED]
   Auth0 code+PKCE -> local user -> role -> Route.access + device ownership gate
   /d/<device_id>/... user views;  /admin/... fleet console;  /credits
```

Same six systemd units. No queue, no broker, no ORM. All new persistence is stdlib `sqlite3` (already used by `history_db.py`) plus the existing atomic-JSON pattern.

### 2.2 Key architectural decision: "a device directory is a legacy state_dir"

`device_config`, `state_store`, `poll_cycle`, `history_db`, `wake`, `render.build_canvas` all take `state_dir`. Rather than rewriting them to be device-keyed, give every device its own directory with the exact layout they already expect, and pass that directory where they take `state_dir`. Consequences:

- Phase 4 is mostly **plumbing a second directory argument**, not a rewrite: `CycleContext.state_dir` becomes `device_dir`, plus a `shared_dir` for the registries that are knowledge rather than preference.
- The migrated current frame can keep `state_path = "."` (its device dir **is** the state root) so migration moves zero files. Only a `devices.state_path` column differs between legacy and new devices. Both layouts work with the same code; shared and device dirs simply coincide for it.
- Tests that pass a `tmp_path` as `state_dir` keep working.

Split of what is per-device vs shared (decision, with reason):

| Data | Scope | Reason |
|---|---|---|
| `device_config.json` (theme, quiet hours, wake interval, LED, display_enabled), `poll_state.json`, `battery_state.json`, `panel.bin`, `img/`, `gallery/`, `history.db` | per device | Preference/state; already `state_dir`-parameterised. |
| calendar rules, colour rules | per device (owner-specific, the calendar is a private ICS) | Personal data must not render onto someone else's frame. |
| `manual_resolutions`, `name_overrides`, `illustrations`, adsbdb hit/miss cache | shared (admin-edited; airline identity is world knowledge) | Same airline looks the same everywhere; sharing multiplies cache hits and saves the third-party budget. |
| `firmware/` | shared, hardware-indexed | See 3.3. |

### 2.3 Component map: new vs modified vs unchanged

| Component | File(s) | Status | What changes |
|---|---|---|---|
| Fleet store | `server/fleet_db.py` | **NEW** | sqlite3, `PRAGMA user_version` migrations, `foreign_keys=ON`, WAL; same `connection_scope` per-thread pattern as `history_db.py`. Tables in section 3. Stdlib only, importable by byos. |
| Hardware registry | `server/hardware.py` | **NEW** | Code-defined `HARDWARE_TYPES` dict (like `device_config.RUNWAYS` and `screens.SCREEN_TYPES`): geometry, palette, image format id, battery profile, firmware target, `screen_id`, wake bounds. Stdlib only (byos imports it). Registers the current board plus `sim-*` types (tests/dev only, gated by env). |
| Fleet migration | `server/fleet_migrate.py` | **NEW** | Idempotent; see section 6. |
| Fleet cycle | `server/fleet_cycle.py` | **NEW** | Outer loop over devices/zones; calls modified `poll_cycle.run_once` per device. `poll_loop.py` calls this instead of `run_once` directly. |
| Zones + budget | `server/plane/zones.py`, `server/plane/budget.py` | **NEW** | Zone key derivation/grouping; global request ledger (`provider_calls.json`) under a short flock. |
| Airport geofences | `server/plane/airports.py` + data file (e.g. `server/data/airports_fr.json`) | **NEW** | Generate corridor geometry for any French airport/runway from published thresholds (offline import, no runtime network). `adsb-test/runway3.json` stays the LFPO source/fixture. |
| Image format | `server/imgfmt.py` (v1 header encode/decode, profile-parametrised pack) | **NEW** | `panel_format.py` becomes the legacy-raw encoder for the 1200x1600/Spectra-6 profile. |
| Auth0 / OIDC | `companion/oidc.py` | **NEW** | Authorization code + PKCE (S256), `state`, `nonce`; token exchange by back-channel `requests` POST to Auth0 over TLS; claim checks (`iss`, `aud`, `exp`, `nonce`); no signature verification per scope decision. |
| Accounts/ownership | `companion/accounts.py` | **NEW** | `current_user(handler)`, `require_role`, `require_device(handler, device_id)` (returns 404 for a device the user does not own - never reveals existence). |
| Admin console | `companion/pages/admin_*.py` | **NEW** | Fleet list, device detail, per-hardware release/schedule, users, audit. |
| Credits page | `companion/pages/credits_page.py` | **NEW** | Static content from `COMPLIANCE.md` data sources. No dependencies; can ship any time. |
| Firmware registry | `server/firmware_registry.py` | **MODIFIED** (schema 1->2) | `releases` and `floor_version` per hardware; `schedules` per device; `compute_offer(registry, device_entry, hardware_type, ...)`; publish requires hardware. Pure-function style and locking kept. |
| Firmware CLI / deploy import | `server/firmware_cli.py`, `scripts/fw_release_manifest.py`, CI tag flow | **MODIFIED** | `--hardware` (defaults to the legacy type so existing tags still import); manifest carries `hardware`. |
| byos | `stub-server/byos_server.py` | **MODIFIED** (largest) | token -> device -> profile -> `device_dir`; per-device image/config/battery reads; per-device `device_report`; writes `device_health` directly; format negotiation; `/img/<device_id>/<sha>.bin`. Registry loaded from `fleet.db` (read-only, fails closed like today's `load_registry`). Still stdlib + `server.*` only. |
| `devices_cli.py` | `stub-server/devices_cli.py` | **MODIFIED** | Writes `fleet.db` (mac, secret hash, hardware, optional owner); `devices.json` becomes migration input only. |
| Detection | `server/plane/detect.py` | **MODIFIED** | Split `poll_current_aircraft()` into `fetch_zone()` (network, per provider raw lists) and `select_*()` (pure). Add `select_position()` for around-a-point mode. Keep `corroborate on candidate-set intersection` semantics. Remove hard `DEFAULT_*` coupling from callers. |
| Poll cycle | `server/poll_cycle.py` | **MODIFIED** | `CycleContext` gains `device`, `hardware`, `device_dir`, `shared_dir`; `detect_flight` consumes a zone result instead of fetching; render takes profile; `_reconcile_firmware` per device. Step structure (`load_cycle_context` ... `cycle_result`) unchanged. |
| Render | `server/plane/render/*` (75 hard-coded WIDTH/HEIGHT refs), `server/panel_format.py`, `server/plane/dither.py` | **MODIFIED** (phase 7) | Profile-driven canvas/palette. See 7. |
| Device policy | `server/device_policy.py`, `server/wake.py` | **MODIFIED** (phase 7) | Battery curve/thresholds from `profile.battery`, not module constants. Must stay stdlib (byos imports it). |
| Device config | `server/device_config.py` | **MINOR** | `tracked_runway` leaves this document (placement moves to `fleet.db`); loader keeps tolerating the old key. Everything else untouched. |
| History | `server/history_db.py` | **MINOR** | Unchanged schema (one DB per device dir). `tail_caddy_battery_log` retired for fleet devices (byos writes directly); keep for the legacy window. |
| Companion app | `companion/app.py`, `routes.py`, `auth.py`, `screens.py`, `page_context.py`, `ui_nav.py`, `pages/*`, `settings/*` | **MODIFIED** | `Route` gains `access`; `PageContext` gains `user`, `device`; every `args.state_dir` use in page/post handlers becomes `device_dir`; screens hardware-aware; nav gets device switcher + admin area. `auth.py`'s stdlib-only "no sqlite3/server" header comment must be relaxed or accounts kept in a sibling module. |
| Backup | `deploy/backup/skypane_backup.py` | **MODIFIED** | Add `fleet.db` (use sqlite online backup API, not a file copy), `devices/`, `provider_calls.json` optional. |
| Deploy units | `deploy/*.service`, `Caddyfile` | **MODIFIED (small)** | Poll unit: drop `--geofence`, add nothing new; companion unit: Auth0 env vars; `TimeoutStartSec` revisited (7). Caddy: Auth0 callback route is just a companion path. |
| Firmware | `firmware/` | **MODIFIED (phases 2 and 8)** | Per-hardware project name (new hardware only), `X-Img-Fmt` capability header + header-aware image reader, build matrix by hardware. Existing frames keep working unmodified. |

---

## 3. Data Model

### 3.1 Entities (fleet.db)

```
users
  id INTEGER PK
  email TEXT UNIQUE NOT NULL            -- invite-only allow-list; lowercase
  auth0_sub TEXT UNIQUE NULL            -- linked on first successful login
  display_name TEXT, lang TEXT          -- 'en' | 'fr' (existing UI i18n)
  role TEXT NOT NULL CHECK(role IN ('admin','user'))
  status TEXT NOT NULL CHECK(status IN ('invited','active','disabled'))
  session_epoch INTEGER NOT NULL DEFAULT 0   -- bump to revoke all that user's sessions
  created_at, last_login_at

locations
  id INTEGER PK
  owner_user_id INTEGER NOT NULL REFERENCES users(id)
  label TEXT
  lat REAL, lon REAL                    -- stored at user precision; rounded (0.01 deg) before any third-party query

hardware types: NOT a table. Code registry server/hardware.py, keyed by string
  key, label, width, height, palette (rgb + wire code), image_format_id,
  battery {curve, low_mv, critical_mv, recover_mv}, firmware_target {idf_target,
  project_name, max_image_bytes}, screen_id, wake_min_s/wake_max_s, has_led

devices
  id TEXT PK                            -- opaque random, e.g. 'd_' + 8 hex; never the MAC
  mac TEXT UNIQUE NOT NULL
  secret_sha256 TEXT NOT NULL           -- enrolment secret hash (as devices.json today)
  hardware_type TEXT NOT NULL           -- validated against hardware.HARDWARE_TYPES; SERVER-ASSIGNED
  owner_user_id INTEGER NULL REFERENCES users(id)   -- NULL = provisioned but unclaimed
  location_id INTEGER NULL REFERENCES locations(id)
  name TEXT
  state_path TEXT NOT NULL              -- 'devices/<id>' ; legacy frame: '.'
  detection_mode TEXT NOT NULL CHECK(detection_mode IN ('runway','position'))
  airport_icao TEXT NULL, runway_id TEXT NULL        -- mode 'runway'
  radius_nm REAL NULL                                -- mode 'position' (center = location)
  status TEXT NOT NULL CHECK(status IN ('provisioned','claimed','retired'))
  fw_version TEXT NULL, last_seen_at TEXT NULL       -- cache written by byos
  created_at, claimed_at

pairing_claims          -- only if the on-panel-code flow is chosen (see 5.3)
  device_id, code_sha256, expires_at, attempts

audit_log
  id, ts, actor_user_id, action TEXT, target TEXT, detail TEXT   -- OTA schedule/cancel, role change, reassign, claim, disable

meta(key, value)        -- schema bookkeeping, migration markers
```

Rules worth stating up front:

1. **`hardware_type` is assigned by the server (admin at provision time), never taken from what the device reports.** Today the frame sends `hw_rev` in `/device/v1/setup` (`firmware/main/api_client.c`, `CONFIG_FP_HW_REV="proto-e1004"`). Record it, compare it, flag a mismatch to the admin - do not trust it for OTA selection.
2. Ownership lives only on `devices.owner_user_id`. A frame has exactly one owner; sharing is out of scope for v1.2.
3. Detection placement is in the DB (not in `device_config.json`) because the scheduler and the admin console query it relationally (grouping devices by zone, listing frames by airport). Preferences stay in the JSON document because `device_config.py`, its lock, its normalisers and byos's tolerant readers stay untouched. `load_cycle_context` overlays `device_cfg["tracked_runway"]` from the DB so downstream code is unchanged. Seam to handle: the companion's runway picker (`GROUP_RUNWAY`) must write the DB, not `save_device_config`.
4. IDs are opaque: the MAC stays a column, not a key or a path component (the MAC regex already exists in `byos_server.normalize_mac`).
5. `PRAGMA user_version` migrations are mandatory here, unlike `history_db`'s "CREATE IF NOT EXISTS is our whole migration story" (its own docstring says a new column was impossible). Identity data will need column changes.

### 3.2 Why SQLite for identity but files for state

- Identity/ownership/placement are relational and need transactions (claim a device exactly once; reassign owner + audit row atomically). The JSON-with-flock pattern would re-invent that badly.
- Per-device preference/state documents already have mature atomic-write + lock + tolerant-loader code and three processes depend on their exact on-disk format (`state_store` docstring). Leave them.
- byos opens `fleet.db` read-mostly. It writes `devices.fw_version/last_seen_at` - that is the one hot write; keep it throttled (write on change or at most once per N minutes) so 30 s poll bursts do not contend with companion writes. Use `busy_timeout`; a failed telemetry write must never turn a poll into a 500 (same rule as `save_battery_state`'s `except OSError`).

### 3.3 Firmware registry schema 2

```
{
 "schema": 2,
 "hardware": {
   "<hw_key>": { "floor_version": "fw-v1.0.0",
                 "releases": [ {version, sha256, size, released_at, published_at,
                                commit, notes, bench, installed_at[]} ] }
 },
 "schedules": { "<device_id>": {id, version, sha256, scheduled_at, state, attempts,
                                failed_at, last_result} },
 "last_outcome": { "<device_id>": {...} },
 "reconciled_seq": 0
}
```

- Offer lookup is `registry.hardware[device.hardware_type].releases` - a device can only ever be offered an image published for its own hardware. `schedule_release(state_dir, device_id, hardware, version, running_version)` rejects a version not in that hardware's list (`"unknown"`), so the admin UI cannot even express a cross-hardware schedule.
- `acknowledged()`, `_newest_event_for_schedule()`, `reconcile()` take a `device_id` and look only at that device's events. This also fixes the single-frame assumption in `_most_recent_device_entry()`.
- `device_report.json` stays byos-owned (single writer) but keys entries by `device_id` instead of MAC/`"default"`. The existing 50-event cap and the seq floor logic (`next_seq` floored by `reconciled_seq` and recorded seqs) carry over unchanged - they exist for restore-skew reasons that still apply.
- Loader stays tolerant: a schema-1 file reads as `hardware[LEGACY].releases = old releases`, `floor_version = old floor`, `schedules = {legacy_device_id: old schedule}`. The write path (`_load_registry_for_write`) migrates and rewrites under the existing lock. No release entry or `.bin` is ever deleted (existing invariant).
- Version uniqueness scope becomes `(hardware, version)`. `RELEASE_TAG_RE` stays valid for the legacy hardware; new hardware may use a prefixed tag (`fw-<hw>-v1.2.0`) or the manifest `hardware` field - decide in the OTA phase, but `publish_release` must require the field explicitly for any non-legacy hardware.

**Defence in depth on the device (phase 2 firmware task, new hardware only):** make `FP_OTA_PROJECT_NAME` and CMake `project()` derive from Kconfig, so a new board's signed app descriptor says e.g. `skypane-<hw>`. Then even a server bug that offers the wrong image is rejected by the frame before a byte is written (`ota.c` already re-derives project/version from the signed descriptor). **The existing frame must keep `"skypane"`** - its running firmware has that string compiled in; changing it would make it reject every future image.

---

## 4. Data Flow Changes

### 4.1 Device poll (byos), before -> after

Before: bearer -> any stored token valid -> serve `--image` -> offer from the one schedule.

After:
1. `Authorization: Bearer` -> constant-time compare against stored tokens (existing `hmac.compare_digest` loop) -> `mac` -> `devices` row. No match is 401. **Delete the `"default"` fallback in `_resolve_device_id`.** Retired/disabled devices get 401 as well.
2. `profile = hardware.get(device.hardware_type)`; `ddir = state_root/device.state_path`.
3. Reads (`read_wake_interval_s`, `read_quiet_hours`, `read_display_enabled`, `read_led_enabled`, `read_battery_critical`) are already functions of a directory: pass `ddir`.
4. Image: read `ddir/panel.bin`; size/format check from the profile (not a module constant); publish to `ddir/img/`; respond `image_url = {scheme}://{host}/img/{device_id}/{sha}.bin`.
5. Telemetry: write `battery_state.json` (as today) **and** `device_health` into `ddir/history.db` (replaces the Caddy-log tail for attribution).
6. OTA: `_record_device_report_and_offer` keeps its lock order (`registry_lock` then `_device_report_lock`) and its atomic offer-vs-cancel property; inputs gain `device_id` and `hardware_type`.
7. `GET /img/<device_id>/<sha>.bin`: both path components regex-validated (`[0-9a-f]{64}` for the hash; device id fixed-shape) before any path join; same unauthenticated, content-addressed rule as today. LOW confidence: confirm the firmware does not constrain `image_url` shape/length beyond the https/host rules (read `api_client.c` download path in phase 4).

### 4.2 Poll cycle (fleet loop), before -> after

Before: one `run_once()`, one geofence, 2 provider requests per cycle (adsb.fi and adsb.lol in parallel, each spaced >= 1.1 s from its own previous call; the spacing ledger is already persisted - `_load_provider_last_calls`).

After (`fleet_cycle.run`):
1. Take the global fleet flock; open `fleet.db`; list `status='claimed'` (and admin-flagged) devices.
2. For each device load its config; evaluate `decide_hold` first. **Held devices contribute no zone** - preserves today's "a hold does no ADS-B call" and is the main budget saver (quiet hours overnight).
3. Group remaining devices by **zone key**:
   - runway mode: `(airport_icao)` - one airport-centre query (radius 5 nm, as `runway3.json`) serves every runway at that airport and every device watching it;
   - position mode: `(round(lat,2), round(lon,2), radius_bucket)`. Rounding to 0.01 deg (~1 km) both lets neighbours share a query and avoids sending a home coordinate to a third party at full precision (compliance angle, see COMPLIANCE.md).
4. For each zone, in oldest-served-first order: `budget.acquire(provider)` (reads/updates `provider_calls.json` under a short flock; sleeps to honour `MIN_SECONDS_BETWEEN_CALLS = 1.1` per provider, which also keeps the **global** rate <= 1/s per provider because one process does all fetching) -> `detect.fetch_zone(zone, providers)` returns `{provider: [aircraft...]}`. Providers still run in parallel; zones are sequential.
5. For each device in the zone: `select_runway(...)` or `select_position(...)` from the shared result (pure; cross-source corroboration on candidate-set intersection exactly as today), then the existing steps `update_battery_low -> advance_display_queue -> render_and_publish -> record -> persist` with `device_dir`.
6. Failure isolation: wrap each device in try/except; one device raising must not abort the others. A zone whose fetch fails marks `source_fault` for its devices only (existing semantics).
7. `_reconcile_firmware` once per cycle for all devices (single locked read-modify-write).

Budget arithmetic (verify with a real measurement in phase 4): a zone costs 1 request per provider, providers in parallel, so wall time ~= `Z x 1.1 s`. At Z zones the cycle needs `Z x 1.1 s` of the 30 s timer. Roughly 20+ zones fit; a small fleet of a handful of zones is far inside. Cap zones per cycle (skip the not-due tail, never exceed the 90 s `TimeoutStartSec`), and serve zones with no active devices zero requests. Per-zone refresh does not have to equal 30 s once Z grows; the pacing queue (`advance_is_due`, `pop_fresh_pending`) already tolerates gaps.

Manual "poll now" (companion `POST /poll-now`): per-device lock (`poll_cycle_lock(device_dir, 0)`), consume a cached zone result if younger than ~30 s, else acquire budget through the same ledger. It must never fetch outside `budget.acquire` or the global rate guarantee is void.

### 4.3 Companion request

`Handler._dispatch` today: Origin check -> route match -> `if route.auth_required and not require_session()` -> handler. After:

1. Origin/Sec-Fetch-Site check (unchanged, first).
2. Route match; `Route.access in {"public","user","admin"}` replaces the bool (keep `auth_required` derived for the baseline test during transition).
3. Resolve session -> `users` row (check `status=active` and `session_epoch` match on every request: this replaces the in-memory revocation set for user sessions, and survives restarts).
4. Role check from the route table, not inside handlers.
5. For `/d/<device_id>/...`: `require_device()` loads the device, requires `owner == user.id or user.role == 'admin'`, else **404**. Handlers receive `ctx.device` and use `device_dir` wherever they currently use `self.args.state_dir`.
6. POST handlers that mutate fleet-level things (OTA schedule, role change, reassign) are `access="admin"` and write an `audit_log` row in the same transaction.

URL design recommendation: path-prefixed `/d/<device_id>/...` rather than an "active device" cookie. A cookie makes two open tabs act on different devices than they display (a wrong-device write is the worst failure here). Keep the old unprefixed routes as redirects to the user's default device so bookmarks and the existing Playwright tests migrate incrementally. Cost: roughly 30 routes plus nav and tests; the `Exact`/`PrefixSuffix` matchers in `routes.py` need a captured-segment variant.

### 4.4 Image format and backward compatibility

Today: raw 960,000 bytes, 4 bpp, no header; firmware refuses anything that is not exactly `FP_IMAGE_BYTES` (`firmware/main/api_client.c`); `image_hash` is sha256 of the served bytes.

Proposal (MEDIUM confidence, design not external fact):
- v1 container: fixed header (magic, format version, width, height, palette/profile id, bits-per-pixel, payload length, flags) + payload. Little-endian, fixed size, unknown-version = reject.
- **Negotiation, not flag day.** New firmware sends `X-Img-Fmt: 1` on the poll. The server serves the headered format only when that header (or a recorded capability at/after a known `fw_version`) is present; otherwise the legacy raw bytes. The existing frame keeps receiving raw 960,000-byte images until it has been OTA-updated to a header-aware build. Server-side the *canonical* artifact is the pixel buffer; the container is a per-response encoding (`imgfmt.encode(profile, pixels, fmt)`).
- Cut-over cost: the device compares `image_hash` against NVS; switching a frame's format changes the hash of identical content -> one extra full refresh (about 31.5 s, battery cost). Accept once per device; do not re-encode silently for devices already displaying.
- The simulated hardware type should initially share geometry 1200x1600 with a different palette/battery profile; otherwise the 75 hard-coded layout references force the render rewrite into phase 3-5. Resolution-changing render is phase 7 (see 7).

---

## 5. Security-sensitive seams (call out in every phase plan)

| # | Seam | Today | Required | Phase |
|---|---|---|---|---|
| S1 | OTA selection by hardware | One list, any device | Releases indexed by hardware; hardware assigned server-side; schedule per device; device-side project-name check for new hardware | 2 |
| S2 | Token -> device resolution | Falls back to `"default"` | 401 on no match; never a shared identity | 1/4 |
| S3 | Per-device files | One shared dir | Device id regex + fixed prefix in every path join (`/img/<id>/<sha>`); never join an unvalidated string (existing `firmware_image_path` discipline) | 4 |
| S4 | Route authorisation | `auth_required: bool`, one password | Access level in the route table + ownership check in one function; 404 on foreign devices; admin routes default-deny (a new route without an explicit `access` fails a test) | 6 |
| S5 | Auth0 login | n/a | `state` + `nonce` + PKCE S256 verifier, single-use and bound to a short-lived cookie; exact registered redirect URI; check `iss`/`aud`/`exp`/`nonce`; require `email_verified` before linking to an invited email; link `sub` once and thereafter match **only on `sub`** (an email change at the IdP must not take over an account); no open signup (unknown email = rejected, not auto-created) | 6 |
| S6 | Session signing key | Derived from the shared password + process salt (restart logs everyone out) | Dedicated persistent secret (`SKYPANE_SESSION_SECRET`); shared-password fallback maps to a synthetic admin with a hard removal date and an off switch; keep `post_origin_ok` and the login throttle | 6 |
| S7 | Claim / pairing | Admin-registered MAC+secret only | Claim requires proof of physical possession (enrolment-secret label/QR, or an on-panel one-time code), attempts rate-limited per device and per user, code single-use and expiring; a device can be claimed once; claim writes `audit_log` | 6 |
| S8 | Privileged mutations | Anyone with the password | Role change, reassign, retire, OTA schedule are admin-only and audited; last-admin guard (cannot demote/disable the only admin) | 6 |
| S9 | Location privacy | n/a | Coordinates visible to owner + admin only; round before any third-party request | 5 |
| S10 | Backup of identity | Allow-list of files | Include `fleet.db` via sqlite backup API; include `devices/`; restore test | 1 |
| S11 | Unauthenticated `/img` and `/fw` | Content-addressed, unauthenticated | Keep (images are public-ish flight info, firmware is signed), but device id in `/img` path must not be enumerable meaningfully: opaque random id | 4 |

---

## 6. Migration of the current frame

Principle: **no reflash, no re-enrolment, no NVS change, no file moves.** (PROJECT.md key decision: the NVS partition survives app flashes and a stale token is never auto-cleared; a migration that changes the token or secret strands the frame.)

`fleet_migrate.py` (idempotent, run from the deploy/activate step, guarded by `meta.migrated_v1`):

1. Create `fleet.db` at `user_version` 1; seed the admin user from `SKYPANE_BOOTSTRAP_ADMIN_EMAIL` (`status='invited'`, `auth0_sub` NULL; linked at first Auth0 login via verified email).
2. Import `devices.json` -> one `devices` row per MAC: same `secret_sha256`, `hardware_type = <legacy key>` (the current XIAO EE02 13.3" Spectra 6 profile), `owner = admin`, `status='claimed'`, `state_path = '.'`, `detection_mode='runway'`, `airport_icao='LFPO'`, `runway_id` from the current `device_config.json["tracked_runway"]`.
3. Keep `byos_state.json` (tokens by MAC) as is; byos maps token -> mac -> device row. The frame's token stays valid.
4. Rewrite `firmware/registry.json` schema 1 -> 2 and `device_report.json` keys MAC/`"default"` -> `device_id`, under the existing locks, keeping the original as `*.pre-fleet`. Carry the existing schedule (if any) into `schedules[device_id]`.
5. Do not touch `panel.bin`, `poll_state.json`, `history.db`, `device_config.json`: they are the legacy device dir because `state_path = '.'`.
6. Verification gates: row counts, the migrated frame's next real poll returns the same `image_hash` and `sleep_s` as before, `X-Fw-Version` still recorded, Update page still shows the running version.

Rollback story: because no file moved and schema-1 loaders tolerate the old registry shape, the previous release still runs against the same state dir (it ignores `fleet.db`, and reads the `*.pre-fleet` or tolerated registry). The one forward-only step is the registry rewrite; keep the `.pre-fleet` copy until the next phase is verified. Moving the legacy frame into `devices/<id>/` is an optional, later, separate step (not worth the risk early).

Deploy order matters: server first (it must still serve legacy frames: raw image format, no `X-Img-Fmt`, `"skypane"` project name), firmware later. Never ship a server that *requires* a new header.

---

## 7. Per-hardware render, battery, health (phase 7 specifics)

- Render: 75 references to `WIDTH`/`HEIGHT` across `server/plane/render/*` (verified by grep count). Recommend **render the canonical 1200x1600 canvas, then adapt** (scale/crop + palette quantise via `dither.py` + pack via `imgfmt`) as the default for any new profile with similar aspect ratio; native layouts per hardware only if the chosen second board's aspect or size makes the adapted text unacceptable. Decide after the second hardware is picked (phase 8 may feed back). The sim type in phases 1-7 should therefore keep a compatible aspect.
- Battery/health: `device_policy.battery_fraction/battery_percent`, `apply_battery_hysteresis`, `apply_battery_critical_hysteresis`, `BATTERY_CRITICAL_*` are module constants that byos, poll_cycle, wake and the companion all import. Parameterise them with a `battery` profile object; keep the legacy numbers as the legacy profile so existing tests pass unchanged. The `battery_chart`/health pages read per-device `history.db`.
- Per-device `wake.py` effective interval already derives from `device_cfg`; add hardware `wake_min_s/wake_max_s` bounds.
- Credits page: independent, static; schedule wherever convenient (cheap early win for the data-source compliance obligations in `COMPLIANCE.md`).

---

## 8. Build order implied by dependencies

Dependency graph (A -> B means B needs A):

```
(1 data model: fleet.db + hardware registry + migration)
   |-> (2 OTA per hardware)            needs hardware key
   |-> (3 image format)                needs profile (dims/palette)
   |-> (4 per-device config/image/state + budget)   needs devices, profile, 3
   |       |-> (5 detection modes)     needs zones/budget from 4
   |       |-> (6 auth + ownership + pairing + admin)   needs devices (1), device dirs (4); admin OTA UI needs 2
   |               |-> (7 render/battery/health + credits) needs 3, 4; credits independent
   |                       |-> (8 second hardware)   needs 2, 3, 7; only phase needing a purchase
(9 comment-history)   independent; see ordering note
```

Recommended chunks (owner's phases kept; refinements marked):

| Phase | Deliver | Key modules | Why here / notes |
|---|---|---|---|
| **1. Data model + migration** | `server/fleet_db.py`, `server/hardware.py` (legacy + `sim-*`), `fleet_migrate.py`, `devices_cli` writes DB, backup allow-list, byos maps token -> device row (still one image) and drops `"default"` fallback | new + small byos change | Everything else keys on this. Keep behaviour identical for the one frame; success = frame polls unchanged. |
| **2. OTA per hardware** | registry schema 2, per-device schedules, `compute_offer` with hardware, CLI `--hardware`, manifest/CI, Update page reads the device's own hardware, device-side project-name derivation (new hardware only) | `firmware_registry.py`, `firmware_cli.py`, byos offer path, companion Update page | Security-critical; do before any second hardware type can exist (even simulated). Server before firmware. |
| **3. Common image format** | `imgfmt.py`, header spec doc, byos negotiation via `X-Img-Fmt`, `panel_format` becomes the legacy encoder, firmware reader for the new build | `imgfmt.py`, byos, firmware `api_client.c` | Can run in parallel with 2 (different files). Must precede 4 so per-device images are served through the format layer once. |
| **4. Per-device config/image/state + poll budget** | device dirs, `CycleContext(device_dir, shared_dir)`, `fleet_cycle`, `zones.py`, `budget.py`, `fetch_zone`/`select_*` split, per-device `/img`, byos writes `device_health`, per-device poll-now | `poll_cycle.py`, `poll_loop.py`, `detect.py`, byos, companion `state_dir` -> `device_dir` | Largest phase; suggest splitting 4a (device dirs + byos per-device + health write, still one zone) and 4b (fleet cycle, zones, budget ledger). Carry `snapshot=` seam for tests; add a fake-clock budget test (hard guarantee <= 1/s). |
| **5. Detection modes** | `airports.py` + data, runway-mode for any French airport/runway, position mode, rendered tag/label generalised from "ORY · RWY 3", placement UI (admin-only until 6) | `detect.py`, `airports.py`, `device_config.RUNWAYS` replaced, render tag text, `runway_config` reuse | Needs 4's zones. Largest unknown: authoritative runway threshold data source and licence (LOW confidence: not researched here; OurAirports is what `runway3.json` already cites). |
| **6. Auth0 + accounts + ownership + pairing + admin console** | Recommend 3 sub-phases: **6a** `oidc.py`, users table use, `Route.access`, session secret, ownership gate, `/d/<id>` routing, shared-password-as-admin fallback; **6b** claim/pairing + user device list; **6c** admin console (fleet, users, per-hardware release/schedule UI from 2, audit) | `companion/*` | Security core. Land 6a's gate and its default-deny test *before* any multi-user page exists. Keep the fallback until 6c is validated, then remove with a dated commit. |
| **7. Per-hardware render/battery/health + credits** | profile-driven render adapter, battery profile, health per device, credits page | `render/*`, `device_policy.py`, `wake.py`, health pages | Credits can be pulled forward at no risk. |
| **8. Second hardware** | choose, buy, firmware target + build matrix (`firmware/build.sh` per hardware), hardware profile, release flow, on-glass validation | `hardware.py`, `firmware/`, CI | Only phase needing money; everything before ran against `sim-*`, which is the point. Expect firmware porting effort to dominate (LOW confidence until the board is chosen). |
| **9. Comment-history debt** | clear violations | `scripts/check_comment_history.py` (`check`, `same-code` proof tool) | **Ordering recommendation: run `check` now.** If it fails on files v1.2 will edit (`firmware_registry.py`, `byos_server.py`, `poll_cycle.py`, `companion/*`), do the cleanup for those files first (or as a phase 0): every later phase edits them and CI enforces the guard. `same-code` already proves comment-only edits are behaviour-neutral. If already green, keep it last. |

Order rationale in one line: identity -> OTA safety -> wire format -> per-device runtime -> new inputs -> user-facing multi-tenancy -> polish -> hardware purchase. The security-critical OTA index (2) is earlier than the owner might expect for a single-user system, deliberately.

---

## 9. Patterns to follow

1. **Directory-as-context** (2.2): pass `device_dir`/`shared_dir`; do not thread `device_id` through leaf modules.
2. **Pure core, locked I/O shell** (already how `firmware_registry` is written): keep new registry/zone/budget logic pure with timestamps as parameters; one locked wrapper.
3. **Tolerant readers, strict writers**: readers degrade to defaults (byos must never 500 a poll); `_load_registry_for_write`-style quarantine for writers. Apply the same to `fleet.db` reads in byos, but **fail closed for identity** (an unreadable `fleet.db` enrols and authenticates nobody, mirroring `load_registry()` in byos today).
4. **Validate-then-join** for every path derived from a request (hash, device id).
5. **Route table as the single gate** (already `routes.py`'s stated design); extend, do not add per-handler checks.
6. **Capability negotiation by request header** for format evolution so servers can deploy ahead of firmware.

## 10. Anti-patterns to avoid

- **Trusting device-reported `hw_rev`/`X-Fw-Version` for authorisation decisions.** Telemetry only.
- **A "current device" cookie** for the companion (wrong-device writes).
- **One `device_config.json` with per-device sub-maps.** Re-creates a single-writer bottleneck and breaks byos's tolerant readers.
- **Fetching ADS-B per device.** N devices at one airport would multiply requests and breach the 1 req/s rule; always go through the zone gate.
- **Growing `history.db` schema with a `device_id` column.** One DB per device dir avoids altering a no-migration schema and keeps retention/reset per device.
- **Auto-creating users on first Auth0 login.** Invite-only is cheap and prevents strangers from consuming budget or claiming devices.
- **Moving the legacy frame's files during migration.** Forward-only and unnecessary.
- **Changing the existing frame's OTA project name.** Would brick future updates for it.

## 11. Scalability

| Concern | 1-5 devices (target) | ~50 devices | Notes |
|---|---|---|---|
| ADS-B requests | 1-3 zones x 2 providers per 30 s | Zone count dominates; hit the 1.1 s spacing wall near ~20 zones per 30 s | Mitigate by lengthening per-zone cadence; held devices excluded |
| Poll process time | seconds | Render cost per device (Pillow, ~ seconds) becomes the limit; cycle must stay under 90 s `TimeoutStartSec` | Render only when the display slot changed (existing `panel_changed` logic) |
| SQLite | trivial | still fine (WAL) | Single VPS, single writer at a time |
| byos | ThreadingHTTPServer, 15 s request timeout | devices wake minutes apart; fine | `devices.last_seen_at` writes throttled |
| Third-party terms | within hobby use | would need re-checking adsb.fi/adsb.lol/adsbdb terms | Out of scope for family fleet |

## 12. Open questions / research flags per phase

- Phase 3: exact header layout and where the firmware's image reader ends; confirm `image_url` constraints in `api_client.c` (LOW until read).
- Phase 5: authoritative runway data source and licensing for French airports; behaviour of corridor/track gates at airports whose runways are close to parallel; position-mode semantics for `departing/arriving` inference (`runway_config.infer_*` uses vertical rate, reusable).
- Phase 6: Auth0 tenant settings (callback URLs, signup disabled, `email_verified` behaviour) and whether skipping signature verification is acceptable given back-channel TLS exchange (OIDC Core allows TLS server validation to stand in for signature check on the token endpoint response; not re-verified in this pass, MEDIUM).
- Phase 8: needs its own research once a board is shortlisted (ESP-IDF target support, e-paper driver, battery gauge).

## Sources

- Read directly in this repo: `server/firmware_registry.py`, `server/plane/detect.py`, `stub-server/byos_server.py`, `companion/screens.py`, `companion/routes.py`, `companion/auth.py`, `companion/app.py` (dispatch), `server/poll_cycle.py` (`run_once`, `CycleContext`, `load_cycle_context`), `server/poll_loop.py`, `server/device_config.py`, `server/state_store.py`, `server/history_db.py` (schema, Caddy tail), `server/panel_format.py`, `firmware/main/ota.c`, `ota_policy.c`, `api_client.c`, `deploy/skypane-byos.service`, `deploy/skypane-poll.service`, `deploy/backup/skypane_backup.py`, `adsb-test/runway3.json`, `ARCHITECTURE.md`, `.planning/PROJECT.md`, `scripts/check_comment_history.py`.
- Sibling research in the same directory (`FEATURES.md`, `PITFALLS.md`) was not relied on.
- No external sources were consulted for this document; Auth0/OIDC points are from training knowledge and marked MEDIUM.
