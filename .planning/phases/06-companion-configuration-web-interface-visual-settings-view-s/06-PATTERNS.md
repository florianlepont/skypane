# Phase 6: Companion Configuration Web Interface - Pattern Map

**Mapped:** 2026-08-27
**Files analyzed:** 15 (new) + 6 (modified)
**Analogs found:** 15 / 15 (every new file has a directly-precedented in-repo analog; RESEARCH.md's own code sketches are the load-bearing spec, cross-referenced against real analog files here)

RESEARCH.md already contains concrete, repo-grounded code sketches for nearly every new file in `companion/` (Architecture Patterns 1-7, plus the session-cookie sketch). This document does not re-derive those — it maps each planned file to the **real existing file** it should copy conventions from, and pulls the exact excerpts the planner needs, since RESEARCH.md's sketches were themselves written by reading these same files.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `companion/app.py` | controller (HTTP server entrypoint) | request-response | `stub-server/byos_server.py` | exact (RESEARCH.md Recommended Project Structure explicitly says "mirrors byos_server.py's shape") |
| `companion/auth.py` | middleware (session/auth) | request-response | `stub-server/byos_server.py` (`bearer_ok`, `secrets.token_hex(32)` pattern) | role-match |
| `companion/history_db.py` | service/model (SQLite persistence) | CRUD + batch (Caddy log tail) | `server/poll_loop.py` (`load_poll_state`/`save_poll_state`, atomic-write discipline) | role-match |
| `companion/panel_preview.py` | utility (transform) | transform | `server/panel_format.py` (`pack_panel`, the function it reverses) | exact |
| `companion/pages/config_page.py` | component (HTML page builder) | request-response | `server/plane/render.py` (`STATE_BACKGROUND`, palette-legality pattern) + `stub-server/byos_server.py` (`send_json`/response-building shape) | role-match |
| `companion/pages/health_page.py` | component (HTML page builder) | request-response | `server/plane/detect.py` (`corroborated` field producer) | role-match |
| `companion/pages/airlines_page.py` | component (HTML page builder) | request-response | `server/plane/enrich.py` (`unresolved_prefixes` registry) | role-match |
| `companion/pages/history_page.py` | component (HTML page builder) | request-response | `companion/history_db.py` (sibling, same phase) | role-match |
| `companion/test_companion_app.py` | test | request-response | `stub-server/test_poll_cycle.py` | exact |
| `companion/test_panel_preview.py` | test | transform | `server/test_render.py` (round-trip style tests) | role-match |
| `deploy/skypane-companion.service` | config (systemd unit) | — | `deploy/skypane-byos.service` | exact |
| `deploy/Caddyfile` (modified: new site block + `log output file` on existing block) | config | — | itself (existing `203-0-113-10.nip.io` block) | exact |
| `deploy/provision.sh` (modified: enable new unit, ufw deny new port) | config | — | itself (existing `skypane-byos.service`/ufw-deny-8642 lines) | exact |
| `deploy/skypane.env.example` (modified: add `SKYPANE_COMPANION_*` vars) | config | — | itself (existing `SKYPANE_BYOS_SECRET` entry) | exact |
| `server/poll_loop.py` (modified: history.db writes, gallery retention, `device_config.json` read, `tracked_runway` passthrough) | service (existing, extended) | CRUD + file-I/O | itself (`load_poll_state`/`save_poll_state`/`write_panel_atomic`) | exact — extend in place |
| `server/plane/detect.py` (modified: `RUNWAY_CONFIGS`/`select_aircraft_for_runway()`, back-compat wrapper) | service (existing, extended) | transform | itself (`runway_axis`/`corridor_params`/`select_runway3_aircraft`) | exact — extend in place |
| `server/plane/render.py` (modified: theme-aware `STATE_BACKGROUND`, runway-aware `TOP_RIGHT_TAG_TEXT`) | service (existing, extended) | transform | itself | exact — extend in place |
| `adsb-test/runway3.json` (modified: `runway`/`corridor` flat shape -> `runways` dict keyed by id) | config/fixture | — | itself | exact — extend in place |

## Pattern Assignments

### `companion/app.py` (controller, request-response)

**Analog:** `stub-server/byos_server.py`

**Imports pattern** (lines 35-41):
```python
import argparse
import hashlib
import json
import os
import secrets
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
```
Copy this shape exactly — stdlib only, no framework. `companion/app.py` additionally needs `sys.path` bootstrap identical to `server/poll_loop.py`'s (lines 31-38) to import `server.poll_loop`/`server.plane.detect` for CFG-07's direct `run_once()` call.

**Response-building pattern** (lines 65-83):
```python
class Handler(BaseHTTPRequestHandler):
    server_version = "flightportrait-byos-example"
    args = None
    state = None

    def send_json(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def read_body_json(self):
        try:
            n = int(self.headers.get("Content-Length", "0"))
            return json.loads(self.rfile.read(n).decode())
        except (ValueError, UnicodeDecodeError):
            return None
```
`companion/app.py`'s `Handler` should follow this exact class-attribute-as-shared-config idiom (`args`, `state` set on the class before `serve_forever()`), and add a `send_html(code, html_str)` sibling to `send_json` for the page routes (Content-Type `text/html; charset=utf-8`).

**Auth pattern** (lines 85-88, generalize):
```python
def bearer_ok(self):
    auth = self.headers.get("Authorization", "")
    return (auth.startswith("Bearer ") and
            auth[7:] in self.state["tokens"].values())
```
`companion/auth.py`'s cookie check plays the same structural role — a boolean gate method called at the top of every `do_GET`/`do_POST` branch, exactly like every branch in `byos_server.py`'s `do_GET`/`do_POST` calls `bearer_ok()` first (lines 133, 154 no-auth for `/img/`, 117 for `/device/v1/log`).

**Routing dispatch pattern** (lines 100-129, 131-165):
```python
def do_POST(self):
    if self.path == "/device/v1/setup":
        ...
        return self.send_json(200, {"device_token": token})
    if self.path == "/device/v1/log":
        if not self.bearer_ok():
            return self.send_json(401, {"detail": "unknown token"})
        ...
    return self.send_json(404, {"detail": "unknown endpoint"})
```
Copy this flat `if self.path == "/x":` dispatch table verbatim in style for `companion/app.py`'s `do_GET`/`do_POST` (RESEARCH.md's Don't Hand-Roll table explicitly calls this out — no framework router needed for 6 routes).

**Entrypoint / server bring-up pattern** (lines 171-204):
```python
def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--port", type=int, default=8642)
    ...
    args = ap.parse_args()
    ...
    Handler.args = args
    Handler.state = load_state(args.state_dir)
    server = ThreadingHTTPServer(("0.0.0.0", args.port), Handler)
    print("serving %s on port %d ..." % (...))
    server.serve_forever()

if __name__ == "__main__":
    main()
```
`companion/app.py` copies this shape with its own port default (a new loopback-only port, e.g. 8643) and binds `0.0.0.0` the same way — loopback restriction is enforced at the firewall/Caddy layer (ufw deny), not in the app, exactly matching `deploy/skypane-byos.service`'s own comment (lines 6-9) about this being "a known vendored behaviour... enforced at the firewall/reverse-proxy layer instead of in the app." Apply the same discipline to the new service rather than special-casing it.

---

### `companion/auth.py` (middleware, request-response)

**Analog:** `stub-server/byos_server.py`'s token-issuance pattern (lines 108, 39)

**Secret-token generation pattern**:
```python
import secrets
token = secrets.token_hex(32)
```
D-01 explicitly says the companion password should be "stored the same way the existing device bearer token is" — `deploy/skypane.env.example`'s `SKYPANE_BYOS_SECRET=replace-with-a-long-random-secret` (line 18, generated via `openssl rand -hex 32` per its own comment) is the template `SKYPANE_COMPANION_PASSWORD` must follow in the new `.env.example` entry.

**Full session-cookie implementation** — already fully sketched and ready to copy verbatim from RESEARCH.md lines 516-547 (`issue_session_cookie`/`verify_session_cookie`/`password_ok`, using `hmac.compare_digest`, `hashlib.sha256`, `secrets`-adjacent stdlib only). No further analog search needed — this sketch is the pattern.

---

### `companion/history_db.py` (service/model, CRUD + batch)

**Analog:** `server/poll_loop.py`'s state-persistence functions (lines 82-115)

**Atomic-write pattern to copy for any JSON side-file** (`device_config.json`):
```python
def _poll_state_path(state_dir):
    return os.path.join(state_dir, "poll_state.json")

def load_poll_state(state_dir):
    """Missing, unreadable, or malformed -> empty state (D-P2-02), never a
    crash.
    """
    try:
        with open(_poll_state_path(state_dir)) as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}

def save_poll_state(state_dir, state):
    """Atomic tmp-write-then-os.replace(), matching
    stub-server/byos_server.py's save_state() (T-02-01-03 / V12). Never
    leaves a stray .tmp file behind, even if the write itself fails.
    """
    path = _poll_state_path(state_dir)
    tmp = path + ".tmp"
    try:
        with open(tmp, "w") as fh:
            json.dump(state, fh, indent=1)
        os.replace(tmp, path)
    except Exception:
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass
        raise
```
`companion/history_db.py`'s (or a small `device_config.py`) `load_device_config()`/`save_device_config()` for the theme/runway settings must copy this exact "missing/malformed -> empty dict, never crash" + tmp-write-then-`os.replace()` shape — this is the established, twice-precedented (`byos_server.py`, `poll_loop.py`) idiom for every JSON side-file in this codebase, and Pitfall 5 explicitly warns against reusing `poll_state.json` itself for this (two-writer race), so it must be a **separate** file following the **same** pattern.

**SQLite schema/write pattern** — already fully sketched, ready to copy, in RESEARCH.md Pattern 2 (lines 260-289: `_history_db()`, `CREATE TABLE IF NOT EXISTS runway_events`, `PRAGMA journal_mode=WAL`, `PRAGMA busy_timeout=5000`, insert-only-on-state-change). This is the load-bearing SQLite pattern; no separate analog exists elsewhere in the repo (this is genuinely new infrastructure) but its *shape* (module-level path helper + explicit `PRAGMA`s) mirrors `poll_loop.py`'s own `_poll_state_path()` helper convention.

**Caddy log-tail pattern** — RESEARCH.md Pattern 6 (lines 363-401), copy verbatim as the starting sketch; verify the exact `request.headers.X-Battery-Mv` JSON path against one real captured log line before trusting it (Assumption A3).

---

### `companion/panel_preview.py` (utility, transform)

**Analog:** `server/panel_format.py`'s `pack_panel()` (lines 104-121) — `unpack_panel()` is its direct mathematical inverse.

**Pack pattern to invert**:
```python
def pack_panel(canvas):
    px = list(canvas.getdata())
    out = bytearray(ROW_BYTES * HEIGHT)
    for row in range(HEIGHT):
        base = row * WIDTH
        obase = row * ROW_BYTES
        for col in range(0, WIDTH, 2):
            left = INDEX_TO_NIBBLE[px[base + col]]
            right = INDEX_TO_NIBBLE[px[base + col + 1]]
            out[obase + col // 2] = (left << 4) | right
    assert len(out) == IMAGE_BYTES
    return bytes(out)
```
`companion/panel_preview.py`'s `unpack_panel()` must use `INDEX_TO_NIBBLE`'s inverted dict (`{v: k for k, v in pf.INDEX_TO_NIBBLE.items()}`) so the two functions can never silently drift — RESEARCH.md's Pattern 4 (lines 316-341) already contains the full 15-line inverse implementation, ready to copy. Use `panel_format.padded_palette()` (lines 81-88) for the Pillow "P"-mode canvas exactly as `new_canvas()` does (lines 91-101).

**Test pattern (round-trip):** `server/test_render.py` — read for its existing canvas-construction/assertion idiom before writing `companion/test_panel_preview.py`'s `pack_panel()` -> `unpack_panel()` round-trip assertion.

---

### `companion/pages/config_page.py`, `health_page.py`, `airlines_page.py`, `history_page.py` (components, request-response)

**Analog for palette/theme legality:** `server/panel_format.py`'s `IDX_BLUE`/`IDX_GREEN`/`PALETTE_RGB` constants (lines 71-76, 55-62) — `config_page.py`'s `THEMES` dict must only reference these named indices, never bare integers, matching `panel_format.py`'s own stated discipline ("no drawing code in render.py ever writes a bare integer palette index," line 69-70). RESEARCH.md Pattern 1 (lines 245-258) has the ready-to-copy single-entry placeholder dict.

**Analog for read-only registry display (`airlines_page.py`):** `server/plane/enrich.py`'s `unresolved_prefixes` registry (referenced at line 722; `trim_unresolved_prefixes()` at line 793) — read `poll_state.json["unresolved_prefixes"]` directly via `poll_loop.load_poll_state()`, never re-derive or duplicate `enrich.py`'s logic (D-16: read-only, zero new computation).

**Analog for corroboration display (`health_page.py`):** `server/plane/detect.py`'s `corroborated` field, produced in `poll_current_aircraft()` (line 486) — expose the existing computed value verbatim, per D-15.

**Escaping pattern (applies to all four page modules):** No direct in-repo analog exists (this is the first HTML-templating code in the project) — RESEARCH.md's Pitfall 2 mandates a single `_html(text)` helper wrapping stdlib `html.escape()`, called at every interpolation site for ADS-B/adsbdb-sourced strings (airline names, callsigns, unresolved prefixes). Treat this helper as shared infrastructure — define it once (e.g. in `companion/app.py` or a small `companion/htmlutil.py`) and import it into every `pages/*.py` module; do not reimplement per-file.

---

### `companion/test_companion_app.py` (test, request-response)

**Analog:** `stub-server/test_poll_cycle.py`

Read this file directly before writing the new harness — RESEARCH.md's Validation Architecture section (lines 605-641) already specifies: subprocess-launch `companion/app.py` on a free local port, drive it with `urllib.request`, mirror `test_poll_cycle.py`'s exact `EXPECTED_CHECK_COUNT` convention, exit 0 only on full pass. No pytest — this project's whole test suite is stdlib-only, directly-executable `test_*.py` scripts (confirmed by `server/README.md` and `scripts/run-all-tests.sh`'s `HARNESSES` array pattern).

