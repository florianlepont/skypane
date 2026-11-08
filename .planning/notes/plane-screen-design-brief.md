# Plane screen: design brief (exploration, not a decision to build)

Outcome of a discussion session about a new look for the e-ink "plane mode"
screen. Nothing here changes the production renderer or the golden fixtures;
the mock-ups come from standalone scripts in `design-exploration/plane-screen/`
(`mock_giant_city.py`, `mock_plane_variants.py`, `mock_themes.py`), run with
`PYTHONPATH=.`. Images live next to this file in `plane-screen-design-brief/`.

## Why change

Reviewer feedback on the current screen (see the four reference renders in the
session): it feels under-designed, the text cannot be read from 2-3 m, and the
previous-flight card adds little. Content sits in the top third of a
1200x1600 frame. At 150 ppi (about 59 px/cm), a 2 cm capital needs roughly
120 px of cap height; the current title is around 30 px.

## Chosen direction

**Giant destination as the background, aircraft on top.**

- The destination city is set in very heavy letters filling the whole portrait
  frame, split into stacked lines (`MAR / SEI / LLE`, `NEW / YORK`), each line
  stretched to the frame width.
- Two tones of one hue: pale field, saturated letters.
- The aircraft is always horizontal (rotated variants were rejected).
- Flight number is large at the bottom (about 150 px, 2.5 cm); airline name
  below it, small. Direction word (DEPARTING / ARRIVING) stays small at the top.
- The previous-flight card is removed.

### Retained aircraft layouts

| | Layout | Notes |
|---|---|---|
| A (primary) | Large nose/cockpit entering from the right edge, smaller rear half (wing and tail) entering from the left edge below it | Both halves bleed off the frame. Shows the airline logo on the fuselage and the livery on the tail. |
| B | Whole aircraft, centred, near full width | Simplest; hides most of the middle text line. |
| C | Whole aircraft in its own band under the lettering | Lettering is compressed into the top part of the frame. |

Rejected: rotated or climbing aircraft, vertical aircraft, tail-only, white
disc, runway band, drop shadow, hard cuts inside the frame.

See `plane-screen-design-brief/layouts-departing.png` (A, B, C in that order)
and `primary-layout-1200x1600.png`.

### Colour pairings (field / lettering)

Grey / black, light blue / blue, light red / red, light yellow / yellow,
white / black. Yellow needs a much lighter field (about 75% white instead of
40%) to separate from its own ink; the panel has a single yellow, so yellow
lettering cannot be darkened except by dithering it with black (tried, rejected
in favour of the lighter field).

See `colour-pairings.png`.

### Destination splitting (decided)

Tried nine names split by hand (`cities-hand-split.png`). Three lines read best
for long names (Bordeaux, Toulouse, Barcelona, Casablanca); two lines for
medium names (London, Frankfurt, New York). Short names (Nice, Lyon, Rome) are
split in two as well, accepting very tall letters, because a single small line
loses the poster effect (`short-names-two-vs-one-line.png`). Known cost: the
aircraft hides the junction between lines on two-line names, so a short name
can read as two fragments; the aircraft position may need to follow the number
of lines.

### Departure vs arrival

Direction is currently only a small word at the top. At 3 m it is invisible, so
the field colour should carry it. A green pairing for arrivals was shown and
liked; the existing `theme_arriving` setting could carry this without new
plumbing. See `cases-arriving-and-generic.png`.

## What the new design keeps, replaces or drops

| Existing feature | Verdict |
|---|---|
| 16+ colour themes (`server/themes.py`) | Reduce to the five pairings above, plus an arrival colour. Flat full-colour themes and the three "band" themes have no place in this look. |
| Per-airline colour rules (`colour_rules.py`) | Keep: a rule still resolves to a theme id, which now selects a pairing. |
| Per-airline illustration | Keep and use much larger; needs per-aircraft-type crop points (see below). The generic grey fallback loses the airline colour cue. |
| Diagonal band | Drop. |
| Previous-flight card | Drop. |
| Small top labels | Keep, small. |

## What would have to change in the code

1. **New portrait layout** beside the current one, selected per device or
   theme, so the golden render stays untouched until a decision is made.
2. **Font**: the mock-ups use Inter Black plus an added stroke. The repo only
   vendors Inter Bold; Inter Black (OFL) would need vendoring. The stretch to
   full width distorts letters; check that this is acceptable on the real panel
   or switch to a condensed face.
3. **City splitting**: a rule for breaking names into 2-3 stacked lines
   (never a single line; spaces and hyphens first, then syllables), and a
   fallback for very long names. Where the aircraft sits relative to the lines
   may need to depend on the line count.
4. **Aircraft halves**: crop points (nose half, rear half) are tuned for the
   A320 family illustration used in the mock-ups. Each aircraft type in
   `server/plane/illustrations.py` needs its own crop fractions, or a
   metadata-free heuristic.
5. **Panel quantisation**: the mock-ups paste full-RGB aircraft over an
   approximated palette. Real output goes through the 6-colour quantiser, which
   needs a look on glass, particularly the white halo and the dithered fields.
6. **Dither limits**: the production background helper asserts a lighten
   fraction below 0.5; the yellow field needs about 0.75.
7. **Landscape (800x480)**: not explored. The giant-letters idea needs a
   landscape variant (one or two lines of lettering, aircraft across).
8. **State screens** (no connection, pairing, SET A LOCATION, NEARBY,
   OVERHEAD): not explored; they should adopt the same pairings.
9. Tests: golden fixtures stay for the current layout; the new layout needs its
   own fixtures.

## Open questions

- Letter distortion vs. a condensed face.
- Whether the contrast between field and lettering is right on real glass
  (the reviewer expects it to be softer there than on a monitor).
- Arrival colour (green was liked, not formally chosen).
- Behaviour when the destination is unknown (airline-only state).
