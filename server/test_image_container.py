#!/usr/bin/env python3
"""Tests for server/image_container.py against the shared golden fixtures.

The same manifest.txt and .bin files are read by the C reader tests, so the
Python decoder and the firmware agree on every accepted and rejected body.
"""
import hashlib
import importlib.util
import pathlib
import struct
import zlib
from types import ModuleType

import pytest

import server.image_container as ic

FIXTURE_DIR = (
    pathlib.Path(__file__).resolve().parent.parent
    / "firmware" / "tests" / "fixtures" / "image_container"
)


def _load_generator() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "generate_fixtures", FIXTURE_DIR / "generate_fixtures.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


GEN = _load_generator()


ManifestCase = tuple[str, str, int, int, tuple[int, int]]


def _parse_manifest() -> tuple[
    tuple[int, int], list[ManifestCase], dict[str, str]
]:
    panel = (0, 0)
    cases: list[ManifestCase] = []
    consts: dict[str, str] = {}
    for raw in (FIXTURE_DIR / "manifest.txt").read_text().splitlines():
        tokens = raw.split("#", 1)[0].split()
        if not tokens:
            continue
        if tokens[0] == "panel":
            panel = (int(tokens[1]), int(tokens[2]))
        elif tokens[0] in ("check_crc32", "full_size_crc32",
                           "full_size_container_sha256"):
            consts[tokens[0]] = tokens[1]
        else:
            override = panel
            if len(tokens) > 4 and tokens[4] == "panel_override":
                override = (int(tokens[5]), int(tokens[6]))
            cases.append((tokens[0], tokens[1], int(tokens[2]),
                          int(tokens[3]), override))
    return panel, cases, consts


PANEL, CASES, CONSTS = _parse_manifest()


def test_manifest_lists_every_fixture_file() -> None:
    on_disk = sorted(p.name for p in FIXTURE_DIR.glob("*.bin"))
    assert sorted(c[0] for c in CASES) == on_disk
    assert len(CASES) >= 22
    assert PANEL == (8, 4)


def test_committed_fixtures_match_generator() -> None:
    built = GEN.build_all()
    assert sorted(built) == sorted(c[0] for c in CASES)
    for name, data in built.items():
        assert (FIXTURE_DIR / name).read_bytes() == data, name
    assert (FIXTURE_DIR / "manifest.txt").read_text() == GEN.manifest_text()


@pytest.mark.parametrize(
    "name,expected,palette,plen,panel", CASES, ids=[c[0] for c in CASES])
def test_decoder_agrees_with_manifest(
    name: str, expected: str, palette: int, plen: int,
    panel: tuple[int, int],
) -> None:
    body = (FIXTURE_DIR / name).read_bytes()
    if expected in ("ok", "legacy"):
        view = ic.decode_container(body, panel[0], panel[1])
        assert view.legacy == (expected == "legacy")
        assert view.palette_id == palette
        assert len(view.payload) == plen
        assert (view.width, view.height) == panel
        return
    with pytest.raises(ic.ImageContainerError) as info:
        ic.decode_container(body, panel[0], panel[1])
    assert info.value.reason == expected


def test_encoder_reproduces_committed_valid_fixture() -> None:
    pixels = GEN.small_payload(16)
    encoded = ic.encode_container(pixels, 8, 4)
    assert encoded == (FIXTURE_DIR / "valid_v1_8x4.bin").read_bytes()
    assert ic.decode_container(encoded, 8, 4).payload == pixels


def test_full_size_container_matches_manifest() -> None:
    pixels = GEN.full_size_pixels()
    assert len(pixels) == 960000
    body = ic.encode_container(pixels, 1200, 1600)
    assert len(body) == 960024
    assert f"{zlib.crc32(pixels):08x}" == CONSTS["full_size_crc32"]
    assert hashlib.sha256(body).hexdigest() == CONSTS[
        "full_size_container_sha256"]
    view = ic.decode_container(body, 1200, 1600)
    assert view.payload == pixels and not view.legacy


def test_crc_check_value() -> None:
    assert zlib.crc32(b"123456789") == 0xCBF43926
    assert CONSTS["check_crc32"] == "cbf43926"


def test_header_field_offsets() -> None:
    pixels = bytes(range(16))
    body = ic.encode_container(pixels, 8, 4)
    assert ic.HEADER_LEN == 24
    assert body[0:4] == b"SPIM"
    assert body[4] == 1
    assert body[5] == 24
    assert struct.unpack_from("<H", body, 6)[0] == 0
    assert struct.unpack_from("<H", body, 8)[0] == 8
    assert struct.unpack_from("<H", body, 10)[0] == 4
    assert body[12] == 1
    assert body[13] == 1
    assert struct.unpack_from("<H", body, 14)[0] == 0
    assert struct.unpack_from("<I", body, 16)[0] == 16
    assert struct.unpack_from("<I", body, 20)[0] == zlib.crc32(pixels)
    assert body[24:] == pixels


@pytest.mark.parametrize(
    "raw,expected",
    [("1", 1), ("001", 1), ("2", 1), ("999", 1),
     ("0", None), ("", None), ("abc", None), ("-1", None), ("+1", None),
     (" 1", None), ("1 ", None), ("1,2", None), ("1000", None),
     ("9" * 100, None), ("١", None), (None, None), (b"1", None)],
)
def test_negotiate_version_matrix(raw: object, expected: int | None) -> None:
    assert ic.negotiate_version(raw) == expected


def test_every_truncated_prefix_is_rejected() -> None:
    body = (FIXTURE_DIR / "valid_v1_8x4.bin").read_bytes()
    assert len(body) == 40
    for cut in range(len(body)):
        prefix = body[:cut]
        with pytest.raises(ic.ImageContainerError):
            ic.decode_container(prefix, 8, 4)


def test_odd_pixel_count_rounds_payload_up() -> None:
    assert ic.payload_size(7, 3) == 11
    legacy = (FIXTURE_DIR / "legacy_7x3.bin").read_bytes()
    assert len(legacy) == 11
    assert ic.decode_container(legacy, 7, 3).legacy


def test_zero_panel_size_is_an_argument_error() -> None:
    with pytest.raises(ic.ImageContainerError) as info:
        ic.decode_container(b"SPIM", 0, 4)
    assert info.value.reason == "argument"


def test_encoder_rejects_bad_inputs() -> None:
    with pytest.raises(ValueError):
        ic.encode_container(b"\x00" * 15, 8, 4)
    with pytest.raises(ValueError):
        ic.encode_container(b"\x00" * 16, 8, 4, version=2)
