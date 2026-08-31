---
spike: 002
name: small-labels-and-white-rhythm
type: standard
validates: |
  002a: Given STATE_LABEL_FONT (20px) and TOP_TAG_FONT (18px), both
  already fully uppercase, when rendered with letter-spacing (tracking)
  instead of a literal small-caps simulation, then the result stays
  crisp and legible at this size on both a flat and a dithered theme.
  002b: Given Phase 8's real, final White-theme render (no backing
  plate, per-theme font weight, 11-theme registry), when the illustration-
  to-text vertical spacing is observed directly, then it's clear whether
  the empty space reads differently on White than on a dithered theme.
verdict: PENDING
related: ["001-panel-theme-colours"]
tags: [render, typography, tracking, letter-spacing, white-theme, layout, e-ink]
---

# Spike 002: Small top-label typography + White-theme vertical rhythm

Two polish ideas surfaced by the developer during Phase 8's on-glass
verification session (2026-08-31), deliberately deferred until Phase 8
closed (now merged to `main`, PR #23). Both were originally raised as
Claude's own suggestions in response to "Quelles autres améliorations tu
verrais pour que ça ressemble à un vrai beau tableau ?" — see this spike's
parent conversation for the exact framing.

## What This Validates

**Part A (`small-caps-labels`):** Given the panel's two smallest
fixed-size text roles, when rendered with a museum-placard-style
letter-spacing treatment, then the result reads as more refined/detached
from the informative body text without becoming illegible or clipping.

**Part B (`white-vertical-rhythm`):** Given the real, final Phase 8
render on White, when the illustration-to-text empty space is observed
directly (not guessed at), then the developer can confirm or reject the
hypothesis that a flat white field makes that space read as more visibly
"empty" than the same proportions did on a dithered colour field.

## Research

**Part A.** Both `STATE_LABEL_TEXT` ("DEPARTING"/"ARRIVING") and
`device_config.RUNWAYS[...]["tag_text"]` ("ORY · RWY 3") are **already
fully uppercase strings** (`server/plane/render.py:207-210`,
`server/device_config.py:204-219`) — there is no lowercase to shrink, so
a literal OpenType small-caps simulation (uppercase-height caps +
reduced-height caps-from-lowercase) doesn't apply here. What the
developer described ("petites capitales avec un peu d'espacement, comme
un cartel de musée") is achievable as **tracked all-caps text** instead —
letter-spacing alone, no case mixing needed.

**Prior art, found in git history — this was already built and shipped
once.** `git log -S"letter-spacing" -- server/plane/render.py` surfaces
commit `73a6eb2` ("two-flight poster layout on real glass pipeline,
D-21/D-24/D-25/D-26"), which *removed* a working tracking implementation
when the panel's whole layout was redesigned — not because it failed.
Phase 2/3 had `draw_tracked_text()` (draws glyph-by-glyph with extra
per-glyph advance, since Pillow has no native tracking API),
`_tracked_text_width()` (pre-computes tracked width for
right/centre-aligned positioning), and `fit_text_size(..., tracking=0)`
support, plus a `LABEL_TRACKING_PX` constant that grew from Phase 2's 4px
to Phase 3's 6px (D-15, "wide letter-spacing"). **Never verified on real
Spectra 6 glass** — `hardware/BRINGUP-LOG.md` has no mention of tracking
at any point, so this spike's on-glass step (if it proceeds to a plan) is
genuinely the first real-ink check this technique has ever had, despite
having shipped once before.

`explore_labels.py` resurrects and adapts `draw_tracked_text()`/
`_tracked_text_width()` (used verbatim from the pre-removal
implementation), monkeypatching `render.draw_top_labels()` for the
duration of each render so every other panel element (illustration, main
text, previous card) comes from the real, current, unmodified production
pipeline — `server/plane/render.py` itself is never edited.

**Part B.** No research needed — this is a direct observation of the
already-shipped Phase 8 render via the production CLI
(`server/plane/render.py --theme white/grey --preview`), no new code.

## How to Run

```bash
server/.venv/bin/python3 .planning/spikes/002-small-labels-and-white-rhythm/explore_labels.py
server/.venv/bin/python3 .planning/spikes/002-small-labels-and-white-rhythm/make_contact_sheet.py
server/.venv/bin/python3 server/plane/render.py --state departing --theme white --preview .planning/spikes/002-small-labels-and-white-rhythm/renders/rhythm-white-departing.png
server/.venv/bin/python3 server/plane/render.py --state departing --theme grey --preview .planning/spikes/002-small-labels-and-white-rhythm/renders/rhythm-grey-departing.png
```

## What to Expect

**Part A:** `renders/contact_sheet_white_departing.png` stacks five
tracking variants (0/2/4/6px, plus a 6px-tracked/2px-smaller variant) as
3x-zoomed crops of just the top label row, on White. Individual
`renders/{variant}-{white,grey}-{departing,arriving}-{full,crop3x}.png`
files cover all 5 variants × 2 themes × 2 states × 2 zoom levels (40
files) for the full comparison set, including the dithered `grey` theme
where letter-spacing has to compete with the dither speckle.

**Part B:** `renders/rhythm-white-departing.png`,
`renders/rhythm-white-arriving.png`, and `renders/rhythm-grey-departing.png`
(the same fixture, same illustration, same layout constants — only the
theme differs) for direct visual comparison of how the empty space
between the aircraft and the panel edges reads on each.

## Investigation Trail

**Part A.**
1. Confirmed both label strings are already uppercase (see Research) —
   reframed the ask from "small caps" to "tracked caps" before writing
   any code, since the literal technique the developer named doesn't
   apply to already-uppercase text.
2. Found and reused Phase 2/3's own removed `draw_tracked_text()`
   implementation rather than reinventing tracking from scratch — same
   glyph-by-glyph-advance technique, proven to work in Pillow.
3. Rendered 5 variants (0/2/4/6px tracking, plus a 6px-tracked/-2px-size
   variant for the "smaller and more refined" reading) through the real
   `build_canvas()` pipeline via a `draw_top_labels()` monkeypatch, on
   both White (flat) and Grey (dithered) — dithered specifically to check
   whether wider letter gaps let more dither speckle "into" the label
   and hurt legibility, not just whether it looks nice on flat white.
4. No canvas-overflow warnings at any tracking level tested (up to 6px);
   the right-aligned runway tag has the most room pressure since it's
   the widest already-short string, and stayed comfortably inside the
   panel at every variant.
5. Visual check (this session, not yet the developer's): at 6px tracking
   on Grey, both labels stay individually crisp against the dithered
   field — the extra letter gaps don't introduce new speckle-fighting,
   if anything each glyph keeps more of its own clean space than the
   tightly-set baseline.

**Part B.**
1. Generated the real, current White-theme render (both states) and a
   Grey-theme render of the identical fixture via the production CLI —
   no synthetic/simplified render, the actual `build_canvas()` output.
2. Visual check (this session): the empty space between the label row,
   the aircraft illustration, and the bottom of the panel is
   pixel-for-pixel identical in proportion between White and Grey (same
   layout constants drive both), but reads very differently — on Grey,
   the dithered field fills the visual field with texture even where
   nothing is drawn, so the same empty area doesn't register as "empty."
   On White, the identical area reads as a large void, especially below
   the main text block where roughly half the panel's height carries no
   content at all.

## Results

**Pending developer review — checkpoint below.** Both directions are
technically feasible (Part A: proven, previously-shipped technique,
never on real glass; Part B: hypothesis visually confirmed in this
session's own screen comparison, not yet the developer's own judgment)
and neither required touching `server/plane/render.py`. No blocking
technical risk found in either.
