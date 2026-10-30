# Phase 51: Per-Device Config, Image and State - Pattern Map

**Mapped:** 2026-10-30
**Files analyzed:** 20 new/modified (plus test files)
**Analogs found:** 20 / 20 (2 are partial matches; see "No Analog Found")

Line numbers refer to the repository at mapping time. Excerpts were read in this session. Use RESEARCH.md for the full single-device assumptions inventory and the Phase 54 route list; this file supplies the concrete code to copy from.

Corrections already recorded in RESEARCH.md that the planner must carry: `devices.id` is text `d_` + 8 hex (not numeric); `_resolve_device_id` already returns `None` (the "default" fallback is gone); the Update page type chooser (`update_page.py:240-253`) is a segmented control, not a `<select>` GET form (UI-SPEC is authoritative).

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `server/device_dirs.py` (new) | utility | transform / file-I/O | `server/atomic_io.py` conventions + `server/fleet_db.py` id format | role-match |
| `server/test_device_dirs.py` (new) | test | transform | `stub-server/test_image_negotiation.py` (pytest style) | role-match |
| `stub-server/byos_server.py` (modify: `_authenticate_device`, `DeviceContext`, extracted display handler, `/img/<id>/<sha>.bin`) | controller | request-response | itself: `bearer_ok` 1169-1189, `do_GET` 1230-1322, `_resolve_device_id` 834-852, `_fleet_device_type` 862-887 | exact |
| `stub-server/fleet_cli.py` (modify: `--state-path auto`) | utility (CLI) | CRUD | `fleet_db.add_device` 386-418 | role-match |
| `server/fleet_db.py` (modify: validate `state_path` in `add_device`) | model | CRUD | itself 386-418 | exact |
| `server/device_policy.py` (modify: tz helpers) | utility | transform | itself 189-277 | exact |
| `server/device_config.py` (modify: `timezone` key) | model | CRUD | itself 221-394 (`normalise_*`, `_validate_*`, `_merged_config`) | exact |
| `server/test_retired_notifications.py:65` (modify: ten to eleven keys) | test | transform | itself | exact |
| `companion/routes.py` (modify: `device_scoped`, `device_id`, prefix strip) | route | request-response | itself 25-28, 201-223 | exact |
| `companion/device_scope.py` (new) | service/utility | request-response | `companion/prefs.py` (ContextVar) + `post_actions._POLL_LOCK` | role-match |
| `companion/app.py` + `companion/post_actions.py` (modify: explicit `device` arg, per-device lock) | controller | request-response | `app.py::_handle_poll_now` 1038-1077 | exact |
| `companion/page_context.py` (modify: resolved device dir) | provider | request-response | itself 336-375 | exact |
| Device selector component in `page_shell` + `static/nav-dropdown.js` + `i18n_fr/nav.py` (new) | component | request-response | `update_page._type_chooser_html` 240-253 (form idiom only) | partial |
| Timezone field in `companion/settings/quiet_hours.py` + `i18n_fr/display.py` (modify) | component | CRUD | existing quiet-hours card (same module) | exact |
| Per-device empty states (health/history/home) | component | request-response | `empty_state()` reuse | exact |
| `deploy/backup/skypane_backup.py` (modify: walk `devices/<id>/`) | utility | batch / file-I/O | itself 195-252 | exact |
| `deploy/tests/test_backup.py` (extend) | test | batch | itself (fleet.db restore test, lines 372-490 per RESEARCH) | exact |
| `test-support/` two-device fixture (new) | test fixture | file-I/O | `test-support/skypane_live_state.py::seed_live_like_state` + `snapshot_dir` | exact |
| `stub-server/test_device_fleet.py` (new) | test | request-response | `stub-server/test_image_negotiation.py` (`FrameServer` fixture) | exact |
| `companion/test_device_poll.py`, `test_device_settings.py`, `test_device_routes.py`, `test_device_pages.py` (new) | test | request-response | `companion/test_poll_now_lock.py` (`make_app_server`, `http_request`, `login`) | exact |

