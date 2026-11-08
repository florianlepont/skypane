"""Long destination names on each of the three retained aircraft layouts.

    PYTHONPATH=. python3 design-exploration/plane-screen/mock_long_names.py OUT_DIR
Writes sheet-1.png (names 1-3) and sheet-2.png (names 4-5): one row per name,
columns = nose/tail layout, whole aircraft, aircraft band.
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mock_giant_city as g  # noqa: E402
import mock_themes as t  # noqa: E402

from server import panel_format as pf  # noqa: E402

W = g.W
NAMES = [
    ("CLERMONT-FERRAND", ["CLER", "MONT", "FERRAND"]),
    ("SAINT-ÉTIENNE", ["SAINT", "ÉTI", "ENNE"]),
    ("AIX-EN-PROVENCE", ["AIX", "EN", "PROVENCE"]),
    ("MONTPELLIER", ["MONT", "PEL", "LIER"]),
    ("VILLEFRANCHE-SUR-SAÔNE", ["VILLE", "FRANCHE", "SUR", "SAÔNE"]),
]
LAYOUTS = ["nose + tail", "whole", "band"]


def render(lines, layout):
    ink = t.ink_rgb(pf.IDX_BLUE)
    canvas = t.field(pf.IDX_BLUE, True).copy()
    box = (40, 130, W - 40, 900 if layout == "band" else 1290)
    g.giant_text(canvas, lines, box, ink, heavy=t.v.HEAVY)
    if layout == "nose + tail":
        t.v.vnose_tail(canvas)
    elif layout == "whole":
        t.v.paste_with_halo(canvas, t.v.load_plane(1120), (W / 2, 710))
    else:
        t.v.paste_with_halo(canvas, t.v.load_plane(1120), (W / 2, 1110))
    t.v.footer(canvas, ink=ink)
    return canvas


def main(out_dir):
    os.makedirs(out_dir, exist_ok=True)
    tw, th = 400, 533
    font = ImageFont.truetype(g.FONT, 28)
    for n, chunk in enumerate((NAMES[:3], NAMES[3:])):
        sheet = Image.new("RGB", (3 * (tw + 12) + 12, len(chunk) * (th + 12) + 12), (110, 110, 110))
        for row, (name, lines) in enumerate(chunk):
            for col, layout in enumerate(LAYOUTS):
                canvas = render(lines, layout)
                thumb = canvas.resize((tw, th), Image.LANCZOS)
                label = name if col == 0 else layout
                ImageDraw.Draw(thumb).text((tw - 12 - font.getlength(label), 8), label, font=font, fill=(255, 255, 255), stroke_width=3, stroke_fill=(0, 0, 0))
                sheet.paste(thumb, (12 + col * (tw + 12), 12 + row * (th + 12)))
        sheet.save(os.path.join(out_dir, "sheet-%d.png" % (n + 1)))


if __name__ == "__main__":
    main(sys.argv[1])
