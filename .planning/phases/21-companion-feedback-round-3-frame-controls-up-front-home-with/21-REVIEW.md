---
phase: 21-companion-feedback-round-3-frame-controls-up-front-home-with
reviewed: 2026-09-12T12:53:17Z
depth: standard
files_reviewed: 28
files_reviewed_list:
  - companion/app.py
  - companion/auth.py
  - companion/i18n_fr/calendar_group.py
  - companion/i18n_fr/display.py
  - companion/i18n_fr/flights.py
  - companion/i18n_fr/health.py
  - companion/i18n_fr/nav.py
  - companion/i18n_fr/rules.py
  - companion/layout.py
  - companion/pages/__init__.py
  - companion/pages/airlines_page.py
  - companion/pages/config_page.py
  - companion/pages/health_page.py
  - companion/pages/history_page.py
  - companion/pages/home_page.py
  - companion/prefs.py
  - companion/static/flight-rows.js
  - companion/static/freshness.js
  - companion/static/list-filter.js
  - companion/static/style.css
  - companion/static/theme-preview.js
  - companion/test_companion_app.py
  - companion/test_config_page.py
  - companion/test_contrast_check.py
  - companion/test_i18n.py
  - companion/test_status_pages.py
  - companion/test_view_pages.py
  - server/device_config.py
findings:
  critical: 1
  warning: 4
  info: 2
  total: 7
status: issues_found
---

# Phase 21: Code Review Report

**Reviewed:** 2026-09-12T12:53:17Z
**Depth:** standard
**Files Reviewed:** 28
**Status:** issues_found

## Summary

Reviewed the phase 21 diff (`git diff 614d41e..HEAD -- companion server`, 28 files,
+5267/-2999) against `21-CONTEXT.md` (D-01..D-20, R-01..R-14) and `21-UI-SPEC.md`.

The security-sensitive surfaces called out by the review brief are all implemented
correctly and match the locked decisions byte-for-byte:

- `_handle_quick_toggle()`'s `return_to` is membership-tested against exactly
  `(layout.HOME_ROUTE, layout.DISPLAY_ROUTE)` before use, with a safe fallback —
  no open redirect (`companion/app.py:2828-2831`).
- `/ui-mode` is a fully-deleted route (unknown path → 404); `auth.UI_MODE_COOKIE_NAME`
  and every cookie write for it are gone; a stale browser cookie of that name is
  never read anywhere under `companion/`.
- `config_page._masked_calendar_url()` parses with `urlsplit()`, returns host-only
  or `""` on any failure (falsy input, `ValueError`, empty netloc), and the caller
  omits the line entirely on empty — verified against a real HTTP round trip
  (`test_config_page.py`'s T-16-SECRET-extended check, and the hostile-URL/
  `javascript:` fail-soft check) — both pass.
- `handle_post()`'s widened `theme_arriving`/`calendar_theme_id` gates accept only
  `("",) + device_config.THEME_IDS` — the empty string is carved out, every other
  non-member value is still rejected — and `server/device_config.py`'s
  `save_device_config()` validation gate for `calendar_theme_id` was correctly
  widened the same way, with the READ-path `normalise_calendar_theme_id()`
  degrade-to-`None` contract left unchanged and every downstream consumer already
  membership-testing before use.
- Every new HTML write site checked (calendar masked URL, Frame colours card, nav
  reminder, Flights detail row, compact table cells) routes through `escape_html()`
  at its interpolation site; no raw interpolation found.
- `flight-rows.js`, the rewritten `theme-preview.js`, `list-filter.js`'s extension,
  and `freshness.js`'s pause-branch removal are all ES5, IIFE + `"use strict"`,
  guarded, and never write markup through an HTML sink — only `className`,
  `textContent`/`.value`, `aria-*` attributes and one `<img>.src` (always from a
  server-rendered `data-preview-src`, never file-built).
- All five test harnesses' `EXPECTED_CHECK_COUNT` pins match their actual output
  exactly (256/258, 220/220, 217/218, 114/114, 22/22, 41/41 — the six failures
  distributed across three of those files are precisely the five pre-existing,
  documented root-sandbox failures `21-CONTEXT.md` names, plus the identical two
  in `server/test_manual_resolutions.py`; no new failure, nothing weakened to
  pass).
