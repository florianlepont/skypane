"""POST /devices/<id>/poll-now: one poll cycle against one device's directory,
under that device's own lock and cooldown; hardware the cycle cannot render
is refused. Real app subprocess (fake providers) for the on-disk effects, the
in-process server for call spies and lock holding.
"""
import os
import re
import sqlite3
import time

import pytest

from companion.test_device_helpers import get, post, snapshot, snapshot_all, start_fleet_app
from skypane_two_device_fleet import seed_two_device_fleet

import companion.app as app_module
from companion import device_scope
from companion import auth
from companion.settings import rules
from companion_app_server import http_request
from server import atomic_io, fleet_db, hardware, history_db
from server.plane import colour_rules


@pytest.fixture
def fleet_app(make_app_server):
    return start_fleet_app(make_app_server, fake_providers=True)


def _prefix(device):
    return "/devices/%s" % device.id


def _retype_landscape_as_unknown(fleet):
    """Give the seeded third device a hardware type no profile knows, the
    one case the poll cycle cannot render."""
    conn = sqlite3.connect(fleet_db.fleet_db_path(os.path.dirname(os.path.dirname(fleet.dev_a.state_dir))))
    try:
        with conn:
            conn.execute(
                "UPDATE devices SET hardware_type = ? WHERE id = ?",
                ("unknown-panel", fleet.landscape.id))
    finally:
        conn.close()


@pytest.fixture
def unsupported_app(make_app_server):
    return start_fleet_app(
        make_app_server, seed_extra=_retype_landscape_as_unknown, fake_providers=True)


def _flash(headers):
    location = headers.get("Location", "")
    assert "flash=" in location, location
    return location.split("flash=", 1)[1]


def _warm_up(app):
    """The first request creates fleet.db's SQLite sidecars and initialises the
    history databases it reads; snapshots are taken after it."""
    get(app, _prefix(app.fleet.dev_a) + "/health")
    get(app, "/health")


def test_poll_now_writes_only_that_devices_directory(fleet_app):
    app = fleet_app
    fleet = app.fleet
    _warm_up(app)
    before_live, _before_a, before_b = snapshot_all(app.server, fleet)
    landscape_before = snapshot(fleet.landscape.state_dir)
    status, headers, _ = post(app, _prefix(fleet.dev_a) + "/poll-now")
    assert status == 303
    assert _flash(headers) == "device_poll_done"
    assert os.path.exists(os.path.join(fleet.dev_a.state_dir, "poll_state.json"))
    assert os.path.exists(history_db.history_db_path(fleet.dev_a.state_dir))
    assert snapshot(fleet.dev_b.state_dir) == before_b
    assert snapshot(fleet.landscape.state_dir) == landscape_before
    live_after = snapshot(app.server.state_dir)
    assert live_after == before_live


def test_poll_now_creates_no_firmware_directory_in_a_device_directory(fleet_app):
    app = fleet_app
    post(app, _prefix(app.fleet.dev_a) + "/poll-now")
    assert not os.path.exists(os.path.join(app.fleet.dev_a.state_dir, "firmware"))


def test_device_poll_flash_names_the_device_on_the_redirect_page(fleet_app):
    app = fleet_app
    prefix = _prefix(app.fleet.dev_a)
    _status, headers, _ = post(app, prefix + "/poll-now")
    status, _, page = get(app, headers["Location"])
    assert status == 200
    assert "was refreshed" in page
    assert "sim-1 was refreshed" in page.lower()


def test_device_poll_redirect_keeps_the_device_prefix(fleet_app):
    app = fleet_app
    prefix = _prefix(app.fleet.dev_a)
    _status, headers, _ = post(
        app, prefix + "/poll-now",
        headers={"Referer": app.server.base_url() + prefix + "/device"})
    assert headers["Location"].startswith(prefix + "/device?flash=")
    _status, headers, _ = post(app, prefix + "/poll-now")
    assert headers["Location"].startswith(prefix + "/?flash=")


