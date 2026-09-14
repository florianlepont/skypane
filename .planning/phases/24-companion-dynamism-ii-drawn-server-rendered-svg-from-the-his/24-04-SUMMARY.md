---
phase: 24-companion-dynamism-ii-drawn-server-rendered-svg-from-the-his
plan: 04
subsystem: companion-ui
tags: [svg, drawing, ring-gauge, battery, themes, no-js, css]

requires:
  - phase: 24-01
    provides: "companion/draw.py — unit_canvas(), circle(), unit_circle_dash_array(), the DRAWING_* class constants and the executable drawing contract (Section 2.8) that collects them"
  - phase: 24-01
    provides: "companion/battery.py as the ONE battery estimator, and the exclusivity scan that keeps it the only one"
  - phase: 24-01
    provides: "the .drawing* CSS vocabulary and DRAWING_FIGURE_CLASS, the viewBox scheme's size route"
  - phase: 24-02
    provides: "companion/test_browser_ux.py's _set_ui_theme(), _computed_paint() and _assert_no_page_overflow() — the harness's dark-mode, resolved-paint and page-overflow capabilities"
  - phase: 19-01
    provides: "battery.battery_percent() as the shared estimate, and the precedent that a drifting copy gets replaced by one shared home"
provides:
  - "draw.ring_gauge(fraction, size, status_class) — the ONE ring emitter, size-parameterised, called at 72px on Health and 36px on Home"
  - "draw.status_class(state) — the one mapping from the app's ok/warn/error verdict to a drawing status modifier"
  - "draw.DRAWING_RING_TRACK_CLASS / DRAWING_RING_VALUE_CLASS, and draw.DRAWING_STATUS_CLASSES"
  - ".drawing-ring-track / .drawing-ring-value, and the .battery-trend-section svg.drawing__figure:not(.icon) size rescue"
  - "health_page._battery_ring_html() / _battery_readout_row_html(), and home_page._battery_tile_content_html()"
affects: [24-05, 24-08]

tech-stack:
  added: []
  patterns:
    - "Size as a RATIO OF THE BOX SIDE, not a pixel constant, so every size is one drawing scaled and a 'small variant' cannot exist"
    - "stroke-width as a presentation ATTRIBUTE and never a CSS declaration, because CSS of any specificity beats a presentation attribute and would flatten every size to one thickness"
    - "A ring gauge draws the PRINTED INTEGER over 100, not a finer-grained fraction of the same input, so the picture and the number are one value in two renderings"
    - "getBBox() excludes the stroke; expand it by half the RESOLVED stroke-width in the open, rather than inside a getBBox() option dictionary whose support would have to be assumed"
    - "Compare a new tile against an untouched NEIGHBOUR, not against 'all siblings equal', when grid stretch would make equality vacuous at one width and false at another"

key-files:
  created: []
  modified:
    - companion/draw.py
    - companion/pages/health_page.py
    - companion/pages/home_page.py
    - companion/static/style.css
    - companion/test_companion_app.py
    - companion/test_status_pages.py
    - companion/test_view_pages.py
    - companion/test_browser_ux.py

key-decisions:
  - "The ring draws `printed_percent / 100`, not `battery_fraction(mv)`. One call into the estimator, two renderings of its result — proven by mutation: sourcing the ring from battery_fraction() instead makes the arc and the text disagree by 0.0033 and fails the check."
  - "The emitter takes a FRACTION, never a millivolt value, because draw.py's own docstring forbids importing battery.py — geometry must not know what it is plotting."
  - "stroke-linecap is butt, not round: a round cap adds half a stroke width at each end, so a 5% reading would draw ~12% of the circle."
  - "Fraction 0 emits NO value arc (a zero-length dash renders as a dot under a round cap); fraction 1 emits a complete circle with NO dash pattern (an arc path whose sweep is the whole circle draws nothing)."
  - "Each page owns its own size constant. A shared sizes table in draw.py would be one rename away from reading as two named variants of one drawing."
  - "Three of this plan's own CSS declarations (flex: none, two × min-width: 0) were measured inert and removed; the comments now record the measurement rather than the reasoning."

requirements-completed: []

duration: ~150min
completed: 2026-09-14
---

# Phase 24 Plan 04: D21's Battery Ring — One Emitter, Two Sizes Summary

**The one number this app shows on two pages is now also a picture on both, drawn by a single size-parameterised emitter whose size moves the radius and the stroke width together — proven by mutating the emitter and watching both pages follow — and drawing exactly the integer printed beside it, so the arc and the text cannot tell different stories.**

## Performance

- **Duration:** ~150 min
- **Tasks:** 4/4
- **Files modified:** 8
- **Lines:** +1324 / −8

