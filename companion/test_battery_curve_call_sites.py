"""Every companion surface that prints a battery percentage uses the curve of
the frame's own hardware profile: Console fleet rows, pending-pairing rows,
the frame switcher status row and the account frame summary."""
import dataclasses
import json
import os
import time
import types

import pytest

import fleet_console_support as fx
from companion import layout  # noqa: F401  (import order: layout before ui_shell)
from companion import battery, console_pairing, device_scope, prefs, ui_shell
from companion.sign_in import SignInMixin
from server import fleet_db, fleet_ops, hardware

MV = 3900
SHIFTED = tuple((mv + 200, pct) for mv, pct in battery.BATTERY_DISCHARGE_CURVE)
LEGACY_PERCENT = battery.percent(MV)
SHIFTED_PERCENT = battery.percent(MV, SHIFTED)
SIM = hardware.SIM_LANDSCAPE_KEY


@pytest.fixture(autouse=True)
def _english():
    prefs.set_request_prefs(lang="en")
    yield


@pytest.fixture
def shifted_sim(monkeypatch):
    """Simulation on, with a sim profile whose curve differs from legacy."""
    sim = hardware.REGISTRY[SIM]
    shifted = dataclasses.replace(
        sim, battery=dataclasses.replace(sim.battery, curve=SHIFTED))
    monkeypatch.setenv(hardware.SIM_ENV_VAR, "1")
    monkeypatch.setattr(
        hardware, "REGISTRY",
        types.MappingProxyType({**hardware.REGISTRY, SIM: shifted}))


def test_the_curves_really_differ():
    assert LEGACY_PERCENT != SHIFTED_PERCENT


def _seed(state_dir, hardware_type):
    """One owned frame of `hardware_type` reporting MV; returns its Device."""
    seed = fx.seed_users(state_dir)
    conn = fleet_db.connect(state_dir)
    try:
        fleet_db.add_device(
            conn, "aa:bb:cc:00:00:09", fx.SECRET_HASH, hardware_type,
            seed.owner_id, name="Test frame", state_path="auto",
            environ=os.environ)
    finally:
        conn.close()
    device = [d for d in device_scope.load_devices(state_dir) if d.name == "Test frame"][0]
    os.makedirs(device.state_dir, exist_ok=True)
    with open(os.path.join(device.state_dir, "battery_state.json"), "w") as fh:
        json.dump({"battery_mv": MV}, fh)
    return device


def _device_row_percent(state_dir):
    view = console_pairing.build_view(state_dir)
    return [r.battery_percent for r in view.rows if r.name == "Test frame"][0]


def _pending_percent(state_dir, stored_type):
    conn = fleet_db.connect(state_dir)
    try:
        pending_id = fleet_ops.register_frame(
            conn, "aa:bb:cc:00:00:0a", fx.SECRET_HASH, hardware.LEGACY_KEY, fx.ACTOR)
        conn.execute(
            "UPDATE pending_devices SET battery_mv = ?, hardware_type = ? WHERE id = ?",
            (MV, stored_type, pending_id))
        conn.commit()
    finally:
        conn.close()
    view = console_pairing.build_view(state_dir)
    return [r.battery_percent for r in view.rows if r.mono_id == str(pending_id)][0]


def _summary_percent(device):
    summary = SignInMixin._frame_summary(
        None, device, __import__("datetime").datetime.now(
            __import__("datetime").timezone.utc), False, None, None)
    return summary.battery_percent


def _switcher_percent(device):
    return ui_shell._switcher_status_row(device, time.time()).battery_percent


def test_profile_curve_is_used_at_every_device_surface(tmp_path, shifted_sim):
    device = _seed(str(tmp_path), SIM)
    assert _device_row_percent(str(tmp_path)) == SHIFTED_PERCENT
    assert _switcher_percent(device) == SHIFTED_PERCENT
    assert _summary_percent(device) == SHIFTED_PERCENT


def test_legacy_frame_shows_the_legacy_percent_everywhere(tmp_path):
    device = _seed(str(tmp_path), hardware.LEGACY_KEY)
    assert _device_row_percent(str(tmp_path)) == LEGACY_PERCENT
    assert _switcher_percent(device) == LEGACY_PERCENT
    assert _summary_percent(device) == LEGACY_PERCENT


def test_pending_row_follows_its_stored_type_even_when_the_gate_is_closed(
        tmp_path, shifted_sim, monkeypatch):
    assert _pending_percent(str(tmp_path), SIM) == SHIFTED_PERCENT
    monkeypatch.delenv(hardware.SIM_ENV_VAR)
    other = tmp_path / "second"
    other.mkdir()
    assert _pending_percent(str(other), SIM) == SHIFTED_PERCENT


def test_pending_row_with_an_unknown_type_reads_legacy_and_does_not_raise(tmp_path):
    assert _pending_percent(str(tmp_path), "no-such-type") == LEGACY_PERCENT


def test_device_with_an_unknown_type_reads_legacy(tmp_path):
    device = _seed(str(tmp_path), hardware.LEGACY_KEY)
    unknown = device._replace(hardware_type="no-such-type") if hasattr(
        device, "_replace") else dataclasses.replace(device, hardware_type="no-such-type")
    assert _switcher_percent(unknown) == LEGACY_PERCENT
    assert _summary_percent(unknown) == LEGACY_PERCENT
