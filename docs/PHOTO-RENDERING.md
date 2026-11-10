# Photo rendering

## Purpose

A user can upload a photo and have it shown on the frame. This document
records how an upload is stored, how the stored copy is rendered to the
six-colour panel, and how the rendering is reviewed on skin tones before
its parameters are declared final.

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

**Status: NOT FROZEN: provisional defaults pending the skin-tone review.**

| Parameter | Provisional value | Allowed range | Meaning |
|-----------|-------------------|---------------|---------|
| cutoff | 1.0 | 0 to 49 | percent clipped at each end of the histogram |
| strength | 0.8 | 0 to 1 | weight of the stretched image in the blend |
| saturation | 1.2 | 0 to 1.3 | colour enhancement factor |

## Skin-tone trial method

- The test images are procedural: a shaded face-like ellipse on a graded
  backdrop, in six skin tones (I to VI), each in a full-range and a dull
  variant. No photo of a real person is stored in the repository.
- The grid renders every tone, scene, panel size (1200x1600 and 800x480)
  and fit mode, for the provisional parameters plus one-factor-at-a-time
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

## Visual verdict and date

## Known limits

## Follow-ups for the upload route and companion

- The preview shown after upload should be rendered by the server with the
  same render function (`preview_png`), not approximated in the browser.
- Concurrent normalisations must be bounded (for example a process-wide
  semaphore of 2), and the body byte cap must be applied while reading the
  request, not after.
- The file input should accept JPEG, PNG and WebP only, with a clear
  message for HEIC.
