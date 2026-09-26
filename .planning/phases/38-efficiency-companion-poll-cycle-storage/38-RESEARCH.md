# Phase 38: Efficiency — companion, poll cycle, storage - Research

**Researched:** 2026-09-26
**Domain:** stdlib HTTP caching (ETag/304), Caddy `encode`, SQLite connection/transaction scoping, per-page script inclusion, JSON state write-avoidance, thread-parallel provider polling with per-provider rate limits
**Confidence:** HIGH for the current code facts (they were measured on `main` at `f4d9709`); MEDIUM for the freshness-token design (see D-2)

<user_constraints>
## User Constraints (from CONTEXT.md)

No `38-CONTEXT.md` exists yet (the phase directory was empty at research time). The constraints the planner has to honour come from the ROADMAP, the audit ledger and CLAUDE.md:

### Locked (ROADMAP Phase 38 + audit ledger)
- Requirements EFF-01..EFF-06, with the remediations the ledger names (`.planning/audits/2026-09-23-code-audit.md` §"Phase 38").
- Success criteria: (1) page weight (bytes transferred) and request time measured before and after on every route; (2) a second page load returns 304s for static files; (3) SQLite connections: 1 per page request and 1 per poll cycle; (4) poll-cycle wall time measured before and after, with no fixed 1.1 s sleep.
- D-A2: tests run on pytest (dev-only). Production stays stdlib + Pillow + requests. **No new runtime dependency.**
- D-A3: English everywhere, and no plan, phase or requirement IDs in comments (`scripts/check_comment_history.py check` runs in CI).
- EFF-02 says "no build step".
- The Caddy site file is SkyPane's own snippet (`/etc/caddy/sites/skypane.caddy`, rendered from `deploy/Caddyfile` by `deploy/render_caddyfile.sh`). A shared host Caddyfile imports it, so it holds **site blocks only, with no global options** (Phase 37).

### Claude's Discretion
- Everything below the requirement level: helper names, where the instruments live, how scripts are declared per page.

### Deferred / OUT OF SCOPE
- CFG-50: the Display page is ~3,743 px tall against a 2,600 px target. Out of scope.
- Phase 39: ARC-01 (`run_once` split and `CycleContext`), ARC-02 (`server/state_store.py` owns `poll_state.json`), ARC-04 (module-global setters), ARC-05 (shared modules), ARC-06 (typing).
- Phase 40: CMP-01 (route table), CMP-02 (one `{route: path}` static allowlist), CMP-04 (typed per-page context), CMP-05 (named templates in `page_shell`), CMP-08 (CSS de-duplication).
- Firmware wake cost (FW-09/FW-10), which is Phase 34 territory.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Status on `main` f4d9709 | Research Support |
|----|-------------|---------------------------|------------------|
| EFF-01 | `encode zstd gzip`; validators + 304; static bytes cached in memory | **PARTLY SOLVED.** Phase 35 cut `style.css` from 510 KB to 140,426 B. Comments are still 44 % of it (62 KB), down from 85 %. Everything else is still open: no `encode`, no ETag/Last-Modified, and the file is re-read on every request | §EFF-01 |
| EFF-02 | Only the scripts each page uses (no build step) | **STILL OPEN.** 15 `<script defer>` on every authenticated page, 16 on Health | §EFF-02 |
| EFF-03 | One connection per request/cycle; schema once per process; one transaction | **STILL OPEN.** 9–12 connections per page (the ledger said 16; the count varies with data and route) and 3 per cycle. Every connection runs 2 PRAGMAs + `init_schema` (6 DDL) | §EFF-03 |
| EFF-04 | Lazy context; severity without markup; light freshness endpoint | **STILL OPEN.** `page_context()` builds the full Health state, markup included, on every page, plus the 404/403 pages. `freshness.js` refetches the whole page every 45 s | §EFF-04 |
| EFF-05 | `poll_state` saved once, only if changed, compact | **PARTLY SOLVED.** Phase 36 made the write atomic (`atomic_io.atomic_write`). Still open: 1–2 saves per cycle, an unconditional save even when nothing changed, `indent=1` | §EFF-05 |
| EFF-06 | Providers queried in parallel, per-provider rate limit kept | **STILL OPEN.** `time.sleep(1.1)` between two *different* providers | §EFF-06 |
</phase_requirements>

## Summary

Every EFF item is still open against current `main`. Phases 35 and 36 changed the numbers but not the findings. Phase 35 shrank the stylesheet 3.6×, but it is still served uncompressed, with no validator, read from disk on every request. Phase 36 made `poll_state.json` writes atomic and serialised cycles under `poll.lock`, but did not reduce how often it writes. No finding can be dropped.

All six fixes can be done in stdlib inside the existing module shapes, without pre-empting Phase 39/40:

- EFF-01: one cached static-serving helper with ETag/Last-Modified/304 behind the existing 17 delegates, and `encode zstd gzip` in the **companion** site block only.
- EFF-02: a per-page script tuple that replaces the 15 fixed `<script>` lines.
- EFF-03: a re-entrant, thread-bound connection scope in `history_db`, so the ~16 existing `open_db()` call sites reuse one connection without changing their signatures. Add schema-once per (path, inode) and writers that no longer commit individually.
- EFF-04: split health *signals* from health *markup*, and make the expensive `page_context` values lazy.
- EFF-05: one save at the end of the cycle, compared against a snapshot serialised at load, written compact.
- EFF-06: a `ThreadPoolExecutor` over the providers, with results kept in provider order and a per-provider last-call time persisted across cycles.

**Primary recommendation:** Build the instruments first (Wave 0) and record the before numbers in a committed `38-EFF-BASELINE.md`, as 37 did. Then make each change behind an invariant test: 1 connection per request/cycle, 0 sleeps between different providers, ≤1 `poll_state` write per cycle and 0 when unchanged, 304 on revalidation, and an exact script set per page.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Transfer compression (zstd/gzip) | CDN/edge (Caddy, companion site block) | — | Caddy already terminates TLS. The app stays identity-only, so no compression code enters `companion/app.py` |
| Static validators (ETag, Last-Modified, 304) and in-memory bytes | API/backend (`companion/app.py` static helpers) | Caddy (appends `-zstd`/`-gzip` to a strong ETag and strips it from `If-None-Match`) | Only the origin knows the content hash |
| Per-page script set | Frontend server (SSR, `companion/layout.py` `page_shell`) | page modules / `app.py` route → scripts mapping | The markup is server-rendered |
| One SQLite connection per request/cycle, schema once | Database/storage (`server/history_db.py`) | `companion/app.py` request entry, `server/poll_loop.py` cycle entry | The connection lifecycle belongs to the storage module. Entry points only open and close the scope |
| Health severity without markup; lazy context | API/backend (`companion/pages/health_page.py`, `app.py page_context`) | — | Pure computation over reads |
| Freshness check | API/backend (session-gated page GET) | Browser (`freshness.js`) | The server decides "unchanged". The client just skips the swap |
| `poll_state` write-once | Backend (`server/poll_loop.py`) | — | Phase 39's `state_store` will later own it; 38 only changes when it is written |
| Parallel providers + rate limit | Backend (`server/plane/detect.py`) | `poll_loop.py` persists the last-call times | detect stays a leaf module and does not import `history_db` |

