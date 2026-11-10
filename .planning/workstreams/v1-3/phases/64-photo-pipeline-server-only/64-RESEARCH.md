# Phase 64: Photo Pipeline (Server Only) - Research

**Researched:** 2026-11-10
**Domain:** Pillow-only image upload hardening, crop/boost/6-colour dithering for Spectra 6 panels, skin-tone trial method
**Confidence:** HIGH for the hardening and render mechanics (every API behaviour below was run against the repo's own Pillow 13.0.0), MEDIUM for the pre-processing starting values (synthetic proxy numbers, not on-glass), LOW for anything about real faces on real ink (cannot be established without the owner's eyes)

<user_constraints>
## User Constraints (from CONTEXT.md)

There is no `64-CONTEXT.md` (the phase directory was empty; no discuss-phase was run). The binding inputs are the concept brief `.planning/notes/photo-mode-concept.md` ("decisions are taken and are not reopened"), SEED-013, `.planning/workstreams/v1-3/REQUIREMENTS.md` and the Phase 64 section of the roadmap. They are copied here so the planner treats them as locked.

### Locked Decisions
- Photo source: the user's own uploaded photos first; provided collections are v1.3.x and not in this milestone's phases. External albums/services are out of scope.
- Privacy: only a reduced, normalised copy is stored, never the original. The admin never sees user photos and no admin view is built. (Storage layout, quotas, deletion and access control are Phase 65, not this phase.)
- Fitting a photo to the panel: crop to fill by default, with a per-photo setting (crop or bands) and a movable crop position. The same stored photo must serve both the portrait (1200x1600) and the landscape (800x480) panels.
- Rendering order (PHOTO-02): crop, then contrast and saturation boost, then 6-colour dithering, through a render path separate from the plane screen.
- Upload hardening equals the illustration upload's rigour (size limit, real image decoding, no trusted filename) and the original bytes are never kept.
- Skin tones must be tried in both panel sizes, and the result and any limit written down before the rendering parameters are frozen (PHOTO-04).
- Plane rendering and `server/fixtures/golden` are never modified. No new runtime dependency, no new daemon. No companion change in this phase. Phases 47/47.1/47.2 and `hardware/` are not touched.
- Quality honesty: "a dithered look is part of the product".

### Claude's Discretion
- Where the new code lives, the stored format and reduced size, the exact limits (bytes, pixels, minimum size), the pre-processing parameters and ranges, how the crop is represented, the skin-tone test method and the doc layout. (Smart crop is CROP-01, a future requirement: out of scope. Whether the companion preview is server-rendered or browser-rendered is a Phase 67 decision, but this phase must make a server-rendered preview possible.)

### Deferred Ideas (OUT OF SCOPE)
- Provided collections and the artist collection (COLL-01/02), automatic switching and schedules (SCHED-01), smart crop (CROP-01), blurred-background fitting (the brief found it "attractive but busy"; not a v1.3 option).
- Everything in Phases 65-68: storage layout, quotas, deletion, backup decision, per-frame mode/rotation, waiting screen, companion screens, wake interval.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PHOTO-01 | Strict validation (size limit, real decoding, no trusted filename) and one reduced normalised stored copy; original never kept | "Upload normalisation" below: byte cap, header-first pixel cap, `Image.open(formats=...)`, real `load()`, `exif_transpose`, ICC-to-sRGB then metadata dropped, JPEG re-encode with a size ladder; the function takes bytes only and writes nothing |
| PHOTO-02 | Stored photo rendered for a panel profile via a render path separate from the plane screen: crop, boost, dither | New `server/photo/` package; reuses `dither.dither_to_full_panel_palette`, `panel_format.new_canvas/pack_panel` unchanged; render is a pure function of (stored bytes, size, fit setting, params) |
| PHOTO-03 | Crop-to-fill (default) or bands; crop movable; same stored photo serves both sizes | Normalised object-position crop `(pos_x, pos_y)` in [0,1], implemented with `ImageOps.fit(centering=...)`; bands via `ImageOps.contain` pasted on a white palette canvas |
| PHOTO-04 | Skin-tone samples tried, result and limits recorded before freeze | Procedural (synthetic) skin-tone generator in `test-support/`, a trial CLI the owner can point at their own local portraits, and `docs/PHOTO-RENDERING.md` written before the parameters are declared final |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- Production Python is stdlib + Pillow + requests only (`server/requirements.txt`, hash-locked). No `pillow-heif`, no numpy, no new package. [VERIFIED: server/requirements.in pins `Pillow==13.0.0`, `requests==2.34.2`]
- Code, comments, docstrings, docs and commit messages in English.
- Comments say what and why (invariants, units, security invariants); no plan, ticket, decision, review or phase IDs in comments or docstrings (`scripts/check_comment_history.py check` in CI). That includes requirement IDs such as PHOTO-01 and the words "Phase 64" and `.planning/` paths. Test docstrings are scanned too.
- Function-size gate: max 80 code lines per function over `server`/`stub-server` (`scripts/check_function_size.py check --max 80 server stub-server`). Test files are exempt, new production modules are not.
- Behaviour-over-source tests: tests assert behaviour, never source text or `.planning/`. (`companion/test_suite_guards.py` enforces it for `companion/` only, but the rule applies in spirit to `server/` tests.) Consequence for PHOTO-04: the doc cannot be verified by a test reading it; the plan verifies it with a checklist step.
- ruff (E4/E7/E9/F), mypy (new modules should be typed at birth and added to `[tool.mypy] files` and the strict override list in `pyproject.toml`), coverage gate `fail_under = 93`, pytest-socket (no network in tests), tests write only under `tmp_path`.
- GSD workflow: all repo edits go through a GSD command (this research only writes the RESEARCH.md).

## Summary

The phase is a pure-function library with no HTTP surface: `normalize(raw bytes) -> one stored JPEG` and `render(stored JPEG, panel size, fit setting) -> "P" image with only the 6 panel indices` (plus a packed-bytes helper). Everything needed exists in Pillow 13.0.0 (already pinned and installed in `server/.venv`): format allowlisting at `Image.open(formats=...)`, header-first size check, `ImageOps.exif_transpose`, `ImageCms.profileToProfile`, `ImageOps.fit(centering=...)` (which is exactly a normalised object-position crop), `ImageOps.contain`, `ImageOps.autocontrast(preserve_tone=True)`, `ImageEnhance.Color`, and the repo's existing `dither_to_full_panel_palette` (Floyd-Steinberg against the 6-entry palette, 0.03 s at 1200x1600). None of the existing illustration helpers fit photos (PNG-only, alpha-required, landscape-only, min-width 1200, transparent-bbox crop), so reuse is limited to the dither, palette, canvas and pack helpers plus the *pattern* "check size from the header before decoding; only ever store our own re-encode".

