#!/usr/bin/env python3
import os
from PIL import Image, ImageDraw, ImageFont

BASE = os.path.dirname(__file__)
RENDERS = os.path.join(BASE, "renders")

CANDIDATES = [
    "ref-band-blue-dithered",
    "ref-band-blue-flat",
    "ref-band-green-dithered",
    "ref-band-red-flat",
    "ref-band-black-flat",
]

SCALE = 0.42
LABEL_H = 36

imgs = []
for name in CANDIDATES:
    path = os.path.join(RENDERS, "%s-full-composition.png" % name)
    img = Image.open(path).convert("RGB")
    img = img.resize((int(img.width * SCALE), int(img.height * SCALE)))
    imgs.append((name, img))

cell_w = imgs[0][1].width
cell_h = imgs[0][1].height + LABEL_H
cols = 3
rows = (len(imgs) + cols - 1) // cols
sheet = Image.new("RGB", (cell_w * cols, cell_h * rows), (255, 255, 255))
draw = ImageDraw.Draw(sheet)
try:
    font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 20)
except Exception:
    font = ImageFont.load_default()

for i, (name, img) in enumerate(imgs):
    col = i % cols
    row = i // cols
    x = col * cell_w
    y = row * cell_h
    draw.text((x + 8, y + 6), name, fill=(0, 0, 0), font=font)
    sheet.paste(img, (x, y + LABEL_H))

out_path = os.path.join(RENDERS, "contact_sheet_full_composition.png")
sheet.save(out_path)
print("wrote", out_path, sheet.size)
