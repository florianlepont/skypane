---
phase: 32-test-foundation-pytest-and-ci-you-can-trust
verified: 2026-09-24T07:01:35Z
status: human_needed
score: 5/5 roadmap success criteria verified locally (9/9 TST requirements satisfied locally; 3 CI-only behaviours need a real GitHub Actions run)
overrides_applied: 0
human_verification:
  - test: "Push the branch (review fixes a40d2f0..e1a22c2 are local only) and open the CI run for PR #105's new head; read the 'Print resolved Python version' step and the test job result"
    expected: "Python 3.14.x printed; lint, the full `./scripts/run-all-tests.sh` (SKYPANE_REQUIRE_BROWSER=1, no browser harness skipped), the coverage gate (93) and the attribution check all green; firmware.yml's `host-tests` job green without the ESP-IDF container"
    why_human: "Only a real GitHub-hosted runner proves setup-python resolves 3.14 and the hash-enforced install works there; the post-review commits have not run on Actions yet"
  - test: "Re-run the CI test job (or push a second commit) with the same playwright pin"
    expected: "'Cache Playwright browsers' reports a cache hit on key playwright-Linux-1.63.0-headless-shell and `playwright install --only-shell` skips the browser download"
    why_human: "actions/cache hit/miss is only observable in Actions logs"
  - test: "On main: push A, approve its deploy; while it is running push B; also try approving an older queued deploy after main moved on to a code change, and after a Markdown-only change"
    expected: "A's running deploy is never cancelled (production-deploy group, cancel-in-progress: false); B's test job starts without waiting for A's approval; an approval for a commit superseded by shipped-file changes fails red with ::error::, a Markdown-only move deploys with ::notice::"
    why_human: "Concurrency/cancellation semantics and the `production` environment reviewer gate only exist on GitHub; locally only the YAML and the git pathspec logic could be checked"
---

# Phase 32: Test foundation — pytest and CI you can trust — Verification Report

**Phase Goal:** Every test runs under pytest on the production Python version, no test touches the network, and a green CI means every check actually ran. Server-side harnesses migrated first; the infrastructure (fixtures, xdist, coverage gate, hash-locked deps) serves Phase 33.
**Verified:** 2026-09-24T07:01:35Z
**Status:** human_needed
**Re-verification:** No, initial verification (after the 32-REVIEW-FIX pass and follow-up e1a22c2)

## Goal Achievement

### Observable Truths (roadmap success criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `pytest -n auto` runs every migrated server/stub-server test; the migration ledger accounts for every pre-migration check (ported, or deleted with a reason) | VERIFIED | `pytest --collect-only -q` → 777 tests, 0 errors; all 15 migrated files collected (server 14 + stub-server/test_poll_cycle.py). `32-ledger-check.py --all` → rc 0, every harness N/N mapped, 0 pending, 0 deleted (e.g. render 140/140, poll_loop 110/110, calendar_rules 113/113, poll_cycle 46/46; total 769). `--self-test` OK (27 checks). Spot check: pipeline_e2e's 7 baseline checks all map to the one consolidated test, which carries the assertions for each (panel size, nibble legality, setup/display, SHA-256 verify, D-04 byte-identity, battery icon diff, BATTERY EMPTY park/recover). `scripts/run_all_tests.py` is gone. |
| 2 | A test opening a non-loopback socket fails; `/poll-now` tests use the fake provider | VERIFIED | pyproject addopts `--disable-socket --allow-unix-socket --allow-hosts=127.0.0.1,::1,localhost`; conftest autouse DNS guard; proxy env stripped at conftest import, in `child_env()` and in `install_child_network_guard()` (CR-01). Self-tests (22 passed) prove in-process connect (SocketConnectBlockedError) + DNS (NetworkAccessBlocked) blocked, child connect/DNS blocked, loopback allowed, loopback-proxy bypass closed. No test opts out (`enable_socket` unused). `companion/test_companion_app.py` Harness.start() uses `child_env(..., fake_providers=FakeProviders(), state_dir=...)`; /poll-now check at ~L10815 asserts the fake served the call via `fake_provider_calls()`; in-process /poll-now at ~L11835 wrapped in `FakeProviders().installed()`. Shim launches every harness with `env=child_env()`. |
| 3 | CI runs on the production Python version and runs the firmware host tests | VERIFIED (locally) / human for runner | ci.yml `python-version: '3.14'`, prints version, ruff `target-version = "py314"`. firmware.yml `host-tests` job (ubuntu-latest, no container, no `needs:`) runs `./firmware/tests/run_host_tests.sh`; run locally: 8 suites passed. Actual 3.14 resolution on Actions → human item 1. |
| 4 | Coverage measured for `companion/app.py` and `byos_server.py`; gate raised to the measured floor | VERIFIED | `[tool.coverage.run] patch = ["subprocess"]`, `sigterm = true`; omit list only the three `test_*.py` globs. Full run (nobody, clean 3.14 venv): app.py 92 %, byos_server.py 94 %, make_test_panel.py 98 %, TOTAL 93.35 % → `fail_under = 93` equals the measurement rounded down, derivation documented. Gate proven live: `pytest --cov=. server/test_dither.py` → "FAIL Required test coverage of 93.0% not reached", rc 1. |
| 5 | Runtime and dev dependencies hash-locked; Playwright shell cached | VERIFIED (locally) / human for cache hit | requirements.txt pins all 6 runtime packages incl. urllib3/certifi/idna/charset-normalizer with hashes; requirements-dev.txt is the superset (21 pins, same runtime versions). A fresh 3.14 venv installed `-r server/requirements-dev.txt --require-hashes` cleanly; a tampered idna hash was rejected ("Expected sha256 0000… Got ab7a…"). deploy.sh: `pip install --require-hashes -r …/server/requirements.txt`, sha256sum of the same file. ci.yml: `--require-hashes -r server/requirements-dev.txt`, `playwright install --with-deps --only-shell chromium`, actions/cache on `~/.cache/ms-playwright` keyed on the installed playwright version. Cache hit → human item 2. |

