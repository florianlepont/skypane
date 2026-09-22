---
phase: 30-aspect-rebuilt-one-tile-three-rows-one-palette-the-calendar-absorbed-sketch-first
plan: 07
subsystem: ui
tags: [config-page, css, accordion, palette, accent-reservation, coverage-ledger, test-harness]

requires:
  - phase: 30-04
    provides: "_aspect_card_html()/_usage_row_html()/_palette_grid_html()/_palette_chip_html()/_palette_swatch_html()/_usage_row_summary_html()/_same_as_departures_chip_html() (companion/pages/config_page.py) — the unstyled Aspect tile markup this plan styles"
  - phase: 30-06
    provides: "_calendar_connection_html() threaded into the Calendar accordion row — the markup this plan's CSS renders alongside the palette"
provides:
  - "companion/static/style.css: .aspect-card/.aspect-card__preview/.usage-row(+--secondary,__name,__meta,__swatch)/.palette/.palette-chip(+__swatch,__name,__check)/.palette-swatch(+__band)/.leading-option(+__name)/.rule-add — 15 new selectors, zero new custom properties/hex literals/font families, one new 10px font-size that widens an existing sub-scale exception rather than adding a new size"
  - "The palette chip's and leading option's selected/checked states joined to the file's single existing @supports selector(:has(*)) block — the block count stays pinned at 1"
  - "The stylesheet's own accent-reservation header list extended by .palette-chip (a re-keyed consumer) and the two outstanding Phase-23 entries (.switch[aria-checked=\"true\"] .switch__track, @keyframes skypane-row-arrive) — exhaustive again for the first time since Phase 23"
  - ".frame-colours*, .theme-carousel*, .theme-chip-grid--strip retired from style.css (26 selector/rule entries), with a three-category (markup/py, js, harness) pre-delete consumer audit recorded in 30-CSS-AUDIT.md"
  - "companion/test_config_page.py: both _ASPECT_REPIN_LEDGER rows owed to 30-07 cleared (destructive-disconnect specificity relationship + palette-chip :has() re-key; segmented-control label-margin reset with the panel-legend serif exception retired outright) — EXPECTED_CHECK_COUNT 274 -> 276"
affects: [30-08]

tech-stack:
  added: []
  patterns:
    - "A CSS component with no `__body`-equivalent wrapper (unlike .theme-chip) can still join the file's shared :has(input:checked)-wash idiom by scoping the 12% accent wash to whichever descendant is NOT the real-colour-bearing swatch — here, .palette-chip__name (the caption) plays the role .theme-chip__body plays for the photo-preview chip, so the swatch's own true ink colour is never tinted by the selection wash."
    - "A plan's own inline <verify> script that bans a literal substring anywhere in a TEST HARNESS file (not the stylesheet) can be structurally unsatisfiable when the harness's own job is to assert that string's ABSENCE from rendered output or from a stylesheet — the assertion's own source code must contain the string it searches for. Distinct from 30-03/30-04/30-06's own documented 'comment-stripped search' fix (which resolves a collision with a HISTORICAL COMMENT), this collision is with a LIVE, load-bearing Python string literal doing real work — comment-stripping cannot remove it, because it was never a comment."

key-files:
  created:
    - .planning/phases/30-aspect-rebuilt-one-tile-three-rows-one-palette-the-calendar-/30-CSS-AUDIT.md
  modified:
    - companion/static/style.css
    - companion/test_config_page.py

