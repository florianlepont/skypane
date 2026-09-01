#!/usr/bin/env python3
"""Stack the White-theme departing-state 3x crops for all tracking variants
into one labelled contact sheet, matching spike 001's contact_sheet.png
convention."""
import os
from PIL import Image, ImageDraw, ImageFont

BASE = os.path.dirname(__file__)
RENDERS = os.path.join(BASE, "renders")

VARIANTS = [
    "baseline-0px",
    "tracked-2px",
    "tracked-4px",
    "tracked-6px",
    "smaller-tracked-6px",
]

LABEL_H = 40
imgs = []
for v in VARIANTS:
    path = os.path.join(RENDERS, "%s-white-departing-crop3x.png" % v)
    imgs.append((v, Image.open(path)))

w = imgs[0][1].width
row_h = imgs[0][1].height + LABEL_H
sheet = Image.new("RGB", (w, row_h * len(imgs)), (255, 255, 255))
draw = ImageDraw.Draw(sheet)
try:
    font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 28)
except Exception:
    font = ImageFont.load_default()

y = 0
for name, img in imgs:
    draw.text((20, y + 6), name, fill=(0, 0, 0), font=font)
    sheet.paste(img, (0, y + LABEL_H))
    y += row_h

out_path = os.path.join(RENDERS, "contact_sheet_white_departing.png")
sheet.save(out_path)
print("wrote", out_path, sheet.size)
