---
phase: 22-companion-audit-round-4-fix-the-blocking-display-save-bar-co
plan: 08
subsystem: i18n
tags: [python, stdlib-http-server, ast-scanning, i18n, accessibility]

requires:
  - phase: 22-companion-audit-round-4-fix-the-blocking-display-save-bar-co
    provides: "22-05/22-06/22-07's page-module rewrites this plan's scanner widening now covers indirectly"
provides:
  - "companion/app.py's FLASH_MESSAGES routed through i18n.t() before any %/format fill, preserving all five special cases"
  - "every authenticated page's <title>, the 404's short title and the login shell's title translated"
  - "aria-label=\"Primary navigation\" and the theme picker's Auto/Light/Dark segments translated"
  - "companion/test_i18n.py's D-05 scan widened to companion/app.py, attribute literals (title/alt/aria-label/placeholder) and companion/static/*.js fallback literals"
affects: [22-10, 22-11, 22-12, 22-16]

tech-stack:
  added: []
  patterns:
    - "translate the TEMPLATE before any %/format fill (i18n.t(FLASH_MESSAGES[key]) as one expression, not a two-step assignment), so the scanner's dict-eligibility tracing sees the dict as a real i18n.t() consumer"
    - "a function-scoped {code: label} lookup table indexed inside the i18n.t() call, not a .capitalize()/.upper() transform, when a loop variable needs scanner-visible translation"
    - "translate an opaque function parameter at its one literal call site, not inside the function that receives it, so the ast scanner can trace it"
    - "attribute-literal and JS-fallback-literal scanning as two new, explicitly-bounded checks layered on top of the existing ast-based constant/dict/call-argument scan"

key-files:
  created: []
  modified:
    - companion/app.py
    - companion/layout.py
    - companion/i18n_fr/common.py
    - companion/i18n_fr/nav.py
    - companion/test_i18n.py
    - companion/test_companion_app.py

key-decisions:
  - "companion/app.py is now a real D-05 scan target, replacing the hand-written _APP_PY_OWNED_STRINGS exception list — its 'small, stable set of strings' had grown to include every flash banner and every page title"
  - "the three singular/plural fixes (manual resolutions, upcoming flights, the days/events caption) are deferred, not implemented — each lives in a file this plan does not own (airlines_page.py/config_page.py/health_page.py, owned by 22-11/22-10/22-12)"
  - "CFG-29 is left unchecked in REQUIREMENTS.md: its own definition names 'plurals' as part of the requirement, and that part remains open"

requirements-completed: []

duration: ~45min
completed: 2026-09-13
---

# Phase 22 Plan 08: French completeness — flash banners, titles, nav/theme labels, and a widened scanner Summary

**Routes every companion/app.py flash template and page `<title>` through `i18n.t()`, translates the nav landmark's `aria-label` and the theme picker's three segments, and widens `test_i18n.py`'s AST scanner to `app.py`, HTML attribute literals and `companion/static/*.js` fallback text — replacing three now-redundant exception lists with real scan coverage.**

## Performance

- **Duration:** ~45 min
- **Completed:** 2026-09-13
- **Tasks:** 3 (all `type="auto"`)
- **Files modified:** 6 (`companion/app.py`, `companion/layout.py`, `companion/i18n_fr/common.py`, `companion/i18n_fr/nav.py`, `companion/test_i18n.py`, `companion/test_companion_app.py`)

## Accomplishments

