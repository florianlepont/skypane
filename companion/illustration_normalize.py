#!/usr/bin/env python3
"""Server-side aircraft-illustration normalization for the companion
Airlines gallery. Source files carry differently-sized padding, so
rendering them raw gave an inconsistent card-for-card aspect ratio
(2.97:1 to 4.98:1). Fixed by cropping each to its *painted* bbox and
re-centring into one shared output frame.

Imports `server.plane.render._opaque_bbox()` rather than
reimplementing bbox detection, so the panel and gallery can never
silently drift on "where does the aircraft end".
"""
import functools
import io
import os

from PIL import Image

from server.plane import render as panel_render

# Width 450: the card image maxes at 325px mobile / 224px desktop, so a
# larger frame is pure oversampling. Height matches the vendored set's
# median aspect ratio (3.42:1), never independently chosen: crops always
# scale to fit inside this box (never crop-to-fill), so the ratio only
# affects letterbox space, never clipping.
ILLUSTRATION_TARGET_WIDTH = 450
ILLUSTRATION_TARGET_HEIGHT = 132
ILLUSTRATION_TARGET_SIZE = (ILLUSTRATION_TARGET_WIDTH, ILLUSTRATION_TARGET_HEIGHT)

# Above the 43 vendored assets plus manual-resolution overrides, so every
# normal installation's whole illustration set stays resident; bounded
# rather than unbounded so a future large override set cannot grow this
# process-lifetime cache without limit.
NORMALIZED_CACHE_MAX_ENTRIES = 128


def normalized_png_bytes(path):
    """Return PNG bytes for the illustration at `path`, resized (LANCZOS)
    then tight-cropped to its opaque bbox (via
    `panel_render._opaque_bbox()`, never reimplemented) and pasted
    centred onto a transparent `ILLUSTRATION_TARGET_SIZE` canvas. A file
    with no opaque bbox falls back to the whole image rather than
    raising. Every output has identical pixel dimensions.
    """
    with Image.open(path) as source:
        rgba = source.convert("RGBA")

    # Resize first, crop the bbox after — never crop-then-resize.
    # Cropping tight before resizing starves LANCZOS of edge context,
    # measured to shift the bbox by up to 2px on some files.
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


@functools.lru_cache(maxsize=NORMALIZED_CACHE_MAX_ENTRIES)
def _cached_normalized_png_bytes(path, mtime_ns):
    # `mtime_ns` is part of the cache key purely so a replaced asset on
    # disk is picked up on the next call — it is never read for any other
    # purpose. The 43 vendored files are therefore normalized once per
    # process, not once per request, and NORMALIZED_CACHE_MAX_ENTRIES
    # bounds how many distinct (path, mtime_ns) entries stay resident.
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
