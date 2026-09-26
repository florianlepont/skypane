---
phase: 35-comment-purge-in-english-and-dead-code
plan: 16
subsystem: companion-comment-hygiene
tags: [comment-hygiene, hyg-01, companion, companion-app, config-page, test-support, conftest]

requires:
  - phase: 35-comment-purge-in-english-and-dead-code
    plan: 13
    provides: "HYG-05 dead code deleted (health_severity, anomaly_active, usable_pairs, label_grid); group 4 (companion Python production) closed, 0 comment-history hits"
provides:
  - "All remaining companion/test_*.py families (config_page_01..05/_04b/_helpers, companion_app_01..05/_04b/_helpers), the smaller standalone companion test modules (test_app_server_fixture.py, test_contrast_check.py, test_health_offbox.py, test_i18n.py, test_login_throttle.py, test_post_origin.py, test_suite_guards.py), companion/conftest.py and test-support/*.py (except test_check_comment_history.py, already clean) purged of plan/decision/threat/quick-task-ID history and change-narration prose — 0 check-tool hits across all 29 files, same-code proves the AST unchanged against base 8a8b8b4 for 27 of them, and a narrowly-scoped --allow (documented below) for the remaining 2 whose module docstring is coupled to a `__doc__` mention elsewhere in the same file"
  - "Group 5 (companion tests + test-support) is now fully purged: combined with 35-14/35-15's status_pages/view_pages/browser families, every companion/test_*.py, companion/conftest.py and test-support/*.py file in the tree has 0 comment-history hits"
affects: [35-17]

tech-stack:
  added: []
  patterns:
    - "A scratch AST/tokenize-based mechanical purge script (/tmp/.../purge.py, not committed) that locates every real docstring/comment SPAN (via ast for docstrings — the first Constant-string statement of a Module/ClassDef/FunctionDef/AsyncFunctionDef body — and tokenize.COMMENT for comments), replaces only history-ID pattern matches found INSIDE those exact spans with a sentinel character, then resolves the sentinels into clean prose with span-scoped punctuation cleanup. This guarantees it never touches a string literal, assert message, or f-string/format call elsewhere in the file — the exact class of file the earlier manual passes (companion_app family onward) needed, given the file sizes involved (7.7k lines / 388 hits across the companion_app family alone)."
    - "Two manual review passes follow every mechanical run: (1) restore 4-space indentation on any docstring continuation line the mechanical pass's sentinel-collapse reduced to a single leading space, and trim any trailing space left before a closing triple-quote; (2) grep for structurally broken remnants specific to multi-line `#`-comment blocks (a parenthetical citation spanning two separate COMMENT tokens leaves a dangling `#)` on the second line, since tokenize treats each `#` line as an independent span) and rewrite those sentences by hand."
    - "same-code's own `keep_module_doc` heuristic treats the literal substring `__doc__` appearing ANYWHERE in a file (base or working text) as evidence the module reads its own docstring via `__doc__` (the argparse `--help` pattern from group 2's illustrations.py) and refuses to strip the module docstring from the AST comparison. Two files in this plan (test_companion_app_02.py, test_suite_guards.py) mention `__doc__` in an ordinary comment/docstring discussing a banned pattern, not as functional code — a false positive the tool cannot avoid, since base's copy of that mention is immutable. Diagnosed by forcing `keep_module_doc=False` for both texts and confirming the AST dumps are otherwise byte-for-byte identical, then applying a narrowly-scoped, disclosed `--allow` for exactly those two files' module docstrings."

key-files:
  created: []
  modified:
    - companion/test_config_page_01.py
    - companion/test_config_page_02.py
    - companion/test_config_page_03.py
    - companion/test_config_page_04.py
    - companion/test_config_page_04b.py
    - companion/test_config_page_05.py
    - companion/test_config_page_helpers.py
    - companion/test_companion_app_01.py
    - companion/test_companion_app_02.py
    - companion/test_companion_app_03.py
    - companion/test_companion_app_04.py
    - companion/test_companion_app_04b.py
    - companion/test_companion_app_05.py
    - companion/test_companion_app_helpers.py
    - companion/test_app_server_fixture.py
    - companion/test_health_offbox.py
    - companion/test_i18n.py
    - companion/test_login_throttle.py
    - companion/test_post_origin.py
    - companion/test_suite_guards.py
    - companion/conftest.py
    - test-support/companion_app_server.py
    - test-support/companion_markup.py
    - test-support/test_companion_markup.py

