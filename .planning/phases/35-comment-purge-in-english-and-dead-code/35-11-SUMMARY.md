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
    - "Second pass: a tokenize-based script that groups consecutive `#` COMMENT tokens into blocks and flags any block over 5 lines, plus an ast-based docstring line-counter flagging any over 15 — used to mechanically verify the hard caps file-wide rather than trusting a manual read-through"

key-files:
  created: []
  modified:
    - companion/layout.py
    - companion/draw.py

key-decisions:
  - "First pass only stripped history-ID hits, leaving comment-block/docstring rhetoric and length uncapped; a second pass (after orchestrator review) mechanically re-verified and enforced the plan's hard caps file-wide in both files — see Deviations"
  - "Every function/module docstring in both files now fits at or under the 15-line security/contract cap (most under 12; draw.py's ring_gauge — the orchestrator's flagship example, originally 67 lines — is now 12); every `#` comment block fits at or under 5 lines. No caps exceptions remain in either file"

requirements-completed: []

duration: several hours (exact figure unavailable: session was interrupted mid-plan by an API rate limit and resumed)
completed: 2026-09-25
---

# Phase 35 Plan 11: companion/layout.py + companion/draw.py comment purge Summary

**Purged 458 plan/decision/threat-ID history references from layout.py and 21 from draw.py, then — after an orchestrator review found the first pass had removed IDs but left comment-block/docstring length and rhetoric uncapped — a second pass mechanically applied the plan's hard caps (function docstring <=8 lines, <=15 for a genuine multi-invariant contract; comment block <=5 lines) file-wide in both files. Final ratios: layout.py 65.4% -> 43.0%, draw.py 63.9% -> 44.9%, both with 0 history hits, code byte-for-byte unchanged (`same-code` clean, no `--allow`), and the full non-browser companion suite green.**

## Performance

- **Duration:** several hours (large files: layout.py was 4168 lines, ~65% comments; session interrupted mid-plan by an API rate limit and resumed; a second, orchestrator-requested pass followed the first)
- **Tasks:** 3/3 completed (lower half, upper half, draw.py), plus a second cap-tightening pass across both files
- **Files modified:** 2

## Accomplishments

