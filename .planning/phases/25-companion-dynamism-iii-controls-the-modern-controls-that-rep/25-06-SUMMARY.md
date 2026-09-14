---
phase: 25-companion-dynamism-iii-controls-the-modern-controls-that-rep
plan: 06
subsystem: companion-controls
tags: [theme-carousel, scroll-snap, no-js-floor, details-disclosure, radiogroup, page-height]
requires:
  - "companion/pages/config_page.py::_theme_chip_grid_html — the ONE chip renderer, four call sites (15-D05 / 21-05)"
  - "companion/static/theme-preview.js — the live preview and its crossfade (20-08, 23-10)"
  - "companion/static/style.css::.js-gate / .control-hit-area (25-01)"
  - "companion/test_browser_ux.py::_persist_without_js / _operate_with_keyboard / _assert_hit_target / _assert_js_gate / _no_js_page / _set_ui_theme (25-02)"
  - "companion/test_companion_app.py::_NO_JS_CONTROL_REGISTRY (25-01)"
provides:
  - "companion/pages/config_page.py::_theme_carousel_html (the presentation, never a second renderer)"
  - "companion/pages/config_page.py::THEME_CAROUSEL_* (strip id, wrapper/pager attributes, four copy constants)"
  - "companion/static/style.css::.theme-chip-grid--strip (+ its chips) / .theme-carousel__all / __pagers / __pager / __dots"
  - "companion/static/theme-preview.js::the two pager click handlers (the file GREW; no new script)"
  - "companion/test_browser_ux.py::_display_page_height (the reusable Display page-height instrument)"
affects:
  - "25-07 (the drop zone — the last control plan; the gate, the hit-area synthesis and the height instrument are all reusable as-is)"
  - "25-08 (the phase gate: the page-height outcome is the item the developer most needs to see, since X6 has now been attempted twice)"
tech-stack:
  added: []
  patterns:
    - "a carousel is the same radio group re-laid-out, not a new control: swipe and arrow keys are then both native"
    - "a <details> can GOVERN the layout of the sibling that follows it, which is how one set of radios can be both a strip and a full grid"
    - "a scroll container needs scroll-padding at its end edge whenever the focus target inside it is a 1px visually-hidden input"
    - "a grid blowout takes TWO declarations to close when a <fieldset> is in the chain, and each alone leaves the whole blowout"
    - "a page-height criterion is a registered instrument, run before the change and again after, never a number typed in afterwards"
key-files:
  created: []
  modified:
    - companion/pages/config_page.py
    - companion/static/style.css
    - companion/static/theme-preview.js
    - companion/i18n_fr/display.py
    - companion/test_config_page.py
    - companion/test_companion_app.py
    - companion/test_browser_ux.py
key-decisions:
  - "ONE set of eighteen radios. The <details> governs the layout of the grid that follows it rather than containing a second copy — the plan's own recommended shape is impossible as literally written, because a closed <details> hides its own children"
  - "a native <details>, never a <dialog>: showModal() is the only thing that opens a dialog, so eighteen themes behind one is eighteen themes behind a dead control with scripts blocked"
  - "the dots row carries each theme's own registry colour and NO selection state — without a script or a :has() chain a server-rendered active dot could only mark the SAVED theme and would be wrong the instant a chip is clicked"
  - "the carousel is NOT moved beside the live preview: the departures panel stays inside .frame-colours__panels, because moving it would break theme-preview.js's four-panel collapse contract for an adjacency that does not exist at the 390px viewport this plan is judged at"
  - "the pager gap is --space-lg and that is a hit-target number, not a spacing one: at --space-sm the two 44px ::before synthesis boxes overlap and the Previous pager hit-tests at 30x45"
patterns-established:
  - "adjacent-sibling [open] layout toggle: details[open] + .strip { flex-wrap: wrap } — no :has(), so the one feature query is untouched and the block count stays at 1"
  - "scroll-padding-right equal to one item's width, with a harness check reading BOTH numbers out of the stylesheet and requiring them equal"
requirements-completed: []
duration: ~5h
completed: 2026-09-14
---

# Phase 25 Plan 06: D5's theme carousel — the measurement it was judged by Summary

