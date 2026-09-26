---
phase: 35-comment-purge-in-english-and-dead-code
plan: 19
subsystem: ui
tags: [css, comment-hygiene, style.css, companion]

requires:
  - phase: 35-comment-purge-in-english-and-dead-code
    provides: 35-18 (group 6, companion static JS purge and close) — the comment-history CLI, the ratchet's pending list, and the 35-COMMENT-RATIO.md table this plan appends to
provides:
  - companion/static/style.css purged of every plan/ticket/decision/quick-task history reference in comments, English-only, file header shrunk to 13 lines
  - style.css removed from scripts/comment-history-pending.txt (the CLI's argument-less `check` now exits 0 for every tracked file)
  - a group-7 section in 35-COMMENT-RATIO.md with the per-file ratio and shipped raw/gzip byte counts before and after
affects: [35-20, 35-21, any future companion-CSS work]

tech-stack:
  added: []
  patterns:
    - "Bottom-up, line-range comment replacement via a small Python helper (edit_lib.apply_edits), verified against exact /* ... */ boundaries before every write, so a same-code failure is caught before a commit rather than after"

key-files:
  created:
    - .planning/phases/35-comment-purge-in-english-and-dead-code/35-19-SUMMARY.md
  modified:
    - companion/static/style.css
    - scripts/comment-history-pending.txt
    - .planning/phases/35-comment-purge-in-english-and-dead-code/35-COMMENT-RATIO.md

key-decisions:
  - "Split the file into 9 bottom-up sections (~1000-1500 lines each) instead of the plan's suggested 2 (S1/S2), one commit per section, for interruption resilience per the orchestrator's instruction"
  - "Kept only comments matching: WCAG contrast/target-size facts with numbers, cross-browser quirks (Safari <summary> markers, <dialog>/showModal() colour inheritance, @starting-style support), specificity/cascade traps (the recurring [hidden]-vs-author-display collision, equal-specificity-plus-source-order idiom, presentation-attribute-vs-CSS-declaration trap), magic-number rationale, and JS/markup/test contracts — everything else (plan/ticket IDs, SUPERSEDED/RETIRED narratives, measured-and-found-inert methodology prose, French developer quotes) was deleted"
  - "File header rewritten from 162 lines to 13 (the ~12-line cap plus opening/closing delimiters), keeping only: no-build-step scope, accent/border reservation rules, and the theming mechanism"
  - "Did not mark HYG-01/HYG-02 as complete and did not merge origin/main, push, or open a PR — per explicit orchestrator instruction for this sequential sub-plan run"

requirements-completed: []

duration: ~3h (across one mid-session interruption; the orchestrator discarded one in-progress, not-yet-committed section after a rate-limit pause and this run redid it correctly)
completed: 2026-09-26
---

# Phase 35 Plan 19: companion/static/style.css comment purge (group 7 close) Summary

**Purged all 830 history references from companion/static/style.css's comments across 9 bottom-up sections, cutting the file from 512795 to 140426 raw bytes (72.6% smaller, 170819 -> 36735 bytes gzipped) with zero CSS token changes, then closed group 7 of the phase's comment-history ratchet.**

## Performance

- **Duration:** ~3h wall time (includes a mid-session pause: the orchestrator caught and discarded one section's uncommitted, boundary-broken edit after an API rate-limit interruption; this run resumed from the last clean commit and redid that section with pre-apply boundary verification)
- **Tasks:** 3 (S2 purge, S1 purge + browser tests, group close) — executed as 9 section commits + 1 pending-list/ratio-doc close commit
- **Files modified:** 3 (style.css, scripts/comment-history-pending.txt, 35-COMMENT-RATIO.md)

## Accomplishments

- `companion/static/style.css`: 10689 -> 4793 lines, 64.0% -> 19.7% comment ratio, 830 -> 0 history hits, 0 remaining `check` hits
- Shipped size: 512795 -> 140426 raw bytes, 170819 -> 36735 gzip bytes (both measured with `wc -c` / `gzip -c | wc -c`, matching the plan's baseline methodology)
- `same-code --base 0b3d61c companion/static/style.css` exits 0 with no `--allow` (CSS token stream, comments stripped, is byte-identical to base)
- Full suite green: 2691 passed, 5 skipped, coverage 93.24% (gate 93.0%); `ruff check .` clean
- `SKYPANE_REQUIRE_BROWSER=1 pytest companion -q -n auto -k "browser or contrast or theme"` (258 tests, which render and measure this stylesheet in a real headless Chromium) passes
- `scripts/comment-history-pending.txt` no longer lists style.css; the argument-less `check` command exits 0 for every tracked file in the repo (every prior group's paths plus this one are now enforced)

## Task Commits

Each section was committed atomically, bottom-up through the file (S2 first, then S1):

1. `ef6edc8` — style.css lines 9464-10689 (tab bar, aspect card)
2. `c86c189` — style.css lines 8447-9463 (home page, Phase 18 audit block)
3. `5fd1df5` — style.css lines 7296-8446 (desktop dashboard shell, lightbox)
4. `9d58531` — style.css lines 6261-7295 (charts, Airlines gallery)
5. `8b0d612` — style.css lines 5297-6260 (stat tiles, dashboard grid) — completes S2
6. `3187275` — style.css lines 4032-5296 (data table, History cards)
7. `9a03c9e` — style.css lines 2545-4031 (forms, buttons, selectable cards)
8. `2c54b63` — style.css lines 1308-2544 (quiet-hours dial, nav shell)
9. `10e802f` — style.css lines 1-1307 (file header, tokens, keyframes, nav shell) — completes S1
10. `163029b` — group 7 close: pending-list removal + 35-COMMENT-RATIO.md group-7 section

_Note: this plan is `type="execute"`, not TDD — there is no test -> feat -> refactor cycle; each commit is a `docs(35-19):` comment-only edit._

## Files Created/Modified

- `companion/static/style.css` — every comment purged of plan/ticket/decision/quick-task-ID references and SUPERSEDED/RETIRED narratives; CSS declarations byte-for-byte unchanged (proven by `same-code`)
- `scripts/comment-history-pending.txt` — `companion/static/style.css` line removed
- `.planning/phases/35-comment-purge-in-english-and-dead-code/35-COMMENT-RATIO.md` — group-7 section appended with the before/after ratio table and shipped-byte totals

## Decisions Made

- **9 sections instead of the plan's 2 (S1/S2):** the orchestrator's instruction to commit every ~1000-1500 lines for interruption resilience took precedence over the plan's own `<conventions>` block, which only asked for a single S1/S2 split point recorded at the midpoint. Each section was still processed bottom-up as instructed, and S1/S2 remain identifiable as "sections 1-5" (S2, 9464 down to 5297) and "sections 6-9" (S1, 4032 down to 1).
- **Keep-list interpreted narrowly, per the orchestrator's `<purge_bar>`:** only WCAG facts, browser-specific workarounds, specificity/cascade traps, magic-number rationale, and JS/markup/test contracts survive as comments (plus short section headers). Several recurring patterns worth naming, since they appear many times across the file and were each kept once at a representative site and trimmed to a pointer or dropped as redundant elsewhere: the `[hidden]`-vs-author-`display` collision (an author `display` declaration always beats the UA `[hidden] { display: none }` rule regardless of source order), the equal-specificity-plus-later-source-order idiom (`.logout-form button` vs. `button[type="submit"]` and its many siblings), and the presentation-attribute-vs-CSS-declaration trap on SVG drawings (a CSS declaration of any specificity beats a presentation attribute, so several rules deliberately declare *no* `fill`/`stroke-width`/`r`).
- **File header rewritten to 13 lines** (from 162): kept the no-build-step/zero-external-reference scope, the accent-reservation and border-is-structural-only rules, and the theming mechanism (`:root` + `prefers-color-scheme` + `data-ui-theme` override, contrast-separation enforced by `test_contrast_check.py`). The exhaustive prose list of every historical accent-reservation addition (Phase 06.6 through Phase 30) was dropped — the list itself is still enforced by the same test, not by the comment.
- **Two apparent worktree/HTML boundary mistakes were caught and fixed before committing**, both from the recurring risk of guessing a comment's closing line rather than reading it: an inline `transition: opacity var(--motion-fast) ease;` declaration was accidentally deleted when a comment's end line was miscounted (caught immediately by `same-code` failing after the very first section, fixed before that section's commit), and — mid-session, after an interruption — a batch of edits that cut two comments mid-sentence and deleted a whole rule (`.field-inline-value`) was caught by the orchestrator's own `same-code` check on the uncommitted diff and discarded; this run re-verified every edit's `/* ... */` boundaries programmatically (via a small `verify_edits` helper) against the *current* file content before applying any edit, and re-ran `same-code` immediately after every apply and before every commit, per the orchestrator's follow-up instruction.
- **Global `(WR-02)` fallback-comment cleanup:** discovered mid-purge that this file's repeated "fallback for browsers without color-mix() (WR-02)" idiom carried a history ID in every occurrence (8 sites across the file, only one of which was in the section then being processed); fixed file-wide in one pass rather than waiting to reach each site's own section, since the fix was mechanical and safe (comment-only) wherever it landed.
- **Did not run `requirements mark-complete` for HYG-02, did not merge `origin/main`, did not push, and did not open a PR** — the orchestrator's `<sequential_execution>` instructions for this run explicitly excluded all four, deferring them to the orchestrator itself.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Accidentally deleted CSS declaration during first section's comment edit, caught by `same-code` before commit**
- **Found during:** Task 1 (S2 purge, first section)
- **Issue:** A comment-replacement line range for the `.theme-live-preview__image` crossfade rule was miscounted by one line, deleting the trailing `transition: opacity var(--motion-fast) ease;` declaration along with the comment above it.
- **Fix:** Restored the declaration with a targeted `Edit`, re-ran `same-code`, confirmed it passed before committing that section.
- **Files modified:** `companion/static/style.css`
- **Verification:** `same-code --base 0b3d61c companion/static/style.css` exits 0
- **Committed in:** `ef6edc8` (the fix landed before this section's commit, not as a separate commit)

**2. [Rule 1 - Bug] Boundary-broken batch edit mid-session, caught by the orchestrator and corrected on resume**
- **Found during:** Task 1 (S2 purge, section covering lines 7296-8446), after an API rate-limit interruption
- **Issue:** A batch of ~56 comment replacements for the desktop-shell/lightbox section included several line ranges that were off by a few lines, cutting two comments mid-sentence (leaving stray trailing prose like `* itself is smaller now, on purpose. */` as bare CSS tokens before `.lightbox--wide {`) and deleting the entire `.field-inline-value { margin-left: var(--space-xs); white-space: nowrap; }` rule along with its preceding comment.
- **Fix:** The orchestrator discarded the uncommitted diff (`git checkout -- companion/static/style.css`) before this run resumed. On resume, every edit range for that section was re-verified against the actual file content (a `verify_edits` helper confirming each range's stripped text starts with `/*` and ends with `*/`) before applying, catching and correcting all mis-bounded ranges up front; `same-code` was then run immediately after applying and again before committing.
- **Files modified:** `companion/static/style.css`
- **Verification:** `same-code --base 0b3d61c companion/static/style.css` exits 0; `grep -n "field-inline-value"` shows the rule intact
- **Committed in:** `5fd1df5`

---

**Total deviations:** 2 auto-fixed (both Rule 1 — accidental code-deletion bugs from comment-range miscounting, both caught by `same-code` before any commit)
**Impact on plan:** Both were process errors in this run's own editing tool, not defects in the plan or the existing codebase; both were caught before landing in git history. No scope creep — the fixes only restored code the purge should never have touched.

## Issues Encountered

- Mid-session API rate-limit interruption (see Deviation 2 above) required the orchestrator to intervene and discard one section's uncommitted work; this run resumed cleanly from the last good commit (`c86c189`) with `git status`/`git log`/`same-code` per the resume instructions, and redid the discarded section with stricter pre-apply verification for the remainder of the plan.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Group 7 (`companion/static/style.css`) is closed: `scripts/comment-history-pending.txt` no longer lists it, and the CLI's argument-less `check` exits 0 for every tracked file the tool can scan.
- HYG-02 (`companion/static/style.css` and the companion JS files) is now technically satisfied by groups 6+7 together, but per the orchestrator's instruction this run does **not** mark it complete in REQUIREMENTS.md — that is left to the orchestrator's own bookkeeping.
- 35-20 (group 8: deploy/, scripts/, .github/, root config, adsb-test/, hardware/) and 35-21 (group 9: firmware, behind gate G-34) are unblocked by this plan and ready to run next per the phase's wave ordering.

## Self-Check: PASSED

All 10 commit hashes (`ef6edc8`, `c86c189`, `5fd1df5`, `9d58531`, `8b0d612`, `3187275`, `9a03c9e`, `2c54b63`, `10e802f`, `163029b`) found in `git log`. `companion/static/style.css` and this SUMMARY.md both exist on disk.

---
*Phase: 35-comment-purge-in-english-and-dead-code*
*Completed: 2026-09-26*
