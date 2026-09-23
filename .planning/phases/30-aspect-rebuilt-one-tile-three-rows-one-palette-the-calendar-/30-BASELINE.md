---
phase: 30
taken: 2026-09-22
sha: 606e9819dfd806ec992c95836c53307c50a2b11b
tree_clean: true
---

# Phase 30 — CFG-86 Pre-Change Baseline

This is the genuine, same-instrument "before" reading for CFG-86 (Display's page
height at 390px, reported against X6's target), captured against the CURRENT,
unmodified tree — before a single byte of Phase 30's markup changes existed.

Captured by running the existing registered check
(`_displays_page_height_is_recorded_at_both_phone_widths()`,
`companion/test_browser_ux.py:13500`) via:

```
server/.venv/bin/python3 companion/test_browser_ux.py 2>&1 | grep 'Display document height'
```

## Measured Readings

| Viewport | Document height (px) | Client box | Theme radios |
|----------|----------------------|------------|--------------|
| 390px    | 3486 px              | 390 x 844  | 18           |
| 360px    | 3505 px              | 360 x 844  | 18           |

Raw instrument output:

```
[25-06 T1] Display document height at 390px: 3486 px (client 390x844, 18 theme radios)
[25-06 T1] Display document height at 360px: 3505 px (client 360x844, 18 theme radios)
```

## Instrument Provenance

The reading above comes from `_display_page_height()`
(`companion/test_browser_ux.py:2870`), the ONE registered instrument this
phase's CFG-86 measurement uses — never a second, ad-hoc measurement script.
It passed all four of its own guards for both viewports:

1. **Client width matches the requested viewport** — the document at 390px
   reports a client width of 390, and at 360px a client width of 360, so
   neither reading is a layout nobody asked for.
2. **The Display heading id is present** — the document carries the Frame
   colours heading (`config_page.FRAME_COLOURS_HEADING_ID`), proving this is
   the authenticated Display page and not the login card it redirects to when
   the session is missing (a quarter of the height).
3. **The page posts exactly `len(device_config.THEME_IDS)` radios named
   `theme`** — 18 radios at both widths, proving the page is not rendering a
   partial or stale set of theme options.
4. **The document is taller than the viewport** — 3486px/3505px both clear
   the 844px client height, so the number is a genuine document height and
   not a viewport height wearing one.

Scripts were ENABLED for this measurement, per the instrument's own
documented reason: the height a visitor sees is the height their browser
actually renders, and Display's `theme-preview.js` collapses three of the
four usage panels at load — a scripts-blocked measurement would report a
page nobody with a default browser ever sees.

## Not the Baseline

None of the following ROADMAP-cited or in-code historical figures is a valid
substitute for the reading above — each is a different tree at a different
moment, and CFG-86 requires a delta computed against a number taken by the
SAME instrument at the SAME moment as the "after" reading:

| Figure | Phase / Source | Why it is NOT this phase's baseline |
|--------|-----------------|--------------------------------------|
| 3 743 px | Phase 25 (25-06, per `.planning/ROADMAP.md`) | A prior phase's own before/after measurement, taken against that phase's tree, not this one. |
| 3 524 px | Phase 27 (per `.planning/ROADMAP.md`) | Same — a later prior-phase re-measurement, still not this phase's tree. |
| 3 556 px | 17-09 audit (per `.planning/ROADMAP.md`) | An audit-time reading, unrelated to this phase's own before/after delta. |
| 4 276 px | `companion/test_browser_ux.py` ~line 13523 (in-code comment, an even earlier baseline) | The harness's own comment records this as an even older historical figure, illustrating how these numbers drift phase to phase — also not this phase's baseline. |

## After

Captured by 30-08-PLAN.md Task 3, using the SAME command against the
finished, clean phase tree:

```
server/.venv/bin/python3 companion/test_browser_ux.py 2>&1 | grep 'Display document height'
```

```
[25-06 T1] Display document height at 390px: 3266 px (client 390x844, 18 theme radios)
[25-06 T1] Display document height at 360px: 3454 px (client 360x844, 18 theme radios)
```

- **Taken:** 2026-09-22
- **SHA:** `9e297809313099fd8247e7ab8e21eb9b17561b77` (this plan's own Task 2
  commit — the phase's last markup/CSS/JS-affecting commit; Task 3 itself
  only ever touches this file)
- **Tree clean:** yes (`git status --short` empty at the moment of this
  reading)
- **Instrument identity confirmed:** `_display_page_height()`
  (`companion/test_browser_ux.py`) diffed directly against the SHA this
  file's own Before section was taken at (`606e9819dfd806ec992c95836c53307c50a2b11b`).
  The only differences in the whole function are the ones 30-RESEARCH.md's
  own Pitfall 1 named in advance and 30-04-PLAN.md Task 2 made: the probe's
  `headingId` argument (`config_page.FRAME_COLOURS_HEADING_ID` →
  `config_page.ASPECT_HEADING_ID`) and the assertion message's own wording
  ("Frame colours heading" → "Aspect heading"). `_DISPLAY_HEIGHT_PROBE`
  itself, the four guards it enforces (client-width match, heading
  presence, full THEME_IDS-sized departures radiogroup, document taller
  than viewport), and the registered check's own name string (apart from
  that identical "Frame colours" → "Aspect" substitution) are byte-for-byte
  unchanged. This is the same instrument, driven the same way, twice.

