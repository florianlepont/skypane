#!/usr/bin/env python3
"""Tests for server/hardware.py: the legacy profile is pinned to the shared
constants, simulated types are env-gated, and production config never
enables them."""
import dataclasses
import glob
import os

import pytest

from skypane_test_support import REPO_ROOT

import server.device_policy as device_policy
import server.hardware as hardware
import server.panel_format as panel_format

SIM_ON = {hardware.SIM_ENV_VAR: "1"}


def test_available_types_without_gate_is_legacy_only() -> None:
    assert hardware.available_types({}) == (hardware.LEGACY_KEY,)


def test_available_types_with_gate_adds_both_sim_types() -> None:
    keys = hardware.available_types(SIM_ON)
    assert hardware.LEGACY_KEY in keys
    assert hardware.SIM_CLONE_KEY in keys
    assert hardware.SIM_LANDSCAPE_KEY in keys


@pytest.mark.parametrize("value", ["0", "true", "", "yes", "11"])
def test_other_gate_values_leave_sim_types_out(value: str) -> None:
    keys = hardware.available_types({hardware.SIM_ENV_VAR: value})
    assert all(not hardware.REGISTRY[k].simulated for k in keys)


def test_gate_is_read_at_call_time(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(hardware.SIM_ENV_VAR, raising=False)
    assert hardware.SIM_CLONE_KEY not in hardware.available_types()
    monkeypatch.setenv(hardware.SIM_ENV_VAR, "1")
    assert hardware.SIM_CLONE_KEY in hardware.available_types()


def test_legacy_profile_matches_shared_constants() -> None:
    p = hardware.get_profile(hardware.LEGACY_KEY, {})
    assert (p.width, p.height) == (panel_format.WIDTH, panel_format.HEIGHT)
    assert p.firmware.max_image_bytes == panel_format.IMAGE_BYTES
    assert p.palette == tuple(panel_format.PALETTE_RGB)
    assert p.battery.curve == device_policy.BATTERY_DISCHARGE_CURVE
    assert p.battery.low_mv == device_policy.BATTERY_LOW_THRESHOLD_MV
    assert p.battery.low_clear_mv == device_policy.BATTERY_LOW_CLEAR_MV
    assert p.battery.critical_mv == device_policy.BATTERY_CRITICAL_MV
    assert p.battery.critical_recover_mv == device_policy.BATTERY_CRITICAL_RECOVER_MV
    assert p.firmware.idf_target == "esp32s3"
    assert p.firmware.project_name == "skypane"
    assert not p.simulated


def test_sim_types_unavailable_without_gate() -> None:
    for key in (hardware.SIM_CLONE_KEY, hardware.SIM_LANDSCAPE_KEY):
        with pytest.raises(hardware.UnknownHardwareType):
            hardware.get_profile(key, {})


def test_unknown_key_raises_value_error() -> None:
    with pytest.raises(ValueError):
        hardware.get_profile("nonsense", SIM_ON)
    assert issubclass(hardware.UnknownHardwareType, ValueError)


def test_clone_shares_legacy_geometry() -> None:
    legacy = hardware.get_profile(hardware.LEGACY_KEY, {})
    clone = hardware.get_profile(hardware.SIM_CLONE_KEY, SIM_ON)
    assert clone.simulated
    assert (clone.width, clone.height) == (legacy.width, legacy.height)
    assert clone.palette == legacy.palette
    assert clone.image_format == legacy.image_format


def test_landscape_profile() -> None:
    p = hardware.get_profile(hardware.SIM_LANDSCAPE_KEY, SIM_ON)
    assert (p.width, p.height) == (800, 480)
    assert p.firmware.max_image_bytes == 192000
    assert p.simulated


def test_is_known_ignores_gate() -> None:
    assert hardware.is_known(hardware.SIM_CLONE_KEY)
    assert hardware.is_known(hardware.LEGACY_KEY)
    assert not hardware.is_known("nonsense")


def test_profiles_and_registry_are_immutable() -> None:
    p = hardware.REGISTRY[hardware.LEGACY_KEY]
    with pytest.raises(dataclasses.FrozenInstanceError):
        p.width = 1  # type: ignore[misc]
    with pytest.raises(TypeError):
        hardware.REGISTRY["x"] = p  # type: ignore[index]


def _env_example_assignments() -> dict[str, str]:
    out: dict[str, str] = {}
    path = os.path.join(REPO_ROOT, "deploy", "skypane.env.example")
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            out[k.strip()] = v.strip()
    return out


def _unit_environment_keys() -> set[str]:
    keys: set[str] = set()
    for path in glob.glob(os.path.join(REPO_ROOT, "deploy", "*.service")):
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("Environment="):
                    for token in line[len("Environment="):].split():
                        keys.add(token.strip('"').partition("=")[0])
                elif line.startswith("EnvironmentFile="):
                    keys.add("FILE:" + line.partition("=")[2])
    return keys


def test_production_config_never_enables_sim_types() -> None:
    env = _env_example_assignments()
    assert hardware.SIM_ENV_VAR not in env
    assert hardware.SIM_ENV_VAR not in _unit_environment_keys()
    for environ in ({}, env):
        keys = hardware.available_types(environ)
        assert all(not hardware.REGISTRY[k].simulated for k in keys)


def test_firmware_bound_is_separate_from_display_bound() -> None:
    from skypane_fw_image import build_image

    import server.firmware_image as firmware_image

    for key in (hardware.LEGACY_KEY, hardware.SIM_CLONE_KEY, hardware.SIM_LANDSCAPE_KEY):
        assert hardware.REGISTRY[key].firmware.max_app_bytes == 0x250000
    assert hardware.REGISTRY[hardware.LEGACY_KEY].firmware.max_image_bytes == 960000
    assert hardware.REGISTRY[hardware.SIM_LANDSCAPE_KEY].firmware.max_image_bytes == 192000
    image = build_image("fw-v1.0.0", size=1_118_208)
    for key in (hardware.LEGACY_KEY, hardware.SIM_LANDSCAPE_KEY):
        firmware_image.validate_for_target(image, hardware.REGISTRY[key].firmware)


def test_every_type_defaults_to_a_signed_image_under_the_committed_key() -> None:
    for profile in hardware.REGISTRY.values():
        assert profile.firmware.require_signature is True
        assert profile.firmware.signing_pubkey == hardware.COMMITTED_SIGNING_PUBKEY
    committed = os.path.join(REPO_ROOT, hardware.COMMITTED_SIGNING_PUBKEY)
    assert os.path.isfile(committed)


def test_firmware_target_signing_fields_are_defaulted() -> None:
    target = hardware.FirmwareTarget(
        idf_target="esp32s3", project_name="x", max_image_bytes=1)
    assert target.require_signature is True
    assert target.signing_pubkey == hardware.COMMITTED_SIGNING_PUBKEY
