---
phase: 40-companion-architecture-routes-pages-templates-i18n-keys
plan: 03
subsystem: api
tags: [route-table, static-cache, dispatch, http-server, companion]

# Dependency graph
requires:
  - phase: 40-companion-architecture-routes-pages-templates-i18n-keys
    provides: "40-01's structural guard (companion/test_structure_guards.py) and committed render baseline (companion/testdata/render_baseline.json) this plan is verified against"
provides:
  - "companion/static_files.py: STATIC_ROUTES allowlist ({route: StaticAsset(path, content_type, cache_control)}) plus the Phase 38 in-memory revalidation cache (static_entry/not_modified/if_none_match_matches/read_static_bytes), moved verbatim from companion/app.py"
  - "companion/routes.py: Exact/PrefixSuffix matchers, RouteMatch, Route, ROUTES (one table for every GET/POST route), match(method, path, query)"
  - "companion/app.py: Handler._dispatch(method) as the sole GET/POST dispatch, replacing _dispatch_get()/_dispatch_post(); Handler._serve_static_route(route); Handler._handle_login_get()/_handle_logout_post()/_handle_rule_delete_post()"
  - "companion/test_route_table.py: table-driven auth coverage proving the public set and every gated route's unauthenticated response against the committed baseline"
affects: ["40-04", "40-05", "40-06", "40-07", "40-08", "40-09", "40-10", "40-11", "40-12", "40-13", "40-14", "40-15", "40-16"]

tech-stack:
  added: []
  patterns:
    - "One route table ((method, matcher, handler, auth_required) namedtuples) instead of hand-repeated if-chains with a require_session() call per branch — gating is now a field checked exactly once in Handler._dispatch(), never duplicated per route"
    - "companion/routes.py never imports companion.app (that would be a cycle since app.py imports routes.py); route constants that exist only in app.py today are duplicated as literals in routes.py, the same duplicated-not-imported contract app.py's own QUICK_*_ROUTE constants already used"
    - "A monkeypatch of a re-exported alias (e.g. app_module._read_static_bytes) never reaches the real caller once the underlying function lives in a different module (static_files.py) — a test that wants to change behaviour patches the owning module directly"
    - "A route-table auth-coverage test derives its own 'must be gated' worklist from the FIXED public-exemption set (LOGIN_ROUTE + STATIC_ROUTES), not from each route's own auth_required field, so a route whose auth_required is wrongly flipped stays in the worklist and its real HTTP response — not the table's own bookkeeping — is what fails"

key-files:
  created:
    - companion/static_files.py
    - companion/routes.py
    - companion/test_route_table.py
  modified:
    - companion/app.py
    - companion/test_static_cache.py
    - companion/test_structure_guards.py
    - test-support/companion_render_snapshot.py
    - test-support/companion_structure.py
    - test-support/computed_style_snapshot.py

key-decisions:
  - "Kept _static_entry/_if_none_match_matches/_not_modified/_STATIC_CACHE/_read_static_bytes as plain module-level aliases in app.py (bound to the real static_files.* functions/objects) rather than rewriting _serve_static()'s body, so that method's existing logic and docstring needed zero changes"
  - "Added three small new Handler methods (_handle_login_get, _handle_logout_post, _handle_rule_delete_post) to hold multi-statement dispatch logic a single lambda couldn't express, instead of duplicating that logic (or _validated_next_route/auth.revoke plumbing) inside companion/routes.py, which must never import companion.app"
  - "Derived test_route_table.py's gated-route worklist from a fixed public-exemption set rather than filtering ROUTES by auth_required, so the plan's own required mutation check (flipping one route's auth_required to False) fails via a real observed HTTP response, not just an absent parametrize case"

requirements-completed: [CMP-01, CMP-02, CMP-06]

duration: ~100min
completed: 2026-09-27
---

# Phase 40 Plan 03: Route table and static-asset allowlist Summary

