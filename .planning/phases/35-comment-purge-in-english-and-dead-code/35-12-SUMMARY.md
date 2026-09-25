---
phase: 35-comment-purge-in-english-and-dead-code
plan: 12
subsystem: companion
tags: [comment-hygiene, i18n, xss-escaping]

requires:
  - phase: 35-comment-purge-in-english-and-dead-code
    provides: "35-07's completion on main (group 3 close, wave-5 gate); the CLI/purge_rules/same-code tooling from 35-02; the comments-only convention from 35-08"
provides:
  - "companion/pages/airlines_page.py, companion/pages/home_page.py and companion/pages/__init__.py comments and docstrings, history-free and in English"
  - "All fourteen companion/i18n_fr/*.py modules' comments and docstrings, history-free and in English, with every French and English string literal byte-identical"
affects: [35-13]

tech-stack:
  added: []
  patterns:
    - "Line-range replacement scripts (Python, not committed) for files where comments interleave with unicode-heavy string literals (curly quotes, em dashes, U+00A0 non-breaking spaces) — the Edit tool's exact-string matching is fragile against those characters; every script run was followed immediately by same-code to catch any accidental string-literal corruption before moving to the next file"
    - "same-code caught two real corruptions during this plan (a display.py rewrite that flattened four U+00A0 non-breaking spaces to plain spaces) — both fixed before commit, documented under Deviations"

key-files:
  created: []
  modified:
    - companion/pages/airlines_page.py
    - companion/pages/home_page.py
    - companion/pages/__init__.py
    - companion/i18n_fr/__init__.py
    - companion/i18n_fr/airlines.py
    - companion/i18n_fr/calendar_group.py
    - companion/i18n_fr/common.py
    - companion/i18n_fr/display.py
    - companion/i18n_fr/flights.py
    - companion/i18n_fr/frame_state.py
    - companion/i18n_fr/health.py
    - companion/i18n_fr/home.py
    - companion/i18n_fr/nav.py
    - companion/i18n_fr/notifications.py
    - companion/i18n_fr/registry.py
    - companion/i18n_fr/rules.py

key-decisions:
  - "companion/pages/__init__.py's module docstring is kept in full (70 lines, far over the 10-line module cap) because the file's only content is the ctx-dict API contract every page module's render(ctx)/handle_post(form, ctx) relies on — condensing it to 10 lines would have deleted the per-key contract (which keys are query-string-derived and re-validated on every use, which reads must never hit the process-scoped cache, which keys default via ctx.get()) rather than its history. Single justification for the whole file rather than one per removed sentence, since the docstring is one coherent reference, not a list of independent facts."
  - "i18n_fr/*.py module docstrings routinely exceed the 10-line cap (11-18 lines each) because each one states which keys are deliberately absent and why (the auto-merge package's duplicate-key ValueError makes this a correctness fact, not history) plus the copy-style rule (sentence case, typographic apostrophe, U+00A0 before punctuation) — both load-bearing for a future editor adding a key. Accepted as a per-file cap exception rather than trimmed further, since the alternative was deleting the duplicate-key cross-references purge_rules require to survive."
  - "Several i18n_fr files stay above the ~35% ratio guideline after two rounds of trimming (see Ratio table) — all are small catalogue files (26-317 lines) where the module docstring plus the per-key duplicate-key/invariant comments dominate a file with few code lines to dilute them against; each was re-read hunting for further cuts before accepting the guideline miss."

requirements-completed: [HYG-01]

duration: several hours
completed: 2026-09-25
---

# Phase 35 Plan 12: airlines/home pages, pages/__init__.py, i18n_fr/*.py comment purge Summary

**Purged 836 plan/decision/threat-ID history references from `companion/pages/airlines_page.py`, `home_page.py`, `pages/__init__.py` and all fourteen `companion/i18n_fr/*.py` catalogue modules, dropping change narratives and restatement while keeping every real why/invariant in one or two plain sentences. Every i18n_fr string literal (French and English) is byte-identical — same-code (AST-equal after docstring removal) passes with no `--allow` on all sixteen files, every file has 0 history hits, and the full non-browser companion pytest suite is green (1545 passed, 129 skipped, all Chromium/Playwright).**