## Pattern Assignments

### `stub-server/byos_server.py` (controller, request-response)

**Analog:** itself. Add `_authenticate_device`, `DeviceContext`, `_device_context`, extract the display branch out of `do_GET` (it is already near the 80-line gate), and add the per-device image route.

**Constant-time token compare, no early exit (copy into `_authenticate_device`, but return the MAC)** (lines 1169-1189 for `bearer_ok`, 834-852 for MAC lookup):
```python
auth = self.headers.get("Authorization", "")
if not auth.startswith("Bearer "):
    return False
presented = auth[len("Bearer "):].encode("utf-8", "surrogateescape")
matched = False
candidates = effective_tokens(self.args.state_dir, self.state)
for stored in list(candidates.values()):
    stored_bytes = stored.encode("utf-8", "surrogateescape")
    if hmac.compare_digest(presented, stored_bytes):
        matched = True
return matched
```
`_resolve_device_id` (848-852) returns on first match (`return mac`). `_authenticate_device` must iterate `candidates.items()`, remember the matching mac in a local, never `return` inside the loop (`test_fleet_auth.py::test_bearer_compare_visits_every_candidate` pins no-early-exit). Leave `bearer_ok` and `_resolve_device_id` untouched (imported by `test_ota_offer.py`).

**fleet.db read-only lookup, fail-closed shape (copy for `_device_context`)** (lines 862-887):
```python
try:
    conn = fleet_db.connect_readonly(state_dir)
except fleet_db.FleetDbAbsent:
    _note_fleet_status(state_dir, fleet_db.STATUS_ABSENT)
    return _FLEET_UNAVAILABLE
except (fleet_db.FleetDbError, sqlite3.Error, OSError) as exc:
    _note_fleet_status(state_dir, fleet_db.STATUS_FAULT, type(exc).__name__)
    return _FLEET_UNAVAILABLE
try:
    if fleet_db.meta_get(conn, fleet_db.META_MIGRATED) is None:
        _note_fleet_status(state_dir, fleet_db.STATUS_ABSENT)
        return _FLEET_UNAVAILABLE
    row = fleet_db.get_device_by_mac(conn, mac)
...
finally:
    conn.close()
```
Reuse this structure but return the whole row (`state_path`, `hardware_type`, `id`), not just the type. `_FLEET_UNAVAILABLE` means legacy mode: the authenticated MAC is the live frame (root, `args.image`).

**Display handler body to extract** (lines 1230-1308). Every `self.args.state_dir` and `self.args.image` in it becomes `ctx.state_dir` / `ctx.image_path`:
```python
if not self.bearer_ok():
    return self.send_json(401, {"detail": "unknown token"})
...
battery_mv = parse_battery_mv(self.headers.get("X-Battery-Mv"))
if battery_mv is not None:
    try:
        save_battery_state(self.args.state_dir, battery_mv)
    except OSError:
        pass
try:
    with open(self.args.image, "rb") as fh:
        image = fh.read()
except OSError:
    return self.send_json(503, {"detail": "image unreadable"})
if len(image) != IMAGE_BYTES:
    return self.send_json(503, {"detail": "image wrong size"})
served = _served_image(self.headers.get("X-Img-Fmt"), image)
digest = hashlib.sha256(served).hexdigest()
try:
    _publish_image(self.args.state_dir, digest, served)
except OSError:
    return self.send_json(503, {"detail": "image unavailable"})
```
Notes for the planner: `_served_image` (664-675) uses module constants `WIDTH, HEIGHT`; pass profile width/height for non-live devices. The `image_url` string at 1273 stays `"%s://%s/img/%s.bin"` for the live frame; non-live gets `"%s://%s/img/%s/%s.bin"` with the device id. `_record_device_report_and_offer(self.args.state_dir, ...)` keeps the ROOT; only `read_battery_low_active` moves to the device dir. The `sleep_s` composition order (1284-1290) is load-bearing; keep it and pass `ctx.state_dir` to each reader. Add no key to the returned JSON.

