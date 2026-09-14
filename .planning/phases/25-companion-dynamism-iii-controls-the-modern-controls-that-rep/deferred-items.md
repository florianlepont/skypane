# Phase 25 — deferred items

Out-of-scope discoveries made while executing a plan in this phase. Nothing
here was fixed by the plan that found it.

---

## `.copy-btn`'s real hit area inside a Flights detail row is 34×26, not 44×44

**Found by:** 25-02, while demonstrating `_hit_area()` against a subject whose
answer was supposed to be already known.

**Measured:** `#flight-detail-0 .copy-btn` on `/flights` at 1280×900, with the
detail row expanded and its `<tr>` hovered (so the desktop
`pointer-events: none`-at-rest rule is not the cause):

    visual box 22×22, real hit area 34×26
    reach from its own centre: 12 left, 21 right, 23 up, 2 down

The `::before` (`position: absolute; inset: -11px`) is genuinely there — every
axis measures more than the 22px visual box, so the synthesis IS reaching the
hit test. But the outer part of it is covered by neighbours inside
`.flight-detail-row__grid`: 12px of the 22 available on the left, and 2px of
the 22 available below.

**Why it matters:** `control-density.md` records `.copy-btn` in the RELOCATED
category on the strength of "a `::before` … synthesizes a real 44×44 hit area
(22 + 11×2 = 44)". That arithmetic is about the rule; it is not what the
browser resolves in this particular container. The same class measures 45×45
in the row toggle's position (`[data-row-toggle]`, same values verbatim), so
the rule is fine and the *placement* inside the detail-row grid is what eats
it.

**Not fixed here because:** it is in `companion/static/style.css` /
`companion/pages/history_page.py`, neither of which 25-02 owns, and it is
pre-existing — not caused by anything this plan changed. 25-02's only job was
to make the measurement available.

**Suggested disposition:** re-measure with `_assert_hit_target()` once this
phase's control plans land, and either give the copy buttons room inside
`.flight-detail-row__grid` or record the 34×26 honestly in the register the
way the `.airline-card__chip` 20px exception is already recorded.

---

## Every shipped theme paints its "Departures" and "Arrivals" swatches the same colour

**Found by:** 25-06, while mutation-testing the carousel's dots row. The
mutation was "paint each dot with the theme's `arriving_index` instead of its
`departing_index`" and it changed **not one byte of output**.

**Measured** (`server/device_config.THEMES`, all eighteen entries):

    departing_index == arriving_index for 18 of 18 themes
    the eighteen themes resolve to SEVEN distinct palette hexes
    (#FFFFFF ×6, #000000 ×2, #2D5F9B ×3, #A02020 ×3, #F0E050 ×2, #326941 ×2)

**Why it matters:** `_theme_chip_grid_html()` renders two `.theme-chip__dot`
swatches per chip and 22-10 added a one-line legend under every grid naming
them — `"Departures · Arrivals"` / `"Départs · Arrivées"`, copy that 22-10
deliberately chose over the UI spec's own wrong `"Background · Ink"` precisely
because the two dots *are* the departing and arriving inks. They are, and on
this registry they are always the same ink, so the legend explains a
distinction the user can never see. Two identical squares plus a label naming
two different things reads as a rendering fault, which is a softer version of
22-AUDIT.md X6's original "two unexplained square swatches per chip/row".

**Not fixed here because:** the fix is either a registry change
(`server/device_config.py`, which decides what the *frame* paints, not what the
companion shows) or a copy/markup change to the one shared chip renderer — and
25-06 owns neither question. Nothing this plan changed caused it; the carousel
merely put the same dots in a row where the repetition is visible at a glance.

**Suggested disposition:** decide which of the two it is. Either the registry is
supposed to allow different departure/arrival inks and no shipped theme
currently uses that (in which case the dots and the legend are correct and
merely under-exercised), or it is not, and the chips should show one swatch
with a legend that names what it actually is.
