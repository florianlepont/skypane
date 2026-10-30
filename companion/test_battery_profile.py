"""The companion battery arithmetic follows a hardware profile's curve,
and reads exactly as before on the legacy curve."""
import dataclasses
import types

import pytest

from companion import battery, device_scope
from server import hardware

# A synthetic curve that reads much lower than the legacy one at the
# same voltage.
SHIFTED_CURVE = tuple((mv + 200, pct) for mv, pct in battery.BATTERY_DISCHARGE_CURVE)


def _device(hardware_type):
    return types.SimpleNamespace(hardware_type=hardware_type)


def test_legacy_sweep_is_identical_to_the_server_policy():
    from server import device_policy
    for mv in list(range(-1, 4300, 7)) + [3000, 3500, 3540, 4200]:
        assert battery.battery_percent(mv) == device_policy.battery_percent(mv)
        assert battery.battery_fraction(mv) == device_policy.battery_fraction(mv)
        assert battery.battery_percent(mv, battery.BATTERY_DISCHARGE_CURVE) == (
            device_policy.battery_percent(mv))


def test_synthetic_curve_changes_percent_and_low_mark():
    assert battery.battery_percent(3900, SHIFTED_CURVE) < battery.battery_percent(3900)
    assert battery.low_display_mv(SHIFTED_CURVE) == battery.LOW_BATTERY_DISPLAY_MV + 200
    assert battery.low_display_mv() == battery.LOW_BATTERY_DISPLAY_MV


def test_life_estimate_follows_the_curve():
    rows = [{"ts": "2026-10-01", "battery_mv": 4000},
            {"ts": "2026-10-05", "battery_mv": 3800}]
    legacy = battery.battery_life_estimate(rows)
    default = battery.battery_life_estimate(rows, curve=battery.BATTERY_DISCHARGE_CURVE)
    shifted = battery.battery_life_estimate(rows, curve=SHIFTED_CURVE)
    assert legacy == default
    assert shifted["days_remaining"] != legacy["days_remaining"]


@pytest.mark.parametrize("bad", [None, "", "no-such-type", 7, object(), "sim-landscape"])
def test_profile_for_never_raises_and_falls_back(bad, monkeypatch):
    monkeypatch.delenv(hardware.SIM_ENV_VAR, raising=False)
    legacy = hardware.REGISTRY[hardware.LEGACY_KEY]
    assert device_scope.profile_for(_device(bad)) is legacy
    assert device_scope.profile_for(bad) is legacy


def test_profile_for_returns_the_registered_profile(monkeypatch):
    monkeypatch.setenv(hardware.SIM_ENV_VAR, "1")
    sim = hardware.REGISTRY[hardware.SIM_LANDSCAPE_KEY]
    assert device_scope.profile_for(_device(sim.key)) is sim
    assert device_scope.profile_for(_device(hardware.LEGACY_KEY)).key == hardware.LEGACY_KEY


def shifted_registry(monkeypatch):
    """Gate simulation on and give sim-landscape a shifted battery curve."""
    sim = hardware.REGISTRY[hardware.SIM_LANDSCAPE_KEY]
    shifted = dataclasses.replace(
        sim, battery=dataclasses.replace(sim.battery, curve=SHIFTED_CURVE))
    monkeypatch.setenv(hardware.SIM_ENV_VAR, "1")
    monkeypatch.setattr(
        hardware, "REGISTRY",
        types.MappingProxyType({**hardware.REGISTRY, sim.key: shifted}))
    return shifted
