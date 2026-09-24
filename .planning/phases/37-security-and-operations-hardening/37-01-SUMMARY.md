---
phase: 37-security-and-operations-hardening
plan: 01
subsystem: auth
tags: [companion, login-throttle, rate-limiting, ipaddress, pytest, threadinghttpserver]

# Dependency graph
requires:
  - phase: 32-test-foundation-pytest-and-ci-you-can-trust
    provides: pytest infrastructure (conftest.py, pyproject.toml [tool.pytest.ini_options], no-network socket guard, skypane_test_support helpers)
provides:
  - "companion/auth.py: keyed, bounded LoginThrottle (OrderedDict, injectable clock, max_entries) plus client_ip()/login_throttle_key() pure helpers"
  - "companion/app.py: login handler keyed on the caller's address via Handler._login_throttle_key(); --bind flag (default 0.0.0.0)"
  - "companion/test_login_throttle.py: the first native pytest test module under companion/ (unit + HTTP integration)"
affects: [37-03 (skypane-companion.service --bind 127.0.0.1), 33 (companion legacy-harness migration)]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "LoginThrottle keyed by collections.OrderedDict[key] -> [failures, locked_until, last_seen], bounded by max_entries with stale-then-LRU eviction"
    - "Single per-request derivation point (Handler._login_throttle_key()) for a value multiple call sites must agree on"
    - "companion/test_login_throttle.py: native pytest test file under companion/, exempted from test_legacy_harness_shim.py's on-disk drift guard rather than folded into the legacy check()/EXPECTED_CHECK_COUNT harness"

key-files:
  created:
    - companion/test_login_throttle.py
    - .planning/phases/37-security-and-operations-hardening/deferred-items.md
  modified:
    - companion/auth.py
    - companion/app.py
    - companion/test_companion_app.py
    - companion/test_legacy_harness_shim.py

key-decisions:
  - "LoginThrottle read-only methods (locked_out/seconds_remaining) never touch or create table entries — only record_failure/record_success can insert, so a mere status check cannot grow the table, and an attacker's own locked entry can still be evicted early under a spray (accepted, T-37-05)"
  - "The three legacy check()-style throttle tests in test_companion_app.py were ported to the keyed API in place (still a stdlib harness, not migrated to pytest — Phase 33 scope) rather than duplicated into test_login_throttle.py"

requirements-completed: [SEC-01, SEC-06]

# Metrics
duration: 25min
completed: 2026-09-24
---

# Phase 37 Plan 01: Per-client-IP login throttle + companion --bind Summary

**Companion login lockouts are now keyed per caller address (bounded OrderedDict + client_ip()/login_throttle_key(), trusting X-Forwarded-For only from a loopback peer) instead of one process-global counter, and companion/app.py gained a backward-compatible `--bind` flag for a future loopback-only production deployment.**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-09-24T07:34:00Z (STATE.md position set)
- **Completed:** 2026-09-24T07:47:15Z (Task 2 commit)
- **Tasks:** 2/2 completed
- **Files modified:** 5 (2 created, 3 modified) + 1 deferred-items.md

## Accomplishments
- `companion/auth.py`'s `LoginThrottle` rewritten to key every bucket on the caller's address (`OrderedDict[key] -> [failures, locked_until, last_seen]`), bounded by `max_entries` with stale-unlocked-first-then-LRU eviction, and an injectable `clock=` for deterministic tests — the "fresh count after a fully-elapsed window" contract preserved byte for byte.
- New pure helpers `client_ip(peer, xff)` and `login_throttle_key(peer, xff)`: XFF trusted only from a loopback peer (including IPv4-mapped loopback), right-most entry taken, IPv6 collapsed to its `/64`.
- `companion/app.py`'s `_handle_login_post` now derives one throttle key per request (`Handler._login_throttle_key()`) and threads it through every `LOGIN_THROTTLE` call — no key-less call sites remain.
- `--bind` flag added to `companion/app.py` (default `0.0.0.0`, unchanged behaviour); `main()` binds `(args.bind, args.port)` instead of the hard-coded `"0.0.0.0"`.
- Proven end to end over real HTTP (SC-1): five wrong passwords with `X-Forwarded-For: 203.0.113.5` lock that key (429); a correct password with `X-Forwarded-For: 198.51.100.7` still logs in (303); the attacker's key stays locked even with the right password.
- `companion/test_login_throttle.py` created — 15 native pytest tests (unit LoginThrottle/`client_ip`/`login_throttle_key`, HTTP integration against a real subprocess, `--bind` parsing and a live loopback-bind smoke test). This is the first native pytest test file under `companion/`.

## Task Commits

Each task was committed atomically:

1. **Task 1: Phase 32 gate, then keyed LoginThrottle + client_ip() in auth.py (TDD)** - `114804f` (feat) — RED (12 failing tests) confirmed, then GREEN.
2. **Task 2: Key the login handler on the client IP, add --bind, port legacy checks, HTTP integration tests** - `17fdc0f` (feat)

**Plan metadata:** (this commit, docs: complete plan)

