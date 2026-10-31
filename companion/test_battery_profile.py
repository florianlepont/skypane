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
        assert battery.percent(mv) == device_policy.battery_percent(mv)
        assert battery.fraction(mv) == device_policy.battery_fraction(mv)
        assert battery.percent(mv, battery.BATTERY_DISCHARGE_CURVE) == (
            device_policy.battery_percent(mv))


def test_synthetic_curve_changes_percent_and_low_mark():
    assert battery.percent(3900, SHIFTED_CURVE) < battery.percent(3900)
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


# --- served pages and chart ---------------------------------------------

import re

from companion import battery_chart
from companion.pages import health_page

_ROWS = [
    {"ts": "2026-10-%02dT08:00:00Z" % day, "battery_mv": 3700 + 10 * day}
    for day in range(9, 0, -1)
]


def _percent_values(html):
    return re.findall(r"≈ (\d+)%", html)


def test_chart_legacy_curve_equals_default():
    default = battery_chart.battery_unit_chart(_ROWS, now="2026-10-10T00:00:00Z")
    explicit = battery_chart.battery_unit_chart(
        _ROWS, now="2026-10-10T00:00:00Z", curve=battery.BATTERY_DISCHARGE_CURVE)
    assert default and default == explicit


def test_chart_percent_and_low_line_follow_the_curve():
    default = battery_chart.battery_unit_chart(_ROWS, now="2026-10-10T00:00:00Z")
    shifted = battery_chart.battery_unit_chart(
        _ROWS, now="2026-10-10T00:00:00Z", curve=SHIFTED_CURVE)
    assert _percent_values(default) != _percent_values(shifted)
    assert "%d mV" % battery.LOW_BATTERY_DISPLAY_MV in default
    assert "%d mV" % (battery.LOW_BATTERY_DISPLAY_MV + 200) in shifted


def test_health_section_legacy_identity_and_difference():
    legacy_html, legacy_state = health_page._battery_section(_ROWS, None)
    same_html, same_state = health_page._battery_section(
        _ROWS, None, battery.BATTERY_DISCHARGE_CURVE)
    other_html, other_state = health_page._battery_section(_ROWS, None, SHIFTED_CURVE)
    assert (legacy_html, legacy_state) == (same_html, same_state)
    assert other_html != legacy_html
    assert other_state == legacy_state


def test_device_curve_follows_the_registered_profile(monkeypatch):
    from companion import page_context
    shifted = shifted_registry(monkeypatch)
    assert page_context.device_curve(_device(shifted.key)) == SHIFTED_CURVE
    assert page_context.device_curve(_device(hardware.LEGACY_KEY)) == (
        battery.BATTERY_DISCHARGE_CURVE)
    assert page_context.device_curve(None) is None
    assert page_context.device_curve(_device("hostile'type")) == (
        battery.BATTERY_DISCHARGE_CURVE)


def _seed_unknown_hardware(fleet):
    from server import fleet_db, history_db
    state_dir = fleet.live.state_dir
    conn = fleet_db.connect(state_dir)
    try:
        conn.execute(
            "UPDATE devices SET hardware_type = ? WHERE id = ?",
            ("<script>no-such-type</script>", fleet.dev_a.id))
    finally:
        conn.close()
    with history_db.open_db(fleet.dev_a.state_dir) as db:
        for hour, mv in ((6, 3900), (7, 3890), (8, 3880)):
            history_db.record_device_health(
                db, "2027-01-15T%02d:00:00+00:00" % hour, battery_mv=mv)


def test_unknown_hardware_row_still_serves_health_and_home(make_app_server):
    from companion.test_device_helpers import get, start_fleet_app
    app = start_fleet_app(make_app_server, seed_extra=_seed_unknown_hardware)
    prefix = "/devices/%s" % app.fleet.dev_a.id
    status, _headers, body = get(app, prefix + "/health")
    assert status == 200
    assert "no-such-type" not in body
    status, _headers, _body = get(app, prefix + "/")
    assert status == 200
