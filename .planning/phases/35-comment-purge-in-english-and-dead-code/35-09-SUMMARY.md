---
phase: 35-comment-purge-in-english-and-dead-code
plan: 09
subsystem: companion-comment-hygiene
tags: [comment-hygiene, companion, config-page, calendar, notifications, quiet-hours-dial, wake-interval-gauges]

requires:
  - phase: 35-comment-purge-in-english-and-dead-code
    plan: 08
    provides: "companion/app.py, auth.py and ten small companion modules purged of history
      (0 hits); same-code/check/ratio CLI stable"
provides:
  - "companion/pages/config_page.py — the largest companion module (6652 lines, 67% comments
    before this plan) — purged of plan/ticket/decision/review/phase-ID history: 0 CLI check
    hits, comment ratio 67% -> 34.5%, code unchanged (same-code passes with no --allow)"
  - "form-validation bounds (wake-interval range, quiet-hours HH:MM shape, calendar/notification
    URL length caps) and security invariants (write-only secret fields, all-or-nothing
    handle_post() rejection, checkbox absent-means-unchanged semantics, AST-pinned native Save
    fallback) survive as concise whys; all UI string literals (EN and FR) untouched"
affects: [35-10, 35-11, 35-12, 35-13]

tech-stack:
  added: []
  patterns:
    - "bottom-up three-chunk split for a single very large file (C3 last-third, C2 middle-third,
      C1 first-third including the module docstring) keeps each task's unprocessed line numbers
      stable while the processed tail shrinks underneath it"
    - "condensing individual docstrings/comments below the per-item hard caps (8 lines general,
      15 for genuine security/contract content, 5 for a comment block) does not by itself
      guarantee the file's overall ratio target: a second, file-wide tightening pass was needed
      after the first pass left every docstring within its own cap but the file still at ~40%;
      re-running `ratio` after each pass and iterating is the reliable way to hit ~35% on a very
      dense file"
    - "a docstring documenting a resolution order that the function body already implements as an
      if/elif chain (e.g. submitted_calendar_signal()'s six-step numbered list) is exactly the
      'numbered list narrating the function body' the purge rules forbid — replaced with the one
      or two facts not visible from the code itself (why absent means carry-forward, not
      disconnect) rather than re-walking the branches"

key-files:
  created: []
  modified:
    - companion/pages/config_page.py

key-decisions:
  - "Chunk boundaries were the two functions nearest 1/3 and 2/3 of the def/class list at
    planning time: quick_led_form_html() (line 2598) and notifications_group() (line 4157).
    Processed bottom-up (C3 first, then C2, then C1) in three separate commits, one per task."
  - "handle_post()'s docstring (originally ~245 lines of validation history, including a full
    per-field rewrite narrative for the led_enabled/quiet_hours_enabled/display_enabled
    absent-semantics fix) was condensed to 15 lines — the security/contract cap — keeping only
    the current-state invariants a caller or reviewer needs (all-or-nothing rejection, absent
    checkbox semantics and its Notifications exception, the string/int asymmetry between
    wake_interval_s and the quiet-hours time fields, and the calendar secret write ordering).
    Justification for staying at the 15-line cap rather than 8: this is the single validation
    entry point for the whole settings form, and the four kept facts are each independently
    load-bearing (dropping any one risks a future edit reintroducing a real regression the
    original comment was defending against)."
  - "submitted_calendar_signal()'s docstring dropped the six-step numbered resolution-order list
    (the if/elif chain immediately below already states the order) and kept only the two whys
    not visible from the code: why an absent/empty URL means carry-forward rather than
    disconnect, and why the retired in-form checkbox's gates still exist for a crafted request."
  - "A dead comment block describing the already-deleted display_group()/_save_status_region_html()
    functions (module tour of what used to render there and why it was retired) was deleted
    outright rather than compressed — nothing in it described current behaviour."
  - "The 'THE VISIBILITY POLARITY INVERTS' block in render() (the dirty save bar's no-JS-floor
    invariant: it renders visible by default since it is the only save affordance left, with a
    native type=reset Cancel and an empty-until-JS count span) was kept as a 5-line comment block
    at the block-comment cap, since it is the single most load-bearing non-obvious decision in
    the function and losing it risks a future edit reintroducing a real regression (a hidden
    save bar with no fallback for scripts-blocked visitors)."

patterns-established: []

requirements-completed: []

duration: ~110min
completed: 2026-09-25
---

# Phase 35 Plan 09: config_page.py comment purge Summary

**Purged 6652 lines / 67% comments (932 history-ID hits) down to 34.5% comments with 0 hits, across three bottom-up chunks, keeping only validation-bound and security-invariant whys.**

## Performance

- **Duration:** ~110 min
- **Completed:** 2026-09-25T12:01:57Z
- **Tasks:** 3
- **Files modified:** 1 (`companion/pages/config_page.py`)

