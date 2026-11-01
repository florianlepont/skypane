"""The two static e-ink screens of the pairing flow: pairing and retired.

Both use the shared hold composition of the other status screens (glyph,
tracked label, short rule, text), English only. They are byte-deterministic:
no clock, no countdown, no frame id, no MAC and no randomness. The only
varying input of the pairing screen is the code, so the frame's content hash
changes only when the code rotates.

The composition is drawn on the 1200x1600 reference canvas. Other hardware
profiles get that canvas scaled by min(w/1200, h/1600) with nearest-neighbour
sampling (palette indices stay exact) and centred on a field of the same
kind, so nothing is clipped and the text is never re-flowed.
"""
from __future__ import annotations

from PIL import Image

from server import hardware, pairing_code, panel_format
from server.plane import dither
from server.plane.render import glyphs, hold_screens, style

_PAIR_LABEL = "PAIR THIS FRAME"
_PAIR_BODY = (
    "Enter this code on the SkyPane companion page.",
    "It changes about every 30 minutes.",
)
_RETIRED_LABEL = "FRAME RETIRED"
_RETIRED_BODY = (
    "This frame was removed from SkyPane.",
    "Ask an administrator to set it up again.",
)


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


def _fit_to_profile(
    reference: Image.Image,
    profile: hardware.HardwareProfile,
    field: Image.Image,
) -> Image.Image:
    """`reference` scaled to fit the profile and centred on `field`."""
    if (profile.width, profile.height) == reference.size:
        return reference
    scale = min(profile.width / reference.width, profile.height / reference.height)
    size = (
        max(1, int(round(reference.width * scale))),
        max(1, int(round(reference.height * scale))),
    )
    scaled = reference.resize(size, Image.Resampling.NEAREST)
    field.paste(
        scaled,
        ((profile.width - size[0]) // 2, (profile.height - size[1]) // 2),
    )
    return field


def render_pairing_image(profile: hardware.HardwareProfile, code: str) -> bytes:
    """The pairing screen for `code` (raw or formatted) as packed panel nibbles."""
    shown = pairing_code.format_code(code.replace("-", "").upper())
    reference = hold_screens._build_hold_canvas(
        glyphs.draw_link_icon,
        glyphs.LINK_ICON_HEIGHT_PX,
        _PAIR_LABEL,
        _PAIR_BODY,
        panel_format.IDX_WHITE,
        panel_format.IDX_BLACK,
        False,
        code_text=shown,
    )
    field = panel_format.new_canvas(
        panel_format.IDX_WHITE, (profile.width, profile.height)
    )
    return _pack(_fit_to_profile(reference, profile, field))


def render_retired_image(profile: hardware.HardwareProfile) -> bytes:
    """The retired screen as packed panel nibbles; it carries no code or id."""
    reference = hold_screens._build_dimmed_hold_canvas(
        glyphs.draw_power_icon,
        glyphs.POWER_ICON_BAR_RISE_PX + glyphs.POWER_ICON_DIAMETER_PX,
        _RETIRED_LABEL,
        _RETIRED_BODY,
    )
    field = dither.dithered_state_background(
        style.DIMMED_FIELD_IDX, size=(profile.width, profile.height)
    )
    return _pack(_fit_to_profile(reference, profile, field))