- **First pass** — `companion/layout.py`: purged in two batches (lower half from `_tab_bar_html()` at the original line 2210 onward, then the upper half including the module docstring), dropping every `NN-NN-PLAN.md`/`D-NN`/`CFG-NN`/`T-NN-NN`/quick-task/`Phase N` reference. `companion/draw.py`: every `CFG-39/40/42/43`, `24-01-PLAN.md`/`24-07-PLAN.md`, `24-RESEARCH.md` and `T-24-04-A`/`T-24-06-A/B/C`/`T-24-07-D` reference removed. Both files reached 0 history hits, but the pass left the surviving prose largely as originally written (long multi-paragraph comment blocks, upper-case rhetoric, several docstrings well over the length caps) — a real gap the orchestrator's review caught.
- **Second pass** (this SUMMARY's final state) — wrote two small verification scripts (a tokenize-based comment-block grouper, an ast-based docstring line-counter) to mechanically find every violation instead of relying on a manual read-through, then rewrote every flagged docstring and comment block in both files: dropped upper-case emphasis ("THE ONE RING EMITTER", "MUST NEVER", "a positive choice rather than a shortcut", "stated so a later caller cannot silently mirror it"), merged or split multi-paragraph `#` blocks so each paragraph is its own <=5-line block separated by a true blank line, and cut every docstring to <=15 lines (most to <=12) while keeping one plain sentence per real invariant. `ring_gauge()` — the orchestrator's flagship example — went from 67 lines of rhetoric to 12 lines covering all six of its invariants (fraction is 0..1 not millivolts, clamped, non-numbers/negatives pin at empty, arc starts at 12 o'clock clockwise, the two degenerate dash cases, the status_class whitelist, aria-hidden since the percentage prints beside it).
- What both passes together kept: the `escape_html()`/`escape()` single-choke-point discipline in both files; the icon-id whitelist as an injection guard; the `duplicated-not-imported` route-constant contract with `companion/app.py`; the accessibility invariant that exactly one "Primary navigation" landmark is ever exposed to the accessibility tree; the no-JS-floor contracts for the hamburger panel, the quick-switch controls, the tab bar and the ring gauge; the i18n ticker-copy/test-equality contracts; the `companion/static/freshness.js` swap-region registry rationale; and draw.py's geometry/units invariants (fixed coordinate domains, SVG dash-route degenerate cases, element-count bounds, measured-pixel derivations).
- `usable_pairs()` and `label_grid()` in `draw.py` are unchanged (dead-code removal is 35-13's job).
- Caught and fixed, mid-first-pass, an over-wide comment-block edit that had accidentally deleted the `QUICK_ACTION_APPLIES_SENTENCE = "..."` assignment statement (a real code line, not a comment) — restored before the next `same-code`/test run, documented under Deviations below.

## Task Commits

1. **Task 1: Purge the lower half of layout.py** - `74cd12c` (refactor)
2. **Task 2: Purge the upper half of layout.py** - `d43d2e8` (refactor, part 1) and `282c47e` (refactor, part 2, includes the QUICK_ACTION_APPLIES_SENTENCE fix)
3. **Task 3: Purge draw.py, then run the tests** - `b96ce97` (refactor)
4. **Second pass (post-review): tighten draw.py to the hard caps** - `f5ecf83` (docs)
5. **Second pass (post-review): tighten layout.py's caps exceptions and cap every comment** - `b124d7d` (docs)

_No TDD tasks in this plan; all five are `type="auto"` comment-only rewrites verified by `same-code`, `check` and the pytest suite._

## Files Created/Modified

- `companion/layout.py` - page shell, nav renderers, timestamp/relative-time helpers, the freshness swap-region registry, the Frame strip and the data-table/stat-tile primitives. 4168 -> 2582 lines; comments 65.4% -> 43.0%; history hits 458 -> 0.
- `companion/draw.py` - shared SVG geometry/emission primitives (percent/unit coordinate schemes, the ring gauge, the day band, the regularity grid). 1367 -> 898 lines; comments 63.9% -> 44.9%; history hits 21 -> 0.

## Ratio (per `check_comment_history.py ratio`)

| File | Lines before | Lines after 1st pass | Comment % before | % after 1st pass | % after 2nd pass (final) | History hits before -> after |
|---|---:|---:|---:|---:|---:|---:|
| companion/layout.py | 4168 | 2830 | 65.4% | 49.1% | 43.0% | 458 -> 0 |
| companion/draw.py | 1367 | 1302 | 63.9% | 62.1% | 44.9% | 21 -> 0 |

## Decisions Made

- Split `layout.py` at `_tab_bar_html()` (the original line 2210, the closest top-level `def` to the file's midpoint) as the plan's conventions instructed, and purged the lower half first.
- Used a small Python line-range replacement script (`apply_repl.py`, kept in the session scratchpad, not committed) rather than the `Edit` tool for the bulk of both files: at ~65%/64% original comment density, single-string `Edit` matches would have needed near-exact reproduction of multi-hundred-line docstrings just to replace a few words; a script that replaces an exact `(start_line, end_line)` span (verified against `dump_spans`/`Read` output before every batch) let each batch stay auditable via `git diff` and `same-code` while moving at the pace this file's size required.
- The first pass treated "0 history hits" as the finish line and under-applied the plan's length/rhetoric caps. The orchestrator's review (citing `ring_gauge()`'s 67-line docstring as the clearest example) was correct: caught, and fixed in a second pass described below.
- Second pass: wrote a tokenize-based script that groups consecutive `#` COMMENT tokens into contiguous blocks and flags any over 5 lines, and an ast-based script that measures every docstring's line count and flags any over 15 — ran both after every edit batch so no violation could hide in a file this size. Multi-paragraph blocks that were previously joined by a blank `#` line (which tokenize still treats as one contiguous block) were re-split with a true blank line between paragraphs, each paragraph independently at or under 5 lines.
- `companion/draw.py`'s module docstring was compressed to the **hard, non-extensible** 10-line module cap (purge_bar states the module cap has no security exception, unlike the function/class cap); the two paragraphs it lost (why the module does not import `companion/battery.py`, and the full `percent_time()`-is-a-third-domain rationale) already live, undiminished, in `ring_gauge()`'s and the `percent_time()` section comment's own docstrings respectively, so no invariant was actually dropped — only relocated to the function that owns it.

## Caps Exceptions

**None remain.** After the second pass, every docstring in both files fits at or under the 15-line security/contract cap (most fit the plain 8-line cap; the longest is 15), and every `#` comment block fits at or under 5 lines. The functions that use the most of the 15-line allowance, each combining multiple independent invariants that would lose real information if compressed further:

| File | Function | Lines | Why it needs the extension |
|---|---|---:|---|
| layout.py | `status_dot`/`data_table`/`absolute_and_relative` | 15 | Each states a whitelist-or-escape XSS invariant plus a distinct fallback/degrade contract. |
| layout.py | `nav_status_html`/`relative_age_text`/`_age_bucket` | 15 | Shared-body no-disagreement contract, or the one shared threshold-ladder definition both time-direction siblings depend on. |
| draw.py | `percent_time`/`day_band` | 15 | Reject-vs-clamp domain contract (DST-aware `day_seconds`) and the collapsed-count/element-bound contract respectively — both proven by dedicated tests. |
| draw.py | `ring_gauge` | 12 | The orchestrator's own flagship example: now states all six invariants (0..1 fraction not millivolts, clamped, 12-o'clock clockwise arc, the two degenerate dash cases, the status whitelist, aria-hidden reasoning) in plain sentences. |

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
- Commit `f5ecf83`: FOUND
- Commit `b124d7d`: FOUND
- `same-code --base 059774e companion/layout.py companion/draw.py`: exit 0 (no `--allow`)
- `check --paths companion/layout.py companion/draw.py`: 0 hits
- `git grep -qw "def usable_pairs" companion/draw.py`: found
- `git grep -qw "def label_grid" companion/draw.py`: found
- `pytest companion -q -n auto -k "not browser"`: 1533 passed, 2 skipped
- `ruff check companion/layout.py companion/draw.py`: all checks passed
- Every function/module docstring in both files: <=15 lines (ast-measured)
- Every `#` comment block in both files: <=5 lines (tokenize-measured)
