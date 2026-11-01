"""Deterministic pairing and retired e-ink screens."""
from __future__ import annotations

import hashlib
import inspect
import subprocess
import sys
from pathlib import Path

import pytest

from server import hardware, pairing_image, panel_format
from server.plane.render import style

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
RETIRED_GOLDEN_SHA256 = "315a0852353acdd9849c6cfd1e2fbffe6bbfc792a9df53907e3868a0c5290c05"
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


def test_simulated_profile_scales(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(hardware.SIM_ENV_VAR, "1")
    profile = hardware.get_profile(hardware.SIM_LANDSCAPE_KEY)
    expected = (profile.width // 2) * profile.height
    pairing = pairing_image.render_pairing_image(profile, FAKE_CODE)
    retired = pairing_image.render_retired_image(profile)
    assert len(pairing) == expected
    assert len(retired) == expected
    assert _nibbles(pairing) <= LEGAL_NIBBLES
    assert _nibbles(retired) <= LEGAL_NIBBLES
    assert _pixel(pairing, profile, 0, 0) in LEGAL_NIBBLES
    # Nothing is clipped: the scaled composition keeps ink away from every edge.
    ink = [
        (x, y)
        for y in range(profile.height)
        for x in range(profile.width)
        if _pixel(pairing, profile, x, y) == panel_format.BLACK
    ]
    assert ink
    assert min(x for x, _ in ink) > 0 and max(x for x, _ in ink) < profile.width - 1
    assert min(y for _, y in ink) > 0 and max(y for _, y in ink) < profile.height - 1
