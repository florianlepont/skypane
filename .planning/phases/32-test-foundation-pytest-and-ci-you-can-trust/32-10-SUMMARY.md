---
phase: 32-test-foundation-pytest-and-ci-you-can-trust
plan: 10
subsystem: testing
tags: [pytest, migration-ledger, poll_loop, monkeypatch, tmp_path, network-guard]

# Dependency graph
requires:
  - phase: 32-test-foundation-pytest-and-ci-you-can-trust (plan 01)
    provides: pytest/xdist/cov/socket config, conftest.py DNS + fake_providers fixture, test-support/skypane_test_support.py
  - phase: 32-test-foundation-pytest-and-ci-you-can-trust (plan 02)
    provides: 32-BASELINE/server__test_poll_loop.txt transcript, 32-ledger-check.py, 32-ledger/ fragment format
provides:
  - server/test_poll_loop.py as a real pytest module (106 test functions covering all 110 baseline checks - checks 1-5 consolidated into one node id per MR-4, every other check 1:1) - the last of the 15 server-side harnesses TST-02 scope
  - 1 ledger fragment under 32-ledger/ mapping all 110 baseline checks to node ids
  - a fix for a real network-guard gap (MR-11): several checks call run_once() with no injected snapshot, taking the LIVE detect.poll_current_aircraft() path, which the DNS-only guard did not block in this sandbox's transparent-HTTPS-proxy environment - closed by making the module's autouse fixture also depend on conftest.py's fake_providers (patches requests.get itself)
affects: [32-13]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "A harness whose checks share cumulative state through one main()-level tmpdir across several sequential _run() calls (checks 1-5, each state depending on the prior cycle's on-disk state) becomes ONE consolidated pytest test per MR-4, with the old per-check labels listed in the docstring and each old assertion becoming one `assert` in source order - not five independent tests, since splitting them would require re-deriving each intermediate state from scratch."
    - "A harness whose checks share REUSABLE HELPER FUNCTIONS (not mutable state) - server/test_poll_loop.py's `_drive()`/`_ever_on_glass()`/`_promotions()`/`_hermetic()`/`_unpaced()`, used by 10 checks driving a scripted fake-time timeline - hoists the helpers to module level (parameterized on an explicit `clock` fixture and `state_dir` instead of a shared global) and keeps each check as its OWN independent test function; `_hermetic()`'s manual enrich.default_transport save/restore becomes redundant once the module's autouse fixture already stubs it, so the wrapper is deleted outright and its call sites simplified to direct calls."
    - "An AST-based detector for the 'save the old value, patch, try/finally-restore' shape (`original = M.attr; M.attr = fake; try: ... finally: M.attr = original`) - matched by walking Try nodes whose entire finally body is exactly that restore assignment, then backward-scanning the same statement list for the paired save+patch assigns - found and mechanically converted 28 such patches (in 25 distinct Try blocks, including one deliberately-redundant giant wrapper spanning ~85 of the 110 checks) to `monkeypatch.setattr(...)` with the try/finally unwrapped and the body dedented one level. A save variable referenced a THIRD time inside its own closure (a spy calling through to the real function, e.g. `return original_build(flight, state, **kwargs)`) is kept rather than deleted - counting identifier occurrences (>2 means 'also used as a passthrough, not just save/restore') distinguished the 4 cases that needed this from the ~20 that didn't."
    - "ast.col_offset/end_col_offset are UTF-8 BYTE offsets, not Python string character indices - slicing a source line directly by these offsets silently corrupts any segment containing a non-ASCII character (this file has one: '(≈ 9%)' in a battery-percentage assertion string), appending an extra trailing character. Fixed by encoding the line to UTF-8, slicing by byte offset, then decoding back, everywhere AST-derived offsets are used to extract source text."
    - "A module-level `fake_providers`-dependent autouse fixture closes a gap a purely enrich-scoped stub leaves open: `enrich.default_transport` only covers adsbdb enrichment calls, but several checks call run_once() with no injected snapshot and so take the LIVE detect.poll_current_aircraft() path (a pre-existing, previously-undocumented gap beyond the two checks this file's own docstring already flagged). Depending on conftest.py's `fake_providers` fixture (which patches requests.get itself, the shared seam both detect.query_provider() and enrich.default_transport() call) closes it for every test in the module at once, proven by a clean non-root run in a sandbox whose transparent HTTPS proxy defeats a DNS-only guard (the proxy's CONNECT never resolves the real target hostname through socket.getaddrinfo)."

