---
phase: 19-companion-audit-follow-through-fix-the-open-findings-from-18
plan: 04
subsystem: security
tags: [csp, security-headers, session-auth, static-assets, http-server]

# Dependency graph
requires:
  - phase: 19
    plan: 02
    provides: "companion/auth.py's revocation set and the LOGOUT_ROUTE branch's auth.revoke() call, which this plan gates with require_session() on top of"
provides:
  - "Zero inline <script> elements anywhere in the companion service (companion/pages/config_page.py's poll_trigger_section() externalized to companion/static/poll-cooldown.js)"
  - "A strict Content-Security-Policy (script-src 'self', no 'unsafe-inline'/nonce) sent on every response, including redirects and static-byte responses"
  - "redirect() now carries the same four hardening headers send_html()/send_bytes() already did, plus Cache-Control: no-store"
  - "POST /ui-theme and POST /logout both require a valid session"
affects: [any future plan touching companion/app.py's do_POST()/do_GET()/_send_hardening_headers()/redirect(), companion/layout.py's page_shell(), or companion/pages/config_page.py's poll_trigger_section()]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "data-* attribute contract for externalized inline scripts: a page module emits escape_html()-gated data-* attributes on the DOM element instead of an inline <script>, and a static .js file (served pre-auth, ES5-safe, no HTML-writing sink) reads them via getAttribute()"
    - "The six-touch-point duplicated-not-imported static-script contract, applied to poll-cooldown.js: app.py's *_SCRIPT_ROUTE + *_JS_PATH + _serve_*_script() + do_GET() dispatch line, layout.py's *_SCRIPT_SRC + page_shell()'s script-tag/tuple entry"
    - "CONTENT_SECURITY_POLICY as a single module-level string constant in companion/app.py, sent from the one _send_hardening_headers() choke point every response helper (send_html/send_bytes/redirect) already funnels through"

key-files:
  created:
    - companion/static/poll-cooldown.js
  modified:
    - companion/app.py
    - companion/layout.py
    - companion/pages/config_page.py
    - companion/test_companion_app.py
    - companion/test_config_page.py

key-decisions:
  - "poll_trigger_section() exposes the countdown/submit-affordance values as escape_html()-gated data-* attributes on the button (data-cooldown, data-cooldown-text-id, data-cooldown-template, data-cooldown-token, data-submit-pending) rather than any Python-to-JS literal-injection scheme, since the whole point of this plan is removing dynamic script generation entirely"
  - "_js_literal() and both inline-script builder functions were deleted outright (no remaining callers after the externalization), along with the now-unused `import json` in config_page.py, rather than left as dead code"
  - "The CSP is copied verbatim from the phase CONTEXT's locked D-18 amendment: default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self'; form-action 'self'; frame-ancestors 'none' — style-src keeps 'unsafe-inline' solely for the seven server-controlled theme-swatch style attributes, never re-derived or reworded"
  - "redirect() also gained Cache-Control: no-store (not explicitly named in the plan's task text but required by its own T-19-05 threat entry): a 303 can carry a Set-Cookie (login/logout/theme-toggle) and was previously cacheable"
  - "Gating POST /logout costs a signed-out caller nothing, so it is gated identically to every other state-changing route — plan 19-02's auth.revoke() call is preserved unchanged, just running after the new gate instead of unconditionally"

requirements-completed: [CFG-01]

# Metrics
duration: ~14min
completed: 2026-09-11
---

# Phase 19 Plan 04: Companion CSP, Redirect Hardening, and Session-Gating (D-18/A-35) Summary

**Externalized the app's last two inline `<script>` elements into `companion/static/poll-cooldown.js`, then locked `script-src 'self'` down with a full Content-Security-Policy sent on every response (including redirects), and closed the two previously-ungated state-changing POST routes.**

## Performance

- **Duration:** ~14 min (first task commit to last)
- **Started:** 2026-09-11T07:20:00Z (approximate — investigation/reads preceded the first commit)
- **Completed:** 2026-09-11T07:33:00Z
- **Tasks:** 3/3
- **Files modified:** 6 (1 created)

## Accomplishments
- `poll_trigger_section()` emits zero `<script>` elements on either branch; the D-01 live countdown and UXA-15 disable-on-submit affordance both moved into `companion/static/poll-cooldown.js`, wired through all six touch points of the duplicated-not-imported static-script contract
- Every HTML, byte and 303 response now carries the amended CSP (plus the pre-existing X-Content-Type-Options/X-Frame-Options/Referrer-Policy), sent from the single `_send_hardening_headers()` choke point
- `redirect()` now calls that same choke point and adds `Cache-Control: no-store`, closing a gap where every 303 (including the login bounce and flash redirects) previously sent none of the hardening headers
- `POST /ui-theme` and `POST /logout` both require a valid session, matching the gate-then-dispatch pattern every other state-changing route already used

## Task Commits

Each task was committed atomically:

1. **Task 1: Externalize both inline poll scripts into companion/static/poll-cooldown.js** - `71aa3a3` (feat)
2. **Task 2: Send a CSP on every response and harden redirects (D-18)** - `f26d074` (feat)
3. **Task 3: Session-gate POST /ui-theme and POST /logout (D-18)** - `fc9aec7` (fix)

**Plan metadata:** committed as part of this SUMMARY's own commit (worktree mode — orchestrator handles STATE.md/ROADMAP.md centrally after merge)

## Files Created/Modified
- `companion/static/poll-cooldown.js` (new) - the countdown + disable-on-submit affordance, ported verbatim behaviourally from the two deleted inline-script builders, reading `data-*` attributes off `#poll-trigger-btn` instead of Python-interpolated literals
- `companion/pages/config_page.py` - deleted `_js_literal()`, `_poll_cooldown_script()`, `_poll_submit_script()`; rewrote `poll_trigger_section()` to emit the `data-*` attribute contract instead of either inline script; removed the now-unused `import json`; fixed two stale comments that referenced the deleted functions
- `companion/app.py` - `POLL_COOLDOWN_SCRIPT_ROUTE`/`_POLL_COOLDOWN_JS_PATH`/`_serve_poll_cooldown_script()`/one `do_GET()` dispatch line; the `CONTENT_SECURITY_POLICY` constant; a fourth `send_header()` call in `_send_hardening_headers()`; `redirect()` now calls `_send_hardening_headers()` and sends `Cache-Control: no-store`; `THEME_ROUTE`/`LOGOUT_ROUTE` branches of `do_POST()` both gated with `require_session()`
- `companion/layout.py` - `POLL_COOLDOWN_SCRIPT_SRC` constant; `page_shell()`'s script-tag format string and value tuple grew from seven to eight entries
- `companion/test_companion_app.py` - 9 new checks (3 for poll-cooldown.js's public-serving/ES5-safety/route-src-agreement, 4 for the CSP/redirect-hardening contract, 2 for the two newly-gated routes' unauthenticated behaviour) plus one retarget-in-place (`_seven_deferred_scripts_before_closing_body` → `_eight_deferred_scripts_before_closing_body`); `EXPECTED_CHECK_COUNT` re-derived from 201 to 210 across three appended assignments, one per task
- `companion/test_config_page.py` - four checks retargeted in place (the live-countdown/zero-cooldown/two forbidden-sink checks) to assert the `data-*` attribute contract and the absence of any `<script` substring, with the forbidden-sink/required-operation coverage moved onto `companion/static/poll-cooldown.js`'s own source read from disk; `EXPECTED_CHECK_COUNT` unchanged at 142 (retargets, not additions)

## Decisions Made
- The CSP string is copied byte-for-byte from 19-CONTEXT.md's locked D-18 amendment — no rewording, no directive reordering
- `_js_literal()` had zero remaining callers after the externalization and was deleted rather than left as dead code, along with `companion/pages/config_page.py`'s now-unused `import json`
- `redirect()` gained `Cache-Control: no-store` in addition to the plan's named hardening-header work, since the docstring's own stated risk (a 303 carrying a `Set-Cookie` being cached) requires it and the plan's Task 2 explicitly calls out checking for and adding it "if and only if absent"

## Deviations from Plan

None - plan executed exactly as written. The `Cache-Control: no-store` addition to `redirect()` was explicitly anticipated by Task 2's own action text ("Also add `Cache-Control: no-store` to `redirect()` if and only if it is absent... record the decision either way in a comment") rather than being an out-of-plan deviation.

## Issues Encountered
- The initial draft of `companion/static/poll-cooldown.js`'s header comment used the literal word "innerHTML" in prose (describing the standing no-HTML-writing-sink constraint), which made the new ES5-safety harness checks in both `test_companion_app.py` and `test_config_page.py` self-detect a false-positive "forbidden sink" match against their own banned-token scan of the file's raw source. Reworded the comment to describe the constraint without using any of the banned literal tokens (also removed a stray backtick from an unrelated comment for the same reason). No functional code was affected — this was purely a comment-text/lint-shape issue caught immediately by the new checks doing exactly what they were built to do.
- Several of `companion/app.py`'s own acceptance-criteria `grep -A<N>` commands from the plan text needed the surrounding comments trimmed/repositioned (moved above the `if path ==` line, matching this codebase's own existing convention for `RESOLVE_ROUTE`) so the literal grep window would still capture `require_session()`/`auth.revoke()`/`_send_hardening_headers()` at the exact line-offsets the plan specified. This did not change behavior, only comment placement.