**Display's eighteen-chip departures grid is now one scroll-snap row of the same
eighteen native radios, with the full grid behind a native `<details>` and two
`.js`-gated pagers — and the page it was supposed to shorten measures 3743 px at
390 px against a 2600 px target, which is 1143 px short and is reported as such.**

## The decision that mattered most

**How one set of radios can be both a strip and a full grid.**

The plan named the duplication question as the thing that decides the whole of
Task 3, and recommended one set: *"the `<details>` wraps the SAME grid, and the
strip is that grid's own overflow presentation when closed."* **Taken literally
that is impossible**, and the impossibility is worth stating plainly because it
is the one plan assumption that turned out wrong: a `<details>` hides its own
non-summary children when it is closed. A disclosure *containing* the grid would
hide all eighteen themes whenever it was shut, and there would be no strip at
all — the exact opposite of what the plan asks for in the same sentence.

So there were two real options:

| | one set | two sets |
|---|---|---|
| radios named `theme` on the page | 18 | 36 |
| what the disclosure does | changes the layout of the grid after it | reveals a second copy of it |
| `--selected` chips on screen | 1 | 2 |
| chip preview images on screen | 18 | 36 |
| risk | a disclosure whose own subtree is one paragraph | two places showing one setting, able to disagree (T-25-06-B) |

**One set was chosen**, and the mechanism is an adjacent-sibling combinator:

```css
.theme-carousel__all[open] + .theme-chip-grid--strip { flex-wrap: wrap; }
```

No `:has()` is involved, so the phase's single highest-risk assertion — the one
`@supports selector(:has(*))` block, whose specificity arithmetic is marked
"verified, not to be re-derived" — was never even approached. The block count is
still exactly 1, brace-anchored, and the whole `.theme-chip` selected treatment
is byte-identical.

The honest consequence, recorded at the markup site as well as here: **nothing is
hidden behind that disclosure at any time.** Every theme is always in the strip,
always reachable by arrow key, always selectable, always saveable. The disclosure
changes a layout, not a visibility, and its body says so in real translated text
rather than leaving a reader to discover it.

The two sets were rejected on a specific ground rather than tidiness: 36 radios
sharing a name and a form are still ONE radio group to a browser (so exactly one
would post), but the page would then carry two `--selected` chips, two check
glyphs and two copies of every chip image for a setting with one value.

## The height, reported honestly

This is the criterion the plan gave itself, and the number is the verdict.

| Viewport | Before (Task 1, before any markup change) | After (Task 4, same instrument) | Change |
|---|---|---|---|
| **390 px** | **4276 px** | **3743 px** | **−533 px** |
| **360 px** | **4269 px** | **3752 px** | **−517 px** |

**X6's target is ≤ 2600 px on a phone. It is NOT MET: 3743 px is 1143 px over
it.** D5's own audit row asks for "Display page drops below 1 500 px", which is
2243 px away.

What this plan closed is real and is the largest single item that was left: the
departures grid was eighteen 104 px chips wrapping three-per-row into six rows,
and it is now one row. What remains is not a grid — it is four more cards
(Calendar, Runway, Quiet hours, the three other usage panels) and the Frame strip
above them. There is no further density win of this size available inside a
control plan's scope, and pretending otherwise by moving the goalposts would be
worse than missing them. 22-10 set the precedent by recording its own shortfall;
this records the second attempt's.

Two things worth noting about the numbers themselves:

- **The before-numbers are much larger than 22-10's own 3661 px at 390 px.** That
  is not a regression this plan caused: phases 23–25 added the runway map, the
  quiet-hours dial and other Display content between the two measurements. The
  only comparison that means anything is before-vs-after **by the same
  instrument on the same tree**, which is exactly why the instrument exists.
- **The carousel itself adds about 82 px** (a 44 px `<summary>`, the dots row and
  the pager row) on top of the ~615 px the strip removes. That cost is in the
  −533 px above; it is not hidden.

## What was built

### Task 1 — the instrument, before there was anything to like

`_display_page_height()` measures Display's `documentElement.scrollHeight` at a
given viewport with scripts **enabled** (the height a visitor actually sees
includes `theme-preview.js` collapsing three of the four usage panels at load; a
scripts-blocked measurement would report a page nobody with a default browser
ever sees).

