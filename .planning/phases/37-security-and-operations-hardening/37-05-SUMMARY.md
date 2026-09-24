---
phase: 37-security-and-operations-hardening
plan: 05
subsystem: auth
tags: [companion, csrf, origin, sec-fetch-site, fetch-metadata, pytest, playwright]

# Dependency graph
requires:
  - phase: 32-test-foundation-pytest-and-ci-you-can-trust
    provides: pytest infrastructure (conftest.py, pyproject.toml [tool.pytest.ini_options], no-network socket guard, skypane_test_support helpers)
  - phase: 37-01
    provides: "companion/auth.py and companion/app.py as 37-01 left them (keyed LoginThrottle, client_ip(), Handler._login_throttle_key(), --bind) — this plan appends to the same two files"
provides:
  - "companion/auth.py: post_origin_ok(headers) — a pure Origin/Sec-Fetch-Site CSRF check, defence in depth on top of SameSite=Strict"
  - "companion/app.py: do_POST()'s first statement gates every POST (login included) through post_origin_ok(); _forbidden_page() (403, mirrors _not_found_page())"
  - "companion/i18n_fr/common.py: FR strings for the 403 page"
  - "companion/test_post_origin.py: unit + HTTP-integration pytest coverage, route list discovered from do_POST()'s own source"
  - "companion/test_browser_origin.py: the first native pytest Playwright test in this repository — real-browser proof of the cross-origin rejection and of same-origin forms/fetch still working"