def test_a_referer_under_another_device_stays_on_this_device(fleet_app):
    app = fleet_app
    fleet = app.fleet
    _status, headers, _ = post(
        app, _prefix(fleet.dev_a) + "/poll-now",
        headers={"Referer": app.server.base_url() + _prefix(fleet.dev_b) + "/device"})
    assert headers["Location"].startswith(_prefix(fleet.dev_a) + "/device?flash=")


def test_live_frame_poll_keeps_its_flash_key_and_redirect(fleet_app):
    app = fleet_app
    status, headers, _ = post(app, "/poll-now")
    assert status == 303
    assert headers["Location"] == "/?flash=poll_triggered"


def test_unsupported_hardware_is_refused_without_touching_any_directory(unsupported_app):
    app = unsupported_app
    fleet = app.fleet
    _warm_up(app)
    live, dev_a, dev_b = snapshot_all(app.server, fleet)
    landscape = snapshot(fleet.landscape.state_dir)
    status, headers, _ = post(app, _prefix(fleet.landscape) + "/poll-now")
    assert status == 303
    assert headers["Location"].startswith(_prefix(fleet.landscape) + "/")
    assert _flash(headers) == "device_poll_unsupported"
    assert snapshot(app.server.state_dir) == live
    assert snapshot(fleet.dev_a.state_dir) == dev_a
    assert snapshot(fleet.dev_b.state_dir) == dev_b
    assert snapshot(fleet.landscape.state_dir) == landscape


def test_unsupported_refusal_toast_is_a_warning_that_never_auto_hides(unsupported_app):
    app = unsupported_app
    _status, headers, _ = post(app, _prefix(app.fleet.landscape) + "/poll-now")
    status, _, page = get(app, headers["Location"])
    assert status == 200
    assert "Poll not available" in page
    assert "data-toast-autohide" not in page
    assert 'role="alert"' in page


def test_unknown_device_poll_is_a_404_and_writes_nothing(fleet_app):
    app = fleet_app
    _warm_up(app)
    before = snapshot_all(app.server, app.fleet)
    status, _, _ = post(app, "/devices/d_00000000/poll-now")
    assert status == 404
    assert snapshot_all(app.server, app.fleet) == before


def test_a_held_poll_lock_file_gives_the_already_running_flash_for_that_device_only(fleet_app):
    app = fleet_app
    fleet = app.fleet
    with atomic_io.exclusive_lock(os.path.join(fleet.dev_a.state_dir, "poll.lock"), 5):
        _status, headers, _ = post(app, _prefix(fleet.dev_a) + "/poll-now")
        assert _flash(headers) == "poll_already_running"
        _status, headers, _ = post(app, _prefix(fleet.dev_b) + "/poll-now")
        assert _flash(headers) == "device_poll_done"
        _status, headers, _ = post(app, "/poll-now")
        assert _flash(headers) == "poll_triggered"


# --- in-process server: spies and in-process locks ---------------------------

@pytest.fixture
def inprocess(app_server_in_process, monkeypatch):
    monkeypatch.setenv(hardware.SIM_ENV_VAR, "1")
    server = app_server_in_process
    fleet = seed_two_device_fleet(server.state_dir, with_landscape=True)
    calls = []

    def fake_run_once(**kwargs):
        calls.append(kwargs)
        return {}

    monkeypatch.setattr(app_module.poll_cycle, "run_once", fake_run_once)
    from companion_app_server import login
    app = type("App", (), {})()
    app.server, app.fleet, app.cookie, app.calls = server, fleet, login(server), calls
    return app


def test_the_cycle_runs_without_a_caddy_log_for_every_directory(inprocess):
    app = inprocess
    post(app, _prefix(app.fleet.dev_a) + "/poll-now")
    post(app, "/poll-now")
    assert len(app.calls) == 2
    for kwargs in app.calls:
        assert kwargs.get("caddy_log") is None
    assert app.calls[0]["state_dir"] == app.fleet.dev_a.state_dir
    assert app.calls[1]["state_dir"] == app.server.state_dir


