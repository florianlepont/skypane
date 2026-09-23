---
phase: 32-test-foundation-pytest-and-ci-you-can-trust
plan: 05
subsystem: testing
tags: [pytest, pytest-xdist, ads-b, fake-providers, monkeypatch, illustrations, plane-detection]

# Dependency graph
requires:
  - phase: 32-01
    provides: pytest/pytest-xdist/pytest-cov infra, repo-root conftest.py (fake_providers fixture, non-loopback DNS guard), skypane_test_support.py (FakeProviders, requires_non_root, child_env)
  - phase: 32-02
    provides: the migration ledger tool (32-ledger-check.py) and the per-harness baselines this plan's fragments verify against
provides:
  - server/test_illustrations.py and server/test_plane_detection.py as real pytest modules (60 + 47 tests, 1:1 with their pre-migration baselines)
  - proof that transport-level ADS-B provider stubbing (adsb.fi/adsb.lol response-key mapping) works through the shared fake_providers fixture end-to-end (TST-03)
  - a reusable pattern (stubbed_query_provider, a monkeypatch-built local fixture) for tests that need to stub detect.query_provider() itself rather than the HTTP transport
affects: [32-06, 32-07, 32-08, 32-09, 32-10, 32-13]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Function-scoped monkeypatch.setattr(module, 'GLOBAL', value) replaces every tempfile.mkdtemp()/manual-save-restore pair from the hand-rolled harnesses"
    - "A local `stubbed_query_provider` fixture (monkeypatch, zeroes MIN_SECONDS_BETWEEN_CALLS) stands in for a harness's own function-replacement helper when the stub is at the query_provider() level rather than the requests.get() transport level"
    - "An autouse fixture resets module-level setter-based state (set_override_state_dir(None)) after every test as a belt-and-braces independence guarantee, mirroring test_enrich.py's manual_resolutions reset"

key-files:
  created:
    - .planning/phases/32-test-foundation-pytest-and-ci-you-can-trust/32-ledger/server__test_illustrations.md
    - .planning/phases/32-test-foundation-pytest-and-ci-you-can-trust/32-ledger/server__test_plane_detection.md
  modified:
    - server/test_illustrations.py
    - server/test_plane_detection.py

key-decisions:
  - "Both harnesses turned out to have exactly one check() call site per baseline PASS line (60/60 and 47/47) - no loop-emitted multi-line checks were present in the current versions of either file, so no @pytest.mark.parametrize was needed; every old check became one test function with an internal loop where the original body looped."
  - "test_plane_detection.py's transport-level check (adsb.fi/adsb.lol response-key mapping) uses the shared fake_providers fixture with one payload carrying both the 'aircraft' and 'ac' keys, served identically to both provider names, so query_provider()'s own key selection is what's proven, not a dict literal."
  - "query_provider()-level stubs (the harness's own _with_stubbed_providers helper) became a local stubbed_query_provider fixture returning an _install(responses) closure, so each test keeps calling it with its own responses dict while teardown/sleep-zeroing is handled once via monkeypatch."

requirements-completed: [TST-02, TST-03]

# Metrics
duration: 45min
completed: 2026-09-23
---

# Phase 32 Plan 05: Migrate test_illustrations and test_plane_detection to pytest Summary

**server/test_illustrations.py (60 checks) and server/test_plane_detection.py (47 checks) are now pytest modules; the ADS-B transport-level provider stub is proven through the shared fake_providers fixture, and query_provider()-level stubbing has a reusable monkeypatch fixture pattern.**

## Performance

- **Duration:** ~45 min
- **Tasks:** 2 completed
- **Files modified:** 4 (2 test modules rewritten, 2 new ledger fragments)

