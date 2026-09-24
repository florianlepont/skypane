---
phase: 33-companion-tests-on-pytest-behaviour-over-source-text
plan: 16
subsystem: testing
tags: [pytest, companion-app, es5-safe-scripts, css-structural-parsing, no-js-control-contract, migration]

# Dependency graph
requires:
  - phase: 33-companion-tests-on-pytest-behaviour-over-source-text
    plan: "15"
    provides: "companion/test_companion_app_helpers.py's shared test doubles, the shrunk companion/test_companion_app.py (EXPECTED_CHECK_COUNT=196) this plan continues shrinking, and the restored main()-level app_module import / _unauth_redirects_to_login() / _static_script_public() plumbing this plan's own checks (and 33-17/33-18's) still depend on"
  - phase: 33-companion-tests-on-pytest-behaviour-over-source-text
    plan: "02"
    provides: "companion/conftest.py's app_server/make_app_server/module_app_server_factory fixtures and test-support/companion_app_server.py's http_request/login/served_asset/served_stylesheet — this plan's static-script and no-JS-control-contract checks use them instead of the legacy Harness"
  - phase: 33-companion-tests-on-pytest-behaviour-over-source-text
    plan: "03"
    provides: "test-support/companion_markup.py's css_rules()/declarations_for() (the .js gate, control-vocabulary and submit-guard CSS checks) and companion/test_suite_guards.py's TST-10/12/13/14 guard, which now scans this plan's new module"
provides:
  - "companion/test_companion_app_03.py: 55 native pytest tests porting companion/test_companion_app.py's original check() calls across ledger rows 123-177 — dirty-state.js's own animation contract; freshness.js/panel-lookup.js/flash-cleanup.js/poll-cooldown.js/confirm-submit.js/theme-preview.js/flight-rows.js/submit-guard.js/relative-time.js/quick-switch.js/value-controls.js's public-route, ES5-safe/sink-free, route/src-agreement and served-body checks; the relative-time/duration wording ladders; the .js gate and shared control vocabulary in style.css; companion.battery's total life-estimate contract; and the executable _NO_JS_CONTROL_REGISTRY contract"
  - "companion/test_companion_app_helpers.py gains strip_js_line_and_block_comments() (shared with later parts of this chain)"
  - "companion/test_companion_app.py shrunk: EXPECTED_CHECK_COUNT 196 -> 141; part 03's checks, their private closures, and the now-unused module-level _NO_JS_CONTROL_REGISTRY tuple removed from main()"
  - "the companion_app ledger fragment's rows 123-177 flipped (55 ported, 0 deleted), Part 03 note added"
affects: [33-17, 33-18]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "A module-scoped app03_server fixture (module_app_server_factory(fake_providers=True)) backs every read-only check in the module; the one check that logs in (the _NO_JS_CONTROL_REGISTRY contract) uses its own function-scoped make_app_server server instead, per 33-MIGRATION-RULES.md section 2's POST-implies-function-scoped rule"
    - "Two checks whose original technique guard G2 bans are rewritten as pure behaviour rather than ported verbatim or deleted: relative-time.js's boundary-mirror check now DISCOVERS layout._age_bucket()'s three s/m/h/d boundaries by bisecting over the function's own return value (never inspect.getsource()), and the battery-module import check now imports companion.battery fresh in a subprocess and reads sys.modules (never ast.parse()) — the same technique 33-15-PLAN.md's draw-module-imports check already established"
    - "A check that used to open companion/static/style.css AND companion/app.py from disk (the submit-guard.js CSS/CSP check) is split into two behavioural reads: the CSS ordering assertion now walks css_rules(served_css) — a source-order-preserving list — comparing rule INDICES instead of text offsets, and the CSP assertion now reads a real GET /login response header, additionally cross-checked against companion.app.CONTENT_SECURITY_POLICY (stronger than reading the Python literal, since it proves the header is actually sent)"
    - "One check (the @supports selector(:has(*)) block count) is kept as a documented, F-01-sanctioned exception to structural CSS parsing: distinguishing a second, identically-nested feature-query block from the rules already inside today's one block needs block-POSITION information no companion_markup.css_rules() caller can recover (the parser records at-rule PRELUDE TEXT, not where it started in the file) — so it stays a comment-stripped regex count, but over the SERVED stylesheet, never a disk read"

key-files:
  created:
    - companion/test_companion_app_03.py
  modified:
    - companion/test_companion_app_helpers.py
    - companion/test_companion_app.py
    - .planning/phases/33-companion-tests-on-pytest-behaviour-over-source-text/33-ledger/companion__test_companion_app.md

