---
spike: 001
name: panel-theme-colours
type: comparison
validates: "Given the real render pipeline (fonts, palette, layout, dither), when the panel background colour and the text-legibility technique are varied, then the developer can pick a direction by eye before any plan is written"
verdict: VALIDATED
related: []
tags: [render, theme, palette, legibility, e-ink, typography]
---

# Spike 001: Panel background colour + text-legibility technique

## What This Validates

Given `server/plane/render.py`'s real drawing pipeline (PT Serif fonts,
the 6-colour Spectra 6 palette, dithered state backgrounds, illustration
compositing), when the background colour and the technique used to keep
text legible over that colour are varied, then produce enough real
rendered comparisons for the developer to react to and pick a direction —
before any ROADMAP phase or plan is written.

Triggered by developer feedback (branch `claude/amelioration-rendu-tableau-bcd0ce`):
after seeing the current Blue/Green panel renders, the developer wants
(1) a plain white background as the new default, (2) Blue/Green kept as
optional selectable themes, and (3) the current solid highlighted
backing-plate rectangle behind every text run removed — they find it
ugly — replaced by some other legibility technique, and to see real
comparisons before committing to any of this.

## Research

No external docs needed — this is entirely internal to the existing
render pipeline. Read `server/plane/render.py`, `server/device_config.py`,
`server/panel_format.py`, `server/plane/dither.py` directly.

Key finding while reading: the current backing-plate rectangle
(`_paint_text_backing()`) was added in Phase 7 (commit `134b9f8`) to fix a
*real* on-glass legibility bug — once the flat state background became a
dithered lighten-toward-White blend, the scattered White speckle visibly
hurt legibility behind white text. So "just remove it" (spike variant
`none`) was expected to reproduce that regression, and did — see Results.

Only 6 colours exist on the real Spectra 6 panel
(`panel_format.PALETTE_RGB`: black, white, yellow, red, blue, green) — any
new background candidate must be one of those 6 (or a dithered blend
toward white of one of them), not an arbitrary RGB value.

## How to Run

```bash
source server/.venv/bin/activate
python .planning/spikes/001-panel-theme-colours/explore.py
```

Writes 12 full-panel PNGs to `renders/`. The script never modifies any
repo file — it monkeypatches `device_config.THEMES` (adds a throwaway
`"white"` entry) and `render._paint_text_backing()` /
`ImageDraw.ImageDraw.text()` only within its own process, restoring the
originals after each variant. All renders reuse the real
`build_canvas()` pipeline, so illustration placement, fonts, and layout
are pixel-faithful to what the device would actually produce (modulo the
`--preview` flag's own documented caveat: these are nominal render-
internal RGB triples, not colour-accurate against real Spectra 6 ink).

## What to Expect

- `01/02-white-*-plate.png` — the white-background candidate (both
  states share one white field; state is distinguished by the
  DEPARTING/ARRIVING label text alone, as today).
- `10/11-sky-*-plate-BASELINE.png` — today's shipped Blue/Green with the
  solid backing plate, for reference.
- `20/21-sky-*-none.png` — backing plate removed, nothing added back.
- `30/31-sky-*-outline-w3.png`, `32/33-*-outline-w1/w2.png`,
  `34/35-*-outline-w2-FULL.png` — text outline/stroke instead of a box,
  three stroke widths.
- `40/41-sky-*-shadow.png` — offset drop-shadow instead of a box.
- `crops/compare2_top_tag.png`, `crops/compare2_prev_caption.png` — 3x
  zoomed side-by-side crops of the two smallest/hardest text runs on the
  panel (the top-right runway tag and the previous-flight card's
  secondary caption, 16px PT Serif) across all six techniques.

## Investigation Trail

1. Registered a throwaway `"white"` theme (`departing_index`/
   `arriving_index` = `IDX_WHITE`, `ink_index` = `IDX_BLACK`) and rendered
   it with the existing (unmodified) backing-plate technique. Confirmed
   clean and legible with no special treatment needed — expected, since
   flat black-on-white has no dithered speckle to fight.
2. Rendered the current Blue/Green theme with the backing plate removed
   and nothing substituted (`none`). Confirmed the Phase 7 regression it
   was built to fix: the smallest caption ("Vueling Airlines", 16px)
   becomes genuinely hard to read against the dithered speckle; the
   top-right runway tag loses most of its contrast.
3. Tried a text outline (PIL `stroke_width`/`stroke_fill`, black stroke
   around the existing white ink) at width 3 — legible and box-free, but
   at the smallest caption size the strokes of adjacent letters touch and
   the text reads as a slightly blotchy mass rather than crisp letterforms.
4. Iterated stroke width down to 2 and 1 to find the point where it stays
   crisp at 16px. Width 1 is too thin — the dithered speckle bleeds into
   the outline itself, extra noisy. Width 2 is the sweet spot: solid
   enough to separate cleanly from the dithered field at every font size
   on the panel (16px through 72px), without clumping into a blob.
