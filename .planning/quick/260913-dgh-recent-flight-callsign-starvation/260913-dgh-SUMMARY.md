---
quick_id: 260913-dgh
status: complete
date: 2026-09-13
commits:
  - 4f6af37
files_modified:
  - companion/static/style.css
  - companion/test_browser_ux.py
  - companion/test_view_pages.py
  - .claude/skills/sketch-findings-skypane/references/data-density.md
---

# 260913-dgh — the recent-flight callsign stops being starved by the time column

## The measurements held — and two of them were not what the brief said

Reproduced before touching anything, with a real Chromium tab against a real
`companion/app.py` subprocess, at five widths x two languages. Every figure in the
brief is confirmed to the pixel:

| vw   | lang | row w  | `grid-template-columns`      | callsign box / own content |
| ---- | ---- | ------ | ---------------------------- | -------------------------- |
| 320  | FR   | 238    | `40px 10.89px 155.11px`      | **10.89 / 57.80** STARVED  |
| 320  | EN   | 238    | `40px 18.64px 147.36px`      | **18.64 / 57.80** STARVED  |
| 360  | FR   | 278    | `40px 50.89px 155.11px`      | **50.89 / 57.80** STARVED  |
| 360  | EN   | 278    | `40px 58.64px 147.36px`      | 58.64 / 57.80 ok           |
| 390  | FR   | 308    | `40px 80.89px 155.11px`      | 80.89 / 57.80 ok           |
| 390  | EN   | 308    | `40px 88.64px 147.36px`      | 88.64 / 57.80 ok           |
| 768  | FR   | 686    | `40px 458.89px 155.11px`     | 458.89 / 57.80 ok          |
| 768  | EN   | 686    | `40px 466.64px 147.36px`     | 466.64 / 57.80 ok          |
| 1280 | FR   | 292.39 | `40px 65.28px 155.11px`      | 65.28 / 57.80 ok, **7.5px of slack** |
| 1280 | EN   | 292.39 | `40px 73.03px 147.36px`      | 73.03 / 57.80 ok           |

The row-width table is confirmed exactly (238 / 278 / 308 / 292.4), including the
point that matters: a media query cannot express this condition.

### Two corrections to the framing

**1. It is not a clip.** Nothing in this component declares `overflow: hidden`. The
*box* collapses and the *text* paints straight out of it, over the time beside it.
The rendered 320px/FR row reads `AFR135ût 00:31` — two strings overprinting glyph
for glyph. This matters for the fix, not just for the prose: a crop would have been
survivable, an overprint is not, and it also explains why `overflow-wrap` treatments
are irrelevant here.

**2. It is not a phone-only defect.** The brief treats 1280px as healthy. Measured,
the 1280px row is 292.4px and the callsign track has **7.5px of slack** — the
narrowest margin of any width tested. `layout.relative_age_text()`'s day bucket has
no upper bound, so the age string only grows. Re-measured with the age forced to
`il y a 365 j`, the **1280px FR track falls to 57.5px for 57.80px of content**: the
desktop starves too. It was always one character away, and this is what ultimately
decided the fix.

## Every treatment measured, at all five widths, in both languages

"starve" is the worst callsign box deficit against its own content (FR; EN is
strictly less bad). "page" is `documentElement.scrollWidth` against the viewport.

| treatment | 320 | 360 | 390 | 768 | 1280 | page | rowH @768 |
| --------- | --- | --- | --- | --- | ---- | ---- | --------- |
| baseline | **-46.9** | **-6.9** | ok | ok | ok | clean | 87.59 |
| (A) `minmax(min-content, 1fr)` | ok | ok | ok | ok | ok | **343 FR / 335 EN vs 320** | 87.59 |
| (B) container query @ 300px | ok | ok | ok | ok | ok | clean | 87.59 |
| (C) container query @ 340px | ok | ok | ok | ok | ok | clean | 87.59 |
| (D) release `nowrap` under (B) | **-46.9** | **-6.9** | ok | ok | ok | clean | 87.59 |
| **(E) wrapping flex line — CHOSEN** | ok | ok | ok | ok | ok | clean | 87.59 |
| (F) time always on its own line | ok | ok | ok | ok | ok | clean | **111.19** |

**(A) rejected.** It stops the starvation and immediately brings back Home's
horizontal scrollbar at 320px: the row grows to 284.91px inside a 238px column and
`documentElement.scrollWidth` goes to 343 (FR) / 335 (EN) against 320. That is the
exact B11 defect quick task 260913-bjy closed hours earlier. A grid row has nowhere
to put what does not fit, so widening the floor only relocates the overflow onto the
page. (At 360px it does not reach the page, but the row still escapes its own column
by 6.9px, where nothing would catch it.)