**Per-device image route (copy and adapt)** (lines 648, 1309-1322):
```python
_IMG_PATH_RE = re.compile(r"\A/img/([0-9a-f]{64})\.bin\Z")
...
match = _IMG_PATH_RE.match(self.path)
if match is not None:
    path = os.path.join(_img_dir(self.args.state_dir), "%s.bin" % match.group(1))
    try:
        with open(path, "rb") as fh:
            image = fh.read()
    except OSError:
        return self.send_json(404, {"detail": "unknown image"})
    self.send_response(200)
    self.send_header("Content-Type", "application/octet-stream")
    self.send_header("Content-Length", str(len(image)))
    self.end_headers()
    self.wfile.write(image)
    return None
```
New sibling regex: `\A/img/(d_[0-9a-f]{8})/([0-9a-f]{64})\.bin\Z`. Resolve id through fleet.db to a `devices/` state_path (never `"."`), read only that device's `img/`; unknown id or hash returns the same 404 body. Match against the raw `self.path` (existing convention, see comment at 650-653).

**Publish and prune (reuse unchanged with the device dir)** (678-692): `_publish_image(state_dir, digest, image)` takes any state dir; `IMG_KEEP = 8`.

**Quiet-hours tz seam** (549-571, 616-637): `read_quiet_hours(state_dir)` reads `device_config.json` fail-open and returns `device_policy.quiet_hours_window(data)`. Add `read_timezone(state_dir)` mirroring it (same `try/except (OSError, ValueError)` shape, same non-dict guard), and have `quiet_hours_sleep_s` pass the tz into `seconds_until_quiet_hours_end(now, start_hm, end_hm, tz)`. Keep `read_quiet_hours`'s return shape (tests pin it).

---

### `server/device_dirs.py` (utility, transform + file-I/O) - new

**Analog:** no existing path-resolution helper. Copy the id format from `server/fleet_db.py:408` (`device_id = "d_" + secrets.token_hex(4)`) and write atomically via `server/atomic_io.atomic_write`. Use RESEARCH.md "Pattern 1" code verbatim (`LIVE_STATE_PATH`, `DEVICE_ID_RE`, `state_path_for`, `resolve_state_dir` with realpath containment). Stdlib only, leaf module (the backup script must not import `server`; duplicate the regex there). Atomic-write convention (from the live-state fixture, `test-support/skypane_live_state.py:34-35`):
```python
def _write_json(path: str, doc: object) -> None:
    atomic_io.atomic_write(path, json.dumps(doc, indent=1))
```
`provision_device_dir(root, device_id, width, height, fill=None)`: `os.makedirs(..., exist_ok=True)`; seed `device_config.json` only if absent; seed `panel.bin` (`bytes([0x11]) * ((w//2)*h)` by default) only if absent via `atomic_write`; create nothing else (`poll_state.json`, `history.db`, `img/` are lazy).

---

### `server/fleet_db.py` (model, CRUD) - modify `add_device`

**Analog:** itself (lines 386-418). Today `state_path: str = "."` is stored unvalidated:
```python
hardware.get_profile(hardware_type, environ)
while True:
    device_id = "d_" + secrets.token_hex(4)
    ...
conn.execute(
    "INSERT INTO devices (id, mac, secret_sha256, token, hardware_type, "
    "owner_user_id, location_id, name, state_path, created_at) "
    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", ...
```
Validate `state_path` (only `"."` or `devices/d_xxxxxxxx`) next to `_check_mac(mac)` / `_check_secret(secret_sha256)` at the top, raising `ValueError` like the siblings. Note the id is generated after the check, so `--state-path auto` must generate the id first or `add_device` must derive `devices/<id>` itself when asked (planner decision).

