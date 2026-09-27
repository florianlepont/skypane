---
phase: 38-efficiency-companion-poll-cycle-storage
plan: 12
subsystem: companion
tags: [http-caching, etag, freshness, javascript, python, pytest, playwright]

# Dependency graph
requires:
  - phase: 38-efficiency-companion-poll-cycle-storage
    provides: "38-06's page_shell(scripts=...) and companion/app.py's _page_shell_for()/_render_tab() single call sites, threaded through by this plan's refresh_token=/etag= additions"
  - phase: 38-efficiency-companion-poll-cycle-storage
    provides: "38-10's _LazyContext and the shared ctx['_health_signals'] loader - this plan's token forces it early, so a later render() reuses the same one snapshot rather than paying for a second health_page.health_signals() read"
provides:
  - "companion/app.py: _page_freshness_token(route, ctx, query) - a sha256 (truncated to 32 hex chars) over a route's own inputs, with zero markup rendered to compute it"
  - "companion/app.py: _render_tab()'s 304 branch (send_not_modified()), checked only after require_session() and page_context(), only on the four refresh pages (layout.REFRESH_PAGE_*)"
  - "companion/app.py: _if_none_match_matches() extracted from _not_modified() (38-02), shared by the static-asset 304 path and this plan's page-freshness 304 path"
  - "companion/layout.py: REFRESH_TOKEN_ATTR ('data-refresh-token') and page_shell(refresh_token=...), rendered on <body> only when given"
  - "companion/static/freshness.js: reads/validates the token once at load, sends If-None-Match on every tick but every ~7th (FORCED_REFRESH_EVERY_N_TICKS), treats a 304 as success with no swap (loaded-at from the response's own Date header), and re-writes both the in-memory token and the body's own data-refresh-token attribute after a 200 swap"
affects: ["39 (ARC-01 run_once split touches server/poll_loop.py's own shape this plan's DB-signal reads depend on, not its behaviour)", "42 (OTA - a new page must declare its own layout.REFRESH_PAGE_* membership deliberately; this plan adds no route)"]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "A page-input token computed from cheap reads (three sources: the request's own scoped SQLite connection, a handful of file stat() calls, and the ctx's own already-shared health_signals() snapshot) rather than from the rendered body - the D-2 shape: conditional GET on the SAME page URL, no new route, no body-hash ETag"
    - "Forcing a shared _LazyContext loader key (ctx['_health_signals']) to resolve BEFORE render() runs, so the token computation and the page's own markup build pay for exactly one health_page.health_signals() call between them, never two"
    - "A test-helper fix pattern for a shared browser-test utility whose own precondition quietly went stale: _force_refresh() (companion/test_browser_ux_03.py) used to always get a full 200 to swap from: once freshness.js starts sending a real token, an unchanged page correctly gets a 304 instead, so four pre-existing swap-identity tests now seed one genuine detection (the same server/history_db.record_runway_event()-backed helper the file already used elsewhere) before each call that needs a real swap"

key-files:
  created:
    - companion/test_freshness_token.py
  modified:
    - companion/app.py
    - companion/layout.py
    - companion/static/freshness.js
    - companion/test_browser_ux_03.py

key-decisions:
  - "The database-backed piece of the token dropped its originally-planned third MAX(id) watermark (wake_epochs) after CI caught server/test_config_history.py::test_nothing_under_companion_reads_the_epoch_table - a repo-wide guard that no file under companion/ may so much as mention that table, since it accrues data for a later phase. Fixed in a separate fix(38-12) commit: two watermarks (runway_events, device_health) plus the existing meta keys; no completeness test asserted a wake_epochs case, so nothing else needed to change."
  - "_page_freshness_token() reads ctx['_health_signals'] directly (the _LazyContext's own internal loader key, shared with 'health_state'/'health_severity') rather than calling health_page.health_signals() a second time - this is the one deliberate coupling to 38-10's lazy-context shape this plan takes, and it is why companion/test_request_connections.py's one-connection-per-request invariant still holds with the token in place."
  - "gallery_newest reads ctx['gallery_entries'] (the _LazyContext's own cached list) rather than a second, direct gallery_entries(state_dir, limit=1) call - the first version of this loader called the module function directly and was caught by companion/test_page_context.py's own at-most-once-per-request assertion (Home was paying for two scandir() calls, not one) before this plan's own commit landed."
  - "_if_none_match_matches() was extracted out of 38-02's _not_modified() as a small, behaviour-preserving refactor (a None sentinel for 'header absent', distinct from a real match/no-match verdict) so the page-freshness 304 path and the static-asset 304 path share one comma-split/W/-strip matcher, per the plan's own explicit instruction to reuse it."
  - "freshness.js reads the token ONCE at page load (not re-read from the DOM on every tick) and updates both the cached value and the body's own data-refresh-token attribute after a swap - <body> is never itself a swap target, so without the explicit attribute write the DOM would keep reporting the page's ORIGINAL token forever even after several real swaps; caught by this plan's own browser test before the GREEN commit landed."

