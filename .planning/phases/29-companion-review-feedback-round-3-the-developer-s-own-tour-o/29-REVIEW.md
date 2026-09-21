---
phase: 29-companion-review-feedback-round-3-the-developer-s-own-tour-o
reviewed: 2026-09-22T00:00:00Z
depth: standard
files_reviewed: 15
files_reviewed_list:
  - companion/pages/airlines_page.py
  - companion/app.py
  - companion/pages/__init__.py
  - companion/i18n_fr/airlines.py
  - companion/static/style.css
  - companion/pages/history_page.py
  - companion/layout.py
  - companion/i18n_fr/flights.py
  - companion/static/freshness.js
  - companion/pages/config_page.py
  - companion/static/value-controls.js
  - companion/i18n_fr/display.py
  - companion/i18n_fr/notifications.py
  - companion/pages/health_page.py
  - companion/i18n_fr/health.py
findings:
  critical: 1
  warning: 2
  info: 1
  total: 4
status: issues_found
---

# Phase 29: Code Review Report

**Reviewed:** 2026-09-22
**Depth:** standard
**Files Reviewed:** 15 (plus the six PLAN.md/SUMMARY.md pairs and REQUIREMENTS.md read for context)
**Status:** issues_found

## Summary

Phase 29 is six plans of settings/page-layout cleanup and an editorial-copy floor across the whole companion app (CFG-79 through CFG-84). The Python side is unusually disciplined — every deletion is grep-gated, every new function is total (no raise on hostile input), every i18n change lands with `test_i18n.py` as an automatic EN/FR-symmetry gate, and the full suite (22 harnesses, 317+ checks) passes clean in this worktree. I traced the specific items the orchestrator flagged (`flights_limit()`'s clamp, the `.quiet-times-row` 480px breakpoint, the `freshness.js`/`layout.py` swap-registry mirror, `edit_mode`/`EDIT_QUERY_PARAM` residue, `ASPECT_CAPTION_EXEMPTIONS`'s single definition site) and all five check out as claimed.

However, one genuine, provable **rendering bug** slipped through the entire test suite because every check that touches it is a markup/string check, never a selector-vs-element-type check: Plan 29-03's new "Show more" control on `/flights` is emitted as an `<a class="calendar-disconnect-btn">`, but the only two CSS rules that paint `.calendar-disconnect-btn` are both scoped to the `button` element (`button.calendar-disconnect-btn`) or to a `.airline-card` ancestor the new anchor is never inside. The control ships with **zero** of the "small, de-emphasised secondary action" styling every comment, docstring and the plan itself claims it reuses "verbatim" — it renders as a bare, default-underlined accent-coloured link. I also found one piece of CFG-81 dead code (an orphaned CSS rule + a 15-line comment describing a control that plan 29-01 deleted), and one requirement (CFG-80's "Start and End on one line") that is honestly disclosed as unmet at the app's own two reference viewports but is nonetheless recorded as the requirement's `status: complete`.

## Critical Issues

### CR-01: The new "Show more" link on /flights renders with none of its intended button styling

**File:** `companion/pages/history_page.py:1698` (markup) / `companion/static/style.css:9776-9796` (the only rules for this class)
**Issue:**
`_show_more_html()` emits the reveal control as a plain anchor:
```python
'<a class="calendar-disconnect-btn" href="%s?%s=%d">%s</a>'
```
Every comment around this line (and the plan itself, 29-03-PLAN.md Task 1 step 5: *"Reuse `.calendar-disconnect-btn` verbatim… do NOT invent a new button class"*) asserts this reuses the shared small-secondary-button treatment. It does not. The only two selectors that paint `.calendar-disconnect-btn` anywhere in `style.css` are:
```css
button.calendar-disconnect-btn { ... }              /* style.css:9776 */
button.calendar-disconnect-btn:hover,
button.calendar-disconnect-btn:focus-visible { ... } /* style.css:9791-9792 */
.airline-card .calendar-disconnect-btn { ... }        /* style.css:6447 — descendant-scoped to .airline-card */
```
`button.calendar-disconnect-btn` is an element-type-qualified selector (deliberately, per its own comment at style.css:9744-9764, to win a specificity fight against `button[type="submit"]`) — it can never match an `<a>` tag, regardless of class. The Flights page's Show-more link is not inside `.airline-card` either, so the second rule doesn't reach it. There is no bare `.calendar-disconnect-btn { ... }` selector anywhere in the file.

The result: the anchor gets none of the 30px min-height, the 4px/8px padding, the 12px font-size, the 6%/12% background wash, or the 20% hairline border. It instead inherits the page's global `a { color: var(--color-accent); }` rule (style.css:983-986) and the browser's default underline — a plain hyperlink sitting inside a centred `<nav>`, not the boxed secondary-button look every other `.calendar-disconnect-btn` consumer has. This is the primary new interactive element of CFG-83 (the pagination reveal the developer explicitly asked for), so the defect is squarely in the feature the phase was built to ship.

