---
phase: 06-companion-configuration-web-interface-visual-settings-view-s
plan: 05
subsystem: api
tags: [http-server, stdlib, routing, session-auth, page-shell]

# Dependency graph
requires:
  - phase: 06-companion-configuration-web-interface-visual-settings-view-s
    provides: "server/device_config.py, server/history_db.py (06-01), server/panel_preview.py (06-03), companion/auth.py, companion/layout.py, companion/static/style.css (06-04)"
provides:
  - "companion/app.py — the runnable companion service: ThreadingHTTPServer, the complete route table, and the single D-02 auth enforcement point (require_session())"
  - "companion/pages/ — the five contract-complete page-builder stubs (render(ctx)/handle_post(form, ctx)) plans 06-07/06-08/06-09 fill in"
  - "The real, live CFG-07 manual poll trigger (POST /poll-now, server-global cooldown) and the real, live CFG-09 theme toggle (POST /ui-theme)"
  - "The real, live CFG-10 preview image route (GET /preview.png) and a safe CFG-11 gallery-file route (GET /gallery/<name>), both directory-listing-validated"
affects: [06-06, 06-07, 06-08, 06-09, 06-10, 06-11, 06-12]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Flat if-self.path==... dispatch table in do_GET/do_POST, exactly stub-server/byos_server.py's own shape — no framework router for six-ish routes"
    - "require_session() called as the literal first statement of every authenticated branch, written out per-route rather than looped over a dict, so each branch is its own auditable call site"
    - "Gallery/static file lookups resolve a client-supplied name against a real os.scandir() directory listing before ever opening a file — never os.path.join() a client string onto a path"
    - "A fixed flash-key -> 06-UI-SPEC.md-copy dictionary; the query string only ever supplies a lookup key, never rendered content"
    - "Server-global (not per-session) cooldown state persisted in history.db's meta table via server.history_db, surviving a second browser tab and a service restart"
    - "POST /poll-now imports server.poll_loop and calls run_once() in-process — the same production code path the systemd timer runs, never a subprocess"

key-files:
  created:
    - companion/app.py
    - companion/pages/__init__.py
    - companion/pages/config_page.py
    - companion/pages/health_page.py
    - companion/pages/airlines_page.py
    - companion/pages/history_page.py
    - companion/pages/preview_page.py
  modified:
    - companion/test_companion_app.py

key-decisions:
  - "Theme-toggle POST (/ui-theme) is deliberately exempt from require_session(), per the plan's own task text — it only ever sets a cookie-scoped UI preference, appears on every page (including the unauthenticated login page's own shell), and carries no security-sensitive effect. The acceptance-criteria require_session() call-site count (>= 8) and the auth-gate harness both intentionally exclude this route from the nine gated routes."
  - "The test harness deliberately does NOT use urllib.request.HTTPCookieProcessor — the session cookie always carries Secure (correctly, for production), and http.cookiejar silently refuses to store or resend a Secure cookie over this local harness's plain-HTTP connection. Cookies are threaded through explicitly as plain Cookie request headers instead, still pure urllib.request with no added dependency."
  - "PREVIEW_THUMB_WIDTH=600 caps /preview.png at half the panel's native 1200px width via panel_preview.py's existing nearest-neighbour resize path, for a faster mobile load (D-22) without inventing any new intermediate colours."
  - "The gallery-traversal test's canary file, and 'requested' filename comparisons, rely on os.scandir()'s bare entry.name (never containing a path separator) — this makes the safety property structural, not merely tested: a traversal-shaped, absolute, or null-byte-containing name can never equal a bare directory-listing entry, regardless of encoding."

patterns-established:
  - "companion/app.py's Handler class-attribute-as-shared-config idiom (Handler.args set once in main() before serve_forever()) mirrors stub-server/byos_server.py's Handler.args/Handler.state pattern exactly."
  - "Page modules never build a full HTML document — render(ctx) returns body markup only; companion/app.py's five near-identical GET branches are the one place layout.page_shell() is called, keeping the D-02 gate and the shell-wrapping logic co-located rather than duplicated per page."

requirements-completed: [CFG-07, CFG-09]