Three measured findings drive the design. (1) Pillow's default `Image.open` tries every plugin, so an allowlist `formats=["JPEG","PNG","WEBP"]` is a real attack-surface reduction (a GIF and an HTML blob are rejected as `UnidentifiedImageError`; an MPO phone photo still opens through the JPEG entry and reports `format == "MPO"`). (2) A 109 KB PNG can declare 900 megapixels; Pillow raises `DecompressionBombError` at `open()` beyond 2x its default limit and only *warns* between 1x and 2x, so the app needs its own cap that is below Pillow's, checked from `img.size` before any `load()`. (3) Per-channel `ImageOps.autocontrast` shifts skin hue (synthetic tone I went from hue 29 to hue 0, tone III from 29 to 42) while `preserve_tone=True` keeps hue within +-3 degrees; saturation above about 1.3 starts pushing mid skin tones toward orange-red (G and B channels collapse). These are the main reasons the pre-processing parameters must be frozen only after the PHOTO-04 trial.

**Primary recommendation:** Create `server/photo/` (`normalize.py`, `render.py`, `prep.py`, `crop.py`), store one 8-bit sRGB baseline JPEG with long edge <= 2048 px and <= 1,000,000 bytes (quality/size ladder), represent the crop as a validated `(pos_x, pos_y)` in [0,1] applied with `ImageOps.fit(centering=...)`, render in the order crop -> `autocontrast(cutoff=1, preserve_tone=True)` blended at 0.8 -> saturation 1.2 -> `dither_to_full_panel_palette` as *trial-pending defaults*, run a synthetic skin-tone grid plus an owner-run local trial, and only then freeze the numbers in `docs/PHOTO-RENDERING.md`.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Upload validation and normalisation | API / Backend (server library) | — | Untrusted bytes must be validated where they are decoded; the frame is dumb and never sees photos |
| Reduced stored copy | Database / Storage (bytes produced here, written by Phase 65) | API / Backend | This phase only returns bytes; it never writes a file, so "original never kept" holds by construction |
| Crop, boost, dither | API / Backend (server render path) | — | Frame is dumb: the server prepares the 6-colour image |
| Panel packing / wire bytes | API / Backend | — | Reuses `panel_format.pack_panel`; BYOS serving is Phase 66 |
| Preview of the dithered result | API / Backend (render function reused) | Browser (Phase 67 shows it) | Browser cannot reproduce the exact palette/dither; Phase 64 only guarantees a render function that can also give a PNG preview |
| Crop position and fit setting storage | Database / Storage (Phase 65/67) | — | Phase 64 defines the value type and validation only |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Pillow | 13.0.0 (pinned; `server/.venv` has 13.0.0) | decode, validate, EXIF transpose, ICC, crop/resize, enhance, quantize/dither, JPEG encode | Already the only imaging dependency; every capability needed is in it [VERIFIED: server/requirements.in; ran against server/.venv Pillow 13.0.0] |
| `server.plane.dither` | in repo | `dither_to_full_panel_palette(rgb) -> "P"` Floyd-Steinberg against exactly the 6 `PALETTE_RGB` entries | Existing, tested helper; do not copy or modify [VERIFIED: server/plane/dither.py, server/test_dither.py] |
| `server.panel_format` | in repo | `PALETTE_RGB`, `IDX_*`, `new_canvas`, `pack_panel` | Single source of truth for palette and wire format [VERIFIED: server/panel_format.py] |
| `server.hardware` | in repo | `HardwareProfile.width/height/layout_family`; sizes for tests (legacy key 1200x1600, `sim-landscape-800x480`) | Tests must derive panel sizes from the registry so they cannot drift [VERIFIED: server/hardware.py] |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `PIL.ImageCms` | part of Pillow (littlecms2 present: `features.check("littlecms2") == True`) | Convert embedded ICC (iPhone Display P3) to sRGB before the profile is dropped | Only when an `icc_profile` is present; on any failure assume sRGB |
| pytest / pytest-xdist / pytest-cov | as locked in `server/requirements-dev.txt` | Tests | Existing infra |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| JPEG stored copy | WebP lossy (about 25% smaller) | The repo already carries a "Pillow build without WebP" fallback branch, i.e. WebP encode is not guaranteed; JPEG is universal. WebP is accepted as an *input* only |
| JPEG stored copy | PNG | Several MB at 2048 px for photos: breaks the ~1 MB-per-photo quota |
| `ImageOps.fit` | hand-computed crop box | `fit` is one `resize(box=...)` call, single resample, no intermediate image; the only trap is that it silently resets out-of-range centering to 0.5, so validate first |
| Pillow-only dither | linear-light or Atkinson/other error diffusion in pure Python | Per-pixel Python loops over 1.9 MP are seconds, not 0.03 s, and the existing helper is the established look. Known limit: dithering happens in gamma-encoded space (document it, do not fix it) |
| `pillow-heif` for HEIC | — | New dependency: forbidden by the stack rule. Sniff the `ftyp` brand only to give a precise rejection reason |

**Installation:** none. No new package is introduced by this phase.

**Version verification:** `server/.venv/bin/python -c "import PIL; print(PIL.__version__)"` -> 13.0.0 (system `python3` has 12.3.0 on this machine: always use `server/.venv/bin/python`). Production runs Python 3.14 per `pyproject.toml`; local venv is 3.13. [VERIFIED: local run]

## Package Legitimacy Audit

No external package is installed or added by this phase (Pillow 13.0.0 is already pinned in `server/requirements.in` and hash-locked in `server/requirements.txt`). slopcheck was not run because there is nothing to check; no `npm`/`pip` install is recommended.

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Architecture Patterns

### System Architecture Diagram

```
 raw upload bytes (from Phase 67 route, already size-capped by the HTTP layer)
        |
        v
 normalize(raw) ---------------------------------------------+
   1. len(raw) in (0, MAX_UPLOAD_BYTES]        -> reject too_large / empty
   2. sniff HEIC ftyp (label only)             -> reject heic_unsupported
   3. Image.open(BytesIO, formats=[JPEG,PNG,WEBP])
        UnidentifiedImageError / any error     -> reject not_an_image
        img.format in {JPEG, MPO, PNG, WEBP}   -> else reject unsupported_format
        PNG/WEBP with n_frames > 1             -> reject animated
   4. w*h > MAX_PIXELS (header only, no load)  -> reject too_many_pixels
      min(w,h) < MIN_SIDE                      -> reject too_small
   5. JPEG/MPO: img.draft("RGB", target)       -> cheap reduced decode
      img.load()  (real decode; truncation     -> reject corrupt)
   6. exif_transpose -> ICC->sRGB (best effort) -> flatten alpha on white
      -> mode normalise (16-bit via point, CMYK/L/P via convert) -> RGB
   7. resize so long edge <= STORE_MAX_SIDE (LANCZOS, never upscale)
   8. JPEG encode, no exif/icc/comment; quality ladder, then shrink,
      until len <= STORE_MAX_BYTES
        v
 StoredPhoto(jpeg_bytes, width, height)   <- the ONLY output; original dropped
        |
        |  (Phase 65 writes it under a server-generated name; not here)
        v
 render_photo(stored, (W,H), FitSetting(mode,pos_x,pos_y), PrepParams)
   a. decode stored JPEG (same format allowlist)
   b. fill : ImageOps.fit(size, centering=(pos_x,pos_y))      \  crop + scale in one resample
      bands: ImageOps.contain(size)                            /
   c. prep: autocontrast(cutoff, preserve_tone) blended -> Color(saturation)
   d. dither_to_full_panel_palette(rgb)            -> "P", 6-entry palette
   e. bands only: paste on pf.new_canvas(IDX_WHITE, size) so bands are exact white
        v
 "P" image (W x H, indices 0..5)  --pf.pack_panel-->  wire bytes (W/2 * H)
        \--> .save(PNG)  -> preview bytes (Phase 67)
```