## Standard Stack

No new packages. Everything here is stdlib, as D-A2 requires.

| Need | Use | Why |
|------|-----|-----|
| Content hash for ETag | `hashlib.sha256` | Already used in `poll_loop.write_panel_atomic` |
| HTTP dates | `email.utils.formatdate(ts, usegmt=True)` / `email.utils.parsedate_to_datetime` | Standard RFC 9110 IMF-fixdate |
| Parallel provider calls | `concurrent.futures.ThreadPoolExecutor` | `requests.get` per call is independent. Threads are right for I/O-bound calls |
| Thread-bound request connection | `contextvars.ContextVar` (precedent: `companion/prefs.set_request_prefs`) or `threading.local` | `ThreadingHTTPServer` runs one thread per request, and `sqlite3` defaults to `check_same_thread=True` |
| Transaction | `sqlite3.Connection` + explicit `conn.commit()` / `rollback()` | Avoid the 3.12+ `autocommit` attribute: local dev runs 3.11 (`server/.venv`), CI and prod run 3.14 |
| Compression | Caddy `encode zstd gzip` | Built-in Caddy directive [CITED: caddyserver.com/docs/caddyfile/directives/encode] |

## Package Legitimacy Audit

No external packages are installed or added by this phase. `server/requirements*.txt` stay unchanged. slopcheck is not applicable.

## Architecture Patterns

### Data flow after the phase

```
Browser ──HTTPS──> Caddy [companion block: encode zstd gzip, HSTS]
                     │  strong ETag "abc" -> "abc-zstd"; If-None-Match "abc-zstd" -> "abc"
                     v
         companion/app.py Handler (one thread per request)
           do_GET ──> history_db.request_scope(state_dir)  (lazy: first open_db() opens it)
             ├─ /static/*  -> _serve_static(path)  [bytes+sha256+mtime cached per process]
             │                 If-None-Match / If-Modified-Since match -> 304 (no body)
             ├─ page GET with X-Requested-With: freshness + If-None-Match == page token -> 304
             └─ page GET -> page_context() [lazy values; health_signals() only]
                            -> page.render(ctx) -> page_shell(scripts=PAGE_SCRIPTS[route])
           scope exit -> close the single connection

systemd timer (30 s) / POST /poll-now
  run_once -> poll_cycle_lock -> history_db.cycle scope (1 connection)
    load poll_state (+ serialized snapshot)
    detect.poll_current_aircraft: ThreadPool[adsbfi, adsblol]
        each worker: wait until own provider's last_call + MIN_SECONDS_BETWEEN_CALLS, then query
        results assembled in DEFAULT_PROVIDER_ORDER (not completion order)
    render/publish panel -> _record_history (all writes, ONE commit) -> notify
    persist poll_state once, compact, only if serialization != snapshot
```

### EFF-01: static files, validators, compression

**Current code.**
- `companion/app.py:1224 _serve_stylesheet` and `:1233 _serve_script_file` `open()`/`read()` the file on every request, then call `send_bytes(200, ..., cache_seconds=300, public=True)` (`:808`).
- No ETag and no Last-Modified. Measured headers: `Cache-Control: public, max-age=300`, `ETag: None`, `Last-Modified: None`.
- Runway PNGs (`_serve_runway_image` `:1313`) are also re-read, private, max-age=300.
- `deploy/Caddyfile` has no `encode` in either block.
- Sizes today: `style.css` 140,426 B (36,939 B gzip-6); the 15 shell scripts 143,568 B (51,921 B gzip-6); `battery-trend.js` 5,780 B; `login-card.js` 4,147 B.

**Design.**
1. Add one `_serve_static(abs_path, content_type, public=True, cache_seconds=...)` helper. `_serve_stylesheet`, `_serve_script_file` and optionally `_serve_runway_image` delegate to it. Keep the 17 routes, 17 delegates and 17 `do_GET` branches exactly as they are: collapsing them is CMP-02 (Phase 40).
2. Keep a module-level cache `{abs_path: (payload, etag, last_modified_http, mtime)}`, filled on first read and guarded by a `threading.Lock`. The companion restarts on every deploy (`deploy/activate.sh:249 systemctl restart skypane-companion.service`), so a per-process cache is never stale in production. ETag: `'"%s"' % sha256(payload).hexdigest()[:32]`, strong and quoted.
3. Evaluate conditionals per RFC 9110 §13.2.2:
   - If `If-None-Match` is present, compare with the weak comparison (strip `W/`, split on commas, `*` matches). Ignore `If-Modified-Since` in that case.
   - Otherwise compare `If-Modified-Since` ≥ the file's mtime, truncated to seconds.
   - On a match, send 304 with `ETag`, `Last-Modified`, `Cache-Control` and the hardening headers, and no body.