---

### `server/device_config.py` (model, CRUD) - add `timezone`

**Analog:** itself. Follow the `normalise_*` / `_validate_*` / `_merged_config` trio exactly.

**Normaliser pattern** (lines 189-195, 209-218):
```python
def normalise_quiet_hours_enabled(value):
    if isinstance(value, bool):
        return value
    return DEFAULT_QUIET_HOURS_ENABLED
```
**Loader returns a fixed key set** (221-254): add `"timezone": normalise_timezone(data.get("timezone"))` and update the docstring "ten keys" wording.
**Validator pattern** (286-295): raise `ValueError("... got %r" % (value,))` before anything is written; add `_validate_timezone(timezone)` (`isinstance(str)` and membership in a cached `zoneinfo.available_timezones()` set).
**Save path** (380-394): `os.makedirs(state_dir, ...)`, `_SAVE_LOCK`, `atomic_io.exclusive_lock(<dir>/device_config.lock)`, load, `_merged_config`, `atomic_write(path, json.dumps(new_config, indent=1))`.
Load-bearing detail (D-18): `_merged_config` must OMIT the `timezone` key when it equals `Europe/Paris`, otherwise the live frame's file bytes change on its next unrelated save. Add `timezone=None` keyword to `save_device_config` (None carries forward). Update `server/test_retired_notifications.py:65` (`_REMAINING_CONFIG_KEYS`) from ten to eleven.

---

### `server/device_policy.py` (utility, transform)

**Analog:** itself. Current shape (lines 189, 205, 221, 260-277):
```python
QUIET_HOURS_TZ = ZoneInfo("Europe/Paris")
def seconds_until_quiet_hours_end(now_utc: datetime, start_hm: str, end_hm: str) -> int | None:
    local_now = now_utc.astimezone(QUIET_HOURS_TZ)
```
Add `tz: ZoneInfo = QUIET_HOURS_TZ` as a trailing keyword, replace the single `.astimezone(QUIET_HOURS_TZ)` with `.astimezone(tz)`, add `timezone_for(config) -> ZoneInfo` (never raises), and call it in `quiet_hours_status` (signature unchanged, so `server/wake.py:175-177`, `server/poll_cycle.py:711`, `companion/pages/home_page.py:376` need no change). Keep the `QUIET_HOURS_TZ` identity (asserted by `test_poll_cycle.py:302` and `test_device_policy.py:284`). Strict typing applies (mypy module list). Update the docstring "Europe/Paris" wording to "the device's time zone" without phase or plan IDs (comment-history guard).

---

### `companion/routes.py` (route, request-response)

**Analog:** itself.

**Tuple shapes to extend with defaults** (lines 25-28):
```python
Exact = collections.namedtuple("Exact", "path")
PrefixSuffix = collections.namedtuple("PrefixSuffix", "prefix suffix")
RouteMatch = collections.namedtuple("RouteMatch", "path query captured")
Route = collections.namedtuple("Route", "method matcher handler auth_required")
```
New: `Route(... "auth_required device_scoped", defaults=(False,))` and `RouteMatch(... "captured device_id", defaults=(None,))`. Existing positional constructions (e.g. line 75, 195-198) keep working.

**Route declaration style** (75, 195-198):
```python
Route("GET", Exact(route), lambda h, m: h._serve_static_route(m.path), False)
Route("POST", PrefixSuffix(RULES_DELETE_ROUTE_PREFIX, RULES_DELETE_ROUTE_SUFFIX),
      lambda h, m: h._handle_rule_delete_post(m.captured), True),
```
**Matcher to extend** (204-223): the loop `for route in ROUTES: ... isinstance(matcher, Exact) ... startswith/endswith`. Add a prefix pre-step: match raw `path` against `\A/devices/(d_[0-9a-f]{8})(/.*)?\Z`; if it matches, run the same loop on the remainder (`"/"` when empty) considering only `route.device_scoped` routes, and set `device_id` on the returned `RouteMatch`. A non-device-scoped route under the prefix (`/devices/<id>/login`) must return `None` (404). Handlers become `lambda h, m: h._handle_poll_now(m.device)` style; resolve `m.device_id` to a `Device` in `Handler._dispatch`, 404 for an id not in fleet.db (never fall through to the live frame). Do not edit `companion/testdata` baselines; add prefixed-form tests separately.