### Recommended Project Structure
```
server/photo/
├── __init__.py     # empty (server/plane and server/net both have one)
├── normalize.py    # PhotoRejected(reason), StoredPhoto, normalize_upload(raw)
├── crop.py         # FitSetting (mode, pos_x, pos_y) + validation
├── prep.py         # PrepParams (frozen defaults) + prepare(rgb, params)
└── render.py       # render_photo(...), render_photo_packed(...), preview_png(...)
server/test_photo_normalize.py
server/test_photo_render.py
server/test_photo_prep.py          # synthetic skin-tone grid, palette/hue properties
server/test_photo_boundaries.py    # subprocess sys.modules check (see Pitfalls)
test-support/photo_samples.py      # procedural images: skin swatches, synthetic face, orientation marker, bomb, CMYK...
scripts/ or `python -m server.photo` trial entry (optional, owner-run; see Skin-tone strategy)
docs/PHOTO-RENDERING.md            # parameters, trial method, results, limits
```
Rationale: a new package keeps the photo render path physically separate from `server/plane/render` (which holds the golden-covered code) and makes the "plane code untouched" check a simple `git diff` over `server/plane` and `server/fixtures/golden`. `server/photo/` imports `server.panel_format` and `server.plane.dither` only; it must not import `server.plane.render`, `companion`, `server.poll_*`. (`server/plane/__init__.py` is empty, so `import server.plane.dither` does not load the renderer; verified by reading the file.)

### Pattern 1: Upload normalisation (strict, bytes in, bytes out)
**What:** One function, no filename parameter, no file I/O, rejection by stable machine codes.
**Example:**
```python
# Source: Pillow 13.0 behaviour verified locally; docs https://pillow.readthedocs.io/en/stable/reference/Image.html
ALLOWED_OPEN = ["JPEG", "PNG", "WEBP"]          # MPO opens through the JPEG entry
ALLOWED_FORMATS = {"JPEG", "MPO", "PNG", "WEBP"}  # what img.format reports

class PhotoRejected(ValueError):
    def __init__(self, reason: str) -> None:       # reason: stable code, maps to EN/FR text later
        super().__init__(reason)
        self.reason = reason

def _open_checked(raw: bytes) -> Image.Image:
    try:
        img = Image.open(io.BytesIO(raw), formats=ALLOWED_OPEN)
    except Image.DecompressionBombError:
        raise PhotoRejected("too_many_pixels") from None
    except Exception:                               # decode boundary: nothing may escape raw
        raise PhotoRejected("not_an_image") from None
    if img.format not in ALLOWED_FORMATS:
        raise PhotoRejected("unsupported_format")
    if img.format in ("PNG", "WEBP") and getattr(img, "n_frames", 1) > 1:
        raise PhotoRejected("animated")             # MPO legitimately has n_frames > 1: do not apply there
    w, h = img.size
    if w * h > MAX_PIXELS:
        raise PhotoRejected("too_many_pixels")
    if min(w, h) < MIN_SIDE:
        raise PhotoRejected("too_small")
    return img
```
Then decode with `draft` for JPEG, `exif_transpose`, colour handling, resize, encode (see Code Examples).

### Pattern 2: Normalised crop position (object-position semantics)
**What:** `FitSetting(mode="fill"|"bands", pos_x=0.5, pos_y=0.5)`. `pos_x`/`pos_y` in [0,1] choose where the crop window sits *within the slack*: 0 = flush left/top, 1 = flush right/bottom, 0.5 = centred. Only the axis that has slack matters for a given target aspect, so one pair of numbers works for the 3:4 portrait panel and the 5:3 landscape panel from the same stored photo. This is exactly `ImageOps.fit(centering=(pos_x, pos_y))` [CITED: pillow.readthedocs.io ImageOps: "(0.0, 0.0) crops from the top left corner, (1.0, 1.0) from the bottom right"]. Moving the crop (Phase 67 drag) is just updating two floats; clamping is implicit because the window can never leave the image.
**When to use:** always for fill. Bands ignore pos (state this in a docstring and test it).
**Validation:** reject non-finite or out-of-[0,1] values with `ValueError` in the constructor. Do NOT pass bad values to `fit`: it silently replaces them (and NaN) with 0.5, which would hide bugs. Store/serialise as plain floats rounded to 4 decimals (hash stability, DB friendliness).
**Why not a normalised rectangle:** a rectangle is aspect-specific; the same rectangle cannot serve two panel aspects. Zoom is not required (smart crop and zoom are future work); if zoom is ever added it is a third scalar `>= 1.0` shrinking the window, compatible with this representation.

### Pattern 3: Render order and bands
`fill`: `ImageOps.fit` -> prep -> dither. `bands`: `ImageOps.contain` -> prep (histogram of the photo area only, so white bands do not skew autocontrast) -> dither -> paste the dithered photo onto `pf.new_canvas(pf.IDX_WHITE, size)` centred. Pasting a "P" image on a "P" canvas copies raw indices, so the result stays within indices 0..5 and the bands are exactly white (verified: a pasted yellow block gave indices {1,2}). Band colour: white (discretion; black is a one-constant alternative, trial it if the owner prefers a gallery look).

### Pattern 4: Render is a pure, deterministic function
Same stored bytes + size + fit + params must give identical output bytes (the BYOS serves content by SHA-256 and the frame skips redraw on an unchanged hash; Phase 66 depends on this). Everything used is deterministic (LANCZOS, `quantize(dither=FLOYDSTEINBERG)` already has a determinism test in `server/test_dither.py`). Do not add randomness, timestamps or dict-ordering dependence. A Pillow upgrade can change decoded pixels slightly and cost one redraw: acceptable, but note it in the doc.

