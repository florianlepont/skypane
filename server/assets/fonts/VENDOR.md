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
  licence notice to travel with the font files. The full OFL 1.1 text is
  vendored as `server/assets/fonts/Inter-OFL.txt`, retrieved from the same
  pinned `v4.1` release tag as the TTFs above
  (`https://raw.githubusercontent.com/rsms/inter/v4.1/LICENSE.txt`,
  retrieved 2026-08-26; sha256
  `262481e844521b326f5ecd053e59b98c8b2da78c8ee1bdbb6e8174305e54935a`), and
  is also available at http://scripts.sil.org/OFL. This notice, plus the
  copyright line above, constitutes that required notice for this
  repository's copy.

  **Correction (2026-08-26, 04-03):** this entry previously claimed the
  full OFL 1.1 text was "vendored alongside the upstream release archive's
  own `LICENSE.txt`" — no such file existed in this directory at the time,
  even though `Inter-Regular.ttf`/`Inter-Bold.ttf` remained committed and
  distributed (see Supersession note below: retained, not deleted). That
  gap is what this correction closes; the claim above is now true because
  `Inter-OFL.txt` was vendored in the same session this correction was
  written.

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
Retention does not reduce the OFL 1.1 obligation: the licence attaches to
distribution of the font files, not to whether they are loaded at
runtime, and these two TTFs are still committed and shipped with every
clone of this repository. That is exactly why `Inter-OFL.txt`'s absence
(corrected above, 04-03) was a real gap and not a moot one.

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

**Correction (2026-08-31, Phase 8, D-06/D-07):** the paragraph above is no
longer accurate on either count. First, Phase 7's on-glass checkpoint (the
"Wave 4" session this note deferred to) ran and found `PTSerif-Regular.ttf`
genuinely legible at every role, on real glass, both before and after the
text-backing-plate fix — `hardware/BRINGUP-LOG.md`'s "PT Serif Regular
legibility" entry records "tout est parfait" across every size tested,
down to the smallest (16px, since grown to 20px by D-11). The risk this
paragraph flagged did not materialise. Second, and unrelated to that
finding, Phase 8 switched every active-state role to `PTSerif-Bold.ttf`
anyway — not because Regular failed, but because D-05 removed the
text-backing-plate rectangle that had been carrying the legibility job
against the dithered state background, and the heavier Bold stroke is
what replaces it. See the Supersession subsection immediately below for
the full record.

### Supersession (Phase 8 — D-06/D-07)

As of Phase 8, `PTSerif-Regular.ttf` is no longer referenced by any
active-state font-role constant in `server/plane/render.py`:
`STATE_LABEL_FONT`, `TOP_TAG_FONT`, `MAIN_LINE1_FONT`, `MAIN_LINE2_FONT`,
`PREVIOUS_LINE1_FONT` and `PREVIOUS_LINE2_FONT` all moved to
`PTSerif-Bold.ttf`, as did the two `fit_text_size()` call sites inside
`draw_main_text_block()` and `draw_previous_text_block()` that previously
read the Regular path directly. `EMPTY_BODY_FONT` is the one remaining
active reference to `PTSerif-Regular.ttf` — the empty state's copy is
explicitly out of scope for this phase, so the file is not fully
unreferenced.

**Why.** Unlike the Zilla Slab supersession above, which was a pure taste
change, this one is functional. The solid backing-plate rectangle
`_paint_text_backing()` painted behind every text run (added Phase 7,
07-01, to fight the dithered background's White speckle behind
white-ink text) was removed on visual grounds this same phase (D-05) — the
developer wanted it gone, no replacement box, outline or shadow. A
stroke outline (1/2/3px widths) and an offset drop-shadow were both built
in the spike and both read as legible, and both were rejected by the
developer on visual grounds before font weight was tried. Zilla Slab
Bold/SemiBold (already vendored, already inactive) was also re-tried at
the same time as an alternative to PT Serif Bold, and again not chosen —
the developer kept PT Serif for typographic consistency with the rest of
the panel, not because Zilla Slab tested worse. All of this was judged on
preview PNGs (`.planning/spikes/001-panel-theme-colours/README.md`);
plan 08-06's on-glass session is where the new weight meets real ink.

**Disposition.** Both `PTSerif-Regular.ttf` and `PTSerif-Bold.ttf` stay
vendored, with their pinned upstream commit, per-file sha256 digests and
licence record intact — the same "retained for provenance, not deleted"
treatment this file already gives the Inter and Zilla Slab entries above.
No font file, digest, commit SHA or licence text changed.
