---
phase: 33-companion-tests-on-pytest-behaviour-over-source-text
verified: 2026-09-25T03:40:00Z
status: passed
score: 9/9 must-haves verified
re_verified: 2026-09-25T04:30:00Z (gap closed in 3e15556)
overrides_applied: 0
gaps:
  - truth: "The suite passes as root and writes nothing outside tmp_path (SC4, TST-13)"
    status: closed
    reason: >-
      Root safety holds: the 5 requires_non_root tests skip under euid 0, and the root run passes.
      But companion/test_config_page_04b.py passes the literal host path "/tmp" as state_dir in
      22 places, to config_page.render(...) and companion_app._resolve_flash_text(...). Rendering
      the Display scope reaches _theme_live_preview_html -> history_db.open_db("/tmp"), and
      history_db.connect() runs os.makedirs + sqlite3.connect + PRAGMA journal_mode=WAL + init_schema.
      That creates /tmp/history.db. Reproduced in a private mount namespace with an empty tmpfs on
      /tmp: one test,
      test_display_render_carries_three_section_intros_in_locked_order, leaves
      /tmp/history.db (36864 bytes) next to pytest-of-root. The whole module leaves the same file.
      33-33's proof missed it because this host already has a root-owned /tmp/history.db from
      2026-09-24 07:37. SQLite does not change that file's mtime when the schema already exists,
      and the proof only checked git status and /nonexistent. The test also reads whatever
      history that host file holds, so its rendered output depends on host state. Guard G6 only
      flags /nonexistent literals and tempfile.*, so it cannot catch a literal "/tmp" state_dir.
      The literal predates Phase 33 (it came from f5aef3d / a43601b in the legacy harness) and
      was carried over unchanged by the migration.
    artifacts:
      - path: "companion/test_config_page_04b.py"
        issue: "22 occurrences of \"state_dir\": \"/tmp\" / _resolve_flash_text(..., \"/tmp\"); production code opens /tmp/history.db"
      - path: "companion/test_suite_guards.py"
        issue: "G6 covers /nonexistent and tempfile.* only; a literal absolute host path used as a state dir passes the guard"
    missing:
      - "Replace every \"/tmp\" state_dir in companion/test_config_page_04b.py with str(tmp_path) (or None where no state is wanted)"
      - "Extend guard G6 (with a failing-sample self-test) to flag string literals that are absolute host paths such as /tmp, /var, /home or /root used as a path or state_dir, while still allowing hostile-input literals"
      - "Re-prove SC4 with a check that is not masked by pre-existing files. For example, run the companion suite under `unshare -m` with a fresh tmpfs on /tmp, or diff `find / -xdev -newer <marker>` against a marker, then confirm /tmp holds only pytest-of-*"
---

# Phase 33: Companion tests on pytest — behaviour over source text: Verification Report

