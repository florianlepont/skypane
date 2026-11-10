"""Landscape (800x480) adaptations of the giant-lettering design.

    PYTHONPATH=. python3 design-exploration/plane-screen/mock_landscape.py OUT_DIR FONT_DIR
FONT_DIR holds Anton-Regular.ttf (SIL OFL, fetched outside the repository).
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mock_giant_city as g  # noqa: E402
import mock_themes as t  # noqa: E402

from server import panel_format as pf  # noqa: E402

W, H = 800, 480


def canvas_for(idx=pf.IDX_BLUE):
    base = t.field(idx, True).resize((1200, 1600)).crop((0, 0, W, H))
    return base.copy()


def footer(c, ink, x=28, y=None, size=64):
    d = ImageDraw.Draw(c)
    y = H - 28 - size - 30 if y is None else y
    d.text((x, y), t.v.FLIGHT, font=ImageFont.truetype(g.FONT, size), fill=ink)
    d.text((x, y + size + 6), t.v.AIRLINE, font=ImageFont.truetype(g.FONT, 26), fill=ink)


def l1(lines, ink):
    """Lettering fills the frame, whole aircraft centred, footer bottom-left."""
    c = canvas_for()
    g.giant_text(c, lines, (16, 24, W - 16, 330), ink, heavy=1, stretch=True)
    t.v.paste_with_halo(c, t.v.load_plane(600), (W / 2, 190), halo=9)
    footer(c, ink)
    return c


def l2(lines, ink):
    """Nose enters from the right, tail from the left, lettering behind."""
    c = canvas_for()
    g.giant_text(c, lines, (16, 24, W - 16, 340), ink, heavy=1, stretch=True)
    full = t.v.load_plane(800)
    nose = full.crop((0, 0, int(full.width * 0.5), full.height))
    nose = nose.crop(nose.getbbox())
    t.v.halo_paste(c, nose, (W - nose.width + 16, 40), halo=9)
    small = t.v.load_plane(540)
    tail = small.crop((int(small.width * 0.5), 0, small.width, small.height))
    tail = tail.crop(tail.getbbox())
    t.v.halo_paste(c, tail, (-12, H - 24 - tail.height), halo=9)
    footer(c, ink, x=430, y=H - 28 - 64 - 32)
    return c


def l3(lines, ink):
    """Lettering on top, aircraft in its own band at the bottom, footer left."""
    c = canvas_for()
    g.giant_text(c, lines, (16, 24, W - 16, 330), ink, heavy=1, stretch=True)
    t.v.paste_with_halo(c, t.v.load_plane(430), (W - 250, 400), halo=9)
    footer(c, ink, y=H - 28 - 64 - 32)
    return c


def main(out_dir, font_dir):
    os.makedirs(out_dir, exist_ok=True)
    g.FONT_HEAVY = os.path.join(font_dir, "Anton-Regular.ttf")
    ink = t.ink_rgb(pf.IDX_BLUE)
    names = [["MARSEILLE"], ["NEW YORK"], ["CLERMONT-FERRAND"]]
    sheet = Image.new("RGB", (3 * (W + 12) + 12, len(names) * (H + 12) + 12), (110, 110, 110))
    for row, lines in enumerate(names):
        for col, fn in enumerate((l1, l2, l3)):
            c = fn(lines, ink)
            c.save(os.path.join(out_dir, "land-%d-%d.png" % (row + 1, col + 1)))
            sheet.paste(c, (12 + col * (W + 12), 12 + row * (H + 12)))
    sheet.save(os.path.join(out_dir, "landscape.png"))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