key-decisions:
  - "Task 1 (new CSS additions) and Task 2 (audited deletions) landed in ONE commit instead of two, because the additions and deletions touched overlapping regions of the same file (the @supports block gained rules from Task 1 and lost rules from Task 2 in adjacent edits) and un-interleaving them after the fact risked introducing a transcription error worse than the documented merge. Both tasks' own <verify> scripts were run and confirmed passing independently against the combined diff before committing, so the boundary is a commit-granularity deviation, not a correctness gap."
  - "The accordion row's own <summary> is overridden to `color: inherit` rather than the UI-SPEC's cited '50%-muted currentColor chevron' — that exact 50% colour-mix strength exists nowhere in the real stylesheet (confirmed by direct grep); it is the developer-approved SKETCH's own throwaway CSS value, not an existing app token. Spending it here would be a new colour-mix strength, which this plan's own 'zero new colour literal' floor forbids. The file's real, already-established 70%-muted-text idiom is used for the chevron instead — same qualitative effect (quiet, not accented), zero new literal."
  - "`.frame-colours__layout`/`.frame-colours__usage-panel`'s own `min-width: 0` load-bearing note does NOT carry forward to any new rule. Its whole reason to exist was a NOWRAP scroll-snap strip forcing a <fieldset>'s UA min-inline-size wide; nothing in the new .aspect-card two-column layout is nowrap, and `.theme-live-preview__image` already declares `width: 100%; height: auto` (never `width: auto`), so no grid cell here can ever be forced wide by unshrinkable content. Stated explicitly in the new CSS's own comment per Task 3's own instruction, rather than silently dropped."
  - "`.rule-add`'s own styling is read as 'spacing only' literally (margin-top + one open-state summary margin) rather than the developer-approved sketch's own fuller bordered/backgrounded box treatment — the plan's Task 1 bullet for this selector says exactly 'add spacing only,' and the sketch's extra border/background/padding was not asked for. Confirmed visually acceptable (not bare or broken) in the eyes-on pass below, though a future plan could add the fuller box treatment as a deliberate, separate decision."
  - "`.theme-chip__body--placeholder` is kept despite having ZERO real consumers anywhere in the repo (confirmed by grep) — this plan's own <task> text and inline <verify> script explicitly name it as a required NON-deletion, so it is kept per that explicit instruction rather than second-guessed. Flagged in 30-CSS-AUDIT.md as a genuine candidate for a future dead-CSS cleanup pass, out of this plan's own scope."
  - "Both `_ASPECT_REPIN_LEDGER` rows owed to 30-07 land under names that diverge from the ledger's own predicted 'replacement' (identical to 'retired', 30-03's same-name-repoint convention) — the identical same-name-repoint guard-collision 30-05-SUMMARY.md and 30-06-SUMMARY.md already documented, at different rows, resolved the same way: '_after_the_accordion_rebuild' and '_after_the_panel_legend_retires' appended to the two landing names respectively."

patterns-established: []

requirements-completed: [CFG-85]