**Phase Goal:** The companion suite runs under pytest with one shared app-server fixture. Tests assert behaviour or parsed DOM, never source text, comments, CSS text or `.planning/` files. `run_all_tests.py`, its hand list and every `EXPECTED_CHECK_COUNT` are retired.
**Verified:** 2026-09-25T03:40:00Z
**Status:** passed (initially gaps_found; the one gap is closed, see Gap Closure below)
**Re-verification:** No. This is the initial verification.

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
| --- | --- | --- | --- |
| 1 | All 24 former harnesses are pytest modules; `scripts/run-all-tests.sh` is a thin pytest wrapper (SC1, TST-14) | VERIFIED | The 15 server harnesses were migrated in Phase 32. The 9 companion legacy files are gone (`test_companion_app.py`, `test_config_page.py`, `test_status_pages.py`, `test_view_pages.py` and `test_browser_ux.py` are absent) or rewritten in place (`test_contrast_check.py`, `test_i18n.py`, `test_browser_ux_health_drawings.py` and `test_browser_ux_quiet_wake.py`). The split modules are `_01`..`_07`, `_04b` and `_05b`. `run-all-tests.sh` ends in `exec python -m pytest -n auto --cov ...`. |
| 2 | No legacy harness machinery remains (EXPECTED_CHECK_COUNT, check()/main() runners, shim, copied Harness/http_request/_NoRedirectHandler) | VERIFIED | `companion/test_legacy_harness_shim.py` and `run_all_tests.py` are absent. A grep for `LEGACY_COMPANION`, `collect_ignore` and `run_all_tests` in code, config and CI returns nothing. A repo-wide grep for `^EXPECTED_CHECK_COUNT`, `^def check(` and `^def main(` in `test_*.py` returns nothing. The only `_NoRedirectHandler`/`http_request` definitions are in the shared `test-support/companion_app_server.py`. The only other `main()` is a fake app inside a string literal in `test_app_server_fixture.py`. Guards G5, G8 and `test_no_legacy_runner_anywhere` enforce this. |
| 3 | One shared app-server fixture (TST-10) | VERIFIED | `companion/conftest.py` provides `app_server`, `make_app_server`, `module_app_server_factory` and `app_server_in_process`, all built on `companion_app_server.AppServer` / `InProcessAppServer`. Every state dir is under tmp_path/tmp_path_factory, and teardown kills the process group (proved by `test_app_server_fixture.py`). No test module starts `companion/app.py` itself. The remaining `subprocess.run` calls are sys.modules import-isolation probes run with `child_env()`. |
| 4 | Browser tests on pytest-playwright; a missing browser fails CI (SC2, TST-11) | VERIFIED | The `browser` fixture override calls `pytest.fail` when `SKYPANE_REQUIRE_BROWSER=1` or `CI=true`, and `pytest.skip` otherwise. `test_browser_policy.py::test_missing_browser_fails_in_ci` and `test_missing_browser_skips_locally` pass. `ci.yml` sets `SKYPANE_REQUIRE_BROWSER: "1"` and installs `--only-shell chromium`. `-m browser` collects 129 tests. The loopback route guard is on `new_context`. |
| 5 | No test reads `.planning/`/UI-SPEC or source text, asserts on a comment, or asserts on raw CSS text; the guard is strict (SC3, TST-12) | VERIFIED | `companion/test_suite_guards.py` scans every `companion/test_*.py` plus `conftest.py`, with only itself exempt, and has failing-sample self-tests. G11 has one allowlist entry, the stray-`*/` scan over served CSS, and a test proves that entry still matches. My greps found no `.planning` read outside docstrings, no `__doc__`, and no `inspect`/`getsource`/`linecache`. The file reads that exist are of state files under tmp_path, vendored PNG assets and `/proc`. Guard run: 134 passed. |
| 6 | The suite passes as root and writes nothing outside tmp_path (SC4, TST-13) | FAILED (partial) | Root half: VERIFIED. Two chmod tests sit under `@requires_non_root` in `test_companion_app_01.py`, the `/nonexistent` literal is removed (G6), and the caller's root run gives 2590 passed and 5 skipped. The tmp_path half FAILED. `test_config_page_04b.py` uses `state_dir: "/tmp"`, and production code creates `/tmp/history.db` there. This was reproduced under `unshare -m` with a tmpfs on `/tmp` (see gaps). The F-03 Playwright dirs are fixed: `find / -xdev -newermt` shows no new files in `/tmp` after commit 908b0ef. |
| 7 | Closing parity: every pre-migration check accounted for, 769 + 1250 = 2019, with the +1 explained (SC5, TST-15) | VERIFIED | `33-ledger-check.py --all` exits 0. All 9 harnesses are fully mapped: 1238 ported, 12 deleted, 0 pending. Every ported node id is validated against `pytest --collect-only`. The 12 deletions carry rubric codes S/P/R/C and reasons. `33-BASELINE/INDEX.md` traces the +1 over the audit's 2018 to commit `17d5bc7` (32-11). |
| 8 | Coverage at or above the pre-migration 93.35% | VERIFIED (recorded measurement) | 33-33 records a like-for-like figure (nobody, CPython 3.14, hash-locked venv) of 93.38%, against 93.35% for the pre-migration tree `d2c53a0` measured the same way. `pyproject.toml` `fail_under = 93` carries the derivation. The caller's root/3.11 run gives 93.24%, which is consistent with the 5 root-only skips (33-33 root: 93.26%). I did not re-measure the non-root figure (full run out of scope), and F-04 notes ±0.01 pp noise. |
| 9 | Docs and CI updated | VERIFIED | `.claude/CLAUDE.md` Tests/CI row on disk describes pytest-playwright, the shared fixtures and the guard, with no "shim until Phase 33". README "Tests" and CONTRIBUTING describe the wrapper, the browser policy, `companion/conftest.py` and the helpers. `ci.yml` runs `./scripts/run-all-tests.sh` with `SKYPANE_REQUIRE_BROWSER=1` and a cached headless shell. |