**Score:** 5/5 success criteria verified in the codebase; CI-runtime confirmation pending (human).

### Plan must-haves (merged)

All plan-level truths from 32-01..32-15 were checked; highlights beyond the roadmap SCs:

| Plan truth | Status | Evidence |
|------------|--------|----------|
| 32-01 collect-only never collects a legacy companion module | VERIFIED | `collect_ignore = LEGACY_COMPANION_COLLECT_IGNORE`; only `companion/test_legacy_harness_shim.py` collected from companion/ (9 parametrised + list-matches-disk) |
| 32-04/08/10/13 migrated tests pass as root and non-root | VERIFIED | root: `pytest -n 4 server stub-server test-support` → 764 passed, 3 skipped (`requires_non_root`); nobody: full suite 777 passed |
| 32-13 run-all-tests.sh is a pytest wrapper with PYTHON= contract; subsets skip the gate (WR-07) | VERIFIED | `exec "${PYTHON}" -m pytest -n "${JOBS:-auto}" --cov …`; `--cov-fail-under=0` only when extra args |
| 32-14 separate concurrency groups; deploy `cancel-in-progress: false`; stale-deploy guard fails loudly | VERIFIED (static) | job-level `test-${{ github.ref }}` / `production-deploy`; guard with `set -euo pipefail`, 40-hex check, `::error::` + exit 1. e1a22c2 pathspec `':(exclude,glob)**/*.md'` simulated: md-only change under server/ → rc 0, without exclusion → rc 1 |
| 32-14 WR-04 browser harness SKIP fails in CI | VERIFIED | shim `pytest.fail` on `^SKIP ` when CI=true or SKYPANE_REQUIRE_BROWSER=1; set in ci.yml; local run with the var set: 0 skipped, test_browser_ux ran (~218 s) |
| 32-15 docs describe pytest and 3.14 | VERIFIED | README "Requires Python 3.14." + pytest Tests section; CONTRIBUTING, server/README, CLAUDE.md stack row |

### Required Artifacts

| Artifact | Status | Details |
|----------|--------|---------|
| `test-support/skypane_test_support.py`, `sitecustomize.py`, `test_test_support.py` | VERIFIED | guard, FakeProviders, child_env, legacy list; sitecustomize installs guard/fake on env var; self-tests pass |
| `conftest.py` | VERIFIED | collect_ignore, proxy strip, autouse DNS guard, `fake_providers` fixture |
| `companion/test_legacy_harness_shim.py` | VERIFIED | 9 harnesses, child_env, process-group timeout, SKIP→fail in CI |
| `pyproject.toml` | VERIFIED | pytest ini, py314, patch subprocess, sigterm, fail_under 93 |
| 15 migrated test files + `32-ledger/*.md` + `32-MIGRATION-LEDGER.md` | VERIFIED | ledger check rc 0 |
| `server/requirements{,-dev}.{in,txt}`, `scripts/lock-deps.sh` | VERIFIED | uv pip compile --generate-hashes --python-version 3.14 |
| `.github/workflows/ci.yml`, `firmware.yml` | VERIFIED | YAML parses; jobs test/deploy, host-tests/build |

### Behavioral Spot-Checks / Probe Execution

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Lint | `ruff check .` (0.16.8) | All checks passed | PASS |
| Collection | `pytest --collect-only -q` | 777 collected | PASS |
| Ledger | `python3 32-ledger-check.py --all` / `--self-test` | rc 0, 15/15 harnesses fully mapped / SELF-TEST OK (27) | PASS |
| Guard self-tests | `pytest test-support/ …::test_legacy_harness_list_matches_disk` | 22 passed | PASS |
| Full suite, 3.14, non-root | `runuser -u nobody -- env SKYPANE_REQUIRE_BROWSER=1 PYTHON=<clean 3.14.0rc2 venv, --require-hashes> ./scripts/run-all-tests.sh` | rc 0, 777 passed, 93.35 % ≥ 93 | PASS |
| Root run of migrated tests | `pytest -n 4 server stub-server test-support` (root) | 764 passed, 3 skipped | PASS |
| Gate trips | `pytest --cov=. server/test_dither.py` | rc 1, coverage 2.38 % < 93 | PASS |
| Hash enforcement | `pip download --require-hashes` good vs tampered idna | good downloaded; tampered rejected | PASS |
| Firmware host tests | `./firmware/tests/run_host_tests.sh` | 8 suites passed | PASS |