It asserts **no target at all** — the number is the criterion — but it does
assert four things about where the number came from: the measurement was taken at
the width asked for, the document is the authenticated Display page (proved by
its Frame colours heading **and** a full `THEME_IDS`-sized departures radiogroup,
never merely "a page rendered"), and the document is taller than the viewport.

### Task 2 — the carousel, around the one renderer

`_theme_carousel_html()` wraps `_theme_chip_grid_html()`'s existing output. It
emits no chip. The departures call site gained one extra grid-level class and an
`id`; nothing else changed.

Proven rather than asserted: **the arrivals, calendar and rule-add grids render
byte-identical output** (captured before the change and diffed after — three of
three identical), and a source scan finds **exactly one** function in
`config_page.py` emitting a chip `<label>` carrying `data-preview-src`.

### Task 3 — the disclosure and the two pagers

`theme-preview.js` **grew**; no new file appeared. The deferred-script pin is
still fifteen and `ls companion/static/*.js | wc -l` is still 17. The reason is
recorded in the script's own header: the phase's one-script budget went to
`value-controls.js` in 25-01, and on the merits this file already owns this radio
group — a second file would be two scripts bound to one control.

The pagers register **click only**. No `keydown`/`keyup`/`keypress` and no
`preventDefault` anywhere in the file, asserted by a harness check, because a
pager capturing `ArrowLeft` would take the native radiogroup selection away from
the scripts-blocked path that depends on it.

### Task 4 — the measurements

See the mutation table below. The three new browser checks are described in the
harness's own `EXPECTED_CHECK_COUNT` comment.

## Every mutation, with its quoted failure

Each was applied to a staged tree, the changed line confirmed with `git diff`,
and reverted with `git checkout-index -f --` (with `__pycache__` cleared after
each sub-second cycle). **Twenty-four mutations were run. Twenty-three produced a
named failure; two are discussed separately below.**

### Non-vacuity of the height instrument (Task 1)

| # | Mutation | Line confirmed changed | Result |
|---|---|---|---|
| M0 | the instrument points at `/device` instead of `/display` | `page.goto(base_url + "/device")` | **RED** — *"`_display_page_height`: the document at 390px carries no Frame colours heading — this is not the authenticated Display page"* |

### Stylesheet and markup (Task 2), against `test_config_page.py`

| # | Mutation | Result |
|---|---|---|
| M1 | strip loses `flex-wrap: nowrap` | **RED** — *"`.theme-chip-grid--strip` does not declare `'flex-wrap: nowrap;'`"* |
| M2 | strip loses `overflow-x: auto` | **RED** — *"does not declare `'overflow-x: auto;'`"* |
| M3 | strip loses `scroll-snap-type` | **RED** — *"does not declare `'scroll-snap-type: x mandatory;'`"* |
| M4 | chips lose `flex: 0 0 auto` | **RED** — *"`.theme-chip-grid--strip > .theme-chip` does not declare `'flex: 0 0 auto;'`"* |
| M5 | chips lose `scroll-snap-align` | **RED** — *"does not declare `'scroll-snap-align: start;'`"* |
| M6 | dots row loses `flex-wrap: wrap` | **RED** — *"`.theme-carousel__dots` does not declare `'flex-wrap: wrap;'`"* |
| M7 | dots row loses `margin-top` | **RED** — *"does not declare `'margin-top: var(--space-sm);'`"* |
| M8 | `.theme-chip--compact` gains `:has(input:checked)` | **RED** — *"a `.theme-chip--compact` rule carries `':has('` in its selector … the compact modifier is SIZE-ONLY"* |
| M9 | dots painted with `arriving_index` instead of `departing_index` | **no failure — and the mutation is unobservable in the product too.** See "Properties found inert" |
| M9b | dots painted with a fixed palette index | **RED** — *"the dots row carries \[18 × '#FFFFFF'\], expected one dot per theme in registry order…"* |
| M10 | dots row loses `aria-hidden` | **RED** — *"no aria-hidden `.theme-carousel__dots` row is rendered"* |
| M11 | the strip loses its `id` | **RED** — *"the strip carries no id='theme-carousel-strip', so the pagers' aria-controls names nothing"* |
| M12 | the departures grid loses the strip modifier | **RED** — *"the Frame colours card renders no `.theme-chip-grid--strip` at all"* |
| M13 | a SECOND chip renderer is forked | **RED** — *"expected exactly ONE function in config_page.py to emit a chip `<label>` carrying data-preview-src, got \['_forked_chip_grid_html', '_theme_chip_grid_html'\]"* |
| M14 | the layout grid track back to a bare `1fr` | **RED** — *"`.frame-colours__layout` does not declare `'grid-template-columns: minmax(0, 1fr);'`"* |
| M15 | the usage panel loses `min-width: 0` | **RED** — *"`.frame-colours__usage-panel` does not declare `'min-width: 0;'`"* |

