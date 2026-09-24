---
phase: 33-companion-tests-on-pytest-behaviour-over-source-text
plan: 17
subsystem: testing
tags: [pytest, companion-app, login-throttle, quick-toggle-routes, illustration-upload, theme-preview-cache, migration]

# Dependency graph
requires:
  - phase: 33-companion-tests-on-pytest-behaviour-over-source-text
    plan: "16"
    provides: "companion/test_companion_app_helpers.py's encode_multipart()/strip_js_line_and_block_comments(), the shrunk companion/test_companion_app.py (EXPECTED_CHECK_COUNT=141) this plan continues shrinking, and the restored main()-level app_module import / _unauth_redirects_to_login() / _static_script_public() plumbing this plan confirmed still present for the next chain plan"
  - phase: 33-companion-tests-on-pytest-behaviour-over-source-text
    plan: "02"
    provides: "companion/conftest.py's app_server/make_app_server/module_app_server_factory fixtures (including make_app_server's env_overrides= parameter, used here for the wake-interval pre-fill/floor checks) and test-support/companion_app_server.py's http_request/login/served_asset/served_stylesheet/cookie_value"
  - phase: 33-companion-tests-on-pytest-behaviour-over-source-text
    plan: "03"
    provides: "test-support/companion_markup.py's css_rules()/rules_with_selector() (the JS gate boundary and login-card CSS-rule-existence checks) and companion/test_suite_guards.py's TST-10/12/13/14 guard, which now scans both of this plan's new modules"
provides:
  - "companion/test_companion_app_04.py: 45 native pytest tests porting companion/test_companion_app.py's original check() calls across ledger rows 178-222 — the JS gate/motion-budget style.css contracts, login-card.js's public-route/ES5/route-agreement/no-inline-script/reveal-toggle checks, the login POST/GET flows (wrong password, right password, deep-link return, open-redirect rejection, the renamed /no-such-route next value, the dedicated login_shell(), the clean/error/lockout card renders), the document-language regression guard, the six authenticated NAV_TABS headings, the retired /preview / legacy-route redirects, the /config 404, the unscoped and scope-rejected /settings saves, the rebuilt Home page, the three /quick/* routes (display, quiet-hours, led) including their return_to whitelist and fetch/204 negotiation, the scoped Display/Device settings split, and the Cache-Control/CSP headers"
  - "companion/test_companion_app_04b.py: 34 native pytest tests porting ledger rows 223-266 (the LAST anchor of part 04) — the redirect/static-CSS hardening headers, the session-gated POST /ui-theme and POST /logout, the POST /ui-lang round trip and its no-session gate, the retired POST /ui-mode's unknown-route 404, D-03 language resolution, the nav toggle's gear glyph, the wake-interval environment pre-fill/floor, the login ?next= round trip for a real NAV_TABS member, two route/nav standing-contract guards, the logout/replay/GET-logout/post-logout-tab cluster, the 404 page-header/health-dot leak guard, the retired /preview.png route, gallery path-traversal rejection with a canary file, the illustration image route, the theme-preview image route (including the stateful ?live=1 cache/fallback branch), and the real-PNG illustration upload round trip"
  - "companion/test_companion_app.py shrunk: EXPECTED_CHECK_COUNT 141 -> 52; part 04's 89 checks, their private closures, the now-dead _ago_iso() helper, and the section's now-redundant first login all removed from main()"
  - "the companion_app ledger fragment's rows 178-266 flipped (89 ported across 79 pytest node ids, 0 deleted), Part 04 note added"
affects: [33-18]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "make_app_server's env_overrides= parameter (33-02) replaces the legacy pattern of mutating os.environ before starting a dedicated Harness() and restoring it in a finally block — the wake-interval pre-fill/floor checks now pass env_overrides={app_module.SLEEP_ENV_VAR: \"900\"} (or \"30\") directly to the factory, so the subprocess sees the value at its own startup with no process-wide environment mutation on the test's own interpreter at all"
    - "Three stateful/sequential check clusters — several old checks that shared one mutable harness in a fixed order — are consolidated into one atomic pytest test each, over their own dedicated function-scoped server, rather than split into separate test functions that would silently depend on pytest/xdist happening to run them in file order: the logout/replay/GET-logout/post-logout-tab cluster (rows 238-241), the three gallery-traversal payloads plus the canary check (rows 247-250), and the five-step ?live=1 cache/fallback sequence (rows 261-265, each step's own assertion depends on the previous step's own mutation to the runway_events table and the theme-preview cache directory)"
    - "A module-scoped, already-logged-in server (module_app_server_factory(fake_providers=True) plus one login()) backs every check in each of the two new modules that only reads, or writes a local fixture file directly into the server's own state dir (canary.txt, panel.bin, a gallery PNG) rather than through a mutating HTTP POST; every check that actually writes device config, ends a session, needs its own subprocess environment, or writes an illustration override file gets its own fresh, function-scoped make_app_server server instead (33-MIGRATION-RULES.md section 2)"

