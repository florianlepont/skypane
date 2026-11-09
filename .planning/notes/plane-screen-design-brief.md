# Plane screen: design brief (exploration, not a decision to build)

Outcome of a discussion session about a new look for the e-ink "plane mode"
screen. Nothing here changes the production renderer or the golden fixtures;
the mock-ups come from standalone scripts in `design-exploration/plane-screen/`
(`mock_*.py`, one per topic), run with `PYTHONPATH=.`. Those using Anton take a
font directory argument: the font was fetched outside the repository, it is not
vendored. Images live next to this file in `plane-screen-design-brief/`.

## Why change

Reviewer feedback on the current screen (see the four reference renders in the
session): it feels under-designed, the text cannot be read from 2-3 m, and the
previous-flight card is questionable (removed in every mock-up; the reviewer
never formally confirmed the removal). Content sits in the top third of a
1200x1600 frame. At 150 ppi (about 59 px/cm), a 2 cm capital needs roughly
120 px of cap height; the current title is around 30 px.

## Chosen direction

**Giant destination as the background, aircraft on top.**

- The destination city is set in very heavy letters filling the whole portrait
  frame, split into stacked lines (`MAR / SEI / LLE`, `NEW / YORK`), each line
  stretched to the frame width.
- Two tones of one hue: pale field, saturated letters (with the diagonal band,
  the lettering flips tone where it crosses the band, see below).
- The aircraft is always horizontal (rotated variants were rejected).
- Flight number is large at the bottom (about 150 px, 2.5 cm, bottom-left in the
  first mock-ups; about 124 px and right-aligned once the band was added, see
  below); airline name below it, small. Direction word (DEPARTING / ARRIVING) stays small at the top.
- The previous-flight card is removed.

### Retained aircraft layouts

All three layouts are kept (reviewer decision), as selectable options rather
than a single winner; A remains the reference mock-up.

| | Layout | Notes |
|---|---|---|
| A (primary) | Large nose/cockpit entering from the right edge, smaller rear half (wing and tail) entering from the left edge below it | Both halves bleed off the frame. Shows the airline logo on the fuselage and the livery on the tail. |
| B | Whole aircraft, centred, near full width | Simplest; hides most of the middle text line. |
| C | Lettering compressed at the top, whole aircraft below it, at the bottom of the frame (not a coloured band; unrelated to the diagonal band) | Lettering is compressed into the top part of the frame. Status unclear: the reviewer found a horizontal band out of step with A and B (three reworks in `band-rework` were not retained) and asked for the diagonal instead; the diagonal was only built on A and B. |

Rejected: rotated or climbing aircraft, vertical aircraft, tail-only, white
disc, runway band, drop shadow, hard cuts inside the frame.

See `plane-screen-design-brief/layouts-departing.png` (A, B, C in that order)
and `primary-layout-1200x1600.png`.

### Lettering font (decided)

Anton (SIL OFL), condensed and naturally very heavy, drawn with at most a 1 px
added stroke. Compared with Inter Black, Bebas Neue (needs a faked stroke), Archivo
Black, Alfa Slab One and Zilla Slab (`fonts-six-marseille.png`,
`fonts-six-newyork.png`; head-to-head `bebas-vs-anton-1.png` and `-2.png`).
Bebas Neue was the runner-up. Sans-serif was preferred over slab. Anton is not vendored yet:
`server/assets/fonts/` would need `Anton-Regular.ttf` plus its OFL text and a
`VENDOR.md` entry.

### Colour pairings (field / lettering)

Grey / black, light blue / blue, light red / red, light yellow / yellow,
white / black. Yellow needs a much lighter field (about 75% white instead of
40%) to separate from its own ink; the panel has a single yellow, so yellow
lettering cannot be darkened except by dithering it with black (tried for the
lettering and rejected in favour of the lighter field; still used for the small
text, see below).

See `colour-pairings.png`.

### Destination splitting (decided)