Every automated check that exercises this control (`test_view_pages.py`'s `_flights_reveal_control_is_a_plain_anchor_no_script_mentions` and friends) verifies the class *string* is present in the markup and that a `.calendar-disconnect-btn {` substring exists somewhere in `style.css` — neither checks that the selector's element-type qualifier actually matches the emitted tag, so the mismatch was invisible to the harness.

**Fix:** Add an anchor-qualified rule (or de-scope the shared declarations to a bare class selector consumed by both element types), e.g.:
```css
/* Anchors need no specificity fight against button[type="submit"] — a plain
 * class selector is enough here. */
a.calendar-disconnect-btn {
  display: inline-block;
  min-height: 30px;
  padding: 4px var(--space-sm);
  font-size: 12px;
  color: var(--color-text);
  background: color-mix(in srgb, var(--color-text) 6%, transparent);
  border: 1px solid color-mix(in srgb, var(--color-text) 20%, transparent);
  border-radius: var(--radius-control);
  text-decoration: none;
}
a.calendar-disconnect-btn:hover,
a.calendar-disconnect-btn:focus-visible {
  background: color-mix(in srgb, var(--color-text) 12%, transparent);
  border-color: color-mix(in srgb, var(--color-text) 20%, transparent);
}
```
and add a check that renders the control and asserts (via a minimal CSS-selector match, not a substring search) that a rule whose selector's tag-and-class actually matches `<a class="calendar-disconnect-btn">` exists — the same class of check `test_companion_app.py`'s CSS-token scans already do for other properties, generalised to selector/tag agreement.

## Warnings

### WR-01: Orphaned CSS rule + stale comment left behind by plan 29-01's own deletion

**File:** `companion/static/style.css:6432-6451`
**Issue:** Plan 29-01 (CFG-81) deleted `_airline_card_html()`'s per-card "Replace picture" button outright (`replace_control_html` and its `.calendar-disconnect-btn` markup — confirmed via `grep -c 'calendar-disconnect-btn' companion/pages/airlines_page.py` = 0). The plan's own acceptance criteria explicitly left the CSS side alone ("`grep -c 'calendar-disconnect-btn' companion/static/style.css` is unchanged from its pre-task value"), but the rule this preserved, `.airline-card .calendar-disconnect-btn { display: block; width: 100%; margin-top: var(--space-sm); }`, together with its 15-line explanatory comment ("the per-card 'Replace picture' control's PLACEMENT inside the card… reused verbatim in the markup as that component's SECOND consumer"), has no reachable consumer left anywhere in the codebase — no markup in `airlines_page.py`, `history_page.py`, `health_page.py` or `config_page.py` ever nests a `.calendar-disconnect-btn` inside `.airline-card`. This directly contradicts 29-01's own "Comment discipline" requirement, which required rewriting (not merely preserving) any surviving comment that describes a deleted control, "by role… never by identifier" once the control it describes is gone. Here the comment still describes the deleted control in the present tense as if it renders today.
**Fix:** Delete the orphaned rule and its comment block (`style.css:6432-6451`) in a follow-up cleanup pass, or, if there's a reason to keep it as a template for a future per-card control, replace the comment with a short note that the control it once served was removed by 29-01-PLAN.md/CFG-81 and this rule is currently unreachable.

### WR-02: CFG-80's "Start and End on one line" is unmet at the app's own two reference viewports, while the requirement reads as delivered

**File:** `companion/static/style.css:3005-3044` (`.quiet-times-row`), `companion/pages/config_page.py` (`quiet_hours_group()`)
**Issue:** CFG-80 and 29-04-PLAN.md's own `must_haves.truths` state plainly: *"Quiet hours reads as one object: Start and End render on one line, as one visual unit with the dial, not as two stacked full-width field groups."* The shipped fix only engages the two-column grid at `≥480px`; below that (via the `@media (max-width: 479.98px)` fallback) it reverts to the original single-column, two-stacked-full-width-lines layout. This app's own two documented reference/contract viewports are 360px and 390px — both fall inside the fallback range. 29-04-SUMMARY.md is honest about this ("Known Limitations… Both of the app's own reference devices (360px, 390px) therefore still see the ORIGINAL stacked layout"), and the arithmetic behind it (native `<input type="time">`'s 144px `min-width` floor) is real and correctly derived, not an oversight. The concern is process, not arithmetic: the requirement's own truth statement is unqualified ("Start and End render on one line"), the phase is recorded as complete, and a reader of ROADMAP.md/REQUIREMENTS.md alone (without opening this specific SUMMARY) would reasonably believe the developer's literal ask ("Start and End on one line, like the dial") now holds on a phone — it does not, on either of the app's two shipped-and-tested screen widths.
**Fix:** Either (a) narrow CFG-80's own requirement text to state the ≥480px threshold explicitly so future readers don't need to open a plan SUMMARY to learn the fix doesn't apply to phones, or (b) revisit the layout once more — e.g., stacking the two 24h twins below their inputs instead of beside them to reclaim the ~16px this needs at 360px — since the gap between "fits" and "doesn't fit" at the contract floor is small (296px needed vs 280px available).

## Info

### IN-01: No check verifies that a reused CSS class actually paints the element type it's applied to

**File:** `companion/test_view_pages.py`, `companion/test_status_pages.py`, `companion/test_companion_app.py` (test-side, cited for context on CR-01's root cause)
**Issue:** CR-01 shipped invisibly because every one of this codebase's many "reuses X's styling" checks (grep/substring searches for a class name in both the markup and the stylesheet) treats "the class string appears in both places" as proof of visual reuse. It isn't — a `button.foo`/`.foo` selector mismatch, or a descendant-scoped selector applied outside its ancestor, both defeat this proof while still passing every existing check. This is the same category of gap this project's own MEMORY.md already flags ("Real-device UI verification — computed-style checks alone missed a real mobile nav bug").
**Fix:** Add a lightweight selector-vs-emitted-tag check (parse the stylesheet's own selector list for a given class, confirm at least one selector's tag qualifier — or no qualifier at all — matches the tag name the page module actually emits for that class) as a standing harness pattern, the same way this codebase already treats "a class that exists in Python and nowhere in style.css paints nothing" as worth a dedicated scanner.

---

_Reviewed: 2026-09-22_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
