#!/usr/bin/env python3
"""Render companion/static/apple-touch-icon.png (180x180) from the logo's
home-screen tile with a headless Chromium.

Pillow cannot render SVG and the server stays stdlib + Pillow + requests, so the
PNG is rendered once here and committed. Run from the repo root:

    PLAYWRIGHT_BROWSERS_PATH=<browsers dir> python3 scripts/render_apple_touch_icon.py

The tile is a full-bleed accent square (iOS rounds the corners itself) with the
whole mark in white, scaled to 56% so it stays inside the safe zone.
"""
import os
import sys

from playwright.sync_api import sync_playwright

SIZE = 180
OUT = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "companion", "static", "apple-touch-icon.png")

# Same geometry as the `icon-logo` sprite symbol in companion/ui_base.py, with
# the accent flick drawn in white as well.
TILE_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 180 180" width="180" height="180">'
    '<rect width="180" height="180" fill="#B13F16"/>'
    '<g transform="translate(39.60 39.60) scale(3.1500)" fill="none" stroke="#FFFFFF" '
    'stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M17 2H10A4 4 0 0 0 6 6V26A4 4 0 0 0 10 30H22A4 4 0 0 0 26 26V15"/>'
    '<path d="M20.6 14.2C20.6 12.2 18.7 11 16 11C13.2 11 11.4 12.3 11.4 14.4C11.4 16.6 13.6 17.4 '
    "16 18.2C18.8 19.1 20.8 20 20.8 22.3C20.8 24.4 18.8 25.6 16 25.6C13.3 25.6 11.4 24.6 "
    '11.1 22.4"/>'
    '<path d="M20.8 9.2L28.2 1.8"/></g></svg>'
)


def main():
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": SIZE, "height": SIZE}, device_scale_factor=1)
        page.set_content(
            "<!doctype html><body style='margin:0'>%s</body>" % TILE_SVG)
        page.screenshot(path=OUT, clip={"x": 0, "y": 0, "width": SIZE, "height": SIZE})
        browser.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
