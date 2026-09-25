---
phase: 33-companion-tests-on-pytest-behaviour-over-source-text
plan: 32
subsystem: testing
tags: [pytest, guard, css-parsing, ci, docs, retirement]

# Dependency graph
requires:
  - phase: 33-companion-tests-on-pytest-behaviour-over-source-text
    plan: "31"
    provides: "the last legacy companion harness deleted; legacy_companion_harnesses() == () and 33-ledger-check.py --all at 0 pending"
  - phase: 33-companion-tests-on-pytest-behaviour-over-source-text
    plan: "03"
    provides: "companion_markup's CSS parser and the TST-10/12/13/14 guard this plan makes strict"
provides:
  - "no transition machinery left: the shim, ORIGINAL/LEGACY_* lists, legacy_companion_harnesses(), collect_ignore, the legacy_harness marker and LegacyHarness (plus its meta-test) are deleted"
  - "a strict guard: scanned_files() is every companion/test_*.py plus companion/conftest.py minus the guard itself; test_no_legacy_runner_anywhere covers server/, stub-server/, test-support/, companion/ and deploy/tests/"
  - "guard rule G11 (no regex / `in` / str search over served stylesheet text) with failing-sample self-tests and a live-allowlist check; guard rule G12 (a test module never imports another test module)"
  - "companion_markup.rule_indices() and at_rule_blocks(), unit-tested"
  - "33-FOLLOWUPS.md F-01 resolved (commit 807e9b2)"
  - "caption_word_count_text() shared from companion/test_config_page_helpers.py"
  - "CI paths filter without .planning re-includes, deploy/README.md re-included; runner, CLAUDE.md, README and CONTRIBUTING describe the finished suite"
  - "stub-server/test_devices_registry.py on tmp_path, its __main__ runner removed"
affects: ["33-33"]

tech-stack:
  added: []
  patterns:
    - "G11 is a flow-insensitive taint pass per module: sources are served_stylesheet() and the body of a GET of the style route; taint flows through assignments, fixtures (by parameter name), str transforms, slices, re.* results and calls to the module's own functions; sinks are re.* / compiled-pattern calls, `in` tests and str search methods"
    - "Stylesheet source order is asserted with rule_indices(); 'exactly one block' is asserted with at_rule_blocks().count(prelude); 'inside the feature query' is declarations_for(..., at_rules=(prelude,))"

key-files:
  created:
    - .planning/phases/33-companion-tests-on-pytest-behaviour-over-source-text/33-32-SUMMARY.md
  modified:
    - companion/test_suite_guards.py
    - test-support/companion_markup.py
    - test-support/test_companion_markup.py
    - test-support/skypane_test_support.py
    - test-support/test_test_support.py
    - test-support/companion_app_server.py
    - conftest.py
    - pyproject.toml
    - companion/conftest.py
    - companion/test_app_server_fixture.py
    - companion/test_browser_ux_helpers.py
    - companion/test_login_throttle.py
    - companion/test_post_origin.py
    - companion/test_config_page_02.py
    - companion/test_config_page_03.py
    - companion/test_config_page_05.py
    - companion/test_config_page_helpers.py
    - companion/test_companion_app_02.py
    - companion/test_companion_app_03.py
    - companion/test_companion_app_04.py
    - companion/test_companion_app_05.py
    - companion/test_view_pages_03.py
    - stub-server/test_devices_registry.py
    - scripts/run-all-tests.sh
    - .github/workflows/ci.yml
    - .claude/CLAUDE.md
    - README.md
    - CONTRIBUTING.md
    - .planning/phases/33-companion-tests-on-pytest-behaviour-over-source-text/33-FOLLOWUPS.md
    - .planning/phases/33-companion-tests-on-pytest-behaviour-over-source-text/33-ledger/companion__test_config_page.md
    - .planning/phases/33-companion-tests-on-pytest-behaviour-over-source-text/33-ledger/companion__test_companion_app.md
    - .planning/phases/33-companion-tests-on-pytest-behaviour-over-source-text/33-ledger/companion__test_view_pages.md
  deleted:
    - companion/test_legacy_harness_shim.py