5. Tried an offset drop-shadow (black copy of the glyphs offset 3px
   down-right, real ink drawn on top) as a second box-free alternative.
   At the smallest caption size the shadow overlaps the main glyphs
   enough to read as smudged/doubled rather than shadowed — reads worse
   than outline at width 2 in the zoomed crop comparison.
6. Rendered full-panel width-2-outline versions of both states
   (`34/35-*-FULL.png`) to sanity-check the technique at normal viewing
   scale, not just zoomed crops — reads clean and unobtrusive at full
   size, close to the backing-plate baseline's legibility without the
   boxed look, but the developer's reaction to the full outline/shadow
   comparison set was that neither looked attractive enough ("pas très
   beau"), prompting a different axis entirely: font weight.
7. Read `server/assets/fonts/VENDOR.md`'s project history: Zilla Slab
   Bold/SemiBold was Phase 3's *original* typography choice, picked
   specifically because thick slab-serif strokes resist e-ink
   hairline-legibility loss; it was later replaced by PT Serif purely
   for looks, and the developer explicitly accepted PT Serif **Regular**
   (thin strokes) knowing the risk (D-27) — VENDOR.md's own documented
   contingency, never before exercised, is to fall back to the
   already-vendored `PTSerif-Bold.ttf`.
8. Rendered the sky theme with the backing plate removed and **no**
   outline/shadow trick, just every text role switched from
   `PTSerif-Regular.ttf` to `PTSerif-Bold.ttf` (`50/51-*-PTBOLD.png`),
   and, for comparison, to `ZillaSlab-SemiBold.ttf`/`ZillaSlab-Bold.ttf`
   (`60-63-*-ZILLA-*.png`). All three read cleanly at every text size on
   the panel, including the 16px caption, with zero visual treatment
   beyond the heavier stroke weight — see `crops/compare3_*.png`.
9. Developer picked **PT Serif Bold** over Zilla Slab (keeps the existing
   typographic family/feel rather than introducing a visually distinct
   slab-serif) and confirmed it should become the single font for every
   theme, including the White default — not just the coloured ones that
   originally needed the legibility fix. Rendered final confirmation
   passes on both White (`70/71-*-FINAL.png`) and Sky/arriving
   (`72-*-FINAL.png`) with PT Serif Bold + no backing plate, both
   states, to check the decision holds project-wide, not just on the
   departing/Blue case already reviewed. Confirmed clean.

## Results

**Verdict: VALIDATED.** No production code changed — this remains a
spike. Confirmed direction, ready to hand to a real plan:

- **White** becomes the new default theme (`DEFAULT_THEME_ID`); DEPARTING
  vs. ARRIVING is distinguished by label text only when the background is
  white for both states.
- **Blue/Green ("sky")** stays available as an optional, user-selectable
  theme via the existing CFG-01 picker.
- **The solid backing-plate rectangle (`_paint_text_backing()`) is
  removed entirely, for every theme.**
- **Every text role switches from `PTSerif-Regular.ttf` to
  `PTSerif-Bold.ttf`, universally (not just on coloured themes)** — this
  is what actually replaces the backing plate's legibility job. No
  outline, no shadow, no box of any kind.
- Outline (tried at 1/2/3px stroke width) and drop-shadow were both
  explored and read as *legible* in the zoomed crops, but were explicitly
  rejected by the developer on visual grounds before the font-weight
  option was tried — recorded here so a future re-read of this spike
  doesn't re-litigate them without new information.
- Not yet tried: additional background colour candidates beyond
  White/Blue/Green (Yellow/Red are the only other palette entries, and
  are currently used for the battery-low/source-fault icons, not
  per-state backgrounds) — open for the developer to request if wanted.
- **Real Spectra 6 glass has not confirmed any of this.** Every judgment
  above is off on-screen preview PNGs. Phase 7's own history
  (`hardware/BRINGUP-LOG.md`) already shows monitor-preview colour and
  legibility calls landing differently on real ink twice (Blue/Green
  hue, and the backing-plate fix itself) — an on-glass re-check belongs
  in whatever plan implements this.

## Round 2 — flight-identifier text content and previous-card sizing

Follow-up requested by the developer in the same conversation, after
Round 1's colour/font direction was confirmed: explore the remaining
palette colours as flat fills (`renders/colours/`, `explore_colours.py`),
then a set of text-content questions about the "AFR1234"-style callsign
shown on both flight cards, plus a reported alignment/sizing issue on the
previous-flight card.

### Investigation Trail (continued)

10. Rendered all 6 Spectra 6 palette colours (Black/White/Yellow/Red/
    Blue/Green) as flat, non-dithered full-panel backgrounds with the
    Round 1 fix (PT Serif Bold, no backing plate) —
    `renders/colours/*-flat-BOLD-noplate.png` + `contact_sheet.png`.
    Flagged, not silently glossed over: dithering was added in Phase 7
    specifically because the flat Blue/Green fill looked too dark/
    saturated on real glass at full coverage, so these flat renders may
    reproduce that same issue on real ink — never confirmed either way
    by the developer in this session (still open, see Requirements).
11. Developer asked whether the displayed callsign ("AFR1234") could
    instead show the real published flight number. Traced the actual
    data flow (`server/plane/enrich.py`, `server/fixtures/adsbdb_hit_*.
    json`): the adsbdb response already carries a `callsign_iata` field
    (IATA-formatted, e.g. "AF1234") that `_parse_route()` fetches and
    discards. Read `.planning/notes/adsbdb-callsign-lookup-legacy-vs-
    rotating.md`: for legacy carriers this IATA field genuinely equals
    the real flight number (their ICAO callsign already is one);  for
    rotating-callsign carriers (Transavia et al.) neither callsign form
    reliably corresponds to one, a structural limitation of any
    callsign-keyed source, not a coverage gap — a real fix needs a live
    schedule/FIDS API instead, out of scope for this round.
12. Developer's decision, twice narrowed over the conversation: never
    display the raw ICAO callsign, anywhere. First pass showed a
    fallback ladder that still fell back to the bare callsign when no
    IATA id existed (`80/81-*-nocallsign.png`, `90-*-iata-flightnum.
    png`) — developer pushed back and asked for it removed even in the
    fallback cases, landing on the 4-tier ladder recorded in
    `MANIFEST.md`'s Round 2 Requirements (IATA+city → city-only →
    airline-name-only with line 1 omitted → "Departing"/"Arriving" +
    "Route unavailable"). Rendered and confirmed each tier separately:
    `91-*` (IATA id + type present), `92-*` (full miss), `93-*`/`94-*`
    (airline-only, line 1 omitted, both the previous-card and main-card
    slots).
