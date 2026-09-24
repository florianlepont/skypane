---
phase: 33
slug: companion-tests-on-pytest-behaviour-over-source-text
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-09-24
---

# Phase 33 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.1.1 + pytest-xdist 3.8.0 + pytest-cov 7.1.0 + pytest-socket 0.8.1 (Phase 32); pytest-playwright 0.9.0 added in Wave 0 |
| **Config file** | `pyproject.toml` (`[tool.pytest.ini_options]`, `[tool.coverage.*]`), `conftest.py`, new `companion/conftest.py` |
| **Quick run command** | `server/.venv/bin/python3 -m pytest -n auto companion/test_<module>.py` |
| **Full suite command** | `./scripts/run-all-tests.sh` (coverage gate 93 enforced with no extra args) |
| **Estimated runtime** | quick: < 120 s per module; full: see 33-RESEARCH.md wall-clock inventory |

---

## Sampling Rate

- **After every task commit:** quick run on the module(s) just migrated, plus `ruff check .`
- **After every plan:** the legacy shim still runs the not-yet-migrated harnesses. `pytest -n auto companion test-support` green, and `33-ledger-check.py <harness>` rc 0 for the harness just migrated
- **After every wave:** `./scripts/run-all-tests.sh` (full suite + coverage gate)
- **Before `/gsd:verify-work`:** full suite green as root AND as non-root (`runuser -u nobody`), `33-ledger-check.py --all` rc 0, `git status --porcelain` clean after the run
- **Max feedback latency:** 120 s for the quick run

---

## Per-Requirement Verification Map

| Requirement | Behavior | Test Type | Automated Command | File Exists | Status |
|-------------|----------|-----------|-------------------|-------------|--------|
| TST-10 | One shared app-server fixture; no copied `Harness` / `http_request` / `_NoRedirectHandler` | guard meta-test | `pytest companion/test_suite_guards.py` (no class Harness / def http_request / _NoRedirectHandler outside the shared support module) | ❌ W0 | ⬜ pending |
| TST-11 | A missing browser fails in CI and skips locally; browser tests run per-test under xdist | fixture behaviour | `CI=true PLAYWRIGHT_BROWSERS_PATH=<empty tmp> pytest -m browser` → non-zero; without CI → skipped with reason | ❌ W0 | ⬜ pending |
| TST-12 | No companion test reads `.planning/`, UI-SPEC, or production source/CSS as text; no comment assertions | guard meta-test (AST scan of companion/test_*.py) | `pytest companion/test_suite_guards.py` | ❌ W0 | ⬜ pending |
| TST-13 | Root-safe; nothing written outside tmp_path | full suite, both euids | `./scripts/run-all-tests.sh` as root and `runuser -u nobody -- ...`; `git status --porcelain` empty | ✅ `requires_non_root` marker exists | ⬜ pending |
| TST-14 | Shim, legacy lists, every `EXPECTED_CHECK_COUNT` retired | static | `grep -rn "EXPECTED_CHECK_COUNT\|LEGACY_COMPANION\|legacy_harness" companion test-support conftest.py pyproject.toml scripts` → empty | ✅ | ⬜ pending |
| TST-15 | Every pre-migration companion check accounted for; coverage ≥ 93 % pre-migration figure | ledger checker + coverage gate | `python3 .planning/phases/33-*/33-ledger-check.py --all` rc 0; `./scripts/run-all-tests.sh` passes `fail_under` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `33-ledger-check.py` (copy/extend of `32-ledger-check.py`: 9 companion harnesses, widened `SUMMARY_RE` for test_i18n) + `33-BASELINE/` captured before any rewrite (browser harnesses need a launchable Chromium)
- [ ] `companion/conftest.py` + shared support module: the `app_server` fixture, no-redirect HTTP client, login helper, all launched through `child_env()`
- [ ] pytest-playwright in `server/requirements-dev.in`, lock regenerated with `scripts/lock-deps.sh`; missing-browser policy fixture
- [ ] `companion/test_suite_guards.py`: TST-10/TST-12 guard meta-tests

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| CI on GitHub runs the browser tests with the cached headless shell and fails if the browser is missing | TST-11 | Only observable on Actions | Read the CI test job on PR #106: browser tests ran (not skipped), and the count matches the local run |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 120s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