coverage:
  - id: D1
    description: "15+ new CSS selectors (.aspect-card, .aspect-card__preview, .usage-row + --secondary/__name/__meta/__swatch, .palette, .palette-chip + __swatch/__name/__check, .palette-swatch + __band, .leading-option + __name, .rule-add) style the Aspect tile end to end on existing tokens only — zero new custom properties, zero new hex literals, zero new font families, and the one new font-size (10px) widens an existing sub-scale exception rather than adding a new size; the three permitted geometry/typography literals (64px palette-grid track floor, the swatch band's four percentages, the 10px/1.2 caption) each carry a written argument beside the declaration"
    requirement: CFG-85
    verification:
      - kind: unit
        ref: "this plan's own Task 1 inline verify script (rule presence, :has() block count pinned at 1, .palette declares no overflow-x/scroll-snap/nowrap, accent-list names .palette-chip/switch__track/skypane-row-arrive) — OK"
        status: pass
      - kind: unit
        ref: "companion/test_companion_app.py (run) — 317/317, including the motion-budget and feature-query-block pins unmoved"
        status: pass
      - kind: other
        ref: "token-growth arithmetic (pre-task HEAD a378020 vs. this plan's tree): custom properties 40 -> 39 (shrank, one --js-gate-display use retired with its rule), hex literals 21 -> 21, font-family declarations 3 -> 3, font-size declarations 10 -> 10 (the 10px caption already existed via .sparkline-axis-label/.drawing-axis-label, so growth is zero as the acceptance criteria's own escape clause allows)"
        status: pass
    human_judgment: false
  - id: D2
    description: "The selected palette chip's border/inset-ring/12%-wash/check-glyph and the leading option's checked-state wash/text/weight both join the file's single existing @supports selector(:has(*)) block rather than opening a second one; the accent-reservation header list is extended by .palette-chip and the two outstanding Phase-23 consumers (.switch[aria-checked=\"true\"] .switch__track, @keyframes skypane-row-arrive), verified still present and still unlisted immediately before the edit"
    requirement: CFG-85
    verification:
      - kind: unit
        ref: "this plan's own Task 1 inline verify script (exactly one @supports selector(:has(*)) block; .palette-chip:has(input:checked) present; accent-list head names all three additions) — OK"
        status: pass
      - kind: other
        ref: "two required mutation tests (quoted in full below): removing button.calendar-disconnect-btn's element qualifier trips the specificity-relationship check; moving .palette-chip:has(input:checked) outside the @supports block trips the single-block-membership check — both reverted, git diff --stat empty after each"
        status: pass
    human_judgment: false
  - id: D3
    description: "The whole .frame-colours* block, .theme-chip-grid--strip and its child rule, and all five .theme-carousel* rules are retired from style.css (26 selector/rule entries) with a three-category (markup/py, js, harness) pre-delete consumer count recorded per selector in 30-CSS-AUDIT.md, SHA-stamped; six selectors with surviving consumers (.theme-chip--compact, .theme-chip__body--placeholder, .theme-live-preview, .calendar-actions, .calendar-masked-url, button.calendar-disconnect-btn) are explicitly kept"
    requirement: CFG-85
    verification:
      - kind: unit
        ref: "this plan's own Task 2 inline verify script (zero live occurrences of .frame-colours/.theme-carousel/.theme-chip-grid--strip in comment-stripped source; all six kept selectors present; 30-CSS-AUDIT.md exists, SHA-stamped, >=20 selector rows, records all six NON-deletions) — OK"
        status: pass
      - kind: unit
        ref: "companion/test_companion_app.py (run) — 317/317 unchanged"
        status: pass
      - kind: other
        ref: "companion/static/style.css line count: 10704 -> 10666 (net -38 lines) — git show a378020:companion/static/style.css | wc -l vs. wc -l companion/static/style.css"
        status: pass
    human_judgment: false
  - id: D4
    description: "Both _ASPECT_REPIN_LEDGER rows owed to 30-07 are cleared: the destructive-disconnect check now asserts the specificity RELATIONSHIP (button.calendar-disconnect-btn after button[type=\"submit\"] in source order, not merely its presence) plus the palette chip's checked-state declarations inside the one @supports block; the segmented-control check keeps the T12 label-margin/height reset and retires the C1 panel-legend serif half outright (no legend left to point at), narrowing the serif boundary's own non-serif-exception set by one. EXPECTED_CHECK_COUNT re-derived by running, 274 -> 276"
    requirement: CFG-85
    verification:
      - kind: unit
        ref: "companion/test_config_page.py (run) — 276/276 checks pass"
        status: pass
      - kind: other
        ref: "no _ASPECT_REPIN_LEDGER row still names owed_by=30-07; both cleared rows' replacement defs are live in the file (confirmed directly, not only via the plan's own literal substring-ban verify script — see Deviations for why that literal script cannot pass as written)"
        status: pass
    human_judgment: false
  - id: D5
    description: "Full suite green outside the known, previously-routed floor: companion/test_companion_app.py 317/317, companion/test_config_page.py 276/276, companion/test_i18n.py untouched, companion/test_browser_ux.py unchanged at 84/91 (3 pre-existing floor + 4 rows already routed to 30-08 per 30-04-SUMMARY.md); scripts/run-all-tests.sh reports exactly one FAILED harness (test_browser_ux.py, the same documented floor) and every other harness green"
    requirement: CFG-85
    verification:
      - kind: integration
        ref: "companion/test_browser_ux.py (run standalone) — 84/91, the same 7 named FAILs 30-04-SUMMARY.md already documented, none newly introduced by this plan's CSS/harness changes"
        status: pass
      - kind: integration
        ref: "scripts/run-all-tests.sh (JOBS=10) — 21/22 harnesses PASS, test_browser_ux.py the one documented FAIL"
        status: pass
      - kind: e2e
        ref: "playwright:display_light_360.png, display_light_desktop.png, display_dark_360.png, display_dark_desktop.png, display_arrivals_open.png, display_calendar_open.png, display_rows_open.png — real Chromium screenshots at 360px/390px/1280px in both colour schemes"
        status: pass
    human_judgment: true
    rationale: "The eyes-on visual read (does the tile look right, is anything illegible or broken in dark mode) is exactly the kind of judgment this plan's own verification section defers to a human read rather than a pixel-diff — the screenshots are attached as evidence, but whether the result is acceptably polished is a call this SUMMARY states plainly rather than one an automated check can make."

duration: ~70min (from 30-06's own completion commit, a378020, to this plan's last commit, c2c2848)
completed: 2026-09-22
status: complete
---

# Phase 30 Plan 07: The Aspect tile is styled, the carousel CSS retires Summary