---

### `companion/app.py` + `companion/post_actions.py` (controller, request-response)

**Analog:** `app.py::_handle_poll_now` (lines 1038-1077). Copy the whole structure, replacing the global lock and `self.args.state_dir`:
```python
back = self._referring_tab()
if not _POLL_LOCK.acquire(blocking=False):
    return self.redirect("%s?flash=%s" % (back, quote(FLASH_KEY_POLL_ALREADY_RUNNING)))
try:
    state_dir = self.args.state_dir
    remaining = poll_cooldown_remaining(state_dir)
    if remaining > 0:
        flash = FLASH_KEY_POLL_COOLDOWN
    else:
        try:
            poll_cycle.run_once(
                state_dir=state_dir, geofence=self.args.geofence,
                lock_timeout_s=0)
        except poll_cycle.PollBusy:
            flash = FLASH_KEY_POLL_ALREADY_RUNNING
        except Exception:
            flash = FLASH_KEY_POLL_FAILED
        else:
            mark_poll_triggered(state_dir)
            flash = FLASH_KEY_POLL_TRIGGERED
finally:
    _POLL_LOCK.release()
return self.redirect("%s?flash=%s" % (back, quote(flash)))
```
Changes: signature `_handle_poll_now(self, device)`; `device_scope.poll_lock_for(device.state_dir)` replaces `_POLL_LOCK`; `device.state_dir` replaces `self.args.state_dir`; never pass `caddy_log`; refuse (303 + warning flash, no filesystem touch) when the device's hardware geometry differs from the poll render geometry (D-16); redirects keep the `/devices/<id>` prefix. The module-level lock lives at `post_actions.py:80` (`_POLL_LOCK = threading.Lock()`), re-exported at `app.py:252` and used at `app.py:1019-1025` for calendar sync; those sites switch to the per-device lock too. `companion/test_companion_app_05.py:1168-1198` acquires `app_module._POLL_LOCK` directly: keep a compatible name for the live frame or update these tests deliberately.

`self.args.state_dir` sites listed in RESEARCH (app.py 660, 673, 729, 755, 761, 785, 788, 812, 931, 1000, 1049, 1063, 1119, 1190-1207, 1248, 1262; post_actions.py 227, 240, 302, 370, 403, 422). The firmware-registry sites (1190-1207, 1248) stay on the ROOT (Update is global, D-17).

File-size ceiling: `app.py` is 1328 lines against the 1500 gate; new logic goes in `companion/device_scope.py`.

---

### `companion/device_scope.py` (service/utility, request-response) - new

**Analog:** `companion/prefs.py` (ContextVar-per-request pattern) for the route-prefix helper:
```python
_LANG_CTX = contextvars.ContextVar("skypane_lang", default=DEFAULT_LANG)

def set_request_prefs(lang=None):
    _LANG_CTX.set(lang if lang in LANG_CHOICES else DEFAULT_LANG)

def current_lang():
    return _LANG_CTX.get()
```
Mirror it: `_PREFIX_CTX = ContextVar("skypane_device_prefix", default="")`, one setter called once in `_dispatch`, one `scoped(route)` helper used by every emitter of a device-scoped route (nav `ui_nav._nav_links`, quick-switch forms `ui_components.py:380` and `settings/runway_led.py:192`, poll forms `settings/rules.py:151,171`, `flash.flash_toast_html`, `_referring_tab`/`return_to` whitelists). The module's docstring discipline ("one set path, N read paths, no other mutation path") is the convention to copy.

