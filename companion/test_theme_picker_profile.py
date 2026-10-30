"""The Display page's theme pickers offer only the themes the device's
hardware profile can draw; every real profile offers all of them."""
import dataclasses
import json
import re
import types

from companion import device_scope
from companion.settings import form_post, look
from server import device_config, hardware, panel_format

REDUCED_INKS = frozenset({
    panel_format.IDX_BLACK, panel_format.IDX_WHITE, panel_format.IDX_RED})
LEGACY = hardware.REGISTRY[hardware.LEGACY_KEY]
REDUCED = dataclasses.replace(LEGACY, key="reduced-test", inks=REDUCED_INKS)
DEVICE = types.SimpleNamespace(hardware_type=REDUCED.key)


def _preview(theme_id):
    return "/preview/%s.png" % theme_id


def _table(**kwargs):
    return look.look_table_html("theme", "", "Departures", _preview, **kwargs)


def _radio_values(html):
    return re.findall(r'<input type="radio" name="theme" value="([^"]*)"', html)


def _use_reduced_profile(monkeypatch):
    monkeypatch.setattr(
        device_scope, "profile_for",
        lambda device: REDUCED if device is DEVICE else LEGACY)
    device_scope.set_request_scope(DEVICE, [DEVICE])


def test_every_real_profile_offers_all_themes(monkeypatch):
    monkeypatch.setenv(hardware.SIM_ENV_VAR, "1")
    for profile in hardware.REGISTRY.values():
        device = types.SimpleNamespace(hardware_type=profile.key)
        assert look.offered_theme_ids(device) == device_config.THEME_IDS


def test_legacy_table_lists_every_theme():
    html = _table()
    assert sorted(_radio_values(html)) == sorted(device_config.THEME_IDS)
    assert html == _table(theme_ids=device_config.THEME_IDS)


def test_reduced_profile_turns_unsupported_themes_into_gap_cells(monkeypatch):
    _use_reduced_profile(monkeypatch)
    offered = look.offered_theme_ids(DEVICE)
    assert 0 < len(offered) < len(device_config.THEME_IDS)
    html = _table()
    assert sorted(_radio_values(html)) == sorted(offered)
    assert html.count("look-table__gap") > _table(
        theme_ids=device_config.THEME_IDS).count("look-table__gap")
    assert look.i18n.t(look.REASON_MESSAGES[look.REASON_NO_THEME]) in html


def test_script_model_only_lists_offered_cells(monkeypatch):
    _use_reduced_profile(monkeypatch)
    model = json.loads(look.look_model_json())
    assert set(model["cells"].values()) <= set(look.offered_theme_ids(DEVICE))
    full = json.loads(look.look_model_json(device_config.THEME_IDS))
    assert len(model["cells"]) < len(full["cells"])


def test_form_validation_still_accepts_any_registry_theme(monkeypatch):
    _use_reduced_profile(monkeypatch)
    hidden = next(
        t for t in device_config.THEME_IDS if t not in look.offered_theme_ids(DEVICE))
    errors = {}
    assert form_post.resolve_theme({"theme": hidden}, errors) == {"theme": hidden}
    assert not errors