def test_holding_one_devices_lock_does_not_block_another(inprocess):
    app = inprocess
    lock = device_scope.poll_lock_for(app.fleet.dev_a.state_dir)
    assert lock.acquire(blocking=False)
    try:
        _status, headers, _ = post(app, _prefix(app.fleet.dev_a) + "/poll-now")
        assert _flash(headers) == "poll_already_running"
        _status, headers, _ = post(app, _prefix(app.fleet.dev_b) + "/poll-now")
        assert _flash(headers) == "device_poll_done"
        _status, headers, _ = post(app, "/poll-now")
        assert _flash(headers) == "poll_triggered"
    finally:
        lock.release()
    assert [c["state_dir"] for c in app.calls] == [
        app.fleet.dev_b.state_dir, app.server.state_dir]


def test_the_cooldown_of_one_device_never_affects_another(inprocess):
    app = inprocess
    _status, headers, _ = post(app, _prefix(app.fleet.dev_a) + "/poll-now")
    assert _flash(headers) == "device_poll_done"
    _status, headers, _ = post(app, _prefix(app.fleet.dev_a) + "/poll-now")
    assert _flash(headers).startswith("poll_cooldown")
    _status, headers, _ = post(app, _prefix(app.fleet.dev_b) + "/poll-now")
    assert _flash(headers) == "device_poll_done"
    _status, headers, _ = post(app, "/poll-now")
    assert _flash(headers) == "poll_triggered"
    assert len(app.calls) == 3


def test_the_lock_registry_is_per_directory(inprocess):
    a = device_scope.poll_lock_for(inprocess.fleet.dev_a.state_dir)
    b = device_scope.poll_lock_for(inprocess.fleet.dev_b.state_dir)
    assert a is not b
    assert a is device_scope.poll_lock_for(inprocess.fleet.dev_a.state_dir)


# --- Poll section markup on the device pages ----------------------------------

MARKUP_NAME = "<b>x</b>&"
BASE_CAPTION = "Ask the server to check for new flight data now."


def _rename_dev_a(fleet):
    conn = sqlite3.connect(fleet_db.fleet_db_path(os.path.dirname(os.path.dirname(fleet.dev_a.state_dir))))
    try:
        with conn:
            conn.execute("UPDATE devices SET name = ? WHERE id = ?", (MARKUP_NAME, fleet.dev_a.id))
    finally:
        conn.close()


def _seed_cooldown_and_rule(fleet):
    _rename_dev_a(fleet)
    with history_db.open_db(fleet.dev_a.state_dir) as conn:
        history_db.set_meta(conn, history_db.META_LAST_POLL_TRIGGER, str(int(time.time()) - 5))
    colour_rules.add_rule(fleet.dev_a.state_dir, colour_rules.RULE_KIND_CALLSIGN, "AFR1234", "white")


@pytest.fixture
def page_app(make_app_server):
    return start_fleet_app(make_app_server, seed_extra=_seed_cooldown_and_rule)


@pytest.fixture
def unsupported_page_app(make_app_server):
    return start_fleet_app(make_app_server, seed_extra=_retype_landscape_as_unknown)


def _poll_section(page):
    found = re.search(
        r'<section class="page-section"><h2 class="text-heading">[^<]*</h2>(.*?)</section>',
        page[page.index('class="config-form"'):], re.S)
    assert found, "the Poll section is missing"
    return found.group(1)


def _caption(section):
    return re.search(r'<p class="text-label section-caption">(.*?)</p>', section, re.S).group(1)


def _device_page(app, device):
    status, _, page = get(app, _prefix(device) + "/device")
    assert status == 200
    return page


def test_the_poll_form_posts_to_the_selected_device(page_app):
    section = _poll_section(_device_page(page_app, page_app.fleet.dev_b))
    assert 'action="%s/poll-now"' % _prefix(page_app.fleet.dev_b) in section
    status, _, live = get(page_app, "/device")
    assert status == 200
    assert '<form method="post" action="/poll-now">' in _poll_section(live)


def test_several_devices_add_the_scope_sentence_to_the_same_caption(page_app):
    section = _poll_section(_device_page(page_app, page_app.fleet.dev_b))
    assert _caption(section) == BASE_CAPTION + " Runs one check for sim-2 only."
    assert section.count("section-caption") == 1


