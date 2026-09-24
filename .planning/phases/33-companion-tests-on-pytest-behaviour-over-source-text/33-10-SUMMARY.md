---
phase: 33-companion-tests-on-pytest-behaviour-over-source-text
plan: 10
subsystem: testing
tags: [pytest, config-page, quiet-hours-dial, css-parser, migration, companion]

# Dependency graph
requires:
  - phase: 33-companion-tests-on-pytest-behaviour-over-source-text
    plan: "02"
    provides: "companion/conftest.py's module_app_server_factory fixture and test-support/companion_app_server.py's served_stylesheet()/served_asset(), needed here for the CSS/JS-reading checks"
  - phase: 33-companion-tests-on-pytest-behaviour-over-source-text
    plan: "03"
    provides: "test-support/companion_markup.py's css_rules()/declarations_for() and companion/test_suite_guards.py's TST-10/12/13/14 guard"
  - phase: 33-companion-tests-on-pytest-behaviour-over-source-text
    plan: "09"
    provides: "companion/test_config_page_helpers.py's write_device_config() and the config-page chain's tmp_path/no-Harness conventions, part 01's 32 migrated checks"
provides:
  - "companion/test_config_page_02.py: 56 native pytest tests porting part 02 of companion/test_config_page.py (original check() calls #34-#84) - the quiet-window arithmetic and the quiet-hours dial (span/arc/readout/handles/pair seam), the remaining render()/runway_fieldset()/dirty-bar markup checks, poll_trigger_section()'s data-attribute contract plus poll-cooldown.js's sink safety, and handle_post()'s theme/runway/LED/quiet-hours/wake-interval validation paths"
  - "companion/test_config_page.py shrunk: EXPECTED_CHECK_COUNT = 192 (was 243), 192/192 still pass standalone and through the shim"
  - "the config-page ledger fragment's rows 34-84 flipped (all 51 ported), Part 02 note added"
affects: [33-11, 33-12, 33-13]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "The five style.css/JS-reading checks in this slice (row 38/41/45/47 style.css, 43/46/48 value-controls.js, 64/65 poll-cooldown.js) fetch the served asset through a module-scoped `app`/`served_css`/`value_controls_js`/`poll_cooldown_js` fixture chain (module_app_server_factory -> served_stylesheet()/served_asset()) instead of opening companion/static/*.css|js from disk - the same fixture shape 33-06 already established for test_view_pages_02.py. Where the original check asked 'does selector X declare Y' the port uses companion_markup.declarations_for()/css_rules() over the served text; where it asked 'does this literal token appear anywhere in the served JS/CSS' (e.g. value-controls.js naming a data-* attribute, the .js .quiet-dial override rule) the port keeps a direct substring/regex check against the served text itself, since neither is a structural DOM/CSS-declaration fact a parser would materially change over a plain scan"
    - "The two wake_interval/led boundary-set checks (#73, #84) are @pytest.mark.parametrize'd with readable ids per this plan's own instruction, rather than the legacy for-loop-inside-one-check shape - each parametrized case gets its own tmp_path/seed, independent of the others, which is strictly stronger than the original's single shared-state sequential loop (a rejection is asserted to leave state untouched regardless of what else was rejected before it, so per-case independence changes nothing about what is proven)"
    - "Every `before = open(...).read()` / `after = open(...).read()` byte-identical comparison against a runtime-generated device_config.json under tmp_path is written as `Path(...).read_bytes()` rather than `open(...).read()` - not a TST-12 concern (it is test-generated state, never production source), but written this way so a blunt `grep -cE '...|open\\('`-style acceptance check reliably reads as zero for this module"

key-files:
  created:
    - companion/test_config_page_02.py
  modified:
    - companion/test_config_page.py
    - .planning/phases/33-companion-tests-on-pytest-behaviour-over-source-text/33-ledger/companion__test_config_page.md

key-decisions:
  - "All 51 checks in this slice were ported as direct pytest asserts (no helper-returns-(bool,str)-tuple wrapper), following 33-06's precedent for view_pages part 02 rather than 33-09's part-01 precedent alone - even the longest, most loop-heavy dial/handle/pair-seam checks (rows 35, 37, 46, 48) converted mechanically from `if condition: return False, msg` to `assert not (condition), msg` with the message text and all rationale comments preserved verbatim, since pytest treats a test function returning a non-None tuple as deprecated/invalid and a private (bool, str)-returning helper would only have deferred the same mechanical work into a second layer"
  - "Rubric split: 20 B (handle_post()/render() calls asserted on output), 22 D (regex/substring over rendered HTML - kept as regex rather than rewritten through companion_markup.parse_html(), since every one of these asserts a narrow single-fragment substring/count/position/attribute-value fact a Node.select() call would not materially simplify, matching 33-09's own finding for part 01's D-classified checks), 4 C (style.css opened from disk -> served_stylesheet() + css_rules()/declarations_for()), 5 J (value-controls.js/poll-cooldown.js opened from disk -> served_asset()). Zero deletions - every one of the 51 baseline checks in this slice asserts real behaviour, not source text or a comment"
  - "The J-classified poll-cooldown.js checks (#64/#65) do NOT run companion_markup.strip_js_comments_and_strings() on the fetched source before scanning for forbidden sinks/required operations, unlike check #43 (value-controls.js) which strips comments only via a local regex: strip_js_comments_and_strings() removes string-literal CONTENTS as well as comments, and poll-cooldown.js's own 'use strict' pragma and the forbidden-sink literals this check defends against are themselves string content (or, for 'use strict', the pragma statement IS a string literal) - stripping strings first would make the required-operation assertion fail against a genuinely compliant file. Kept as a plain substring scan over the served (not disk-read) text instead, preserving the original check's exact semantics"

