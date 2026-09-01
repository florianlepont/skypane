---
spike: 003
name: diagonal-band-theme
type: comparison
validates: |
  Given a diagonal band drawn behind the aircraft illustration (as one new
  dedicated theme, existing 11 themes untouched), when several band
  colours/treatments and geometries are rendered through the real
  build_canvas() pipeline, then at least one reads well on a 6-colour
  e-ink panel, passes the real _assert_legal_palette() background-
  dominance guard rail, and does not collide with any text.
verdict: PENDING - round 2 (precise reference reproduction) presented, 2 findings need a decision (tag collision, black+black-ink)
related: ["001-panel-theme-colours", "002-small-labels-and-white-rhythm"]
tags: [render, theme, diagonal-band, layout, e-ink, palette-guard-rail]
---

# Spike 003: Diagonal decorative band theme

Developer shared a travel-poster-style aviation illustration (cream
background, muted grey-blue diagonal stripe behind the fuselage, italic
route subtitles) as inspiration, then explicitly scoped it down once told
the real Spectra 6 hardware has only 6 fixed inks: drop the textured
cream background entirely, keep the diagonal band as the one genuinely
new element, apply no colour treatment to the aircraft illustrations.
Ships as one new dedicated theme (band drawn behind the illustration),
existing 11 themes untouched.

## What This Validates

Given a White base field with a diagonal band drawn behind the
illustration, when several band colour/treatment/geometry candidates are
rendered through the real production pipeline, then at least one is
visually close to the reference's intent, passes
`render._assert_legal_palette()`'s real background-dominance check
(called directly, not reimplemented), and doesn't collide with any text
role.

## Research

