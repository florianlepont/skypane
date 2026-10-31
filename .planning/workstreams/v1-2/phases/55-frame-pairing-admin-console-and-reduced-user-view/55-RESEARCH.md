# Phase 55: Frame Pairing, Admin Console and Reduced User View - Research

**Researched:** 2026-10-30
**Domain:** Python stdlib HTTP companion + BYOS device server + SQLite fleet.db (pairing, audit, ownership-gated user view, admin console)
**Confidence:** HIGH for everything read from the repository (file:line evidence below); MEDIUM for the design recommendations marked `[ASSUMED]`.

All claims below are `[VERIFIED: codebase read]` unless tagged otherwise. Nothing in this phase needs a new external package.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Fixed by the owner before discussion (do not reopen)
- **D-01:** Frames keep MAC + secret authentication, independent of Auth0. What the live frame receives (image, interval, auth) does not change; `stub-server/test_phase47_freeze.py` stays green; expand-only.
- **D-02:** No production deploy. No real Auth0 or external service in tests (fake Auth0, pytest-socket guard). No Auth0 secret or real pairing code in the repo.
- **D-03:** Pairing works server-side with what the firmware already does (a frame shows whatever image the display endpoint returns and sleeps for the interval it is given). Any firmware need is reported to the owner, never worked around or added here.
- **D-04:** `legacy-admin` removal stays the owner's decision; do not remove it.
- **D-05:** Co-management is Phase 60; do not implement it. `access.authorized_device_id` keeps its owner-as-input shape.

#### Unassigned frame (owner choice)
- **D-06:** A `pending_devices` table (new, schema 3) holds a frame that is enrolled but not yet assigned: MAC, secret hash, hardware type, device token, current pairing code (hash) and expiry. The `devices` row is created only on claim, with its owner, so the Phase 48 rule "exactly one owner, NOT NULL" is untouched. The BYOS registry and token lookups (`tokens_by_mac`, `registry_view`, setup enrolment) must also read `pending_devices`.
- **D-07:** An admin registers a new frame from a form in the console (MAC + secret SHA-256 printed by `firmware/provision.sh`, hardware type). The CLI gets the same verb. The raw secret never enters the companion; only its hash is submitted.
- **D-08:** A pending frame calling `/device/v1/display` receives a server-rendered pairing image in the format it already understands (raw legacy format for 1200x1600; Phase 50 container where negotiated) and a server-chosen 300 s interval. The live frame never takes this path.

#### Pairing code (owner choice)
- **D-09:** 8 characters of Crockford base32 (no 0/O/1/I/L), shown as `XXXX-XXXX`, entered case-insensitively, with look-alike characters normalised. Generated with `secrets`; only a hash is stored; compared in constant time.
- **D-10:** Valid 30 minutes; a new code is issued on expiry at the pending frame's next wake. An unpaired frame wakes every 5 minutes (server-imposed, new frames only), so a displayed code always outlives at least one wake.
- **D-11:** Single use and atomic: claiming a code is one SQLite transaction that deletes the pending row, inserts the `devices` row (owner, hardware, state directory) and writes the audit entry. Two simultaneous claims: exactly one wins, the other gets "invalid or expired". Wrong, expired and already-claimed codes answer identically.
- **D-12:** Claim attempts are throttled per admin session and globally (reuse `LoginThrottle` patterns) and every failed attempt is audited without recording the guess.

#### Reassign and retire (owner choice)
- **D-13:** Reassigning a frame to another user wipes the previous owner's data: device config (calendar URL, colour rules, airline overrides, illustration overrides), history, poll state, gallery. The frame keeps its MAC, secret and token (no re-enrolment) and restarts like a new frame. The live frame (`state_path = "."`) is never wiped: reassigning it changes the owner only, and retiring it is refused (guard that protects the Phase 47 measurements).
- **D-14:** Retiring a frame keeps its token valid and serves a "frame retired" image with a 24 h interval, so the current firmware (no recovery from 401 before Phase 57) neither loops nor drains the battery. Retirement is reversible: an admin can re-activate the frame, which returns it to the pending state with a fresh code. Hard deletion stays a CLI-only act (`devices remove`).