| # | Commit | Message |
|---|---|---|
| 1 | `a7ab0fa` | `test(24-04): a failing check for the one ring emitter, before it exists` |
| 2 | `bdb5c23` | `feat(24-04): one ring emitter, whose size parameter moves the geometry` |
| 3 | `0ee6eea` | `test(24-04): a failing check that the ring and the readout agree` |
| 4 | `f4a63b6` | `feat(24-04): the large ring on Health, drawing the number beside it` |
| 5 | `accfaf7` | `test(24-04): a failing check that Home's ring is Health's ring, smaller` |
| 6 | `f0baec6` | `feat(24-04): the same ring, smaller, in Home's battery tile` |
| 7 | `7f79600` | `test(24-04): the ring measured in a browser, both themes, 360px, no JS` |

## The decision that mattered most

**The ring draws the printed integer over 100 — not `battery_fraction(mv)`.**

The plan offered two readings of "one call into `companion/battery.py`". The
obvious one is that the gauge takes the fraction (24-01 added
`battery_fraction()` for exactly this) and the text takes the percentage. Those
are two calls into the estimator. They agree today because one is literally the
other rounded — but "agree today" is precisely the phrase that preceded every
drift this project has had to undo.

The alternative is narrower and stronger: the page makes ONE call,
`battery.battery_percent(mv)`, and the ring's fraction is that integer over 100.
The arc and the number are then not two values that happen to match, they are
the same value rendered twice.

The cost is real and worth stating: the ring quantises to 1% steps. At 72px that
is 3.6° of arc, about 0.6px of ink — invisible. The benefit is that the class of
defect CFG-40 names becomes unreachable rather than merely unlikely.

This was not settled by argument. It was settled by mutation. Sourcing the ring
from `battery_fraction()` instead, on the seeded 3690 mV reading:

```
the ring draws 0.4333 of its circumference while the readout beside it
prints '≈ 43% · 3690 mV' — the picture and the number are telling
different stories (CFG-40)
```

The check's 0.0005 tolerance is tight enough to see the difference between "one
number twice" and "two calls that round apart". That is the whole requirement,
made measurable.

`battery_fraction()` is still reached — `battery_percent()` is its only caller
and its whole body. It is not called directly from a page, and now there is a
recorded reason.

## What was built

### `draw.ring_gauge(fraction, size, status_class=None)`

One emitter. No `variant` parameter, and the docstring says why one must never be
added: a variant name is how two drawings hide inside one function.

The geometry comes from **ratios of the box side**, which is the mechanism that
makes a CSS-only "small variant" impossible:

```
RING_STROKE_RATIO    = 0.12   # stroke, as a fraction of the side
RING_CLEARANCE_RATIO = 0.02   # clear space outside the stroke's outer edge
RING_MIN_SIZE        = 8      # below this a ring is not a ring; clamped, never refused
```

| size | centre | radius | stroke | outer ink edge | viewBox margin |
|------|--------|--------|--------|----------------|----------------|
| 72 (Health) | 36 | 30.24 | 8.64 | 70.56 | 1.44 |
| 36 (Home) | 18 | 15.12 | 4.32 | 35.28 | 0.72 |

Both ratios are identical by construction: 0.42 radius-over-side and 0.12
stroke-over-side at both sizes. That equality is what the cross-page check
measures.

Emitted markup, at 0.43 and size 72:

```html
<svg class="drawing__figure drawing--ok" viewBox="0 0 72 72" width="72" height="72" aria-hidden="true">
  <circle class="drawing-ring-track" cx="36.00" cy="36.00" r="30.24" fill="none" stroke-width="8.64"/>
  <circle class="drawing-ring-value" cx="36.00" cy="36.00" r="30.24" fill="none" stroke-width="8.64"
          transform="rotate(-90 36.00 36.00)" stroke-dasharray="81.7015 108.3020"/>
</svg>
```

Four properties worth naming:

**`stroke-width` is a presentation ATTRIBUTE, never a stylesheet declaration.**
CSS of any specificity beats a presentation attribute, so a `stroke-width` in
`.drawing-ring-*` would flatten both sizes to one thickness — making the small
ring's stroke proportionally twice as thick — and hand the size parameter back
to CSS. Neither rule declares one, and both say so out loud.

**Both degenerate fractions are handled where both arc mechanisms fail.** At 0 no
value arc is emitted at all (a zero-length dash renders as a *dot* under a round
cap, so empty would read as a few percent). At 1 a complete circle is emitted
with no dash pattern (an arc `<path>` whose sweep is the whole circle is
degenerate in SVG and draws *nothing*, so full would read as empty — the worst
possible value to be wrong at).

**`stroke-linecap: butt`, declared explicitly even though it is the initial
value,** because the comment is the point: a round cap adds half a stroke width
of ink at *each* end, so at 36px a 5% reading would draw roughly 12% of the
circle and the picture would disagree with the number — CFG-40's own failure,
arriving through a line cap.

