"""The giant-lettering layout rendered in every colour theme of the registry.

Standalone exploration: reads server.themes, does not touch the renderer.
    PYTHONPATH=. python3 design-exploration/plane-screen/mock_themes.py OUT_DIR
Writes theme-<id>.png (1200x1600) and sheet-1..3.png (6 themes each).
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mock_giant_city as g  # noqa: E402
import mock_plane_variants as v  # noqa: E402

from server import panel_format as pf  # noqa: E402
from server import themes  # noqa: E402
from server.plane import dither  # noqa: E402


def ink_rgb(idx):
    return tuple(pf.PALETTE_RGB[idx * 3 : idx * 3 + 3])


def field(idx, dithered):
    """Full-canvas RGB field: flat ink, or the ink dithered toward white."""
    if dithered:
        return dither.dithered_state_background(idx).convert("RGB")
    return Image.new("RGB", (g.W, g.H), ink_rgb(idx))


def theme_colours(theme):
    """(background image, lettering fill, text ink) for one registry theme."""
    band = theme.get("band_index")
    idx = theme["departing_index"]
    if band is not None and idx == pf.IDX_WHITE:
        # white field: the band colour moves onto the lettering
        letters = field(band, bool(theme["band_dithered"])) if theme["band_dithered"] else ink_rgb(band)
        return field(idx, False), letters, ink_rgb(band)
    if theme["dithered"]:
        # light field: the same hue, flat, carries the lettering
        # yellow has no darker ink than black, which keeps the lettering legible
        ink_idx = band if band is not None else (pf.IDX_BLACK if idx == pf.IDX_YELLOW else idx)
        letters = ink_rgb(ink_idx)
        return field(idx, True), letters, letters
    ink = ink_rgb(theme["ink_index"])
    return field(idx, False), ink, ink


# (label, field ink, field dithered, lettering ink): the chosen pairings
PAIRS = [
    ("grey / black", pf.IDX_BLACK, True, pf.IDX_BLACK),
    ("light blue / blue", pf.IDX_BLUE, True, pf.IDX_BLUE),
    ("light red / red", pf.IDX_RED, True, pf.IDX_RED),
    ("light yellow / yellow", pf.IDX_YELLOW, True, pf.IDX_YELLOW),
    ("white / black", pf.IDX_WHITE, False, pf.IDX_BLACK),
]


def render_pair(field_idx, dithered, letters_idx):
    ink = ink_rgb(letters_idx)
    # yellow needs a lighter field (75% white) to separate from its own ink
    canvas = (lightened_field(field_idx, 0.75) if field_idx == pf.IDX_YELLOW else field(field_idx, dithered)).copy()
    g.giant_text(canvas, v.LINES, (40, 130, g.W - 40, 1290), ink, heavy=v.HEAVY)
    v.vnose_tail(canvas)
    v.footer(canvas, ink=ink)
    return canvas


def render(theme):
    bg, letters, ink = theme_colours(theme)
    canvas = bg.copy()
    g.giant_text(canvas, v.LINES, (40, 130, g.W - 40, 1290), letters, heavy=v.HEAVY)
    v.vnose_tail(canvas)
    v.footer(canvas, ink=ink)
    return canvas


def main(out_dir):
    os.makedirs(out_dir, exist_ok=True)
    ids = list(themes.THEMES)
    tw, th = 400, 533
    font = ImageFont.truetype(g.FONT, 30)
    for n in range(0, len(ids), 6):
        chunk = ids[n : n + 6]
        sheet = Image.new("RGB", (3 * (tw + 12) + 12, 2 * (th + 12) + 12), (110, 110, 110))
        for i, tid in enumerate(chunk):
            canvas = render(themes.THEMES[tid])
            canvas.save(os.path.join(out_dir, "theme-%s.png" % tid))
            thumb = canvas.resize((tw, th), Image.LANCZOS)
            ImageDraw.Draw(thumb).text((tw - 12 - font.getlength(tid), 8), tid, font=font, fill=(255, 255, 255), stroke_width=3, stroke_fill=(0, 0, 0))
            sheet.paste(thumb, (12 + (i % 3) * (tw + 12), 12 + (i // 3) * (th + 12)))
        sheet.save(os.path.join(out_dir, "sheet-%d.png" % (n // 6 + 1)))


def main_pairs(out_dir):
    os.makedirs(out_dir, exist_ok=True)
    tw, th = 400, 533
    font = ImageFont.truetype(g.FONT, 30)
    sheet = Image.new("RGB", (3 * (tw + 12) + 12, 2 * (th + 12) + 12), (110, 110, 110))
    for i, (label, fidx, dith, lidx) in enumerate(PAIRS):
        canvas = render_pair(fidx, dith, lidx)
        canvas.save(os.path.join(out_dir, "pair-%d.png" % (i + 1)))
        thumb = canvas.resize((tw, th), Image.LANCZOS)
        ImageDraw.Draw(thumb).text((tw - 12 - font.getlength(label), 8), label, font=font, fill=(255, 255, 255), stroke_width=3, stroke_fill=(0, 0, 0))
        sheet.paste(thumb, (12 + (i % 3) * (tw + 12), 12 + (i // 3) * (th + 12)))
    sheet.save(os.path.join(out_dir, "pairs.png"))


def lightened_field(idx, fraction):
    """Like field(idx, True) but with an adjustable share of white."""
    return dither.dithered_state_background(idx, lighten_fraction=fraction).convert("RGB")


def darkened_ink(idx, fraction):
    """Full-canvas pattern: `idx` ink dithered toward black (a darker shade)."""
    r, g_, b = ink_rgb(idx)
    flat = Image.new("RGB", (g.W, g.H), tuple(round(c * (1 - fraction)) for c in (r, g_, b)))
    two = Image.new("P", (1, 1))
    two.putpalette([r, g_, b, 0, 0, 0])
    return flat.quantize(palette=two, dither=Image.FLOYDSTEINBERG).convert("RGB")


def main_yellow(out_dir):
    os.makedirs(out_dir, exist_ok=True)
    yellow = ink_rgb(pf.IDX_YELLOW)
    variants = [
        ("current", field(pf.IDX_YELLOW, True), yellow),
        ("lighter field", lightened_field(pf.IDX_YELLOW, 0.75), yellow),
        ("darker letters", field(pf.IDX_YELLOW, True), darkened_ink(pf.IDX_YELLOW, 0.45)),
    ]
    tw, th = 400, 533
    font = ImageFont.truetype(g.FONT, 30)
    sheet = Image.new("RGB", (3 * (tw + 12) + 12, th + 24), (110, 110, 110))
    for i, (label, bg, letters) in enumerate(variants):
        canvas = bg.copy()
        g.giant_text(canvas, v.LINES, (40, 130, g.W - 40, 1290), letters, heavy=v.HEAVY)
        v.vnose_tail(canvas)
        v.footer(canvas, ink=yellow if label != "darker letters" else tuple(round(c * 0.55) for c in yellow))
        canvas.save(os.path.join(out_dir, "yellow-%d.png" % (i + 1)))
        thumb = canvas.resize((tw, th), Image.LANCZOS)
        ImageDraw.Draw(thumb).text((tw - 12 - font.getlength(label), 8), label, font=font, fill=(255, 255, 255), stroke_width=3, stroke_fill=(0, 0, 0))
        sheet.paste(thumb, (12 + i * (tw + 12), 12))
    sheet.save(os.path.join(out_dir, "yellow.png"))


if __name__ == "__main__":
    if os.environ.get("MOCK_YELLOW"):
        main_yellow(sys.argv[1])
        sys.exit(0)
    (main_pairs if os.environ.get("MOCK_PAIRS") else main)(sys.argv[1])