key-files:
  created:
    - .planning/phases/32-test-foundation-pytest-and-ci-you-can-trust/32-ledger/server__test_poll_loop.md
  modified:
    - server/test_poll_loop.py

key-decisions:
  - "All 110 old checks map to 106 pytest node ids: checks 1-5 (the two-deep flight-history sequence, genuinely sequential - each cycle depends on the prior cycle's on-disk state in the SAME state_dir) consolidate into test_two_deep_flight_history_sequence (5:1, MR-4); every other check is 1:1."
  - "Module-level helpers _tick(clock, seconds), _wake_epoch_rows(state_dir), CLIMB, _NOTIFY_TOPIC_URL and _notify_device_cfg() - all originally local to the pre-migration main() function - were promoted to module scope so the now-independent test functions (which no longer share a main()-level closure) can still call them; this surfaced only as NameErrors on the first full test run, not as a design decision made up front, and was fixed by hoisting each one verbatim (no behaviour change)."
  - "The read-only-gallery-directory check (test_readonly_gallery_dir_does_not_fail_cycle) is the file's only permission-bit-dependent check (one os.chmod(0o500) pair) - marked @requires_non_root per MR-8, since euid 0 ignores the read-only bit and the check would otherwise silently stop exercising the degraded-write path it exists to prove."
  - "The autouse fixture stubbing enrich.default_transport was extended to also depend on conftest.py's fake_providers fixture (rather than leaving detect.query_provider's live path unstubbed) - discovered when a non-root verification run genuinely reached opendata.adsb.fi over HTTPS and failed only on TLS cert-bundle permissions, proving the DNS-only network guard does not block this sandbox's transparent HTTPS-proxy path. This is a Rule 1 bug fix (a guard gap the migration surfaced, not introduced) rather than new scope: MR-7's 'no test may reach the real network' requirement was violated by several checks that predate this migration."

requirements-completed: []  # TST-02 spans plans 32-03..32-10 (this is the LAST of 8 server-side migration plans - all 15 harnesses now migrated); not (re-)marked by this plan per the "every plan it spans" rule (32-13 assembles the final ledger and closes out TST-02). TST-03 was already completed by plan 32-01.

# Metrics
duration: ~2h (large single-task plan: 110 checks, 4,637-line source file, heaviest manual-monkeypatch density of the phase)
completed: 2026-09-23
---

# Phase 32 Plan 10: Migrate test_poll_loop to pytest Summary

**server/test_poll_loop.py's 110-check run_once() contract harness - two-deep flight history, the mechanism-C bounded-age pending queue, config/theme/runway/fault plumbing, quiet-hours/display-off/battery-empty holds, manual/colour/calendar theme routing, and the battery/silence notification hooks - is now 106 real pytest test functions, with a genuine network-guard gap (live ADS-B queries on checks that omit an injected snapshot) closed along the way.**

## Performance

- **Duration:** ~2h
- **Tasks:** 1
- **Files modified:** 2 (1 test module + 1 new ledger fragment)

