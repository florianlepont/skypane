# SPDX-License-Identifier: AGPL-3.0-only
"""Seeds shared by the Health Battery browser tests: a run of readings at an hourly cadence
(charging or discharging) written through the history database and the device config."""
from datetime import datetime, timedelta, timezone

from companion.test_browser_ux_helpers import seed_state_dir
from server import device_config, history_db

__test__ = False

# An hourly cadence keeps the readings fresh for two hours, so the shared,
# read-only server below never outlives its fixture however slow the run.
INTERVAL_S = 3600


def _seed_readings(state_dir, mvs):
    now = datetime.now(timezone.utc)
    with history_db.open_db(state_dir) as conn:
        for i, mv in enumerate(mvs):
            ts = now - timedelta(seconds=10 + INTERVAL_S * (len(mvs) - 1 - i))
            history_db.record_device_health(
                conn, ts.isoformat(timespec="seconds"), battery_mv=mv,
                fw_version="1.0.0", boot_reason="wake", rssi="-60")
    device_config.save_device_config(
        state_dir, wake_interval_s=INTERVAL_S, display_enabled=True, quiet_hours_enabled=False)


def _seed_charging(state_dir):
    seed_state_dir(state_dir)
    _seed_readings(state_dir, [3700 + 12 * i for i in range(12)])


def _seed_discharging(state_dir):
    seed_state_dir(state_dir)
    _seed_readings(state_dir, [4000 - 3 * i for i in range(12)])