## Performance

- **Duration:** several hours (airlines_page.py alone was 2503 lines at 66% comments, the densest single file this phase has purged)
- **Tasks:** 2/2 completed
- **Files modified:** 16

## Accomplishments

- **Task 1** — `companion/pages/airlines_page.py`: rewrote the module docstring and every function docstring/`#` comment across 2503 lines, dropping every `D-NN`/`CFG-NN`/`WR-NN`/`T-NN-NN`/`Phase N`/`NN-NN-PLAN.md`/quick-task reference and every "previously/now/SUPERSEDED/DELIBERATELY" change-narrative paragraph, while keeping the real invariants: the CR-02 fallback logic (a missing live gap row means "re-validate and fall through", not "nothing to resolve"), the escape-once discipline on every interpolated value, the `panel_attrs` built-once-shared-by-two-triggers contract, the `%s` arity comments on the superseded-note template, and the AttributeError-safety fix in `_gap_card_html()` (`example_callsign` coerced to `str()` before `.lower()`).
- **Task 2** — `companion/pages/home_page.py`: rewrote the module docstring, 20 function docstrings and every inline comment, keeping the day-band's DST-aware `day_seconds` invariant, the `_plain_text_from_markup()` escape-once-not-twice contract, and the `_hero_html()` unconditional-wrapper reasoning. `companion/pages/__init__.py`: rewrote the module docstring to drop every plan/D-id while keeping the full per-key ctx contract (health_severity, resolve_prefix's validate-then-join, manual_resolutions/colour_rules' process-scoped-cache exclusion) — the plan's own note to "rewrite or drop" the `health_severity` mentions was honored by rewriting them concisely; no function in this file was touched. All fourteen `companion/i18n_fr/*.py` modules: rewrote every module docstring and `#` comment (never a string literal) to drop plan/decision references while keeping the duplicate-key cross-references the auto-merge package's `ValueError` makes load-bearing, the copy-style rule (sentence case, U+2019, U+00A0-before-punctuation), and real translation invariants (singular/plural French forms, grammatical-agreement mismatches between shared keys, NBSP-before-unit formatting).
- Ran `same-code`, `check`, `ratio` and `pytest companion -q -n auto -k "i18n or home or airlines or view"` after every file; ran the full `pytest companion -q -n auto` (1545 passed, 129 skipped) and `ruff check` across all sixteen files at the end.

## Task Commits

1. **Task 1: Purge airlines_page.py** - `59c2b90` (refactor)
2. **Task 2: Purge home_page.py, pages/__init__.py and i18n_fr, then run the tests** - `ba9c12f` (refactor)

_No TDD tasks in this plan; both are `type="auto"` comment-only rewrites verified by `same-code`, `check` and the pytest suite._

## Files Created/Modified

- `companion/pages/airlines_page.py` - Airlines gallery, coverage-gap strip and resolve-an-unidentified-flight flow. 2503 -> 1293 lines; comments 66.0% -> 34.5%; history hits 382 -> 0.
- `companion/pages/home_page.py` - Home page: Frame strip, status tiles, day band, current picture and recent flights. 950 -> 696 lines; comments 52.3% -> 34.9%; history hits 89 -> 0.
- `companion/pages/__init__.py` - The ctx-dict API contract every page module's `render(ctx)`/`handle_post(form, ctx)` follows. 176 -> 71 lines; comments 100.0% -> 100.0% (pure-documentation file, see Caps Exceptions); history hits 35 -> 0.
- `companion/i18n_fr/*.py` (14 files) - The French translation catalogue package. See Ratio table below for per-file figures; history hits 330 -> 0 across all fourteen.

## Ratio (per `check_comment_history.py ratio`)

