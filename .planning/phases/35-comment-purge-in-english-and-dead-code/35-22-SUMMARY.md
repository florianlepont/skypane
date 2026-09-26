---
phase: 35-comment-purge-in-english-and-dead-code
plan: 22
subsystem: infra
tags: [comment-hygiene, ci-guard, mutation-testing, ast, regex]

# Dependency graph
requires:
  - phase: 35-comment-purge-in-english-and-dead-code
    plan: 21
    provides: "group 9 (firmware/) purged; every group's history hits at 0 against its own base"
  - phase: 35-comment-purge-in-english-and-dead-code
    plan: 21b
    provides: "hash-file same-code fix (dbc1c28) applied and re-tightened across 24 group 2/8/9 files"
provides:
  - "scripts/comment-history-pending.txt deleted; check() with no --paths scans every tracked code file, no exceptions"
  - "_PRAGMA_RE's shellcheck alternative narrowed to real directives (disable|enable|source|shell|external-sources=), no longer pinning prose that starts with the word shellcheck"
  - "_same_code_python's keep-module-doc heuristic replaced with an AST ast.Name(id='__doc__', ctx=Load) check, no longer pinning a docstring merely because __doc__ appears in a string literal or as another object's attribute"
  - "45/45 pattern-set and heuristic mutations killed by the test suite on the final tree; a planted D-06 in one file per language (Python/C/JS/CSS/shell/YAML) makes check exit non-zero every time"
  - "35-COMMENT-RATIO.md Final section: whole-tree before/after totals (9441 -> 0 history hits, 40% -> 24.1% comment ratio, 264 -> 267 files), style.css and JS shipped-size before/after, and Requirements section confirming HYG-01..06 with evidence"
affects: []

tech-stack:
  added: []
  patterns:
    - "A same-code heuristic that keys off a text substring (the old '__doc__' in text check) is provably weaker than an AST-based check for the same intent; a string literal or an attribute access on another object can trigger a naive substring match without describing the module's own docstring being read"
    - "A pragma-preservation regex anchored on a bare keyword (the old '# shellcheck' prefix) will match prose that happens to start with that word; anchoring on the directive's own '=' syntax (disable=, source=, etc.) is the general fix for any future pragma family with the same shape"

key-files:
  created: []
  modified:
    - scripts/check_comment_history.py
    - scripts/comment-history-pending.txt
    - test-support/test_check_comment_history.py
    - CONTRIBUTING.md
    - .github/workflows/ci.yml
    - .planning/phases/35-comment-purge-in-english-and-dead-code/35-COMMENT-RATIO.md
    - .planning/REQUIREMENTS.md
    - .planning/ROADMAP.md

key-decisions:
  - "Kept CLAUDE.md untouched: grep found no pending-list mention there (only CONTRIBUTING.md and ci.yml's step comment referenced it), so HYG-04's citation stays exactly what 35-01 wrote"
  - "Reused 35-01's own 43-mutation methodology (write a throwaway script, mutate one regex alternative at a time, run the full test file, confirm a failure, restore) rather than inventing a new proof style, and extended it with 2 new mutations for this plan's own tool changes (the shellcheck directive alternative, the __doc__ AST check) for a 45-mutation total"
  - "Final ratio table computed by classifying every row of both ratio-before.tsv and a fresh whole-tree `ratio` run into the same 8 directory groups INDEX.md defines (verified against INDEX.md's own before-numbers: 0 unclassified rows, every group's totals match exactly), rather than trusting the per-group markdown tables' own file lists, which are known to differ slightly from the baseline's accounting (e.g. group 8's own table omits scripts/check_comment_history.py, which the baseline always counted there)"
  - "Group 8 and group 9's Final numbers diverge from their own closing-plan sections above (7848 vs 7471 lines; 8403 vs 9098 lines) because 35-21b re-tightened many of their files after those plans closed; documented as a dedicated note rather than silently overwriting the historical per-group sections"
  - "No PR opened and nothing pushed: the orchestrator's execution context for this run explicitly said not to (overriding this plan's own Task 2 text), matching the convention already used by 35-21b"

requirements-completed: [HYG-01, HYG-02, HYG-03, HYG-04, HYG-05, HYG-06]

# Metrics
duration: ~90min
completed: 2026-09-26
---

