"""Exploration mock-up: giant destination letters, sliced aircraft on top.

Standalone: does not touch server/plane/render. Run from the repo root:
    python3 design-exploration/plane-screen/mock_giant_city.py OUT.png [CITY_LINES...]
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from server import panel_format as pf
from server.plane import illustrations

W, H = pf.WIDTH, pf.HEIGHT
MODE = os.environ.get("MOCK_MODE", "sliced")
FONT = "server/assets/fonts/Inter-Bold.ttf"
FONT_HEAVY = "/usr/share/fonts/opentype/inter/Inter-Black.otf"
BLUE = tuple(pf.PALETTE_RGB[12:15])
WHITE = (255, 255, 255)
LIGHT = (176, 202, 232)  # light blue, rendered by dithering blue/white
if os.environ.get("MOCK_THEME") == "green":  # arriving: panel green ink on a light green
    BLUE = tuple(pf.PALETTE_RGB[15:18])
    LIGHT = (184, 214, 190)


def fit_font(text, width, path=FONT):
    size = 100
    while ImageFont.truetype(path, size).getlength(text) < width:
        size += 4
    return ImageFont.truetype(path, size - 4)


def giant_text(canvas, lines, box, fill, heavy=0, stretch=False):
    """Each line is stretched to the box width and fitted to its own slot."""
    x0, y0, x1, y1 = box
    slot = (y1 - y0) / len(lines)
    gap = 14
    for i, line in enumerate(lines):
        f = ImageFont.truetype(FONT_HEAVY if heavy else FONT, 600)
        left, top, right, bottom = f.getbbox(line, stroke_width=heavy)
        layer = Image.new("L", (right - left, bottom - top), 0)
        ImageDraw.Draw(layer).text((-left, -top), line, font=f, fill=255, stroke_width=heavy, stroke_fill=255)
        if len(lines) == 1 and not stretch:  # a single word keeps its own proportions, centred in the box
            scale = (x1 - x0) / layer.width
            layer = layer.resize((x1 - x0, round(layer.height * scale)), Image.LANCZOS)
            y_top = round((y0 + y1 - layer.height) / 2)
        else:
            layer = layer.resize((x1 - x0, round(slot - gap)), Image.LANCZOS)
            y_top = round(y0 + slot * i)
        pos = (x0, y_top)
        if isinstance(fill, Image.Image):  # a canvas-sized pattern, e.g. a dithered ink
            src = fill.crop((pos[0], pos[1], pos[0] + layer.width, pos[1] + layer.height))
        else:
            src = Image.new("RGB", layer.size, fill)
        canvas.paste(src, pos, layer)


def sliced_plane(canvas, key, half_w, center_y, gap=36):
    """Two equal-width halves, point-symmetric about the canvas centre.

    The nose half is flush with the right edge, the tail half flush with the
    left edge; the halves are stacked without overlap and the stack is
    centred vertically on `center_y`.
    """
    path = illustrations.resolved_illustration_path(key)
    im = Image.open(path).convert("RGBA")
    im = im.crop(im.getbbox())
    plane_w = half_w * 2
    h = round(im.height * plane_w / im.width)
    im = im.resize((plane_w, h), Image.LANCZOS)
    front, rear = im.crop((0, 0, half_w, h)), im.crop((half_w, 0, plane_w, h))
    pieces = []
    for piece in (front, rear):
        piece = piece.crop(piece.getbbox())
        pieces.append(piece)
    total = sum(p.height for p in pieces) + gap
    y = round(center_y - total / 2)
    xs = (W - pieces[0].width, 0)
    for piece, x in zip(pieces, xs):
        halo = Image.new("RGBA", piece.size, WHITE + (0,))
        halo.putalpha(piece.getchannel("A").filter(ImageFilter.MaxFilter(15)))
        canvas.paste(halo, (x, y), halo)
        canvas.paste(piece, (x, y), piece)
        y += piece.height + gap
    print("pieces", [p.size for p in pieces], "stack", total)


def whole_plane(canvas, key, plane_w, center_y):
    """The uncut aircraft, centred on the canvas."""
    im = Image.open(illustrations.resolved_illustration_path(key)).convert("RGBA")
    im = im.crop(im.getbbox())
    im = im.resize((plane_w, round(im.height * plane_w / im.width)), Image.LANCZOS)
    pos = ((W - im.width) // 2, round(center_y - im.height / 2))
    halo = Image.new("RGBA", im.size, WHITE + (0,))
    halo.putalpha(im.getchannel("A").filter(ImageFilter.MaxFilter(15)))
    canvas.paste(halo, pos, halo)
    canvas.paste(im, pos, im)


def main(out, lines, key="air-france", flight="AF1006", airline="Air France", state="DEPARTING"):
    bg = Image.new("RGB", (W, H), WHITE)
    d = ImageDraw.Draw(bg)
    d.rectangle((0, 0, W, H), fill=LIGHT)
    giant_text(bg, lines, (40, 130, W - 40, 1290), BLUE)
    if MODE == "whole":
        whole_plane(bg, key, 1120, 710)
    else:
        sliced_plane(bg, key, 620, 710)
    d = ImageDraw.Draw(bg)
    small = ImageFont.truetype(FONT, 56)
    d.text((64, 56), state, font=small, fill=BLUE)
    big = ImageFont.truetype(FONT, 150)
    d.text((64, 1330), flight, font=big, fill=BLUE)
    d.text((64, 1500), airline, font=ImageFont.truetype(FONT, 56), fill=BLUE)
    bg.save(out)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:] or ["MAR", "SEI", "LLE"])