Run note: the provided scratchpad venv (`…/scratchpad/venv314`) sits under 0700 directories (`/tmp/claude-0`, `/root`), so `nobody` cannot execute it. A first attempt that temporarily added o+x to those directories lost access partway through (2 browser-harness shim tests failed with `PermissionError` executing the interpreter, an environment artefact, not a code failure; permissions were restored). The run that counts used a fresh copy of the same CPython 3.14.0rc2 and a clean venv in a world-readable temp dir, installed from `server/requirements-dev.txt --require-hashes`, which was deleted afterwards. Log: `…/scratchpad/fullrun-nobody-clean.log`.

### Requirements Coverage

| Requirement | Source Plan | Status | Evidence |
|-------------|------------|--------|----------|
| TST-01 pytest/xdist/cov dev deps, pyproject config, conftest, gate on pytest-cov, docs | 32-01, 32-13, 32-15 | SATISFIED | see SC1/SC4, docs row |
| TST-02 migration + ledger | 32-02..32-10, 32-13 | SATISFIED | ledger check rc 0, 769/769 |
| TST-03 fake provider fixture + non-loopback guard | 32-01, 32-11 | SATISFIED (warning below) | SC2 |
| TST-04 CI + ruff on production version | 32-01, 32-14 | SATISFIED | 3.14 / py314 |
| TST-05 firmware host tests in firmware.yml | 32-14 | SATISFIED | host-tests job |
| TST-06 separate concurrency; never cancel in-flight deploy | 32-14 | SATISFIED (static) / human | job-level groups |
| TST-07 --only-shell + cache | 32-14 | SATISFIED (static) / human | ci.yml |
| TST-08 hash-pinned locks | 32-12 | SATISFIED | tamper rejected |
| TST-09 subprocess coverage + floor | 32-13, 32-15, WR-02 | SATISFIED | 93.35 % / 93 |

No orphaned requirements: REQUIREMENTS.md maps only TST-01..TST-09 to Phase 32.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `stub-server/test_devices_registry.py` | 105, 144, 185 | `byos_server.py` / `make_test_panel.py` / `devices_cli.py` children launched without `child_env()` (no child network guard); temp dirs via `tempfile.mkdtemp` rather than `tmp_path` | WARNING | File arrived from Phase 34 (#102) and is outside the 15-harness migration scope. Those children have no outbound network code (stdlib http.server only) and proxy vars are stripped from the inherited env by conftest, so nothing touches the network today; but the "guard applies to every subprocess" contract from 32-CONTEXT is not enforced for this file. Suggested follow-up: pass `env=child_env()` there (Phase 33's app-server/fixture work is the natural home). |
| `companion/test_*.py` legacy harnesses | n/a | Red when run as root (review IN-05) | INFO | Deferred: companion root-safety is Phase 33 scope (32-CONTEXT "Not in this phase"). CI runs non-root. |
| review IN-01..IN-04 | n/a | DNS guard is function-scoped (not during collection/session fixtures), `to_file()` log sharing, IP-literal naming, CI comment wording | INFO | Left open by design (out of fix scope); none defeats the connect guard. |

No `TBD`/`FIXME`/`XXX` debt markers in files changed by this phase (the two `"XXX"` hits are IATA fixture values).

### Human Verification Required

1. **CI on the post-review head.** Push and check PR #105's new run: `python3 --version` prints 3.14.x; test job (ruff, full suite with SKYPANE_REQUIRE_BROWSER=1, gate 93, attribution) green; firmware.yml `host-tests` green without the container.
2. **Playwright cache hit.** A second run shows a cache hit on `playwright-Linux-1.63.0-headless-shell` and skips the browser download.
3. **Deploy concurrency and stale-deploy guard on real Actions.** An in-flight deploy is never cancelled, a pending approval doesn't block the next push's tests, a superseded-by-code approval fails red, and a Markdown-only move still deploys. The `production` environment reviewer must also exist in repo Settings.

### Gaps Summary

No blocking gaps. Every roadmap success criterion and TST-01..TST-09 is backed by code I ran: 777 tests under pytest on CPython 3.14 as non-root with the gate at the measured 93 % floor, a complete ledger, guard self-tests, hash enforcement and firmware host tests. One warning: `stub-server/test_devices_registry.py` (from Phase 34) starts children without the child network guard. It is harmless today but should get `child_env()`. The remaining open items can only be checked on GitHub Actions, which is why the status is human_needed.

---

_Verified: 2026-09-24T07:01:35Z_
_Verifier: Claude (gsd-verifier)_
