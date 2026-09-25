---
phase: 35-comment-purge-in-english-and-dead-code
plan: 11
subsystem: companion
tags: [comment-hygiene, xss-escaping, accessibility, svg-geometry, i18n]

requires:
  - phase: 35-comment-purge-in-english-and-dead-code
    provides: "35-08's purge of companion/app.py, auth.py and the small companion modules; the CLI/purge_rules/same-code tooling from 35-02"
provides:
  - "companion/layout.py comments and docstrings, history-free and in English"
  - "companion/draw.py comments and docstrings, history-free and in English"
affects: [35-13]

tech-stack:
  added: []
  patterns:
    - "Docstring/comment rewrite via a line-range replacement script (apply_repl.py) driven by exact (start_line, end_line) spans read with the Read tool, applied bottom-up — used because Edit's exact-string matching is impractical at this file's original comment density (~65%/64%)"

key-files:
  created: []
  modified:
    - companion/layout.py
    - companion/draw.py

key-decisions:
  - "layout.py's module/function docstrings that mix an XSS-escaping contract, an accessibility invariant, or a cross-file swap-registry/test-pinning contract are kept above the normal 8/15-line docstring cap, each listed below with a one-line justification, per purge_bar's exception rule"
  - "draw.py's per-function why-comments (fixed geometry domains, SVG dash-route degenerate cases, element-count bounds, measured-pixel derivations) were left largely as originally written once their history-ID references were stripped, since they are exactly the geometry/invariant content purge_rules require to survive — only the module docstring was compressed to fit the hard 10-line module cap"

requirements-completed: []

duration: several hours (exact figure unavailable: session was interrupted mid-plan by an API rate limit and resumed)
completed: 2026-09-25
---

# Phase 35 Plan 11: companion/layout.py + companion/draw.py comment purge Summary

**Purged 458 plan/decision/threat-ID history references from layout.py and 21 from draw.py — layout.py's comment ratio fell 65.4% -> 49.1% and draw.py's 63.9% -> 62.1%, both with 0 remaining history hits, code byte-for-byte unchanged (`same-code` clean, no `--allow`), and the full non-browser companion suite green.**

## Performance

- **Duration:** several hours (large files: layout.py was 4168 lines, ~65% comments; session interrupted mid-plan by an API rate limit and resumed)
- **Tasks:** 3/3 completed (lower half, upper half, draw.py)
- **Files modified:** 2

## Accomplishments

