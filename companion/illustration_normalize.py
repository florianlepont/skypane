#!/usr/bin/env python3
"""companion/illustration_normalize.py — server-side aircraft-illustration
normalization for the companion Airlines gallery (quick task 260902-req-02,
sibling to 260902-req plan 01's panel-side fix in `server/plane/render.py`).

`companion/pages/airlines_page.py` used to render each of the 43 vendored
per-airline illustrations as a plain `<img>` at `width: 100%; height: auto`,
streaming the raw source PNG bytes verbatim (`Handler._serve_illustration_image()`
in `companion/app.py`). Every source file carries its own, differently-sized
transparent padding around the painted aircraft, so the gallery inherited that
inconsistency card-for-card: measured across the 43 files, the painted
content's aspect ratio spans 2.97:1 (`chalair-aviation.png`) to 4.98:1
(`amelia-embraer.png`).

This module fixes that server-side, at the route, by cropping each source
image to its *painted* content (not its raw alpha bbox — see
`server.plane.render._opaque_bbox()`'s own docstring for why those differ),
then re-centring that crop into one shared output frame every card renders
into identically.

Deliberate constraint: this module imports `server.plane.render`'s
`_opaque_bbox()` / `_threshold_alpha()` (and, transitively,
`ILLUSTRATION_ALPHA_THRESHOLD`) rather than reimplementing bbox detection or
defining a second alpha-threshold constant. The panel already solved
"where does the aircraft actually end" once — the originating debug session
(`illustration-crop-text-margin`) is precisely the story of a *second*,
differently-thresholded measurement silently drifting from the first. This
module must never become a second implementation for that same measurement to
drift against; it may only ever import the one at `server/plane/render.py`.
This is why this module deliberately does NOT edit `server/plane/render.py`
itself (that stays plan 01's sibling territory) and instead only reads from
it.
"""
import functools
import io
import os

from PIL import Image

from server.plane import render as panel_render

# Painted-content aspect ratios across all 43 vendored illustrations range
# 2.97:1 (chalair-aviation) to 4.98:1 (amelia-embraer), median 3.42:1
# (measured 2026-09-02 via server.plane.render._opaque_bbox() over every
# file in server/assets/icons/illustrations/). Because every crop is scaled
# to FIT INSIDE this box (never crop-to-fill — clipping a wingtip to fill a
# frame is worse than the padding inconsistency this module fixes), the
# choice of target ratio can never cause clipping; it only decides how much
# transparent letterbox space each file gets. A target near the widest
# ratio would letterbox every narrower file with dead horizontal space on
# both sides; the measured median instead spreads that dead space evenly
# across the whole distribution. 900x263 (3.4221:1) sits at that median,
# rounded to clean output pixel dimensions.
ILLUSTRATION_TARGET_WIDTH = 900
ILLUSTRATION_TARGET_HEIGHT = 263
ILLUSTRATION_TARGET_SIZE = (ILLUSTRATION_TARGET_WIDTH, ILLUSTRATION_TARGET_HEIGHT)


def normalized_png_bytes(path):
    """Return PNG bytes for the illustration at `path`, tight-cropped to its
    opaque (painted) bbox — via `panel_render._opaque_bbox()`, the same
    measurement `server/plane/render.py` paints against, never a
    reimplementation of it. The whole source image is scaled (LANCZOS,
    matching `panel_render._resize_illustration()`) so that its painted
    content fits inside `ILLUSTRATION_TARGET_SIZE` preserving aspect
    ratio, the opaque bbox is re-measured against that resized image (not
    against the pre-resize crop — see the resize-order comment below),
    and that tight region is pasted centred onto a fully transparent
    canvas of exactly `ILLUSTRATION_TARGET_SIZE`.

    A file whose opaque bbox comes back `None` (nothing painted above the
    alpha threshold — a fully transparent or entirely sub-threshold image)
    falls back to the whole source image instead of raising, mirroring
    `panel_render.IllustrationPlacement`'s own documented `rect` fallback
    for the same condition.

    Every output has identical pixel dimensions
    (`ILLUSTRATION_TARGET_SIZE`), so the caller never needs to special-case
    a per-file size.
    """
    with Image.open(path) as source:
        rgba = source.convert("RGBA")

    # Deliberately mirrors panel_render._resize_illustration()'s own shape:
    # resize the WHOLE source image first (LANCZOS, full surrounding
    # context on every edge), and only measure/crop to the opaque bbox
    # AFTER that resize — never crop-then-resize. Cropping tight to the
    # bbox before resizing starves LANCZOS of context exactly at the
    # painted edge, which was measured (during this module's own test
    # development) to shift the re-measured post-resize bbox by up to 2px
    # on one side only, breaking the "centred within 1px" contract for a
    # handful of files (air-europa.png among them). Resizing first, the
    # way the panel itself does, does not have that problem: the only
    # remaining source of offset error is the centring division's integer
    # rounding, at most 0.5px per axis.
    src_w, src_h = rgba.size
    bbox = panel_render._opaque_bbox(rgba)
    content_w, content_h = (bbox[2] - bbox[0], bbox[3] - bbox[1]) if bbox is not None else (src_w, src_h)

    target_w, target_h = ILLUSTRATION_TARGET_SIZE
    scale = min(target_w / content_w, target_h / content_h)
    resized_w = max(1, round(src_w * scale))
    resized_h = max(1, round(src_h * scale))
    resized = rgba.resize((resized_w, resized_h), Image.LANCZOS)

    resized_bbox = panel_render._opaque_bbox(resized)
    painted = resized.crop(resized_bbox) if resized_bbox is not None else resized
    painted_w, painted_h = painted.size

    canvas = Image.new("RGBA", ILLUSTRATION_TARGET_SIZE, (0, 0, 0, 0))
    offset = ((target_w - painted_w) // 2, (target_h - painted_h) // 2)
    canvas.paste(painted, offset, painted)

    buffer = io.BytesIO()
    canvas.save(buffer, format="PNG")
    return buffer.getvalue()


@functools.lru_cache(maxsize=None)
def _cached_normalized_png_bytes(path, mtime_ns):
    # `mtime_ns` is part of the cache key purely so a replaced asset on
    # disk is picked up on the next call — it is never read for any other
    # purpose. The 43 vendored files are therefore normalized once per
    # process, not once per request.
    return normalized_png_bytes(path)


def cached_normalized_png_bytes(path):
    """`normalized_png_bytes(path)`, cached per process and keyed on `path`
    plus the file's current mtime (nanoseconds) — a replaced asset on disk
    still gets picked up, since a changed mtime is a cache miss. Raises
    `OSError` if `path` cannot be stat'd, exactly like `normalized_png_bytes`
    would raise opening a missing file — callers already handle that
    (`Handler._serve_illustration_image()`'s existing `except OSError`
    branch).
    """
    mtime_ns = os.stat(path).st_mtime_ns
    return _cached_normalized_png_bytes(path, mtime_ns)
