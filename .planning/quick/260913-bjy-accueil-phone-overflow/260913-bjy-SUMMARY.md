---
quick_id: 260913-bjy
status: complete
date: 2026-09-13
commits:
  - 6a6fda2
files_modified:
  - companion/static/style.css
  - companion/test_view_pages.py
  - companion/test_browser_ux.py
---

# 260913-bjy — Accueil stops scrolling sideways (B11's missing fourth surface)

## The diagnosis held, exactly

Reproduced before touching anything, with a real Chromium tab against a real
`companion/app.py` subprocess, across six widths x two languages x two themes:

| lang | vp   | `doc.scrollWidth` | `.recent-flight` | `.recent-flight__time` | `.time-value__age` |
| ---- | ---- | ----------------- | ---------------- | ---------------------- | ------------------ |
| EN   | 390  | 408 (cw 390)      | 41..349 (308)    | 261..349 (88)          | 348..408 (60)      |
| FR   | 390  | 411 (cw 390)      | 41..349 (308)    | 256..349 (93)          | 346..411 (65)      |

Every number in the brief is confirmed: 411 FR / 408 EN, a 308px `.recent-flight`
ending at x=349, a `nowrap` `display: block` time cell 93px wide ending at x=349,
and an `inline` `.time-value__age` painting out to x=411. Both themes. The only
element in the whole document painting right of the viewport was
`.time-value__age`, five of them, one per row.

## Two things the diagnosis did not say

**1. The time cell is clamped to exactly 60% of its own content, at every width.**
`.recent-flight__time`'s `clientWidth` is 88px (EN) / 93px (FR) while its own
`scrollWidth` is 147px / 155px. 88/147 = 0.6 and 93/155 = 0.6, and those numbers
are *identical* at 320, 390, 430, 768, 960, 1280 and 1440px.

**2. So the spill was never phone-only.** At 960px and 1280px the age still paints
outside `.recent-flight` — right edge 1253 against a row ending at 1191 at 1280px.
It just stays inside the wider viewport, so no scrollbar appears. That is how this
survived nine plans: the desktop half is invisible to `scrollWidth`, and the phone
half is the same defect merely escaping a smaller box.

## The cause, and why the treatment is a deletion

`.recent-flight` is `grid-template-columns: 40px minmax(0, 1fr) auto`. The time
sits in the third, **content-sized `auto`** track, so that track resolves to the
item's own max-content width. `.recent-flight__time` then carried `max-width: 60%`
— and a percentage resolves against the grid area, which *is* that content-derived
track. The cap therefore clamped the box to 60% of exactly the content it was
meant to bound, guaranteeing a 40%-of-the-line overflow unconditionally. Under
`white-space: nowrap` nothing can reflow into the smaller box, so the remainder is
simply painted outside.

The declaration is a lie to the layout engine: **reserve 88px, paint 147px.** It
could not do its job in any viewport, in any language, in any theme. This is the
user's framing confirmed at the mechanism level — "a column that cannot size to
its content is the real problem" — except the column *could* size to its content;
the cap forbade the item from occupying the column it had already sized.

So the fix is one deleted declaration. `text-align: right`, `justify-self: end`
and `white-space: nowrap` all stay untouched, the markup is untouched, and
`_recent_flight_time_html()` is untouched — **22-07's one-line intent is preserved
verbatim, not reverted.** With the cap gone the track *is* the line.

## The alternative was measured first, then rejected on the measurement

The obvious "truer" treatment was to let the pair wrap under pressure: make
`.recent-flight__time` a `flex-wrap: wrap` container so the clock and the age
break *between* atoms while each stays internally unbreakable. It was measured
across the same six widths and two languages before being chosen or rejected.