#### Console and user view (owner choice)
- **D-15:** Admin console pages: Fleet (every device with owner, hardware, last seen, battery, firmware, pending and retired frames, actions), Users (invite with email + role, change role, disable and re-enable, unlink Auth0 identity; guard: the last active admin cannot be demoted or disabled, nobody disables themselves), Audit log (read-only, newest first), Releases (the existing per-hardware `/update` page entered from the console, no redesign), Locations (see D-18). From the Fleet list an admin opens a frame's own pages under `/devices/<id>/...` as today.
- **D-16:** An ordinary user sees only their own frames (pending, retired and other users' frames do not exist for them: 404). Per frame they keep: Home, Flights, Display (look, quiet hours, time zone, display on/off), Calendar, colour rules and airline names/resolution (the former Display and Airlines pages), and a reduced Health. They do not get: the fleet list, other users, the audit log, releases/update, wake interval, LED, "poll now", the hardware/OTA details.
- **D-17:** The user's Health page shows the frame only: last contact, battery, next wake, frame anomalies. It hides the ADS-B and airline-source status (platform health). Platform health stays admin-only.
- **D-18:** Locations are available to both roles. An admin manages all locations in the console; an ordinary user creates their own locations (name, latitude, longitude, time zone), sees only their own, and picks one for their own frames. This needs an owner column on `locations` (schema 3, expand-only: existing locations belong to nobody and stay visible to admins and assignable by admins; users cannot see or use them). Quota, validation and rate limits are research items. Zones and detection modes remain Phases 52/53; this phase only stores and assigns the location.

#### Audit and safety
- **D-19:** An append-only `audit_log` table (fleet.db, therefore in the backup): actor, action, target, outcome, timestamp, source IP; no secrets, no codes, no guesses. Events: frame registered, pairing issued/claimed/failed, reassigned, retired/re-activated, user invited/role changed/disabled/enabled/identity unlinked, location changes, release actions. Read-only page for admins; no purge in this phase.
- **D-20:** Per-session CSRF token on every state-changing admin and pairing POST (the Phase 54 hand-off asked to revisit this before destructive admin actions). Existing Origin / Sec-Fetch-Site checks stay.
- **D-21:** All new schema changes are one expand-only migration to schema 3 (`pending_devices`, `audit_log`, `locations.owner_user_id`). Same rollback caveat as Phase 54: the previous release's byos refuses a schema it does not know; surface it in the hand-off. The freeze test and the backup/restore test cover the new tables.

### Claude's Discretion
Module layout, table and column names, how the pairing image is drawn (Pillow, vendored fonts, six-colour palette), page layouts under `sketch-findings-skypane`, bilingual strings in `companion/i18n_fr/`, route paths, plan split and waves, throttle parameters, location quotas.

### Deferred Ideas (OUT OF SCOPE)
- Device co-management — Phase 60.
- Removal of the `legacy-admin` fallback — owner decision, any time after this phase.
- Firmware recovery after 401 and any on-device pairing UI — Phase 57.
- "View as user" (AUTH-07).
- Audit log purge/export.

Also out of scope (CONTEXT domain): firmware changes (Phase 57), fleet polling and zones (52), detection modes (53), per-hardware rendering and battery profiles (56), any production deploy, Phase 47 files and `hardware/`. First plan = the Phase 54 hand-off section A (matrix rows).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| AUTH-04 | An admin can pair a new frame to a user with a short, single-use, expiring on-panel code, claimed atomically and audited. | Section 2 (BYOS pending path, firmware facts), Section 3 (pairing image render/cache), Section 4 (schema 3, claim transaction), Section 9 (code security, throttle, audit), "Pairing code" and "Claim transaction" patterns. |
| AUTH-05 | An admin can use a console (fleet, users, reassign/retire, releases); ordinary users get a reduced view of their own frames. | Section 1 (matrix + ownership gate), Section 5 (wipe), Section 6 (UI, nav, Health split), Section 7 (locations), Section 8 (tests), CSRF design, role-conditional rendering and field-stripping landmines. |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- Code, identifiers, comments, docstrings, docs, commit messages in English; companion UI bilingual (EN/FR strings in `companion/i18n_fr/`, every user-facing string literal is an `i18n.msg(...)`).
- Comments say what/why (invariants, units, spec pointers). **No plan/ticket/decision/review/phase IDs in comments** (`scripts/check_comment_history.py check` runs in CI). Do not write "D-11" or "Phase 55" in code comments.
- Server stack: Python 3.14 production (venv here is 3.13), **stdlib + Pillow + requests only**; no new dependency.
- Tests: pytest + xdist + cov; **behaviour-over-source** (tests assert served HTML/CSS/JS or a browser, never source text or `.planning/`; `companion/test_suite_guards.py` enforces); browser tests on pytest-playwright (missing browser fails CI); ruff (E4/E7/E9/F); mypy over the module list in `pyproject.toml` `[tool.mypy] files` (a new typed module must be added to both `files` and the strict `overrides.module` list); function-size gate (`scripts/check_function_size.py check --max 80 server stub-server`, so `byos_server.py` and `server/` functions <= 80 code lines; companion is not gated); coverage floor 93% whole-suite; hash-locked `server/requirements*.txt`.
- GSD workflow: file edits happen through a GSD command (this research writes only the RESEARCH.md).
- UI work follows `Skill("sketch-findings-skypane")` (tokens, toasts for alerts, accent-reservation list, 360 px floor, 44 px targets, serif headings only).

## Summary

The phase is mostly **additive plumbing on four solid seams** that already exist: (1) a single route table with a mandatory `Access` and a default-deny dispatcher (`companion/routes.py`, `Handler._dispatch`); (2) `fleet_db` with stepwise migrations and `BEGIN IMMEDIATE` transactions; (3) the BYOS token -> MAC -> fleet row -> directory resolution (`byos_server._device_context`), which already refuses unknown rows with 401; (4) a per-device directory layer (`server/device_dirs.py`). The current firmware needs **no change** for pairing or retirement: it reads only `image_url`, `image_hash` (`sha256:<64 hex>`) and `sleep_s` (integer 1..86400, so 300 and 86400 are valid, 86400 exactly at the inclusive ceiling) plus optional `led_enabled`; it sends **no** `X-Img-Fmt` yet (no match in `firmware/main/*.c`), so a pairing image is the raw 960000-byte legacy form.

The risky parts are not the pairing mechanics but the **blast radius of opening device routes to ordinary users**. Five facts drive the plan order: (a) every device-scoped route is `ADMIN_ONLY` today and `Access(USER, "device")` cannot simply be set because `access.decide` is fed `route_match.captured`, which is `None` for un-prefixed `Exact` routes and the live frame is un-prefixed, so admins would 404; (b) `config_page.handle_post` applies `wake_interval_s`, `led_enabled`, `tracked_runway` whatever the scope, so a user POST to `/devices/<id>/settings` can change admin-only settings unless the server strips them; (c) `device_scope.load_devices` and the selector have no owner filter and `Device` has no owner field; (d) `current_prefix()`/`scoped()` emit **un-prefixed** URLs for the live frame, but D-13 allows a user to own the live frame, whose user URLs must be `/devices/<id>/...`; (e) the Health page and nav dot mix frame and platform state in one `health_signals` severity.

The second cluster is **schema and BYOS coupling**: `registry_view`/`tokens_by_mac`/`list_devices` are consumed by byos, tests and the migration tool; retirement needs a storage slot not named in D-21 (recommendation: a `status` column on `pending_devices`); pairing images must live outside `img/` (the live frame's `img/` is pruned to 8 files) and outside the backup include list; `byos_state.json`/`devices.json` must never be written by the companion (byos rewrites them from memory). The pairing image must be byte-deterministic per code (hash-skip is the firmware's only battery protection against redraws every 5 minutes).

**Primary recommendation:** Build in this order: schema 3 + `fleet_db` API (pending/audit/locations/role/last-admin guard) -> pure `pairing_code` + `pairing_image` modules -> BYOS pending branch + `/img/p_<id>/` route -> access/ownership restructure **together with** role-conditional rendering and server-side field stripping (never open user routes before the content is reduced) -> CSRF + audit helpers -> console pages and actions -> matrix rows and real-handler layer for every new/changed route.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Pairing code generation, hashing, normalisation, constant-time compare | API / Backend (`server/pairing_code.py`, stdlib, no sqlite) | — | Pure functions, host-testable, shared by byos (issue) and companion (claim). |
| Code issue + expiry rotation at the frame's wake | API / Backend (BYOS `/device/v1/display`) | Database (`pending_devices`) | The frame only talks to byos; the code is born at the display poll. |
| Pairing/retired image rendering and storage | API / Backend (new `server/pairing_image.py`) | File store (`<state>/pairing/<id>/`) | Pillow + vendored fonts live in `server/`; byos serves content-addressed bytes. |
| Atomic claim, reassign, retire, re-activate | Database (`fleet_db.transaction`) | API (companion handlers) | One `BEGIN IMMEDIATE` transaction is the atomicity guarantee. |
| Ownership gate for device routes | API / Backend (`access.decide`, `Handler._dispatch`) | Database (`fleet_db.get_device_owner`) | Default-deny in one place; matrix proves it. |
| CSRF token derivation and check | API / Backend (`companion/auth.py` + dispatcher) | Browser (hidden form field) | Derived from the session cookie token; no schema change. |
| Role-conditional page content (Display, Health, nav, Account) | Frontend Server (SSR in `companion/pages/*`) | API (server-side field stripping on POST) | Hiding controls is cosmetic; the POST handler must enforce. |
| Audit log writes | Database (append-only table, triggers) | API (`companion/audit.py` helper) | Written in the same transaction as the action it records. |
| Fleet/Users/Audit/Locations pages | Frontend Server (new `companion/pages/*`) | API | Read-mostly SSR pages; actions are POST + redirect with flash. |
| Pending-device wipe/provision of directories | File store (`server/device_dirs.py`) | API | Only `device_dirs` turns a stored path into a filesystem path. |

## Standard Stack

### Core (no new packages)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python stdlib (`sqlite3`, `secrets`, `hmac`, `hashlib`, `http.server`, `json`, `shutil`) | 3.13 venv / 3.14 prod | Everything server-side | Project rule: stdlib + Pillow + requests only. |
| Pillow | per `server/requirements.txt` (hash-locked, already installed in `server/.venv`) | Pairing/retired image drawing | Already the render dependency (`server/plane/render/*`). |
| Vendored fonts `server/assets/fonts/*` (Inter, PT Serif, Zilla Slab; OFL) | in repo | Pairing screen text | Already the only fonts the frame render uses (`server/assets/fonts/VENDOR.md`). |

### Supporting (existing project modules to reuse)

| Module | Purpose | When to Use |
|--------|---------|-------------|
| `server/fleet_db.py` (`transaction`, `add_device`, `assign_owner`, `add_location`, `connect_readonly`) | Schema, atomic writes | All DB work; extend, do not bypass. |
| `companion/auth.py` (`LoginThrottle`, `client_ip`, `new_session_token`, `hash_session_token`, `post_origin_ok`) | Throttle, IP, CSRF derivation | Claim throttle, audit source IP, CSRF. |
| `server/device_dirs.py` (`provision_device_dir`, `resolve_state_dir`, `LIVE_STATE_PATH`) | Directory create/validate | Claim (create) and reassign (wipe + recreate). |
| `server/plane/render/text.py` (`_font`, `_wrap_text`, `draw_tracked_text`), `server/panel_format.py` (`padded_palette`, `IDX_*`, `INDEX_TO_NIBBLE`) | Drawing | Pairing image (read-only use; do not edit these files). |
| `server/image_container.py` via `byos_server._served_image` | Container negotiation | Reuse for the pending response unchanged. |
| Test support: `test-support/companion_app_server.py` (`InProcessAppServer`, `session_cookie_for_state_dir`, `login_via_auth0`), `test-support/fake_auth0.py`, `companion/conftest.py` fixtures | HTTP tests | All companion tests. |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Storing retired state as `pending_devices.status` | `devices.retired_at` column | `devices` requires an owner (NOT NULL); a retired frame has none, so the `pending_devices` slot keeps the Phase 48 rule intact. Both are expand-only. Recommended: `pending_devices.status`. |
| CSRF token stored in `sessions` | Derived `sha256("csrf-v1:" + raw_session_token)` | A column would be a fourth schema change (D-21 lists three); derivation needs no storage and no new secret. Recommended: derive. |
| Pairing image in `fleet.db` BLOB | File under `<state>/pairing/<pid>/` | BLOB puts 960 kB and a code in every backup; file is excluded from backup (needs one `KNOWN_EXCLUDED` entry). Recommended: file. |

**Installation:** none. **Version verification:** not applicable (no new package). The only new third-party surface is zero.

## Package Legitimacy Audit

No external packages are added by this phase. Pillow and the fonts are already vendored/locked in the repository.

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| (none) | — | — | — | — | not run (nothing to check) | — |

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Architecture Patterns

### System Architecture Diagram

```
Admin browser                                   Frame (ESP32, current firmware)
   | POST /console/frames/register (mac+sha256)    | POST /device/v1/setup (mac, provision_secret)
   v                                               v
Companion (companion/app.py)  ----fleet.db----  BYOS (stub-server/byos_server.py)
 _dispatch: origin -> match -> access.decide      _enrol: registry = devices UNION pending(+retired)
   -> csrf check (new routes) -> handler            issue_token -> pending_devices.token
 handler: BEGIN IMMEDIATE                          GET /device/v1/display (Bearer)
   register -> pending_devices (+audit)              _authenticate_device (tokens incl. pending)
   claim(code, owner) :                              _device_context: devices row? -> normal path (unchanged)
     match code hash over pending rows (const time)          else pending row? -> pending branch:
     DELETE pending, INSERT devices, provision dir,             expired/no code -> issue code, render image
     INSERT audit  -> COMMIT                                     to pairing/<pid>/, UPDATE row (BEGIN IMMEDIATE)
   retire / re-activate / reassign(+wipe dir)                    answer {image_url=/img/<pid>/<sha>.bin,
 pages: Fleet / Users / Audit / Locations                          image_hash, sleep_s=300|86400, firmware:null,
 user view: /devices/<owned id>/... (gate = owner)                 reset:false, led_enabled}
                                                    GET /img/p_xxxxxxxx/<sha>.bin -> pairing/<pid>/img/ (content-addressed)
Frame shows image, sleeps sleep_s; next wake: hash-skip if unchanged.
```

### Recommended Project Structure

```
server/
├── pairing_code.py        # NEW pure stdlib: alphabet, generate, normalise, salted hash, verify (mypy-strict listed)
├── pairing_image.py       # NEW Pillow: pairing + retired canvases for any HardwareProfile, raw nibble pack
├── fleet_db.py            # + migration 3, pending/audit/location/role/last-admin API (all typed)
├── device_dirs.py         # + wipe_device_dir(root, state_path) (refuses "."), pairing_dir helpers
companion/
├── audit.py               # NEW thin helper: actor/ip -> fleet_db.audit_append inside the caller's transaction
├── console_actions.py     # NEW mixin (like post_actions.SettingsActionsMixin): register/claim/retire/reactivate/reassign/users/locations POSTs
├── user_view.py           # NEW role helpers: admin-only field set, frame-only health severity, nav for user
├── pages/fleet_page.py, users_page.py, audit_page.py, locations_page.py   # NEW
├── i18n_fr/console.py     # NEW (auto-discovered by pkgutil; no __init__ edit)
stub-server/
├── byos_server.py         # pending branch extracted into small helpers (_handle_display is 57 lines of the 80 allowed)
├── fleet_cli.py           # + devices register-pending / pending-list / retire / reactivate verbs
deploy/backup/skypane_backup.py  # + "pairing" in KNOWN_EXCLUDED (+ test in deploy/tests/test_backup.py)
```

### Pattern 1: Per-route-form access for device-scoped routes (the hand-off, section A)

**What:** A device-scoped route keeps ONE `Route` object for both forms, but the access rule differs by form: `/devices/<id>/...` is `Access(USER, "device")` with the **device id** as the captured value; the un-prefixed form acts on the live frame and stays admin-only.
**Why:** `Handler._dispatch` (companion/app.py:976-1008) calls `access.decide(principal, route.access, route_match.captured, self._owner_lookup)`. For `Exact` routes `captured` is `None` (routes.py:324 `RouteMatch(path, query, None, device_id)`); for `PrefixSuffix` routes `captured` is the path middle, not the device id (the 51 doc says so too). `access.authorized_device_id(principal, None, ...)` returns `None` for **everyone including admins** (access.py:48), so a naive `Access(USER, "device")` 404s the admin on every un-prefixed page.
**Example (shape, not final code):**
```python
# Source: companion/app.py _dispatch + companion/access.py decide (read 2026-10-30)
def _effective_access(route, route_match):
    if not route.device_scoped:
        return route.access, route_match.captured
    if route_match.device_id is None:          # un-prefixed form = live frame
        return routes.ADMIN_ONLY, None
    return route.access, route_match.device_id # Access(USER, "device") for user-reachable routes
```
Routes that stay `ADMIN_ONLY` (no `device_arg`): `/device`, `/poll-now`, `/quick/led`, `/update*`, `/runway-image/{}`, and everything new in the console. Routes that become `Access(USER, "device")`: Home, Display, Flights, Health, Airlines, the three legacy redirects, gallery, illustration GET/POST, theme-preview, frame-preview, `POST /settings`, `/quick/display`, `/quick/quiet-hours`, airlines resolve/rename/reset/manual delete, rules add/delete, calendar connect/disconnect.

### Pattern 2: Atomic claim transaction

**What:** one `fleet_db.transaction(conn)` (BEGIN IMMEDIATE, fleet_db.py:286-295) does: select candidate pending rows, constant-time match the presented code against **every** row (no early exit, a dummy compare when there are none), check expiry and `status == 'pending'`, delete the pending row, `add_device(..., token=pending.token, state_path="auto")`, create the directory, insert the audit row. The directory is created inside the transaction exactly like `fleet_cli.cmd_devices_add` (stub-server/fleet_cli.py:170-192: `provision_device_dir` inside the `with`, `shutil.rmtree(created_dir)` in the `except BaseException`).
**Two concurrent claims:** BEGIN IMMEDIATE serialises writers; the loser finds no row and answers the same "invalid or expired" as a wrong code (D-11).
**Concurrent frame display poll vs claim:** byos reads pending via `connect_readonly` per request (no cache), so after COMMIT the frame's next wake finds a `devices` row and takes the normal path.

### Pattern 3: BYOS pending branch (pending frame at `/device/v1/display`)

`_handle_display` (byos_server.py:1445-1525) today: `_authenticate_device` -> `_device_context` -> `_NO_DEVICE` => 401. Add a third outcome from the context lookup (a `PENDING` sentinel carrying the pending row) before the 401, and an early `return self._handle_pending_display(row)` so the function stays under 80 lines. The pending branch:
1. `BEGIN IMMEDIATE` via `fleet_db.connect(state_dir, create=False)`; if the row has no live code (never issued or `code_expires_at <= now` or image file missing), generate a code, render the image to `<state>/pairing/<pid>/panel.bin`, publish the served bytes (container if announced) with `_publish_image(<state>/pairing/<pid>, digest, served)` (it writes `<dir>/img/<digest>.bin`, byos_server.py:699-713), store `code_salt`, `code_hash`, `code_expires_at`, `last_seen_at`, optional `battery_mv`/`fw_version`, append an audit row ("pairing issued", actor `frame:<pid>`).
2. Answer `{"image_url": "<scheme>://<host>/img/<pid>/<digest>.bin", "image_hash": "sha256:<digest>", "sleep_s": 300, "firmware": null, "reset": false, "led_enabled": ...}`. A retired row answers the same shape with `sleep_s: 86400` and the retired image.
3. Never call `_record_device_report_and_offer`, `save_battery_state(ctx.state_dir...)`, `_record_device_health` (no directory; the live frame's `battery_state.json` must not be touched). `firmware: null` for pending frames.

### Pattern 4: Reduced user view = filter at three layers

Page render (hide), POST handler (strip/refuse), route access (404). Never rely on the first alone.

### Anti-Patterns to Avoid

- **Writing `byos_state.json` / `devices.json` from the companion.** byos holds `Handler.state` in memory and rewrites the whole file on the next enrolment (`issue_token` -> `save_state`, byos_server.py:379-398, 1619). `fleet_cli.RESTART_CAUTION` (fleet_cli.py:50-54) exists for this. Console actions touch **fleet.db only**.
- **Writing a pending frame's token into `byos_state.json`.** When fleet.db is unreadable, `effective_tokens` falls back to the legacy tokens and `_context_without_fleet_db` (byos_server.py:1012-1024) serves the **live image** to a MAC in `live_frame_macs.json` only, but with no `devices/` dir it serves the live image to any authenticated MAC. Pending tokens must exist only in fleet.db.
- **Publishing pairing images into the root `img/`.** `_prune_images` keeps 8 files per `img/` (byos_server.py:716-745, `IMG_KEEP = 8` at :665); pairing images would evict the live frame's served images.
- **Changing `server/device_policy.py` constants** (300 s / 86400 s) — the freeze file pins `wake_constants` (`WAKE_INTERVAL_MAX_S` 3600, `DISPLAY_OFF_SLEEP_S` 300 ...). Put the pending/retired cadences as constants in the new pairing module, not in `device_policy`.
- **Per-request varying pixels** in the pairing image (a clock, a countdown). A changed hash forces a ~31 s panel redraw every 5 minutes.
- **Editing `server/plane/render/*`, `server/panel_format.py`, `server/hardware.py`, `server/poll_cycle.py`, `server/poll_loop.py`** (Phases 52/56 territory).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Throttle | new counter dict | `auth.LoginThrottle` (auth.py:203-291) | Bounded table, per-key lockout, eviction, already tested (`companion/test_login_throttle.py`). |
| Constant-time compare | `==` on hashes | `hmac.compare_digest` over every candidate, no early exit (pattern at byos_server.py:952-967) | Timing side channel. |
| Atomic multi-write | manual commit/rollback | `fleet_db.transaction` (fleet_db.py:286-295) | BEGIN IMMEDIATE + ROLLBACK on any exception. |
| Directory validation | string joins | `device_dirs.resolve_state_dir` / `valid_state_path` | Only code allowed to turn a stored path into a filesystem path (device_dirs.py:1-13). |
| Client IP | read `X-Forwarded-For` | `auth.client_ip(peer, xff)` (auth.py:164-185) | Trusts XFF only from a loopback peer (Caddy). |
| Image container | new framing | `byos_server._served_image` + `image_container.encode_container` | Phase 50 negotiation already tested. |
| Fonts/wrapping | new font loader | `server/plane/render/text._font/_wrap_text` | Same vendored font handling. |
| Form parsing / body caps | new reader | `Handler.read_form` (app.py:675-695, 8 KiB cap, drain) | Existing hardening. |
| Last-admin / self-disable race | check-then-write across requests | count + update inside one `fleet_db.transaction` | Two admins demoting each other concurrently otherwise leave zero admins. |
| Append-only audit | convention | SQLite `BEFORE UPDATE/DELETE ... RAISE(ABORT)` triggers in migration 3 | Enforced by the engine, testable. |

**Key insight:** every hazard in this phase (races, timing, path escape, cross-owner leaks) already has a project-local primitive; the work is wiring them consistently and proving the wiring with the matrix.

## 1. Phase 54 hand-off, section A: what is actually missing (with evidence)

State at HEAD `f2fb236`:

| Item (54-HANDOFF.md section A) | Current state | Evidence |
|---|---|---|
| Every real per-device route `Access(USER, "device")` | **Not done.** All 27 device-scoped routes are `ADMIN_ONLY` with `device_arg=None`. | companion/routes.py:139-209 (GET), :215-272 (POST); `ADMIN_ONLY = Access(ADMIN, None)` at :60. |
| One matrix row per route and derived resource | **Rows exist for all 27 (as `ADMIN_ONLY`)**; the table has no owner-device policy kind. Derived resources (gallery, illustration, theme/frame preview) already have rows. | companion/test_access_matrix.py:48-89 (`ROUTE_POLICY`), :93-105 (`DEVICE_SCOPED`), :109-119 (`OUTCOMES` has only PUBLIC / SIGNED_IN / ADMIN_ONLY). "firmware status", "battery chart" and "history" have **no separate route**: they are rendered inside the pages (no extra row needed). |
| Probe family `/d/<id>/_probe` | Test-only harness (never in production table); keep as a canary. | test_access_matrix.py:220-222 asserts absence from `routes.ROUTES`; support at test-support/access_matrix_support.py:104-112 (`probe_routes`), :115-116; probe tests :418-490. It is the only code that exercises `Access(USER, "device")` with the owner gate today. |
| Re-run the HTTP layer with the real handlers | **Not done.** `stub_routes` swaps *every* handler for a recorder (access_matrix_support.py:95-101). No test drives a real device handler as owner/other/admin. | test_access_matrix.py:307-313 (`stubbed` fixture). `seed_matrix_fleet` (access_matrix_support.py:36-55) stores `state_path="auto"` but **does not create the directories**; real handlers need `device_dirs.provision_device_dir`. |
| Account "Frames" empty state replaced | **Not done.** `account_page.render` always renders the empty state. | companion/pages/account_page.py:76-77, `Handler._handle_account_get` sign_in.py:234-247 reads no frames. |
| Per-session CSRF revisited | **Not done.** No CSRF anywhere; comments say SameSite=Strict only. | grep `csrf` hits only comments: post_actions.py:217/296/364/435, routes.py:227, quick-switch.js:169, auth.py:109. |
| `access.authorized_device_id` keeps owner-as-input | unchanged requirement | access.py:42-57. |

### Exactly what the matrix needs (Plan 1 scope)

1. **New policy kind** `OWNER_DEVICE` (hand-written in `ROUTE_POLICY`) for the 24 routes that become user-reachable, with outcomes under `/devices/<owner device id>/...`: anonymous `login`, owner `allow`, other `not-found`, admin and legacy-admin `allow`. The un-prefixed form of the same route is `admin-only` (owner and other `not-found`). Add a new second table (e.g. `UNPREFIXED_OUTCOMES`) rather than overloading `OUTCOMES`.
2. **Pure layer rewrite.** `test_decide_matches_the_policy_table` (test_access_matrix.py:241-245) calls `access.decide(principal, route.access, None, _never_owner)`; `_never_owner` (:237-238) raises if called. For `Access(USER, "device")` routes it must be called with the device id and a stub `owner_lookup` returning the owner id. Keep the global-route cells unchanged.
3. **`test_a_prefixed_route_never_has_less_access_than_its_base_route`** (:201-209) asserts `prefixed.access == Access(ADMIN-or-USER, None)`. After the change `device_arg` is `"device"` for owner-device routes: update the expected value, keep the "prefixed never weaker than base" invariant by comparing `min_role` and that the un-prefixed form is still resolved as admin by `_effective_access`.
4. **HTTP layer.** `MatrixRig.request` (:266-271) POSTs `data=b""` with only an Origin header. If CSRF is enforced in `_dispatch` for new routes, the helper must also send the derived token for allow-rows; add a separate test that a missing/wrong token is 403 and the handler did not run. (Option: enforce CSRF inside the handlers instead, leaving the matrix untouched, but a dispatcher check cannot be forgotten by a new handler; recommended: dispatcher.)
5. **`stub_routes`** builds `routes.Route(r.method, r.matcher, handler, r.access, r.device_scoped)` positionally (access_matrix_support.py:100-101). Any new `Route` field (e.g. `csrf=False`) must be a defaulted trailing field so this keeps working, and `stub_routes` must copy it.
6. **New rows** for every new console/pairing route (all `ADMIN_ONLY`, `SAMPLE_MIDDLE` entries for templated ones), plus the user-facing `/locations` routes (`SIGNED_IN`-class, ownership by `owner_user_id` is a **second ownership dimension**: add a row set and a probe-style test for "user A cannot read/modify user B's location").
7. **Real-handler layer** (new): no stubbing, seed two users + two provisioned devices, assert owner 200 / other 404 identical to unknown-path 404 body / admin 200 for each user-reachable page and each derived image, and that a user POST cannot change `wake_interval_s`/`led_enabled`/`tracked_runway` (see Pitfall 2).
8. **Completeness guard** `test_every_route_has_a_policy_row_and_every_row_has_a_route` (:173-182) and `DEVICE_SCOPED` equality (:189-192) already fail naming the route — they are the tripwire, no change needed beyond adding rows.

### Dispatch details the planner must account for

- `_dispatch` order today: Origin gate (app.py:984-985) -> `routes.match` (:987) -> principal + `access.decide` (:991-997) -> LOGIN/NOT_FOUND (:998-1001) -> `_dispatch_for_device` (:1008). Insert the CSRF check **after** a successful ALLOW so anonymous callers still get the sign-in redirect and a denied role still gets the generic 404.
- `read_form()` reads `self.rfile` once (app.py:675-695). A dispatcher-level CSRF check needs the form: cache the parsed form on the handler (reset at the top of `_dispatch` next to `_principal_cache`) so handlers that call `read_form()` again get the same dict. Multipart upload routes (`airlines_page.py:432,1188`) are existing routes and are out of the CSRF scope unless the owner wants them (open question).
- Un-prefixed routes under a user principal: after `_effective_access` they are `ADMIN` => 404 for users; no handler can fall through to `devices[0]` (the live frame, device_dispatch.py:30-32) for a user.

## 2. BYOS side for a pending (enrolled, unassigned) frame

### What exists

- **Registry/tokens** are read **per request** from fleet.db, not cached: `_fleet_view` (byos_server.py:342-366) opens `connect_readonly`, requires `META_MIGRATED`, returns `{"registry": registry_view(conn), "tokens": tokens_by_mac(conn)}`; `effective_registry` (:369-371), `effective_tokens` (:374-376). Fleet.db failure => fall back to legacy files, never allow-all (comment at :309-316).
- **The in-memory caches that matter** are legacy only: `Handler.state = load_state(...)` (byos_server.py:1619, tokens from `byos_state.json`) used when fleet.db is unusable, and `issue_token` appends to it and rewrites the file (:379-398). `fleet_cli.RESTART_CAUTION` (fleet_cli.py:50-54) and devices_cli.py:110-113 describe "stop byos before CLI edit": the running byos would write its in-memory copy back over `byos_state.json`/`devices.json`. **Pending registration via companion or CLI must write fleet.db only**, so no restart is needed. `fleet_cli devices remove` for a pending/retired MAC must delete the pending row (and only mirror to legacy files if it was ever there), and keep printing the caution for the legacy mirror.
- **Setup**: `_enrol` (byos_server.py:401-418): `registry = effective_registry` -> `mac in registry["devices"]` else 403 -> `secret_matches` else 401 -> `issue_token` -> 200 `{"device_token": token}`. `issue_token` writes `fleet_db.set_device_token(conn, mac, token)` for `devices` rows only; returns `None` (=> 503) when no such row (:389-392).
- **Display**: `_handle_display` (byos_server.py:1445-1525): `_authenticate_device` (:952-967, loops all candidate tokens, no early exit) -> `_device_context` (:1027-1052; `row = _fleet_row(..., _row_by_mac(mac))`, `None` => `_NO_DEVICE` => 401) -> telemetry, `save_battery_state(ctx.state_dir)`, read `ctx.image_path`, size check, `_served_image`, `_publish_image(ctx.state_dir, ...)`, `_record_device_report_and_offer`, JSON response. `resolve_hardware_type` (:919-935) resolves only `devices` rows (None for pending => OTA unresolved => no offer).
- **Response fields the firmware actually reads** (firmware/main/api_client.c:592-616): `image_url` (string, URL validator, `fp_url_valid`), `image_hash` (`fp_image_hash_valid`: `sha256:<64 hex>`, < 80 chars), `sleep_s` (number, `fp_sleep_s_parse` accepts exact integers `FP_SLEEP_S_MIN 1` .. `FP_SLEEP_S_MAX 86400` inclusive: firmware/main/validate.h:16-17, validate.c:67-80), `led_enabled` (optional). `firmware`/`reset` are read in a separate block. The key name is **`sleep_s`** (there is no `refresh_rate`).
- **Frame flow**: no token => `fp_api_setup()`; display call; on `FP_ERR_HTTP_AUTH` (401/403) erase token and re-enrol next wake (api_client.c:573-580); hash-skip when `image_hash` equals the NVS copy (state_machine.c:257-263 => no download, no redraw); download verified against the hash and exactly `FP_IMAGE_BYTES = 960000` (api_client.h:28, 104-106); `sleep_s == 0` or failure => backoff 5 min .. 6 h (sleep_decision.c:15-22, backoff.c: base 300 s, cap 6 h). Panel guard spacing `CONFIG_FP_MIN_REFRESH_SPACING_S` default 60 s (Kconfig.projbuild:174-178) < 300 s.
- **X-Img-Fmt**: no occurrence in `firmware/main/*.c`/`*.h` (grep of `X-Img|Img-Fmt|img_fmt` empty). Today's firmware never announces a container, so `_served_image` (byos_server.py:685-696) returns the raw file: a pairing image must be exactly `(1200//2)*1600 = 960000` bytes for the 1200x1600 profile. Container negotiation stays in place for future firmware.

### Real firmware need: **none** for AUTH-04/AUTH-05 (confirmed)

- 300 s and 86400 s are accepted `sleep_s` values; the retired image + 86400 s works with the current firmware and 401-erases do not occur because the token stays valid (D-14).
- Residual battery/ghosting considerations to **report to the owner** (not worked around): (1) a never-claimed frame redraws the panel at every code rotation (about every 35 minutes: 30 min validity, observed at the next 5-minute wake) which is roughly 40 full ~31 s redraws a day; (2) the display shows the code only after the frame's first wake with the server reachable, so there is no on-device "not enrolled" feedback until Phase 57; (3) a frame whose NVS is erased re-enrols with its secret and stays retired/pending.

### Required changes in byos (all additive, freeze-safe)

| Where | Change |
|---|---|
| `fleet_db` | `pending_registry_view(conn)`, `pending_tokens_by_mac(conn)`, `get_pending_by_mac`, `set_pending_token`, `issue_pending_code`, `touch_pending`. **Do not change** `registry_view`/`tokens_by_mac` signatures or behaviour: `test_fleet_db.py:294-307`, `test_fleet_sessions.py:224`, `test_auth_independence.py:69` assert their exact results. |
| `_fleet_view` (:342-366) | Merge the pending views into `registry`/`tokens` (devices and pending MACs are disjoint by construction, see Pitfall 6). |
| `issue_token` (:379-398) | If `set_device_token` finds no devices row, try `set_pending_token`; **do not** write the legacy `state["tokens"]` for a pending MAC. |
| `_device_context` (:1027-1052) | New `PENDING` outcome before `_NO_DEVICE`. |
| `_handle_display` | Early return into `_handle_pending_display` (keep `_handle_display` <= 80 code lines; it is 57 today, `check_function_size report` shows `Handler._handle_display` 57). |
| `Handler.do_GET` (:1398-1411) | New `_PENDING_IMG_PATH_RE = r"\A/img/(p_[0-9a-f]{8})/([0-9a-f]{64})\.bin\Z"` -> `_serve_image_file(<state>/pairing/<pid>/img, digest)`; same unauthenticated, content-addressed model as `/img/<id>/<sha>.bin`. |
| `bearer_ok` (:1337-1357) | Already uses `effective_tokens`; once the view includes pending tokens, `/device/v1/log` accepts a pending frame's logs (acceptable, logs go to stdout only). |

## 3. Rendering and caching the pairing / retired images

### Facts

- Hardware profile: `hardware.get_profile(key, environ)` (server/hardware.py:160-164) gives `width, height, palette, image_format`; production has only `LEGACY_KEY = xiao-ee02-13in3-spectra6` (1200x1600); sim types need `SKYPANE_SIM_HARDWARE=1` (hardware.py:149-157).
- Palette: Spectra 6, six legal indices `IDX_BLACK/WHITE/YELLOW/RED/BLUE/GREEN` and `pf.padded_palette()` (server/panel_format.py:44-77, 83-90). Nibble codes via `INDEX_TO_NIBBLE` (0x4 skipped). `pf.new_canvas` and `pf.pack_panel` are **hard-wired to 1200x1600** (panel_format.py: `new_canvas` uses `WIDTH, HEIGHT`; `pack_panel` asserts `len == WIDTH*HEIGHT`).
- Existing "static screen" precedent: `server/plane/render/hold_screens.py` builds NO CONNECTION, UPDATING, BATTERY EMPTY canvases by one shared composition and documents that constant bytes mean hash-skip ("the image's bytes (and sha256 hash) must stay constant for the whole parked episode, so every hourly byos check-in is a hash-skip, never a redraw", hold_screens.py `_build_battery_empty_canvas`). Fonts: `server/assets/fonts/{Inter,PTSerif,ZillaSlab}*` OFL, vendored (VENDOR.md). Accents (French) are covered by Inter/PT Serif.
- Container: `image_container.encode_container(image, w, h, version=...)` and `negotiate_version(announced)`; the legacy raw form is `ceil(w*h/2)` bytes without the `SPIM` magic (image_container.py docstring).

### Recommendation

- **New module `server/pairing_image.py`** (do not edit `hold_screens.py`/`layout.py`/`style.py`/`panel_format.py`: Phase 56 changes the render package for per-hardware geometry). API: `render_pairing_image(profile, code) -> bytes` and `render_retired_image(profile) -> bytes`, both returning the **raw packed nibble bytes** for `(w//2)*h`. Build with `Image.new("P", (w, h), IDX_WHITE)` + `putpalette(pf.padded_palette())`; pack locally using the public `pf.INDEX_TO_NIBBLE` (a 6-line translate) so non-1200x1600 sim profiles work and `pf.pack_panel` is not touched.
- Layout (flat colours only, **no dithering, no timestamp, no countdown**): heading in PT Serif Bold; the code `XXXX-XXXX` at the largest size that fits `w - 2*margin` (fit with `text.fit_text_size`), black on white with a yellow or blue rule; two instruction lines EN then FR ("Enter this code in the SkyPane console" / "Saisissez ce code dans la console SkyPane"). Safe-area margin 64 px as in `style.SAFE_BOX` for the legacy geometry; scale margins by `min(w, h)/1200` otherwise.
- **Determinism:** the same `(profile, code)` must produce identical bytes across processes. Pillow text rendering is deterministic for a fixed Pillow + font file; add a test that renders twice and a subprocess render and compares sha256. A golden hash of the *retired* image (no secret content) is a good freeze for accidental redraw churn.
- **Cache/storage:** the code is stored only as a salted hash, so the plaintext exists only at issue time: render **at issue time** and write the raw bytes to `<state>/pairing/<pending id>/panel.bin` (mode 0600, `atomic_io.atomic_write`); every later display poll reads that file (no re-render, no code needed) and publishes the served bytes through the existing content-addressed `_publish_image(<state>/pairing/<pid>, digest, served)` which stores `<state>/pairing/<pid>/img/<digest>.bin`. A missing/unreadable `panel.bin` = "no live code": issue a new one. Delete `pairing/<pid>/` on claim (best effort, after COMMIT) and keep it for a retired frame (its retired image is not secret).
- **Backup:** `deploy/backup/skypane_backup.py` reports any top-level state entry not in its include or `KNOWN_EXCLUDED` lists as drift (test: `deploy/tests/test_backup.py::...::test_wal_shm_and_status_file_never_archived_nor_drift` asserts no "not in include list"). Add `"pairing"` to `KNOWN_EXCLUDED` (skypane_backup.py:61-79 region) and extend that test to seed a `pairing/` directory. The pairing dir also contains a short-lived plaintext-in-pixels code; excluding it from backups is a feature.
- **Freeze test impact:** none, provided (a) the live path in `_handle_display` is untouched, (b) `measured_fields_freeze.json` is not edited, (c) no new key is added to the **live** response (`test_display_response_keys_equal_the_freeze_list`, test_phase47_freeze.py around line 194). Pending responses use the same six keys, so a sibling test can assert key equality for the pending branch. Add a test that serving a pending frame writes nothing under the live `img/` and does not modify the live `battery_state.json`.

## 4. fleet.db migration 3, backup and everything that enumerates the schema

### Mechanics (server/fleet_db.py)

- `MIGRATIONS = (_migrate_v1, _migrate_v2)` at :137, `SCHEMA_VERSION = len(MIGRATIONS)` at :138. Append `_migrate_v3`; each step is applied by `migrate_schema` inside `BEGIN IMMEDIATE` together with `PRAGMA user_version = n` and a re-check for concurrent upgraders (:170-194).
- Too-new refusal: `_refuse_if_too_new` (:162-167) is called by `connect` (before touching the journal mode, :212) and `connect_readonly` (:237); byos maps it to `STATUS_FAULT` and falls back to legacy files (byos_server.py:351-353, 988-990). This **is** the rollback caveat of D-21.
- Suggested v3 DDL (names are Claude's discretion):
  - `ALTER TABLE locations ADD COLUMN owner_user_id INTEGER REFERENCES users(id)` (SQLite accepts ADD COLUMN with a REFERENCES clause when the default is NULL, which is the case; existing rows get NULL = "nobody", admin-only).
  - `CREATE TABLE pending_devices (id TEXT PRIMARY KEY CHECK (id GLOB 'p_[0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f]'), mac TEXT NOT NULL UNIQUE, secret_sha256 TEXT NOT NULL, token TEXT, hardware_type TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','retired')), code_salt TEXT, code_hash TEXT, code_expires_at INTEGER, last_seen_at INTEGER, battery_mv INTEGER, fw_version TEXT, created_at TEXT NOT NULL, created_by INTEGER)`.
  - `CREATE TABLE audit_log (id INTEGER PRIMARY KEY, ts INTEGER NOT NULL, actor_user_id INTEGER, actor_label TEXT NOT NULL, action TEXT NOT NULL, target_type TEXT NOT NULL, target_id TEXT, outcome TEXT NOT NULL CHECK (outcome IN ('ok','failed','denied')), source_ip TEXT, detail TEXT)` + `CREATE INDEX audit_log_ts ON audit_log (ts DESC, id DESC)` + two triggers `BEFORE UPDATE`/`BEFORE DELETE` ... `SELECT RAISE(ABORT, 'audit_log is append-only')`. No FK on `actor_user_id` (rows must outlive any future user removal); store a label snapshot.
  - `mac` uniqueness across `devices` **and** `pending_devices` cannot be a SQL constraint; enforce inside the write transaction in `fleet_db.add_device` **and** `register_pending` (central choke point), and in `mirror_to_fleet`/`_apply_mirror` (byos_server.py:452-464, creates a `devices` row from the legacy CLI).
- **Retirement storage (gap in D-21):** D-21 lists three schema changes; retirement needs a place for a frame that has no owner. Recommendation: retire = one transaction that deletes the `devices` row and inserts/updates a `pending_devices` row with `status='retired'` (same MAC, secret hash, token, hardware), wipes the directory, and audits; re-activate = `status='pending'` + `code_*` cleared. This keeps "`devices.owner_user_id` NOT NULL" and needs only the column already in the proposed table. [ASSUMED] — confirm with the owner that the retired frame's history is discarded on retire.
- Pre-existing locations: `owner_user_id IS NULL` = admin-visible, admin-assignable, invisible/unusable for users (D-18). `fleet_migrate._ensure_location` (fleet_migrate.py:256-270) looks up by name and inserts; unaffected as long as `add_location` keeps its signature and `owner_user_id` is an optional trailing parameter.

### Tests and code that enumerate schema or hard-code versions (must be updated)

| File:line | What | Action |
|---|---|---|
| server/test_fleet_db.py:34 | `{"users","locations","devices","meta"} <= tables` | still passes; add new tables to an assertion. |
| server/test_fleet_db.py:408-421 | `test_v1_database_upgrades_in_place_to_v2` asserts `schema_version == 2` twice | change to `SCHEMA_VERSION`/3 and add the v3 objects; keep a v1->v3 and v2->v3 upgrade test. |
| server/test_fleet_db.py:~436-455 | concurrent upgrade test asserts `versions == [2, 2]` | `[SCHEMA_VERSION] * 2`. |
| server/test_fleet_migrate.py:416-436 | `_downgrade_to_v1` drops only `sessions` and sets `user_version=1`; asserts messages `schema 1 -> 2` and `== 2` | After v3 the leftover `pending_devices`/`audit_log` tables make `CREATE TABLE` in `_migrate_v3` fail on re-run. Fix the helper to drop the v3 objects (and rebuild `locations` without the column or make `_migrate_v3` tolerant), update the expected text to `1 -> 3` (fleet_migrate.py:201-203 builds it from `SCHEMA_VERSION`). |
| stub-server/test_fleet_auth.py:170, test_fleet_db.py:458 | use `SCHEMA_VERSION + 1` | fine. |
| deploy/tests/test_backup.py:371-380, 383-412 | `_seed_fleet_db`, restored schema == `SCHEMA_VERSION` | extend `_seed_fleet_db` with a pending row, an audit row and an owned location; assert them after restore (`snapshot_db` uses `sqlite3.backup`, deploy/backup/skypane_backup.py:150-165, which copies every table). |
| stub-server/test_phase47_freeze.py `test_migration_reruns_change_nothing` (:288-300 region), `test_replay_*` | replay across the migration with a legacy-shaped state | pass unchanged if v3 is applied by the same `fleet_migrate`/`connect`; add one assertion that a v3 DB with no pending rows serves the identical frozen response. |
| server/fleet_migrate.py:81, 201-203, 214 | uses `fleet_db.SCHEMA_VERSION` generically | no change; its `_snapshot_from` reads only `devices` secrets/tokens (:218-226): pending rows are not legacy-mirrored, which is correct. |
| `dump_logical` (fleet_db.py:591-593) | `iterdump()` — covers all tables/triggers automatically | used by test_fleet_migrate.py:51 (drops `created_at` statements); a logical-equality test for backup/restore of the new tables can reuse it. |

Backup/restore: `deploy/backup/skypane_backup.py` snapshots `fleet.db` through the SQLite backup API (SNAPSHOT_DBS at :54, `snapshot_db` :150-165), so the three schema changes are included automatically. Sessions are already in the archive (hand-off C). Pending/retired rows hold `secret_sha256`, `token` and a salted code hash: the same sensitivity class as `devices` (token and hash are already in the archive).

Parallel-phase conflict: Phase 52/53 may also want a fleet.db migration (zones, detection mode). **Append-only ordering matters**: reserve index 3 for this phase's `_migrate_v3` and tell the other phases to append v4+. Merge conflict surface is the single `MIGRATIONS` tuple line (fleet_db.py:137) and the tests above.

## 5. Reassign wipe

- A device directory is `<root>/devices/<id>/` (`device_dirs.provision_device_dir`, device_dirs.py:90-114) created with `device_config.json` (`{}`) and `panel.bin` (white). Files it may contain at runtime (backup lists + code): `device_config.json`, `poll_state.json`, `battery_state.json`, `calendar_rules.json`, `calendar_url.secret`, `colour_rules.json`, `manual_resolutions.json`, `airline_name_overrides.json`, `history.db` (+ `-wal`, `-shm`), `gallery/`, `illustration_overrides/`, `img/`, `panel.bin`, `poll.lock`, `theme_previews/`, `frame_previews/` (deploy/backup/skypane_backup.py DEVICE_INCLUDE_FILES/DIRS, companion/theme_preview.py:67,288, poll_cycle.py GALLERY_DIRNAME). There is **no existing wipe function**.
- **Recommendation:** add `device_dirs.wipe_device_dir(root, state_path) -> None`: refuse `LIVE_STATE_PATH` (raise `ValueError`), resolve through `resolve_state_dir` (refuses symlinked/escaping directories), `shutil.rmtree` the directory, then the caller re-runs `provision_device_dir` (fresh `{}` config + white panel). Simpler and safer than enumerating filenames (an enumerated list would silently miss a file a later phase adds). Everything in the directory is per-device state by construction.
- **Live-frame guard (two layers):** the pure function refuses `"."`; the companion handler refuses retire when `state_path == "."` with the generic "not allowed" outcome and an audit row `outcome=denied`; reassigning the live frame calls `assign_owner` only and never the wipe. Test: a live-frame reassign leaves every root file byte-identical (`snapshot_dir` from `test-support/skypane_live_state.py` is the helper the freeze test uses).
- **Concurrency:** take the in-process poll lock `device_scope.poll_lock_for(device.state_dir)` non-blocking (as `_handle_poll_now` does, app.py:1141-1147) and, when it exists, the cross-process `poll_cycle.poll_cycle_lock` before the rmtree; refuse with a "frame busy, retry" flash when busy. byos opens `history.db` per call and closes it (`_record_device_health`, byos_server.py:1061-1077) so a mid-wipe write at worst recreates a stray file that the next provisioning step tolerates (it never overwrites existing files, device_dirs.py:85-88) — wipe, then provision, then **verify `panel.bin` size** before commit.
- **Order of operations for reassign:** transaction { `assign_owner`, `set_device_location(mac, None)`, name reset to NULL, audit } then filesystem wipe+provision, or the reverse with rollback of the directory on failure? Recommended: wipe + provision **inside** the transaction body (like `cmd_devices_add`) so an exception rolls the owner change back; a crash between COMMIT and a late wipe would leave the old owner's data under the new owner, which is the worse failure. [ASSUMED] design choice.
- **Cross-owner location leak:** the previous owner's `location_id` must be cleared on reassign (a user cannot use another user's locations, D-18).

## 6. Companion UI: selector, nav, pages, Health split

### Device selector and owner filtering

- `device_scope.load_devices(root)` (device_scope.py:100-113): live first then others by name/id; built from `_fleet_rows` -> `fleet_db.list_devices` (fleet_db.py:530-539) which **does not select `owner_user_id`**. `Device` is `namedtuple("Device", "id name hardware_type state_path state_dir is_live")` (device_scope.py:30-31); constructed in only two places (device_scope.py:48, 91) plus two tests (`companion/test_device_links.py:298`, `test_device_poll.py:299`). Add `owner_user_id` to `list_devices` and as a **defaulted trailing field** on `Device` (`defaults=(None,)`) so those tests keep compiling.
- `Handler._dispatch_for_device` (device_dispatch.py:21-47) passes `devices = load_devices(root)` to `set_request_scope`; for a user principal filter to `owner_user_id == principal.user_id` there (and never include the synthetic "live" fallback that has no row, `_live_from_row(root, None)` at device_scope.py:46-54, 113). `switch_target` (device_scope.py:304-327) then returns `SWITCH_UNKNOWN` for an unowned id => 404 automatically.
- `device_selector_html` (ui_shell.py:355-387) hides itself with fewer than 2 devices; a one-frame user sees no selector (fine).
- **Live-frame prefix landmine:** `current_prefix()` returns "" for the live device (device_scope.py:223-228), `target_path` un-prefixes it (:254-259), and `_switch_device` maps `"live"` (:295-301). D-13 allows a user to own the live frame; their URLs must be `/devices/<id>/...` because the un-prefixed form is admin-only. Make the prefix rule principal-aware (`prefs.current_principal()` role `user` => always prefix with the real `d_` id), and use the real id (not the literal `"live"`) in user selector values. Existing admin behaviour must not change (Phase 51 `TestPrefixCrawl` in companion/test_device_routes.py).
- `Handler._referring_tab` returns `access.home_for(principal)` for a user (device_dispatch.py:64-65): after a user's POST (settings, quick toggle, airline actions) they would be thrown to `/account`. Change to the referer-derived device page for users (validated by `routes.DEVICE_PREFIX_RE` and membership in the user's allowed pages).

### Nav and page registration

- Routes: `companion/routes.py` `_GET_ROUTES`/`_POST_ROUTES` tuples (:139-272), then `ROUTES` derived with `device_scoped` from `_DEVICE_SCOPED_KEYS` (:309-314). New console routes are global (not device-scoped).
- Page titles/scripts: `Handler._page_shell_for` uses `_PAGE_TITLES = dict(layout.NAV_TABS)` (app.py:268, 897-902) and `_PAGE_SCRIPTS[route]` (app.py:285-328); `companion/test_page_scripts.py` fails if a `NAV_TABS` route has no scripts entry. **Do not add console pages to `NAV_TABS`**: `NAV_TABS` also drives `_validated_next_route` (app.py:346-353), `device_scope.page_routes` (device_scope.py:287-292) and `_referring_tab` (device_dispatch.py:71). Give the console its own table (e.g. `layout.CONSOLE_NAV`) and a `_page_shell_for` branch that accepts a title/scripts for console routes.
- Admin nav renderers: `ui_nav.sidebar_nav` (ui_nav.py:184-241), `_tab_bar_html` (:386-448), `_mobile_nav_html` (:551...). Users: `USER_NAV` (ui_nav.py:51-57) = Account only; `_user_sidebar_nav` (:157-181); `_tab_bar_html` returns "" for users (:387); `ui_shell.py:454` also special-cases users. The reduced view needs a user nav that lists the current device's Home/Display/Flights/Airlines/Health (device-scoped hrefs via `device_scope.scoped`) plus Account, and a user tab bar (or sidebar-only with a documented decision). Admin nav needs a Console group (Fleet, Users, Locations, Audit log, Releases).
- Account page: `account_page.render(identity, ui_theme)` (pages/account_page.py:66-87) is "pure markup with no data"; its docstring promises it carries no frame data. Replace the empty state with a list of the user's own frames (name, status online/offline/never-seen from `device_scope.device_status`, links to Home/Display) fed from the owner-filtered list, and keep `home_for(principal)` -> `/account` for users (sign_in.py:184-187 and the matrix assume this; changing it touches `test_account_page.py`/`test_sign_in_surfaces.py`). Recommended: keep `/account` as the user landing.
- i18n: auto-discovery (`companion/i18n_fr/__init__.py` merges every sibling module's `MESSAGES` via `pkgutil`); add `i18n_fr/console.py`. Every new literal is `i18n.msg("area.slug", "English")`; duplicate ids with different English raise at import.

### Which existing pages/sections need role-conditional content (the reduced view)

| Page | Admin | User (D-16/D-17) | Where it is built |
|---|---|---|---|
| Home `/` | as today incl. "Refresh now" (poll trigger on Home) | hide the poll trigger and any hardware/OTA detail | pages/home_page.py (poll trigger section also in `config_page.poll_trigger_section`, config_page.py:675) |
| Display `/display` | all `EVERYDAY_GROUPS` = theme, calendar, runway, quiet hours (screens.py:21-22) | theme (look), calendar, quiet hours (+ time zone, display on/off); **no runway group** | config_page `_display_groups_html` (:446-459), `scope_groups` (:296-312) |
| Device `/device` | wake interval, LED, poll, hardware | **admin only** (keep `Access(ADMIN)`) | config_page `SCOPE_DEVICE` |
| Flights `/flights` | as today | as today (own device's history) | history_page |
| Airlines `/airlines` | as today | as today (names/resolution; D-16 keeps it) | airlines_page |
| Health `/health` | frame + platform | frame only (below) | health_page.render (:1055-1121) |
| Update `/update` | admin | none (stays `ADMIN_ONLY`, global) | update_page |
| Nav Health dot | `_health_alert_for_admin` (app.py:765-776) | frame-only severity | health_signals.overall_severity (:369-396) |

### Where Health mixes frame and platform (D-17)

`health_page.render` (health_page.py:1055-1121): `screen_rows = _connection_row + _battery_row` (frame) and `server_rows = _flight_data_row + _sources_row + _identification_row + _backup_row` (platform) in two `group_html` groups; also `_source_fault_block(state["source_fault_raw"])` (:744), the anomaly banner built from `collect_anomalies` (health_signals.py:335-366) which mixes frame anomalies (check-in stale, battery dropped) with platform ones (flight data stale, sources disagreed, all sources failed, off-box backup, fleet database unavailable), and the unresolved-airline registry/resolve dialog (`_registry_section`, `_resolve_dialog_html`). The nav-dot severity `overall_severity` (health_signals.py:369-396) also folds `source_fault`, `pipeline_state`, `disagreement_warn`, `offbox_state`, `fleet_fault` in. Home also uses `pipeline_state` in `_needs_attention` (home_page.py:645-660).

**Recommendation (minimal diff, Phase 56 conflict-aware):** add a single `platform: bool = True` parameter to `health_page.render` and gate the `server_rows` group, `_source_fault_block`, the registry section and the platform anomalies behind it; compute the user's anomalies and severity by calling `collect_anomalies`/`overall_severity` with `pipeline_state="ok"`, `disagreement_warn=False`, `source_fault=False`, `offbox_state="ok"`, `fleet_fault=False` (a `companion/user_view.py` helper), and use that severity for the user's nav dot and for Home's attention row. The freshness ETag for Health is computed from the same state (`freshness._page_freshness_token`): for a user compute it from frame-only inputs so a platform change cannot toggle their page (low risk, a hash only, but it causes spurious refreshes).

## 7. Locations and parallel-phase conflicts

### Current schema and usage

- `locations(id, name, latitude CHECK -90..90, longitude CHECK -180..180, timezone)` at fleet_db.py:94-101; `devices.location_id REFERENCES locations(id)` (:110). API: `add_location(conn, name, lat, lon, timezone)` with validation (name non-empty, ranges, `ZoneInfo(timezone)`) (:405-429), `list_locations` (:432-433), `set_device_location(conn, mac, location_id)` (:567-573). `list_devices` joins the location name (:530-539).
- **Nothing in `companion/` reads locations**; the only consumers are `server/fleet_migrate.py:228,256-270,319` (creates the "Orly" location) and `stub-server/fleet_cli.py:133-149,228-241` (add/list/set-location). Phase 52/53 will read lat/lon/timezone for zones and detection.

### Phase 55 design

- `owner_user_id` NULL = admin-only legacy rows. Admin: all locations; user: `WHERE owner_user_id = ?`.
- New functions (all typed, in `fleet_db.py`): `add_location(..., owner_user_id=None)` (keep positional compatibility), `list_locations_for(conn, user_id|None)`, `update_location`, `delete_location_if_unused` (refuse when a device references it), `set_device_location_checked(conn, device_id, location_id, actor)` enforcing "device owner == location owner or admin (NULL owner)". A user may only assign a location they own to a device they own; an admin may assign any.
- **Quota/validation/rate limit (research items, recommendations [ASSUMED]):** per-user cap 10 locations (reject the 11th with a flash, no audit row for a quota reject beyond one `denied`), name <= 80 chars stripped of control characters, latitude/longitude parsed with `float()` and `math.isfinite`, range-checked, **rounded to 4 decimals on store** (about 11 m; Phase 53 requires rounding anyway for third parties), time zone through `ZoneInfo`, France bounds enforced later by Phase 53 (not here), create/edit/delete rate limit via a second `LoginThrottle` instance keyed by user id (e.g. 20 mutations per 10 minutes). Deleting a location in use is refused. Audit every location change (D-19).
- Risk: user-supplied coordinates are later sent to third parties (Phase 53). This phase must store only; a note in the hand-off that rounding/bounds belong to 53.

### Likely file overlap with Phases 52 and 56 (avoid these)

| Phase | Likely files | Phase 55 rule |
|---|---|---|
| 52 (fleet poll, zones, 1 req/s budget) | `server/poll_cycle.py`, `server/poll_loop.py`, `server/plane/detect.py`, `server/state_store.py`, `server/http_fetch.py`, `companion/app.py::_handle_poll_now` (app.py:1129-1182), possibly a `fleet_db` migration (zones) and `locations` readers | Do not touch these; in `app.py` only add the audit calls/CSRF/dispatch edits in **other** functions; reserve `MIGRATIONS[2]`. |
| 53 (detection modes) | `adsb-test/*`, `server/plane/runway_config.py`, config pages for runway/position selection (`companion/settings/runway_led.py`, `config_page.py` runway group), `fleet_db` device columns | Phase 55 only *hides* the runway group for users via a role flag; no edits inside `runway_led.py`. |
| 56 (per-hardware render, battery, health, credits) | `server/plane/render/*`, `server/panel_format.py`, `server/hardware.py`, `server/device_policy.py`, `companion/pages/health_page.py`, `companion/health_signals.py`, `companion/pages/home_page.py`, `companion/battery*.py`, a credits page + `i18n_fr` | Keep the `health_page.render` change to one parameter plus a `user_view.py` helper; put pairing drawing in a **new** module; do not edit `panel_format.py`/`hardware.py`. Expect a trivial merge in `health_page.py` and `routes.py`. |

Shared hot files all three phases and this one will touch: `companion/routes.py` (route tuples), `companion/app.py` (route-adjacent handlers), `companion/test_access_matrix.py` (rows), `server/fleet_db.py` (migrations). Keep edits to those as append-only blocks to minimise conflicts.

## 8. Test infrastructure to reuse and run times

- **Fixtures:** `companion/conftest.py` (`app_server`, `make_app_server(seed=..., env_overrides=...)`, `module_app_server_factory`); `test-support/companion_app_server.py` (`AppServer` subprocess, `InProcessAppServer(state_dir)` at :457 with `apply_env`, `http_request`, `login`, `login_via_auth0`, `auth0_env`, `session_cookie_for_state_dir(state_dir, email, role)` at :162); `test-support/fake_auth0.py` (`FakeAuth0`); the matrix `rig` fixture (test_access_matrix.py:284-304) is the model for a module-scoped two-user, provisioned-fleet rig.
- **Browser tests:** `companion/test_browser_*.py` (557 tests carry `-m browser`; `server/.venv` has playwright; the sandbox needs the chromium 1248/1243 symlink workaround noted in 54-HANDOFF D.4; CI is unaffected and a missing browser fails CI). Reuse `browser_login` (companion_app_server.py:202) and `test_browser_ux_helpers.py`.
- **BYOS tests:** `test-support/skypane_frame_server.py` (`FrameServer`), `skypane_two_device_fleet.py`, `skypane_live_state.py` (`seed_live_like_state`, `snapshot_dir`), `stub-server/test_device_fleet.py` and `test_image_negotiation.py` as patterns for enrol + display + container assertions.
- **Guards that will run on new code:** comment-history (`scripts/check_comment_history.py check`, no plan/decision IDs in comments); function-size (80 code lines over `server stub-server`); mypy (`pyproject.toml` `files` + strict overrides: add `server/pairing_code.py`; add `server/pairing_image.py` only if fully annotated); ruff; `companion/test_suite_guards.py` (behaviour-over-source: no test may read source text or `.planning/`); `companion/test_i18n.py` (every Message has French; no bare string literals).
- **How to run a relevant subset fast** (measured here, 4 cores): `server/.venv/bin/python3 -m pytest companion/test_access_matrix.py -n 4 --no-cov -p no:cacheprovider` -> 852 tests in 4.8 s. A schema/byos/backup/matrix slice (`server/test_fleet_db.py server/test_fleet_migrate.py stub-server/test_phase47_freeze.py stub-server/test_fleet_cli.py stub-server/test_fleet_auth.py deploy/tests/test_backup.py companion/test_access.py companion/test_device_routes.py`) -> 332 tests in 8.8 s. Full suite: 6254 tests collected (12 s to collect), `./scripts/run-all-tests.sh`; with extra pytest args it disables the coverage gate (`--cov-fail-under=0`). Lint/type/size: `server/.venv/bin/ruff check .`, `server/.venv/bin/mypy`, `server/.venv/bin/python scripts/check_function_size.py check --max 80 server stub-server`, `server/.venv/bin/python scripts/check_comment_history.py check`.

## 9. Pairing code security

- **Alphabet (decision needed, D-09 is arithmetically inconsistent):** Crockford base32 is `0123456789ABCDEFGHJKMNPQRSTVWXYZ` (32 symbols; it already excludes I, L, O, U). D-09 also excludes `0` and `1`, which leaves **30 symbols** (`23456789ABCDEFGHJKMNPQRSTVWXYZ`), not 32. 30^8 = 6.56e11, about 39.3 bits (32^8 would be 40 bits). Recommended: the 30-symbol display alphabet generated with `secrets.choice`; entropy is still ample for a 30-minute, throttled, admin-only, audited code. [ASSUMED] that the owner's intent is "Crockford minus 0/1" — confirm.
- **Normalisation** (input): strip whitespace and `-`, uppercase (case-insensitive), apply Crockford look-alike folding (`O`->`0`, `I`/`L`->`1`) and reject any character outside the alphabet (since `0`/`1` never appear in issued codes a folded `0`/`1` fails like any wrong code), require length 8, then hash.
- **Hash:** `sha256(salt || code)` with a per-row random salt (`secrets.token_hex(8)`), stored hex; compare by iterating **all** pending rows with `hmac.compare_digest` and no early exit; when there are no rows perform one dummy hash+compare so timing does not reveal emptiness. A plain unsalted sha256 of a 39-bit secret is brute-forceable offline from a database copy within the validity window... mitigated by 30-minute expiry, but the salt prevents precomputed tables. Do not use `==`.
- **Store:** `code_salt`, `code_hash`, `code_expires_at` (integer epoch seconds, matches the sessions convention in fleet_db.py:120-135); **never** the plaintext, never in logs, audit detail, flash messages or exception text. The plaintext exists only in the byos request that issues it (then only as pixels).
- **Throttle (reuse `LoginThrottle`):** two process-global instances in the companion (single process, `ThreadingHTTPServer`): per-session `LoginThrottle(limit=5, lockout_s=300)` keyed by `sha256(session token)[:16]` (never the token); global `LoginThrottle(limit=20, lockout_s=900)` with a constant key and **no `record_success`** (a success must not reset the global counter; `record_success` zeroes the entry, auth.py:271-276). Locked out => 429 with remaining seconds, no code evaluation at all. State is in memory (restart resets, as for login; acceptable, state it in the hand-off). Audit once per lockout transition, not per rejected request.
- **Failed attempts audited without the guess:** action `pairing.claim`, outcome `failed`, `detail` limited to a coarse reason enum (`invalid`, `throttled`), target empty. Wrong/expired/already-claimed answer one identical page and status (D-11); a claim by a non-admin is a 404 like every admin route.
- **Audit fields:** `ts` (epoch), `actor_user_id` (nullable: legacy admin and frames have none), `actor_label` (email, `legacy-admin`, or `frame:<p_id>`), `action` (dotted enum, e.g. `frame.register`, `pairing.issue`, `pairing.claim`, `device.reassign`, `device.retire`, `device.reactivate`, `user.invite`, `user.role`, `user.disable`, `user.enable`, `user.unlink`, `location.add|update|delete`, `release.install|cancel`), `target_type` (`device|pending|user|location|release`), `target_id` (id, never MAC secrets/tokens; MAC is acceptable on admin-only pages but prefer the `p_`/`d_` id), `outcome`, `source_ip` (via `auth.client_ip(self.client_address[0], XFF)`; byos events store NULL or a copy of that helper because byos cannot import `companion/`), `detail` (bounded JSON of non-secret facts such as old/new role or owner email). Written in the **same transaction** as the action.
- **Code lifecycle summary:** issue at the pending frame's display poll when absent or expired (30 min, 1800 s); after claim the pending row and `pairing/<pid>/` are gone; after retire/re-activate `code_*` cleared and a fresh code issued at the next wake; the displayed code outlives a 300 s wake by construction.

## CSRF (D-20) design

- **Token:** `csrf = hex(sha256(b"csrf-v1:" + raw_session_cookie_token))` computed in `companion/auth.py` next to `hash_session_token` (auth.py:76-78). The database stores only `sha256(token)` (sessions table, fleet_db.py:123-133), so a database leak does not yield tokens; the cookie is HttpOnly (auth.py:105-117), so page script cannot read it, but the server can embed the derived token in forms. The legacy-admin session uses the same cookie, so it works unchanged. Compare with `hmac.compare_digest`.
- **Embedding:** a single `ui_components.csrf_field()` returning `<input type="hidden" name="csrf_token" value="...">` for the new forms. There are about 33 POST forms across 14 files (grep above: ui_nav, login_page, settings/*, ui_components, pages/*). Do **not** retrofit them all in this phase unless the owner asks (open question); the scope of D-20 is "admin and pairing POSTs", and existing user-facing routes keep SameSite=Strict + Origin checks. Release actions (`/update/install`, `/update/cancel`, forms at pages/update_page.py:309, 343, 588 and the confirm page) are **admin** destructive-ish actions and D-19 audits them, so they should get tokens too (small, self-contained change).
- **Enforcement:** a defaulted `Route.csrf: bool = False` (trailing field so `stub_routes`' positional constructor still works), set on every new POST route; `_dispatch` verifies `form["csrf_token"]` after ALLOW and answers the existing `_forbidden_page` (403). The fetch-based quick switch (static/quick-switch.js) is unaffected (not in scope).
- Origin/Sec-Fetch-Site checks stay (`auth.post_origin_ok`, auth.py:302-337).

## Common Pitfalls

### Pitfall 1: `Access(USER, "device")` 404s admins on un-prefixed pages
**What goes wrong:** every admin page 404s. **Why:** see Pattern 1 (`captured` is `None`/the path middle, not the device id). **Avoid:** `_effective_access` per route form; test every `(route form x principal)` cell. **Warning sign:** `test_http_outcome_matches_the_policy_table` admin/legacy-admin cells failing for `/`.

### Pitfall 2: A user POST to `/devices/<id>/settings` changes admin-only settings
**What goes wrong:** forged `wake_interval_s`, `led_enabled`, `tracked_runway`, `scope=all` take effect. **Why:** `config_page.handle_post` (config_page.py:845-908) resolves every group's field whatever the scope (`resolve_wake_interval(form, errors)`, `resolve_led`, `resolve_runway` take no scope; `submitted_scope` accepts `all`, config_page.py:316-326). **Avoid:** in `_handle_settings_post` (app.py:1072-1120), when the principal is a user, drop `wake_interval_s`, `led_enabled`, `tracked_runway` and force `scope=display` before `handle_post`; the render side hides the controls. Test with a crafted POST asserting `device_config.json` fields unchanged. Same check for `/quick/led` (stays `ADMIN_ONLY`) and `/poll-now`.

### Pitfall 3: Live frame owned by a user gets un-prefixed links
See Section 6; `device_scope.current_prefix` must emit `/devices/<id>` for user principals, else every link 404s (un-prefixed = admin-only).

### Pitfall 4: BYOS writes legacy files for pending tokens / companion writes legacy files
See Anti-Patterns; plus `byos_server._apply_mirror` (:452-464) creates a `devices` row from a legacy CLI add with `META_BOOTSTRAP_OWNER`: it must refuse (or adopt) a MAC already present in `pending_devices`.

### Pitfall 5: Pairing images evict the live frame's images / get backed up
Use `<state>/pairing/<pid>/` only; add `pairing` to `KNOWN_EXCLUDED`; never `_publish_image(root, ...)` for a pending frame.

### Pitfall 6: A MAC in both `devices` and `pending_devices`
SQL cannot enforce it across tables. Enforce inside the same write transaction in `add_device`, `register_pending`, `_apply_mirror`, and claim (delete pending first). `registry_view` merge must not silently prefer one.

### Pitfall 7: Hash churn
Any per-request variance (time, random dither) in the pairing image changes the hash and forces a redraw every 5 minutes. The `_served_image` container wrapper is deterministic (crc over a fixed payload). Render once at issue.

### Pitfall 8: Frame-only severity leaks platform state
The nav dot, Home attention row, Health banner and freshness token all derive from `health_signals`. Gate all four for users or platform info leaks through the dot/toast even if the rows are hidden (matrix test asserts a user's page bodies contain none of the platform strings).

### Pitfall 9: Last-admin / self-disable races
Do the count and the update in one `fleet_db.transaction`; count only `role='admin' AND disabled=0`; the legacy-admin principal has no `users` row and does not count as an admin for the guard. Disabling must also `delete_sessions_for_user` (as `fleet_cli._set_disabled`, fleet_cli.py:97-107) and "unlink identity" is `fleet_sessions.unlink_identity` (fleet_sessions.py:185). `fleet_db` has **no role setter** today (`get_user_role` only, :392-399): add `set_user_role`.

### Pitfall 10: Claim response differences leak validity
Wrong, expired, already-claimed, throttled-after-lockout must be indistinguishable in body and status except the explicit 429 lockout notice, and must not vary in timing (compare all rows).

### Pitfall 11: Newly claimed frames stay white until polled
A claimed non-live device gets `provision_device_dir`'s white `panel.bin`; the fleet poll arrives only with Phase 52, and users have no "poll now" (D-16). Today only an admin's `POST /devices/<id>/poll-now` (admin-only, supported for 1200x1600 hardware via `device_scope.poll_supported`) can render it. Surface to the owner in the hand-off; do not give users poll-now.

## Code Examples

### Pending lookup and constant-time code match (shape)
```python
# Source: pattern from byos_server._authenticate_device (no early exit) and fleet_db.transaction
import hashlib, hmac

def match_pending(conn, presented_code_hash_inputs, now):
    """Return the pending row whose salted hash matches, else None. Scans every row."""
    matched = None
    rows = conn.execute(
        "SELECT * FROM pending_devices WHERE status = 'pending' AND code_hash IS NOT NULL"
    ).fetchall()
    for row in rows:
        candidate = hashlib.sha256((row["code_salt"] + presented_code_hash_inputs).encode()).hexdigest()
        ok = hmac.compare_digest(candidate, row["code_hash"])
        if ok and row["code_expires_at"] > now and matched is None:
            matched = row
    if not rows:                                   # keep timing uniform when nothing is pending
        hmac.compare_digest("0" * 64, "0" * 64)
    return matched
```

### Claim transaction (shape)
```python
# Source: fleet_db.transaction (fleet_db.py:286-295) + fleet_cli.cmd_devices_add (fleet_cli.py:170-192)
created_dir = None
try:
    with fleet_db.transaction(conn):
        row = match_pending(conn, normalised_code, now)
        if row is None:
            raise ClaimRefused()                      # identical answer for every refusal
        conn.execute("DELETE FROM pending_devices WHERE id = ?", (row["id"],))
        new_id = fleet_db.add_device(
            conn, row["mac"], row["secret_sha256"], row["hardware_type"], owner_id,
            token=row["token"], state_path="auto")
        created_dir = device_dirs.provision_device_dir(root, new_id, profile.width, profile.height)
        audit.append(conn, actor, "pairing.claim", "device", new_id, "ok", source_ip)
except BaseException:
    if created_dir is not None:
        shutil.rmtree(created_dir, ignore_errors=True)
    raise
```

### Frame-only severity (shape)
```python
# Source: companion/health_signals.overall_severity (health_signals.py:369-396)
severity = health_signals.overall_severity(
    signals["device_state"], "ok", signals["battery_state"], False,
    source_fault=False, offbox_state="ok", fleet_fault=False)
```

### Pending display response (shape)
```python
# Source: byos_server._handle_display response (byos_server.py:1497-1525), same six keys
{"image_url": "%s://%s/img/%s/%s.bin" % (scheme, host, pending_id, digest),
 "image_hash": "sha256:" + digest,
 "sleep_s": 300,            # 86400 for a retired frame (FP_SLEEP_S_MAX is inclusive)
 "firmware": None, "reset": False, "led_enabled": True}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| All device routes admin-only | Owner-gated device routes with 404 on foreign devices | Phase 51/54 groundwork, completed here | The matrix is the proof; each route needs a row. |
| Shared-password session derived from the password | Opaque server-side session token, only its hash stored | Phase 54 | CSRF can be derived from the token without a schema change. |
| Single registry (`devices.json`) | fleet.db identity source with legacy mirror | Phase 48 | Pending frames exist only in fleet.db (no legacy mirror). |
| Raw legacy image only | Versioned container on `X-Img-Fmt` announcement | Phase 50 | Pending/retired responses reuse `_served_image`; current firmware gets raw. |

**Deprecated/outdated:** none relevant. `legacy-admin` stays (D-04).

## Runtime State Inventory

(Not a rename/refactor phase; one reassign/retire data-lifecycle inventory instead.)

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | `devices/<id>/` per-device files (config, history.db, poll/battery state, gallery, calendar secret) | wipe via `device_dirs.wipe_device_dir` on reassign/retire (never for `"."`) |
| Live service config | none outside fleet.db | none |
| OS-registered state | none new (no new units/timers) | none |
| Secrets/env vars | none new; `SKYPANE_COMPANION_*` unchanged; no Auth0 secret in repo | none |
| Build artifacts | `<state>/pairing/<pid>/` (new, regenerable, not backed up) | add to backup `KNOWN_EXCLUDED` |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Retirement is stored as `pending_devices.status='retired'` and the retired frame's history is discarded on retire | 4 | If the owner wants history kept, retire must keep the directory and use a `devices.retired_at` column instead (still schema 3). |
| A2 | Owner's intended alphabet is Crockford minus `0`/`1` (30 symbols, ~39.3 bits) | 9 | If 32 symbols are wanted, 0/1/O/I/L cannot all be excluded; changes the code shape. |
| A3 | CSRF scope = new admin/pairing POSTs plus `/update/install` and `/update/cancel`; existing user routes keep SameSite + Origin only | CSRF | If all ~33 forms are wanted, a central form-injection or per-form edit across 14 files is needed. |
| A4 | Reassign wipe + provision run inside the transaction body (rollback on failure) | 5 | Alternative ordering risks old-owner data under the new owner after a crash. |
| A5 | User landing stays `/account` (frame list), not an auto-redirect to the frame's Home | 6 | Changes `home_for` and several sign-in/account tests. |
| A6 | Location quota 10/user, 4-decimal rounding on store, mutation rate limit 20/10 min | 7 | Policy numbers are not verified against any requirement. |
| A7 | Pairing events written by byos store a NULL `source_ip` (byos cannot import `companion/auth.py`) | 9 | Audit rows for "pairing issued" lack an IP; could copy the XFF rule into `server/`. |
| A8 | User Health hides the unresolved-airline registry (it is on the Airlines page) | 6 | If the owner wants it on user Health, keep the registry section for users. |
| A9 | Unclaimed-frame redraw cadence (about every 35 min) is acceptable until Phase 57 | 2 | Alternative: after N expiries serve a static "not paired" image at 24 h (deviates from D-10). |

## Open Questions

1. **D-09 alphabet (30 vs 32 symbols).** What we know: the Crockford alphabet excludes I/L/O/U; excluding 0/1 too leaves 30 symbols. Unclear: whether the owner meant exactly that. Recommendation: confirm and use the 30-symbol display alphabet.
2. **Where does a retired frame live in the schema?** D-21 names three changes. Recommendation: `pending_devices.status`, as above; needs one-line owner confirmation (A1).
3. **CSRF scope.** Recommendation: new admin/pairing POSTs + release actions; retrofitting all forms is a separate decision (A3).
4. **Newly claimed frame shows white until polled** (Pitfall 11): acceptable for this phase, or should the console expose admin "poll now" prominently after claim? Recommendation: link to the existing admin poll-now; report to owner.
5. **Unpaired-frame redraw cost.** Report to the owner (see Section 2); no firmware work here.
6. **Migration index.** Confirm Phase 52/53 append v4+ (Section 4).

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python venv `server/.venv` | all tests | yes | 3.13 (prod 3.14) | — |
| pytest + xdist + cov, playwright, ruff, mypy | CI parity | yes (in venv) | locked | — |
| Chromium headless shell | `-m browser` tests | partly (sandbox: 1243 installed vs 1248 expected; local symlink workaround in 54-HANDOFF D.4) | — | CI has the right browser; run non-browser subset locally |
| Pillow + vendored fonts | pairing image | yes | locked | — |
| Network (Auth0, ADS-B) | none needed | blocked by pytest-socket by design | — | fake Auth0 |
| `docker`/`espressif/idf` | firmware build | not needed (no firmware change) | — | — |

**Missing dependencies with no fallback:** none.
**Missing dependencies with fallback:** browser version mismatch only (sandbox).

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9 (`minversion 9.0`) + xdist + cov; pytest-socket loopback-only guard; pytest-playwright for `-m browser` |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` (importlib mode, `pythonpath = [".", "test-support"]`, `testpaths = server stub-server companion test-support deploy hardware`) |
| Quick run command | `server/.venv/bin/python3 -m pytest <files> -n 4 --no-cov -p no:cacheprovider` |
| Full suite command | `./scripts/run-all-tests.sh` (coverage floor 93, `--cov-fail-under=0` when extra args are given) |

### Phase Requirements -> Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| AUTH-04 | Code alphabet/normalisation/hash/constant-time verify; deterministic issue | unit | `pytest server/test_pairing_code.py -x` | Wave 0 |
| AUTH-04 | Pairing + retired image: size `(w//2)*h`, palette indices only, deterministic across processes, golden hash for retired | unit | `pytest server/test_pairing_image.py -x` | Wave 0 |
| AUTH-04 | Migration 3: v1->v3, v2->v3, idempotent, concurrent upgraders, triggers make `audit_log` append-only, owner column default NULL | unit | `pytest server/test_fleet_db.py -x` | extend (update 3 hard-coded `2`s) |
| AUTH-04 | Atomic claim: single winner under two threads; wrong/expired/claimed identical; row moved to `devices` with token; audit row; dir provisioned; rollback removes dir | unit/integration | `pytest server/test_pairing_claim.py -x` | Wave 0 |
| AUTH-04 | Throttle per session and global; lockout 429; failed attempts audited without the guess (assert no guess in table) | HTTP | `pytest companion/test_pairing_claim_http.py -x` | Wave 0 |
| AUTH-04 | BYOS: pending enrol (setup) issues token in pending row only; display returns pairing image, `sleep_s` 300, six keys, `firmware` null; hash stable until expiry then changes; claimed frame next poll gets its own device image; never writes live `img/` or `battery_state.json`; legacy files untouched | integration (subprocess) | `pytest stub-server/test_pending_pairing.py -x` | Wave 0 |
| AUTH-04 | Retired: 86400 s, retired image, token still valid, re-activate -> pending + new code; live frame retire refused | integration | `pytest stub-server/test_pending_pairing.py companion/test_console_retire.py -x` | Wave 0 |
| AUTH-04 | Freeze: live response/keys unchanged, migration rerun no-op with schema 3 | integration | `pytest stub-server/test_phase47_freeze.py -x` | exists (must stay green) |
| AUTH-04 | Backup/restore carries pending, audit, location owner; `pairing/` excluded without drift | integration | `pytest deploy/tests/test_backup.py -x` | extend |
| AUTH-04 | CLI verbs register-pending/retire/reactivate/pending list, fleet.db only (no legacy write) | integration | `pytest stub-server/test_fleet_cli.py -x` | extend |
| AUTH-05 | Matrix: new owner-device policy, un-prefixed = admin only, new console rows, locations ownership, probe canary kept | HTTP (stubbed) | `pytest companion/test_access_matrix.py -n 4 -x` | extend |
| AUTH-05 | Real-handler layer: owner 200 / other 404 identical to unknown / admin 200 for pages and images; user cannot change wake/LED/runway via crafted POST | HTTP (real) | `pytest companion/test_user_view_http.py -x` | Wave 0 |
| AUTH-05 | Selector/prefix: user sees only own frames; live frame owned by a user uses `/devices/<id>` links; `?device=` of a foreign id 404 | HTTP | `pytest companion/test_device_selector.py companion/test_device_routes.py -x` | extend |
| AUTH-05 | Health split: user page has no ADS-B/airline-source/backup/fleet strings, frame-only dot/anomalies; admin unchanged | HTTP | `pytest companion/test_user_health.py -x` | Wave 0 |
| AUTH-05 | Users page: invite, role change, disable (sessions deleted), enable, unlink; last-admin and self-disable refused under concurrency | HTTP + unit | `pytest companion/test_console_users.py server/test_fleet_users.py -x` | Wave 0 |
| AUTH-05 | Fleet/Audit pages: every device incl. pending/retired with owner, hardware, last seen, battery, firmware; audit newest first, read-only (no POST route) | HTTP | `pytest companion/test_console_pages.py -x` | Wave 0 |
| AUTH-05 | Reassign wipe: previous owner's files gone, token/MAC/secret kept, location cleared, live frame only owner changes and files byte-identical | integration | `pytest server/test_device_dirs.py companion/test_console_reassign.py -x` | extend + Wave 0 |
| AUTH-05 | Locations: user CRUD limited to own rows, quota, validation, device assignment cross-owner refused, admin sees all incl. NULL-owner | HTTP + unit | `pytest companion/test_locations.py server/test_fleet_locations.py -x` | Wave 0 |
| D-20 | CSRF: missing/wrong token 403 and handler not run; valid token OK; anonymous still sign-in redirect; token differs per session | HTTP | `pytest companion/test_csrf.py -x` | Wave 0 |
| AUTH-05 | Browser: console pages and user view render at 360 px, 44 px targets, theme switch, French strings | browser | `pytest companion/test_browser_console.py -m browser` | Wave 0 |
| both | i18n completeness, comment-history, ruff, mypy, function-size | guard | `pytest companion/test_i18n.py companion/test_suite_guards.py` + the four CI commands | exists |

### Sampling Rate
- **Per task commit:** the touched test file(s) with `-n 4 --no-cov` (seconds), plus `companion/test_access_matrix.py` whenever `routes.py` or `access.py` change.
- **Per wave merge:** the 332-test slice above plus `companion/` non-browser tests (`-m "not browser"`).
- **Phase gate:** full `./scripts/run-all-tests.sh` green (with browser), ruff, mypy, function-size, comment-history, `scripts/check-attribution.sh` before `/gsd:verify-work`.

### Wave 0 Gaps
- [ ] `server/test_pairing_code.py`, `server/test_pairing_image.py`, `server/test_pairing_claim.py`
- [ ] `stub-server/test_pending_pairing.py` (use `FrameServer` + a hand-seeded fleet.db, no real code in the repo: generate codes at test time)
- [ ] `companion/test_user_view_http.py`, `test_user_health.py`, `test_console_users.py`, `test_console_pages.py`, `test_console_reassign.py`, `test_console_retire.py`, `test_locations.py`, `test_csrf.py`, `test_pairing_claim_http.py`, `test_browser_console.py`
- [ ] Shared fixture: a `provisioned_fleet` helper in `test-support/access_matrix_support.py` (or a new support module) that calls `device_dirs.provision_device_dir` for seeded devices
- [ ] Update the hard-coded schema-version tests listed in Section 4
- Framework install: none.

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes (pairing code is a bearer credential; frames keep MAC+secret) | single-use salted-hash code, 30 min expiry, throttle (`LoginThrottle`), constant-time compare; frame auth unchanged |
| V3 Session Management | yes | existing server-side sessions; CSRF derived from the session token; disabling a user deletes sessions |
| V4 Access Control | yes (core of the phase) | default-deny route table, owner gate `access.authorized_device_id`, 404 on denial, matrix test, server-side stripping of admin-only fields |
| V5 Input Validation | yes | MAC/sha256 regex in `fleet_db`, device/pending id regexes, location validation (`ZoneInfo`, finite ranges), email normalisation, 8 KiB form cap |
| V6 Cryptography | yes (limited) | `secrets`, `hashlib.sha256`, `hmac.compare_digest`; never hand-roll |
| V7 Logging/Audit | yes | append-only `audit_log`, no secrets/codes/guesses; companion logs method+path only (`log_message`, app.py:1373-1378) |
| V13 API | yes | BYOS pending branch has the same auth model as the live path; content-addressed unauthenticated image routes unchanged |

### Known Threat Patterns for stdlib HTTP + SQLite fleet

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Pairing-code brute force | Spoofing | 30-symbol x 8, 30 min, single use, per-session + global throttle, admin-only claim, audit |
| Code timing / existence oracle | Information disclosure | scan all rows with `compare_digest`, identical responses, dummy compare when empty |
| IDOR on `/devices/<id>/...` | Elevation / Info disclosure | owner gate + identical 404 body for foreign/unknown (matrix asserts equal bodies) |
| Mass assignment via crafted settings POST | Tampering | strip admin-only fields server-side for user principals |
| CSRF on destructive admin POST | Tampering | derived per-session token + Origin/Sec-Fetch-Site |
| Last-admin lockout / self-disable | Denial of service | in-transaction guard |
| Path traversal via stored state path or `/img/<id>/` | Tampering | `device_dirs.resolve_state_dir`, strict id regexes (`p_[0-9a-f]{8}`), content-addressed names |
| Pairing image / retire as battery drain | DoS (device) | deterministic image (hash-skip), 300 s / 86400 s cadences |
| Audit tampering | Repudiation | triggers abort UPDATE/DELETE; no purge route |
| SSRF via user-supplied calendar URL | Tampering / SSRF | existing `server/net/safe_fetch` gate is already used by `calendar_rules` (calendar_rules/__init__.py:227,439); opening Calendar to users makes it reachable by non-admins: keep and test it (a user URL to loopback/private is rejected) |

## Risks / Landmines

1. **Opening routes before reducing content.** If `Access(USER,"device")` lands before the render/POST stripping, a user who owns a device (possible today via `fleet_cli devices assign`) reaches the wake-interval/LED/runway controls. Land the access change and the reduction in the same plan, or keep routes `ADMIN_ONLY` until both exist (Pitfall 2).
2. **Matrix semantics change.** Three existing assertions encode the old shape (test_access_matrix.py:201-209, 237-245, 266-271). Expect to rewrite them, not just add rows.
3. **Un-prefixed = live frame.** The un-prefixed form must remain admin-only; a user must never reach `devices[0]` (device_dispatch.py:30-32).
4. **Live frame ownership by a user** breaks prefix assumptions in `scoped()`, selector values (`"live"`), `_referring_tab`, redirects after POST.
5. **`registry_view`/`tokens_by_mac` are public test surface.** Add pending-specific functions instead of changing them.
6. **BYOS never-writes-legacy rule** for pending tokens; companion never writes `devices.json`/`byos_state.json`.
7. **Pairing images outside `img/` and outside the backup include list**, else live images are evicted or the backup job reports drift.
8. **`_handle_display` size budget:** 57 of 80 lines used; extract the pending branch.
9. **Freeze list is owner-only:** do not edit `measured_fields_freeze.json`; do not add constants to `device_policy` (frozen `wake_constants`); live response keys unchanged.
10. **Schema 3 rollback caveat** (previous release's byos refuses schema 3, falls back to legacy files, Health shows a fleet fault). Also **frames claimed after the upgrade have no legacy token**, so on rollback they fail 401 and (firmware erases the token and re-enrols with its secret, which the legacy registry also lacks => 403 => backoff up to 6 h). Surface both in the hand-off.
11. **Hard-coded schema version tests** (`== 2`, `[2, 2]`, `_downgrade_to_v1` leaving v3 tables) will fail; update them in the same plan as migration 3.
12. **`LoginThrottle` is per-process and in-memory** (companion restart resets, auth.py:223-226): state it; `record_success` resets a key, so do not call it on the global throttle.
13. **CSRF in `_dispatch` needs the form cached** (read once from `rfile`); multipart upload routes are not urlencoded.
14. **i18n/guards:** every new literal needs `i18n.msg` + French; no plan/decision IDs in comments; behaviour-over-source tests only.
15. **Phase 52/56 merge hotspots** (`routes.py`, `app.py`, `health_page.py`, `fleet_db.py` `MIGRATIONS`): keep edits append-only and small.
16. **Retired frame + hard delete:** `fleet_cli devices remove` must also remove pending/retired rows and the `pairing/<pid>` dir; `devices.json` mirror only if present.
17. **Unpaired frame cost:** about 40 redraws/day per never-claimed frame (report, no firmware work).
18. **Claimed frame stays white until polled** (fleet poll is Phase 52; users have no poll-now).
19. **User calendar connect** exposes the server-side fetch to non-admins: verify the SSRF gate and per-device poll lock behaviour under user traffic; consider rate-limiting calendar connects per user.
20. **Production safety:** no deploy; no real pairing code or Auth0 secret in tests/fixtures (generate at test time); pytest-socket allows only loopback.

## Recommended plan shape (for the planner; waves are Claude's discretion)

- **Wave 1** — 55-01: hand-off section A: matrix machinery (owner-device policy kind, un-prefixed admin-only table, real-handler layer with provisioned dirs), `_effective_access`, `Device.owner_user_id`, principal-aware prefix, owner-filtered selector, server-side field stripping and role-conditional Display/Home/Health/nav/Account, `Route.csrf` field. Routes flip to `USER/device` only here, together with the reductions. 55-02: schema 3 + `fleet_db` API (pending, audit, locations, `set_user_role`, last-admin guard) + hard-coded-version test updates + backup test/`KNOWN_EXCLUDED`.
- **Wave 2** — 55-03: `pairing_code` + `pairing_image` (pure, mypy-listed, deterministic tests). 55-04: BYOS pending path, `/img/p_…` route, `issue_token`, `_fleet_view` merge, freeze-safety tests, CLI verbs. 55-05: CSRF helper + audit helper + throttles.
- **Wave 3** — 55-06: console actions (register, claim with throttle, retire/re-activate, reassign with wipe, users, locations, release audit) + matrix rows for each route. 55-07: Fleet / Users / Audit / Locations pages, console nav, French strings.
- **Wave 4** — 55-08: user-facing Locations, Account frame list, browser tests, hand-off doc (rollback caveat, redraw cost, white-until-polled, alphabet decision, CSRF scope).

## Sources

### Primary (HIGH confidence — repository, read 2026-10-30)
- companion/routes.py, access.py, app.py (:452-1008, 1072-1363), auth.py, device_dispatch.py, device_scope.py, sign_in.py, ui_nav.py, ui_shell.py, layout/ui_base (NAV_GROUPS), page_context.py, pages/{account,health,config,home}_page.py, health_signals.py, screens.py, post_actions.py
- companion/test_access_matrix.py, test-support/access_matrix_support.py, companion_app_server.py, fake_auth0.py, companion/conftest.py
- server/fleet_db.py, fleet_sessions.py, fleet_migrate.py, device_dirs.py, hardware.py, panel_format.py, image_container.py, plane/render/hold_screens.py, assets/fonts/VENDOR.md
- stub-server/byos_server.py, fleet_cli.py, devices_cli.py (caution text), measured_fields_freeze.json, test_phase47_freeze.py
- firmware/main/{api_client.c, validate.c/h, state_machine.c, sleep_decision.c, backoff.c, panel_guard.h, Kconfig.projbuild} (read only, not modified)
- deploy/backup/skypane_backup.py, deploy/tests/test_backup.py
- pyproject.toml, scripts/run-all-tests.sh, check_function_size.py, check_comment_history.py
- .planning/workstreams/v1-2/{REQUIREMENTS,STATE,ROADMAP}.md, phases/54-*/54-HANDOFF.md, phases/51-*/51-DEVICE-SCOPED-ROUTES.md
- Measured here: matrix suite 852 tests / 4.8 s (4 workers); schema+byos+backup+matrix slice 332 tests / 8.8 s; 6254 tests collected in total (557 browser).

### Secondary / Tertiary
- None (no web research performed by design; the task was code-only).

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new dependencies; everything reuses read-and-verified modules.
- Architecture: HIGH for seams and conflicts (file:line verified); MEDIUM for the retirement storage, CSRF scope and location policy numbers (flagged `[ASSUMED]`).
- Pitfalls: HIGH — each traced to specific code.
- Firmware: HIGH — field names, ranges and absence of `X-Img-Fmt` read directly from `firmware/main`; no firmware change needed.

**Research date:** 2026-10-30
**Valid until:** the next merge touching `companion/routes.py`, `fleet_db.py` or `byos_server.py` (about 7 days given three parallel phases); re-run the file:line checks before planning if phases 52/56 land first.