coverage:
  - id: D1
    description: "The D-02 whole-site auth gate is enforced route by route — nine authenticated routes (five tabs, preview image, gallery image, config POST, poll POST) each individually redirect to /login with no page content when no valid session cookie is presented; a login POST with the correct password sets a session cookie carrying HttpOnly/Secure/SameSite=Strict and grants access to all five tabs; logout clears the cookie and a subsequent request is refused again."
    requirement: "CFG-09"
    verification:
      - kind: integration
        ref: "companion/test_companion_app.py#unauthenticated GET/POST checks (9 routes) + login flow + 5 authenticated tab checks + logout checks"
        status: pass
      - kind: manual_procedural
        ref: "Deliberately removed require_session() from the /health branch, confirmed exactly 1 of 49 checks failed (48/49), then reverted (git diff --stat companion/app.py showed no residual change) — see Deviations."
        status: pass
    human_judgment: false
  - id: D2
    description: "POST /poll-now imports server.poll_loop and calls run_once() in-process (the real production code path, never a subprocess), behind a server-global cooldown persisted in history.db's meta table — a second, freshly-authenticated browser session is refused by the same cooldown, and it survives independent of any single session."
    requirement: "CFG-07"
    verification:
      - kind: integration
        ref: "companion/test_companion_app.py#a first poll trigger redirects with poll_triggered; an immediate second redirects with poll_cooldown; a fresh second-opener session is also refused"
        status: pass
      - kind: unit
        ref: "grep -c poll_state.json companion/app.py == 0; grep -vE '^\\s*#' companion/app.py | grep -c subprocess == 0"
        status: pass
    human_judgment: false
  - id: D3
    description: "The gallery file route resolves a client-supplied filename against a real directory listing (os.scandir()) before ever opening a file, never by joining the client string onto a path — traversal-shaped, absolute-path, and null-byte-containing names all 404, and a canary file placed one level above the gallery directory never leaks into any response."
    requirement: "CFG-11"
    verification:
      - kind: integration
        ref: "companion/test_companion_app.py#three traversal-payload checks + the canary-never-returned check"
        status: pass
      - kind: unit
        ref: "grep -nE 'os\\.path\\.join\\([^)]*self\\.path|os\\.path\\.join\\([^)]*name\\b' companion/app.py returns no lines"
        status: pass
    human_judgment: false
  - id: D4
    description: "GET /preview.png serves the live panel.bin as a real PNG (404 when no panel exists yet, 503 with the 'temporarily unavailable' copy on a malformed panel), and POST /ui-theme actually persists the CFG-09 theme choice as a cookie the page shell then reflects."
    requirement: "CFG-09"
    verification:
      - kind: integration
        ref: "companion/test_companion_app.py#GET /preview.png missing-file and real-panel-PNG-signature checks"
        status: pass
      - kind: manual_procedural
        ref: "Live curl round trip: POST /ui-theme dark, then GET /config with both cookies, confirmed data-ui-theme=\"dark\" in the rendered document"
        status: pass
    human_judgment: false
  - id: D5
    description: "The service refuses to start when SKYPANE_COMPANION_PASSWORD is unset, printing a message that never contains a password value, and exits non-zero."
    requirement: "CFG-09"
    verification:
      - kind: manual_procedural
        ref: "env -u SKYPANE_COMPANION_PASSWORD server/.venv/bin/python3 companion/app.py --port 18643 exited 1 with the AuthNotConfigured message and no password value"
        status: pass
    human_judgment: false

# Metrics
duration: ~50min
completed: 2026-08-28
status: complete
---

# Phase 6 Plan 05: Companion App Router + Page Stubs Summary

**`companion/app.py` — a stdlib `ThreadingHTTPServer` with a hand-rolled route table and a single D-02 auth-gate enforcement point, plus five contract-complete page-builder stubs — the runnable companion service that plans 06-07/06-08/06-09 build their real page bodies into.**

## Performance

- **Duration:** ~50 min
- **Tasks:** 3
- **Files created:** 7 (`companion/app.py`, `companion/pages/__init__.py` + 5 page modules)
- **Files modified:** 1 (`companion/test_companion_app.py`)

## Accomplishments

