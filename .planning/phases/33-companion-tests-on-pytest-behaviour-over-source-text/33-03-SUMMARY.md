---
phase: 33-companion-tests-on-pytest-behaviour-over-source-text
plan: 03
subsystem: testing
tags: [pytest, ast, css-parser, html-parser, migration-guard, companion]

# Dependency graph
requires:
  - phase: 33-companion-tests-on-pytest-behaviour-over-source-text
    plan: "01"
    provides: "the migration ledger tool and baselines every later plan's ledger fragment updates build on (not used directly by this plan, but the same phase's shared context)"
  - phase: 33-companion-tests-on-pytest-behaviour-over-source-text
    plan: "02"
    provides: "companion/conftest.py's app_server/make_app_server/new_context fixtures and companion_app_server.py's http_request/served_stylesheet/served_asset - this plan's guard enforces that every later module uses them instead of redefining Harness/http_request"
provides:
  - "test-support/companion_markup.py: parse_html()/Node (select/find_all/find/text over html.parser), css_rules()/declarations_for()/rules_with_selector()/keyframes()/custom_properties() (a brace/string-aware CSS tokenizer over nested @media/@supports/@keyframes), strip_js_comments_and_strings()"
  - "companion/test_suite_guards.py: scan_source()/scanned_files() - an ast.NodeVisitor enforcing TST-10/12/13/14's G1-G10 rules on every non-legacy companion test module, with its own 30 detector self-tests"
  - "skypane_test_support.ORIGINAL_COMPANION_HARNESSES / legacy_companion_harnesses() / LEGACY_COMPANION_HARNESSES / LEGACY_HELPER_MODULES / LEGACY_COMPANION_COLLECT_IGNORE - the legacy companion set, derived from disk instead of hand-edited"
  - "companion/test_legacy_harness_shim.py::test_legacy_set_is_consistent_with_disk - replaces the old exact-set hand-list check with a three-part disk-consistency proof"
affects: [33-04, 33-05, 33-06, 33-07, 33-08, 33-09, 33-10, 33-11, 33-12, 33-13, 33-14, 33-15, 33-16, 33-17, 33-18, 33-19, 33-20, 33-21, 33-22, 33-23, 33-24, 33-25, 33-26, 33-27, 33-28, 33-29, 33-30, 33-31, 33-32]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "companion_markup.py's CSS tokenizer is brace/string-aware from the ground up (a shared _tokenize_css_top_level()/_extract_block_body() pair, both scanning char-by-char with explicit quote-state tracking) rather than regex-splitting on ';'/'{'/'}', so a declaration value containing a quoted ';' or '}' (content: \"};\") or nested parens (color-mix(in srgb, ...)) never breaks parsing - proven against the real 10,689-line companion/static/style.css (585 rules, 4 keyframes, 33 :root custom properties, parsed in ~22ms) in addition to the unit tests"
    - "declarations_for()'s two-tier miss semantics: KeyError only when `selector` matches no rule anywhere in the stylesheet; an empty dict when it exists but not under the requested at_rules context. This lets a migrated test assert 'this selector's media-query variant has no override' without it reading as 'this selector doesn't exist, something is badly wrong'"
    - "test_suite_guards.py's exemption set has a getattr() compatibility shim (skypane_test_support.legacy_companion_harnesses() with a fallback to the pre-Task-3 LEGACY_COMPANION_HARNESSES hand tuple) specifically so Task 2 and Task 3 of the same plan can land as independent, individually-green commits regardless of order - neither task's files_modified list includes the other's files"
    - "the legacy-companion-set derivation lives in ONE function (skypane_test_support.legacy_companion_harnesses()), computed once at import time into LEGACY_COMPANION_HARNESSES, and read by three independent consumers (the shim's parametrize, conftest.py's collect_ignore via LEGACY_COMPANION_COLLECT_IGNORE, and test_suite_guards.py's scanned_files()) - a migration plan that finishes a harness needs to touch only that harness's own EXPECTED_CHECK_COUNT line to shrink the set everywhere at once"

key-files:
  created:
    - test-support/companion_markup.py
    - test-support/test_companion_markup.py
    - companion/test_suite_guards.py
  modified:
    - test-support/skypane_test_support.py
    - test-support/test_test_support.py
    - companion/test_legacy_harness_shim.py
    - companion/test_app_server_fixture.py
    - companion/test_browser_policy.py