Per-device lock registry: a dict keyed by `os.path.realpath(state_dir)` guarded by a leaf `threading.Lock` held only to fetch or create the entry, never while polling (lock order in `atomic_io`). Keep non-blocking acquire (`companion/test_poll_now_lock.py` pins it).

`Device` lookup: read fleet.db via `fleet_db.connect_readonly` / `list_devices` (returns `id, mac, hardware_type, name, state_path, ...`, no token), then `device_dirs.resolve_state_dir(root, row["state_path"])`. Never list directories as authority.

---

### `companion/page_context.py` (provider, request-response)

**Analog:** itself, the single seam (lines 336-375):
```python
state_dir = handler.args.state_dir
...
device_cfg = device_config.load_device_config(state_dir)
last_checkin_ts = _safe_last_checkin_ts(state_dir)
battery_critical = wake.read_battery_critical(state_dir)
ctx = PageContext({"state_dir": state_dir, "ui_theme": ..., "device_config": device_cfg, ...
```
Replace line 343 with the per-request resolved device directory (passed in, not read from a global). All 257 `ctx.state_dir` uses in page modules then work unchanged. Exception: `health_signals._read_fleet_status(state_dir)` must receive the ROOT. Add a `device` field to the context so pages can render the selector and per-device empty states.

---

### Device selector (component, request-response)

**Analog (idiom only):** `companion/pages/update_page.py::_type_chooser_html` (lines 240-253):
```python
return (
    '<form class="theme-form update-type-chooser" method="get" action="%s" aria-label="%s">%s</form>'
) % (layout.UPDATE_ROUTE, escape_html(i18n.t(TYPE_CHOOSER_LABEL_TEXT)), buttons)
```
Copy: GET form that works without script, `escape_html`, `i18n.t(...)`. Do NOT copy the segmented buttons or `aria-label` on the form. UI-SPEC requires `<div role="group" aria-labelledby=...>` wrapping an unnamed `<form>`, a `<label for>` plus native `<select>`, always-visible submit hidden only under `device-selector--armed`, and the `change` handler in the existing `static/nav-dropdown.js`. Render nothing when fleet.db lists one device (keeps baselines byte-identical). Strings through `i18n.msg` with French entries in `companion/i18n_fr/nav.py` (`test-support/test_i18n_ids.py` enforces coverage).

---

### Timezone field in quiet-hours card (component, CRUD)

**Analog:** the existing quiet-hours card in `companion/settings/quiet_hours.py` (not excerpted; read it in the plan task). Constraints from UI-SPEC: field goes last in the card (after the dial and readout), carries `form="settings-form"` because the card renders outside `#settings-form`, joins the card's `data-dirty-section`, curated ten-zone list with server-computed UTC offset, whole POST rejected atomically on invalid zone with the field restored to the stored value. The settings POST handler (`post_actions.py` around 227-422) must forward `timezone` to `save_device_config(device.state_dir, ...)` and omit it from the call when unchanged. Display page baselines in `companion/testdata` need regeneration (intended change).

---

### `deploy/backup/skypane_backup.py` (utility, batch/file-I/O)

