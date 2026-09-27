---
phase: 40-companion-architecture-routes-pages-templates-i18n-keys
plan: 09
subsystem: api
tags: [http-server, refactor, module-split, companion]

# Dependency graph
requires:
  - phase: 40-companion-architecture-routes-pages-templates-i18n-keys
    provides: "40-03's companion/routes.py ROUTES table and companion/static_files.py static allowlist, whose handler lambdas reference Handler methods by name — this plan keeps every moved method name identical so that table keeps resolving unchanged"
provides:
  - "companion/request_body.py: parse_content_length(headers), drain_capped_body(rfile, length, cap) -> (raw or None, over_cap) — the shared capped-body drain behind Handler.read_form()/_read_upload_body()"
  - "companion/flash.py: FLASH_MESSAGES, FLASH_ROLES, every FLASH_KEY_*, resolve_flash_text(), poll_cooldown_remaining()"
  - "companion/freshness.py: the four refresh-page slugs and every _freshness_*()/_page_freshness_token() helper behind the light freshness check's 304 path"
  - "companion/login_page.py: login_body(), login_reveal_toggle_html(), render_login_page(), not_found_page(), forbidden_page() — pure markup functions"
  - "companion/post_actions.py: SettingsActionsMixin (illustration replace, manual-resolution add/delete, colour-rule add/delete, calendar connect/disconnect, notifications test) plus _illustration_filenames(), parse_single_uploaded_file(), MAX_ILLUSTRATION_UPLOAD_BYTES, and _POLL_LOCK"
  - "companion/app.py: Handler._choice_cookie_header(name, value, choices, max_age_s) — the shared Set-Cookie builder behind _handle_theme_post()/_handle_lang_post()"
affects: ["40-11 (moves page_context() next, the other half of CMP-03's app.py file split)", "40-10", "40-12", "40-13", "40-14", "40-15", "40-16"]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "One capped read-then-drain loop (companion/request_body.drain_capped_body()) behind two callers that keep their own cap and degrade value ({} vs None), instead of two near-identical inline loops"
    - "A Handler mixin (companion/post_actions.SettingsActionsMixin) for a cohesive group of POST handlers, inherited ahead of BaseHTTPRequestHandler (Handler(SettingsActionsMixin, BaseHTTPRequestHandler)) so method names — and companion/routes.py's lambda references to them — never change"
    - "Extraction-with-rebind: every name a new module owns is re-imported into companion/app.py under its historical name (FLASH_KEY_*, _resolve_flash_text, _page_freshness_token, _POLL_LOCK, MAX_ILLUSTRATION_UPLOAD_BYTES, parse_single_uploaded_file, _illustration_filenames) so every existing call site and test assertion against companion.app keeps resolving, and no new module ever imports companion.app (verified by grep, no cycle)"
    - "Pure-markup extraction: companion/login_page.py's functions take already-resolved request state (ui_theme, health_alert) as arguments and never touch self/the request; the Handler keeps a thin method that gathers that state (self._resolved_ui_theme(), self._is_authenticated(), prefs.set_request_prefs()) and calls in"
    - "_page_freshness_token is called through app.py's own module global inside _render_tab() (not a direct freshness.* call), so test_freshness_token.py's monkeypatch.setattr(app, \"_page_freshness_token\", ...) still reaches every call site — Python resolves a function's globals against its DEFINING module, not the instance's class"

key-files:
  created:
    - companion/request_body.py
    - companion/flash.py
    - companion/freshness.py
    - companion/login_page.py
    - companion/post_actions.py
  modified:
    - companion/app.py
    - companion/test_companion_app_01.py
    - test-support/companion_render_snapshot.py

