---
phase: 35-comment-purge-in-english-and-dead-code
plan: 18
subsystem: testing
tags: [javascript, comment-purge, ci-guard, companion-static, es5]

requires:
  - phase: 35-comment-purge-in-english-and-dead-code
    provides: "the check_comment_history.py CLI (check/ratio/same-code), the pending-list ratchet, and the group-close procedure established by plans 35-01/35-06/35-17"
provides:
  - "companion/static/*.js (17 files) with 0 comment-history guard hits and code unchanged"
  - "group 6 closed: companion/static/*.js removed from scripts/comment-history-pending.txt"
  - "35-COMMENT-RATIO.md group-6 section with per-file before/after ratios and shipped-JS-byte totals"
  - "two pre-existing companion test bugs fixed (rhetoric-only assertions, a plan-id-string region boundary) that the purge exposed"
affects: [35-19-close-phase, HYG-02]

tech-stack:
  added: []
  patterns:
    - "JS file-header cap (~8 lines): what the script does, which page(s)/attributes it binds to, progressive-enhancement contract"
    - "Function/inline comment caps (~5-6 lines, up to 12 for genuine contract content), applied uniformly across the group"

key-files:
  created: []
  modified:
    - companion/static/battery-trend.js
    - companion/static/confirm-submit.js
    - companion/static/copy-button.js
    - companion/static/dirty-state.js
    - companion/static/flash-cleanup.js
    - companion/static/flight-rows.js
    - companion/static/freshness.js
    - companion/static/list-filter.js
    - companion/static/login-card.js
    - companion/static/nav-dropdown.js
    - companion/static/panel-lookup.js
    - companion/static/poll-cooldown.js
    - companion/static/quick-switch.js
    - companion/static/relative-time.js
    - companion/static/submit-guard.js
    - companion/static/theme-preview.js
    - companion/static/value-controls.js
    - scripts/comment-history-pending.txt
    - .planning/phases/35-comment-purge-in-english-and-dead-code/35-COMMENT-RATIO.md
    - companion/test_config_page_03.py
    - companion/test_status_pages_07.py

key-decisions:
  - "Purged every companion/static/*.js file bottom-to-top by comment block, never touching code tokens, so same-code's JS token-stream comparison (comments stripped) passes with no --allow for all 17 files against base ebe66f9."
  - "Two files (confirm-submit.js, flash-cleanup.js) stay just above the ~35% review-trigger guideline (37.0%, 36.1%) because their fixed-cost ≤8-line header dominates a 36-46 line file; documented with justifications in 35-COMMENT-RATIO.md rather than cut further, since the remaining content is the security/DOM-contract note purge_rules require to survive."
  - "Fixed two pre-existing companion test bugs the purge exposed rather than reintroducing banned rhetoric into production comments: dirty-state.js's test required the literal strings 'never introduce a network call' and 'ONE NAMED EXCEPTION' verbatim in the header (upper-case emphasis rhetoric this phase's own purge_rules ban); freshness.js's test used the plan-id string '23-05-PLAN.md Task 2' as a text-search region-boundary marker, which check_comment_history.py itself flags as a history reference."

requirements-completed: [HYG-02]

duration: 50min
completed: 2026-09-25
---

# Phase 35 Plan 18: Companion static JS comment purge (group 6 close) Summary

