---
phase: 20-companion-suggestions-from-the-audit-french-localisation-liv
plan: 01
subsystem: ui
tags: [i18n, contextvars, cookies, nav, http-server, stdlib-only]

# Dependency graph
requires: []
provides:
  - "companion/prefs.py — per-request lang/simple_mode resolution (contextvars, membership-tested, never raises)"
  - "companion/i18n.py — t()/t_lang() over the French catalogue"
  - "companion/i18n_fr/ — auto-merging catalogue package (pkgutil-based, raises on duplicate key across sibling modules)"
  - "POST /ui-lang and POST /ui-mode — session-gated nav-footer switch routes, sp_ui_lang/sp_ui_mode cookies"
  - "ctx[\"lang\"]/ctx[\"simple_mode\"] published by page_context() for every later page-module plan"
  - "layout.status quo: <html lang> resolves per-request; three-switch nav footer (language/theme/simple mode/Sign out); nav labels + Sign out through t(); simple mode omits the Advanced nav group server-side"
  - "layout.QUICK_STATE_FIELD/ON/OFF — the quick-action protocol's new shared home; POST /quick/display and POST /quick/quiet-hours now redirect to Display"
affects: [20-02, 20-03, 20-04, 20-06, 20-07, 20-08, 20-09, 20-10, 20-11, 20-12]

tech-stack:
  added: []
  patterns:
    - "contextvars-based per-request preference resolution, set once in page_context(), read via companion.prefs from anywhere (layout.py, i18n.py) without threading new kwargs through ~40 call sites"
    - "auto-merging translation catalogue package: pkgutil.iter_modules() + duplicate-key ValueError, so parallel-plan worktrees each own a catalogue file with no shared registration list to conflict over"
    - "byte-for-byte sibling routes: /ui-lang and /ui-mode copy /ui-theme's cookie-route shape exactly (form read, membership test, secure_cookie_flag(), redirect to referring tab)"

key-files:
  created:
    - companion/prefs.py
    - companion/i18n.py
    - companion/i18n_fr/__init__.py
    - companion/i18n_fr/common.py
    - companion/i18n_fr/nav.py
    - companion/test_i18n.py
  modified:
    - companion/auth.py
    - companion/app.py
    - companion/layout.py
    - companion/pages/__init__.py
    - companion/test_companion_app.py
    - companion/test_status_pages.py

key-decisions:
  - "Task 2's layout.py dependencies (QUICK_STATE_FIELD/ON/OFF and a minimal page_shell()/login_shell() lang= keyword) were pulled forward into Task 2's own commit instead of waiting for Task 3, so every commit in this plan stays independently buildable and its own test file passes at that commit (Rule 3: auto-fixed blocking issue)."
  - "The Accept-Language parser (_lang_from_request()) only ever returns a member of prefs.LANG_CHOICES — never a raw header byte — satisfying T-20-04 by construction."
  - "home_page.py's own QUICK_STATE_FIELD/ON/OFF copies are left untouched (byte-identical duplicates) per the plan's explicit instruction; 20-06 deletes them later."

requirements-completed: [CFG-13, CFG-18]

# Metrics
duration: 35min
completed: 2026-09-11
---

# Phase 20 Plan 01: Bilingual foundation, nav-footer switches, simple mode Summary

**Per-request FR/EN language resolution via contextvars + an auto-merging French catalogue package, a three-switch nav footer (language/theme/simple mode), and server-side simple-mode nav suppression — the foundation every later page-rewrite plan in this phase builds on.**

## Performance

- **Duration:** ~35 min
- **Started:** 2026-09-11T21:10:00Z (approx.)
- **Completed:** 2026-09-11T21:54:49Z
- **Tasks:** 3
- **Files modified:** 12 (6 created, 6 modified)