4. Caddy: add `encode zstd gzip` to the **companion** block (`config-203-0-113-10.nip.io`) only. Leave the device block (byos, 8642) untouched: the device protocol and battery-log block are Phase 34/36 territory, and the firmware gains nothing (PNG is not in `encode`'s default match list).
   - Caddy suffixes a strong upstream ETag with `-<encoding>` and strips that suffix from an incoming `If-None-Match` before proxying, so origin-side 304s keep working through `encode`. [VERIFIED: github.com/caddyserver/caddy/blob/master/modules/caddyhttp/encode/encode.go]
   - Default `minimum_length` is 512 B, so 304s and tiny bodies are not encoded. [CITED: caddyserver.com/docs/caddyfile/directives/encode]
5. `Cache-Control` for CSS/JS is **decision D-1** (see Open Questions). Criterion 2, "second page load returns 304s", is only observable when the browser revalidates. With `max-age=300`, a second load inside 5 min is served from cache and makes no request at all. Chromium's normal reload also does not revalidate fresh sub-resources [ASSUMED].

### EFF-02: per-page scripts

**Current code.**
- `companion/layout.py:1848 page_shell()` emits 15 hard-coded `'<script src="%s" defer></script>\n'` lines (`:1983-1997`), with 15 positional values (`:2017-2060`).
- `login_shell()` (`:1705`) already emits exactly one (`login-card.js`).
- `health_page` emits `battery-trend.js` inside its own body when a chart is present. This per-page precedent is already pinned by `companion/test_status_pages_03.py:124-135`.

**Hook scan** (rendered HTML on a seeded state dir, measured in the scratchpad):

| Route | Scripts whose hooks are present |
|------|------|
| `/` Home | freshness, nav-dropdown, quick-switch, relative-time, submit-guard |
| `/display` | dirty-state, freshness, nav-dropdown, quick-switch, relative-time, submit-guard, theme-preview, value-controls (+ flash-cleanup with `?flash=`) |
| `/device` | dirty-state, nav-dropdown, poll-cooldown, quick-switch, relative-time, submit-guard (+ confirm-submit when the calendar is connected, `form[data-confirm]`; + value-controls for the dial/slider) |
| `/flights` | copy-button, flight-rows, freshness, list-filter, nav-dropdown, relative-time, submit-guard |
| `/health` | battery-trend (in body), freshness, nav-dropdown, relative-time, submit-guard (+ copy-button / list-filter if the registry table renders) |
| `/airlines` | list-filter, nav-dropdown, panel-lookup, relative-time, submit-guard |

The scan is state-dependent, so it is a hint and not the source of truth.

**Design.**
- Add a `scripts` parameter to `page_shell()`: an ordered tuple of `*_SCRIPT_SRC`. The shell prepends a **global** set present on every authenticated page: `nav-dropdown` (hamburger), `submit-guard` (every form), `flash-cleanup` (any page can carry `?flash=`), and `relative-time` (nav status and freshness line). It then generates the tags with `"".join(...)`, which removes 15 of the positional `%s`. Named templates stay Phase 40's (CMP-05).
- Define the per-route tuple once, next to `_PAGE_TITLES` in `app.py` (`_page_shell_for`, `:1689`, is the single call site for all GET tabs and the rejected-POST re-render).
- Each tuple must be the **superset over every state of that page**, including regions that `freshness.js` may swap in later. For example, Flights with zero rows at load still needs `flight-rows`, `copy-button` and `list-filter`, because rows can arrive by swap.
- 404/403 (`_not_found_page`, `_forbidden_page`) get the global set only.
- Do not delete any script route or file. Only inclusion changes.

**Correctness guard (behaviour, not source).** For every route, over several seeded states, parse the served HTML (`test-support/companion_markup.parse_html`). Every hook present in the DOM must have its script among the `script[src]` nodes. The hook → script mapping comes from the layout constants, not from JS source text.

### EFF-03: one connection per request/cycle, schema once, one transaction

**Current code.**
- `server/history_db.py:145 connect()` runs `sqlite3.connect`, `PRAGMA journal_mode=WAL`, `PRAGMA busy_timeout=5000` and `init_schema(conn)` (4 `CREATE TABLE IF NOT EXISTS` + 2 `CREATE INDEX IF NOT EXISTS` + commit) on **every** connection. `open_db()` at `:160` wraps it.
- Writers commit individually: `record_runway_event:192`, `record_device_health:200`, `record_wake_epoch:223`, `set_meta:430`. `ingest_caddy_battery_log:530` commits once per reading plus once for the offset.

**Measured per page** (seeded, mean of 5, in-process `InProcessAppServer`, `sqlite3.connect` wrapped):

| Route | connections | statements | per-caller |
|------|------|------|------|
| `/` | 12 | 108 | health `_safe_query` 7, home `_safe_query` 3, `_safe_last_checkin_ts` 1, `poll_cooldown_remaining` 1 |
| `/display` | 11 | 99 | health 7, config_page `_rule_suggestion_chips_html` 1, `_theme_live_preview_html` 1, +2 app |
| `/device` | 10 | 90 | health 7, config_page `wake_battery_rows` 1, +2 app |
| `/flights` | 10 | 90 | health 7, history `_safe_query` 1, +2 app |
| `/health` | 11 | 99 | health 9 (7 from `page_context` + stats + regularity in `render()`), +2 app |
| `/airlines` | 9 | 81 | health 7, +2 app |

**Measured per poll cycle:** 3 connections (`_last_source_fault:587`, `_record_history:622`, the `_notify_silence_transition` wrapper at `:924` or `:1286`), 3 `init_schema` runs and 2–4 COMMITs.

**Call sites to cover** (none need signature changes under the scope design):
- `companion/app.py:575` (`poll_cooldown_remaining`, which has **no** try/except), `:612`, `:630`, `:638`
- `companion/pages/home_page.py:168`, `health_page.py:427`, `history_page.py:410`
- `config_page.py:941`, `:1949`, `:2609`
- `server/poll_loop.py:594`, `:645`, `:924`, `:1286`

**Design (behaviour-level, no new plumbing through page signatures).**
1. `history_db.connection_scope(state_dir)`: a re-entrant context manager that stores a lazily-opened connection in a `ContextVar`. `open_db(state_dir)` yields the scoped connection when a scope for the same `history_db_path` is active on this thread, and does **not** close it. Otherwise it keeps today's open/close behaviour, so every test and CLI path keeps working unchanged.
2. Enter the scope in `Handler.do_GET` and `do_POST` (wrap the dispatch in `try/finally`) and in `poll_loop._run_once_locked` (or `run_once` inside the lock). A POST `/poll-now` nests the cycle scope inside the request scope, and re-entrancy makes it reuse the connection.
3. If opening the scoped connection fails, remember the failure for the rest of the scope and re-raise the same `sqlite3.Error`/`OSError` at each `open_db()`. Each caller's existing `except (sqlite3.Error, OSError)` then degrades exactly as today, without retrying the open 12 times.
4. Schema once per process: a module-level `_SCHEMA_READY` set keyed by `(path, st_dev, st_ino)`, checked after connect and guarded by a lock. Keying by inode means a restored or recreated `history.db` (Phase 37 backup/restore) gets its schema again. Keep `busy_timeout` per connection (cheap). `journal_mode=WAL` is persistent in the file, so setting it once per key is enough.
5. One transaction: remove the `conn.commit()` calls inside the writers. `open_db()` commits on clean exit and rolls back on exception, for a non-scoped connection **and** for a scoped one at the exit of the outermost `open_db` block that wrote. The simplest correct rule: `open_db` exit commits if `conn.in_transaction`.
   - `_record_history` does all its writes and then one explicit `conn.commit()`. The write transaction must never stay open across `_notify_silence_transition`'s ntfy HTTP call: that would hold the SQLite write lock and make the companion's `mark_poll_triggered` wait out `busy_timeout`.
   - Existing test seeding (`with open_db(...) as conn: record_...(conn, ...)`, ~100 sites across 14 test files) keeps working because the block exit commits.

**Where the 39/40 line is.** Do not introduce `CycleContext` (ARC-01) or pass `conn`/`ctx.db` through page functions (CMP-04). The scope makes today's call sites share one connection. Phase 39 can later replace it with an explicit field.

### EFF-04: lazy context, severity without markup, light freshness

**Current code.**
- `companion/app.py:972 page_context()` eagerly builds, for every tab:
  - `health_page.safe_health_state()` → `compute_health_state()` (`health_page.py:1064`) → `_read_health_inputs()` (`:2161`): 7 DB connections, `device_config` loaded a **second** time, `unresolved_rows()` reading `poll_state.json`. It builds `device_html`, `pipeline_html`, `battery_html`, `corroboration_html`, `device_detail_html` and `pipeline_detail_html`, and reads the off-box marker.
  - The remaining values: `device_config`, calendar registry, `_safe_last_checkin_ts`, `read_battery_critical`, `_resolve_flash_text`, `poll_cooldown_remaining`, `gallery_entries`, `runway_images_available`, `manual_resolutions`, `colour_rules`, `calendar_is_configured` and `calendar_secret_mode_is_unsafe`.
  - Measured: `compute_health_state` ≈ 3.1 ms of a 7–9 ms request on the dev box. Each connection ≈ 0.28 ms.
- `_not_found_page` (`:1063`) and `_forbidden_page` also build the full health state just for the nav dot.
- Only `home_page` (`:303`, which reads `pipeline_state`, `battery_state`, `device_state`, `device_detail_html`) and `health_page.render` (`:2262`) consume `ctx["health_state"]`. Every page needs `ctx["health_severity"]`.

**Design.**
1. Split `compute_health_state` into `health_signals(state_dir, now)` and the markup step. `health_signals` does the reads plus `device_state`, `pipeline_state`, `battery_state`, `disagreement_warn`, `coverage_state`, `source_fault`, `offbox`, `severity` and `anomalies`, with no HTML. `compute_health_state(state_dir, now)` becomes `signals + markup built from those same signals`, so the invariant "nav dot and banner can't disagree" (docstring `:1064`) still holds.
   - Several `_x_section()` helpers return `(html, state)` tuples, and one harness pins `_battery_section`'s 2-tuple (comment at `:1101`). Add state-only siblings (for example `_device_state(...)`) and have the `_section` builders reuse them. Do not change the pinned tuples.
2. `page_context()` returns a `dict` subclass with lazy loaders for the expensive keys: `health_state`, `gallery_entries`, `manual_resolutions`, `colour_rules`, `calendar_*` and `poll_cooldown_remaining`.
   - It must override `__getitem__`, `get` and `__contains__`, because `dict.get` never calls `__missing__`.
   - `health_severity` comes from `health_signals` unless `health_state` was already built, in which case it is taken from that one snapshot.
   - Page unit tests that build plain dict contexts are unaffected. A typed per-page context stays CMP-04 (Phase 40).
3. The 404/403 pages use `health_signals()` severity.
4. **Light freshness (decision D-2).** Recommended shape: a conditional GET on the **same page URL**, not a new route. This keeps CMP-01's route table untouched and keeps the existing browser tests that `page.route("**/health", ...)` meaningful.
   - `freshness.js`'s `doRefresh()` (fetch at ~`:470`; interval `AUTO_REFRESH_INTERVAL_MS = 45000`, `:17`; pages with `data-refresh-page`: home, display, health, flights) sends `If-None-Match: "<token>"`. It takes the token from a `data-refresh-token` attribute that `page_shell` renders on `<body>`, which no swap ever replaces.
   - `_render_tab` checks for `X-Requested-With: freshness` and a matching token **before** `page_context()`/`render()`, and answers `304` (`no-store`, `ETag`). On a mismatch it renders normally and sends the new token (ETag header plus body attribute).
   - `freshness.js` treats 304 as success with no swap: `succeed()`, and the loaded-at value comes from the response `Date` header. It sends no `If-None-Match` every N-th tick (for example every 5 min), which forces a full refresh as a safety net.
   - The token is a sha256 over cheap inputs read on the request's single connection:
     - `MAX(id)` of `runway_events`, `device_health` and `wake_epochs`
     - meta `last_detection` and `source_fault`
     - the `health_signals` states and severity and the anomaly list at `now`, which changes exactly when a staleness threshold is crossed
     - `frame_state.resolve_state` and `next_wake_iso`, for the Home/Display frame strip
     - the Paris date, for the regularity grid
     - `(mtime_ns, size)` of `device_config.json`, `poll_state.json`, the calendar registry, manual resolutions, colour rules, `panel.bin` and the off-box marker, plus the newest gallery name
     - lang, UI theme and the query string

### EFF-05: `poll_state` written once, only if changed, compact

**Current code.** `server/poll_loop.py:540 save_poll_state` does `atomic_io.atomic_write(path, json.dumps(state, indent=1))`. Save sites inside `_run_once_locked`:

| Branch | Save sites | Measured saves |
|------|------|------|
| Hold (early return) | conditional `:906` + unconditional `:928` | entry 2, repeat 1 (content unchanged) |
| Flight on display changed | unconditional `:1179` + final `:1290` | 2 |
| Held flight | conditional `:1245` + final `:1290` | 1–2 |
| Empty | conditional `:1274` + final `:1290` | 1 |

The final save exists because `_notify_*_transition` mutates `poll_state["notifications"]`. Measured size: 1,218 B at `indent=1` vs 1,036 B compact on a small state. Real states carry `enrichment_cache` (up to `CACHE_MAX_ENTRIES = 300`) and `unresolved_prefixes` (up to 200), so the saving grows with them.

**Readers:** `load_poll_state`, `wake.read_battery_critical`, `stub-server/byos_server.py:337`, the companion (`health_page:1644`, `airlines_page:656,901`) and Phase 42's `battery_low_active` read. All of them use `json.load`, so the format change is invisible to them. Nobody reads `poll_state.json`'s mtime (grep verified).

**Design.** Keep `save_poll_state(state_dir, state)` as an always-write public seam, since tests use it to seed (~15 sites). Change its serialization to `json.dumps(state, separators=(",", ":"))`. In `_run_once_locked`:
- after `load_poll_state`, capture `baseline = _serialize(poll_state)`;
- delete the mid-branch saves;
- at the two exits (the hold return and the final return) call one `_persist_poll_state(state_dir, poll_state, baseline)`, which writes only when `_serialize(poll_state) != baseline`.

Keep the ordering guarantee "panel.bin before poll_state": it is unchanged, because the save moves later, never earlier. The first cycle after deploy rewrites the file once, because the format changed.

### EFF-06: parallel providers, per-provider rate limit

**Current code.**
- `server/plane/detect.py:727-729`: `for i, name in enumerate(provider_names): if i > 0: time.sleep(MIN_SECONDS_BETWEEN_CALLS)` with `MIN_SECONDS_BETWEEN_CALLS = 1.1` (`:104`).
- `PROVIDER_TIMEOUT_S = 5.0` and `PROVIDER_DEADLINE_S = 8.0` (`:148-149`), so the worst case today is 8 + 1.1 + 8 s.
- Order is load-bearing: the first provider's record wins on agreement (`:785-795`).

Measured wall time (fake providers, 0.25 s simulated latency each):
- live cycles take 1.61–1.90 s, and every one records `sleeps=[1.1]`;
- with 0 latency, 1.11–1.26 s, so the fixed sleep is ~90 % of a no-network cycle;
- hold cycles take 0.004–0.25 s with no sleep.

**What "rate limit kept" means here.**
- adsb.fi documents 1 request/s on public endpoints, and 4xx responses count against it. [CITED: github.com/adsbfi/opendata]
- adsb.lol documents *dynamic* limits, not a fixed 1 req/s [CITED: adsb.lol/docs/open-data/api]. COMPLIANCE.md:204-213 says "both document 1 request/second", which is slightly inaccurate for adsb.lol and should be corrected in the same plan.
- Within one cycle each provider is called once, so no limit applies there.
- The real hazard is **two cycles back to back**: the timer cycle, then a `/poll-now` waiting on `poll.lock`, then the second cycle starting immediately. Today's sequential sleep accidentally guarantees ≥1.1 s between two calls to the *same* provider across such a pair. Removing it without a replacement would break that guarantee.

**Design.**
1. `poll_current_aircraft(..., last_call_at=None)` takes a `dict {provider: epoch_s}`. Each worker sleeps only for `max(0, last_call_at[name] + MIN_SECONDS_BETWEEN_CALLS - time.time())`, records `last_call_at[name] = time.time()` just before its request, then calls `query_provider`.
2. Run the workers in `ThreadPoolExecutor(max_workers=len(provider_names))`. Collect the futures **in provider order**, so `queried`, `failed` and `polled` keep `DEFAULT_PROVIDER_ORDER` semantics. Per-provider exception handling stays the same.
3. `poll_loop` reads the last-call times from `history.db` meta (for example keys `provider_last_call:adsbfi`) on the cycle connection before detection, and writes them in `_record_history`'s single transaction.
   - Use the meta table rather than `poll_state`, so `poll_state` does not change every live cycle, which would defeat EFF-05.
   - Hold cycles do not touch it.
   - The CLI `--provider all` path (airplanes.live) passes an in-memory dict.
4. detect stays a leaf module and never imports `history_db`.
5. Update the COMPLIANCE.md "Runtime behaviour" paragraph and the `skypane-poll.service` timeout comment (the budget is now ~8 s for providers, not 17 s).

### Anti-Patterns to Avoid
- **`encode` in the device (byos) site block.** It changes the device protocol surface for no gain.
- **A catch-all `/static/` handler or a route table.** Those are CMP-01/02 (Phase 40). Add the cache and validators behind the existing delegates.
- **Holding a write transaction across network I/O** (ntfy POST, provider calls).
- **Assembling provider results in completion order.** It silently changes which record reaches the renderer.
- **Checking "changed" against the live dict.** The dict is mutated in place, so the baseline must be the serialized string taken at load.
- **Asserting source text in tests** (`companion/test_suite_guards.py` G1–G12). Count through served responses, `sqlite3.connect` wrappers and monkeypatched seams.
- **Comments naming EFF-0x or Phase 38** (the `check_comment_history.py` CI gate).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Compression | gzip in `app.py` | Caddy `encode zstd gzip` | Content negotiation, `Vary`, ETag suffixing and minimum length are already handled [VERIFIED: encode.go] |
| HTTP date format and parse | strftime strings | `email.utils.formatdate(usegmt=True)` / `parsedate_to_datetime` | Locale-independent IMF-fixdate |
| Thread pool | manual `threading.Thread` + join bookkeeping | `concurrent.futures.ThreadPoolExecutor` | Futures carry exceptions and keep the ordered collection simple |
| Atomic JSON write | new temp-file logic | `server/atomic_io.atomic_write` (Phase 36) | Already the only writer path |
| HTML parsing in tests | regex over markup | `test-support/companion_markup.parse_html` / `_select` | Guard G11 spirit; existing helper |

## Runtime State Inventory

This is not a rename phase, but two runtime-state effects matter:

| Category | Items Found | Action Required |
|----------|-------------|-----------------|
| Stored data | `poll_state.json` on the VPS is in `indent=1` format. `history.db` gains new meta keys (`provider_last_call:*`) | None: readers use `json.load`, and the first cycle rewrites the file compact. Meta keys are created by upsert |
| Live service config | `/etc/caddy/sites/skypane.caddy` changes (encode). `activate.sh` validates it (`caddy validate`, `:211`) and reloads Caddy only when the site file changed | Deploy through the normal pipeline. Verify on the VPS with curl (manual checkpoint) |
| OS-registered state | None: unit files are unchanged, apart from an optional comment in `skypane-poll.service` | — |
| Secrets/env vars | None | — |
| Build artifacts | None (no build step). The in-memory static cache is per process and reset on every `systemctl restart skypane-companion` in `activate.sh:249` | — |

## Common Pitfalls

### Pitfall 1: The 304 cannot be observed through `max-age`
**What goes wrong:** the browser test for criterion 2 sees no request at all on the second load.
**How to avoid:** decide D-1. Assert at HTTP level with `If-None-Match`/`If-Modified-Since` (deterministic), and in the browser count origin statuses server-side (`InProcessAppServer` plus a `send_response` recorder) rather than relying on Playwright's cache reporting [ASSUMED behaviour].

### Pitfall 2: A script dropped from a page whose hook arrives by swap
**What goes wrong:** Flights loads with 0 rows. `freshness.js` later swaps rows in, but `flight-rows.js`/`copy-button.js` were never loaded.
**How to avoid:** per-route tuples are supersets over all states. The coverage test seeds empty and non-empty states for each page.

### Pitfall 3: Phase 42 adds an Update page
**What goes wrong:** 42 touches `companion/app.py` and `companion/layout.py` (nav) and adds `companion/pages/update_page.py` with a `data-confirm` Install button, which needs `confirm-submit.js`. If 42 lands after 38 and forgets its tuple, confirm dialogs disappear silently. The server-side confirmation page still applies (42 D-04), so this degrades rather than breaks.
**How to avoid:** the hook-coverage test iterates every tab route in `layout.NAV_TABS`/`_PAGE_TITLES`, so a new page without a tuple fails CI.

### Pitfall 4: Order-sensitive provider tests
**What goes wrong:** `server/test_plane_detection.py:430-441` asserts `recorded == ["adsbfi", "adsblol"]` on call order, which becomes nondeterministic.
**How to avoid:** assert the call set, and assert `diagnostics["queried"]` order, which stays deterministic. Tests that set `MIN_SECONDS_BETWEEN_CALLS = 0` (`:136`, `:437`, `:1180`) still work.

### Pitfall 5: Shared connection and threads
**What goes wrong:** `sqlite3` refuses cross-thread use (`check_same_thread=True`).
**How to avoid:** the provider worker threads never touch the DB, and the scope is thread-bound (ContextVar or threading.local). `ThreadingHTTPServer` runs one thread per request.

### Pitfall 6: `poll_cooldown_remaining` has no error guard
**What goes wrong:** `app.py:569` opens the DB without try/except, so a DB failure already 500s every tab.
**How to avoid:** under the scope design the failure re-raises identically, so behaviour is unchanged. Either keep it as is, or make it degrade to 0 in the lazy loader (a small robustness win). Say explicitly in the plan which one.

### Pitfall 7: Commit semantics change for writers
**What goes wrong:** removing `conn.commit()` from writers breaks any caller that writes and then reads from a *different* connection inside the same `with open_db` block.
**How to avoid:** `open_db` commits at exit; `_record_history` commits explicitly; run the full suite. The seeding helpers in the 14 test files use one block per seed, which is fine.

### Pitfall 8: Coverage floor (93 %)
**What goes wrong:** new defensive branches (scope failure memo, inode re-init, conditional-header parsing) drop coverage. This happened to 36-01.
**How to avoid:** plan tests for every branch.

### Pitfall 9: Freshness token misses an input
**What goes wrong:** a region stays stale while the token says "unchanged".
**How to avoid:** the forced full refresh every N ticks; a token-completeness test that mutates each input and expects a token change; and a no-op test (another identical cycle) that expects the same token.

## Code Examples

```python
# Conditional GET evaluation for a cached static asset (RFC 9110 §13.2.2 order).
def _not_modified(headers, etag, mtime_s):
    inm = headers.get("If-None-Match")
    if inm is not None:
        tags = [t.strip() for t in inm.split(",")]
        return "*" in tags or any(t.removeprefix("W/") == etag for t in tags)
    ims = headers.get("If-Modified-Since")
    if ims:
        try:
            return int(mtime_s) <= email.utils.parsedate_to_datetime(ims).timestamp()
        except (TypeError, ValueError, OverflowError):
            return False
    return False
```

```python
# Providers in parallel, results in provider order (the first provider still wins on agreement).
with concurrent.futures.ThreadPoolExecutor(max_workers=len(provider_names)) as pool:
    futures = [(name, pool.submit(_rate_limited_query, name, ...)) for name in provider_names]
    for name, fut in futures:            # submission order, not as_completed()
        queried.append(name)
        try:
            aircraft = fut.result()
        except (requests.RequestException, ValueError) as exc:
            failed.append(name); continue
        ...
```

```python
# Write-once poll_state.
def _serialize(state):
    return json.dumps(state, separators=(",", ":"))
baseline = _serialize(poll_state)          # right after load_poll_state()
...
if _serialize(poll_state) != baseline:
    atomic_io.atomic_write(_poll_state_path(state_dir), _serialize(poll_state))
```

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|------------------|--------|
| Time-based caching only (`max-age`) | Validators (strong ETag) + revalidation, compression at the edge | 304s instead of full re-downloads; ~3.8× smaller CSS on the wire (140 KB → 37 KB gzip-6) |
| Sequential polite sleeps between different upstreams | Per-upstream rate limiting, concurrent requests | A cycle takes about as long as the slowest provider |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | A Chromium normal reload does not revalidate fresh sub-resources, so `max-age=300` hides 304s | EFF-01 / Pitfall 1 | Only affects how criterion 2 is tested, not correctness |
| A2 | The VPS Caddy (official Cloudsmith repo, `provision.sh:72`) is recent enough to have the ETag-suffix/strip logic in `encode` | EFF-01 | If older, a compressed response keeps the upstream ETag. The worst case is a 200 instead of a 304, never a wrong body |
| A3 | ESP-IDF `esp_http_client` sends no `Accept-Encoding` (grep found none in `firmware/main`) | EFF-01 | Irrelevant if encode stays out of the device block |
| A4 | Python 3.14's `threading.Thread` does not inherit the parent's context by default (non-free-threaded build) | EFF-03 | The scope is set per request anyway. Using `threading.local` removes the question |
| A5 | adsb.lol has no fixed documented per-second limit (docs say "dynamic") | EFF-06 | Only COMPLIANCE.md wording is affected; keeping ≥1.1 s per provider is conservative either way |

## Open Questions (developer decisions)

1. **D-1: `Cache-Control` for CSS/JS.** This has user-visible impact.
   - (a) `public, no-cache` + ETag: every page load revalidates, 304s are observable, and there is never a window where new HTML runs with old JS after a deploy. Today's 5-minute window is a real risk, because layout constants are duplicated and pinned equal in JS. The cost is ~6–8 small 304 round-trips per page.
   - (b) Keep `max-age=300` + ETag: fewer requests, but the post-deploy staleness window stays and criterion 2 is only observable after 5 min.
   - (c) Content-hashed URLs (`?v=<sha>`) + `immutable`: zero requests, but every `*_SCRIPT_SRC` constant and route becomes dynamic, which overlaps CMP-02.
   - **Recommendation: (a).**
2. **D-2: Freshness mechanism.**
   - (a) Recommended: conditional GET on the same page URL with a server-computed input token, plus a forced full refresh every ~5 min. Saves both CPU and bytes when nothing changed, but the token could miss an input (bounded by the forced refresh).
   - (b) A new `/freshness` JSON route: same token logic, but adds a route (CMP-01 overlap) and changes the URL that the existing browser tests break with `page.route("**/health")`.
   - (c) An ETag computed from the rendered body: no staleness risk and bytes saved, but no CPU saved. Server-rendered relative-time fallback text changes every minute, so hits would be rare.
3. **Should `poll_cooldown_remaining` degrade instead of 500 on a DB error?** This is a tiny robustness change. Recommend yes, inside the lazy loader. It does not need the developer unless the planner wants strict behaviour-preservation.

## Coordination and Overlap

| File | 38 change | Also touched by | Note |
|------|-----------|-----------------|------|
| `deploy/Caddyfile`, `deploy/tests/test_caddyfile.py` | `encode zstd gzip` in the companion block + a rendered-text test | 37-11: no (it touches byos unit, env example, README, test_units). 42: no | Safe |
| `deploy/skypane-poll.service` | comment only (timeout budget) | 37-11 does not; 36 did | Optional; skip if 37-11 is still open |
| `deploy/README.md` | avoid | 37-11 **and** 42 | Put the compression note in `ARCHITECTURE.md`/`COMPLIANCE.md` instead, or leave it to Phase 41 |
| `stub-server/byos_server.py` | **none** | 37-11, 42 | 38 must not touch byos |
| `companion/app.py` | static helper, `_render_tab` 304, scope in `do_GET`/`do_POST`, per-route scripts, lazy ctx | 42 (Update route, 2 plans) | Merge conflict likely; whichever lands second rebases. The hook test catches a missing tuple |
| `companion/layout.py` | `page_shell(scripts=...)`, `data-refresh-token` | 42 (nav entry) | Different regions of the file |
| `server/poll_loop.py` | scope, save-once, provider meta | 42 (`battery_low_active` read only), 39 (ARC-01 rewrite) | 38 keeps `run_once`'s shape; 39 then splits it |
| `server/plane/detect.py`, `COMPLIANCE.md` | parallel + rate state | none | — |
| `server/history_db.py` | scope, schema-once, writer commits | 42's backup (`deploy/backup/skypane_backup.py` uses `sqlite3` directly, unaffected) | — |
| `companion/static/freshness.js` | 304 path, token header, forced refresh | none | Browser tests in `test_browser_ux_02/03/health_drawings/quiet_wake` exercise it |

**The 39/40 line:** 38 changes *when* and *how often* work happens, not *where code lives*.
- No new modules beyond small helpers inside existing files.
- No route table, no typed context, no named templates.
- No `state_store`; `save_poll_state` stays in `poll_loop`.
- No `CycleContext`.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python (dev venv) | tests | ✓ | 3.11.15 (`server/.venv`); CI/prod 3.14 | Avoid 3.12+-only sqlite3 APIs |
| pytest, xdist, pytest-socket, playwright (Python pkg) | tests | ✓ | from `requirements-dev.txt` | — |
| Chromium headless shell | browser tests | ✗ locally (no `~/.cache/ms-playwright`) | — | Skips locally, **required in CI** (`CI=true` fails on missing browser) |
| caddy binary | validating `encode` | ✗ locally and in CI (`deploy/tests/test_caddyfile.py` docstring) | — | Rendered-text test in CI. `caddy validate` runs on the VPS in `activate.sh:211`. Manual curl checkpoint for `Content-Encoding` |
| VPS access | live before/after bytes | developer-only | — | `checkpoint:human-verify` |

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (+ xdist, pytest-cov, pytest-socket `--disable-socket --allow-hosts=127.0.0.1,::1,localhost`, pytest-playwright) — `pyproject.toml [tool.pytest.ini_options]` |
| Config file | `pyproject.toml` (coverage `fail_under = 93`) |
| Quick run command | `server/.venv/bin/python -m pytest -n auto -q server/test_history_db_scope.py server/test_poll_efficiency.py companion/test_static_cache.py companion/test_page_scripts.py companion/test_request_connections.py companion/test_freshness_token.py deploy/tests/test_caddyfile.py` |
| Full suite command | `./scripts/run-all-tests.sh` (CI also sets `SKYPANE_REQUIRE_BROWSER=1` implicitly via `CI=true`) |

### Instruments (build before any change; Wave 0)
Add a stdlib helper module `test-support/efficiency_probe.py`, with its own test in `test-support/test_test_support.py` or a new `test-support/test_efficiency_probe.py`:
- `count_connections()`: a context manager that wraps `sqlite3.connect` (as the scratchpad did) and returns connects, `init_schema` calls (via a monkeypatched `history_db.init_schema`), statements and COMMITs through `set_trace_callback`.
- `route_weight(server, path, cookie)`: identity bytes, gzip-6 bytes, the `script[src]` list via `companion_markup.parse_html`, and elapsed ms.
- `cycle_probe(monkeypatch)`: patches `detect.time.sleep` to record calls, `detect.query_provider` with a latency fake, and `poll_loop.save_poll_state`/`atomic_io.atomic_write` for the `poll_state.json` path to count writes. It returns wall time and counts.

Add a CLI `scripts/measure_efficiency.py` (outside the coverage source) that uses the probe to print the baseline tables in markdown. Run it before the first code change and after the last; both outputs go into `38-EFF-BASELINE.md`, the same pattern as `37-SEC-BASELINE.md`. Record the commit SHA, machine, Python version and N. Timings are informative, not asserted.

### Baseline numbers measured during research (for cross-check)
Machine: dev container, Python 3.11.15, `InProcessAppServer`, seeded state (30 device_health rows, 30 runway_events), mean of 5.

| Route | HTML bytes (identity / gzip-6) | ms | `<script>` | SQLite conns |
|---|---|---|---|---|
| `/` | 23,112 / 4,388 | 9.1 | 15 | 12 |
| `/display` | 65,856 / 7,830 | 9.0 | 15 | 11 |
| `/device` | 18,491 / 4,119 | 7.4 | 15 | 10 |
| `/flights` | 93,750 / 6,536 | 9.1 | 15 | 10 |
| `/health` | 36,367 / 6,574 | 8.2 | 16 | 11 |
| `/airlines` | 52,899 / 6,644 | 7.4 | 15 | 9 |
| `/login` | 1,493 / 758 | 1.0 | 1 | 0 |
| `/static/style.css` | 140,426 / 36,939 | 1.1 | — | 0 |
| 15 shell scripts (sum) | 143,568 / 51,921 | — | — | 0 |

A first authenticated page load is therefore ≈ 300–380 KB identity / ≈ 93–97 KB if gzipped (today it is sent identity). Each 45 s `freshness.js` tick re-downloads the page HTML, 15–94 KB identity.

Poll cycle (fake providers, 0.25 s latency each):

| Branch | wall | sleeps | conns | init_schema | commits | poll_state saves |
|---|---|---|---|---|---|---|
| empty sky (first / repeat) | 1.69 / 1.63 s | [1.1] | 3 | 3 | 3 / 2 | 1 / 1 |
| flight detected | 1.77 s | [1.1] | 3 | 3 | 4 | 2 |
| same flight again | 1.64 s | [1.1] | 3 | 3 | 3 | 2 |
| nothing new, flight on screen | 1.61 s | [1.1] | 3 | 3 | 2 | 1 |
| display_off hold entry / repeat | 0.25 / 0.004 s | [] | 3 | 3 | 3 / 2 | 2 / 1 |

With 0 s latency, the live branches take 1.11–1.26 s, so the fixed sleep dominates.

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| EFF-01 | Every `/static/*.css/.js` response carries a strong ETag and Last-Modified. `If-None-Match` equal (also `W/`-prefixed and in a list) → 304 with no body. `If-Modified-Since` ≥ mtime → 304. A mismatched tag → 200 with the full body. The body is served from memory (file read counted once per process via a monkeypatched `open` in the in-process server) | integration (in-process server) | `pytest companion/test_static_cache.py -x` | ❌ Wave 0 |
| EFF-01 | Second page load: origin sees 304 for every static request (recorder on `send_response`), per D-1 | browser | `pytest companion/test_static_cache.py -m browser -x` | ❌ Wave 0 |
| EFF-01 | The rendered companion block contains `encode zstd gzip`; the device block does not | unit (deploy) | `pytest deploy/tests/test_caddyfile.py -x` | ✅ extend |
| EFF-01 | Live: `curl -s -o /dev/null -w '%{size_download}' --compressed` and `-H 'Accept-Encoding: zstd'` show `Content-Encoding` and the transferred bytes before and after | manual checkpoint (VPS) | recorded in `38-EFF-BASELINE.md` | — |
| EFF-02 | For each tab route × {empty, seeded} states: the `script[src]` set equals global ∪ that route's declared tuple, and every DOM hook has its script. 404/login keep their own sets | integration | `pytest companion/test_page_scripts.py -x` | ❌ Wave 0 |
| EFF-02 | Existing behaviour holds with fewer scripts (freshness swaps, flight rows, theme preview, dial) | browser (existing) | `pytest companion/test_browser_ux_0*.py -x` | ✅ |
| EFF-03 | GET on every tab route → exactly 1 `sqlite3.connect` and ≤1 `init_schema` per process. A second request → 0 `init_schema` | integration (in-process) | `pytest companion/test_request_connections.py -x` | ❌ Wave 0 |
| EFF-03 | One poll cycle on every branch → 1 connection; all history writes in 1 COMMIT; no transaction open during the notify send (the fake sender asserts `not conn.in_transaction`) | unit | `pytest server/test_poll_efficiency.py -x` | ❌ Wave 0 |
| EFF-03 | Scope: re-entrant reuse, failure memo, an inode change re-runs the schema, `open_db` commits on exit and rolls back on exception | unit | `pytest server/test_history_db_scope.py -x` | ❌ Wave 0 |
| EFF-04 | A non-Home/Health tab never builds health markup (monkeypatched `_device_section` etc. count 0). Severity from `health_signals` equals `compute_health_state()["severity"]` across the existing severity fixtures | unit/integration | `pytest companion/test_request_connections.py companion/test_health_signals.py -x` | ❌ Wave 0 |
| EFF-04 | Freshness: an unchanged state gives 304 on `X-Requested-With: freshness` + `If-None-Match`. Each input mutation (new runway event, device_health row, device_config save, gallery file, off-box marker, crossing the pipeline-stale threshold with a fake `now`) changes the token. An identical second poll cycle does not | integration | `pytest companion/test_freshness_token.py -x` | ❌ Wave 0 |
| EFF-04 | Browser: a tick with an unchanged state does no swap and shows no failure badge; after seeding a new event the next tick swaps the region; the forced full refresh happens after N ticks | browser | `pytest companion/test_freshness_token.py -m browser -x` | ❌ Wave 0 |
| EFF-05 | Per branch: ≤1 write of `poll_state.json` per cycle; 0 writes on an unchanged repeat (hold repeat, empty-sky repeat); the file parses and has no newlines/indent (`json.loads` round-trip + byte-length ≤ compact) | unit | `pytest server/test_poll_efficiency.py -k poll_state -x` | ❌ Wave 0 |
| EFF-06 | With fake providers each sleeping L s: cycle wall < 1.1 s + L (for example < L + 0.5), `detect.time.sleep` never called with 1.1 between different providers, the result still comes from adsbfi on agreement, and `diagnostics["queried"] == ["adsbfi", "adsblol"]` | unit | `pytest server/test_plane_detection.py server/test_poll_efficiency.py -k parallel -x` | ✅ extend / ❌ |
| EFF-06 | Rate limit kept: two back-to-back cycles with a fake clock → each provider's second call starts ≥ `MIN_SECONDS_BETWEEN_CALLS` after its first (the recorded per-provider start times), and last-call meta persists across process-like reloads | unit | `pytest server/test_poll_efficiency.py -k rate -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** the quick run command for the touched files, plus `scripts/check_comment_history.py check`
- **Per wave merge:** `./scripts/run-all-tests.sh`
- **Phase gate:** full suite green in CI (browsers required), `38-EFF-BASELINE.md` has before and after tables, and the VPS curl checkpoint is recorded

### Wave 0 Gaps
- [ ] `test-support/efficiency_probe.py` + its test
- [ ] `scripts/measure_efficiency.py` → the before tables committed to `38-EFF-BASELINE.md`
- [ ] New test modules listed above (companion ones must respect `test_suite_guards.py`: fixtures from `companion/conftest.py`, `InProcessAppServer` for monkeypatch-visible counting, no source reads, writes only under `tmp_path`)

## Security Domain

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no change | — |
| V3 Session Management | yes | 304/freshness responses for session-gated pages go through `require_session()` first. Page responses stay `Cache-Control: no-store`. Public static assets stay pre-auth (unchanged) |
| V4 Access Control | yes | The freshness 304 must be computed **after** `require_session()`, so an unauthenticated probe cannot learn "page changed?" |
| V5 Input Validation | yes | Parse `If-None-Match`/`If-Modified-Since` defensively (malformed → treat as no match, never raise). Never echo header bytes into responses |
| V8 Data Protection | yes | `Vary: Accept-Encoding` from Caddy. Never mark a session-gated response `public`. Keep `send_bytes`'s fail-closed `public=False` default |
| V14 Configuration | yes | `encode` only in the companion block, and the site snippet stays free of global options (host-file import constraint) |

| Pattern | STRIDE | Mitigation |
|---------|--------|-----------|
| BREACH-style compression oracle on pages that mix secrets with attacker-reflected input | Information disclosure | The companion pages carry no CSRF token (CSRF is the Origin/Sec-Fetch-Site check, SEC-03) and reflect little attacker input. The session cookie is in the request, not the body. Low risk; note in the plan [ASSUMED risk assessment] |
| Token as a change oracle | Information disclosure | Session-gated only |
| Provider rate-limit violation → IP ban (adsb.fi counts 4xx too) | Denial of service | Persisted per-provider last-call spacing |

## Sources

### Primary (HIGH confidence)
- Current code on `main` f4d9709. The measurements come from throwaway scripts in the scratchpad (`measure_routes.py`, `hooks.py`, `measure_cycle.py`, `prof_ctx.py`), run against `InProcessAppServer` and `poll_loop.run_once`.
- Caddy `encode` source: https://github.com/caddyserver/caddy/blob/master/modules/caddyhttp/encode/encode.go (ETag suffix/strip, Vary, 206 disable)
- Caddy `encode` docs: https://caddyserver.com/docs/caddyfile/directives/encode (defaults zstd+gzip, `minimum_length` 512, match list)

### Secondary (MEDIUM confidence)
- adsb.fi open data: https://github.com/adsbfi/opendata (1 req/s public; 4xx count)
- adsb.lol API: https://www.adsb.lol/docs/open-data/api/ and https://api.adsb.lol/docs (dynamic limits)

### Tertiary (LOW)
- Chromium reload/revalidation behaviour for sub-resources (training knowledge, A1)

## Metadata

**Confidence breakdown:**
- Current-state findings: HIGH (measured)
- Designs for EFF-01/02/03/05/06: HIGH/MEDIUM (stdlib, precedents in repo)
- EFF-04 freshness token: MEDIUM (completeness risk, needs D-2)

**Research date:** 2026-09-26
**Valid until:** until Phase 42 or 37-11 lands on `main` (re-check the `app.py`/`layout.py` line numbers then)
