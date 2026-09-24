---
phase: 33-companion-tests-on-pytest-behaviour-over-source-text
plan: 02
subsystem: testing
tags: [pytest, pytest-playwright, fixtures, companion, chromium, ci]

# Dependency graph
requires:
  - phase: 32-test-foundation-pytest-and-ci-you-can-trust
    provides: "the repo-root conftest.py bootstrap, skypane_test_support.py's child_env()/FakeProviders/requires_non_root, and the fixture-override precedent for a hand-rolled Harness -> pytest fixture migration"
provides:
  - "test-support/companion_app_server.py: AppServer (real subprocess, start_new_session=True + killpg SIGTERM->SIGKILL teardown), InProcessAppServer, LegacyHarness (transition alias), http_request/_NoRedirectHandler/cookie_value/login/get/served_stylesheet/served_asset"
  - "companion/conftest.py: app_server, make_app_server, module_app_server_factory, app_server_in_process fixtures"
  - "companion/conftest.py: the missing-browser policy (session-scoped browser override: pytest.fail in CI/SKYPANE_REQUIRE_BROWSER=1, pytest.skip otherwise) and the loopback-only new_context route guard + blocked_requests fixture"
  - "server/requirements-dev.txt: pytest-playwright==0.9.0 (plus pytest-base-url, python-slugify, text-unidecode) hash-locked; runtime lock untouched"
  - "the \"browser\" pytest marker registered in pyproject.toml"
affects: [33-04, 33-05, 33-06, 33-07, 33-08, 33-09, 33-10, 33-11, 33-12, 33-13, 33-14, 33-15, 33-16, 33-17, 33-18, 33-19, 33-20, 33-21, 33-22, 33-23, 33-24, 33-25, 33-26, 33-27, 33-28, 33-29, 33-30, 33-31]

# Tech tracking
tech-stack:
  added: ["pytest-playwright==0.9.0 (dev-only)", "pytest-base-url==2.1.0", "python-slugify==8.0.4", "text-unidecode==1.3"]
  patterns:
    - "One shared AppServer/InProcessAppServer/LegacyHarness implementation behind companion/conftest.py's fixtures, replacing per-file Harness/_InProcessHarness/http_request/_NoRedirectHandler copies - every later migration plan writes def test_x(app_server): ... instead of building its own subprocess lifecycle"
    - "start_new_session=True + killpg(getpgid(pid), sig) teardown (SIGTERM then SIGKILL) instead of proc.terminate(): the child's pid IS its own process-group id (a new session leader), so any grandchild it spawns without its own setsid() is killed the same way - proven with a synthetic fake-app grandchild in test_app_server_fixture.py, not just documented"
    - "pytest-playwright's own browser/new_context fixtures overridden by name in companion/conftest.py rather than reimplemented: browser_type.launch() wrapped in try/except (pytest.fail under CI/SKYPANE_REQUIRE_BROWSER=1, pytest.skip otherwise), and new_context wrapped to install a Playwright route guard on every context it returns - since context/page are themselves built on new_context, the guard covers all three without needing three separate overrides"
    - "Zombie-aware process-liveness check (read /proc/<pid>/stat's state character, treat 'Z' as gone) rather than a bare os.kill(pid, 0) - needed because a just-terminated grandchild reparented to init stays kill(pid,0)-visible as a zombie until init reaps it"

key-files:
  created:
    - test-support/companion_app_server.py
    - companion/conftest.py
    - companion/test_app_server_fixture.py
    - companion/test_browser_policy.py
  modified:
    - server/requirements-dev.in
    - server/requirements-dev.txt
    - pyproject.toml

key-decisions:
  - "AppServer.start() creates its own state_dir (os.makedirs(..., exist_ok=True)) rather than requiring the caller to pre-create it, so the plain app_server fixture can pass tmp_path/\"state\" (which does not exist yet) directly"
  - "The 'stop() also terminates a grandchild in the same process group' behaviour is proven with a small synthetic fake_app.py the test writes to tmp_path and points AppServer.APP_PATH at (via monkeypatch) - companion/app.py itself never spawns a subprocess, so there is no real-world grandchild scenario to observe directly; the synthetic harness proves the killpg mechanism instead of only asserting it exists in the source"
  - "companion/test_app_server_fixture.py and test_browser_policy.py are, by construction, new companion/test_*.py files that are neither one of the 9 legacy harnesses nor the shim/helpers - this makes companion/test_legacy_harness_shim.py::test_legacy_harness_list_matches_disk fail from this commit onward. This is the documented, anticipated transition state MIGRATION-RULES.md section 1 describes (\"the legacy set is derived from disk (33-03)\"): 33-03 (a sibling wave-1 plan, not yet executed) rewrites that guard to derive the legacy set instead of a hand list. Left unfixed here per 33-MIGRATION-RULES.md section 2's explicit \"do NOT edit ... companion/test_legacy_harness_shim.py\" ownership boundary (it is one of 33-03's own files_modified) - fixing it here would collide with that plan"