key-decisions:
  - "MAX_ILLUSTRATION_UPLOAD_BYTES, parse_single_uploaded_file(), and _illustration_filenames() moved into companion/post_actions.py (not left in app.py) because the moved _handle_illustration_replace() needs them and post_actions.py can never import companion.app; app.py rebinds all three under their historical names, so companion/pages/airlines_page.py's own lazy `from companion.app import MAX_ILLUSTRATION_UPLOAD_BYTES` and the two companion_app.parse_single_uploaded_file()/MAX_ILLUSTRATION_UPLOAD_BYTES test call sites keep resolving unchanged."
  - "_POLL_LOCK (the threading.Lock() the calendar-connect route and app.py's own POST /settings / poll-now trigger serialise against) is defined once in companion/post_actions.py and rebound in app.py — never a second, independent Lock() — since two independent locks would silently stop serialising the two call sites against each other."
  - "poll_cooldown_remaining() and _resolve_flash_text() moved to companion/flash.py together (not just the FLASH_MESSAGES/FLASH_KEY_* data) because resolve_flash_text()'s own FLASH_KEY_POLL_COOLDOWN branch calls it — keeping the call in-module avoids yet another cross-module rebind for a function whose only other production call site (_handle_poll_now(), staying in app.py) already gets one via the historical-name alias."
  - "companion/freshness.py exposes only the historical underscore-prefixed names (matching the 40-03 precedent of _static_entry = static_files.static_entry) rather than a clean public rename, since every internal freshness helper except _FRESHNESS_PAGE_SLUGS and _page_freshness_token has no call site outside that module — a public rename would add API surface nothing else calls."

requirements-completed: [CMP-07, CMP-03]

# Metrics
duration: ~2h40min
completed: 2026-09-27
---

# Phase 40 Plan 09: Body-drain/cookie helpers, flash/freshness/login/post-actions split Summary

**Extracted a shared capped-body-drain helper and a shared theme/lang cookie builder (CMP-07), then split app.py's flash-message vocabulary, freshness-token machinery, login/error page markup, and eight settings-action POST handlers into four new modules — shrinking companion/app.py from 2466 to 1466 lines with zero behaviour change.**

## Performance

- **Duration:** ~2h40min
- **Completed:** 2026-09-27
- **Tasks:** 2/2 completed
- **Files created:** 5
- **Files modified:** 3

## Accomplishments

