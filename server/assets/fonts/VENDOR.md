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

### Supersession (Phase 3, 03-01)

As of Phase 3, `Inter-Regular.ttf` / `Inter-Bold.ttf` are no longer referenced
by `server/plane/render.py`'s active font-role constants (D-15 replaces
Inter with Zilla Slab, see the entry below). The files
stay vendored in this repository for provenance — same "retained for
provenance, not loaded at runtime" treatment `server/assets/icons/VENDOR.md`
already gives its superseded SVG sources — and are **not deleted**.

## `ZillaSlab-SemiBold.ttf` / `ZillaSlab-Bold.ttf`

- **Upstream source:** https://github.com/google/fonts
- **Pinned commit / retrieval date:** commit
  `f473a26ceba660d85cf223ff121dea1fe91cfcb6` (the most recent commit
  touching `ofl/zillaslab` at retrieval time, resolved via
  `https://api.github.com/repos/google/fonts/commits?path=ofl/zillaslab&per_page=1`),
  retrieved 2026-08-26. Downloaded from that immutable commit SHA, never
  from a branch ref (T-03-01-01 mitigation — a branch name is a mutable
  pointer an upstream compromise or force-push could repoint; a pinned
  SHA plus a recorded digest makes any later substitution detectable).
- **Upstream paths:** `ofl/zillaslab/ZillaSlab-SemiBold.ttf`,
  `ofl/zillaslab/ZillaSlab-Bold.ttf` (retrieved via
  `https://raw.githubusercontent.com/google/fonts/<SHA>/ofl/zillaslab/<file>`).
- **Per-file sha256:**
  - `ZillaSlab-SemiBold.ttf`:
    `aafcb295b88d520357db1ecf9a1c3167055e87e9ddf5f63e560cbd139ec2805e`
  - `ZillaSlab-Bold.ttf`:
    `4ec3a04a4eef37074b42ef542e4d874e13646668cfe65256e0bf100441cf8719`
- **Licence:** SIL OFL 1.1 — Copyright 2017, The Mozilla Foundation
  (https://github.com/google/fonts, `ofl/zillaslab/OFL.txt`). The licence
  requires the copyright and licence notice to travel with the font
  files; the full OFL 1.1 text is vendored alongside as
  `server/assets/fonts/ZillaSlab-OFL.txt` (retrieved from the same pinned
  commit) and is also available at http://scripts.sil.org/OFL. This
  notice, plus the copyright line above, constitutes that required
  notice for this repository's copy.
- **Family/weight verification:** both TTFs load via
  `PIL.ImageFont.truetype()` without raising and report family name
  `Zilla Slab` (weights `SemiBold` / `Bold` respectively) via
  `getname()`; the two files have distinct sizes and distinct sha256
  digests, ruling out a silent same-file redirect (T-03-01-02
  mitigation).

### Local modifications

None — copied byte-for-byte from the pinned commit's `ofl/zillaslab/`
directory. Only the static **SemiBold (600)** and **Bold (700)** cuts
were vendored; `ZillaSlab-Regular.ttf`, `ZillaSlab-Light.ttf`,
`ZillaSlab-Medium.ttf`, and every italic cut in that directory were
deliberately **not** vendored. This is a hard rule (D-15,
`03-CONTEXT.md`/`03-UI-SPEC.md`), not a style preference: the Regular
and Light cuts thin out stroke width in exactly the way this panel's
e-ink hairline-legibility risk describes — a slab serif was chosen
specifically because its serifs are structurally as thick as the
letter's main strokes, and a thin cut would reintroduce the same
hairline risk a high-contrast display serif was already rejected for.

### Supersession (Phase 3, later in the same session — D-20/D-27)

Zilla Slab is **no longer referenced** by `server/plane/render.py`'s active
font-role constants. After seeing a real rendered preview, the developer
did not like Zilla Slab's look and chose **PT Serif** instead (see the
entry below) — files stay vendored here for provenance, same
"retained but inactive" treatment this file already gives Inter above.

## `PTSerif-Regular.ttf` / `PTSerif-Bold.ttf`

- **Upstream source:** https://github.com/google/fonts
- **Pinned commit / retrieval date:** commit
  `80327115aa6e63ea8947558e5fb676f5287878ba` (the most recent commit
  touching `ofl/ptserif` at retrieval time, resolved via
  `https://api.github.com/repos/google/fonts/commits?path=ofl/ptserif&per_page=1`),
  retrieved 2026-08-26. Downloaded from that pinned commit SHA via
  `https://raw.githubusercontent.com/google/fonts/<SHA>/ofl/ptserif/<file>`.
- **Upstream paths:** `ofl/ptserif/PT_Serif-Web-Regular.ttf` (vendored here
  as `PTSerif-Regular.ttf`), `ofl/ptserif/PT_Serif-Web-Bold.ttf` (vendored
  here as `PTSerif-Bold.ttf`) — the static desktop/web TTFs, not a variable
  font (PT Serif ships only static weight files upstream, no variable axis).
- **Per-file sha256:**
  - `PTSerif-Regular.ttf`:
    `a4951fade06ff8f09b7673aa81ffb65a8cd409e24d3289a6dc670bc4dda2557a`
  - `PTSerif-Bold.ttf`:
    `038ba7336bd7ea14f12ad155bed51a4345cac5153275d521dec3ba04021c526e`
- **Licence:** SIL OFL 1.1 — Copyright (c) 2010, ParaType Ltd.
  (http://www.paratype.com/public), with Reserved Font Names "PT Sans",
  "PT Serif" and "ParaType" (`ofl/ptserif/OFL.txt`, same pinned commit).
  The full OFL 1.1 text is vendored alongside as
  `server/assets/fonts/PTSerif-OFL.txt`.
- **Family/weight verification:** both TTFs load via
  `PIL.ImageFont.truetype()` without raising and report family name
  `PT Serif` (weights `Regular` / `Bold` respectively) via `getname()`;
  the two files have distinct sizes and distinct sha256 digests.

### Local modifications

None — copied byte-for-byte from the pinned commit's `ofl/ptserif/`
directory.

### Known risk — Regular weight is active (D-27, deliberate, flagged)

Unlike the Zilla Slab entry above (which hard-banned Regular/Light cuts
for e-ink hairline-legibility reasons), **`PTSerif-Regular.ttf` IS the
active weight** for every text role after D-27 — the developer explicitly
asked for a thinner look after seeing the Bold-only render and accepted
this tradeoff after being shown the risk. PT Serif's Regular cut has
visibly thinner strokes than the slab-serif Bold/SemiBold cuts this
project previously restricted itself to. **This has not yet been verified
on real Spectra 6 glass** — it is confirmed only on-screen (developer
judgment via generated preview PNGs). Wave 4's on-glass checkpoint must
explicitly re-verify legibility at this weight before treating it as
final; if strokes prove illegible on the real panel, the documented
fallback is `PTSerif-Bold.ttf` (already vendored here) for at least the
smallest text roles.