**Fifteen new CSS selectors style the merged Aspect accordion tile (card, rows, wrapping 18-swatch palette, leading option, nested rule-add disclosure) entirely on existing tokens, the selected-chip and leading-option states join the file's one `@supports selector(:has(*))` block, the accent-reservation header list is exhaustive again for the first time since Phase 23, `.frame-colours*`/`.theme-carousel*`/`.theme-chip-grid--strip` (26 rules) retire with a three-category pre-delete audit, and both `_ASPECT_REPIN_LEDGER` rows owed to this plan are cleared with `test_config_page.py` re-pinned from 274 to 276.**

## Performance

- **Duration:** ~70 min (from 30-06's own completion commit, `a378020`, to this plan's last commit, `c2c2848`)
- **Started:** 2026-09-22 (immediately following 30-06's completion)
- **Completed:** 2026-09-22
- **Tasks:** 3/3
- **Files modified:** 2 (`companion/static/style.css`, `companion/test_config_page.py`) + 1 created (`30-CSS-AUDIT.md`)

## Accomplishments

- **`companion/static/style.css`** (10704 → 10666 lines, net -38): `.aspect-card`'s own `>=960px` two-column layout (`grid-template-columns: minmax(360px, 1fr) minmax(0, 1fr); grid-template-rows: auto repeat(4, auto);`, the live preview in `grid-row: 2 / -1` of column 1, the four `.usage-row` elements auto-placing into column 2) — everything else the card needs (surface, hairline, responsive padding) is already inherited from `.page-section`, restated nowhere. `.usage-row` gets a `border-top` divider (never on the first row, matching the developer-approved sketch's own accordion markup verbatim) and its own `<summary>` override: `color: inherit` (not the UI-SPEC's cited, non-existent "50%-muted" literal — see Deviations) plus `gap`/`padding` around the inherited global 44px-floor chevron, whose own colour is separately muted to the file's real, established 70%-strength idiom. `.usage-row__name`/`__meta`/`__swatch` carry the row's typography/swatch sizing (`--space-xl`, 32px, spent as the token rather than restated as a literal). `.palette` is the wrapping `grid-template-columns: repeat(auto-fill, minmax(64px, 1fr))` grid CFG-85 names explicitly — no strip, no scroll-snap, no nowrap, no fixed child width. `.palette-chip`/`__swatch`/`__name`/`__check` and `.palette-swatch`/`__band` give the new, smaller CSS-drawn swatch its shape (no `<img>`, no photo, per the Swatch Rendering Contract) — `.palette-chip__name` at 10px/1.2 widens the existing `.sparkline-axis-label`/`.drawing-axis-label` sub-scale exception rather than inventing a size. `.leading-option`/`__name` gives "Comme les départs" a full-row-width control (`grid-column: 1 / -1` inside the same `.palette` grid its 18 siblings occupy — load-bearing, confirmed against the sketch). `.rule-add` gets spacing only, per the plan's own literal instruction. Inside the file's ONE `@supports selector(:has(*))` block: `.palette-chip:has(input:checked)` (border + inset ring), `.palette-chip:has(input:checked) .palette-chip__name` (12% accent wash — the swatch itself is deliberately excluded, exactly as `.theme-chip__preview` is, so the real ink colour is never tinted), `.palette-chip:has(input:checked) .palette-chip__check` (display: inline-flex), and `.leading-option:has(input:checked)` (a re-keyed consumer of `.theme-form .theme-option--active`'s existing 12%-wash/accent-text/semibold idiom) — four new rules; two retired rules removed from the same block (`.frame-colours__list li:has(input:checked) .frame-colours__row`, `.theme-carousel:has(.theme-carousel__all[open]) .theme-chip-grid--strip`). The header comment's accent-reservation list is extended (verbatim quote below) by `.palette-chip` and by Phase 23's two long-outstanding consumers (`.switch[aria-checked="true"] .switch__track`, `@keyframes skypane-row-arrive`), both re-verified present and unlisted immediately before the edit. The whole `.frame-colours*` block, `.theme-chip-grid--strip` + its child rule, and all five `.theme-carousel*` rules are deleted, with a dangling comment pointer to the retired `.frame-colours__panel-legend` corrected in place (not deleted) to point at `.data-table th` instead.
- **`.planning/phases/30-…/30-CSS-AUDIT.md`** (created): per-selector, three-category (markup/py, js, harness) pre-delete consumer counts for all 26 deleted rule entries and explicit NON-deletion rows for all six kept selectors, SHA-stamped at `a378020113551a3dc8a78f836e7fa5497a23bcc1`.
- **`companion/test_config_page.py`** (274 → 276 checks): `_destructive_disconnect_is_secondary_and_selection_is_free_and_focusable_after_the_accordion_rebuild` re-proves the destructive control's specificity RELATIONSHIP (element-qualified AND after `button[type="submit"]` in source order — not merely present) plus the palette chip's checked-state declarations living inside the one `@supports` block. `_segmented_control_resets_the_global_label_margin_and_the_legend_leaves_the_serif_after_the_panel_legend_retires` keeps the T12 half (the rule-kind segmented control's label-margin/height reset, confirmed unaffected) and retires the C1 half outright — `.frame-colours__panel-legend` has no legend left to point at, and the rule-add form's own "Match by" control never had a `<legend>` to begin with (it labels itself via a visually-hidden `<span>` + `aria-labelledby`). Both ledger rows land under names diverging from the ledger's own predicted "replacement" (a same-name-repoint guard collision, resolved identically to 30-05/30-06's own precedent). `EXPECTED_CHECK_COUNT` re-derived by running: 274 → 276.

