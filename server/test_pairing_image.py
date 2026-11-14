"""Deterministic pairing and retired e-ink screens."""
from __future__ import annotations

import hashlib
import inspect
import subprocess
import sys
from pathlib import Path

import pytest

from PIL import Image

from server import hardware, pairing_image, panel_format
from server.plane.render import style
from server.plane.render.giant import status

REPO_ROOT = Path(__file__).resolve().parent.parent
FAKE_CODE = "ABCD2345"
LEGAL_NIBBLES = {
    panel_format.BLACK,
    panel_format.WHITE,
    panel_format.YELLOW,
    panel_format.RED,
    panel_format.BLUE,
    panel_format.GREEN,
}
# sha256 of the retired screen for the legacy profile; changes only when the
# retired layout, copy or fonts change on purpose.
RETIRED_GOLDEN_SHA256 = "7222f198c2ce485f5ab0d67a62d1198bc9259e2a006740eb830c07d2e5d93f04"
# sha256 of the pairing screen for FAKE_CODE on the legacy profile.
PAIRING_GOLDEN_SHA256 = "3e5d41f52f68dc506fa4f3e983b597f9382d2c183e8e9bdd47c93a8d55ba7ba0"


@pytest.fixture()
def legacy() -> hardware.HardwareProfile:
    return hardware.get_profile(hardware.LEGACY_KEY)