| File | Lines before | Lines after | Comment % before | Comment % after | History hits before -> after |
|---|---:|---:|---:|---:|---:|
| companion/pages/airlines_page.py | 2503 | 1293 | 66.0% | 34.5% | 382 -> 0 |
| companion/pages/home_page.py | 950 | 696 | 52.3% | 34.9% | 89 -> 0 |
| companion/pages/__init__.py | 176 | 71 | 100.0% | 100.0% | 35 -> 0 |
| companion/i18n_fr/__init__.py | 47 | 34 | 51.1% | 32.4% | 3 -> 0 |
| companion/i18n_fr/airlines.py | 140 | 108 | 41.4% | 24.1% | 26 -> 0 |
| companion/i18n_fr/calendar_group.py | 77 | 28 | 68.8% | 32.1% | 15 -> 0 |
| companion/i18n_fr/common.py | 236 | 200 | 27.5% | 14.5% | 20 -> 0 |
| companion/i18n_fr/display.py | 485 | 247 | 63.7% | 29.2% | 102 -> 0 |
| companion/i18n_fr/flights.py | 160 | 110 | 55.6% | 35.5% | 26 -> 0 |
| companion/i18n_fr/frame_state.py | 70 | 26 | 90.0% | 76.9% | 9 -> 0 |
| companion/i18n_fr/health.py | 383 | 317 | 38.9% | 26.2% | 43 -> 0 |
| companion/i18n_fr/home.py | 146 | 94 | 60.3% | 38.3% | 27 -> 0 |
| companion/i18n_fr/nav.py | 101 | 53 | 69.3% | 41.5% | 30 -> 0 |
| companion/i18n_fr/notifications.py | 72 | 44 | 62.5% | 38.6% | 16 -> 0 |
| companion/i18n_fr/registry.py | 59 | 46 | 54.2% | 41.3% | 3 -> 0 |
| companion/i18n_fr/rules.py | 74 | 44 | 63.5% | 45.5% | 10 -> 0 |
| **Plan total** | **5679** | **3411** | **60.2%** | **34.1%** | **836 -> 0** |

## Decisions Made

- `companion/pages/airlines_page.py` and `companion/pages/home_page.py` (the two page modules, dominated by real code) both landed under the 35% guideline (34.5%, 34.9%) after the standard purge — no caps exceptions needed there.
- `companion/pages/__init__.py` is a pure-documentation file: no statements beyond the module docstring, 100% comment by construction — kept at its full, condensed-but-complete docstring rather than gutted to fit the module cap; see Caps Exceptions.
- Every `i18n_fr/*.py` module docstring keeps its "deliberately absent, reused from sibling module" cross-reference list (condensed to a parenthetical rather than a bulleted enumeration) because the auto-merge package's `ValueError` on a duplicate key makes this a correctness fact a future editor adding a key must know, not project history.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] A line-range rewrite of `companion/i18n_fr/display.py` flattened four U+00A0 non-breaking spaces to plain spaces**
- **Found during:** Task 2, immediately after rewriting the "Quiet hours"/"Device-only groups"/"Save" sections of `display.py` via a Python line-range replacement script
- **Issue:** The replacement script's new French string values ("# s", "# min", "# h", "# j", the wake-interval sentence, the poll-triggered flash) were retyped with a literal space where the original held `\xa0` (a real non-breaking space, per this module's own D-09 formatting rule) — `same-code --base` failed (AST string-constant mismatch), which is exactly the guard the plan's threat model names for this risk.
- **Fix:** Located the four exact strings via an AST diff between the base and working versions, restored `\xa0` in each, re-ran `same-code` (clean).
- **Files modified:** `companion/i18n_fr/display.py`
- **Verification:** `same-code --base <group-base> companion/i18n_fr/display.py` exits 0; `check` reports 0 hits.
- **Committed in:** `ba9c12f` (fixed before commit, so no separate commit exists for it)

