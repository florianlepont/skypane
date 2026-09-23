---
phase: 32-test-foundation-pytest-and-ci-you-can-trust
plan: 03
subsystem: testing
tags: [pytest, migration-ledger, network-guard, monkeypatch, subprocess-fixture]

# Dependency graph
requires:
  - phase: 32-test-foundation-pytest-and-ci-you-can-trust (plan 01)
    provides: pytest/xdist/cov/socket config, conftest.py fake_providers fixture and DNS guard, test-support/skypane_test_support.py (child_env, requires_non_root)
  - phase: 32-test-foundation-pytest-and-ci-you-can-trust (plan 02)
    provides: 32-BASELINE/*.txt transcripts, 32-ledger-check.py, 32-ledger/ fragment format
provides:
  - server/test_dither.py, server/test_runway_config.py, server/test_notify.py, server/test_panel_preview.py, server/test_pipeline_e2e.py as real pytest modules
  - 5 ledger fragments under 32-ledger/ mapping all 47 baseline checks (6+15+8+11+7) to node ids
  - the first worked example of stubbing a production SSRF DNS check (server/notify.py's _url_is_safe()) under the non-loopback network guard
  - the first worked example of a subprocess-launching pytest fixture (byos_server_factory) using child_env()
affects: [32-04, 32-05, 32-06, 32-07, 32-08, 32-09, 32-10, 32-13]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "A production SSRF gate that does its own socket.getaddrinfo() DNS check (server/plane/calendar_rules._host_is_safe(), reused by server/notify.py) needs its own per-module DNS stub when the non-loopback guard blocks it - an autouse fixture patching socket.getaddrinfo for the one known-safe hostname the tests use, rather than bypassing the gate function itself, so the gate's own logic stays genuinely exercised."
    - "A hand-rolled check() call whose body loops over several inputs and reports ONE pass/fail (not one baseline PASS/FAIL line per input) stays ONE pytest test function with an internal loop, not a @pytest.mark.parametrize split - parametrize is for checks the OLD harness itself emitted as separate PASS/FAIL lines from a loop (Pitfall 1), not for internal iteration inside a single check()."
    - "Heavy inter-check ctx-dict reuse for expensive, pure, order-independent artifacts (panel_png_bytes() at two thumbnail sizes) becomes module-scoped pytest fixtures instead of a shared dict, keeping tests independent (MR-4) while computing shared work once."
    - "A harness whose checks are GENUINELY sequential (shared tmp_path state directory across setup/download/battery/park, each check depending on state an earlier one created) becomes ONE consolidated pytest test function with a docstring enumerating the old check labels, rather than several tests coupled by execution order - all N old checks map to that one node id in the ledger."
    - "A subprocess-launching Harness class becomes a factory fixture (byos_server_factory) rather than a single-instance yield fixture when a test needs to start more than one instance of the same server against different state dirs in sequence - the factory tracks every instance it creates and stops all of them at teardown, in a finally-equivalent way that survives a mid-test failure."

key-files:
  created:
    - .planning/phases/32-test-foundation-pytest-and-ci-you-can-trust/32-ledger/server__test_dither.md
    - .planning/phases/32-test-foundation-pytest-and-ci-you-can-trust/32-ledger/server__test_runway_config.md
    - .planning/phases/32-test-foundation-pytest-and-ci-you-can-trust/32-ledger/server__test_notify.md
    - .planning/phases/32-test-foundation-pytest-and-ci-you-can-trust/32-ledger/server__test_panel_preview.md
    - .planning/phases/32-test-foundation-pytest-and-ci-you-can-trust/32-ledger/server__test_pipeline_e2e.md
  modified:
    - server/test_dither.py
    - server/test_runway_config.py
    - server/test_notify.py
    - server/test_panel_preview.py
    - server/test_pipeline_e2e.py

key-decisions:
  - "server/test_notify.py gained an autouse module fixture stubbing socket.getaddrinfo('ntfy.sh', ...) to a fixed public IP (93.184.216.34, the historical example.com/example.org address, never actually connected to) - send_notification()'s SSRF gate does a real DNS lookup as its first line, which the non-loopback guard correctly blocks; the fix keeps that gate genuinely exercised rather than monkeypatching the gate function itself away."
  - "server/test_pipeline_e2e.py's 7 old checks all map to ONE consolidated pytest test function (one ledger node id for all 7 baseline rows) because every check after the first shares and mutates the same tmp_path state directory - splitting them would either duplicate the setup or introduce inter-test ordering dependencies MR-4 forbids."
  - "server/test_pipeline_e2e.py's run_once() calls use the fake_providers fixture (default adsbdb 404 'unknown callsign') rather than relying on the network guard's own exception being silently swallowed by enrich.py's lookup_route() - both produce the identical route_source='airline_only' baseline outcome, but the fixture makes the hermeticity intentional and readable instead of incidental."

requirements-completed: []  # TST-02 spans plans 32-03..32-10 (10 harnesses remain); TST-03 was already completed by plan 32-01 (already marked complete in REQUIREMENTS.md) - neither is (re-)marked by this plan per the "every plan it spans" rule.

# Metrics
duration: ~45min
completed: 2026-09-23
---

# Phase 32 Plan 03: Migrate the 5 smallest server-side harnesses to pytest Summary

**server/test_dither.py, test_runway_config.py, test_notify.py, test_panel_preview.py, and test_pipeline_e2e.py (47 baseline checks total) are now real pytest modules passing under `-n 4` with zero network access and zero filesystem writes outside tmp_path, every baseline check mapped in a 32-ledger/ fragment.**

## Performance

- **Duration:** ~45 min
- **Tasks:** 2
- **Files modified:** 10 (5 test modules + 5 new ledger fragments)

## Accomplishments
- `server/test_dither.py` (6 checks), `server/test_runway_config.py` (15 checks - the baseline's actual count, not the plan's stale "14"), `server/test_notify.py` (8 checks), and `server/test_panel_preview.py` (11 checks) converted to plain `test_*` functions/fixtures, all passing under both `-n 0` and `-n 4`, zero `tempfile.`/`EXPECTED_CHECK_COUNT`/`def check(` remaining.
- `server/test_pipeline_e2e.py` (7 checks, launches `stub-server/byos_server.py` as a real subprocess three times against a shared `tmp_path` state directory) converted to one consolidated test plus a `byos_server_factory` fixture that starts each subprocess with `child_env()` and guarantees teardown of every instance it created.
- Found and fixed a real gap the migration surfaced: `server/notify.py`'s SSRF gate (`calendar_rules._url_is_safe()`) does a genuine `socket.getaddrinfo()` DNS lookup for the notification topic host, which the non-loopback guard from plan 32-01 correctly blocks - stubbed with a fixed public IP so the gate's own logic keeps running under test instead of being bypassed.
- All 5 ledger fragments verified against `32-ledger-check.py`: 47/47 baseline checks mapped, 0 pending, 0 `EXPECTED_CHECK_COUNT`/`def check(` leftovers.

## Task Commits

Each task was committed atomically:

1. **Task 1: Migrate test_dither, test_runway_config, test_notify, test_panel_preview** - `c09bdd4` (feat)
2. **Task 2: Migrate test_pipeline_e2e (byos subprocess fixture)** - `bfc2f87` (feat)

**Plan metadata:** (this commit, docs: complete plan)

## Files Created/Modified
- `server/test_dither.py` - 6 `test_*` functions, `tempfile.mkdtemp()`→`tmp_path`
- `server/test_runway_config.py` - 15 `test_*` functions, a module-scoped `track` fixture for the shared real fixture replay
- `server/test_notify.py` - 8 `test_*` functions (the SSRF check stays one function with an internal loop over 4 hostile URLs, matching the baseline's single PASS/FAIL line), new autouse `_stub_ntfy_sh_dns` fixture
- `server/test_panel_preview.py` - 11 `test_*` functions, 3 module-scoped fixtures (`all_six_indices_raw`, `full_png_bytes`, `thumb_png_bytes`) replacing the old harness's `ctx` dict
- `server/test_pipeline_e2e.py` - 1 consolidated `test_full_pipeline_end_to_end_through_the_real_device_protocol`, `byos_server_factory` fixture, `BYOSHarness` class updated to accept `env=` (defaults to `child_env()`)
- `.planning/phases/32-test-foundation-pytest-and-ci-you-can-trust/32-ledger/server__test_dither.md` (new)
- `.planning/phases/32-test-foundation-pytest-and-ci-you-can-trust/32-ledger/server__test_runway_config.md` (new)
- `.planning/phases/32-test-foundation-pytest-and-ci-you-can-trust/32-ledger/server__test_notify.md` (new)
- `.planning/phases/32-test-foundation-pytest-and-ci-you-can-trust/32-ledger/server__test_panel_preview.md` (new)
- `.planning/phases/32-test-foundation-pytest-and-ci-you-can-trust/32-ledger/server__test_pipeline_e2e.md` (new)

## Decisions Made
- Kept `server/test_notify.py`'s SSRF-refusal check as one function looping over the 4 hostile URLs (not `@pytest.mark.parametrize`) because the baseline harness's own `check()` call reported ONE pass/fail for all four - parametrize is reserved for checks the OLD harness itself emitted as N separate PASS/FAIL lines from a loop (32-PATTERNS.md Pitfall 1), which this was not; a 1-baseline-row-to-4-node-ids mapping would also have broken the ledger tool's strict 1:1 row-count check.
- `server/test_pipeline_e2e.py`'s ledger fragment maps all 7 old check labels to the SAME single node id (`test_full_pipeline_end_to_end_through_the_real_device_protocol`) - the ledger format explicitly allows several old checks to consolidate into one node id, and this harness's checks are genuinely sequential (shared `tmp_path`, shared `poll_state.json`/`battery_state.json` across three byos_server.py subprocesses), not independently re-orderable.
- `server/test_runway_config.py`'s baseline is 15 checks, not the plan's `<planner_notes>` count of 14 - the file's own `EXPECTED_CHECK_COUNT` history shows it was bumped 14→15 in a later plan (19-12-PLAN.md Task 1) and the baseline transcript (captured by 32-02, the authoritative source per this plan's own read_first instructions) already reflects 15; all 15 are ported.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] server/test_notify.py: stubbed the SSRF gate's real DNS lookup that the network guard now blocks**
- **Found during:** Task 1, first verification run of the 4-file batch
- **Issue:** `send_notification("https://ntfy.sh/skypane-test", ...)`'s first line calls `calendar_rules._url_is_safe()`, which performs a genuine `socket.getaddrinfo("ntfy.sh", ...)` DNS lookup as part of its SSRF public-address check. Plan 32-01's autouse non-loopback DNS guard correctly raised `NetworkAccessBlocked` for this real external hostname, failing 5 of the 8 tests (every one using the literal ntfy.sh URL).
- **Fix:** Added an autouse fixture (`_stub_ntfy_sh_dns`) that patches `socket.getaddrinfo` to return a fixed, genuinely-public address (93.184.216.34) for the `ntfy.sh` host only, falling through to the real (guarded) resolver for anything else. The SSRF gate's own code (`_host_is_safe()`'s public-address classification) still runs and still passes - only the network round trip is stubbed, matching MR-7 ("no test opens a non-loopback socket... stub it in the test").
- **Files modified:** `server/test_notify.py`
- **Verification:** All 8 tests pass under `-n 0` and `-n 4`; ledger check confirms 8/8 mapped.
- **Committed in:** `c09bdd4` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 bug fix - a real gap the network guard correctly surfaced, not a guard weakness)
**Impact on plan:** The fix keeps the SSRF gate's DNS-based logic genuinely under test rather than working around it; no scope creep beyond server/test_notify.py.

## Issues Encountered

None beyond the notify.py DNS stub above. `server/test_pipeline_e2e.py` passed on the first full run once the legacy-runner bridge's own `sys.path` bootstrap was extended to include `test-support/` (needed because `child_env()`/`skypane_test_support` is only auto-added to `sys.path` by pytest's own `pythonpath` config, not by a direct `python3 server/test_pipeline_e2e.py` invocation) - folded into the same Task 2 commit before verification, not a separate deviation since it was caught and fixed before the commit was made.

## Next Phase Readiness
- 5 of 15 server-side harnesses now migrated (47 of 769 baseline checks); 10 remain across plans 32-04..32-10.
- `server/notify.py`'s DNS-stub pattern (autouse fixture patching `socket.getaddrinfo` for one known-safe hostname) is reusable by any later plan whose harness exercises `calendar_rules._url_is_safe()`/`_host_is_safe()` against a real hostname (most directly `server/test_calendar_rules.py`, owned by plan 32-08).
- `byos_server_factory`'s "factory fixture, tracks every instance, stops all at teardown" shape is reusable by `stub-server/test_poll_cycle.py`'s own migration (plan 32-06), which shares the same `Harness` structural ancestor per 32-PATTERNS.md.
- No blockers. TST-02 stays "Pending" in REQUIREMENTS.md (10 more harnesses to go); TST-03 was already "Complete" from plan 32-01.

---
*Phase: 32-test-foundation-pytest-and-ci-you-can-trust*
*Completed: 2026-09-23*

## Self-Check: PASSED

All 5 migrated test modules, 5 ledger fragments, and this summary confirmed present on disk;
task commit hashes (`c09bdd4`, `bfc2f87`) and this summary's own commit (`84ca692`) confirmed
present in `git log --oneline --all`.