**Analog:** itself. Allow-list loop (lines 213-229) and drift loop (238-245):
```python
with tarfile.open(partial_path, "w:gz") as tar:
    for db_name in SNAPSHOT_DBS:
        db_src = os.path.join(state_dir, db_name)
        if os.path.exists(db_src):
            snap_path = os.path.join(tmp_dir, db_name)
            snapshot_db(db_src, snap_path)
            tar.add(snap_path, arcname=db_name, filter=_no_symlinks)
    for filename in INCLUDE_FILES:
        path = os.path.join(state_dir, filename)
        if os.path.exists(path):
            tar.add(path, arcname=filename, filter=_no_symlinks)
    for dirname in INCLUDE_DIRS:
        path = os.path.join(state_dir, dirname)
        if os.path.isdir(path):
            tar.add(path, arcname=dirname, filter=_no_symlinks_or_known_excluded)
...
known = set(INCLUDE_FILES) | set(INCLUDE_DIRS) | set(SNAPSHOT_DBS)
for entry in sorted(os.listdir(state_dir)):
    if entry in known or _is_known_excluded(entry):
        continue
    print("skypane_backup: not in include list: %s" % entry)
```
Add a loop over `devices/` entries matching `\Ad_[0-9a-f]{8}\Z` (duplicate the regex; do not import `server`), archive per-device files (`device_config.json`, `poll_state.json`, `battery_state.json`, `calendar_rules.json`, `calendar_url.secret`, `colour_rules.json`, `manual_resolutions.json`), dirs (`illustration_overrides`, `gallery`), and `history.db` through `snapshot_db` with `arcname="devices/<id>/<name>"`. Skip `firmware` per device (root only), keep `panel.bin`, `img`, `*.lock`, `*.tmp`, WAL files excluded via `_is_known_excluded`, refuse symlinks (`_no_symlinks`, lines 105-112). Add `devices` to `known`; an unexpected file inside a device dir still prints a drift line. The function is already long; extract a helper to stay under the function-size gate where applicable.

---

### Test fixtures and tests

**Two-device fixture (analog `test-support/skypane_live_state.py`):** `seed_live_like_state(state_dir, mac, secret_hex, token)` (lines 61-96) writes `devices.json`, `byos_state.json`, `device_config.json`, `poll_state`, `battery_state.json`, `firmware/device_report.json`, `panel.bin`, and returns `SimpleNamespace(state_dir, mac, secret_hex, token, ...)`. Build the new fixture on it: live frame via `seed_live_like_state`, then add a second device with a different MAC/token (write into `byos_state.json` tokens plus a fleet.db row with `state_path="devices/<id>"`, `SKYPANE_SIM_HARDWARE=1` set explicitly) and `device_dirs.provision_device_dir(..., fill=...)`. The byte-identical proof uses `snapshot_dir(path)` (lines 99-108), which returns `{relpath: (sha256, mtime_ns)}`:
```python
before = snapshot_dir(dev_b.state_dir)
save_device_config(dev_a.state_dir, quiet_hours_enabled=True, timezone="America/Martinique")
assert snapshot_dir(dev_b.state_dir) == before
```

**BYOS integration tests (analog `stub-server/test_image_negotiation.py`):**
```python
@pytest.fixture(autouse=True)
def _no_sim(monkeypatch):
    monkeypatch.delenv("SKYPANE_SIM_HARDWARE", raising=False)

@pytest.fixture
def served(tmp_path):
    live = seed_live_like_state(str(tmp_path))
    with open(os.path.join(live.state_dir, "panel.bin"), "wb") as fh:
        fh.write(deterministic_panel())
    server = FrameServer(live.state_dir)
    server.start()
    yield live, server
    server.stop()
```
sys.path bootstrap (lines 20-28): insert `REPO_ROOT` and `test-support`, then `from skypane_frame_server import FrameServer`, `from skypane_live_state import seed_live_like_state`. In the new file the `_no_sim` fixture must be overridden to set `SKYPANE_SIM_HARDWARE=1`. `POLL_HEADERS` (lines 33-38) and `REFERENCE_DISPLAY` (46-53) are the live-frame regression oracle; do not modify `test_image_negotiation.py`, `test_phase47_freeze.py` or `measured_fields_freeze.json`.