affects: [40 (CMP-01 companion route-table refactor — the gate's single-helper shape is deliberately easy to relocate)]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "post_origin_ok(headers): a pure function over any headers mapping with .get(), same shape as auth.client_ip() (37-01) — testable with a plain dict, no server needed"
    - "do_POST()'s Origin/Sec-Fetch-Site gate as the literal first statement, before urlsplit()/routing/read_form() — one choke point covering every route including login, matching the plan's own D-16 requirement"
    - "test_post_origin.py discovers do_POST()'s exact-match route constants from the method's own source (inspect.getsource + regex + getattr chain) rather than hardcoding route strings, so a route added later is covered automatically"
    - "test_browser_origin.py: the first native pytest Playwright test — reuses companion/test_browser_ux_helpers.py's _login()/_persist_without_js() rather than re-deriving the operate-submit-reload-verify contract"

key-files:
  created:
    - companion/test_post_origin.py
    - companion/test_browser_origin.py
  modified:
    - companion/auth.py
    - companion/app.py
    - companion/i18n_fr/common.py
    - companion/test_legacy_harness_shim.py

key-decisions:
  - "post_origin_ok() checks Sec-Fetch-Site first (rejects cross-site AND same-site — same-site catches a sibling *.nip.io host SameSite=Strict itself cannot distinguish, T-37-23), then Origin (rejected only if literally \"null\" or its netloc disagrees with Host after default-port normalisation); a request carrying neither header is allowed, since it still needs a valid session cookie (T-37-24, accepted)"
  - "The 403 body is a second, deliberately separate helper (_forbidden_page()) rather than folded into _not_found_page() — same pre-auth-safe shape, kept apart so Phase 40's route-table refactor can relocate the gate without first having to split the two response bodies"
  - "Chromium launch in test_browser_origin.py retries once against the full chrome-linux/chrome build already present in this sandbox's preinstalled cache when the pinned playwright package's default headless-shell binary is missing (a browser-cache/package version skew pre-dating this plan, not fixable by editing app code) — CI/SKYPANE_REQUIRE_BROWSER=1 still fail rather than skip if nothing launches, matching the legacy harnesses' own policy; playwright install was not run, per phase policy"

requirements-completed: [SEC-03]

# Metrics
duration: 17min
completed: 2026-09-24
---

# Phase 37 Plan 05: Origin/Sec-Fetch-Site gate on every companion POST Summary

**Every companion POST route, including /login, now passes through one `auth.post_origin_ok()` check before any routing or form read — a cross-site Origin, an `Origin: null`, or a `Sec-Fetch-Site: cross-site`/`same-site` request gets a localized 403 and changes nothing, proven over real HTTP for every route and, separately, by a real Chromium browser.**

## Performance

- **Duration:** ~17 min
- **Started:** 2026-09-24T08:31:47Z (STATE.md position set after 37-04)
- **Completed:** 2026-09-24T08:48:29Z (Task 2 commit)
- **Tasks:** 2/2 completed
- **Files modified:** 6 (2 created, 4 modified)

## Accomplishments
- `companion/auth.py` gained `post_origin_ok(headers)`: rejects `Sec-Fetch-Site: cross-site`/`same-site` first, then `Origin: null`, then any `Origin` whose netloc (default `:443`/`:80` stripped) disagrees with `Host`; allows requests carrying neither header. Pure function, unit-tested with plain dicts.
- `companion/app.py`'s `do_POST()` gates on this check as its literal first statement — before `urlsplit()`, before routing, before any `read_form()` — so `/login` and all 17 other POST routes (14 exact-match + 3 prefix-match) are covered by the one choke point, per D-16.
- `_forbidden_page()` added, mirroring `_not_found_page()` byte for byte in shape (pre-auth-safe language resolution, `health_alert` threaded only when authenticated, `send_html()`'s existing `Cache-Control: no-store`).
- FR strings added to `companion/i18n_fr/common.py` (typographic apostrophe, D-09), automatically proven live by `test_i18n.py`'s existing ast-based scan (no new check needed — the same mechanism that already covers `NOT_FOUND_TITLE`/`NOT_FOUND_PURPOSE_TEXT` covers `FORBIDDEN_TITLE`/`FORBIDDEN_PURPOSE_TEXT`).
- `companion/test_post_origin.py`: 11 unit tests of `post_origin_ok()` plus HTTP-integration tests parametrised over **every** POST route `do_POST()` dispatches — the route list is read from `do_POST()`'s own source via `inspect.getsource()`, so a route added later needs no edit here. Proven end to end: a cross-site POST to the quick-switch route is rejected with `device_config.json` unchanged on disk; the identical POST with a matching `Origin` + `Sec-Fetch-Site: same-origin` is applied; `/login` with the right password and a cross-site `Origin` gets 403 with no `Set-Cookie`; `/login` with neither header behaves exactly as before (303). 49 tests total, all green.
- `companion/test_browser_origin.py`: the first native pytest Playwright test in this repository. Scenario 1 drives a genuine second loopback origin (its own `http.server`) whose auto-submitting form POSTs to the companion's quick-display route — a real browser proves the response is 403 and the device config is byte-identical before/after. Scenario 2 proves the real quick-switch fetch control (`companion/static/quick-switch.js`) and a scripts-blocked native Settings form save (via `test_browser_ux_helpers._persist_without_js()`) both still work same-origin. Both scenarios genuinely ran (not skipped) in this sandbox via a one-shot Chromium-launch fallback (see Deviations).

## Task Commits

Each task was committed atomically:

1. **Task 1: Phase 32 gate, post_origin_ok() + do_POST() hook + 403 page, HTTP tests over every POST route (TDD)** - `2fcb2e7` (feat)
2. **Task 2: Playwright proof — cross-origin form rejected, same-origin UI unaffected** - `667e4bb` (test)

**Plan metadata:** (this commit, docs: complete plan)

## Files Created/Modified
- `companion/auth.py` - `post_origin_ok(headers)`, `_ORIGIN_DEFAULT_PORT`, `urlsplit` added to the stdlib import list and module docstring
- `companion/app.py` - `FORBIDDEN_TITLE`/`FORBIDDEN_PURPOSE_TEXT` constants, `_forbidden_page()`, `do_POST()`'s new first statement
- `companion/i18n_fr/common.py` - Two new FR entries for the 403 page, module docstring updated
- `companion/test_post_origin.py` - New: 11 unit tests + 38 parametrised/scenario HTTP-integration tests (49 total)
- `companion/test_browser_origin.py` - New: 2 Playwright scenario tests, plus a Chromium-launch fallback helper
- `companion/test_legacy_harness_shim.py` - Both new native pytest files exempted from the on-disk drift guard, matching `test_login_throttle.py`'s/`test_health_offbox.py`'s own precedent (37-01/37-02)

## Decisions Made
- `Sec-Fetch-Site` is checked before `Origin` because it is the more specific signal and the only one that distinguishes a same-site sibling host from this site — `Origin`/`Host` agreement alone cannot make that distinction, and D-16 explicitly calls out rejecting `same-site` too (T-37-23).
- Header-less requests are allowed by design (T-37-24, accepted risk): they still need a valid session cookie, and refusing them would only break non-browser and pre-Fetch-Metadata browser clients with no security gain given SameSite=Strict already covers modern browsers.
- `_forbidden_page()` is a separate helper rather than a parameter on `_not_found_page()`, so Phase 40's route-table refactor can move the gate on its own.
- The Chromium-launch fallback in `test_browser_origin.py` is scoped to that one file only — the pre-existing legacy Playwright harnesses (`test_browser_ux*.py`) are untouched and still skip in this sandbox, which is out of this plan's scope (Phase 33 territory) and unrelated to SEC-03.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Exempted both new native pytest files from the legacy-harness drift guard**
- **Found during:** Task 1 and Task 2, running the plan's own verify steps
- **Issue:** `test_legacy_harness_shim.py::test_legacy_harness_list_matches_disk` asserts every `test_*.py` file under `companion/` (besides a fixed exemption list) is a registered legacy harness. `test_post_origin.py` and `test_browser_origin.py` are this plan's own native pytest deliverables — the guard failed on their mere existence, exactly the same situation 37-01/37-02 already recorded and fixed the same way.
- **Fix:** Added both filenames to the same exemption tuple `test_login_throttle.py`/`test_health_offbox.py` already occupy, one commit per task.
- **Files modified:** `companion/test_legacy_harness_shim.py`
- **Verification:** `pytest -q companion/test_legacy_harness_shim.py -k test_legacy_harness_list_matches_disk` passes after each addition; full suite re-run confirms no other file lost coverage.
- **Committed in:** `2fcb2e7` (Task 1), `667e4bb` (Task 2)

**2. [Rule 3 - Blocking] Chromium-launch fallback in test_browser_origin.py**
- **Found during:** Task 2, first run of the new test — Chromium failed to launch with `Executable doesn't exist at .../chromium_headless_shell-1243/...`
- **Issue:** The plan's own acceptance criteria require the browser test to genuinely run (not skip) here. `server/.venv`'s pinned `playwright==1.63.0` expects browser revision 1243 (`chrome-headless-shell`), but this sandbox's preinstalled `/opt/pw-browsers` only carries revision 1194 — a pre-existing environment mismatch (the existing legacy `test_browser_ux*.py` harnesses hit the identical error and SKIP today, confirmed by running them directly). `playwright install` is explicitly out of bounds for this plan.
- **Fix:** `_launch_chromium()` tries the normal `playwright.chromium.launch()` first; on failure, it retries once against the full `chromium-1194/chrome-linux/chrome` binary (present in the same cache, CDP-compatible) with `executable_path=` set explicitly, still headless. If neither launches, the existing skip-or-fail policy applies unchanged.
- **Files modified:** `companion/test_browser_origin.py` only — the legacy harnesses (`test_browser_ux*.py`) are untouched and still skip via their own unmodified `sync_playwright()` call, which is correct: fixing their launch path is Phase 33 migration scope, not this plan's.
- **Verification:** `pytest -v companion/test_browser_origin.py` shows both scenarios `PASSED` (not `SKIPPED`), confirmed again with `CI=true` set (the fail-instead-of-skip path still passes rather than failing).
- **Committed in:** `667e4bb` (Task 2)

---

**Total deviations:** 2 auto-fixed (both Rule 3 - blocking)
**Impact on plan:** Both fixes are necessary consequences of adding the plan's own required test files in this sandbox; neither touches production code (`companion/auth.py`/`companion/app.py`) or widens scope beyond what Task 1/Task 2 already asked for.

## Issues Encountered

**Pre-existing, root-euid-only test failures (not caused by this plan, not fixed — already recorded in `deferred-items.md` from 37-01/37-02).** `./scripts/run-all-tests.sh` in this sandbox (running as `root`) leaves exactly two failures: `test_companion_app` (318/320) and `test_status_pages` (316/317), both from WR-11-style checks that simulate a write failure via `os.chmod(dir, 0o500)` — root ignores permission bits. Re-confirmed identical counts before and after this plan's changes; fixing them is Phase 33 scope. Full suite: 924 passed, 6 skipped (3 root-euid skips in already-migrated pytest files; 3 of the legacy Playwright harnesses still skipping on the same pre-existing Chromium version-skew this plan's own deviation #2 works around only for its own new file), 2 known-failed, coverage 93.13% (gate: 93.0%).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `auth.post_origin_ok()` is a stable, importable name any later plan touching `companion/app.py`'s POST routes inherits automatically (it runs before any routing, so no per-route wiring is needed).
- Phase 40 (CMP-01, companion route-table refactor) can relocate the gate call by moving one `if not auth.post_origin_ok(...)` line plus `_forbidden_page()` — both were kept deliberately separate from `_not_found_page()` for exactly this future move.
- No blockers for the rest of Wave A.

---
*Phase: 37-security-and-operations-hardening*
*Completed: 2026-09-24*

## Self-Check: PASSED

All files claimed as created/modified exist on disk (`companion/auth.py`,
`companion/app.py`, `companion/i18n_fr/common.py`,
`companion/test_post_origin.py`, `companion/test_browser_origin.py`,
`companion/test_legacy_harness_shim.py`, this file). Both task commits
(`2fcb2e7`, `667e4bb`) are present in `git log --oneline --all`.
