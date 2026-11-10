# Photo rendering

## Purpose

A user can upload a photo and have it shown on the frame. This document
records how an upload is stored, how the stored copy is rendered to the
six-colour panel, and what the skin-tone review of its parameters did
and did not establish.

## Stored copy contract

- One reduced copy is kept per upload: baseline sRGB JPEG, long edge at
  most 2048 px, about 1 MB, all metadata dropped. The original is never
  kept.
- Limits on the upload: 12 MiB, 50 megapixels, at least 200 px on the
  shorter side.
- Accepted inputs: JPEG, PNG, WebP (still images). HEIC/HEIF is not
  supported. Animated PNG and animated WebP are rejected.
- A refused upload reports a stable reason code, never a traceback.

## Render order and fit semantics

- Order: crop (or fit into bands), tone boost, dither to the six panel
  colours. The same order applies in both fit modes.
- `fill` scales the photo to cover the panel and crops the overflow.
  `pos_x` and `pos_y`, both in [0, 1], choose which part is kept: 0 is
  flush left/top, 1 flush right/bottom, 0.5 centred. Only the axis that
  has slack matters for a given panel aspect.
- `bands` scales the photo to fit inside the panel; the unused area is
  white. The boost only sees the photo area.
- The same stored photo serves every panel size.
- Rendering is deterministic: the same stored bytes, size, fit setting and
  parameters give identical pixels.

## Rendering parameters

**Status: defaults kept; real faces not tried (2026-11-10).**

The owner was shown synthetic contact sheets and could not judge them (see
the verdict section). The values below are the starting defaults, kept
unchanged. They are a starting point to revisit once real portraits have
been tried, not a verified-good result. `DEFAULT_PREP` in
`server/photo/prep.py` holds them and a test pins the literals, so a change
must be deliberate.

| Parameter | Value | Range tried | Allowed range | Reason |
|-----------|-------|-------------|---------------|--------|
| cutoff | 1.0 | 0.5, 1.0, 2.0 | 0 to 49 | percent clipped at each end of the histogram; no measurable difference between 0.5 and 2.0 on the synthetic scenes |
| tone preservation | on | not varied | fixed | keeps hue when the histogram is stretched |
| strength | 0.8 | 0.5, 0.8, 1.0 | 0 to 1 | weight of the stretched image in the blend; 1.0 gave the largest hue shift of the three |
| saturation | 1.2 | 1.0, 1.15, 1.2, 1.3 | 0 to 1.3 | colour enhancement factor; 1.3 is the ceiling and was not exceeded |
| resample | LANCZOS | not varied | fixed | |
| sharpening | none | not tried | n/a | |

## Skin-tone trial method

- The test images are procedural: a shaded face-like ellipse on a graded
  backdrop, in six skin tones (I to VI), each in a full-range and a dull
  variant. No photo of a real person is stored in the repository.
- The grid renders every tone, scene, panel size (1200x1600 and 800x480)
  and fit mode, for the default parameters plus one-factor-at-a-time
  variations of saturation, strength and cutoff.
- Per cell it measures, inside the skin region: mean colour and hue before
  and after the boost, the share of each palette colour, and the error
  between a blurred boosted image and the blurred dithered result.
- One contact sheet per tone is written for visual review.

Run the synthetic grid (a fresh temporary directory is used when `--out`
is omitted):

    python -m server.photo --synthetic --out /path/outside/the/repo

Try a portrait of your own:

    python -m server.photo --in ~/portrait.jpg --out /path/outside/the/repo \
        --fit fill --pos-x 0.5 --pos-y 0.3

Your own portraits stay outside git. The command refuses an output
directory inside the repository, and nothing it writes is committed.

## Results per tone and panel size

Default parameters, `fill` fit, mean over the skin region. Hue is in
degrees before and after the boost. Fidelity is the error between a blurred
boosted image and the blurred dithered result (lower is closer). White share
is the fraction of skin pixels that dither to white. "Full" is the
full-range scene, "dull" the low-contrast one.