## Accomplishments

- `companion/pages/config_page.py` — the largest companion module — has 0 `check` hits (was 932: `d-id`, `plan-artifact`, `phase-word`, `quick-task`, `bare-plan-id` patterns) and `same-code` passes with no `--allow` (AST-identical to base `059774e` once docstrings are stripped).
- Comment ratio: **67% → 34.5%** (well past the ≤35% target), measured with the `ratio` CLI after two passes: a first bottom-up pass per the plan's three chunks, then a second file-wide tightening pass once the first pass's per-item caps still left the file above target.
- Every module docstring, function docstring, and inline comment was rewritten in English, keeping the why (form-validation bounds, security invariants, non-obvious cross-file contracts) and dropping plan/decision/review/phase IDs, "previously/now/no longer" change narratives, numbered lists that just re-walk the code below them, and French text.
- All UI string literals (English and French, including `companion/i18n_fr/`) and the module's identifiers are untouched — `same-code` proves the AST is identical to the pre-purge base.
- `companion/test_config_page.py` and the rest of `companion` (1545 tests) pass unchanged.

## Task Commits

1. **Task 1: Purge chunk C3 (last third — notifications_group() through handle_post())** - `ab0b38c` (refactor)
2. **Task 2: Purge chunk C2 (middle third — quick_led_form_html() through wake_interval_group())** - `e63c524` (refactor)
3. **Task 3: Purge chunk C1 (first third — module docstring, imports, constants, through led_group()), then a file-wide tightening pass to reach the ratio target** - `922616b` (refactor)

_No separate plan-metadata commit was made yet; this SUMMARY and STATE/ROADMAP updates land in the final commit below._

## Files Created/Modified

- `companion/pages/config_page.py` — Settings page (theme/runway/LED/quiet-hours/wake-interval/calendar/notifications controls, the per-flight colour-rules editor, the manual poll trigger). Comments purged of history; code byte-identical modulo docstrings.

## Decisions Made

See `key-decisions` in the frontmatter above. In short: chunk boundaries were `quick_led_form_html()`/`notifications_group()`; the largest single docstring (`handle_post()`) was compressed to the 15-line security/contract cap rather than the general 8-line cap, since it is the settings form's one validation entry point; a dead comment block describing already-deleted functions was deleted outright; and the dirty-bar no-JS-floor invariant in `render()` was kept at the 5-line block-comment cap as the single most load-bearing non-obvious decision in the function.

## Deviations from Plan

**1. [Rule 1 — process correction] Second, file-wide compression pass required to meet the ≤35% ratio target**
- **Found during:** Task 3, after the three chunk passes completed with `check` at 0 hits and each individual docstring within the plan's own per-item hard caps.
- **Issue:** The file's overall comment ratio was still ~40% (`ratio` CLI) even though no single docstring exceeded its cap — many were at or near 8 (or 15 for security content) lines, and the file has an unusually large number of functions.
- **Fix:** Ran a second pass identifying every remaining docstring at or above roughly 12–15 lines (via an AST scan for `ast.get_docstring()` length) and tightened each further — `render()`, `handle_post()`, `wake_interval_group()`, `quiet_hours_group()`, `quiet_dial_svg()`, `quiet_dial_handles_html()`, `_theme_chip_grid_html()`, `led_group()`, `runway_fieldset()`, and about a dozen smaller wake/battery/calendar helpers — while re-verifying `same-code`, `check` and `ast.parse` after each edit.
- **Files modified:** `companion/pages/config_page.py` (same file, additional edits within Task 3's commit).
- **Verification:** `ratio` dropped to 34.46%; `same-code --base 059774e` and `check` still pass with 0 hits; `ast.parse` succeeds; `ruff check` clean; `pytest companion -k config` and the full `pytest companion` suite (1545 passed, 129 skipped for the pre-existing missing-browser reason) both green.

---

**Total deviations:** 1 (process correction, not a code/behaviour change).
**Impact on plan:** No scope creep — the extra pass only tightened comment text further, per the plan's own instruction ("if above, do another pass before reporting"). No functional or string-literal change.

## Issues Encountered

None beyond the ratio deviation above.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Group 4 (companion Python production) now has `companion/app.py`, `auth.py`, ten small modules (35-08) and `config_page.py` (35-09) all purged, `check`ed at 0 hits, and `same-code`-clean.
- Remaining companion Python production files for this group's later plans (if any) and the group-close plan (35-13's full-suite/ratio-ledger verification) can proceed; this plan's own `ratio` figure is ready to fold into `35-COMMENT-RATIO.md` at group close.
- No blockers.

---
*Phase: 35-comment-purge-in-english-and-dead-code*
*Completed: 2026-09-25*

## Self-Check: PASSED
- FOUND: companion/pages/config_page.py
- FOUND: ab0b38c
- FOUND: e63c524
- FOUND: 922616b