**Total.** `None`, `True`, `False`, a NaN, a string, a dict, `-0.5` and `1.5` all
produce a defined drawing. Negatives pin at empty; anything above 1 pins at
exactly a full ring and never wraps to a second lap. An unusable `size` clamps to
`RING_MIN_SIZE` (T-24-04-A).

### `draw.status_class(state)`

One mapping from the app's `ok`/`warn`/`error` vocabulary to a drawing modifier,
so the two pages cannot grow two dicts. An unrecognised verdict returns `None`
rather than a guessed class, so nothing arbitrary reaches a class attribute —
`layout.stat_tile()`'s fixed-dict discipline, restated.

### Health: `_battery_ring_html()` + `_battery_readout_row_html()`

The ring sits beside the existing readout, inside the existing card. No new card,
no glyph in the `<h2>`. The colour is `battery_status()`'s verdict — the one this
section already computed for its own card edge, never a second judgement.

With no drawable reading, `_battery_readout_row_html()` returns
`_battery_readout_block()`'s markup **unwrapped**, so the no-reading page is not
a slightly different page — it is byte-identically the same page.

### Home: `_battery_tile_content_html()`

The same emitter at 36px, beside the tile's two text lines rather than above
them. That is a height decision, not a taste one: `.dashboard-grid` stretches
every tile in a row to its tallest sibling, so a taller Battery tile does not
merely grow itself — it pushes the whole row down.

The tile still prints its verdict, its `≈ NN%` and its mV detail. The ring is an
addition. Removing the percentage would break the emitter's `aria-hidden`
justification *and* remove the only exact value on the tile — both pinned.

### CSS

`.drawing-ring-track` (structural `--color-border`, deliberately not
`currentColor`, so the track stays structural when the status modifier turns the
value arc amber or rose) and `.drawing-ring-value` (`currentColor`, `butt` caps),
plus:

```css
.battery-trend-section svg.drawing__figure:not(.icon) { width: auto; height: auto; }
```

**This rule is the plan's one genuine surprise** and is covered in its own
section below.

## The collision the plan did not predict, and how it was settled

`.battery-trend-section svg:not(.icon) { width: 100%; height: 160px; }` — the
chart's own size route, landed in 06.6.1 — matches **every descendant `<svg>`** of
that section. The ring lives inside that section. Unhandled, it would have
rendered 312px wide and 160px tall.

Four options were considered and three rejected:

| Option | Rejected because |
|--------|------------------|
| Narrow the selector to `> svg` | Breaks a harness pin (`expected a fixed px height declaration on '.battery-trend-section svg:not(.icon)'`), and 24-05 owns that rule |
| Narrow it to `svg.sparkline__canvas` | Same pin, plus it breaks the moment 24-05 renames the chart's class |
| Give the ring `.icon` | Semantically false, and `.icon` carries its own sizing |
| **Override with `width: auto; height: auto`** | **Taken** |

The reasoning against `auto` looked strong: if the width/height *attributes* are
presentational hints mapped to the CSS properties, then `width: auto` overrides
them, the SVG has no intrinsic size left, and CSS replaced-element sizing lands
on the 300×150 default that `layout.icon_html()`'s docstring already records as a
trap — or on 150×150 once the 1:1 ratio is applied.

**That reasoning is wrong, and it was measured rather than trusted.** A
standalone Chromium probe with exactly this rule pair returned 72×72 and 36×36:
the width/height attributes establish the SVG's *intrinsic* dimensions
independently of the CSS used value, so `auto` resolves back to them. The rule
went in only after that number came back.

The `:not(.icon)` in the override filters nothing — a ring is never an icon. It
is there to carry one more class than the rule it must outrank, so the override
wins on **specificity** rather than on source order. Two equally-specific rules
would leave the ring's size depending on which block a later edit happens to move
first.

## Every mutation, with its quoted failure

Thirteen mutations. Each was reverted immediately, and every revert was done with
`git checkout-index` against a **staged** tree — see Findings for why that
sentence is here.

### Task 1 — the emitter

**M1 — the fraction-0 guard removed** (`if fraction > 0` → `>= 0`)

> a fraction of 0 emitted a value arc: `<circle class="drawing-ring-value" cx="36.00" cy="36.00" r="30.24" fill="none" stroke-width="8.64" transform="rotate(-90 36.00 36.00)" stroke-dasharray="0.0000 190.0035"/>` — a zero-length dash renders as a dot under a round cap, so empty would read as a few percent

**M2 — the stroke width pinned to one size** (the CSS-only "small variant")

> two sizes emitted the same `'stroke-width'` (`'8.64'`) — the size parameter is not driving the geometry, which is the CSS-only 'small variant' CFG-40 forbids

**M3 — fraction 1.0 emits a dash pattern** (`if fraction < 1` → `<= 1`)