**2. [Rule 1 - Bug] A stray Python one-liner truncated `companion/i18n_fr/home.py` to an empty file mid-edit**
- **Found during:** Task 2, while drafting a line-range replacement for `home.py`
- **Issue:** An exploratory script opened the file in `"w"` mode to sanity-check a plan and never wrote content back, truncating it to 0 bytes before the real rewrite ran.
- **Fix:** `git checkout -- companion/i18n_fr/home.py` restored the pre-edit content immediately (before any commit), then the intended rewrite was redone correctly.
- **Files modified:** `companion/i18n_fr/home.py`
- **Verification:** File restored to its original 146 lines before the real edit; final `same-code`/`check`/`ratio`/`ruff` all pass.
- **Committed in:** n/a (caught and reverted before any commit touched this file)

---

**Total deviations:** 2 auto-fixed (both Rule 1 - bugs introduced by this plan's own tooling, caught by `same-code`/`git checkout` before commit)
**Impact on plan:** No scope creep; both were mechanical slips in the purge tooling itself, not judgment calls about what to keep or cut. Neither reached a commit.

## Caps Exceptions

Per-item justification for every docstring/file exceeding a hard cap in the purge_bar:

| File | Cap | Actual | Justification |
|---|---|---:|---|
| companion/pages/__init__.py | Module docstring <=10 lines | 70 lines | The file's only content is the ctx-dict API contract every page module's `render(ctx)`/`handle_post(form, ctx)` relies on — which keys are query-string-derived and re-validated on every use (`resolve_prefix`, `flights_limit`), which reads must never hit the process-scoped cache (`manual_resolutions`, `colour_rules`), which keys default via `ctx.get()` for `render({})` call-site parity. Condensing to 10 lines would delete the contract, not its history. Single exception for the whole file. |
| companion/i18n_fr/airlines.py | Module docstring <=10 lines | 12 lines | States which keys are reused from sibling modules (a duplicate-key `ValueError` risk) plus the copy-style rule; both load-bearing. |
| companion/i18n_fr/common.py | Module docstring <=10 lines | 11 lines | Same reason: the two FLASH_MESSAGES keys deliberately absent here, plus copy style. |
| companion/i18n_fr/display.py | Module docstring <=10 lines | 17 lines | Three keys reused from sibling modules, the registry/theme-label indirection, and copy style — the file with the most cross-references in the group. |
| companion/i18n_fr/flights.py | Module docstring <=10 lines | 14 lines | Nine keys reused from four different sibling modules, condensed to one parenthetical list; still over 10 lines at that density. |
| companion/i18n_fr/frame_state.py | Module docstring <=10 lines | 18 lines | Documents a real, currently-unresolved grammatical-agreement mismatch between this module's copy and two sibling entries sharing the same English key — dropping it would silently re-open a known translation bug for a future editor. |
| companion/i18n_fr/health.py | Module docstring <=10 lines | 13 lines | Copy style plus the U+00A0-before-unit rule with a concrete example, needed since this module owns the relative-time ladder every quantity string in it must match byte-for-byte. |
| companion/i18n_fr/home.py | Module docstring <=10 lines | 12 lines | The "Home" key's reuse from nav.py, plus copy style. |
| companion/i18n_fr/nav.py | Module docstring <=10 lines | 14 lines | The seven fixed nav labels enumerated (locked copy, not discretionary), plus the cross-module grouping rationale for the landmark/theme-picker strings this file also carries. |
| companion/i18n_fr/notifications.py | Module docstring <=10 lines | 15 lines | Six keys deliberately absent (read through a different module's `body_for_lang()`, never `i18n.t()`) — a real routing fact, not history. |
| companion/i18n_fr/registry.py | Module docstring <=10 lines | 14 lines | Explains the id-vs-label distinction and the display-site translation pattern this cross-page catalogue depends on. |
| companion/i18n_fr/rules.py | Module docstring <=10 lines | 16 lines | Six keys deliberately absent plus the identifier/data exclusion (rule keys and theme ids are never translated) — both correctness facts. |

## Files still above the ~35% ratio guideline

Each was re-read once more hunting for further cuts (dropping section-header comments entirely, shortening multi-line why-comments to one line) before accepting the guideline miss — all are small catalogue files where the module docstring dominates a file with few code lines to dilute it against.

| File | After | Justification |
|---|---:|---|
| companion/pages/__init__.py | 100.0% | Pure-documentation file: the entire file is the module docstring described in Caps Exceptions above. Every line is a comment by construction; there is no code to change the ratio. |
| companion/i18n_fr/frame_state.py | 76.9% | Smallest file in the group (26 lines, 3 key/value pairs) carrying a genuinely load-bearing docstring (the unresolved grammatical-agreement mismatch above) — three catalogue entries cannot dilute a docstring that size below 35%. |
| companion/i18n_fr/rules.py | 45.5% | 44 lines, 9 key/value pairs; docstring states 7 absent keys plus the identifier/data exclusion. |
| companion/i18n_fr/nav.py | 41.5% | 53 lines; docstring enumerates 7 locked nav labels plus cross-module grouping. |
| companion/i18n_fr/registry.py | 41.3% | 46 lines; the id-vs-label distinction is necessarily stated once. |
| companion/i18n_fr/notifications.py | 38.6% | 44 lines; 6 keys deliberately routed through a different resolver. |
| companion/i18n_fr/home.py | 38.3% | 94 lines; one key reused from nav.py plus copy style, on a file with modest code volume. |
| companion/i18n_fr/flights.py | 35.5% | 110 lines; nine cross-module key reuses condensed to one line each. |

## Issues Encountered

None beyond the two auto-fixed deviations above, both caught before any commit.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- All 16 files in this plan's `files_modified` list have 0 history hits, pass `same-code` with no `--allow`, and pass the full non-browser companion pytest suite (1545 passed, 129 skipped, all pre-existing Chromium/Playwright skips) plus `ruff check`.
- `companion/pages/` and `companion/i18n_fr/` are now fully purged for this wave; 35-13 (group 4 close, per 35-08/35-11's own notes) is unblocked to proceed with `companion/` dead-code removal (`health_severity`, `anomaly_active`, `usable_pairs`, `label_grid`) without this plan's files being mid-purge.
- No blockers.

## Known Stubs

None.

## Threat Flags

None — no new network endpoints, auth paths, file-access patterns or schema changes were introduced; this plan only rewrote comments and docstrings, and same-code proves every file's code is byte-for-byte unchanged.

## Self-Check: PASSED

- `companion/pages/airlines_page.py`: FOUND
- `companion/pages/home_page.py`: FOUND
- `companion/pages/__init__.py`: FOUND
- `companion/i18n_fr/__init__.py`: FOUND
- `companion/i18n_fr/airlines.py`: FOUND
- `companion/i18n_fr/calendar_group.py`: FOUND
- `companion/i18n_fr/common.py`: FOUND
- `companion/i18n_fr/display.py`: FOUND
- `companion/i18n_fr/flights.py`: FOUND
- `companion/i18n_fr/frame_state.py`: FOUND
- `companion/i18n_fr/health.py`: FOUND
- `companion/i18n_fr/home.py`: FOUND
- `companion/i18n_fr/nav.py`: FOUND
- `companion/i18n_fr/notifications.py`: FOUND
- `companion/i18n_fr/registry.py`: FOUND
- `companion/i18n_fr/rules.py`: FOUND
- Commit `59c2b90`: FOUND
- Commit `ba9c12f`: FOUND
- `same-code --base <group-base> <all 16 files>`: exit 0 (no `--allow`)
- `check --paths <all 16 files>`: 0 hits
- `pytest companion -q -n auto -k "i18n or home or airlines or view"`: 290 passed, 18 skipped
- `pytest companion -q -n auto` (full suite): 1545 passed, 129 skipped
- `ruff check companion/pages/airlines_page.py companion/pages/home_page.py companion/pages/__init__.py companion/i18n_fr/`: all checks passed

---
*Phase: 35-comment-purge-in-english-and-dead-code*
*Completed: 2026-09-25*
