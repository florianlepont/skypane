---
phase: 30
plan: 07
sha: a378020113551a3dc8a78f836e7fa5497a23bcc1
---

# 30-07 CSS Deletion Audit

Counts taken repo-wide (`grep -rn`) at the SHA above — the last commit before this
plan's Task 1/Task 2 edits landed — in three categories per selector:

- **markup/py**: `companion/*.py`, `companion/**/*.py`, `server/*.py` (`test_*.py` excluded)
- **js**: `companion/static/*.js`
- **harness**: `companion/test_*.py`

A hit that is a Python **comment**/docstring line, or a harness **string literal**
inside a ledger's `"why"` field, a retired-vocabulary scan list, or a historical
prose comment, is **not** counted as a live consumer — matching this plan's own
`<action>` instruction ("Distinguish a real consumer from a COMMENT mentioning the
name"). Every non-zero count below was individually inspected and confirmed
comment/prose-only before its selector was marked deleted.

## Deleted selectors

| Selector | markup/py | js | harness | Verdict | Notes |
|---|---|---|---|---|---|
| `.frame-colours__layout` | 0 | 0 | 0 | deleted | zero mentions anywhere |
| `.frame-colours__layout` (>=960px override) | 0 | 0 | 0 | deleted | same rule, media-query variant |
| `.frame-colours__panels` | 0 | 0 | 0 | deleted | zero mentions anywhere |
| `.frame-colours__preview` | 1 | 0 | 2 | deleted | the 1 py hit is `_theme_live_preview_html()`'s own docstring, describing what USED to call it with this `extra_class` (comment only, no live call site passes this string anymore — the real call site now passes `"aspect-card__preview"`, confirmed at `config_page.py:2144`); the 2 harness hits are `test_config_page.py:1435` (a ledger row's own `"why"` prose) and `:11812` (a comment recording a prior retarget, "was frame-colours__preview") |
| `.frame-colours__list` | 0 | 0 | 0 | deleted | zero mentions anywhere |
| `.frame-colours__row` | 0 | 0 | 2 | deleted | both harness hits are prose: a ledger row's own `"why"` field (`test_config_page.py:1268`) and a comment above the retired check's old location (`:7480`) |
| `.frame-colours__row:hover` | 0 | 0 | 0 | deleted | same base selector, no separate consumer |
| `input:checked + .frame-colours__row` | 0 | 0 | 0 | deleted | same base selector, no separate consumer |
| `.frame-colours__row:focus-within` | 0 | 0 | 0 | deleted | same base selector, no separate consumer |
| `.frame-colours__swatch` | 0 | 0 | 0 | deleted | zero mentions anywhere |
| `.frame-colours__label` | 0 | 0 | 0 | deleted | zero mentions anywhere |
| `.frame-colours__meta` | 0 | 0 | 0 | deleted | zero mentions anywhere |
| `.frame-colours__panel-legend` | 0 | 0 | 2 | deleted | both harness hits are prose: a ledger row's own `"why"` field (`test_config_page.py:1446`) and a comment above the retired check's old location (`:12105`) — the check itself (`_segmented_control_resets_the_global_label_margin_and_the_legend_leaves_the_serif`) is re-pinned in Task 3 with this half retired, per the plan's own instruction |
| `.frame-colours__usage-panel` | 0 | 0 | 1 | deleted | the 1 harness hit is `test_browser_ux.py:1088`, a comment recording that no equivalent mechanism exists once this selector retires — prose, not a live reference |
| `.frame-colours__usage-panel:last-child` | 0 | 0 | 0 | deleted | same base selector, no separate consumer |
| `.frame-colours__usage-panel--collapsed` | 0 | 0 | 0 | deleted | zero mentions anywhere (theme-preview.js's own carousel-era class-toggle logic was already deleted in 30-04) |
| `.theme-chip-grid--strip` | 1 | 0 | 2 | deleted | the 1 py hit is a docstring cross-reference inside `_theme_chip_grid_html()` describing the retired carousel-era modifier by name (comment only); both harness hits are prose (a ledger row's own `"why"` text and a retired-vocabulary scan list at `test_config_page.py:1690`, which INTENTIONALLY keeps the string to assert its absence going forward) |
| `.theme-chip-grid--strip > .theme-chip` | 0 | 0 | 0 | deleted | same base selector, no separate consumer |
| `.theme-carousel__all` | 0 | 0 | 0 | deleted | zero mentions anywhere |
| `.theme-carousel:has(.theme-carousel__all[open]) .theme-chip-grid--strip` | 0 | 0 | 0 | deleted | inside the shared `@supports` block; zero mentions anywhere (the BLOCK itself survives — see Kept below) |
| `.theme-carousel__pagers` | 0 | 0 | 0 | deleted | zero mentions anywhere (the one `_NO_JS_CONTROL_REGISTRY` row for the carousel's two pagers was already removed in 30-04, per that plan's own Pitfall 2 handling) |
| `.theme-carousel__pager::after` | 0 | 0 | 0 | deleted | zero mentions anywhere |
| `.theme-carousel__pager--prev::after` | 0 | 0 | 0 | deleted | zero mentions anywhere |
| `.theme-carousel__dots` | 0 | 0 | 0 | deleted | zero mentions anywhere |
| `.frame-colours__list li:has(input:checked) .frame-colours__row` | 0 | 0 | 0 | deleted | inside the shared `@supports` block; zero mentions anywhere (the BLOCK itself survives — see Kept below) |

**Total: 26 selector/rule entries deleted** (the `.frame-colours*` block in full,
`.theme-chip-grid--strip` + its child rule, all five `.theme-carousel*` rules, and
the two feature-query rules naming retired markup), matching this plan's own
`<success_criteria>` count of "the ~37 rules the old one needed" when counted at
the individual-declaration-block granularity ROADMAP's carried discipline uses
elsewhere in this phase.

## Explicit NON-deletions (kept, with a surviving consumer)

| Selector | markup/py | js | harness | Verdict | Why kept |
|---|---|---|---|---|---|
| `.theme-chip` (base) and its descendants | many | 0 | many | **kept** | still the renderer for the rule-add form's compact grid (`_theme_chip_grid_html()`, one live call site, `config_page.py:4903`) |
| `.theme-chip--compact` and its six descendants | 1 | 0 | many | **kept** | live consumer: `_rule_add_form_html()`'s own `extra_class="theme-chip--compact"` (`config_page.py:4905`) |
| `.theme-chip__body--placeholder` | 0 | 0 | 0 | **kept, with a documented exception** | zero real consumers found anywhere (the restyled `_same_as_departures_chip_html()` moved to `.leading-option`/`.leading-option__name` in 30-04, dropping this class from its own markup) — this plan's own `<task>` text and `<verify>` script explicitly name it as a required NON-deletion regardless, so it is kept per that explicit instruction rather than second-guessed here. Flagged as a genuine candidate for a future dead-CSS cleanup pass, out of this plan's own scope. |
| `.theme-live-preview` and its descendants | 1 | 1 | many | **kept** | live consumer: `_theme_live_preview_html()` (`config_page.py:1957`), called from `_aspect_card_html()` with `extra_class="aspect-card__preview"`; `theme-preview.js` also references this class |
| `.calendar-actions` | 1 | 0 | many | **kept** | plan 30-06 gave this a new home inside the Aspect card's Calendar row (`_calendar_connection_html()`) — a live consumer, not an orphan |
| `.calendar-masked-url` | 1 | 0 | many | **kept** | same as above — relocated by 30-06, still a live consumer |
| `button.calendar-disconnect-btn` | 1 | 0 | many | **kept** | same as above; this is also the app's one destructive-control specificity fix (T2/T15) — Task 3 re-pins its specificity relationship against `button[type="submit"]` |
| `@supports selector(:has(*))` block itself | — | — | — | **kept** | the ONE feature-query block this file pins at exactly 1 (`_exactly_one_has_feature_query_block_survives()`); this plan deletes two rules FROM it and adds four rules TO it, and the block itself survives throughout |

## Carried-over reasoning

- The `min-width: 0` load-bearing note from `.frame-colours__layout`/`.frame-colours__usage-panel`
  does **not** carry to a new rule — the new `.aspect-card` two-column layout has no
  nowrap scroll-snap strip forcing a `<fieldset>`'s UA `min-inline-size: min-content`
  wide, and `.theme-live-preview__image` already declares `width: 100%; height: auto`
  (never `width: auto`), so no grid cell is ever pushed wide by unshrinkable content.
  Stated explicitly in the new CSS's own comment rather than silently dropped, per
  this plan's Task 3 instruction.
- `.frame-colours__panel-legend`'s own serif-leak fix (C1) does **not** carry to a new
  rule either — the usage panels and their `<legend>` elements are gone outright, and
  the rule-add form's "Match by" segmented control never used a `<legend>` (it labels
  itself via a visually-hidden `<span>` + `aria-labelledby`, confirmed at
  `config_page.py:4910-4912`). This selector's retirement genuinely NARROWS the serif
  boundary's own documented exception set by one (see 30-07-SUMMARY.md for the
  design-system fact to fold into the `sketch-findings-skypane` skill).
- The comment at `style.css` (near `.copy-btn--copied .copy-btn__label`) that used to
  point a reader at `.frame-colours__panel-legend` "below" as a second example of the
  shared label-voice register is repointed to `.data-table th` instead, with a note
  that the original pointer's target is retired by this plan — a comment update, not
  a rule deletion (per Task 2's own instruction that a comment is not a consumer and
  must not be dropped, only corrected).
