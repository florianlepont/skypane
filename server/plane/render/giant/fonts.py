"""Anton loader and glyph-support helpers for the giant-lettering family.

Imports nothing from `server.plane.render.layout` (that module imports the
render family, so the reverse would be a cycle).
"""
import os
import unicodedata

from PIL import ImageFont

ANTON_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
    "assets", "fonts", "Anton-Regular.ttf",
)

INTER_BOLD_PATH = os.path.join(os.path.dirname(ANTON_PATH), "Inter-Bold.ttf")

# Size at which a stretched line is drawn before being scaled to fit, so the
# scaled result stays sharp.
SUPERSAMPLE_PX = 600

# A code point no font maps; fonts draw their fallback glyph for it.
_UNMAPPED_CHAR = "\U0010FFFF"
_MEASURE_PX = 64

_font_cache: dict = {}


def anton(px):
    """Cached Anton ImageFont at `px` pixels."""
    if px not in _font_cache:
        _font_cache[px] = ImageFont.truetype(ANTON_PATH, px)
    return _font_cache[px]


def inter_bold(px: int) -> ImageFont.FreeTypeFont:
    """Cached Inter Bold ImageFont at `px` pixels, used for small text."""
    key = ("inter", px)
    if key not in _font_cache:
        _font_cache[key] = ImageFont.truetype(INTER_BOLD_PATH, px)
    return _font_cache[key]


def cap_height(px):
    """Height in pixels of a capital letter at `px`, measured from "H" so
    accented lines are not shrunk by their diacritics.
    """
    left, top, right, bottom = anton(px).getbbox("H")
    return bottom - top


def _glyph_bytes(char):
    return bytes(anton(_MEASURE_PX).getmask(char))


def supports(text):
    """Whether Anton has a real glyph for every non-space character in
    `text`. A character counts as missing when it renders identically to a
    code point no font maps. Cost is linear in the distinct characters.
    """
    missing = _glyph_bytes(_UNMAPPED_CHAR)
    for char in set(text):
        if char.isspace():
            continue
        if _glyph_bytes(char) == missing:
            return False
    return True


def ascii_fallback(text):
    """`text` with accents decomposed away and non-ASCII dropped, stripped;
    None when nothing printable remains.
    """
    decomposed = unicodedata.normalize("NFKD", text)
    kept = "".join(ch for ch in decomposed if ch.isascii() and (ch.isprintable()))
    kept = kept.strip()
    return kept or None
