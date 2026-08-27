# server/assets/icons — Vendor Provenance

## `illustrations/*.png`

- **Generation date:** 2026-08-26 (visual-style revision on the same date).
- **Tool:** OpenAI built-in image generation (`gpt-image`), generated as
  transparent PNG cutouts and visually inspected after generation.
- **Prompt recipe:** polished modern aviation-poster illustration with crisp
  ink-like contours, clean coloured body planes, and restrained blue-grey
  graphic shadows; one aircraft, landscape framing, nose pointing **left**,
  authentic carrier livery colours, and a genuinely transparent RGBA
  background with no ground, sky, vignette, halo, scenery, or extra aircraft.
  The generic fallback additionally prohibits all airline identities, logos,
  and livery colours.
- **Selected aircraft types (Phase 3 baseline, 8 files):**
  - `air-france.png` — Airbus A320
  - `iberia-airlines.png` — Airbus A320
  - `tap-portugal.png` — Airbus A321neo
  - `air-algerie.png` — Boeing 737-800
  - `air-corsica.png` (renamed from `ccm-airlines.png`, 260827-kih) — Airbus A320 (Air Corsica; adsbdb still resolves the pre-2013-rebrand name "CCM Airlines")
  - `vueling-airlines.png` — Airbus A320
  - `transavia-france.png` — Boeing 737-800
  - `generic-fallback.png` — unbranded generic narrow-body jet
- **Local modifications / validation (Phase 3 baseline):** TAP and Air
  Algérie were regenerated after a visual check identified an opaque
  vignette in earlier drafts. The final eight files are all native RGBA
  PNGs, at least 1200px wide, and passed
  `server/plane/illustrations.py --validate`. All source profiles were
  visually confirmed nose-left before hand-off.
- **Phase 3.1 expansion (D-19 accuracy upgrade, 2026-08-27):** aircraft
  type is no longer a free "plausible for that carrier" choice — it is now
  dictated by the filename itself (an unsuffixed `{airline}.png` is the
  carrier's numerically dominant type; a `{airline}-{shape}.png` file is a
  named secondary variant). The full per-file type table, including every
  Phase 3.1 airline primary, secondary-variant, and neutral-shape file, is
  now maintained in `illustrations/VENDOR.md`'s "Per-file digests" section
  rather than duplicated here — that file is the authoritative record from
  this phase forward. This directory-level summary is retained only for
  the Phase 3 baseline above.
- **New category — neutral shape fallbacks (D-07, 7 files):**
  `generic-a320.png`, `generic-b737.png`, `generic-atr72.png`,
  `generic-beechcraft1900d.png`, `generic-embraer.png`, `generic-a330.png`,
  `generic-a350.png` — shown when the airline itself is unrecognized but
  the detected ICAO type classifies to one of the seven D-03 base shapes.
  These are distinct from `generic-fallback.png` (the pre-existing D-08
  universal fallback, used only when neither the airline nor the shape
  resolves): the neutral shape files are a correct-shape-but-no-brand
  middle tier, `generic-fallback.png` is the last-resort catch-all. None of
  the seven carry any airline identity, livery colour, tail marking, or
  logo shape — see `illustrations/VENDOR.md` and `illustrations/HANDOFF.md`
  for the full requirement.

## `plane-takeoff.svg` / `plane-takeoff.png`, `plane-landing.svg` / `plane-landing.png`

- **Upstream repository/source:** https://github.com/lucide-icons/lucide
- **Pinned release tag / retrieval date:** release tag `1.31.0`, retrieved
  2026-08-10 via
  `https://raw.githubusercontent.com/lucide-icons/lucide/1.31.0/icons/plane-takeoff.svg`
  and `.../1.31.0/icons/plane-landing.svg`.
- **Upstream path:** `icons/plane-takeoff.svg`, `icons/plane-landing.svg`
  (source SVGs, unmodified except the pre-rasterization step below).
- **Licence:** ISC License — Copyright (c) 2026 Lucide Icons and
  Contributors (https://github.com/lucide-icons/lucide). Permission to
  use, copy, modify, and/or distribute this software for any purpose with
  or without fee is hereby granted, provided that the above copyright
  notice and this permission notice appear in all copies. The full ISC
  licence text is available at
  `https://raw.githubusercontent.com/lucide-icons/lucide/1.31.0/LICENSE`.
  This notice, plus the copyright line above, constitutes the required
  notice for this repository's copy. (Lucide's LICENSE file also notes a
  subset of icons are derived from the Feather project; `plane-takeoff`
  and `plane-landing` are original Lucide icons, not part of that
  Feather-derived subset.)

### Local modifications