## Task Commits

1. **Task 1 + Task 2 (combined — see Deviations): the new rules on existing tokens, and the audited deletions** — `f36bd8c` (feat)
2. **Task 3: re-pin the CSS-declaration checks and clear the 30-07 ledger rows** — `c2c2848` (test)

**Plan metadata:** this SUMMARY's own commit (docs, made after this file)

## Files Created/Modified

- `companion/static/style.css` — 15 new selectors styling the Aspect tile; four new rules plus two deletions inside the one `@supports selector(:has(*))` block; the accent-reservation header list extended by three entries; `.frame-colours*`/`.theme-carousel*`/`.theme-chip-grid--strip` retired (26 rule entries); net -38 lines.
- `companion/test_config_page.py` — two `_ASPECT_REPIN_LEDGER` rows cleared with new re-pinned check functions; `EXPECTED_CHECK_COUNT` 274 → 276.
- `.planning/phases/30-…/30-CSS-AUDIT.md` — created, the three-category pre-delete consumer audit.

## Accent-List Edit (verbatim, from `companion/static/style.css`'s header comment)

```
 * 30-07-PLAN.md Task 1 (CFG-85): the Aspect card's palette chip
 * (`.palette-chip`, `@supports selector(:has(*))` block, far below) is a
 * NEW SELECTOR consuming the ALREADY-LISTED selected-selectable-card use
 * above (`.theme-chip`/`.runway-card`'s own border/check-glyph/
 * background-wash) — the identical accent treatment, at a smaller box,
 * for a third selectable-card component. Not a new use; naming the
 * selector here rather than duplicating the list entry.
 *
 * The same commit also closes a gap this list's own prose has recorded
 * as open since Phase 23 (see the sketch-findings-skypane skill's Colour
 * section, "the pointer above is currently POINTING AT A LIST THAT IS NO
 * LONGER EXHAUSTIVE"): two genuine Phase 23 accent consumers were added
 * without ever being named here, re-verified still present and still
 * unlisted immediately before this edit. (1) `.switch[aria-checked=
 * "true"] .switch__track { background: var(--color-accent); border-
 * color: var(--color-accent); }` (23-07) — a switch's on-state, an
 * author fill on a custom button and therefore NOT covered by the
 * existing native-`accent-color` entry above. (2) the
 * `@keyframes skypane-row-arrive` wash — `color-mix(in srgb,
 * var(--color-accent) 22%, transparent)` (23-08) — the newly-arrived
 * Flights row's draining wash, an ARRIVAL signal distinct from the
 * selected-card wash entry's SELECTION signal, a use this list has
 * never carried. Both genuine broadenings, recorded because this list
 * is kept exhaustive on purpose.
```

**Pre-check confirmation:** both `.switch[aria-checked="true"] .switch__track` (`style.css:8747` pre-edit) and `@keyframes skypane-row-arrive` (`style.css:577` pre-edit) were grepped directly and confirmed present and unlisted in the header comment immediately before this edit — neither had been closed by any plan between Phase 25 (the last plan to check) and now.

## Token-Growth Arithmetic (Task 1's own required artifact)

Measured against the pre-task `HEAD` (`a378020113551a3dc8a78f836e7fa5497a23bcc1`), comment-stripped:

