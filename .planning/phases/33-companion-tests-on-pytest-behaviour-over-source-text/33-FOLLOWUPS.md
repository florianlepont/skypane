# Phase 33 follow-ups (orchestrator-tracked)

Items found while executing the migration plans that the closing plans
(33-32 guard tightening, 33-33 closing parity/verification) must resolve.

## F-01: text-level assertions over the served stylesheet

**Status: RESOLVED in 33-32, commit `807e9b2`.** Every regex, `in` test and
str search over served stylesheet text in `companion/test_*.py` and the
`*_helpers.py` modules was rewritten over `companion_markup`:
`test_config_page_02.py`, `test_config_page_03.py`, `test_companion_app_02.py`,
`test_companion_app_03.py` (the `@supports` count), `test_companion_app_04.py`
(the motion budget and its brace-matching helper) and `test_view_pages_03.py`.
`companion_markup` gained `rule_indices()` (source order) and
`at_rule_blocks()` (countable at-rule blocks), each unit-tested. Guard rule
G11 in `companion/test_suite_guards.py` follows served stylesheet text
through assignments, fixtures, string transforms, slices and local helpers,
and flags any regex, `in` test or str search over it; failing-sample
self-tests prove it. The one allowlisted function is
`test_status_pages_07.py::test_style_css_carries_no_stray_comment_terminator`,
which must scan raw served characters, and a test fails if that entry ever
stops matching a real raw-text scan. The comment-only sub-clauses of ledger
rows 112-113 (config_page) were dropped under rubric C; every node id is
unchanged.

Original finding:

33-CONTEXT.md (TST-12) says CSS checks parse the served stylesheet
structurally, not with a regex over its text. Some migrated checks fetch
`style.css` over HTTP (no disk read, so guard G-rules pass) but then assert
with `re.search` / `str.index` / substring tests on the raw served text,
following 33-10's precedent. Known so far:

- `companion/test_config_page_02.py` (33-10), `companion/test_config_page_03.py`
  (33-11, ~9 large checks per its SUMMARY), `companion/test_view_pages_03.py`
  and `companion/test_companion_app_02.py` (substring/regex hits over served
  CSS/JS text).

Resolution in 33-32: sweep every migrated module for regex/index/substring
assertions over served CSS text; rewrite each over
`companion_markup.css_rules()` / `declarations_for()` / `rules_with_selector()`
(or a computed-style browser assertion). Anything that genuinely cannot be
expressed structurally is listed in the ledger with its reason. Then extend
`companion/test_suite_guards.py` with a rule that flags regex/index/substring
use on a value obtained from `served_stylesheet()`.

Served JS is different: without a JS engine, some contracts (e.g. "no
setTimeout", "ES5 only") are only expressible over the comment-stripped
served text; those stay, but must go through `strip_js_*` helpers, never raw
source on disk.

## F-02: gsd-sdk STATE.md mutations

**Status: OPEN (tooling, outside Phase 33's scope).** Seen again in 33-33 and
hand-corrected before commit.

Every `gsd-sdk query state.*` mutation resets frontmatter `percent` and can
rewrite the demoted historical block in STATE.md. Executors hand-correct it.
Not a phase-33 code issue; report upstream (get-shit-done-cc
`sdk/src/query/state-mutation.ts`).

## F-03: Playwright's driver leaves empty temp dirs in /tmp

**Status: OPEN (found in 33-33; predates Phase 33).** Every full run leaves two
empty `playwright-artifacts-*` dirs and two empty `playwright_chromiumdev_profile-*`
dirs in the system temp dir, owned by whichever user ran the suite. These are
Playwright's own per-launch temp dirs, created by the Node driver under its
`os.tmpdir()`. No test chooses these paths, and nothing under the repo,
`/nonexistent` or any other test-chosen path is touched. Evidence from 33-33:

- 20 such dirs from this plan's 5 full runs, all empty. Their mtimes fall near
  session end, which suggests the driver empties them and then exits before
  removing the dir itself on some xdist workers.
- The host already held 230 of them, going back to 2026-09-24T07. That is before
  33-01's baseline capture and before any pytest-playwright code, so the legacy
  browser harnesses leaked the same way.
- A single browser module run with `-n 0` and `-n 2` leaked nothing, so the leak is
  timing-dependent.

Fixing it needs the driver's `TMPDIR` pointed at a `tmp_path_factory` dir when
`sync_playwright().start()` runs. That means overriding pytest-playwright's
session `playwright` fixture, which guard G10 forbids in companion test files.
`browser_type.launch(downloads_path=...)` would relocate only the artifacts dir,
not the Chromium profile. The fix is a test-infrastructure design change,
probably a sanctioned fixture in `test-support/` plus a G10 allowance. Candidate:
Phase 36 (test hygiene) or a quick task.

## F-04: one companion/app.py line's coverage is racy under full-suite load

**Status: OPEN (measurement noise, +/-1 statement).** `companion/app.py`'s
`return None` after `require_session()` on the manual-resolution delete route
runs after the 303 response has already been written. In
`companion/test_companion_app_05.py::test_manual_resolve_and_delete_routes_require_auth_and_write_nothing`,
that unauthenticated POST is the test's last request, so teardown's SIGTERM can
reach the child before the daemon request thread executes that line.
Coverage's `sigterm` handler then saves without it.

- Covered in 15/15 isolated runs, and in 2 of the 3 full non-root runs in 33-33.
- Instrumenting `stop()` showed no SIGKILL fallback: all 147 stops took 34 ms or
  less, with rc -15.
- Effect: TOTAL moves by 0.01 pp (93.38 vs 93.39).
- Possible fix: a graceful shutdown path in the fixture's `stop()` that lets
  the child finish in-flight request threads before coverage saves. A later
  request in the same test would only narrow the window, not close it.