key-files:
  created:
    - companion/test_companion_app_04.py
    - companion/test_companion_app_04b.py
  modified:
    - companion/test_companion_app.py
    - .planning/phases/33-companion-tests-on-pytest-behaviour-over-source-text/33-ledger/companion__test_companion_app.md

key-decisions:
  - "The illustration-upload check's own SIDE EFFECTS (the pre-upload GET and the real multipart POST) could not simply be deleted along with its check() wrapper: three still-legacy checks past this plan's own LAST anchor (row 266) — 33-18/part 05's own territory — read the override file the upload writes and the _illustration_pre_upload_render list it populates, by name, via closure. The check's assertions moved to pytest as usual, but its setup stays in main() as bare, un-checked code (an AssertionError on an unexpected status, rather than a check() return), exactly matching 33-MIGRATION-RULES.md section 1's \"setup that remaining checks still need stays\" — confirmed by grepping the whole remaining tail of the file for every name this plan's slice defined, not assumed."
  - "The authenticated section's FIRST login (session_cookie = _login(harness), previously reused by every row-187-241 check this plan just removed) is deleted outright rather than kept: once every check between it and the second (\"re-authenticate\") login is gone, nothing reads that first session before the second login immediately overwrites the same variable. The second login's own comment is corrected to say it is now the section's ONLY login, not a re-authentication."
  - "Rows 178 and 192 (the JS-gate selector-boundary check and the login page's clean-render CSS-rule-existence assertions) are classified under rubric C even though most of their own assertions are markup checks (D), because the technique that needed converting in each — a disk-read companion/static/style.css scan — is the C transformation (css_rules()/rules_with_selector() over served_stylesheet()); the SUMMARY's own rubric split picks the dominant CONVERTED technique per row, matching 33-16's own precedent for mixed-technique checks."
  - "Row 179 (the motion budget) stays a regex over comment-stripped text, per the F-01-sanctioned exception 33-16 already established for the @supports block count: distinguishing a duplicate @keyframes name or a bare-literal animation-duration needs the raw comment-stripped SOURCE, which companion_markup.css_rules()'s per-declaration view cannot recover — the only change from the legacy check is reading served_stylesheet() instead of the file on disk."

requirements-completed: []

# Metrics
duration: ~75min
completed: 2026-09-24
---

# Phase 33 Plan 17: Companion-App Part 04 — Login/Nav/Settings/Quick-Toggle/Illustration/Theme-Preview Summary

