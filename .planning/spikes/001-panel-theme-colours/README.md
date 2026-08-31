---
spike: 001
name: panel-theme-colours
type: comparison
validates: "Given the real render pipeline (fonts, palette, layout, dither), when the panel background colour and the text-legibility technique are varied, then the developer can pick a direction by eye before any plan is written"
verdict: VALIDATED
related: []
tags: [render, theme, palette, legibility, e-ink]
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