### Disclosure, pagers and script (Task 3)

| # | Mutation | Result |
|---|---|---|
| M16 | the `<details>` becomes a `<dialog>` | **RED** — *"the Display page renders a `<dialog>` — a dialog cannot be opened without script"* |
| M17 | the disclosure renders AFTER the strip | **RED** — *"the stylesheet reaches the strip through an adjacent-sibling combinator on the disclosure's \[open\] state, which only matches when the disclosure comes first"* |
| M18 | the pager wrapper renders outside the gate | **RED** — *"the pager wrapper's classes are '' — without 'js-gate' it renders permanently with scripts blocked"* |
| M19 | the pagers lose their `aria-label` | **RED** — *"it draws its arrow in CSS and has no text of its own, so without one it announces nothing at all"* |
| M20 | `aria-controls` stops naming the strip | **RED** — *"that is not only an announcement: theme-preview.js resolves the element to scroll through this very attribute"* |
| M21 | `theme-preview.js` grows a `keydown` listener | **RED** — *"a pager that captures an arrow key breaks the native radiogroup selection the no-JS path depends on"* |
| M22 | the script renames its pager constant to `data-theme-pagerr` | **no failure at first — a real bug in the check, fixed. See below** |
| M22b | the same rename, against the boundary-anchored check | **RED** — *"companion/static/theme-preview.js never names 'data-theme-pager', so the two pagers it is supposed to own are two buttons that do nothing"* |
| M23 | the `[open]` rule loses `flex-wrap: wrap` | **RED** — *"`.theme-carousel__all[open] + .theme-chip-grid--strip` does not declare `'flex-wrap: wrap;'`"* |
| M24 | the pager gap drops to `--space-sm` | **RED** — *"`.theme-carousel__pagers` does not declare `'gap: var(--space-lg);'`"* |
| M25 | the prev chevron loses its rotation | **RED** — *"`.theme-carousel__pager--prev::after` does not declare `'transform: rotate(135deg);'`"* |

### The browser, against `test_browser_ux.py` (Task 4)

| # | Mutation | Result |
|---|---|---|
| M26 | **the strip's radios given `display: none` instead of `.visually-hidden`** (the mutation the plan named) | **RED, two checks** — *"the saved theme's radio could not take focus with scripts blocked ({'focused': False}) — a radio hidden with display:none rather than the .visually-hidden utility is exactly this, and it takes arrow-key selection away with it"* and *"`_operate_with_keyboard`: `'input[name="theme"][value="black"]'` did not take focus from el.focus()"* |
| M27 | the strip stops reserving a chip's width at its end edge | **RED** — *"after 1 ArrowDown(s) the selected chip 'grey' sits 0.0px past the strip's left edge and 50.0px past its right"* |
| M28 | the pager gap drops to `--space-sm` | **RED** — *"the carousel's prev pager on /display: `'[data-theme-pager="prev"]'`'s hit area measures 30x45 at 360px, under the 44px floor in the x axis"* |
| M29 | the strip's chips lose `flex: 0 0 auto` | **RED, three checks** — *"the strip's scrollWidth (278) does not exceed its clientWidth (278) … it is not a strip and there is nothing to scroll"*, *"the Next pager left the strip at scrollLeft 0"*, and *"the carousel's FIRST chip … hit area measures 9x71 … its visual box is 7.9x70.4"* |
| M30 | the strip loses `overflow-x: auto` | **RED, four checks** — *"documentElement.scrollWidth 2049 against a client width of 360, painted past the right edge by \['theme-chip theme-chip--compact', …\]"* |
| M31 | the `[open]` rule stops re-wrapping the strip | **RED, two checks** — *"the disclosure opened and the strip is still one row (flex-wrap 'nowrap', chips spread over 0px) — 'See all themes' laid nothing out"*, plus the **pre-existing** every-disclosure-open sweep: *"gives a scroll container its own horizontal scrollbar with every disclosure open … boxWidth 278, content 2008"* |