key-decisions:
  - "companion/test_browser_ux_helpers.py is added to test_suite_guards.py's ALWAYS_EXEMPT (alongside the guard's own file and the shim), not left to fail the guard nor force-fixed: its three browser.new_context(...) calls (G10) predate 33-02's guarded new_context fixture, and routing them through it means threading that fixture through every one of test_browser_ux.py's own call sites - real behavioural plumbing 33-19 owns, not a rename this plan can make safely"
  - "Rule 3 (blocking, auto-fixed): the new guard's own per-file self-test caught two real G8 violations the guard did not yet exist to catch when 33-02 landed - a dead 'if __name__ == \"__main__\": raise SystemExit(pytest.main(...))' tail in both companion/test_app_server_fixture.py and companion/test_browser_policy.py (never reached under pytest execution, since pytest never imports a test module as __main__). Removed both, plus the now-unused `import pytest` this left behind in test_app_server_fixture.py. Both modules re-verified fully green afterward (11 + 5 tests, including the 3 real-browser tests with SKYPANE_REQUIRE_BROWSER=1)"

patterns-established:
  - "Every migration plan from 33-04 onward writes companion_markup.parse_html(served_html).select(...) / css_rules(served_stylesheet(server)) instead of a regex/substring probe over rendered HTML or a disk-read stylesheet, and every new module it writes is provable non-legacy the moment test_suite_guards.py's per-file parametrize picks it up (no plan needs to edit the guard itself to be covered by it)"

requirements-completed: []

# Metrics
duration: 28min
completed: 2026-09-24
---

# Phase 33 Plan 03: Migration Toolkit and the Behaviour-Over-Source-Text Guard Summary

**Built the three pieces every later companion-harness migration plan depends on: stdlib HTML/CSS/JS structural parsers (`companion_markup.py`) that replace source-text idioms, an `ast`-based guard (`test_suite_guards.py`) enforcing TST-10/12/13/14 with 10 detector rules and 30 self-tests, and a disk-derived legacy-harness set that replaces the hand-edited `LEGACY_COMPANION_HARNESSES` tuple everywhere it was read.**

## Performance