**(D) rejected as inert, which is the most interesting negative result here.** The
measured `grid-template-columns` after applying it is **byte-identical to the
baseline at every width and in both languages**. A grid `auto` track is sized from
max-content and never consults the min-content that releasing `white-space: nowrap`
lowers. This would have shipped as a dead declaration that reads like a fix — the
same class of thing the design-system notes retired the sticky header for.

**(F) rejected.** Fits everywhere; charges every row 23.6px of extra height at 768px,
where the row is 686px wide and there is nothing to fix.

## Why the container query lost, measured rather than asserted

The brief's instinct is right and I want to be precise about where it stops being
right. A media query genuinely cannot express this condition — the row is 238px
inside a 320px viewport but only 292.4px inside a 1280px one. A container query can
read that width, so I built one and measured it rather than dismissing it.

It works. It is still rejected, on exactly one property: **a container query needs a
hard-coded px threshold, and the content that threshold has to clear has no ceiling.**
Since the desktop row (292.4px) starves once the age grows, any honest threshold must
cover it — and every threshold that covers 292.4px therefore charges the second line
at 1280px unconditionally, in both languages, forever, including today when it fits.

The decisive measurement:

| age string | treatment | 1280 / FR | 1280 / EN |
| ---------- | --------- | --------- | --------- |
| `il y a 42 j` (today) | (B) container query @300px | two lines (111.19) | two lines (111.19) |
| `il y a 42 j` (today) | **(E) flex** | **ONE line (87.59)** | **ONE line (87.59)** |
| `il y a 365 j` (stressed) | (B) container query @300px | two lines (111.19) | two lines (111.19) |
| `il y a 365 j` (stressed) | **(E) flex** | two lines (111.19) | **ONE line (87.59)** |

The last row is the whole argument. Flex line breaking runs on the items' own content
widths, so at the same viewport, with the same fixture, it wraps in French and does
not wrap in English. No fixed threshold can give a per-language, per-content answer.

So: **the container-query framing was the right diagnosis of why a media query fails,
and the wrong instrument.** The honest instrument turned out to be the one that asks
*does this content fit on one line* instead of *is this container under N pixels*. I
have recorded this in the design system as a general caution, not as a one-off.

`.status-row` in this same stylesheet already ships `display: flex` + `flex-wrap:
wrap` + `align-items: baseline`, so this joins an existing pattern rather than
introducing a mechanism.

## What shipped

`.recent-flight` becomes a wrapping flex line. `.recent-flight__detail` re-expresses
its `grid-column: 2 / -1; grid-row: 2` as `order: 1` + `flex: 1 1 100%` +
`margin-inline-start: calc(40px + var(--space-md))`. `.recent-flight__time` swaps the
grid-only self-alignment for an auto inline-start margin; **`white-space: nowrap` is
untouched — B18's one-line contract on the clock/age pair stands verbatim**, and its
own guard still pins it.

Post-fix, callsign box against callsign content, both languages: **57.80 for 57.80 at
320, 360, 390, 768 and 1280** — starved at no width in either language. Geometry is
otherwise the old grid placement to the pixel: the detail line still starts at
`row.left + 56`, the time's right edge is still `row.right`, at every width. The
second line appears only where there is genuinely no room for it: 320px in both
languages, and 360px in French.

No markup change, no new user-facing string, so CFG-29/CFG-30 cannot regress.

## Mutation test

The new check is `no recent-flight callsign is ever starved by the time column`.

| state | harness | result |
| ----- | ------- | ------ |
| fix in place | browser-ux | **25/25 pass** |
| three CSS rules reverted to grid | browser-ux | **24/25** — only the new check red |
| reverted, widths list narrowed to `(360,)` | browser-ux | **24/25** — only the new check red |

Failure text at 320px, unedited:

> the recent-flight callsign column is STARVED at 320px/fr — its box is narrower than
> its own text, so the callsign paints out of it and over the time beside it:
> `['AFR135: box 10.89px for 57.80px of content', ...]`

and at 360px, with the widths narrowed to prove that width is independently covered:

> ... STARVED at 360px/fr ... `['AFR135: box 50.89px for 57.80px of content', ...]`

The stylesheet was then restored and verified **byte-identical** to the committed
version (`diff` clean), and the harness returned to 25/25.

`EXPECTED_CHECK_COUNT` 24 -> **25**, re-derived by RUNNING the harness (the on-disk
`check(` call count is also 25), never by arithmetic.

## Two things the check does that are new here

