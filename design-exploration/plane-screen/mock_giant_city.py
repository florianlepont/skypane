"""Exploration mock-up: giant destination letters, sliced aircraft on top.

Standalone: does not touch server/plane/render. Run from the repo root:
    python3 design-exploration/plane-screen/mock_giant_city.py OUT.png [CITY_LINES...]
"""
import sys

from PIL import Image, ImageDraw, ImageFont

from server import panel_format as pf
from server.plane import dither, illustrations

W, H = pf.WIDTH, pf.HEIGHT
FONT = "server/assets/fonts/Inter-Bold.ttf"
BLUE = tuple(pf.PALETTE_RGB[12:15])
WHITE = (255, 255, 255)
LIGHT = (176, 202, 232)  # light blue, rendered by dithering blue/white


def fit_font(text, width, path=FONT):
    size = 100
    while ImageFont.truetype(path, size).getlength(text) < width:
        size += 4
    return ImageFont.truetype(path, size - 4)


def giant_text(canvas, lines, box, fill):
    """Each line is stretched to the box width and fitted to its own slot."""
    x0, y0, x1, y1 = box
    slot = (y1 - y0) / len(lines)
    gap = 14
    for i, line in enumerate(lines):
        f = ImageFont.truetype(FONT, 600)
        l, t, r, b = f.getbbox(line)
        layer = Image.new("L", (r - l, b - t), 0)
        ImageDraw.Draw(layer).text((-l, -t), line, font=f, fill=255)
        layer = layer.resize((x1 - x0, round(slot - gap)), Image.LANCZOS)
        canvas.paste(Image.new("RGB", layer.size, fill), (x0, round(y0 + slot * i)), layer)


def sliced_plane(canvas, key, plane_w, y_front, y_rear, cut=0.5):
    path = illustrations.resolved_illustration_path(key)
    im = Image.open(path).convert("RGBA")
    im = im.crop(im.getbbox())
    h = round(im.height * plane_w / im.width)
    im = im.resize((plane_w, h), Image.LANCZOS)
    cx = round(plane_w * cut)
    front, rear = im.crop((0, 0, cx, h)), im.crop((cx, 0, plane_w, h))
    # front half bleeds off the left edge, rear half off the right edge
    for piece, x, y in ((front, 40, y_front), (rear, W - 40 - (plane_w - cx), y_rear)):
        halo = Image.new("RGBA", piece.size, WHITE + (0,))
        alpha = piece.getchannel("A").filter(__import__("PIL.ImageFilter", fromlist=["x"]).MaxFilter(15))
        halo.putalpha(alpha)
        canvas.paste(halo, (x, y), halo)
        canvas.paste(piece, (x, y), piece)


def main(out, lines, key="air-france", flight="AF1006", airline="Air France", state="DEPARTING"):
    bg = Image.new("RGB", (W, H), WHITE)
    d = ImageDraw.Draw(bg)
    d.rectangle((0, 0, W, H), fill=LIGHT)
    giant_text(bg, lines, (40, 130, W - 40, 1290), BLUE)
    sliced_plane(bg, key, 1700, 520, 700)
    d = ImageDraw.Draw(bg)
    small = ImageFont.truetype(FONT, 56)
    d.text((64, 56), state, font=small, fill=BLUE)
    big = ImageFont.truetype(FONT, 150)
    d.text((64, 1330), flight, font=big, fill=BLUE)
    d.text((64, 1500), airline, font=ImageFont.truetype(FONT, 56), fill=BLUE)
    bg.save(out)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:] or ["MAR", "SEI", "LLE"])