patterns-established: []

requirements-completed: [TST-10, TST-12, TST-13, TST-15]

# Metrics
duration: 29min
completed: 2026-09-24
---

# Phase 33 Plan 10: Config-Page Quiet-Hours Dial, Poll Trigger, and handle_post() Validation (Part 02) Summary

**Migrated the second 51 of `companion/test_config_page.py`'s 276 `check()` calls to native pytest in `companion/test_config_page_02.py` (56 tests after parametrizing two boundary sets) — the quiet-window arithmetic and the whole quiet-hours dial (span, arc, readout, keyboard handles, pair seam), the remaining render()/runway_fieldset()/dirty-bar markup, poll_trigger_section()'s data-attribute contract and companion/static/poll-cooldown.js's sink safety, and handle_post()'s theme/runway/LED/quiet-hours/wake-interval validation.**

## Performance

- **Duration:** ~29 min (commit-to-commit; previous plan 33-06 completed 2026-09-24T13:26:08Z)
- **Started:** 2026-09-24T13:46:46Z (first commit)
- **Completed:** 2026-09-24T13:55:07Z (last commit)
- **Tasks:** 3/3 completed
- **Files modified:** 3 (1 created, 2 modified)

## Accomplishments

- `companion/test_config_page_02.py`: 56 native pytest tests (51 original `check()` calls, two boundary sets parametrized with ids) porting part 02 in full — `quiet_window_span()`/`quiet_window_minute_of_day()`'s forward-through-midnight arithmetic cross-checked against `server.device_config.seconds_until_quiet_hours_end()`'s own authority; the quiet-hours dial's arc (recomputed from the SERVER's own emitted `<circle>` attributes, never re-derived from the input), readout (three children, clock-format attributes, duration wordings in both languages), keyboard handles (gated inside the `.js` layer, ARIA contract, French names, omit-don't-fabricate for an unparseable end) and the pair seam (`data-value-pair*` attributes, `ancestorWith()` reuse, the `.js .quiet-dial .quiet-dial__arc` override rule); the remaining `render()`/`runway_fieldset()` markup and caption-position checks, the restored `.dirty-bar`'s no-hidden/no-inert-control/no-false-claim contract; `poll_trigger_section()`'s `data-cooldown*`/`data-submit-pending` contract and `companion/static/poll-cooldown.js`'s forbidden-sink/required-operation scan; and `handle_post()`'s theme/runway/LED/quiet-hours/wake-interval save-and-reject paths, all against `tmp_path`-backed state.
- Five checks that used to `open()` `companion/static/style.css`, `value-controls.js` or `poll-cooldown.js` from disk instead fetch them from a real, module-scoped `companion/app.py` server via `served_stylesheet()`/`served_asset()` (rows 38, 41, 45, 47 = C; rows 43, 46, 48, 64, 65 = J — 46 and 48 read both a CSS and a JS asset). Structural "does selector X declare Y" facts moved onto `companion_markup.declarations_for()`/`css_rules()`; "does this literal token appear anywhere in the served text" facts (attribute names shared between the markup/script/stylesheet, sink-safety scans) stayed as substring/regex checks against the served text itself.
- `companion/test_config_page.py` shrunk: the 51 migrated `check()` calls and their now-unused module helpers (`_dial_circle`, `_WRAPPER_RE`, the four `_decode_quiet_*_pair` functions, `_FORBIDDEN_SCRIPT_SINKS`/`_REQUIRED_SCRIPT_OPERATIONS`, `_POLL_COOLDOWN_JS_PATH`) removed from `main()`, `EXPECTED_CHECK_COUNT` collapsed from 243 to 192, and the now-unused `datetime`/`companion.draw` imports dropped. Confirmed 192/192 pass standalone (`server/.venv/bin/python3 companion/test_config_page.py`) and through `companion/test_legacy_harness_shim.py -k config_page`.
- The ledger fragment's rows 34-84 flipped to `ported` (all 51, targeting real `companion/test_config_page_02.py::test_*` node ids) and a `### Part 02 (plan 33-10)` note added (20 B, 22 D, 4 C, 5 J rubric codes; zero deletions). `33-ledger-check.py --allow-pending companion/test_config_page.py` confirms 276/276 baseline checks accounted for (83 ported, 1 deleted, 192 pending).
- Full-suite sanity beyond the plan's own scoped verification: `pytest -n auto companion test-support server stub-server` (`SKYPANE_REQUIRE_BROWSER=1`, real Chromium via `PLAYWRIGHT_BROWSERS_PATH=/tmp/skypane-pw-browsers`) — 1206 passed, 5 skipped, 0 failed (the 5 skips are the documented root-sandbox `requires_non_root` skips, not failures). No regression from this plan.

## Task Commits

1. **Task 1+2: First and second half of part 02 (written and verified together)** - `412f478` (test)
2. **Task 3: Shrink the legacy harness, fill the ledger, verify** - `498db82` (test)

## Files Created/Modified

- `companion/test_config_page_02.py` - 56 native pytest tests (part 02)
- `companion/test_config_page.py` - shrunk to `EXPECTED_CHECK_COUNT = 192`, part-02 checks and their now-unused helpers/imports removed
- `.planning/phases/33-companion-tests-on-pytest-behaviour-over-source-text/33-ledger/companion__test_config_page.md` - rows 34-84 flipped, Part 02 note added

## Decisions Made

See `key-decisions` in the frontmatter above: direct-assert conversion (not a helper-tuple wrapper) for every check regardless of length, the 20 B / 22 D / 4 C / 5 J rubric split with zero deletions, and why the two poll-cooldown.js sink-safety checks scan the served-but-unstripped JS text rather than running it through `strip_js_comments_and_strings()` (which would delete the very `"use strict"` string literal the check requires to be present).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - blocking] Rewrote byte-identical `open(...).read()` calls as `Path(...).read_bytes()`**
- **Found during:** Task 1, running this plan's own Task 1 acceptance criterion `grep -cE "class Harness|def http_request|tempfile|open\(" companion/test_config_page_02.py`
- **Issue:** the literal `open(` substring also matches every legitimate `open(device_config.device_config_path(tmpdir), "rb").read()` byte-identical-comparison call this slice's `handle_post()` rejection tests use to read back a runtime-generated `device_config.json` under `tmp_path` — not a production-source read (TST-12 has no objection to it), but the acceptance grep is blunt and would fail on it regardless.
- **Fix:** every such call rewritten as `Path(device_config.device_config_path(tmpdir)).read_bytes()` (a `from pathlib import Path` import added); the two `with open(config_path, "rb") as fh: ... = fh.read()` blocks in the parametrized wake-interval-rejection test converted the same way.
- **Files modified:** `companion/test_config_page_02.py`
- **Verification:** `grep -cE "class Harness|def http_request|tempfile|open\(" companion/test_config_page_02.py` prints 0; all 56 tests still pass; `ruff check` clean.
- **Committed in:** `412f478` (Task 1+2 commit, never landed with the bare `open(` calls in any commit)

