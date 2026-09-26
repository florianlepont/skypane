---
phase: 38-efficiency-companion-poll-cycle-storage
verified: 2026-09-26T21:37:28Z
status: human_needed
score: 10/10 must-haves verified (4 ROADMAP criteria + 6 requirement truths); 1 live-VPS item pending human check
overrides_applied: 0
human_verification:
  - test: "Live Caddy compression on the production companion host (38-13 Task 2), after this branch is deployed"
    expected: "style.css / freshness.js answer with content-encoding zstd (or gzip), an ETag ending -zstd/-gzip, Cache-Control 'public, no-cache', Vary: Accept-Encoding, style.css about 37 KB or less; a revalidation with that ETag prints revalidate=304 size=0; the device host returns no Content-Encoding. Rows recorded in 38-EFF-BASELINE.md 'Live compression (VPS)' (38-13 Task 3), or marked pending deploy."
    why_human: "No caddy binary in CI or this container; only the VPS runs Caddy, and VPS access is developer-only."
---

# Phase 38: Efficiency — companion, poll cycle, storage — Verification Report

**Phase Goal:** Pages and poll cycles do only the work they need: compressed and cacheable static files, per-page scripts, one SQLite connection per request/cycle, no throwaway markup, one state write per cycle, no fixed sleep between providers.
**Verified:** 2026-09-26T21:37:28Z
**Status:** human_needed
**Re-verification:** No, this is the initial verification.

## Goal Achievement

### Observable Truths (ROADMAP success criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Page weight and request time measured before/after on every route | VERIFIED | `38-EFF-BASELINE.md` has Before (commit 2b1d7fd) and After (79e1039) tables from the same `scripts/measure_efficiency.py` for all 6 tabs, /login and 17 static assets, plus Deltas. I re-ran the instrument (`--label verify --repeats 2`) and got the same After figures, e.g. `/` 22327 B identity, 6 scripts. |
| 2 | Second page load returns 304s for static files | VERIFIED | `companion/app.py` `_serve_static` (l.1693) uses an in-memory `_STATIC_CACHE`, a strong sha256 ETag, Last-Modified, and `_not_modified` (RFC 9110 order). CSS/JS are served with `public, no-cache`. My re-run printed `style.css`/`freshness.js` → `304`, 0 bytes. `test_static_cache.py::test_second_page_load_gets_304_for_every_static_request` (browser) passes. |
| 3 | SQLite connections: 1 per page request, 1 per poll cycle | VERIFIED | `do_GET`/`do_POST` wrap dispatch in `history_db.connection_scope` (app.py l.2247, l.2606). `run_once` nests `connection_scope` inside `poll_cycle_lock`. In my re-run every tab showed `sqlite_conns=1.0` and every poll branch `connections=1`, `commits=1`. `test_request_connections.py` and `test_poll_efficiency.py` pass. |
| 4 | Poll cycle wall time before/after, no fixed 1.1 s sleep | VERIFIED | `detect.poll_current_aircraft` now uses `ThreadPoolExecutor`. It waits only on each provider's own `last_call_at` spacing (`_spaced_query`) and collects results in submission order. At latency 0, empty-sky time is 1.1688 s before and 0.0665 s after (0.0909 s in my re-run). The only After sleeps are concurrent same-provider spacing from back-to-back measurement cycles; no sleep between providers remains. |

