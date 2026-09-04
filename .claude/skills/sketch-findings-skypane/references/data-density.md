# Data Density

## Design Decisions

**Winning variant, origin: Sketch 003, Variant B ("Inline compact").** The core column-merge decision still holds and is current: History's table renders 7 columns (Timestamp, Callsign, Type, Route, State, Corroboration, Runway — `companion/pages/history_page.py`'s `_HEADERS`), down from an original 9, by merging Callsign+Hex and Type+Airline into single dot-separated inline cells. Row height stays the same as the pre-merge table — the deciding factor over the sketch's rejected Variant A (stacked cells, which grew row height).

- **Callsign + Hex merge:** one column, one line — callsign in bold mono (`.cell-primary`), a middle-dot separator (`.cell-inline-sep`, glyph `·`), hex in muted mono (`.cell-secondary`).
- **Type + Airline merge:** same pattern, one column, one line.
- Column order after merge: Timestamp, Callsign (merged), Type (merged), Route, State, Corroboration, Runway — unchanged left-to-right order, two fewer columns than the pre-06.6.1 table.
- The 06.6 relative-timestamp dependency this file used to flag as an open risk (whether History's Timestamp column would still be a full ISO string, taking more horizontal space than the sketch assumed) is resolved: `companion/layout.py`'s `concise_timestamp_html()` ships the concise clock-time-plus-relative-age format, so the 7-column table fits as designed.

**What the merged-cell parts actually declare — corrected.** The sketch's own CSS pattern named a `--color-text-muted` token SUPERSEDED for the secondary/separator parts. **No such token exists anywhere in this stylesheet, and its absence is deliberate** — `companion/static/style.css`'s own comment on `.cell-primary`/`.cell-secondary` states directly that inventing a new token, or hard-coding a grey, would be wrong in one of the two themes. The shipped rule instead applies `opacity: 0.7` to the existing `--color-text` token, which gives the same muted read in both light and dark mode with no per-theme value to keep in sync. Do not reach for that token name in future work on this file — it has never existed and was never adopted.

**Mobile: the horizontal-scroll fallback claim is retired.** This file previously said to keep `.data-table-wrap`'s horizontal-scroll behaviour as History's own mobile fallback. That is no longer true SUPERSEDED — 06.6.3 (D-07) replaced it with a **separate card-list rendering**, `.history-cards`, shown below 960px instead of a cropped/scrollable table. The desktop `.data-table-wrap` rendering and the mobile `.history-cards` rendering are both always present in the DOM; a `.history-cards ~ .data-table-wrap` sibling-combinator rule (not a bare `.data-table-wrap` selector) toggles which one is visible at which width — scoped specifically so Airlines' and Health's own independent reuse of `.data-table-wrap` (neither of which ever renders a `.history-cards` sibling) is never hidden by this rule.

**The secondary-data muting strength is shared on purpose.** History's merged Hex / Type·Airline parts render as `.cell-secondary` (opacity 0.7) in the desktop table and as `.history-card__secondary` (also opacity 0.7) in the mobile card — the *same* opacity value, deliberately, because the two are the same content at two different viewport widths. A second muting strength on either side would mean identical content reads at two different visual weights purely as a function of viewport width, which is exactly the defect this file's own accent-token comment already documents having been fixed twice elsewhere in the stylesheet.

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

- **Variant A ("Stacked cells")** — still rejected. Two-line cells increase row height, working against the goal of scanning many rows quickly on a small screen.
- **Variant C ("Max density", 6 columns, merges State into Route too)** — still explicitly not part of locked scope. Do not implement it without a fresh discuss-phase decision extending the merge further.
- Reaching for the sketch's SUPERSEDED `--color-text-muted` token for any secondary/muted text in this file — it does not exist; use `opacity` on `--color-text` (matching `.cell-secondary`) or `color-mix(in srgb, var(--color-text) 70%, transparent)` (matching `.data-table th`/`.filter-bar__count`), whichever this file's existing precedent for that specific element already uses.
- Reintroducing a horizontal-scroll-only mobile fallback for History specifically — the `.history-cards` card list replaced it; other pages' `.data-table-wrap` reuse (Airlines, Health) is unaffected and still scrolls horizontally as before, since they never pair with a `.history-cards` sibling.
- Giving `.cell-secondary` and `.history-card__secondary` two different opacity values — they render the same content at two viewport widths and must stay at one shared muting strength.

## Origin
Synthesized from sketch: 003 (history-table-density), winner: Variant B. Corrected against the shipped implementation (`companion/pages/history_page.py`, `companion/static/style.css`) per 06.6.3 (D-07, mobile card list, table restyle) and `companion/layout.py`'s `concise_timestamp_html()` (06.6.3, resolving this file's own former open timestamp-format risk) — quick task 260901-t00.
Source file available in: `sources/003-history-table-density.html` (historical artifact, byte-identical, not current-reality documentation).
