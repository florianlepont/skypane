"""Hold/status screens in the giant-lettering design (portrait, 1200x1600).

    PYTHONPATH=. python3 design-exploration/plane-screen/mock_states.py OUT_DIR FONT_DIR
FONT_DIR holds Anton-Regular.ttf (SIL OFL, fetched outside the repository).
The pairing screen is excluded: its code is read up close and typed by hand.
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mock_giant_city as g  # noqa: E402
import mock_themes as t  # noqa: E402

from server import panel_format as pf  # noqa: E402
from server.plane.render import glyphs  # noqa: E402

W, H = g.W, g.H
WHITE = (255, 255, 255)

# (key, lettering lines, small label, body lines, icon drawer)
# Generic screens: they do not follow the theme and share one look: the
# dimmed (dithered dark) field with white ink, as the non-watching screens
# are today.
STATES = [
    ("watching", ["RUNWAY", "3"], "WATCHING", ["No aircraft detected yet.", "The display updates the moment one is."], glyphs.draw_runway_icon),
    ("quiet hours", ["QUIET", "HOURS"], "SLEEPING", ["Back at 07:00"], glyphs.draw_moon_icon),
    ("display off", ["DISPLAY", "OFF"], "SWITCHED OFF", ["Turn it back on from the companion page."], glyphs.draw_power_icon),
    ("battery empty", ["BATTERY", "EMPTY"], "CHARGE ME", ["Charge the frame over USB-C.", "It will pick up where it left off."], glyphs.draw_empty_battery_icon),
    ("no connection", ["NO", "CONNEC", "TION"], "OFFLINE", ["The frame can't reach its server.", "It will try again on its own."], glyphs.draw_alert_icon),
    ("updating", ["UPDA", "TING"], "FIRMWARE", ["Installing a firmware update.", "The frame will restart when it's ready."], glyphs.draw_updating_icon),
    ("frame retired", ["FRAME", "RETIRED"], "SKYPANE", ["This frame was removed from SkyPane.", "Ask an administrator to set it up again."], glyphs.draw_power_icon),
]


def icon_mask(drawer):
    """The production glyph as an L mask (the glyph code draws with palette indices)."""
    img = Image.new("P", (200, 200), 0)
    img.putpalette([0, 0, 0, 255, 255, 255])
    drawer(ImageDraw.Draw(img), 100, 60, 1)
    return img.convert("L")


def render(lines, label, body, drawer):
    c = t.field(pf.IDX_BLACK, True).copy()
    ink = WHITE
    g.giant_text(c, lines, (40, 130, W - 40, 1290), ink, heavy=1)
    dr = ImageDraw.Draw(c)
    dr.text((64, 56), label, font=ImageFont.truetype(g.FONT, 56), fill=ink)
    mask = icon_mask(drawer)
    c.paste(Image.new("RGB", mask.size, ink), (W - 64 - 38 - 100, 44 - 60), mask)
    y = 1330
    for line in body:
        font = ImageFont.truetype(g.FONT, 46)
        dr.text((W - 64 - font.getlength(line), y), line, font=font, fill=ink)
        y += 64
    return c


def main(out_dir, font_dir):
    os.makedirs(out_dir, exist_ok=True)
    g.FONT_HEAVY = os.path.join(font_dir, "Anton-Regular.ttf")
    tw, th = 300, 400
    label_font = ImageFont.truetype("server/assets/fonts/Inter-Bold.ttf", 22)
    sheet = Image.new("RGB", (4 * (tw + 12) + 12, 2 * (th + 12) + 12), (110, 110, 110))
    for i, (key, lines, label, body, drawer) in enumerate(STATES):
        c = render(lines, label, body, drawer)
        c.save(os.path.join(out_dir, "state-%s.png" % key.replace(" ", "_")))
        thumb = c.resize((tw, th), Image.LANCZOS)
        ImageDraw.Draw(thumb).text((8, th - 30), key, font=label_font, fill=(255, 255, 255), stroke_width=3, stroke_fill=(0, 0, 0))
        sheet.paste(thumb, (12 + (i % 4) * (tw + 12), 12 + (i // 4) * (th + 12)))
    sheet.save(os.path.join(out_dir, "states.png"))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
