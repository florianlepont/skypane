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

**A SECOND table has now been measured into this exception (Phase 22, B12) — and the warning above stands verbatim.** Health's unresolved-prefix registry table (`table.data-table--registry`) overflowed 1280px **in French** ("EXEMPLE D'INDIC" clipped, the Resolve column reachable only by horizontal scroll), and took the same stacked-cell treatment for the same reason, on the same evidence: the wrap's real budget is **830px**, and the table measured **886px (EN) / 1026px (FR)** before the fix. Record it as the exception's **second measured consumer**, so the entry reads as *"applied twice, by measurement, both times"* rather than as a rule quietly drifting wider. Two things that did **not** change: the exception is still a per-table scoped selector, never a shared-rule edit; and the registry table keeps `.data-table`'s `min-width: max-content` **no-crop floor** — releasing it (what `.data-table--prose` does for the stats table) was the other obvious way to make it fit and was deliberately **not** taken, because that floor is what stops the prefix and callsign columns cropping. A check asserts no bare `.data-table--registry { … }` rule exists. **The bar for a third consumer is unchanged: measure first, in both languages, at the real viewport, or do not do it.**

**A third table met that bar and was still NOT admitted to this exception — it took the OTHER remedy (quick task 260913-cz6).** The stacked-cell exception therefore still has exactly **two** consumers (Flights' When/Flight, the registry), and this entry is the record of why the count did not become three. Health's **battery readings table** (`table.data-table--readings`, behind Étatʼs closed-by-default « Voir 20 relevés » `details.readings-disclosure`) hit the identical measured cause — `min-width: max-content` sizing every column to its widest unwrapped line — at a **390px** viewport: the table measured **432px (FR) / 369px (EN)** inside a **308px** `.data-table-wrap`, the « Horodatage » column alone taking **302px** for the one-line concise form `31 juil. 08:00 (il y a 44 j)` against **130px** for the four-digit millivolt column. The stacked treatment was measured on this table **first**, and rejected on its own numbers: stacking only lowers the floor from 432px to **297px**, which clears 390px by **exactly zero** and still overflows at **360px** (297 against 278) and **320px** (297 against 238) — a fix already broken on a common Android width — while also forcing two lines at 1280px, where the wrap has 830px to spare. Releasing the floor (`table.data-table--readings { min-width: 0 }`, the `.data-table--prose` remedy) was taken instead, and the reason it is right here and was right to reject for the registry is **specific to each table's columns**: the floor exists to stop short **opaque codes** cropping, the registry has two such columns (prefix, example callsign) with no safe internal break point, and this table has none — one column is a four-digit integer (a single token with no break opportunity, so the floor is inert for it) and the other is a timestamp whose every break opportunity is a real word boundary. Measured at 360px and 390px in both languages, the released line breaks on the exact semantic boundary (`31 juil. 08:00` / `(il y a 44 j)`), because the space before the parenthesis is the only mid-string break opportunity and French already carries a non-breaking space inside `44 j`; at 768px and 1280px it stays on one line. **The general lesson, which is new:** this defect was invisible for its whole life because the **wrapper** scrolls, not the page — `document.documentElement.scrollWidth` stayed exactly 390 open *and* closed — and because the table sits behind a disclosure no visual sweep had ever opened. A page-level overflow assertion is structurally incapable of seeing this class; measure each `.data-table-wrap` against its own `clientWidth`, with every `<details>` forced open, or it will not be seen. The browser harness now does exactly that for Étatʼs tables.


**A FOURTH site of the same cause, outside a table entirely, and it took a THIRD remedy (quick task 260913-dgh).** Read this before assuming either of the two remedies above transfers. The measured cause is the one this file has now recorded four times — *a content-sized track never yields, so its flexible neighbour absorbs every shortfall* — but the site is Home's recent-flights list, not a table, and neither the stacked-cell exception nor the floor-release applies to it. `.recent-flight` was a three-track grid: a fixed 40px thumbnail, `minmax(0, 1fr)` for the callsign, and `auto` for the clock-plus-relative-age pair. The time carries B18's one-line contract, so its min-content and max-content widths are the same number and the `auto` track resolves to one rigid figure at every width — measured **155.1px in French, 147.4px in English**. That leaves the callsign track as the only one that can yield, and `minmax(0, 1fr)`'s explicit **0 floor** means it yields all the way down: measured in a real Chromium, the callsign box was **10.9px (FR) / 18.6px (EN) for 57.8px of content at 320px**, and **50.9px (FR) at 360px** — a common Android width. **The 0 floor is the whole defect.** A flex item's automatic minimum size holds a line at min-content for free; `minmax(0, 1fr)` is precisely the declaration that opts out of that, and this is the one thing to carry away from this entry: writing `minmax(0, 1fr)` is a decision to let that track be starved to nothing, and it needs somewhere for the overflow to go.

**What the defect looked like, and why every existing check was blind to it.** Not a crop — nothing here declares `overflow: hidden`. The starved *box* collapsed and its *text* painted straight out of it and over the time beside it (at 320px the rendered row reads `AFR135ût 00:31`, the two strings overprinting glyph for glyph). Every overflow assertion in this repo measures a box against a **container** — the viewport, the row, the `.data-table-wrap`. This element stayed inside its row and inside the viewport the whole time, so `documentElement.scrollWidth` was exactly 320, the row-box sweep quick task 260913-bjy added found nothing, and the defect was invisible. **The general lesson, which is new and is the counterpart to cz6's:** a box can be wrong with respect to its own CONTENT while being perfectly correct with respect to every container it sits in. Measure the box against a `Range` over its own contents (`selectNodeContents` + `getBoundingClientRect`), not against its parent — and not against `scrollWidth` either, which rounds to an integer and reports 81 for an 80.89px box.

**Viewport width does not predict row width here, so a media query cannot express the condition.** Measured: the row is **238px inside a 320px viewport, 278px at 360px, 308px at 390px, 686px at 768px — and back DOWN to 292.4px at 1280px**, where the desktop sidebar and the two-column picture row narrow it again.

**A container query was measured, works, and was still rejected — on its numbers.** It is the obvious instrument for a condition a media query cannot express, and this codebase does not use one yet, so introducing one would have been a deliberate act worth making. The reason not to is specific and measurable: a container query needs a hard-coded threshold, and the content that threshold has to clear **grows without a ceiling**. `layout.relative_age_text()`'s day bucket has no upper bound, so the age string only ever gets wider. Measured with the age stressed to `il y a 365 j`, the **1280px** callsign track falls to **57.5px for 57.8px of content** — the desktop starves too, and it was only ever ~7px away. Any threshold that covers a 292.4px desktop row therefore pays the second line at 1280px **unconditionally, in both languages, forever**, and a threshold that does not cover it ships already-broken. **A wrapping flex line was taken instead**, because flex line-breaking runs on the items' own content widths: it asks *does this fit on one line*, which is the condition that actually matters, instead of naming a width at which it might not. Measured after the change, callsign box against callsign content, both languages: **57.8 for 57.8 at 320, 360, 390, 768 and 1280** — starved at no width in either language — with the second line appearing only at 320px (both languages) and at 360px in French. With the age stressed, the same rule wraps at 1280px in **French** and stays on one line at 1280px in **English**: a per-language, per-content answer no fixed threshold can give. `.status-row` already shipped this exact combination (flex, wrapping, baseline-aligned), so the row joined an existing pattern rather than inventing one.

**Two further treatments measured and rejected, recorded so nobody re-derives them.** (a) `minmax(min-content, 1fr)` on the callsign track: it does stop the starvation, but the row then grows to **284.9px inside a 238px column** and Home's horizontal scrollbar comes straight back (`documentElement.scrollWidth` **343 FR / 335 EN against 320**) — the exact B11 defect quick task 260913-bjy had just closed. A grid row has nowhere to put what does not fit. (b) Releasing the time's one-line contract under a container query: this changed the resolved tracks by **literally nothing**, because a grid `auto` track is sized from max-content and never consults the min-content such a release lowers. It would have shipped inert — the same dead-declaration class this file retired the sticky header for. (c) An unconditional second line for the time fits everywhere and charges every row **23.6px of extra height at 768px**, where there are 686px of room and nothing to fix.

**320px: what this does and does not settle.** For this component it settles it completely — the callsign is unstarved and the page does not scroll sideways at 320px in either language. It says nothing about whether 320px is a supported width for the app as a whole; that question is open and belongs to whoever decides it deliberately.

**Corroboration is dot-only here, and only here.** `layout.status_dot()` gained a `visually_hide_label=False` keyword; every pre-existing call site (Health's own table) is byte-identical, and Flights' desktop Corroboration cell is the one caller passing `True` — the dot keeps its real accessible name and `title` tooltip, only the visible `.dot-label` span is hidden. This is what makes the five-column budget realistic: a visible ~90px-wide label on the column that carries the least essential at-a-glance information (its own dot colour already answers the question) would have blown the budget the stacking fix above exists to protect.

**Scoped padding, not a shared-rule change.** `table.data-table--flights td, th { padding: var(--space-sm) var(--space-sm); }` (8px both axes) is a second, narrower register value that exists only inside this one table's own selector — the shared `.data-table td/th` rule (16px, Health's and Airlines' own tables) is untouched.

**Day separators (Phase 22, X5).** Thirty-six to fifty rows used to run together with nothing marking where one day ended and the next began. A real `<tr>` separator now carries a "Today" / "Yesterday" / absolute-date label, grouped by `paris_day()` — the **Europe/Paris** calendar day, never the UTC one, which is the same rule the daily battery buckets follow. **The label's shape is the output of the Paris-day formatter, and that is not a licence to call `strftime` directly:** the absolute form is composed from `layout.month_abbr()`, the one twelve-entry language-aware table this codebase exposes, so the separator cannot grow a second date path of its own. The shipped form is therefore the **abbreviated** month — `26 Aug` / `26 août` — not the full `%-d %B` the phase's own copy table drafted; a full-month label would need a second exposed table in `layout.py`, and it belongs there, not in this page. `history_page.py` contains **zero** direct date-formatting calls, asserted by a harness check. **These separators are NOT sticky, and as of 2026-09-13 that is a settled decision, not a deferral.** D7's sticky half was put to the developer with both variants rendered on the real page at the same scroll offset: the sticky title works, but **every row already carries its own date** (`1 août 21:41`), so it would repeat information already on every line — and it costs turning the list into a ~7-row bounded-height box inside a half-empty page. Declined. **Revisit only if the per-row date is ever removed**, which would make the title non-redundant. The original deferral read: sticky day headers are D7, Phase 23; this phase's T4 *removed* the app's one broken sticky claim rather than adding a second, and the separator rule declares no sticky positioning at all — its own comment says why without quoting the phrase, so a `grep`-shaped guard is not tripped by prose describing its own absence.

### The Flights list is live (Phase 23, D7/CFG-37)

**Both renderings are swap regions, not whichever one is visible.** Flights declares four regions to the shared refresh loop — the freshness line, `ul.history-cards`, `.data-table-wrap` and `[data-filter-count]`. Declaring both renderings of the list is deliberate: the `.history-cards ~ .data-table-wrap` sibling toggle above decides which one is *visible*, but **both are always in the DOM**, so swapping one would leave the other showing an older list the moment a window was resized. Everything `list-filter.js` resolves once at load — the input, Clear, the empty-state block and the set hooks — is excluded **by name**, with the reason in the registry's own comment; the filter count is in only because it stepped out of that category (it is now looked up fresh inside `applyFilter()`, which is the change that made it swappable at all).

**Identity before position, and this is the transferable rule.** A row's own `runway_events.id` is rendered as `data-flight-id="e{id}"` on the summary `<tr>`, its sibling detail `<tr>` and the phone card `<li>`. The pre-existing `flight-detail-{n}` and `data-filter-group={n}` are untouched and still the **loop index**, because they do a different job — they pair one render's two representations — and **both renumber the instant a detection arrives at the top**. A highlight keyed to the index lights up every row below the insertion; an open-row record keyed to it reopens whichever row inherited the number. Both failure modes are measured, not reasoned about. The degrade is one-directional by construction: a row with no integer id falls back to its timestamp and hex, and if several rows share a value the consequence is a highlight **suppressed**, never one invented, because a shared identity reads as already-known.

**The arrival signal is one-shot and is diffed against the page as first rendered.** `.is-new-row` (a `--motion-slow` background wash that drains) is applied only to identities absent from the set collected at load. **An empty starting set is the defect to avoid**: it makes the first refresh announce the entire list, which is the same as announcing nothing — measured at 108 elements highlighted on a refresh that brought nothing new. The class is added and never removed, and nothing needs to remove it: the node it lands on was itself just inserted, its background is its ordinary one before and after, and the next swap replaces the node entirely.

**The detail row's reveal is a real height, and the closing direction is instant on purpose.** `<tr>` is `display: table-row`, so it is not a grid container and has no track to grow; the animation therefore lives one level down, on a two-element wrapper inside the `<td>` — an outer single-track grid transitioning `grid-template-rows: 0fr → 1fr`, and an inner element carrying `overflow: hidden` **and `min-height: 0`**. The second is load-bearing and is the part most likely to be dropped as redundant: a grid item's automatic minimum size is its content's, so without it the track never reaches `0fr` at all and the row simply appears with a pointless transition attached. `interpolate-size`/`calc-size()` were not reached for — Chromium-only, banned by name in the motion guard. `@starting-style` supplies the entry value (a row going from `display: none` to displayed has no previous computed value to transition from), and **both it and the transition are scoped to `.flight-rows-live`**, a class `flight-rows.js` adds to `<html>` — because with scripts blocked every detail row renders open, and an unscoped entry animation would unfold up to fifty rows at first paint in front of a reader who has touched nothing. **`transition-behavior: allow-discrete` was considered and declined in writing**: for the whole of that transition, and on every browser without the property, a closed row's copy buttons and links are still in the tab order and still in the accessibility tree — measured, 4 of 4 controls focusable — so a keyboard user tabs into a row nobody can see. A row that shuts instantly is a smaller loss than a row that is secretly still there.

**Every relative age that does NOT tick, enumerated rather than forgotten — this is the list, and it is the list CFG-34's own final clause asks for.** Phase 23 gave the app a `<time data-relative>` convention and a one-second ticker, and converting `layout.concise_timestamp_html()` carried it to Health, Flights' phone card, Airlines and Home for free. Four visible or near-visible ages are still static, read live off the code at this phase's close:

| Site | What the reader sees | Why it is still static |
|---|---|---|
| `history_page._when_cell_html()` | the Flights **desktop** table's When cell — a clock over a static age | Composes from `layout.relative_age_text()` directly; its own docstring says why it does not reach for `concise_timestamp_html()` (Pitfall 4, the inline-suffix shape). **Nothing blocks the conversion.** It needs a plan that owns `history_page.py`. **Correction of record:** 23-03's inventory routed this site to 23-08 while describing it as "the mobile card's relative-age secondary line" — it is the **desktop** cell; the phone card goes through `concise_timestamp_html()` and **does** tick. So today the same row's age is live below 960px and frozen above it. |
| `config_page`'s Calendar status detail | "Connected · 12 entries, refreshed 3m ago" on Display | A status detail string, not a clock beside a time. Live-capable, nothing blocks it; no plan owned it. |
| `health_page`'s unresolved-prefix registry cells | "31 juil. 08:00 · il y a 44 j" | Hand-composed `.cell-primary`/`.cell-secondary` pair, same shape as the Flights desktop cell. Live-capable; no plan owned it. |
| `health_page`'s battery `when` text | inside a `title` tooltip on the battery chart | **Structurally cannot become an element**: `battery-trend.js` writes it into a `title` attribute with `setAttribute`, markup in a `title` renders as literal angle brackets, and a shipped check pins that the script does no client-side date math. Changing this means changing that script's transport first. |

One further site is **not** a visible age and is listed only so the count reconciles: `history_page`'s `"ts"` row key still holds `absolute_and_relative()`'s plain-text form, but its own comment records that no renderer uses it for the visible cell any more.

**The detail row's own no-JS floor.** The `<tr class="flight-detail-row">` server-renders with no `hidden` attribute and no inline style — fully visible by default. A new script, `companion/static/flight-rows.js` (ES5, registered through the same six-touch-point static-script contract `theme-preview.js` already established), adds a `flight-detail-row--collapsed` class to every detail row at load and toggles it on click of the row's own `[data-row-toggle]` button (which also flips `aria-expanded` and swaps its own text between `data-more-text`/`data-less-text`). This is the same per-script class-at-load pattern `theme-preview.js`'s own usage-panel collapse uses (see `references/control-density.md`), not a page-wide `.js` class — chosen specifically so a page where only this one script is blocked by a stricter CSP still shows every detail row, rather than a page-wide gate silently hiding data no script actually collapsed.

### The drawing contract (new, Phase 24, D21/D8/D13/D20/D4, CFG-39..CFG-45)

Phase 24 gave this app its first **shared drawing module**, and this entry is that
module's contract — a fourth standing contract beside the motion budget, the
colour-separation contract and the spacing tokens. Every value below was read live
out of `companion/draw.py`, `companion/battery.py` and `companion/static/style.css`
at the phase's close, not recalled from a plan.

**One geometry vocabulary: `companion/draw.py`.** Stdlib-only, imports nothing from
`companion/pages/` and nothing from `server/` (both pinned by an **AST** scan, not a
token scan — an AST carries no comment and no docstring by construction, which is a
stronger statement of the comment-strip claim than stripping them). It exposes the
scales (`percent_x`, `percent_y`, `percent_time`), the canvases (`percent_canvas`,
`unit_canvas`, `label_grid`), the shape emitters (`rect`, `line`, `circle`, `path`,
`title`, `label_span`), the four composed drawings (`ring_gauge`, `day_band`,
`regularity_grid`, plus `unit_circle_dash_array`/`unit_point_on_circle` beneath the
first), the filters (`usable_pairs`, `is_number`) and the two class mappings
(`status_class`, `cell_class`). It does **not** import `companion/battery.py` even
though it may: **geometry must not know what it is plotting.** A drawing takes a
fraction, an instant or a verdict — never a millivolt value.

**Two coordinate schemes, and the rule for choosing between them.** They are two
separately-named helper families (`percent_*` / `unit_*`), never one helper with a
`use_viewbox=` flag — a flag is how the two get mixed inside one drawing — and they
have one canvas class each.

| | **Percentage scheme** (`percent_canvas`, `.drawing__canvas`) | **viewBox scheme** (`unit_canvas`, `.drawing__figure`) |
|---|---|---|
| Use it for | a card-filling time series that must stretch to whatever width its card gets | an intrinsically aspect-locked mark (a ring, a grid of squares) |
| The SVG carries | **no `viewBox` at all** | `viewBox` **plus** intrinsic `width`/`height` attributes in CSS pixels |
| Labels | HTML `<span>`s **outside** the canvas, placed by `label_grid()`'s two-track CSS grid | same — see below |
| Sized by | CSS: `width: 100%` and `height: var(--drawing-canvas-height, 160px)` | its own intrinsic attributes; the class deliberately declares **no** size |
| Consumers | Health's battery chart, Home's day band | Health's battery ring (72px), Home's battery ring (36px), Health's regularity grid |

The percentage scheme is the older of the two — it is `battery_sparkline_svg()`'s own,
generalised rather than invented — and the reason it is kept is measured: **give that
chart a `viewBox` and every stroke width, marker radius and hit target scales with the
box**, so at the 360px floor the tap targets shrink below the size they were chosen
for. The reason the viewBox scheme exists at all is the mirror: a ring drawn in
percentages is an ellipse the moment its box is not square.

**Labels are HTML, outside the canvas, in both schemes — and that is what makes
`viewBox` overflow unreachable rather than merely avoided for text.** A label placed
this way also keeps one constant CSS size instead of shrinking with its box.
`.drawing-axis-label` is 10px / line-height 1.2 — not a new type tier, exactly
`.sparkline-axis-label`'s own values, which already sit in `SKILL.md`'s sub-scale
exception tier. When 24-07 needed a scale under its grid it used spans too, so **this
phase emitted no SVG `<text>` node anywhere**; the containment obligation is still
discharged, on the cells' own ink (`getBBox()` expanded by half the *resolved* stroke
width, in the open, rather than inside a `getBBox({stroke: true})` option dictionary
whose support would have to be assumed).

**The nested-viewBox escape hatch** (24-05). A percentage-scheme canvas can host a
user-unit sub-drawing without either scheme leaking into the other: a nested
`<svg viewBox="0 0 100 100" preserveAspectRatio="none">` establishes its own viewport
in which user unit N maps to exactly N% of the same box **in each axis
independently**, so a plain user-unit `<polygon>` lands on the coordinates the outer
scheme's percentages already produce. This is what made the battery chart's area
possible at all: **percentages are not legal in a `points` list or a `d` string**
(the same rule that already made the trend line `n-1` `<line>` segments rather than
one polyline), and nothing but `<rect>` takes percentage geometry, so a per-segment
trapezoid was not available either. The nested layer deliberately gets **no CSS rule
of its own** — its box comes from the single `.battery-trend-section svg:not(.icon)`
declaration, and a check asserts no `.sparkline__area` rule exists.

**Paint is a class and a token, never a literal, and never a reference.** Four
anti-patterns are enforced by a machine (`companion/test_companion_app.py` Section
2.8), each mutation-proven:

1. **No colour literal in emitted SVG.** A colour decided in Python is correct in one
   theme. Every shape takes its colour from a class bound to a theme token, which the
   dark-theme block redefines, so the shape follows for free — and a literal is also
   invisible to `companion/contrast_check.py`.
2. **No unpainted shape.** A `<rect>`/`<circle>`/`<path>` with neither a class nor an
   explicit `fill`/`stroke` takes the SVG default fill, which is **black**: correct
   against a light card, invisible against a dark one, and invisible to the contrast
   harness too. `fill: none` counts as an explicit route and is declared on purpose,
   not as tidy-up.
3. **Every emitted class resolves to a real selector in `style.css`.** A class that
   exists in Python and nowhere in CSS paints *nothing at all*, and nothing else in
   this codebase would notice. The check matches on a **selector boundary**
   (`\.<class>(?![-\w])`), because `.drawing-axis` is a substring of
   `.drawing-axis-label` and a plain `in css` test reports both resolved on the
   strength of one unrelated selector.
4. **No loaded or externally-painted attribute.** `REFUSED_ATTRIBUTES` is `href`,
   `xlink:href`, `src`, `style`, `filter`, `mask`, `clip-path` (plus anything starting
   `on`), refused by name whatever they carry; `PAINT_ATTRIBUTES` (`fill`, `stroke`,
   `stop-color`) may carry only a keyword from `PAINT_KEYWORDS`
   (`none`/`currentColor`/`transparent`/`inherit`). **Everything else is text, which
   is escaped, never refused** — a refusal would turn a page render into an exception
   for a value the app does not control (an airline name out of `history.db` carrying
   an angle bracket).

**`url(` is banned outright, and that is why this phase ships no gradient.**
`battery_sparkline_svg()` carries a standing, directly-asserted guarantee that its
return value contains no `url(`, `<image` or `<script` — a literal substring scan with
no scheme analysis to appeal to. A `<linearGradient>` is only referenceable as
`fill="url(#id)"`, so CFG-41's "gradient area" could only have shipped by relaxing a
security-shaped assertion for decoration. **It did not.** The area is a flat
`fill: currentColor` + `fill-opacity: 0.14`, which delivers the property that clause
actually names — *derived from the line's own colour, so it is correct in dark mode by
the same mechanism the line already is* — and the three shapes are measured resolving
to one identical ink in each theme. Recorded as a **deliberate non-build with its
ground**, not as a gradient that is coming later.

**A drawing and any number printed beside it must come from the SAME value — one
call, two renderings, never two calls that agree today.** This is the phase's
sharpest rule and it was settled by mutation rather than by argument. Health's and
Home's battery rings draw `battery_percent(mv) / 100` — the printed integer over a
hundred — and **not** `battery_fraction(mv)`, even though 24-01 added
`battery_fraction()` for exactly this. Sourcing the ring from the fraction instead
makes the arc and the text disagree by **0.0033** on a seeded 3690 mV reading, and the
check (tolerance 0.0005) fails naming both: *the ring draws 0.4333 of its
circumference while the readout beside it prints '≈ 43% · 3690 mV'*. The cost is real
and worth stating: the ring quantises to 1% steps, which at 72px is 3.6° of arc, about
0.6px of ink. The benefit is that the whole class of defect becomes unreachable rather
than unlikely. The same rule shapes the day band from the other direction: the emitter
returns the number of marks it **collapsed**, so the caption cannot print a total the
drawing does not show.

**One battery estimator, with exactly TWO allow-listed homes.** `companion/battery.py`
holds `BATTERY_FULL_MV` (4200), `BATTERY_EMPTY_MV` (3300), `battery_percent()`,
`battery_fraction()`, `LOW_BATTERY_DISPLAY_PERCENT` (20) and `LOW_BATTERY_DISPLAY_MV`
— the last **derived** (3480, and `battery_percent(3480) == 20`), never typed, so the
line a chart draws and the percentage printed beside it cannot tell two stories. The
second allow-listed home is **`server/poll_loop.py`'s deliberate private copy**
(`_NOTIFY_BATTERY_FULL_MV` / `_NOTIFY_BATTERY_EMPTY_MV` /
`_battery_percent_estimate()`), and it is allow-listed **by name with a written
justification** rather than scoped away: the server package may never import the
web-app package (D-27), so the poll oneshot genuinely cannot call the shared module.
A **third** definition anywhere under `companion/` or `server/` fails the check. The
scan has three nets, because the first two can be evaded by renaming: the constant
names, a second `battery_percent`/`battery_fraction` definition, and — the one that
catches a copy whatever it calls itself — **`4200` and `3300` appearing together in
one module**. (`4200` alone is innocent: `health_page.SPARKLINE_Y_MAX_MV` is
legitimately the same number.) A page that calls the estimator must call it
**qualified** (`battery.battery_percent(...)`), because a bare
`from companion.battery import battery_percent` makes it read as the page's own.

**The estimator's SECOND arithmetic, and the honesty rule that governs it (new, Phase
25, D18/CFG-49, 25-01/25-05).** `battery_life_estimate(rows, current_s, proposed_s)`
joins the same module — same one home, same guard, no new file. It answers a question
this app had never answered before ("how long does a charge last?") and it answers it
**only as far as this device's own observed history supports**, which is the rule
worth carrying forward rather than the function:

- **Five NAMED states, never an overloaded `None`:** `no-reading`,
  `not-enough-history`, `rising`, `flat`, `falling`. **Only `falling` carries a
  number.** `rising` carries none *deliberately* — a charged device has a positive
  slope, and dividing by it gives a negative or an infinite lifetime, and both are
  numbers a reader would act on.
- **No per-wake energy cost is assumed anywhere**, because this project has never
  measured one (DEVICE-05's discharge run is still open). The audit's own
  "estimated battery life ≈ 38 days" **cannot be computed honestly today and was not
  computed**. This is the dishonest-state defect class Phase 22 spent a phase
  removing, met before it shipped rather than after.
- **Two observation floors, both load-bearing and both pinned from the opposite
  extreme.** `LIFE_MIN_OBSERVED_SPAN_DAYS = 2` (a one-day delta between two daily
  *averages* is inside this series' own noise — a 150 mV fall measured across one day
  would otherwise report three days remaining) and `LIFE_MIN_OBSERVED_DROP_MV = 10`
  (a 1 mV fall over three days divides out to roughly five years, which a reader takes
  as a promise). The second is load-bearing for **totality** as well as honesty:
  without it a perfectly flat series divides by zero.
- **`relative_factor` is separable and always available** — the ratio of two cadences
  and nothing else — which is what lets a gauge say something true on day one. Its
  docstring states precisely what it is **not**: a multiplier on the lifetime, which
  would only be the same number if every joule this device spends went into waking.
- **The honesty rule is made STRUCTURAL at the presentation layer, not promised.** The
  absolute "≈ N days" sentence is rendered by the **server, outside every element a
  script can rewrite**; what the script may rewrite is a template naming two cadences
  and containing no days figure at all. "The script cannot be braver than the server
  was" is therefore not a policy a future editor has to remember — **there is no
  template through which it could be.** Full card-level contract in
  `references/settings-page-patterns.md`.
- **The `≈` marker travels with it**, the same marker the battery percentage already
  wears, plus a named source ("from this frame's own recent readings") over a **14-day**
  window — deliberately shorter than health_page's three-month trend window, because
  the sentence says *recent* and a slope measured across a charge three months ago is
  not. Dropping the marker fails a check by name.
- **Phase 24's paragraph in `companion/battery.py` forbidding this was corrected IN
  PLACE, not deleted.** It read: *"Deliberately NOT added here: a 'battery life
  remaining' estimate … it needs a discharge model this project has no data to
  justify."* That reasoning was right about the **model** and wrong about the
  **conclusion** — what it ruled out was an estimate built on an assumed per-wake
  cost, which this is not. **DEVICE-05 will change this**: a measured mAh-per-cycle
  figure lets a later plan add a second, model-based branch inside this same module
  and print it through the same wording. **The gap is in the data, not in the
  presentation**, and nothing in the card needs to change to accept it.

**Phase 24's drawings carry no motion, deliberately.** The `.drawing*` block declares
no `transition` and no `animation`; the stylesheet's `@keyframes` count is still
**4** and the reduce-block count still **2**, exactly where Phase 23 left them. A
drawing that animates on every refresh swap would be ambient motion nobody asked for
on the app's busiest page.

**The three drawings' own numbers, read live.**

- **Ring gauge** — one emitter, `ring_gauge(fraction, size, status_class=None)`, with
  **no `variant` parameter and the docstring saying why one must never be added**.
  The geometry is **ratios of the box side**, which is the mechanism that makes a
  CSS-only "small variant" impossible: `RING_STROKE_RATIO` 0.12, `RING_CLEARANCE_RATIO`
  0.02, `RING_MIN_SIZE` 8 (clamped, never refused). At 72px: r 30.24, stroke 8.64,
  outer ink edge 70.56 inside a 72 viewBox. At 36px: r 15.12, stroke 4.32, edge 35.28.
  Both ratios identical by construction (0.42 and 0.12), and that equality is what the
  cross-page check measures. **`stroke-width` is a presentation ATTRIBUTE, never a
  stylesheet declaration** — CSS of any specificity beats a presentation attribute, so
  a `stroke-width` in `.drawing-ring-*` would flatten both sizes to one thickness and
  hand the size parameter back to CSS. **Both degenerate fractions are handled where
  both arc mechanisms fail:** at 0 no value arc is emitted at all (a zero-length dash
  renders as a *dot* under a round cap), and at 1 a complete circle is emitted with no
  dash pattern (an arc `<path>` whose sweep is the whole circle is degenerate in SVG
  and draws *nothing* — so full would read as empty, the worst possible value to be
  wrong at). `stroke-linecap: butt` is declared explicitly even though it is the
  initial value, because a round cap adds half a stroke width at *each* end and a 5%
  reading would draw ~12% of the circle. The track is `--color-border` and
  deliberately **not** `currentColor`, so it stays structural when the status modifier
  turns the value arc amber or rose.
- **Day band** — `day_band()` on `percent_time()`, the phase's only TIME-domain scale,
  which **rejects** an out-of-day instant rather than clamping it (clamping invents a
  check-in at an edge of the band). `DAY_BAND_MARK_WIDTH_PX` 2 and
  `DAY_BAND_MIN_MARK_SPACING_PERCENT` **1.5** — re-derived from the band's **measured**
  278px canvas (4 / 278 = 1.4388%, rounded **up**, because this is a floor on
  legibility and rounding down permits exactly what the constant prevents). At 278px
  that is 4.17px centre to centre; the element-count ceiling is **67** marks and the
  finest resolvable interval on a 24-hour day is ~22 minutes. The quiet-hours window
  crossing midnight is **two** spans, never one — one span from 22:00 back to 07:00
  has a negative width, and the obvious repair (swap them) shades the whole day and
  leaves the night clear, which looks entirely plausible.
- **Regularity grid** — `regularity_grid()`, bounded by its own geometry rather than
  by its caller's window: `CARD_DRAWING_WIDTH_PX` 278, `CELL_MIN_SIZE_PX` 24 (WCAG
  2.5.8), `CELL_GAP_PX` 3, so `grid_columns()` **computes** ten columns at 25.10px
  (eleven would give 22.55px, under the floor) and `GRID_MAX_ROWS` 6 caps it at
  **60 cells**. The bucket count comes down, never the cell size. It keeps the
  **newest** buckets and reports how many it dropped. **Four** states, not three:
  `drawing-cell--on-cadence` / `--late` / `--missing` / `--none`, and the fourth is
  produced by the classifier itself (`wake.classify_check_in_gap(None, cadence)`
  already answers `unknown`) so **no branch on the page decides any cell's colour**.
  `cell_class()` falls to the no-observation class for anything unrecognised — not to
  on-cadence (which would report health from a value nobody recognised) and not to
  missing (which would accuse the device on the same).

