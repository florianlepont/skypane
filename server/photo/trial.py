"""Skin-tone trial tooling for the photo render path.

Everything here is for reviewing the rendering by eye and by numbers: a
procedural skin-tone grid (no binary data, no real people), a renderer for
an owner-supplied file, and the measures reported per grid cell. Output is
only ever written to a directory the caller names, and never inside the
repository work tree, so portraits kept outside git stay outside git.
"""

from __future__ import annotations

import colorsys
import io
import math
import re
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageOps, ImageStat

from server.photo.crop import FitSetting
from server.photo.normalize import MAX_UPLOAD_BYTES, normalize_upload
from server.photo.prep import DEFAULT_PREP, PrepParams, prepare
from server.photo.render import BAND_INDEX, preview_png, render_photo

# Illustrative approximations of a six-step skin-tone range, not a standard.
SKIN_TONES: dict[str, tuple[int, int, int]] = {
    "I": (255, 224, 196),
    "II": (241, 194, 155),
    "III": (224, 172, 124),
    "IV": (198, 134, 90),
    "V": (141, 85, 54),
    "VI": (80, 50, 36),
}

SCENE_SIZE = (480, 640)
# Box (left, top, right, bottom) of the face ellipse inside the scene.
_FACE_BOX = (120, 170, 360, 470)

PANELS: Mapping[str, tuple[int, int]] = {
    "portrait": (1200, 1600),
    "landscape": (800, 480),
}
FITS = ("fill", "bands")
SCENES = ("full", "dull")

REPO_ROOT = Path(__file__).resolve().parents[2]
_BLUR_RADIUS = 6
_THUMB = 150
_LABEL_H = 14
_STEM_MAX = 40


def skin_swatch(tone: str, size: tuple[int, int] = (64, 64)) -> Image.Image:
    """Flat swatch of one skin tone."""
    return Image.new("RGB", size, SKIN_TONES[tone])


def _backdrop(size: tuple[int, int]) -> Image.Image:
    w, h = size
    img = Image.new("RGB", size)
    draw = ImageDraw.Draw(img)
    for y in range(h):
        v = 70 + (y * 110) // max(1, h - 1)
        draw.line([(0, y), (w, y)], fill=(v, v + 10, v + 25))
    return img


def _shaded_face(tone: str, size: tuple[int, int]) -> Image.Image:
    """Skin colour scaled by a radial light falloff from the upper left."""
    base = SKIN_TONES[tone]
    left, top, right, bottom = _FACE_BOX
    fw, fh = right - left, bottom - top
    cx, cy = fw * 0.35, fh * 0.30
    face = Image.new("RGB", (fw, fh))
    px = face.load()
    assert px is not None
    reach = (fw * fw + fh * fh) ** 0.5
    for y in range(fh):
        for x in range(fw):
            d = (((x - cx) ** 2 + (y - cy) ** 2) ** 0.5) / reach
            k = 1.12 - 0.62 * d
            px[x, y] = tuple(max(0, min(255, round(c * k))) for c in base)  # type: ignore[assignment]
    return face


def face_scene(
    tone: str, *, dull: bool = False, size: tuple[int, int] = SCENE_SIZE
) -> tuple[Image.Image, tuple[int, int, int, int]]:
    """Shaded ellipse face on a graded backdrop with dark hair and a bright
    shirt band. Returns the image and the box of the skin region (an inner
    box of the face ellipse, well inside it). ``dull`` blends toward mid
    grey for a low-contrast variant."""
    img = _backdrop(size)
    left, top, right, bottom = _FACE_BOX
    draw = ImageDraw.Draw(img)
    draw.ellipse((left - 10, top - 50, right + 10, top + 150), fill=(25, 20, 18))
    mask = Image.new("L", (right - left, bottom - top), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, right - left - 1, bottom - top - 1), fill=255)
    img.paste(_shaded_face(tone, size), (left, top), mask)
    draw.rectangle((0, size[1] - 110, size[0], size[1] - 40), fill=(245, 245, 240))
    if dull:
        img = Image.blend(img, Image.new("RGB", size, (128, 128, 128)), 0.55)
    cx = (left + right) // 2
    cy = (top + bottom) // 2 + 20
    return img, (cx - 50, cy - 50, cx + 50, cy + 50)


def check_out_dir(out_dir: Path | str) -> Path:
    """Resolve ``out_dir`` and refuse anything inside the repository."""
    resolved = Path(out_dir).expanduser().resolve()
    if resolved == REPO_ROOT or REPO_ROOT in resolved.parents:
        raise ValueError("output directory must be outside the repository")
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def default_out_dir() -> Path:
    """A fresh scratch directory outside the repository."""
    return Path(tempfile.mkdtemp(prefix="skypane-photo-trial-"))