key-decisions:
  - "The guard detects served-CSS text checks by taint analysis rather than by name-matching `css`/`served_css` variables, so a renamed fixture or a helper taking the text as a parameter is still caught; the one allowlist entry is pinned by a test that fails if it stops matching a real raw-text scan"
  - "Sub-clauses that asserted stylesheet COMMENTS (config_page ledger rows 112-113) were dropped under rubric C; the rows stay `ported` because their selector checks carry the behaviour"
  - "The two-copy agreement check for the caption counting rule became a parametrised behaviour test of the one shared rule with pinned outputs; it was a secondary node id named only in ledger prose, and row 320's primary id is unchanged"
  - "deploy/README.md is re-included in the CI paths filter: deploy/tests/test_docs.py reads it, so dropping every doc re-include would have let a README-only change skip the test that guards it"
  - "TST-10..15 stay Pending in REQUIREMENTS.md; 33-33 closes them"

requirements-completed: []

duration: ~30min
completed: 2026-09-25
---

# Phase 33 Plan 32: Retire the transition machinery, strict guard, F-01 closed

**The legacy shim, the legacy lists, `collect_ignore`, the `legacy_harness` marker and `LegacyHarness` are gone. The guard now scans every companion test module and bans hand-rolled runners across all test directories. Served-stylesheet checks parse the CSS instead of searching its text (F-01), and a new guard rule G11 enforces that. CI and the docs describe the finished suite.**

## Performance

- **Duration:** ~30 min by commit clock (two full-suite runs of ~4-5 min each included)
- **Started:** 2026-09-25T02:01Z
- **Completed:** 2026-09-25T02:31Z
- **Tasks:** 3 plan tasks plus 2 orchestrator-required items (F-01, shared caption helper), 5 commits
- **Files modified:** 32 (1 deleted)

## Accomplishments

- **Transition machinery retired (Task 1).** Pre-condition held: `legacy_companion_harnesses()` returned `()`, and `33-ledger-check.py --all` exited 0 with 0 pending. Deleted `companion/test_legacy_harness_shim.py`; `ORIGINAL_COMPANION_HARNESSES`, `legacy_companion_harnesses()`, `LEGACY_COMPANION_HARNESSES`, `LEGACY_HELPER_MODULES`, `LEGACY_COMPANION_COLLECT_IGNORE` and their test; `conftest.py`'s `collect_ignore`; the `legacy_harness` marker; the shim mentions in the pyproject coverage comments (`source`/`omit`/`patch`/`sigterm` untouched); `LegacyHarness` (the last `tempfile` user in the shared fixtures, `grep -c tempfile` = 0) and `test_legacy_harness_still_matches_original_behaviour`. Stale live-machinery prose in `companion/conftest.py` and `test_browser_ux_helpers.py` was reworded.
- **Strict guard.** `scanned_files()` is every `companion/test_*.py` plus `companion/conftest.py`, minus the guard itself: 44 parametrised ids, equal to `ls companion/test_*.py | wc -l`. `test_scanned_files_are_every_companion_test_module_but_the_guard` replaces the old exemption test. The new `test_no_legacy_runner_anywhere` scans `server/`, `stub-server/`, `test-support/`, `companion/` and `deploy/tests/` for G8 markers. No `sys.exit(pytest.main())` allowance was needed: the only remaining `__main__` runner, in `stub-server/test_devices_registry.py`, was a PASS/FAIL loop and was removed.
- **F-01 resolved (commit `807e9b2`).** G11 found 139 sink sites in 6 modules, all rewritten structurally:
  - `test_config_page_03.py`: 9 tests. Fixed-width text windows became `declarations_for()` reads in a named at-rule context. `str.index()` source-order checks became `rule_indices()`. `@supports`/`@keyframes` counts became `at_rule_blocks()`. The "muted mix appears ≥ 17 times", "`content: attr(...)` exactly twice" and "no French copy" checks now count declarations.
  - `test_config_page_02.py`: the handle/hit-area source-order pin.
  - `test_companion_app_02.py`: class-styled and rule-presence checks.
  - `test_companion_app_03.py`: the `@supports` count.
  - `test_companion_app_04.py`: the whole motion budget, retiring its brace-matching text helper.
  - `test_view_pages_03.py`: 5 tests, plus 2 unused text-level rule-body helpers deleted.

  Mutation-checked against a temporarily edited stylesheet (restored afterwards). A comment quoting `@supports selector(:has(*)) {`, `content: "Current"` and `actuel` left the tests green. A real second `@supports` block and a changed selection scale failed all three targeted tests.