## Accomplishments
- Converted `server/test_poll_loop.py` (4,637 lines, 110 `check()` calls covering `run_once()`'s two-deep current/previous flight history, the mechanism-C pending-queue pacing mitigation, battery hysteresis, config/theme/runway threading, CFG-05 fault classification, history-write gating, gallery retention, quiet-hours/display-off/battery-empty hold states and their transition edges, D-01/D-02/D-14 manual-resolution routing, D-13 colour-rule and calendar-theme routing, and the D-26/T-16/T-20/T-24 notification transition hooks) into 106 standalone pytest test functions.
- Consolidated checks 1-5 (the two-deep flight-history sequence, whose cycles depend on cumulative on-disk state in one shared directory) into a single `test_two_deep_flight_history_sequence` per MR-4; hoisted the mechanism-C pending-queue group's shared helpers (`_drive()`, `_ever_on_glass()`, `_promotions()`, `BURST`/`SUSTAINED` fixtures) to module level and kept its 10 checks as independent tests, deleting the now-redundant `_hermetic()`/`_unpaced()` wrappers whose job the module's autouse fixture already does.
- Built an AST-based detector for the file's "save old value, patch, try/finally-restore" idiom and mechanically converted all 28 matching instances (across 25 Try blocks, including one giant wrapper spanning ~85 checks) to `monkeypatch.setattr()` (MR-6); preserved the 4 cases where the saved value is also used as a spy's passthrough-to-real-implementation rather than deleting it as dead code.
- Converted all `tempfile.mkdtemp()` calls to `tmp_path` via a small `_mkdir()` helper (MR-5); fixed an AST byte-offset-vs-character-offset bug the transform surfaced (a non-ASCII `≈` character in one assertion string) before it could silently corrupt extracted source text.
- Found and fixed a real, previously-undocumented network-guard gap (MR-11/MR-7): several checks call `run_once()` with no injected snapshot, taking the LIVE `detect.poll_current_aircraft()` path - unstubbed, this reaches the real network. Extended the module's autouse fixture to also depend on `conftest.py`'s `fake_providers` fixture, closing the gap for the whole module; verified via a clean `runuser -u nobody` run in this sandbox's transparent-HTTPS-proxy environment (which had silently defeated the DNS-only guard by never calling `socket.getaddrinfo` on the real target host).
- Marked the one permission-bit-dependent check (`test_readonly_gallery_dir_does_not_fail_cycle`) `@requires_non_root` (MR-8).
- All 110 baseline checks verified mapped by `32-ledger-check.py`: 110/110, 110 ported, 0 deleted, 0 pending.
- Passes under both `-n 0` and `-n 4` (106 passed/1 skipped as root, 106 passed as non-root), `ruff check` clean, legacy-runner bridge (`server/.venv/bin/python3 server/test_poll_loop.py`) exits 0, zero `EXPECTED_CHECK_COUNT`/`def check(`/`tempfile.` occurrences, zero new untracked files after a fresh run, zero production-code changes, zero `enable_socket` markers.

## Task Commits

Each task was committed atomically:

1. **Task 1: Migrate test_poll_loop** - `12df198` (feat)

**Plan metadata:** (this commit, docs: complete plan)

## Files Created/Modified
- `server/test_poll_loop.py` - 106 `test_*` functions; module docstring trimmed of the `EXPECTED_CHECK_COUNT` changelog and the multi-paragraph `_DEFAULT_CONFIG_DIGEST` re-pin history (MR-10); `poll_loop`/`device_config`/`detect`/`render`/`calendar_rules`/`colour_rules`/`enrich`/`manual_resolutions`/`history_db` now module-level imports; `clock` and autouse `_stub_adsbdb` fixtures added; `_mkdir`/`_tick`/`_wake_epoch_rows`/`CLIMB`/`_NOTIFY_TOPIC_URL`/`_notify_device_cfg` hoisted to module scope; `pytestmark = pytest.mark.slow`; legacy-runner `__main__` bridge with `test-support/` added to `sys.path`
- `.planning/phases/32-test-foundation-pytest-and-ci-you-can-trust/32-ledger/server__test_poll_loop.md` (new) - 110 rows, all `ported` (5 rows point at the one consolidated node id, 105 rows are 1:1)

## Decisions Made
- Consolidated checks 1-5 into one node id (5:1) rather than reconstructing each intermediate state independently - the old checks' entire point is that state SURVIVES across `run_once()` calls against the same directory, so splitting them into independent tests would mean re-deriving (not testing) each prior cycle's outcome.
- Hoisted `_drive()`/`_ever_on_glass()`/`_promotions()` (shared by checks 9-18) to module level with an explicit `clock`/`state_dir` parameter rather than closing over a module-global `CLOCK` dict and an owned-tempdir fallback - keeps every test independent under `-n 4` and removes the one remaining hidden `tempfile.mkdtemp()` call the original `_drive()` had (undercounted by a literal grep, per the 32-09 lesson: hidden behind a shared helper).
- Used an AST pattern-matcher (walk `Try` nodes whose `finalbody` is exactly a restore assignment, then backward-scan the same statement list for the paired save+patch) rather than hand-editing all 28 manual-patch instances individually - safe because the shape is syntactically uniform across the file, and because reference-counting each saved variable's identifier (>2 occurrences means "also called through", not just saved/restored) correctly distinguished the 4 spy/passthrough cases from the rest without a human having to inspect all 28 by hand.
- Extended the network stub to also cover `detect.query_provider()`'s live path (via `fake_providers`) rather than leaving it as a documented pre-existing gap (as the original file's own docstring did for checks 1-5) - MR-7/MR-11 are explicit in this phase's migration rules that a guard-exposed real-network access must be stubbed in the test, and the gap is now provably closed rather than merely narrower.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Several checks reached the real network through the unstubbed live detection path**
- **Found during:** Task 1, non-root verification run (`runuser -u nobody`) - `test_battery_empty_missing_or_corrupt_reading_never_parks_and_never_clears` failed with a TLS certificate-bundle `OSError` while actually connecting to `opendata.adsb.fi`
- **Issue:** The original harness's own docstring only flagged checks 1-5 as "not hermetic on that axis" (reaching live adsbdb for FLIGHT1-4 callsigns), but the same gap exists far more broadly: every check that calls `run_once(state_dir=..., geofence=...)` with no `snapshot=` argument takes the LIVE `detect.poll_current_aircraft()` path, which calls `detect.query_provider()` -> `requests.get()`. The module's `enrich.default_transport`-only stub never touched this seam, and in this sandbox the DNS-based non-loopback guard doesn't block it either (a transparent HTTPS proxy handles the CONNECT without ever resolving the real target hostname through `socket.getaddrinfo`), so the request actually reached the real network - it happened to keep "passing" as root only because root's environment has read access to the sandbox's CA bundle.
- **Fix:** Made the module's autouse `_stub_adsbdb` fixture also depend on `conftest.py`'s `fake_providers` fixture, which patches `requests.get` itself (the shared seam both `detect.query_provider()` and `enrich.default_transport()` use) with empty/miss defaults.
- **Files modified:** `server/test_poll_loop.py`
- **Verification:** `pytest server/test_poll_loop.py -q` (root, `-n 0` and `-n 4`) and `runuser -u nobody -- ... pytest server/test_poll_loop.py -q` all pass cleanly with no network reachable.
- **Committed in:** `12df198` (part of task commit)

