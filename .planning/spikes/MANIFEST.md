# Spike Manifest

## Idea

Explore panel background colour and text-legibility treatment for the
SkyPane e-ink display before committing to a plan: candidate plain-white
default background, keeping Blue/Green as optional selectable themes, and
replacing the current solid text-backing-plate rectangle (found ugly by
the developer) with a box-free legibility technique.

## Requirements

Design decisions confirmed by the developer during spiking (spike 001).
Non-negotiable for the real build:

- White becomes the new default theme (`DEFAULT_THEME_ID`) — both
  DEPARTING and ARRIVING share one flat white field; the two states are
  distinguished by the existing label text alone ("DEPARTING"/"ARRIVING"
  + "to"/"from" phrasing), not by colour.
- Blue/Green ("sky") remain available as an optional, user-selectable
  theme via the existing CFG-01 companion theme picker — not removed.
- The solid text-backing-plate rectangle (`_paint_text_backing()`) is
  removed entirely, for every theme, not just the coloured ones.
- **Font weight, not a visual trick, is what replaces it**: every text
  role switches from `PTSerif-Regular.ttf` to the already-vendored
  `PTSerif-Bold.ttf`, across ALL themes (white included) for visual
  consistency — confirmed to stay legible over the Blue/Green dithered
  background with no box, outline, or shadow needed. Outline/shadow
  variants were explored and explicitly rejected by the developer as not
  attractive enough, even though they tested as legible.
- Any future background colour must be one of the 6 real Spectra 6
  palette entries (or a dithered blend toward White of one) — no
  arbitrary RGB.

Not yet decided / open for the planning phase:
- Whether `PTSerif-Regular.ttf` stays vendored-but-unused (matching the
  Zilla Slab/Inter "retained for provenance" precedent in
  `server/assets/fonts/VENDOR.md`) or is removed outright.
- Real Spectra 6 glass has not yet confirmed Bold's legibility — only
  on-screen preview PNGs (same caveat Phase 7's own history carries for
  every colour/legibility judgment made off real glass).

## Spikes

| # | Name | Type | Validates | Verdict | Tags |
|---|------|------|-----------|---------|------|
| 001 | panel-theme-colours | comparison | White vs. Blue/Green backgrounds, and box-free text-legibility techniques (font weight vs. outline vs. shadow) vs. the current solid backing plate | VALIDATED — White default + optional Blue/Green + PT Serif Bold (no box) confirmed by developer | render, theme, palette, legibility, e-ink |
