"""Seven horizontal ways to place the aircraft over the giant destination lettering.

Standalone exploration: does not touch server/plane/render. Run from the repo
root with PYTHONPATH=.:
    python3 design-exploration/plane-screen/mock_plane_variants.py OUT_DIR
Writes variant-01.png .. variant-07.png (1200x1600) and sheet.png.
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mock_giant_city as g  # noqa: E402

from server.plane import illustrations  # noqa: E402

W, H = g.W, g.H
BLUE, WHITE, LIGHT = g.BLUE, g.WHITE, g.LIGHT
LINES = os.environ.get("MOCK_LINES", "MAR,SEI,LLE").split(",")
PLANE_KEY = os.environ.get("MOCK_PLANE", "air-france")
STATE = os.environ.get("MOCK_STATE", "DEPARTING")
FLIGHT = os.environ.get("MOCK_FLIGHT", "AF1006")
AIRLINE = os.environ.get("MOCK_AIRLINE", "Air France")
HEAVY = int(os.environ.get("MOCK_HEAVY", "22"))  # extra stroke in px at 600 px font size


def load_plane(width, angle=0):
    path = illustrations.generic_fallback_path() if PLANE_KEY == "generic" else illustrations.resolved_illustration_path(PLANE_KEY)
    im = Image.open(path).convert("RGBA")
    im = im.crop(im.getbbox())
    im = im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)
    if angle:
        im = im.rotate(-angle, expand=True, resample=Image.BICUBIC)
    return im


def paste_with_halo(canvas, im, centre, halo=15):
    pos = (round(centre[0] - im.width / 2), round(centre[1] - im.height / 2))
    if halo > 1:
        layer = Image.new("RGBA", im.size, WHITE + (0,))
        layer.putalpha(im.getchannel("A").filter(ImageFilter.MaxFilter(halo)))
        canvas.paste(layer, pos, layer)
    canvas.paste(im, pos, im)


def base(text_box=(40, 130, W - 40, 1290), text_fill=BLUE, bg=LIGHT):
    canvas = Image.new("RGB", (W, H), bg)
    g.giant_text(canvas, LINES, text_box, text_fill, heavy=HEAVY)
    return canvas


def footer(canvas, state=None, flight=None, airline=None, ink=None):
    ink = ink or BLUE
    state, flight, airline = state or STATE, flight or FLIGHT, airline or AIRLINE
    d = ImageDraw.Draw(canvas)
    d.text((64, 56), state, font=ImageFont.truetype(g.FONT, 56), fill=ink)
    d.text((64, 1330), flight, font=ImageFont.truetype(g.FONT, 150), fill=ink)
    d.text((64, 1500), airline, font=ImageFont.truetype(g.FONT, 56), fill=ink)


def v01():  # whole, centred, full width
    c = base()
    paste_with_halo(c, load_plane(1120), (W / 2, 710))
    return c


def v05():  # huge close-up, nose and tail cropped by the frame
    c = base()
    paste_with_halo(c, load_plane(2100), (W / 2, 720), halo=1)
    return c


def v06():  # runway band: full-width dark band, aircraft rides on it
    c = base()
    d = ImageDraw.Draw(c)
    d.rectangle((0, 640, W, 840), fill=BLUE)
    for x in range(0, W, 120):
        d.rectangle((x + 20, 735, x + 80, 745), fill=WHITE)
    paste_with_halo(c, load_plane(1100), (W / 2, 640), halo=1)
    return c


def v07():  # white disc (sun / porthole), aircraft breaks out of it
    c = base()
    d = ImageDraw.Draw(c)
    d.ellipse((120, 300, 1080, 1260), fill=WHITE)
    paste_with_halo(c, load_plane(1160), (W / 2, 780), halo=1)
    return c


def v08():  # tail fin only, giant, bottom-right: the livery from afar
    c = base()
    full = load_plane(2200)
    tail = full.crop((int(full.width * 0.62), 0, full.width, full.height))
    pos = (W - tail.width + 40, 1330 - tail.height)
    layer = Image.new("RGBA", tail.size, WHITE + (0,))
    layer.putalpha(tail.getchannel("A").filter(ImageFilter.MaxFilter(15)))
    c.paste(layer, pos, layer)
    c.paste(tail, pos, tail)
    return c


def v09():  # lettering compressed on top, aircraft in its own lower band
    c = base(text_box=(40, 130, W - 40, 900))
    paste_with_halo(c, load_plane(1120), (W / 2, 1110))
    return c


def v10():  # aircraft with a hard offset shadow in the dark ink
    c = base()
    plane = load_plane(1120)
    shadow = Image.new("RGBA", plane.size, BLUE + (0,))
    shadow.putalpha(plane.getchannel("A"))
    c.paste(shadow, (round(W / 2 - plane.width / 2) + 28, 710 - plane.height // 2 + 40), shadow)
    paste_with_halo(c, plane, (W / 2, 710), halo=1)
    return c


def vcockpit():  # nose and cockpit only, entering from the right edge
    c = base()
    full = load_plane(2500)
    nose = full.crop((0, 0, int(full.width * 0.36), full.height))
    nose = nose.crop(nose.getbbox())
    pos = (W - nose.width + 30, 700 - nose.height // 2)
    layer = Image.new("RGBA", nose.size, WHITE + (0,))
    layer.putalpha(nose.getchannel("A").filter(ImageFilter.MaxFilter(15)))
    c.paste(layer, pos, layer)
    c.paste(nose, pos, nose)
    return c


def halo_paste(canvas, piece, pos, halo=15):
    layer = Image.new("RGBA", piece.size, WHITE + (0,))
    layer.putalpha(piece.getchannel("A").filter(ImageFilter.MaxFilter(halo)))
    canvas.paste(layer, pos, layer)
    canvas.paste(piece, pos, piece)


def vnose_tail(c=None):
    """Big nose above, small tail below; both halves bleed off the frame."""
    c = c or base()
    full = load_plane(2200)
    nose = full.crop((0, 0, int(full.width * 0.5), full.height))
    nose = nose.crop(nose.getbbox())
    ny = 470 - nose.height // 2
    halo_paste(c, nose, (W - nose.width + 30, ny))
    small = load_plane(1250)
    tail = small.crop((int(small.width * 0.5), 0, small.width, small.height))
    tail = tail.crop(tail.getbbox())
    halo_paste(c, tail, (-30, 1275 - tail.height))
    return c


VARIANTS = [v01, v09, vcockpit, vnose_tail]


def main(out_dir):
    os.makedirs(out_dir, exist_ok=True)
    tw, th = 360, 480
    sheet = Image.new("RGB", (len(VARIANTS) * (tw + 12) + 12, th + 24), (110, 110, 110))
    label_font = ImageFont.truetype(g.FONT, 36)
    for i, fn in enumerate(VARIANTS):
        canvas = fn()
        footer(canvas)
        canvas.save(os.path.join(out_dir, "variant-%02d.png" % (i + 1)))
        thumb = canvas.resize((tw, th), Image.LANCZOS)
        ImageDraw.Draw(thumb).text((tw - 50, th - 52), str(i + 1), font=label_font, fill=(200, 30, 30))
        sheet.paste(thumb, (12 + i * (tw + 12), 12))
    sheet.save(os.path.join(out_dir, "sheet.png"))


if __name__ == "__main__":
    main(sys.argv[1])
