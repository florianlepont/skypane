# SPDX-License-Identifier: AGPL-3.0-only
"""Register a frame's identity (MAC, secret hash, token) in fleet.db.

The device server reads identity from fleet.db only, so a test that needs
an enrolable frame writes its row here before starting the server. The
database is created and marked migrated on first use, with a synthetic
owner; every frame uses the live state path, as the legacy import did, so
several MACs can share one state directory.
"""
from __future__ import annotations

import os

from server import fleet_db, hardware

OWNER_EMAIL = "owner@example.com"


def _ensure_migrated(conn) -> int:
    row = fleet_db.get_user_by_email(conn, OWNER_EMAIL)
    owner_id = int(row["id"]) if row is not None else fleet_db.add_user(
        conn, OWNER_EMAIL, "admin")
    if fleet_db.meta_get(conn, fleet_db.META_MIGRATED) is None:
        fleet_db.meta_set(conn, fleet_db.META_BOOTSTRAP_OWNER, str(owner_id))
        fleet_db.meta_set(conn, fleet_db.META_MIGRATED, fleet_db.utc_now_iso())
    return owner_id


def register_device(
    state_dir: str, mac: str, secret_sha256: str, replace: bool = False,
    token: str | None = None,
) -> str:
    """Add `mac` with its secret hash (and optionally a token); with
    `replace` an existing row only gets the new hash. Returns the MAC."""
    os.makedirs(state_dir, exist_ok=True)
    conn = fleet_db.connect(state_dir)
    try:
        with fleet_db.transaction(conn):
            owner_id = _ensure_migrated(conn)
            if fleet_db.get_device_by_mac(conn, mac) is not None:
                if not replace:
                    raise ValueError("%s is already registered" % mac)
                fleet_db.set_device_secret(conn, mac, secret_sha256)
                if token is not None:
                    fleet_db.set_device_token(conn, mac, token)
            else:
                fleet_db.add_device(
                    conn, mac, secret_sha256, hardware.LEGACY_KEY, owner_id,
                    token=token, allow_shared_live=True)
    finally:
        conn.close()
    return mac