# Phase 35 Plan 22: Phase close — ratchet removed, mutation-reproven, final ratio table Summary

**Deleted the comment-history pending list so `check` now scans every tracked code file unconditionally, fixed two guard false-positive bugs (a shellcheck-prose pragma match, a `__doc__`-substring docstring pin) found during the phase, re-proved the guard with 45/45 killed mutations plus a 6-language planted-ID sweep, and closed out 35-COMMENT-RATIO.md with a whole-tree Final table and HYG-01..06 evidence.**

## Performance

- **Duration:** ~90 min
- **Started:** 2026-09-26T (session start)
- **Completed:** 2026-09-26
- **Tasks:** 2 completed
- **Files modified:** 8 (5 in Task 1, 3 in Task 2 including the two requirements/roadmap trackers)

## Accomplishments

- Deleted `scripts/comment-history-pending.txt` and its read path (`PENDING_PATH`, `load_pending()`) from `scripts/check_comment_history.py`; `check` with no `--paths` now scans every tracked file the tool has a comment syntax for, no exceptions list to consult.
- Removed the now-stale pending-list mentions in `CONTRIBUTING.md`'s "Code language and comments" section and the CI "Comment history guard" step's own comment in `.github/workflows/ci.yml`.
- Fixed `_PRAGMA_RE`'s shellcheck alternative: `#\s*shellcheck\b.*$` (matched any comment starting with the word "shellcheck", including prose) narrowed to `#\s*shellcheck\s+(?:disable|enable|source|shell|external-sources)=.*$` (matches only real shellcheck directives). This let the ci.yml "shellcheck is preinstalled..." sentence — previously required to stay byte-identical because the old regex treated it as a must-preserve pragma — be simplified to a shorter, equivalent comment.
- Fixed the `__doc__` same-code heuristic: `_same_code_python`'s `keep_module_doc` used to be `"__doc__" in base_text or "__doc__" in working_text`, a text substring check that false-positives on a string literal spelling the word or an attribute access on some other object's docstring (`companion/test_suite_guards.py` has both shapes as test-fixture data). Replaced with `_reads_module_dunder_doc()`, which parses the source with `ast` and looks for a real `ast.Name(id="__doc__", ctx=Load)` — the actual `argparse.ArgumentParser(description=__doc__)` idiom — walking the whole module tree.
- Added 4 new regression tests for the `__doc__` fix (string-literal false positive, attribute-access false positive, both proving `differing == []` where the old heuristic would have forced `differing != []`) and 4 new tests for the shellcheck fix (all 5 real directive shapes matched via `_pragma_spdx_multiset`, the prose sentence correctly ignored, a same-code reword-allowed case, a same-code real-directive-must-stay-identical case), plus replaced the removed pending-list test with `test_check_no_args_scans_every_tracked_file`.
- Re-proved the guard on the final tree with a throwaway mutation script (same methodology as `35-01`'s original 43-mutation sweep, `/tmp` scratch, never committed): all 45 mutations — the original 43 pattern-set alternatives plus the 2 new ones from this plan's tool fixes — killed at least one test when removed, restored, `git diff` empty after every restore.
- Planted `# see D-06` (or the language's own comment syntax) in one tracked file per language family (`server/plane/dither.py`, `firmware/main/wake_deadline.c`, `companion/static/copy-button.js`, `companion/static/style.css`, `scripts/lock-deps.sh`, `.github/workflows/firmware.yml`) and confirmed `check` exits 1 and names the file each time; reverted with `git checkout --` after each plant, `check` back to exit 0, `git diff` empty.
- Assembled `35-COMMENT-RATIO.md`'s "Final" section: an 8-group whole-tree before/after summary table (264 -> 267 files, 148524 -> 117887 lines, 39.9% -> 24.1% comment ratio, 9441 -> 0 history hits), a note explaining why groups 8 and 9's Final numbers diverge from their own closing-plan sections (35-21b's later tightening plus `scripts/check_comment_history.py` itself being counted in group 8 per the baseline), `style.css` and the 17 JS files' shipped raw/gzip sizes before/after, and a "Requirements" section citing evidence for HYG-01 through HYG-06.
- Marked HYG-01, HYG-02, HYG-03, HYG-06 complete in `REQUIREMENTS.md` (checkbox and traceability-table status); HYG-04 and HYG-05 were already complete.
- Confirmed the full verification suite green on the final tree: `SKYPANE_REQUIRE_BROWSER=1 ./scripts/run-all-tests.sh` (2705 passed, 5 skipped, 93.24% coverage), `ruff check .` clean, `./firmware/tests/run_host_tests.sh` (10/10 suites), `check_log_contract.sh` and `check_production_config.sh static` both PASS, and `check_comment_history.py check` (no args, whole tree) exits 0.

## Task Commits

1. **Task 1: Delete the pending mechanism and re-prove the guard** - `ec5ddda` (feat)
2. **Task 2: Final ratio table, requirement confirmation** - metadata-only, no source changes; see the plan-metadata commit below

**Plan metadata:** (this SUMMARY + REQUIREMENTS.md + ROADMAP.md + STATE.md commit follows, per the standard end-of-plan protocol)

## Files Created/Modified

- `scripts/check_comment_history.py` - pending-list code path removed; `_PRAGMA_RE` shellcheck alternative tightened; `_reads_module_dunder_doc()` added, used by `_same_code_python`
- `scripts/comment-history-pending.txt` - deleted
- `test-support/test_check_comment_history.py` - pending-list test replaced with a no-args-scans-everything test; 8 new tests for the two tool fixes
- `CONTRIBUTING.md` - pending-list sentence removed from the comment-hygiene paragraph
- `.github/workflows/ci.yml` - "Comment history guard" step comment updated (no pending list); "Shellcheck deploy scripts" step comment simplified now that it is free to be reworded
- `.planning/phases/35-comment-purge-in-english-and-dead-code/35-COMMENT-RATIO.md` - Final whole-tree section, 35-21b divergence note, style.css/JS shipped-size before/after, Requirements (HYG-01..06) section
- `.planning/REQUIREMENTS.md` - HYG-01, HYG-02, HYG-03, HYG-06 checkboxes and traceability rows marked Complete
- `.planning/ROADMAP.md` - 35-22 plan checkbox marked complete

## Decisions Made

See `key-decisions` in the frontmatter above: the Final ratio table's group classification was built and cross-checked against `35-BASELINE/INDEX.md`'s own before-numbers rather than trusting each group's markdown table's file list; the group 8/9 divergence from `35-21b` is documented rather than silently reconciled; no PR was opened per this run's explicit orchestrator instruction.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `_PRAGMA_RE`'s shellcheck alternative matched prose, not just directives**
- **Found during:** Task 1, per the plan's own explicit instruction (this was a known issue surfaced during `35-21b`, not newly discovered here)
- **Issue:** `#\s*shellcheck\b.*$` matched any comment starting with the literal word "shellcheck", so `.github/workflows/ci.yml`'s "shellcheck is preinstalled on the ubuntu-24.04 runner image" sentence was pinned byte-identical by the pragma-preservation check even though it is prose, not a directive.
- **Fix:** Narrowed to `#\s*shellcheck\s+(?:disable|enable|source|shell|external-sources)=.*$`, matching only real shellcheck directive shapes.
- **Files modified:** `scripts/check_comment_history.py`, `test-support/test_check_comment_history.py`, `.github/workflows/ci.yml` (the now-freed-up comment was simplified)
- **Verification:** New parametrized test over all 5 real directive shapes (`test_pragma_multiset_matches_every_real_shellcheck_directive_shape`), a prose-is-not-a-pragma test, a same-code reword-allowed test, a same-code real-directive-still-flagged test, plus the mutation-proof removal of the alternative killing 2 of those tests
- **Committed in:** `ec5ddda`

**2. [Rule 1 - Bug] `__doc__` same-code heuristic false-positived on a substring, not a real read**
- **Found during:** Task 1, per the plan's own explicit instruction (surfaced by `companion/test_companion_app_02.py` and `companion/test_suite_guards.py`, though at the time of this plan neither file's current text actually contains the substring `__doc__` any more — the fix stands on its own merits and closes the general class of false positive, proven with synthetic string-literal and attribute-access test cases)
- **Issue:** `"__doc__" in base_text or "__doc__" in working_text` pins a module's docstring as "code" (never allowed to change without failing `same-code`) whenever the text merely contains the word — including inside a string literal or as `other_module.__doc__`, neither of which means the module reads its own docstring.
- **Fix:** Added `_reads_module_dunder_doc()`, an AST walk for `ast.Name(id="__doc__", ctx=Load)`; `_same_code_python` now calls it instead of the substring check.
- **Files modified:** `scripts/check_comment_history.py`, `test-support/test_check_comment_history.py`
- **Verification:** Two new tests proving a docstring-only edit is still allowed (`differing == []`) when `__doc__` appears only in a string literal or as another object's attribute; the existing genuine-read test (`argparse.ArgumentParser(description=__doc__)`) still requires `differing != []`; mutation-proof reverting to the substring check kills the two new tests
- **Committed in:** `ec5ddda`

---

**Total deviations:** 2 auto-fixed (both Rule 1, both the plan's own explicitly-named tool refinements — not surprises found mid-execution)
**Impact on plan:** Both fixes are scoped exactly to the two bugs the plan named; no additional scope taken on.

## Issues Encountered

- The mutation-proof script's first draft used a Python raw-string literal that didn't match the tool file's actual on-disk text byte-for-byte (an escaping mismatch between the search needle and the real `_PRAGMA_RE` source line), tripping an `assert ... in ORIGINAL` guard before any file was mutated. No file was left in a bad state (the assertion fired before the file was ever written), but it did cost one full ~2-minute background run before the fix. Corrected the needle to the exact source line and reran; all 45 mutations (43 original + 2 new) were then confirmed killed.
- `companion/test_companion_app_02.py` no longer contains the string `__doc__` at all (unlike when the plan's notes were written) — likely cleaned up by an earlier group-5 purge plan. The fix and its regression tests still stand on their own merits against a synthetic case with the same shape (a `__doc__`-spelling string literal), so this did not change scope.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 35 is closed: all 22 plans complete, `check_comment_history.py check` (no args) exits 0 over the whole tree, HYG-01 through HYG-06 all marked complete in `REQUIREMENTS.md`.
- No PR was opened and nothing was pushed by this plan — the orchestrator's execution context for this run explicitly said not to, matching `35-21b`'s prior convention that the orchestrator owns that step. The commit (`ec5ddda`) and this SUMMARY's own metadata commit sit on `claude/plan-phase-35`, which already contains `origin/main` merged in (via `c508eb2`).
- **Follow-up flagged, not fixed here (outside this plan's file scope):** `.claude/skills/sketch-findings-skypane/references/data-density.md` (lines 83, 86, 100) still names `usable_pairs()` and `label_grid()`, the two `companion/draw.py` functions `35-13` deleted for HYG-05. `git grep` confirms neither name exists anywhere in `.py`/`.js`/`.css` source any more. This is a project skill reference doc, not a `.planning/` artifact or tracked code file the guard scans, so it was out of both this plan's `files_modified` and the guard's own scope — a future pass over that skill's findings should drop or update those two references.
- No blockers for Phase 36 (state integrity and device protocol), which depends on Phase 35 being complete (gate G-35).

## Self-Check: PASSED

- `scripts/comment-history-pending.txt` confirmed absent (`git ls-files` and filesystem both).
- `grep -rn "comment-history-pending" scripts .github test-support CONTRIBUTING.md .claude/CLAUDE.md` returns nothing.
- Commit `ec5ddda` confirmed in `git log --oneline --all`.
- `server/.venv/bin/python -m pytest test-support/test_check_comment_history.py -q` — 113 passed.
- `server/.venv/bin/python scripts/check_comment_history.py check` — exit 0 over the whole tree.
- `SKYPANE_REQUIRE_BROWSER=1 ./scripts/run-all-tests.sh` — 2705 passed, 5 skipped, coverage 93.24%.
- `server/.venv/bin/ruff check .` — all checks passed.
- `./firmware/tests/run_host_tests.sh` — 10/10 suites passed.
- `sh firmware/tests/check_log_contract.sh` and `sh firmware/tests/check_production_config.sh static` — both PASS.
- `.planning/phases/35-comment-purge-in-english-and-dead-code/35-COMMENT-RATIO.md` confirmed present with "Final", "HYG-06" and "gzip" all present (grep-confirmed).

---
*Phase: 35-comment-purge-in-english-and-dead-code*
*Completed: 2026-09-26*