It produced **byte-identical numbers to the plain deletion at every single width**
— because the `auto` track always grows to max-content before the neighbouring
`minmax(0, 1fr)` track yields, so `flex-wrap` never engages at any width from
320px up. It would have shipped inert: the same class of dead declaration the
design-system notes retired the sticky-header entry for ("inert from the day it
shipped, in every browser, on every page"). Not added.

The design system's own precedent — the stacked-cell exception applied twice by
measurement (Flights' When/Flight cells, Health's registry table) — was considered
and is **not** needed here, because after the deletion the one-line shape fits with
no overflow at every width from 390px to 1440px in both languages. That exception's
stated bar ("measure first, in both languages, at the real viewport, or do not do
it") is met in the direction of *not* invoking it. No new token, size or breakpoint
was introduced; the change is a net deletion of one declaration.

## A check that anchored on the defect

`companion/test_view_pages.py`'s `_recent_flight_time_nowrap_in_css()` located
`.recent-flight__time`'s dedicated rule by searching for the literal
`max-width: 60%` — deliberately, because the shared colour-only rule ends in the
*identical* `.recent-flight__time {` and comes first in source order. Deleting the
declaration would have made that check raise. Retargeted onto `justify-self: end`,
verified unique in the stylesheet, and deliberately still a *different*
declaration from the asserted one, so the check still fails if `white-space:
nowrap` alone is ever dropped. Its comment was corrected rather than left lying.

## The new harness check, and its mutation test

One check in `companion/test_browser_ux.py`, written for the **class** on Accueil
rather than the one selector: in **both languages**, at **390px and 1280px** —

- `documentElement.scrollWidth <= viewport width`;
- no element anywhere on the page paints right of the viewport;
- no `.recent-flights` descendant paints outside its own `.recent-flight` row box.

The third assertion is not redundant: it is the only one that can see the desktop
half, where the age escaped its card while staying inside a 1280px viewport. A
non-empty row count is asserted too, so the check cannot pass by measuring nothing.

Both languages because French is the wider driver here, and the seeded age string
only grows with wall-clock time — `layout.relative_age_text()`'s day bucket has no
ceiling — so this check can only get stronger, never quieter.

**Mutation test, both numbers:**

- Deleted declaration restored → **22/23**, the new check the only one red, and it
  named the overflow: *"Home scrolls sideways at 390px/en: documentElement.scrollWidth
  408 against a client width of 390, painted past the right edge by
  ['time-value__age']"*.
- Declaration removed again → **23/23**.

`EXPECTED_CHECK_COUNT` re-derived by **running** the harness: 22 → **23**.

## Verification

`./scripts/run-all-tests.sh` — at the documented sandbox baseline of exactly **5**
failing checks, all pre-existing, all root-only artifacts:

| harness             | result      |
| ------------------- | ----------- |
| browser-ux          | **23/23**   |
| companion-app       | 270/272 (2 x WR-11 read-only) |
| status-pages        | 267/268 (`anomaly_active()`)  |
| manual_resolutions  | 21/23 (2 x WR-11 read-only)   |
| view-pages          | PASS (retargeted anchor)      |
| i18n                | PASS        |

No test exception added — the suite still carries none. No new user-facing string,
so no French catalogue entry was needed; CFG-29/CFG-30 do not regress. The
stylesheet's stray-comment-terminator guard passes (the new comment is one opener,
one closer, and never writes a terminator inside itself). Visually confirmed at
390px in French: the rows now read `2 août 00:31 · (il y a 42 j)` complete, on one
line, inside the card.

## Found, not fixed, and deliberately

**At 320px the callsign is starved, and was before this change too.**
`.recent-flight__callsign` measures a 19px (EN) / 11px (FR) box against a 58px
`scrollWidth` at a 320px viewport — clipped. The numbers are **identical before and
after** this task, so it is neither introduced nor worsened here: at 320px the
one-line time takes 147/155px of a 280px row and the `auto` track wins against
`minmax(0, 1fr)` every time. Fixing it honestly needs the column to shrink under
pressure, which viewport media queries cannot express — the row is 292px wide at
1280px and 308px at 390px, so viewport width does not predict row width at all. The
real predictor is container width, i.e. a container query, which is a new layout
mechanism for this codebase and deserves its own plan rather than a quick task's
drive-by. Recorded here, not silently absorbed.

**B11 is now closed on all four surfaces:** Flights (22-09), Airlines (22-11),
Health (22-12), Accueil (this task).
