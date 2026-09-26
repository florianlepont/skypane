---
phase: 35-comment-purge-in-english-and-dead-code
plan: 14
subsystem: companion-comment-hygiene
tags: [comment-hygiene, hyg-01, companion, browser-tests, playwright]

requires:
  - phase: 35-comment-purge-in-english-and-dead-code
    plan: 13
    provides: "HYG-05 dead code deleted; group 4 (companion Python production) closed, 0 comment-history hits"
provides:
  - "The nine companion/test_browser_*.py files (test_browser_ux_helpers.py, test_browser_ux_01..04.py, test_browser_ux_health_drawings.py, test_browser_ux_quiet_wake.py, test_browser_origin.py, test_browser_policy.py) purged of plan/ticket/decision/phase IDs, change narration and restatements — 0 check-tool hits, same-code proves the AST is unchanged against base 8a8b8b4"
  - "Comment lines roughly halved across the family (4357 -> 2281, 48%), with test docstrings collapsed to one behaviour-stating sentence and comment blocks kept to the why (measurement rationale, wait/timeout/settle reasoning, browser quirks)"
  - "The browser test family's collected node count is unchanged (129 before and after) and all 129 pass with SKYPANE_REQUIRE_BROWSER=1 (no skips); the full companion suite (1672 tests) is green"
affects: [35-17]

tech-stack:
  added: []
  patterns:
    - "The plan's files_modified list predated Phase 33's final file splits (it named a retired test_browser_ux.py and omitted test_browser_ux_03.py/_04.py, which now exist); the authoritative file set was the glob `git ls-files 'companion/test_browser_*.py'` (9 files), per the plan's own ownership convention — recorded here rather than silently substituted"
    - "Two helper docstrings and one JS-probe comment block exceed the 8-line/5-line purge_bar caps deliberately, each packing several independently load-bearing behavioural contracts that a shorter version would drop (see Purge Bar Exceptions below)"
    - "Assertion-message string literals were left untouched even where they still carry an ID (e.g. 'CFG-77', 'X2'): the check tool does not scan string literals, and the purge_bar explicitly forbids editing them — confirmed by same-code passing with no --allow on every file"

key-files:
  created: []
  modified:
    - companion/test_browser_ux_helpers.py
    - companion/test_browser_origin.py
    - companion/test_browser_policy.py
    - companion/test_browser_ux_01.py
    - companion/test_browser_ux_02.py
    - companion/test_browser_ux_03.py
    - companion/test_browser_ux_04.py
    - companion/test_browser_ux_health_drawings.py
    - companion/test_browser_ux_quiet_wake.py

key-decisions:
  - "Split into six task commits instead of the plan's two, one per file (or small file group) as each was finished, to keep the diffs reviewable and reduce the risk of losing a large amount of purge work to a single failed verification step. The two-task shape in the plan predates the file-set correction (nine files, not two) and would have produced one enormous commit per task."
  - "Ownership followed the glob, not the stale files_modified list: purged every file `git ls-files 'companion/test_browser_*.py'` returns (9 files, ~13.4k lines, matching the plan's own scope description), including test_browser_ux_03.py and test_browser_ux_04.py (absent from files_modified) and excluding the already-deleted test_browser_ux.py (present in files_modified)."
  - "Where a helper's docstring documented three or more genuinely independent behavioural contracts (e.g. _computed_paint, _assert_js_gate, _persist_without_js), the docstring was condensed as far as possible without dropping a contract rather than forced under the 8-line cap — each case is named below with a one-line justification, per the purge_bar's own exceed-with-justification allowance."

requirements-completed: []

duration: ~3h
completed: "2026-09-25"
---

# Phase 35 Plan 14: Browser test family comment purge Summary

**Purged plan/ticket/decision-ID history from all nine `companion/test_browser_*.py` files (13.4k lines), cutting comment lines from 4357 to 2281 (48%) and history-check hits from 636 to 0, with same-code proving the code itself is byte-for-byte unchanged and all 129 browser tests still passing.**

## Performance

- **Duration:** ~3h
- **Completed:** 2026-09-25T16:50:00Z
- **Tasks:** 2 planned, executed as 6 per-file/per-group commits (see Task Commits)
- **Files modified:** 9