def safe_stem(name: str) -> str:
    """Filename stem reduced to alphanumerics, dash and underscore."""
    stem = re.sub(r"[^A-Za-z0-9_-]", "_", Path(name).stem)[:_STEM_MAX]
    return stem or "photo"


def param_sets() -> list[tuple[str, PrepParams]]:
    """The default plus one-factor-at-a-time variations around it."""
    base = DEFAULT_PREP
    variants: list[tuple[str, PrepParams]] = [("default", base)]
    for sat in (1.0, 1.15, 1.3):
        variants.append((f"sat{sat}", PrepParams(base.cutoff, base.strength, sat)))
    for strength in (0.5, 0.8, 1.0):
        variants.append((f"str{strength}", PrepParams(base.cutoff, strength, base.saturation)))
    for cutoff in (0.5, 1.0, 2.0):
        variants.append((f"cut{cutoff}", PrepParams(cutoff, base.strength, base.saturation)))
    seen: set[PrepParams] = set()
    unique: list[tuple[str, PrepParams]] = []
    for label, params in variants:
        if params not in seen:
            seen.add(params)
            unique.append((label, params))
    return unique


def _jpeg(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.convert("RGB").save(buf, "JPEG", quality=90)
    return buf.getvalue()


@dataclass(frozen=True)
class _Framed:
    """Source framed for a panel: the photo area, its mask and placement."""

    photo: Image.Image
    mask: Image.Image
    offset: tuple[int, int]
    size: tuple[int, int]


def _frame(
    src: Image.Image, box: tuple[int, int, int, int], size: tuple[int, int], fit: FitSetting
) -> _Framed:
    """Mirror the crop of render_photo for the skin mask (measurement only)."""
    mask = Image.new("L", src.size, 0)
    ImageDraw.Draw(mask).rectangle(box, fill=255)
    if fit.mode == "fill":
        centering = (fit.pos_x, fit.pos_y)
        photo = ImageOps.fit(src, size, Image.Resampling.LANCZOS, centering=centering)
        m = ImageOps.fit(mask, size, Image.Resampling.BILINEAR, centering=centering)
        return _Framed(photo, m, (0, 0), size)
    photo = ImageOps.contain(src, size, Image.Resampling.LANCZOS)
    m = ImageOps.contain(mask, size, Image.Resampling.BILINEAR)
    offset = ((size[0] - photo.width) // 2, (size[1] - photo.height) // 2)
    return _Framed(photo, m, offset, size)


def _on_canvas(framed: _Framed, photo: Image.Image, fill: int) -> Image.Image:
    canvas = Image.new("RGB", framed.size, (fill, fill, fill))
    canvas.paste(photo, framed.offset)
    return canvas


def _mask_canvas(framed: _Framed) -> Image.Image:
    canvas = Image.new("L", framed.size, 0)
    canvas.paste(framed.mask.point(lambda v: 255 if v > 127 else 0), framed.offset)
    return canvas


def _mean_rgb(img: Image.Image, mask: Image.Image) -> tuple[float, float, float]:
    r, g, b = ImageStat.Stat(img.convert("RGB"), mask).mean[:3]
    return (r, g, b)


def _hue_deg(rgb: tuple[float, float, float]) -> float:
    h, _s, _v = colorsys.rgb_to_hsv(rgb[0] / 255, rgb[1] / 255, rgb[2] / 255)
    return h * 360.0


def _blur(img: Image.Image) -> Image.Image:
    return img.filter(ImageFilter.BoxBlur(_BLUR_RADIUS))


def _measure(
    framed: _Framed, params: PrepParams, dithered: Image.Image
) -> dict[str, Any]:
    """Numbers for one rendered cell, inside the skin mask."""
    mask = _mask_canvas(framed)
    prepped = _on_canvas(framed, prepare(framed.photo, params), 255)
    before = _mean_rgb(_on_canvas(framed, framed.photo, 255), mask)
    after = _mean_rgb(prepped, mask)
    total = max(1, sum(mask.histogram()[255:]))
    counts = dithered.histogram(mask)[:6]
    diff = ImageChops.difference(_blur(prepped), _blur(dithered.convert("RGB")))
    return {
        "skin_before": before,
        "skin_after": after,
        "hue_before": _hue_deg(before),
        "hue_after": _hue_deg(after),
        "palette_share": [c / total for c in counts],
        "fidelity_error": float(sum(ImageStat.Stat(diff, mask).mean[:3]) / 3.0),
    }


def _thumb(img: Image.Image) -> Image.Image:
    out = img.convert("RGB")
    out.thumbnail((_THUMB, _THUMB), Image.Resampling.BOX)
    return out


def _sheet(
    tone: str, columns: list[str], rows: list[tuple[str, list[Image.Image]]]
) -> Image.Image:
    """Rows of thumbnails: source first, then one render per parameter set."""
    label_w = 120
    cell_w, cell_h = _THUMB + 4, _THUMB + _LABEL_H + 4
    sheet = Image.new("RGB", (label_w + cell_w * len(columns), _LABEL_H * 2 + cell_h * len(rows)), "white")
    draw = ImageDraw.Draw(sheet)
    draw.text((2, 2), f"tone {tone}", fill=(0, 0, 0))
    for c, name in enumerate(columns):
        draw.text((label_w + c * cell_w + 2, _LABEL_H), name, fill=(0, 0, 0))
    for r, (label, thumbs) in enumerate(rows):
        y = _LABEL_H * 2 + r * cell_h
        draw.text((2, y + 2), label, fill=(0, 0, 0))
        for c, thumb in enumerate(thumbs):
            sheet.paste(thumb, (label_w + c * cell_w + 2, y + 2))
    return sheet


def _grid_cell(
    tone: str, scene: str, panel: str, size: tuple[int, int], fit_mode: str,
    sets: Sequence[tuple[str, PrepParams]],
) -> tuple[list[dict[str, Any]], list[Image.Image]]:
    img, box = face_scene(tone, dull=scene == "dull")
    stored = _jpeg(img)
    src = Image.open(io.BytesIO(stored)).convert("RGB")
    fit = FitSetting(fit_mode)
    framed = _frame(src, box, size, fit)
    rows: list[dict[str, Any]] = []
    thumbs = [_thumb(src)]
    for label, params in sets:
        dithered = render_photo(stored, size, fit, params)
        row = {"tone": tone, "scene": scene, "panel": panel, "fit": fit_mode, "params": label}
        row.update(_measure(framed, params, dithered))
        rows.append(row)
        thumbs.append(_thumb(dithered))
    return rows, thumbs


def run_grid(
    out_dir: Path | str | None = None,
    *,
    tones: Sequence[str] = tuple(SKIN_TONES),
    panels: Mapping[str, tuple[int, int]] = PANELS,
    sets: Sequence[tuple[str, PrepParams]] | None = None,
) -> list[dict[str, Any]]:
    """Render the synthetic grid; one contact sheet PNG per tone goes to
    ``out_dir`` (a fresh temp directory when omitted). Returns the measure
    rows."""
    target = check_out_dir(out_dir) if out_dir is not None else check_out_dir(default_out_dir())
    chosen = list(sets) if sets is not None else param_sets()
    columns = ["source"] + [label for label, _ in chosen]
    all_rows: list[dict[str, Any]] = []
    for tone in tones:
        sheet_rows: list[tuple[str, list[Image.Image]]] = []
        for scene in SCENES:
            for panel, size in panels.items():
                for fit_mode in FITS:
                    rows, thumbs = _grid_cell(tone, scene, panel, size, fit_mode, chosen)
                    all_rows.extend(rows)
                    sheet_rows.append((f"{scene} {panel} {fit_mode}", thumbs))
        _sheet(tone, columns, sheet_rows).save(target / f"skin-tone-{tone}.png", "PNG")
    return all_rows


def render_file(
    path: Path | str, out_dir: Path | str, fit: str = "fill", pos_x: float = 0.5, pos_y: float = 0.5
) -> list[Path]:
    """Run an owner file through the real normaliser and write one preview
    PNG per panel orientation. Raises ``PhotoRejected`` (with ``reason``)
    when the upload is refused and ValueError for a bad fit setting."""
    setting = FitSetting(fit, pos_x, pos_y)
    target = check_out_dir(out_dir)
    with Path(path).open("rb") as handle:
        raw = handle.read(MAX_UPLOAD_BYTES + 1)
    stored = normalize_upload(raw).jpeg
    stem = safe_stem(Path(path).name)
    written: list[Path] = []
    for panel, size in PANELS.items():
        dest = target / f"{stem}-{panel}-{setting.mode}.png"
        dest.write_bytes(preview_png(render_photo(stored, size, setting)))
        written.append(dest)
    return written


def format_rows(rows: Sequence[Mapping[str, Any]]) -> str:
    """Plain-text table of the measure rows."""
    head = "tone scene panel fit params hue_before hue_after fidelity bands_white"
    lines = [head]
    for r in rows:
        lines.append(
            f"{r['tone']} {r['scene']} {r['panel']} {r['fit']} {r['params']} "
            f"{r['hue_before']:.1f} {r['hue_after']:.1f} {r['fidelity_error']:.2f} "
            f"{r['palette_share'][BAND_INDEX]:.3f}"
        )
    return "\n".join(lines)


def rows_finite(rows: Sequence[Mapping[str, Any]]) -> bool:
    """True when every number in every row is finite."""
    for r in rows:
        nums: list[float] = [r["hue_before"], r["hue_after"], r["fidelity_error"]]
        nums += list(r["skin_before"]) + list(r["skin_after"]) + list(r["palette_share"])
        if not all(math.isfinite(n) for n in nums):
            return False
    return True