1. `plane-takeoff.svg` / `plane-landing.svg` — copied byte-for-byte from
   the pinned release tag; retained only for provenance, not loaded at
   runtime (no SVG parser is a runtime dependency of this project, per
   02-RESEARCH.md's "Don't Hand-Roll" table).
2. `plane-takeoff.png` / `plane-landing.png` — pre-rasterized once at
   vendor time from the corresponding SVG (`stroke="currentColor"`
   replaced with `stroke="#ffffff"`, rendered onto an opaque black
   background) into a 256x256 grayscale-content PNG: white glyph strokes
   on a black field. `server/plane/render.py`'s `load_binary_mask()` loads
   this file with `Image.open(...).convert("L")`, resizes it to the target
   glyph size, and hard-thresholds it back to a strictly binary mask
   before compositing (02-RESEARCH.md Architecture Pattern 2) — the PNG
   itself is not required to be pre-thresholded, only high-contrast enough
   for that threshold step to recover a clean glyph shape. Rasterized with
   `cairosvg` 2.9.0 (a vendor-time-only tool, not added to
   `server/requirements.txt` — it is never imported by any file under
   `server/` at runtime).

## `aircraft-silhouette.svg` / `aircraft-silhouette.png`

- **Upstream source:** freesvg.org / OpenClipart, **SVG ID 178507**,
  "Passenger aircraft silhouette clip art"
  (`https://freesvg.org/passenger-aircraft-silhouette-clip-art`,
  download endpoint `https://freesvg.org/download/178507`).
- **Retrieval date:** 2026-08-10.
- **Licence:** Public Domain / **CC0** — the source page's
  `<meta itemprop="license" content="https://creativecommons.org/publicdomain/zero/1.0/">`
  tag confirms CC0 Public Domain Dedication. Originally derived by
  OpenClipart from a public-domain Wikimedia Commons line drawing, per
  freesvg.org's own attribution convention for OpenClipart-sourced
  uploads. No attribution is legally required, but the source URL and
  SVG ID are recorded here for provenance.
- **Locked selection (02-UI-SPEC.md Design System, binding):** chosen over
  OpenClipart SVG ID 18321 and SVG ID 37085 as the only CC0 candidate
  reading as a modern commercial jet in profile without per-airline
  livery detail. Do not substitute a different asset without updating
  02-UI-SPEC.md first.

### Local modifications

1. `aircraft-silhouette.svg` — copied byte-for-byte from the freesvg.org
   download endpoint; retained only for provenance, not loaded at runtime
   (no SVG parser is a runtime dependency of this project, per
   02-RESEARCH.md's "Don't Hand-Roll" table). The source artwork is a
   detailed 3/4-aerial-view line-art drawing (a single compound SVG
   `<path>` using an even-odd fill rule to trace outline strokes,
   panel/window detail, and shading — not already a flat solid
   silhouette).
2. `aircraft-silhouette.png` — pre-rasterized once at vendor time
   (`cairosvg` 2.9.0, the same vendor-time-only tool used for the Lucide
   glyphs above; not a runtime dependency) into a 1800x830 grayscale-content
   PNG: white aircraft shape on a black field, matching the same
   `load_binary_mask()`-compatible convention as the Lucide glyphs. Unlike
   the Lucide glyphs, this source is not already a flat shape, so a
   cleanup pass was required beyond straight rasterization, per
   02-UI-SPEC.md's Design System executor note ("clean up stray anchor
   points and over-fine detail... so the silhouette reads as one clean
   solid jet in profile"):
   - Rasterized at 3600px width for antialiasing headroom, thresholded to
     a binary ink mask (outline strokes + shaded regions).
   - Closed hairline gaps in the traced outline (a thin unfilled cheatline
     channel along the fuselage, and a thin gap in the tail assembly, both
     of which let a background flood-fill leak into the aircraft's
     interior) with a small morphological dilation (Pillow
     `ImageFilter.MaxFilter`).
   - Flood-filled the true exterior background from multiple canvas-edge
     seed points, then treated every pixel *not* reached by that flood
     fill — both the original ink and the now-enclosed interior
     (previously-white fuselage/wing surface detail, window rows, panel
     lines) — as the solid aircraft mask. This is what removes the
     source's interior line-art detail and leaves one flat, continuous
     shape.
   - Eroded back by the same amount used for the closing dilation to
     restore the true outer boundary, then a slight Gaussian blur +
     re-threshold pass to smooth pixel-staircase edges before the final
     LANCZOS downscale to 1800px width with a small padding margin.
   - Verified at simulated render size (~579x260, the actual in-panel
     target box) that the cleaned shape still reads as one solid,
     unfragmented jet silhouette after the render pipeline's own
     resize-then-threshold step (02-RESEARCH.md Pattern 2).
   - **Source nose orientation: LEFT.** The source artwork's cockpit/nose
     section renders on the left side of the canvas, tail assembly on the
     right. `server/plane/render.py` must mirror
     (`Image.transpose(Image.FLIP_LEFT_RIGHT)`) for the `departing` state
     (UI-SPEC requires nose-right) and leave the source orientation
     unmirrored for the `arriving` state (UI-SPEC requires nose-left,
     which already matches the source).
   - Content aspect ratio after cleanup: approximately 2.22:1 (width:height)
     — wider than UI-SPEC's "~220-260px tall" anticipation once scaled to
     fit that height, meaning the binding size constraint at render time is
     the ~260px zone-3 height cap, not the ~900px width cap; actual
     rendered width is well under 900px. This does not change the shape,
     only which UI-SPEC dimension governs the final scale.

### Independent-design note (carried from 02-UI-SPEC.md Revision 2, informational)

flightportrait's public `flightportrait/frame` GitHub repository contains
only device firmware and the minimal reference protocol server
(`stub-server/byos_server.py`, already vendored in this project) — the
repo's own README states its poster renderer is "separate, closed
components." There is no vendorable rendering code, layout logic, or
asset pipeline for flightportrait's own poster artwork; this project's
full-bleed silhouette-centerpiece composition (and the specific choice of
this CC0 asset) is an independent design decision reverse-engineered from
flightportrait.com's public visual reference, not a copy of their
implementation. A future contributor looking for "the flightportrait
renderer" in that repo will not find one.