## Accomplishments
- `server/test_illustrations.py` rewritten as 60 pytest test functions, 1:1 with its pre-migration baseline; every `tempfile.mkdtemp()`/manual-save-restore pair replaced with `tmp_path` and `monkeypatch.setattr` (`ILLUSTRATION_DIR`, `ILLUSTRATION_MAX_PIXELS`) plus an autouse fixture that resets `set_override_state_dir(None)` after every test.
- `server/test_plane_detection.py` rewritten as 47 pytest test functions, 1:1 with its pre-migration baseline. The one check that stubs at the transport level (`query_provider: adsb.fi and adsb.lol response keys are never interchanged`) now runs through the shared `fake_providers` fixture instead of a hand-rolled `fake_get`. Every check that stubs `detect.query_provider()` itself now goes through a local `stubbed_query_provider` fixture built on `monkeypatch`.
- Both modules pass under `-n 0` and `-n 4`, pass ruff, leave zero untracked files in the repo after a run, and make zero production-code changes.
- Ledger fragments map all 107 baseline checks (60 + 47) to their new node ids; `32-ledger-check.py` confirms 60/60 and 47/47 mapped with 0 pending.

## Task Commits

Each task was committed atomically:

1. **Task 1: Migrate test_illustrations (loop-emitted checks → parametrize)** - `2efdeb4` (feat)
2. **Task 2: Migrate test_plane_detection onto the fake_providers fixture** - `72007a0` (feat)

**Plan metadata:** (this commit, docs: complete plan)

## Files Created/Modified
- `server/test_illustrations.py` - 60 pytest tests for normalise_airline_key(), classify_aircraft_type(), select_illustration()'s four-tier fallback, validate_illustration_file()'s rejection categories, the target/required/outstanding filename contracts, target_variants_by_airline(), and the override-resolution layer
- `server/test_plane_detection.py` - 47 pytest tests for filter_in_geofence(), select_runway3_aircraft(), the runway-3 identification gate (corridor/track/ground gates), provider default order, per-poll cross-source corroboration, and CFG-12's runway-parameterised detection
- `.planning/phases/32-test-foundation-pytest-and-ci-you-can-trust/32-ledger/server__test_illustrations.md` - 60 baseline rows, all `ported`
- `.planning/phases/32-test-foundation-pytest-and-ci-you-can-trust/32-ledger/server__test_plane_detection.md` - 47 baseline rows, all `ported`

## Decisions Made
- The planner's Pitfall 1 note ("53 `check(` call sites vs 60 printed checks") did not hold against the current file: `grep -c '^\s*check('` returned exactly 60 for `test_illustrations.py` and exactly 47 for `test_plane_detection.py`, matching both baselines line-for-line. No loop-emitted parametrize split was needed; every old check became one test function, preserving any internal loop from the original check body as an in-test loop (still one node id, one ledger row).
- `test_provider_keys_are_not_interchanged` (the highest-consequence check in `test_plane_detection.py`) needed a payload usable for both provider names at once (it proves adsb.fi reads `"aircraft"` and adsb.lol reads `"ac"` from the SAME transport call pattern) - solved by calling `fake_providers.respond()` twice with the identical dict (both keys present) under each provider name, then reading `fake_providers.calls[0]["url"]` for the URL-shape assertion instead of a hand-rolled `captured_urls` list.
- Kept `geofence` as a `scope="module"` fixture (read-only, loaded once per worker) since no test mutates it in place; the one test that needs a mutated copy (`test_corridor_params_for_02_20_and_malformed_fallback`) already deep-copies via `json.loads(json.dumps(geofence))`.

## Deviations from Plan

None - plan executed exactly as written. Both files matched MR-1..MR-13 without needing Rule 1-4 deviations: no bugs found, no missing critical functionality, no blocking issues, no architectural changes.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- `server/test_illustrations.py` and `server/test_plane_detection.py` are fully migrated and verified; 107 of the phase's 769 baseline checks are now ported (with 32-03/32-04's earlier plans, running total higher still).
- The `stubbed_query_provider` fixture pattern (local, monkeypatch-built, distinct from the shared `fake_providers` transport fixture) is available as precedent for any later migration plan (e.g. `stub-server/test_poll_cycle.py`, 32-06) that stubs at the same "replace the query function itself" level rather than the HTTP transport.
- No blockers for 32-06 onward.

---
*Phase: 32-test-foundation-pytest-and-ci-you-can-trust*
*Completed: 2026-09-23*