> a fraction of 1 emitted a dash pattern (`'190.0035 0.0000'`) — a complete circle is emitted complete, so no rounding of the circumference can leave a seam at 100%

**M4 — `.drawing-ring-value` renamed away in style.css** (24-01's class-resolution guard)

> companion/draw.py can emit class `'drawing-ring-value'` and companion/static/style.css carries no selector for it — a class that exists in Python and nowhere in CSS paints NOTHING at all, and nothing else in this codebase would notice

**M5 — the explicit fill route dropped** (`"fill"` → `"data-fill"`)

> a ring arc at fraction 0.5 carries no explicit `fill="none"`: `<circle class="drawing-ring-track" cx="36.00" cy="36.00" r="30.24" data-fill="none" stroke-width="8.64"/>` — a stroked shape with no fill route takes the SVG default black, correct in one theme and invisible in the other

**M6 — the arc mirrored** (`rotate(-90 …)` → `rotate(-90 …) scale(-1 1)`)

> the value arc's transform is `'rotate(-90 36.00 36.00) scale(-1 1)'`, not `'rotate(-90 36.00 36.00)'` — that one attribute is what puts the arc's start at twelve o'clock and leaves it running clockwise, so anything else here is a silently mirrored or re-based gauge

### Task 2 — Health

**M7 — the fraction hardcoded, ignoring the reading**

> the ring draws 0.5000 of its circumference while the readout beside it prints `'≈ 43% · 3690 mV'` — the picture and the number are telling different stories (CFG-40)

**M8b — a ring rendered on the zero-rows empty-state branch**

> a device with no battery reading rendered `'drawing-ring-track'` — an empty ring reads as 0%, which is a false statement about a device that has simply not checked in

**M9 — the ring sourced from `battery_fraction()` instead of the printed percentage**

> the ring draws 0.4333 of its circumference while the readout beside it prints `'≈ 43% · 3690 mV'` — the picture and the number are telling different stories (CFG-40)

**M10 — a glyph reintroduced into the battery `<h2>`**

> a Health `<h2>` carries an `<svg>` — the battery heading's glyph was removed on the developer's own instruction and the ring must not reintroduce one

### Task 3 — Home, and the CFG-40 proof

**The one-emitter proof.** Two changes made *inside* `draw.ring_gauge()`, each
rendered on both pages:

| Mutation | Home (36px) | Health (72px) |
|----------|-------------|---------------|
| `DRAWING_RING_TRACK_CLASS` → `"drawing-ring-MUTATED"` | `<circle class="drawing-ring-MUTATED" cx="18.00" …/>` | `<circle class="drawing-ring-MUTATED" cx="36.00" …/>` |
| `rotate(-90 …)` → `rotate(90 …)` | `transform="rotate(90 18.00 18.00)"` | `transform="rotate(90 36.00 36.00)"` |

Both pages changed on both mutations. Both reverted. That is CFG-40's actual
requirement — and it is what a `grep` for `draw.` in two files would not have
shown, because both files could import the emitter and still draw two different
pictures.

**M11 — a drifted second component** (the small ring keeps a fixed 2px stroke)

> the two rings disagree about stroke width as a proportion of their own box: Home 0.0556, Health 0.1200. They are not one drawing at two sizes — they are two components, which is exactly the drift CFG-40 forbids

**M12 — Home's ring drawn at Health's size**

> Home's ring is not SMALLER than Health's — 72.0 against 72.0; two sizes is half of what CFG-40 asks for

**M13 — the printed percentage removed, leaving only the picture**

> expected the Battery tile to still print `'≈ 43%'` — the ring is an ADDITION to the verdict, the percentage and the millivolt detail, never a replacement for them

**M14 — an empty ring for a device with no reading**

> a device with no battery reading rendered `'drawing-ring-track'` on Home — an empty ring reads as 0%, which is a false statement about a device that has simply not checked in

### Task 4 — the browser

**MB1 — the value arc's `stroke: currentColor` removed from style.css**

> Home in light: the ring's value arc resolves stroke to the SVG default `'none'` — it inherited no colour from the cascade and is painting nothing a theme chose

and, from the second check:

> Home with scripts blocked, in dark: the ring resolves `('stroke',)` to the SVG default — 'correct in dark mode with scripts off' is the combination most likely to be wrong, which is why it is the one measured

**MB2 — the track painted with `currentColor` too**

> Home in light: the value arc and the track resolve to the same paint (`'rgb(22, 163, 74)'`), so the gauge reads as a plain circle with no reading in it

**MB3 — the stroke width doubled, the viewBox left alone** (the criterion's own named mutation)

> Home: drawing-ring-track inks [-1.440, -1.440, 37.440, 37.440], outside its own viewBox 0 0 36 36 — the stroke is clipped at the box edge, which is the ring's own half-stroke overhang going unaccounted for

**MB4 — Home's ring stacked above the text** (`flex-direction: column`)

> Home's Battery tile's own content is 119.59px tall against its Frame neighbour's 75.59px at 360px — the ring pushed the tile down, and `.dashboard-grid`'s stretch would push the whole row with it

**MB5b — Health's ring enlarged to 420px** (proving the overflow assertion fires)

> Health scrolls sideways at 360px: documentElement.scrollWidth 516 against a client width of 360, painted past the right edge by `['[object SVGAnimatedString]', 'battery-readout', …]` (CFG-45's page-body floor)

The pre-existing `_every_disclosure_on_every_page_opens_without_overflow` check
fired on the same mutation with the same numbers — the new assertion agrees with
it rather than contradicting it.

**MB6 — the emitter returns `""`** (proving the scripts-blocked assertion is not vacuous)

> Home: expected exactly one ring value arc at 360px, got 0

and

> Home: no svg.drawing__figure on the page — with none, this check measures nothing

## Checks that failed the vacuity question, and what was done

### 1. The fill assertion was defeated by its own substring (found by M5)

The first version tested `'fill="none"' not in element`. Renaming the attribute
to `data-fill` left it **green** — because `data-fill="none"` *contains*
`fill="none"`. This is the `.drawing-axis`-inside-`.drawing-axis-label` trap the
standing constraints name, met from the other direction and inside an attribute
name rather than a class. Replaced with a boundary regex
`(?<![-\w])fill="none"`, which then failed correctly.

### 2. The arc's direction was documented and unmeasured (found by M6)

The docstring states "twelve o'clock, clockwise". Mirroring the arc with an extra
`scale(-1 1)` left every assertion green. The one property a later caller is most
likely to get silently wrong was the one property nothing measured. A transform
pin was added; M6 now fails.

### 3. "All three tiles are equal height" would have been false *and* vacuous

The plan's acceptance criterion asks for equal tile heights at 360px. Measured
**before** writing the check, on the unmodified tree:

| width | Frame | Battery | Data | layout |
|-------|-------|---------|------|--------|
| 360 | 111.59 | 111.59 | 131.19 | one column, three grid rows |
| 390 | 111.59 | 111.59 | 131.19 | one column, three grid rows |
| 768 | 111.59 | 111.59 | 111.59 | two rows |
| 1280 | 131.19 | 131.19 | 131.19 | one row, `align-items: stretch` |

At 360px the three are **not** equal — `.dashboard-grid` collapses to one column,
each tile is its own grid row at its own intrinsic height, and the Data tile is
legitimately taller because its detail wraps to a second line. At 1280px they
share a row and `stretch` makes them equal **no matter what** — an "all equal"
assertion there measures nothing.

Neither width can carry the property the plan actually owes. The check compares
the Battery tile against the **untouched Frame neighbour**, which carries the same
two text lines in the same box, on both its box height and its own content
height. MB4 proves it fires.

### 4. `min-width: 0` and `flex: none` were inert (found by MB5)

The first mutation of the 360px overflow guard — removing `min-width: 0` from
both flex text columns — did **not** fail. Investigated rather than adjusted.

Measured at 360px with a 60-character unbreakable run forced into the readout:

| | with the declaration | without it |
|---|---|---|
| Home `documentElement.scrollWidth` | 601 | 601 |
| Health `documentElement.scrollWidth` | 707 | 707 |
| ring width with / without `flex: none` | 72 | 72 |

All three declarations change nothing. `min-width: 0` buys nothing because
nothing in the ancestor chain clips, so the run overflows either way;
`flex: none` buys nothing because a replaced element's own automatic minimum size
already floors it at its intrinsic width.

They were written with confident load-bearing comments. **All three were
removed**, and the comments now record the measurement rather than the reasoning
— dead declarations with confident prose are worse than none, because they are
what the next reader trusts *instead of* measuring. `align-items: center` is the
one declaration doing real work on the figure (a flex row's default `stretch`
would letterbox the aspect-locked `<svg>`), and the comments now say so.

## A real regression caught in the same pass

Moving the readout inside `.battery-readout-row` silently deleted the 8px gap
between the readout and the chart: `.battery-readout`'s own
`margin: 0 0 var(--space-sm)` was zeroed for flex alignment, and the new wrapper
carried no margin of its own. `margin-bottom: var(--space-sm)` now lives on the
row. Measured after: the readout-to-chart gap is 20px at 360px (8px row margin
plus 12px of vertical centring, since the 72px ring is taller than the 48px
readout), and the no-ring path is byte-identically unchanged at 8px.

## Byte-identity, verified against the pre-task modules

Both page modules were loaded twice in one process — the working-tree version and
`git show HEAD:…` — on a **frozen clock** (`history_db.utc_now_iso` patched),
because the first attempt diffed `in 51s` against `22m ago` and looked like a
code change when it was wall-clock drift.

### Health

| case | result |
|------|--------|
| `battery_sparkline_svg()`, raw series | IDENTICAL (3355 chars) |
| `battery_sparkline_svg()`, daily series | IDENTICAL (2643 chars) |
| `_battery_section([])` | IDENTICAL (238 chars) |
| `_battery_section()`, one row | IDENTICAL (439 chars) |
| `_battery_section()`, non-numeric rows only | IDENTICAL (617 chars) |
| `_battery_section()`, six rows | +420 chars at offset 3 — the ring and its wrapper, nothing else |

**The chart's diff is empty.** This plan did not touch it; 24-05 owns it.

### Home

| case | result |
|------|--------|
| no state dir at all | IDENTICAL (1210 chars) |
| `history.db` present, zero readings | IDENTICAL (1210 chars) |
| `battery_mv = 0` (refused by the estimator) | IDENTICAL (1210 chars) |
| a real 3690 mV reading | +457 chars — the ring and its wrapper |

## Browser measurements

All at `VIEWPORT_MIN_SUPPORTED` (360×844), through 24-02's helpers.

### Resolved paint of the ring's value arc — four values, none the SVG default

| page | light | dark |
|------|-------|------|
| Home | `rgb(22, 163, 74)` | `rgb(74, 222, 128)` |
| Health | `rgb(22, 163, 74)` | `rgb(74, 222, 128)` |

Track, for contrast: `rgb(223, 215, 200)` light, `rgb(42, 48, 64)` dark. Body
canvas resolved `rgb(247, 244, 239)` / `rgb(12, 15, 20)`, which is
`_set_ui_theme()` confirming the page genuinely repainted.

### Body overflow at 360px

| page | `documentElement.scrollWidth` | `clientWidth` | verdict |
|------|------------------------------|---------------|---------|
| Home | 360 | 360 | PASS |
| Health | 360 | 360 | PASS |

### viewBox containment — measured, not derived

| page | viewBox | arc bbox (geometry) | resolved stroke | inked box |
|------|---------|---------------------|-----------------|-----------|
| Home | 0 0 36 36 | [2.88, 2.88, 30.24, 30.24] | 4.32 | [0.72, 0.72, 35.28, 35.28] |
| Health | 0 0 72 72 | [5.76, 5.76, 60.48, 60.48] | 8.64 | [1.44, 1.44, 70.56, 70.56] |

`getBBox()` excludes the stroke, so half the **resolved** stroke width is added
on every side in the open — that half-stroke is the property under test, and
hiding it inside a `getBBox({stroke: true})` option dictionary would also mean
assuming that dictionary is supported.

### Scripts blocked, through `_no_js_page()`

One ring value arc on each page, and in dark mode it still resolves
`rgb(74, 222, 128)` — no SVG default on any property.

### Home's tiles at 360px, after the ring

| tile | box height | content height | rings |
|------|-----------|----------------|-------|
| Frame | 111.59 | 75.59 | 0 |
| **Battery** | **111.59** | **75.59** | **1** |
| Data | 131.19 | 95.19 | 0 |

Identical to the pre-ring measurement in every cell. The ring added **zero**
height.

## Acceptance criteria — every one run literally

### Task 1

| Criterion | Result |
|---|---|
| 0.0 emits no value-arc geometry at all (absence asserted) | PASS — M1 proves it fires |
| 1.0 emits a complete one | PASS — a dash-free complete circle; M3 proves it fires |
| 0.5 emits half the circumference, computed from emitted attributes | PASS — 95.0018 against an emitted-radius circumference of 190.0035, tolerance 0.01 |
| Two sizes → different radius AND different stroke width | PASS — M2 proves it fires |
| Every arc carries `fill="none"` and a class; zero colour literals | PASS — M5 proves it fires (after the substring fix) |
| None, True, -0.5, 1.5 each defined, nothing raised | PASS |
| Explicit size route; the class resolves via 24-01's guard | PASS — viewBox + width + height; M4 proves the guard fires |
| 24-01's drawing-contract checks still pass | PASS — all eight |
| `ruff check .` clean | PASS |

### Task 2

| Criterion | Result |
|---|---|
| Exactly one ring; encoded fraction == printed percentage, asserted against both at once | PASS — M7/M9 prove it fires |
| No reading → zero rings, section otherwise byte-identical | PASS — three no-reading cases byte-identical; M8b proves it fires |
| `battery_sparkline_svg()` byte-identical — diff recorded as empty | PASS — 3355 and 2643 chars, IDENTICAL |
| The `<h2>` contains no `<svg>` | PASS — M10 proves it fires |
| `test_i18n.py` passes; every new string has a French sibling | PASS — 24/24; **no new strings exist** (see Findings) |
| `EXPECTED_CHECK_COUNT` re-derived by running | PASS — 287 → 288 |
| `ruff check .` clean | PASS |

### Task 3

| Criterion | Result |
|---|---|
| Home's tile: exactly one ring, plus verdict, `≈` percentage and mV detail | PASS — M13 proves it fires |
| The mutation proof recorded: one change inside the emitter, both pages changed, both reverted | PASS — two mutations, table above |
| No reading → byte-identical to the pre-task render | PASS — three cases, 1210 chars each |
| The frame verdict rendered exactly once | PASS |
| `EXPECTED_CHECK_COUNT` re-derived by running | PASS — 153 → 154 |
| `ruff check .` clean | PASS |

### Task 4

| Criterion | Result |
|---|---|
| Resolved paint of the value arc on both pages in both themes — four values, none the SVG default | PASS — table above |
| Body overflow at 360px: PASS on both pages, two numbers recorded | PASS — 360/360 and 360/360 |
| The viewBox containment check fails when the stroke is doubled without widening the box | PASS — MB3 recorded |
| The scripts-blocked render contains the ring, via `_no_js_page()` | PASS — MB6 proves it fires |
| Home's three tile heights are equal at 360px, measured | **DID NOT EVALUATE AS PREDICTED** — see below |
| `EXPECTED_CHECK_COUNT` re-derived by running | PASS — 54 → 57 |
| `ruff check .` clean | PASS |

## Did not evaluate as predicted

**"Home's three tile heights are equal at 360px."** They are not, and they were
not before this plan either: 111.59 / 111.59 / 131.19. `.dashboard-grid` is
`repeat(auto-fit, minmax(240px, 1fr))`, which collapses to a single column at
360px, so each tile is its own grid row at its own intrinsic height and the Data
tile's wrapping detail makes it legitimately taller. The criterion is recorded
as written and **not** quietly adjusted; what shipped instead is the Battery-vs-
Frame comparison described above, which is the property the criterion was
reaching for and which is neither false at 360px nor vacuous at 1280px.

**"Any new user-visible string has its French sibling."** There are no new
strings. The ring is `aria-hidden` and decorative, carries no `<title>`, no label
and no text node, and every word beside it already existed. `companion/i18n_fr/
health.py` and `companion/i18n_fr/home.py` are listed in the plan's
`files_modified` and were **not** modified — correctly, and the right outcome
rather than an omission.

## Plan assumptions that turned out wrong

1. **`.battery-trend-section svg:not(.icon)` would not reach the ring.** The
   plan's `<interfaces>` section names `layout.icon_html()`'s 300×150 trap but
   not this rule, which stretches *every* descendant `<svg>` of the battery
   section. It required a dedicated override (section above).

2. **`width: auto` on an SVG with overridden width/height attributes falls back
   to the SVG default size.** It does not — the attributes establish intrinsic
   dimensions independently of the CSS used value. Measured at 72×72 and 36×36
   in Chromium before the rule was written.

3. **Task 1's `<files>` list has no test file**, yet the task is `tdd="true"`
   and its acceptance criteria are all emitter-level assertions. They went into
   `companion/test_companion_app.py` Section 2.8 — this phase's single home for
   the drawing contract — rather than into a page harness, because a second home
   for "what `draw.py` must emit" is the exact two-copies-that-drift failure
   CFG-40 itself names. Recorded as a deviation from the declared file set.

4. **`companion/battery.py` was not modified**, and did not need to be. The
   "one call" requirement was satisfiable through the existing
   `battery_percent()` without exposing a new rounding entry point.

## Findings

### The mutation round destroyed uncommitted work, once

The first mutation pass reverted with `git checkout -- companion/draw.py` while
the implementation was still **unstaged**. `git checkout --` restores from HEAD,
which at that moment did not contain `ring_gauge()` at all — so the revert
deleted the implementation, and all four "failures" in that round were the same
`AttributeError: module 'companion.draw' has no attribute
'DRAWING_RING_TRACK_CLASS'` rather than the intended mutation failures. The
results were void and were discarded.

The standing constraint says "stage before you mutate", and it says it for
exactly this. Every subsequent revert used `git checkout-index -f --` against a
staged tree, which restores the *index* rather than HEAD and cannot outrun
uncommitted work. Both the implementation scripts were kept in the scratchpad,
so re-applying cost one command rather than a rewrite.

### Two pre-existing checks broke by construction, and both were sharpened

**`expected exactly one non-icon <svg, got 2`.** The arithmetic
`rendered.count("<svg") - rendered.count("<use")` stopped proving "one sparkline"
the moment Health gained a second deliberate non-icon drawing. Retargeted onto
`'<svg class="sparkline__canvas"'`, which is what "exactly one sparkline" always
meant and is strictly sharper — the old count would have been satisfied by the
*ring alone* if the chart vanished. No count contribution.

**`expected '.battery-readout {''s rule body to contain 'font-weight: …'`.** The
cross-file CSS guard's `_rule_body()` used a bare `css_source.index(selector)`,
which resolved `.battery-readout {` to the **tail** of the new
`.battery-readout-row > .battery-readout {` rule and read the wrong body
entirely. The same substring trap, met from the other direction and inside a CSS
selector. Anchored at `"\n" + selector` — every selector these guards key on
opens its own rule at column 0. Fixed in **both** copies of `_rule_body()` in the
file, since the trap was identical in each. No count contribution.

### A guard that looked like dead code is not

`_battery_ring_html()`'s `if not latest_reading: return ""` is unreachable from
`_battery_section()` today, because the ring is built inside the
`if sparkline_html:` block. Removing it to check was instructive: the helper then
raises `cannot unpack non-iterable NoneType object`. It is the helper's own
contract, not a redundant branch, and T-24-04-C's "a page must never raise" runs
through it.

## Re-derived check counts, obtained by running

| harness | before | after | delta |
|---------|--------|-------|-------|
| `companion-app` | 299 | **300** | +1 (Task 1) |
| `status-pages` | 287 | **288** | +1 (Task 2) |
| `view-pages` | 153 | **154** | +1 (Task 3) |
| `browser-ux` | 54 | **57** | +3 (Task 4) |
| `config-page` | 240 | 240 | — |
| `config-history` | 87 | 87 | — |
| `i18n` | 24 | 24 | — |
| `contrast` | 43 | 43 | — |
| `poll-loop` | 99 | 99 | — |
| deferred-script pin | 14 | 14 | — (this plan adds no script) |

Every number above came from a run, never from arithmetic.

## Sandbox baseline — verified by failing check NAMES

`./scripts/run-all-tests.sh` exits 1 with exactly five failures, all five
pre-existing and all five root-sandbox artefacts that pass in CI:

1. `POST /airlines/resolve redirects with the manual_save_failed flash key … (WR-11)`
2. `POST /airlines/manual-resolutions/{prefix}/delete redirects with the manual_delete_failed flash key … (WR-11)`
3. `add_entry() returns ADD_FAILED (never raises) when its state dir cannot be created … (WR-11)`
4. `delete_entry() returns False (never raises) when the state dir goes read-only mid-write … (WR-11)`
5. `anomaly_active() runs on every page render and must never raise …`

Verified by name against the baseline captured before any edit, not by counting
failing files. No sixth failure.

## Requirements

CFG-40 is complete in code and measured, and is **deliberately left unticked** —
CFG-39…CFG-45 belong to phase 24's closing plan, and phase 23's precedent of
leaving CFG-34/CFG-37 unticked rather than rounding up is held here.

`.planning/STATE.md`, `ROADMAP.md` and `REQUIREMENTS.md` are untouched, matching
what 24-01, 24-02 and 24-03 each did in this phase.

## What this hands the later plans

- **24-05** gets the chart provably untouched — `battery_sparkline_svg()`'s
  output is byte-identical, recorded above — and a `.battery-trend-section` whose
  descendant-`<svg>` sizing collision is already solved for any aspect-locked
  figure added beside the chart.
- **24-08**'s hero reuses Home's small ring by calling `draw.ring_gauge()` at
  whatever size it wants. It must be a call, not a copy; the cross-page
  proportion check in `test_view_pages.py` is the thing that will notice if it
  becomes a copy.
- Every later drawing inherits `draw.status_class()` rather than writing a third
  `{"ok": …}` dict.

## Self-Check: PASSED

Files claimed, verified present on disk:

- `companion/draw.py` — FOUND (`ring_gauge`, `status_class`, `DRAWING_RING_TRACK_CLASS`, `DRAWING_RING_VALUE_CLASS`, `DRAWING_STATUS_CLASSES` all present)
- `companion/pages/health_page.py` — FOUND (`BATTERY_RING_SIZE`, `_battery_ring_html`, `_battery_readout_row_html`)
- `companion/pages/home_page.py` — FOUND (`BATTERY_RING_SIZE`, `_battery_tile_content_html`)
- `companion/static/style.css` — FOUND (`.drawing-ring-track`, `.drawing-ring-value`, `.battery-readout-row`, `.stat-tile__gauge`, the `.battery-trend-section svg.drawing__figure:not(.icon)` override)
- `companion/test_companion_app.py`, `companion/test_status_pages.py`, `companion/test_view_pages.py`, `companion/test_browser_ux.py` — FOUND

Commits claimed, verified in `git log`:

`a7ab0fa`, `bdb5c23`, `0ee6eea`, `f4a63b6`, `accfaf7`, `f0baec6`, `7f79600` — all seven FOUND.