requirements-completed: [EFF-04]

# Metrics
duration: ~2h10min
completed: 2026-09-26
---

# Phase 38 Plan 12: Light freshness check (EFF-04, D-2) Summary

**A conditional GET on the same page URL: `_page_freshness_token()` hashes a route's own inputs (three cheap reads, no markup ever built) into a 32-hex token, `_render_tab()` answers a matching freshness tick with a bodiless 304 before `render()` ever runs, and `freshness.js` sends the token, treats a 304 as success with no swap, and forces a full refresh roughly every five minutes to bound whatever the token might miss.**

## Performance

- **Duration:** ~2h10min
- **Completed:** 2026-09-26T21:20:00Z (approx.)
- **Tasks:** 2 completed (each its own RED/GREEN TDD cycle), plus one CI-driven fix commit
- **Files modified:** 4 (1 created, 3 modified) across the two tasks, plus the fix commit

## Accomplishments

- `companion/app.py`: `_page_freshness_token(route, ctx, query)` builds the token from: the two per-table `MAX(id)` watermarks (`runway_events`, `device_health`) and the `last_detection`/`source_fault` meta keys, read in one `_freshness_db_signal()` helper through the request's own single scoped connection (a read failure collapses the whole group to the literal `"unavailable"`, still hashed, never a 500); the shared `health_signals()` snapshot's twelve fields (`severity`, `anomalies`, every section state, `next_wake_iso`/`effective_interval_s`/`hold_reason`); `(mtime_ns, size)`/`"missing"` stats for `device_config.json`, `poll_state.json`, the calendar/manual-resolutions/colour-rules registries, `panel.bin` and the off-box marker (`"disabled"` when unconfigured); the newest gallery filename (via the ctx's own cached `gallery_entries` list); `lang`, `ui_theme`, `route` and the raw query string; plus, for Home/Display, `frame_state.resolve_state()`'s own resolved value, and for Health, the `last_pipeline_run` meta key and the Europe/Paris calendar date.
- `_render_tab()` computes the token right after `page_context()` but before `render()`, only for the four `layout.REFRESH_PAGE_*` routes; a request whose `X-Requested-With` equals `"freshness"` and whose `If-None-Match` already matches gets `send_not_modified()` (304, `Cache-Control: no-store`, the same `ETag`, hardening headers, no body) with `render()` never called at all. A normal navigation carrying a stale but matching `If-None-Match` (no freshness header) is never answered 304. `send_html()` gained an optional `etag=` parameter; `_page_shell_for()` gained `refresh_token=None`, forwarded to `layout.page_shell()`. `/device` and `/airlines` (not refresh pages) carry neither an `ETag` nor a `data-refresh-token` attribute.
- `companion/layout.py`: `REFRESH_TOKEN_ATTR = "data-refresh-token"`; `page_shell(refresh_token=None)` renders it on `<body>`, escaped, only when given.
- `companion/static/freshness.js`: reads and validates the token once at load (`/^[0-9a-f]{16,64}$/`); sends it as `If-None-Match` on every tick except roughly every 7th (`FORCED_REFRESH_EVERY_N_TICKS`, ~5 minutes at the 45s cadence), which sends none at all; checks `response.status === 304` **before** the existing `!response.ok` branch (a 304 has `ok === false`, same as any other non-2xx); on a 304, sets `loadedAtMs` from the response's own `Date` header (falling back to `Date.now()` only if that header is missing/unparseable), clears the in-flight guard and succeeds with no swap at all; after a successful 200 swap, re-reads the token from the fetched document and writes it back onto **both** the in-memory variable and the live `<body>`'s own `data-refresh-token` attribute (never itself a swap target, so it would otherwise report the page's original token forever).
- `companion/test_freshness_token.py` (22 tests, new): HTTP-level shape/304/stability/completeness tests (18) plus 4 real-Chromium browser tests (unchanged tick → 304, no swap, no failure badge; a seeded new row → 200, swap, and a changed body token; the forced full refresh landing within 7 ticks; loaded-at tracking a 304's own `Date` header via a visibilitychange catch-up proof).
- Four pre-existing `companion/test_browser_ux_03.py` checks (`test_a_swap_leaves_the_region_holding_focus_alone`, `test_a_swap_leaves_a_pending_region_alone`, `test_the_picture_fades_only_when_the_picture_changed`, `test_a_refresh_landing_mid_flip_does_not_repaint_the_switch`) needed one genuine seeded detection before each `_force_refresh()` call that expects a real swap - see Deviations.

## Task Commits

Each task ran its own RED → GREEN TDD cycle:

1. **Task 1 RED: failing tests for the token/304 path** - `4f65efe` (test) — 17 of 18 fail against pre-token `companion/app.py`/`layout.py` (the 18th passes trivially: neither `/device` nor `/airlines` carries the attribute either way)
2. **Task 1 GREEN: server token, 304 branch, ETag/data-refresh-token** - `14076af` (feat) — all 18 pass; full companion suite green
3. **Task 2 RED: failing browser tests for the freshness.js token round trip** - `d9b3aad` (test) — 3 of 4 new browser tests fail against pre-token `freshness.js` (the forced-refresh check passes trivially); also fixes the four pre-existing `test_browser_ux_03.py` checks, confirmed harmless (25/25 pass) against the pre-token script
4. **Task 2 GREEN: freshness.js sends the token, treats 304 as success, forces refresh** - `511cbf3` (feat) — all 4 new browser tests and all 25 `test_browser_ux_03.py` browser tests pass
5. **Fix (CI-driven): drop wake_epochs from the freshness token's DB signal** - `895e347` (fix) — `server/test_config_history.py::test_nothing_under_companion_reads_the_epoch_table` caught the literal string in `_freshness_db_signal()`'s SQL and a dict key; dropped to two watermarks

**Plan metadata:** (this commit) - `docs(38-12): complete light freshness check plan`

## Files Created/Modified

- `companion/app.py` - `FRESHNESS_FETCH_HEADER_VALUE`; `_if_none_match_matches()` (extracted from `_not_modified()`); `_freshness_file_stamp()`/`_freshness_file_stamps()`/`_freshness_db_signal()`/`_freshness_paris_date()`/`_page_freshness_token()`; `send_html(etag=None)`; `send_not_modified()`; `_page_shell_for(refresh_token=None)`; `_render_tab()`'s new 304 branch; `_FRESHNESS_PAGE_SLUGS`; `_FRESHNESS_SIGNAL_FIELDS`.
- `companion/layout.py` - `REFRESH_TOKEN_ATTR`; `page_shell(refresh_token=None)`.
- `companion/static/freshness.js` - `TOKEN_ATTR`/`TOKEN_RE`/`FORCED_REFRESH_EVERY_N_TICKS`; `readToken()`; `currentToken`/`ticksSinceForcedRefresh`; `doRefresh()`'s conditional header and 304 branch; the post-swap token/attribute write-back.
- `companion/test_freshness_token.py` - New: 22 tests (18 HTTP-level, 4 browser).
- `companion/test_browser_ux_03.py` - Four pre-existing swap-identity tests changed from the shared read-only `server` fixture to their own dedicated `make_app_server`, each now seeding one genuine `_record_a_new_detection()` call before a `_force_refresh()` that needs a real 200-and-swap.

## Decisions Made

See `key-decisions` in the frontmatter above (wake_epochs removal, the `_LazyContext` coupling for `_health_signals`/`gallery_entries`, the `_if_none_match_matches()` extraction, and freshness.js's own read-once/write-back token discipline).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `_page_freshness_token()`'s gallery read paid for two `scandir()` calls on Home instead of one**
- **Found during:** Task 1 GREEN, running the full companion suite per the plan's own instruction
- **Issue:** The first version of the token's `gallery_newest` input called `gallery_entries(state_dir, limit=1)` directly (a second, independent read), bypassing the `_LazyContext`'s own cached `"gallery_entries"` loader that Home's `render()` also reads - `companion/test_page_context.py::test_expensive_registries_load_lazily_at_most_once_per_request` caught the resulting `2 <= 1` failure on `/`.
- **Fix:** Changed to `ctx["gallery_entries"]` (the shared, cached list), taking `[0]` as the newest filename - the same cache Home's own render pays for exactly once.
- **Files modified:** `companion/app.py`
- **Verification:** `companion/test_page_context.py` and the full companion suite (not-browser) both green.
- **Committed in:** `14076af` (Task 1 GREEN) - found and fixed before that commit landed, not a separate commit.

**2. [Rule 1 - Bug in pre-existing tests] Four `test_browser_ux_03.py` swap-identity checks assumed every forced refresh gets a full 200**
- **Found during:** Task 2's own verify command (the plan's required `test_browser_ux_03.py -m browser` run)
- **Issue:** `test_a_swap_leaves_the_region_holding_focus_alone`, `test_a_swap_leaves_a_pending_region_alone`, `test_the_picture_fades_only_when_the_picture_changed` and `test_a_refresh_landing_mid_flip_does_not_repaint_the_switch` each call the shared `_force_refresh()` helper and then assert, as a CONTROL, that some region (`.page-header__freshness`) really was swapped - true unconditionally before this plan (every tick always got a full re-render), now false whenever nothing server-side actually changed since the last tick, since the light freshness check correctly answers that case with a bodiless 304 instead.
- **Fix:** Each now seeds one genuine new detection (`_record_a_new_detection()`, the same `server/history_db.record_runway_event()`-backed helper this same file already uses for `test_a_new_detection_is_highlighted_and_an_existing_row_is_not`) immediately before each `_force_refresh()` call that needs a real swap - and switched from the shared, read-only module-scoped `server` fixture to a dedicated `make_app_server`, so the seeded rows never leak into another test sharing that fixture. Confirmed the fix is harmless against the PRE-token `freshness.js` too (25/25 pass either way).
- **Files modified:** `companion/test_browser_ux_03.py`
- **Verification:** `companion/test_browser_ux_03.py -m browser` (25/25) both before and after `freshness.js`'s own GREEN commit.
- **Committed in:** `d9b3aad` (Task 2 RED, test-only) and confirmed again in `511cbf3` (Task 2 GREEN).

**3. [Rule 3 - Blocking, CI-reported] `wake_epochs` mentioned under `companion/` violated a repo-wide guard**
- **Found during:** CI, after Task 1's GREEN commit (`14076af`) had already landed
- **Issue:** `server/test_config_history.py::test_nothing_under_companion_reads_the_epoch_table` scans every file under `companion/` for the literal string `"wake_epochs"` and fails if found at all - the table accrues data for a later phase and nothing in this one may read it yet. `_freshness_db_signal()`'s third `MAX(id)` watermark (`wake_epochs`) violated this in both the raw SQL string and a dict key.
- **Fix:** Dropped the third watermark; the DB signal now carries exactly the two the plan's own interfaces text names first (`runway_events`, `device_health`) plus the unchanged meta keys. No completeness test in this plan asserted a `wake_epochs`-specific case, so nothing else needed to change.
- **Files modified:** `companion/app.py`
- **Verification:** The guard test, the full `companion`/`server` suite (not-browser, 2528 passed), and `companion/test_freshness_token.py` all green afterward.
- **Committed in:** `895e347` (fix, separate from the two task commits, as flagged by the coordinator).

---

**Total deviations:** 3 auto-fixed (2 Rule 1, 1 Rule 3 CI-driven). No architectural changes, no scope creep beyond the plan's own `files_modified` list plus the one pre-existing test file its own behaviour change required touching.

## Issues Encountered

None beyond the three deviations above.

## User Setup Required

None - no external service configuration, environment variable, or deploy-pipeline change. The companion service picks up the new behaviour on its next normal restart.

## Next Phase Readiness

- EFF-04 is now fully closed (with 38-05's severity/markup split and 38-10's lazy `page_context`): `page_context()` is lazy, Health severity is computed without markup, and the light freshness check answers an unchanged tick with a bodiless 304 without ever rendering the page.
- `companion/test_freshness_token.py` (22 tests) plus the full companion/server suite (not-browser, 2528 passed) plus the whole-repo suite with the Playwright shim (3021 passed, 1 known local Chromium-baseline failure unrelated to this plan - `test_the_heros_grouping_holds_at_both_widths_and_owes_nothing_to_a_script` - 6 skipped, coverage 94.21% against the 93.0% floor) are all green. `ruff` and `scripts/check_comment_history.py check` are both clean.
- Phase 38 (efficiency-companion-poll-cycle-storage) is now complete at 12/13 plans on this branch, with EFF-01 through EFF-06 all closed. The one remaining item is the phase's own closing verification pass (not a numbered plan in this file).
- No blockers.

---
*Phase: 38-efficiency-companion-poll-cycle-storage*
*Completed: 2026-09-26*

## Self-Check: PASSED

- FOUND: companion/app.py
- FOUND: companion/layout.py
- FOUND: companion/static/freshness.js
- FOUND: companion/test_freshness_token.py
- FOUND: companion/test_browser_ux_03.py
- FOUND: 4f65efe
- FOUND: 14076af
- FOUND: d9b3aad
- FOUND: 511cbf3
- FOUND: 895e347