## Files Created/Modified
- `companion/auth.py` - Keyed/bounded `LoginThrottle`, `client_ip()`, `login_throttle_key()`; docstring rewritten (why-only, no plan IDs); `ipaddress`/`collections` added to the stdlib import list
- `companion/app.py` - `Handler._login_throttle_key()`, keyed `_handle_login_post`, `--bind` argparse flag, `main()` binds `args.bind`, module docstring and `LOGIN_THROTTLE` comment updated
- `companion/test_login_throttle.py` - New pytest file: 15 tests (unit + HTTP integration + `--bind`)
- `companion/test_companion_app.py` - The three legacy `_login_throttle_*` checks ported to the keyed API (one now uses `clock=` injection instead of a private-attribute time-travel hack); `EXPECTED_CHECK_COUNT` unchanged (320) since no check was added or removed
- `companion/test_legacy_harness_shim.py` - `test_legacy_harness_list_matches_disk` exempts the new native pytest file, the same way it already exempts `test_browser_ux_helpers.py`
- `.planning/phases/37-security-and-operations-hardening/deferred-items.md` - New: records two pre-existing, out-of-scope test failures found while verifying (see Issues Encountered)

## Decisions Made
- `locked_out()`/`seconds_remaining()` are pure reads: a missing key returns "not locked"/`0` without creating an entry, so a status check alone can never grow the bounded table — only a `record_failure`/`record_success` call can insert.
- The legacy `test_companion_app.py` checks were edited in place (not migrated to pytest) per the plan's own instruction — that file's shape stays Phase 33 scope; this plan only had to keep its three throttle checks correct against the new keyed API.
- `test_login_throttle.py`'s HTTP integration tests reimplement the `Harness` pattern already used by `test_companion_app.py` (own subprocess, own temp dir, own free port) rather than importing `Harness` from that legacy module — the legacy module is a `check()`/`main()` script, not meant to be imported, and `conftest.py`'s `collect_ignore` already keeps pytest from touching it directly.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Exempted the new native pytest file from the legacy-harness drift guard**
- **Found during:** Task 2, running `./scripts/run-all-tests.sh`
- **Issue:** `test_legacy_harness_shim.py::test_legacy_harness_list_matches_disk` asserts every `test_*.py` file under `companion/` (other than the shim itself and `test_browser_ux_helpers.py`) is a registered legacy harness. `companion/test_login_throttle.py` is the plan's own deliverable and the first native pytest file in that directory — the guard failed on its mere existence.
- **Fix:** Added `"test_login_throttle.py"` to the same exemption tuple that already excludes `test_browser_ux_helpers.py`, with a comment explaining why.
- **Files modified:** `companion/test_legacy_harness_shim.py`
- **Verification:** `pytest -q companion/test_legacy_harness_shim.py -k test_legacy_harness_list_matches_disk` passes; full suite re-run confirms no other file lost coverage.
- **Committed in:** `17fdc0f` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Necessary consequence of adding the plan's own required test file. No scope creep — the fix touches only the drift guard's exemption list, not the harness's migration status.

## Issues Encountered

**Pre-existing, root-euid-only test failures (not caused by this plan, not fixed — see `deferred-items.md`).** `./scripts/run-all-tests.sh` in this sandbox (running as `root`) leaves two failures: `test_companion_app` (318/320) and `test_status_pages` (316/317), both from WR-11 checks that simulate a write failure with `os.chmod(dir, 0o500)` — root ignores permission bits, so the simulated failure never happens. These exact counts are already recorded in `32-REVIEW.md` as a known gap ("legacy harnesses have no equivalent [to `@requires_non_root`], so running `./scripts/run-all-tests.sh` in a root container is red"), predating this plan and unrelated to `companion/auth.py`/`companion/app.py`. Fixing it is Phase 33 scope (migrating those two harnesses to pytest, where `@requires_non_root` already exists). Confirmed this plan introduces no new failures: before the one drift-guard fix above, the full suite showed exactly these same 2 failures plus the 1 (self-inflicted, now fixed) drift-guard failure — 3 total, 784 passed.

`server/.venv` was also missing its dev dependencies (`pytest`, `pytest-cov`, `pytest-socket`, `pytest-xdist`, etc. — only the runtime `server/requirements.txt` set was installed) at the start of this session; ran `server/.venv/bin/python -m pip install -r server/requirements-dev.txt` (hash-locked, no version drift) before any test could run. Not a code change, not committed.

## User Setup Required

None - no external service configuration required. (Production's `skypane-companion.service` `--bind 127.0.0.1` cutover is Plan 37-03's job, not this plan's.)

## Next Phase Readiness

- `auth.login_throttle_key()`/`auth.client_ip()` are stable, importable names Plan 37-05 (and any other Wave A plan touching `companion/app.py`) can rely on per the plan's own interface contract.
- `--bind` is ready for `deploy/skypane-companion.service` to pass `127.0.0.1` in Plan 37-03 — no further `companion/app.py` change needed for that cutover.
- No blockers for the rest of Wave A (SEC-02..SEC-08 minus byos).

---
*Phase: 37-security-and-operations-hardening*
*Completed: 2026-09-24*

## Self-Check: PASSED

All files claimed as created/modified exist on disk (`companion/auth.py`,
`companion/app.py`, `companion/test_login_throttle.py`,
`companion/test_companion_app.py`, `companion/test_legacy_harness_shim.py`,
`deferred-items.md`, this file). Both task commits (`114804f`, `17fdc0f`)
are present in `git log --oneline --all`.