- **Guard rule G11** has 7 failing samples (regex, fixture `in` test, index after `.lower()`, count over a slice, regex inside a helper that receives the served text, compiled pattern over `re.sub` output, `in` over a style-route body) and 4 accepted samples (parsed structure, served JS, style-route headers, the allowlisted function). `test_g11_allowlist_entry_still_scans_raw_stylesheet_text` fails if the one allowlist entry (row 298's stray-comment-terminator scan in `test_status_pages_07.py`) no longer contains a raw-text scan.
- **`companion_markup` extended minimally:** `rule_indices(css, selector, at_rules=None)` and `at_rule_blocks(css)`, with two unit tests in `test-support/test_companion_markup.py`.
- **Shared caption counting rule.** `caption_word_count_text()` now lives in `companion/test_config_page_helpers.py`, and both `_05` modules import it. The sibling-module import is gone, and **G12** (with 3 failing samples and 1 accepted sample) forbids a test module importing another test module.
- **Runner, CI, docs (Task 2).**
  - `run-all-tests.sh`: header rewritten. The `exec` line and every non-comment line are byte-identical.
  - `ci.yml`: both paths filters drop the three `.planning` re-includes and re-include `deploy/README.md`. The header now states what is re-included and why. The browser step is renamed "Download the Chromium headless shell the browser tests drive". `SKYPANE_REQUIRE_BROWSER`, the cache key and the install command are unchanged. YAML validated with the system `python3`'s PyYAML (`yaml.safe_load`, both `paths` lists and the step names printed); the venv has no PyYAML.
  - CLAUDE.md's Tests / CI row, README "## Tests" and CONTRIBUTING are updated.
- **`test_devices_registry.py` fold-in (Task 3).** Five `tempfile.mkdtemp` sites (the plan expected two) now take `tmp_path`: the `Harness` takes `state_dir`, and the four CLI tests use it directly. `shutil`/`tempfile` and every `rmtree` are gone. Node ids are unchanged.

## Full-suite result

`PLAYWRIGHT_BROWSERS_PATH=/tmp/skypane-pw-browsers SKYPANE_REQUIRE_BROWSER=1 ./scripts/run-all-tests.sh` as root (euid 0), with the runner's own testpaths and `-n auto --cov`:

- **2588 passed, 5 skipped, 0 failed** in 309 s
- all 5 skips are `requires_non_root` permission tests, skipped because the run was root
- **TOTAL coverage 93.23 %**, gate 93.0 % reached

2588 is 2569 (33-31's run) minus the 4 removed legacy tests (the shim's own consistency test, the legacy-set test, `test_legacy_harness_still_matches_original_behaviour` and `test_exemption_set_is_only_legacy_harnesses`) plus 23 new ids:

- 2 new guard tests
- 11 G11 self-test cases and 1 allowlist check
- 4 G12 cases
- 2 `companion_markup` unit tests
- a net +3 from the 4-case caption rule test that replaced the old agreement check

The shim's empty-parametrize skip is gone, taking skips from 6 to 5. The 57 warnings are all pre-existing: Pillow `getdata()` deprecations in `server/` and the pytest-socket guard's own self-test. `git status --porcelain` was empty after the run.

Coverage note for 33-33: 93.23 % passes the 93.0 gate but is below the 93.35 % pre-migration figure CONTEXT records for TST-15. 33-33 owns that comparison and the `fail_under` decision.

## Task Commits

1. **Task 1: retire the shim and make the guard strict** - `f451ed0` (test)
2. **F-01: parse the served stylesheet instead of searching its text** - `807e9b2` (test)
3. **Shared caption counting rule + G12** - `6b466e4` (test)
4. **Task 2: runner comments, CI paths filter, docs** - `00f4a09` (docs)
5. **Task 3: devices-registry tests on tmp_path** - `ac8e6a4` (test)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Removed `stub-server/test_devices_registry.py`'s `__main__` runner in Task 1, not Task 3**
- **Found during:** Task 1
- **Issue:** The new `test_no_legacy_runner_anywhere` guard lands in Task 1, and that file still carried a PASS/FAIL `__main__` runner, so the Task 1 commit would have failed.
- **Fix:** Deleted the runner and its docstring mention in the Task 1 commit. The tmp_path conversion stayed in Task 3.
- **Commit:** `f451ed0`

**2. [Rule 2 - Missing critical functionality] Re-included `deploy/README.md` in the CI paths filter**
- **Found during:** Task 2
- **Issue:** The plan's premise that "tests read no docs" is false. `deploy/tests/test_docs.py` reads `deploy/README.md`, which `!**/*.md` excludes, so a README-only change would skip the test that guards it (T-33-32-01). This gap predates this plan.
- **Fix:** Re-included `deploy/README.md` in both triggers and said so in the header.
- **Commit:** `00f4a09`

**3. [Rule 2] Guard rule G12 (test module importing a test module)**
- **Found during:** the caption-helper move
- **Issue:** Nothing prevented the sibling-module import from coming back.
- **Fix:** Added G12 with self-tests. No current module trips it.
- **Commit:** `6b466e4`

### Acceptance-criteria notes

- The plan's grep `EXPECTED_CHECK_COUNT` over `companion` cannot print nothing: `companion/test_suite_guards.py` must name `EXPECTED_CHECK_COUNT` to detect it (the G8 rule and its self-test sample). Every other hit, including four comments in `test_browser_ux_helpers.py`, `test_login_throttle.py` and `test_post_origin.py`, was reworded.
- `grep -c "server/assets/\*\*/VENDOR.md" ci.yml` prints 3, not 2: the header comment names the path once, as it did before this plan, and both `paths` blocks carry it.
- The docs describe the browser tests, the app-server fixtures and the behaviour-over-source rule. The CLAUDE.md row edit is exactly the planned clause, extended with the fixture and rule wording the orchestrator required.

## Known Stubs

None.

## Next Phase Readiness

- 33-33 (closing parity/verification) can run `--assemble`. The three fragments touched here carry "Closing sweep (plan 33-32)" notes, and no node id changed. `33-ledger-check.py --all` exits 0 without `--allow-pending`.
- TST-10..15 remain Pending in REQUIREMENTS.md for 33-33.
- `/nonexistent/definitely-not-here` on this host dates from 2026-09-24 12:38, before this session: the pre-migration root-unsafe leftover TST-13 describes. This plan's run created nothing new there.

---
*Phase: 33-companion-tests-on-pytest-behaviour-over-source-text*
*Completed: 2026-09-25*

## Self-Check: PASSED

All five commits (`f451ed0`, `807e9b2`, `6b466e4`, `00f4a09`, `ac8e6a4`) found in
`git log --all`, each ending with the required trailers; the SUMMARY, the
guard and `companion_markup.py` found on disk; `companion/test_legacy_harness_shim.py`
confirmed deleted.
