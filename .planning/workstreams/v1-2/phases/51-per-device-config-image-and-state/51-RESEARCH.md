# Phase 51: Per-Device Config, Image and State - Research

**Researched:** 2026-10-30
**Domain:** Threading a per-device state directory through the BYOS device endpoint, the poll cycle and the companion (stdlib Python, no new dependency)
**Confidence:** HIGH (every finding below was read from the repository in this session; no external library is involved)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Owner-fixed (not to be reopened)**
- **D-01 (owner):** The live frame keeps its MAC, secret, token, file paths (`state_path = "."`), current raw image and wake interval byte for byte. `stub-server/test_phase47_freeze.py` stays green.
- **D-02 (owner):** Expand-only: the previous release still runs on the state this phase produces.
- **D-03 (owner):** A frame that does not announce the container still receives the raw image (Phase 50 negotiation applies per device).
- **D-04 (owner):** No production deploy.

**Directory layout (owner choice, 2026-10-30)**
- **D-05:** New devices live in `<state_dir>/devices/<id>/`, `<id>` being the numeric `devices.id` of fleet.db. The path is stored in `devices.state_path`. No MAC in paths.
- **D-06:** The live frame stays at the root of the state dir (`state_path = "."`); it is never moved. Each device directory holds the same file set a state dir holds today (`device_config.json`, `poll_state.json`, `panel.bin`, history DB, `img/`, battery state).
- **D-07:** The BYOS resolves the presented token or MAC to its device and reads/writes only that device's directory. `--image` remains the live frame's image only; no other device ever falls back to it, and the `"default"` device fallback is gone (an unresolved token is a 401).

**Companion navigation (owner choice)**
- **D-08:** A device selector at the top of the companion. Existing pages (home, health, history, settings) show the selected device; the live frame is selected by default and its current URLs keep working unchanged.
- **D-09:** Per-device routes use a `/devices/<id>/...` prefix and are declared in the route table so Phase 54 can annotate each with a minimum role and ownership check without restructuring. All device-scoped handlers take an explicit device argument; none reads a global state dir.
- **D-10:** Bilingual UI (strings in `companion/i18n_fr/`), design per `sketch-findings-skypane`.

**Single-device poll (owner choice)**
- **D-11:** "Poll now" for a device runs the existing cycle (same Orly runway-3 detection) against that device's directory only: image, poll state, history and health are written there and nowhere else. Fleet-wide polling and zone sharing are Phase 52.
- **D-12:** The poll lock is per device, so polling one device never blocks or alters another.

**Quiet hours and timezone (owner choice)**
- **D-13:** The timezone is a validated IANA field in each device's own `device_config.json`, next to quiet hours. Default `Europe/Paris`, so the live frame's behaviour does not change. The fixed `QUIET_HOURS_TZ` constant becomes the default, not the only value.
- **D-14:** Setting quiet hours or timezone for one device writes that device's config only; a test proves other devices' files are byte-identical.

### Claude's Discretion
Module and function names, the device-resolution helper, test layout, plan split and waves, how simulated devices get their initial image/config, and the migration of nothing for the live frame (none is needed).

### Deferred Ideas (OUT OF SCOPE)
- Fleet poll loop, shared zones, request budget - Phase 52.
- Per-device location/detection mode - Phase 53.
- Role and ownership enforcement on device routes - Phase 54.
- Device creation UI and pairing - Phase 55.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| FLT-01 | Each device has its own config, image, poll state, history and health; the BYOS serves each frame its own image from its own directory. | Sections "Single-device assumptions inventory", "Pattern 1/2/3", "Image URL for non-live devices", "Per-device health and history". |
| FLT-02 | The owner or a user can trigger a poll for one device and set its quiet hours and timezone without affecting others. | Sections "Pattern 4 (route table)", "Per-device poll lock", "Per-device timezone", "Validation Architecture" (byte-identical-other-devices test). |
</phase_requirements>

## Summary