### Requirement-level truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 5 | EFF-01: compression, validators + 304, static bytes in memory | VERIFIED (code). The live effect needs a human check. | `deploy/Caddyfile` has `encode zstd gzip` in the `config-…` (companion) block only, and the device block has none. `deploy/tests/test_caddyfile.py` asserts both. `_read_static_bytes` runs at most once per process (tested). |
| 6 | EFF-02: only the scripts each page uses, no build step | VERIFIED | `layout.SHELL_SCRIPT_ORDER` + `GLOBAL_PAGE_SCRIPTS`, `_PAGE_SCRIPTS` per NAV_TABS route, wired through `_page_shell_for(... scripts=_PAGE_SCRIPTS[route])`. Script counts per page went from 15/16 to 6–10. `test_page_scripts.py` covers hooks for every tab. |
| 7 | EFF-03: one connection per request/cycle, schema once per process, one transaction | VERIFIED | `history_db.connection_scope` (thread-local, lazy, failure memo) and `_SCHEMA_READY` keyed by (realpath, dev, ino) with a re-run when the file is empty. `write_batch` + `_commit` wrap `_record_history`. ntfy is sent after the batch commits (`test_no_write_transaction_open_during_notify_send…` passes). |
| 8 | EFF-04: lazy context, severity without markup, light freshness check | VERIFIED | `_LazyContext` + lazy loaders. `health_page.health_signals`/`safe_health_signals`/`health_state_from_signals`. `_page_freshness_token` runs before `render()`. A freshness tick with a matching token returns a bodiless 304. My re-run: all four refresh pages → 304/0 B. |
| 9 | EFF-05: poll_state saved once, only if changed, compact | VERIFIED | `_persist_poll_state` compares against a baseline serialized at load time and is called only at the two exits of `_run_once_locked`. Output is compact JSON (`separators=(",",":")`). Re-run: unchanged repeats write 0 times, other branches write at most once. |
| 10 | EFF-06: providers in parallel, per-provider rate limit kept across cycles | VERIFIED | `META_PROVIDER_LAST_CALL_PREFIX` meta rows are loaded before detection and written inside the cycle's `write_batch`. Hold and injected-snapshot paths skip them. `test_provider_rate.py` passes, including the back-to-back spacing test. |

**Score:** 10/10 truths verified.

### Locked decisions and boundaries

| Item | Status | Evidence |
|------|--------|----------|
| D-1: CSS/JS `Cache-Control: public, no-cache` + strong ETag/Last-Modified, 304 | Honoured | `_serve_stylesheet`/`_serve_script_file` pass `"public, no-cache"`. The ETag is a quoted sha256 prefix with no `W/`. Runway images keep `private, max-age=300` but also get validators. |
| D-2: conditional GET on same URL, token without rendering, after auth, forced refresh, no new route | Honoured | `_render_tab`: `require_session()` → `page_context()` → token → 304 only when `X-Requested-With: freshness` and If-None-Match match, all before `render(ctx)`. There is no `/freshness` route. `freshness.js` `FORCED_REFRESH_EVERY_N_TICKS = 7` (45 s × 7 ≈ 5 min) omits If-None-Match. The token is validated against `/^[0-9a-f]{16,64}$/` before it is sent. |
| Phase 39/40 boundaries (no route table, state_store, CycleContext, typed context) | Respected | The diff from ed56221 adds no such identifiers. The only new non-test files are `scripts/measure_efficiency.py` and `test-support/efficiency_probe.py`. `run_once` keeps its signature. |
| `stub-server/byos_server.py`, `deploy/README.md` untouched | Respected | `git diff ed56221 HEAD` is empty for both, and `git log` shows no phase commit touching them. |

### Required Artifacts

| Artifact | Status | Details |
|----------|--------|---------|
| `test-support/efficiency_probe.py`, `scripts/measure_efficiency.py` | VERIFIED | Runs offline and reproduces the After tables. |
| `companion/app.py` (`_serve_static`, `_PAGE_SCRIPTS`, `connection_scope`, `_LazyContext`, `_page_freshness_token`) | VERIFIED | Substantive and wired (see truths above). |
| `companion/layout.py` (`SHELL_SCRIPT_ORDER`, `GLOBAL_PAGE_SCRIPTS`, `data-refresh-token`) | VERIFIED | Wired from `_page_shell_for`. |
| `companion/pages/health_page.py` (`health_signals` etc.) | VERIFIED | Used by the lazy loaders and by the 404/403 nav dot. |
| `companion/static/freshness.js` | VERIFIED | Sends If-None-Match, handles 304 before `!response.ok`, and forces a refresh. |
| `server/history_db.py` (`connection_scope`, `write_batch`, schema-once, meta prefix) | VERIFIED | |
| `server/poll_loop.py` (`_persist_poll_state`, scope in `run_once`, provider meta) | VERIFIED | |
| `server/plane/detect.py` (parallel, per-provider spacing) | VERIFIED | |
| `deploy/Caddyfile` + test | VERIFIED | |
| `38-EFF-BASELINE.md` Before/After/Deltas/Criteria | VERIFIED | The "Live compression (VPS)" table is still a placeholder until 38-13 Tasks 2–3 (human item). |

### Key Link Verification