- **Duration:** ~28 min
- **Started:** 2026-09-24T09:17:51Z (previous plan's completion timestamp)
- **Completed:** 2026-09-24T09:46:00Z
- **Tasks:** 3/3 completed
- **Files modified:** 8 (3 created, 5 modified)

## Accomplishments

- `test-support/companion_markup.py`: a stdlib-only (`re`, `html.parser`, `typing`) toolkit — `parse_html()`/`Node` give `select()`/`find_all()`/`find()`/`text()` over a small DOM built on `html.parser.HTMLParser` (void elements never swallow siblings; an unsupported selector raises `ValueError`, never a silent empty list); `css_rules()`/`declarations_for()`/`rules_with_selector()`/`keyframes()`/`custom_properties()` are a brace/string-aware tokenizer handling nested `@media`/`@supports`, comma selector lists, `@keyframes` (recorded separately, never returned as rules), and declaration values containing `;`/`}` or nested parens; `strip_js_comments_and_strings()` is a small state machine over `//`, `/* */`, quotes and backticks. 17/17 unit tests pass (RED confirmed via a temporary `ModuleNotFoundError` before the implementation existed), ruff clean. Smoke-tested live against the real 10,689-line `companion/static/style.css`: 585 rules, 4 keyframes, 33 `:root` custom properties, parsed in ~22ms with no errors.
- `companion/test_suite_guards.py`: `scan_source()` is an `ast.NodeVisitor` implementing all 10 rules from the plan (G1 planning/UI-SPEC strings, G2 `inspect`/`ast`/`tokenize`/`linecache` introspection, G3 a source-suffixed `open()`/`.read_text()`/`.read_bytes()`/`os.path.join()`/`Path()`/`Path /` over `__file__`/`HERE`/`REPO_ROOT`/`*_DIR`/`*_ROOT`, G4 `.__doc__`, G5 `Harness`/`_InProcessHarness`/`_NoRedirectHandler`/`http_request`/an `HTTPRedirectHandler` subclass/`build_opener`, G6 a `/nonexistent` literal or `tempfile.*`, G7 `os.chmod` without `@requires_non_root`, G8 `EXPECTED_CHECK_COUNT`/module-level `check()`/`main()`/`if __name__ == "__main__"`, G9 a `*_helpers.py` module missing `__test__ = False`, G10 a direct `browser.new_context()`/`new_page()`/`sync_playwright()` call). 18 positive self-tests (one per rule, including G9's filename-driven case) + 8 negative self-tests (a served route, a docstring, a comment, `/no-such-route`, a PNG path, a `tmp_path` probe write, a `@requires_non_root`-decorated chmod, a `_helpers.py` with the marker) + a per-file parametrized test over the current scanned set (`companion/conftest.py`, `test_app_server_fixture.py`, `test_browser_policy.py`) + an exemption-set guard = 30 tests, all green, ruff clean.
- `test-support/skypane_test_support.py`: `ORIGINAL_COMPANION_HARNESSES` (the frozen 9-path pre-Phase-33 set) plus `legacy_companion_harnesses()` (returns the subset that exists on disk AND still has a line matching `^EXPECTED_CHECK_COUNT\s*=`, reading test files only) replace the old hand-written `LEGACY_COMPANION_HARNESSES` tuple; `LEGACY_COMPANION_HARNESSES` is now computed from that function at import time. `companion/test_legacy_harness_shim.py`'s `test_legacy_harness_list_matches_disk` (an exact-set equality check that broke the moment 33-02 added two new non-legacy `companion/test_*.py` modules) is replaced by `test_legacy_set_is_consistent_with_disk`, a three-part proof (every legacy path exists; every non-legacy original is gone or marker-free; no `companion/test_*.py` outside the 9 originals hides a fresh `EXPECTED_CHECK_COUNT`). `conftest.py` needed no change (`git diff --quiet conftest.py` confirmed). All 9 harnesses still detected as legacy today (confirmed both by the plan's own python one-liner and by a monkeypatched-`REPO_ROOT` unit test against a disposable fake tree in `test-support/test_test_support.py`).

## Task Commits

1. **Task 1 (RED): add failing tests for companion_markup parsers** - `758d014` (test)
2. **Task 1 (GREEN): implement companion_markup stdlib HTML/CSS/JS parsers** - `71e7657` (feat)
3. **Task 2: add the TST-10/12/13/14 behaviour-over-source-text guard** - `2072161` (feat)
4. **Task 3: derive the legacy companion harness set from disk** - `dd0fcf9` (feat)

## Files Created/Modified

- `test-support/companion_markup.py` - stdlib HTML/CSS/JS structural parsers migrated tests build on instead of source-text idioms
- `test-support/test_companion_markup.py` - 17 self-tests, one per `<behavior>` line
- `companion/test_suite_guards.py` - the TST-10/12/13/14 `ast`-based guard, 30 tests
- `test-support/skypane_test_support.py` - `ORIGINAL_COMPANION_HARNESSES`, `legacy_companion_harnesses()`, disk-derived `LEGACY_COMPANION_HARNESSES`/`LEGACY_HELPER_MODULES`/`LEGACY_COMPANION_COLLECT_IGNORE`
- `test-support/test_test_support.py` - a monkeypatched-fake-tree unit test for `legacy_companion_harnesses()`
- `companion/test_legacy_harness_shim.py` - `test_legacy_set_is_consistent_with_disk` replaces the exact-set hand-list check
- `companion/test_app_server_fixture.py` - dead `if __name__ == "__main__"` tail and now-unused `import pytest` removed (Rule 3 deviation, see below)
- `companion/test_browser_policy.py` - same dead tail removed (Rule 3 deviation, see below)

## Decisions Made

- `companion/test_browser_ux_helpers.py` joins `test_suite_guards.py`'s `ALWAYS_EXEMPT` (three real `browser.new_context(...)` calls, G10) rather than being fixed here or left failing the guard — converting them means threading 33-02's guarded `new_context` fixture through every one of `test_browser_ux.py`'s own call sites, real plumbing 33-19 owns per the plan's own explicit instruction, not a same-plan rename.
- `test_suite_guards.py`'s exemption computation uses a `getattr(skypane_test_support, "legacy_companion_harnesses", None)` compatibility shim with a fallback to the pre-Task-3 hand tuple, so Task 2's own commit (before Task 3 exists) and every later run (after Task 3 lands) both work without a second edit to this file — Task 3's `files_modified` list never includes `test_suite_guards.py`, confirming this was the intended design rather than a workaround.
- `declarations_for()` distinguishes "selector matches no rule anywhere" (raises `KeyError`) from "selector exists but not under this `at_rules` context" (returns `{}`) — reconciling the plan's `<behavior>` examples (`declarations_for(css, ".x")` → `{}` when `.x` only exists nested under `@media`) with its `<action>` prose ("raises KeyError when no rule matches"), read as two different senses of "no rule matches."

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Removed dead `if __name__ == "__main__"` tails the new guard correctly flagged (G8) in two of 33-02's own modules**
- **Found during:** Task 2, running `test_suite_guards.py`'s own `test_module_obeys_behaviour_over_source_rules` against the current scanned set
- **Issue:** `companion/test_app_server_fixture.py:226` and `companion/test_browser_policy.py:123` both carried `if __name__ == "__main__": raise SystemExit(pytest.main([__file__, "-v"]))` — legitimate-looking but dead code, since pytest never imports a test module as `__main__`. This is exactly the G8 legacy-harness-shape rule the guard exists to enforce, and it genuinely blocked Task 2's own acceptance criteria (the per-file test must pass on the current tree).
- **Fix:** Removed both tails; removed the now-unused `import pytest` this left behind in `test_app_server_fixture.py` (`import pytest` was otherwise unused there — `test_browser_policy.py` still needs it for `pytest.mark.browser`/`pytest.raises`/`pytest.mark.slow`, so its import stayed).
- **Files modified:** `companion/test_app_server_fixture.py`, `companion/test_browser_policy.py`
- **Verification:** Both modules re-run standalone afterward — 11/11 and 5/5 tests green respectively, including the 3 real-Chromium tests in `test_browser_policy.py` (`SKYPANE_REQUIRE_BROWSER=1`, `PLAYWRIGHT_BROWSERS_PATH=/tmp/skypane-pw-browsers`). `ruff check` clean on both.
- **Committed in:** `2072161` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Necessary for Task 2's own guard to prove anything about the current tree; zero behavioural change (dead code under pytest execution in both cases). No scope creep — no other file was touched for this fix.

## Issues Encountered

None beyond the deviation above. One editing slip while adding a unit test to `test-support/test_test_support.py` (an `Edit` call's `old_string` match didn't include a trailing line, briefly leaving a stray duplicate `empty.json()` line at file end) was caught immediately by a follow-up `ast.parse()` syntax check before running any test, and corrected before commit — never landed in a commit.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Every migration plan from 33-04 onward has `companion_markup.py`'s parsers, the live guard, and the disk-derived legacy set ready to use with zero further setup.
- Full-suite verification (`pytest -n auto companion test-support server stub-server`, `SKYPANE_REQUIRE_BROWSER=1`, real Chromium via `PLAYWRIGHT_BROWSERS_PATH=/tmp/skypane-pw-browsers`): **836 passed, 2 failed, 3 skipped in 305s.** The 2 failures are the exact same pre-existing root-sandbox artifacts already classified in `33-BASELINE/INDEX.md` before this plan started (`test_companion_app`'s two `os.chmod` read-only-under-root checks; `test_status_pages`'s `anomaly_active("/nonexistent/...")` mkdir-as-root check) — this sandbox runs as `euid 0`, and 33-01/33-02's own summaries hit and documented the identical failures. Neither is caused by, nor in scope for, this plan (33-14/33-25 own their fixes per `33-MIGRATION-RULES.md`). No other regression anywhere in the 836-test run.
- `test_browser_ux_helpers.py`'s `ALWAYS_EXEMPT` entry is a named, tracked debt for 33-19 to remove alongside its own conversion work — not an open-ended exemption.
- No blockers for 33-04 (the first harness-migration plan).

---
*Phase: 33-companion-tests-on-pytest-behaviour-over-source-text*
*Completed: 2026-09-24*

## Self-Check: PASSED

All 8 claimed created/modified files found on disk (`test-support/companion_markup.py`,
`test-support/test_companion_markup.py`, `companion/test_suite_guards.py`,
`test-support/skypane_test_support.py`, `test-support/test_test_support.py`,
`companion/test_legacy_harness_shim.py`, `companion/test_app_server_fixture.py`,
`companion/test_browser_policy.py`) plus this summary, and all 4 commit hashes
(`758d014`, `71e7657`, `2072161`, `dd0fcf9`) found in `git log --oneline --all`.
