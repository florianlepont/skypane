# server/assets/fonts — Vendor Provenance

## `Inter-Regular.ttf` / `Inter-Bold.ttf`

- **Upstream repository/source:** https://github.com/rsms/inter
- **Pinned commit / retrieval date:** release tag `v4.1`, retrieved 2026-08-09
  via `https://github.com/rsms/inter/releases/download/v4.1/Inter-4.1.zip`
- **Upstream path:** `extras/ttf/Inter-Regular.ttf`, `extras/ttf/Inter-Bold.ttf`
  (the static-weight desktop TTFs, not the variable font or the web-font
  build)
- **Licence:** SIL OFL 1.1 — Copyright (c) 2016 The Inter Project Authors
  (https://github.com/rsms/inter). The licence requires the copyright and
  licence notice to travel with the font files; the full OFL 1.1 text is
  vendored alongside the upstream release archive's own `LICENSE.txt` and
  is also available at http://scripts.sil.org/OFL. This notice, plus the
  copyright line above, constitutes that required notice for this
  repository's copy.

### Local modifications

None — copied byte-for-byte from the release archive's `extras/ttf/`
directory. Only the static Regular (400) and Bold (700) weights were
extracted; the variable font, the web-font (woff/woff2) builds, and the
rest of the release archive were not vendored.
