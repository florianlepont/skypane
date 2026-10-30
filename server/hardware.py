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
from datetime import date

from server import device_policy, panel_format

LEGACY_KEY = "xiao-ee02-13in3-spectra6"
SIM_CLONE_KEY = "sim-ee02-clone"
SIM_LANDSCAPE_KEY = "sim-landscape-800x480"
SIM_ENV_VAR = "SKYPANE_SIM_HARDWARE"

# Repo-relative path of the public key release images are checked against.
COMMITTED_SIGNING_PUBKEY = "firmware/signing/skypane-signing-pubkey.pem"

# Four bits per pixel, two pixels per byte, Spectra 6 colour indices.
IMAGE_FORMAT_SPECTRA6_NIBBLE = "spectra6-nibble-packed"


class UnknownHardwareType(ValueError):
    """The hardware key is not available in this environment."""


# Layout families a profile can declare. Portrait is the 1200x1600 frame.
LAYOUT_PORTRAIT = "portrait"
LAYOUT_LANDSCAPE = "landscape"
LAYOUT_FAMILIES = (LAYOUT_PORTRAIT, LAYOUT_LANDSCAPE)
PORTRAIT_SIZE = (1200, 1600)

# Names of the battery values a profile documents.
BATTERY_VALUE_NAMES = (
    "curve", "low_mv", "low_clear_mv", "critical_mv", "critical_recover_mv",
)
PROVENANCE_STATUSES = ("provisional", "final")

# Every Spectra 6 ink, as palette indices (black, white, yellow, red, blue,
# green); matches the IDX_* values in panel_format.
ALL_SPECTRA6_INKS: frozenset[int] = frozenset({
    panel_format.IDX_BLACK, panel_format.IDX_WHITE, panel_format.IDX_YELLOW,
    panel_format.IDX_RED, panel_format.IDX_BLUE, panel_format.IDX_GREEN,
})


@dataclass(frozen=True)
class BatteryProvenance:
    """Where one battery value comes from and how far it can be trusted."""
    value: str  # one of BATTERY_VALUE_NAMES
    source: str  # document path and section, or why it was copied
    status: str  # "provisional" or "final"
    date: str  # ISO date the value was set or last validated


@dataclass(frozen=True)
class BatteryProfile:
    curve: tuple[tuple[int, int], ...]  # (millivolts, percent)
    low_mv: int
    low_clear_mv: int
    critical_mv: int
    critical_recover_mv: int
    provenance: tuple[BatteryProvenance, ...] = ()

    def provenance_for(self, name: str) -> BatteryProvenance:
        """Provenance entry for a battery value; KeyError when absent."""
        for entry in self.provenance:
            if entry.value == name:
                return entry
        raise KeyError(name)


@dataclass(frozen=True)
class BatterySlot:
    """Placeholder for hardware whose battery numbers are not measured yet.

    Every value is None on purpose: nothing here may be used as a number.
    """
    label: str
    status: str
    note: str
    values: tuple[tuple[str, None], ...]


@dataclass(frozen=True)
class FirmwareTarget:
    idf_target: str
    project_name: str
    max_image_bytes: int  # packed display image, not the firmware
    # Bounds the OTA application image (the ota slot in
    # firmware/partitions.csv); a new hardware type sets it from its own
    # partition table.
    max_app_bytes: int = 0x250000
    # Signing policy applied to this type's release images at publish time:
    # a signature sector is required unless require_signature is False, and
    # when signing_pubkey (a repo-relative PEM path) is set the embedded
    # modulus must equal that key's.
    require_signature: bool = True
    signing_pubkey: str | None = COMMITTED_SIGNING_PUBKEY


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
    inks: frozenset[int] = ALL_SPECTRA6_INKS
    layout_family: str = LAYOUT_PORTRAIT


