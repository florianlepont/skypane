"""Deterministic pairing and retired e-ink screens."""
from __future__ import annotations

import hashlib
import inspect
import subprocess
import sys
from pathlib import Path

import pytest

from server import hardware, pairing_image, panel_format

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
RETIRED_GOLDEN_SHA256 = "245ccd04e6fd38e8756fe7894617ce3cbbadfdbe0b4548dc588e0575675b37f9"


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
    retired = hashlib.sha256(pairing_image.render_retired_image(legacy)).hexdigest()
    assert out[1] == retired
    assert retired == RETIRED_GOLDEN_SHA256


def test_pairing_regions(legacy: hardware.HardwareProfile) -> None:
    data = pairing_image.render_pairing_image(legacy, FAKE_CODE)
    for y in (0, 100, 219):
        for x in (0, 1100, 1199):
            assert _pixel(data, legacy, x, y) == panel_format.RED
    assert _pixel(data, legacy, 1199, 230) == panel_format.WHITE
    assert _pixel(data, legacy, 5, 5) == panel_format.RED
    # The 6 px frame of the code box and the code glyphs are black.
    assert _pixel(data, legacy, 82, 700) == panel_format.BLACK
    region = [
        _pixel(data, legacy, x, y)
        for y in range(700, 900, 2)
        for x in range(100, 1100, 2)
    ]
    assert panel_format.BLACK in region


def test_retired_has_no_code_area_and_no_code_argument(
    legacy: hardware.HardwareProfile,
) -> None:
    assert list(inspect.signature(pairing_image.render_retired_image).parameters) == [
        "profile"
    ]
    pairing = pairing_image.render_pairing_image(legacy, FAKE_CODE)
    retired = pairing_image.render_retired_image(legacy)
    # The pairing code box frame is absent on the retired screen.
    assert _pixel(pairing, legacy, 82, 700) == panel_format.BLACK
    assert _pixel(retired, legacy, 82, 700) == panel_format.WHITE
    assert _pixel(retired, legacy, 600, 5) == panel_format.BLACK
    # No code glyph rows at the centre of the box on the retired screen.
    box = [
        _pixel(retired, legacy, x, y)
        for y in range(600, 800)
        for x in range(100, 1100)
    ]
    assert panel_format.BLACK not in box


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