**Score:** 8/9 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
| --- | --- | --- | --- |
| `companion/conftest.py` | Shared fixtures, browser policy, route guard, driver TMPDIR | VERIFIED | Substantive and used by every companion module |
| `test-support/companion_app_server.py` | AppServer, no-redirect HTTP client, served_asset/served_stylesheet | VERIFIED | Imported by conftest and the test modules |
| `test-support/companion_markup.py` | Structural HTML/CSS helpers | VERIFIED | Unit-tested in `test-support/test_companion_markup.py` |
| `companion/test_suite_guards.py` | Strict TST-10/12/13/14 guard | VERIFIED (with G6 limitation) | G6 misses literal absolute host paths such as `"/tmp"` |
| `companion/test_browser_policy.py` | Missing-browser policy and F-03 proof | VERIFIED | Passes with `SKYPANE_REQUIRE_BROWSER=1` |
| `33-MIGRATION-LEDGER.md`, `33-ledger/*.md`, `33-ledger-check.py` | Parity ledger and checker | VERIFIED | Checker exits 0 with `--all` (no `--allow-pending`) |
| `scripts/run-all-tests.sh` | Thin pytest wrapper | VERIFIED | Single `exec pytest` |

### Key Link Verification

| From | To | Via | Status | Details |
| --- | --- | --- | --- | --- |
| companion tests | `companion/app.py` | `conftest` fixtures → `AppServer` → `child_env` subprocess | WIRED | No direct Popen of app.py in any test module |
| `browser` fixture | CI failure | `_browser_required()` → `pytest.fail` | WIRED | Proven by a subprocess test with an empty `PLAYWRIGHT_BROWSERS_PATH` |
| ledger ported rows | real node ids | `pytest --collect-only` inside the checker | WIRED | Checker run passed |
| CI | full suite | `ci.yml` → `run-all-tests.sh` → `pytest -n auto --cov` | WIRED | `SKYPANE_REQUIRE_BROWSER: "1"` set |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| --- | --- | --- | --- |
| Lint clean | `server/.venv/bin/ruff check .` | All checks passed | PASS |
| Ledger complete | `33-ledger-check.py --all` | 9/9 harnesses fully mapped, rc 0 | PASS |
| Guards, browser policy, test-support | `PLAYWRIGHT_BROWSERS_PATH=/tmp/skypane-pw-browsers SKYPANE_REQUIRE_BROWSER=1 pytest -q -n auto companion/test_suite_guards.py companion/test_browser_policy.py test-support` | 134 passed | PASS |
| Browser marker | `pytest --collect-only -q -m browser companion` | 129 collected | PASS |
| No writes outside tmp_path | `unshare -m sh -c 'mount -t tmpfs tmpfs /tmp && pytest companion/test_config_page_04b.py; ls /tmp'` | `/tmp/history.db` created | FAIL |

### Probe Execution

No probes were declared for this phase. Step 7c is not applicable.

### Requirements Coverage