key-decisions:
  - "Ownership followed the plan's own scope note exactly: every companion/test_*.py NOT matched by test_browser_*/test_status_pages*/test_view_pages*, plus companion/conftest.py and every test-support/*.py except test_check_comment_history.py. The plan's files_modified list predates Phase 33's final splits (it lists test_config_page.py/test_companion_app.py and omits their _05 siblings); the live tree's actual file set (companion/test_config_page_01..05/_04b/_helpers.py, companion/test_companion_app_01..05/_04b/_helpers.py — 14 files, not the plan's 14-entry list with different names) was used instead, matching the orchestrator's own authoritative 29-file scope glob. test_legacy_harness_shim.py, named in the plan's Task 2 file list, no longer exists in the tree (already deleted by an earlier Phase 33 plan) — dropped from scope, nothing to record beyond its absence."
  - "companion/test_contrast_check.py, test-support/sitecustomize.py, test-support/skypane_test_support.py and test-support/test_test_support.py already had 0 history-check hits before this plan touched anything — confirmed via the check tool and left completely untouched (0 diff), consistent with the plan's own scope note that only files with real hits need edits."
  - "Given the family's total size (companion_app alone is ~7.7k lines / 388 hits, config_page ~9.8k lines / 660 hits), the config_page family (already substantially built out from prior sessions' hand-editing muscle memory) was purged by direct Edit calls file-by-file, while the companion_app family and remaining small files used a scratch mechanical AST/tokenize-scoped script followed by two manual review passes (see tech-stack patterns) — faster at this volume while keeping the same safety guarantee (only real comment/docstring spans are ever touched, verified per-file by same-code)."
  - "Two Rule-1-class mistakes were caught and reverted during manual editing before they reached a commit: an early pass on test_config_page_02.py/04.py/05.py accidentally edited a handful of assert-message string literals that merely LOOKED like citations (e.g. \"(27-02-PLAN.md Task 3's own acceptance bar)\" inside an assertion's own message, \"(D-18: externalized to poll-cooldown.js)\" repeated across five assert messages) — caught immediately by same-code failing, diagnosed with a small ast.dump()-diff script, and reverted to the exact original string before the task's own commit. No committed file carries an edited string literal; purge_rules' \"never edit string literals\" rule held throughout."
  - "test_companion_app_02.py and test_suite_guards.py both need `--allow` for same-code because each mentions the literal substring `__doc__` in an ordinary comment/docstring (discussing a banned test pattern, not functional `__doc__` use in test_companion_app_02.py; core to the guard's own detection logic in test_suite_guards.py) — same-code's own heuristic (`\"__doc__\" in base_text or \"__doc__\" in working_text`) treats this as evidence of an argparse-`--help`-style module and refuses to strip the module docstring from its AST comparison, regardless of what the module docstring itself says. Since base's copy of the mention is immutable, no edit can avoid the OR condition. Both cases were confirmed isolated to the module docstring alone by forcing `keep_module_doc=False` and diffing the resulting AST dumps (identical outside the docstring in both cases)."

requirements-completed: []

duration: ~2h40m
completed: "2026-09-25"
---

# Phase 35 Plan 16: All remaining companion tests + conftest + test-support comment purge Summary