**Purged history/rhetoric from all 17 companion/static/*.js files (57% → 31% average comment ratio, 340 → 0 history hits) and closed group 6, with code proven byte-for-byte unchanged by the JS token-stream same-code check.**

## Performance

- **Duration:** ~50 min
- **Completed:** 2026-09-25T22:33Z
- **Tasks:** 3 (all `<task type="auto">`)
- **Files modified:** 21 (17 JS files, the pending-list ratchet, the ratio doc, 2 test files)

## Accomplishments

- All 17 `companion/static/*.js` files purged: file headers rewritten to ≤8 lines (what the script does, which page(s)/attributes it binds to, progressive-enhancement contract), function/inline comments compressed to the purge_bar caps, every history ID/rhetoric/French-quote removed.
- `same-code --base ebe66f9` (the group base) exits 0 with **no `--allow`** for every file — the JS/CSS token-stream comparator (comments stripped, `.split()` on whitespace) confirms the code itself never changed.
- `check --paths` reports 0 history hits across the group; `node --check` passes for all 17 files.
- Group 6 closed: the 17 paths removed from `scripts/comment-history-pending.txt` (only `companion/static/style.css`, group 7's own scope, remains under `companion/static/`); `CLI check` (no args) exits 0.
- `35-COMMENT-RATIO.md` carries a Group 6 section: per-file before/after lines/ratio/hits, a group-total row matching `35-BASELINE/INDEX.md`'s group-6 row (17 files, 6518 lines, 57%, 340 hits) exactly, the two >35%-guideline files with justifications, and the shipped-JS-bytes totals (raw 303536 → 153483 bytes; gzip 112307 → 55831 bytes).
- Full suite green: `SKYPANE_REQUIRE_BROWSER=1 ./scripts/run-all-tests.sh` — 2691 passed, 5 skipped (root-only), coverage 93.20% (gate 93.0%). `ruff check .` clean.

## Task Commits

Each task's files were committed in 2-3-file groups (interruption resilience), and Task 3's own deviations were committed separately:

1. **Task 1: Purge the four heaviest scripts** - `47e36ad` (freshness.js, value-controls.js), `ede326f` (dirty-state.js, panel-lookup.js)
2. **Task 2: Purge the remaining scripts and run the browser tests** - `db7d7c1` (theme-preview.js, quick-switch.js, relative-time.js), `75e6acd` (flight-rows.js, list-filter.js), `a2c21dd` (nav-dropdown.js, battery-trend.js), `0c56458` (submit-guard.js, copy-button.js), `9e06af8` (login-card.js, poll-cooldown.js, flash-cleanup.js, confirm-submit.js)
3. **Task 3: Close group 6** - `021b020` (fix: banned-token substrings), `327044a` (fix: test rhetoric/plan-id-marker assertions), `b186212` (pending-list ratchet + 35-COMMENT-RATIO.md)

**Plan metadata:** not yet committed (this SUMMARY + STATE/ROADMAP updates land in the final metadata commit).

## Files Created/Modified

- `companion/static/{battery-trend,confirm-submit,copy-button,dirty-state,flash-cleanup,flight-rows,freshness,list-filter,login-card,nav-dropdown,panel-lookup,poll-cooldown,quick-switch,relative-time,submit-guard,theme-preview,value-controls}.js` - comments purged of history/rhetoric, code unchanged
- `scripts/comment-history-pending.txt` - the 17 `companion/static/*.js` lines removed
- `.planning/phases/35-comment-purge-in-english-and-dead-code/35-COMMENT-RATIO.md` - group-6 section appended
- `companion/test_config_page_03.py`, `companion/test_status_pages_07.py` - two assertions fixed (see Deviations)

## Decisions Made

- Purged bottom-up per file, editing only comment regions with exact-match `Edit` calls so every code line stayed character-identical, then verified with `same-code` per file before moving to the next — never a full-file rewrite that risked silently changing a token.
- Where a file's post-purge ratio still sat just above the ~35% review-trigger guideline (`confirm-submit.js` 37.0%, `flash-cleanup.js` 36.1%), left it there with a recorded justification rather than compressing further: both are small files (36-46 lines) where the required ≤8-line header is an outsized fraction of the total, and the remaining content is a security note or a DOM/behaviour contract purge_rules require to survive.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Two rewritten comments accidentally contained ES5-banned-token substrings**
- **Found during:** Task 2, running the browser/full test suite
- **Issue:** `nav-dropdown.js`'s rewritten comment used the English word "let" ("would otherwise let this stale callback…"), and `relative-time.js`'s used "translated" (containing "late") — both tripped existing tests that ban the literal substrings `"let "` / `"late"` anywhere in the served script (ES5-safety and no-verdict-vocabulary checks).
- **Fix:** Reworded both comments ("would otherwise allow this stale callback…", "already localised") with no change to meaning or to any code token.
- **Files modified:** `companion/static/nav-dropdown.js`, `companion/static/relative-time.js`
- **Verification:** `same-code`/`check`/`node --check` still pass; the two originally-failing tests (`test_nav_dropdown_script_es5_safe_and_side_effect_free`, `test_relative_time_script_es5_safe_and_no_html_write`) pass.
- **Committed in:** `021b020`

**2. [Rule 1 - Bug] Two pre-existing companion tests asserted on exact history/rhetoric text this phase's purge_rules require removed**
- **Found during:** Task 2, running the full test suite
- **Issue:** `companion/test_config_page_03.py::test_dirty_state_js_is_network_free_again_with_one_named_timer_exception` required the literal substrings `"never introduce a network call"` and the upper-case `"ONE NAMED EXCEPTION"` to appear verbatim in `dirty-state.js`'s header — exactly the upper-case-emphasis rhetoric `35-CONTEXT.md`'s D-A3 decision and this plan's `purge_bar` both ban. `companion/test_status_pages_07.py::test_freshness_js_breathes_only_from_the_loops_own_state` used the plan-id string `"23-05-PLAN.md Task 2"` as a text-search end-boundary for a region of `freshness.js`, which `check_comment_history.py`'s own `plan-artifact` pattern flags as a history reference — the test could not pass at the same time as `check --paths freshness.js` reporting 0 hits.
- **Fix:** Removed the two purely-rhetorical assertions from the dirty-state.js test (its four structural assertions above them — single `setTimeout`, inside the reset handler, literal zero delay, no `preventDefault`/`returnValue` — already prove the real behavioural contract) and updated the docstring accordingly. Replaced the freshness.js test's plan-id boundary marker with `"function syncLiveDot()"`, the function that genuinely follows `clearState()` in the current file, keeping the same region-scoped assertion.
- **Files modified:** `companion/test_config_page_03.py`, `companion/test_status_pages_07.py`
- **Verification:** Both tests pass; the full suite (2691 tests) is green; `check_comment_history.py check` still reports 0 hits.
- **Committed in:** `327044a`

---

**Total deviations:** 4 auto-fixed (2 comment-wording fixes, 2 test-assertion fixes), all Rule 1 (bugs directly caused by this plan's own comment rewrite).
**Impact on plan:** All four were required to keep the full test suite green per the close_procedure's "no behaviour change" proof. No scope creep: the two test edits touch only the specific assertions in conflict with this phase's own decisions, not the tests' structural/behavioural coverage.

## Issues Encountered

None beyond the deviations above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Group 6 (companion static JS) is fully purged and CI-enforced (0 pending entries, `check` exits 0 with no exemption).
- HYG-02 is not marked complete in this plan per the orchestrator's instruction (`stub-server/` and `companion/static/style.css`, group 7, remain).
- `scripts/comment-history-pending.txt` still lists `companion/static/style.css` (group 7) and every other still-open group's paths — untouched by this plan.
- No PR opened and `main` not merged into this branch, per the sequential-executor's explicit instruction (orchestrator's responsibility).

---
*Phase: 35-comment-purge-in-english-and-dead-code*
*Completed: 2026-09-25*

## Self-Check: PASSED

All 17 purged `companion/static/*.js` files, the ratio doc, this SUMMARY, and
the two fixed test files were confirmed present on disk; all 10 commit
hashes cited above were confirmed present in `git log --oneline --all`.
