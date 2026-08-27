---
phase: 06-companion-configuration-web-interface-visual-settings-view-s
plan: 04
subsystem: auth
tags: [hmac, session-cookie, html-escaping, css-design-system, stdlib-http]

# Dependency graph
requires: []
provides:
  - "companion/auth.py — password_ok()/issue_session_token()/verify_session_token() stateless HMAC-signed session gate, session_set_cookie_header()/logout_set_cookie_header(), parse_cookies(), LoginThrottle"
  - "companion/layout.py — escape_html() (the single canonical escaping call site), page_shell(), NAV_TABS, status_dot()/anomaly_banner()/flash_banner()/data_table()/empty_state(), ui_theme_from_cookie()"
  - "companion/static/style.css — 06-UI-SPEC.md's full design system (spacing/typography tokens, light/dark palettes, status colors, responsive nav, 44px tap-target floor)"
  - "companion/test_companion_app.py — 20-check stdlib harness covering both new modules, structured for plan 06-05 to append a route-driven third section"
affects: [06-05, 06-06, 06-07, 06-08, 06-09, 06-11]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Stateless HMAC-signed session cookie (expiry.hex-signature, hmac.compare_digest, signature verified before expiry is parsed) — no server-side session store"
    - "Single canonical escape_html() call site in companion/layout.py; every other companion module is expected to import it rather than call html.escape directly"
    - "Process-global (not per-session) LoginThrottle, since D-01/D-02's single-shared-password model has no distinct users to key a per-session guard on"
    - "CSS custom properties + prefers-color-scheme + explicit data-ui-theme override, zero JavaScript, for CFG-09's three-state theme control"

key-files:
  created:
    - companion/__init__.py
    - companion/auth.py
    - companion/layout.py
    - companion/static/style.css
    - companion/test_companion_app.py
  modified: []

key-decisions:
  - "requirements-completed left empty for CFG-09 (this plan's sole frontmatter requirement) — the theme *mechanism* (cookie resolution, CSS override, the shell's data-ui-theme attribute and theme form markup) is fully built and tested here, but there is no HTTP route to actually receive the theme POST until companion/app.py ships in plan 06-05. Matches 06-01/06-02/06-03's established precedent of not checking off a requirement until the user-facing route exists."
  - "Restructured task execution into real RED/GREEN/RED/GREEN/finalize commits (5 commits total) rather than writing the full implementation and full test file in one shot, to match this phase's own established TDD precedent (06-01's commit history) for tasks marked tdd=\"true\"."
  - "Confirmed live (Task 3's own honesty requirement): swapping companion/auth.py's hmac.compare_digest() for a plain == inside password_ok() leaves the 20-check harness green (a timing side-channel is not observable from a unit-level check) but drops Task 1's acceptance-criteria grep count for hmac.compare_digest from 2 to 1, below its required floor of 2 — the acceptance grep, not the harness, is what actually guards this property. Demonstrated then reverted before committing."
  - "Confirmed live: removing SameSite=Strict from session_set_cookie_header()'s literal cookie string makes the harness's cookie-flags check fail (19/20). Demonstrated then reverted before committing."

patterns-established:
  - "companion/ is a stdlib-only package (hashlib, hmac, http.cookies, html, os, time) — no Pillow, no sqlite3, no imports from server/, mirroring stub-server/byos_server.py's own stdlib-first discipline"

requirements-completed: []

