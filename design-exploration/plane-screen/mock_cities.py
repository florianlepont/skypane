"""The primary layout with different destination names (hand-split lines).

    PYTHONPATH=. python3 design-exploration/plane-screen/mock_cities.py OUT_DIR
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mock_giant_city as g  # noqa: E402
import mock_themes as t  # noqa: E402

from server import panel_format as pf  # noqa: E402

CITIES = [
    ("NICE", ["NI", "CE"]),
    ("LYON", ["LY", "ON"]),
    ("LONDON", ["LON", "DON"]),
    ("BORDEAUX", ["BOR", "DEA", "UX"]),
    ("TOULOUSE", ["TOU", "LOU", "SE"]),
    ("CASABLANCA", ["CASA", "BLAN", "CA"]),
    ("FRANKFURT", ["FRANK", "FURT"]),
    ("BARCELONA", ["BAR", "CEL", "ONA"]),
    ("NEW YORK", ["NEW", "YORK"]),
]


SHORT = [("NICE", ["NI", "CE"], ["NICE"]), ("LYON", ["LY", "ON"], ["LYON"]), ("ROME", ["RO", "ME"], ["ROME"])]


def main_short(out_dir):
    """Short names: split over two lines (top row) vs one whole word (bottom row)."""
    os.makedirs(out_dir, exist_ok=True)
    tw, th = 400, 533
    font = ImageFont.truetype(g.FONT, 30)
    sheet = Image.new("RGB", (3 * (tw + 12) + 12, 2 * (th + 12) + 12), (110, 110, 110))
    for col, (name, split, whole) in enumerate(SHORT):
        for row, lines in enumerate((split, whole)):
            t.v.LINES = lines
            canvas = t.render_pair(pf.IDX_BLUE, True, pf.IDX_BLUE)
            canvas.save(os.path.join(out_dir, "short-%s-%d.png" % (name.lower(), row + 1)))
            thumb = canvas.resize((tw, th), Image.LANCZOS)
            label = "%s (%d line%s)" % (name, len(lines), "s" if len(lines) > 1 else "")
            ImageDraw.Draw(thumb).text((tw - 12 - font.getlength(label), 8), label, font=font, fill=(255, 255, 255), stroke_width=3, stroke_fill=(0, 0, 0))
            sheet.paste(thumb, (12 + col * (tw + 12), 12 + row * (th + 12)))
    sheet.save(os.path.join(out_dir, "short-names.png"))


def main(out_dir):
    os.makedirs(out_dir, exist_ok=True)
    tw, th = 400, 533
    font = ImageFont.truetype(g.FONT, 30)
    sheet = Image.new("RGB", (3 * (tw + 12) + 12, 3 * (th + 12) + 12), (110, 110, 110))
    for i, (name, lines) in enumerate(CITIES):
        t.v.LINES = lines
        canvas = t.render_pair(pf.IDX_BLUE, True, pf.IDX_BLUE)
        canvas.save(os.path.join(out_dir, "city-%d.png" % (i + 1)))
        thumb = canvas.resize((tw, th), Image.LANCZOS)
        ImageDraw.Draw(thumb).text((tw - 12 - font.getlength(name), 8), name, font=font, fill=(255, 255, 255), stroke_width=3, stroke_fill=(0, 0, 0))
        sheet.paste(thumb, (12 + (i % 3) * (tw + 12), 12 + (i // 3) * (th + 12)))
    sheet.save(os.path.join(out_dir, "cities.png"))


if __name__ == "__main__":
    (main_short if os.environ.get("MOCK_SHORT") else main)(sys.argv[1])