**It measures a box against its own CONTENT.** Every overflow assertion in this repo
measures a box against a *container* — the viewport, the row, the `.data-table-wrap`.
This element never left its row or the viewport, so `documentElement.scrollWidth` was
exactly 320 and the row-box sweep quick task 260913-bjy added found nothing. The
content width is taken from a `Range` over the element's contents, not from
`scrollWidth`, which rounds to an integer and would report 81 for an 80.89px box.

**Its "same line" test is vertical overlap, not equal tops.** Equal tops was tried
first and was measured being wrong: the row is baseline-aligned and the time renders
at the smaller label size, so two items on the *same* line have tops 3px apart. The
overlap test discriminates exactly — false at 320px in both languages and 360px in
French, true at every other width/language pair.

The 768px one-line assertion is what stops a future "fix" from becoming treatment (F).
It is deliberately **not** asserted at 1280px, where the growing age string will one
day legitimately wrap — that is the fix working, not failing. Conversely, the 1280px
*starvation* assertion gets stronger with wall-clock time, never weaker.

## One correction to an existing check

`companion/test_view_pages.py`'s B18 nowrap guard anchored on `justify-self: end`,
which this task removes (it is grid-only and would have become a dead declaration).
The anchor moved to the auto inline-start margin that replaced it, re-verified as the
single occurrence in the stylesheet. The guard's *assertion* is unchanged, and the
anchor is still deliberately a different declaration from the assertion, so it still
fails if `white-space: nowrap` alone is ever dropped. This is the second consecutive
quick task to move this anchor; the check's comment now records both moves.

## 320px: what this achieves there, and what it does not

Stated deliberately rather than decided, per the brief.

**What it achieves:** for this component, 320px is fully fixed in both languages. The
callsign box is 57.80 for 57.80px of content, nothing overprints, the page does not
scroll sideways (`documentElement.scrollWidth` 320 against 320), and the row reads
cleanly as thumbnail + callsign / time / detail. There is no residual 320px compromise
in `.recent-flight` — it is not "less bad at 320", it is correct at 320.

**What it does not achieve:** it says nothing about the *rest* of Accueil or about the
readings table the previous executor flagged. It removes one of the two 320px issues
that prompted the "is 320px supported at all" question, but it does not answer that
question, and it should not be read as evidence either way — this component happened to
admit a remedy that costs nothing at wider widths, which may not be true of the others.
The decision remains open and belongs to the developer.

## Anything else in the framing that turned out wrong

Only the two corrections above (it is an overprint, not a clip; it is not phone-only).
Everything else held:

- The grid-track figures, the row widths at all four quoted viewports, and the
  callsign box/content numbers at 320/360/390 in both languages — all confirmed exactly.
- "Viewport width does not predict row width" — confirmed, including the 1280px case.
- Not caused by 260913-bjy — I took this on trust as instructed and did not re-derive
  it. The mechanism I measured is consistent with it: the `max-width: 60%` cap acted on
  the *time*, in track 3; the starvation is track 2 losing a fight it was declared to
  lose, independent of anything in track 3's own box.
- Phase 22 did not lengthen the content — likewise taken on trust, and nothing measured
  contradicts it.

## Verification

`./scripts/run-all-tests.sh` — **exactly 5 failing checks**, matching the documented
sandbox baseline by name:

| harness | count | failing check |
| ------- | ----- | ------------- |
| manual_resolutions | 21/23 | `add_entry()` returns ADD_FAILED ... read-only (WR-11) |
| manual_resolutions |  | `delete_entry()` returns False ... read-only (WR-11) |
| companion-app | 270/272 | `POST /airlines/resolve` ... manual_save_failed (WR-11) |
| companion-app |  | `POST /airlines/manual-resolutions/{prefix}/delete` ... (WR-11) |
| status-pages | 267/268 | `anomaly_active()` ... non-existent state_dir |

4 x WR-11 read-only + 1 x `anomaly_active()`, all root-only sandbox artefacts. No new
failure, in any harness. `browser-ux: 25/25`, `view-pages: 143/143`, `i18n 24/24`.

Structural guards: `companion/static/style.css` carries **zero** stray comment
terminators (re-run with the harness's own algorithm after every edit — the new
comment is long and every note was appended *inside* the block). No test exception was
added anywhere. No `companion/static/*.js` file was touched, so the ES5/backtick guard
is not in play.

## Design system

`references/data-density.md` records this as the content-sized-track cause's **fourth
measured site** — the first outside a table — and as a **third distinct remedy**. The
stacked-cell exception's consumer count deliberately stays at **two**: this is neither
that treatment nor the floor-release. Two new general lessons are recorded: that
`minmax(0, 1fr)` is an explicit decision to let a track be starved to nothing and needs
somewhere for the overflow to go, and that a box can be wrong against its own *content*
while correct against every *container* it sits in — the counterpart to 260913-cz6's
scrolling-wrapper lesson.
