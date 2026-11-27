# Phase 67 Baseline (the "before" record)

Measured 2026-11-27 on the tree below. Every number names the command that produced it, so the "after" record is taken the same way.

commit ace564b526ea6b86ab260bc2008e2b0305d4cbec

Code on this commit is identical to the last green main CI run (run 45993237674, code commit df9b781); the commits in between touch only `.planning/`.

before.ids sha256: 96b64df5aab477e27ed49cb8862b9dbb3bfa9a640c61955a2996fbdf7122b65c

Collected test ids: 17,598 (sorted with `LC_ALL=C sort`, one id per line). Regenerate the list from the commit with:

```
git checkout ace564b
server/.venv/bin/python -m pytest --collect-only -q --no-cov -p no:cacheprovider 2>/dev/null | grep '::' | LC_ALL=C sort > before.ids
sha256sum before.ids
```

Later plans compare the regenerated list with `comm -23 before.ids after.ids` (ids that vanished must be empty or explained by a rename).

## Environment

Local runs use Python 3.13; CI and production use Python 3.14. Browser tests run only in CI (no Chromium locally). Pull requests run with `SKYPANE_COVERAGE=off`; the coverage floor applies only on pushes to `main` and manual dispatch.

## Metrics

Scope: `git ls-files`, `.planning/` excluded unless stated. Date for all rows: 2026-11-27. Commit: ace564b. Python: 3.13.18 locally (CI rows: 3.14).

| Metric | Value | Command |
|--------|-------|---------|
| Python lines, tracked, outside `.planning` | 277,257 | `git ls-files '*.py' ':!.planning' \| xargs cat \| wc -l` |
| `server/` | 68,498 lines: 27,646 production in 82 modules, 40,852 tests in 108 files | `git ls-files 'server/*.py' \| xargs cat \| wc -l`, split on `/test_` in the path |
| `server/` flat top level | 34 production modules, 13,841 lines | `git ls-files 'server/*.py' \| awk -F/ 'NF==2'`, excluding `/test_` |
| `companion/` | 166,963 lines: 45,856 production in 166 modules, 121,107 tests in 380 files | same split, root `companion` |
| `stub-server/` | 11,146 lines: 2,666 production in 4 modules, 8,480 tests in 21 files | same split |
| `scripts/` | 6,629 lines: 5,324 production in 21 modules, 1,305 tests in 8 files | same split |
| `deploy/` | 6,765 lines: 940 production in 3 modules, 5,825 tests in 22 files | same split |
| `test-support/` | 7,887 lines: 5,364 production in 35 modules, 2,523 tests in 12 files | same split |
| `hardware/` | 6,886 lines: 4,387 production in 3 modules, 2,499 tests in 6 files | same split |
| CSS / JS in `companion/static` | 20,225 lines in 10 files / 12,727 lines in 34 files | `git ls-files 'companion/static/*.css' \| xargs cat \| wc -l` (same with `*.js`) |
| Tracked files / under `.planning` | 3,139 / 1,710 | `git ls-files \| wc -l`; `git ls-files .planning \| wc -l` |
| Twelve largest production files | `stub-server/byos_server.py` 1,891; `server/poll_cycle.py` 1,841; `server/fleet_db.py` 1,611; `companion/app.py` 1,446; `companion/pages/airlines_page.py` 1,375; `server/history_db.py` 1,342; `server/plane/illustrations.py` 1,253; `server/firmware_registry.py` 1,245; `companion/ui_base.py` 1,244; `server/plane/enrich.py` 1,162; `companion/pages/history_page.py` 1,121; `server/plane/detect.py` 1,091 | `git ls-files '*.py' ':!.planning' \| grep -v '/test_' \| grep -E '^(server\|companion\|stub-server)/' \| grep -v conftest \| xargs wc -l \| sort -rn` |
| Five largest functions, gate scope (max 80) | 76 `history_db.init_schema`; 70 `render/layout.build_canvas`; 66 `render/text.draw_previous_text_block`; 65 `calendar_rules.fetch_ics`; 65 `byos_server Handler._handle_display`; none over 80 | `server/.venv/bin/python scripts/check_function_size.py report server stub-server` |
| Five largest functions outside the gate | 89 `scripts/check_comment_history.py::_js_chunks`; 85 `adsb-test/analyze_samples.py::render_report`; 78 `companion/ui_shell.page_shell`; 77 `hardware/logtools.build_run_report`; 75 `companion/page_context.build_page_context` | `server/.venv/bin/python scripts/check_function_size.py report companion scripts adsb-test test-support deploy hardware` |
| mypy | no issues in 51 source files, of 251 production modules (server 82, stub-server 4, companion 165) | `server/.venv/bin/python -m mypy`; module count: `git ls-files 'server/*.py' 'stub-server/*.py' 'companion/*.py' \| grep -v '/test_' \| grep -v conftest \| wc -l` |
| Function annotation coverage (all parameters and the return annotated, `self`/`cls` excluded, production only) | server 589 of 1,141 (51.6 %); companion 18 of 1,856 (1.0 %); stub-server 0 of 129 (0.0 %); overall 607 of 3,126 (19.4 %) | an `ast` walk over `git ls-files '*.py'` in the three roots, skipping `test_*.py` and `conftest.py`; run from the scratchpad, not committed |
| ruff | All checks passed | `server/.venv/bin/python -m ruff check .` |
| Tests collected | 17,598 | `server/.venv/bin/python -m pytest --collect-only -q --no-cov -p no:cacheprovider` |
| Last green main CI run | run id 45993237674 (workflow CI, push, code commit df9b781) | `gh api repos/<owner>/<repo>/actions/runs?branch=main&status=success` |
| Executed / skipped (that run) | 17,598 executed, 0 failures, 0 errors, 0 skipped (browser shards 1084, 777, 796, 690, 719, 676; core shards 5938, 6918) | log of the final job "Lint, test, coverage, attribution", step `scripts/ci_gates.py totals` |
| Coverage TOTAL (that run) | `TOTAL 30488 1174 96%` (96.15 %); gate `fail_under = 93` | same job log, `grep -E '^TOTAL' coverage-report.txt` |
| Wall time per job (that run) | whole workflow 10 min 24 s; static checks 0:39; non-browser shards 3:43 and 3:30; browser shards 7:04, 7:24, 6:21, 6:54, 7:09 and 9:49 (shard 5 slowest); final combine job 0:29 | `gh api repos/<owner>/<repo>/actions/runs/45993237674/jobs` (`completed_at` minus `started_at`) |
| Local freeze and golden fast check | 115 passed in about 7.5 s | `SKYPANE_COVERAGE=off JOBS=4 ./scripts/run-all-tests.sh -- stub-server/test_phase47_freeze.py server/test_golden_render.py server/test_golden_giant_render.py` |
| Non-main remote branches | 40 | `gh api "repos/<owner>/<repo>/branches?per_page=100" --paginate --jq '.[].name' \| grep -vc '^main$'` |
| Gates today | `MIN_EXECUTED = 12821` (raised by plan 67-01), `MAX_SKIPPED = 0`; coverage floor 93; function size 80 over `server stub-server`; comment-history guard; ruff; mypy module list | `scripts/ci_gates.py`, `pyproject.toml`, CI workflow |

Local collection took about 3.4 s of pytest time (5.4 s wall) for the 17,598 ids.
