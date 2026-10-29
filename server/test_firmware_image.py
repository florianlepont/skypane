#!/usr/bin/env python3
"""Tests for server/firmware_image.py: parser and target validation on
synthetic images from the shared test-support builder."""
import dataclasses

import pytest

import server.firmware_image as fi
import server.firmware_registry as fr
import server.hardware as hardware
from skypane_fw_image import CORRUPTIONS, build_image, default_modulus

TARGET = hardware.get_profile(hardware.LEGACY_KEY).firmware
VERSION = "fw-v1.2.3"


def test_round_trip_signed_image() -> None:
    data = build_image(VERSION)
    image = fi.parse_app_image(data)
    assert image.chip_id == 0x0009
    assert image.version == VERSION
    assert image.project_name == "skypane"
    assert image.signature_offset is not None
    assert image.signature_offset % 4096 == 0
    assert image.modulus == default_modulus()
    assert image.size == len(data)
    assert fi.validate_for_target(data, TARGET, manifest_version=VERSION) == image


def test_round_trip_unsigned_image() -> None:
    data = build_image(VERSION, signed=False)
    image = fi.parse_app_image(data)
    assert image.signature_offset is None
    assert image.modulus is None
    assert image.image_end == len(data)


@pytest.mark.parametrize("corrupt", CORRUPTIONS)
def test_each_corruption_is_rejected_with_a_field_name(corrupt: str) -> None:
    data = build_image(VERSION, corrupt=corrupt)
    with pytest.raises(ValueError, match=r"^(image|descriptor|signature): "):
        fi.parse_app_image(data)


def test_short_file_is_rejected() -> None:
    with pytest.raises(ValueError, match=r"^image: "):
        fi.parse_app_image(b"\xe9" * 100)


def test_zero_segments_is_rejected() -> None:
    data = bytearray(build_image(VERSION))
    data[1] = 0
    with pytest.raises(ValueError, match=r"^image: "):
        fi.parse_app_image(bytes(data))


def test_segment_walk_past_end_is_rejected() -> None:
    data = bytearray(build_image(VERSION))
    data[1] = 200
    with pytest.raises(ValueError, match=r"^image: "):
        fi.parse_app_image(bytes(data))


def test_non_ascii_descriptor_string_is_rejected() -> None:
    data = bytearray(build_image(VERSION, signed=False))
    data[48] = 0xFF
    with pytest.raises(ValueError, match=r"^descriptor: "):
        fi.parse_app_image(bytes(data))


def test_wrong_chip_is_rejected() -> None:
    data = build_image(VERSION, chip_id=0x0005)
    with pytest.raises(ValueError, match=r"^chip: "):
        fi.validate_for_target(data, TARGET)


def test_wrong_project_name_is_rejected() -> None:
    data = build_image(VERSION, project_name="otherproj")
    with pytest.raises(ValueError, match=r"^project_name: "):
        fi.validate_for_target(data, TARGET)


def test_unknown_idf_target_fails_closed() -> None:
    target = dataclasses.replace(TARGET, idf_target="esp99")
    with pytest.raises(ValueError, match=r"^chip: unknown idf_target"):
        fi.validate_for_target(build_image(VERSION), target)


def test_version_must_match_manifest() -> None:
    data = build_image(VERSION)
    with pytest.raises(ValueError, match=r"^version: "):
        fi.validate_for_target(data, TARGET, manifest_version="fw-v1.2.4")


def test_bench_version_needs_bench_flag() -> None:
    data = build_image("fw-v1.2.3-bench1")
    with pytest.raises(ValueError, match=r"^version: "):
        fi.validate_for_target(data, TARGET)
    fi.validate_for_target(data, TARGET, bench=True)


def test_non_release_version_is_rejected() -> None:
    with pytest.raises(ValueError, match=r"^version: "):
        fi.validate_for_target(build_image("1.2.3"), TARGET)


def test_unsigned_image_policy() -> None:
    data = build_image(VERSION, signed=False)
    with pytest.raises(ValueError, match=r"^signature: "):
        fi.validate_for_target(data, TARGET)
    fi.validate_for_target(data, TARGET, require_signature=False)
    fi.validate_for_target(build_image(VERSION), TARGET, require_signature=False)


def test_expected_modulus_comparison() -> None:
    data = build_image(VERSION)
    fi.validate_for_target(data, TARGET, expected_modulus=default_modulus())
    with pytest.raises(ValueError, match=r"^signature: key mismatch"):
        fi.validate_for_target(data, TARGET, expected_modulus=b"\x80" * 384)


def test_size_bound_defaults_to_the_ota_slot_not_the_display_bound() -> None:
    big = build_image(VERSION, size=1_118_208)
    assert len(big) >= 1_118_208
    assert TARGET.max_image_bytes < len(big)
    fi.validate_for_target(big, TARGET)
    with pytest.raises(ValueError, match=r"^size: "):
        fi.validate_for_target(big, TARGET, max_bytes=1_000_000)
    too_big = build_image(VERSION, size=TARGET.max_app_bytes + 1)
    with pytest.raises(ValueError, match=r"^size: "):
        fi.validate_for_target(too_big, TARGET)


SAMPLES = [
    "fw-v1.0.0", "fw-v0.0.0", "fw-v1.10.20", "fw-v9999.9999.9999",
    "fw-v10000.0.0", "fw-v01.0.0", "fw-v1.0", "v1.0.0", "fw-v1.0.0-bench1",
    "fw-v1.0.0-", "fw-v1.0.0-Bench", "fw-v1.0.0\n", "", "fw-v1.0.0-a.b-c",
]


@pytest.mark.parametrize("sample", SAMPLES)
def test_local_version_patterns_agree_with_the_registry(sample: str) -> None:
    assert bool(fi._RELEASE_TAG_RE.match(sample)) == bool(fr.RELEASE_TAG_RE.match(sample))
    assert bool(fi._BENCH_VERSION_RE.match(sample)) == bool(fr.VERSION_RE.match(sample))