**2. [Rule 3 - Blocking] Local helper functions/constants defined inside the old main() needed hoisting to module scope**
- **Found during:** Task 1, first full test run - `NameError` for `CLIMB`, `_notify_device_cfg`, `_tick`, `_wake_epoch_rows`, each used by multiple now-independent test functions but never defined at module scope in the pre-migration file (they were local to `main()`, available to every nested check via closure)
- **Issue:** Promoting each check from a nested closure to a standalone top-level function meant it could no longer see these four names.
- **Fix:** Moved each definition verbatim to module scope (no behaviour change - `_tick` gained an explicit `clock` parameter matching the new per-test `clock` fixture instead of closing over a module global).
- **Files modified:** `server/test_poll_loop.py`
- **Verification:** `pytest server/test_poll_loop.py -q -n 0` and `-n 4`, both green.
- **Committed in:** `12df198` (part of task commit)

---

**Total deviations:** 2 auto-fixed (1 bug, 1 blocking)
**Impact on plan:** Both necessary for correctness - the network-guard gap is a real MR-7 violation the migration is explicitly required to close (not new scope), and the hoisting fix is required for the file to import at all. No scope creep.

## Issues Encountered
- `ast.col_offset`/`end_col_offset` are UTF-8 byte offsets, not Python string character indices; a transform script slicing a source line directly by these offsets silently produced a corrupted extra-character result for the one assertion string containing a non-ASCII `≈` character. Fixed by encoding-then-byte-slicing-then-decoding everywhere the migration's mechanical transform extracted source text by AST offset - caught by a syntax error on the very first full-file parse, not silently.

## Next Phase Readiness
- All 15 of the phase's server-side harnesses are now migrated (14 through 32-08/32-09, plus `server/test_poll_loop.py` from this plan) - 769 of 769 baseline checks across the phase. TST-02's harness-migration work is complete; 32-13 assembles the final `32-MIGRATION-LEDGER.md` from all 15 fragments and retires the legacy `scripts/run_all_tests.py` runner.
- The AST-based "save/patch/try-finally-restore -> monkeypatch.setattr" detector and the UTF-8-byte-offset lesson are reusable for any future mechanical-transform work touching this codebase's other hand-rolled harnesses (companion/, Phase 33).
- No blockers. TST-02 stays "Pending" in REQUIREMENTS.md until 32-13's ledger assembly step closes it out per the "every plan it spans" rule; TST-03 was already "Complete" from plan 32-01.

---
*Phase: 32-test-foundation-pytest-and-ci-you-can-trust*
*Completed: 2026-09-23*

## Self-Check: PASSED

`server/test_poll_loop.py`, the ledger fragment, and this summary confirmed present on
disk; task commit hash (`12df198`) confirmed present in `git log --oneline --all`.
