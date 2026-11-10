"""Seed helper for the photo store tests: one frame and the people around it.

No pytest import. Builds plain fleet.db rows.
"""
from typing import NamedTuple

from server import fleet_db, hardware

OWNER_EMAIL = "owner@example.test"
CO_EMAIL = "comanager@example.test"
OTHER_EMAIL = "other@example.test"
ADMIN_EMAIL = "admin@example.test"
DISABLED_EMAIL = "disabled@example.test"

_SECRET = "c" * 64
PHOTO_DEVICE_MAC = "aa:bb:cc:dd:ee:10"


class PhotoFleet(NamedTuple):
    owner_id: int
    co_manager_id: int
    other_id: int
    admin_id: int
    disabled_id: int
    device_id: str


def seed_photo_fleet(state_dir: str) -> PhotoFleet:
    """Owner, co-manager, other user, pure admin and a disabled co-manager,
    plus one device owned by the owner."""
    conn = fleet_db.connect(state_dir)
    try:
        fleet_db.meta_set(conn, fleet_db.META_MIGRATED, "1")
        owner = fleet_db.add_user(conn, OWNER_EMAIL, "user")
        co = fleet_db.add_user(conn, CO_EMAIL, "user")
        other = fleet_db.add_user(conn, OTHER_EMAIL, "user")
        admin = fleet_db.add_user(conn, ADMIN_EMAIL, "admin")
        disabled = fleet_db.add_user(conn, DISABLED_EMAIL, "user")
        device = fleet_db.add_device(
            conn, PHOTO_DEVICE_MAC, _SECRET, hardware.LEGACY_KEY, owner,
            state_path="auto")
        fleet_db.add_co_manager(conn, device, co, owner)
        fleet_db.add_co_manager(conn, device, disabled, owner)
        # Direct update: set_user_disabled would also remove the co-manager
        # rows of frames the user owns, and this one owns none, but the
        # membership must stay so only the disabled flag refuses access.
        conn.execute("UPDATE users SET disabled = 1 WHERE id = ?", (disabled,))
    finally:
        conn.close()
    return PhotoFleet(owner, co, other, admin, disabled, device)