- Dead-code removal (simple mode, the Health pause button, the arrivals
  checkbox, the four theme chip grids, the Calendar fusion `:has()` rule, the
  `.status-card*`/`.home-hero` CSS, the `QUICK_ACTION_*` constants relocated to
  `layout.py`) is clean: no orphaned constant, CSS selector or catalogue entry
  was found still describing the removed behaviour, other than the two
  documentation-only staleness items noted below.

One real, provable defect was found in the new "Frame colours" card's own CSS
(a broken selector that leaves the whole 4-row radiogroup with **no visible
keyboard-focus indicator, in any browser** — not merely an older-browser
`:has()` fallback gap), plus out-of-scope, undocumented behaviour changes to
the Health battery chart's localisation that contradict this phase's own
explicit "out of bounds" list, and two minor documentation/attribute
staleness items.

## Critical Issues

### CR-01: Frame colours radiogroup rows never show a keyboard focus indicator, in any browser

**File:** `companion/static/style.css:5834-5841` (rule authored per
`21-UI-SPEC.md` §D verbatim; markup at `companion/pages/config_page.py:1242-1257`,
`_frame_colours_row_html()`)

**Issue:** The row markup nests the radio *inside* its own label:

```html
<li><label class="frame-colours__row">
  <input type="radio" name="colour_usage" value="departures" class="visually-hidden" checked>
  <span class="frame-colours__swatch">...</span>
  ...
</label></li>
```

`style.css` then styles the checked/focused state with a **sibling** combinator:

```css
input:checked + .frame-colours__row { ... }
input:focus-visible + .frame-colours__row {
  outline: 2px solid var(--color-accent);
  outline-offset: 2px;
}
```

`+` matches a `.frame-colours__row` element that *immediately follows* the
`<input>` as a sibling under the same parent. Here `.frame-colours__row` is the
**ancestor** of the `<input>` (the label wrapping it), not its sibling — this
selector can never match this markup, in any browser, at any `:has()` support
level. The comment above the rule (`style.css:5829-5833`) claims this is "a
plain `:checked` sibling selector — works in every browser, no `:has()` needed
for a same-parent radio+label pair," which is factually wrong for this exact
DOM shape.

