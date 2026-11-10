"""Three reworks of the band layout, in the same art direction as the others.

    PYTHONPATH=. python3 design-exploration/plane-screen/mock_band_rework.py OUT_DIR FONT_DIR
FONT_DIR holds Anton-Regular.ttf (SIL OFL, fetched outside the repository).
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mock_giant_city as g  # noqa: E402
import mock_themes as t  # noqa: E402

from server import panel_format as pf  # noqa: E402

W, H = g.W, g.H
WHITE = (255, 255, 255)


def start(lines, ink, text_bottom):
    c = t.field(pf.IDX_BLUE, True).copy()
    g.giant_text(c, lines, (40, 130, W - 40, text_bottom), ink, heavy=1)
    return c


def labels(c, ink, flight_xy=(64, 1330), colour=None):
    d = ImageDraw.Draw(c)
    colour = colour or ink
    d.text((64, 56), t.v.STATE, font=ImageFont.truetype(g.FONT, 56), fill=ink)
    d.text(flight_xy, t.v.FLIGHT, font=ImageFont.truetype(g.FONT, 150), fill=colour)
    d.text((flight_xy[0], flight_xy[1] + 170), t.v.AIRLINE, font=ImageFont.truetype(g.FONT, 56), fill=colour)


def r1(lines, ink):
    """Large aircraft cropped by both frame edges, lettering above."""
    c = start(lines, ink, 800)
    t.v.paste_with_halo(c, t.v.load_plane(1420), (W / 2 - 100, 1020))
    labels(c, ink)
    return c


def r2(lines, ink):
    """Full-bleed solid band; the aircraft breaks out of it, cropped by the frame."""
    c = start(lines, ink, 800)
    ImageDraw.Draw(c).rectangle((0, 930, W, 1230), fill=ink)
    t.v.paste_with_halo(c, t.v.load_plane(1420), (W / 2 - 100, 1010), halo=1)
    labels(c, ink)
    return c


def r3(lines, ink):
    """Solid footer band carrying flight and airline in white; aircraft rides its top edge."""
    c = start(lines, ink, 800)
    ImageDraw.Draw(c).rectangle((0, 1140, W, H), fill=ink)
    t.v.paste_with_halo(c, t.v.load_plane(1420), (W / 2 - 100, 1010))
    labels(c, ink, flight_xy=(64, 1260), colour=WHITE)
    return c


def main(out_dir, font_dir):
    os.makedirs(out_dir, exist_ok=True)
    g.FONT_HEAVY = os.path.join(font_dir, "Anton-Regular.ttf")
    ink = t.ink_rgb(pf.IDX_BLUE)
    tw, th = 400, 533
    names = [["MAR", "SEI", "LLE"], ["NEW", "YORK"]]
    sheet = Image.new("RGB", (3 * (tw + 12) + 12, len(names) * (th + 12) + 12), (110, 110, 110))
    for row, lines in enumerate(names):
        for col, fn in enumerate((r1, r2, r3)):
            c = fn(lines, ink)
            c.save(os.path.join(out_dir, "band-%d-%d.png" % (row + 1, col + 1)))
            sheet.paste(c.resize((tw, th), Image.LANCZOS), (12 + col * (tw + 12), 12 + row * (th + 12)))
    sheet.save(os.path.join(out_dir, "band-rework.png"))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