| Tone | Scene | Panel | Hue before to after | Fidelity | White share |
|------|-------|-------|---------------------|----------|-------------|
| I | full | 1200x1600 | 29.6 to 32.3 | 5.04 | 0.617 |
| I | full | 800x480 | 29.6 to 32.6 | 5.00 | 0.620 |
| II | full | 1200x1600 | 27.1 to 27.9 | 7.46 | 0.391 |
| II | full | 800x480 | 27.1 to 32.4 | 7.63 | 0.451 |
| III | full | 1200x1600 | 28.7 to 28.7 | 5.89 | 0.215 |
| III | full | 800x480 | 28.7 to 34.6 | 8.80 | 0.297 |
| IV | full | 1200x1600 | 24.4 to 24.5 | 3.33 | 0.053 |
| IV | full | 800x480 | 24.4 to 32.9 | 10.18 | 0.163 |
| V | full | 1200x1600 | 21.4 to 21.4 | 6.00 | 0.000 |
| V | full | 800x480 | 21.4 to 21.3 | 10.64 | 0.000 |
| VI | full | 1200x1600 | 18.3 to 18.5 | 3.69 | 0.000 |
| VI | full | 800x480 | 18.3 to 18.3 | 5.66 | 0.000 |
| I | dull | 1200x1600 | 29.2 to 31.9 | 2.69 | 0.594 |
| I | dull | 800x480 | 29.2 to 31.9 | 2.72 | 0.594 |
| II | dull | 1200x1600 | 27.4 to 27.9 | 4.29 | 0.393 |
| II | dull | 800x480 | 27.4 to 32.1 | 4.98 | 0.453 |
| III | dull | 1200x1600 | 29.2 to 29.2 | 3.25 | 0.218 |
| III | dull | 800x480 | 29.2 to 35.6 | 5.81 | 0.304 |
| IV | dull | 1200x1600 | 24.4 to 24.5 | 1.66 | 0.070 |
| IV | dull | 800x480 | 24.4 to 33.2 | 7.74 | 0.194 |
| V | dull | 1200x1600 | 20.7 to 20.8 | 3.01 | 0.000 |
| V | dull | 800x480 | 20.7 to 20.8 | 7.58 | 0.013 |
| VI | dull | 1200x1600 | 19.5 to 19.2 | 1.92 | 0.000 |
| VI | dull | 800x480 | 19.5 to 19.5 | 4.02 | 0.000 |

Summary of the 390 measured cells (24 tone and scene combinations, two
panel sizes, two fit modes, eight parameter sets):

- Portrait 1200x1600, both fit modes, and landscape 800x480 with `bands`:
  the hue of the skin region moved by at most 2.8 degrees at the default
  parameters. Landscape `fill` moved it by up to 8.8 degrees (tones II to
  IV); the cause was not investigated, so it is recorded as measured.
- Tones V and VI sit at 0 white share and tones I to III keep the most
  white; this is the palette at work, not a tuning effect.
- One factor at a time on tone I, full scene, portrait: saturation 1.0 to
  1.3 moved fidelity from 4.21 to 5.27 and white share from 0.656 to 0.599;
  strength 0.5 to 1.0 moved hue after from 31.2 to 33.2; cutoff 0.5 to 2.0
  changed nothing beyond 0.05 in fidelity.
- Fidelity values run from 1.66 to 7.46 on portrait and 1.70 to 10.64 on
  landscape at the defaults. The numbers say how close the dither is to the
  boosted image, not whether a face looks good.

These are synthetic faces. Nothing here says how a real face looks.

## Visual verdict and date

On 2026-11-10 the owner was shown synthetic contact sheets for tones I,
III and VI. His answer, in his words: "I don't know". He gave no judgement
of how skin looks.

What was and was not looked at:

- Looked at: synthetic contact sheets for three tones only.
- Not looked at: real portraits, his own portraits, the physical frame.

Decision: keep the current defaults unchanged (cutoff 1.0, strength 0.8,
saturation 1.2). No verdict on skin rendering is claimed. Revisit the
defaults when real portraits have been tried, for example through
`python -m server.photo --in`.

## Known limits

- Only six colours exist, so faces become speckled yellow, red and white.
  Dark skin shows green, red and black dots. This is a palette limit and is
  not fixed.
- Smooth gradients show banding.
- Dithering runs in gamma-encoded space, not linear light.
- The palette RGB values are nominal; on glass, blue and green are more
  muted.
- Nothing was measured with a colorimeter.
- The tone swatches are illustrative approximations, not a standard scale.
- Real faces were never tried, so every statement about skin is about
  synthetic images only.
- A Pillow upgrade can change decoded pixels slightly and cost one redraw.

## Not tried

- Real people, on screen or on the physical frame.
- Sharpening.
- Dithering in linear light.
- Smart (face-aware) cropping.
- Blurred-background fitting.

## How to re-run

Run the synthetic grid with `python -m server.photo --synthetic --out
/path/outside/the/repo`, or render a portrait of your own with `python -m
server.photo --in ~/portrait.jpg --out /path/outside/the/repo`. Both
refuse an output directory inside the repository.

## Follow-ups for the upload route and companion

- The preview shown after upload should be rendered by the server with the
  same render function (`preview_png`), not approximated in the browser.
- Concurrent normalisations must be bounded (for example a process-wide
  semaphore of 2), and the body byte cap must be applied while reading the
  request, not after.
- The file input should accept JPEG, PNG and WebP only, with a clear
  message for HEIC.

## Follow-ups for the rendering

- Try real portraits with `python -m server.photo --in <portrait> --out <dir>`
  (outside the repository) and revisit the defaults from what is seen.
- Investigate the hue drift of up to 8.8 degrees on tones II to IV in the
  landscape crop-to-fill render (at most 2.8 degrees elsewhere). The cause
  is not known; the small face region in the 800x480 render is one
  suspect that was not tested.
