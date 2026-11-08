"""Hold/status screens in the giant-lettering design (portrait, 1200x1600).

    PYTHONPATH=. python3 design-exploration/plane-screen/mock_states.py OUT_DIR FONT_DIR
FONT_DIR holds Anton-Regular.ttf (SIL OFL, fetched outside the repository).
The pairing screen is excluded: its code is read up close and typed by hand.
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mock_diagonal as d  # noqa: E402
import mock_giant_city as g  # noqa: E402
import mock_themes as t  # noqa: E402

from server import panel_format as pf  # noqa: E402

W, H = g.W, g.H

# (key, lettering lines, small label, body lines, field ink, field lightening)
STATES = [
    ("watching", ["WATCH", "ING"], "RUNWAY 3", ["No aircraft detected yet.", "The display updates the moment one is."], pf.IDX_BLUE, None),
    ("quiet hours", ["QUIET", "HOURS"], "SLEEPING", ["Back at 07:00"], pf.IDX_BLACK, None),
    ("display off", ["DISPLAY", "OFF"], "SWITCHED OFF", ["Turn it back on from the companion page."], pf.IDX_BLACK, None),
    ("battery empty", ["BATTERY", "EMPTY"], "CHARGE ME", ["Charge the frame over USB-C.", "It will pick up where it left off."], pf.IDX_RED, None),
    ("no connection", ["NO", "CONNEC", "TION"], "OFFLINE", ["The frame can't reach its server.", "It will try again on its own."], pf.IDX_RED, None),
    ("updating", ["UPDA", "TING"], "FIRMWARE", ["Installing a firmware update.", "The frame will restart when it's ready."], pf.IDX_BLUE, None),
    ("frame retired", ["FRAME", "RETIRED"], "SKYPANE", ["This frame was removed from SkyPane.", "Ask an administrator to set it up again."], pf.IDX_BLACK, None),
]


def render(lines, label, body, idx, fraction):
    ink = t.ink_rgb(idx)
    field = t.lightened_field(idx, fraction) if fraction else t.field(idx, True)
    solid = Image.new("RGB", (W, H), ink)
    mask = d.band_mask()
    c = field.copy()
    c.paste(solid, (0, 0), mask)
    tone = Image.composite(field, solid, mask)
    g.giant_text(c, lines, (40, 130, W - 40, 1290), tone, heavy=1)
    layer = Image.new("L", (W, H), 0)
    dr = ImageDraw.Draw(layer)
    dr.text((64, 56), label, font=ImageFont.truetype(g.FONT, 56), fill=255)
    y = 1330
    for line in body:
        font = ImageFont.truetype(g.FONT, 46)
        dr.text((W - 64 - font.getlength(line), y), line, font=font, fill=255)
        y += 64
    c.paste(tone, (0, 0), layer)  # the text flips tone where it crosses the band
    return c


def main(out_dir, font_dir):
    os.makedirs(out_dir, exist_ok=True)
    g.FONT_HEAVY = os.path.join(font_dir, "Anton-Regular.ttf")
    tw, th = 300, 400
    label_font = ImageFont.truetype("server/assets/fonts/Inter-Bold.ttf", 22)
    sheet = Image.new("RGB", (4 * (tw + 12) + 12, 2 * (th + 12) + 12), (110, 110, 110))
    for i, (key, lines, label, body, idx, fraction) in enumerate(STATES):
        c = render(lines, label, body, idx, fraction)
        c.save(os.path.join(out_dir, "state-%s.png" % key.replace(" ", "_")))
        thumb = c.resize((tw, th), Image.LANCZOS)
        ImageDraw.Draw(thumb).text((8, th - 30), key, font=label_font, fill=(255, 255, 255), stroke_width=3, stroke_fill=(0, 0, 0))
        sheet.paste(thumb, (12 + (i % 4) * (tw + 12), 12 + (i // 4) * (th + 12)))
    sheet.save(os.path.join(out_dir, "states.png"))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
