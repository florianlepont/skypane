"""The diagonal-band design on the 800x480 landscape panel.

    PYTHONPATH=. python3 design-exploration/plane-screen/mock_landscape_diagonal.py OUT_DIR FONT_DIR
FONT_DIR holds Anton-Regular.ttf (SIL OFL, fetched outside the repository).
Writes sheet-nose-tail.png and sheet-whole.png (3 cities x 4 pairings each).
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mock_giant_city as g  # noqa: E402
import mock_themes as t  # noqa: E402

from server import panel_format as pf  # noqa: E402
from server.plane.render import style  # noqa: E402

W, H = 800, 480
COLOURS = [("blue", pf.IDX_BLUE, None), ("red", pf.IDX_RED, None), ("grey", pf.IDX_BLACK, None), ("yellow", pf.IDX_YELLOW, 0.75)]
CITIES = [("NICE", "NICE"), ("BORDEAUX", "BORDEAUX"), ("SAINT-ÉTIENNE", "SAINT-ÉTIENNE")]


def band_mask():
    poly = [
        (style.BAND_TOP_LEFT_FRAC * W, 0), (style.BAND_TOP_RIGHT_FRAC * W, 0),
        (style.BAND_BOT_RIGHT_FRAC * W, H), (style.BAND_BOT_LEFT_FRAC * W, H),
    ]
    mask = Image.new("L", (W, H), 0)
    ImageDraw.Draw(mask).polygon(poly, fill=255)
    return mask


def field_for(idx, fraction):
    full = t.lightened_field(idx, fraction) if fraction else t.field(idx, True)
    return full.crop((0, 0, W, H))


def label_fill(idx):
    """Plain ink, except yellow: it is dithered toward black so the small text
    separates from the light yellow field."""
    if idx == pf.IDX_YELLOW:
        return t.darkened_ink(idx, 0.45).crop((0, 0, W, H))
    return Image.new("RGB", (W, H), t.ink_rgb(idx))


def labels(c, idx):
    layer = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(layer)
    d.text((28, 12), t.v.STATE, font=ImageFont.truetype(g.FONT, 24), fill=255)
    for text, size, top in ((t.v.FLIGHT, 64, 360), (t.v.AIRLINE, 26, 428)):
        font = ImageFont.truetype(g.FONT, size)
        d.text((W - 28 - font.getlength(text), top), text, font=font, fill=255)
    c.paste(label_fill(idx), (0, 0), layer)


def build(name, idx, fraction, layout):
    ink = t.ink_rgb(idx)
    field = field_for(idx, fraction)
    solid = Image.new("RGB", (W, H), ink)
    c = field.copy()
    mask = band_mask()
    c.paste(solid, (0, 0), mask)
    tone = Image.composite(field, solid, mask)
    g.giant_text(c, [name], (16, 52, W - 16, 340), tone, heavy=1, stretch=True)
    if layout == "whole":
        t.v.paste_with_halo(c, t.v.load_plane(560), (W / 2, 190), halo=9)
    else:
        full = t.v.load_plane(800)
        nose = full.crop((0, 0, int(full.width * 0.5), full.height))
        nose = nose.crop(nose.getbbox())
        t.v.halo_paste(c, nose, (W - nose.width + 16, 40), halo=9)
        small = t.v.load_plane(540)
        tail = small.crop((int(small.width * 0.5), 0, small.width, small.height))
        tail = tail.crop(tail.getbbox())
        t.v.halo_paste(c, tail, (-12, H - 24 - tail.height), halo=9)
    labels(c, idx)
    return c


def main(out_dir, font_dir):
    os.makedirs(out_dir, exist_ok=True)
    g.FONT_HEAVY = os.path.join(font_dir, "Anton-Regular.ttf")
    tw, th = 400, 240
    label_font = ImageFont.truetype(g.FONT, 22)
    for layout, fname in (("nose_tail", "sheet-nose-tail.png"), ("whole", "sheet-whole.png")):
        sheet = Image.new("RGB", (len(COLOURS) * (tw + 12) + 12, len(CITIES) * (th + 12) + 12), (110, 110, 110))
        for row, (city, name) in enumerate(CITIES):
            for col, (cname, idx, fraction) in enumerate(COLOURS):
                c = build(name, idx, fraction, layout)
                c.save(os.path.join(out_dir, "%s-%d-%d.png" % (layout, row + 1, col + 1)))
                thumb = c.resize((tw, th), Image.LANCZOS)
                ImageDraw.Draw(thumb).text((6, th - 30), "%s / %s" % (city, cname), font=label_font, fill=(255, 255, 255), stroke_width=3, stroke_fill=(0, 0, 0))
                sheet.paste(thumb, (12 + col * (tw + 12), 12 + row * (th + 12)))
        sheet.save(os.path.join(out_dir, fname))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