- Every one of `FLASH_MESSAGES`' 37 templates is translated. 35 needed a new `companion/i18n_fr/common.py` entry; two ("Test notification sent.", "Couldn't reach that topic — check the URL.") and one ("Poll triggered recently — try again in {n}s.") already had a home in `notifications.py`/`display.py` and were reused, not duplicated.
- Every authenticated page's `<title>` is translated. The six `_PAGE_TITLES` values reuse the exact strings `companion/i18n_fr/nav.py` already translates as nav labels, so no new catalogue entry was needed there — only the `i18n.t()` wrapping at the one `page_shell()` call site. The 404's own short `<title>` ("Not Found" → "Introuvable") and the login shell's ("Login" → "Connexion", a literal inside `layout.py`'s `login_shell()`, not `app.py`) each got a new `common.py` entry.
- `aria-label="Primary navigation"` (both the sidebar and mobile-nav copies) and the theme picker's "Auto"/"Light"/"Dark" segments are translated.
- `companion/test_i18n.py`'s D-05 scan now covers `companion/app.py` directly, replacing the `_APP_PY_OWNED_STRINGS` hand-written exception list. Two more now-redundant exception lists (`_FLASH_AWAITING_TRANSLATION_WIRING`, and the already-empty `_FRAME_STATE_AWAITING_CONSUMERS` placeholder) are deleted outright.
- Two new checks: Check 5 (every literal `title=`/`alt=`/`aria-label=`/`placeholder=` attribute value across the scanned module set needs a catalogue entry) and Check 6 (a regex-based, explicitly-bounded scan of `companion/static/*.js` fallback literals). Both pass with zero findings against the tree this plan leaves.
- `EXPECTED_CHECK_COUNT` re-derived by running the harnesses: `test_i18n.py` 22 → 24; `test_companion_app.py` 258 → 260.

## Task Commits

1. **Task 1: Flash banners and page titles speak French** — `7b86f23` (feat)
2. **Task 2: Singular forms, the nav's accessible name, and the theme segments** — `8de28b9` (feat) — plural forms deferred, see Deviations
3. **Task 3: Widen the scanner to the three places it cannot see** — `bb6d1af` (test)

No separate plan-metadata commit was made before this SUMMARY; the metadata/state-update commit follows this file.

## Files Created/Modified