### Anti-Patterns to Avoid
- **Calling the illustration helpers:** `validate_illustration_file` (PNG only, requires alpha, landscape, width >= 1200) and `illustration_normalize` (transparent-bbox crop, PNG) are wrong for photos; importing `server.plane.illustrations` for `ILLUSTRATION_MAX_PIXELS` couples photo code to the plane domain. Define photo constants in the photo package.
- **Mutating Pillow globals** (`Image.MAX_IMAGE_PIXELS`, `ImageFile.LOAD_TRUNCATED_IMAGES`): they are process-wide and the companion process also renders plane/illustration images. Never set them.
- **Using `warnings.catch_warnings()` / `simplefilter("error")` to catch the bomb warning:** it mutates global state and is not thread-safe under `ThreadingHTTPServer`. The app cap (50 MP) is below Pillow's warn threshold (89,478,485 px), so check the cap yourself from the header.
- **Trusting filename, extension or Content-Type:** the normaliser has no such parameter. A PNG named `.jpg` is accepted *because the bytes are a valid PNG*, and is stored as JPEG.
- **`except Exception` outside the single decode boundary:** keep it in `_open_checked`/`_decode` only.
- **Passing `exif=`/`icc_profile=`/`comment=` to `save`:** omit them; verified the stored bytes then contain no `Exif`, no `ICC_PROFILE`, only JFIF.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Format detection | extension/magic-byte sniffing | `Image.open(..., formats=[...])` + `img.format` | Pillow already identifies by content; the allowlist also removes TIFF/EPS(Ghostscript)/PSD etc. decoders from the attack surface |
| Orientation | manual rotate table | `ImageOps.exif_transpose` (applies and drops the orientation tag) [CITED: Pillow ImageOps docs] | All 8 cases, PNG/WebP EXIF too |
| Metadata stripping | parse/blank EXIF | re-encode and pass no `exif`/`icc_profile` to `save` | Verified: GPS IFD, maker tag, ICC and EXIF marker absent from the output bytes |
| Colour management | matrix maths | `ImageCms.profileToProfile(img, src, createProfile("sRGB"), outputMode="RGB")` (note: this Pillow exposes the camelCase name; `profile_to_profile` does not exist in 13.0.0) | Phones tag Display P3; dropping the tag without converting desaturates |
| Crop + scale | slicing + two resizes | `ImageOps.fit(..., centering=...)` / `ImageOps.contain` | One resample, correct rounding |
| Tone stretch | custom histogram code | `ImageOps.autocontrast(img, cutoff=..., preserve_tone=True)` [CITED: Pillow ImageOps docs] | Luminance-based stretch; keeps hue |
| Saturation | HSV loops | `ImageEnhance.Color` | Fast C path |
| 6-colour dither | custom error diffusion | `server.plane.dither.dither_to_full_panel_palette` | Exactly-6-entry palette (a 256-pad is a documented footgun), tested, deterministic |
| Packing | nibble loops | `panel_format.pack_panel` | Vectorised, already the wire contract |
| Decompression-bomb defence | stream decoder limits | header `img.size` check + Pillow's own `DecompressionBombError` | Header check costs nothing and happens before any pixel decode |
| JPEG downscale on decode | decode full then resize | `img.draft("RGB", target_size)` (JPEG/MPO only) | Cuts memory 4x/16x for 48 MP phone photos |

**Key insight:** every hard part of this phase is already a single audited Pillow call; the risk is in the *order* and *limits* around them, which is why the plan should concentrate on tests for those, not on code volume.

## Common Pitfalls

### Pitfall 1: Decompression bomb slips through (or only warns)
**What goes wrong:** A tiny PNG declares a huge canvas. Measured: a 109,283-byte 1-bit PNG at 30000x30000 raises `DecompressionBombError` at `open()`; the same kind of file at 9000x9000 (81 MP) opens silently and would decode to hundreds of MB.
**Why:** Pillow's own limit is 89,478,485 px (warn) / 178,956,970 (error), far above what a 4 GB VPS wants per request.
**How to avoid:** `MAX_PIXELS = 50_000_000` checked from `img.size` right after `open()`, before `draft`/`load`; map `DecompressionBombError` to `too_many_pixels`. Test with a generated 1-bit PNG (a few KB).
**Warning signs:** test for the cap runs for seconds or allocates memory.

### Pitfall 2: Per-channel autocontrast shifts skin hue
**What goes wrong:** `ImageOps.autocontrast(rgb)` stretches R, G, B independently. Measured on synthetic skin tone I: skin hue 29 -> 0 (pinkish red); tone III: 29 -> 42 (yellowish).
**How to avoid:** always `preserve_tone=True` (hue stayed 28..32 for tone I, 29 for III, 21..22 for V, 18..20 for VI in the grid below). Test asserts hue of a skin patch is preserved within a few degrees after prep.
**Warning signs:** faces look salmon-pink or green-yellow in the contact sheet.

### Pitfall 3: Full-strength autocontrast + saturation over-cooks skin
**What goes wrong:** On a dull/narrow-range scene, full-strength stretch moves a mid tone from (169,143,119) to (217,161,109) and saturation 1.3 on top to (230,157,90); G and B collapse so the dither goes yellow/red-dominated. Dark tones (V, VI) lose the brown-vs-black separation.
**How to avoid:** blend the stretched image with the original (`Image.blend(orig, stretched, strength)`), start at strength 0.8, saturation 1.2, hard ceiling 1.3 in the allowed range until the trial says otherwise.

### Pitfall 4: 16-bit grayscale PNG renders white
**What goes wrong:** `Image.convert("RGB")` on mode `I;16` clips instead of scaling: a 40000/65535 grey became (255,255,255).
**How to avoid:** for modes `I;16*`/`I`, use `img.point(lambda v: v / 256, "L")` first (verified: 40000 -> 156), then `convert("RGB")`. Add a test with a 16-bit PNG.

### Pitfall 5: `draft()` does not always shrink
**What goes wrong:** `draft("RGB", (2048, 2048))` on a 4000x3000 JPEG left it at 4000x3000 (it only picks a scale that stays >= the requested size on both axes).
**How to avoid:** request the exact aspect-correct target `(ceil(w*s), ceil(h*s))` with `s = STORE_MAX_SIDE / max(w, h)`. Verified: 8000x6000 -> request 2048x1536 -> decoded at 4000x3000 (1/2 scale, 12 MP, ~36 MB RGB instead of ~144 MB). 12 MP phone photos will not shrink on decode; that is fine. Call `draft` before `load`, and before `exif_transpose`.

### Pitfall 6: MPO and animated formats
**What goes wrong:** Many phone JPEGs are MPO (`img.format == "MPO"`, `n_frames == 2`), so (a) an allowlist of `{"JPEG"}` on `img.format` rejects valid photos and (b) an "n_frames > 1 means animated" rule rejects them too.
**How to avoid:** `ALLOWED_FORMATS` includes `MPO`; apply the animated rule only to PNG and WebP (an animated WebP measured `n_frames == 2`). Always use the first frame only.

