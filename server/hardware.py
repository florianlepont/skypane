#!/usr/bin/env python3
"""Committed registry of hardware types a frame can be.

A hardware type bundles what the server must know to serve a device:
resolution, palette, image format, battery profile and firmware target.
Adding a type is a code change, never a database row. The legacy EE02
entry is built from the constants the rest of the server already uses, so
the two cannot drift apart.

Simulated types exist for development and tests. They are visible only
when SKYPANE_SIM_HARDWARE equals the string "1"; the gate is read at call
time so tests can toggle it, and no production unit or env template sets
it.
"""
from __future__ import annotations

import os
import types
from collections.abc import Mapping
from dataclasses import dataclass

from server import device_policy, panel_format

LEGACY_KEY = "xiao-ee02-13in3-spectra6"
SIM_CLONE_KEY = "sim-ee02-clone"
SIM_LANDSCAPE_KEY = "sim-landscape-800x480"
SIM_ENV_VAR = "SKYPANE_SIM_HARDWARE"

# Four bits per pixel, two pixels per byte, Spectra 6 colour indices.
IMAGE_FORMAT_SPECTRA6_NIBBLE = "spectra6-nibble-packed"


class UnknownHardwareType(ValueError):
    """The hardware key is not available in this environment."""


@dataclass(frozen=True)
class BatteryProfile:
    curve: tuple[tuple[int, int], ...]  # (millivolts, percent)
    low_mv: int
    low_clear_mv: int
    critical_mv: int
    critical_recover_mv: int


@dataclass(frozen=True)
class FirmwareTarget:
    idf_target: str
    project_name: str
    max_image_bytes: int  # packed display image, not the firmware
    # Bounds the OTA application image (the ota slot in
    # firmware/partitions.csv); a new hardware type sets it from its own
    # partition table.
    max_app_bytes: int = 0x250000


@dataclass(frozen=True)
class HardwareProfile:
    key: str
    label: str
    width: int
    height: int
    palette: tuple[int, ...]  # flat RGB triples
    image_format: str
    battery: BatteryProfile
    firmware: FirmwareTarget
    simulated: bool


def _packed_image_bytes(width: int, height: int) -> int:
    """Two pixels per byte."""
    return (width // 2) * height


_LEGACY_BATTERY = BatteryProfile(
    curve=device_policy.BATTERY_DISCHARGE_CURVE,
    low_mv=device_policy.BATTERY_LOW_THRESHOLD_MV,
    low_clear_mv=device_policy.BATTERY_LOW_CLEAR_MV,
    critical_mv=device_policy.BATTERY_CRITICAL_MV,
    critical_recover_mv=device_policy.BATTERY_CRITICAL_RECOVER_MV,
)

_PALETTE = tuple(panel_format.PALETTE_RGB)

_LEGACY = HardwareProfile(
    key=LEGACY_KEY,
    label="XIAO ePaper EE02 13.3in Spectra 6",
    width=panel_format.WIDTH,
    height=panel_format.HEIGHT,
    palette=_PALETTE,
    image_format=IMAGE_FORMAT_SPECTRA6_NIBBLE,
    battery=_LEGACY_BATTERY,
    firmware=FirmwareTarget(
        idf_target="esp32s3",
        project_name="skypane",
        max_image_bytes=panel_format.IMAGE_BYTES,
    ),
    simulated=False,
)

_SIM_CLONE = HardwareProfile(
    key=SIM_CLONE_KEY,
    label="Simulated EE02 clone",
    width=_LEGACY.width,
    height=_LEGACY.height,
    palette=_LEGACY.palette,
    image_format=_LEGACY.image_format,
    battery=_LEGACY.battery,
    firmware=_LEGACY.firmware,
    simulated=True,
)

_SIM_LANDSCAPE = HardwareProfile(
    key=SIM_LANDSCAPE_KEY,
    label="Simulated 800x480 landscape",
    width=800,
    height=480,
    palette=_PALETTE,
    image_format=IMAGE_FORMAT_SPECTRA6_NIBBLE,
    battery=BatteryProfile(
        curve=_LEGACY_BATTERY.curve,
        low_mv=_LEGACY_BATTERY.low_mv,
        low_clear_mv=_LEGACY_BATTERY.low_clear_mv,
        critical_mv=_LEGACY_BATTERY.critical_mv,
        critical_recover_mv=_LEGACY_BATTERY.critical_recover_mv,
    ),
    firmware=FirmwareTarget(
        idf_target=_LEGACY.firmware.idf_target,
        project_name=_LEGACY.firmware.project_name,
        max_image_bytes=_packed_image_bytes(800, 480),
    ),
    simulated=True,
)

REGISTRY: Mapping[str, HardwareProfile] = types.MappingProxyType(
    {p.key: p for p in (_LEGACY, _SIM_CLONE, _SIM_LANDSCAPE)}
)


def _sim_enabled(environ: Mapping[str, str] | None) -> bool:
    env = os.environ if environ is None else environ
    return env.get(SIM_ENV_VAR) == "1"


def available_types(environ: Mapping[str, str] | None = None) -> tuple[str, ...]:
    """Keys usable in this environment; simulated ones only when gated on."""
    sim = _sim_enabled(environ)
    return tuple(k for k, p in REGISTRY.items() if sim or not p.simulated)


def get_profile(key: str, environ: Mapping[str, str] | None = None) -> HardwareProfile:
    """Exact-key lookup; raises UnknownHardwareType when unavailable."""
    if key not in available_types(environ):
        raise UnknownHardwareType(f"unknown hardware type: {key!r}")
    return REGISTRY[key]


def is_known(key: str) -> bool:
    """Registry membership regardless of the simulation gate."""
    return key in REGISTRY