patterns-established:
  - "Fixture-override-by-name for pytest-playwright: companion/conftest.py's browser/new_context fixtures request the plugin's own same-named fixture as a parameter and wrap it, rather than duplicating the plugin's launch/context-creation logic"

requirements-completed: []

# Metrics
duration: 17min
completed: 2026-09-24
---

# Phase 33 Plan 02: Shared Companion App-Server Fixture and Browser Policy Summary

**Built the one shared companion/app.py test-server fixture family (AppServer/InProcessAppServer/LegacyHarness) that every later migration plan builds on, plus pytest-playwright's missing-browser-fails-in-CI policy and a loopback-only route guard on every browser context.**

## Performance

- **Duration:** ~17 min
- **Started:** 2026-09-24T08:56:46Z (previous plan's completion timestamp)
- **Completed:** 2026-09-24T09:13:42Z
- **Tasks:** 3/3 completed
- **Files modified:** 7 (3 created test-support/companion files, 1 new conftest, 2 new self-test modules, 3 dep/config files)

## Accomplishments

- Added `pytest-playwright==0.9.0` (and its transitive `pytest-base-url`, `python-slugify`, `text-unidecode`) to the hash-locked dev dependency set via `scripts/lock-deps.sh`, confirmed the runtime lock (`server/requirements.txt`) is byte-identical, and registered the `browser` pytest marker — the full `server`/`stub-server`/`test-support` suite (764 tests) still passes unchanged.
- Built `test-support/companion_app_server.py`: `AppServer` (a real `companion/app.py` subprocess with `start_new_session=True` + `killpg` SIGTERM→SIGKILL teardown, so an orphaned grandchild is killed too — proven with a synthetic fake-app grandchild, not just asserted), `InProcessAppServer` (the `_InProcessHarness` in-process `ThreadingHTTPServer` technique for tests that need to monkeypatch a module in the server's own interpreter), `LegacyHarness` (a no-arg-constructor transition alias for the 4 still-legacy `Harness` copies), and the shared `http_request`/`_NoRedirectHandler`/`cookie_value`/`login`/`get`/`served_stylesheet`/`served_asset` helpers.
- Wired `companion/conftest.py`'s `app_server`, `make_app_server`, `module_app_server_factory` and `app_server_in_process` fixtures on top of that module, and wrote 11 self-tests in `companion/test_app_server_fixture.py` proving every `<behavior>` line in the plan (login flow, non-redirect-following HTTP, distinct ports/state dirs, process-group teardown including a grandchild, the no-network child env var + PYTHONPATH, fake-providers spec/call-log, seed-before-start, in-process password restore, served stylesheet/asset content types).
- Added the TST-11 missing-browser policy (`companion/conftest.py`'s `browser` fixture override: `pytest.fail` under CI/`SKYPANE_REQUIRE_BROWSER=1`, `pytest.skip` otherwise, verified live via two subprocess probe tests with an empty `PLAYWRIGHT_BROWSERS_PATH`) and the loopback-only `new_context` route guard (covers `context`/`page` too, since the plugin builds both on `new_context`) with a `blocked_requests` fixture and teardown-time `pytest.fail` for any unresolved recorded URL — proven in `companion/test_browser_policy.py`, all 16 tests across both self-test modules green with `SKYPANE_REQUIRE_BROWSER=1` and 0 skipped.

## Task Commits

Each task was committed atomically (Tasks 2 and 3 carry `tdd="true"`, so each followed the RED/GREEN cycle):

1. **Task 1: add pytest-playwright to the dev lock and register the browser marker** - `85cb37b` (chore)
2. **Task 2 (RED): add failing tests for the shared app-server fixture** - `52b1404` (test)
3. **Task 2 (GREEN): implement the shared app-server fixture module** - `0af5a23` (feat)
4. **Task 3 (RED): add failing tests for the missing-browser policy and loopback guard** - `195c279` (test)
5. **Task 3 (GREEN): add the missing-browser policy and loopback-only browser guard** - `d668edc` (feat)

## Files Created/Modified

- `test-support/companion_app_server.py` - the one AppServer/InProcessAppServer/LegacyHarness implementation and the shared HTTP client helpers
- `companion/conftest.py` - app_server/make_app_server/module_app_server_factory/app_server_in_process fixtures, plus the browser missing-browser policy and loopback-only new_context guard
- `companion/test_app_server_fixture.py` - 11 self-tests for the app-server fixture family
- `companion/test_browser_policy.py` - 5 self-tests (3 in-browser + 2 subprocess probes) for the TST-11 policy
- `server/requirements-dev.in` / `server/requirements-dev.txt` - pytest-playwright pin, hash-locked
- `pyproject.toml` - the `browser` marker

## Decisions Made

- `AppServer.start()` creates its own state directory rather than requiring callers to pre-create it, so the plain `app_server` fixture can hand it a `tmp_path` subpath that does not exist yet.
- The grandchild-in-process-group teardown behaviour is proven with a small synthetic `fake_app.py` script the test writes to `tmp_path` (via `monkeypatch.setattr(companion_app_server, "APP_PATH", ...)`), since `companion/app.py` itself never spawns a subprocess in normal operation — there is no real-world grandchild to observe otherwise, and this proves the `killpg` mechanism actually works rather than only asserting the source calls it.
- Process-liveness checks in the self-tests read `/proc/<pid>/stat`'s state character instead of a bare `os.kill(pid, 0)`, because a just-SIGTERM'd grandchild (reparented to init once its own parent, the fake app, was killed) remains `kill(pid, 0)`-visible as a zombie until init reaps it — a bare kill-probe would have made the grandchild-teardown test flaky/wrong.

## Deviations from Plan

### Auto-fixed Issues

None — no bugs or missing critical functionality were found; both tasks passed TDD RED/GREEN with the design as specified in the plan.

### Noted, not fixed (out of this plan's scope)

**1. `companion/test_legacy_harness_shim.py::test_legacy_harness_list_matches_disk` now fails**
- **Found during:** running the broader `companion/` suite (beyond the plan's own scoped `<verification>`, which only requires `test_app_server_fixture.py` + `test_browser_policy.py` + `server`/`stub-server`/`test-support`) as an extra sanity check.
- **Cause:** that guard asserts every on-disk `companion/test_*.py` file (excluding the shim and `test_browser_ux_helpers.py`) is one of the 9 hand-listed `LEGACY_COMPANION_HARNESSES`. This plan's two new native pytest modules (`test_app_server_fixture.py`, `test_browser_policy.py`) are neither legacy harnesses nor in that exclusion list, so the assertion now fails.
- **Why not fixed here:** `companion/test_legacy_harness_shim.py` and `test-support/skypane_test_support.py` (which owns `LEGACY_COMPANION_HARNESSES`) are both explicitly in plan 33-03's `files_modified`, and 33-MIGRATION-RULES.md section 2 explicitly forbids other plans from editing them ("Do NOT edit companion/conftest.py, test-support/*, ... They are owned by 33-02/33-03 and the closing plans"). 33-03's own objective is exactly this: deriving the legacy set from disk instead of a hand list, so it stops breaking every time a new native module appears. 33-03 is a sibling wave-1 plan (`depends_on: []`), so this is the anticipated, temporary state between the two plans landing, not a regression introduced by this plan's own logic.
- **Verification this is pre-existing/expected, not new breakage:** the plan's own `<verification>` section scopes exactly to `test_app_server_fixture.py test_browser_policy.py` + `server`/`stub-server`/`test-support`, deliberately excluding the rest of `companion/`; the two other `companion/test_legacy_harness_shim.py` failures observed in the same run (`test_status_pages` at 316/317, `test_companion_app` at 318/320) are the exact known root-sandbox artifacts already classified in `33-BASELINE/INDEX.md` (an `os.chmod` check and an `anomaly_active("/nonexistent/...")` mkdir-as-root check), unrelated to this plan.

## User Setup Required

None.

## Next Phase Readiness

- Every migration plan from 33-04 onward can now write `def test_x(app_server): ...` / `def test_y(page, app_server): ...` and get a real, isolated `companion/app.py` server or a guarded Chromium context with zero lifecycle plumbing of its own.
- `LegacyHarness` is in place so 33-19 can repoint the remaining legacy browser harnesses away from importing `test_companion_app.Harness` in stages.
- 33-03 (sibling wave-1 plan) is expected to fix `test_legacy_harness_list_matches_disk` by deriving the legacy set from disk; until it lands, that one guard check fails for the reason documented above (not a blocker for any migration plan's own scoped verification, which never runs the full `companion/` directory as one collection).

---
*Phase: 33-companion-tests-on-pytest-behaviour-over-source-text*
*Completed: 2026-09-24*

## Self-Check: PASSED

All 4 claimed created/modified files found on disk (`test-support/companion_app_server.py`,
`companion/conftest.py`, `companion/test_app_server_fixture.py`,
`companion/test_browser_policy.py`) plus this summary, and all 5 commit hashes
(`85cb37b`, `52b1404`, `0af5a23`, `195c279`, `d668edc`) found in `git log --oneline --all`.