**What the grid does NOT claim, and this is a contract clause rather than copy.** It
reports **observed check-in regularity**, judged against the cadence currently in
force. It is not a rate of wakes the device kept, and it must never be renamed into
one: a log rotation the ingest missed leaves a hole indistinguishable from a missed
wake, and no schema change recovers it. The caption carries three clauses, each
separately asserted and each separately mutation-proven, and the two words the
roadmap's own draft name for this drawing used are asserted **absent** from the
rendered page in both languages.

### Measurement conventions this phase paid for (Phase 24)

Three of these cost a real defect each. They belong here rather than in a SUMMARY
nobody re-reads.

**1. Assert the FLOOR, not only the ceiling.** Three consecutive plans shipped
ceiling-only assertions and each let a real defect through with every check green:

- **24-06.** All four of the day band's checks were ceilings ("no more than N marks").
  A collapse rule comparing each position against its *immediate predecessor* instead
  of the *last kept* mark passes every one of them — and at a cadence finer than the
  minimum spacing it keeps the first position and never another. Measured on the
  mutant: a day of **1 440 check-ins drew one mark at 0.00%** and an empty band after
  it, the frame rendering as dead since midnight, while `collapsed` dutifully reported
  1 439. The correct rule draws 66 marks from 0.00% to 99.31%. *(The docstring's own
  recorded reason for the last-kept rule was also wrong — it claimed a ceiling
  argument, and the ceiling holds under either rule. The reason is the floor.)*