---

### `server/poll_loop.py` (modified — extend in place)

**Analog:** itself — `write_panel_atomic()` (line 118 onward, see file for full body) is the call site the new gallery-retention hook (RESEARCH.md Pattern 5, lines 348-361) attaches after. `load_poll_state`/`save_poll_state` (lines 86-116) is the pattern the new `history.db` write path (Pattern 2) and `device_config.json` read path must follow structurally, though `history.db` itself is SQLite, not JSON.

---

### `server/plane/detect.py` (modified — extend in place)

**Analog:** itself — `runway_axis()` (lines 162-205) and `corridor_params()` (lines 208-228) are the exact two functions CFG-12 generalizes. Current signatures:
```python
def runway_axis(geofence):
    runway = geofence.get("runway")
    ...

def corridor_params(geofence):
    block = geofence.get("corridor")
    ...
```
RESEARCH.md Pattern 7 (lines 403-436) already sketches the `runway_id=DEFAULT_RUNWAY_ID` parameterization plus the `select_runway3_aircraft()` back-compat wrapper — note `corridor_params()`'s existing "malformed config falls back to module defaults, never raises" discipline (its own docstring, lines 210-212) must be preserved and extended to "unrecognized `runway_id` falls back to default, never raises" per RESEARCH.md's Security Domain table (CFG-12 threat row).