- `companion/layout.py`: purged in two passes (lower half from `_tab_bar_html()` at the original line 2210 onward, then the upper half including the module docstring), dropping every `NN-NN-PLAN.md`/`D-NN`/`CFG-NN`/`T-NN-NN`/quick-task/`Phase N` reference while keeping: the `escape_html()` single-choke-point discipline; the icon-id whitelist as an injection guard; the `duplicated-not-imported` route-constant contract with `companion/app.py`; the accessibility invariant that exactly one "Primary navigation" landmark is ever exposed to the accessibility tree; the no-JS-floor contracts for the hamburger panel, the quick-switch controls and the tab bar; the i18n ticker-copy/test-equality contracts; and the `companion/static/freshness.js` swap-region registry rationale (why each page's regions are what they are, and what is deliberately excluded).
- `companion/draw.py`: every `CFG-39/40/42/43`, `24-01-PLAN.md`/`24-07-PLAN.md`, `24-RESEARCH.md` and `T-24-04-A`/`T-24-06-A/B/C`/`T-24-07-D` reference removed; the module docstring rewritten to fit the 10-line module cap while keeping the mandatory `escape()` choke point, the two-coordinate-scheme (`percent_*` vs `unit_*`) boundary, and the no-JS/import-boundary contract. The dense per-function geometry why-comments (fixed domains, SVG dash-route degenerate cases, element-count bounds, measured-pixel derivations) were otherwise left as written, since they are exactly the invariant/units content purge_rules require to keep.
- `usable_pairs()` and `label_grid()` in `draw.py` are unchanged (dead-code removal is 35-13's job).
- Caught and fixed, mid-pass, an over-wide comment-block edit that had accidentally deleted the `QUICK_ACTION_APPLIES_SENTENCE = "..."` assignment statement (a real code line, not a comment) — restored before the next `same-code`/test run, documented under Deviations below.

## Task Commits

1. **Task 1: Purge the lower half of layout.py** - `74cd12c` (refactor)
2. **Task 2: Purge the upper half of layout.py** - `d43d2e8` (refactor, part 1) and `282c47e` (refactor, part 2, includes the QUICK_ACTION_APPLIES_SENTENCE fix)
3. **Task 3: Purge draw.py, then run the tests** - `b96ce97` (refactor)

_No TDD tasks in this plan; all three are `type="auto"` comment-only rewrites verified by `same-code`, `check` and the pytest suite._

## Files Created/Modified

- `companion/layout.py` - page shell, nav renderers, timestamp/relative-time helpers, the freshness swap-region registry, the Frame strip and the data-table/stat-tile primitives. 4168 -> 2830 lines; comments 65.4% -> 49.1%; history hits 458 -> 0.
- `companion/draw.py` - shared SVG geometry/emission primitives (percent/unit coordinate schemes, the ring gauge, the day band, the regularity grid). 1367 -> 1302 lines; comments 63.9% -> 62.1%; history hits 21 -> 0.

## Ratio (per `check_comment_history.py ratio`)

| File | Lines before | Lines after | Comment % before | Comment % after | History hits before -> after |
|---|---:|---:|---:|---:|---:|
| companion/layout.py | 4168 | 2830 | 65.4% | 49.1% | 458 -> 0 |
| companion/draw.py | 1367 | 1302 | 63.9% | 62.1% | 21 -> 0 |

## Decisions Made

- Split `layout.py` at `_tab_bar_html()` (the original line 2210, the closest top-level `def` to the file's midpoint) as the plan's conventions instructed, and purged the lower half first.
- Used a small Python line-range replacement script (`apply_repl.py`, kept in the session scratchpad, not committed) rather than the `Edit` tool for the bulk of both files: at ~65%/64% original comment density, single-string `Edit` matches would have needed near-exact reproduction of multi-hundred-line docstrings just to replace a few words; a script that replaces an exact `(start_line, end_line)` span (verified against `dump_spans`/`Read` output before every batch) let each batch stay auditable via `git diff` and `same-code` while moving at the pace this file's size required.
- `companion/layout.py`'s module docstring and several function docstrings that mix an XSS-escaping contract, an ARIA/accessibility invariant, or a cross-file test-pinning contract are kept above the plan's normal 8-line (15 for security/contract) docstring cap. Each is listed below with a one-line justification, per the purge_bar's own exception rule.
- `companion/draw.py`'s module docstring was compressed hard to fit the **hard, non-extensible** 10-line module cap (purge_bar states the module cap has no security exception, unlike the function/class cap); the two paragraphs it lost (why the module does not import `companion/battery.py`, and the full `percent_time()`-is-a-third-domain rationale) already live, undiminished, in `ring_gauge()`'s and the `percent_time()` section comment's own docstrings respectively, so no invariant was actually dropped — only relocated to the function that owns it.

## Caps Exceptions

Docstrings kept above the plan's 8-line (15 for security/contract) cap, each earning it by combining multiple independent XSS/accessibility/contract invariants in one function:

| File | Function | Lines | Justification |
|---|---|---:|---|
| layout.py | `nav_status_html` | 30 | Combines the shared-body no-disagreement contract, the `device_config` no-context degrade, the plain-`<a>`-no-script no-JS floor, the escaping/`i18n.t()` discipline, and the Home-page no-self-link accessibility fix — five distinct correctness points in one reminder-rendering function. |
| layout.py | `data_table` | 28 | The core "why" of this file's central escaping contract: `mono_columns`/`raw_columns`/`desc_columns`/`prose`/`modifier` are five independently-scoped parameters, and `raw_columns` alone carries the XSS invariant that reopens a real defect class if a caller passes a bare string. |
| layout.py | `page_header` | 26 | A signature-compatibility contract (many call sites depend on exact parameter order) plus a separate raw-markup XSS-escaping contract plus the `FLASH_SLOT_MARKER` splice-point contract — three independent invariants a later editor must not conflate. |
| layout.py | `relative_time_html` | 23 | The no-JS-floor contract, the raw-markup XSS-interpolation contract, and the `countdown`/`static_text` two-parameter state machine, each load-bearing on its own. |
| layout.py | `sidebar_nav` | 22 | The `health_alert` raw-markup-interpolation invariant plus the `aria-current` single-active-link accessibility invariant plus the `device_config` no-context degrade. |
| layout.py | `concise_timestamp_html` | 22 | The visible-format contract, the `title`-is-always-day-qualified invariant, the raw-markup XSS contract, and the explicit "not superseded by `absolute_and_relative()`" note that stops a future edit from deleting a still-needed sibling. |
| layout.py | `frame_strip_html` | 21 | One shared body for two pages (so they cannot disagree) plus a `return_to` redirect-target validation note plus the `data-quick-switch` JS-hook dependency plus the full-function escaping/translation discipline. |
| layout.py | `status_row` | 20 | The XSS-safe state-to-class-name whitelist (never a bare interpolation of caller-controlled `state`) plus the caller-does-the-translating contract. |
| layout.py | `quick_switch_html` | 19 | The `is_on`/posted-state-is-always-the-opposite no-JS invariant (a real correctness trap for a future editor) plus the redirect-target server-validation note plus the nested-form `form_id` workaround. |
| layout.py | `icon_html` | 17 | The fragment-reference injection-guard whitelist (the same class of invariant `status_row()`'s and `data_table()`'s docstrings state) plus the `aria-hidden` decorative-icon accessibility rule. |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] An over-wide comment-block edit deleted a real assignment statement**
- **Found during:** Task 2 (purging the upper half of `layout.py`), while applying a batch of comment-block replacements around the `QUICK_ACTION_APPLIES_SENTENCE` constant
- **Issue:** One replacement's `end_line` was set to the line *after* the comment block ended, which happened to be the code line `QUICK_ACTION_APPLIES_SENTENCE = "Applies the next time the frame wakes up."` — the line-range replacement script overwrote it along with the comment, silently deleting a module-level constant that `_FRAME_DELAY_UNKNOWN_TEXT = QUICK_ACTION_APPLIES_SENTENCE` still referenced later in the same file (a `NameError` waiting to happen at import time).
- **Fix:** Caught immediately by the next `same-code --base 059774e` check (it failed, and diffing the AST dump located the missing `Assign` node); re-inserted the exact original assignment statement at its original position via a targeted `Edit`.
- **Files modified:** `companion/layout.py`
- **Verification:** `same-code` re-run clean; `python -c "import companion.layout"` succeeds; full non-browser companion suite green (1533 passed, 2 skipped, both pre-existing root-euid skips).
- **Committed in:** `282c47e` (part of the same task commit — the fix landed before that commit, so no separate commit exists for it)

None - otherwise plan executed exactly as written.

## Known Stubs

None.

## Threat Flags

None — no new network endpoints, auth paths, file-access patterns or schema changes were introduced; this plan only rewrote comments and docstrings.

## Self-Check: PASSED

- `companion/layout.py`: FOUND
- `companion/draw.py`: FOUND
- Commit `74cd12c`: FOUND
- Commit `d43d2e8`: FOUND
- Commit `282c47e`: FOUND
- Commit `b96ce97`: FOUND
- `same-code --base 059774e companion/layout.py companion/draw.py`: exit 0 (no `--allow`)
- `check --paths companion/layout.py companion/draw.py`: 0 hits
- `git grep -qw "def usable_pairs" companion/draw.py`: found
- `git grep -qw "def label_grid" companion/draw.py`: found
- `pytest companion -q -n auto -k "not browser"`: 1533 passed, 2 skipped
- `ruff check companion/layout.py companion/draw.py`: all checks passed