- `companion/app.py` — `_resolve_flash_text()` routes `FLASH_MESSAGES[flash_key]` through `i18n.t()` as one expression (so the scanner's dict-eligibility tracing sees it as a real consumer); the `FLASH_KEY_RULE_REPLACED` fallback branch's untranslated bypass is fixed; `_PAGE_TITLES[route]` and the 404's title are wrapped in `i18n.t()`; the login form's `error` argument is translated at its one literal call site (`_handle_login_post()`), not inside `_login_body()`, so the ast scanner can trace it across the function-call boundary.
- `companion/layout.py` — `login_shell()`'s `<title>Login - %s</title>` literal translates the "Login" half only; `sidebar_nav()`/`_mobile_nav_html()`'s `aria-label` is translated; `_theme_form_html()` uses a function-scoped `{code: label}` table instead of `.capitalize()` so the scanner can trace it.
- `companion/i18n_fr/common.py` — 35 new flash-message entries, plus "Not Found" and "Login".
- `companion/i18n_fr/nav.py` — "Primary navigation", "Auto", "Light", "Dark".
- `companion/test_i18n.py` — `app.py` added to `_SCAN_RELATIVE_PATHS`; the "deliberately not scanned" paragraph rewritten to record the reversal; `_APP_PY_OWNED_STRINGS`/`_FLASH_AWAITING_TRANSLATION_WIRING`/`_FRAME_STATE_AWAITING_CONSUMERS` deleted; a ninth exclusion reason (`http-header-directive-list`) added for `CONTENT_SECURITY_POLICY`; Checks 5 and 6 added; `EXPECTED_CHECK_COUNT` 22 → 24.
- `companion/test_companion_app.py` — two new round-trip checks (`i18n.t_lang()`, never `set_request_prefs()`) for every flash template/title and for the nav/theme labels; `EXPECTED_CHECK_COUNT` 258 → 260.

## Decisions Made

- **Reused existing catalogue entries rather than duplicating them.** `FLASH_KEY_POLL_COOLDOWN`'s text was already keyed in `display.py`; the two Notifications flash strings were already keyed in `notifications.py`. Verified byte-for-byte via `i18n_fr.CATALOG.get()` before writing any new entry, since the auto-merge package raises `ValueError` on a duplicate key.
- **`_PAGE_TITLES`' six values need no new catalogue entry.** They are the exact same English strings `companion/i18n_fr/nav.py` already translates as nav labels — `i18n.t()` resolves them from that existing entry, and the scanner's dict-eligibility tracing (`i18n.t(_PAGE_TITLES[route])`) proves the dict itself as a real consumer.
- **A function-scoped lookup table over `.capitalize()`/`.upper()`.** The scanner's `_fold_string()` cannot fold a method call back to a literal; a call shaped `i18n.t(choice.capitalize())` would be scanner-invisible. The codebase's own documented "local builder table indexed by a loop variable inside i18n.t()" pattern (test_i18n.py's Pass 1b comment) made this the natural fix rather than a special case.
- **Translate an opaque parameter at its one call site, not inside the function that receives it.** The login form's `error` parameter crossed a function-call boundary rule (c) has no way to trace (a bare `ast.Name` function parameter is not a module constant, a scan-eligible dict value, nor a loop/zip binding). Moving the `i18n.t()` call to `_handle_login_post()`'s one literal call site made it provable; `_login_body()` now only escapes an already-translated string.
- **A ninth, new exclusion reason (`http-header-directive-list`) rather than a Check-2 exception.** `CONTENT_SECURITY_POLICY`'s semicolon-separated directive list matched rule (a)'s "module constant" shape the instant `app.py` joined the scan, but it is not language content — a browser parses it, no reader ever does. This is a new, permanent, reasoned exclusion category (mirroring the eight that already existed for other non-prose shapes), not a temporary Check-2 exception — T-22-29's "every temporary exception dated and owned" rule does not apply to it, since it is not temporary and does not excuse an already-catalogued orphaned key.
- **CFG-29 is left unchecked.** Its own REQUIREMENTS.md definition names "plurals" as part of the requirement; the three named plural fixes are deferred to other plans (see below), so the requirement is not fully served by this plan alone. Checked rather than assumed, per the plan's own instruction.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `FLASH_KEY_RULE_REPLACED`'s fallback branch bypassed translation entirely**
- **Found during:** Task 1
- **Issue:** `_resolve_flash_text()`'s `FLASH_KEY_RULE_REPLACED` branch returned `FLASH_MESSAGES[FLASH_KEY_RULE_ADDED]` directly on an invalid `rule_key` — the raw English template, never routed through `i18n.t()`, even after every other return path in the function was fixed to translate first.
- **Fix:** Changed to `i18n.t(FLASH_MESSAGES[FLASH_KEY_RULE_ADDED])`.
- **Files modified:** `companion/app.py`
- **Commit:** `7b86f23`

**2. [Rule 3 - Blocking] `CONTENT_SECURITY_POLICY` broke Check 1 the moment `app.py` joined the scan**
- **Found during:** Task 3
- **Issue:** `app.py`'s CSP header value matched rule (a)'s module-constant naming convention and had no fitting exclusion category — a genuine scanner false positive, not a translation gap.
- **Fix:** Added a ninth, documented exclusion reason (`http-header-directive-list`) recognising a semicolon-separated `lowercase-hyphenated-name <space> value(s)` list.
- **Files modified:** `companion/test_i18n.py`
- **Commit:** `bb6d1af`

**3. [Rule 3 - Blocking] The login page's `error` parameter was invisible to the widened scanner**
- **Found during:** Task 3
- **Issue:** `_login_body()` called `i18n.t(error)` on an opaque function parameter — functionally correct (French rendered fine before this plan), but untraceable by rule (c) once `app.py` joined the scan, orphaning "Incorrect password. Try again." in Check 2.
- **Fix:** Moved the `i18n.t()` call to `_handle_login_post()`'s one literal call site; `_login_body()` now only escapes the already-translated string.
- **Files modified:** `companion/app.py`
- **Commit:** `bb6d1af`

---

**Total deviations:** 3 auto-fixed (1 bug, 2 blocking)
**Impact on plan:** All three were necessary to make the widened scanner's own verify block pass; none changed the plan's scope. No scope creep.

## Widened-Scanner Findings (Task 3 requirement)

**Genuinely new leaks the widened scanner found:** two, both listed above as deviations 2 and 3 — `CONTENT_SECURITY_POLICY` (a false positive, resolved with a new exclusion reason, not a translation) and the login `error` parameter (a real scanner-tracing gap, resolved by moving the `i18n.t()` call). No other new findings surfaced; Task 1/2's own translation work had already closed every genuine leak `app.py` itself contained, so the widening's remaining job was almost entirely verification, not discovery.

**Exceptions added, and their stated reasons:**
- `http-header-directive-list` (new, permanent exclusion reason, `test_i18n.py`) — CSP header value, not prose. Not a temporary Check-2 exception (T-22-29's dating/naming rule does not apply to it).
- No temporary, dated Check-2 exceptions were added. Three were **removed**: `_APP_PY_OWNED_STRINGS`, `_FLASH_AWAITING_TRANSLATION_WIRING`, `_FRAME_STATE_AWAITING_CONSUMERS` (the last already empty before this plan, deleted per its own comment's instruction).
- During construction (Task 1's own commit, since superseded by Task 3's commit in the same plan), `_APP_PY_OWNED_STRINGS` was temporarily widened with the new flash strings so `test_i18n.py` stayed green ahead of the scanner-widening commit. This is not present in the final tree — Task 3 deleted the whole frozenset.

**Strings originating in `server/`:** none. Every `FLASH_MESSAGES` value is defined directly in `companion/app.py`. The only related server-side bilingual mechanism is `server/notify.py`'s own `_BODY_FR` dict for push-notification bodies (battery-low, frame-silent, etc.) — a separate code path, untouched by this plan, already noted as deliberately absent from `companion/i18n_fr/notifications.py`'s own docstring.

## Acceptance Criteria That Did Not Evaluate As The Plan Predicted

**Task 2's plural acceptance criteria are unmet, by design, not by oversight:**
- "the three counted strings each have a singular and a plural form in both catalogues" — **not done.** All three named strings live in files this plan does not own:
  - `"%d manual resolutions"` / `MANUAL_SUMMARY_TEMPLATE_NONE` — `companion/pages/airlines_page.py:427`, catalogue `companion/i18n_fr/airlines.py:79`. Owned by **22-11**.
  - `"%d upcoming flights · checked %s"` / `CALENDAR_STATUS_DETAIL_TEMPLATE` — `companion/pages/config_page.py:741`, catalogue `companion/i18n_fr/calendar_group.py:48`. Owned by **22-10**.
  - `"over the last %d days, %d events"` — `companion/pages/health_page.py:3033`, catalogue `companion/i18n_fr/health.py:105`. Owned by **22-12**.
  - The plan's own read_first instruction anticipated this exactly: "if one lives in a page module this plan does not own, record it in the SUMMARY instead of editing it." Recorded here for 22-10/22-11/22-12 to close.
- "a count of 1 renders the singular form in both languages" — not evaluable; no singular form exists yet.
- Everything else in Task 2's acceptance criteria (the `aria-label` grep, the round-trip checks, `test_i18n.py`/`test_status_pages.py` passing, `ruff check .`) evaluated exactly as predicted.

**CFG-29 is not fully served by this plan alone**, contrary to the plan's own conditional expectation ("CFG-29 is served by this plan alone, so it may be complete after this one — check rather than assume"). REQUIREMENTS.md's own CFG-29 row explicitly names "plurals" as part of the requirement; since the three plural fixes are deferred to 22-10/22-11/22-12, `requirements mark-complete` was **not** run for CFG-29 in this plan's state update. It should be marked complete once 22-10, 22-11 and 22-12 have each landed their own plural fix.

## Issues Encountered

None beyond the deviations already documented above.

## User Setup Required

None — no external service configuration required.

## Self-Check: PASSED

All files claimed as modified exist on disk; all three task commit hashes (`7b86f23`, `8de28b9`, `bb6d1af`) exist in `git log --oneline --all`.

## Next Phase Readiness

- `companion/test_i18n.py` exits 0 at 24/24; `companion/test_companion_app.py` at 258/260 (the two documented WR-11 root-sandbox FAILs, unrelated to this plan); `companion/test_status_pages.py` at 251/252 (the one documented `anomaly_active()` FAIL). `ruff check .` clean. `scripts/run-all-tests.sh` shows the same three known root-sandbox failures (`server/test_manual_resolutions.py`, `companion/test_companion_app.py`, `companion/test_status_pages.py`) and no new ones; coverage 93% (≥ 83 threshold).
- 22-10, 22-11 and 22-12 each have a concrete, file:line-scoped plural fix waiting for them (see above) — closing all three is what completes CFG-29.
- Plan 22-10 (which depends on this plan) inherits a scanner that will now demand a French catalogue entry for anything it hardcodes into an attribute or fails to route through `i18n.t()` in `config_page.py` — Checks 5/6 apply to every file already in `_SCAN_RELATIVE_PATHS`, `config_page.py` included.

---
*Phase: 22-companion-audit-round-4-fix-the-blocking-display-save-bar-co*
*Completed: 2026-09-13*