key-decisions:
  - "The module-level _NO_JS_CONTROL_REGISTRY tuple (and its documenting comment block, ~150 lines) is removed from the legacy file during the shrink, not merely left in place: it is a module-level constant, not a closure inside main(), but grepping the whole repo confirmed it is read by exactly one check (the one this plan migrated) and named nowhere else except in production-code comments. Confirmed safe by a clean `ruff check` (0 F821 undefined-name errors) on the shrunk file before committing, following 33-15's own precedent of tracing every F821 error back to its origin rather than assuming plumbing is dead."
  - "_static_script_public() (defined just above this plan's own slice, textually adjacent) is confirmed to survive the shrink untouched: it is still called by name from /static/login-card.js's own still-legacy check further down main() (33-17/33-18 territory), the same shared-plumbing shape 33-15 already restored for _unauth_redirects_to_login()/_static_script_public() itself."
  - "The submit-guard.js check's CSS ordering assertion (button:disabled must stay AFTER button:active in source order) is expressed as an index comparison over css_rules(served_css)'s source-order-preserving list, rather than declarations_for()'s merged dict (which discards order) — declarations_for() answers 'what does this selector declare', not 'which rule came first', and this check specifically needs the latter."
  - "relative-time.js's boundary-mirror check's Python-side boundaries are DISCOVERED by bisection over layout._age_bucket()'s own return value rather than assumed to be the historically-known 60/3600/86400: the check would keep working unchanged if those constants were ever revised, which a check that hard-coded the expected numbers would not."
  - "The @supports selector(:has(*)) block-count check keeps a regex over the SERVED (HTTP-fetched) stylesheet — recorded explicitly in the ledger's Part 03 note as an F-01-sanctioned exception — because block POSITION (not per-rule at-rule text) is the property being measured, and companion_markup.css_rules() has no API that exposes it."

requirements-completed: []

# Metrics
duration: ~17min
completed: 2026-09-24
---

# Phase 33 Plan 16: Companion-App Part 03 — Static-Script Gauntlet, Wording Ladders, CSS Control Vocabulary, No-JS Contract Summary

**Migrated 55 more companion_app checks (ledger rows 123-177) to native pytest — the remaining nine static scripts' public-route/ES5-safe/route-agreement/served-body checks, the relative-time/duration wording ladders, the `.js` gate and shared control vocabulary in `style.css`, `companion.battery`'s total life-estimate contract, and the executable `_NO_JS_CONTROL_REGISTRY` contract — replacing two `guard-G2`-banned source-introspection checks with behavioural rewrites and folding a disk-read CSS/CSP check into a structural stylesheet read plus a real response-header check.**

## Performance

- **Duration:** ~17 min (commit-to-commit)
- **Started:** 2026-09-24T16:52:00Z (approx, first commit)
- **Completed:** 2026-09-24T17:09:41Z (last commit)
- **Tasks:** 3/3 completed
- **Files modified:** 4 (1 created, 3 modified)

## Accomplishments

