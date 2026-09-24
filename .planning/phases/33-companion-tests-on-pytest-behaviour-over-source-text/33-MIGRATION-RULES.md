# Phase 33 — Migration Rules (executor rubric for every harness-migration plan)

Every plan from 33-04 to 33-31 migrates a contiguous slice of one legacy companion harness.
Each of those plans references this file. It holds the mechanics and the rubric they share,
so the 28 plans cannot drift apart. The plans hold what differs: which harness, which slice,
which module, and which known hotspots.

Paths used below:
- `PD` = `.planning/phases/33-companion-tests-on-pytest-behaviour-over-source-text`
- `LEDGER` = `server/.venv/bin/python3 PD/33-ledger-check.py` (built by 33-01)

## 0. Pre-flight (every plan, before the first edit)

1. Coordinate with Phase 37 (CONTEXT "Coordination"). Run `git fetch origin main`. If
   `git rev-list --count HEAD..origin/main` is non-zero, run `git merge origin/main`. If both
   sides touched the same companion test file, resolve the conflict by keeping both behaviours.
   If the merge added or renamed a legacy `check(...)` call in any harness that is still legacy
   (it still contains `EXPECTED_CHECK_COUNT`):
   - record each new label with `LEDGER --add-check <harness> "<label>" --source <merge-commit-sha>`.
     The tool appends the label to `PD/33-BASELINE/<key>.addendum.txt` and appends a `pending`
     row to that harness's fragment.
   - a renamed check gets its OLD row marked `deleted`, with reason
     `renamed on main by <sha> to "<new label>"`, and its new label added with `--add-check`.
   - keep that harness's single `EXPECTED_CHECK_COUNT = N` line equal to its pending-row count.
