---
phase: 29-companion-review-feedback-round-3-the-developer-s-own-tour-o
fixed_at: 2026-09-21T23:43:14Z
review_path: .planning/phases/29-companion-review-feedback-round-3-the-developer-s-own-tour-o/29-REVIEW.md
iteration: 1
findings_in_scope: 3
fixed: 3
skipped: 1
status: partial
---

# Phase 29: Code Review Fix Report

**Fixed at:** 2026-09-21T23:43:14Z
**Source review:** .planning/phases/29-companion-review-feedback-round-3-the-developer-s-own-tour-o/29-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope (fix_scope: critical_warning — CR-*/WR-* only): 3
- Fixed: 3
- Skipped: 1 (IN-01, out of scope for this fix pass — info-level, not requested)

## Fixed Issues

### CR-01: The new "Show more" link on /flights renders with none of its intended button styling

**Files modified:** `companion/static/style.css`, `companion/test_view_pages.py`
**Commit:** `7d48aec`
**Applied fix:** Added an `a.calendar-disconnect-btn` rule (plus its `:hover`/`:focus-visible` pair) to `style.css`, since the pre-existing `button.calendar-disconnect-btn` selector is element-type-qualified and can never match the `<a>` tag `_show_more_html()` actually emits. Also added a new harness check, `_flights_reveal_anchor_has_a_matching_css_selector`, to `test_view_pages.py`: it renders the Show-more control, reads its real tag/class, parses `style.css`'s own selector list for rules mentioning `.calendar-disconnect-btn`, and requires at least one selector whose rightmost compound has no tag qualifier (or one matching the rendered tag) with no ancestor compound to its left — a real selector-vs-emitted-tag proof, not a substring search. `EXPECTED_CHECK_COUNT` re-derived by running: 168 → 169. Mutation-proven: with the CSS fix temporarily reverted, the new check failed with `"expected a CSS selector whose rightmost compound has no tag qualifier or matches the rendered <a>... found only ['.airline-card .calendar-disconnect-btn', 'button.calendar-disconnect-btn', ...], none of which actually paints <a class=\"calendar-disconnect-btn\">"` — confirmed non-vacuous, then the fix was restored and the suite re-verified green (169/169).

### WR-01: Orphaned CSS rule + stale comment left behind by plan 29-01's own deletion

**Files modified:** `companion/static/style.css`
**Commit:** `772fb11`
**Applied fix:** Independently re-verified (fresh `grep` across `companion/pages/*.py`) that no markup anywhere nests `.calendar-disconnect-btn` inside `.airline-card` before touching anything — confirmed zero hits, matching the review's own finding. Deleted the orphaned `.airline-card .calendar-disconnect-btn` rule and its 15-line comment block at `style.css:6432-6451`. Also corrected two now-stale comment cross-references to that deleted rule found while verifying: one pre-existing comment near `button.calendar-disconnect-btn` that described the deleted rule as still existing "further down" (now rewritten in past tense, naming 29-01/CFG-81 as the removal and WR-01/29-REVIEW.md as the cleanup, per this project's own comment-discipline convention of describing a gone control by role, not by identifier); and one dangling reference introduced by this same pass's own CR-01 fix (written before WR-01 was applied), corrected to not cite the rule being deleted. Full suite re-run clean afterward (all 22 harnesses, 317/317 in `test_companion_app.py`, 169/169 in `test_view_pages.py`, 274/274 in `test_config_page.py`).

### WR-02: CFG-80's "Start and End on one line" is unmet at the app's own two reference viewports, while the requirement reads as delivered

**Files modified:** `.planning/REQUIREMENTS.md`
**Commit:** `b140c33`
**Applied fix:** Applied the review's option (a) — no layout redesign. Updated CFG-80's requirement checklist entry (line 106) and its traceability-table row (line 257) to state the `≥480px` threshold explicitly and to note that both of the app's own reference viewports (360px, 390px) still see the original stacked layout below that width, citing `29-04-SUMMARY.md`'s Known Limitations for the underlying arithmetic. A future reader of `REQUIREMENTS.md` alone no longer needs to open the plan SUMMARY to learn the one-line fix doesn't reach phones. `.planning/ROADMAP.md`'s narrative Phase 29 entry was left untouched, per the fix's own scope instruction — it already documents this honestly at the plan level.

## Skipped Issues

### IN-01: No check verifies that a reused CSS class actually paints the element type it's applied to

**File:** `companion/test_view_pages.py`, `companion/test_status_pages.py`, `companion/test_companion_app.py`
**Reason:** Out of scope — `fix_scope` for this pass is `critical_warning` (CR-*/WR-* only); IN-01 is an info-level finding proposing a standing harness pattern generalized beyond this phase's specific bug. CR-01's fix above does add a targeted instance of exactly this kind of check (selector-vs-emitted-tag) for the Show-more control, but does not generalize it into the standing pattern IN-01 asks for.
**Original issue:** Every one of this codebase's "reuses X's styling" checks treats a class string appearing in both markup and stylesheet as proof of visual reuse, without checking that a selector's tag qualifier or ancestor-scoping actually reaches the emitted element — which is exactly how CR-01 shipped invisibly.

---

_Fixed: 2026-09-21T23:43:14Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
