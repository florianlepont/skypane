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

All three layouts are kept (reviewer decision), as selectable options rather
than a single winner; A remains the reference mock-up.

| | Layout | Notes |
|---|---|---|
| A (primary) | Large nose/cockpit entering from the right edge, smaller rear half (wing and tail) entering from the left edge below it | Both halves bleed off the frame. Shows the airline logo on the fuselage and the livery on the tail. |
| B | Whole aircraft, centred, near full width | Simplest; hides most of the middle text line. |
| C | Whole aircraft in its own band under the lettering | Lettering is compressed into the top part of the frame. |

Rejected: rotated or climbing aircraft, vertical aircraft, tail-only, white
disc, runway band, drop shadow, hard cuts inside the frame.

See `plane-screen-design-brief/layouts-departing.png` (A, B, C in that order)
and `primary-layout-1200x1600.png`.

### Lettering font (decided)

Anton (SIL OFL), condensed and naturally very heavy, drawn without any added
stroke. Compared with Inter Black, Bebas Neue (needs a faked stroke), Archivo
Black, Alfa Slab One and Zilla Slab (`fonts-six-marseille.png`,
`fonts-six-newyork.png`; head-to-head `bebas-vs-anton-1.png` and `-2.png`).
Bebas Neue was the runner-up. Sans-serif was preferred over slab. Anton is not vendored yet:
`server/assets/fonts/` would need `Anton-Regular.ttf` plus its OFL text and a
`VENDOR.md` entry.

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

Long names (`long-names-1.png`, `long-names-2.png`, five names on all three
layouts): layout C keeps every line readable; layouts A and B hide part of the
middle line (and, for A, part of the bottom line). Four-line names such as
Villefranche-sur-Saône flatten the letters. This is a trade-off the layouts
carry, not a defect to fix in one of them.

### Landscape (800x480)

The three layouts were adapted to the 7.3" landscape panel
(`landscape-800x480.png`) and all three are kept. The destination is one
stretched line across the width (long names such as Clermont-Ferrand still
fit), the flight number and airline sit bottom-left or bottom-right. Layout A
(nose and tail) covers less lettering than in portrait; B hides the centre of
the word; C keeps everything readable with a smaller aircraft. The flight
number is about 1.3 cm tall at 128 ppi, readable to roughly 2 m, not 3 m.

### Diagonal band (decided)

The diagonal band of the current renderer comes back, with its real geometry
(`style.BAND_*_FRAC`), as a solid band in the pairing's ink over the light
field. Lettering is two-tone: ink off the band, the pairing's light field shade
inside it (white inside the band was tried and rejected: it works for blue,
red and grey but fails for yellow). Validated in all five pairings on the
nose-and-tail layout (`diagonal-band-colours-light-lettering.png`; earlier
tries in `diagonal-band.png` and `diagonal-band-colours.png`). Known weakness:
the flight number sits across the band edge at the bottom left and loses
contrast there, so its position (or its tone) needs to be reworked. Not yet
shown on the other two layouts or in landscape.

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
| Diagonal band | Keep, reworked (see "Diagonal band" below). |
| Previous-flight card | Drop. |
| Small top labels | Keep, small. |

## What would have to change in the code

1. **New portrait layout** beside the current one, selected per device or
   theme, so the golden render stays untouched until a decision is made.
2. **Font**: vendor Anton (see above). Lines are stretched to the full frame
   width, which widens the condensed letters; check this on the real panel.
3. **City splitting**: a rule for breaking names into 2-3 stacked lines
   (never a single line; spaces and hyphens first, then syllables), and a
   fallback for very long names. Where the aircraft sits relative to the lines
   may need to depend on the line count.
4. **Layout selection**: three layouts to expose (per device, theme or rule),
   with a default; a way to choose between them must be designed.
5. **Aircraft halves**: crop points (nose half, rear half) are tuned for the
   A320 family illustration used in the mock-ups. Each aircraft type in
   `server/plane/illustrations.py` needs its own crop fractions, or a
   metadata-free heuristic.
6. **Panel quantisation**: the mock-ups paste full-RGB aircraft over an
   approximated palette. Real output goes through the 6-colour quantiser, which
   needs a look on glass, particularly the white halo and the dithered fields.
7. **Dither limits**: the production background helper asserts a lighten
   fraction below 0.5; the yellow field needs about 0.75.
8. **Landscape (800x480)**: a landscape variant of each layout is needed (one
   stretched line of lettering, see above).
9. **State screens** (no connection, pairing, SET A LOCATION, NEARBY,
   OVERHEAD): not explored; they should adopt the same pairings.
10. Tests: golden fixtures stay for the current layout; the new layout needs its
   own fixtures.

## Open questions

- Letter distortion vs. a condensed face.
- Whether the contrast between field and lettering is right on real glass
  (the reviewer expects it to be softer there than on a monitor).
- Arrival colour (green was liked, not formally chosen).
- Behaviour when the destination is unknown (airline-only state).