2. Browser plans only (33-19..33-24): prove Chromium launches:
   `server/.venv/bin/python3 -c "from playwright.sync_api import sync_playwright as s; p=s().start(); p.chromium.launch().close(); p.stop()"`.
   If that fails (this sandbox's `/opt/pw-browsers` holds a stale r1194):
   - run `export PLAYWRIGHT_BROWSERS_PATH=/tmp/skypane-pw-browsers`
   - run `server/.venv/bin/python3 -m playwright install --only-shell chromium`
   - keep that export for every browser command in the plan

   Always run browser tests with `SKYPANE_REQUIRE_BROWSER=1`, so a launch failure is a FAIL
   and never a skip that reads as green (RESEARCH Pitfall 3).

## 1. Staged-migration mechanics (the suite stays green after every plan)

- The legacy harness stays at its original path, e.g. `companion/test_status_pages.py`. It is
  still a legacy harness, which means `test-support/skypane_test_support.py` still detects it:
  - it is one of the 9 `ORIGINAL_COMPANION_HARNESSES`;
  - it still contains a line starting `EXPECTED_CHECK_COUNT`.

  While both hold, `companion/test_legacy_harness_shim.py` keeps running it and
  `conftest.py`'s `collect_ignore` keeps pytest from importing it. There is no hand list to
  edit: the legacy set is derived from disk (33-03). Parallel plans never touch a shared list,
  so they never conflict.
- Slices are defined by ORIGINAL check()-call order in the legacy `main()`. Each plan takes
  the first remaining `check(...)` calls, from the plan's FIRST anchor label through its LAST
  anchor label. It moves them into its new module and deletes them, plus the closures only they
  use, from legacy `main()`. Setup that remaining checks still need stays. Line numbers in the
  plans are the original ones at baseline commit, for orientation only: after an earlier plan
  cuts code, find the slice by its anchor labels.
- Out-of-order exceptions are named explicitly in a plan, e.g. the root-unsafe checks pulled
  forward into 33-14 / 33-25.
- A legacy harness has exactly ONE authoritative line, `EXPECTED_CHECK_COUNT = <remaining>`,
  placed immediately above `def main():`. The chain's first plan deletes every historical
  `EXPECTED_CHECK_COUNT = ...` reassignment and the history comments around them, and adds
  that single line. Every later plan edits only that line. `LEDGER --allow-pending <harness>`
  fails unless `<remaining>` equals the fragment's pending-row count.
- The chain's LAST plan deletes the legacy file with `git rm`. `LEDGER <harness>` without
  `--allow-pending` must then exit 0: zero pending rows, and the legacy file gone.
- Single-plan harnesses (i18n, contrast_check, both small browser files) are rewritten IN
  PLACE at their original path. The legacy markers disappear in the same commit.

## 2. New-module conventions

- Staged harnesses: new modules are `companion/test_<stem>_NN.py`, where `<stem>` is the
  harness name without `test_`, e.g. `companion/test_status_pages_03.py`. `NN` is the plan's
  part number. A plan may split its part further into `test_<stem>_NNa.py` / `_NNb.py` when that
  helps xdist; list every file you create in the SUMMARY.
- Helpers shared by several parts of one harness live in `companion/test_<stem>_helpers.py`.
  That file sets `__test__ = False` at module level (the guard enforces this) and contains no
  test functions. Only the plans of that harness's chain edit it, and those run sequentially.
- Do NOT edit `companion/conftest.py`, `test-support/*`, `pyproject.toml` or `conftest.py`.
  They are owned by 33-02/33-03 and the closing plans, and parallel plans would collide there.
  If you are missing a shared capability, build it locally in the chain's helpers module and
  note it in the SUMMARY under "for the closing plan".
- One `test_` function per old check. The function name is derived from the label, and its
  docstring is the old label (Phase 32 convention, `32-PATTERNS.md`). A check that a loop
  emitted becomes `@pytest.mark.parametrize` with readable `ids`. Every parametrised id is its
  own ledger node id.
- Fixtures come from `companion/conftest.py` (33-02):
  - `app_server`: function-scoped, own state dir under `tmp_path`, no fake providers.
  - `make_app_server`: function-scoped factory taking `seed=`, `extra_args=` and
    `fake_providers=`.
  - `module_app_server_factory`: module-scoped factory, for a module's own seeded read-only
    server fixture.
  - `app_server_in_process`.
  - pytest-playwright's `page`, and the guarded `new_context(viewport=..., java_script_enabled=...)`
    factory for extra viewports or no-JS contexts. Never call `browser.new_context` / `sync_playwright`
    directly (guard G10): only the fixture installs the loopback-only route guard.

  Any test that POSTs or otherwise mutates state uses a function-scoped server. Read-only GETs
  may share a module-scoped server. No test may depend on another test having run first
  (xdist).
- HTTP and parsing come from `test-support/companion_app_server.py`:
  - `http_request`, `login`, `cookie_value`, `get`, `served_stylesheet`, `served_asset`.

  and from `test-support/companion_markup.py`:
  - `parse_html`, `Node.select` / `find_all` / `text`, `css_rules`, `declarations_for`,
    `keyframes`, `strip_js_comments_and_strings`.
- Tests migrated from `test_companion_app.py` whose legacy `Harness` ran with fake providers
  keep `fake_providers=True`. Tests from the other harnesses do not (RESEARCH Pitfall 4).
- Paths: write only under `tmp_path` / `tmp_path_factory`. Do not call `tempfile.mkdtemp` or
  `TemporaryDirectory`. No literal `/nonexistent...` string: a "missing path" is
  `tmp_path / "absent" / "nested"`, and a missing HTTP route is `/no-such-route`.
- Any `os.chmod` permission test carries `@requires_non_root` (imported from
  `skypane_test_support`, never redefined).
- English only in code, comments and docstrings (D-A3). New comments state behaviour and do
  not cite plan IDs.

## 3. TST-12 classification rubric (every check in the slice gets exactly ONE code)

| Code | What the legacy check does | Disposition |
|------|---------------------------|-------------|
| B | Calls a production function or makes an HTTP request, and asserts on its output | `ported`: only the plumbing changes (fixture in place of Harness, `http_request` from test-support) |
| D | Regex or substring test over rendered HTML | `ported`: use `parse_html(...)` when the assertion is about structure (element counts, nesting, attributes, order). A plain substring test is acceptable only for user-visible text in a rendered response |
| C | Opens `companion/static/style.css` (or any CSS) from disk, or does regex/`.index` slicing over CSS text | `ported`: fetch via `served_stylesheet(server)` and assert on `css_rules` / `declarations_for` (selector X has declaration Y, under at-rule Z). In a browser module, use computed style through `_computed_paint` / `_resolved_property` instead. If the check asserted on a CSS COMMENT (header accent list, "was:" notes, plan IDs), it is `deleted` with reason `C: asserted a stylesheet comment; no rendered behaviour` |
| J | Opens a served JS asset (`companion/static/*.js`) as text | `ported`: fetch it over HTTP with `served_asset(server, "/static/x.js")`, run `strip_js_comments_and_strings` on it, then assert the delivery contract (ES5-only syntax, no `innerHTML` sink, a named export exists). Better still, prove it in a browser module. Assertions on JS comments are `deleted`, reason `J: asserted a JS comment` |
| S | Opens a production `.py`/`.html` source file, or calls `inspect.getsource` / `ast.parse` / `tokenize` on production code | Rewrite as behaviour when there is an observable consequence. For "module X never imports Y": import X in a fresh `subprocess` built with `child_env()` and assert that `Y` is not in `sys.modules`. For "retired symbol gone": assert `not hasattr(module, "NAME")`. For "no form element in page": render and parse. With no observable consequence, it is `deleted` with reason `S: asserted source text (<what>); no behaviour` |
| P | Opens `.planning/...` or a UI-SPEC file | When the spec pins user-visible copy: rewrite so the rendered page is asserted against the literal string, copied into the test as a literal constant. Otherwise `deleted`, reason `P: asserted planning-document prose; no behaviour` |
| R | Self-referential: opens the test file itself, e.g. `_ASPECT_REPIN_LEDGER` | `deleted`, reason `R: self-referential plan-history bookkeeping; opens a .py file to grep text` |
| T | Root-unsafe (`os.chmod`, or a literal host path production code may `mkdir`) | `ported` with `@requires_non_root` and/or a `tmp_path` absent path. A `FAIL` baseline row still maps to the new node id |

- Ledger reason format for `deleted`: `<code>: <why there is no behaviour / what covers it now>`.
  Every deletion names its code.
- Several old checks may map to one node id when they are consolidated. When one old check
  splits into several tests, the ledger row points at the primary node id and the SUMMARY lists
  the others.
- A production fix is allowed ONLY when a rewritten behaviour test exposes a real bug. Keep it
  minimal and record it in the SUMMARY under "Deviations" (CONTEXT "Not in this phase").

## 4. Ledger fragment

- `PD/33-ledger/<key>.md` (key = `companion__test_<stem>`) was scaffolded by 33-01 with every
  row set to `pending`. Flip only your slice's rows:
  - `ported`: target is the full node id, e.g. `companion/test_status_pages_03.py::test_x`, or
    `...::test_y[id]` for a parametrised test. Browser node ids carry pytest-playwright's
    `[chromium]` suffix exactly as `pytest --collect-only -q` prints it.
  - `deleted`: target is the reason.
- Add a short `### Part NN (plan 33-XX)` note under the table:
  - the counts per rubric code;
  - the new module(s) created.

## 5. Per-plan verification (all must pass before the commit)

1. `server/.venv/bin/python3 -m pytest -n auto -p no:cacheprovider <new module(s)>`. For browser
   modules, run it with `SKYPANE_REQUIRE_BROWSER=1`.
2. `server/.venv/bin/python3 -m pytest -p no:cacheprovider companion/test_legacy_harness_shim.py -k <stem>`
   passes (the shrunk legacy harness is still green). This step does not apply once the legacy
   file is deleted.
3. `server/.venv/bin/python3 -m pytest -p no:cacheprovider companion/test_suite_guards.py test-support` passes.
   The TST-10/12/13/14 guard scans the new modules; they are not legacy.
4. `LEDGER --allow-pending companion/test_<stem>.py` exits 0 (chain-final plans: without
   `--allow-pending`).
5. `server/.venv/bin/ruff check <this plan's files>` exits 0. The whole tree is linted by the closing plans and CI; a sibling plan in the same wave may be mid-edit elsewhere.
6. `git status --porcelain -- <this plan's files>` is clean after the commit. Parallel plans in the same wave share the working tree, so ignore other plans' in-flight files. No stray files appear outside
   `tmp_path`, and nothing new exists under `/nonexistent` (`ls /nonexistent 2>/dev/null`
   lists nothing that was not there before).

## 6. Commit and push

- Stage ONLY this plan's files with `git add <paths>`, never `git add -A` / `git add .`, because sibling plans may be editing other files in the same working tree.
- If the guard or `--collect-only` reports a problem only in a file another in-flight plan owns, it is not this plan's failure. Re-run scoped with `-k <stem>`.
- One commit per task is fine. The plan's final commit carries the new modules, the shrunk
  legacy file and the fragment update together, so the suite is green at that commit.
- Push with `git push origin claude/phase-33` after the plan's last commit.