def _packed_image_bytes(width: int, height: int) -> int:
    """Two pixels per byte."""
    return (width // 2) * height


_BATTERY_RUN = "hardware/BATTERY-RUN.md"
_LEGACY_PROVENANCE = (
    BatteryProvenance(
        "curve",
        _BATTERY_RUN + ', "Calibration & Follow-Up Findings", finding 1: '
        "table built from the first discharge run (2026-09-02 to 2026-09-14); "
        'hardware/BATTERY-MODEL.md "Percentage calibration at the top of the '
        'curve" records the 4000-4112 mV segment as not calibrated',
        "provisional", "2026-09-23"),
    BatteryProvenance(
        "low_mv",
        "server/device_policy.py rationale (margin above the 3400 mV logging "
        "cutoff); validated by " + _BATTERY_RUN + " finding 2",
        "provisional", "2026-09-23"),
    BatteryProvenance(
        "low_clear_mv",
        "server/device_policy.py: 100 mV re-arm buffer against flapping; "
        "no measurement behind it",
        "provisional", "2026-10-05"),
    BatteryProvenance(
        "critical_mv",
        _BATTERY_RUN + ', "Follow-up: BATTERY EMPTY park"',
        "provisional", "2026-09-23"),
    BatteryProvenance(
        "critical_recover_mv",
        _BATTERY_RUN + ', "Follow-up: BATTERY EMPTY park": 400 mV re-arm '
        "buffer once charging resumes",
        "provisional", "2026-09-23"),
)

_LEGACY_BATTERY = BatteryProfile(
    curve=device_policy.BATTERY_DISCHARGE_CURVE,
    low_mv=device_policy.BATTERY_LOW_THRESHOLD_MV,
    low_clear_mv=device_policy.BATTERY_LOW_CLEAR_MV,
    critical_mv=device_policy.BATTERY_CRITICAL_MV,
    critical_recover_mv=device_policy.BATTERY_CRITICAL_RECOVER_MV,
    provenance=_LEGACY_PROVENANCE,
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
        provenance=tuple(
            BatteryProvenance(
                p.value,
                "copied from the legacy profile for simulation; "
                "not a measurement",
                "provisional",
                p.date,
            )
            for p in _LEGACY_PROVENANCE
        ),
    ),
    firmware=FirmwareTarget(
        idf_target=_LEGACY.firmware.idf_target,
        project_name=_LEGACY.firmware.project_name,
        max_image_bytes=_packed_image_bytes(800, 480),
    ),
    simulated=True,
    layout_family=LAYOUT_LANDSCAPE,
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


# Hardware planned but not measured. Deliberately outside REGISTRY: it
# cannot be selected and carries no numbers.
PLANNED_BATTERY_SLOTS: Mapping[str, BatterySlot] = types.MappingProxyType({
    "seeed-ee04-7in3-spectra6": BatterySlot(
        label="Seeed EE04 7.3in, 800x480",
        status="unmeasured",
        note="to be measured when the hardware is validated",
        values=tuple((name, None) for name in BATTERY_VALUE_NAMES),
    ),
})


def _is_iso_date(text: str) -> bool:
    try:
        date.fromisoformat(text)
    except ValueError:
        return False
    return True


def _battery_problems(profile: HardwareProfile) -> list[str]:
    problems: list[str] = []
    entries = profile.battery.provenance
    if sorted(e.value for e in entries) != sorted(BATTERY_VALUE_NAMES):
        problems.append(f"{profile.key}: provenance must name each battery value once")
    for e in entries:
        if e.status not in PROVENANCE_STATUSES:
            problems.append(f"{profile.key}.{e.value}: bad status {e.status!r}")
        if not e.source.strip():
            problems.append(f"{profile.key}.{e.value}: empty source")
        if not _is_iso_date(e.date):
            problems.append(f"{profile.key}.{e.value}: bad date {e.date!r}")
        if e.status == "final" and "measure" not in e.source.lower():
            problems.append(f"{profile.key}.{e.value}: final needs a measurement source")
    return problems


def registry_problems() -> list[str]:
    """Human-readable problems found in REGISTRY; empty when it is valid."""
    problems: list[str] = []
    for profile in REGISTRY.values():
        if not profile.simulated:
            problems.extend(_battery_problems(profile))
        if profile.inks != ALL_SPECTRA6_INKS:
            problems.append(f"{profile.key}: profiles must carry all six inks")
        if profile.layout_family not in LAYOUT_FAMILIES:
            problems.append(f"{profile.key}: unknown layout family {profile.layout_family!r}")
        elif (profile.layout_family == LAYOUT_PORTRAIT
              and (profile.width, profile.height) != PORTRAIT_SIZE):
            problems.append(f"{profile.key}: portrait requires 1200x1600")
        elif (profile.layout_family == LAYOUT_LANDSCAPE
              and (profile.width % 2 or profile.height % 2)):
            problems.append(f"{profile.key}: landscape needs even dimensions")
    return problems