---

## Shared Patterns

### Stdlib-only HTTP serving
**Source:** `stub-server/byos_server.py` (whole file; docstring line 4: "Stdlib only")
**Apply to:** `companion/app.py`, `companion/auth.py`
Zero new pip packages for the primary recommendation — `http.server.ThreadingHTTPServer` + hand-rolled `if self.path == ...` dispatch, exactly as this file already does in production.

### Atomic JSON side-file persistence
**Source:** `server/poll_loop.py` lines 86-116 (`load_poll_state`/`save_poll_state`), `stub-server/byos_server.py` lines 50-62 (`load_state`/`save_state`)
**Apply to:** `companion/history_db.py`'s `device_config.json` read/write path
tmp-write-then-`os.replace()`, malformed/missing -> empty dict never a crash. Twice-precedented in this codebase; a third file must follow the exact same shape.

### Secrets discipline
**Source:** `deploy/skypane.env.example` (whole file), `deploy/skypane-byos.service` line 17 (`EnvironmentFile=/opt/skypane/skypane.env`)
**Apply to:** New `SKYPANE_COMPANION_PASSWORD` / `SKYPANE_COMPANION_PORT` entries in `deploy/skypane.env.example`, read via `EnvironmentFile=` in the new `deploy/skypane-companion.service` — never a python-dotenv or other loader library (already explicitly rejected by 02-RESEARCH.md per this file's own comment, line 10-11).

### systemd unit + firewall discipline
**Source:** `deploy/skypane-byos.service` (whole file), `deploy/provision.sh` lines 76-79 (unit install), 100-109 (ufw)
**Apply to:** New `deploy/skypane-companion.service`
```
[Service]
Type=simple
User=skypane
Group=skypane
EnvironmentFile=/opt/skypane/skypane.env
WorkingDirectory=/opt/skypane
ExecStart=/opt/skypane/venv/bin/python3 /opt/skypane/companion/app.py --port ${SKYPANE_COMPANION_PORT} --state-dir ${SKYPANE_STATE_DIR}
Restart=always
RestartSec=5
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/skypane/state
```
And in `provision.sh`: add `install -m 644 "${HERE}/skypane-companion.service" ...`, `systemctl enable skypane-companion.service`, and `ufw deny <companion-port>/tcp` alongside the existing `ufw deny 8642/tcp` (line 108) — same "explicit deny in addition to default-deny" discipline, same comment style.

### Reverse-proxy + TLS site block
**Source:** `deploy/Caddyfile` (whole file, 44 lines)
**Apply to:** New site block for `config-<vps-ip>.nip.io` (D-05)
```
config-203-0-113-10.nip.io {
    reverse_proxy 127.0.0.1:<companion-port>
    log {
        output stdout
        format json
    }
}
```
Plus modify the *existing* `203-0-113-10.nip.io` block's `log` directive per RESEARCH.md Pattern 6 (durable `output file` instead of `output stdout`, with `roll_size`/`roll_keep`) — this is a real, targeted edit to the existing block, not just an addition.

### Vendored-code and read-only-integration discipline
**Source:** `stub-server/VENDOR.md`, `deploy/README.md`'s "Known vendored behaviour" section, `deploy/skypane-byos.service` lines 4-9
**Apply to:** Every companion-service integration point that touches `byos_server.py`'s territory (battery telemetry) — never edit `stub-server/byos_server.py`; solve limitations at the infrastructure layer (Caddy log tail), exactly as the existing loopback-binding limitation is already solved at the firewall/reverse-proxy layer rather than patched in the app.

## No Analog Found

None — every new file in this phase has a directly-precedented existing analog in the repo (the project's small, consistent 3-phase-old stdlib-only pattern set covers HTTP serving, JSON persistence, systemd units, Caddy config, and palette/wire-format transforms). The one genuinely novel piece of infrastructure — SQLite persistence (`history.db`) — has no in-repo precedent to copy from, but RESEARCH.md Pattern 2 already supplies a complete, ready-to-use sketch grounded in stdlib `sqlite3` and this repo's own atomic-write conventions.

## Metadata

**Analog search scope:** `stub-server/`, `server/`, `server/plane/`, `deploy/` (entire directories read or grepped)
**Files scanned:** `stub-server/byos_server.py`, `deploy/Caddyfile`, `deploy/skypane-byos.service`, `deploy/skypane.env.example`, `deploy/provision.sh`, `server/poll_loop.py`, `server/panel_format.py`, `server/plane/detect.py` (targeted sections), `server/plane/enrich.py` (grep only)
**Pattern extraction date:** 2026-08-27