- **24-07.** The grid's containment assertion was `x + w <= box_w`. A whole-pixel cell
  size (25 instead of 25.10) puts ten cells and nine gaps at **277px inside a 278px
  canvas** — inside the box, so green — and the HTML label row beneath, which sizes
  itself from the *card* rather than from the emitter's arithmetic, then names a column
  one pixel off. One scale places the cells and the labels, and a ceiling cannot see
  that. Fixed by asserting the last column's right edge **equals** the canvas width.
- **24-08.** `.home-overview > *` is **(0,1,0)** — the universal selector contributes
  nothing — which *ties* `.frame-strip`'s own (0,1,0) `margin-bottom` and loses on
  source order. Measured: the hero's first two parts sat **40.00px** apart where 16 was
  declared, while the other gap was correct, because `.home-section` and
  `.page-section` are declared above the new rule and lost while `.frame-strip` did
  not. **Two thirds of the composition were right and one third was not** — precisely
  the shape a ceiling ("at most 40px") or an eyeball passes. Fixed with the doubled
  selector `.home-overview.home-overview > *` (0,2,0), the same hazard and the same fix
  `.page-section.banner--anomaly` already documents.

**2. Mutate every property you add.** Six-plus CSS declarations shipped in this phase
with confident load-bearing comments and measured either **inert** or
**load-bearing-but-invisible**. Both outcomes are defects, and only a per-declaration
mutation finds either:

| Declaration | Verdict | What the mutation showed |
|---|---|---|
| `.battery-readout-row` `min-width: 0` ×2, `.stat-tile__gauge` `flex: none` (24-04) | **inert** | `documentElement.scrollWidth` identical with and without, at 360px with a 60-char unbreakable run; a replaced element's automatic minimum size already floors the ring |
| `.sparkline-swatch` `flex: none` (24-05) | **inert** | the legend's line is 161px inside a 278px row — there is no overflow to shrink against |
| `.sparkline__legend` `grid-column: 1 / -1` (24-05) | **load-bearing, invisible** | with `auto` the legend claims the auto-sized Y-label column and the canvas drops **229.97px → 109.00px** inside the same 278px grid. It overflows nothing, so every assertion stayed green |
| `.day-band` `--drawing-canvas-height: 24px` (24-06) | **load-bearing, invisible** | removing it silently takes `.drawing__canvas`'s 160px default — a **6.7× taller** block. Overflows nothing, moves no mark, changes no colour |
| `.check-in-key__swatch` `flex: none` (24-07) | **inert** | *because of a sibling*: `flex-wrap: wrap` means no line ever takes width from a swatch. Remove the wrap and a French swatch is squeezed 12.00 → 9.03px |
| `.check-in-key__item` `align-items: center` (24-07) | **inert by coincidence** | the swatch is 12px tall and the label's line box is 10 × 1.2 = 12px, so cross-start and centre are the same place |

Every inert declaration was **deleted and the measurement written where it stood** —
a dead declaration with confident prose is worse than none, because it is what the
next reader trusts *instead of* measuring. Every load-bearing-but-invisible one got
the assertion that can see it (the canvas's share of its grid; the canvas's rendered
height). **The backlog this implies:** this discipline only ever ran over declarations
*this phase added*. The rest of `style.css` has never been swept, and the two classes
above are both silent by construction, so there is no reason to believe the ratio is
different there. A sweep is worth a plan of its own.

**3. Clear `__pycache__` after any sub-second mutate/revert cycle.** 24-08 lost a
browser run to this and the failure looked exactly like a defect in its own work.
`git checkout-index -f --` restored `companion/draw.py`, `git status` was clean — and
the next run reported two failures in another plan's checks, with the **mutated class
string still being served**. CPython validates a cached `.pyc` by comparing the source
mtime for **equality at one-second granularity**; the restored source's mtime was the
same second the `.pyc` had recorded, so the stale bytecode was considered valid and
the corrected source was never recompiled. The mutation and its revert had both
happened inside one second because the renders between them took milliseconds.
Verified against a pristine `git archive` of the same commit: clean. **Clear every
`__pycache__` outside `.venv` after reverting**, or the next harness run measures a
module that no longer exists on disk.