**Purged plan/decision/threat/quick-task-ID history and change-narration prose from all 29 remaining companion/test_*.py + companion/conftest.py + test-support/*.py files (20,951 lines, 1048 history-check hits before), cutting hits to 0 everywhere, with same-code proving the AST unchanged (27 files with no --allow, 2 with a documented, narrowly-scoped --allow for a `__doc__`-substring tool quirk) and all 1811 companion + test-support tests still passing.**

## Performance

- **Duration:** ~2h40m
- **Completed:** 2026-09-25T21:13:00Z
- **Tasks:** 2 planned (config_page + companion_app families; the rest of the companion tests and test-support), executed as 16 per-file/small-group commits for interruption resilience (see Task Commits)
- **Files modified:** 24 (of the 29-file scope; 5 files already had 0 history-check hits and needed no edits — see Decisions Made)

## Accomplishments

- Purged the full `companion/test_config_page_01.py` through `_05.py` (plus `_04b.py` and `_helpers.py`) family — 9,843 lines, 660 history-check hits before — to 0 hits each, same-code clean against base `8a8b8b4` with no `--allow`.
- Purged the full `companion/test_companion_app_01.py` through `_05.py` (plus `_04b.py` and `_helpers.py`) family — 7,754 lines, 388 history-check hits before — to 0 hits each. Same-code is clean with no `--allow` for 6 of 7 files; `test_companion_app_02.py` needs a documented `--allow` for its module docstring alone (see Deviations).
- Purged `companion/test_app_server_fixture.py`, `test_health_offbox.py`, `test_i18n.py`, `test_login_throttle.py`, `test_post_origin.py` and `test_suite_guards.py` — 6 module docstrings/comments rewritten, 24 history hits cut to 0. `test_suite_guards.py` needs the same documented `--allow` as `test_companion_app_02.py`, for the identical `__doc__`-substring reason (this file's own guard logic legitimately checks `node.attr == "__doc__"`).
- Purged `companion/conftest.py` (5 hits) and `test-support/companion_app_server.py`, `companion_markup.py`, `test_companion_markup.py` (5 hits combined) — same-code clean with no `--allow` for all four.
- Confirmed `companion/test_contrast_check.py`, `test-support/sitecustomize.py`, `skypane_test_support.py`, `test_test_support.py` and `test-support/test_check_comment_history.py` already carried 0 history-check hits and left every one of them byte-for-byte untouched.
- Built and used a scratch AST/tokenize-scoped mechanical purge script for the companion_app family and the remaining small files (not committed, lives only under the session scratchpad) — it locates exact docstring/comment source spans via Python's own `ast`/`tokenize` modules (the same technique the `check`/`same-code` tool itself uses) and only ever substitutes inside those spans, by construction never touching a string literal or other code.
- Caught and reverted, before any commit, a handful of accidental string-literal edits made during the config_page family's manual pass (assert-message text that merely resembled a citation) — diagnosed each with a small `ast.dump()`-diff script comparing base vs. working AST, confirmed the revert restored byte-for-byte equality, and only then committed.
- Ran the FULL `pytest companion test-support -q -n auto` suite (not just the touched files) at the end: 1811 passed, 2 skipped (expected root-permission skips), 0 failed, 285s. `ruff check` on the full 29-file scope: all checks passed.
- Confirmed `pytest --collect-only -q` over the 29-file scope reports the identical 1014 tests before and after the whole plan.

## Task Commits

Executed as 16 commits (2 planned tasks, split per file/small-group for interruption resilience):

1. **test_config_page_01, 02** - `110c612` (test)
2. **test_config_page_03** - `33cb249` (test)
3. **test_config_page_helpers** - `c61e2e4` (test)
4. **test_config_page_04** - `5141c80` (test)
5. **test_config_page_04b** - `0e41715` (test)
6. **test_config_page_05** - `77409bd` (test)
7. **test_companion_app_helpers** - `2308537` (test)
8. **test_companion_app_01** - `63a77d7` (test)
9. **test_companion_app_02** - `af4454c` (test)
10. **test_companion_app_03** - `629d672` (test)
11. **test_companion_app_04** - `2aa2536` (test)
12. **test_companion_app_04b** - `95fa38b` (test)
13. **test_companion_app_05** - `8ca3469` (test)
14. **test_app_server_fixture, test_health_offbox, test_i18n, test_login_throttle, test_post_origin, test_suite_guards** - `25ec0e4` (test)
15. **companion/conftest.py** - `b33a284` (test)
16. **test-support/companion_app_server, companion_markup, test_companion_markup** - `83a1339` (test)

**Plan metadata:** this commit (docs: complete plan)

## Per-File Ratios (before -> after)

Measured with `server/.venv/bin/python scripts/check_comment_history.py ratio` at group base `8a8b8b4` and again after all sixteen commits.

| File | Lines before | Comment lines before | Ratio before | Comment lines after | Ratio after | Hits before -> after |
|---|---:|---:|---:|---:|---:|---:|
| companion/conftest.py | 218 | 81 | 37.2% | 81 | 37.2% | 5 -> 0 |
| companion/test_app_server_fixture.py | 211 | 52 | 24.6% | 52 | 24.6% | 2 -> 0 |
| companion/test_companion_app_01.py | 897 | 267 | 29.8% | 250 | 28.4% | 65 -> 0 |
| companion/test_companion_app_02.py | 1607 | 354 | 22.0% | 324 | 20.5% | 72 -> 0 |
| companion/test_companion_app_03.py | 1541 | 341 | 22.1% | 282 | 19.0% | 111 -> 0 |
| companion/test_companion_app_04.py | 967 | 183 | 18.9% | 160 | 17.0% | 39 -> 0 |
| companion/test_companion_app_04b.py | 904 | 204 | 22.6% | 187 | 21.1% | 28 -> 0 |
| companion/test_companion_app_05.py | 1661 | 296 | 17.8% | 279 | 17.0% | 70 -> 0 |
| companion/test_companion_app_helpers.py | 197 | 81 | 41.1% | 70 | 37.6% | 3 -> 0 |
| companion/test_config_page_01.py | 658 | 147 | 22.3% | 120 | 19.0% | 57 -> 0 |
| companion/test_config_page_02.py | 2220 | 690 | 31.1% | 629 | 29.1% | 157 -> 0 |
| companion/test_config_page_03.py | 1777 | 508 | 28.6% | 453 | 26.3% | 125 -> 0 |
| companion/test_config_page_04.py | 938 | 216 | 23.0% | 183 | 20.2% | 68 -> 0 |
| companion/test_config_page_04b.py | 1000 | 220 | 22.0% | 187 | 19.3% | 81 -> 0 |
| companion/test_config_page_05.py | 1578 | 321 | 20.3% | 269 | 17.6% | 128 -> 0 |
| companion/test_config_page_helpers.py | 145 | 79 | 54.5% | 42 | 38.9% | 10 -> 0 |
| companion/test_contrast_check.py | 335 | 91 | 27.2% | 91 | 27.2% | 0 -> 0 |
| companion/test_health_offbox.py | 269 | 33 | 12.3% | 29 | 10.9% | 7 -> 0 |
| companion/test_i18n.py | 287 | 61 | 21.2% | 60 | 21.0% | 3 -> 0 |
| companion/test_login_throttle.py | 182 | 40 | 22.0% | 38 | 21.1% | 6 -> 0 |
| companion/test_post_origin.py | 232 | 39 | 16.8% | 38 | 16.4% | 5 -> 0 |
| companion/test_suite_guards.py | 777 | 83 | 10.7% | 83 | 10.7% | 1 -> 0 |
| test-support/companion_app_server.py | 320 | 85 | 26.6% | 83 | 26.1% | 2 -> 0 |
| test-support/companion_markup.py | 594 | 118 | 19.9% | 118 | 19.9% | 1 -> 0 |
| test-support/sitecustomize.py | 26 | 10 | 38.5% | 10 | 38.5% | 0 -> 0 |
| test-support/skypane_test_support.py | 391 | 93 | 23.8% | 93 | 23.8% | 0 -> 0 |
| test-support/test_check_comment_history.py | 545 | 32 | 5.9% | 32 | 5.9% | 0 -> 0 |
| test-support/test_companion_markup.py | 190 | 8 | 4.2% | 8 | 4.2% | 2 -> 0 |
| test-support/test_test_support.py | 284 | 17 | 6.0% | 17 | 6.0% | 0 -> 0 |
| **Family total (29 files)** | **20951** | **4750** | **22.7%** | **4268** | **20.9%** | **1048 -> 0** |

The family total's "before" figures (29 files, 20951 lines, 1048 history hits) match the orchestrator's own scope description (`~21k lines, 23% comments, 1048 hits`) closely (22.7% measured vs. 23% stated, rounding).

`test_suite_guards.py`'s ratio (10.7%) and `test_companion_app_02.py`'s module docstring both stayed unchanged in byte count relative to what a from-scratch purge would otherwise remove, because their module docstrings needed a full content rewrite that the `--allow` exception (see Deviations) makes safe to commit even though same-code cannot verify it without the flag.

### Files still above the ~20%-per-file guideline

`companion/conftest.py` (37.2%), `test_companion_app_helpers.py` (37.6%), `test_config_page_helpers.py` (38.9%), `test-support/sitecustomize.py` (38.5%) sit above the ~20% per-file target the purge_bar states as "where possible." All four are short, fixture-dense files (conftest.py's own scope-rationale comments, the two `*_helpers.py` modules' one-why-paragraph-per-helper shape, and `sitecustomize.py`'s tiny 26-line body where even one why-comment is a large fraction of the file) — the purge_bar's own "keep" list protects genuine why-content (fixture scope rationale, network-guard reasons) in every one of these, and none of them had unpurged history left (all report 0 hits). `companion/test_config_page_02.py` (29.1%), `_03.py` (26.3%), `test_companion_app_01.py` (28.4%), `_03.py` (19.0%, at the boundary) are the dense multi-hundred-test files carrying genuine why-content per assertion (root-safety notes, paint-order/geometry rationale, why a fixture value was chosen) that the purge_bar protects — consistent with 35-15's own finding for the sibling status_pages/view_pages families.

### Purge Bar Exceptions (docstrings/blocks over the 6-line/5-line cap)

None retained over cap. Every module docstring across all 24 edited files was rewritten to at or under 6 lines (several — `test_config_page_03.py`, `test_companion_app_02/03/04/04b/05.py` — were originally 15-27-line multi-paragraph migration-chain narratives, condensed to what/why paragraphs). Multi-paragraph comment blocks carrying a real why (the icon-whitelist growth history in `test_companion_app_01.py`, the root-safety notes throughout the config_page family) were condensed to fit the 5-line cap rather than granted an exception.

## Files Created/Modified

- `companion/test_config_page_01.py` through `_05.py` (including `_04b.py`) and `test_config_page_helpers.py` — the config_page test family; comments purged, code unchanged.
- `companion/test_companion_app_01.py` through `_05.py` (including `_04b.py`) and `test_companion_app_helpers.py` — the companion_app test family; comments purged, code unchanged.
- `companion/test_app_server_fixture.py`, `test_health_offbox.py`, `test_i18n.py`, `test_login_throttle.py`, `test_post_origin.py`, `test_suite_guards.py` — the standalone companion test modules; comments purged, code and guard logic unchanged.
- `companion/conftest.py` — the shared companion test fixture family; comments purged, fixture behaviour unchanged.
- `test-support/companion_app_server.py`, `companion_markup.py`, `test_companion_markup.py` — shared test-support helpers; comments purged, code unchanged.
- `companion/test_contrast_check.py`, `test-support/sitecustomize.py`, `skypane_test_support.py`, `test_test_support.py`, `test-support/test_check_comment_history.py` — verified already clean (0 hits); not modified.

## Decisions Made

See `key-decisions` in the frontmatter above. In short: (1) file ownership followed the orchestrator's own 29-file scope glob, reconciling the plan's stale `files_modified` list (predating Phase 33's final file splits) against the live tree; (2) five files needed no edits at all, confirmed via the check tool before skipping them; (3) the config_page family was hand-edited file-by-file while the companion_app family and remaining small files used a scratch mechanical AST/tokenize-scoped script plus two manual review passes, given the family's combined ~21k-line, 1048-hit size; (4) two accidental string-literal edits during manual work were caught by same-code failing and reverted before any commit; (5) two files (`test_companion_app_02.py`, `test_suite_guards.py`) need a documented, narrowly-scoped `--allow` for same-code because of a `__doc__`-substring false positive in the tool's own module-docstring-preservation heuristic — diagnosed and isolated to exactly the module docstring in both cases.

## Deviations from Plan

### Auto-fixed Issues

None beyond the scope reconciliation and known-clean-file skips described in Decisions Made — no Rule 1-4 auto-fixes were needed in the code itself, since this plan's diffs are comment/docstring-only by construction (same-code proves it for 27 of 29 files with no flag, and for the other 2 with a disclosed, narrowly-scoped exception).

### Known same-code exceptions (disclosed, not a violation of "no --allow" for the other 27 files)

1. **`companion/test_companion_app_02.py`** — its module docstring cannot be edited without `--allow` because the file's own body (at the line documenting `companion/pages/__init__.py`'s docstring-reading ban) contains the literal substring `__doc__`, which trips `same-code`'s own `keep_module_doc = "__doc__" in base_text or "__doc__" in working_text` heuristic (designed for the argparse `--help` pattern in group 2's `illustrations.py`). Verified via a standalone `ast.dump()` diff with `keep_module_doc` forced `False`: the rest of the file is byte-for-byte identical to base; only the module docstring differs, and only because it was purged. `server/.venv/bin/python scripts/check_comment_history.py same-code --base 8a8b8b4 --allow companion/test_companion_app_02.py companion/test_companion_app_02.py` exits 0.
2. **`companion/test_suite_guards.py`** — same root cause, but here `__doc__` is genuinely functional: the guard's own G4 rule checks `node.attr == "__doc__"` to detect a test reading a module's docstring. Its own module docstring (which describes this exact rule) can never be edited without `--allow`, for as long as the guard exists. Verified identically: the rest of the file is byte-for-byte identical to base once `keep_module_doc` is forced `False`.

Both exceptions are scoped to exactly one file's module docstring each; every other span in both files, and every other file in this plan's 29-file scope, passes `same-code --base 8a8b8b4` with no `--allow` at all — the aggregate command `same-code --base 8a8b8b4 <27-file list excluding these two>` exits 0.

## Issues Encountered

- Two rounds of accidental string-literal edits during the config_page family's manual pass (`test_config_page_02.py` twice, `test_config_page_04.py` once, `test_config_page_helpers.py` once) — each caught by `same-code` failing before the task's commit, diagnosed with a small `ast.dump()`-diff script pinpointing the exact differing AST node, and reverted to the byte-identical original before proceeding. No committed file carries an edited string literal.
- The mechanical purge script's first two iterations had real bugs of their own (documented as part of building the tool, not shipped): an unconditional `\(\s*\)` cleanup regex that stripped genuine empty-argument function calls like `escape_html()`/`check()` anywhere in a docstring that had ANY unrelated match elsewhere in the same span, fixed by switching to a sentinel-marker design that only ever touches text adjacent to an actual removed match.
- Multi-line `#`-comment blocks where a parenthetical citation spans two separate `#` lines are invisible to the mechanical script as a single unit (Python's `tokenize` module treats each `#`-prefixed line as an independent `COMMENT` token), leaving a dangling `#)` or stray `/` on the second line — caught in every file by a targeted `grep` pass after the mechanical run, and fixed by hand.

## User Setup Required

None - no external service configuration required.

## Verification Results

- **`check --paths` over the full 29-file scope:** 0 history hits, exit 0.
- **`same-code --base 8a8b8b4` over the 27-file subset excluding the two documented exceptions:** exit 0, no `--allow`, in every case.
- **`same-code --base 8a8b8b4 --allow <file> <file>` for `test_companion_app_02.py` and `test_suite_guards.py`:** exit 0 each; confirmed via a standalone AST-diff script that forcing `keep_module_doc=False` makes both files byte-for-byte identical to base outside the module docstring.
- **`pytest --collect-only -q` over the 29-file scope:** 1014 tests, identical before and after the whole plan.
- **`pytest companion test-support -q -n auto` (the FULL suite, not just the touched files):** 1811 passed, 2 skipped (expected root-permission skips — `companion/test_companion_app_01.py:810`/`:851`), 0 failed, in 285.28s.
- **`ruff check` on the full 29-file scope:** "All checks passed!"
- **TDD gate compliance:** not applicable — this plan's tasks are `type="auto"`, not `tdd="true"`; no RED/GREEN/REFACTOR gate sequence is required.

## Next Phase Readiness

Group 5 (companion tests + test-support) is now fully closed: combined with 35-14's browser family and 35-15's status_pages/view_pages families, every `companion/test_*.py`, `companion/conftest.py` and `test-support/*.py` file in the tree has 0 comment-history hits. Per the orchestrator's own instruction, this plan does not append to `35-COMMENT-RATIO.md` or remove group-5 paths from `scripts/comment-history-pending.txt` — that group-close bookkeeping, along with marking HYG-01 progress in `REQUIREMENTS.md`, is left to 35-17 (or whichever plan the orchestrator designates), consistent with the pattern 35-15 documented for its own sibling plan. The two `--allow`-requiring files (`test_companion_app_02.py`, `test_suite_guards.py`) should be flagged to whichever plan finalizes group 5's own "Proof of no behaviour change" verification, since the group-level `same-code` sweep across ALL of group 5's files will need the same two `--allow` flags this plan's own file-scoped runs used.

---
*Phase: 35-comment-purge-in-english-and-dead-code*
*Completed: 2026-09-25*

## Self-Check: PASSED

- All 24 modified files verified present on disk (`companion/test_config_page_01.py` through `_helpers.py`, `test_companion_app_01.py` through `_helpers.py`, `test_app_server_fixture.py`, `test_health_offbox.py`, `test_i18n.py`, `test_login_throttle.py`, `test_post_origin.py`, `test_suite_guards.py`, `conftest.py`, `test-support/companion_app_server.py`, `companion_markup.py`, `test_companion_markup.py`) — FOUND
- All 16 task commits verified present in `git log --oneline --all`: `110c612`, `33cb249`, `c61e2e4`, `5141c80`, `0e41715`, `77409bd`, `2308537`, `63a77d7`, `af4454c`, `629d672`, `2aa2536`, `95fa38b`, `8ca3469`, `25ec0e4`, `b33a284`, `83a1339` — FOUND
