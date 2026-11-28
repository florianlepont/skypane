#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
"""scripts/multi_site_setup.py -- creates a scratch state root with simulated
devices, each on a chosen airport and runway.

The root is an isolated copy of the fleet layout: its own fleet.db, one
scratch owner, one simulated device per --device NAME=ICAO:DESIGNATOR, and
a held live row so the root's own frame never joins a zone. Nothing here
reads or writes a production path or an env file. The simulation flag is
passed to the fleet database call as an argument and never set in the
shell, the environment or a file.

The root carries a marker file written before anything else. A directory
that is the server's default state directory, or that looks like a real
state root (live_frame_macs.json, panel.bin, fleet.db) without the marker,
or that is not empty without the marker, is refused.

Example:
  multi_site_setup.py --root /scratch/fleet \
      --device orly-b=LFPO:06/24 --device cdg=LFPG:08L/26R
"""
import argparse
import dataclasses
import hashlib
import os
import secrets
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from server import (  # noqa: E402
    detection,
    device_config,
    device_dirs,
    fleet_db,
    hardware,
    state_store,
)

MARKER_FILENAME = ".multisite-scratch"
OWNER_EMAIL = "scratch-owner@example.invalid"
DEFAULT_HARDWARE = hardware.SIM_CLONE_KEY
_SIM_ENVIRON = {hardware.SIM_ENV_VAR: "1"}
_REAL_ROOT_MARKERS = (device_dirs.LIVE_MACS_FILENAME, device_dirs.PANEL_FILENAME,
                      fleet_db.FLEET_DB_FILENAME)
# 00:00:5e:00:53:xx is the address block reserved for documentation (RFC 7042),
# so a generated MAC can never belong to a real frame.
_MAC_PREFIX = "00:00:5e:00:53:"
_LIVE_MAC = _MAC_PREFIX + "00"


class ScratchRootError(Exception):
    """The directory is not a safe place for a scratch fleet."""


@dataclasses.dataclass(frozen=True)
class DeviceSpec:
    name: str
    icao: str
    designator: str


@dataclasses.dataclass(frozen=True)
class ScratchDevice:
    name: str
    id: str
    state_dir: str
    icao: str
    designator: str


def parse_device(text):
    """`NAME=ICAO:DESIGNATOR` as a DeviceSpec; ValueError for any other shape."""
    name, sep, rest = text.partition("=")
    icao, sep2, designator = rest.partition(":")
    if not (sep and sep2 and name.strip() and icao and designator):
        raise ValueError("expected NAME=ICAO:DESIGNATOR, got %r" % text)
    return DeviceSpec(name.strip(), icao, designator)


def check_root(root):
    """Refuse a root that is, or looks like, a real state directory.

    A root with the scratch marker is accepted (a second setup call adds
    devices) except when it is the server's default state directory.
    """
    real = os.path.realpath(root)
    if real == os.path.realpath(state_store.DEFAULT_STATE_DIR):
        raise ScratchRootError("refusing the server's default state directory")
    if not os.path.isdir(real):
        if os.path.lexists(real):
            raise ScratchRootError("not a directory: %s" % root)
        return
    if os.path.exists(os.path.join(real, MARKER_FILENAME)):
        return
    for name in _REAL_ROOT_MARKERS:
        if os.path.exists(os.path.join(real, name)):
            raise ScratchRootError(
                "%s holds %s and no scratch marker: looks like a real state root"
                % (root, name))
    if os.listdir(real):
        raise ScratchRootError("%s is not empty and has no scratch marker" % root)


def _simulated_profile(hardware_type):
    """The profile of a simulated type that renders on this server."""
    try:
        profile = hardware.get_profile(hardware_type, _SIM_ENVIRON)
    except hardware.UnknownHardwareType as exc:
        raise ValueError("unknown hardware type: %r" % hardware_type) from exc
    if not profile.simulated:
        raise ValueError("%s is not a simulated hardware type" % hardware_type)
    return profile


def _new_mac(conn):
    while True:
        mac = _MAC_PREFIX + "%02x" % (1 + secrets.randbelow(254))
        if fleet_db.get_device_by_mac(conn, mac) is None:
            return mac


def _new_secret_hash():
    return hashlib.sha256(secrets.token_bytes(16)).hexdigest()


def _owner_id(conn, email):
    row = fleet_db.get_user_by_email(conn, email)
    if row is not None:
        return int(row["id"])
    return fleet_db.add_user(conn, email, "admin")


def _ensure_live_row(conn, owner_id):
    """The scratch root's own live frame row, so the root mirrors a fleet."""
    if conn.execute(
        "SELECT 1 FROM devices WHERE state_path = ?", (device_dirs.LIVE_STATE_PATH,)
    ).fetchone() is None:
        fleet_db.add_device(
            conn, _LIVE_MAC, _new_secret_hash(), hardware.LEGACY_KEY, owner_id,
            name="scratch-live", state_path=device_dirs.LIVE_STATE_PATH)


def create_scratch_fleet(root, specs, owner_email=OWNER_EMAIL, hardware_type=DEFAULT_HARDWARE):
    """Create the scratch fleet under `root` and return its ScratchDevices.

    Everything is validated before the first write. The live row's display
    is switched off in the root's own device config, so it joins no zone
    and costs no provider request.
    """
    specs = list(specs)
    if not specs:
        raise ValueError("at least one device is required")
    if not owner_email or "@" not in owner_email:
        raise ValueError("an owner e-mail is required")
    profile = _simulated_profile(hardware_type)
    for spec in specs:
        detection.validate_runway_selection(spec.icao, spec.designator)
    check_root(root)
    os.makedirs(root, exist_ok=True)
    marker = os.path.join(root, MARKER_FILENAME)
    if not os.path.exists(marker):
        with open(marker, "w", encoding="utf-8") as handle:
            handle.write("scratch fleet root; never a production state directory\n")
    conn = fleet_db.connect(root)
    made = []
    try:
        fleet_db.meta_set(conn, fleet_db.META_MIGRATED, "1")
        owner_id = _owner_id(conn, owner_email)
        _ensure_live_row(conn, owner_id)
        for spec in specs:
            device_id = fleet_db.add_device(
                conn, _new_mac(conn), _new_secret_hash(), hardware_type, owner_id,
                name=spec.name, state_path="auto", environ=_SIM_ENVIRON)
            state_dir = device_dirs.provision_device_dir(
                root, device_id, profile.width, profile.height)
            detection.apply_runway_selection(state_dir, spec.icao, spec.designator)
            made.append(ScratchDevice(spec.name, device_id, state_dir, spec.icao, spec.designator))
    finally:
        conn.close()
    device_config.save_device_config(root, display_enabled=False)
    return made


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--root", required=True, help="scratch state root to create")
    parser.add_argument("--device", action="append", default=[], metavar="NAME=ICAO:DESIGNATOR")
    parser.add_argument("--owner", default=OWNER_EMAIL, help="scratch owner e-mail")
    parser.add_argument("--hardware", default=DEFAULT_HARDWARE, help="a simulated hardware key")
    args = parser.parse_args(argv)
    try:
        specs = [parse_device(text) for text in args.device]
        made = create_scratch_fleet(
            args.root, specs, owner_email=args.owner, hardware_type=args.hardware)
    except (ScratchRootError, ValueError) as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 2
    for device in made:
        print("%s\t%s\t%s:%s\t%s" % (
            device.name, device.id, device.icao, device.designator, device.state_dir))
    return 0


if __name__ == "__main__":
    sys.exit(main())
