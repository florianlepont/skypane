---
phase: 32-test-foundation-pytest-and-ci-you-can-trust
fixed_at: 2026-09-24T00:00:00Z
review_path: .planning/phases/32-test-foundation-pytest-and-ci-you-can-trust/32-REVIEW.md
iteration: 1
findings_in_scope: 9
fixed: 9
skipped: 0
status: all_fixed
---

# Phase 32: Code Review Fix Report

**Fixed at:** 2026-09-24
**Source review:** .planning/phases/32-test-foundation-pytest-and-ci-you-can-trust/32-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 9 (CR-01, CR-02, WR-01 to WR-07). The Info findings IN-01 to IN-05 were out of scope and left as they are.
- Fixed: 9
- Skipped: 0

I checked every finding against the code before fixing it, and all of them reproduced. CR-01: with the sandbox's loopback `HTTPS_PROXY`, `requests.get("https://api.adsbdb.com/...")` returned `LEAKED 200` under `install_child_network_guard()`. WR-03: `from_file()` raised `AttributeError: module 'requests' has no attribute 'SSLError'`. The other findings were confirmed by reading the code.

**Final verification:** I ran the full suite as a non-root user (`runuser -u nobody`) on CPython 3.14.0rc2, using a fresh venv built from `server/requirements-dev.txt` with `--require-hashes` and `SKYPANE_REQUIRE_BROWSER=1`. The command was `./scripts/run-all-tests.sh`, a full run with the gate on. It exited 0 with `Required test coverage of 93.0% reached. Total coverage: 93.35%` and `777 passed, 57 warnings in 272.03s`. `ruff check .` reported that all checks passed.

## Fixed Issues

### CR-01: The network guard is bypassed whenever an HTTP(S) proxy env var points at loopback

**Files modified:** `test-support/skypane_test_support.py`, `conftest.py`, `test-support/test_test_support.py`
**Commits:** 7ce3013, 73e61d4 (follow-up)
**Applied fix:**
- Added `PROXY_ENV_VARS` and `strip_proxy_env()`.
- Proxy variables are now stripped in three places:
  - in `install_child_network_guard()`, before the guard installs;
  - in `child_env()`, on the copied env;
  - at `conftest.py` import time, which covers every xdist worker and every child that inherits `os.environ`.
- New self-tests:
  - no proxy variable is set in-process;
  - `child_env()` drops the proxy variables;
  - a child that has the guard and every proxy variable set to `http://127.0.0.1:9` still fails with `NetworkAccessBlocked`. Without the strip, the same child gets a `ProxyError`, so this test really tells the two cases apart.
- Follow-up 73e61d4: the self-test now uses `http://` instead of `https://`. As a non-root user, the environment's `REQUESTS_CA_BUNDLE` (under `/root`) could not be read, and the `https://` request failed on that before it reached the guard.

### CR-02: The stale-deploy guard skips valid deploys when `main` moved to a commit that will never deploy itself

**Files modified:** `.github/workflows/ci.yml`
**Commit:** a40d2f0 (shared with WR-01: both findings are in the same step)
**Applied fix:** The step that marked the run "stale" and let every deploy step skip, with a green job, is replaced by one gating step that decides as follows:
- **Deploy** when `github.sha` is still the tip of `main`.
- **Deploy** when `main` moved on, but the `git diff` between this sha and the tip leaves every shipped path unchanged (`server stub-server companion adsb-test/runway3.json deploy`, the paths `deploy.sh` rsyncs plus the script itself). A docs-only tip is the typical case, and it would never deploy itself.
- **Fail the job** with `::error::` when the newer tip changes shipped files.

So a reviewer's approval can no longer end in a green run that shipped nothing. I removed the per-step `if: stale` conditions and updated the header and job comments. The logic was simulated against local git repos: tip → rc 0; docs-only tip → notice, then rc 0; code tip → error, rc 1; unreachable remote → rc 128. The YAML parses with `yaml.safe_load` (actionlint is not available here).

### WR-01: A failing `git ls-remote` is silently treated as "stale"

**Files modified:** `.github/workflows/ci.yml`
**Commit:** a40d2f0 (shared with CR-02)
**Applied fix:** The step now runs with `set -euo pipefail`. `latest` must match `^[0-9a-f]{40}$`, otherwise the step prints `::error::` and exits 1. A failed `git fetch` or `git diff` also fails the job, so an error can never pass for a skip.