**Companion tests (analog `companion/test_poll_now_lock.py`):**
```python
from companion_app_server import http_request, login
server = make_app_server(fake_providers=True)
base = server.base_url()
cookie = login(server)
lock_path = os.path.join(server.state_dir, "poll.lock")
with atomic_io.exclusive_lock(lock_path, 5):
    status, headers, _ = http_request(base + "/poll-now", method="POST", cookie=cookie)
    assert status == 303
    assert "flash=poll_already_running" in headers.get("Location", "")
```
Tests must assert served HTML/behaviour, never source text or `.planning/` (enforced by `companion/test_suite_guards.py`).

## Shared Patterns

### Atomic, locked file writes
**Source:** `server/atomic_io.py` (`atomic_write`, `exclusive_lock`), used at `server/device_config.py:380-394`
**Apply to:** `device_dirs.provision_device_dir`, any new per-device write. Lock order: in-process lock, then `poll.lock`, then `calendar_rules.lock`; `device_config.lock` never nested. Never hand-roll open/write/rename.

### Fail-open readers on the always-on BYOS
**Source:** `stub-server/byos_server.py:549-571` (`read_quiet_hours`), 1243-1248 (battery write swallowed on `OSError`)
**Apply to:** `read_timezone`, per-device health recording (Pitfall 8 in RESEARCH): a telemetry side effect must never turn a healthy poll into a 500; failures degrade to "no signal".

### Fail closed, never fall back to the live frame
**Source:** `_resolve_device_id` (834-852) returning `None`, display 401 at 1232-1233, 503 on unreadable or wrong-size image 1252-1255
**Apply to:** BYOS `_device_context` (unknown MAC 401, bad `state_path` 503), companion unknown id (404), per-device `/img/<id>/...` (404 body `{"detail": "unknown image"}`).

### Path safety
**Source:** RESEARCH Pattern 1 (`resolve_state_dir`), `skypane_backup._no_symlinks` (105-112)
**Apply to:** BYOS, companion `device_scope`, `fleet_db.add_device`, backup. Validate ids with `\Ad_[0-9a-f]{8}\Z` on every URL and DB value; never concatenate request text into a path; match the raw path (no `unquote` before the regex).

### State dir as the unit of isolation
**Source:** every `server/*.py` module takes `state_dir` (device_config, state_store, history_db, poll_cycle, firmware_registry)
**Apply to:** pass the device dir everywhere except `firmware_registry`, `fleet_db`, `fleet_status.json` and the OTA registry, which stay on the ROOT. Never pass `caddy_log` to `poll_cycle.run_once` for a device dir.

### i18n and design system
**Source:** `companion/i18n_fr/*`, `test-support/test_i18n_ids.py`, `.claude/skills/sketch-findings-skypane/`
**Apply to:** every new user-facing string (English plus French in the module named in UI-SPEC's copywriting table). No new tokens, keyframes or script files.

### CI gates
`ruff check .`, `scripts/check_comment_history.py check` (no plan, phase or decision IDs in comments), mypy (module list in `pyproject.toml`; add `server/device_dirs.py` if it is typed), `scripts/check_function_size.py check --max 80 server stub-server`, `companion/test_structure_guards.py` (`FILE_LINE_LIMIT = 1500`, `FUNCTION_LINE_LIMIT = 80`), coverage floor 93.

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `server/device_dirs.py` | utility | file-I/O | No existing state-path resolution or per-directory provisioning helper; use RESEARCH Pattern 1 code plus `atomic_io` conventions. |
| Device selector `<select>` | component | request-response | No existing native `<select>` GET-form navigator in the companion (the Update chooser is a segmented control); reuse the form idiom only and follow UI-SPEC Component 1. |

## Metadata

**Analog search scope:** `stub-server/`, `server/`, `companion/` (app, routes, page_context, prefs, pages/update_page), `deploy/backup/`, `test-support/`, test files named above.
**Files read or grepped:** about 18 (RESEARCH.md was read to line 442 of 522; the unread tail is the end of the Validation Architecture test map and does not change file selection).
**Pattern extraction date:** 2026-10-30
