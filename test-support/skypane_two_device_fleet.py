"""One-call fixture: the live frame plus two simulated devices.

`seed_two_device_fleet(state_dir)` seeds the live frame's state directory,
imports it into fleet.db the way the production migration does, then adds
two `sim-ee02-clone` devices (and optionally a landscape one), each with
its own directory under `devices/`, its own panel image (a distinct fill
byte), its own secret and its own token.

Simulated hardware types exist only while SKYPANE_SIM_HARDWARE=1. The
helper sets and restores that variable itself for its own calls; a
FrameServer or AppServer subprocess that must serve these devices has to
be started by the calling fixture with the variable set in its env (see
`sim_hardware_env`).
"""
from __future__ import annotations

import contextlib
import hashlib
import os
import sys
from collections.abc import Iterator
from types import SimpleNamespace

import skypane_live_state as live_state

from server import device_dirs, fleet_db, fleet_migrate, hardware

_STUB_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "stub-server")
if _STUB_DIR not in sys.path:
    sys.path.insert(0, _STUB_DIR)
import byos_server  # noqa: E402

OWNER_EMAIL = "owner@example.com"
FILL_A = 0x22
FILL_B = 0x33
FILL_LANDSCAPE = 0x44

_POLL_HEADERS = {
    "X-Battery-Mv": "3900",
    "X-Fw-Version": "1.0.0",
    "X-Boot-Reason": "timer",
    "X-Rssi": "-60",
}


@contextlib.contextmanager
def sim_hardware_env() -> Iterator[None]:
    """Set SKYPANE_SIM_HARDWARE=1 for the block and restore it after."""
    old = os.environ.get(hardware.SIM_ENV_VAR)
    os.environ[hardware.SIM_ENV_VAR] = "1"
    try:
        yield
    finally:
        if old is None:
            os.environ.pop(hardware.SIM_ENV_VAR, None)
        else:
            os.environ[hardware.SIM_ENV_VAR] = old


def device_headers(device: SimpleNamespace) -> dict[str, str]:
    """The headers a frame sends when it polls for its image."""
    headers = {"Authorization": "Bearer %s" % device.token}
    headers.update(_POLL_HEADERS)
    return headers


def _simulated_device(
    state_dir: str,
    conn: object,
    owner_id: int,
    index: int,
    hardware_type: str,
    fill: int,
) -> SimpleNamespace:
    mac = "aa:bb:cc:dd:ee:%02x" % (0x10 + index)
    secret_hex = hashlib.sha256(("secret-%d" % index).encode()).hexdigest()
    secret_sha = live_state.secret_hash(secret_hex)
    token = "tok-%02d-" % index + "e" * 36
    device_id = fleet_db.add_device(
        conn, mac, secret_sha, hardware_type, owner_id,  # type: ignore[arg-type]
        name="sim-%d" % index, token=token, state_path="auto")
    profile = hardware.get_profile(hardware_type, os.environ)
    directory = device_dirs.provision_device_dir(
        state_dir, device_id, profile.width, profile.height, fill=fill)
    # Legacy dual write, as `fleet_cli devices add` does.
    byos_server.register_device(state_dir, mac, secret_sha)
    legacy = byos_server.load_state(state_dir)
    legacy["tokens"][mac] = token
    byos_server.save_state(state_dir, legacy)
    return SimpleNamespace(
        id=device_id, mac=mac, secret_hex=secret_hex, token=token,
        state_dir=directory, fill=fill, hardware_type=hardware_type)


def seed_two_device_fleet(state_dir: str, with_landscape: bool = False) -> SimpleNamespace:
    """Seed the live frame plus two simulated devices; see module docstring."""
    seeded = live_state.seed_live_like_state(state_dir)
    fleet_migrate.migrate(state_dir, OWNER_EMAIL, dry_run=False)
    conn = fleet_db.connect(state_dir)
    try:
        live_row = fleet_db.get_device_by_mac(conn, seeded.mac)
        assert live_row is not None
        owner_id = int(live_row["owner_user_id"])
        live = SimpleNamespace(
            id=str(live_row["id"]), mac=seeded.mac, secret_hex=seeded.secret_hex,
            token=seeded.token, state_dir=state_dir, fill=None,
            hardware_type=hardware.LEGACY_KEY)
        # As `fleet_cli devices add --state-path auto` does before devices/ exists.
        device_dirs.record_live_macs(state_dir, {seeded.mac})
        with sim_hardware_env(), fleet_db.transaction(conn):
            dev_a = _simulated_device(
                state_dir, conn, owner_id, 1, hardware.SIM_CLONE_KEY, FILL_A)
            dev_b = _simulated_device(
                state_dir, conn, owner_id, 2, hardware.SIM_CLONE_KEY, FILL_B)
            landscape = None
            if with_landscape:
                landscape = _simulated_device(
                    state_dir, conn, owner_id, 3, hardware.SIM_LANDSCAPE_KEY,
                    FILL_LANDSCAPE)
    finally:
        conn.close()
    fleet = SimpleNamespace(live=live, dev_a=dev_a, dev_b=dev_b)
    if landscape is not None:
        fleet.landscape = landscape
    return fleet
