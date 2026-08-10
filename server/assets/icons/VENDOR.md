# server/assets/icons — Vendor Provenance

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
