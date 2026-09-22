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

## After (TBD — filled by 30-08)

**Target:** X6's 2600px at 390px.

**After reading:** TBD — filled by 30-08.

The target above is stated once, as X6's number, and is not paraphrased into
a range or a "roughly." CFG-86 forbids restating the target to fit the
result, and the cheapest way to break that rule is to blur the target now,
before the result is known.