### WR-02: Subprocess coverage is lost for every SIGTERM-stopped server

**Files modified:** `pyproject.toml`
**Commit:** b8616f2
**Applied fix:**
- Added `sigterm = true` to `[tool.coverage.run]`, with a comment.
- Re-measured on CPython 3.14.0rc2 as non-root with the full suite: **93.35%**, up from 88.11%. `byos_server.py` is now at 94% and `companion/app.py` at 92%.
- Raised `fail_under` from **88 to 93** (the measurement rounded down, no margin) and rewrote the derivation comment.
- I did not change the harness `stop()` methods to send SIGINT. That part of the finding was optional, and SIGTERM is now captured.

### WR-03: `FakeProviders.from_file()` checks `requests.exceptions` but reads the class from `requests`

**Files modified:** `test-support/skypane_test_support.py`, `test-support/test_test_support.py`
**Commit:** 6c5c8b9
**Applied fix:**
- `from_file()` now loads the class from `requests.exceptions` and requires a `RequestException` subclass. This rejects `BaseHTTPError`.
- `to_file()` now rejects a failure that the child could not rebuild, and raises in the parent instead.
- Added tests:
  - `SSLError`, `ProxyError`, `ChunkedEncodingError` and `ReadTimeout` survive the round trip through the file;
  - `to_file()` rejects a non-requests exception;
  - `from_file()` rejects `BaseHTTPError`.

### WR-04: Browser harnesses pass vacuously through the shim when Chromium cannot launch

**Files modified:** `companion/test_legacy_harness_shim.py`, `.github/workflows/ci.yml`
**Commit:** daded9f
**Applied fix:**
- When a harness exits 0 with a line starting `SKIP `, the shim now calls `pytest.fail` if `CI=true` or `SKYPANE_REQUIRE_BROWSER=1`. Otherwise the result is a visible `pytest.skip`.
- The CI test step now sets `SKYPANE_REQUIRE_BROWSER: "1"`.
- Checked with an empty `PLAYWRIGHT_BROWSERS_PATH`: skipped locally, failed with `CI=true`, and passed normally when Chromium is present.
- No non-browser harness prints a `SKIP ` line.
- Moving these harnesses fully to pytest-playwright stays in Phase 33.

### WR-05: `byos_server_factory` leaks the server subprocess when startup fails

**Files modified:** `server/test_pipeline_e2e.py`
**Commit:** 7226110
**Applied fix:** Each harness is now added to the teardown list before `start()`. In teardown, every `stop()` is wrapped so that a stop that raises falls back to `proc.kill()` and never leaves the remaining harnesses running.

### WR-06: `paths-ignore` skips CI for Markdown that the test suite actually reads

**Files modified:** `.github/workflows/ci.yml`
**Commit:** fb80a7b
**Applied fix:**
- Replaced `paths-ignore` on both triggers with an ordered `paths` filter: `'**'` first, then the `!` exclusions for docs.
- That filter re-includes by name the Markdown the suite reads:
  - `06.6.3-CONTEXT.md`, `20-UI-SPEC.md` and `21-UI-SPEC.md`, which the legacy harnesses read;
  - `server/assets/**/VENDOR.md`, which `check-attribution.sh` checks. The review did not mention these files, but I found them in the same search.
- Updated the header comment, including a note that a new test which reads a doc must be added to this list.

### WR-07: Every subset invocation of `run-all-tests.sh` fails on the coverage gate

**Files modified:** `scripts/run-all-tests.sh`
**Commit:** e21b3c7
**Applied fix:**
- With no extra arguments (the CI invocation), the gate is enforced as before.
- With any extra argument, the script prints a notice and passes `--cov-fail-under=0` before the user's arguments, so an explicit later `--cov-fail-under=N` still wins.
- The script's usage text documents this.
- The empty-array expansion uses a form that also works on bash 3.2 under `set -u`.
- Checked: `JOBS=2 ./scripts/run-all-tests.sh server/test_dither.py` → 6 passed, exit 0.

## Notes

- CR-02 and WR-01 share one commit (a40d2f0) because both are fixed by rewriting the same single shell step. Splitting them would have meant committing an intermediate guard that is still wrong.
- IN-01 to IN-05 are not addressed. IN-05 (legacy harnesses fail when run as root) is why the final run was done as `nobody`.

---

_Fixed: 2026-09-24_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