## User Setup Required

None - no external service configuration required.

## Self-Check: PASSED

- FOUND: companion/static/poll-cooldown.js
- FOUND: companion/app.py
- FOUND: companion/layout.py
- FOUND: companion/pages/config_page.py
- FOUND: companion/test_companion_app.py
- FOUND: companion/test_config_page.py
- FOUND commit 71aa3a3
- FOUND commit f26d074
- FOUND commit fc9aec7

## Next Phase Readiness
- D-18/A-35 is closed: no inline `<script>` remains anywhere in the companion service, the CSP is strict on `script-src`, every response (including redirects) carries the full hardening-header set, and the two previously-ungated state-changing POST routes now require a session
- `companion-app` harness: 208/210 (the 2 documented pre-existing root-sandbox WR-11 failures, unrelated to this plan, unchanged); `config-page` harness: 142/142; `view-pages`: 67/67; `status-pages`: 170/171 (the 1 documented pre-existing `anomaly_active()` root-sandbox failure, unrelated to this plan, unchanged)
- `scripts/run-all-tests.sh` reports the same 3 pre-existing-failure harnesses as an untouched checkout (`server/test_manual_resolutions.py`, `companion/test_companion_app.py`, `companion/test_status_pages.py`), no new failures
- No blockers for subsequent phase-19 plans

---
*Phase: 19-companion-audit-follow-through-fix-the-open-findings-from-18*
*Plan: 04*
*Completed: 2026-09-11*
