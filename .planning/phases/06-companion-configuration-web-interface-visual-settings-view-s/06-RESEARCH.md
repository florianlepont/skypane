# Phase 6: Companion Configuration Web Interface - Research

**Researched:** 2026-08-27
**Domain:** Small internal admin/config web service (Python stdlib HTTP), SQLite time-series persistence, geofence-corridor generalization for a second/third runway
**Confidence:** MEDIUM-HIGH (stack/architecture grounded directly in this repo's own code; CFG-12's numeric thresholds for the two new runways are explicitly LOW/unverified — see Assumptions Log)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Access is gated by a single shared password (not per-user accounts, not IP restriction). Stored the same way the existing device bearer token is (a gitignored environment file, extending `deploy/skypane.env.example`'s pattern) — never committed, never logged.
- **D-02:** The password protects the entire site uniformly — including read-only views (CFG-03/04/06/11), not just state-changing actions (CFG-01/07/12).
- Session mechanism (cookie duration, rate-limiting failed attempts) is **Claude's Discretion**.
- **D-03:** A new, separate service — its own process/systemd unit — not folded into `poll_loop.py`, never modifying vendored `stub-server/byos_server.py`.
- **D-04:** The project's real VPS provider is **OVH**, not Hetzner — `.claude/CLAUDE.md`'s Hetzner recommendation is stale; treat OVH as ground truth per `deploy/README.md`.
- **D-05:** Exposed via a separate nip.io subdomain (e.g. `config-<vps-ip>.nip.io`), not a path prefix on the device-protocol hostname. New Caddy site block, reverse-proxying to a new loopback port, ufw-denied from outside — same discipline as the existing `byos_server.py` deployment. Framework choice (stdlib vs. Flask/FastAPI) is **Claude's Discretion**.
- **D-06:** A setting changed on the web page takes effect on the **device's next regularly-scheduled poll** — never an early-wake/push mechanism (preserves MSG-01's poll-only security model).
- **D-07:** After saving a setting, show an explicit confirmation ("Saved — will apply on the frame's next scheduled refresh").
- **D-08:** CFG-02 (view switching) is OUT of this phase — moved back to v2 Requirements.
- **D-09:** The panel's colors are **not yet calibrated on real glass** — Phase 7 (not yet run) is where that happens. Do not assume any panel color is real-glass-validated before Phase 7 completes.
- **D-10:** CFG-01's background-color configurability is scoped to a **theme picker among a small set of DEPARTING/ARRIVING color variants validated on real glass** — not a free-form picker, not simply exposing the current (screen-only-confirmed) D-21 pair as the sole option.
- **D-11:** CFG-01's real multi-theme list cannot be finalized until Phase 7 (which runs after this phase) delivers it. **Left to planning to resolve explicitly** — e.g. ship the picker mechanism now against a placeholder/single-option list (the current D-21 pair), with the real list arriving as a small follow-up once Phase 7 completes, OR defer CFG-01's implementation task until after Phase 7. Research's recommendation: ship the mechanism now against a single-option placeholder (see Architecture Patterns, Pattern 1) — see Open Questions.
- **D-12:** CFG-03 shows history/trend, not just a current snapshot.
- **D-13:** Retention is unbounded, kept forever (estimated "~1-2MB/year" at a **15-minute** cadence assumption — see Assumptions Log A4, this research found the real current cadence is 30s, not 15min). UI shows recent weeks by default, not full history, for readability only.
- **D-14:** The page must visually flag anomalies (stale last-poll, abnormal battery drop), not just show raw numbers.
- **D-15:** Also surface the ADS-B cross-source `corroborated` status (already computed by `detect.py`) — zero new computation, just expose it.
- **New persistence needed:** `poll_state.json` has no per-poll history and does not persist battery voltage or per-poll timestamps — this phase needs new, separate persistence, not touching `poll_state.json`'s existing shape.
- **D-16:** CFG-04 is read-only display of the existing `unresolved_prefixes` registry — no in-page actions.
- **D-17 (CFG-07):** Manual poll trigger needs a short cooldown (tens of seconds) after use, to protect the free adsb.fi/adsb.lol APIs from accidental repeated triggering — not a hard abuse rate-limit.
- **D-18 (CFG-06):** Flight-history log of recently-detected flights, retention/format left to planning.
- **D-19 (CFG-08):** Airline/route resolution statistics over time, beyond CFG-04's raw list — metrics/visualization left to planning, likely derived from the same new history persistence D-15 needs.
- **D-20 (CFG-10/11):** Both grounded in `server/plane/render.py`'s existing `--preview`/`--state`/`--callsign` CLI capability — but see this research's finding under "Particularly Important #5": CFG-10 (what's *currently displaying*) and CFG-11 (gallery) are NOT simple wrappers of that CLI capability; see Architecture Patterns Pattern 4/5.
- **D-26/D-27/D-28 (CFG-12):** Select which of Orly's three runways to track (runway 3, 06/24, 02/20) — one at a time, global setting, applies on the device's next scheduled poll. The corridor/track-alignment geometry for 06/24 and 02/20 already exists in the codebase for *exclusion* purposes and must be repurposed for *positive tracking*, not derived from scratch. Does not rewrite PLANE-01/02/03's already-complete requirement text; CFG-12 generalizes the underlying detection logic.
- **D-21 (visual tone):** Plain utility tool, not "ambient art" — deliberately less visual investment than the physical frame.
- **D-22:** Must be responsive on mobile — basic adaptation only.
- **D-23:** UI copy is in English.
- **D-24:** Simple "SkyPane" title/header, no logo.
- **D-25:** Multiple pages/tabs (e.g. Config / Health / Airlines / History), not one long scroll. Exact grouping left to planning.

### Claude's Discretion

- Web framework choice (stdlib vs. Flask/FastAPI) for the new service.
- Session/cookie mechanism (D-01/D-02) — duration, failed-attempt handling.
- New persistence format for poll/battery history and flight log (D-12/D-15/D-18/D-19) — file-based (JSON/SQLite) vs. something else; exact schema.
- Exact page/tab grouping (D-25) and per-page layout.
- Exact metrics/visualization for CFG-08.
- Whether CFG-01's theme picker ships now against a placeholder or waits for Phase 7 (D-11).

### Deferred Ideas (OUT OF SCOPE)

- Simulate a flight/state for preview (typing a callsign or forcing a state) — proposed alongside CFG-10/CFG-11, not selected.
- Webhook/notification integration — explicitly not proposed (would reintroduce a phone dependency for an ambient device, contradicting CFG-03's own rationale).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CFG-01 | Theme picker (DEPARTING/ARRIVING color variants validated on real glass) | Pattern 1 (placeholder-now approach), `panel_format.PALETTE_RGB` as the legality constraint, `device_config.json` persistence |
| CFG-03 | Health status + trend (last poll, battery, corroboration) | Pattern 2/6 (SQLite `device_health`/`runway_events` tables, Caddy log tail for battery since `byos_server.py` is off-limits) |
| CFG-04 | Read-only unresolved-prefix registry display | Direct read of `poll_state.json["unresolved_prefixes"]` — zero new computation |
| CFG-05 | Fault icon pointing to CFG-03 during a real ADS-B outage | Out of this research's deep-dive (already a locked seed design); note only that `poll_current_aircraft()`'s disagreement/failure paths are the trigger signal, already logged |
| CFG-06 | Flight-history log | `runway_events` SQLite table (Pattern 2) |
| CFG-07 | Manual poll trigger, rate-limited | Direct `import server.poll_loop; poll_loop.run_once(...)` call (Pattern 3) + global (not per-session) cooldown gate (Pitfall 8) |
| CFG-08 | Resolution statistics over time | `runway_events.route_source` aggregation query (Pattern 2) |
| CFG-09 | Dark/light theme for the page itself | Pure CSS (`prefers-color-scheme` + a manual toggle persisted client-side or in the session) — no server-side research needed |
| CFG-10 | Live preview of what the panel currently displays | New `unpack_panel()` (reverse of `panel_format.pack_panel()`) reading the live-served `panel.bin` directly — NOT `render.py --preview` (Pattern 4) |
| CFG-11 | Gallery of recently rendered images | New retention hook in `poll_loop.py` (`state/gallery/`), triggered on `panel_changed=True` (Pattern 5) |
| CFG-12 | Runway selection (3 / 06-24 / 02-20) | `RUNWAY_CONFIGS`-style parameterization of `detect.py` (Pattern 7), `device_config.json`'s `tracked_runway` key, `deploy/skypane-poll.service`'s existing `--geofence` flag as the delivery hook |
</phase_requirements>

## Summary

This phase adds one new thing to the SkyPane architecture — a small, password-gated, server-rendered HTML admin service — on top of a codebase that has, without exception, kept every existing service to two dependencies (Pillow + requests) and Python's own standard library for HTTP serving (`stub-server/byos_server.py` is explicitly "stdlib only"). The research strongly supports continuing that pattern: `http.server.ThreadingHTTPServer` plus a small hand-rolled router, styled directly on `byos_server.py`'s own `Handler` class, needs **zero new third-party packages** for this phase's whole scope — including HMAC-signed session cookies (stdlib `hmac`/`hashlib`/`secrets`), SQLite persistence (stdlib `sqlite3`), and PNG conversion (Pillow is already a dependency, reused from `server/plane/panel_format.py`). A Flask-based alternative is documented for completeness but is not the primary recommendation (see Standard Stack).

Two of this phase's requirements are materially harder than "read an existing JSON file and render it": CFG-12 (runway selection) requires generalizing `server/plane/detect.py`'s runway-3-specific corridor gate — the exact code the 2026-08-27 runway3-false-positive debug session hardened — into a runway-parameterized form, reusing threshold coordinates for 06/24 and 02/20 that already exist in `adsb-test/runway3.json` but were only ever used to *exclude* traffic, never to positively gate it; this phase must ship without empirically-derived corridor thresholds for those two runways (runway 3's own thresholds were derived from real captured traffic specifically for runway 3), which is a genuine, flagged risk. CFG-10/CFG-11 (render preview/gallery) are not simple HTTP wrappers around `render.py`'s existing `--preview` CLI flag as CONTEXT.md's D-20 assumed on first pass — that CLI flag renders a synthetic *sample* flight, not what the panel is *actually currently displaying*; the correct data source for CFG-10 is the literal `panel.bin` bytes already served to the device (needs a new small `unpack_panel()` function, the mirror-image of the existing `pack_panel()`), and CFG-11 needs a new, small retention mechanism in `poll_loop.py` since nothing today keeps more than the single currently-served panel.

A third hard problem this research surfaced independently: `stub-server/byos_server.py` receives the device's `X-Battery-Mv` header on every poll but only prints it to stdout — and is explicitly off-limits to modify (D-03). Persisting battery telemetry (CFG-03) without touching that vendored file is solved by extending the already-active Caddy JSON access log (which by default includes non-sensitive request headers) to a durable file, and having the companion service (or a small tailer) read new lines from it.

**Primary recommendation:** A new top-level `companion/` directory, `http.server.ThreadingHTTPServer` + a hand-rolled router (styled on `byos_server.py`), sharing `server/.venv`'s existing Pillow/requests install (no new pip packages), a new `state/history.db` SQLite database written by `poll_loop.py` and read by the companion service, a new `state/device_config.json` for user-settable config (theme, tracked runway), and Caddy's existing JSON access log extended to a durable file as the sole path to persisting device battery telemetry without touching vendored code.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Companion HTML pages (Config/Health/Airlines/History tabs) | API/Backend (companion service, server-rendered HTML) | — | No client-side JS framework; this project has no browser-tier code at all today, and D-21 explicitly wants a plain utility page, not an SPA |
| Session/password auth | API/Backend (companion service) | — | Single shared secret, HMAC-signed cookie computed and verified server-side |
| Theme/runway config persistence | Database/Storage (`state/device_config.json`) | API/Backend (companion service writes, `poll_loop.py`/`detect.py`/`render.py` read) | New, small, infrequently-written file — kept separate from `poll_state.json` to avoid a two-writer race (see Pitfall 5) |
| Runway detection logic change (CFG-12's actual behavior) | API/Backend (`server/plane/detect.py`, `poll_loop.py`) | — | This is the one capability in this phase that is NOT a display/config layer — it changes what the ADS-B detection pipeline itself does, per CONTEXT.md's own note |
| Panel rendering | API/Backend (`server/plane/render.py`, unchanged) | — | Untouched by this phase except for the `TOP_RIGHT_TAG_TEXT` runway-tag string and a small gallery-retention hook |
| History/health/flight-log storage | Database/Storage (`state/history.db`, SQLite) | API/Backend (`poll_loop.py` writes, companion service reads) | Time-series + aggregate queries (CFG-03 trend, CFG-08 stats) are exactly SQL's job; stdlib `sqlite3` needs no new dependency |
| Render gallery storage | Database/Storage (`state/gallery/*.png`, filesystem) | API/Backend (`poll_loop.py` writes on `panel_changed=True`) | Binary image blobs are cheaper to keep as plain files than as SQLite BLOBs at this small scale |
| Device battery telemetry capture | CDN/Static-equivalent (Caddy's own JSON access log) | Database/Storage (tailed into `history.db`) | The only path that doesn't touch vendored `byos_server.py` (D-03) |
| Physical device display | *(no browser-tier analog — physical e-ink)* | — | Out of this phase's scope; the device only ever reads `panel.bin` via the unchanged device protocol |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python (stdlib) `http.server` | bundled with Python 3.12 | HTTP serving for the companion service | `stub-server/byos_server.py`'s own docstring: "Stdlib only." This project has never added a web framework dependency; `ThreadingHTTPServer` is the exact class the vendored device-protocol server already uses in production |
| Python (stdlib) `sqlite3` | bundled (SQLite 3.53.4 verified available in this environment `[VERIFIED: local interpreter]`) | New history/health/flight-log persistence | Zero new dependency; supports the range/aggregate queries CFG-03/06/08 need, which flat JSON cannot do without hand-rolled scanning |
| Python (stdlib) `hmac`, `hashlib`, `secrets` | bundled | Signed session cookie (D-01/D-02) | Matches `byos_server.py`'s own `secrets.token_hex(32)` bearer-token pattern already in this codebase; `hmac.compare_digest()` avoids a timing side-channel on the password check |
| Pillow | 12.3.0 (already pinned in `server/requirements.txt`) | Convert `panel.bin`'s raw nibble bytes to a viewable PNG for CFG-10/CFG-11 | Already a dependency; the companion service can share `server/.venv`'s existing install rather than adding a second one |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Python (stdlib) `html` | bundled | Escape ADS-B/adsbdb-sourced text (airline names, callsigns, unresolved prefixes) before interpolating into HTML | Every place CFG-04/06/08 render text that ultimately originated from an external, untrusted feed (see Common Pitfalls #2) |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| stdlib `http.server` + hand-rolled router | Flask 3.1.x (+ Werkzeug, Jinja2, itsdangerous, click, MarkupSafe transitively) | Jinja2's autoescaping removes the "forgot to `html.escape()`" risk class entirely, and `flask.session` gives signed cookies for free — genuinely less code to write. Rejected as primary because it breaks this project's unbroken 3-phase pattern of stdlib-only servers with exactly 2 pinned third-party packages, and every package in the Flask stack came back `[SUS]` in this session's Package Legitimacy Gate (see below) purely because this sandboxed environment cannot reach a download-stats endpoint — a real re-check with network access would very likely clear all six (they are the long-established, widely-used Pallets project packages), but that re-check has not happened this session. If a future session picks Flask instead, gate every install behind `checkpoint:human-verify` per the audit below. |
| SQLite (`state/history.db`) | Append-only JSONL file | JSONL is simpler to write but requires a full-file scan (or hand-rolled indexing) for CFG-03's "recent weeks" trend view and CFG-08's aggregate resolution-rate-over-time query — SQLite's `WHERE ts > ?` and `GROUP BY` do this natively, and it is still zero new dependency (stdlib `sqlite3`) |
| Caddy JSON-log tailing for battery telemetry | Modifying `stub-server/byos_server.py` to persist `X-Battery-Mv` directly | Rejected outright — D-03/`stub-server/VENDOR.md` explicitly forbid modifying the vendored file; `deploy/README.md`'s own "Known vendored behaviour" section already sets the precedent of solving a byos_server.py limitation (loopback binding) at the infrastructure layer instead of patching the file |

**Installation:**
```bash
# No new pip packages for the primary (stdlib) recommendation. The
# companion service reuses server/.venv (already has Pillow==12.3.0,
# requests==2.34.2) purely for its PNG-conversion helper.

# If the Flask alternative is chosen instead:
server/.venv/bin/pip install Flask==3.1.3
```

**Version verification:** `sqlite3` bundled version confirmed via `python3 -c "import sqlite3; print(sqlite3.sqlite_version)"` → `3.53.4` in this environment `[VERIFIED: local interpreter]`. Flask's current PyPI release (3.1.3, Feb 2026) found via WebSearch `[CITED: pypi.org/project/Flask]` — not independently re-verified via `pip index versions` because this sandboxed environment has no outbound network access to PyPI (confirmed — see Package Legitimacy Audit below).

## Package Legitimacy Audit

> Primary recommendation (stdlib `http.server` + `sqlite3` + `hmac`) installs **zero new third-party packages** — this audit only applies if the Flask alternative is chosen.

The `gsd-tools query package-legitimacy check --ecosystem pypi` seam was run against every package the Flask alternative would add. Every one came back `SUS` for the same single reason (`unknown-downloads`) — this sandboxed environment cannot reach the download-stats provider, not a real signal about the packages themselves (all six are the long-established Pallets ecosystem projects with real, long-lived GitHub repos and non-recent-first-publish dates, except `click` whose reported `publishedAt` of 2026-08-26 looks like a *release* date for a routine version bump of an existing, mature project, not a first-publish date — `[ASSUMED]`, not independently confirmed this session).

| Package | Registry | Age (per tool) | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----------------|-----------|--------------|---------|-------------|
| flask | PyPI | released 2026-02-19 | unknown (offline) | github.com/pallets/flask/ | SUS | Flagged — planner must add `checkpoint:human-verify` if Flask is chosen |
| werkzeug | PyPI | released 2026-04-02 | unknown (offline) | github.com/pallets/werkzeug/ | SUS | Flagged — same as above |
| jinja2 | PyPI | released 2025-03-05 | unknown (offline) | github.com/pallets/jinja/ | SUS | Flagged — same as above |
| itsdangerous | PyPI | released 2024-04-16 | unknown (offline) | github.com/pallets/itsdangerous/ | SUS | Flagged — same as above |
| click | PyPI | released 2026-08-26 | unknown (offline) | github.com/pallets/click/ | SUS | Flagged (also "too-new" signal — likely a routine point release, not a new package; re-verify) |
| markupsafe | PyPI | released 2025-09-27 | unknown (offline) | github.com/pallets/markupsafe/ | SUS | Flagged — same as above |

**Packages removed due to `[SLOP]` verdict:** none.
**Packages flagged as suspicious `[SUS]`:** flask, werkzeug, jinja2, itsdangerous, click, markupsafe — all six, all for the identical offline-only reason above. If the planner selects the Flask alternative, gate the `pip install` behind a `checkpoint:human-verify` task that re-runs the legitimacy check (or at minimum `pip show`/PyPI-page-eyeball) with real network access before trusting these as clean.

*The primary (stdlib) recommendation needs no such gate — nothing new is installed.*

## Architecture Patterns

### System Architecture Diagram

```
                                    ┌─────────────────────────────┐
                                    │   Physical SkyPane frame     │
                                    │  (unchanged this phase)      │
                                    └──────────────┬───────────────┘
                                                    │ HTTPS poll (existing
                                                    │ device protocol, D-06:
                                                    │ picks up config changes
                                                    │ here, next scheduled poll)
                                                    ▼
┌────────────────────┐   reverse_proxy   ┌───────────────────────┐
│  Caddy (existing)   │◄──────────────────┤ byos_server.py         │
│  <device-host>.nip  │  127.0.0.1:8642   │ (vendored, UNCHANGED)  │
│  .io site block     │                   │ reads panel.bin        │
│                     │                   └───────────┬────────────┘
│  log{output file}   │  X-Battery-Mv header logged    │ writes/reads
│  (NEW: durable,     │  in every JSON access-log line  │
│  not stdout-only)   │◄─────────────────────────────────┘
└─────────┬───────────┘
          │ tailed periodically by
          ▼
┌─────────────────────────────────────────────────────────────┐
│  companion/ (NEW service, separate process, D-03)             │
│  ThreadingHTTPServer + hand-rolled router, own systemd unit   │
│                                                                 │
│  GET /login, POST /login  ───────► HMAC-signed session cookie  │
│  GET /config, POST /config ──────► writes state/device_config │
│                                     .json (theme, runway)       │
│  GET /health ─────────────────────► reads state/history.db     │
│                                     (device_health, runway_evt) │
│  GET /airlines ───────────────────► reads state/poll_state.json│
│                                     ["unresolved_prefixes"]     │
│  GET /history ────────────────────► reads state/history.db     │
│                                     (runway_events)             │
│  POST /poll-now ──────────────────► import poll_loop; run_once()│
│                                     (global cooldown gate)      │
│  GET /preview.png ────────────────► unpack_panel(state/panel.bin)│
│  GET /gallery ─────────────────────► lists state/gallery/*.png  │
└───────────┬───────────────────────────────┬────────────────────┘
            │ reads                          │ reads/writes
            ▼                                ▼
┌────────────────────────┐      ┌─────────────────────────────┐
│ state/poll_state.json   │      │ state/device_config.json     │
│ (existing, UNCHANGED    │      │ (NEW — theme, tracked_runway)│
│  shape)                 │      └──────────────┬────────────────┘
└────────────┬────────────┘                     │ read every cycle
             │ read every cycle                 ▼
             │                    ┌───────────────────────────────┐
             └───────────────────►│ poll_loop.py (existing, small   │
                                   │ additions this phase)           │
                                   │  - reads device_config.json     │
                                   │    for tracked_runway            │
                                   │  - passes runway_id into         │
                                   │    detect.select_aircraft_for_   │
                                   │    runway()                      │
                                   │  - writes state/history.db rows  │
                                   │    (runway_events, on state      │
                                   │    change only)                  │
                                   │  - writes state/gallery/*.png    │
                                   │    when panel_changed=True       │
                                   └───────────────┬───────────────────┘
                                                    │ calls
                                                    ▼
                                   ┌───────────────────────────────┐
                                   │ detect.py (generalized this     │
                                   │ phase, CFG-12): RUNWAY_CONFIGS  │
                                   │ keyed by runway id, each with    │
                                   │ its own corridor/heading gate    │
                                   └───────────────────────────────────┘
```

### Recommended Project Structure
```
companion/
├── app.py              # entry point: ThreadingHTTPServer + Handler, mirrors byos_server.py's shape
├── auth.py             # HMAC session cookie issue/verify, password check (hmac.compare_digest)
├── history_db.py        # sqlite3 schema + read/write helpers, shared with poll_loop.py
├── pages/                # small HTML-string-builder functions, one per tab (Config/Health/Airlines/History)
│   ├── config_page.py
│   ├── health_page.py
│   ├── airlines_page.py
│   └── history_page.py
├── panel_preview.py      # unpack_panel(): reverse of panel_format.pack_panel()
└── test_companion_app.py # stdlib harness, subprocess-launches app.py on a free port (mirrors stub-server/test_poll_cycle.py)
```

### Pattern 1: CFG-01 theme picker — ship now against a single-option placeholder

**What:** A `THEMES` dict (analogous to `detect.py`'s future `RUNWAY_CONFIGS`) keyed by a short theme id, each entry naming `{departing_bg_idx, arriving_bg_idx, label}` — indices must be members of `panel_format.PALETTE_RGB`'s legal set (`IDX_BLUE`/`IDX_GREEN` today). Ship with **exactly one entry**, built from the current (screen-only-confirmed) D-21 pair, so the picker UI, its persistence (`device_config.json["theme"]`), and `render.py`'s consumption of that setting are all real and wired — but the visible choice is a single radio button/dropdown option until Phase 7 adds more.
**When to use:** Now (D-11's "ship mechanism now" branch) — the alternative (defer the whole task) leaves CFG-01 permanently blocked on a phase that runs strictly after this one in the roadmap, with no way to re-open it as a small follow-up.
**Example:**
```python
# companion/pages/config_page.py (sketch)
THEMES = {
    "sky": {"departing_idx": pf.IDX_BLUE, "arriving_idx": pf.IDX_GREEN, "label": "Sky (default)"},
    # Phase 7 adds more entries here once on-glass validation confirms them —
    # no structural change needed, just new dict entries.
}
```
Then `render.py`'s `STATE_BACKGROUND` dict becomes a function of the *selected* theme (read from `device_config.json`) rather than a fixed module-level constant — this is the actual code change CFG-01 requires in `render.py`, beyond the companion service itself.

### Pattern 2: SQLite history — log on state-change, not on every 30s poll

**What:** `poll_loop.py` opens `state/history.db` (WAL mode) and inserts a `runway_events` row **only when something changed this cycle** — a new `hex` (new flight), a `confirmed_state` flip, or a `corroborated` flip — not on every one of the ~2,880/day 30-second cycles. `device_health` rows (battery/last-poll) come from a *separate* source (the Caddy log tailer, Pattern 6), not from `poll_loop.py` at all, since `poll_loop.py` never sees `X-Battery-Mv`.
**When to use:** Any write path from `poll_loop.py` into the new history store.
**Example:**
```python
# server/poll_loop.py (sketch — new code, additive to run_once())
import sqlite3

def _history_db(state_dir):
    conn = sqlite3.connect(os.path.join(state_dir, "history.db"), timeout=5.0)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.execute("""CREATE TABLE IF NOT EXISTS runway_events (
        id INTEGER PRIMARY KEY, ts TEXT NOT NULL, hex TEXT, callsign TEXT,
        aircraft_type TEXT, confirmed_state TEXT, corroborated TEXT,
        route_source TEXT, tracked_runway TEXT)""")
    return conn

# Inside run_once(), only on a real transition (new hex / state flip / corroborated flip):
conn = _history_db(state_dir)
conn.execute(
    "INSERT INTO runway_events (ts, hex, callsign, aircraft_type, confirmed_state, "
    "corroborated, route_source, tracked_runway) VALUES (?,?,?,?,?,?,?,?)",
    (now_iso, flight.get("hex"), flight.get("callsign"), flight.get("aircraft_type"),
     confirmed_state, str(flight.get("corroborated")), route_source, tracked_runway),
)
conn.commit()
conn.close()
```
CFG-06 (flight log) reads this table directly (most recent N rows). CFG-08 (resolution stats) runs `SELECT route_source, COUNT(*) FROM runway_events WHERE ts > ? GROUP BY route_source`. CFG-03's corroboration trend runs `SELECT ts, corroborated FROM runway_events ORDER BY ts DESC LIMIT ?`.

### Pattern 3: CFG-07 manual poll trigger — direct import, not subprocess

**What:** The companion service's `POST /poll-now` handler does `import server.poll_loop as poll_loop; poll_loop.run_once(state_dir=STATE_DIR)` directly, in-process — exactly the pattern `server/test_pipeline_e2e.py` and `poll_loop.py`'s own `main()` already use for calling `run_once()`. No subprocess, no shelling out.
**When to use:** CFG-07's trigger handler.
**Example:**
```python
# companion/app.py (sketch, inside the POST /poll-now handler)
import server.poll_loop as poll_loop  # same sys.path bootstrap as poll_loop.py itself needs

def handle_poll_now(self):
    if not _cooldown_elapsed():          # D-17: global, not per-session (Pitfall 8)
        return self.send_json(429, {"detail": "cooldown active, try again shortly"})
    result = poll_loop.run_once(state_dir=STATE_DIR)  # reuses the exact production code path
    _mark_triggered_now()
    return self.send_json(200, {"flight": result.get("flight"), "state": result.get("state")})
```
Rationale for import-over-subprocess: `run_once()` already returns a structured result dict the handler can render directly; a subprocess would require re-parsing stdout, adds process-spawn latency inside an HTTP request, and diverges from every other in-repo caller's pattern (`poll_loop.main()`, `test_pipeline_e2e.py`).

### Pattern 4: CFG-10 live preview — unpack the actually-served `panel.bin`, not `render.py --preview`

**What:** `render.py --preview` renders a **synthetic sample flight** (`_PREVIEW_ROUTE`, a hardcoded Air France/JFK example) for manual QA — it has no way to show what the panel is *actually currently displaying* to the device. The correct data source is the literal bytes in `state_dir/panel.bin` (the same file `byos_server.py` serves), unpacked back into a viewable image via a new function that reverses `panel_format.pack_panel()`.
**When to use:** CFG-10's `GET /preview.png` handler.
**Example:**
```python
# companion/panel_preview.py (new — reverse of panel_format.pack_panel())
from PIL import Image
from server import panel_format as pf

_NIBBLE_TO_INDEX = {v: k for k, v in pf.INDEX_TO_NIBBLE.items()}

def unpack_panel(raw_bytes):
    """Reverse of pf.pack_panel(): 960,000 packed bytes -> a viewable RGB PNG,
    using the same render-internal PALETTE_RGB swatch pf.new_canvas() uses
    (D-P2-03: nominal preview colours, not colour-accurate against real glass).
    """
    assert len(raw_bytes) == pf.IMAGE_BYTES
    canvas = Image.new("P", (pf.WIDTH, pf.HEIGHT))
    canvas.putpalette(pf.padded_palette())
    px = bytearray(pf.WIDTH * pf.HEIGHT)
    for row in range(pf.HEIGHT):
        obase = row * pf.ROW_BYTES
        base = row * pf.WIDTH
        for col in range(0, pf.WIDTH, 2):
            byte = raw_bytes[obase + col // 2]
            px[base + col] = _NIBBLE_TO_INDEX[byte >> 4]
            px[base + col + 1] = _NIBBLE_TO_INDEX[byte & 0x0F]
    canvas.putdata(bytes(px))
    return canvas.convert("RGB")
```
This mirrors `pack_panel()`'s own row/column/nibble loop exactly in reverse, using the identical `INDEX_TO_NIBBLE` table (inverted) so the two functions can never silently drift.

### Pattern 5: CFG-11 render gallery — new retention hook in `poll_loop.py`, not `render.py`

**What:** Nothing today keeps more than the single currently-served `panel.bin` — `write_panel_atomic()` overwrites it in place. CFG-11 needs `poll_loop.py` to additionally save a copy (as PNG, via the same `canvas.convert("RGB").save(...)` `render.py --preview` already uses) into `state/gallery/` whenever `panel_changed=True`, with a retention cap pruning the oldest beyond N (recommend N=20-30 given each PNG is a full 1200x1600 image, order of a few hundred KB).
**When to use:** Right after `write_panel_atomic()` returns `True` in `run_once()`.
**Example:**
```python
# server/poll_loop.py (sketch — additive, near write_panel_atomic() call sites)
GALLERY_MAX_ENTRIES = 25

def _save_to_gallery(state_dir, canvas, now_iso):
    gallery_dir = os.path.join(state_dir, "gallery")
    os.makedirs(gallery_dir, exist_ok=True)
    safe_ts = now_iso.replace(":", "-")
    canvas.convert("RGB").save(os.path.join(gallery_dir, "%s.png" % safe_ts))
    entries = sorted(os.listdir(gallery_dir))
    while len(entries) > GALLERY_MAX_ENTRIES:
        os.remove(os.path.join(gallery_dir, entries.pop(0)))
```
Requires `render.build_canvas()`'s return value (the pre-pack canvas) to be threaded through to this call — `render_panel()` currently only returns the *packed* bytes, so `run_once()` needs to call `render.build_canvas()` + `pf.pack_panel()` separately (or `render_panel()` gains an optional "also return the canvas" path) instead of only calling `render.render_panel()`.

### Pattern 6: Battery telemetry — tail Caddy's durable JSON access log, never touch `byos_server.py`

**What:** `stub-server/byos_server.py` prints `X-Battery-Mv` to stdout via `log_telemetry()` but persists nothing, and is explicitly off-limits to modify (D-03). Caddy's JSON access log (`format json`) includes request headers by default, with only a fixed sensitive-header set (`Cookie`, `Set-Cookie`, `Authorization`, `Proxy-Authorization`) redacted `[CITED: caddyserver.com/docs/logging]` — `X-Battery-Mv` is not in that redacted set, so it appears in cleartext in the log line for every `GET /device/v1/display` request. Change the *existing* byos site block's `log` directive from `output stdout` (journald-bound, rotates — already documented as an anti-pattern by `poll_loop.py`'s own module docstring for the unrelated unresolved-prefix registry) to `output file <durable path>`, and have the companion service periodically tail new lines, extract the header, and insert into `history.db`'s `device_health` table.
**When to use:** The one and only path to CFG-03's battery-voltage history, given D-03's constraint.
**Example:**
```caddyfile
# deploy/Caddyfile (existing byos site block, log directive extended)
203-0-113-10.nip.io {
    reverse_proxy 127.0.0.1:8642
    log {
        output file /opt/skypane/state/caddy-access.log {
            roll_size 10MiB
            roll_keep 5
        }
        format json
    }
}
```
```python
# companion/history_db.py (sketch — periodic tailer, e.g. run every 60s by
# a small thread inside the companion service, or its own tiny systemd timer)
import json

def tail_battery_readings(log_path, last_offset):
    with open(log_path) as fh:
        fh.seek(last_offset)
        for line in fh:
            try:
                entry = json.loads(line)
            except ValueError:
                continue
            if entry.get("request", {}).get("uri") != "/device/v1/display":
                continue
            battery_mv = entry.get("request", {}).get("headers", {}).get("X-Battery-Mv", [None])[0]
            if battery_mv is not None:
                yield entry.get("ts"), battery_mv
        return fh.tell()
```
`[ASSUMED — MEDIUM confidence]`: the exact JSON field path (`request.headers.X-Battery-Mv`) is Caddy's documented shape but was not hand-verified against a live Caddy instance this session; confirm the exact nesting against a real captured log line before relying on it (see Assumptions Log A3).

### Pattern 7: CFG-12 — `RUNWAY_CONFIGS` parameterization of `detect.py`

**What:** Restructure `adsb-test/runway3.json`'s top-level shape from a single flat `runway`/`corridor` pair into a `runways` dict keyed by runway id, each holding its own `runway` (two thresholds + heading) and `corridor` (half_width_m/extension_m/axis_tolerance_deg) block — keeping `bbox`/`center`/`radius_nm`/`alt_ceiling_ft` shared at the top level (the coarse bbox prefilter is intentionally broad enough to already contain all three runways — confirmed in the file's own `bbox.correction_2026_08_27` note: 71.9%/80.5% of the other two runways' pavement already falls inside it). Filename stays `runway3.json` (deploy scripts already hardcode this path — `deploy/deploy.sh`, `deploy/skypane-poll.service` — changing it adds unnecessary deploy-script churn).
**When to use:** CFG-12's core implementation.
**Example:**
```python
# server/plane/detect.py (sketch of the generalization)
DEFAULT_RUNWAY_ID = "3"

def runway_axis(geofence, runway_id=DEFAULT_RUNWAY_ID):
    runways = geofence.get("runways")
    runway = (runways or {}).get(runway_id) if isinstance(runways, dict) else geofence.get("runway")
    # ^ back-compat: an old-shape geofence (bare "runway" key) still works for runway_id="3"
    ...

def corridor_params(geofence, runway_id=DEFAULT_RUNWAY_ID):
    runways = geofence.get("runways")
    block = ((runways or {}).get(runway_id) or {}).get("corridor") if isinstance(runways, dict) else geofence.get("corridor")
    ...

def select_aircraft_for_runway(aircraft, geofence, runway_id=DEFAULT_RUNWAY_ID):
    # body identical to today's select_runway3_aircraft(), just threading
    # runway_id through to filter_in_geofence()'s runway_axis()/corridor_params() calls
    ...

def select_runway3_aircraft(aircraft, geofence):
    """Back-compat thin wrapper — every existing caller (poll_loop.py,
    the CLI, all 28 checks in test_plane_detection.py) keeps working
    unchanged, pinned to runway_id="3"."""
    return select_aircraft_for_runway(aircraft, geofence, runway_id="3")
```
`poll_loop.py` reads `device_config.json["tracked_runway"]` (default `"3"`) once per cycle and passes it to `detect.poll_current_aircraft(geofence, runway_id=tracked_runway)`. `render.py`'s `TOP_RIGHT_TAG_TEXT = "ORY · RWY 3"` module constant must also become a function of the tracked runway (e.g. using `runway3.json`'s existing `icao_heading_designators` field per runway, "07/25" / "06/24" / "02/20") — a small, additional, currently-unlisted code touch this phase requires.

**06/24 and 02/20's corridor thresholds are copied from runway 3's measured values (500m half-width, 2500m extension, 30° tolerance) as a first cut, NOT independently re-derived from real captured traffic on those runways** — runway 3's numbers came from comparing real runway-3 arrivals (measured ≤31m cross-track) against real wrong-runway traffic (measured ≥611m cross-track); no equivalent live-capture dataset exists for 06/24 or 02/20. This is `[ASSUMED]` — see Assumptions Log A1 and Common Pitfalls #7.

### Anti-Patterns to Avoid

- **Storing `device_config.json`'s theme/runway settings inside `poll_state.json`:** `poll_loop.py` already read-modify-writes `poll_state.json` every cycle via `load_poll_state()`/`save_poll_state()`'s whole-file tmp-write-then-`os.replace()` pattern; a second writer (the companion service, on a user Save click) racing against that same file risks silently dropping whichever write loses the race. Use a separate, small, infrequently-written file instead.
- **Calling `render.py --preview` (subprocess or otherwise) to answer "what is the panel showing right now":** it always renders a synthetic sample flight, never the real state. Read `panel.bin` directly (Pattern 4).
- **Modifying `stub-server/byos_server.py` to persist `X-Battery-Mv`:** explicitly forbidden by D-03/`stub-server/VENDOR.md`; use the Caddy-log-tail approach (Pattern 6) instead.
- **Trusting a per-session cooldown for CFG-07's rate limit:** D-01/D-02 mean there are no distinct user accounts — a second browser tab gets a second session cookie and would bypass a per-session gate entirely. The cooldown must be global/server-side (Pitfall 8).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Session cookie signing | A custom cipher or a bespoke token format | `hmac.new(secret, payload, hashlib.sha256)` over an expiry-stamped payload, verified with `hmac.compare_digest()` | HMAC-SHA256 is a correctly-scoped, well-understood primitive for "prove this cookie was issued by us and hasn't expired" — this project already trusts exactly this level of crypto (`secrets.token_hex(32)` bearer tokens in `byos_server.py`); no need for a signing *library*, just the stdlib primitive used correctly |
| Time-series storage with range/aggregate queries | A hand-rolled JSONL scanner with manual date-range filtering | stdlib `sqlite3` with `WHERE ts > ?` / `GROUP BY` | SQL is the standard tool for exactly this query shape; writing an equivalent JSONL scanner is more code, slower, and more bug-prone than a `SELECT` |
| Panel byte unpacking | A generic "decode any bit-packed image format" library | A ~15-line function mirroring `pack_panel()`'s own loop in reverse (Pattern 4) | The wire format is a project-specific 4-bit nibble packing over a fixed 6-entry palette; no general-purpose library targets this shape, and the reverse of an already-existing, already-tested function is trivial and auditable |
| Multi-page HTML routing | A full web framework's URL-dispatch machinery | A small `if self.path == "/x":` dispatch table, exactly `byos_server.py`'s own `do_GET`/`do_POST` shape | Four to six routes total; framework-grade routing (regex path params, blueprints) solves a scaling problem this phase does not have |

**Key insight:** Every "don't hand-roll" item above is already precedented somewhere else in this exact codebase (bearer tokens, tmp-write-then-replace persistence, a stdlib-only HTTP handler) — this phase's job is to extend those same already-trusted patterns to a second service, not to introduce a new architectural idiom.

## Common Pitfalls

### Pitfall 1: D-13's storage estimate assumed the wrong cadence
**What goes wrong:** D-13 estimates "~1-2MB/year" of history data "even at an unrealistically-frequent 15-minute cadence." This project's actual **server-side ADS-B poll cadence is 30 seconds** (`server/poll_loop.py`'s `POLL_INTERVAL_S = 30`, driven by `deploy/skypane-poll.timer`'s `OnUnitActiveSec=30s`) — if history rows were naively written on every poll cycle rather than only on state changes, that's ~2,880 rows/day, ~1M/year, roughly 30x D-13's assumption.
**Why it happens:** D-13's estimate implicitly modeled the *device's* poll cadence (currently also 30s, but explicitly a "bring-up/test default," per STATE.md, expected to lengthen substantially once Phase 5's real battery-life data lands), not the *server's* independent, fixed 30s ADS-B detection cadence.
**How to avoid:** Follow Pattern 2 — write `runway_events` rows only on a real transition (new flight, state flip, corroboration flip), not on every cycle. `device_health` rows are keyed to the device's own poll cadence (via Caddy log tailing), which is a separate, much lower-frequency signal once tuned.
**Warning signs:** `history.db` growing by more than a few hundred KB/week in early testing is a sign the write path is firing on every cycle instead of on state changes.

### Pitfall 2: Un-escaped ADS-B/adsbdb-sourced text reaching raw HTML
**What goes wrong:** Airline names (from `enrich.py`, ultimately from adsbdb or a static table), callsigns, and unresolved ICAO prefixes are all, at origin, untrusted external input (this codebase already treats them this way elsewhere — `T-02-04-02`, `T-hyy-01`, the `_CALLSIGN_SAFE_RE`/`_AIRLINE_PREFIX_SHAPE_RE` gates in `enrich.py`). If the companion service's stdlib string-templated HTML interpolates any of these fields without `html.escape()`, a crafted callsign/airline string could inject markup into the admin page (stored/reflected XSS, ASVS V5).
**Why it happens:** stdlib string formatting has no autoescaping (unlike Jinja2) — every interpolation site is a manual opt-in.
**How to avoid:** Route every dynamic string through `html.escape()` at the single point it's interpolated into an HTML template string; consider a small `_html(text)` helper used everywhere, rather than remembering to call `html.escape()` inline at each of the ~6-10 interpolation sites across the four page modules.
**Warning signs:** Any page-builder function string-concatenating a field value directly into an f-string without a visible `html.escape()`/`_html()` call.

### Pitfall 3: Missing cookie security flags
**What goes wrong:** A session cookie set without `HttpOnly`, `Secure`, and `SameSite=Strict` (or at minimum `Lax`) is readable by any injected script (defeats Pitfall 2's mitigation if it ever fails) and is a CSRF target for the state-changing endpoints (`POST /config`, `POST /poll-now`) — an attacker's page could submit a cross-site form against those endpoints using the victim's ambient cookie.
**Why it happens:** `Set-Cookie` requires each flag to be explicitly appended; it's easy to ship a bare `session=<value>`.
**How to avoid:** `Set-Cookie: session=<value>; HttpOnly; Secure; SameSite=Strict; Path=/` — `Secure` is safe to set unconditionally since Caddy always terminates TLS in front of this service (matching `deploy/README.md`'s existing TLS-only posture for the device protocol).
**Warning signs:** `curl -v` against any Set-Cookie response missing one of the three flags.

### Pitfall 4: Non-constant-time password comparison
**What goes wrong:** Comparing the submitted password to the configured secret with `==` leaks timing information proportional to the matching prefix length — a real (if narrow) side-channel against the one shared secret this whole site's auth depends on (ASVS V2).
**Why it happens:** `==` is the natural first instinct and works functionally.
**How to avoid:** `hmac.compare_digest(submitted, configured)`.
**Warning signs:** Any `if password == os.environ["SKYPANE_COMPANION_PASSWORD"]:` in the codebase.

### Pitfall 5: Two writers racing on the same JSON config file
**What goes wrong:** If theme/runway settings were folded into `poll_state.json` instead of a dedicated file, `poll_loop.py`'s own periodic whole-file overwrite (every 30s) could race against a user's Save click on the companion service — whole-file `os.replace()` means one writer's change is silently lost, not merged.
**Why it happens:** `poll_state.json`'s existing read-modify-write pattern was designed for a single writer (`poll_loop.py` itself).
**How to avoid:** Use a separate `device_config.json`, written only by the companion service, read-only by `poll_loop.py`/`detect.py`/`render.py`.
**Warning signs:** A theme change that "doesn't stick" after a poll cycle runs — a symptom of exactly this race.

### Pitfall 6: Temptation to patch the vendored device-protocol server
**What goes wrong:** The most direct-looking fix for "persist `X-Battery-Mv`" is adding two lines to `byos_server.py`'s `do_GET` handler — but this file is explicitly vendored and off-limits (D-03, `stub-server/VENDOR.md`).
**Why it happens:** It's genuinely the shortest code path; the constraint is a project-policy decision, not a technical one.
**How to avoid:** Pattern 6 (Caddy log tailing).
**Warning signs:** Any diff touching `stub-server/byos_server.py` in this phase's plan.

### Pitfall 7: Trusting runway-3's numeric corridor thresholds for 06/24 and 02/20 without validation
**What goes wrong:** The exact bug the 2026-08-27 runway3-false-positive debug session fixed was "geometry that looks plausible but was never checked against real traffic." Copying runway 3's `half_width_m`/`extension_m`/`axis_tolerance_deg` values onto the other two runways, unvalidated, risks a symmetric version of the same class of bug (e.g., a runway-3 aircraft on a wide base leg being wrongly gated onto 06/24's corridor, or vice versa) — this time on purpose-built code that has never been checked against a single real capture on those runways.
**Why it happens:** The values are readily available (same module, same shape) and "just reuse them" is the path of least resistance.
**How to avoid:** Ship CFG-12 with the reused thresholds as an explicit, documented placeholder (mirroring how `panel_format.py`'s yellow/red palette entries are already documented as "LOW confidence, interim, pending on-glass calibration"), and add a manual verification task to the plan — capture a handful of real 06/24 and 02/20 polls after CFG-12 ships and confirm the gate behaves as expected, the same live-capture discipline the original runway3-false-positive fix used.
**Warning signs:** No live-capture verification step anywhere in the phase's plan for CFG-12.

### Pitfall 8: Per-session cooldown for the manual poll trigger
**What goes wrong:** D-17 wants a short cooldown to protect the free adsb.fi/adsb.lol APIs from accidental rapid triggering. Given D-01/D-02 (one shared password, no per-user accounts), a naive `session["last_triggered"]` cooldown is trivially defeated by opening a second tab (a fresh session cookie), and does not actually protect the shared upstream APIs.
**Why it happens:** Cooldowns are usually modeled per-user by default in web frameworks/tutorials; this site has no concept of distinct users.
**How to avoid:** Track the cooldown globally — a single in-process timestamp (acceptable given the companion service is intentionally a single, unthreaded-for-writes process) or a tiny file (`state/last_poll_trigger.txt`).
**Warning signs:** Cooldown state stored in the session cookie or a per-session dict rather than process-global/file-global state.

### Pitfall 9: SQLite lock contention between `poll_loop.py` and the companion service
**What goes wrong:** `poll_loop.py` is a short-lived oneshot process invoked every 30s; the companion service is a long-running process that both reads `history.db` (page requests) and occasionally writes it (Pattern 6's battery tailer). Without `PRAGMA journal_mode=WAL` and a `busy_timeout`, a write from one process while the other holds a lock raises `sqlite3.OperationalError: database is locked` instead of waiting briefly and succeeding.
**Why it happens:** SQLite's default rollback-journal mode blocks concurrent readers during a write; WAL mode allows readers to proceed during a writer's transaction.
**How to avoid:** `PRAGMA journal_mode=WAL` once (persists in the database file itself, no need to re-set every connection) plus `PRAGMA busy_timeout=5000` on every connection (Pattern 2's example already does both).
**Warning signs:** Intermittent `database is locked` errors in `poll_loop.py`'s journald output, especially during a manual poll trigger (CFG-07) that runs concurrently with the companion service's own read traffic.

## Code Examples

See Architecture Patterns 1-7 above for the load-bearing code sketches (theme placeholder, SQLite schema/write path, direct `run_once()` import, `unpack_panel()`, gallery retention, Caddy log tail, `RUNWAY_CONFIGS` parameterization) — each is grounded directly in this repo's existing code (`panel_format.py`, `poll_loop.py`, `detect.py`, `render.py`, `deploy/Caddyfile`), not generic boilerplate.

### Session cookie issue/verify (companion/auth.py sketch)
```python
import hashlib
import hmac
import os
import time

SESSION_TTL_S = 12 * 3600  # 12h — Claude's Discretion (D-01/D-02); unremarkable, not elaborate

def _secret():
    return os.environ["SKYPANE_COMPANION_PASSWORD"].encode()  # never logged, never committed

def issue_session_cookie():
    expiry = str(int(time.time()) + SESSION_TTL_S)
    sig = hmac.new(_secret(), expiry.encode(), hashlib.sha256).hexdigest()
    return "%s.%s" % (expiry, sig)

def verify_session_cookie(cookie_value):
    if not cookie_value or "." not in cookie_value:
        return False
    expiry, sig = cookie_value.split(".", 1)
    expected = hmac.new(_secret(), expiry.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sig, expected):
        return False
    try:
        return int(expiry) > time.time()
    except ValueError:
        return False

def password_ok(submitted):
    return hmac.compare_digest(submitted.encode(), _secret())
```
This needs no server-side session store at all (stateless, signed-expiry cookie) — appropriate for a single shared secret with no per-user revocation requirement.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| `adsb-test/runway3.json`'s bbox alone as the "on runway 3" test | Runway-aligned corridor + track-alignment gate (`corridor` block) | 2026-08-27, runway3-false-positive debug session | This phase's CFG-12 must extend the *gated* form (corridor+track), never regress to bbox-only for the new runways |
| `render.py --preview`/CLI-only visibility into render output | This phase adds HTTP-facing visibility (CFG-10/11) | This phase | Changes render.py's audience from "developer with SSH" to "anyone with the companion password" — the CLI flags themselves are unchanged, but the *live-panel* and *gallery* views are new code, not a wrapper |
| `X-Battery-Mv` logged to stdout only (journald, rotates) | This phase's Caddy-log-tail persists it durably | This phase | First durable battery-history signal in the project; `poll_loop.py`'s own docstring already established the "journald rotates, durable state doesn't" principle for the unrelated unresolved-prefix registry (quick task 260827-oz9) — same principle applied here |

**Deprecated/outdated:** none — this phase is additive; no existing mechanism is being replaced.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | 06/24 and 02/20's corridor gate can reuse runway 3's measured thresholds (500m/2500m/30°) as a safe first cut | Pattern 7, Pitfall 7 | If wrong, CFG-12 could reintroduce a variant of the exact runway3-false-positive bug on the newly-supported runways — recommend a live-capture verification checkpoint before considering CFG-12 "done" |
| A2 | The Flask package stack (flask/werkzeug/jinja2/itsdangerous/click/markupsafe) is legitimate despite this session's `[SUS]` verdicts | Package Legitimacy Audit | Low risk (these are extremely well-known packages) but not independently re-verified with real network access this session — only relevant if the Flask alternative is chosen over the stdlib primary recommendation |
| A3 | Caddy's default JSON access log nests request headers at `request.headers.<Header-Name>` as a list | Pattern 6 | If the actual field path differs, the battery tailer silently extracts nothing — verify against one real captured log line before relying on it in production |
| A4 | D-13's "~1-2MB/year" estimate used a 15-minute cadence assumption that doesn't match the server's real 30s ADS-B poll cadence | Pitfall 1 | If history writes are naively keyed to every 30s cycle instead of state changes, storage could be ~30x higher than D-13 assumed (still likely tolerable on a VPS, but worth designing around from the start rather than discovering it later) |
| A5 | SQLite WAL mode + a 5s busy_timeout is sufficient for the two-process (poll_loop.py oneshot + companion service) concurrency pattern this phase introduces | Pitfall 9 | Not load-tested this session; if wrong, manifests as occasional `database is locked` errors under real usage, recoverable by retrying rather than data loss |

**If this table is empty:** N/A — see rows above.

## Open Questions

1. **CFG-01 sequencing: ship placeholder now, or defer to after Phase 7?**
   - What we know: D-11 explicitly leaves this to planning, with an explicit instruction not to silently pick either way.
   - What's unclear: Whether the user would rather see a working (if single-option) picker sooner, or avoid building UI for a feature that's materially incomplete until Phase 7.
   - Recommendation: Ship now against a single-option placeholder (Pattern 1) — the mechanism (persistence, `render.py` consumption) is genuinely useful infrastructure regardless of how many themes exist, and D-07's "explicit confirmation" copy works identically whether there's 1 option or 4. Flag this choice explicitly to the user during planning/discuss rather than assuming.

2. **CFG-03's "last successful poll time" — device poll or server ADS-B poll, or both?**
   - What we know: These are two distinct signals with different failure modes (device unreachable vs. ADS-B aggregators unreachable) and different data sources (Caddy log tail vs. `poll_state.json`'s own mtime / a `history.db` row).
   - What's unclear: CONTEXT.md's wording doesn't disambiguate.
   - Recommendation: Show both, labeled distinctly ("Device last checked in" vs. "ADS-B pipeline last ran") — they answer genuinely different "is something wrong?" questions, and CFG-05's fault icon (D-15's corroboration signal) is specifically about the ADS-B side.

3. **Exact gallery retention count (CFG-11) and `SESSION_TTL_S` (session duration).**
   - What we know: Both are explicitly Claude's Discretion / not discussed live.
   - What's unclear: No strong signal either way; low-risk either direction.
   - Recommendation: Gallery N=20-30 (bounds disk use to a few MB); session TTL=12h (long enough to not be annoying for a single operator, short enough that a stolen/leaked cookie doesn't stay valid indefinitely) — both are easy to tune later, not architecturally load-bearing.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python stdlib `sqlite3` | CFG-03/06/08 persistence | Yes | 3.53.4 (bundled SQLite) `[VERIFIED: local interpreter]` | — |
| Python stdlib `http.server` | Whole companion service | Yes | bundled | — |
| Pillow | CFG-10/11 PNG conversion | Yes (already pinned `server/requirements.txt`) | 12.3.0 | — |
| Caddy (on the OVH VPS) | Pattern 6's log-file directive, new subdomain site block | Yes (already deployed and running per `deploy/README.md`) | version not re-verified this session (assume current, matches existing deployment) | — |
| systemd (on the OVH VPS) | New companion service unit | Yes (already the deployment target for every existing service) | — | — |
| nip.io / Let's Encrypt HTTP-01 | D-05's new subdomain | Yes (already proven working for the existing `<vps-ip>.nip.io` device-protocol hostname) | — | — |

**Missing dependencies with no fallback:** none.
**Missing dependencies with fallback:** none — the primary recommendation introduces zero new external dependencies.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | None (project convention: stdlib-only, directly-executable `test_*.py` scripts — no pytest; see `server/README.md`) |
| Config file | none — see Wave 0 |
| Quick run command | `server/.venv/bin/python3 companion/test_companion_app.py` |
| Full suite command | `scripts/run-all-tests.sh` (once `companion/test_companion_app.py` is added to its `HARNESSES` array) |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CFG-01 | Theme saved persists to `device_config.json`, `render.py` reads it | unit + integration | `server/.venv/bin/python3 companion/test_companion_app.py` | ❌ Wave 0 |
| CFG-03 | Health page renders trend from `history.db`/Caddy-tailed battery data | integration | `companion/test_companion_app.py` | ❌ Wave 0 |
| CFG-04 | Unresolved-prefix registry rendered read-only | integration | `companion/test_companion_app.py` | ❌ Wave 0 |
| CFG-06 | Flight log lists recent `runway_events` rows | integration | `companion/test_companion_app.py` | ❌ Wave 0 |
| CFG-07 | Manual poll trigger calls `run_once()`, cooldown enforced globally | integration | `companion/test_companion_app.py` | ❌ Wave 0 |
| CFG-08 | Resolution stats aggregate query returns expected shape | unit | `companion/test_companion_app.py` (or a dedicated `history_db` test) | ❌ Wave 0 |
| CFG-10 | `/preview.png` returns a viewable image matching `panel.bin`'s content | unit | `server/.venv/bin/python3 companion/test_panel_preview.py` (round-trip `pack_panel`→`unpack_panel`) | ❌ Wave 0 |
| CFG-11 | Gallery retention caps at N, prunes oldest | unit | extend `server/test_poll_loop.py` | ❌ Wave 0 |
| CFG-12 | `select_aircraft_for_runway()` correctly gates each of the 3 runways; `select_runway3_aircraft()` back-compat wrapper unchanged | unit (regression) | extend `server/test_plane_detection.py` (all 28 existing checks must still pass) | ✅ existing file, ❌ new checks Wave 0 |
| D-01/D-02 auth | Password gate blocks every route without a valid session; login issues a valid cookie | unit | `companion/test_companion_app.py` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `server/.venv/bin/python3 companion/test_companion_app.py` (and `server/test_plane_detection.py` for CFG-12 work)
- **Per wave merge:** `scripts/run-all-tests.sh` (full suite)
- **Phase gate:** Full suite green before `/gsd-verify-work`, plus `ruff check .` and `scripts/check-attribution.sh` (unchanged, already required repo-wide)

### Wave 0 Gaps
- [ ] `companion/test_companion_app.py` — stdlib harness, subprocess-launches `companion/app.py` on a free local port and drives it with `urllib.request`, mirroring `stub-server/test_poll_cycle.py`'s exact pattern (deterministic setup, `EXPECTED_CHECK_COUNT` convention, exit 0 only on full pass) — covers auth, CFG-01/03/04/06/07/08 route behavior
- [ ] `companion/test_panel_preview.py` (or fold into the above) — round-trips `pack_panel()` → `unpack_panel()` on a known canvas and asserts pixel-for-pixel equality
- [ ] Extend `server/test_plane_detection.py` — new checks for `select_aircraft_for_runway()` against 06/24 and 02/20 geometry (using the already-committed neighbouring-runway coordinates from `runway3.json`, now as *positive* fixtures instead of only exclusion regressions), while keeping all 28 existing checks green unchanged
- [ ] Extend `server/test_poll_loop.py` — gallery retention (Pattern 5), `history.db` write-on-state-change-only behavior (Pattern 2), `device_config.json` read path
- [ ] Add `companion/` to `pyproject.toml`'s `[tool.coverage.run] source` list and `scripts/run-all-tests.sh`'s `HARNESSES` array once the new test file(s) exist
- [ ] Framework install: none — stdlib only, no new `pip install` needed for tests

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | Yes | Single shared password, `hmac.compare_digest()` constant-time check (Pitfall 4), no plaintext logging of the password anywhere (matches `deploy/skypane.env.example`'s existing secrets discipline) |
| V3 Session Management | Yes | Stateless HMAC-signed, expiry-stamped session cookie (`HttpOnly`/`Secure`/`SameSite=Strict`, Pitfall 3); no server-side session store to leak or grow unbounded |
| V4 Access Control | Yes (narrow) | D-02: uniform, whole-site gate — no differentiated roles/permissions to get wrong, which simplifies this category considerably for v1 |
| V5 Input Validation | Yes | `html.escape()` (or an equivalent helper) on every ADS-B/adsbdb-sourced string before HTML interpolation (Pitfall 2); theme/runway selection values validated against the fixed `THEMES`/`RUNWAY_CONFIGS` key sets server-side (never trust a client-submitted arbitrary string as a dict key without a membership check) |
| V6 Cryptography | Yes (narrow) | `hmac`/`hashlib.sha256` only, stdlib, no custom cipher, no password hashing needed (there's no stored password hash — the shared secret is compared directly via `hmac.compare_digest()` against an env var, matching `byos_server.py`'s own `--secret` comparison pattern) |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| CSRF against `POST /config`, `POST /poll-now`, `POST /login` | Spoofing/Tampering | `SameSite=Strict` cookie (Pitfall 3) — sufficient here since there is exactly one origin, no cross-site legitimate use case, and no separate CSRF-token infrastructure needed for a single-user tool |
| Reflected/stored XSS via airline name/callsign/unresolved-prefix fields | Tampering | `html.escape()` on every dynamic interpolation site (Pitfall 2) |
| Timing side-channel on password comparison | Information Disclosure | `hmac.compare_digest()` (Pitfall 4) |
| Session cookie theft via missing `Secure`/`HttpOnly` | Information Disclosure/Elevation of Privilege | Explicit cookie flags (Pitfall 3) |
| Brute-forcing the single shared password | Elevation of Privilege | A simple failed-attempt backoff/lockout (Claude's Discretion per D-01/D-02 — e.g. a short delay or temporary IP-agnostic lockout after N consecutive failures, given D-01 already rejected IP-based mechanisms as impractical) |
| SQL injection into `history.db` queries | Tampering | Always use parameterized `sqlite3` queries (`?` placeholders, as in every example above) — never string-format a value into SQL text, even though today's inputs are server-internal (ADS-B callsigns), not directly user-submitted, this is the standard/expected discipline regardless |
| CFG-12: a spoofed/malformed `tracked_runway` value reaching `detect.py` | Tampering | The companion service must validate the submitted runway id against `RUNWAY_CONFIGS`' fixed key set before writing `device_config.json`; `detect.py`'s `runway_axis()`/`corridor_params()` should also degrade safely (fall back to a default, never raise) on an unrecognized `runway_id`, mirroring the existing "missing corridor block falls back to module defaults" discipline already in `corridor_params()` |

## Sources

### Primary (HIGH confidence)
- Direct repository reads (this session): `server/plane/detect.py`, `server/poll_loop.py`, `server/plane/render.py`, `server/panel_format.py`, `server/plane/enrich.py`, `server/plane/runway_config.py`, `stub-server/byos_server.py`, `deploy/Caddyfile`, `deploy/provision.sh`, `deploy/deploy.sh`, `deploy/README.md`, `deploy/skypane-byos.service`, `deploy/skypane-poll.service`, `deploy/skypane-poll.timer`, `deploy/skypane.env.example`, `adsb-test/runway3.json`, `server/requirements.txt`, `server/README.md`, `pyproject.toml`, `.github/workflows/ci.yml`, `scripts/run-all-tests.sh`, `stub-server/test_poll_cycle.py`, `server/test_plane_detection.py`, `.planning/seeds/on-device-fault-icon.md`
- `python3 -c "import sqlite3; print(sqlite3.sqlite_version)"` run directly in this environment `[VERIFIED: local interpreter]` — confirms stdlib `sqlite3` availability and bundled SQLite version 3.53.4

### Secondary (MEDIUM confidence)
- Caddy official logging documentation (WebSearch, cross-checked against `caddyserver.com/docs/caddyfile/directives/log` and `caddyserver.com/docs/logging`) `[CITED: caddyserver.com/docs/logging]` — default JSON access log includes request headers, with a fixed sensitive-header redaction list not including custom headers like `X-Battery-Mv`
- Flask 3.1.3 current release (WebSearch, `[CITED: pypi.org/project/Flask]`) — used only for the documented alternative, not the primary recommendation

### Tertiary (LOW confidence)
- `gsd-tools query package-legitimacy check` results for the Flask package stack — all six `[SUS]` purely due to this sandboxed environment's lack of outbound network access to the download-stats provider; not a real signal about the packages, but not independently re-verified with network access either (see Assumptions Log A2)
- Exact JSON field nesting for Caddy's logged request headers (Pattern 6) — documented behavior, not hand-verified against a live captured log line this session (see Assumptions Log A3)

## Metadata

**Confidence breakdown:**
- Standard stack (stdlib-only companion service): HIGH — directly grounded in this repo's own unbroken 3-phase precedent, zero new dependencies to verify
- Architecture (SQLite schema, Caddy log tail, panel unpack/gallery): MEDIUM-HIGH — all patterns are novel to this phase but built from existing, well-understood pieces (`pack_panel()`'s own logic, Caddy's documented logging behavior, stdlib `sqlite3`)
- CFG-12 (runway parameterization): MEDIUM for the code structure (directly modeled on existing `detect.py` patterns), LOW for the specific numeric corridor thresholds on 06/24 and 02/20 (explicitly unvalidated against real traffic — Assumption A1)
- Pitfalls: HIGH — every pitfall is traced to a specific, cited line of existing code or a specific locked decision, not generic web-security advice

**Research date:** 2026-08-27
**Valid until:** 30 days for the architecture/stack recommendations (stable); the CFG-12 corridor-threshold assumption (A1) should be considered valid only until a real live-capture verification pass happens, regardless of elapsed time
