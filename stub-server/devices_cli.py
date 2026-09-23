#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Florian Lepont
# SPDX-License-Identifier: Apache-2.0
"""Operator CLI for byos_server.py's per-device enrolment registry.

Stdlib only. Adds, removes and lists devices.json entries (MAC -> the
SHA-256 hex digest of that device's own enrolment secret - never the
secret itself), and revokes a single device's issued bearer token from
byos_state.json. Shares byos_server.py's own registry/state functions
(register_device, load_registry, save_registry, load_state, save_state,
normalize_mac) by importing that module directly, so the on-disk format
never drifts between the CLI and the server that reads it.

--state-dir is required, with no default: an operator must name the
directory explicitly, so a wrong or stale --state-dir can never be
guessed into silently editing the wrong registry.

Usage:
    python3 devices_cli.py --state-dir DIR add --mac aa:bb:cc:dd:ee:ff \\
        --secret-sha256 <64 lowercase hex> [--replace]
    python3 devices_cli.py --state-dir DIR remove --mac aa:bb:cc:dd:ee:ff
    python3 devices_cli.py --state-dir DIR list
    python3 devices_cli.py --state-dir DIR revoke-token --mac aa:bb:cc:dd:ee:ff

Exit codes: 0 success, 2 usage/validation error, 1 not found.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import byos_server  # noqa: E402 - the sys.path bootstrap above must run first


def cmd_add(args):
    try:
        mac = byos_server.register_device(
            args.state_dir, args.mac, args.secret_sha256, replace=args.replace)
    except ValueError as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 2
    print("registered %s" % mac)
    return 0


def cmd_remove(args):
    mac = byos_server.normalize_mac(args.mac)
    if mac is None:
        print("error: not a MAC address: %r" % (args.mac,), file=sys.stderr)
        return 2
    registry = byos_server.load_registry(args.state_dir)
    if mac not in registry["devices"]:
        print("error: %s is not registered" % mac, file=sys.stderr)
        return 1
    del registry["devices"][mac]
    byos_server.save_registry(args.state_dir, registry)
    print("removed %s" % mac)
    return 0


def cmd_list(args):
    registry = byos_server.load_registry(args.state_dir)
    if not registry["devices"]:
        print("(no devices registered)")
        return 0
    for mac, entry in sorted(registry["devices"].items()):
        secret_hash = entry.get("secret_sha256", "") if isinstance(entry, dict) else ""
        # Never print the full hash - a hash prefix is enough to spot a
        # copy/paste mistake without giving a shoulder-surfer anything
        # closer to a working secret.
        print("%s %s…" % (mac, secret_hash[:12]))
    return 0


def cmd_revoke_token(args):
    mac = byos_server.normalize_mac(args.mac)
    if mac is None:
        print("error: not a MAC address: %r" % (args.mac,), file=sys.stderr)
        return 2
    state = byos_server.load_state(args.state_dir)
    if mac not in state["tokens"]:
        print("error: %s has no issued token" % mac, file=sys.stderr)
        return 1
    del state["tokens"][mac]
    byos_server.save_state(args.state_dir, state)
    print("revoked %s's token" % mac)
    print("warning: byos keeps issued tokens in memory - stop "
          "skypane-byos before this edit, and start it again after, or "
          "the running process will overwrite this file with its own "
          "in-memory copy (still holding the revoked token) on its next "
          "write")
    return 0


def build_parser():
    ap = argparse.ArgumentParser(
        description="Manage byos_server.py's per-device enrolment registry.")
    ap.add_argument("--state-dir", required=True,
                     help="the same --state-dir byos_server.py runs with "
                          "(no default - never guess which registry to edit)")
    sub = ap.add_subparsers(dest="command", required=True)

    add = sub.add_parser("add", help="register a device (or overwrite with --replace)")
    add.add_argument("--mac", required=True)
    add.add_argument("--secret-sha256", required=True,
                      help="sha256(secret_hex) - 64 lowercase hex characters")
    add.add_argument("--replace", action="store_true",
                      help="overwrite an existing MAC's registered hash")
    add.set_defaults(func=cmd_add)

    remove = sub.add_parser("remove", help="unregister a device")
    remove.add_argument("--mac", required=True)
    remove.set_defaults(func=cmd_remove)

    listp = sub.add_parser("list", help="list registered devices (hash prefix only)")
    listp.set_defaults(func=cmd_list)

    revoke = sub.add_parser(
        "revoke-token", help="delete a device's issued bearer token, forcing re-enrolment")
    revoke.add_argument("--mac", required=True)
    revoke.set_defaults(func=cmd_revoke_token)

    return ap


def main():
    args = build_parser().parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
