"""The primary layout with different lettering fonts.

    PYTHONPATH=. python3 design-exploration/plane-screen/mock_fonts.py OUT_DIR FONT_DIR
FONT_DIR holds Anton-Regular.ttf, BebasNeue-Regular.ttf, ArchivoBlack-Regular.ttf and
AlfaSlabOne-Regular.ttf (all SIL OFL, fetched outside the repository).
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mock_giant_city as g  # noqa: E402
import mock_themes as t  # noqa: E402

from server import panel_format as pf  # noqa: E402

TEXTS = [["MAR", "SEI", "LLE"], ["NEW", "YORK"]]


def fonts(font_dir):
    """(label, path, extra stroke in px at 600 px font size)."""
    return [
        ("Inter Black (current)", g.FONT_HEAVY, 22),
        ("Anton", os.path.join(font_dir, "Anton-Regular.ttf"), 6),
        ("Bebas Neue", os.path.join(font_dir, "BebasNeue-Regular.ttf"), 14),
        ("Archivo Black", os.path.join(font_dir, "ArchivoBlack-Regular.ttf"), 6),
        ("Alfa Slab One", os.path.join(font_dir, "AlfaSlabOne-Regular.ttf"), 4),
        ("Zilla Slab Bold", "server/assets/fonts/ZillaSlab-Bold.ttf", 22),
    ]


def main(out_dir, font_dir):
    os.makedirs(out_dir, exist_ok=True)
    tw, th = 400, 533
    label_font = ImageFont.truetype(g.FONT, 28)
    for n, lines in enumerate(TEXTS):
        t.v.LINES = lines
        sheet = Image.new("RGB", (3 * (tw + 12) + 12, 2 * (th + 12) + 12), (110, 110, 110))
        for i, (label, path, stroke) in enumerate(fonts(font_dir)):
            g.FONT_HEAVY = path
            t.v.HEAVY = stroke
            canvas = t.render_pair(pf.IDX_BLUE, True, pf.IDX_BLUE)
            canvas.save(os.path.join(out_dir, "font-%d-%d.png" % (n + 1, i + 1)))
            thumb = canvas.resize((tw, th), Image.LANCZOS)
            ImageDraw.Draw(thumb).text((tw - 12 - label_font.getlength(label), 8), label, font=label_font, fill=(255, 255, 255), stroke_width=3, stroke_fill=(0, 0, 0))
            sheet.paste(thumb, (12 + (i % 3) * (tw + 12), 12 + (i // 3) * (th + 12)))
        sheet.save(os.path.join(out_dir, "fonts-%d.png" % (n + 1)))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