def test_the_device_name_is_escaped_in_the_caption(page_app):
    page = _device_page(page_app, page_app.fleet.dev_a)
    caption = _caption(_poll_section(page))
    assert caption.endswith("Runs one check for &lt;b&gt;x&lt;/b&gt;&amp; only.")
    assert "<b>x</b>" not in _poll_section(page)


def test_the_caption_is_translated(page_app):
    cookie = "%s; %s=fr" % (page_app.cookie, auth.UI_LANG_COOKIE_NAME)
    _status, _, body = http_request(
        page_app.server.base_url() + _prefix(page_app.fleet.dev_b) + "/device", cookie=cookie)
    caption = _caption(_poll_section(body.decode("utf-8")))
    assert caption.endswith("Lance une vérification pour sim-2 uniquement.")


def test_one_device_keeps_the_shipped_caption_and_markup():
    one = rules.poll_trigger_section(0)
    assert one == rules.poll_trigger_section(0, None, 1)
    only = rules.poll_trigger_section(0, device_scope.Device(
        "live", "Orly frame", hardware.LEGACY_KEY, "", "", True), 1)
    assert only == one
    assert _caption(one) == BASE_CAPTION
    assert 'action="/poll-now"' in one and "aria-disabled" not in one


def test_an_unsupported_screen_type_disables_the_button_and_replaces_the_caption(unsupported_page_app):
    section = _poll_section(_device_page(unsupported_page_app, unsupported_page_app.fleet.landscape))
    assert re.search(r"<button[^>]* disabled aria-disabled=\"true\">", section)
    assert _caption(section) == "Not available for this screen type yet."
    assert section.count("<p") == 1
    assert BASE_CAPTION not in section


def test_the_unsupported_caption_is_translated(unsupported_page_app):
    app = unsupported_page_app
    cookie = "%s; %s=fr" % (app.cookie, auth.UI_LANG_COOKIE_NAME)
    _status, _, body = http_request(
        app.server.base_url() + _prefix(app.fleet.landscape) + "/device", cookie=cookie)
    assert _caption(_poll_section(body.decode("utf-8"))) == "Indisponible pour ce type d’écran pour l’instant."


def test_the_cooldown_shown_is_that_devices_own(page_app):
    fleet = page_app.fleet
    cooling = _poll_section(_device_page(page_app, fleet.dev_a))
    assert "data-cooldown=" in cooling and " disabled " in cooling
    assert 'id="poll-cooldown-text"' in cooling
    idle = _poll_section(_device_page(page_app, fleet.dev_b))
    assert "data-cooldown=" not in idle and "disabled" not in idle
    live = _poll_section(get(page_app, "/device")[2])
    assert "disabled" not in live


def test_rule_and_settings_forms_carry_the_device_prefix(page_app):
    fleet = page_app.fleet
    prefix = _prefix(fleet.dev_a)
    status, _, page = get(page_app, prefix + "/display")
    assert status == 200
    assert 'id="settings-form" data-dirty-form method="post" action="%s/settings"' % prefix in page
    assert 'action="%s/settings/rules/add"' % prefix in page
    assert 'action="%s/settings/rules/callsign/AFR1234/delete"' % prefix in page
    _status, _, live = get(page_app, "/display")
    assert 'id="settings-form" data-dirty-form method="post" action="/settings"' in live
    assert 'action="/settings/rules/add"' in live
    assert "/settings/rules/callsign/AFR1234/delete" not in live
    assert 'action="/devices/' not in live


def test_non_live_devices_poll_with_their_own_profile(inprocess):
    app = inprocess
    post(app, _prefix(app.fleet.landscape) + "/poll-now")
    post(app, _prefix(app.fleet.dev_a) + "/poll-now")
    post(app, "/poll-now")
    landscape, clone, live = app.calls
    assert landscape["profile"].key == hardware.SIM_LANDSCAPE_KEY
    assert clone["profile"].key == hardware.SIM_CLONE_KEY
    assert "profile" not in live
