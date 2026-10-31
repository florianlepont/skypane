"""A fleet.db plus real device directories for tests that run the companion's
real handlers with no stubs.

No pytest import. `provision_fleet` writes plain data: one admin, two users,
frames with provisioned directories (a seeded config and panel, a gallery
image), the live-frame row, and a pending and a retired row.
"""
import json
import os
import time

from server import device_config, device_dirs, fleet_db, hardware, history_db

ADMIN_EMAIL = "admin@example.test"
USER_A_EMAIL = "user-a@example.test"
USER_B_EMAIL = "user-b@example.test"
FRAMELESS_EMAIL = "frameless@example.test"

NAME_A1 = "Orly window"
NAME_A2 = "Kitchen shelf"
NAME_B1 = "Neighbour frame"

GALLERY_FILENAME = "sample.png"

# Admin-only settings seeded to values that differ from every default, so an
# unwanted overwrite is visible.
SEEDED_ADMIN_ONLY = {
    "wake_interval_s": 900,
    "led_enabled": False,
    "tracked_runway": "06-24",
}

_SECRET = "d" * 64
_PANEL_PIXELS = 2


class ProvisionedFleet:
    """Ids of the rows `provision_fleet` created."""

    def __init__(self, **ids):
        self.__dict__.update(ids)


def _png_bytes():
    import io

    from PIL import Image
    buffer = io.BytesIO()
    Image.new("RGB", (4, 4), (255, 255, 255)).save(buffer, format="PNG")
    return buffer.getvalue()


def _provision(root, device_id):
    directory = device_dirs.provision_device_dir(
        root, device_id, _PANEL_PIXELS, _PANEL_PIXELS)
    gallery = os.path.join(directory, "gallery")
    os.makedirs(gallery, exist_ok=True)
    with open(os.path.join(gallery, GALLERY_FILENAME), "wb") as fh:
        fh.write(_png_bytes())
    device_config.save_device_config(directory, **SEEDED_ADMIN_ONLY)
    return directory


def _add_frame(conn, mac, owner_id, name, state_path="auto"):
    return fleet_db.add_device(
        conn, mac, _SECRET, hardware.LEGACY_KEY, owner_id, name=name,
        state_path=state_path)


def provision_fleet(state_dir, live_owner="admin"):
    """Seed `state_dir` and return a ProvisionedFleet.

    Rows: an admin, user A (two frames), user B (one frame), a user with no
    frame, the live frame (state path ".", owned by `live_owner`: "admin" or
    "a"), one pending frame and one retired frame. Every non-live frame has a
    directory with a config, a panel and a gallery image.
    """
    os.makedirs(state_dir, exist_ok=True)
    conn = fleet_db.connect(state_dir)
    try:
        fleet_db.meta_set(conn, fleet_db.META_MIGRATED, "1")
        admin_id = fleet_db.add_user(conn, ADMIN_EMAIL, "admin")
        a_id = fleet_db.add_user(conn, USER_A_EMAIL, "user")
        b_id = fleet_db.add_user(conn, USER_B_EMAIL, "user")
        frameless_id = fleet_db.add_user(conn, FRAMELESS_EMAIL, "user")
        a1 = _add_frame(conn, "aa:bb:cc:00:00:01", a_id, NAME_A1)
        a2 = _add_frame(conn, "aa:bb:cc:00:00:02", a_id, NAME_A2)
        b1 = _add_frame(conn, "aa:bb:cc:00:00:03", b_id, NAME_B1)
        live_owner_id = a_id if live_owner == "a" else admin_id
        live = _add_frame(
            conn, "aa:bb:cc:00:00:04", live_owner_id, "Live frame",
            state_path=device_dirs.LIVE_STATE_PATH)
        retired_source = _add_frame(conn, "aa:bb:cc:00:00:05", b_id, "Retired frame")
        pending = fleet_db.register_pending(
            conn, "aa:bb:cc:00:00:06", _SECRET, hardware.LEGACY_KEY, admin_id)
        retired = fleet_db.park_retired(conn, retired_source, 1_700_000_000)
    finally:
        conn.close()
    for device_id in (a1, a2, b1):
        _provision(state_dir, device_id)
    device_config.save_device_config(state_dir, **SEEDED_ADMIN_ONLY)
    return ProvisionedFleet(
        admin_id=admin_id, a_id=a_id, b_id=b_id, frameless_id=frameless_id,
        a1=a1, a2=a2, b1=b1, live=live, pending=pending, retired=retired)


def device_dir(state_dir, device_id):
    return device_dirs.resolve_state_dir(
        state_dir, device_dirs.state_path_for(device_id))


def mark_checked_in(state_dir, device_id, source_fault=False):
    """Record a check-in for a provisioned frame so its Health page renders
    the full rows (a frame never seen shows only an empty state), and
    optionally raise the platform source-fault flag in its history."""
    directory = device_dir(state_dir, device_id)
    with open(os.path.join(directory, "battery_state.json"), "w") as fh:
        json.dump({"received_at": time.time()}, fh)
    if source_fault:
        with history_db.open_db(directory) as conn:
            history_db.set_meta(conn, history_db.META_SOURCE_FAULT, "True")