That last one is worth naming: a check this plan did not write, from quick task
260913-eab, independently proves that opening the disclosure genuinely stops the
strip scrolling. It passes on the shipped tree and fails on the mutation.

### The one check that failed the vacuity question, and what was done

**M22.** The first version of the script-side seam clause asked
`if config_page.THEME_CAROUSEL_PAGER_ATTR not in script`. Renaming the script's
own constant to `"data-theme-pagerr"` — which matches nothing in the markup and
leaves both pagers completely inert — **passed it**, because the typo *contains*
the real name. This is Trap 2 wearing different clothes. The clause was rewritten
to match on a `(?<![-\w])…(?![-\w])` boundary, the same discipline
`test_companion_app.py`'s own gate-class pin already records, and re-mutated:
RED. A comment at the site records the measurement so the next reader does not
"simplify" it back.

## Properties found inert (and one that is not this plan's)

**M9 — the dots' colour source is unobservable, because the registry makes it
so.** Painting each dot with `arriving_index` instead of `departing_index`
changed **not one byte** of output. The cause is not a weak check:

    departing_index == arriving_index for 18 of 18 themes
    the eighteen themes resolve to SEVEN distinct palette hexes

So `.theme-chip`'s two swatch dots — the ones 22-10's `"Departures · Arrivals"`
legend names, copy 22-10 deliberately chose over the spec's wrong
`"Background · Ink"` *precisely because* the dots are the departing and arriving
inks — are the **same colour as each other in every shipped theme**. The legend
explains a distinction nobody can see. Nothing here caused it and nothing here
fixes it; the carousel merely put the same dots in a row where the repetition is
obvious. **Logged to `deferred-items.md`** with the measurement and a suggested
disposition.

The check was strengthened rather than left as-is: it now also requires the row
to carry **more than one distinct colour**, which catches the wrong
implementation that actually exists (a fixed palette index for every dot — M9b,
RED).

No declaration added by this plan was found inert. Every one of the eighteen new
declarations is covered by a mutation above.

## Criteria that did not evaluate as predicted

### 1. "A narrower viewport cannot make a reflowing page shorter" is false on Display

The first version of Task 1's check asserted it. Run against an unmodified tree,
Display measured **4276 px at 390 px and 4269 px at 360 px** — seven pixels
*shorter* at the narrower width — and the check failed a page with nothing wrong
with it. The cause is ordinary (a stack of cards whose rows round independently,
a handful landing on a different line count). The clause was **removed rather
than loosened to a tolerance**, because a tolerance would have been a number
invented to make a wrong belief pass. The measurement and the reason are recorded
in the check.

### 2. "The strip renders BESIDE the big live preview" — it does not, and should not here

The plan's Task 2 behaviour list says the strip sits *"beside the big live
preview"*. **It does not.** The departures grid stays inside its own
`.frame-colours__usage-panel`, in `.frame-colours__panels`, which is the card's
full-width third row — so the strip renders *under* the preview/assignment pair,
not beside it.

This was deliberate. Moving the departures panel out of `.frame-colours__panels`
would take it out of `theme-preview.js`'s four-panel collapse machinery, which is
D-08's locked no-JS floor (the server renders all four panels visible; the script
is the only thing that ever collapses three). Breaking that to gain a horizontal
adjacency **that does not exist at either of the two viewports this plan's own
success criterion measures** — everything stacks below 960 px — is a bad trade.
Stated rather than silently skipped.

### 3. The plan's prescribed no-JS mutation needed a check the plan did not name