### Pitfall 7: Wrong colours from phone profiles
**What goes wrong:** iPhone JPEGs are tagged Display P3 [ASSUMED]; dropping the profile without conversion makes colours look flat, and the later saturation boost would then be compensating for a bug.
**How to avoid:** convert with `ImageCms.profileToProfile` when `info["icc_profile"]` exists; on `OSError`/`PyCMSError` (garbage profile, Lab profile on RGB data, truncated profile; all three observed) assume sRGB and continue. Test: garbage ICC bytes must not reject the upload.

### Pitfall 8: Size ladder never fits
**What goes wrong:** Worst-case noise at 2048x1536 is 1.3-2.1 MB at any sane quality. A single fixed quality cannot honour "about 1 MB".
**How to avoid:** quality ladder (88, 82, 76, 70, 62) at the current size, then shrink the long edge by 0.85 and repeat; measured noise: 1638x1228 q76-82 is ~0.8-1.0 MB, 1310x983 q82 is 592 KB, so the loop always terminates. Real photos at 2048x1536 q88 are expected to be 0.3-0.9 MB [ASSUMED; the "smooth" synthetic image was 169 KB at q88]. Test the ladder with a noise image.

### Pitfall 9: Changing the plane tree by accident
**What goes wrong:** editing `server/plane/dither.py` (e.g. adding a photo function) or `panel_format.py` risks the golden fixtures.
**How to avoid:** import, do not edit. Phase gate: `git diff --stat main -- server/fixtures/golden server/plane server/panel_format.py hardware firmware` must be empty (only `pyproject.toml` mypy list, new files, docs and tests change). Existing golden/render tests must pass unmodified.

### Pitfall 10: Real faces in the repository
**What goes wrong:** committing a portrait fixture or a trial output.
**How to avoid:** all test images are generated in memory or under `tmp_path`; no binary image fixtures are committed; trial outputs go to a temp/scratch dir, never the repo; the owner's real-portrait trial is run locally and only a *written* summary enters `docs/PHOTO-RENDERING.md`.

### Pitfall 11: Concurrency memory
**What goes wrong:** the companion is a `ThreadingHTTPServer`; several simultaneous 50 MP PNG decodes (~150 MB each) on a 4 GB box next to other units.
**How to avoid:** Phase 64 stays a pure function; record in the doc that the Phase 67 route must serialise normalisation (e.g. a process-wide `threading.BoundedSemaphore(2)`) and apply the byte cap while reading the body (the existing `request_body.drain_capped_body` pattern). The existing 4 MiB illustration cap is too small for phone photos (see Open Questions).

## Code Examples

### Decode, normalise, encode (shape; each helper under 80 lines)
```python
# Source: verified against Pillow 13.0.0 in server/.venv
def _to_rgb(img: Image.Image) -> Image.Image:
    img = ImageOps.exif_transpose(img)                    # applies and removes Orientation
    if img.mode in ("I;16", "I;16L", "I;16B", "I"):
        img = img.point(lambda v: v / 256, "L")           # convert() would clip, not scale
    if "transparency" in img.info or img.mode in ("RGBA", "LA", "P", "PA"):
        rgba = img.convert("RGBA")
        flat = Image.new("RGB", rgba.size, (255, 255, 255))
        flat.paste(rgba, mask=rgba.getchannel("A"))       # transparent pixels become white
        return flat
    return img.convert("RGB")                             # L, CMYK, RGB, 1

def _icc_to_srgb(img: Image.Image, icc: bytes | None) -> Image.Image:
    if not icc:
        return img
    try:
        src = ImageCms.ImageCmsProfile(io.BytesIO(icc))
        return ImageCms.profileToProfile(img, src, ImageCms.createProfile("sRGB"), outputMode="RGB")
    except (OSError, ImageCms.PyCMSError):
        return img                                        # unusable profile: treat as sRGB
```
Order: read `icc = img.info.get("icc_profile")` *before* `exif_transpose` (which may drop info), convert to RGB first, then ICC, then flatten alpha.

### Store with a size ladder
```python
def _encode_within(img: Image.Image) -> bytes:
    while True:
        for quality in QUALITY_LADDER:                    # (88, 82, 76, 70, 62)
            buf = io.BytesIO()
            img.save(buf, "JPEG", quality=quality, optimize=True)   # no exif/icc/comment
            if buf.tell() <= STORE_MAX_BYTES:
                return buf.getvalue()
        w, h = img.size
        img = img.resize((max(1, round(w * 0.85)), max(1, round(h * 0.85))), Image.LANCZOS)
```
(Terminates: dimensions strictly shrink and size is monotonic in pixels.)

### Render
```python
def render_photo(stored: bytes, size: tuple[int, int], fit: FitSetting = FitSetting(),
                 params: PrepParams = DEFAULT_PREP) -> Image.Image:
    src = _open_stored(stored)                            # same allowlist; JPEG only
    if fit.mode == "fill":
        framed = ImageOps.fit(src, size, Image.LANCZOS, centering=(fit.pos_x, fit.pos_y))
        return dither.dither_to_full_panel_palette(prepare(framed, params))
    inner = ImageOps.contain(src, size, Image.LANCZOS)
    dithered = dither.dither_to_full_panel_palette(prepare(inner, params))
    canvas = pf.new_canvas(pf.IDX_WHITE, size)
    canvas.paste(dithered, ((size[0] - inner.width) // 2, (size[1] - inner.height) // 2))
    return canvas
```
Validate `size`: positive, even width (the existing `pack_panel` requires even width), upper bound to protect memory (<= 2400 on either axis is ample for current hardware; assert against registry sizes in tests).

### Pre-processing
```python
def prepare(img: Image.Image, p: PrepParams) -> Image.Image:
    stretched = ImageOps.autocontrast(img, cutoff=p.cutoff, preserve_tone=True)
    mixed = Image.blend(img, stretched, p.strength)
    return ImageEnhance.Color(mixed).enhance(p.saturation)
```

## Pre-processing parameters to try (starting values, not final)

Run on synthetic scenes (below). The numbers come from this research's own proxy experiment and are MEDIUM/LOW confidence until the trial; the owner's earlier visual trials (concept brief) only establish that "auto-contrast and saturation before dithering" beats plain dithering.

| Parameter | Start (default) | Range to try | Notes |
|-----------|-----------------|--------------|-------|
| autocontrast `cutoff` (%) | 1.0 | 0.5, 1, 2 | 0 over-reacts to a single dark or bright pixel |
| `preserve_tone` | True (fixed) | — | per-channel mode shifts skin hue (measured) |
| blend `strength` of the stretch | 0.8 | 0.5, 0.8, 1.0 | 1.0 over-cooks dull scenes; 0.6 is gentler on tone III-V |
| `saturation` (ImageEnhance.Color) | 1.2 | 1.0, 1.15, 1.3, 1.5 | skin risk begins about 1.3; 1.5 measurably worse (below) |
| contrast beyond autocontrast | none | 1.0-1.1 only if needed | measured to worsen dither fidelity for little gain |
| sharpening after downscale | none | optional `UnsharpMask(radius 1, percent 60)` | untested; try only if the contact sheet looks soft |
| resample | LANCZOS | — | one constant |