For the **checked/selected** state there is a working fallback one block down
(`.frame-colours__list li:has(input:checked) .frame-colours__row`, inside the
file's existing `@supports selector(:has(*))` block at `style.css:2192`), so in
practice modern browsers (which now widely support `:has()`) do show the
selected row correctly — the bug is "masked," not harmless.

For **`:focus-visible`** there is no such fallback anywhere in the file (`grep`
for `frame-colours` in `style.css` shows only the one broken sibling rule) —
so a keyboard user tabbing through the 4-row radiogroup gets **zero visible
focus indicator**, in every browser, unconditionally. The radio itself is
`class="visually-hidden"` (`position:absolute; clip-path: inset(50%); width/
height: 1px`), so the browser's own native focus ring on the input is
effectively invisible too. This is a genuine WCAG 2.4.7 (Focus Visible)
regression on a brand-new interactive control, and it is exactly the class of
defect the codebase's own established idiom for this same problem
(`.runway-card`/`.theme-chip`, which correctly use
`.runway-card:not(.runway-card--selected):focus-within` /
`.theme-chip:not(.theme-chip--selected):focus-within`, an ancestor-relative
pseudo-class that *does* match this nesting) already avoids elsewhere in this
exact file. No test in `test_config_page.py`/`test_contrast_check.py` exercises
focus-visible styling for this component, so nothing caught it.

**Why it matters:** A no-mouse/keyboard-only user (the population WCAG 2.4.7
protects) cannot tell which of the four Frame-colours rows is currently
focused. This ships a real accessibility regression on a card the UI-SPEC's
own "Accessibility Floors" section explicitly requires radiogroup semantics
for.

**Fix:** Replace both broken sibling rules with the same ancestor-relative
pattern already used by `.runway-card`/`.theme-chip`:

```css
.frame-colours__row:focus-within {
  outline: 2px solid var(--color-accent);
  outline-offset: 2px;
}
```

(Optionally drop the now-provably-dead `input:checked + .frame-colours__row`
rule too, since the `:has()` block below it is what actually does the work —
or, if `:focus-within` alone isn't wanted for the checked/selected treatment,
add a `.frame-colours__list li:has(input:focus-visible) .frame-colours__row`
companion inside the existing `@supports` block, mirroring the checked-state
fallback already there.)

## Warnings

### WR-01: Out-of-scope, undocumented localisation change to the Health battery chart

**File:** `companion/pages/health_page.py:850-861,899,988-996`;
`companion/layout.py:601-610` (`month_abbr()`)

**Issue:** `21-CONTEXT.md`'s own "Out of scope" list states: *"The battery
chart, the poll countdown, the 'State' read-aloud text ... (points 9, 11, 13,
14 — accepted)"* are out of bounds for this phase. The diff nonetheless:

- deletes `health_page._MONTH_ABBR` (a fixed, deliberately English-only table
  whose own removed comment explained this was *"a deliberate, narrow scope
  boundary of 20-03-PLAN.md Task 2 ... not this chart's own private
  axis-label helper"*), and
- routes the chart's X-axis day label through the new, language-aware
  `layout.month_abbr()` (defaulting to `prefs.current_lang()`), and
- moves the "daily average" hover/tap readout strings
  (`BATTERY_AVERAGE_WHEN_ONE_TEMPLATE`/`_MANY_TEMPLATE`/`_BARE_TEMPLATE`) through
  `i18n.t()` for the first time.

Every occurrence is tagged only `# Phase 21 polish` in the source — it does not
correspond to any of D-01..D-20, is not mentioned in `21-UI-SPEC.md`, and does
not appear in any of the eight `21-0N-SUMMARY.md` files' Deviations sections
(the mechanism this codebase otherwise uses to flag and justify an
out-of-plan fix). It reverses a previous, deliberately-documented decision
without going through this project's own decision process.

**Why it matters:** Functionally this is probably a harmless (arguably
positive) change — nothing broke and `test_i18n.py`'s completeness harness
passed because French catalogue entries were added for the new keys — but it
is unauthorized scope expansion into a boundary this very phase's planning
document explicitly drew, with no review trail. If it had introduced a
regression (e.g., a locale-dependent chart label mismatch), no reviewer
scoping to `21-CONTEXT.md`'s decisions would have looked for it here.

**Fix:** Either retroactively document this as an accepted deviation (with the
same "Deviations from Plan" discipline every other out-of-plan fix in this
phase used), or revert it to a separate, explicitly-scoped follow-up task/phase
per this project's own workflow discipline.

### WR-02: `data-usage-panel` attribute is dead weight; its own docstring's claim about it is false

**File:** `companion/pages/config_page.py:1235-1236,1244,1254` (attribute
declared and emitted); `companion/static/theme-preview.js` (never reads it)

**Issue:** `_frame_colours_row_html()`'s docstring says: *"`data-usage-panel`
is the attribute contract theme-preview.js reads to know which usage panel
this row shows."* The attribute is indeed rendered on every row's `<input>`
(`COLOUR_USAGE_PANEL_ATTR = "data-usage-panel"`), but `theme-preview.js`
(reviewed in full) never queries `data-usage-panel` anywhere — it determines
the active usage from `input[name="colour_usage"]:checked`'s own `.value`
instead, and matches panels via the (different, and actually used)
`data-usage-panel-target` attribute on the panel `<fieldset>`s.

**Why it matters:** Not a functional bug (the feature works via the `.value`
path), but it's dead markup plus a docstring asserting a contract that does
not exist — exactly the kind of drift this codebase's own greppable-contract
discipline (cited throughout the diff, e.g. `COLOUR_USAGE_PANEL_TARGET_ATTR`'s
own comment) is supposed to prevent. A future edit to `theme-preview.js` could
reasonably "clean up" the row's radio value while leaving the stale
`data-usage-panel` attribute both unremoved and unexplained.

**Fix:** Either delete `COLOUR_USAGE_PANEL_ATTR`/`data-usage-panel` and its one
call-site usage, or correct the docstring to state the attribute is currently
unused/reserved and have theme-preview.js actually read it instead of `.value`
(pick one; don't leave the contract and the code disagreeing).

### WR-03: Corroboration column's tooltip becomes unreachable once the label is visually hidden

**File:** `companion/layout.py:1594-1599` (`status_dot()`);
`companion/pages/history_page.py:899-901` (call site, `visually_hide_label=True`)

**Issue:** `status_dot()` puts the `title="..."` attribute on the **label**
span, and `visually_hide_label=True` gives that same span
`class="dot-label visually-hidden"`. `.visually-hidden` (`style.css:819-829`)
clips the element to `width:1px;height:1px;clip-path:inset(50%)` — a target a
mouse cannot meaningfully hover to trigger the native tooltip. Previously (the
label visible), hovering the Corroboration cell's text surfaced the extended
explanation for the "None" state (`_CORROBORATION_TITLES["None"] = "Only one
saw it"`); after this change the dot itself carries no `title`, so that
tooltip is effectively unreachable by a mouse user in the new dot-only
column.

**Why it matters:** This is a real (if minor) loss of an existing affordance
for sighted mouse users in exactly the row the D-15 compaction targeted —
"the dot alone already answers agree/disagree/unknown" per the UI-SPEC, but
the *tooltip's own extra detail* ("Only one saw it" vs. the visible-but-now-
gone "Single-source" word) is no longer reachable at all, not even on hover.

**Fix:** Move the `title` attribute onto the `.dot` span itself (or duplicate
it there) when `visually_hide_label=True`, so the hoverable, visible dot still
carries the tooltip.

### WR-04: Stale docstrings/comments still name the deleted `_rules_section_html()` function as a live call site

**File:** `companion/pages/config_page.py:2708` (docstring of
`_rule_add_form_html()`); `companion/i18n_fr/rules.py:3-4` (module docstring)

**Issue:** `_rules_section_html()` and its heading constant
`RULES_SECTION_HEADING` are correctly deleted (per D-10) — confirmed by
`grep`, no `def _rules_section_html` remains anywhere. However
`_rule_add_form_html()`'s own docstring still reads *"the one live call site
(`_rules_section_html()` below) keeps calling this..."*, and
`companion/i18n_fr/rules.py`'s module docstring still describes itself as
serving *"config_page.py's `_rule_add_form_html()`/`_rule_row_html()`/
`_rules_section_html()`"*. The actual (and only) call site today is
`_frame_colours_card_html()` at `config_page.py:1386`.

**Why it matters:** Low risk on its own, but this project relies heavily on
literal-text greps (the code's own comments say so repeatedly, e.g.
`21-01-SUMMARY.md`'s own "the harness's own post-task verification grep
scan[s] raw file text, not parsed code") as a regression-pinning mechanism —
a docstring that names a function that no longer exists is exactly the kind
of drift that later misleads a human or an agent doing the same kind of
grep-based verification this codebase depends on.

**Fix:** Update both comments to name `_frame_colours_card_html()` (or simply
drop the now-incorrect parenthetical function name).

## Info

### IN-01: `freshness.js`'s deleted `data-pause-text`/`data-resume-text` pattern is still cited by name in three other files' comments

**File:** `companion/static/copy-button.js:24-25`;
`companion/static/dirty-state.js:64-65`; `companion/pages/history_page.py:665`

**Issue:** These three comments say "the same shape `freshness.js` already
uses for `data-pause-text`/`data-resume-text`" as a design-precedent analogy.
`freshness.js` no longer has that pattern (D-18 deleted it outright) — the
closest surviving analogue in this diff is `flight-rows.js`'s own
`data-more-text`/`data-less-text` pair. Purely cosmetic/historical-accuracy
drift, not a functional issue.

**Fix:** Optional — reword the three comments to cite `flight-rows.js`'s
`data-more-text`/`data-less-text` (or `copy-button.js`'s own
`data-copied-text`) instead of the now-deleted precedent.

### IN-02: `@supports selector(:has(*))` block-count history is confusing across summaries but resolves correctly in the shipped code

**File:** `companion/static/style.css` (one block, line 2081);
`21-05-SUMMARY.md` (claims the count "stays pinned at 2")

**Issue:** `21-05-SUMMARY.md`'s Decisions section states the
`@supports selector(:has(*))` block count "stays pinned at 2" after the Frame
colours work, but the final shipped `style.css` (after 21-07's Calendar-card
merge, per its own retargeted `test_config_page.py` comment at line 545-546:
"the whole-file pinned block count moved from 2 to 1") has exactly **one**
such block. This is not a bug in the code — the two plans landed
sequentially and the final state is internally consistent and test-pinned
(220/220 pass) — but a reader of 21-05-SUMMARY.md in isolation would draw the
wrong conclusion about the final file.

**Fix:** None required in the shipped code. If the phase's own documentation
is revisited, note that 21-07 (Calendar) further reduced the block count from
2 to 1.

## Summary Table

| ID | Severity | File | Issue |
|----|----------|------|-------|
| CR-01 | Critical | `companion/static/style.css:5834-5841` | Frame colours row: `:focus-visible` sibling selector never matches this markup — no keyboard focus indicator, in any browser |
| WR-01 | Warning | `companion/pages/health_page.py`, `companion/layout.py` | Undocumented, out-of-scope localisation change to the Health battery chart, contradicting `21-CONTEXT.md`'s explicit "out of bounds" list |
| WR-02 | Warning | `companion/pages/config_page.py`, `companion/static/theme-preview.js` | `data-usage-panel` attribute is dead; docstring's claim that theme-preview.js reads it is false |
| WR-03 | Warning | `companion/layout.py`, `companion/pages/history_page.py` | Corroboration column's extended tooltip is unreachable once its label is visually-hidden |
| WR-04 | Warning | `companion/pages/config_page.py`, `companion/i18n_fr/rules.py` | Stale docstrings still name the deleted `_rules_section_html()` as a live call site |
| IN-01 | Info | `copy-button.js`, `dirty-state.js`, `history_page.py` | Comments cite freshness.js's deleted pause-label pattern as a still-live precedent |
| IN-02 | Info | `style.css`, `21-05-SUMMARY.md` | `:has()` block-count claim in a wave summary is stale relative to the final (later-wave) file state; no code defect |

## Verdict

**Fix first.** The security-sensitive surfaces named in the review brief
(`return_to` whitelisting, the `/ui-mode` removal, the masked calendar URL,
the widened theme/calendar validation gates, and every new HTML write site)
are all correct, and all five test harnesses' pinned counts match real output
with no weakened checks. However, CR-01 is a real, provable, unconditional
accessibility regression (zero keyboard focus indication on a new, primary
interactive control) that should be fixed before this ships — it is a
one-line CSS fix. WR-01 should be resolved (documented as an accepted
deviation, or reverted) before merge so the phase's own scope boundary stays
trustworthy for future review. WR-02..WR-04 and the Info items can be
folded into this or a follow-up cleanup pass.

---

_Reviewed: 2026-09-12T12:53:17Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_

## Resolutions (orchestrator, 2026-09-12)

| ID | Resolution |
|---|---|
| CR-01 | Fixed: `.frame-colours__row:focus-within` replaces the sibling selector that could never match (`companion/static/style.css`). |
| WR-01 | Accepted as a documented orchestrator polish, not reverted: the developer's standing instruction is "garde les deux langues", and the wave-5 sweep showed English chart text and month names on the French Health page. The CONTEXT's "battery chart out of bounds" sentence protected the chart's behaviour (point 13 "ok"), not the completeness of its French; the change touches only text and the month table, through the same `i18n.t()`/catalogue path as every other string. Recorded in commit a747c8a and in the phase summary. |
| WR-02 | Docstring corrected: `data-usage-panel` is the server-side statement of the row/panel pairing; `theme-preview.js` reads the radio's `value`. |
| WR-03 | Fixed: when the label is visually hidden, the `title` lands on the dot span; the default output stays byte-identical (`layout.status_dot`). |
| WR-04 | Fixed: the three docstrings/comments now name the rules usage panel of `frame_colours_section_html()`. |
| IN-01 | Fixed: the three comments no longer cite the retired pause-label pair as a live precedent. |
| IN-02 | No code change; the block count in the shipped stylesheet is the pinned one (`test_config_page.py` green). |

All harnesses green apart from the five documented root-sandbox checks; `ruff check .` clean.