Tried nine names split by hand (`cities-hand-split.png`). Three lines read best
for long names (Bordeaux, Toulouse, Barcelona, Casablanca); two lines for
medium names (London, Frankfurt, New York). Short names (Nice, Lyon, Rome) are
split in two as well, accepting very tall letters, because a single small line
loses the poster effect (`short-names-two-vs-one-line.png`). Known cost: the
aircraft hides the junction between lines on two-line names, so a short name
can read as two fragments; the aircraft position may need to follow the number
of lines. Splitting is fully automatic (no correction table), decided in the phase 62 discussion.

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
field. The white / black pairing was not rendered with the band. Lettering is two-tone: ink off the band, the pairing's light field shade
inside it (white inside the band was tried and rejected: it works for blue,
red and grey but fails for yellow). Validated in four pairings (blue, red,
grey, yellow) on the nose-and-tail layout (`diagonal-band-colours-light-lettering.png`; earlier
tries in `diagonal-band.png` and `diagonal-band-colours.png`). The flight
number and airline are right-aligned at the bottom right, in the pairing's
plain ink on the light field, outside the band (`diagonal-band-flight-right-*.png`,
nose-and-tail and whole-aircraft layouts); centred inside the band or across its
edge lost contrast. For yellow, the small text (state, flight, airline) is dithered
toward black (about 45%) so it separates from the light yellow field; the giant
lettering stays plain yellow. Landscape versions of both layouts with the band
are in `landscape-diagonal-nose-tail.png` and `landscape-diagonal-whole.png`;
there the state label sits above the lettering so the two no longer touch.

### Status screens (decided)

Today's hold screens (watching, quiet hours, display off, battery empty, no
connection, updating, retired; `status-screens-current.png`) are a tiny icon
plus a small label and are unreadable from 3 m. Pairing is excluded: its code
is typed from close up. Final direction: `status-screens-calm.png`.

- Generic screens: no diagonal band, no theme colours, same colours as today
  (white field with black ink for watching, dithered dark field with white ink
  for the others).
- Calm layout: 110 px margins, Anton at natural proportions (not stretched),
  flush left, whole words only (never split), each line sized to fit the width.
- The production icon, about 120 px, sits top-left above the small label; the
  body text is small and bottom-left.
- Watching shows the runway number as the keyword ("RUNWAY / 3"), "WATCHING" as
  the small label. Updating reads "FIRMWARE / UPDATE" with label "INSTALLING";
  no connection reads "NO / CONNECTION".
- Rejected along the way: stretched full-page lettering with a band, icons
  inline with the lettering (too big, crude edges), icon in a corner
  (poorly integrated). Earlier renders: `status-screens-new.png`,
  `status-screens-icon-*.png`.
- Open: the calm layout reads less from afar than the stretched one; the icons
  are enlarged production glyphs and would need redrawing at this size; the
  landscape version is not explored.
- No connection and updating are drawn by the firmware from a mask generated by
  `_build_no_connection_canvas()` / `_build_updating_canvas()`; the masks and the
  firmware headers would have to be regenerated, with exactly two colours.
  OVERHEAD, NEARBY and SET A LOCATION are tags on the flight screens and follow
  them.

### Departure vs arrival

Direction is currently only a small word at the top. At 3 m it is invisible, so
the field colour should carry it. A green pairing for arrivals was shown and
liked (shown before the band and the pairings were settled); the existing
`theme_arriving` setting could carry this without new plumbing. Green is not
among the five pairings, so an arrival colour has to be added to them. See
`cases-arriving-and-generic.png`.

## What the new design keeps, replaces or drops

| Existing feature | Verdict |
|---|---|
| 18 colour themes (`server/themes.py`) | Reduce to the five pairings above, plus an arrival colour. Flat full-colour themes and the three "band" themes have no place in this look. |
| Per-airline colour rules (`colour_rules.py`) | Keep: a rule still resolves to a theme id, which now selects a pairing. |
| Per-airline illustration | Keep and use much larger; needs per-aircraft-type crop points (see below). The generic grey fallback loses the airline colour cue. |
| Diagonal band | Keep, reworked (see "Diagonal band" above). |
| Previous-flight card | Drop. |
| Small top labels | Keep, small. |

## What would have to change in the code

1. **New portrait layout** beside the current one, selected per device or
   theme, so the golden render stays untouched until a decision is made.
2. **Font**: vendor Anton (see above). On flight screens, lines are stretched
   to the full frame width, which widens the condensed letters; check this on
   the real panel. Status screens use natural proportions.
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
9. **State screens**: portrait design decided (see above), to implement in
   `hold_screens.py` (not the pairing screen); landscape not explored.
   SET A LOCATION, NEARBY and OVERHEAD are tags on the flight screens and
   follow them.
10. Tests: golden fixtures stay for the current layout; the new layout needs its
   own fixtures.

## Open questions

- How much the stretched Anton letters distort on flight screens, judged on
  glass.
- Whether to keep three layouts as options, and what the default is.
- Whether layout C survives, and in what form.
- Status screens in landscape.
- Whether the contrast between field and lettering is right on real glass
  (the reviewer expects it to be softer there than on a monitor).
- Arrival colour (green was liked, not formally chosen).
- Behaviour when the destination is unknown (airline-only state).