## Accomplishments

- Purged `companion/test_browser_ux_helpers.py` (2717 lines, the largest file, 57 history hits) to 0 hits, 1399 -> 530 comment lines (62% reduction), while preserving every genuine measurement rationale (why `getComputedStyle` proves theme-token painting, why `elementFromPoint` beats `getBoundingClientRect` for hit-testing, why the pointer-recorder discriminates on event provenance, etc.).
- Purged the two small suites, `test_browser_origin.py` and `test_browser_policy.py`, to 0 hits.
- Purged `test_browser_ux_01.py` through `test_browser_ux_04.py` (the four migrated UX chain parts) to 0 hits each, condensing every test's rambling parenthetical ID citation into a one-sentence docstring and every numbered inline comment block into a single why-sentence.
- Purged `test_browser_ux_health_drawings.py` (the SVG-drawing scenario group) and `test_browser_ux_quiet_wake.py` (the quiet-hours dial / wake-interval slider group) to 0 hits, keeping the dense contrast-floor and geometry-derivation rationale that those checks depend on.
- Verified the authoritative file set against `git ls-files 'companion/test_browser_*.py'` before starting (see Deviations): 9 files, not the 2 named in the plan's stale `files_modified`.
- Ran `same-code --base 8a8b8b4` on every file individually and on the full 9-file set together: exit 0, no `--allow`, on every run.
- Confirmed the collected browser-test node count is unchanged: 129 before any edit (recorded via `git stash`) and 129 after, both via `pytest --collect-only -q companion/test_browser*.py`.
- Ran the full browser family with `SKYPANE_REQUIRE_BROWSER=1 pytest companion/test_browser*.py -q -n auto`: 129 passed, 0 skipped (the Chromium headless shell was installed mid-session via `playwright install --only-shell chromium` to make this a real run rather than a skip-only proof).
- Ran the full `companion` suite: 1672 passed, 2 skipped (pre-existing root-euid permission-bit skips, unrelated to this plan).
- Ran `ruff check` on the full 9-file set: clean.

## Task Commits

Executed as six commits, one per file or small natural file group, rather than the plan's two large tasks (see Decisions Made):

1. **Helpers + two small suites** - `6fb50df` (test) — test_browser_ux_helpers.py, test_browser_origin.py, test_browser_policy.py
2. **UX chain parts 01 and 02** - `99e3a11` (test) — test_browser_ux_01.py, test_browser_ux_02.py
3. **UX chain part 03** - `a99e28a` (test) — test_browser_ux_03.py
4. **UX chain part 04** - `b7d8dd2` (test) — test_browser_ux_04.py
5. **Health-drawings suite** - `5795b44` (test) — test_browser_ux_health_drawings.py
6. **Quiet-hours/wake suite** - `1b8c037` (test) — test_browser_ux_quiet_wake.py

**Plan metadata:** this commit (docs: complete plan)

## Per-File Ratios (before -> after)

Measured with `server/.venv/bin/python scripts/check_comment_history.py ratio` at group base `8a8b8b4` and again after all six commits.

| File | Lines before | Comment lines before | Ratio before | Comment lines after | Ratio after | Hits before -> after |
|---|---:|---:|---:|---:|---:|---:|
| companion/test_browser_ux_helpers.py | 2717 | 1399 | 51.5% | 530 | 28.7% | 57 -> 0 |
| companion/test_browser_origin.py | 159 | 32 | 20.1% | 19 | 13.2% | 4 -> 0 |
| companion/test_browser_policy.py | 134 | 36 | 26.9% | 18 | 15.5% | 2 -> 0 |
| companion/test_browser_ux_01.py | 1408 | 542 | 38.5% | 240 | 21.7% | 136 -> 0 |
| companion/test_browser_ux_02.py | 1954 | 562 | 28.8% | 320 | 18.8% | 115 -> 0 |
| companion/test_browser_ux_03.py | 1844 | 269 | 14.6% | 191 | 10.9% | 110 -> 0 |
| companion/test_browser_ux_04.py | 1486 | 340 | 22.9% | 259 | 18.5% | 79 -> 0 |
| companion/test_browser_ux_health_drawings.py | 1794 | 554 | 30.9% | 354 | 22.2% | 60 -> 0 |
| companion/test_browser_ux_quiet_wake.py | 1938 | 623 | 32.2% | 350 | 21.0% | 73 -> 0 |
| **Family total** | **13434** | **4357** | **32.4%** | **2281** | **17.5%** | **636 -> 0** |

