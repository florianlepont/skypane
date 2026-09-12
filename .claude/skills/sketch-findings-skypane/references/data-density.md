# Data Density

## Design Decisions

**Winning variant, origin: Sketch 003, Variant B ("Inline compact").** The core column-merge MECHANISM (dot-separated inline `.cell-primary`/`.cell-inline-sep`/`.cell-secondary` cells) is still current — but the specific **7-column count below is SUPERSEDED by Phase 21 (D-15, CFG-22)**: History's table (the page is now named Flights in the nav) renders 7 columns (Timestamp, Callsign, Type, Route, State, Corroboration, Runway — `companion/pages/history_page.py`'s `_HEADERS`), down from an original 9, by merging Callsign+Hex and Type+Airline into single dot-separated inline cells SUPERSEDED. See "Flights table recompacted to five columns plus a detail row (Phase 21, D-15)" below for the current shape. Row height stays the same as the pre-merge table — the deciding factor over the sketch's rejected Variant A (stacked cells, which grew row height) — this reasoning is what Phase 21's own table inherited and then had to locally override for exactly two columns (see below).

- **Callsign + Hex merge:** one column, one line — callsign in bold mono (`.cell-primary`), a middle-dot separator (`.cell-inline-sep`, glyph `·`), hex in muted mono (`.cell-secondary`).
- **Type + Airline merge:** same pattern, one column, one line.
- Column order after merge: Timestamp, Callsign (merged), Type (merged), Route, State, Corroboration, Runway — unchanged left-to-right order, two fewer columns than the pre-06.6.1 table.
- The 06.6 relative-timestamp dependency this file used to flag as an open risk (whether History's Timestamp column would still be a full ISO string, taking more horizontal space than the sketch assumed) is resolved: `companion/layout.py`'s `concise_timestamp_html()` ships the concise clock-time-plus-relative-age format, so the 7-column table fits as designed.

**What the merged-cell parts actually declare — corrected.** The sketch's own CSS pattern named a `--color-text-muted` token SUPERSEDED for the secondary/separator parts. **No such token exists anywhere in this stylesheet, and its absence is deliberate** — `companion/static/style.css`'s own comment on `.cell-primary`/`.cell-secondary` states directly that inventing a new token, or hard-coding a grey, would be wrong in one of the two themes. The shipped rule instead applies `opacity: 0.7` to the existing `--color-text` token, which gives the same muted read in both light and dark mode with no per-theme value to keep in sync. Do not reach for that token name in future work on this file — it has never existed and was never adopted.

**Mobile: the horizontal-scroll fallback claim is retired.** This file previously said to keep `.data-table-wrap`'s horizontal-scroll behaviour as History's own mobile fallback. That is no longer true SUPERSEDED — 06.6.3 (D-07) replaced it with a **separate card-list rendering**, `.history-cards`, shown below 960px instead of a cropped/scrollable table. The desktop `.data-table-wrap` rendering and the mobile `.history-cards` rendering are both always present in the DOM; a `.history-cards ~ .data-table-wrap` sibling-combinator rule (not a bare `.data-table-wrap` selector) toggles which one is visible at which width — scoped specifically so Airlines' and Health's own independent reuse of `.data-table-wrap` (neither of which ever renders a `.history-cards` sibling) is never hidden by this rule.

**The secondary-data muting strength is shared on purpose.** History's merged Hex / Type·Airline parts render as `.cell-secondary` (opacity 0.7) in the desktop table and as `.history-card__secondary` (also opacity 0.7) in the mobile card — the *same* opacity value, deliberately, because the two are the same content at two different viewport widths. A second muting strength on either side would mean identical content reads at two different visual weights purely as a function of viewport width, which is exactly the defect this file's own accent-token comment already documents having been fixed twice elsewhere in the stylesheet.

### Flights table recompacted to five columns plus a detail row (Phase 21, D-15, CFG-22)

**Current contract.** The desktop table's header row is now `When / Flight / Route / State / Corroboration`, plus a sixth, visually-hidden "Details" header naming the toggle column — five *visible* data columns, down from the 06.6.1-era seven above. `_when_cell_html()`/`_flight_cell_html()` (replacing the retired `_clock_cell_html()`/`_callsign_hex_cell()`/`_type_airline_cell()`) still build on the same `.cell-primary`/`.cell-inline-sep`/`.cell-secondary` merged-cell mechanism this file's own winning-variant decision established — the mechanism survived the column-count supersession above, it just now feeds fewer, differently-grouped columns. What actually moved out of the summary row: the ICAO24 hex, the full ISO timestamp, the runway, and the copy-name button — all four now live in a sibling `<tr class="flight-detail-row">` (one per summary row, `colspan` across all six cells), revealed by a small "More"/"Plus" `.row-toggle` button at the end of each summary row.

**The When/Flight cells are a scoped exception to the merged-cell inline shape.** Every other merged cell in this codebase (including Flights' own Route/State cells) stays on the standard inline `primary · secondary` composition documented above. When/Flight do not: `table.data-table--flights .cell-primary, table.data-table--flights .cell-secondary { display: block; }` plus `.cell-inline-sep { display: none; }` makes these two columns' two lines genuinely stacked. This was not a stylistic choice — it was forced by measurement. `.data-table`'s pre-existing `min-width: max-content` rule (the "no-crop floor" the winning-variant decision above already relies on) sizes each column to its widest *unwrapped* line; with the inline shape, a Flight cell rendering `"AFR1380 · Air France · A320"` on one line wanted roughly 400px, and the real measured table width came to ~1081px (EN) / ~1173px (FR) inside an 880px content column at 1280px viewport width — overflowing even the full viewport in French. Stacking the two lines makes each column's max-content width the wider of its two lines instead of their concatenation; a headless Playwright probe (pinned Chromium, the real `/ui-lang` control) confirmed `.data-table-wrap`'s `scrollWidth === clientWidth === 880` and `document.documentElement.scrollWidth === window.innerWidth === 1280` in both languages after the fix. Do not read this as license to stack any OTHER merged cell in the app "for consistency" — it is a local fix to this one table's own measured width budget, not a new general rule.

**Corroboration is dot-only here, and only here.** `layout.status_dot()` gained a `visually_hide_label=False` keyword; every pre-existing call site (Health's own table) is byte-identical, and Flights' desktop Corroboration cell is the one caller passing `True` — the dot keeps its real accessible name and `title` tooltip, only the visible `.dot-label` span is hidden. This is what makes the five-column budget realistic: a visible ~90px-wide label on the column that carries the least essential at-a-glance information (its own dot colour already answers the question) would have blown the budget the stacking fix above exists to protect.

**Scoped padding, not a shared-rule change.** `table.data-table--flights td, th { padding: var(--space-sm) var(--space-sm); }` (8px both axes) is a second, narrower register value that exists only inside this one table's own selector — the shared `.data-table td/th` rule (16px, Health's and Airlines' own tables) is untouched.

**The detail row's own no-JS floor.** The `<tr class="flight-detail-row">` server-renders with no `hidden` attribute and no inline style — fully visible by default. A new script, `companion/static/flight-rows.js` (ES5, registered through the same six-touch-point static-script contract `theme-preview.js` already established), adds a `flight-detail-row--collapsed` class to every detail row at load and toggles it on click of the row's own `[data-row-toggle]` button (which also flips `aria-expanded` and swaps its own text between `data-more-text`/`data-less-text`). This is the same per-script class-at-load pattern `theme-preview.js`'s own usage-panel collapse uses (see `references/control-density.md`), not a page-wide `.js` class — chosen specifically so a page where only this one script is blocked by a stricter CSP still shows every detail row, rather than a page-wide gate silently hiding data no script actually collapsed.

### Airlines gallery illustration frame (quick task 260904-e92, UIR-08)

**Current contract.** Every companion-served Airlines illustration
(`GET /illustration/{key}.png`) normalizes server-side to exactly
**450x132** pixels — one single size, no srcset, no per-request size
parameter. That pair is set by `companion/illustration_normalize.py`'s
`ILLUSTRATION_TARGET_WIDTH`/`ILLUSTRATION_TARGET_HEIGHT`/
`ILLUSTRATION_TARGET_SIZE`, and it is duplicated by necessity (not
imported) into `companion/static/style.css` in two places that must
always move together: `.airline-card__image`'s `aspect-ratio: 450 / 132`
and `.lightbox--wide`'s `max-width: 450px`. Both are pinned to the
Python constants by harness cross-file checks in
`companion/test_status_pages.py` (an aspect-ratio derivation check and
`_lightbox_wide_max_width_matches_illustration_target_width()`), so the
CSS and the Python constants cannot silently drift apart.

The ratio (450/132 = 3.4091:1) is not an independently chosen aspect —
it tracks the *measured painted-content median* across all 43 vendored
illustrations (2.97:1 to 4.98:1, median 3.42:1), the same median the
original 900x263 frame was built from. The height is *derived* from
that median, never chosen: `round(450 * 263 / 900) = round(131.5) = 132`
— an exact integer reproduction of the 900:263 ratio is impossible below
900x263 itself, since `gcd(900, 263) = 1` (263 is prime).

**The old 900x263 frame is SUPERSEDED** by this quick task for UIR-08 —
the audit found the rendered `.airline-card__image` never exceeding
325px wide on mobile or 224px on desktop, making the 900x263 frame pure
oversampling. The frame was halved (option-a of the audit's two proposed
fixes; a srcset/multi-size mechanism, option-b, was rejected). Measured
byte win: per-file served bytes dropped from 132.5-175.5KB to
40.8-53.1KB, and the full 27-card gallery total dropped from 3.92MB to
1.20MB (31% of the pre-change weight). A harness byte-ceiling check
(64KB per file) now guards against a silent revert to the old frame
size.

One accepted, deliberate side effect: `.lightbox--wide`'s `max-width`
(450px) now sits BELOW `.lightbox`'s own 480px base max-width — an
inversion of that rule's original "wide variant is wider than the base"
intent. This was measured and accepted by the developer at decision
time: the desktop enlarged view shrinks from ~852px to ~402px (mobile is
unaffected, since `.lightbox`'s own narrower width formula already binds
there before either max-width does).

**Load-bearing warning for whoever reads this next: this target governs
the COMPANION WEB rendering only.** The physical e-ink panel resizes the
exact same source files independently, via
`server/plane/render.py`'s `_resize_illustration()`, at whatever
resolution its own canvas needs. `companion/illustration_normalize.py`
never writes back to disk and never touches that path. Do not lower this
companion-web target further "for consistency" with the panel, and do
not read the panel's own resize target as a hint that this one should
match it — they are deliberately separate call sites reading the same
source files for two different purposes.

### Table restyle this file predates (06.6.4, D-07)

- **Header:** moved from a filled `--color-secondary` block to a quiet uppercase 11px label with only a bottom hairline — no background at all.
- **Zebra striping:** retired. A single row surface plus a `tbody tr:hover` 4%-tint hover cue replaces the old `tr.row-alt` alternating background. The server-side `row-alt` class computation (`companion/layout.py`'s `data_table()`, `history_page.py`, `airlines_page.py`) is deliberately left in place as inert markup rather than removed — removing it would mean three Python edits and three harness updates for zero visible gain.
- **Last-row separator:** removed — `.data-table tbody tr:last-child td { border-bottom: none; }` gives the table a clean bottom edge instead of a trailing hairline.
- **Sticky-header scoping:** `.data-table-wrap th` is `position: sticky; top: 0;`, scoped to the table's own scroll container so it never collides with the `>=960px` sticky sidebar. Its background token is `--color-canvas` (chosen because History's table — the only one long enough for sticky to actually engage — renders directly on the page background, not inside a card). The stylesheet itself flags this specific token as never live-validated for the in-card cases (Airlines, Health): if those tables read as a visibly mismatched strip against their white card surface once scrolled, `--color-dominant` is the documented equally-valid alternative and a one-declaration change.

## CSS Patterns

```css
.cell-primary {
  font-family: var(--font-mono);
  font-weight: var(--weight-semibold);
}
.cell-secondary {
  font-family: var(--font-mono);
  font-size: 12px;
  opacity: 0.7;   /* NOT the sketch's SUPERSEDED --color-text-muted — that token has never existed */
}
.cell-inline-sep {
  opacity: 0.7;
  margin: 0 var(--space-xs);
}

/* History's mobile/desktop toggle — sibling combinator, not a bare selector */
.history-cards ~ .data-table-wrap { display: none; }
@media (min-width: 960px) {
  .history-cards { display: none; }
  .history-cards ~ .data-table-wrap { display: block; }
}

.history-card__secondary {
  opacity: 0.7;   /* same strength as .cell-secondary — one muted role, two viewport widths */
}
```

## HTML Structures

```html
<td>
  <span class="cell-primary">AFR123</span><span class="cell-inline-sep">·</span><span class="cell-secondary">39d301</span>
</td>
```

In the real codebase this is `companion/pages/history_page.py`'s `_merged_cell()` / `_callsign_hex_cell()` / `_type_airline_cell()` — the merged-cell rendering routes through `companion.layout.escape_html()` exactly like every other cell in the module; no second escaping path exists. `CELL_PRIMARY_CLASS`, `CELL_SECONDARY_CLASS`, `CELL_SEPARATOR_CLASS` and `CELL_SEPARATOR_TEXT` (the `·` glyph) are named module constants, not inline literals, so the class names and the stylesheet's counterpart selectors are cross-checked by a harness guard rather than left to drift.

Below 960px, `_history_cards_html()` renders the same merged data as `<li class="history-card">` elements inside a `<ul class="history-cards">` — see `references/settings-page-patterns.md`'s sibling reference file set and `companion/pages/history_page.py`'s own docstrings for the card's internal structure (`.history-card__primary`, `.history-card__secondary`, `.history-card__time`, `.history-card__details`).

## What to Avoid

- **Variant A ("Stacked cells")** — still rejected as a whole-table pattern. Two-line cells increase row height, working against the goal of scanning many rows quickly on a small screen. **Narrow exception (Phase 21, D-15):** the Flights table's own When/Flight columns ARE stacked, but only because measurement proved the inline shape overflows that table's real width budget — see "Flights table recompacted…" above. Do not generalize this exception to Route/State/Corroboration on the same table, or to any other table's merged cells, without the same measure-first discipline that justified it here.
- **Variant C ("Max density", 6 columns, merges State into Route too)** — still explicitly not part of locked scope. Do not implement it without a fresh discuss-phase decision extending the merge further. (Phase 21's own 5-visible-column table is a *different* reduction — it moved data OUT of the table into a detail row, it did not merge State into Route — so it does not retroactively authorize Variant C.)
- Reaching for the sketch's SUPERSEDED `--color-text-muted` token for any secondary/muted text in this file — it does not exist; use `opacity` on `--color-text` (matching `.cell-secondary`) or `color-mix(in srgb, var(--color-text) 70%, transparent)` (matching `.data-table th`/`.filter-bar__count`), whichever this file's existing precedent for that specific element already uses.
- Reintroducing a horizontal-scroll-only mobile fallback for Flights specifically — the `.history-cards` card list replaced it (D-16 confirms it is unchanged by Phase 21); other pages' `.data-table-wrap` reuse (Airlines, Health) is unaffected and still scrolls horizontally as before, since they never pair with a `.history-cards` sibling.
- Giving `.cell-secondary` and `.history-card__secondary` two different opacity values — they render the same content at two viewport widths and must stay at one shared muting strength.
- Keying the Flights detail row's collapse off a page-wide `.js` class instead of `flight-rows.js`'s own scoped class-at-load — that would hide detail data on a page where a stricter CSP blocks only that one script, per the reasoning above.

## Origin
Synthesized from sketch: 003 (history-table-density), winner: Variant B. Corrected against the shipped implementation (`companion/pages/history_page.py`, `companion/static/style.css`) per 06.6.3 (D-07, mobile card list, table restyle) and `companion/layout.py`'s `concise_timestamp_html()` (06.6.3, resolving this file's own former open timestamp-format risk) — quick task 260901-t00. Updated Phase 21 (21-03-PLAN.md, D-15, CFG-22): the desktop table recompacted from 7 to 5 visible columns plus a detail-row toggle column, the When/Flight cells' scoped stacked-line exception (measured, not assumed), the dot-only Corroboration column (`status_dot(visually_hide_label=True)`), the scoped 8px cell-padding register, and `flight-rows.js`'s own no-JS floor for the new detail row.
Source file available in: `sources/003-history-table-density.html` (historical artifact, byte-identical, not current-reality documentation).
