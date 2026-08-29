# Data Density

## Design Decisions

**Winning variant: Sketch 003, Variant B ("Inline compact")**

Reduces History's table from 9 columns (Timestamp, Callsign, Hex, Aircraft type, Airline, Route, State, Corroboration, Runway) to 7, so it fits a 13" laptop (~1280px content width) without horizontal scroll.

- **Callsign + Hex merge:** one column, one line: `AFR123 · 39d301` — callsign in bold mono (`.cell-primary`), a middle-dot separator, hex in muted grey mono (`.cell-secondary`, 12px).
- **Aircraft type + Airline merge:** same pattern, one column, one line: `A320 · Air France`.
- **Row height stays the same as today** — this was the deciding factor over Variant A (stacked cells, which put callsign/hex or type/airline on two lines inside one cell, growing row height). The developer picked B specifically to keep scanning many rows fast.
- Column order after merge: Timestamp, Callsign (merged), Type (merged), Route, State, Corroboration, Runway — same left-to-right order as today, just two fewer columns.
- Depends on 06.6 (not yet shipped as of this sketch) also landing its relative-timestamp format (`"3m ago"` instead of the current full ISO string like `2026-08-29T07:24:05+00:00`) — the sketch assumed that shortened Timestamp column already exists. If 06.6.1 ships before 06.6, the Timestamp column will still be the long ISO string and take more horizontal space than shown in the sketch; re-verify the 7-column table actually fits without 06.6's timestamp shortening before shipping, or note it as a known interim state.

## CSS Patterns

```css
.cell-primary{ font-family:var(--font-mono); font-weight:600; }
.cell-secondary{ font-family:var(--font-mono); color:var(--color-text-muted); font-size:12px; }
.cell-inline-sep{ color:var(--color-text-muted); margin:0 4px; }
```

## HTML Structures

```html
<td>
  <span class="cell-primary">AFR123</span><span class="cell-inline-sep">·</span><span class="cell-secondary">39d301</span>
</td>
```

In the real codebase, this is `companion/pages/history_page.py`'s `_history_table_html()` — it hand-builds table markup (rather than delegating to `layout.data_table()`) specifically because the Corroboration column's `layout.status_dot()` markup can't pass through `data_table()`'s escaping. The merged-cell rendering for Callsign/Hex and Type/Airline needs to go through `companion.layout.escape_html()` exactly like every other cell already does in that function — don't introduce a second escaping path.

## What to Avoid

- **Variant A ("Stacked cells")** — rejected. Two-line cells (callsign/hex or type/airline stacked vertically within one `<td>`) increase row height, which worked against the developer's stated goal of scanning many rows quickly on a small screen.
- **Variant C ("Max density", 6 columns, merges State into Route too)** — explicitly NOT part of the locked scope for this phase. 06.6.1-CONTEXT.md's decision only covers Callsign+Hex and Type+Airline. Variant C was shown only as a "how far could this go" reference; do not implement it without a fresh discuss-phase decision extending the merge further.
- Mobile: keep the existing horizontal-scroll fallback (`.data-table-wrap`) for the <960px case — 06.6.1-CONTEXT.md's decision was explicitly to keep scroll-on-mobile rather than switch to a stacked-card responsive pattern, since 7 columns (down from 9) is "already easier to manage" on a phone.

## Origin
Synthesized from sketch: 003 (history-table-density), winner: Variant B
Source file available in: `sources/003-history-table-density.html`