def _pixel(data: bytes, profile: hardware.HardwareProfile, x: int, y: int) -> int:
    byte = data[y * (profile.width // 2) + x // 2]
    return byte >> 4 if x % 2 == 0 else byte & 0x0F


def _nibbles(data: bytes) -> set[int]:
    return {b >> 4 for b in data} | {b & 0x0F for b in data}


def test_lengths(legacy: hardware.HardwareProfile) -> None:
    expected = (legacy.width // 2) * legacy.height
    assert expected == 960000
    assert len(pairing_image.render_pairing_image(legacy, FAKE_CODE)) == expected
    assert len(pairing_image.render_retired_image(legacy)) == expected


def test_only_panel_colours(legacy: hardware.HardwareProfile) -> None:
    assert _nibbles(pairing_image.render_pairing_image(legacy, FAKE_CODE)) <= LEGAL_NIBBLES
    assert _nibbles(pairing_image.render_retired_image(legacy)) <= LEGAL_NIBBLES


def test_determinism_and_golden(legacy: hardware.HardwareProfile) -> None:
    first = pairing_image.render_pairing_image(legacy, FAKE_CODE)
    second = pairing_image.render_pairing_image(legacy, FAKE_CODE)
    assert hashlib.sha256(first).digest() == hashlib.sha256(second).digest()
    other = pairing_image.render_pairing_image(legacy, "WXYZ6789")
    assert hashlib.sha256(other).digest() != hashlib.sha256(first).digest()
    script = (
        "import sys, hashlib\n"
        f"sys.path.insert(0, {str(REPO_ROOT)!r})\n"
        "from server import hardware, pairing_image\n"
        f"p = hardware.get_profile({hardware.LEGACY_KEY!r})\n"
        f"print(hashlib.sha256(pairing_image.render_pairing_image(p, {FAKE_CODE!r})).hexdigest())\n"
        "print(hashlib.sha256(pairing_image.render_retired_image(p)).hexdigest())\n"
    )
    out = subprocess.run(
        [sys.executable, "-I", "-c", script],
        capture_output=True, text=True, check=True, cwd="/",
    ).stdout.split()
    assert out[0] == hashlib.sha256(first).hexdigest()
    assert out[0] == PAIRING_GOLDEN_SHA256
    retired = hashlib.sha256(pairing_image.render_retired_image(legacy)).hexdigest()
    assert out[1] == retired
    assert retired == RETIRED_GOLDEN_SHA256


def test_pairing_screen_is_byte_identical_to_its_pinned_hash(
    legacy: hardware.HardwareProfile,
) -> None:
    """The pairing code is read up close and typed by hand: the calm status
    restyle must not touch this screen."""
    shown = hashlib.sha256(pairing_image.render_pairing_image(legacy, FAKE_CODE)).hexdigest()
    assert shown == PAIRING_GOLDEN_SHA256


def _ink_rows(data: bytes, profile: hardware.HardwareProfile) -> list[tuple[int, int, int]]:
    """Bands of consecutive rows holding black ink: (first row, last row, width)."""
    bands: list[tuple[int, int, int]] = []
    start = None
    left, right = profile.width, -1
    for y in range(profile.height):
        xs = [
            x for x in range(0, profile.width, 1)
            if _pixel(data, profile, x, y) == panel_format.BLACK
        ]
        if xs:
            if start is None:
                start, left, right = y, profile.width, -1
            left, right = min(left, xs[0]), max(right, xs[-1])
        elif start is not None:
            bands.append((start, y - 1, right - left + 1))
            start = None
    return bands


def test_pairing_is_white_black_with_centred_blocks(
    legacy: hardware.HardwareProfile,
) -> None:
    data = pairing_image.render_pairing_image(legacy, FAKE_CODE)
    assert _nibbles(data) == {panel_format.WHITE, panel_format.BLACK}
    assert _pixel(data, legacy, 0, 0) == panel_format.WHITE
    assert _pixel(data, legacy, 1199, 1599) == panel_format.WHITE
    bands = _ink_rows(data, legacy)
    # Glyph, label, rule, code, then the two body lines.
    assert len(bands) >= 6
    widths = [width for _, _, width in bands]
    code_band = max(bands, key=lambda band: band[2])
    # The code is the widest and tallest element and fits the safe box.
    assert code_band[2] == max(widths)
    assert code_band[2] <= style.SAFE_BOX[2] - style.SAFE_BOX[0]
    assert all(
        code_band[1] - code_band[0] > b[1] - b[0] for b in bands if b is not code_band
    )
    # The whole block is vertically centred like the other hold screens.
    top, bottom = bands[0][0], bands[-1][1]
    assert abs(top - (legacy.height - 1 - bottom)) <= 40


def test_longest_code_fits_the_safe_box(legacy: hardware.HardwareProfile) -> None:
    data = pairing_image.render_pairing_image(legacy, "WWWWWWWW")
    for y in range(legacy.height):
        for x in (*range(0, style.SAFE_BOX[0]), *range(style.SAFE_BOX[2], legacy.width)):
            assert _pixel(data, legacy, x, y) == panel_format.WHITE


def test_retired_has_no_code_and_no_code_argument(
    legacy: hardware.HardwareProfile,
) -> None:
    assert list(inspect.signature(pairing_image.render_retired_image).parameters) == [
        "profile"
    ]
    retired = pairing_image.render_retired_image(legacy)
    assert _nibbles(retired) == {panel_format.WHITE, panel_format.BLACK}
    # Dithered field: black and white both appear in every sampled block.
    block = {
        _pixel(retired, legacy, x, y) for x in range(100, 108) for y in range(100, 108)
    }
    assert block == {panel_format.WHITE, panel_format.BLACK}
    # The retired screen does not depend on any code.
    assert retired == pairing_image.render_retired_image(legacy)


def test_simulated_profile_gets_the_landscape_composition(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(hardware.SIM_ENV_VAR, "1")
    profile = hardware.get_profile(hardware.SIM_LANDSCAPE_KEY)
    expected = (profile.width // 2) * profile.height
    pairing = pairing_image.render_pairing_image(profile, FAKE_CODE)
    retired = pairing_image.render_retired_image(profile)
    assert len(pairing) == expected
    assert len(retired) == expected
    assert _nibbles(pairing) <= LEGAL_NIBBLES
    assert _nibbles(retired) <= LEGAL_NIBBLES


def _landscape_profiles(monkeypatch: pytest.MonkeyPatch) -> list[hardware.HardwareProfile]:
    monkeypatch.setenv(hardware.SIM_ENV_VAR, "1")
    return [
        hardware.get_profile(hardware.SIM_LANDSCAPE_KEY),
        hardware.get_profile(hardware.EVALUATION_KEY),
    ]


def test_landscape_pairing_is_the_calm_status_composition(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for profile in _landscape_profiles(monkeypatch):
        shown = "ABCD-2345"
        data = pairing_image.render_pairing_image(profile, FAKE_CODE)
        size = (profile.width, profile.height)
        assert len(data) == (profile.width // 2) * profile.height
        assert _nibbles(data) <= LEGAL_NIBBLES
        assert data == pairing_image._pack(status.build_pairing(size, shown))
        assert data == pairing_image.render_pairing_image(profile, "abcd-2345")
        assert data != pairing_image.render_pairing_image(profile, "WXYZ6789")
        # The dithered dark field, like the retired screen.
        block = {_pixel(data, profile, x, y) for x in range(100, 108) for y in range(100, 108)}
        assert block == {panel_format.WHITE, panel_format.BLACK}


def _white_bands(canvas: Image.Image) -> list[tuple[int, int, int, int]]:
    """Bands of consecutive rows holding ink on a flat canvas:
    (first row, last row, left, right)."""
    pixels = canvas.load()
    width, height = canvas.size
    bands: list[tuple[int, int, int, int]] = []
    start = None
    left, right = width, -1
    for y in range(height):
        xs = [x for x in range(width) if pixels[x, y] == panel_format.IDX_WHITE]
        if xs:
            if start is None:
                start, left, right = y, width, -1
            left, right = min(left, xs[0]), max(right, xs[-1])
        elif start is not None:
            bands.append((start, y - 1, left, right))
            start = None
    if start is not None:
        bands.append((start, height - 1, left, right))
    return bands


@pytest.mark.parametrize("code", ["ABCD-2345", "WWWW-WWWW"])
def test_landscape_pairing_code_is_the_widest_giant_line_and_stays_in_the_margins(
    code: str,
) -> None:
    size = (800, 480)
    canvas = status.build_pairing(size, code, flat=True)
    bands = _white_bands(canvas)
    margin = round(size[1] * 0.069)
    # Glyph, label, lead word, code, then the two instruction lines.
    assert len(bands) >= 6
    widths = [right - left + 1 for _, _, left, right in bands]
    lead_band, code_band = bands[2], bands[3]
    assert code_band[3] - code_band[2] + 1 > widths[2]
    assert code_band[1] - code_band[0] >= lead_band[1] - lead_band[0] - 2
    assert min(left for _, _, left, _ in bands) >= margin - 1
    assert max(right for _, _, _, right in bands) <= size[0] - margin
    assert all(code_band[1] - code_band[0] >= b[1] - b[0] for b in bands)


def test_pairing_is_not_a_status_kind() -> None:
    with pytest.raises(ValueError):
        status.build_status("pairing", (800, 480))
