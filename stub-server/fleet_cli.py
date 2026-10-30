#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Florian Lepont
# SPDX-License-Identifier: Apache-2.0
"""Operator CLI for the fleet database (users, locations, devices).

Stdlib only. Manages fleet.db and keeps the legacy device files that the
byos server still reads (devices.json, byos_state.json) in step: every
device add, remove and token revoke is mirrored there through byos_server's
own registry functions, so the on-disk format has one definition. Creates
fleet.db mode 0600 on first use but never marks it migrated; that is the
job of `python3 -m server.fleet_migrate`.

--state-dir is required, with no default: an operator names the directory
explicitly, so a stale path can never be guessed into editing the wrong
fleet.

Usage:
    fleet_cli.py --state-dir DIR users add --email E --role admin|user [--disabled]
    fleet_cli.py --state-dir DIR users list
    fleet_cli.py --state-dir DIR users disable|enable --email E
    fleet_cli.py --state-dir DIR users unlink-identity --email E
    fleet_cli.py --state-dir DIR locations add --name N --latitude F \\
        --longitude F --timezone TZ
    fleet_cli.py --state-dir DIR locations list
    fleet_cli.py --state-dir DIR devices add --mac M --secret-sha256 H \\
        --owner-email E [--hardware-type K] [--location-id N] [--name S] \\
        [--state-path .|auto]
    fleet_cli.py --state-dir DIR devices list
    fleet_cli.py --state-dir DIR devices assign --mac M --owner-email E
    fleet_cli.py --state-dir DIR devices set-location --mac M --location-id N
    fleet_cli.py --state-dir DIR devices remove --mac M
    fleet_cli.py --state-dir DIR devices revoke-token --mac M
    fleet_cli.py --state-dir DIR hardware list

Exit codes: 0 success, 2 usage/validation error, 1 not found.
"""
import argparse
import os
import shutil
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import byos_server  # noqa: E402 - the sys.path bootstrap above must run first
from server import (  # noqa: E402
    device_dirs, fleet_db, fleet_sessions, hardware,
)

RESTART_CAUTION = (
    "warning: byos keeps its registry and issued tokens in memory - stop "
    "skypane-byos before this edit and start it again after, or the "
    "running process will write its own copy back"
)


def _fail(message, code=2):
    print("error: %s" % message, file=sys.stderr)
    return code


def _open(args):
    return fleet_db.connect(args.state_dir)


def _mac_or_none(raw):
    return byos_server.normalize_mac(raw)


def _owner_id(conn, email):
    """The id of the user with this email, or None when unknown."""
    row = fleet_db.get_user_by_email(conn, email)
    return None if row is None else int(row["id"])


# ---- users -----------------------------------------------------------


def cmd_users_add(args):
    conn = _open(args)
    with fleet_db.transaction(conn):
        fleet_db.add_user(conn, args.email, args.role, disabled=args.disabled)
    print("added %s (%s)" % (fleet_db.normalize_email(args.email), args.role))
    return 0


def cmd_users_list(args):
    users = fleet_db.list_users(_open(args))
    if not users:
        print("(no users)")
    for row in users:
        print("%s %s %s" % (
            row["email"], row["role"], "disabled" if row["disabled"] else "enabled"))
    return 0


def _set_disabled(args, disabled):
    conn = _open(args)
    with fleet_db.transaction(conn):
        found = fleet_db.set_user_disabled(conn, args.email, disabled)
        if found and disabled:
            row = fleet_db.get_user_by_email(conn, args.email)
            fleet_sessions.delete_sessions_for_user(conn, int(row["id"]))
    if not found:
        return _fail("no such user: %s" % args.email, 1)
    print("%s %s" % ("disabled" if disabled else "enabled", args.email))
    return 0


def cmd_users_disable(args):
    return _set_disabled(args, True)


def cmd_users_enable(args):
    return _set_disabled(args, False)


def cmd_users_unlink_identity(args):
    """Forget a user's Auth0 link so the next verified login can link afresh."""
    conn = _open(args)
    if fleet_db.get_user_by_email(conn, args.email) is None:
        return _fail("no such user: %s" % args.email, 1)
    if fleet_sessions.unlink_identity(conn, args.email):
        print("unlinked %s" % args.email)
    else:
        print("%s is already unlinked" % args.email)
    return 0


# ---- locations -------------------------------------------------------


def cmd_locations_add(args):
    conn = _open(args)
    with fleet_db.transaction(conn):
        location_id = fleet_db.add_location(
            conn, args.name, args.latitude, args.longitude, args.timezone)
    print("added location %d (%s)" % (location_id, args.name))
    return 0


def cmd_locations_list(args):
    rows = fleet_db.list_locations(_open(args))
    if not rows:
        print("(no locations)")
    for row in rows:
        print("%d %s %s %s %s" % (
            row["id"], row["name"], row["latitude"], row["longitude"], row["timezone"]))
    return 0


