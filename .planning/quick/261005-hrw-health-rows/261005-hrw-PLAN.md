---
quick_id: 261005-hrw
type: quick
autonomous: true
branch: claude/health-rows
---

# 261005-hrw: Health ("État") as one card of rows

## Objective

Owner-approved redesign of the Health page, direction B ("list of rows"), answering the owner's
feedback on the tile layout:

1. Desktop misalignment (tiles stopped at 760 px while the cards ran to 880 px, a third tile
   orphaned by 8 px): one consistent width, the 760 px cap is gone.
2. The status tile needs a finer, more modern treatment.
3. "Régularité des relevés" and "Aujourd'hui" were not useful as cards: both are removed. The
   30-day wake regularity survives only inside the Frame connection row's details; the 24 h band
   is dropped (quiet hours are shown by the Device page's dial).
4. The server and off-server backup signals get a finished treatment and sit above the
   unidentified-airlines table.

## Design

- One hairline card, two group bands ("Screen", "Server & data": the `<h2>`s keep the
  `#screen` / `#server-data` anchors), one native `<details>` row per subsystem: Frame
  connection, Battery, Flight data, Data sources, Flight identification, Off-box backup (only
  when the marker is configured).
- A summary shows a state icon (a different shape for ok / warn / error / neutral, with a
  visually hidden state word, so colour is never the only signal), the name, a one-line verdict,
  a right-aligned value and the shared chevron. A row whose state is warn or error renders open.
  No script is involved; the identification row carries a small neutral ring and "N to resolve".
- Row bodies hold the evidence: facts and the wake-regularity grid (connection), the battery
  ring/readout/chart (battery, moved inside its row unchanged), timestamps (flight data), the
  three corroboration outcomes with their explanations (sources), the window sentence, a link to
  the unresolved table and the resolution breakdown table (identification), the last backup.
- Phone: name over verdict over value; on 700 px and up a single line with a 208 px name column.
  Everything sits on the 8 px grid (32 px icon, 16 px gutter, 64 px row).
- One elevation rule on the page: a hairline at rest, no hover reveal on the rows card or the
  registry card.
- "Compagnies non identifiées" stays below the card, unchanged.
- The anomaly toast and the source-outage toast keep their semantics. The freshness loop now
  swaps each row's `<summary>` (never a `<details>`), so a row the visitor opened stays open.
- The tile builders, the day band, the regularity card heading and the resolution-statistics card
  are removed; `compute_health_state()` drops the three tile fragments nothing read and gains the
  raw reads the rows render from (`inputs`) and `next_wake_clock`.

## Tasks

1. `companion/health_rows.py`: generic row / group / card / facts components.
2. `health_page`: per-row builders, `render()` rewritten; `health_sections`: regularity block
   without its card, day band and tile/stat-card builders removed.
3. `style.css`: rows card CSS, 760 px cap and tile rules removed, one elevation rule.
4. i18n (EN source, FR catalogue), freshness registry (Python and `freshness.js`).
5. Tests: status-page structure tests re-pointed at rows; browser drawing tests open the rows
   first; new browser test for one width and aligned columns; render baseline regenerated.