**Everything keys off one `state_dir` string.** `device_config`, `state_store` (poll_state, battery_state), `history_db`, `poll_cycle` (panel.bin, gallery, poll.lock), `manual_resolutions`, `name_overrides`, `colour_rules`, `calendar_rules` and the BYOS `img/` store all take `state_dir` as an argument [VERIFIED: grep of server/*.py]. So a per-device directory reuses all of that code by passing `<root>/devices/<id>` instead of `<root>`. The poll lock is already a file lock inside the state dir (`poll.lock`), so it is per device for free; only the companion's in-process `_POLL_LOCK` is global and must become a keyed registry. The new work is concentrated in three seams: (1) the BYOS display handler, which today authenticates with `bearer_ok()` (any known token) and then serves the single `--image`, so it must resolve token -> MAC -> fleet.db row -> state dir; (2) the companion, where `PageContext.state_dir` is already an eager field built in one place (`page_context.build_page_context`) but ~30 handler sites in `app.py`/`post_actions.py` read `self.args.state_dir`, and ~350 route/href/action literals must learn a `/devices/<id>` prefix; (3) `device_policy`, where `QUIET_HOURS_TZ` is a module constant used by three arithmetic paths.

**Two facts in CONTEXT.md need correcting before planning.** (a) `devices.id` is **not numeric**: it is `TEXT PRIMARY KEY` generated as `"d_" + 8 hex` (`fleet_db.add_device`), so `<id>` is e.g. `d_1a2b3c4d`. That is already path-safe; validate it with `\Ad_[0-9a-f]{8}\Z`. [VERIFIED: server/fleet_db.py lines 103, 386-420] (b) The `"default"` device fallback is **already gone from `_resolve_device_id`** (Phase 48 made it return `None`); what remains of the "shared default" behaviour is that the display handler serves `--image` to *any* valid token and reads one global state dir. Removing that is the real work for success criterion 3. The two tests that mention `"default"` (`test_fleet_auth.py::test_default_bucket_untouched_by_valid_poll`, `test_ota_offer.py::test_legacy_default_bucket_survives_valid_poll`) assert that a legacy `"default"` bucket in `firmware/device_report.json` is left untouched; they stay valid and must not be deleted. [VERIFIED: stub-server/byos_server.py:834-852, test files]

**Primary recommendation:** Add one small stdlib leaf module `server/device_dirs.py` (path validation, resolution, provisioning), resolve the device once per BYOS request and once per companion request, then pass the resulting device directory everywhere `state_dir` is passed today. The live frame resolves to the root and `--image`, so its code path is the existing one. Extract the BYOS display branch out of `Handler.do_GET` (already 64 lines against an 80-line gate) and put all companion device-scoping in a new module because `companion/app.py` is 1328 lines against a 1500-line ceiling.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Token -> device -> state dir resolution for frame requests | API / Backend (BYOS `stub-server/byos_server.py`) | Database (fleet.db read-only) | Auth boundary; must fail closed (401) and never fall back to `--image`. |
| Per-device image publish/serve (`img/`, `/img/...`) | API / Backend (BYOS) | Storage (device dir) | Content-addressed files live under the owning device's dir only. |
| Per-device poll (image, poll state, history) | API / Backend (`server/poll_cycle.py` invoked by companion `/poll-now`) | Storage | Same cycle, different `state_dir`; lock is `poll.lock` in that dir. |
| Device selector, `/devices/<id>/...` routing, per-device pages | Frontend Server (companion, server-rendered) | Database (fleet.db read-only list) | Companion is stdlib SSR; route table is the single declaration point Phase 54 annotates. |
| Quiet-hours timezone arithmetic | `server/device_policy.py` (shared pure module) | BYOS, poll cycle, companion consumers | One shared implementation; consumers pass the device's tz. |
| Device directory provisioning (create dir, seed config/image) | CLI (`stub-server/fleet_cli.py`) calling `server/device_dirs.py` | - | Device creation UI is Phase 55; Phase 51 needs a scriptable path for simulated devices and tests. |
| Backup of per-device dirs | Deploy tooling (`deploy/backup/skypane_backup.py`) | - | Allow-list based; `devices/` is currently reported as drift and NOT archived. |

## Single-device assumptions inventory

[VERIFIED: grep and reads in this session]

### BYOS (`stub-server/byos_server.py`, 1430 lines)

| Site | Assumption | Phase 51 change |
|------|-----------|-----------------|
| `Handler.bearer_ok()` (1169) | Any token in `effective_tokens()` passes; does not say *whose*. Compares every candidate (no early exit; `test_fleet_auth.py::test_bearer_compare_visits_every_candidate` pins this). | Keep `bearer_ok()` as is for `/device/v1/log`. Add `_authenticate_device()` that also visits every candidate (no early exit) and returns the matching MAC. Do not reuse `_resolve_device_id` as is: it returns on first match. |
| `do_GET` display branch (1231-1308) | `open(self.args.image)`; `save_battery_state(self.args.state_dir, ...)`; `_publish_image(self.args.state_dir, ...)`; `read_wake_interval_s/read_quiet_hours/read_led_enabled/read_display_enabled/read_battery_critical(self.args.state_dir)`. | Resolve a `DeviceContext(root, state_dir, image_path, mac, device_id, width, height)` once; pass `ctx.state_dir` to every reader/writer and `ctx.image_path` for the image. For the live frame `state_dir == root` and `image_path == args.image`. |
| `_IMG_PATH_RE` route (1309-1322) | `/img/<sha>.bin` reads `<root>/img/`. Unauthenticated, content-addressed. | Live frame keeps `/img/<sha>.bin` (frozen: `image_url_path_template`). See "Image URL for non-live devices". |
| `_record_device_report_and_offer` (1003) | `device_id` = MAC; OTA registry and `firmware/device_report.json` live at root and are shared per hardware type; `read_battery_low_active(state_dir)` reads root `poll_state.json`. | Registry and device report stay at root (shared, keyed by MAC). Only `battery_low_active` must be read from the device's own dir. |
| `_fleet_view`, `effective_tokens`, `issue_token`, `_enrol` | fleet.db and `byos_state.json` tokens at root. | Unchanged: identity stays at root; enrolment unchanged. |
| `main()` | `--image` required, `Handler.state = load_state(root)`. | Unchanged. `--image` stays the live frame's image only (D-07). |

`_resolve_device_id` is imported by tests (`test_ota_offer.py:505-533, 899-904`); keep its name and contract (`{"tokens": ...}` state shape, `None` for no match).

### Server (`server/`)

| Module | Per-dir already? | Note |
|--------|------------------|------|
| `device_config.py` | Yes (`load_device_config(state_dir)`, `save_device_config(state_dir, ...)`, lock `device_config.lock` in dir) | Add `timezone` key. `load_device_config` returns exactly ten keys; `server/test_retired_notifications.py:65` asserts ten (`_REMAINING_CONFIG_KEYS`) and must be updated to eleven. |
| `state_store.py` | Yes | No change. |
| `history_db.py` | Yes (`<state_dir>/history.db`, `connection_scope(state_dir)`) | No change. `history_db.py:502` hardcodes `Europe/Paris` for day bucketing: leave (see Open Questions). |
| `poll_cycle.py` | Yes (`run_once(state_dir=..., lock_timeout_s=0)`) | Two caveats: `_reconcile_firmware(ctx.state_dir)` and `caddy_log` (below). |
| `poll_cycle.poll_cycle_lock` | `<state_dir>/poll.lock` (flock) | Already per device and cross-process. |
| `firmware_registry.py` | Takes `state_dir` and reads `<state_dir>/firmware/` | Must keep receiving the ROOT, never a device dir. |
| `fleet_db.py` | Root-level DB; `devices.state_path TEXT NOT NULL DEFAULT '.'` | No schema change needed (no migration). `list_devices` already returns `state_path`. |

**Poll-cycle caveats for non-live devices**
1. `run_once(..., caddy_log=...)`: the Caddy access log has no per-device identity (it records `X-Battery-Mv` per display URI). Passing it for a non-live device would ingest the live frame's battery readings into that device's `history.db`. The companion `/poll-now` already calls `run_once` without `caddy_log` (app.py:1063), and the systemd poll polls the root only, so the rule is: **never pass `caddy_log` for a device dir** (add a test). [VERIFIED: poll_cycle.py:413-500, app.py:1060-1066, server/poll_loop.py:66-78]
2. `_reconcile_firmware(ctx.state_dir, ...)` (poll_cycle.py:249, 1416) calls `firmware_registry.apply_reconcile_all(state_dir)`, which reads `<state_dir>/firmware/`. In a device dir that directory does not exist, so it is a harmless no-op, but it may create `firmware/` lock files via `registry_lock` -> `_ensure_firmware_dir`. Verify with a test that a device-dir poll leaves no `firmware/` directory behind; if it does, skip reconcile when `state_dir` is not the root (add a `reconcile_root` parameter or guard on `devices/` membership).
3. `poll_cycle.write_panel_atomic` always renders 1200x1600 (`panel_format`). A simulated `sim-landscape-800x480` device would receive a 960,000-byte panel that disagrees with its 192,000-byte profile. Per-hardware rendering is Phase 56, so Phase 51 must either restrict `/poll-now` to devices whose profile geometry equals the render geometry (recommended; flash "polling not available for this hardware yet") or leave landscape devices on a seeded placeholder only. See Open Questions.
4. The provider rate limiter state is in each dir's `history.db` meta (`_load_provider_last_calls`), so provider spacing is no longer shared between the live poll and a device poll-now. FLT-03 (Phase 52) owns the global budget; document as an accepted gap and keep poll-now manual (cooldown is per dir already: `flash.poll_cooldown_remaining(state_dir)` reads `history.db` meta).

### Companion

| Site | Assumption | Phase 51 change |
|------|-----------|-----------------|
| `page_context.build_page_context` (line ~194): `state_dir = handler.args.state_dir` | The single seam for all page modules (257 `state_dir` references go through `ctx.state_dir`). | Read the resolved per-request device dir instead. Every page module keeps working unchanged. |
| `app.py` ~30 sites of `self.args.state_dir` (lines 660, 673, 729, 755, 761, 785, 788, 812, 931, 1000, 1049, 1063, 1119, 1190-1207, 1248, 1262) and `post_actions.py` (227, 240, 302, 370, 403, 422) | Handler-level global. | Replace with an explicit `device` argument (D-09). Firmware-registry sites (1190-1207, 1248) keep the ROOT: Update is not device-scoped. |
| `post_actions._POLL_LOCK` (re-exported as `app._POLL_LOCK`) | One `threading.Lock` for all devices. Used by `/poll-now` and by calendar-URL sync in `_handle_settings_post`. | Replace with `poll_lock_for(state_dir)` backed by a dict guarded by a small lock, keyed by `os.path.realpath(state_dir)`. `companion/test_poll_now_lock.py` pins the current behaviour; keep the non-blocking acquire. |
| `health_signals._read_fleet_status(state_dir)` | fleet.db status file at root. | Must read the ROOT even when `ctx.state_dir` is a device dir; pass the root explicitly (fleet status is global, not per device). |
| `LOGIN_THROTTLE`, theme/lang cookies | Process-global. | Unchanged (not device state). |

## Standard Stack

No new external packages. Everything is stdlib plus the already-pinned Pillow/requests. `[VERIFIED: server/requirements.txt, CLAUDE.md "stdlib + Pillow + requests only"]`. Therefore no Package Legitimacy Audit applies (no package is installed in this phase).

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python stdlib (`os`, `re`, `json`, `sqlite3`, `threading`, `zoneinfo`, `fcntl` via `server/atomic_io.py`) | CPython 3.14 prod (local venv 3.13) | Path validation, per-device locks, tz validation | Project constraint; matches existing modules. |
| `server/atomic_io.py` | in repo | `atomic_write`, `exclusive_lock` for every new file write | Existing contract: mode, fsync, same-dir temp. |
| `server/fleet_db.py` | in repo | Read device row (`get_device_by_mac`, `list_devices`) | Already the identity source. |
| `zoneinfo.available_timezones()` | stdlib | Membership validation of IANA keys | Rejects path-like keys such as `../x` before `ZoneInfo()` is called. |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| New `server/device_dirs.py` | Put helpers in `fleet_db.py` | `fleet_db` is typed and DB-only; path logic is also needed by the companion and the backup script (which must not import server). Keep a separate leaf module. |
| `/devices/<id>` prefix twin generated by `routes.match` | A second hand-written route list | Violates "declared once" (D-09) and doubles Phase 54's annotation work. |
| Device in cookie/query (`?device=`) | - | Rejected by D-09 (owner chose path prefix). |

**Version verification:** not applicable (no registry packages).

## Architecture Patterns

### System Architecture Diagram

```
Frame (MAC+secret, Bearer token, X-Img-Fmt, X-Battery-Mv ...)
   |  GET /device/v1/display
   v
BYOS Handler.do_GET --> _authenticate_device(headers)  (visits every token, constant-time)
   |                        | no match -> 401 {"detail":"unknown token"}
   v mac
fleet.db (read-only) --> row {id, state_path, hardware_type}
   |  fleet.db absent/faulted -> legacy: every registered MAC is the live frame (state_path ".")
   v
device_dirs.resolve(root, state_path)   state_path "." -> root + args.image  (LIVE, unchanged code path)
   |                                    "devices/d_xxxxxxxx" -> <root>/devices/d_xxxxxxxx + <dir>/panel.bin
   |                                    anything else / escapes root -> 503, never fall back
   v DeviceContext
read panel -> size check (profile geometry, 960000 for legacy type)
   -> _served_image(X-Img-Fmt) -> sha256 -> _publish_image(ctx.state_dir) -> offer (root OTA registry; battery_low from ctx dir)
   -> sleep_s = quiet_hours_sleep_s(battery_critical_sleep_s(display_off_sleep_s(wake_interval(ctx.state_dir)...)), tz of ctx config)
   -> {"image_url": live: /img/<sha>.bin | other: /img/<id>/<sha>.bin, "image_hash", "sleep_s", ...}

Owner browser --> companion Handler._dispatch
   routes.match(method, path)  -- strips optional /devices/<id> prefix for device_scoped routes
   |-> RouteMatch.device_id (None = live frame, URLs unchanged)
   v
device_scope.resolve(root, device_id)  -> Device(id, state_dir, name, hardware profile) | 404
   v
page_context(handler, device) -> ctx.state_dir = device.state_dir -> existing page modules
POST /poll-now -> poll_lock_for(device.state_dir) (non-blocking) -> poll_cycle.run_once(state_dir=device.state_dir, caddy_log=None)
POST /settings, /quick/* -> device_config.save_device_config(device.state_dir, ...)  (only that dir)
```

### Recommended Project Structure
```
server/device_dirs.py            # NEW leaf, stdlib only: LIVE_STATE_PATH, DEVICE_ID_RE, state_path_for(id), resolve_state_dir(root, state_path), provision_device_dir(...)
server/test_device_dirs.py       # NEW
stub-server/byos_server.py       # _authenticate_device, DeviceContext, _handle_display (extracted), per-device /img route
stub-server/fleet_cli.py         # devices add: --state-path auto|. ; provisions dir for non-live
companion/device_scope.py        # NEW: Device lookup from fleet.db, route prefix helpers, per-device poll locks
companion/routes.py              # Route gains device_scoped; match() strips /devices/<id>
companion/app.py, post_actions.py# handlers take explicit device; no self.args.state_dir in device handlers
server/device_policy.py          # timezone helpers; QUIET_HOURS_TZ stays as the default
server/device_config.py          # "timezone" key
deploy/backup/skypane_backup.py  # per-device dir allow-list walk
test-support/                    # two_device_fleet fixture (fleet.db + devices/ dirs + FrameServer)
```

### Pattern 1: Device directory resolution (single validated chokepoint)
**What:** `resolve_state_dir(root, state_path)` returns the absolute directory or raises `ValueError`. Accepts only `"."` or `devices/<id>` where `<id>` matches `\Ad_[0-9a-f]{8}\Z`; verifies `os.path.realpath(result)` is inside `os.path.realpath(root)/devices` (rejects symlink escapes; the backup already refuses symlinks, so a symlinked device dir is never legitimate). Never concatenates a request-supplied string: the only request-derived values are a token (compared) and a route `<id>` (regex-validated, then looked up in fleet.db; the directory comes from the stored `state_path`, not from the URL).
**When to use:** every place that turns a fleet.db row or a URL id into a path (BYOS, companion, fleet_cli, backup).
**Example:**
```python
# Source: derived from server/fleet_db.py (id format) and server/atomic_io.py conventions
LIVE_STATE_PATH = "."
DEVICE_ID_RE = re.compile(r"\Ad_[0-9a-f]{8}\Z")
_DEVICES_DIRNAME = "devices"

def state_path_for(device_id: str) -> str:
    if not DEVICE_ID_RE.match(device_id):
        raise ValueError("bad device id")
    return "%s/%s" % (_DEVICES_DIRNAME, device_id)

def resolve_state_dir(root: str, state_path: str) -> str:
    if state_path == LIVE_STATE_PATH:
        return root
    head, _, tail = state_path.partition("/")
    if head != _DEVICES_DIRNAME or not DEVICE_ID_RE.match(tail):
        raise ValueError("bad state_path")
    path = os.path.join(root, head, tail)
    base = os.path.realpath(os.path.join(root, _DEVICES_DIRNAME))
    if os.path.commonpath([os.path.realpath(path), base]) != base:
        raise ValueError("state_path escapes the devices directory")
    return path
```

### Pattern 2: BYOS `DeviceContext`, resolved once per request
**What:** `_authenticate_device(headers) -> mac | None` (visit every token with `hmac.compare_digest`, record match, no early exit), then `_device_context(root, mac)`:
- fleet.db usable (`_fleet_view` is not None): row via `fleet_db.get_device_by_mac`; no row -> 401; row -> `resolve_state_dir(root, row["state_path"])` (ValueError -> 503 `{"detail":"device state unavailable"}`).
- fleet.db unavailable (absent/fault): legacy behaviour, every authenticated MAC is the live frame (root, `--image`). This preserves D-03 of Phase 48 (live frame keeps working without fleet.db). A device that exists only in fleet.db has no token in the legacy store, so it cannot authenticate in this mode (fail closed, matching `resolve_hardware_type`).
- `state_path == "."` -> `image_path = args.image`; otherwise `image_path = <dir>/panel.bin`. The size check uses `hardware.get_profile(type)` geometry for a non-legacy type (`(w//2)*h`), the existing `IMAGE_BYTES` for the legacy type, so the live frame's check is byte-identical.
**Example:**
```python
# Source: stub-server/byos_server.py existing helpers (_fleet_device_type, _note_fleet_status)
def _handle_display(self):
    mac = self._authenticate_device()
    if mac is None:
        return self.send_json(401, {"detail": "unknown token"})
    ctx = _device_context(self.args, mac)       # DeviceContext or None
    if ctx is None:
        return self.send_json(503, {"detail": "device state unavailable"})
    ...  # same body as today, with ctx.state_dir / ctx.image_path / ctx.width / ctx.height
```
Keep `bearer_ok()` and `_resolve_device_id` untouched for `/device/v1/log` and the tests that import them.

### Pattern 3: Per-device timezone in `device_policy` (byte-identical default)
`seconds_until_quiet_hours_end(now_utc, start_hm, end_hm, tz=QUIET_HOURS_TZ)` (new keyword with default; the only change inside is `.astimezone(tz)`). Add `timezone_for(config: object) -> ZoneInfo` (valid IANA string in `config["timezone"]` else `QUIET_HOURS_TZ`; never raises). `quiet_hours_status(config, now_epoch)` calls `timezone_for(config)`; its signature is unchanged, so `server/wake.py:175-177`, `server/poll_cycle.py:711`, `companion/pages/home_page.py:376` need no signature change. The BYOS path (`quiet_hours_sleep_s(base, state_dir, now=None)`) reads the tz through a new `read_timezone(state_dir)` that mirrors `read_quiet_hours` (fail-open, never raises), keeping `read_quiet_hours`'s return shape (tests pin it). `QUIET_HOURS_TZ` stays exported with its identity (`test_poll_cycle.py:302` asserts `byos_module.QUIET_HOURS_TZ is device_policy.QUIET_HOURS_TZ`; `test_device_policy.py:284` asserts `device_config.QUIET_HOURS_TZ is device_policy.QUIET_HOURS_TZ`).
`device_config` stores `timezone` only when it differs from the default (omit the key when equal to `Europe/Paris`). Reason: `save_device_config` rewrites the whole file, so always writing the key would change the live frame's `device_config.json` bytes on its next unrelated save (D-01). `load_device_config` always returns the key (default filled). Validation: `isinstance(str)`, `value in zoneinfo.available_timezones()` (cache the set once), reject everything else with `ValueError` like the sibling `_validate_*` helpers. The previous release ignores the unknown key on read and drops it on its own next save (reverting to Paris): acceptable under D-02, note it in the plan.
Also update the DST-fold docstring wording ("Europe/Paris" in `seconds_until_quiet_hours_end` docstring, `device_policy.py:205-222`) so the comment states the window is in the device's timezone (comment-history guard: no phase/plan IDs).

### Pattern 4: Route table shape for Phase 54
Extend the existing namedtuple, do not restructure:
```python
Route = collections.namedtuple("Route", "method matcher handler auth_required device_scoped", defaults=(False,))
RouteMatch = collections.namedtuple("RouteMatch", "path query captured device_id", defaults=(None,))
```
`match(method, path, query)`: if `path` matches `\A/devices/(d_[0-9a-f]{8})(/.*)?\Z`, set `device_id` and match the remainder (or `"/"` when empty -> HOME) against routes with `device_scoped=True` only; a `/devices/<id>/login` or `/devices/<id>/ui-theme` must be a 404 (assert in a test). Un-prefixed paths match as today with `device_id=None` (live frame). Handlers receive `m.device_id` through `RouteMatch`; `Handler._dispatch` resolves it to a `Device` once (404 page for an id that is not in fleet.db, never a fallthrough to the live frame) and passes it explicitly: `lambda h, m: h._handle_poll_now(m.device)` style. Add a `device` field to `RouteMatch` instead of mutating the handler, so no handler can reach a "current device" global.
Existing tests that parametrise over `routes.ROUTES` (`test_route_table.py::_GATED_ROUTES`, baseline JSON in `testdata/`) keep working because the un-prefixed forms are unchanged; add a new test class for prefixed forms rather than editing the committed baseline.

**Exact device-scoped route list (Phase 54 must annotate these; the final report must reproduce this list)**
GET (all become `device_scoped=True`):
- `HOME_ROUTE` `/`, `DISPLAY_ROUTE` `/display`, `DEVICE_ROUTE` `/device`, `FLIGHTS_ROUTE` `/flights`, `HEALTH_ROUTE` `/health`, `AIRLINES_ROUTE` `/airlines`
- legacy redirects `SETTINGS_ROUTE` `/settings`, `HISTORY_LEGACY_ROUTE` `/history`, `PREVIEW_PAGE_ROUTE` `/preview` (redirect target must keep the device prefix)
- `/gallery/<name>` (reads `<device dir>/gallery`), `/illustration/<key>.png` (GET; per-dir overrides), `THEME_PREVIEW_ROUTE_PREFIX` `<...>.png`, `FRAME_PREVIEW_ROUTE_PREFIX` `<...>.png` (theme_preview takes state_dir)
POST (all `device_scoped=True`):
- `/settings`, `/poll-now`, `/quick/display`, `/quick/quiet-hours`, `/quick/led`
- `airlines_page.RESOLVE_ROUTE`, `RENAME_ROUTE`, `RENAME_RESET_ROUTE`, `MANUAL_DELETE_ROUTE_PREFIX...SUFFIX`, POST `/illustration/<key>.png` (replace)
- `RULES_ADD_ROUTE`, `RULES_DELETE_ROUTE_PREFIX...SUFFIX`, `CALENDAR_CONNECT_ROUTE`, `CALENDAR_DISCONNECT_ROUTE`
NOT device-scoped (stay as is; Phase 54 treats them as session/admin-level): `/login`, `/logout`, `/ui-theme`, `/ui-lang`, the 18 static assets, `/static/runway-*.png` (`RUNWAY_IMAGE_ROUTE_PREFIX`, static diagrams), and **`/update` + `UPDATE_INSTALL_ROUTE` + `UPDATE_CANCEL_ROUTE`** (the OTA registry is per hardware type at the root, shared across devices; see Open Questions).

### Pattern 5: Prefix-aware links and forms (the large mechanical part)
The pages embed ~350 absolute-route literals (`href`, `action`, `return_to` hidden fields, `a[href="/health"]` selectors in `ui_nav.py:322`). Recommended mechanism: a request-scoped `ContextVar` (the same pattern as `companion/prefs.py::set_request_prefs`) holding the route prefix (`""` for the live frame reached un-prefixed, `"/devices/<id>"` otherwise), set once in `_dispatch`, plus one helper `device_scope.scoped(route)` used by every emitter of a device-scoped route: nav links (`ui_nav._nav_links`), quick-switch forms (`ui_components.py:380`, `settings/runway_led.py:192`), poll forms (`settings/rules.py:151,171`), calendar/rules/airline-sheet forms, `flash.flash_toast_html(..., self.path)`, the freshness script's fetch URL, and the `_referring_tab`/`return_to` whitelists (compare the prefix-stripped path, redirect to the re-prefixed one). Rejected alternative: regex-rewriting rendered HTML at `send_html` (brittle against JS strings and attribute shapes). The completeness safety net is a crawl test (see Validation Architecture): for every device-scoped GET page rendered for a non-live device, every `href`/`action`/`return_to` that equals a device-scoped route must start with that device's prefix.
For the live frame, un-prefixed requests emit un-prefixed links, so existing browser baselines (`companion/testdata`, `test_render_baseline.py`) stay byte-identical.

### Pattern 6: Device selector
A small component rendered in `page_shell` only when fleet.db lists more than one device (a single-device install renders nothing new, so the live frame's current HTML and the committed baselines are unchanged). Use the existing segmented-control/`<select>` GET-form idiom already used by the Update page type chooser (`update_page.py:252`) per `sketch-findings-skypane`; options link to `/devices/<id>/<current page>`; the live frame is option 1 and un-prefixed. Strings go through `i18n.msg` with French entries in `companion/i18n_fr/nav.py` (`test_i18n_ids.py` enforces coverage). Device display name: `devices.name`, else the short id; never show MAC, token or secret prefix.

### Anti-Patterns to Avoid
- **Resolving a device by directory listing** (`os.listdir(devices/)`): the directory name is not authority; fleet.db is. A directory without a row serves nothing.
- **Falling back to the live frame on any resolution failure** (unknown id, bad `state_path`, missing panel): return 401/404/503. A fallback is exactly the "shared default" Phase 51 removes.
- **`self.args.state_dir` inside a device-scoped handler.** Add a structure test that greps nothing (behaviour-over-source rule) but instead behaviourally proves isolation (two devices, mutate A, assert B bytes unchanged).
- **Passing the device dir to `firmware_registry`/`fleet_db`.** Those read the root.
- **Writing `timezone` unconditionally** (changes live-frame file bytes on any save).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Atomic file writes | open/write/rename | `server/atomic_io.atomic_write` | Mode, fsync, no torn files. |
| Cross-process device lock | new lock file scheme | `poll_cycle.poll_cycle_lock(state_dir, timeout_s=0)` (`poll.lock`) | Already per directory, flock, `PollBusy`. |
| Concurrent device_config read-modify-write | own lock | `save_device_config` (flock `device_config.lock` + in-process lock) | Already per `state_dir`. |
| SQLite snapshot for backup | file copy of `history.db` | `skypane_backup.snapshot_db` | WAL-safe backup API plus `integrity_check`. |
| IANA validation | regex or manual table | `zoneinfo.available_timezones()` membership | Handles aliases; rejects path-like keys. |
| Image container for `X-Img-Fmt` | second encoder | `server/image_container` (`negotiate_version`, `encode_container`) via existing `_served_image` | Phase 50 single encoder; pass profile width/height. |
| Placeholder image bytes | PIL render | `bytes([0x11]) * ((w//2)*h)`-style fill (nibble 1 = white, per `panel_format.WHITE`), distinct per device if a test needs distinguishing images | No Pillow in the BYOS/provision path; poll-now replaces it with a real render. |

**Key insight:** the repo already made `state_dir` the unit of isolation everywhere; the phase is about *choosing the right directory per request*, not about new storage mechanics. Anything that introduces a second keying scheme (device id as a column, per-device tables) fights the existing code.

## Common Pitfalls

### Pitfall 1: Breaking the live frame's frozen contract
**What goes wrong:** the live frame's image URL, hash or state files change.
**Why:** `measured_fields_freeze.json` freezes `image_url_path_template = "/img/{sha256}.bin"`, the display response key set `{firmware,image_hash,image_url,led_enabled,reset,sleep_s}`, `battery_state` keys `{battery_mv, received_at}`, poll-state keys, wake constants. `test_image_negotiation.py::test_legacy_response_keys_equal_the_freeze_list` and `test_announce_adds_no_display_key` forbid new response keys.
**How to avoid:** the per-device image URL must be a *different path shape only for non-live devices*; add no key to the display JSON; do not add keys to `battery_state.json` or the live `poll_state.json`; keep `FREEZE` untouched (changing it needs owner agreement). The live branch must run the identical code path with `state_dir == root`.
**Warning signs:** `test_phase47_freeze.py` or `test_image_negotiation.py` diffs; a `device_config.json` byte diff after an unrelated save.

### Pitfall 2: `/img/<sha>.bin` has no device identity
**What goes wrong:** a non-live device's image is published to `<its dir>/img/<sha>.bin`, but the unauthenticated `/img/<sha>.bin` route only searches the root, so the frame gets 404.
**How to avoid:** non-live devices get `"image_url": ".../img/<device_id>/<sha>.bin"`. New route regex `\A/img/(d_[0-9a-f]{8})/([0-9a-f]{64})\.bin\Z`; resolve the id through fleet.db (must have `state_path` of the `devices/` form, never `"."`), read only from that device's `img/`. Unknown id/hash -> the existing 404 body. Do not search all device dirs by hash. The firmware accepts any URL passing `fp_url_valid` (scheme/host/length), so a longer path is fine [VERIFIED: firmware/main/api_client.c:606,653 - length is `sizeof(image_url)`, confirm buffer size in the plan]. Keep `/img/<sha>.bin` for the live frame so the freeze template still holds.

### Pitfall 3: Path traversal via `<id>` and `state_path`
**What goes wrong:** `/devices/..%2f..` or a tampered `state_path` row reads outside `devices/`.
**How to avoid:** `DEVICE_ID_RE` on every id (URL and DB), the `resolve_state_dir` containment check, and path matching on the raw `parsed.path` (the router already matches the raw path; do not `unquote` before the regex). `fleet_db.add_device` currently accepts any `state_path` string: add validation there (call `device_dirs.resolve_state_dir`-style shape check) so a bad row can never be written; resolution re-validates on read.

### Pitfall 4: Concurrent writers
**What goes wrong:** two companion tabs or poll-now + settings write the same device dir.
**How to avoid:** every write already goes through atomic_io or an flock; the new shared mutable thing is the in-process `_POLL_LOCK` registry: create entries under a registry lock; key by realpath; never hold the registry lock while polling. Lock order documented in `atomic_io` (in-process lock, then `poll.lock`, then `calendar_rules.lock`; `device_config.lock` never nested): the registry lock is a leaf taken only to fetch the per-device lock. Also create `devices/<id>/` with `os.makedirs(..., exist_ok=True)` and the same mode semantics as the root (setgid, group-writable via the service umask 0027); provisioning must not race the poll creating the same dir (`exist_ok=True`).

### Pitfall 5: Backup silently omits per-device data
**What goes wrong:** `skypane_backup.py` allow-lists top-level names; `devices` is neither included nor in `KNOWN_EXCLUDED`, so today it only produces a drift line and is **not archived**. Every non-live device's config, history and gallery would be lost on restore.
**How to avoid:** extend the backup to walk `devices/d_xxxxxxxx` directories matching `DEVICE_ID_RE`, archiving per-device `INCLUDE_FILES` (the per-device subset: `device_config.json`, `poll_state.json`, `battery_state.json`, `calendar_rules.json`, `calendar_url.secret`, `colour_rules.json`, `manual_resolutions.json`), `INCLUDE_DIRS` (`illustration_overrides`, `gallery`), and `history.db` via `snapshot_db`, with `arcname=devices/<id>/<name>`; keep `panel.bin`, `img/`, `*.lock`, `*.tmp`, `history.db-wal/-shm` excluded and symlinks refused. Add `devices` to the known-top-level set so no drift line appears for it, while an unexpected file inside a device dir still reports drift. Tests in `deploy/tests/test_backup.py` style: concurrent writer on a device `history.db`, restore into an empty dir and compare (existing fleet.db restore test is the template, lines 372-490). Note the byos/companion systemd units already have `ReadWritePaths=/opt/skypane/state` (covers subdirectories) [VERIFIED: deploy/*.service].

### Pitfall 6: Expand-only and the previous release
**What goes wrong:** rollback behaviour surprises.
**Facts:** the previous release ignores `devices/` and the new `timezone` key; it keeps serving the live frame from root. BUT `fleet_cli devices add` also calls `byos_server.register_device` (legacy `devices.json`) and enrolment dual-writes tokens into `byos_state.json`, so a new device's MAC/token also authenticate against the *previous* release, which serves them the live frame's `--image` and writes their battery into the root `battery_state.json`. That is inherent in the dual-write design chosen in Phase 48 and affects only devices created in this phase (simulated/test devices, no production deploy per D-04). Record it as a rollback note in the plan and in `deploy/README.md`; do not try to engineer around it. No change to the live frame's rows, `state_path` stays `"."`, no migration step is needed (confirm `fleet_migrate` is not re-run with changes).

### Pitfall 7: Existing tests that encode single-state assumptions
- `server/test_retired_notifications.py:65` asserts ten config keys -> update to eleven.
- `stub-server/test_poll_cycle.py:293-313` pins the `QUIET_HOURS_TZ` identity -> keep the constant.
- `companion/test_route_table.py` + `companion/testdata` baseline -> do not edit the baseline; add tests for the prefixed forms.
- `companion/test_structure_guards.py`: `FILE_LINE_LIMIT = 1500`, `FUNCTION_LINE_LIMIT = 80`; `app.py` is 1328 lines. Put new companion code in `companion/device_scope.py`, and extract (not inline) the BYOS display body: `Handler.do_GET` is 64 code lines against the 80 gate [VERIFIED: `check_function_size.py report`].
- `_record_device_report_and_offer` is already long: pass `state_dir` (root) and a new `device_state_dir` parameter rather than growing the body.

### Pitfall 8: Health/history fidelity for non-live devices
The live frame's check-in and battery history come from the Caddy log tailer (no device identity), which must not run for device dirs (Pitfall in the poll-cycle caveats). So a non-live device would have no `device_health` rows and its Health page would show "no check-in". Recommended small addition, BYOS-side and only when `state_dir != root`: after a successful display poll, best-effort `history_db.record_device_health(conn, ts, battery_mv, fw_version, boot_reason, rssi)` into the device's own `history.db` (stdlib-only module; `history_db` imports only stdlib, so the BYOS stays dependency-free) [VERIFIED: server/history_db.py imports]. This is skipped for the live frame so its freeze-tested behaviour is untouched. Failures are swallowed (like `save_battery_state`). If the planner prefers less scope, the Health page for a non-live device must at least render "never checked in" without error (test it).

## Code Examples

### Per-device poll in the companion (explicit device, per-device lock)
```python
# Source: companion/app.py _handle_poll_now (existing) adapted; poll_cycle.run_once(lock_timeout_s=0) existing
def _handle_poll_now(self, device):
    back = self._referring_tab()
    lock = device_scope.poll_lock_for(device.state_dir)       # dict keyed by realpath, created under a registry lock
    if not lock.acquire(blocking=False):
        return self.redirect(device_scope.scoped_redirect(back, device, FLASH_KEY_POLL_ALREADY_RUNNING))
    try:
        remaining = poll_cooldown_remaining(device.state_dir)
        ...
        poll_cycle.run_once(state_dir=device.state_dir, geofence=self.args.geofence, lock_timeout_s=0)  # no caddy_log
    finally:
        lock.release()
```

### Two-device isolation test skeleton (D-14 byte-identical)
```python
# Source: pattern from stub-server/test_image_negotiation.py + test-support/skypane_live_state.snapshot_dir
before = snapshot_dir(dev_b.state_dir)               # {relpath: (sha256, mtime_ns)}
save_device_config(dev_a.state_dir, quiet_hours_enabled=True, timezone="America/Martinique")
assert snapshot_dir(dev_b.state_dir) == before      # includes mtimes, so an untouched file proves no write
assert snapshot_dir(live.state_dir) == live_before
```

## Simulated devices: initial image and config

Provision with one function used by `fleet_cli devices add` (new flag `--state-path auto`, default stays `.` so existing invocations and `test_fleet_cli.py` are unchanged) and by test fixtures:
`device_dirs.provision_device_dir(root, device_id, width, height)`:
1. `os.makedirs(<root>/devices/<id>, exist_ok=True)`.
2. Seed `device_config.json` only if absent, using the same defaults `load_device_config` returns (so a missing file and a seeded one behave identically; seeding with `{}` is acceptable and leaves the Paris default implicit).
3. Seed `panel.bin` only if absent: `(width//2)*height` bytes (960,000 for the clone type), via `atomic_io.atomic_write`. For tests that need "own image" proof, accept an optional `fill` byte so two devices differ (their served hashes differ and `/img/<id>/<sha>.bin` returns each device's own bytes).
4. Do not create `poll_state.json`/`history.db`/`img/`; those are created lazily by the existing code paths.
The first `POST /poll-now` for a `sim-ee02-clone` device renders a real image into its dir. Simulated types require `SKYPANE_SIM_HARDWARE=1` in the byos and companion processes; `fleet_db.add_device` already enforces the gate, and `resolve_hardware_type` fails closed (no OTA offer) when the gate is off, but image serving must also behave sanely (a row whose type is unavailable -> 503, not a crash). Test fixtures must set the env var explicitly (existing tests have an autouse `_no_sim` fixture that clears it).

## Runtime State Inventory

Not a rename/migration phase for the live frame (D-06: it is never moved; no migration). For completeness:

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | Live frame: root-level files and `fleet.db` row with `state_path="."`. New devices only create new rows/dirs. | None for live. New code only writes new dirs. |
| Live service config | None (Caddy proxies the whole BYOS port; no path allow-list found in `deploy/Caddyfile`). | Re-check Caddyfile for `/img` path matchers when planning (grep found none). |
| OS-registered state | systemd units unchanged; `ReadWritePaths=/opt/skypane/state` already covers subdirs. | None. |
| Secrets/env vars | `SKYPANE_SIM_HARDWARE` gates simulated types. | Tests must set it; never in production env template. |
| Build artifacts | None. | None. |

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `"default"` device bucket in `firmware/device_report.json` | MAC-keyed entries; unresolved token gets no bucket | Phase 48 | Legacy `"default"` key is read-tolerated only; keep its two regression tests. |
| Single raw image | Per-request container negotiation (`X-Img-Fmt`) | Phase 50 | Must be preserved per device (D-03). |
| One `QUIET_HOURS_TZ` | Default plus per-device `timezone` | This phase | Pure helper takes tz argument. |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `fp_url_valid` / the `image_url` buffer in firmware accept `/img/d_xxxxxxxx/<64 hex>.bin` (about 90 chars of path) | Pitfall 2 | A frame could reject the URL; read `firmware/main/api_client.c` and its size constant in the plan; only non-live (simulated) devices are affected in this phase. |
| A2 | Caddy forwards any path on the BYOS vhost without a path matcher | Runtime State Inventory | `/img/<id>/...` would 404 in production; grep showed no matcher but the Caddyfile template should be re-read by the planner. |
| A3 | A circular dependence of the freshness script on `location.pathname` means it needs no change for prefixed URLs | Pattern 5 | Auto-refresh could poll the wrong device page; verify `companion/static/freshness.js` in the plan. |
| A4 | The Update page and OTA registry should remain global (not device-scoped) in this phase | Pattern 4 | Phase 54 role design differs; needs owner confirmation (Open Question 3). |
| A5 | Per-device `history.db` health rows should be fed by the BYOS (not Caddy) for non-live devices | Pitfall 8 | If owner wants no BYOS history writes, Health shows "never checked in" for non-live devices. |

## Open Questions

1. **Numeric id vs `d_xxxxxxxx` (CONTEXT D-05).**
   - Known: the schema and `add_device` use an opaque text id; the live frame's row already has one.
   - Recommendation: treat D-05 as "the `devices.id` of fleet.db" and use it verbatim as the directory name and URL segment. Flag to the owner in the plan summary; no schema change.
2. **Non-1200x1600 simulated devices and `/poll-now`.** `poll_cycle` renders only the legacy geometry. Recommend refusing poll-now for a type whose profile geometry differs from `panel_format` (clear flash text, FR/EN), leaving landscape devices on the seeded placeholder until Phase 56. Alternative: only ever create clones in tests.
3. **Is the Update (OTA) page device-scoped?** Recommended: no (registry is per hardware type, root-level); keep `/update*` global and let Phase 54 make it admin-only.
4. **UI time display timezone.** `companion/ui_base.LOCAL_TZ` stays Europe/Paris for timestamps; only quiet-hours arithmetic follows the device timezone. A device in another zone would show "until 07:00" in its own zone but timestamps in Paris time. Recommend leaving as is (FLT-02 scope) and noting it for Phase 53/56.
5. **`locations.timezone` (fleet.db) vs `device_config.timezone`.** Two sources now exist for one fact. Recommend `device_config.json` authoritative for quiet hours (BYOS and poll read only the device dir); Phase 53 reconciles with the location.
6. **Timezone input UX.** Recommended: a `<select>` with a curated France-wide list (Europe/Paris plus overseas zones such as America/Martinique, America/Guadeloupe, America/Cayenne, Indian/Reunion, Indian/Mayotte, Pacific/Noumea, Pacific/Tahiti) plus the stored value if outside it; server validation against the full IANA set regardless.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3 + `server/.venv` (pytest, xdist, cov, ruff, mypy, playwright) | all tests and gates | yes (venv is 3.13 locally, 3.14 in prod) | 3.13 | - |
| Chromium via pytest-playwright | companion browser tests | not probed in this session | - | `SKYPANE_REQUIRE_BROWSER=1` makes a missing browser fail CI; plan browser tests accordingly |
| `tzdata` / system zoneinfo | timezone validation | assumed present on Ubuntu 26.04 and dev hosts | - | If `available_timezones()` is empty in a test environment the validator must not silently accept everything; test with a known key |

No external services are needed (all tests run on loopback; pytest-socket blocks non-loopback).

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9 + pytest-xdist + pytest-cov + pytest-socket + pytest-playwright (`[tool.pytest.ini_options]`, `--import-mode=importlib`, `testpaths = server stub-server companion test-support deploy hardware`) |
| Config file | `/home/user/skypane/pyproject.toml` (also `[tool.coverage]` floor `fail_under = 93`, `[tool.mypy] files = [...]`) |
| Quick run command | `server/.venv/bin/python3 -m pytest stub-server/test_phase47_freeze.py stub-server/test_image_negotiation.py stub-server/test_device_fleet.py server/test_device_dirs.py -x -q` |
| Full suite command | `./scripts/run-all-tests.sh` (CI also runs `ruff check .`, `scripts/check_comment_history.py check`, `mypy`, `scripts/check_function_size.py check --max 80 server stub-server`) |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| FLT-01 | Two simulated devices each get their own image bytes/hash from their own dir; `/img/<id>/<sha>.bin` returns that device's bytes only; cross-device hash 404 | integration (real byos subprocess via `FrameServer` + fleet.db seeded) | `pytest stub-server/test_device_fleet.py -x` | Wave 0 |
| FLT-01 | Live frame responses and files unchanged with other devices present | regression | `pytest stub-server/test_phase47_freeze.py stub-server/test_image_negotiation.py -x` | exists (must stay green, unmodified) |
| FLT-01 | `X-Img-Fmt` negotiation per device; non-announcing device gets raw; announcing gets container with profile dims | integration | `pytest stub-server/test_device_fleet.py -k negotiation` | Wave 0 |
| FLT-01 | Unresolved/unknown token -> 401; token for a device whose row has a bad `state_path` -> 503, never the live image; fleet.db absent -> live frame still served | integration/unit | `pytest stub-server/test_device_fleet.py -k "401 or fallback or legacy"` | Wave 0 |
| FLT-01 | `device_dirs.resolve_state_dir` rejects `..`, absolute paths, wrong id shape, symlink escape; `fleet_db.add_device` rejects bad `state_path` | unit | `pytest server/test_device_dirs.py server/test_fleet_db.py -x` | Wave 0 / extend |
| FLT-01 | Per-device health and history pages render from the device dir (own history rows, own battery, never-checked-in state OK) | companion integration | `pytest companion/test_device_pages.py -x` | Wave 0 |
| FLT-01 | Backup archives `devices/<id>/` per-device files and WAL-safe `history.db`, excludes `panel.bin`/`img`/locks, restore round-trip | unit | `pytest deploy/tests/test_backup.py -k devices -x` | extend |
| FLT-02 | `/poll-now` on device A runs cycle in A's dir only (panel.bin, poll_state, history written in A; B and live byte-identical incl. mtimes); no `caddy_log`; no `firmware/` dir created in A | integration (companion with `fake_providers=True`) | `pytest companion/test_device_poll.py -x` | Wave 0 |
| FLT-02 | Per-device poll lock: lock held for A does not block B; held lock gives "already running" for A only | unit/integration | `pytest companion/test_poll_now_lock.py companion/test_device_poll.py -k lock -x` | extend |
| FLT-02 | Quiet hours/timezone POST on `/devices/<id>/settings` writes only that device's `device_config.json`; others byte-identical (D-14) | integration | `pytest companion/test_device_settings.py -x` | Wave 0 |
| FLT-02 | `device_policy` tz arithmetic: default Paris byte-identical to previous results incl. DST edges; non-Paris tz shifts window; invalid tz falls back to default; `device_config` rejects bad IANA (`../x`, `""`, non-str) and omits key at default | unit | `pytest server/test_device_policy.py server/test_config_history.py -x` | extend |
| FLT-02 | BYOS `sleep_s` uses the device's own tz and quiet hours; live frame sleep scenarios unchanged | integration | `pytest stub-server/test_wake_interval_delivery.py stub-server/test_device_fleet.py -k sleep` | extend/Wave 0 |
| FLT-01/02 | Route table: every `device_scoped` route resolves under `/devices/<id>`; global routes 404 under the prefix; unknown id 404 (no live fallback); un-prefixed baseline unchanged | unit/integration | `pytest companion/test_route_table.py companion/test_device_routes.py -x` | extend/Wave 0 |
| FLT-01/02 | Prefix completeness crawl: every device-scoped link/form/`return_to` on every device page carries the prefix; redirects (flash, `return_to`, legacy `/settings`) stay in the device | integration | `pytest companion/test_device_routes.py -k crawl` | Wave 0 |
| FLT-01 | Device selector bilingual, hidden when single device, live default selected | companion + i18n | `pytest companion/test_device_selector.py companion/test_i18n.py companion/test_i18n_ids.py -x` (test-support) | Wave 0 |
| FLT-01/02 | Selector and device pages at 360 px (design contract) | browser | `pytest companion/test_browser_device_selector.py -x` | Wave 0 (marker `browser`) |

### Sampling Rate
- **Per task commit:** the quick command plus the touched module's test file.
- **Per wave merge:** `./scripts/run-all-tests.sh` (whole suite incl. coverage gate), `ruff check .`, `mypy`, `check_function_size.py check --max 80 server stub-server`, `check_comment_history.py check`.
- **Phase gate:** full suite green, `test_phase47_freeze.py` and `test_image_negotiation.py` unmodified and green, before `/gsd:verify-work`.

### Wave 0 Gaps
- [ ] `test-support/skypane_two_device_fleet.py` - fixture helper: seeds `fleet.db` via `fleet_db`/`fleet_cli`, provisions two sim device dirs with distinct fill bytes, sets `SKYPANE_SIM_HARDWARE=1`, returns tokens; reuses `skypane_live_state.seed_live_like_state`, `skypane_frame_server.FrameServer`, `companion_app_server.AppServer`. Must be added to `test_test_support.py` conventions.
- [ ] `server/test_device_dirs.py`, `stub-server/test_device_fleet.py`, `companion/test_device_routes.py`, `companion/test_device_poll.py`, `companion/test_device_settings.py`, `companion/test_device_pages.py`, `companion/test_device_selector.py`, `companion/test_browser_device_selector.py`.
- [ ] mypy: add `server/device_dirs.py` to `[tool.mypy] files` and to the strict-override module list (typed at birth); `server/device_policy.py` is already listed, so the new tz helpers must be fully annotated (`ZoneInfo`, `object` inputs). `companion/device_scope.py` and `stub-server/byos_server.py` are not in the typed set; do not add them.
- [ ] Function-size gate covers only `server` and `stub-server` (max 80 code lines, docstrings excluded); companion has its own ceilings in `companion/test_structure_guards.py` (file 1500 lines, function 80) so `app.py` (1328 lines) cannot absorb the device logic.
- [ ] Behaviour-over-source rule: tests assert served HTML/CSS/JS or a browser, never source text or `.planning/` (`companion/test_suite_guards.py` enforces); no `ast`/`inspect` in companion tests.
- [ ] Coverage floor is 93%: new modules need tests that execute error branches (bad id, escape, missing panel).
- [ ] Comment-history guard: no phase/plan/decision IDs in new comments or docstrings (including "D-05" style references). `scripts/check_comment_history.py check` runs in CI; run it before and after.

## Security Domain

`security_enforcement` is enabled (`.planning/config.json`, ASVS level 1, block on high).

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes (frame bearer token -> device) | Existing token store; `hmac.compare_digest` over every candidate; unresolved = 401. Companion password gate unchanged (Phase 54 adds Auth0). |
| V3 Session Management | no change | Existing signed session cookie; do not make the selected device a trust boundary (no role enforcement until Phase 54). |
| V4 Access Control | partially (isolation between devices; role/ownership is Phase 54) | Device resolved from fleet.db, never from client-supplied path text; route table `device_scoped` flag is the hook for Phase 54. |
| V5 Input Validation | yes | `DEVICE_ID_RE`, `resolve_state_dir` containment, IANA membership check, existing form validators. |
| V6 Cryptography | no change | Tokens/secrets unchanged; never log them. |
| V12 Files/Resources | yes | Atomic writes, mode 0600/umask, regular files only, no symlinks (backup refuses them). |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Path traversal through `/devices/<id>` or `state_path` | Tampering / Info disclosure | Regex on id, `resolve_state_dir` realpath containment, validation in `fleet_db.add_device`, raw-path matching. |
| Cross-device image disclosure via `/img/` | Info disclosure | Device id in URL plus fleet.db lookup; no search across dirs; 256-bit content hash; unauthenticated route kept only because content is non-secret (same rule as today). |
| Fallback to live frame on resolution failure | Info disclosure / Spoofing | Explicit 401/404/503; test that a second device never receives the `--image` bytes. |
| Timing leak in token comparison | Info disclosure | `_authenticate_device` visits every token (mirror `bearer_ok`; existing spy test pattern). |
| Hostile timezone string (`../../etc/passwd`, huge, NUL) | Tampering | Membership in `available_timezones()` before `ZoneInfo()`; fail-open to default on read. |
| CSRF on device POSTs | Tampering | Existing Origin/Sec-Fetch-Site gate runs before `routes.match()`; keep it ahead of prefix handling. |
| Log/secret leakage | Info disclosure | Never print token/MAC secret; log device id only. |

## Sources

### Primary (HIGH confidence) - repository files read in this session
- `.planning/workstreams/v1-2/phases/51-per-device-config-image-and-state/51-CONTEXT.md`, `REQUIREMENTS.md`, `ROADMAP.md` (Phase 51), `STATE.md`, Phase 48 and 50 `*-CONTEXT.md`
- `stub-server/byos_server.py` (all device-handling sections), `stub-server/test_phase47_freeze.py`, `stub-server/measured_fields_freeze.json`, `stub-server/test_image_negotiation.py`, `stub-server/test_fleet_auth.py`, `stub-server/test_ota_offer.py`, `stub-server/fleet_cli.py`
- `server/device_policy.py`, `server/device_config.py`, `server/state_store.py`, `server/poll_cycle.py`, `server/fleet_db.py`, `server/hardware.py`, `server/history_db.py`, `server/atomic_io.py`, `server/firmware_registry.py`
- `companion/routes.py`, `companion/app.py`, `companion/page_context.py`, `companion/post_actions.py`, `companion/flash.py`, `companion/health_signals.py`, `companion/test_route_table.py`, `companion/test_structure_guards.py`, `companion/prefs.py`
- `deploy/backup/skypane_backup.py`, `deploy/tests/test_backup.py`, `deploy/skypane-*.service`, `deploy/provision.sh`
- `pyproject.toml`, `scripts/run-all-tests.sh`, `scripts/check_function_size.py report` output, `test-support/skypane_frame_server.py`, `skypane_live_state.py`, `companion_app_server.py`
- `.claude/CLAUDE.md`, `.claude/skills/sketch-findings-skypane/SKILL.md` (design contract: 360 px minimum, accent reservation, toasts for alerts)

### Secondary / Tertiary
- None. No web sources were needed; no external library is involved.

## Project Constraints (from CLAUDE.md)

- Code, identifiers, comments, docstrings, docs and commit messages in English; companion UI bilingual (EN/FR in `companion/i18n_fr/`, every user-facing string literal via `i18n.msg`).
- Comments say what and why; **no plan/ticket/decision/review/phase IDs in comments** (`scripts/check_comment_history.py check` is a CI gate).
- Server stack is stdlib + Pillow + requests only; the BYOS stays dependency-free (do not import Pillow/requests there; `server/device_dirs.py` and `history_db` are stdlib-only and safe).
- Function-size gate: max 80 code lines over `server` and `stub-server`; companion has its own 1500-line file / 80-line function ceilings.
- mypy module list in `pyproject.toml`; typed modules must stay fully annotated; no PEP 695 syntax in typed files (venv is 3.13/3.11-compatible).
- Tests: pytest with xdist; behaviour-over-source rule (tests assert served output or a browser, never source text or `.planning/`); non-loopback network blocked by pytest-socket; a missing browser fails CI; coverage gate at the measured floor (93%).
- GSD workflow: all file changes through a GSD command; this research writes only the RESEARCH.md. Do not touch Phase 47 files or `hardware/`.
- Owner is French-speaking and not an engineer: anything the owner must do is plain French; repository docs stay English.
- No production deploy (D-04).

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - no new dependencies; all modules read directly.
- Architecture: HIGH - `state_dir` seam verified in every consumer; route/prefix mechanism is a design recommendation (MEDIUM until the crawl test proves completeness over the ~350 route literals).
- Pitfalls: HIGH for freeze, backup, numeric-id and caddy-log findings (verified in code); MEDIUM for firmware URL-length acceptance (A1) and Caddy path handling (A2).

**Research date:** 2026-10-30
**Valid until:** 2026-11-30 (repository-internal; invalidated by changes to `byos_server.py`, `routes.py` or Phase 49/50 follow-ups)