coverage:
  - id: D1
    description: "A wrong password cannot yield a session token, and a token this server did not issue (wrong signature, forged secret, or expired) is rejected — always in constant time for the password comparison, never raising for a malformed token."
    requirement: "CFG-09"
    verification:
      - kind: unit
        ref: "companion/test_companion_app.py#password_ok() accepts the correct password and rejects a wrong one"
        status: pass
      - kind: unit
        ref: "companion/test_companion_app.py#verify_session_token() returns False for five malformed inputs without raising"
        status: pass
      - kind: unit
        ref: "companion/test_companion_app.py#flipping a single hex character of a valid signature invalidates the token"
        status: pass
      - kind: unit
        ref: "companion/test_companion_app.py#a forged token signed with a different secret is rejected"
        status: pass
      - kind: unit
        ref: "companion/test_companion_app.py#a hand-built token expired by one second is rejected despite a correct signature"
        status: pass
    human_judgment: false
  - id: D2
    description: "The service refuses to authenticate at all when no password is configured (fail closed), and never lets the configured password value reach an exception message."
    requirement: "CFG-09"
    verification:
      - kind: unit
        ref: "companion/test_companion_app.py#password_ok() raises AuthNotConfigured when the password env var is unset"
        status: pass
      - kind: unit
        ref: "companion/test_companion_app.py#AuthNotConfigured's message never contains the configured password value"
        status: pass
    human_judgment: false
  - id: D3
    description: "Session and logout cookies carry HttpOnly/Secure/SameSite=Strict/Path=/, and cookie parsing never raises on a missing or malformed Cookie header."
    requirement: "CFG-09"
    verification:
      - kind: unit
        ref: "companion/test_companion_app.py#session_set_cookie_header() carries HttpOnly/Secure/SameSite=Strict/Path"
        status: pass
      - kind: unit
        ref: "companion/test_companion_app.py#logout_set_cookie_header() expires the cookie immediately"
        status: pass
      - kind: unit
        ref: "companion/test_companion_app.py#parse_cookies() returns each cookie by name and never raises on a bad header"
        status: pass
    human_judgment: false
  - id: D4
    description: "Every dynamic value has exactly one escaping path into HTML (escape_html()), enforced by a single-call-site grep; page_shell()'s output never carries an unescaped script tag for an escaped hostile body."
    requirement: "CFG-09"
    verification:
      - kind: unit
        ref: "companion/test_companion_app.py#escape_html() escapes all five HTML-special characters"
        status: pass
      - kind: unit
        ref: "companion/test_companion_app.py#page_shell()'s output contains no unescaped script tag for an escaped hostile body"
        status: pass
      - kind: unit
        ref: "companion/test_companion_app.py#status_dot() encodes the state as a fixed class, escapes the label, falls back to warn"
        status: pass
      - kind: unit
        ref: "companion/test_companion_app.py#data_table() escapes every header/cell and emits the empty-state block for zero rows"
        status: pass
    human_judgment: false
  - id: D5
    description: "The stylesheet implements 06-UI-SPEC.md's four type sizes, two weights, both colour palettes, the three status colours, the responsive nav, the CFG-09 dark/light/auto theme mechanism (prefers-color-scheme + data-ui-theme override), and the 44px tap-target floor, with zero external network references."
    requirement: "CFG-09"
    verification:
      - kind: automated_ui
        ref: "grep -c 'url(' companion/static/style.css == 0; grep -c '@font-face' == 0; grep -c 'prefers-color-scheme' >= 1; grep -c 'data-ui-theme' >= 2; grep -c '44px' >= 1; all light/dark/status hex values present"
        status: pass
      - kind: unit
        ref: "companion/test_companion_app.py#page_shell() reflects the supplied UI theme; ui_theme_from_cookie() falls back to auto"
        status: pass
    human_judgment: true
    rationale: "The stylesheet's automated checks (token presence, zero external references, hex-value coverage) are fully proven, but its actual visual legibility in both light/dark modes and mobile-width adaptation (D-22) can only be confirmed once plan 06-05's companion/app.py serves a real page — no rendered page exists yet for a human to look at."

# Metrics
duration: ~35min
completed: 2026-08-27
status: complete
---

# Phase 6 Plan 04: Companion Auth + Layout Backbone Summary