## Delta

| Viewport | Before | After | Delta (px) | Delta (%) |
|----------|--------|-------|-----------|-----------|
| 390px    | 3486 px | 3266 px | −220 px | −6.31% |
| 360px    | 3505 px | 3454 px | −51 px  | −1.46% |

## Verdict

**The target is NOT met: 3266px at 390px, 666px over the 2600px target.**

## Where the height went

Attributed collectively to the named mechanisms this phase's own plans
retired or merged — this session did not take an intermediate height
reading after each individual CSS change, so the figures below are the
whole 220px/51px deltas explained qualitatively by mechanism, not an
itemized per-component pixel budget:

- **The departures/arrivals/calendar strips' fixed-width, one-row,
  horizontally-scrolling chips are gone**, along with each strip's own dot
  row, its two pager buttons, and its "see all" disclosure wrapper (three
  of these stacks retired outright, one per usage row that used to carry
  one) — 30-03/30-04-PLAN.md.
- **The two merged cards' second heading, second caption and second
  card's own padding/border are gone**: Frame colours and Calendar used to
  be two separate `.page-section` cards; Aspect is one — 30-04/30-06-PLAN.md.
- **The retired per-chip 320×120 preview `<img>` is gone** from every
  departures/arrivals/calendar chip; `.palette-chip` draws a small
  CSS-only swatch instead, with no photograph and no `theme-preview` route
  fetch per chip — 30-02-PLAN.md.
- **Working against the above, not helping it**: the open row's own
  `.palette` is now a WRAPPING grid showing all 18 chips at once (never
  collapsed further, unlike the old strip's default one-row view), so the
  currently-open row's own palette is taller than the old collapsed
  strip's default state — this is why the improvement is NOT larger, and
  it is also why the improvement is SMALLER at 360px (−1.46%) than at
  390px (−6.31%): a narrower container fits fewer `minmax(64px, 1fr)`
  columns per row, so the same 18 chips wrap across MORE rows at 360px
  than at 390px, eating into the same-width-independent savings the old
  fixed-width strip never had to pay (the retired strip was exactly one
  row wide regardless of viewport width, so its own height never varied
  with the viewport at all).

The after-reading is genuinely LOWER than the before-reading at both
measured widths, so the retirements above outweigh the wrapping grid's own
added height — but not by enough to reach X6's target, which is reported
plainly above rather than narrowed to fit.