Measured proxy (synthetic gradient-shaded face on a banded backdrop, `preserve_tone=True`, cutoff 1; "fidelity" = mean absolute RGB difference between the 6px-box-blurred prepped image and the blurred dithered image inside the skin mask, lower is better; not on-glass):

| Skin tone (RGB base) | strength 0.6, sat 1.0 | strength 0.6, sat 1.3 | strength 1.0, sat 1.3 | strength 0.6, sat 1.5 |
|----------------------|-----------------------|-----------------------|-----------------------|-----------------------|
| I (255,224,196) | 3.5 | 5.2 | 5.6 | 6.0 |
| III (224,172,124) | 2.1 | 4.9 | 6.7 | 7.9 |
| V (141,85,54) | 3.1 | 6.7 | 8.5 | 9.0 |
| VI (80,50,36) | 1.9 | 3.7 | 4.9 | 5.0 |

Reading: error roughly doubles from sat 1.0 to 1.5 and strength 1.0 is worse than 0.6 on mid and dark tones; hue stays put with `preserve_tone`. On a *dull* scene the same settings lifted skin much more (tone III base (169,143,119) -> (217,161,109) at strength 1.0), which is where the stretch helps and also where it can overshoot, hence the blend. Palette share observed inside skin regions with no pre-processing: light tones dither to white+yellow+red, tone V to red+green+black, tone VI to black+red+green (green speckle in dark skin is a palette limit to record, not to fix).

## Skin-tone test strategy (no real people in the repository)