The family total's "before" figures (9 files, 13434 lines, 636 history hits) match the plan's own scope description (`~13.4k lines, 32% comments, 636 history hits`) exactly.

### Files still above the ~20%-per-file guideline

`test_browser_ux_helpers.py` (28.7%), `test_browser_ux_01.py` (21.7%) and `test_browser_ux_health_drawings.py` (22.2%) sit a few points above the ~20% per-file target the purge_bar states as "where possible." All three are dense measurement-technique files (`_hit_area`'s binary-search hit-testing, `_computed_paint`'s browser-vs-source-scan rationale, per-drawing contrast-floor derivations) where the remaining comments are genuine why-content the purge_bar's own "keep" list protects, not restatement — cutting further would start deleting the reasoning a future maintainer needs to safely change these tests. `test_browser_ux_quiet_wake.py` (21.0%) and `test_browser_ux_04.py` (18.5%) are close to the same shape for the same reason.

### Purge Bar Exceptions (docstrings/blocks over the 8-line/5-line cap)

- **`_computed_paint` docstring, `test_browser_ux_helpers.py`** (11 lines, cap 8): documents three independent invariants four drawing-test call sites rely on — the browser-vs-source-scan rationale for why this measurement exists at all, the `svg_default` field's exact semantics (a legitimately-`stroke:none` shape reporting `stroke` there is correct, not a false positive), and the raise-vs-None contract for an empty match. Compressing further would drop one of the three without a shorter equivalent.
- **`_HIT_AREA_PROBE` comment block, `test_browser_ux_helpers.py`** (9 lines, cap 5): explains why `elementFromPoint`-based binary-search hit-testing is used instead of `getBoundingClientRect()` alone — the technique is explicitly "recorded here because a later reader will otherwise simplify it back into a wrong measurement" in the pre-purge source, and the two failure modes it guards against (understating a synthesized target, overstating an occluded one) each need their own sentence to be actionable.
- **`_persist_without_js` docstring, `test_browser_ux_helpers.py`** (12 lines, cap 8): the single most heavily reused helper in the family (five control plans' worth of save-floor checks), with six independently meaningful parameters (`shows_back`, `restore`, `cookies`) each carrying a real behavioural contract that a caller needs before choosing whether to override the defaults.

## Files Created/Modified

- `companion/test_browser_ux_helpers.py` — shared constants/helpers for the browser test family; comments purged, code unchanged.
- `companion/test_browser_origin.py` — SEC-03 cross-origin proof; comments purged, code unchanged.
- `companion/test_browser_policy.py` — missing-browser policy / loopback guard self-tests; comments purged, code unchanged.
- `companion/test_browser_ux_01.py` through `_04.py` — the four migrated `browser_ux` chain parts; comments purged, code unchanged.
- `companion/test_browser_ux_health_drawings.py` — SVG-drawing scenario group (battery ring/chart, day band, regularity grid, hero); comments purged, code unchanged.
- `companion/test_browser_ux_quiet_wake.py` — quiet-hours dial / wake-interval slider group; comments purged, code unchanged.

## Decisions Made

See `key-decisions` in the frontmatter above. In short: (1) six commits instead of the plan's two, since the plan's two-task shape predates the file-set correction and a single commit per remaining task would have bundled 4-6 files each; (2) ownership followed the live glob rather than the plan's stale `files_modified` list; (3) three helper docstrings and one JS-probe comment block were allowed to exceed the purge_bar's hard caps, each with a one-line justification, rather than dropping a load-bearing behavioural contract to fit an arbitrary line count.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Plan's files_modified list did not match the current file set**
- **Found during:** Start of Task 1, checking `git ls-files 'companion/test_browser_*.py'` against the plan's own `files_modified` (which named `companion/test_browser_ux.py`, deleted by an earlier phase, and omitted `test_browser_ux_03.py`/`test_browser_ux_04.py`, added by Phase 33's file splits).
- **Issue:** Following the stale list would have purged a file that no longer exists and missed two files with 79 + 110 = 189 of the family's 636 history hits.
- **Fix:** Followed the plan's own ownership convention ("this plan owns every file matching `git ls-files 'companion/test_browser_*.py'`... the glob wins") and purged all 9 files the glob returns.
- **Files modified:** All 9 files in the table above (the glob's full result).
- **Verification:** `git ls-files 'companion/test_browser*.py'` matches the 9 files purged; same-code and check both pass on all 9.
- **Committed in:** Spread across all six task commits (the file-set correction is structural, not a single commit).

---

**Total deviations:** 1 auto-fixed (1 blocking — a stale file list in the plan's own frontmatter)
**Impact on plan:** Required to purge the actual browser test family rather than a subset of it. No scope creep — every file purged matches the plan's own scope description and threat model.

## Issues Encountered

- The sandbox's Playwright install initially had no Chromium headless shell binary (`playwright install --only-shell chromium` had not been run), so the browser tests skipped locally rather than running. Installed the shell mid-session (a one-time, ~114 MB download) so the plan's own verification commands (`SKYPANE_REQUIRE_BROWSER=1 pytest ...`) could run for real rather than relying on same-code alone, matching the plan's own notes ("browser tests skip locally when Playwright's headless shell is absent... same-code is the proof they are unchanged" — this plan went further and ran them for real once the shell was available).

## User Setup Required

None - no external service configuration required.

## Verification Results

- **`same-code --base 8a8b8b4`, per file and as a 9-file set:** exit 0, no `--allow`, in every case.
- **`check --paths`, per file and as a 9-file set:** 0 history hits, exit 0, in every case.
- **`pytest --collect-only -q companion/test_browser*.py`:** 129 tests, matching the pre-edit count (recorded via `git stash` against the same command before any file was touched).
- **`SKYPANE_REQUIRE_BROWSER=1 pytest companion/test_browser*.py -q -n auto`:** 129 passed, 0 skipped, 0 failed.
- **`pytest companion -q -n auto` (full companion suite):** 1672 passed, 2 skipped (pre-existing, unrelated), 0 failed.
- **`ruff check` on the 9-file set:** "All checks passed!"
- **TDD gate compliance:** not applicable — this plan's tasks are `type="auto"`, not `tdd="true"`; no RED/GREEN/REFACTOR gate sequence is required.

## Next Phase Readiness

The browser test family (group 5's largest, most history-dense slice) is purged, same-code-proven and fully green. Group 5 (companion tests + test-support) is not yet closed — `companion/test_status_pages*.py`, `test_view_pages*.py` and the rest of group 5's non-browser files remain for sibling plans (35-15, 35-16) before 35-17 can close the group, append its `35-COMMENT-RATIO.md` section, and remove the group-5 paths from `scripts/comment-history-pending.txt`. Neither of those group-close artifacts was touched by this plan, per the orchestrator's own instruction that 35-17 owns them. HYG-01 remains open in `REQUIREMENTS.md`, correctly, since it spans groups not yet fully closed.

---
*Phase: 35-comment-purge-in-english-and-dead-code*
*Completed: 2026-09-25*

## Self-Check: PASSED

- `companion/test_browser_ux_helpers.py` — FOUND
- `companion/test_browser_origin.py` — FOUND
- `companion/test_browser_policy.py` — FOUND
- `companion/test_browser_ux_01.py` — FOUND
- `companion/test_browser_ux_02.py` — FOUND
- `companion/test_browser_ux_03.py` — FOUND
- `companion/test_browser_ux_04.py` — FOUND
- `companion/test_browser_ux_health_drawings.py` — FOUND
- `companion/test_browser_ux_quiet_wake.py` — FOUND
- Commit `6fb50df` (helpers + two small suites) — FOUND
- Commit `99e3a11` (UX chain parts 01, 02) — FOUND
- Commit `a99e28a` (UX chain part 03) — FOUND
- Commit `b7d8dd2` (UX chain part 04) — FOUND
- Commit `5795b44` (health-drawings suite) — FOUND
- Commit `1b8c037` (quiet-wake suite) — FOUND