| From | To | Status |
|------|----|--------|
| `_serve_stylesheet/_serve_script_file/_serve_runway_image` | `_serve_static(` | WIRED |
| `_page_shell_for` | `layout.page_shell(scripts=_PAGE_SCRIPTS[route])` | WIRED |
| `run_once` | `history_db.connection_scope(` inside `poll_cycle_lock` | WIRED |
| `_record_history` | `history_db.write_batch(` + `META_PROVIDER_LAST_CALL_PREFIX` | WIRED |
| `Handler.do_GET/do_POST` | `history_db.connection_scope(self.args.state_dir)` | WIRED |
| `_run_once_locked` exits | `_persist_poll_state(state_dir, poll_state, poll_state_baseline)` | WIRED (both exits) |
| `_run_once_locked` | `detect.poll_current_aircraft(..., last_call_at=provider_last_calls)` | WIRED |
| `page_context` | `safe_health_signals` / `health_state_from_signals` | WIRED |
| `freshness.js doRefresh` | `_render_tab` via `fetch(window.location.href)` with If-None-Match | WIRED |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| After tables reproduce | `server/.venv/bin/python scripts/measure_efficiency.py --label verify --repeats 2` | exit 0. Tabs: 1 conn each. Static: 304/0 B. Freshness: 304/0 B. Poll: 1 conn, 1 commit, ≤1 write per branch, 0 on repeats. Latency-0 empty sky: 0.0909 s. | PASS |
| Full suite | `SKYPANE_REQUIRE_BROWSER=1 ./scripts/run-all-tests.sh` | 3021 passed, 6 skipped (root-permission skips), 1 failed. Coverage 94.21% against a 93.0% gate. | PASS (the only failure is the known local-only old-Chromium artefact `test_the_heros_grouping_holds_at_both_widths_and_owes_nothing_to_a_script`, which is outside this phase's scope) |
| Comment-history guard | `scripts/check_comment_history.py check` | exit 0 | PASS |
| Lint | `ruff check .` | All checks passed | PASS |

### Probe Execution

Step 7c: SKIPPED. The phase declares no `probe-*.sh`; its instrument is `scripts/measure_efficiency.py`, which is run above.

### Requirements Coverage

| Requirement | Source Plans | Status | Evidence |
|-------------|--------------|--------|----------|
| EFF-01 | 38-01, 38-02, 38-13 | SATISFIED (live Caddy effect needs a human check) | Truths 2, 5 |
| EFF-02 | 38-01, 38-06, 38-13 | SATISFIED | Truth 6 |
| EFF-03 | 38-01, 38-03, 38-07, 38-08, 38-13 | SATISFIED | Truths 3, 7 |
| EFF-04 | 38-01, 38-05, 38-10, 38-12, 38-13 | SATISFIED | Truth 8 |
| EFF-05 | 38-01, 38-09, 38-13 | SATISFIED | Truth 9 |
| EFF-06 | 38-01, 38-04, 38-11, 38-13 | SATISFIED | Truths 4, 10 |

No requirements are orphaned: REQUIREMENTS.md maps only EFF-01..06 to Phase 38, and every plan claims at least one of them.

### Anti-Patterns Found

None. The lines added by the phase contain no TBD/FIXME/XXX/TODO/HACK markers. Nothing is a stub: every new helper is called from production paths and covered by tests.

### Human Verification Required

#### 1. Live Caddy compression (38-13 Task 2 → Task 3)

**Test:** After deploy, run the curl commands in 38-13-PLAN.md Task 2 against the companion host. Also run them against the device host.
**Expected:** The companion host answers `content-encoding: zstd`/`gzip` with an ETag suffixed `-zstd`/`-gzip`, `public, no-cache`, and `vary: Accept-Encoding`. style.css comes back at about 37 KB or less. Revalidating with that ETag gives `304 size=0`. The device host sends no Content-Encoding. Record the rows in the "Live compression (VPS)" table of `38-EFF-BASELINE.md`, or mark them "pending deploy".
**Why human:** There is no caddy binary in CI or this container, and VPS access is developer-only. The origin-side 304 through Caddy relies on Caddy stripping the encoding suffix from If-None-Match, which only the live check proves.

### Gaps Summary

There are no gaps. All four ROADMAP criteria and all six EFF requirements hold in the code, and I reproduced the numbers independently with the phase's own instrument. The one open item is the developer's live VPS compression check. It is non-blocking by design and is listed above as the human-verification item.

---

_Verified: 2026-09-26T21:37:28Z_
_Verifier: Claude (gsd-verifier)_