The plan required that the no-JS check FAIL when the strip's radios are given
`display: none`. It would not have, as written from the plan's own materials:
`_persist_without_js()` operates a radio through `target.click()`, and
`HTMLElement.click()` works perfectly well on a `display: none` element, so the
save would still have reached disk. The property `display: none` actually
destroys is **focusability**, and with it arrow-key selection. So the no-JS check
gained an explicit clause — focus the saved radio through its own `.focus()` with
scripts blocked, assert it became `document.activeElement`, then press a real
`ArrowDown` and require the selection to move (arrow navigation in a radiogroup
is the browser's default action, so it works with no listener at all). With that
clause the prescribed mutation is RED twice over. Without it, it would have been
green, and the plan would have recorded a proof it did not have.

## Defects found and fixed while measuring

### The grid blowout, and why it took two declarations

With the strip in place and nothing else changed,
`documentElement.scrollWidth` read **2049 against a client width of 360** — the
page itself scrolling sideways by 1689 px, which is exactly the floor CFG-52
forbids.

The fix is two declarations, and **each was measured alone and each alone leaves
the entire 2049 px blowout in place**:

- `.frame-colours__layout { grid-template-columns: minmax(0, 1fr) }` — `1fr` is
  `minmax(auto, 1fr)`, and an `auto` minimum is the item's min-content width,
  which with a nowrap strip of eighteen chips is about 2000 px.
- `.frame-colours__usage-panel { min-width: 0 }` — the panel is a `<fieldset>`,
  and the UA stylesheet's `min-inline-size: min-content` re-introduces the same
  minimum one level down.

Both are pinned in `test_config_page.py` with the measurement in the comment, so
neither can be "tidied" away on the grounds that the other exists.

### Scroll-snap and the keyboard did not agree

Measured, and it is the finding this plan is most glad it looked for. Arrow-keying
moves focus to the next **radio**, and that radio is a 1 px `.visually-hidden` box
at its chip's top-left corner. The browser scrolls a 1 px target into view, is
satisfied the instant the chip's left edge appears, and leaves the chip the
visitor just selected hanging off the right edge:

    six ArrowDowns at 360px: focused chip at left 224 inside a 278px strip
                             — 50px of it outside, inView: false

Four candidate fixes were measured against 1, 3, 6, 10 and 17 steps. A
`scroll-margin-right` on the radio did nothing; `scroll-snap-align: center`
halved the problem; **`scroll-padding-right` on the scroll container fixed every
position**. The reserved width is one chip's width, and `test_config_page.py`
reads both that number and `.theme-chip--compact`'s own declared `width` out of
the stylesheet and requires them equal, so a future density pass cannot change
one and silently re-break the keyboard.

### The pagers' hit target, in this control's own container

`.control-hit-area` declares a 22 × 22 box with a `::before` at `inset: -11px`,
i.e. 44 × 44 on paper. **Measured at 360 px with the two pagers `--space-sm`
apart:**

    .theme-carousel__pager--prev
      visual box 22.0 x 22.0, real hit area 30 x 45
      reach from its own centre: 23 left, 6 right, 22 up, 22 down

The Next pager's own `::before` reaches 11 px left and wins the hit test in the
8 px gap, eating the Previous pager's right side — the same defect 25-02 recorded
for `.copy-btn` inside a Flights detail row. The gap is `--space-lg` (24 px), at
which the two `::before`s stop 2 px short of each other. **After the fix, both
pagers measure a real 45 × 45.**

## The measured hit-target results, in this plan's own container

At 360 px, on `/display`, by real hit-testing rather than by reading a rule:

| Element | Visual box | Hit area | Reach L/R/U/D |
|---|---|---|---|
| first chip in the strip | 106.1 × 70.4 | **106 × 71** | 53 / 52 / 35 / 35 |
| last chip in the strip | 106.1 × 70.4 | **106 × 71** | — |
| Previous pager | 22.0 × 22.0 | **45 × 45** | 23 / 21 / 22 / 22 |
| Next pager | 22.0 × 22.0 | **45 × 45** | — |

`control-density.md`'s **exempt-by-delegation** category stays valid for the chip
radios: the wrapping `.theme-chip` label exceeds 44 px in both axes inside the
strip, measured, at the narrowest supported width. **No new entry is added to the
touch-target floor register**, and the `.control-hit-area` relocation entry is
unchanged — the pagers are its fourth consumer at its own values verbatim.

## Re-derived check counts, obtained by RUNNING

| Harness | Before | After | How |
|---|---|---|---|
| `companion/test_browser_ux.py` | 74 | **78** | 74 → 75 (T1, +1) → 78 (T4, +3), run each time, 0 SKIPs |
| `companion/test_config_page.py` | 256 | **259** | 256 → 258 (T2, +2) → 259 (T3, +1), run each time |
| `companion/test_companion_app.py` | 313 | **313** | +0 — one registry row appended, no new check. 311 passing (the two documented WR-11 sandbox failures) |
| `companion/test_i18n.py` | 24 | 24 | unchanged, 24/24 |
| `companion/test_status_pages.py` | 302 | 302 | unchanged, 301/302 (the documented `anomaly_active()` sandbox failure) |
| `companion/test_contrast_check.py` | 49 | 49 | unchanged |

Other measured invariants, before → after:

| | Before | After |
|---|---|---|
| `@supports selector(:has(*)) {` blocks (brace-anchored) | 1 | **1** |
| `@keyframes` | 5 | 5 |
| `prefers-reduced-motion` occurrences | 9 | 9 |
| `interpolate-size` / `calc-size(` | ban comments only | unchanged |
| `ls companion/static/*.js \| wc -l` | 17 | **17** |
| deferred `<script src=` on the authenticated shell | 15 | **15** |
| stray comment terminators in `style.css` | 0 | 0 |

## Threat model

Every disposition in the plan's register holds.

- **T-25-06-A** (a posted `theme` outside the registry) — the whitelist gate in
  `handle_post()` is untouched; `_persist_without_js()` exercises a real save
  end to end in both languages.
- **T-25-06-B** (duplicate radios for one setting) — **resolved to one set and
  asserted on the whole rendered page**, not just the card: exactly
  `len(THEME_IDS)` inputs named `theme`.
- **T-25-06-C** (the `/theme-preview/{id}.png` route) — accepted, unchanged, not
  widened.
- **T-25-06-D** (registry label text in chip markup) — every interpolation still
  goes through `escape_html()`; the renderer is unchanged.
- **T-25-06-SC** — zero packages installed in any ecosystem.

No new security-relevant surface was introduced: no route, no auth path, no file
access, no schema change. **No threat flags.**

## Verification

```
PYTHON=…/server/.venv/bin/python bash scripts/run-all-tests.sh
```

**Exactly the 5 documented baseline failures, by name, and no others:**

1. `add_entry() returns ADD_FAILED … read-only … (WR-11)` — `server/test_manual_resolutions.py`
2. `delete_entry() returns False … read-only … (WR-11)` — `server/test_manual_resolutions.py`
3. `POST /airlines/resolve … manual_save_failed … (WR-11)` — `companion/test_companion_app.py`
4. `POST /airlines/manual-resolutions/{prefix}/delete … manual_delete_failed … (WR-11)` — `companion/test_companion_app.py`
5. `anomaly_active() … must never raise …` — `companion/test_status_pages.py`

`companion/test_browser_ux.py` 78/78 with **zero SKIPs**. `ruff check .` clean.

## Scope boundaries stated rather than left to be found

- **The arrivals, calendar and rule-add grids are not converted**, and the reason
  is in `_theme_chip_grid_html()`'s own docstring: they are already compact,
  already sit beside other controls, and none of them is the page-height problem
  X6 named. Four carousels would have multiplied the `:has()` risk by four for no
  gain on the three cards that were never the defect.
- **No requirement was ticked.** CFG-46…CFG-52 belong to 25-08;
  `STATE.md`, `ROADMAP.md` and `REQUIREMENTS.md` are untouched by this plan.
- **No overlay drawer, in any form** — three recorded rejections plus a locked
  Phase 22 decision, one from real-device testing.

## Commits

| Commit | Task |
|---|---|
| `6ad403d` | the height this plan is judged against, taken before the carousel |
| `85ac031` | the carousel, which is the same radio group in a different place |
| `4410e35` | eighteen themes reachable with scripts blocked, and no new script |
| `095ba49` | the carousel measured at 360px, by keyboard, and with scripts off |

## Self-Check: PASSED

Every file this summary names exists on disk, and all four commit hashes resolve
in `git log --oneline --all`.