13. Separately, developer noticed the aircraft type label
    (`_TYPE_DISPLAY_LABELS`) was missing from these mockups and asked if
    that was intentional — it was not: the throwaway preview fixture in
    this spike's ad hoc scripts simply never set `aircraft_type` on the
    flight dict. `_flight_line2_text()` itself was never touched;
    re-rendered with `aircraft_type` set to confirm (`91-*.png` onward
    all show "Air France · A320" correctly).
14. Developer reported the previous-flight card's text looked shifted
    right of the aircraft it belongs to. Rather than eyeball it,
    instrumented `draw_previous_text_block()` to print the exact pixel
    values: `prev_placement.content[2]` (the illustration's measured
    opaque-pixel right edge) and the rendered text's own `textbbox`
    right edge were IDENTICAL (1091px, delta 0) for the reference
    Vueling fixture — confirmed mathematically exact, not a bug.
    Rendered a vertical guide line at that exact x-coordinate
    (`95-alignment-guide-and-bigger-subline.png`) so the developer could
    judge against ground truth rather than a screenshot. Working theory,
    stated as a theory: the aircraft's rightmost pixel sits on a thin,
    raked tail-fin tip, not the visual mass of the fuselage/tail body —
    the eye anchors on the latter, so the mathematically-exact version
    reads as shifted right. Developer confirmed the effect was still
    perceptible after seeing the guide and asked for an intentional
    optical correction rather than the strict measurement.
15. Iterated the optical-correction offset live: 15px left
    (`96-prev-text-nudged-left-15px.png`) → developer asked for "a tiny
    bit more" → 20px left (`97-prev-text-nudged-left-20px.png`) →
    confirmed. Applied to both of the previous card's lines (keeps them
    both right-aligned to the same shifted edge); the main card's
    centre-anchored text was not touched — centred text doesn't exhibit
    this failure mode the same way, since it isn't pinned to one raked
    edge, so no equivalent nudge was requested or applied there.
16. Same pass bumped `PREVIOUS_LINE2_FONT` from 16px to 20px per the
    developer's request ("légèrement augmenter la taille de la
    sous-ligne") — confirmed alongside the alignment nudge in the same
    renders (95/96/97), never shown in isolation since the two changes
    were requested back-to-back and are visually independent (one is
    font size, the other is horizontal position).

### Round 2 Results

**Confirmed, added to `MANIFEST.md`'s Requirements:**
- Raw ICAO callsign never displayed; `callsign_iata` (currently
  discarded by `enrich._parse_route()`) becomes the displayed flight
  identifier when present, with a 4-tier content fallback ladder that
  never re-introduces the raw callsign at any tier.
- `PREVIOUS_LINE2_FONT`: 16px → 20px.
- Previous card's text block: 20px intentional left offset from
  `prev_placement.content[2]`, an optical correction on top of the
  already-correct mathematical anchor — not a change to which edge is
  measured.

**Still open:**
- The Black/Yellow/Red flat-background candidates were shown but never
  reacted to.
- Whether the 20px optical nudge (tuned against one illustration file)
  holds up visually across the other ~42 vendored illustration files,
  whose tail shapes/rake angles vary.