# ---- devices ---------------------------------------------------------


def cmd_devices_add(args):
    mac = _mac_or_none(args.mac)
    if mac is None:
        return _fail("not a MAC address: %r" % (args.mac,))
    conn = _open(args)
    owner_id = _owner_id(conn, args.owner_email)
    if owner_id is None:
        return _fail("no such owner: %s" % args.owner_email, 1)
    live_macs = {str(row["mac"]) for row in conn.execute(
        "SELECT mac FROM devices WHERE state_path = ?",
        (device_dirs.LIVE_STATE_PATH,))}
    if args.state_path != "auto" and live_macs:
        return _fail(
            "a live frame already exists; add this device with "
            "--state-path auto so it gets its own directory")
    # The legacy write runs inside the transaction: if it raises, the
    # insert is rolled back and the two stores stay equal.
    new_id = None
    created_dir = None
    try:
        with fleet_db.transaction(conn):
            new_id = fleet_db.add_device(
                conn, mac, args.secret_sha256, args.hardware_type, owner_id,
                location_id=args.location_id, name=args.name,
                state_path=args.state_path)
            if args.state_path == "auto":
                profile = hardware.get_profile(args.hardware_type, os.environ)
                # Recorded before devices/ first appears, so a corrupt
                # fleet.db can never leave per-device state without it.
                device_dirs.record_live_macs(args.state_dir, live_macs)
                created_dir = device_dirs.provision_device_dir(
                    args.state_dir, new_id, profile.width, profile.height)
            byos_server.register_device(args.state_dir, mac, args.secret_sha256)
    except BaseException:
        # The row is rolled back; do not leave its directory behind.
        if created_dir is not None:
            shutil.rmtree(created_dir, ignore_errors=True)
        raise
    print("registered %s" % mac)
    if args.state_path == "auto":
        print("device id %s" % new_id)
    return 0


def cmd_devices_list(args):
    rows = fleet_db.list_devices(_open(args))
    if not rows:
        print("(no devices)")
    for row in rows:
        # Hash prefix only: enough to spot a copy/paste mistake, nothing
        # closer to a working secret.
        print("%s %s %s %s %s…" % (
            row["mac"], row["owner_email"], row["hardware_type"],
            row["location_name"] or "-", row["secret_prefix"]))
    return 0


def cmd_devices_assign(args):
    mac = _mac_or_none(args.mac)
    if mac is None:
        return _fail("not a MAC address: %r" % (args.mac,))
    conn = _open(args)
    owner_id = _owner_id(conn, args.owner_email)
    if owner_id is None:
        return _fail("no such owner: %s" % args.owner_email, 1)
    with fleet_db.transaction(conn):
        found = fleet_db.assign_owner(conn, mac, owner_id)
    if not found:
        return _fail("%s is not registered" % mac, 1)
    print("assigned %s to %s" % (mac, args.owner_email))
    return 0


def cmd_devices_set_location(args):
    mac = _mac_or_none(args.mac)
    if mac is None:
        return _fail("not a MAC address: %r" % (args.mac,))
    conn = _open(args)
    known = {int(r["id"]) for r in fleet_db.list_locations(conn)}
    if args.location_id not in known:
        return _fail("no such location: %d" % args.location_id, 1)
    with fleet_db.transaction(conn):
        found = fleet_db.set_device_location(conn, mac, args.location_id)
    if not found:
        return _fail("%s is not registered" % mac, 1)
    print("moved %s to location %d" % (mac, args.location_id))
    return 0


def _mirror_remove(state_dir, mac):
    registry = byos_server.load_registry(state_dir)
    if mac in registry["devices"]:
        del registry["devices"][mac]
        byos_server.save_registry(state_dir, registry)
    state = byos_server.load_state(state_dir)
    if mac in state.get("tokens", {}):
        del state["tokens"][mac]
        byos_server.save_state(state_dir, state)


def cmd_devices_remove(args):
    mac = _mac_or_none(args.mac)
    if mac is None:
        return _fail("not a MAC address: %r" % (args.mac,))
    conn = _open(args)
    with fleet_db.transaction(conn):
        found = fleet_db.remove_device(conn, mac)
        if found:
            _mirror_remove(args.state_dir, mac)
    if not found:
        return _fail("%s is not registered" % mac, 1)
    print("removed %s" % mac)
    print(RESTART_CAUTION)
    return 0


def _mirror_revoke(state_dir, mac):
    """Drop the legacy token; True when one was present."""
    state = byos_server.load_state(state_dir)
    if mac not in state.get("tokens", {}):
        return False
    del state["tokens"][mac]
    byos_server.save_state(state_dir, state)
    return True