- `companion/app.py`: a runnable companion service mirroring `stub-server/byos_server.py`'s own shape — flat `if self.path == ...` dispatch in `do_GET`/`do_POST`, `require_session()` called as the first statement of every one of nine authenticated branches (five tabs, preview image, gallery image, config POST, poll POST), a startup refusal when `SKYPANE_COMPANION_PASSWORD` is unset, and a `sys.stdout.reconfigure(line_buffering=True)` fix (a real bug found while smoke-testing, matching `byos_server.py`'s own precedent) so log lines are never lost on process termination.
- The manual poll trigger (CFG-07) is real and live now: `POST /poll-now` imports `server.poll_loop` and calls `run_once()` in-process — the exact code path the systemd timer runs — behind a `POLL_COOLDOWN_S=45` cooldown persisted in `history.db`'s meta table, proven server-global (not per-session) against a freshly-authenticated second session.
- The theme toggle (CFG-09) is real and live now: `POST /ui-theme` validates the submitted value against `layout.UI_THEME_CHOICES`, sets the `sp_ui_theme` cookie, and redirects back to the referring tab (drawn from a fixed five-route allowlist derived from `layout.NAV_TABS`, never a client-supplied URL) — live-verified end to end with a curl round trip.
- The live panel preview (CFG-10) is served over HTTP without SSH access: `GET /preview.png` reads `panel.bin` via `server.panel_preview.read_panel_file()`/`panel_png_bytes()`, capped to `PREVIEW_THUMB_WIDTH=600` for a faster mobile load, with distinct 404 (no panel yet) and 503 (`PanelDecodeError`) failure modes.
- The gallery route (part of CFG-11's plumbing) resolves a requested filename against a real `os.scandir()` listing before ever opening a file — structurally safe against path traversal because `os.scandir()` entry names never contain a path separator, proven against three traversal-shaped payloads (parent-directory segments, an absolute path, a null byte) and a canary file placed one level above the gallery directory.
- Five `companion/pages/*.py` stubs (`config_page`, `health_page`, `airlines_page`, `history_page`, `preview_page`) each render their documented 06-UI-SPEC.md empty state, making the service navigable end to end from this plan onward; `airlines_page.py` stays action-free (no form, no button) per D-16.
- `companion/test_companion_app.py` grew from 20 to 49 checks: a new `Harness` class subprocess-launches the real `companion/app.py` on a free local port (mirroring `stub-server/test_poll_cycle.py`), asserting the D-02 gate route by route, the login flow and cookie flags, the 404 copy, the preview PNG path, gallery traversal rejection, and the server-global poll cooldown.

## Task Commits

Each task was committed atomically:

1. **Task 1: companion/app.py — ThreadingHTTPServer, route table, auth gate** - `fdfaa8c` (feat)
2. **Task 2: companion/pages/ — five contract-complete stubs** - `cc6e64d` (feat)
3. **Task 3: extend companion/test_companion_app.py with route/auth-gate checks** - `7b8481e` (test)

**Plan metadata:** (this commit)

## Files Created/Modified

- `companion/app.py` - `DEFAULT_PORT`, `GALLERY_DIRNAME`, `POLL_COOLDOWN_S`, `PREVIEW_THUMB_WIDTH`, `Handler` (`send_html`/`send_bytes`/`redirect`/`require_session`/`read_form`/`page_context`/`log_message`), `build_parser()`, `main()`, `poll_cooldown_remaining()`, `mark_poll_triggered()`, `gallery_entries()`, `gallery_bytes()`
- `companion/pages/__init__.py` - the `render(ctx)`/`handle_post(form, ctx)` module contract every later page-builder plan fills in
- `companion/pages/config_page.py` - `render(ctx)`, `handle_post(form, ctx)` (stub, reports save-failure), the real Trigger Poll Now form
- `companion/pages/health_page.py`, `companion/pages/airlines_page.py`, `companion/pages/history_page.py`, `companion/pages/preview_page.py` - `render(ctx)` stubs emitting 06-UI-SPEC.md's documented empty states
- `companion/test_companion_app.py` - `Harness`, `http_request()`, `_cookie_value()`, `_login()`, `_NoRedirectHandler`, and 29 new Section-3 checks (`EXPECTED_CHECK_COUNT` 20 -> 49)

## Decisions Made

- Left the theme-toggle POST route (`/ui-theme`) exempt from `require_session()`, exactly as the plan's task text specifies — it is a low-stakes, cookie-only UI preference that appears on every page shell including the unauthenticated login page.
- Chose `os.scandir()` + bare `entry.name`/`entry.path` over `os.listdir()` + `os.path.join()` for the gallery route, so the acceptance criteria's `os.path.join([^)]*name\b)` grep prohibition is satisfied by construction, not just by care — the safety property and the literal grep gate point at the same code shape.
- Marked CFG-07 and CFG-09 complete in REQUIREMENTS.md (see below) — unlike the theme/runway *save* mechanism (still a stub, correctly left unmarked as part of no requirement), the manual poll trigger and the theme toggle are both genuinely end-to-end functional as of this plan, not partial infrastructure.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] stdout was fully buffered, silently losing log lines on process termination**
- **Found during:** Task 1, while smoke-testing the running service with curl
- **Issue:** `companion/app.py`'s `main()` did not call `sys.stdout.reconfigure(line_buffering=True)`. Once stdout is redirected to a file (or, in production, captured by journald via a non-TTY pipe), Python fully buffers it by default; a `SIGTERM` before the buffer next flushes silently drops every pending log line, including `server.poll_loop.run_once()`'s own diagnostic print — verified live: killing the process after a poll trigger left the log file completely empty.
- **Fix:** Added `sys.stdout.reconfigure(line_buffering=True)` in `main()`, in the same place `stub-server/byos_server.py`'s own `main()` already does this.
- **Files modified:** `companion/app.py`
- **Verification:** Re-ran the same smoke test; the log file correctly contained the startup line, the request log line, and `poll_loop`'s own diagnostic line after the same kill sequence.
- **Committed in:** `fdfaa8c` (Task 1 commit)

