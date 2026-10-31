"""Behaviour tests for the role-conditional user view: the settings form
policy that stops a user principal changing admin-only settings, the role
helpers, and the frame-only severity helper. Render-level checks for the
individual pages live in test_user_health.py and test_user_nav.py.
"""
import pytest

import companion.prefs as prefs
import companion.test_config_page_helpers as cp
from companion import access, user_view
from companion.pages import config_page
from server import device_config


@pytest.fixture(autouse=True)
def _reset_principal():
    prefs.set_request_principal(None)
    yield
    prefs.set_request_principal(None)


def _as(role):
    prefs.set_request_principal(role, role)


CRAFTED_USER_FORM = {
    "wake_interval_s": "60",
    "led_enabled": "on",
    "tracked_runway": "06-24",
    "scope": "all",
}


def test_user_form_loses_admin_only_fields_and_scope_is_forced_to_display():
    cleaned = user_view.sanitise_settings_form(
        dict(CRAFTED_USER_FORM, theme="sky"), access.USER)
    for name in user_view.ADMIN_ONLY_SETTING_FIELDS:
        assert name not in cleaned
    assert cleaned["scope"] == config_page.SCOPE_DISPLAY
    assert cleaned["theme"] == "sky"


@pytest.mark.parametrize("scope", ["all", "device", "bogus"])
def test_user_scope_is_always_display(scope):
    cleaned = user_view.sanitise_settings_form({"scope": scope}, access.USER)
    assert cleaned["scope"] == config_page.SCOPE_DISPLAY


def test_admin_form_is_unchanged():
    form = dict(CRAFTED_USER_FORM)
    cleaned = user_view.sanitise_settings_form(form, access.ADMIN)
    assert cleaned == form
    assert cleaned is not form


def test_crafted_user_post_leaves_admin_only_config_untouched(tmp_path):
    state_dir = str(tmp_path)
    cp.write_device_config(state_dir, "sky", "3", led_enabled=False)
    before = device_config.load_device_config(state_dir)

    form = user_view.sanitise_settings_form(CRAFTED_USER_FORM, access.USER)
    flash_key = config_page.handle_post(form, {"state_dir": state_dir})

    assert flash_key == config_page.FLASH_SAVED
    after = device_config.load_device_config(state_dir)
    for key in ("wake_interval_s", "led_enabled", "tracked_runway"):
        assert after.get(key) == before.get(key), key


def test_platform_visible_without_principal_and_for_admin_not_for_user():
    assert user_view.platform_visible() is True
    assert user_view.is_user_view() is False
    _as("admin")
    assert user_view.platform_visible() is True
    _as("user")
    assert user_view.platform_visible() is False
    assert user_view.is_user_view() is True


def test_frame_only_severity_ignores_platform_inputs():
    assert user_view.frame_only_severity(
        "ok", "error", "ok", True, source_fault=True, offbox_state="warn",
        fleet_fault=True) == "ok"
    assert user_view.frame_only_anomalies(
        "ok", "error", "ok", True, source_fault=True,
        offbox={"state": "warn"}, fleet_fault=True) == []


def test_frame_only_severity_keeps_check_in_and_battery():
    assert user_view.frame_only_severity("warn", "ok", "ok", False) == "warn"
    assert user_view.frame_only_severity("error", "ok", "ok", False) == "error"
    assert user_view.frame_only_severity("ok", "ok", "warn", False) == "warn"
    assert len(user_view.frame_only_anomalies("warn", "ok", "warn", False)) == 2
