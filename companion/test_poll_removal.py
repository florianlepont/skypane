"""The companion no longer offers a manual poll: the pages carry no poll
form or cooldown script, the stylesheet/script set has no cooldown asset, and
the per-device poll lock that calendar-connect syncs take stays per directory.
"""
import pytest

from companion.test_device_helpers import get, start_fleet_app

from companion import device_scope


def _prefix(device):
    return "/devices/%s" % device.id


@pytest.fixture
def fleet_app(make_app_server):
    return start_fleet_app(make_app_server)


@pytest.mark.parametrize("path", ("/", "/device", "/display", "/flights", "/health"))
def test_pages_carry_no_poll_form_button_or_cooldown_script(fleet_app, path):
    prefixes = [_prefix(fleet_app.fleet.live), _prefix(fleet_app.fleet.dev_a)]
    if path in ("/device", "/health"):
        # The Console pages of the served frame also answer without a prefix.
        prefixes.append("")
    for prefix in prefixes:
        status, _headers, page = get(fleet_app, prefix + path)
        assert status == 200
        assert "poll-now" not in page
        assert "poll-trigger-btn" not in page
        assert "poll-cooldown" not in page
        assert "Refresh now" not in page


def test_the_cooldown_script_is_not_served(fleet_app):
    status, _headers, _body = get(fleet_app, "/static/poll-cooldown.js")
    assert status == 404


def test_the_poll_lock_registry_is_per_directory(fleet_app):
    fleet = fleet_app.fleet
    a = device_scope.poll_lock_for(fleet.dev_a.state_dir)
    b = device_scope.poll_lock_for(fleet.dev_b.state_dir)
    assert a is not b
    assert a is device_scope.poll_lock_for(fleet.dev_a.state_dir)


def test_rule_and_settings_forms_carry_the_device_prefix(fleet_app):
    prefix = _prefix(fleet_app.fleet.dev_a)
    status, _, page = get(fleet_app, prefix + "/display")
    assert status == 200
    assert 'id="settings-form" data-dirty-form method="post" action="%s/settings"' % prefix in page
    assert 'action="%s/settings/rules/add"' % prefix in page
    live_prefix = _prefix(fleet_app.fleet.live)
    _status, _, live = get(fleet_app, live_prefix + "/display")
    assert 'id="settings-form" data-dirty-form method="post" action="%s/settings"' % live_prefix in live
    assert 'action="%s/settings/rules/add"' % live_prefix in live
    assert 'action="%s/' % prefix not in live
