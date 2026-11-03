#!/usr/bin/env python3
"""The X-Wake-Stats request header on the byos request path.

A non-live (fleet) device's poll stores the wake columns in that device's
own history database. A malformed or absent header, or an unwritable
database, never changes the response. The live device's path is untouched:
its state files and stdout carry no trace of the header.
"""
import json
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
for _p in (REPO_ROOT, os.path.join(REPO_ROOT, "test-support")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from skypane_frame_server import FrameServer  # noqa: E402
from skypane_two_device_fleet import device_headers, seed_two_device_fleet  # noqa: E402

from server import history_db  # noqa: E402

VALID = "v=1;seq=830;bt=400;wf=1500;att=2;p_seq=829;p_aw=41000;p_rd=1;p_out=ok"
SIM_ENV = {"SKYPANE_SIM_HARDWARE": "1"}


@pytest.fixture
def served(tmp_path, monkeypatch):
    monkeypatch.setenv("SKYPANE_SIM_HARDWARE", "1")
    fleet = seed_two_device_fleet(str(tmp_path), with_landscape=True)
    server = FrameServer(fleet.live.state_dir, env_overrides=SIM_ENV)
    server.start()
    yield fleet, server
    server.stop()


_battery = iter(range(3600, 4200))


def poll(server, device, extra=None):
    headers = dict(device_headers(device))
    headers.pop("Authorization")
    # History rows are unique per (timestamp, battery); vary the reading so
    # polls within one second each store a row.
    headers["X-Battery-Mv"] = str(next(_battery))
    headers.update(extra or {})
    status, doc = server.display(device.token, headers)
    assert status == 200, doc
    return doc


def rows(directory):
    with history_db.open_db(directory) as conn:
        return [dict(r) for r in history_db.recent_device_health(conn)]


def shape(doc):
    return (sorted(doc), doc["image_hash"], doc["sleep_s"])


def test_valid_header_stores_the_wake_columns(served):
    fleet, server = served
    poll(server, fleet.dev_a, {"X-Wake-Stats": VALID})
    row = rows(fleet.dev_a.state_dir)[0]
    assert row["wake_seq"] == 830
    assert row["boot_ms"] == 400
    assert row["wifi_ms"] == 1500
    assert row["wifi_attempts"] == 2
    assert row["prev_seq"] == 829
    assert row["prev_awake_ms"] == 41000
    assert row["prev_redraw"] == 1
    assert row["prev_outcome"] == "ok"


@pytest.mark.parametrize("value", [None, "v=2;seq=1", "v=1;seq=abc", "garbage", "v=1;bogus=1"])
def test_absent_or_malformed_header_stores_null_columns_and_same_response(served, value):
    fleet, server = served
    baseline = poll(server, fleet.dev_a)
    extra = {} if value is None else {"X-Wake-Stats": value}
    doc = poll(server, fleet.dev_a, extra)
    assert shape(doc) == shape(baseline)
    stored = rows(fleet.dev_a.state_dir)
    assert len(stored) == 2
    assert all(r["wake_seq"] is None and r["prev_outcome"] is None for r in stored)


def test_valid_header_leaves_the_response_unchanged(served):
    fleet, server = served
    plain = poll(server, fleet.dev_a)
    with_header = poll(server, fleet.dev_a, {"X-Wake-Stats": VALID})
    assert shape(with_header) == shape(plain)


def test_unwritable_history_never_changes_the_response(served):
    fleet, server = served
    baseline = poll(server, fleet.dev_a)
    db = os.path.join(fleet.dev_a.state_dir, "history.db")
    for suffix in ("", "-wal", "-shm"):
        if os.path.exists(db + suffix):
            os.remove(db + suffix)
    os.makedirs(db)
    doc = poll(server, fleet.dev_a, {"X-Wake-Stats": VALID})
    assert shape(doc) == shape(baseline)


def read_state(device):
    out = {}
    for name in ("battery_state.json", os.path.join("firmware", "device_report.json")):
        path = os.path.join(device.state_dir, name)
        if os.path.exists(path):
            with open(path, encoding="utf-8") as fh:
                out[name] = json.load(fh)
    return out


def test_live_device_state_files_are_unchanged_by_the_header(served):
    fleet, server = served
    extra = {"X-Battery-Mv": "3900"}
    poll(server, fleet.live, extra)
    without = read_state(fleet.live)
    poll(server, fleet.live, dict(extra, **{"X-Wake-Stats": VALID}))
    with_header = read_state(fleet.live)
    for name, doc in without.items():
        assert sorted(with_header[name]) == sorted(doc)
    assert with_header["battery_state.json"]["battery_mv"] == 3900
    assert not os.path.exists(os.path.join(fleet.live.state_dir, "history.db"))


def test_header_value_never_reaches_stdout(served):
    fleet, server = served
    poll(server, fleet.dev_a, {"X-Wake-Stats": VALID})
    poll(server, fleet.live, {"X-Wake-Stats": VALID})
    out = server.stdout_text()
    assert VALID not in out
    assert "seq=830" not in out