**4. Stage before you mutate, and revert with `git checkout-index -f --`.** Not
`git checkout --`, which restores from **HEAD** and will delete an unstaged
implementation outright — 24-04 lost a whole mutation round to exactly that, with all
four "failures" turning out to be one `AttributeError` for a function the revert had
just removed.

### Measurement conventions Phase 25 paid for, on top of those four

Phase 24's four are unchanged and still binding. Phase 25 ran ~170 mutations across
six plans and added these; **convention 4 above cost a second full re-write in this
phase, which is why it is restated here rather than assumed learned.**

**5. VACUITY is this codebase's recurring defect class, and MUTATION is the only
thing that finds it.** Not one of the checks below was wrong-looking; every one of
them was green against an implementation it was written to refuse. 25-01 strengthened
**four** before committing, 25-03 found **four**, 25-04 **three**, 25-05 **two**,
25-06 **one**. The *shapes* transfer even where the subjects do not, and each of these
is a specific thing to look for in your own check before you trust it:

| Shape | Where it bit | Why it passes |
|---|---|---|
| A mutation that edits a **comment** | 25-01 (twice), 25-07 | `str.replace(…, 1)` hits the paragraph quoting the constant, eleven lines above the assignment. The run is silent, the diff looks perfect, and the mutation **proves nothing while looking rigorous**. Print the changed line numbers and re-read the file after substituting. |
| A **substring rename** survives a seam check | 25-06 | `data-theme-pagerr` *contains* `data-theme-pager`, so `if NAME not in script` passed while both pagers were completely inert. Match on a `(?<![-\w])…(?![-\w])` boundary — the same discipline the gate-class pin already used. |
| A subject located by a **bare id string** | 25-05 | `markup.find("wake-interval-s-error")` matched inside the *input's own* `aria-describedby`, so a clause about element order passed against the one arrangement it forbids. Locate by the element (`<p class="field-error…" id="…"`), not by the id alone. |
| Width compared against **another element** | 25-05 | "the slider is full width" was asserted against the number input beside it — which a range with **no width rule at all** passes, its intrinsic ~129 px beating the field's 96 px. Compare against the container's own content box (278 px), which is the property under test. |
| `.click()` works on a **`display: none`** element | 25-06 | The prescribed mutation stayed green because the save still reached disk. `display: none` destroys **focusability**, not clickability — ask the keyboard question directly. |
| `locator.count()` counts a **hidden** element | 25-04 | "the arc is present with scripts blocked" passed against the arc moved *behind the gate* — the exact refactor it existed to notice. Measure the rendered **box**, not the node count. |
| An **inert** source order | 25-03 | "parse the label before the id" was asserted against a registry where the two sources cannot disagree, so swapping them changed no angle at all. Build a fixture where they genuinely disagree (id `31-13`, label `Runway 9 (07/25)`). |
| An attribute satisfied by a **child** | 25-03 | `"width=" in svg` was satisfied by the `<rect>` children while the `<svg>`'s own size route was gone. Scope the assertion to the opening tag. |
| The **border box** instead of the content box | 25-03 | A 64 px drawing inside an 87 px card's *border* box passes while overflowing its 53 px **content** box by 11 px. Read `getBoundingClientRect()` minus padding and border — and normalise by the element's own transform scale, because a selected card carries `scale(1.02)` while its padding does not. |
| A **first-paint** sample of a live-state rule | 25-03 | At rest the saved card *is* the checked card, so deleting the live `:has()` rule changed nothing a first-paint measurement could see. Pull the two apart with the keyboard — one card checked, a different one saved, a third neither. |
| A fixture that never produces the value under test | 25-05 | The "the figure equals the estimator's return" clause would pass against a card that prints no figure at all. **Assert the fixture produces one** before reading the sentence. |

**The general question, and it is the one to ask of every new check: what would a
WRONG implementation do here?** If the answer is "pass", the check is decoration.

