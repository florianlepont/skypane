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