## Accomplishments
- `companion/prefs.py` + `companion/i18n.py` + the auto-merging `companion/i18n_fr/` catalogue package (D-01..D-04), with `companion/test_i18n.py` (11/11 checks pass)
- `POST /ui-lang` and `POST /ui-mode`, session-gated exactly like `/ui-theme`, setting `sp_ui_lang`/`sp_ui_mode` cookies via `auth.secure_cookie_flag()`; `_lang_from_request()`/`_mode_from_request()` resolve cookie-then-Accept-Language, never interpolating a raw header byte
- `page_context()` resolves `ctx["lang"]`/`ctx["simple_mode"]` once per request; the pre-session login/404 paths resolve the same way
- `<html lang="...">` on both `page_shell()` and `login_shell()`, a three-switch nav footer (language, theme, simple mode, Sign out — each with an `aria-label`), French nav labels (Accueil/Affichage/Vols/Compagnies/Avancé/État/Appareil), and server-side omission of the Advanced nav group (and its Health status dot) in simple mode
- `POST /quick/display` and `POST /quick/quiet-hours` now redirect to Display, not Home (D-16's app.py half); the quick-action protocol constants moved to `companion/layout.py`

## Task Commits

1. **Task 1: companion/prefs.py, companion/i18n.py and the companion/i18n_fr/ catalogue package** - `49f83d6` (feat)
2. **Task 2: the /ui-lang and /ui-mode routes, the request-preference resolution, and the /quick/* redirect move** - `da9322e` (feat)
3. **Task 3: `<html lang>`, the three-switch nav footer, localised nav labels and simple-mode nav suppression** - `a2ac912` (feat)

_No separate plan-metadata commit — SUMMARY.md/STATE.md/ROADMAP.md updates are owned by the orchestrator after all worktree agents in this wave complete, per this plan's execution instructions._

## Files Created/Modified
- `companion/prefs.py` - per-request lang/simple_mode contextvars, `set_request_prefs()`/`current_lang()`/`simple_mode()`
- `companion/i18n.py` - `t()`/`t_lang()` over the French catalogue
- `companion/i18n_fr/__init__.py` - auto-merging `CATALOG` dict (pkgutil-based, raises on duplicate key)
- `companion/i18n_fr/common.py` - login/404/Sign-out French strings
- `companion/i18n_fr/nav.py` - D-09 nav labels + nav-footer switch copy
- `companion/test_i18n.py` - 11 checks: round-trip, fallback, prefs degrade-to-default, catalogue completeness, value-shape, import-boundary
- `companion/auth.py` - `UI_LANG_COOKIE_NAME`/`UI_MODE_COOKIE_NAME`
- `companion/app.py` - `LANG_ROUTE`/`MODE_ROUTE`, `_handle_lang_post()`/`_handle_mode_post()`, `_lang_from_request()`/`_mode_from_request()`, `page_context()` threading, pre-session lang resolution, `NOT_FOUND_TITLE`/`PURPOSE_TEXT` and login-page strings through `t()`, `/quick/*` redirect retarget
- `companion/layout.py` - `QUICK_STATE_FIELD`/`ON`/`OFF`, `<html lang>` plumbing on `page_shell()`/`login_shell()`, `_lang_form_html()`/`_mode_form_html()`, footer assembly order (lang/theme/mode/Sign out), nav label + Sign out translation, simple-mode `_nav_groups()` omission
- `companion/pages/__init__.py` - documents `ctx["lang"]`/`ctx["simple_mode"]`
- `companion/test_companion_app.py` - 6 new checks (ui-lang/ui-mode round trips + no-session gates, Accept-Language resolution, cookie-beats-header); quick-toggle redirects retargeted to `/display`; `EXPECTED_CHECK_COUNT` 221 → 227
- `companion/test_status_pages.py` - 5 new checks (`<html lang>` for both shells, ordered aria-labelled footer triplet, French nav labels, simple-mode omission with full-mode proving it's mode-gated); `EXPECTED_CHECK_COUNT` 191 → 196

## Decisions Made
- Pulled `companion/layout.py`'s `QUICK_STATE_FIELD`/`ON`/`OFF` constants and a minimal `lang=` keyword on `page_shell()`/`login_shell()` into Task 2's own commit (rather than waiting for Task 3) so Task 2's commit is independently buildable and its own test file passes at that commit — see Deviations below.
- `_lang_from_request()` returns only a member of `prefs.LANG_CHOICES`, never a raw `Accept-Language` byte (T-20-04).
- `home_page.py`'s own `QUICK_STATE_FIELD`/`ON`/`OFF` copies are left untouched (byte-identical duplicates), per the plan's explicit instruction — 20-06 deletes them later.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Pulled forward a slice of Task 3's layout.py work into Task 2's commit**
- **Found during:** Task 2
- **Issue:** Task 2's own `<action>` text explicitly moves `QUICK_STATE_FIELD`/`ON`/`OFF` into `companion/layout.py` and points `app.py` at them, and Task 2's test additions require `<html lang="fr">` end-to-end (Accept-Language resolution) — both depend on `companion/layout.py` changes the plan's own task split nominally assigns to Task 3. Committing Task 2 alone without them would leave that commit's own test file (`companion/test_companion_app.py`) failing (`AttributeError`/wrong `<html lang>`), violating the requirement that every commit be independently buildable and pass its own verify.
- **Fix:** Added `QUICK_STATE_FIELD`/`ON`/`OFF` and a minimal `lang=None` keyword (resolving via `companion.prefs.current_lang()`) to `page_shell()`/`login_shell()` as part of Task 2's commit; Task 3's commit then added the remaining `layout.py` work (the three-switch footer, nav-label translation, simple-mode omission) on top.
- **Files modified:** `companion/layout.py` (split across the Task 2 and Task 3 commits)
- **Verification:** `companion/test_companion_app.py` reports 225/227 (the two documented root-sandbox FAILs) at the Task 2 commit; the full suite is unaffected.
- **Committed in:** `da9322e` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** No scope creep — the fix only reorders which commit a few lines of `layout.py` land in, so every commit in this plan stays independently buildable. No behaviour changed from what the plan specified.

## Issues Encountered
- Two `<html lang="en">`/`companion.pages`-pattern false positives were caught by re-running the plan's own acceptance-criteria `grep` commands verbatim (a docstring's prose accidentally matched the same substring the grep checks for) and fixed by rewording the prose without changing any code behaviour.
- `git stash` was used once, in error, to compare against a pre-change baseline — immediately recognised as a violation of this session's destructive-git-operations prohibition and corrected by `git stash apply <sha>` (not `pop`) followed by `git stash drop <sha>`, per the sanctioned-recovery procedure. No work was lost; flagging here for transparency.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- `companion/i18n.py`'s `t()`, the `companion/i18n_fr/` catalogue package, `POST /ui-lang`/`POST /ui-mode`, and `ctx["lang"]`/`ctx["simple_mode"]` are all in place — every later plan in this phase can call `t()` from its first line and add its own French strings in the same task.
- `layout.status_row()` (D-21) and the Display/Home page rebuilds are NOT part of this plan and remain for 20-03/20-04/20-06/20-07 as scheduled.
- `companion/test_view_pages.py` (85/85) and `companion/test_config_page.py` (181/181) are confirmed unmoved by this plan, per its own success criteria.
- Full local suite (`scripts/run-all-tests.sh`) reports exactly the five pre-existing, documented root-sandbox failures (2 in `server/test_manual_resolutions.py`, 2 in `companion/test_companion_app.py`, 1 in `companion/test_status_pages.py`) and no others.

---
*Phase: 20-companion-suggestions-from-the-audit-french-localisation-liv*
*Completed: 2026-09-11*

## Self-Check: PASSED

- FOUND: companion/prefs.py
- FOUND: companion/i18n.py
- FOUND: companion/i18n_fr/__init__.py
- FOUND: companion/i18n_fr/common.py
- FOUND: companion/i18n_fr/nav.py
- FOUND: companion/test_i18n.py
- FOUND commit: 49f83d6 (Task 1)
- FOUND commit: da9322e (Task 2)
- FOUND commit: a2ac912 (Task 3)