def cmd_devices_revoke_token(args):
    mac = _mac_or_none(args.mac)
    if mac is None:
        return _fail("not a MAC address: %r" % (args.mac,))
    conn = _open(args)
    row = fleet_db.get_device_by_mac(conn, mac)
    had_db_token = row is not None and row["token"] is not None
    with fleet_db.transaction(conn):
        if had_db_token:
            fleet_db.set_device_token(conn, mac, None)
        had_legacy_token = _mirror_revoke(args.state_dir, mac)
    if not (had_db_token or had_legacy_token):
        return _fail("%s has no issued token" % mac, 1)
    print("revoked %s's token" % mac)
    print(RESTART_CAUTION)
    return 0


# ---- hardware --------------------------------------------------------


def cmd_hardware_list(args):
    for key in hardware.available_types():
        profile = hardware.REGISTRY[key]
        print("%s %dx%d%s" % (
            key, profile.width, profile.height,
            " (simulated)" if profile.simulated else ""))
    return 0


# ---- parser ----------------------------------------------------------


def _add_users(sub):
    users = sub.add_parser("users", help="manage users and roles")
    verbs = users.add_subparsers(dest="verb", required=True)
    add = verbs.add_parser("add", help="create a user")
    add.add_argument("--email", required=True)
    add.add_argument("--role", required=True, help="admin or user")
    add.add_argument("--disabled", action="store_true")
    add.set_defaults(func=cmd_users_add)
    verbs.add_parser("list", help="list users").set_defaults(func=cmd_users_list)
    for name, func in (("disable", cmd_users_disable), ("enable", cmd_users_enable)):
        p = verbs.add_parser(name, help="%s a user" % name)
        p.add_argument("--email", required=True)
        p.set_defaults(func=func)
    unlink = verbs.add_parser(
        "unlink-identity", help="clear a user's Auth0 link and sessions")
    unlink.add_argument("--email", required=True)
    unlink.set_defaults(func=cmd_users_unlink_identity)


def _add_locations(sub):
    locations = sub.add_parser("locations", help="manage locations")
    verbs = locations.add_subparsers(dest="verb", required=True)
    add = verbs.add_parser("add", help="create a location")
    add.add_argument("--name", required=True)
    add.add_argument("--latitude", required=True, type=float)
    add.add_argument("--longitude", required=True, type=float)
    add.add_argument("--timezone", required=True, help="IANA name, e.g. Europe/Paris")
    add.set_defaults(func=cmd_locations_add)
    verbs.add_parser("list", help="list locations").set_defaults(func=cmd_locations_list)


def _add_devices(sub):
    devices = sub.add_parser("devices", help="manage devices")
    verbs = devices.add_subparsers(dest="verb", required=True)
    add = verbs.add_parser("add", help="register a device with one owner")
    add.add_argument("--mac", required=True)
    add.add_argument("--secret-sha256", required=True,
                     help="sha256(secret_hex) - 64 lowercase hex characters")
    add.add_argument("--owner-email", required=True)
    add.add_argument("--hardware-type", default=hardware.LEGACY_KEY)
    add.add_argument("--location-id", type=int, default=None)
    add.add_argument("--name", default=None)
    add.add_argument("--state-path", choices=[".", "auto"], default=".",
                     help="'auto' gives the device its own directory under devices/")
    add.set_defaults(func=cmd_devices_add)
    verbs.add_parser("list", help="list devices (hash prefix only)").set_defaults(
        func=cmd_devices_list)
    assign = verbs.add_parser("assign", help="change a device's owner")
    assign.add_argument("--mac", required=True)
    assign.add_argument("--owner-email", required=True)
    assign.set_defaults(func=cmd_devices_assign)
    setloc = verbs.add_parser("set-location", help="move a device to a location")
    setloc.add_argument("--mac", required=True)
    setloc.add_argument("--location-id", required=True, type=int)
    setloc.set_defaults(func=cmd_devices_set_location)
    remove = verbs.add_parser("remove", help="unregister a device")
    remove.add_argument("--mac", required=True)
    remove.set_defaults(func=cmd_devices_remove)
    revoke = verbs.add_parser("revoke-token", help="delete a device's bearer token")
    revoke.add_argument("--mac", required=True)
    revoke.set_defaults(func=cmd_devices_revoke_token)


def build_parser():
    ap = argparse.ArgumentParser(description="Manage the SkyPane fleet database.")
    ap.add_argument("--state-dir", required=True,
                    help="the state directory the services run with "
                         "(no default - never guess which fleet to edit)")
    sub = ap.add_subparsers(dest="group", required=True)
    _add_users(sub)
    _add_locations(sub)
    _add_devices(sub)
    hw = sub.add_parser("hardware", help="list hardware types")
    hw_verbs = hw.add_subparsers(dest="verb", required=True)
    hw_verbs.add_parser("list", help="list available types").set_defaults(
        func=cmd_hardware_list)
    return ap


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except (ValueError, sqlite3.IntegrityError) as exc:
        return _fail(exc)
    except (sqlite3.Error, OSError) as exc:
        return _fail(type(exc).__name__, 1)


if __name__ == "__main__":
    sys.exit(main())
