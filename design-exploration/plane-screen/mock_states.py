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
# Generic screens: they do not follow the theme. As today, the watching screen
# is white with black ink (the frame is working) and the others use the dimmed
# (dithered dark) field with white ink (the frame is resting).
STATES = [
    ("watching", ["RUNWAY", "3"], "WATCHING", ["No aircraft detected yet.", "The display updates the moment one is."], glyphs.draw_runway_icon),
    ("quiet hours", ["QUIET", "HOURS"], "SLEEPING", ["Back at 07:00"], glyphs.draw_moon_icon),
    ("display off", ["DISPLAY", "OFF"], "SWITCHED OFF", ["Turn it back on from the companion page."], glyphs.draw_power_icon),
    ("battery empty", ["BATTERY", "EMPTY"], "CHARGE ME", ["Charge the frame over USB-C.", "It will pick up where it left off."], glyphs.draw_empty_battery_icon),
    ("no connection", ["NO", "CONNECTION"], "OFFLINE", ["The frame can't reach its server.", "It will try again on its own."], glyphs.draw_alert_icon),
    ("updating", ["FIRMWARE", "UPDATE"], "INSTALLING", ["Installing a firmware update.", "The frame will restart when it's ready."], glyphs.draw_updating_icon),
    ("frame retired", ["FRAME", "RETIRED"], "SKYPANE", ["This frame was removed from SkyPane.", "Ask an administrator to set it up again."], glyphs.draw_power_icon),
]


def icon_mask(drawer):
    """The production glyph as an L mask (the glyph code draws with palette indices)."""
    img = Image.new("P", (200, 200), 0)
    img.putpalette([0, 0, 0, 255, 255, 255])
    drawer(ImageDraw.Draw(img), 100, 60, 1)
    return img.convert("L")


def render(lines, label, body, drawer, watching=False, icon_at="corner"):
    """icon_at: "corner" (small, top right), "start" (before the first line) or
    "end" (after the last line); the icon then shares its line, scaled to the
    line's height."""
    c = Image.new("RGB", (W, H), WHITE) if watching else t.field(pf.IDX_BLACK, True).copy()
    ink = (0, 0, 0) if watching else WHITE
    calm = icon_at == "calm"
    x0, x1, y0, y1 = (110, W - 110, 380, 1180) if calm else (40, W - 40, 130, 1290)
    slot = (y1 - y0) / len(lines)
    mask = icon_mask(drawer)
    mask = mask.crop(mask.getbbox())
    gap = 14
    for i, line in enumerate(lines):
        left, right = x0, x1
        target = (icon_at == "start" and i == 0) or (icon_at == "end" and i == len(lines) - 1)
        if target:
            icon_h = round(slot - gap)
            icon_w = round(mask.width * icon_h / mask.height)
            icon = mask.resize((icon_w, icon_h), Image.LANCZOS)
            top = round(y0 + slot * i)
            if icon_at == "start":
                c.paste(Image.new("RGB", icon.size, ink), (x0, top), icon)
                left = x0 + icon_w + 30
            else:
                c.paste(Image.new("RGB", icon.size, ink), (x1 - icon_w, top), icon)
                right = x1 - icon_w - 30
        if calm:  # natural proportions, flush left, one common cap height
            size = min(330, round(slot * 0.8))  # leave a gap between lines
            font = ImageFont.truetype(g.FONT_HEAVY, size)
            c_draw = ImageDraw.Draw(c)
            bb = c_draw.textbbox((0, 0), line, font=font)
            scale = min(1.0, (x1 - x0) / (bb[2] - bb[0]))
            if scale < 1.0:
                font = ImageFont.truetype(g.FONT_HEAVY, round(size * scale))
                bb = c_draw.textbbox((0, 0), line, font=font)
            c_draw.text((x0 - bb[0], round(y0 + slot * i) - bb[1]), line, font=font, fill=ink)
            continue
        g.giant_text(c, [line], (left, round(y0 + slot * i), right, round(y0 + slot * (i + 1))), ink, heavy=1, stretch=True)
    dr = ImageDraw.Draw(c)
    label_x = 64
    if icon_at == "label":  # small icon before the small label, same row
        h = 64
        icon = mask.resize((round(mask.width * h / mask.height), h), Image.LANCZOS)
        c.paste(Image.new("RGB", icon.size, ink), (64, 54), icon)
        label_x = 64 + icon.width + 22
    if icon_at == "footer":  # icon bottom-left, facing the body text
        h = 120
        icon = mask.resize((round(mask.width * h / mask.height), h), Image.LANCZOS)
        c.paste(Image.new("RGB", icon.size, ink), (64, 1330), icon)
    if calm:
        h = 120
        icon = mask.resize((round(mask.width * h / mask.height), h), Image.LANCZOS)
        c.paste(Image.new("RGB", icon.size, ink), (110, 120), icon)
        dr.text((110, 262), label, font=ImageFont.truetype(g.FONT, 52), fill=ink)
        y = 1290
        for line in body:
            dr.text((110, y), line, font=ImageFont.truetype(g.FONT, 40), fill=ink)
            y += 58
        return c
    dr.text((label_x, 56), label, font=ImageFont.truetype(g.FONT, 56), fill=ink)
    if icon_at == "corner":
        small = icon_mask(drawer)
        c.paste(Image.new("RGB", small.size, ink), (W - 64 - 38 - 100, 44 - 60), small)
    y = 1330
    for line in body:
        font = ImageFont.truetype(g.FONT, 46)
        dr.text((W - 64 - font.getlength(line), y), line, font=font, fill=ink)
        y += 64
    return c


def main(out_dir, font_dir):
    icon_at = os.environ.get("MOCK_ICON", "corner")
    os.makedirs(out_dir, exist_ok=True)
    g.FONT_HEAVY = os.path.join(font_dir, "Anton-Regular.ttf")
    tw, th = 300, 400
    label_font = ImageFont.truetype("server/assets/fonts/Inter-Bold.ttf", 22)
    sheet = Image.new("RGB", (4 * (tw + 12) + 12, 2 * (th + 12) + 12), (110, 110, 110))
    for i, (key, lines, label, body, drawer) in enumerate(STATES):
        c = render(lines, label, body, drawer, watching=(key == "watching"), icon_at=icon_at)
        c.save(os.path.join(out_dir, "state-%s.png" % key.replace(" ", "_")))
        thumb = c.resize((tw, th), Image.LANCZOS)
        ImageDraw.Draw(thumb).text((8, th - 30), key, font=label_font, fill=(255, 255, 255), stroke_width=3, stroke_fill=(0, 0, 0))
        sheet.paste(thumb, (12 + (i % 4) * (tw + 12), 12 + (i // 4) * (th + 12)))
    sheet.save(os.path.join(out_dir, "states.png"))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