**Stdlib-only `companion/auth.py` (HMAC-signed stateless session cookies, constant-time password gate, fail-closed on missing secret, process-global login throttle) and `companion/layout.py` + `companion/static/style.css` (the single-call-site `escape_html()` helper, the full page shell, and 06-UI-SPEC.md's complete design system) — the security and presentation backbone every later companion-service page builds on.**

## Performance

- **Duration:** ~35 min
- **Tasks:** 3 (Tasks 1-2 `type="auto" tdd="true"`, Task 3 `type="auto"`)
- **Files created:** 5 (`companion/__init__.py`, `companion/auth.py`, `companion/layout.py`, `companion/static/style.css`, `companion/test_companion_app.py`)
- **Files modified:** 0

## Accomplishments

- `companion/auth.py`: `password_ok()` compares the submitted password against `SKYPANE_COMPANION_PASSWORD` via `hmac.compare_digest()` only (never `==`), raising `AuthNotConfigured` (fail closed) when the env var is unset or empty. `issue_session_token()`/`verify_session_token()` implement a stateless `expiry.hex-signature` cookie — no server-side session store — with the signature verified *before* the expiry field is ever parsed, so a forged token can never influence control flow through its own payload. `session_set_cookie_header()`/`logout_set_cookie_header()` carry `HttpOnly; Secure; SameSite=Strict; Path=/` unconditionally. `parse_cookies()` never raises on a malformed header. `LoginThrottle` is deliberately process-global, not per-session, since D-01/D-02's single-shared-password model has no distinct users for a per-session counter to key on.
- `companion/layout.py`: `escape_html()` is the one canonical `html.escape()` call site in the package (grep-auditable at exactly 1 non-comment occurrence). `page_shell()` renders a complete HTML5 document — `lang="en"`, a viewport meta tag, the stylesheet link, `data-ui-theme` resolved from the supplied theme, all five `NAV_TABS` links with the active one marked, and CFG-09's three-option theme form (a POST, never a GET, per D-06/CSRF discipline). `status_dot()`, `data_table()`, `empty_state()`, `flash_banner()`, `anomaly_banner()` round out 06-UI-SPEC.md's small component set, every one escaping its dynamic text internally so a future page author cannot forget.
- `companion/static/style.css`: hand-written, no build step, no framework, no web font. Implements the exact spacing scale (4/8/16/24/32/48px), the four type sizes/two weights, both light and dark palettes plus the three status colors (error reusing Destructive rather than a fifth color), `prefers-color-scheme` with an explicit `data-ui-theme` override for CFG-09, the responsive nav strip below 480px, the 44px tap-target floor on every interactive element, and an accent-colored focus outline — zero `url()`, zero `@font-face`, zero reference to the frame's own vendored font assets.
- `companion/test_companion_app.py`: 20/20 checks, built as real RED→GREEN TDD pairs per task (auth.py's 9 base checks RED against a missing module then GREEN once `auth.py` landed; layout.py's 7 base checks RED against a missing module then GREEN once `layout.py`/`style.css` landed; Task 3 added the 4 hardening checks — forged-secret token, hand-built one-second-expired token, `AuthNotConfigured`'s password-free message, and `page_shell()`'s script-tag-free rendering of an escaped hostile body).

## Task Commits

Each task was committed as a genuine RED/GREEN pair (Tasks 1-2 are `tdd="true"`):

1. **Task 1: companion/auth.py** — `731a121` (test, RED: harness fails on `ImportError` for `companion.auth`) → `d9bd8fd` (feat, GREEN: 9/9 checks pass)
2. **Task 2: companion/layout.py + style.css** — `2fe27a7` (test, RED: harness fails on `ImportError` for `companion.layout`) → `314eae4` (feat, GREEN: 16/16 checks pass)
3. **Task 3: finalize companion/test_companion_app.py** — `5284997` (test: 20/20 checks pass, plus the live-demonstrated-then-reverted `SameSite=Strict` removal and `hmac.compare_digest`→`==` swap named in Task 3's own acceptance criteria)

**Plan metadata:** committed alongside this SUMMARY (see final commit below).

## Files Created/Modified

- `companion/__init__.py` - one-line package docstring
- `companion/auth.py` - HMAC session-token issue/verify, password gate, cookie headers, cookie parsing, login throttle
- `companion/layout.py` - `escape_html()`, page shell, nav/theme rendering, component builders
- `companion/static/style.css` - full 06-UI-SPEC.md design-system implementation
- `companion/test_companion_app.py` - 20-check stdlib harness for both new modules

## Decisions Made

- Restructured commit sequencing into literal RED→GREEN pairs per `tdd="true"` task (auth.py's tests written and proven failing before the implementation existed; same for layout.py), matching plan 06-01's already-established precedent for this phase rather than committing a single "implementation + full test file" blob. See `key-decisions` in the frontmatter for the two live-demonstrated regression checks (SameSite removal, compare_digest→== swap) this uncovered/confirmed.
- Left `requirements-completed: []` for CFG-09 — the theme mechanism this plan builds is real and fully tested, but CFG-09 is only genuinely satisfied once plan 06-05's HTTP route exists for a user to actually submit the theme form against.

## Deviations from Plan

None — plan executed exactly as written. All acceptance-criteria greps (auth.py's `compare_digest`/`HttpOnly`/`Secure`/`SameSite=Strict`/no-`print`/no-direct-equality checks; layout.py's single `html.escape` call site and `page_shell()` document-shape checks; style.css's zero-`url()`/zero-`@font-face`/`prefers-color-scheme`/`data-ui-theme`/`44px`/full hex-palette checks) pass exactly as specified, with no relaxation.

## Issues Encountered

None. The one near-miss was a test-authoring bug (not a product bug): the initial `escape_html()` special-character check naively asserted the literal `&` character was absent from the escaped output, which is definitionally false since `html.escape()`'s own `&`-entity (`&amp;`) contains `&`. Fixed by comparing against `html.escape()`'s own reference output instead of a naive per-character containment check.

## User Setup Required

None - no external service configuration required. (Plan 06-11 later adds the `SKYPANE_COMPANION_PASSWORD` entry to `deploy/skypane.env.example` and the systemd `EnvironmentFile=` reference; this plan only defines the env var name `companion/auth.py` reads.)

## Next Phase Readiness

- `companion/auth.py` and `companion/layout.py` are ready for plan 06-05 (`companion/app.py`, the HTTP server entrypoint) to import directly — both modules are proven via 20/20 passing checks and every acceptance-criteria grep from the plan.
- `companion/test_companion_app.py` is structured (two clearly-commented sections, `EXPECTED_CHECK_COUNT` at the top) so plan 06-05 can append a third, route-driven section without restructuring `main()`.
- No blockers. `companion/device_config.py`/`history_db.py`/`panel_preview.py` (06-01/06-03) and this plan's `auth.py`/`layout.py` are now all available for the page-builder plans (06-05 through 06-09) to compose.

---
*Phase: 06-companion-configuration-web-interface-visual-settings-view-s*
*Completed: 2026-08-27*

## Self-Check: PASSED

All 5 created files verified present on disk (`companion/__init__.py`, `companion/auth.py`, `companion/layout.py`, `companion/static/style.css`, `companion/test_companion_app.py`); all 6 commit hashes (`731a121`, `d9bd8fd`, `2fe27a7`, `314eae4`, `5284997`, `8af9802`) verified present in `git log --oneline --all`.
