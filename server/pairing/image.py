"""The two static e-ink screens of the pairing flow: pairing and retired.

Both use the calm status composition at the profile's own size, portrait or
landscape: the dithered dark field, a glyph, a small label and giant lines. The
pairing screen shows PAIR and then the code as its second giant line; the
retired screen shows FRAME RETIRED. Both are English only and byte-deterministic:
no clock, no countdown, no frame id, no MAC and no randomness. The only
varying input of the pairing screen is the code, so the frame's content hash
changes only when the code rotates.

A portrait profile of a size other than 1200x1600 gets the retired screen
scaled by min(w/1200, h/1600) with nearest-neighbour sampling (palette indices
stay exact) and centred on a field of the same kind, so nothing is clipped and
the text is never re-flowed.
"""
from __future__ import annotations

from PIL import Image

from server import hardware, panel_format, visible_window
from server.pairing import code as pairing_code
from server.plane import dither
from server.plane.render import style
from server.plane.render.giant import status


# Bumped whenever the retired screen's copy or layout changes on purpose; the
# server caches the retired panel under a name that carries it, so frames that
# are already retired pick the new screen up at their next wake.
RETIRED_SCREEN_REVISION = 4


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


def _framed(profile: hardware.HardwareProfile, build):
    """`build(size)` at the panel size, or inside the profile's visible window."""
    window = profile.visible_window
    if window is None:
        return build((profile.width, profile.height))
    return visible_window.place(
        build((window.width, window.height)), (profile.width, profile.height), window)


def render_pairing_image(profile: hardware.HardwareProfile, code: str) -> bytes:
    """The pairing screen for `code` (raw or formatted) as packed panel nibbles."""
    shown = pairing_code.format_code(code.replace("-", "").upper())
    return _pack(_framed(profile, lambda size: status.build_pairing(size, shown)))


def render_retired_image(profile: hardware.HardwareProfile) -> bytes:
    """The retired screen as packed panel nibbles; it carries no code or id.

    It is the calm status screen: landscape profiles get the landscape
    variant at their own size, portrait profiles the 1200x1600 reference
    scaled to fit.
    """
    if profile.width > profile.height:
        return _pack(_framed(profile, status.build_retired))
    reference = status.build_retired((panel_format.WIDTH, panel_format.HEIGHT))
    field = dither.dithered_state_background(
        style.DIMMED_FIELD_IDX, size=(profile.width, profile.height)
    )
    return _pack(_fit_to_profile(reference, profile, field))