| Category | Before | After | Verdict |
|---|---|---|---|
| Custom properties (`--[a-z-]+:` distinct) | 40 | 39 | shrank (one `--js-gate-display` use retired with `.theme-carousel__pagers`) — not a growth |
| Hex literals (`#[0-9A-Fa-f]{3,8}` distinct) | 21 | 21 | unchanged |
| `font-family:` declarations (distinct) | 3 | 3 | unchanged |
| `font-size:` declarations (distinct) | 10 | 10 | unchanged — the new 10px caption already exists in the file via `.sparkline-axis-label`/`.drawing-axis-label`, so it grows the SET by zero, exactly the escape clause the acceptance criteria describes |

## `style.css` Line Delta (Task 2's own required artifact)

- Before (`a378020113551a3dc8a78f836e7fa5497a23bcc1`): **10704** lines
- After (this plan's final commit): **10666** lines
- **Net: -38 lines**

## Mutation Test Results (Task 3's two required mutations, both quoted, both reverted)

1. **Remove `button.calendar-disconnect-btn`'s element qualifier** (mutated to `button.calendar-disconnect-btn-XXX {`):
   > `expected style.css to declare 'button.calendar-disconnect-btn {' (element-qualified — a bare '.calendar-disconnect-btn' is only (0,1,0) and loses to button[type="submit"]'s (0,1,1) regardless of source order)`
   (caught by `_destructive_disconnect_is_secondary_and_selection_is_free_and_focusable_after_the_accordion_rebuild`)

2. **Move `.palette-chip:has(input:checked)`'s base rule outside the `@supports` block:**
   > `expected '.palette-chip:has(input:checked) {' to live inside the @supports selector(:has(*)) block`
   (caught by the same check)

Both mutations reverted from a backup taken before mutating; `git diff --stat companion/static/style.css` empty after restore, `companion/test_config_page.py` re-confirmed at 276/276 and `companion/test_companion_app.py` at 317/317.

## Narrowed Serif-Exception Set (design-system fact for `sketch-findings-skypane`)

`.frame-colours__panel-legend` — the skill file's own documented "Second non-serif exception" (a `<legend>` wearing the 12px uppercase label voice, overridden off the shared serif family) — retires WITH its selector this plan. The rule-add form's "Match by" segmented control, the only remaining candidate consumer in this region, never had a `<legend>` of its own to begin with (it labels itself via a visually-hidden `<span>` + `aria-labelledby`, confirmed at `config_page.py:4910-4912`). This genuinely NARROWS the serif boundary's own documented non-serif-exception set by one — a fact for a future session to fold into the skill's Typography section, not merely a locator change.

## Visual Eyes-On Pass (real Chromium, `Harness` + Playwright, both themes)

Booted a real `companion/app.py` subprocess (`Harness`), signed in, and captured `/display` with a real Chromium browser at 360×1200 and 1280×1400, in both `light` and `dark` colour schemes, plus three interaction states (Arrivals row open, Calendar row open, Rules row + nested "Add rule" disclosure open). Screenshots retained at `/private/tmp/.../scratchpad/shots/` for this session.

**What is right:**
- The card renders as one coherent tile — preview, four accordion rows, dividers between them — with no visible breakage at either width or in either theme.
- At `>=960px` the two-column layout works exactly as designed: the live preview sits in the left column, spanning the full height of the four accordion rows in the right column, with the "Aspect" heading spanning both columns above.
- The selected palette chip (White, Departures) is clearly legible in BOTH themes: a visible accent border + inset ring in light mode, and an equally legible accent border against the dark card surface in dark mode (measured by direct pixel crop) — no "legible in light, invisible in dark" defect.
- The accordion row's own `<summary>` (e.g. "Departures — White") reads in the ordinary text colour, not accent, with a quietly muted chevron — matching the UI-SPEC's "not accented" requirement without inventing a new colour-mix strength.
- The "Comme les départs" leading option, when checked (Arrivals' default state), renders as a clearly full-row-width, accent-washed, bold-accent-text control, visually distinct from the palette chips below it.
- The Calendar row's connection block (status dot, "Not connected", the feed-URL field, the accent-filled "Connect calendar" button, "How it works") flows directly beneath the palette with no third "Gérer" wrapper, exactly as 30-UI-SPEC.md §6 specifies.
- The Rules row's nested "+ Add rule" disclosure correctly renders the UNCHANGED, visually distinct `.theme-chip--compact` grid (photo-preview chips), confirming the two chip renderers stay genuinely separate components.

**What is not (a stated observation, not a blocking defect):** the `.rule-add` disclosure has no visual separation (border/background) from the rule list above it — the transition from the rule list into the open "Add rule" form reads a little flat/bare, since this plan's own instruction for that selector was "add spacing only," and the developer-approved sketch's own fuller bordered/backgrounded treatment was deliberately not carried over (see Deviations). This is not broken, and 30-UI-SPEC.md does not require the fuller treatment — flagged here as a genuine, future, separate polish decision rather than fixed unilaterally in this plan.

## Decisions Made

See `key-decisions` in the frontmatter for the five substantive ones: the Task 1+2 commit-granularity merge; the `color: inherit` substitution for the UI-SPEC's non-existent "50%-muted" chevron literal; the explicit non-carry-forward of `min-width: 0`'s reasoning; the literal "spacing only" reading of `.rule-add`; and the kept-despite-zero-consumers status of `.theme-chip__body--placeholder`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] The header-comment accent-list edit's own Phase-23 paragraph broke a plan verify assertion by wrapping a search literal across a line break**
- **Found during:** Task 1's own inline verify script, first run
- **Issue:** The `@keyframes skypane-row-arrive` name was hyphenated across two comment lines (`skypane-\n * row-arrive`), so a literal substring search for `"skypane-row-arrive"` failed even though the prose read correctly to a human.
- **Fix:** Reworded the sentence so the identifier is never split across a line break.
- **Files modified:** `companion/static/style.css`
- **Verification:** the verify script's `head` check passes; `git diff` shows only prose rewording, no property change.
- **Committed in:** `f36bd8c` (Task 1+2 commit)

**2. [Rule 1 - Bug] Task 3's own new segmented-control check tripped its own C1-half assertion via its own docstring/comment**
- **Found during:** Task 3, first run of the new check after writing it
- **Issue:** `if ".frame-colours__panel-legend" in source: ...` (raw substring) failed because this exact plan's own repointed comment in `style.css` (the corrected dangling pointer near `.copy-btn--copied .copy-btn__label`) legitimately names the retired selector by name to explain what it used to point at — the identical class of collision 30-03/30-04/30-06-SUMMARY.md already documented for other checks.
- **Fix:** Comment-stripped the source before searching, matching this file's own established idiom (`re.sub(r"/\*.*?\*/", "", source, flags=re.DOTALL)`, already used by `_strong_selected_treatment_is_keyed_to_the_live_checked_radio()` and others).
- **Files modified:** `companion/test_config_page.py`
- **Verification:** `companion/test_config_page.py` 276/276.
- **Committed in:** `c2c2848` (Task 3 commit)

### Escalated, Not Auto-Fixed

**3. [Escalated] Task 3's own literal inline `<verify>` script (`for dead in (...): if dead in cp: fail...`) cannot pass as written against the finished tree, and was not force-satisfied by weakening a real check**
- **Found during:** Task 3, running the plan's own copy-pasted verify script verbatim
- **Issue:** The script bans the raw substrings `"frame-colours"`, `"theme-carousel"`, `"theme-chip-grid--strip"` anywhere in `companion/test_config_page.py`. This is structurally unsatisfiable for two independent reasons, neither fixable by comment-stripping (deviation 2's fix): (a) `_ASPECT_RETIRED_MARKUP_TOKENS` (a pre-existing, LIVE, load-bearing tuple from 30-05-PLAN.md Task 1, used by `_aspect_card_full_shape_checklist()` and others to assert these exact strings are ABSENT from rendered Display markup) necessarily contains them as real Python string literals, not comments — deleting this tuple to satisfy the scan would remove genuine CFG-85 regression coverage, which is the opposite of this gate's own intent; (b) this plan's OWN two new check functions must contain the retired selector names as search targets to assert their ABSENCE from `style.css` (e.g. `if ".frame-colours__panel-legend" in stripped:`) — an assertion of absence is, unavoidably, a piece of code that names the thing being checked for.
- **Why not fixed:** Deleting or respelling `_ASPECT_RETIRED_MARKUP_TOKENS`, or writing my own two checks without naming their search targets, would either destroy real test coverage or make the checks silently vacuous — both strictly worse outcomes than the literal script failing. Extensive historical prose from 30-03/30-05/30-06 (ledger `"why"` fields, retired-check-location comments) also legitimately names these retired selectors as historical record and was left untouched, matching this phase's own established convention that a comment is not a consumer and existing record-keeping should not be scrubbed to satisfy a grep.
- **What was verified instead:** The INTENDED property this gate exists to prove — no LIVE code, and no test locator, still tries to find real markup via a retired selector — is confirmed directly: both cleared ledger rows' replacement functions have live `def`s (confirmed by the plan's own ledger-guard check, `_every_aspect_repin_ledger_row_names_a_live_or_owed_replacement`, PASS); `_ASPECT_RETIRED_MARKUP_TOKENS` continues to correctly assert these strings are absent from rendered `/display` output (confirmed by `_aspect_card_full_shape_checklist` staying green); and neither of this plan's own two new checks uses a retired selector as its locating mechanism (both use the NEW mechanism — `button.calendar-disconnect-btn`'s source order, and `.palette-chip:has(input:checked)` — for locating what they assert on; the retired strings appear only in prose and in an absence-assertion).
- **Files modified:** none beyond what Tasks 1-3 already changed
- **Verification:** `companion/test_config_page.py` 276/276; `companion/test_companion_app.py` 317/317; `scripts/run-all-tests.sh` — 21/22 harnesses green, the one documented `test_browser_ux.py` floor unchanged.
- **Committed in:** n/a (verification-methodology finding, no code change beyond the two commits already described)