**2. [Rule 3 - Blocking] The plan's literal acceptance-criteria grep for `<form`/`<button` in airlines_page.py also matched explanatory docstring prose**
- **Found during:** Task 2, while verifying the plan's own acceptance criteria
- **Issue:** The module's docstring explained D-16's read-only constraint using literal `<form>`/`<button>` HTML-tag notation ("must never contain a `<form>` or a `<button>`"), which made `grep -rn "<form" companion/pages/airlines_page.py` (an acceptance criterion) match the docstring itself, not real markup.
- **Fix:** Reworded the docstring to say "form element"/"button element" instead of the literal tag syntax, preserving the same explanation with zero semantic change.
- **Files modified:** `companion/pages/airlines_page.py`
- **Verification:** `grep -rn "<form" companion/pages/airlines_page.py` and `grep -rn "<button" companion/pages/airlines_page.py` both now return no lines.
- **Committed in:** `cc6e64d` (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (1 real bug, 1 blocking acceptance-criteria/grep mismatch)
**Impact on plan:** Both fixes are small, self-contained, and directly strengthen the plan's own stated goals (durable logging, an acceptance criterion that actually measures what it intends to measure) — no scope creep, no behavior change beyond the fix itself.

## Issues Encountered

None beyond the two auto-fixed deviations above. The live-demonstrated `require_session()` removal (acceptance criterion for Task 3) confirmed the harness catches exactly one failure per missing gate call, then was reverted — `git diff --stat companion/app.py` after the revert showed no residual change against the Task 1 commit.

## User Setup Required

None — no external service configuration required. (Plan 06-11 still owns adding `SKYPANE_COMPANION_PASSWORD` to `deploy/skypane.env.example` and the systemd unit's `EnvironmentFile=` reference, per 06-04-SUMMARY.md.)

## Next Phase Readiness

- `companion/app.py` and `companion/pages/` are ready for plans 06-07 (Config page's real theme/runway save), 06-08 (Health/Airlines real data), and 06-09 (History/Preview gallery real data) to fill in `render(ctx)`/`handle_post(form, ctx)` bodies without touching the router.
- `gallery_entries()`/`gallery_bytes()` are ready for plan 06-10's gallery-writer to populate `state/gallery/*.png`, and for plan 06-09's Preview page to list real entries via `gallery_entries()`.
- `companion/test_companion_app.py`'s `Harness` class is ready for later plans to add further route-driven checks without restructuring `main()` — Section 3 is clearly delimited and self-contained.
- No blockers for 06-06 onward. Full 9-harness suite (`scripts/run-all-tests.sh`) green at 82% coverage; `ruff check .` clean; `git status --porcelain stub-server/` empty (D-03 untouched).

## Self-Check: PASSED
