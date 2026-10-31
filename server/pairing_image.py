"""The two static e-ink screens of the pairing flow: pairing and retired.

Both are byte-deterministic: no clock, no countdown, no frame id, no MAC and
no randomness. The only varying input of the pairing screen is the code, so
the frame's content hash changes only when the code rotates. Text is drawn
with antialiasing off in exact palette indices, from the vendored fonts only.
Layout constants are for the 1200x1600 portrait panel; other hardware
profiles scale every coordinate and size by min(w/1200, h/1600) and never
re-flow the text.
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from server import hardware, pairing_code, panel_format

_FONT_DIR = Path(__file__).resolve().parent / "assets" / "fonts"
_REGULAR = str(_FONT_DIR / "Inter-Regular.ttf")
_BOLD = str(_FONT_DIR / "Inter-Bold.ttf")

# Reference panel the layout constants below are written for.
_REF_W = 1200
_REF_H = 1600

_MARGIN = 80
_TEXT_WIDTH = 1040  # reference width available between the margins

_PAIR_HEADER = "PAIR THIS FRAME"
_PAIR_EN = (
    "1. Open SkyPane on your phone or computer.",
    "2. Ask your administrator to enter this code.",
)
_PAIR_FR = (
    "1. Ouvrez SkyPane sur votre téléphone ou ordinateur.",
    "2. Demandez à votre administrateur de saisir ce code.",
)
_VALIDITY_EN = "Code changes about every 30 minutes."
_VALIDITY_FR = "Le code change environ toutes les 30 minutes."
_STATUS = "Waiting for pairing / En attente d'association"

_RETIRED_HEADER = "FRAME RETIRED"
_RETIRED_EN = (
    "This frame is no longer in service.",
    "Contact your administrator if this is a mistake.",
)
_RETIRED_FR_HEADER = "CADRE RETIRÉ"
_RETIRED_FR = (
    "Ce cadre n'est plus en service.",
    "Contactez votre administrateur en cas d'erreur.",
)
_BRAND = "SkyPane"

_CODE_SIZE = 168
_CODE_FLOOR = 128
_CODE_STEP = 8
_CODE_MAX_WIDTH = 944
_CODE_TRACKING = 10
_HYPHEN_FACTOR = 0.6

Font = ImageFont.FreeTypeFont


class _Layout:
    """Drawing context: the canvas, its scale and its centred origin."""

    def __init__(self, width: int, height: int) -> None:
        self.width = width
        self.height = height
        self.scale = min(width / _REF_W, height / _REF_H)
        self.origin_x = int(round((width - _REF_W * self.scale) / 2))
        self.origin_y = int(round((height - _REF_H * self.scale) / 2))
        self.image = Image.new("P", (width, height), panel_format.IDX_WHITE)
        self.image.putpalette(panel_format.padded_palette())
        self.draw = ImageDraw.Draw(self.image)
        # Antialiasing off: every pixel is an exact palette index.
        self.draw.fontmode = "1"

    def s(self, value: float) -> int:
        return max(1, int(round(value * self.scale)))

    def x(self, value: float) -> int:
        return self.origin_x + int(round(value * self.scale))

    def y(self, value: float) -> int:
        return self.origin_y + int(round(value * self.scale))

    def font(self, path: str, size: int) -> Font:
        return ImageFont.truetype(path, self.s(size))


def _pack(image: Image.Image) -> bytes:
    """Pack a P-mode canvas into two-pixels-per-byte panel nibbles."""
    table_hi = bytes(
        panel_format.INDEX_TO_NIBBLE.get(i, 0) << 4 for i in range(256)
    )
    table_lo = bytes(panel_format.INDEX_TO_NIBBLE.get(i, 0) for i in range(256))
    raw = image.tobytes()
    hi = raw[0::2].translate(table_hi)
    lo = raw[1::2].translate(table_lo)
    return (int.from_bytes(hi, "big") | int.from_bytes(lo, "big")).to_bytes(
        len(hi), "big"
    )


def _wrap(text: str, font: Font, max_width: int) -> list[str]:
    """Greedy word wrap of one paragraph to `max_width` pixels."""
    lines: list[str] = []
    current = ""
    for word in text.split(" "):
        trial = word if not current else f"{current} {word}"
        if current and font.getlength(trial) > max_width:
            lines.append(current)
            current = word
        else:
            current = trial
    lines.append(current)
    return lines


def _text_block(
    lay: _Layout,
    paragraphs: tuple[str, ...],
    top: int,
    size: int,
    pitch: int,
    path: str = _REGULAR,
) -> None:
    """Left-aligned paragraphs from reference y `top`, wrapped at the text width."""
    font = lay.font(path, size)
    line_y = lay.y(top)
    for paragraph in paragraphs:
        for line in _wrap(paragraph, font, lay.s(_TEXT_WIDTH)):
            lay.draw.text(
                (lay.x(_MARGIN), line_y), line, font=font, fill=panel_format.IDX_BLACK
            )
            line_y += lay.s(pitch)


def _header_band(lay: _Layout, text: str, fill: int) -> None:
    """Full-width band over reference y 0..220 with white bold text."""
    lay.draw.rectangle(
        (0, lay.y(0), lay.width - 1, lay.y(220) - 1), fill=fill
    )
    font = lay.font(_BOLD, 88)
    box = lay.draw.textbbox((0, 0), text, font=font)
    top = lay.y(110) - (box[1] + box[3]) // 2
    lay.draw.text(
        (lay.x(_MARGIN), top), text, font=font, fill=panel_format.IDX_WHITE
    )


def _centered(lay: _Layout, text: str, font: Font, centre_y: int) -> None:
    box = lay.draw.textbbox((0, 0), text, font=font)
    left = lay.origin_x + (lay.s(_REF_W) - (box[2] - box[0])) // 2 - box[0]
    top = centre_y - (box[1] + box[3]) // 2
    lay.draw.text((left, top), text, font=font, fill=panel_format.IDX_BLACK)


def _footer(lay: _Layout, status: str | None) -> None:
    """Blue rule at reference y 1500 with the brand and optional status."""
    lay.draw.rectangle(
        (lay.x(_MARGIN), lay.y(1500), lay.x(_REF_W - _MARGIN) - 1, lay.y(1508) - 1),
        fill=panel_format.IDX_BLUE,
    )
    font = lay.font(_REGULAR, 40)
    text_y = lay.y(1540)
    lay.draw.text(
        (lay.x(_MARGIN), text_y), _BRAND, font=font, fill=panel_format.IDX_BLUE
    )
    if status is not None:
        right = lay.x(_REF_W - _MARGIN)
        left = right - int(round(font.getlength(status)))
        lay.draw.text(
            (left, text_y), status, font=font, fill=panel_format.IDX_BLUE
        )


def _code_font_and_layout(lay: _Layout, text: str) -> tuple[Font, list[tuple[str, int]], int]:
    """The code font (stepped down to fit) with per-glyph advances and total width."""
    size = _CODE_SIZE
    limit = lay.s(_CODE_MAX_WIDTH)
    tracking = lay.s(_CODE_TRACKING)
    while True:
        font = lay.font(_BOLD, size)
        glyphs: list[tuple[str, int]] = []
        for ch in text:
            adv = font.getlength(ch)
            if ch == "-":
                adv *= _HYPHEN_FACTOR
            glyphs.append((ch, int(round(adv))))
        total = sum(a for _, a in glyphs) + tracking * (len(glyphs) - 1)
        if total <= limit or size <= _CODE_FLOOR:
            return font, glyphs, total
        size -= _CODE_STEP


def _code_box(lay: _Layout, text: str) -> None:
    """Black-framed white box over reference y 560..1040 holding the code."""
    frame = lay.s(6)
    box = (lay.x(_MARGIN), lay.y(560), lay.x(_REF_W - _MARGIN) - 1, lay.y(1040) - 1)
    lay.draw.rectangle(box, fill=panel_format.IDX_BLACK)
    lay.draw.rectangle(
        (box[0] + frame, box[1] + frame, box[2] - frame, box[3] - frame),
        fill=panel_format.IDX_WHITE,
    )
    font, glyphs, total = _code_font_and_layout(lay, text)
    tracking = lay.s(_CODE_TRACKING)
    cursor = (box[0] + box[2] + 1 - total) // 2
    ref = lay.draw.textbbox((0, 0), "0", font=font)
    top = (box[1] + box[3] + 1) // 2 - (ref[1] + ref[3]) // 2
    for ch, adv in glyphs:
        lay.draw.text((cursor, top), ch, font=font, fill=panel_format.IDX_BLACK)
        cursor += adv + tracking


def render_pairing_image(profile: hardware.HardwareProfile, code: str) -> bytes:
    """The pairing screen for `code` (raw or formatted) as packed panel nibbles."""
    shown = pairing_code.format_code(code.replace("-", "").upper())
    lay = _Layout(profile.width, profile.height)
    _header_band(lay, _PAIR_HEADER, panel_format.IDX_RED)
    _text_block(lay, _PAIR_EN, 260, 52, 68)
    _code_box(lay, shown)
    small = lay.font(_REGULAR, 44)
    _centered(lay, _VALIDITY_EN, small, lay.y(1082))
    _centered(lay, _VALIDITY_FR, small, lay.y(1136))
    _text_block(lay, _PAIR_FR, 1180, 52, 68)
    _footer(lay, _STATUS)
    return _pack(lay.image)


def render_retired_image(profile: hardware.HardwareProfile) -> bytes:
    """The retired screen as packed panel nibbles; it carries no code or id."""
    lay = _Layout(profile.width, profile.height)
    _header_band(lay, _RETIRED_HEADER, panel_format.IDX_BLACK)
    _text_block(lay, _RETIRED_EN, 300, 56, 76)
    lay.draw.rectangle(
        (lay.x(_MARGIN), lay.y(820), lay.x(_REF_W - _MARGIN) - 1, lay.y(824) - 1),
        fill=panel_format.IDX_BLACK,
    )
    _text_block(lay, (_RETIRED_FR_HEADER,), 890, 72, 90, path=_BOLD)
    _text_block(lay, _RETIRED_FR, 1040, 56, 76)
    _footer(lay, None)
    return _pack(lay.image)