No external research needed - this is a new drawing primitive built from
existing project techniques (`ImageDraw.polygon()` for the band shape,
`dither.dithered_state_background()`'s toward-White blend reused for a
"soft" band treatment). The real hardware constraint (6 fixed Spectra 6
inks, `server/panel_format.py`'s `PALETTE_RGB`) rules out the reference's
literal cream/muted-grey-blue colours - every candidate here uses only
`IDX_BLACK/WHITE/YELLOW/RED/BLUE/GREEN`, flat or dithered toward white.

## How to Run

```bash
server/.venv/bin/python3 .planning/spikes/003-diagonal-band-theme/explore_band.py
server/.venv/bin/python3 .planning/spikes/003-diagonal-band-theme/make_contact_sheet.py
```

## What to Expect

`renders/contact_sheet_band_candidates.png` stacks all 7 candidates for
side-by-side comparison. Individual `renders/{label}-departing.png` files
give full-resolution single-candidate views. Candidates:

- `blue-flat-shallow` / `blue-dithered-shallow` - same geometry (top at
  62% width, bottom at 28%, 22% wide), pure Blue vs. Blue dithered
  toward White (softer, closer to the reference's muted tone).
- `black-flat-shallow` - same geometry, pure Black.
- `green-dithered-shallow` - same geometry, Green dithered toward White.
- `blue-flat-narrow` / `blue-flat-wide` - same centreline, band width
  13%/32% instead of 22%.
- `blue-flat-steep` - a steeper diagonal (58%→42% instead of 62%→28%).

## Investigation Trail

1. Implemented `draw_diagonal_band()` as an `ImageDraw.polygon()`
   parallelogram, monkeypatching `panel_format.new_canvas()` so the band
   draws immediately after the flat White fill and before
   `build_canvas()`'s real pipeline draws labels/text/illustration on
   top - the aircraft occludes the band naturally, matching the
   developer's "band behind the illustration" requirement, with zero
   changes to `server/plane/render.py`.
2. Ran `render._assert_legal_palette()` (the real guard rail, not a
   reimplementation) against every candidate: **all 7 pass** - the band
   never outweighs the flat White field's pixel count at any width
   tested here (13-32% of canvas width).
3. **Found and fixed a real bug in this spike's own script**, not in the
   production render path: the monkeypatch was re-derived from
   `pf.new_canvas`'s *current* value inside the candidate loop instead of
   a value captured once before any patching. Each candidate's patch
   ended up wrapping the *previous* candidate's patch rather than the
   true original, so a later, differently-shaped band (e.g. the 13%-wide
   `blue-flat-narrow`, following four 22%-wide candidates) never fully
   covered the wider band(s) drawn underneath it by the accumulated
   chain - visible as a stippled colour fringe outside the new band's
   edges. Confirmed via an isolated single-candidate reproduction
   (`new_canvas()` called exactly once, colour counts consistent with
   ordinary illustration detail - real aircraft nav-light colours, not a
   leak) versus the full 7-candidate loop (fringe visible, matching
   exactly where a narrower/differently-angled candidate followed a
   wider one). Fixed by capturing the true original `new_canvas` once,
   outside the loop; every candidate's patch wraps that, never the
   previous candidate's patch. Re-ran clean - no fringe on any candidate.
4. **Found a real legibility collision, not a script bug**: on
   `black-flat-shallow`, the main text block's ink colour (`IDX_BLACK`,
   White theme's declared ink) is drawn directly over the band where
   they overlap, and both are the same colour - "AF1234 to New York"
   partially disappears into the band, only "...ew York" stays visible
   against the White field beyond the band's edge. This is real and
   would need addressing before a black band variant could ship (e.g.
   route the ink colour through the band's own colour, or restrict which
   band colours are offered).
5. Zoomed both edges of `blue-flat-wide` at full resolution to rule out
   the same fringe pattern at the widest geometry tested - clean, hard
   diagonal edges, no artefact.

## Results

**Round 1 - band colour/geometry exploration: developer feedback
received.** Chose 5 band colours to carry forward: green light
(dithered), blue light (dithered), red (flat), black (flat), blue
(flat) - and asked for the diagonal's exact shape and the reference's
text layout/font to be reproduced precisely, not approximated.

**Round 2 - precise reproduction (`explore_full_composition.py`).**
Measured the reference image
(`~/Downloads/d8b790c7-1316-4121-b23c-749d9ada7491.png`, 1023x1537)
directly via per-row pixel scanning + linear regression on each edge
independently, rather than eyeballing it:

- **The band is a TRAPEZOID, not a parallelogram** - this round 1 missed
  entirely. Left edge: `x = -0.338*y + 595.2`. Right edge:
  `x = -0.250*y + 871.9`. As fractions: top edge spans 58.2%-85.2% of
  canvas width (27% wide), bottom edge spans 7.4%-47.7% (40.3% wide) -
  the band widens noticeably going down, it doesn't stay a constant
  width like every round-1 candidate assumed.
- **Text hierarchy measured the same way**: a big bold flight number
  ("AF1006"), left-anchored at the same x as the top-left state label,
  starting ~49% down the canvas; a thin 1-2px dash rule directly under
  both the state label and the flight number; a tracked small-caps route
  line ("PARIS — NEW YORK") reusing the exact `draw_tracked_text()`/
  `LABEL_TRACKING_PX` technique already shipped for the top labels
  (quick task 260831-njw) on a new text role; the airline name in
  italic, smaller, last.
- **PT Serif Italic is not vendored** - only `PTSerif-Regular.ttf`/
  `PTSerif-Bold.ttf` exist in `server/assets/fonts/`. This round renders
  the airline line in Regular as an explicit placeholder, not a decision
  - italic would need vendoring (new font file, licence text, sha256,
  pinned commit, matching `VENDOR.md`'s existing discipline) before it
  could ship as designed.
- Implemented by monkeypatching `panel_format.new_canvas()` (band, same
  technique as round 1) and `render.draw_main_text_block()` (new text
  hierarchy, left-anchored instead of the current centred block) for
  the duration of the script only - `server/plane/render.py` untouched.
- **All 5 requested colours pass `render._assert_legal_palette()`** -
  the real guard rail, called directly.

**Two real findings from the precise reproduction, both worth a decision
before this goes further:**

1. **The band's top-right corner sits close enough to the runway tag
   ("ORY · RWY 3") to visibly cross into its first character or two, at
   every band colour** - confirmed by direct pixel comparison of the
   black and red variants: both show the identical geometric overlap
   (the band edge crosses through the "O" of "ORY"), it's just far more
   visually jarring on black (see finding 2). The reference image's own
   measured tag position (84.3% width) sits only ~1 percentage point
   left of the band's measured top-right edge (85.2%) - close enough
   that this project's own font metrics/tracking (different font,
   different letter-spacing than whatever produced the reference) push
   a near-miss into a real, visible collision.
2. **Black band + black ink text is a genuine, separate bug**: the White
   theme's ink colour is always `IDX_BLACK`, so wherever the band
   crosses behind text, a black band makes that text invisible - "PARIS
   — NEW YORK" loses its final "K" on `ref-band-black-flat`, on top of
   finding 1's tag collision. Red/blue/green bands keep black text
   legible (real contrast), so this is specific to the black candidate,
   not the geometry.

Both are fixable (nudge the band's top-right edge left of the tag's
measured position; either exclude black from the shipped set or resolve
text ink per-band), but need the developer's call before implementation
- see the checkpoint presented alongside this file.