1. **Generator** `test-support/photo_samples.py` (procedural, stdlib+Pillow): six flat swatches for Fitzpatrick-like tones I-VI (starting RGB: I (255,224,196), II (241,194,155), III (224,172,124), IV (198,134,90), V (141,85,54), VI (80,50,36); these are common approximations of the emoji-modifier/Fitzpatrick palette [ASSUMED, document as "illustrative, not a standard"]), plus a **synthetic face scene**: radial-gradient shaded ellipse (light from upper left) on a graded backdrop with a dark "hair" ellipse and a bright "shirt" band, in two variants (full tonal range, dull/low-contrast via `Image.blend` with mid grey). These cover what matters for dithering: smooth gradients on skin, adjacent dark and bright regions, and low-contrast input. They are not photographs of anyone.
2. **Grid**: tones x scene variants x parameter combos x panel sizes (1200x1600 and 800x480, both fit modes). Output: a contact sheet PNG per tone written to a scratch dir (never committed) and a table of measures: skin-region mean RGB and hue before/after prep, palette-index shares, blurred fidelity.
3. **Automated assertions** (in `server/test_photo_prep.py`, run in seconds): hue of the skin patch after `prepare` within +-6 degrees of the source hue for every tone at default params; output of the full render uses only indices 0..5; skin patch is not one flat index (dither actually mixes) for tones I-V; default saturation <= 1.3. These guard regressions; they do not prove beauty.
4. **Human step (PHOTO-04's real content)**: the owner looks at the contact sheets (browser/monitor, nominal colours, as the repo already warns they are not colour-accurate) and, if hardware is at hand, at the portrait frame. The owner may also run the same render CLI on *their own* local portraits or public-domain portraits kept outside the repo and outside git, and reports verdicts in words. This is a `checkpoint:human-verify` in the plan; automated tests cannot judge faces.
5. **Optional trial entry point**: `python3 -m server.photo` (or a script) taking `--in FILE --panel portrait|landscape --fit fill|bands --pos-x --pos-y --out DIR`, writing a preview PNG per panel. Cheap (the render function exists) and it is what makes step 4 possible without committing anything. Keep its `main` under the function-size gate.
6. **Recording** in `docs/PHOTO-RENDERING.md` (English; created before the parameters are declared final): the frozen parameter table (value, range tried, why), method (this section), results per tone and panel size, visual verdict and date, known limits (6 colours: faces become speckled yellow/red/white; dark skin shows green/red/black dots; banding in smooth gradients; dithering in gamma space; palette RGBs are nominal and the on-glass blue/green are more muted; nothing measured with a colorimeter), what was *not* tried (real people on real glass unless the owner did), how to re-run. Verification is a plan checklist step (file exists, sections present, parameters in the doc equal the constants in `prep.py`); a test must not read the doc text. A mismatch check can be behavioural: a test that asserts `DEFAULT_PREP` equals the literal values listed in the test itself, forcing a deliberate edit when they change.
7. **Sequencing**: generator and CLI first -> grid run -> owner review -> choose values -> write the doc -> set `DEFAULT_PREP` to the frozen values in the same change that adds the doc. Before that point the defaults are explicitly provisional (a docstring says "values are fixed by the skin-tone record in docs/PHOTO-RENDERING.md"; no IDs).

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `ImageOps.autocontrast` per channel | `preserve_tone=True` (luminance-based) | Pillow 8.2.0 [CITED: Pillow ImageOps docs] | Keeps hue; required for skin |
| `Image.open(fp)` trying all plugins | `Image.open(fp, formats=[...])` allowlist | long-standing parameter [CITED: Pillow Image docs] | Smaller decoder attack surface |
| snake_case `ImageCms.profile_to_profile` | this Pillow still exposes `profileToProfile` | verified in 13.0.0 | Use the camelCase name; guard with a test that runs the ICC path |

**Deprecated/outdated:** anything relying on `Image.MAX_IMAGE_PIXELS = None` (never do this); `LOAD_TRUNCATED_IMAGES = True` (never do this).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Photo upload byte cap of 12 MiB and pixel cap of 50 MP are the right limits for the owner's phone photos | Summary / Open Questions | Too low: valid phone photos rejected; too high: more memory per request. Owner/plan must confirm |
| A2 | Stored copy: JPEG, long edge 2048, <= 1,000,000 bytes serves both panels adequately | Architecture | If portraits of 16:9 panoramas look too soft, raise the long edge to 2400 (cost: larger files against the ~1 MB quota) |
| A3 | iPhone photos carry Display P3 profiles and iOS browsers hand JPEG to `<input type=file>` rather than HEIC | Pitfall 7 / Phase 67 note | If HEIC reaches the server it is rejected with `heic_unsupported`; Phase 67 must set `accept` to JPEG/PNG/WebP and word the message |
| A4 | Skin RGB swatches are adequate illustrative approximations of Fitzpatrick tones | Skin-tone strategy | Only affects the synthetic trial's coverage; the doc labels them illustrative |
| A5 | Real photos at 2048x1536 q88 are mostly 0.3-0.9 MB | Pitfall 8 | If many exceed 1 MB the ladder lowers quality/size more often; harmless but visible |
| A6 | Starting parameters (cutoff 1, strength 0.8, saturation 1.2) are near the best defaults | Parameters | Explicitly provisional until the owner's trial; the plan must not freeze them earlier |
| A7 | Rejecting animated PNG/WebP (rather than taking frame 1) is the preferred behaviour | Pattern 1 | Owner-visible product choice; taking frame 1 is a trivial change |
| A8 | Band colour white is preferred | Pattern 3 | One-constant change |

## Open Questions

1. **Upload size and pixel limits (A1).**
   - Known: the existing illustration cap is 4 MiB (`MAX_ILLUSTRATION_UPLOAD_BYTES`), too small for typical 12-50 MP phone photos; 4 GB RAM VPS; stored copy is bounded separately at ~1 MB.
   - Unclear: the owner's actual photo sources.
   - Recommendation: constants `PHOTO_MAX_UPLOAD_BYTES = 12 MiB`, `PHOTO_MAX_PIXELS = 50_000_000`, `PHOTO_MIN_SIDE = 200`; named in one place so the owner can change them; ask the owner to confirm in the plan review.
2. **Is a stored long edge of 2048 px acceptable, or does the owner want to keep more for future larger panels?** Recommendation: 2048; the panels are 1200x1600 and 800x480, and the ~1 MB quota dominates.
3. **HEIC.** Recommendation: unsupported (no new dependency), with a distinct rejection reason; Phase 67 handles the wording and the file input `accept`.
4. **Animated PNG/WebP: reject or use first frame (A7)?** Recommendation: reject with a clear reason.
5. **Does the owner want to look at real portraits during the PHOTO-04 trial, and on the physical frame?** The plan needs a human checkpoint either way; without it the doc must say real faces were not tried.
6. **Preview ownership (Phase 67):** server-rendered preview is strongly indicated (exact palette and dither), which only requires this phase to expose `render_photo` and a PNG preview helper. Confirm at Phase 67 discuss time.
7. **Concurrency guard location (Phase 67):** semaphore in the route vs inside `normalize_upload`. Recommendation: in the route, keeping this phase pure.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `server/.venv/bin/python` | all tests and gates | yes | Python 3.13, Pillow 13.0.0 | — |
| Pillow JPEG / PNG / WebP codecs | normalise + tests that build WebP/PNG inputs | yes | libjpeg-turbo 6.2, WebP yes | — |
| Pillow littlecms2 (`ImageCms`) | ICC to sRGB | yes | `features.check("littlecms2") == True` | on any failure the code assumes sRGB (also the runtime behaviour) |
| System `python3` | not to be used | 3.13.18 with Pillow 12.3.0 | differs from the pinned lock | use the venv |
| Production Python 3.14 | runtime | not available locally | — | CI/deploy cover it; avoid 3.13-only syntax |
| Network | none needed | pytest-socket blocks it | — | — |

**Missing dependencies with no fallback:** none.
**Missing dependencies with fallback:** none.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (minversion 9.0) with xdist, cov, pytest-socket; config in `pyproject.toml` (`--import-mode=importlib`, `pythonpath = [".", "test-support"]`) |
| Config file | `pyproject.toml` |
| Quick run command | `server/.venv/bin/python -m pytest server/test_photo_normalize.py server/test_photo_render.py server/test_photo_prep.py server/test_photo_boundaries.py -q --no-cov -p no:cacheprovider` |
| Full suite command | `./scripts/run-all-tests.sh` (CI-equivalent, enforces `fail_under = 93`) |
| Other gates | `server/.venv/bin/ruff check`, mypy per `pyproject.toml`, `server/.venv/bin/python scripts/check_function_size.py check --max 80 server stub-server`, `server/.venv/bin/python scripts/check_comment_history.py check` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PHOTO-01 | Rejects: empty, over byte cap, HTML bytes, GIF, BMP/TIFF/SVG/PDF bytes, truncated JPEG, bomb PNG (few KB declaring > cap), animated WebP, tiny image, HEIC-brand bytes; each with the expected stable reason | unit (parametrised) | `pytest server/test_photo_normalize.py -k reject -x` | Wave 0 |
| PHOTO-01 | Accepts JPEG, PNG (RGB, RGBA, P, L, 16-bit), WebP, MPO, CMYK JPEG; output is JPEG, RGB, long edge <= cap, bytes <= cap | unit | `pytest server/test_photo_normalize.py -k accept` | Wave 0 |
| PHOTO-01 | EXIF orientation 1-8 produce an upright result (asymmetric marker image) | unit | `-k orientation` | Wave 0 |
| PHOTO-01 | Metadata stripped: sentinel strings placed in EXIF (incl. GPS IFD), XMP/comment, ICC and PNG text chunk are absent from output bytes; `Image.open(out).getexif()` empty; trailing garbage after the image end is gone | unit | `-k metadata` | Wave 0 |
| PHOTO-01 | A misleading name/type cannot matter: PNG bytes accepted as such regardless of caller; function accepts bytes only; call in a `tmp_path` cwd leaves the directory empty and the original sentinel is not in the result ("original not kept") | unit | `-k original_not_kept` | Wave 0 |
| PHOTO-01 | Garbage / Lab ICC does not reject; P3-like profile is converted (pixel changes, sRGB profile of identity leaves pixels) | unit | `-k icc` | Wave 0 |
| PHOTO-01 | Size ladder: noise image 3000x2000 ends <= 1,000,000 bytes; 8000x6000 flat JPEG decodes via draft and finishes quickly | unit | `-k ladder` | Wave 0 |
| PHOTO-02 | For both sizes (taken from `hardware` registry: legacy key and `sim-landscape-800x480` with `SKYPANE_SIM_HARDWARE` mapping): mode "P", exact size, index set subset of {0..5}, `pack_panel` length == w/2*h, every nibble in `INDEX_TO_NIBBLE.values()`; container round-trip via `image_container` accepted | unit | `pytest server/test_photo_render.py -k panel` | Wave 0 |
| PHOTO-02 | Deterministic: two renders equal bytes; input bytes unchanged | unit | `-k deterministic` | Wave 0 |
| PHOTO-02 | Render path separation: in a fresh subprocess, `import server.photo.render` leaves `server.plane.render` and `companion` out of `sys.modules` | subprocess (pattern from `server/test_import_boundaries.py`) | `pytest server/test_photo_boundaries.py` | Wave 0 |
| PHOTO-02 | Plane unchanged: existing golden tests pass unmodified; `git diff` over `server/plane server/fixtures/golden` is empty | existing + shell | `pytest server/test_golden_render.py server/test_golden_giant_render.py server/test_render.py server/test_dither.py`; `git diff --exit-code -- server/fixtures/golden server/plane server/panel_format.py` | exists |
| PHOTO-03 | Fill: left-red/right-blue source, portrait panel, `pos_x=0` mostly red, `1` mostly blue, `0.5` both, and the three outputs differ; landscape panel uses `pos_y` with a top/bottom marker | unit | `pytest server/test_photo_render.py -k crop` | Wave 0 |
| PHOTO-03 | Bands: whole photo visible (marker at all four corners of the photo area), bands exactly index 1, photo area size equals `contain` size, `pos` has no effect; same stored bytes render for both sizes | unit | `-k bands` | Wave 0 |
| PHOTO-03 | `FitSetting` rejects NaN, inf, -0.1, 1.1, unknown mode; default is fill 0.5/0.5 | unit | `-k fitsetting` | Wave 0 |
| PHOTO-04 | Prep properties on the synthetic tones I-VI: hue preserved, saturation default <= 1.3, output only palette indices, skin not a single flat index (tones I-V) | unit | `pytest server/test_photo_prep.py` | Wave 0 |
| PHOTO-04 | Record exists and matches frozen defaults | manual checklist (plan verify step) + a test that pins `DEFAULT_PREP` literals | `pytest server/test_photo_prep.py -k defaults_pinned` | Wave 0 (+ manual) |
| PHOTO-04 | Owner reviewed contact sheets / own portraits | manual-only: faces cannot be judged by a test | checkpoint:human-verify | n/a |

### Sampling Rate
- **Per task commit:** the quick run command above (target well under 30 s; the heaviest cases are the 8000x6000 flat JPEG and the 1200x1600 dither at 0.03 s).
- **Per wave merge:** quick run + ruff + mypy + function-size + comment-history + the golden/render tests above.
- **Phase gate:** `./scripts/run-all-tests.sh` green (coverage >= 93%), the `git diff --exit-code` plane check, and the PHOTO-04 doc checklist signed off before `/gsd:verify-work`.

### Wave 0 Gaps
- [ ] `test-support/photo_samples.py` - procedural builders (skin swatches, synthetic face scenes, orientation marker with all 8 EXIF variants, left/right and top/bottom halves, bomb PNG, CMYK/16-bit/animated WebP/MPO/HEIC-brand bytes)
- [ ] `server/test_photo_normalize.py`, `server/test_photo_render.py`, `server/test_photo_prep.py`, `server/test_photo_boundaries.py`
- [ ] `pyproject.toml` `[tool.mypy]` file list and strict override: add the four new modules (the only edit outside new files)
- [ ] `docs/PHOTO-RENDERING.md` skeleton (parameters filled only after the trial)
- Framework install: none (existing).

## Security Domain

`security_enforcement` is enabled in `.planning/config.json` (ASVS level 1, block on high).

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no (no route in this phase) | Phase 65/67 |
| V3 Session Management | no | — |
| V4 Access Control | no (storage and visibility are Phase 65) | — |
| V5 Input Validation | yes | allowlist of decoders, byte cap, header pixel cap, real decode, re-encode; reason codes, no echo of attacker-controlled strings (no filenames, no Pillow messages) in results or logs |
| V6 Cryptography | no (no secrets; do not hash with custom schemes; any content hash is Phase 65/66 via `hashlib.sha256`) | — |
| V12 Files and resources | yes | original never persisted; metadata (GPS) stripped; server-generated names (Phase 65); no path ever built from input |

### Known Threat Patterns for stdlib + Pillow image upload

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Decompression bomb (tiny file, huge canvas) | Denial of service | `PHOTO_MAX_PIXELS` from header before `load`; catch `DecompressionBombError`; draft for JPEG; caller-side concurrency bound |
| Format confusion / polyglot (file named .jpg that is HTML, SVG, EPS, TIFF, GIF) | Tampering, elevation | `Image.open(formats=[JPEG, PNG, WEBP])`, content-only identification, full re-encode (trailing/embedded payloads dropped) |
| Decoder bug in an exotic plugin | Elevation | allowlist keeps TIFF/EPS/PSD/etc. out; pin Pillow (already hash-locked) |
| GPS / device metadata leak in stored copy | Information disclosure | strip all metadata; EXIF GPS sentinel test |
| Path traversal via filename | Tampering | no filename parameter in the API |
| Memory exhaustion through concurrency | Denial of service | pure function + Phase 67 semaphore; document |
| Truncated/corrupt file crashes worker | Denial of service | full `load()`; `LOAD_TRUNCATED_IMAGES` left False (verified: truncated JPEG raises `OSError`) |
| Log leakage of user content | Information disclosure | log reason code only, never bytes, names, EXIF |

## Sources

### Primary (HIGH confidence)
- Local execution against Pillow 13.0.0 in `server/.venv` (format allowlist, MPO behaviour, bomb thresholds, EXIF/GPS stripping, ICC functions and failure types, 16-bit conversion, draft behaviour, JPEG size ladder measurements, P-on-P paste, dither/pack timings, `ImageOps.fit` source).
- Repo files read: `server/plane/dither.py`, `server/test_dither.py`, `server/panel_format.py`, `server/hardware.py`, `server/image_container.py`, `docs/IMAGE-FORMAT.md`, `companion/illustration_normalize.py`, `server/plane/illustrations.py` (`validate_illustration_file`, `ILLUSTRATION_MAX_PIXELS`), `companion/post_actions.py` (`_handle_illustration_replace`, `parse_single_uploaded_file`), `companion/request_body.py`, `pyproject.toml`, `scripts/check_function_size.py`, `scripts/check_comment_history.py`, `scripts/ci_shards.py`, `companion/test_suite_guards.py`, `deploy/README.md` (2 vCPU / 4 GB RAM).
- Pillow docs: https://pillow.readthedocs.io/en/stable/reference/ImageOps.html (autocontrast `preserve_tone` since 8.2.0, `exif_transpose`, `fit` centering, `contain`); https://pillow.readthedocs.io/en/stable/reference/Image.html (`Image.open` `formats`, `draft` JPEG/MPO only, `MAX_IMAGE_PIXELS` warning/error at 1x/2x).

### Secondary (MEDIUM confidence)
- The synthetic skin-tone experiment results (proxy metrics, reproducible with the generator this phase adds; scratch scripts were run outside the repo).

### Tertiary (LOW confidence)
- Fitzpatrick tone RGB approximations, iPhone Display P3 tagging and iOS HEIC-to-JPEG behaviour (training knowledge, marked [ASSUMED] above).

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - no new packages; every call exercised on the pinned Pillow.
- Architecture: HIGH - package layout, reuse and crop representation follow directly from existing helpers and measured behaviour.
- Pre-processing values: MEDIUM/LOW - proxy metrics only; the PHOTO-04 owner review is the real gate.
- Pitfalls: HIGH for the Pillow behaviours (each reproduced), MEDIUM for real-world file-size expectations.

**Research date:** 2026-11-10
**Valid until:** 2026-12-10 (stable; re-check only if Pillow is bumped, since decode output and the `ImageCms` names are version-sensitive)