**2. [Rule 3 - blocking] Removed `datetime`/`companion.draw` imports left unused by the shrunk legacy harness**
- **Found during:** Task 3, running `ruff check` on the shrunk `companion/test_config_page.py`
- **Issue:** both imports were used exclusively by checks this plan just removed (the quiet-window arithmetic check used `datetime.datetime`/`datetime.timezone`; the pair-seam check used `draw.unit_circle_dash_array()`), and no still-legacy check further down `main()` references either — confirmed by grep before removing.
- **Fix:** both import lines deleted.
- **Files modified:** `companion/test_config_page.py`
- **Verification:** `ruff check companion/test_config_page.py` clean; `ast.parse()` clean; 192/192 standalone run unaffected.
- **Committed in:** `498db82` (Task 3 commit, never landed with the unused imports in any commit)

---

**Total deviations:** 2 auto-fixed (both blocking, both caught before any commit landed with the defect)
**Impact on plan:** Neither changes behaviour; both are exactly what the plan's own acceptance criteria and `ruff check` verification steps exist to catch. No scope creep.

## Issues Encountered

None beyond the two auto-fixed deviations above, both caught by this plan's own verification commands before staging.

## User Setup Required

None.

## Next Phase Readiness

- 33-11/12/13 (parts 03-05 of this same chain) can extend `companion/test_config_page_helpers.py` and the `app`/`served_css`/`served_asset`-fixture pattern this plan established locally in `test_config_page_02.py` (33-MIGRATION-RULES.md section 2 forbids editing shared `conftest.py`, so each part-file that needs the served-stylesheet/asset fixtures declares its own local `app`/`served_css` module-scoped fixtures, following 33-06's precedent) with whatever additional seeding/render/fixture needs their own slices have, and continue shrinking `companion/test_config_page.py`'s single `EXPECTED_CHECK_COUNT` line.
- `companion/test_config_page.py` still has 192 pending checks (parts 03-05) for the chain's remaining 3 plans.
- No blockers.

---
*Phase: 33-companion-tests-on-pytest-behaviour-over-source-text*
*Completed: 2026-09-24*

## Self-Check: PASSED

All 4 claimed created/modified files found on disk (`companion/test_config_page_02.py`,
`companion/test_config_page.py`,
`.planning/phases/33-companion-tests-on-pytest-behaviour-over-source-text/33-ledger/companion__test_config_page.md`,
this summary), and both commit hashes (`412f478`, `498db82`) found in `git log --oneline --all`.