**Migrated 89 more companion_app checks (ledger rows 178-266, the largest slice in the chain at 80 original call sites) into two native pytest modules — the login POST/GET flow family, the six NAV_TABS headings, the three /quick/* toggle routes, the scoped Display/Device settings split, D-03 language resolution, the wake-interval environment pre-fill/floor, the logout/replay cluster, the illustration and theme-preview image routes, and the real-PNG illustration upload round trip — consolidating three order-dependent check clusters into atomic tests and keeping the upload's own setup alive in the legacy file for the checks after it that still need it.**

## Performance

- **Duration:** ~75 min (commit-to-commit, including a mid-plan correction of a boundary-line mistake in the legacy shrink, caught before committing)
- **Started:** 2026-09-24T19:32:00Z (approx, first commit)
- **Completed:** 2026-09-24T20:47:00Z (last commit)
- **Tasks:** 3/3 completed
- **Files modified:** 4 (2 created, 2 modified)

## Accomplishments

- `companion/test_companion_app_04.py`: 45 native pytest tests (ledger rows 178-222) — `layout.JS_GATE_CLASS`'s selector-boundary contract and the phase-23 motion budget read structurally/regex over `served_stylesheet()`; login-card.js's public-route, ES5-safe/sink-free, route/src-agreement, no-inline-script and reveal-toggle contracts; the full login POST/GET family (wrong password, right password with cookie flags, the deep-link return round trip, both open-redirect-rejection cases, the renamed `/no-such-route` next value, the dedicated `login_shell()`, the clean/error/lockout card renders — the lockout check driving its own fresh server's `LOGIN_THROTTLE` to its limit); the `page_shell()`/`login_shell()` document-language guard; the six authenticated `NAV_TABS` headings; the retired `/preview`/legacy-route redirects and the `/config` 404; the unscoped and field-rejected `/settings` saves; the rebuilt Home page; all three `/quick/*` routes (display, quiet-hours, led) with their `return_to` whitelist and fetch/204 content negotiation; the scoped Display/Device settings split; and the `Cache-Control`/CSP headers on an authenticated response.
- `companion/test_companion_app_04b.py`: 34 native pytest tests (ledger rows 223-266, the LAST anchor) — the redirect/static-CSS hardening headers; the session-gated `POST /ui-theme`/`POST /logout`; the `POST /ui-lang` round trip and its own no-session gate; the retired `POST /ui-mode`'s unknown-route 404; D-03 language resolution (`Accept-Language`, the `sp_ui_lang` cookie beating it); the nav toggle's gear glyph and translated `aria-label`; the wake-interval environment pre-fill (`SKYPANE_SLEEP_S=900`) and below-floor degrade (`=30`), both driven through `make_app_server`'s `env_overrides=` rather than mutating `os.environ`; the login `?next=/display` round trip; two route/nav-tuple standing-contract guards; the illustration image route (real/unknown/traversal/unauthenticated, plus two isolated manual-resolution-key checks); the theme-preview image route (real/unknown/traversal/unauthenticated); and the real-PNG illustration upload round trip over a real HTTP POST.
- Three stateful, order-dependent check clusters are consolidated into one atomic pytest test each, over their own dedicated fresh server, rather than split into separate functions that would silently depend on file-definition order surviving xdist: the logout/replayed-cookie/GET-logout-404/post-logout-tab-refused sequence (rows 238-241), the three gallery-traversal payloads plus the canary-leak check (rows 247-250), and the five-step `?live=1` sample-fallback/cache-reuse/newer-event/unknown-theme/zero-query sequence (rows 261-265, where each step's assertion depends on the previous step's own mutation to `runway_events` and the theme-preview cache directory).
- The illustration-upload check's setup (the pre-upload GET, the real multipart POST, and populating `_illustration_pre_upload_render`) is kept in the legacy file as bare, un-checked code rather than deleted outright: three still-legacy checks past this plan's own LAST anchor (33-18/part 05's territory) read the override file and the pre-upload render it produces, by name, via closure — confirmed by grepping the remaining tail of the file for every name this slice's own setup defines.
- `companion/test_companion_app.py` shrunk: `EXPECTED_CHECK_COUNT` 141 -> 52; part 04's 89 checks and their private closures removed from `main()`, plus the now-dead `_ago_iso()` helper (used only by the now-migrated stale-pipeline seed) and the authenticated section's now-redundant FIRST login (superseded the instant every check between it and the second login is gone). The shrunk harness runs 52/52 standalone and through `companion/test_legacy_harness_shim.py -k companion_app`. `ruff check` on the shrunk file found and fixed three more now-dead imports (`companion.theme_preview`, `companion.pages.health_page`, `server.history_db`, all only ever used by this plan's own migrated checks) and one redundant `import companion.app as app_module` (F811, already in scope from an earlier line in the same block) before committing.
- The ledger fragment's rows 178-266 flipped (89 `ported` across 79 distinct pytest node ids — three consolidations account for the gap — 0 `deleted`); a `### Part 04 (plan 33-17)` note added recording the rubric-code split (70 B, 15 D, 3 C, 1 J, 0 S), the three consolidations, and the shrink's own dead-code removals. `33-ledger-check.py --allow-pending` confirms 320/320 baseline checks accounted for (267 ported total, 1 deleted, 52 pending).
- Full-suite verification: `pytest -n auto companion test-support server stub-server deploy` as root (`SKYPANE_REQUIRE_BROWSER=1`, real Chromium via `PLAYWRIGHT_BROWSERS_PATH=/tmp/skypane-pw-browsers`) — **2041 passed, 5 skipped, 0 failed** in 231s. `ruff check .` clean across the whole tree. No new DeprecationWarnings in any file this plan wrote (the Pillow `getdata()` warnings in the full-suite output are pre-existing, from `server/test_panel_preview.py`/`server/test_render.py`, untouched by this plan).

## Task Commits

1. **Task 1: Calls #169-#208 (ledger rows 178-222) into test_companion_app_04.py** - `680813b` (test)
2. **Task 2: Calls #209-#248 (ledger rows 223-266) into test_companion_app_04b.py** - `8d47d31` (test)
3. **Task 3: Shrink the legacy harness, fill the ledger, verify** - `8df5c8e` (test)

## Files Created/Modified

- `companion/test_companion_app_04.py` - 45 native pytest tests, part 04a of the companion_app migration chain
- `companion/test_companion_app_04b.py` - 34 native pytest tests, part 04b (the LAST anchor of part 04)
- `companion/test_companion_app.py` - shrunk to `EXPECTED_CHECK_COUNT = 52`; part 04's checks, `_ago_iso()`, and the redundant first login removed; the illustration-upload setup kept as bare code for 33-18's own checks
- `.planning/phases/33-companion-tests-on-pytest-behaviour-over-source-text/33-ledger/companion__test_companion_app.md` - rows 178-266 flipped, Part 04 note added

## Decisions Made

See `key-decisions` in the frontmatter above: keeping the illustration-upload setup alive as bare code for 33-18's own downstream checks (confirmed by grep, not assumed), deleting the now-redundant first login rather than leaving dead code in the shrunk file, and the rubric-code classification convention for the two mixed-technique rows (178, 192) and the one F-01-sanctioned regex-over-served-text exception (179, following 33-16's own precedent for the `@supports` block count).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] First attempt at the legacy shrink cut the slice boundary one function too late, leaving row 178's already-migrated closure as dead code**
- **Found during:** Task 3, while reconstructing the shrunk `main()` body
- **Issue:** The plan's FIRST anchor is the `check()` CALL's own label text ("layout.JS_GATE_CLASS resolves to a real selector..."), but that call's `def _js_gate_class_is_one_name_in_python_and_in_the_stylesheet():` closure begins 19 lines EARLIER in the file. Cutting at the `check(` call line (as an initial pass did) would have left that whole closure — and by the same mechanism, every other row's closure — behind as unreachable dead code, silently duplicating logic already ported to pytest.
- **Fix:** Re-derived the correct cut boundary from the closure's own `def` line (confirmed via `grep -n "^        def _js_gate_class"`) before writing the shrunk file, and verified with a full re-read of the boundary region afterward.
- **Files modified:** `companion/test_companion_app.py` (caught before the file was ever committed in this state — no separate fix commit needed)
- **Verification:** `ruff check` (0 F821 errors) and the 52/52 standalone harness run confirmed no dead closures remained.
- **Committed in:** `8df5c8e` (the boundary was corrected before this, the only shrink commit, was made)

**2. [Rule 3 - Blocking] Three now-dead top-level imports and one redundant re-import surfaced by ruff after the shrink**
- **Found during:** Task 3's own `ruff check` pass on the shrunk file
- **Issue:** `companion.theme_preview`, `companion.pages.health_page` and `server.history_db` were imported at module scope solely for checks this plan just migrated (the theme-preview cache checks and the stale-pipeline-run seed); a second `import companion.app as app_module` inside the kept illustration-upload setup block was already redundant with an earlier import in the same enclosing scope (F811).
- **Fix:** Removed all three now-unused imports from the module-level import line, and removed the redundant re-import (replaced with a one-line comment pointing at the earlier import already in scope).
- **Files modified:** `companion/test_companion_app.py`
- **Verification:** `ruff check` clean (0 errors); 52/52 harness re-run confirmed no behaviour change.
- **Committed in:** `8df5c8e`

---

**Total deviations:** 2 auto-fixed (1 bug caught pre-commit, 1 blocking lint cleanup)
**Impact on plan:** Neither affected any test's behaviour — both were caught and corrected during the shrink itself, before the Task 3 commit was made. No production code was touched.

## Issues Encountered

None beyond the deviations above. The 80-call-site / 89-row split described in the plan's own `<slice>` (loop-generated calls expanding 4 call sites into 13 ledger rows: 2 open-redirect values, 6 NAV_TABS tabs, 2 legacy-route pairs, 3 gallery-traversal payloads) matched exactly what the current file's anchor labels bounded, confirming the FIRST/LAST anchor approach (rather than the plan's own approximate call-number range, which had drifted slightly from later Phase 37 coordination) as the reliable way to find the slice.

## User Setup Required

None.

## Next Phase Readiness

- 33-18 (part 05, the chain's LAST plan) continues from ledger row 267 (`the overridden air-france render and the vueling-airlines render...come out of the identical illustration_normalize pipeline`), immediately after this plan's LAST anchor.
- The illustration-upload setup this plan kept alive (the pre-upload GET, the real multipart POST, `_illustration_pre_upload_render`, `_VENDORED_ILLUSTRATIONS_DIR`, `_vendored_air_france_path`, `_pre_upload_vendored_hash`, `_pre_upload_vendored_stat`) is confirmed present and correct in the shrunk file — 33-18 will migrate the checks that read it, then can retire the setup itself once nothing legacy reads it any more.
- 33-18 is expected to be the chain's closing plan: after it, `EXPECTED_CHECK_COUNT` should reach 0 and the legacy file can be deleted outright (33-MIGRATION-RULES.md section 1's "the chain's LAST plan deletes the legacy file with `git rm`").
- No blockers.

---
*Phase: 33-companion-tests-on-pytest-behaviour-over-source-text*
*Completed: 2026-09-24*

## Self-Check: PASSED

All 4 claimed created/modified files found on disk (`companion/test_companion_app_04.py`,
`companion/test_companion_app_04b.py`, `companion/test_companion_app.py`,
`.planning/phases/33-companion-tests-on-pytest-behaviour-over-source-text/33-ledger/companion__test_companion_app.md`)
plus this summary, and all 3 commit hashes (`680813b`, `8d47d31`, `8df5c8e`) found in
`git log --oneline --all`.
