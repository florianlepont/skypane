"""Behaviour of the check-interval experiment predicate and its CLI."""
import json
import os
import subprocess
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
_TEST_SUPPORT_DIR = os.path.join(REPO_ROOT, "test-support")
for _p in (REPO_ROOT, _TEST_SUPPORT_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from server import check_interval, device_config  # noqa: E402
from skypane_test_support import child_env  # noqa: E402

NOW = 1_800_000_000.0


def write_raw(state_dir, payload):
    with open(os.path.join(str(state_dir), check_interval.EXPERIMENT_FILENAME), "w") as fh:
        if isinstance(payload, str):
            fh.write(payload)
        else:
            json.dump(payload, fh)


def active(state_dir, wake=900, battery=3900, now=NOW):
    return check_interval.active_check_interval_s(str(state_dir), wake, battery, now)


def test_active_when_everything_valid(tmp_path):
    write_raw(tmp_path, {"check_interval_s": 60, "expires_at": NOW + 3600})
    assert active(tmp_path) == 60


def test_missing_file_is_inactive(tmp_path):
    assert active(tmp_path) is None


@pytest.mark.parametrize("payload", [
    "not json", "[1, 2]", {},
    {"check_interval_s": True, "expires_at": NOW + 3600},
    {"check_interval_s": "60", "expires_at": NOW + 3600},
    {"check_interval_s": 60.5, "expires_at": NOW + 3600},
    {"check_interval_s": 59, "expires_at": NOW + 3600},
    {"check_interval_s": 60, "expires_at": "soon"},
    {"check_interval_s": 60, "expires_at": True},
    {"check_interval_s": 60, "expires_at": NOW},
    {"check_interval_s": 60, "expires_at": NOW - 5},
    {"check_interval_s": 60, "expires_at": NOW + 72 * 3600 + 1},
])
def test_invalid_or_expired_file_is_inactive(tmp_path, payload):
    write_raw(tmp_path, payload)
    assert active(tmp_path) is None


def test_expiry_exactly_72h_away_is_accepted(tmp_path):
    write_raw(tmp_path, {"check_interval_s": 60, "expires_at": NOW + 72 * 3600})
    assert active(tmp_path) == 60


def test_expires_by_itself(tmp_path):
    write_raw(tmp_path, {"check_interval_s": 60, "expires_at": NOW + 100})
    assert active(tmp_path, now=NOW) == 60
    assert active(tmp_path, now=NOW + 101) is None


@pytest.mark.parametrize("wake", [None, True, "900", 60, 59, 12.5])
def test_wake_interval_must_be_a_longer_integer(tmp_path, wake):
    write_raw(tmp_path, {"check_interval_s": 60, "expires_at": NOW + 3600})
    assert active(tmp_path, wake=wake) is None


@pytest.mark.parametrize("battery,expected", [
    (None, None), (True, None), (0, None), (3700, None), (3699, None),
    (3701, 60), (4100, 60),
])
def test_battery_floor(tmp_path, battery, expected):
    write_raw(tmp_path, {"check_interval_s": 60, "expires_at": NOW + 3600})
    assert active(tmp_path, battery=battery) == expected


def test_redraw_due():
    assert check_interval.redraw_due(None, NOW, 900) is True
    assert check_interval.redraw_due("x", NOW, 900) is True
    assert check_interval.redraw_due(NOW - 899, NOW, 900) is False
    assert check_interval.redraw_due(NOW - 900, NOW, 900) is True
    assert check_interval.redraw_due(NOW + 5, NOW, 900) is True


def run_cli(state_dir, *args):
    return subprocess.run(
        [sys.executable, "-m", "server.check_interval", *args, "--state-dir", str(state_dir)],
        cwd=REPO_ROOT, env=child_env(), capture_output=True, text=True, timeout=60)


def experiment_file(state_dir):
    return os.path.join(str(state_dir), check_interval.EXPERIMENT_FILENAME)


def test_cli_set_status_clear(tmp_path):
    device_config.save_device_config(str(tmp_path), wake_interval_s=900)
    result = run_cli(tmp_path, "set", "--check-interval-s", "60", "--hours", "24")
    assert result.returncode == 0, result.stderr
    with open(experiment_file(tmp_path)) as fh:
        data = json.load(fh)
    assert data["check_interval_s"] == 60
    import time
    assert abs(data["expires_at"] - (time.time() + 86400)) < 120
    status = run_cli(tmp_path, "status")
    assert status.returncode == 0
    assert "inactive" in status.stdout  # no battery reading yet
    with open(os.path.join(str(tmp_path), "battery_state.json"), "w") as fh:
        json.dump({"battery_mv": 3900}, fh)
    status = run_cli(tmp_path, "status")
    assert status.stdout.startswith("active")
    assert run_cli(tmp_path, "clear").returncode == 0
    assert not os.path.exists(experiment_file(tmp_path))
    assert run_cli(tmp_path, "clear").returncode == 0


@pytest.mark.parametrize("args", [
    ("--hours", "73"), ("--check-interval-s", "59"), ("--hours", "0"),
    ("--check-interval-s", "900"),
])
def test_cli_set_refuses_invalid_values(tmp_path, args):
    device_config.save_device_config(str(tmp_path), wake_interval_s=900)
    result = run_cli(tmp_path, "set", *args)
    assert result.returncode != 0
    assert not os.path.exists(experiment_file(tmp_path))


def test_cli_set_refuses_without_saved_wake_interval(tmp_path):
    result = run_cli(tmp_path, "set")
    assert result.returncode == 2
    assert not os.path.exists(experiment_file(tmp_path))