| Requirement | Description | Status | Evidence |
| --- | --- | --- | --- |
| TST-10 | Migrated to pytest; one app-server fixture | SATISFIED | Truths 1 to 3 |
| TST-11 | pytest-playwright; missing browser fails in CI; xdist per test | SATISFIED | Truth 4 |
| TST-12 | Behaviour/parsed-DOM or deleted with a reason; no `.planning/`, no comments | SATISFIED | Truth 5, ledger deletions |
| TST-13 | Permission tests skip under euid 0; every path inside tmp_path | BLOCKED (partial) | The root half is met. The `"/tmp"` state_dir in `test_config_page_04b.py` writes `/tmp/history.db`. REQUIREMENTS.md marks this `[x]`, which is premature |
| TST-14 | run_all_tests.py and counts retired; thin wrapper | SATISFIED | Truths 1 and 2 |
| TST-15 | Closing parity; coverage ≥ pre-migration | SATISFIED | Truths 7 and 8 |

No orphaned requirements. All six IDs are claimed by the phase plans.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| --- | --- | --- | --- | --- |
| `companion/test_config_page_04b.py` | 163, 190, 213, 245, 251, 320, 344, 511, 587, 624, 746, 808, 842-844, 875-877, 893, 912, 934, 953, 964, 981 | Literal host path `"/tmp"` as state_dir | BLOCKER (for SC4) | Creates `/tmp/history.db` outside tmp_path, and reads host state into rendered output |
| `companion/test_companion_app_01.py` | 150-158 | Reads `deploy/skypane.env.example` as text | Info | A documentation contract, not production source. It is outside the TST-12 letter (no `.py/.html/.js/.css`), but it is a text-over-file assertion worth revisiting |
| — | — | TBD/FIXME/XXX markers | none found in the phase's test/support files | — |

### Human Verification Required

None.

### Gaps Summary

One gap, with one root cause. The migration carried the legacy harness's literal `"/tmp"` state dir into `companion/test_config_page_04b.py`. Rendering the Display scope with that context makes production code (`history_db.connect`) create `/tmp/history.db`, so the suite writes outside tmp_path. It also reads host state into what it renders. Neither the guard nor the 33-33 proof caught it. G6 only knows `/nonexistent` and `tempfile.*`, and the proof checked only git status and `/nonexistent`, on a host where `/tmp/history.db` already existed.

The fix is small: use `str(tmp_path)` in that module, extend G6 to flag absolute host paths, and re-prove SC4 on an empty `/tmp`. No later phase in the milestone covers this, so it is not deferred.

Everything else holds up against the code:
- no legacy runner remains, and there is one shared fixture;
- pytest-playwright is in place, with a missing browser failing in CI;
- the guard is strict, and the ledger accounts for all 2019 checks, with node ids validated by collection;
- coverage is recorded at or above 93.35%;
- the docs and CI are updated.

---

_Verified: 2026-09-25T03:40:00Z_
_Verifier: Claude (gsd-verifier)_

## Gap Closure (re-verification)

The SC4 / TST-13 gap is closed in `3e15556`:

- `companion/test_config_page_04b.py`: an autouse fixture gives every test a state dir under
  `tmp_path` (module-level contexts included); no `"/tmp"` literal remains.
- Guard G6 now flags a literal system temp dir (`/tmp`, `/var/tmp`, `/dev/shm`) or a path inside
  one, with positive and negative self-tests. Run over the previous version of the module it
  reports all 22 literals.
- Proof on an empty `/tmp`: in a private mount namespace (`unshare -m`, tmpfs on `/tmp`, the
  Chromium headless shell bind-mounted elsewhere), `SKYPANE_REQUIRE_BROWSER=1
  ./scripts/run-all-tests.sh` gives 2593 passed, 5 skipped (`requires_non_root`), 0 failed,
  coverage 93.24%; afterwards `/tmp` holds only `pytest-of-root` (pytest's basetemp), and
  `git status --porcelain` is empty.
- F-03 (Playwright driver temp dirs) was closed earlier in `908b0ef`; the same run confirms it.

TST-13 stays marked complete in REQUIREMENTS.md, now with this evidence.