---

**Total deviations:** 2 auto-fixed (both Rule 1, verify-script-collision fixes with no property change) + 1 escalated (a plan-authored verify script that is structurally unsatisfiable without destroying real test coverage, resolved by verifying the underlying intended property directly instead)
**Impact on plan:** None of the three changed what the Aspect tile renders or how it behaves. The two auto-fixes are pure verification-methodology corrections (a line-wrap, a comment-stripping idiom) matching this phase's own repeated precedent. The escalated item is a genuine plan-authoring imprecision, not a code defect — the underlying CFG-85 property (no live reference to retired CSS) is affirmatively confirmed, just not via the exact literal script text.

## Issues Encountered

None beyond the deviations documented above. `scripts/run-all-tests.sh` ran cleanly in ~230s wall time (JOBS=10), with `test_browser_ux.py` the one expected FAIL (the same 7-check floor 30-04/30-05/30-06 already documented, none newly introduced here).

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- The Aspect tile is now fully styled and visually verified in both themes at both the 360px floor and desktop — no known visual regressions from this plan's own CSS work.
- `companion/test_config_page.py` is green at `EXPECTED_CHECK_COUNT = 276`; `companion/test_companion_app.py` unchanged at `317/317`; `_ASPECT_REPIN_LEDGER` owes nothing further to any plan in this phase (both remaining rows, both owed to 30-07, are now cleared — the ledger's own guard confirms no row anywhere still names `owed_by` outside `""`).
- `companion/test_browser_ux.py` carries forward its documented 84/91 floor (3 pre-existing + 4 rows already routed to 30-08 by 30-04-SUMMARY.md) — untouched by this plan, as instructed.
- 30-08 (the phase's own remaining plan, per ROADMAP) inherits a fully-styled, fully-CSS-audited Aspect card and can proceed directly to its own scope (the `.theme-chip`-locator browser-check rewrites and the CFG-86 closing measurement) without any CSS debt left behind by this plan.
- `.theme-chip__body--placeholder`'s zero-consumer status (kept per this plan's own explicit instruction) is flagged as a candidate for a future dead-CSS cleanup pass — not blocking, not this plan's to resolve.
- The `.rule-add` disclosure's minimal "spacing only" styling (vs. the sketch's fuller bordered box) is flagged as a genuine, separate, future polish decision — not a defect, not blocking.

---
*Phase: 30-aspect-rebuilt-one-tile-three-rows-one-palette-the-calendar-absorbed-sketch-first*
*Completed: 2026-09-22*

## Self-Check: PASSED

- FOUND: `.planning/phases/30-aspect-rebuilt-one-tile-three-rows-one-palette-the-calendar-/30-07-SUMMARY.md`
- FOUND: `.planning/phases/30-aspect-rebuilt-one-tile-three-rows-one-palette-the-calendar-/30-CSS-AUDIT.md`
- FOUND: commit `f36bd8c` in `git log --oneline --all`
- FOUND: commit `c2c2848` in `git log --oneline --all`