Replaced companion/app.py's 18 hand-written `if path == X: return self._serve_..._script()` branches and two over-80-line `_dispatch_get()`/`_dispatch_post()` if-chains with one static-asset allowlist (`companion/static_files.py`) and one route table (`companion/routes.py`) that `Handler._dispatch(method)` walks — gating a route is now a table field checked exactly once, never a hand-repeated `require_session()` call.

## Performance

- **Duration:** ~100 min
- **Completed:** 2026-09-27
- **Tasks:** 2/2 completed
- **Files created:** 3
- **Files modified:** 6

## Accomplishments

- `companion/static_files.py` holds the 18 static-asset route constants, the Phase 38 in-memory revalidation cache, and a `STATIC_ROUTES` allowlist (`{route: StaticAsset(path, content_type, cache_control)}`); every asset is looked up by exact dict key, so no request-derived path segment is ever joined onto `STATIC_DIR`. `companion/app.py` rebinds every constant and the cache object under its historical name so every existing call site and test keeps resolving.
- Deleted `_serve_stylesheet()`, `_serve_script_file()`, and all 17 `_serve_*_script()` delegate methods from `companion/app.py`, replaced by one `Handler._serve_static_route(route)` that looks the route up in `STATIC_ROUTES`.
- `companion/routes.py` defines `Exact`/`PrefixSuffix` matchers, `RouteMatch`, `Route`, and one `ROUTES` tuple covering every GET and POST route (including the 18 static routes, generated from `STATIC_ROUTES` itself) in today's if-chain order. `match(method, path, query)` returns the first matching `(Route, RouteMatch)` or `None`.
- `companion/app.py`'s `Handler._dispatch(method)` is now the single dispatch point: the POST-only Origin/Sec-Fetch-Site gate still runs first, then `routes.match()`, then the route's own `auth_required` field decides whether `require_session()` runs, then the route's handler is called. `do_GET()`/`do_POST()` both call `self._dispatch(...)` inside their unchanged `history_db.connection_scope()` wrapper. `_render_tab()` no longer calls `require_session()` itself — the table gates every tab before it runs.
- `companion/test_route_table.py` proves: the public set is exactly GET/POST `/login` plus one GET per `STATIC_ROUTES` entry; every gated route (built from a route-identity list independent of the route's own `auth_required` field) answers an anonymous request with the same 303-to-`/login` status/Location the committed pre-refactor baseline recorded; every baseline route is matched by exactly one `ROUTES` entry (no route dropped, none declared twice — the one baseline 404 sample is the documented exception); and every route's handler is callable.
- `grep -o "self.require_session()" companion/app.py | wc -l` now prints `1` (down from 24); `companion_structure.long_functions()` reports zero offenders in `companion/app.py` (the two removed `_dispatch_get`/`_dispatch_post` entries dropped from `test_structure_guards.py`'s `PENDING_LONG_FUNCTIONS`).

## Task Commits

Each task was committed atomically:

1. **Task 1: Static allowlist module (CMP-02)** - `9477df5` (feat)
2. **Task 2: Route table and table-driven dispatch (CMP-01)** - `f50872d` (feat)

_No TDD RED→GREEN split recorded for Task 2's tests: `test_route_table.py`'s four tests all passed on first run against the already-written `routes.py`/`app.py` changes (written together, then verified) — the required "proves it can fail" property was instead demonstrated directly via the mutation check below, per Task 2's own acceptance criteria._

## Files Created/Modified

- `companion/static_files.py` - STATIC_ROUTES allowlist, StaticAsset namedtuple, the Phase 38 static-asset cache (`_StaticEntry`, `_STATIC_CACHE`, `read_static_bytes`, `static_entry`, `if_none_match_matches`, `not_modified`)
- `companion/routes.py` - Exact, PrefixSuffix, RouteMatch, Route, ROUTES, match()
- `companion/test_route_table.py` - the four route-table auth-coverage tests
- `companion/app.py` - rebinds the 18 static route constants and cache from static_files; `_serve_static_route()`; `_handle_login_get()`/`_handle_logout_post()`/`_handle_rule_delete_post()`; `Handler._dispatch(method)` replacing `_dispatch_get()`/`_dispatch_post()`; `_render_tab()` no longer self-gates
- `companion/test_static_cache.py` - two monkeypatches (`_read_static_bytes`, `_STYLE_CSS_PATH`) retargeted to `static_files` itself, since a monkeypatch of app.py's re-exported alias never reaches the real caller
- `companion/test_structure_guards.py` - removed the two now-nonexistent `_dispatch_get`/`_dispatch_post` entries from `PENDING_LONG_FUNCTIONS`
- `test-support/companion_render_snapshot.py`, `test-support/companion_structure.py`, `test-support/computed_style_snapshot.py` - three comments updated from `_dispatch_get()`/`_dispatch_post()` to the real current names (`routes.py`'s ROUTES table, `_handle_login_get()`, `Handler._dispatch`), staleness caused directly by this plan's rename

## Decisions Made

- Kept `_static_entry`/`_if_none_match_matches`/`_not_modified`/`_STATIC_CACHE`/`_read_static_bytes` as plain module-level aliases in `app.py` bound to the real `static_files.*` objects, so `_serve_static()`'s existing body and docstring needed zero edits.
- Added three small Handler methods (`_handle_login_get`, `_handle_logout_post`, `_handle_rule_delete_post`) rather than duplicating their multi-statement logic (or `app._validated_next_route`/`auth.revoke` plumbing) inside `routes.py`, which must never import `companion.app`.
- `test_route_table.py`'s gated-route worklist is built from a fixed public-exemption set (`LOGIN_ROUTE` + `STATIC_ROUTES`), not from filtering `ROUTES` by `auth_required` — so the mutation check below fails via a real observed HTTP response, not merely an absent parametrize case.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `test_static_cache.py`'s two monkeypatches did not reach the real caller after the move**
- **Found during:** Task 1 verification (`test_static_bytes_are_read_from_disk_at_most_once_per_process` failed: 0 disk reads instead of 1)
- **Issue:** `monkeypatch.setattr(app_module, "_read_static_bytes", counting)` patches app.py's re-exported alias, but `static_files.static_entry()` calls the name `read_static_bytes` looked up in `static_files`'s own module namespace — the alias is never consulted. Same problem for `monkeypatch.setattr(app_module, "_STYLE_CSS_PATH", missing_path)`: that constant no longer exists as an app.py attribute at all once the path is baked into a `StaticAsset` namedtuple inside `STATIC_ROUTES` at import time.
- **Fix:** Retargeted the first monkeypatch to `static_files.read_static_bytes`. Retargeted the second to `monkeypatch.setitem(static_files.STATIC_ROUTES, app_module.STYLE_ROUTE, original_asset._replace(path=missing_path))`, swapping the allowlist entry itself (restored automatically at teardown) rather than a path constant.
- **Files modified:** `companion/test_static_cache.py`
- **Verification:** `companion/test_static_cache.py` full file passes (15/15).
- **Committed in:** `9477df5` (Task 1 commit)

**2. [Rule 1 - Bug] `ruff` F401 on `companion.pages.home_page` after the dispatch removal**
- **Found during:** Task 2 post-edit `ruff check companion`
- **Issue:** `home_page` was imported into `companion/app.py` solely for the old `_dispatch_get()`'s `self._render_tab(HOME_ROUTE, home_page.render)` call; that call now lives in `companion/routes.py`, which imports `home_page` itself, leaving app.py's import unused.
- **Fix:** Removed `home_page` from `companion/app.py`'s `from companion.pages import (...)` block.
- **Files modified:** `companion/app.py`
- **Verification:** `ruff check companion` clean.
- **Committed in:** `f50872d` (Task 2 commit)

**3. [Rule 1 - Bug] A phase/ticket ID slipped into a new docstring**
- **Found during:** Task 2, `scripts/check_comment_history.py check` after staging
- **Issue:** `Handler._dispatch()`'s own docstring named "CMP-01" directly, which `check_comment_history.py` flags (CLAUDE.md: no plan/ticket/phase IDs in comments) — the checker only scans tracked files, so this would have passed pre-commit but failed once staged/committed.
- **Fix:** Reworded to describe the same reasoning ("the one table that makes every route's gating a field of the route itself") with no ID literal. Also removed the same requirement-ID literal from `companion/test_route_table.py`'s module docstring, caught by the same self-check before staging.
- **Files modified:** `companion/app.py`, `companion/test_route_table.py`
- **Verification:** `scripts/check_comment_history.py check` clean after staging all new/modified files.
- **Committed in:** `f50872d` (Task 2 commit)

**4. [Rule 1 - Bug] Three test-support comments referenced the now-deleted `_dispatch_get()`/`_dispatch_post()` names**
- **Found during:** Task 2, a repo-wide grep for the deleted method names after removing them
- **Issue:** `test-support/computed_style_snapshot.py`, `test-support/companion_render_snapshot.py` (two spots), and `test-support/companion_structure.py`'s own docstring example all named `_dispatch_get()`/`_dispatch_post()`, methods this plan's own change deletes — directly caused by this task, out of the plan's declared `files_modified` but a one-line accuracy fix each.
- **Fix:** Updated each comment to name the real current entry point (`companion/routes.py`'s ROUTES table, `_handle_login_get()`, or `Handler._dispatch`).
- **Files modified:** `test-support/companion_render_snapshot.py`, `test-support/companion_structure.py`, `test-support/computed_style_snapshot.py`
- **Verification:** `ruff check test-support` clean; `companion/test_render_baseline.py` and `companion/test_structure_guards.py` still pass (both exercise the touched modules).
- **Committed in:** `f50872d` (Task 2 commit)

---

**Total deviations:** 4 auto-fixed (3 Rule 1 bugs surfaced by the plan's own verification commands, 1 Rule 1 comment-accuracy fix directly caused by this task's rename)
**Impact on plan:** All four were necessary for the refactor to be correct (Task 1's cache tests would otherwise silently test nothing) or clean (ruff/comment-history gates this plan's own `<verification>` block requires). No scope creep — no production behaviour outside `companion/app.py`'s dispatch and static-serving path was touched.

## Issues Encountered

None beyond the deviations above.

## Mutation Check (Task 2 acceptance criterion)

Flipped the `HEALTH_ROUTE` GET route's `auth_required` from `True` to `False` in `companion/routes.py`, ran `companion/test_route_table.py`, then reverted:

- `test_public_routes_are_exactly_login_and_static_assets` failed: `Extra items in the left set: ('GET', Exact(path='/health'))`.
- `test_every_gated_route_redirects_an_anonymous_request[GET_health]` failed: `GET /health: expected the committed baseline's 303, got 200` — a real anonymous HTTP request to `/health` was actually served unauthenticated, not merely a bookkeeping mismatch.

Both failures named `/health` directly. Reverted before committing; `companion/test_route_table.py` (32/32) and the full Task 2 verify list pass clean afterward.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `companion/app.py`'s dispatch surface is now a table (`companion/routes.py`) plus a static allowlist (`companion/static_files.py`); later CMP-03 (file split) and CMP-04 (typed per-page context) plans can build on `routes.py`'s handler lambdas without touching the if-chain shape that no longer exists.
- `companion/app.py` is still 2,466 lines (over the 1,500-line ceiling) and remains in `test_structure_guards.py`'s `PENDING_OVERSIZED_FILES` — CMP-03's later file split is expected to shrink it, not this plan.
- No blockers.

---
*Phase: 40-companion-architecture-routes-pages-templates-i18n-keys*
*Completed: 2026-09-27*

## Self-Check: PASSED

All 3 created files confirmed present on disk (`companion/static_files.py`, `companion/routes.py`, `companion/test_route_table.py`); both task commit hashes (`9477df5`, `f50872d`) confirmed present in git history.