- `companion/test_companion_app_03.py`: 55 native pytest tests, one per ledger row (no consolidation, no parametrization needed for this part) — dirty-state.js's own remove/reflow/re-add animation contract; freshness.js/panel-lookup.js/flash-cleanup.js/poll-cooldown.js/confirm-submit.js/theme-preview.js/flight-rows.js/submit-guard.js/relative-time.js/quick-switch.js/value-controls.js's public-route, ES5-safe/sink-free, route/src cross-file agreement, `<script>`-tag-count and served-body contracts, all driven against a real `companion/app.py` subprocess via `served_asset()`/`http_request()` instead of disk reads or the legacy Harness; the relative-time/duration wording ladders (every wording layout renders, filled with `_age_bucket()`'s own quantity, equals the ladder functions' own output in both languages); the `.js` gate and 44px shared control vocabulary in `companion/static/style.css`, read structurally via `companion_markup.css_rules()`/`declarations_for()` over the served stylesheet; `companion.battery.battery_life_estimate()`'s totality contract across six series shapes; and the executable `_NO_JS_CONTROL_REGISTRY` contract, proven non-vacuous against four fixtures built from real group-builder output.
- Two checks that read production `.py` source with a guard-G2-banned technique are resolved per rubric S rather than ported as-is: the relative-time boundary-mirror check now DISCOVERS `layout._age_bucket()`'s three s/m/h/d boundaries by bisecting over the function's own return value instead of `inspect.getsource()`; the battery-module import check now imports `companion.battery` fresh in a subprocess and reads `sys.modules` instead of `ast.parse()` — the exact technique 33-15's `test_draw_module_imports_no_page_and_no_server` established.
- One check (submit-guard.js's served-body/CSS/CSP contract) that used to open both `companion/static/style.css` and `companion/app.py` from disk is split into two behavioural reads: the CSS ordering half now compares rule indices in `css_rules(served_css)` (a source-order-preserving list), and the CSP half now reads a real `GET /login` response header, additionally cross-checked against `companion.app.CONTENT_SECURITY_POLICY` — strictly stronger than reading the Python literal, since it proves the header is actually sent.
- One check (the `@supports selector(:has(*))` block count) is kept as a documented, F-01-sanctioned exception: distinguishing a second, identically-nested feature-query block needs block-position information `companion_markup.css_rules()` has no API for (it records at-rule prelude TEXT, not position), so it stays a comment-stripped regex count over the served (never disk-read) stylesheet.
- `companion/test_companion_app.py` shrunk: `EXPECTED_CHECK_COUNT` 196 → 141; part 03's checks and their private closures removed from `main()`, plus the now-unused module-level `_NO_JS_CONTROL_REGISTRY` tuple (confirmed safe to remove — read by exactly one check, the one this plan migrated). The shrunk harness runs 141/141 standalone and through `companion/test_legacy_harness_shim.py -k companion_app`. `_static_script_public()`, textually adjacent to this plan's slice, was confirmed to survive untouched (still called by `/static/login-card.js`'s own still-legacy check further down `main()`), via a clean `ruff check` (0 F821 errors) before committing.
- The ledger fragment's rows 123-177 flipped (55 `ported`, 0 `deleted`); a `### Part 03 (plan 33-16)` note added recording the rubric-code split (9 B, 27 J, 6 D, 3 C, 2 S) and the three hard-case dispositions (the two S-rewrites, the submit-guard.js CSS/CSP split, and the documented `@supports` block-count exception). `33-ledger-check.py --allow-pending` confirms 320/320 baseline checks accounted for (178 ported total, 1 deleted, 141 pending).
- Full-suite verification beyond the plan's own scoped checks: `pytest -n auto companion test-support server stub-server` as root (`SKYPANE_REQUIRE_BROWSER=1`, real Chromium via `PLAYWRIGHT_BROWSERS_PATH=/tmp/skypane-pw-browsers`) — **1633 passed, 5 skipped, 0 failed** (up from the prior baseline's 1577 passed/5 skipped; +56 = the 55 new tests plus the guard's own new per-file parametrize node for `test_companion_app_03.py`). `ruff check .` clean across the whole tree. No new DeprecationWarnings in any file this plan touched.

## Task Commits

1. **Task 1: First half of part 03 (rows 123-149)** - `8e4e11a` (test)
2. **Task 2: Second half of part 03 (rows 150-177)** - `af8d87b` (test)
3. **Task 3: Shrink the legacy harness, fill the ledger, verify** - `976baf6` (test)

## Files Created/Modified

- `companion/test_companion_app_03.py` - 55 native pytest tests, part 03 of the companion_app migration chain
- `companion/test_companion_app_helpers.py` - gains `strip_js_line_and_block_comments()` (shared with 33-17/33-18)
- `companion/test_companion_app.py` - shrunk to `EXPECTED_CHECK_COUNT = 141`; the now-dead module-level `_NO_JS_CONTROL_REGISTRY` tuple removed alongside the checks that used it
- `.planning/phases/33-companion-tests-on-pytest-behaviour-over-source-text/33-ledger/companion__test_companion_app.md` - rows 123-177 flipped, Part 03 note added

## Decisions Made

See `key-decisions` in the frontmatter above: removing the now-dead `_NO_JS_CONTROL_REGISTRY` module-level tuple during the shrink (confirmed via a repo-wide grep plus a clean `ruff check`), confirming `_static_script_public()` survives untouched for 33-17/33-18, expressing the submit-guard.js CSS ordering check as a `css_rules()` index comparison rather than `declarations_for()`'s merged/order-losing dict, discovering the relative-time ladder's boundaries by bisection rather than hard-coding the historically-known constants, and keeping the `@supports selector(:has(*))` block count as a documented served-text exception (F-01) rather than forcing a structural expression that does not exist.

## Deviations from Plan

None — plan executed exactly as written. The two rubric-S rewrites and the submit-guard.js CSS/CSP split were anticipated in the plan's own `<slice>`/hotspots section ("JS behaviour described via source... prefer the served-asset contract, or delete with code J") and in `33-MIGRATION-RULES.md`'s rubric table; no unplanned production code was touched.

## Issues Encountered

None beyond the deviations already covered above (none occurred). The plan's own "55 calls" count matched the ledger's row count exactly for this part (unlike 33-15, where three loop-generated call sites expanded 63 source calls into 72 ledger rows) — no loops in this slice, so the anchor-label boundaries and the row count agreed from the start.

## User Setup Required

None.

## Next Phase Readiness

- 33-17 (part 04) continues from ledger row 178 (`layout.JS_GATE_CLASS resolves to a real selector in companion/static/style.css...`), immediately after this plan's LAST anchor.
- The shared main()-level plumbing 33-17/33-18 still need (`app_module` import, `_unauth_redirects_to_login`, `_static_script_public`) is confirmed present and correct in the shrunk file.
- `companion/test_companion_app_helpers.py`'s `strip_js_line_and_block_comments()` is available for any later part's own comment-sensitive served-JS checks.
- No blockers.

---
*Phase: 33-companion-tests-on-pytest-behaviour-over-source-text*
*Completed: 2026-09-24*

## Self-Check: PASSED

All 4 claimed created/modified files found on disk (`companion/test_companion_app_03.py`,
`companion/test_companion_app_helpers.py`, `companion/test_companion_app.py`,
`.planning/phases/33-companion-tests-on-pytest-behaviour-over-source-text/33-ledger/companion__test_companion_app.md`)
plus this summary, and all 3 commit hashes (`8e4e11a`, `af8d87b`, `976baf6`) found in
`git log --oneline --all`.
