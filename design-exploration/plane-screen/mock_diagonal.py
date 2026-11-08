"""The diagonal band of the current renderer, brought into the giant-lettering design.

    PYTHONPATH=. python3 design-exploration/plane-screen/mock_diagonal.py OUT_DIR FONT_DIR
FONT_DIR holds Anton-Regular.ttf (SIL OFL, fetched outside the repository).
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mock_giant_city as g  # noqa: E402
import mock_themes as t  # noqa: E402

from server import panel_format as pf  # noqa: E402
from server.plane.render import style  # noqa: E402

W, H = g.W, g.H
WHITE = (255, 255, 255)


def band_mask():
    poly = [
        (style.BAND_TOP_LEFT_FRAC * W, 0), (style.BAND_TOP_RIGHT_FRAC * W, 0),
        (style.BAND_BOT_RIGHT_FRAC * W, H), (style.BAND_BOT_LEFT_FRAC * W, H),
    ]
    mask = Image.new("L", (W, H), 0)
    ImageDraw.Draw(mask).polygon(poly, fill=255)
    return mask


def two_tone(outside, inside, mask):
    """Canvas-sized pattern: `outside` ink off the band, `inside` ink on it."""
    return Image.composite(inside, outside, mask)


def paint_labels(c, fill):
    """State, flight and airline drawn through `fill` (an RGB tuple or a canvas-sized image)."""
    layer = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(layer)
    d.text((64, 56), t.v.STATE, font=ImageFont.truetype(g.FONT, 56), fill=255)
    d.text((64, 1330), t.v.FLIGHT, font=ImageFont.truetype(g.FONT, 150), fill=255)
    d.text((64, 1500), t.v.AIRLINE, font=ImageFont.truetype(g.FONT, 56), fill=255)
    src = fill if isinstance(fill, Image.Image) else Image.new("RGB", (W, H), fill)
    c.paste(src, (0, 0), layer)


def build(field, band, letters, labels):
    c = field.copy()
    mask = band_mask()
    c.paste(band, (0, 0), mask)
    g.giant_text(c, t.v.LINES, (40, 130, W - 40, 1290), letters, heavy=1)
    t.v.vnose_tail(c)
    paint_labels(c, labels)
    return c


def main(out_dir, font_dir):
    os.makedirs(out_dir, exist_ok=True)
    g.FONT_HEAVY = os.path.join(font_dir, "Anton-Regular.ttf")
    blue = t.ink_rgb(pf.IDX_BLUE)
    white = Image.new("RGB", (W, H), WHITE)
    solid = Image.new("RGB", (W, H), blue)
    light = t.field(pf.IDX_BLUE, True)
    mask = band_mask()
    variants = [
        ("light band, white field, blue lettering", build(white, light, blue, blue)),
        ("solid band, white field, two-tone lettering", build(white, solid, two_tone(solid, white, mask), two_tone(solid, white, mask))),
        ("solid band, light field, two-tone lettering", build(light, solid, two_tone(solid, white, mask), two_tone(solid, white, mask))),
    ]
    tw, th = 400, 533
    font = ImageFont.truetype(g.FONT, 24)
    names = [["MAR", "SEI", "LLE"], ["NEW", "YORK"]]
    sheet = Image.new("RGB", (3 * (tw + 12) + 12, len(names) * (th + 12) + 12), (110, 110, 110))
    for row, lines in enumerate(names):
        t.v.LINES = lines
        built = [
            build(white, light, blue, blue),
            build(white, solid, two_tone(solid, white, mask), two_tone(solid, white, mask)),
            build(light, solid, two_tone(solid, white, mask), two_tone(solid, white, mask)),
        ]
        for col, c in enumerate(built):
            c.save(os.path.join(out_dir, "diag-%d-%d.png" % (row + 1, col + 1)))
            thumb = c.resize((tw, th), Image.LANCZOS)
            if row == 0:
                ImageDraw.Draw(thumb).text((8, th - 34), variants[col][0], font=font, fill=(255, 255, 255), stroke_width=3, stroke_fill=(0, 0, 0))
            sheet.paste(thumb, (12 + col * (tw + 12), 12 + row * (th + 12)))
    sheet.save(os.path.join(out_dir, "diagonal.png"))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
