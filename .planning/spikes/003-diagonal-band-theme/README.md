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
verdict: PENDING - round 15 reverts to the below-illustration position and fixes a real per-line centring bug (three lines now share one x), awaiting developer reaction
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

**Round 3 - both findings fixed, developer's own proposed solutions.**

1. **Band shifted left by `BAND_SHIFT_FRAC = -0.09`** (a pure translation
   of the measured trapezoid, same width/shape, not a re-derivation).
   Our real render's runway tag starts at `x_frac=0.8117`
   (`render._tracked_text_width()`, measured directly - not the
   reference's own 0.8117, different font/tracking); the shifted band's
   top-right edge now sits at `0.762`, a genuine ~5-point margin below
   the tag. Confirmed clear on all 5 candidates.
2. **Main text block (flight number/dash/route/airline) moved from below
   the illustration to the gap above it** - developer's own proposed
   fix, not a fallback. The block is now bottom-anchored just above
   `main_placement.content[1]` (the illustration's opaque top edge) via
   a measure-then-place pass (each line's height computed with a dry-run
   `textbbox()` at (0,0) before choosing where the block's top goes) -
   the same drawing code runs top-down from that computed `top_y`, so no
   line-height math is duplicated between the measure and draw passes.
   At the height range this puts the block in (roughly 9-28% of canvas
   height), the shifted band sits at 55-73% width, comfortably clear of
   this left-anchored block's typical extent (~5-30% width).

**Both real findings are now resolved in every one of the 5 requested
candidates** - no tag collision, no band/ink-colour text collision, on
blue light (dithered), green light (dithered), red (flat), black (flat),
and blue (flat). `renders/contact_sheet_full_composition.png` is the
current, corrected comparison set. The developer has not yet reacted to
this round.

**Round 4 - content-ladder consistency fix (developer catch).** Round 3's
text hierarchy invented content that doesn't exist in the shipped
project: a `"{origin} — {destination}"` route-pair line (production only
ever shows the ONE city relevant to the current state, per
`enrich.city_for_state()`) and a bare airline name (dropping the
aircraft type `_flight_line2_text()` always appends). Developer caught
this as "un mix entre le vrai projet et la photo" - real bug, not a
style choice. Fixed by calling `render._flight_line1_text()`/
`_flight_line2_text()` **verbatim** (the real, unmodified functions -
same data, same never-shows-the-raw-callsign guarantee, same four-tier
fallback) and only choosing how to SPLIT the real tier-1 string across
the big-number/tracked-route-line visual roles - never re-deriving or
inventing what those functions return. Tier 3 (line 1 omitted) and tier
4 ("Unknown flight") both collapse gracefully to a single line with no
number, matching production's own promotion behaviour. Verified: tier1
(number+route+airline·type), and a live tier-2 check
(`callsign_iata=None` - no number line, just "TO NEW YORK" tracked, no
crash) both render correctly.

**PT Serif Italic - decided, not open.** Developer's call: stay Regular
project-wide for the e-ink screen - no italic vendoring. Matches Phase
8's own on-glass finding that heavier weight already reads "agressif" on
this panel (D-06); italic was reference-image styling, not a real need.
`ROUTE_LINE_FONT` changed from Bold to Regular in this round too, for
the same reason.

**Round 5 - text-to-aircraft distance fix (developer catch: "très
écarté").** The above-illustration anchor (`main_placement.content[1]`,
the topmost technically-opaque pixel) is dominated by the tail fin's
tip on a swept-tail silhouette - measured directly on the Air France
file: the tail tip sits only 8px into the resized illustration, but the
fuselage doesn't reach 40% of the illustration's own max row width until
169px down. Anchoring 32px above `content[1]` is mathematically tight to
a real pixel, but that pixel is a nearly-invisible sliver of tail, so the
text reads as stranded near the top labels instead of "belonging to" the
aircraft. New `_fuselage_visual_top_y()` re-selects and re-resizes the
same illustration file `_build_active_canvas()` already chose (same
functions, same parameters - never changes which file is drawn), reads
its alpha-channel row-width profile, and anchors to the first row that
reaches 40% of the illustration's own max width instead of the first
opaque row at all. Text now sits directly against the fuselage/livery on
every candidate, adapting per-file the same way `MAIN_TEXT_GAP_PX`
already adapts to nose/wheel position on the bottom edge - this is the
same category of fix, just for the top edge, which no prior phase needed
before text moved above the illustration.

**Round 6 - previous card gets the same three-level hierarchy.**
Developer: "je ne comprends pas la différence de traitement entre
l'avion principal et l'avion secondaire" - the previous (bottom-right)
card still had the old flat two-line format while the main card had
been restructured into number/dash/tracked-route/airline·type. New
`patched_draw_previous_text_block()` mirrors the main card's tier-split
logic exactly (same real-content-ladder reuse from round 4) but
right-aligned and scaled to the previous card's own long-established
~57% scale (`PREV_NUMBER_FONT`=32px vs. the main card's 56px). Position
stays BELOW the previous illustration, unchanged from production - unlike
the main card, the shifted band never reaches this far right at this
card's height (checked: band's rightmost extent here is ~45% width,
this card's text sits at ~89% width), so there's no collision to dodge
and no reason to also flip it above its own aircraft.

**Round 7 - merge the top labels, free the band to shift right
(developer's new proposal).** Instead of shifting the band away from the
runway tag (round 3's fix), the developer proposed removing the
collision's cause entirely: merge the top-right tag into the top-left
state label - "DEPARTING FROM ORY · RWY 3" / "ARRIVING TO ORY · RWY 3" -
so nothing occupies the top-right corner and the band can shift right
instead of left. `BAND_SHIFT_FRAC` flipped from `-0.09` to `+0.08` (past
the reference's own as-measured, unshifted position). New
`patched_draw_top_labels()` reuses `runway_tag_text()`/
`STATE_LABEL_TEXT`/`draw_tracked_text()`/`LABEL_TRACKING_PX` verbatim -
only the two separate strings become one, drawn as a single tracked run,
no right-side draw call at all. Confirmed the merged string stays
comfortably inside the canvas at both states (departing: 446px wide,
ending at x=510 vs. the 1136px safe-box edge; arriving: 383px). No
information lost - the developer's explicit call from earlier this
session (D-13 precedent: no info drops silently) is upheld, "RWY 3"
survives merged in, not removed.

**Round 8 - main card's text moved back below the aircraft.** Now that
round 7's merged top label freed the band to shift right instead of
left, the original reason to move the main card's text above its
aircraft (round 2's band-collision fix) no longer applies. Checked the
band's position at the below-illustration text block's height range
(~50-55% canvas height): it now spans ~39-73% width, clear of this
left-anchored block's ~5-30% extent. Reverted to the real
`draw_main_text_block()`'s own anchor (`main_placement.content[3] +
MAIN_TEXT_GAP_PX`) - simpler than round 5's fuselage-visual-top
machinery too, since the bottom edge never had the swept-tail-tip
problem the top edge did (this is the same anchor the shipped production
function has always used). Confirmed clear on both the blue-dithered and
black-flat candidates - the two extremes (softest and hardest edge
against the band) - with no collision on either.

**Round 9 - un-merge the top labels, nose-align the main text, smaller
leftward shift.** Developer: bring RWY 3 back to its own top-right tag,
shift the band left again (but less than round 3's -0.09), and align the
main text block's left edge to the aircraft's nose instead of the canvas
margin. Un-merging is a pure revert (stopped patching
`draw_top_labels()`, the real shipped function runs as-is). Nose
alignment uses `main_placement.content[0]` (the nose's own leftmost
opaque pixel) - safe to reuse directly here, unlike the vertical case:
a side-view nose is a filled, rounded shape, not a thin spike, so no
separate width-profile analysis was needed. `BAND_SHIFT_FRAC` set to
`-0.07` (top-right edge at 0.7823, a ~2.9pt margin below the tag's
0.8117 start).

**Found and fixed: round 8+9 together reopened the band collision.**
Verified numerically before showing anything: with the main text block
still below the illustration (round 8) AND now nose-aligned (round 9),
the band's left edge at that height (~52% canvas height, ~24.5% width)
sits well INSIDE the text block's own right edge (~33% width) - a real
~8pt overlap, confirmed visually on `black-flat` (text genuinely cut:
"AF123" without its "4", "TO NEW Y" without "ORK"). There is no single
`BAND_SHIFT_FRAC` that clears both the restored tag (wants the band
pushed left) and the below-position nose-aligned text (wants it pushed
right) at once - the trapezoid's own shape makes the two constraints
mutually exclusive at that text position. Moved the main block back
above the illustration (round 5's `_fuselage_visual_top_y()` anchor,
not round 8's below-anchor) - verified numerically this clears both
constraints (band's left edge stays 38-46% across that height range,
clear of the nose-aligned block's ~35% max extent), then confirmed
visually on both `blue-dithered` and `black-flat`. Flagged explicitly
rather than silently reverting the developer's own round-8 request.

**Round 11 - developer's correction: split the tag, not merge it whole.**
Round 9 restored the full "ORY · RWY 3" tag and had to move the main
text back above the aircraft to avoid the collision it reopened. The
developer's actual intent was different: keep "ORY" merged into the
top-left label ("DEPARTING FROM ORY" / "ARRIVING TO ORY"), but keep a
SHORTER separate tag on the right - "RWY 3" alone. Measured: "RWY 3"
alone starts at `x_frac=0.8817` vs. the full tag's `0.8117` - a 7-point
gain. With that gain, `BAND_SHIFT_FRAC=0.0` (the reference's own
unshifted, as-measured position, no shift needed at all) clears BOTH the
shorter tag (2.9pt margin) AND the below-illustration, nose-aligned main
text (5pt margin, checked against the precisely measured text-block
right edge of 0.265 - not the earlier rounds' rough 0.33 guess) at once.
Main text moved back below the illustration (round 11 supersedes round
10's above-position workaround, which is no longer needed).
`patched_draw_top_labels()` now draws two separate tracked runs -
`full_tag.partition(" · ")` splits the real `runway_tag_text()` output
into the airport code (goes left) and the runway part (stays right,
still its own `TOP_TAG_FONT`-sized, right-aligned run) - not a hardcoded
re-derivation of either string. Confirmed clean on `black-flat` (the
tightest case throughout this whole exploration).

**Round 12 - text centred INSIDE the band, not beside it (developer's new
idea).** Instead of the text sitting to the side of the diagonal (round
9-11's nose-aligned position, which happens to land outside the band at
this geometry), the developer proposed centring it directly inside the
band, below the aircraft. New `_band_center_x(canvas_y, w)` computes the
band's own horizontal centre at a given y (same linear interpolation the
collision checks in earlier rounds already used), and every line of the
main text block is now centre-anchored there instead of left-anchored
at the nose.

**Real finding, not a corner case: black band + black ink is now a
total failure, not a tight-margin collision.** White theme's ink is
always `IDX_BLACK` - with the text sitting directly ON the band instead
of beside it, `black-flat` renders the entire block (`AF1234`/`TO NEW
YORK`/`Air France · A320`) completely invisible, not just clipped at an
edge. Checked all 5 requested candidates: `blue-dithered`, `blue-flat`,
`green-dithered`, and `red-flat` all keep the text legible (their inks
are dark/saturated but not literally black, so black text still has
enough luminance contrast) - only `black-flat` fails, and it fails
completely. This needs a developer decision before it can ship: exclude
black from this "text-inside-the-band" treatment specifically (keep it
available for the band colour, just not paired with this text
placement), or resolve it some other way (e.g. a different ink for that
one candidate) - not something to silently paper over.

**Round 13 - white ink for the black band's text.** Developer: "il suffit
d'écrire en blanc pour le noir." New `_CURRENT_BAND_IDX` (set per
candidate in `main()`) lets `patched_draw_main_text_block()` use the
band's own contrast colour instead of the theme's global `ink_idx` -
`IDX_WHITE` when the band is black, unchanged (`IDX_BLACK`, already
correct) for every other candidate. `black-flat` now reads perfectly:
white "AF1234 / TO NEW YORK / Air France · A320" fully legible against
the black band. Confirmed `_assert_legal_palette()` still passes (White
stays dominant even with the added white-ink text on black).

**Round 14 - canvas-centre experiment, found and flagged a collision
before presenting it as done.** Developer wanted the main text block
vertically centred - asked which reference frame, developer's answer:
"centre de l'écran" (`HEIGHT/2 = 800`, literal canvas centre). Checked
numerically before rendering: the block's own height (~150px) means its
top would land at y≈725, well above the aircraft's own bottom edge
(y=793) - rendered it anyway to confirm the severity, and the collision
was real and visible ("AF1234" partially hidden behind the fuselage).
Presented this finding with the actual render rather than the intended
result, and proposed centring within the available space below the
aircraft instead.

**Round 15 - developer's correction: revert vertical, fix a real
alignment bug round 12 introduced.** Developer: keep the vertical
position as it was before (round 11's real-production anchor, back
below the illustration) - but flagged that the three text lines
"ne sont pas centrées entre elles" (aren't centred relative to each
other). Real bug, not a misperception: round 12's `_band_center_x()`
call was recomputed PER LINE at that line's own y, and since the band
is a trapezoid whose centreline shifts ~50px over this block's ~150px
total height, the three lines ended up centred on three different x
values - a visible stagger, not a clean aligned column. Fixed by
computing `center_x` ONCE at the block's top and reusing that single
value for every line, mirroring the "one shared x for the whole block"
principle the nose-aligned version (rounds 9-11) already used for
`left_x`. Confirmed aligned on both `blue-dithered` and `black-flat`.

**Still open:**
- This entire spike is screen-preview only, per this project's own D-13
  precedent (every visual/typography change needs a real on-glass check
  before being considered final) - nothing here has been near the real
  panel yet.
- The previous-flight card's text (bottom-right, unchanged from
  production) was checked visually for band collision at its height
  range (~75-85% canvas height, band sits at ~17-46% width there) and
  looks clear in every candidate, but wasn't measured as precisely as
  the main block's fixed issues.
- The main text block's now-content-aware height varies by tier (tier 1
  is taller than tier 2/3/4, since it has an extra number+dash pair) -
  each tier was spot-checked to still land clear of the illustration and
  the band, but not exhaustively swept across every route/state
  combination in the vendored illustration set.