- `companion/request_body.py`'s `drain_capped_body(rfile, length, cap)` replaces two near-identical read-cap-then-drain loops in `Handler.read_form()`/`Handler._read_upload_body()`; each caller keeps its own degrade value (`{}` vs `None`) and cap (`MAX_FORM_BYTES` vs `MAX_ILLUSTRATION_UPLOAD_BYTES`). `grep -c "65536" companion/app.py` is 0; `companion/request_body.py` has exactly 1.
- `Handler._choice_cookie_header(name, value, choices, max_age_s)` replaces the identical `Set-Cookie` format string duplicated in `_handle_theme_post()`/`_handle_lang_post()`. `grep -c "SameSite=Strict; Path=/; Max-Age" companion/app.py` is 1 (inside `_choice_cookie_header()` alone — the session cookie's own copy of that string lives in `companion/auth.py`, untouched).
- `companion/flash.py` holds `FLASH_MESSAGES`, `FLASH_ROLES`, every `FLASH_KEY_*` alias, `resolve_flash_text()`, and `poll_cooldown_remaining()`. `companion/freshness.py` holds the four refresh-page slugs and every `_freshness_*()`/`_page_freshness_token()` helper behind the light freshness check's bodiless-304 path. `companion/login_page.py` holds the login card's markup and the shared 404/403 page bodies as pure functions taking already-resolved request state. `companion/post_actions.py` holds `SettingsActionsMixin` — the eight settings-action POST handlers — plus the illustration-upload helpers and `_POLL_LOCK` those handlers (and app.py's own `_handle_settings_post()`/`_handle_poll_now()`) need.
- `companion/app.py`'s `Handler` now inherits `post_actions.SettingsActionsMixin` ahead of `BaseHTTPRequestHandler`; every moved method keeps its historical name, so `companion/routes.py`'s `ROUTES` table (built in plan 40-03) keeps resolving every handler lambda unchanged. `companion/app.py` re-imports/rebinds every other moved name (`FLASH_KEY_*`, `_resolve_flash_text`, `_page_freshness_token`, `_FRESHNESS_PAGE_SLUGS`, `_POLL_LOCK`, `MAX_ILLUSTRATION_UPLOAD_BYTES`, `parse_single_uploaded_file`, `_illustration_filenames`) under its current name, and none of the four new modules imports `companion.app` (verified: `grep -cE "^import companion.app|^from companion.app|from companion import app" companion/flash.py companion/freshness.py companion/login_page.py companion/post_actions.py companion/request_body.py | grep -v ":0"` prints nothing).
- `companion/app.py`: 2466 -> 1466 lines — 1383 lines smaller than 40-03's own recorded baseline of 2849, well past the plan's 700-line acceptance floor.

## Task Commits

Each task was committed atomically:

1. **Task 1: Shared body-drain and cookie helpers (CMP-07)** - `6639e61` (feat)
2. **Task 2: Move flash, freshness, login/error bodies and settings-action handlers out of app.py** - `211688d` (refactor)

_No TDD RED->GREEN split recorded: Task 1 is `tdd="true"` per the plan, but its new tests (`drain_capped_body` unit tests plus the theme/lang cookie HTTP test) were written and verified passing directly against the already-written implementation in one commit, matching 40-03's own precedent for this kind of extraction-with-verbatim-behaviour task._

## Files Created/Modified

- `companion/request_body.py` - `parse_content_length()`, `drain_capped_body()`
- `companion/flash.py` - `FLASH_MESSAGES`, `FLASH_ROLES`, every `FLASH_KEY_*`, `resolve_flash_text()`, `poll_cooldown_remaining()`
- `companion/freshness.py` - `_FRESHNESS_PAGE_SLUGS`, `_freshness_file_stamp()`/`_freshness_file_stamps()`/`_freshness_db_signal()`/`_freshness_paris_date()`, `_FRESHNESS_SIGNAL_FIELDS`, `_page_freshness_token()`
- `companion/login_page.py` - `login_body()`, `login_reveal_toggle_html()`, `render_login_page()`, `not_found_page()`, `forbidden_page()`, and the login/404/403 text constants
- `companion/post_actions.py` - `SettingsActionsMixin` (the eight settings-action POST handlers), `_illustration_filenames()`, `parse_single_uploaded_file()`, `MAX_ILLUSTRATION_UPLOAD_BYTES`, `_POLL_LOCK`
- `companion/app.py` - `read_form()`/`_read_upload_body()` call the shared drain; `Handler._choice_cookie_header()`; `Handler(post_actions.SettingsActionsMixin, BaseHTTPRequestHandler)`; every moved name rebound under its historical name; `_not_found_page()`/`_forbidden_page()`/`_render_login_page()` reduced to thin wrappers gathering request state and calling into `login_page`; the eight settings-action methods and their own bare-name dependencies (`email.message`, `io`, `tempfile`, `threading`, `Image`, `atomic_io`, `notify`, `frame_state`, `hashlib`, `json`, `ZoneInfo`) removed
- `companion/test_companion_app_01.py` - four `drain_capped_body()` unit tests (at cap, over cap, short read, `socket.timeout`) and one HTTP test pinning the exact `Set-Cookie` bytes `_choice_cookie_header()` produces for every allowed `/ui-theme`/`/ui-lang` value, and none for a disallowed one
- `test-support/companion_render_snapshot.py` - one comment updated from `companion/app.py`'s `_freshness_file_stamp()` to `companion/freshness.py`'s, staleness caused directly by this plan's move

## Decisions Made

See `key-decisions` in the frontmatter above (post_actions.py owning the illustration-upload helpers and `_POLL_LOCK`; `poll_cooldown_remaining()` moving alongside `resolve_flash_text()`; `freshness.py` keeping its historical underscore-prefixed names).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug/accuracy] A dropped `POLL_COOLDOWN_S` rebind in app.py would have been dead code**
- **Found during:** Task 2, while rebinding module constants
- **Issue:** `POLL_COOLDOWN_S` (the poll-cooldown seconds constant) was only ever read inside `poll_cooldown_remaining()`, which moved to `companion/flash.py` in full — a rebind `POLL_COOLDOWN_S = flash.POLL_COOLDOWN_S` in app.py would have had no call site left in that file and no test reads it via `app_module.POLL_COOLDOWN_S` either (checked by grep).
- **Fix:** Removed the rebind entirely rather than leave a pointless alias; `flash.py` is now the constant's sole home.
- **Files modified:** `companion/app.py`
- **Verification:** `ruff check companion` clean (no unused-name warning would have fired either way, since it's a module-level assignment, but the dead alias served no purpose); full companion suite green.
- **Committed in:** `211688d` (Task 2 commit)

**2. [Rule 1 - Comment accuracy] One test-support comment named the pre-move module**
- **Found during:** Task 2, grepping the repo for stale cross-references after moving `_freshness_file_stamp()`
- **Issue:** `test-support/companion_render_snapshot.py`'s own module docstring said "`companion/app.py`'s `_freshness_file_stamp()`", which is now `companion/freshness.py`'s — directly caused by this plan's move, out of its declared `files_modified` list but a one-line accuracy fix.
- **Fix:** Updated the module reference to `companion/freshness.py`.
- **Files modified:** `test-support/companion_render_snapshot.py`
- **Verification:** `companion/test_render_baseline.py` (which imports this module) still passes.
- **Committed in:** `211688d` (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (both Rule 1, both directly caused by this plan's own rename/move work). No scope creep — no production behaviour outside the plan's declared extraction was touched.

## Issues Encountered

None beyond the deviations above.

## Mutation/behaviour proofs

- `_page_freshness_token` stays a bare module-global reference inside `_render_tab()` (never a direct `freshness.` call), specifically so `test_freshness_token.py`'s `monkeypatch.setattr(app, "_page_freshness_token", counting_token)` keeps reaching every call site — confirmed green (`companion/test_freshness_token.py`, including that exact monkeypatch test).
- The route-table auth-coverage suite (`companion/test_route_table.py`, run as part of the full companion suite) still passes with every moved handler resolving through `companion/routes.py`'s existing lambdas — proving `Handler(SettingsActionsMixin, BaseHTTPRequestHandler)`'s MRO change didn't drop or rename any handler method.
- `server/.venv/bin/python3 -c "import companion.app as app; print(app.Handler.__mro__)"` confirms the mixin sits ahead of `BaseHTTPRequestHandler` in the MRO.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `companion/app.py` is now 1466 lines, holding the Handler's request plumbing (dispatch, auth, response helpers, form/cookie parsing) plus `page_context()` — the one remaining CMP-03 extraction, explicitly deferred to plan 40-11 per this plan's own objective.
- `companion/routes.py`'s `ROUTES` table needed zero changes: every moved handler method kept its name and is still resolved the same way (`h._handle_X(...)`).
- Full companion suite (1856 tests, not-browser + browser) green; `ruff check companion` clean; `scripts/check_comment_history.py check` clean.
- No blockers.

---
*Phase: 40-companion-architecture-routes-pages-templates-i18n-keys*
*Completed: 2026-09-27*

## Self-Check: PASSED

All 8 referenced files confirmed present on disk (`companion/request_body.py`,
`companion/flash.py`, `companion/freshness.py`, `companion/login_page.py`,
`companion/post_actions.py`, `companion/app.py`, `companion/test_companion_app_01.py`,
`test-support/companion_render_snapshot.py`); both task commit hashes (`6639e61`, `211688d`)
confirmed present in git history.