**6. Never sample at a guessed instant — and this is now a THREE-phase finding.**
25-03's paint check read an interpolation frame and reported that *"the selected paint
is the same in BOTH themes — it is not coming from a token that inverts"*, against a
stylesheet that was entirely correct: the strips carry `transition: fill
var(--motion-fast)`, so a `getComputedStyle` taken straight after a theme flip read
**rgb(41, 43, 49)** for a strip whose settled dark value is **rgb(241, 243, 246)** —
about 8 % of the way along. (The `color-mix` samples gave it away by changing colour
**space**: `color(srgb …)` settled, `oklab(…)` mid-interpolation.) 25-05 met the
identical defect on the global `input, select` rule's `transition: background-color
.15s`. Phase 24 lost a check to the same class and the orchestrator fixed it with
`transitionrun`. **The instrument is the browser's own signal, never a timer:** await
the Web Animations `finished` promise on the elements (an element with nothing running
returns an empty list and resolves at once, so it can neither hang nor flake), or
listen for `transitionrun`. Counting `getAnimations()` immediately after a theme flip
also finds **zero**, before any style recalculation has created them — await one
`requestAnimationFrame`, a real browser callback, first.

**7. A SYNTHETIC event can drive a real control, and the guard and the proof need not
trade against each other.** 25-04 measured `_operate_with_keyboard()`'s own pointer
recorder self-test — an `el.dispatchEvent(new PointerEvent("pointerdown"))`, which
carries `clientX/clientY` of `(0, 0)` — **moving the user's saved quiet window from
23:15 to 22:30** while merely proving the recorder was alive. Any script on the page
could have done the same. `value-controls.js` now refuses `evt.isTrusted === false`
(compared against `false`, not negated, so a browser without the property does not
refuse every real drag) on both `pointerdown` and `pointermove`. That guard would
normally make the real gesture unmeasurable — but 25-07 showed it need not:
**Chromium's DevTools protocol `Input.dispatchDragEvent` carries a real `files` list
through the same input pipeline a pointer uses**, and the handler sees
`isTrusted: true`. One check now measures the real gesture *and* proves the fake one
inert.

**8. A function NAME can trip an existing guard, and the guard may be right.** 25-05's
`wake_battery_life_text()` failed `test_companion_app.py`'s battery one-home guard by
its name alone. The resolution was the **rename** — the function does not compute a
lifetime and should not claim to — **not an allow-list entry**, which would have let a
real second estimate in under that name later. When a guard objects to a name, check
whether the name was the defect before widening the guard.

**9. A mutation suite without a NULL CONTROL cannot tell a load-bearing property from
layout jitter.** 25-07 mutated twenty-nine CSS declarations and re-measured the
**rendered** result in a real browser each time. A mutation editing only a *comment*
inside the same block reported **14 measurements moved** — every one a
sub-pixel-to-4-pixel geometry jitter in the dialog's own width. Without that control,
every mutation in the sweep would have looked RED for the wrong reason. The named
properties moved for the null control **not at all**, which is what separates signal
from noise. The same run found one genuinely inert declaration (`.upload-drop
{ width: 100% }` moved the rendering by **0.00 px** where the null control moved it by
0.01) and kept a neighbouring one that moved it by ~1.9 px — and the stylesheet now
carries **both** results in a comment.

**10. Restated because it cost a second full re-write: STAGE BEFORE YOU MUTATE.**
25-07 ran its first Task 2 mutation against an **unstaged** tree, and the revert step
(`git checkout-index -f --`) restored `panel-lookup.js` from the index — deleting the
entire task's implementation in one step. 25-04 lost an implementation the same way.
Nothing was lost permanently either time, and both cost a full re-write. **Stage every
time, not the first time**, and clear `__pycache__` after the revert (convention 3
above), because a sub-second mutate/revert cycle leaves stale bytecode serving the
mutated behaviour.

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

**The FRAMING PREVIEW, and the recorded ground for having no client crop
(new, Phase 25, D19/CFG-51, 25-07).** The drop zone shows the visitor
what they picked and how it will be framed. It does **not** crop.

- **The preview box RESERVES the normaliser's own frame**, through an
  inline `--upload-preview-ratio` computed from
  `ILLUSTRATION_TARGET_WIDTH`/`HEIGHT` and read by `style.css` with
  **no fallback value** — a fallback would keep the box the right shape
  after the inline property stopped being rendered, which *masks* the
  deletion of the live value rather than guarding it. Measured at 360 px,
  at rest, before any image exists: **3.4098:1** against the module's
  **3.4091:1**. The `<img>` is `object-fit: contain` inside it.
- **There is NO client-side canvas crop, and this is a decision with a
  ground rather than an omission.** `companion/illustration_normalize.py`'s
  own docstring records that a *second, differently-thresholded
  measurement silently drifting from the first* is the debug session
  (`illustration-crop-text-margin`) that created it, and that the module
  "must never become a second implementation for that same measurement
  to drift against". A browser-side crop that "matches" it **is** that
  second implementation — in a language the server cannot check, on a
  machine it cannot trust. **The absence is asserted, not assumed:**
  `panel-lookup.js` names no `getContext`, `drawImage`, `toBlob`,
  `toDataURL`, `OffscreenCanvas` or `createImageBitmap`, comments
  included, and `companion/illustration_normalize.py` is unchanged by
  **one line** across the whole of Phase 25 (verified by diff against
  the phase's base commit).
- **Dropped and picked bytes are proven the same act, three ways, in this
  order of strength:** the static absence of every canvas API; a
  comparison of the file's **size in the input** on both paths; and a
  byte comparison of what landed on disk. The third is the *weakest* of
  the three and that is recorded rather than assumed — the server
  re-encodes every upload through Pillow, which absorbed a deliberate
  one-byte truncation and produced byte-identical output, so the clause
  that actually bit was the in-input size. Measured: the same source
  file stored **1833 bytes** whether picked or dropped, with **the
  stored file deleted between the two uploads**, or the comparison would
  have passed on the file left behind.
- **A future phase proposing a client crop meets this argument, not the
  idea.** So does one proposing an upload **progress bar**:
  `submit-guard.js` already disables a form's submitting control on
  submit, app-wide, and a ≤ 4 MB upload to a household server does not
  need `XMLHttpRequest.upload.onprogress`. (The recommendation's other
  half — adding an "Uploading…" label beside that disable — was **not**
  built either, and is on the developer's decision list rather than
  quietly dropped.)

### Table restyle this file predates (06.6.4, D-07)

- **Header:** moved from a filled `--color-secondary` block to a quiet uppercase 11px label with only a bottom hairline — no background at all.
- **Zebra striping:** retired. A single row surface plus a `tbody tr:hover` 4%-tint hover cue replaces the old `tr.row-alt` alternating background. The server-side `row-alt` class computation (`companion/layout.py`'s `data_table()`, `history_page.py`, `airlines_page.py`) is deliberately left in place as inert markup rather than removed — removing it would mean three Python edits and three harness updates for zero visible gain.
- **Last-row separator:** removed — `.data-table tbody tr:last-child td { border-bottom: none; }` gives the table a clean bottom edge instead of a trailing hairline.
- **Sticky-header scoping. SUPERSEDED (Phase 22, T4) — the rule is deleted, and the reason is not "we changed our mind."** The entry read: *"`.data-table-wrap th` is `position: sticky; top: 0;`, scoped to the table's own scroll container so it never collides with the `>=960px` sticky sidebar. Its background token is `--color-canvas` (chosen because History's table — the only one long enough for sticky to actually engage — renders directly on the page background, not inside a card)."* **That header could never stick.** `position: sticky` needs a scroll container with a constrained height to stick *within*; `.data-table-wrap` declares `overflow-x: auto` and **no height at all**, so it never scrolls vertically and the sticky offset had nothing to resolve against. The declaration was inert from the day it shipped, in every browser, on every page — a claim the stylesheet made about itself and never delivered. It is removed rather than made to work: **sticky day headers are Phase 23 (D7)**, and doing it properly means a real scroll container and a measured height, not a token swap.
  - **The never-live-validated `--color-canvas` background note is MOOT, not deferred.** That note (quick task 260901-uzi finding 5, candidate (b)) asked whether the stuck header should read `--color-canvas` or `--color-dominant` for the in-card cases (Airlines, Health), and flagged that nobody had ever seen it stuck to judge. The background declaration went with the rule it belonged to, so there is no longer a stuck header whose background could mismatch anything. Do not carry this question forward as an open item; if D7 reintroduces a sticky header it will be a new rule making a fresh choice, not a resumption of this one.
  - **Phase 23 IS D7, and it considered re-adding this and did NOT — the sentence above ("sticky day headers are Phase 23") is therefore SUPERSEDED as a forward pointer, in place, with its outcome.** The structural ground Phase 22 recorded has not changed: making a sticky header engage still means giving the Flights table a bounded-height scroll region of its own, which is a layout decision with the measured width and density budget in this file behind it, and it interacts with the phone card list, which is a different rendering entirely. But **that is no longer the deciding reason**, and the better one was found by rendering rather than by arguing: both variants were put on the real page with seeded data and scrolled to the same offset, and **every flight row already carries its own date** (`1 août 21:41`), so a pinned title would repeat what is already on every line — while the sticky variant shrinks the list to a ~7-row box inside a half-empty page and leaves a clipped row peeking under the pinned header. **Declined by the developer on 2026-09-13 (option A), on that evidence.** Nothing sticky was added: `grep -cE 'position: *sticky' companion/static/style.css` is **3**, its pre-phase value, of which two occurrences are prose. **The revisit condition is narrow and specific: only if the per-row date is ever removed** — for phone density, say — which would make the title non-redundant. This entry is now a settled decision, not a deferral, and it should not be re-proposed as an unexamined idea.

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

- **Variant A ("Stacked cells")** — still rejected as a whole-table pattern. Two-line cells increase row height, working against the goal of scanning many rows quickly on a small screen. **Narrow exception (Phase 21, D-15; a second measured consumer added Phase 22, B12):** the Flights table's own When/Flight columns ARE stacked, and Health's registry table joined them — but each only because measurement proved the inline shape overflowed that table's real width budget, the second time in French at 1280px. See "Flights table recompacted…" above. Do not generalize this exception to Route/State/Corroboration on the same table, or to any other table's merged cells, without the same measure-first discipline that justified it both times. **A third table (Health's battery readings table) was measured against this exception in quick task 260913-cz6 and deliberately NOT admitted** — stacking was measured to clear its 390px target by exactly zero and still overflow at 360px, so it took the floor-release remedy instead; the consumer count stays at **two**. See the "third table" paragraph above.
- **Writing `minmax(0, 1fr)` for a text column that sits beside a content-sized `auto` track** — that pair hands the flexible track every pixel of shortfall and explicitly floors it at zero, which is how Home's recent-flight callsign ended up with a 10.9px box for 57.8px of content and painted over the time beside it (quick task 260913-dgh). If the row genuinely cannot shed width, it needs somewhere for the overflow to GO — a wrapping flex line, not a wider floor, which only moves the overflow onto the page.
- **Reaching for a container query the moment a media query cannot express the condition** — right instinct, and it was measured here rather than assumed. It still lost, because its threshold has to be a fixed number and the content it must clear (the relative-age string) has no upper bound. Prefer a mechanism that reads the content instead of a width, when one exists; if you do reach for a container query, measure the growth of the content first.
- **Reintroducing `position: sticky` on a table header inside `.data-table-wrap`** — Phase 22 (T4) removed the app's one sticky-header declaration because the wrap has no height and it could never engage. A sticky header needs a real scroll container with a constrained height first. **The trailing clause of this entry used to read "that is D7, Phase 23, not a token swap" — SUPERSEDED (Phase 23): D7 ran, put both variants on the real page, and DECLINED it**, because every flight row already carries its own date. Revisit only if that per-row date is removed. See the sticky-header entry above for the full record; do not re-propose this as an open idea.
- **Calling `strftime` (or any direct date-formatting call) inside `history_page.py`** to shape a day-separator label — the label's shape is the Paris-day formatter's own output, composed from `layout.month_abbr()`. A second date path in this module is exactly what the one-formatter rule exists to prevent, and a harness check counts it.
- **Variant C ("Max density", 6 columns, merges State into Route too)** — still explicitly not part of locked scope. Do not implement it without a fresh discuss-phase decision extending the merge further. (Phase 21's own 5-visible-column table is a *different* reduction — it moved data OUT of the table into a detail row, it did not merge State into Route — so it does not retroactively authorize Variant C.)
- Reaching for the sketch's SUPERSEDED `--color-text-muted` token for any secondary/muted text in this file — it does not exist; use `opacity` on `--color-text` (matching `.cell-secondary`) or `color-mix(in srgb, var(--color-text) 70%, transparent)` (matching `.data-table th`/`.filter-bar__count`), whichever this file's existing precedent for that specific element already uses.
- Reintroducing a horizontal-scroll-only mobile fallback for Flights specifically — the `.history-cards` card list replaced it (D-16 confirms it is unchanged by Phase 21); other pages' `.data-table-wrap` reuse (Airlines, Health) is unaffected and still scrolls horizontally as before, since they never pair with a `.history-cards` sibling.
- Giving `.cell-secondary` and `.history-card__secondary` two different opacity values — they render the same content at two viewport widths and must stay at one shared muting strength.
- **Adding a client-side `<canvas>` crop for the artwork upload** (Phase 25, D19) — `companion/illustration_normalize.py`'s own docstring names a second, differently-thresholded implementation of that measurement as the failure mode it exists to prevent, and the absence is asserted by a source scan naming six canvas APIs. The preview *frames*; it never crops.
- **Adding an `XMLHttpRequest.upload.onprogress` progress bar** — `submit-guard.js` already disables the submitting control on submit, app-wide, and the upload is capped at 4 MB to a household server.
- **Writing a mutation sweep with no NULL CONTROL** (Phase 25) — a comment-only mutation inside the same block moved 14 rendered measurements by up to 4 px. Without that control every mutation in the sweep reads RED for the wrong reason.
- **Sampling a transitioning property at a guessed instant** — three phases running have lost a check to this. Await the Web Animations `finished` promise or listen for `transitionrun`; never a timer, and never immediately after a theme flip (the transitions do not exist yet).
- **Trusting a mutation that produced no failure without confirming it changed the line you meant** — the silent case is a `str.replace` landing in a comment that quotes the constant. Print the changed line numbers and re-read the file after substituting.
- Keying the Flights detail row's collapse off a page-wide `.js` class instead of `flight-rows.js`'s own scoped class-at-load — that would hide detail data on a page where a stricter CSP blocks only that one script, per the reasoning above.

## Origin
Synthesized from sketch: 003 (history-table-density), winner: Variant B. Corrected against the shipped implementation (`companion/pages/history_page.py`, `companion/static/style.css`) per 06.6.3 (D-07, mobile card list, table restyle) and `companion/layout.py`'s `concise_timestamp_html()` (06.6.3, resolving this file's own former open timestamp-format risk) — quick task 260901-t00. Updated Phase 21 (21-03-PLAN.md, D-15, CFG-22): the desktop table recompacted from 7 to 5 visible columns plus a detail-row toggle column, the When/Flight cells' scoped stacked-line exception (measured, not assumed), the dot-only Corroboration column (`status_dot(visually_hide_label=True)`), the scoped 8px cell-padding register, and `flight-rows.js`'s own no-JS floor for the new detail row. Updated Phase 22 (22-companion-audit-round-4, T4/X5/B12, CFG-31): the sticky-header entry SUPERSEDED outright (the wrap has no height, so it could never engage) with its never-live-validated `--color-canvas` background note recorded as **moot** rather than deferred; the Flights day separators, grouped by Paris calendar day and shaped by the Paris-day formatter rather than a direct date call, and explicitly not sticky; and Health's registry table recorded as the stacked-cell exception's **second measured consumer**, with its own numbers, leaving the do-not-generalise warning verbatim. Updated quick task 260913-cz6: Health's battery readings table measured against the same cause at 390px behind a closed `<details>`, the stacked treatment measured and REJECTED on its own numbers, the floor-release remedy (`table.data-table--readings { min-width: 0 }`) taken instead — the stacked-cell exception's consumer count deliberately stays at **two** — plus the new general lesson that a scrolling WRAPPER is invisible to `document.documentElement.scrollWidth` and must be measured against its own `clientWidth` with every disclosure forced open. Updated quick task 260913-dgh: a FOURTH site of the same content-sized-track cause, this one outside a table — Home's `.recent-flight` grid row, whose `minmax(0, 1fr)` callsign track was starved to 10.9px (FR) / 18.6px (EN) for 57.8px of content at 320px and 50.9px (FR) at 360px by a rigid `auto` time track; a container query was measured, worked, and was rejected because its threshold cannot track an unbounded relative-age string (the same defect reaches the 1280px desktop row once the age grows), and a wrapping flex line was taken as a THIRD distinct remedy — plus the new general lesson that a box can be wrong against its own CONTENT while correct against every container it sits in, so it must be measured with a `Range` over its own contents rather than against a parent or against integer-rounded `scrollWidth`. Updated Phase 23 (23-companion-dynamism, D7/D14, CFG-34/CFG-37, 23-03/23-08/23-11): the Flights list joining the shared refresh loop with both renderings as swap regions, identity-before-position as a transferable rule, the one-shot arrival wash and why its known set must never start empty, the detail row's `grid-template-rows` height with its `min-height: 0` and its `.flight-rows-live` scope and the written argument against `allow-discrete`, the enumeration of every relative age that deliberately stays static (with a correction of record: the unconverted site is the DESKTOP When cell, not the phone card), and sticky day headers **declined** on rendered evidence with their revisit condition — every value re-read from `companion/pages/history_page.py`, `companion/pages/config_page.py`, `companion/pages/health_page.py` and `companion/static/style.css` at execution time. **Updated Phase 24 (24-companion-dynamism-ii-drawn, D21/D8/D13/D20/D4, CFG-39..CFG-45) — recorded here at Phase 25's close, because Phase 24 added this file's largest entry (the whole drawing contract) and its four measurement conventions without extending this line, which is the same class of omission as a stale number and is corrected in place rather than silently:** `companion/draw.py` as the one geometry vocabulary, the two coordinate schemes and the rule for choosing, the nested-viewBox escape hatch, the class-and-token paint idiom with its four machine-enforced anti-patterns, the `url(` ban that rules out gradients, the one-value rule, the one battery estimator's two allow-listed homes, and the four conventions (assert the floor; mutate every property; clear `__pycache__`; stage before you mutate). Updated Phase 25 (25-companion-dynamism-iii-controls, D18/D19, CFG-49/CFG-51, 25-01/25-05/25-07/25-08): the estimator's second arithmetic and **the battery honesty rule made structural** (five named states, a number only from `falling`, two observation floors pinned from the opposite extreme, the absolute sentence rendered outside every script-writable element, and Phase 24's own forbidding paragraph corrected in place rather than deleted); the **framing-preview** pattern with the recorded ground for having no client crop and the three-way proof that dropped and picked bytes are one act; and six further measurement conventions on top of Phase 24's four — the vacuity shape table, the never-sample-at-a-guessed-instant rule as a three-phase finding, the synthetic-event finding and the trusted-drag instrument that answers it, the guard-tripping function NAME, the mutation-suite null control, and stage-before-you-mutate restated because it cost a second full re-write.
Source file available in: `sources/003-history-table-density.html` (historical artifact, byte-identical, not current-reality documentation).
