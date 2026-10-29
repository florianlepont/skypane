"""Plain-request (no browser) tests for the Update page's Install/Cancel
POST flows: POST /update/install's two-step server-side confirmation
and POST /update/cancel's cancel-until-acknowledged
window, against a real companion/app.py subprocess -- never
source text (companion/test_suite_guards.py's behaviour-over-source
rule). companion/test_browser_update.py covers the JS confirm-dialog
and mobile-fit gate that need a real browser; this module proves every
outcome a plain client (no JavaScript) already gets.
"""
import hashlib
import json
import os
import urllib.parse

import pytest

import companion.auth as auth
import companion.i18n as i18n
import companion.layout as layout
import companion.prefs as prefs
from companion.pages import update_page
from companion_app_server import get, http_request, login
from companion_markup import flash_toast_title_detail
from server import atomic_io
from server import firmware_registry as fr
from skypane_fw_image import build_image

_NOW = "2026-09-28T12:00:00+00:00"

# Three published releases: fw-v1.0.0 (at the floor), fw-v1.1.0, and
# fw-v1.2.0 (the running version) -- so both fw-v1.0.0 and fw-v1.1.0 are
# installable downgrades, with no special-cased wording expected.
_RUNNING_VERSION = "fw-v1.2.0"
_DOWNGRADE_VERSION = "fw-v1.1.0"
_FLOOR_VERSION = "fw-v1.0.0"
_UNKNOWN_VERSION = "fw-v9.9.9"


def _seed_releases(state_dir):
    """Three published releases through firmware_registry's own write API,
    plus a hand-written device_report.json -- byos-owned in production,
    matching companion/test_update_page.py's own _seed_update_state().
    """
    os.makedirs(str(state_dir), exist_ok=True)
    for version in (_FLOOR_VERSION, _DOWNGRADE_VERSION, _RUNNING_VERSION):
        image_path = os.path.join(str(state_dir), version + ".bin")
        image_bytes = build_image(version)
        with open(image_path, "wb") as fh:
            fh.write(image_bytes)
        manifest = {
            "version": version, "sha256": hashlib.sha256(image_bytes).hexdigest(),
            "size": len(image_bytes), "released_at": _NOW, "commit": "a" * 40,
            "hardware_type": fr.hardware.LEGACY_KEY,
            "notes": ["release " + version],
        }
        fr.publish_release(str(state_dir), manifest, image_path, now=_NOW)
    device_report = {
        "schema": 1, "next_seq": 1,
        "devices": {
            "dev1": {"fw_version": _RUNNING_VERSION, "reported_at": _NOW, "events": []}},
    }
    atomic_io.atomic_write(fr.device_report_path(str(state_dir)), json.dumps(device_report))


def _mark_offered(state_dir, schedule_id):
    """Simulate byos having served the offer for `schedule_id`: an
    "offered" event, the same shape companion/test_update_page.py's own
    "in_progress" fixture uses -- acknowledged() then reads True.
    """
    report = fr.load_device_report(str(state_dir))
    report["devices"]["dev1"]["events"].append({
        "seq": report["next_seq"], "at": _NOW, "kind": "offered",
        "schedule_id": schedule_id, "token": None, "version": None,
    })
    report["next_seq"] += 1
    atomic_io.atomic_write(fr.device_report_path(str(state_dir)), json.dumps(report))


def _set_floor(state_dir, floor_version):
    registry = fr.load_registry(str(state_dir))
    registry["floor_version"] = floor_version
    fr._save_registry(str(state_dir), registry)


def _post(server, path, cookie, data=None):
    body = urllib.parse.urlencode(data or {}).encode()
    return http_request(
        server.base_url() + path, method="POST", data=body, cookie=cookie,
        extra_headers={"Origin": server.base_url()})


@pytest.fixture
def server(make_app_server):
    """A fresh, function-scoped server per test: every check here schedules
    or cancels a real update, mutating the registry, so tests must never
    share one server (companion/test_browser_update.py's module docstring
    documents the same rule for its own mutating checks).
    """
    return make_app_server(seed=_seed_releases)


@pytest.fixture
def cookie(server):
    return login(server)


# ==========================================================================
# POST /update/install: the no-confirm branch renders the server-side
# confirmation page without touching the registry.
# ==========================================================================


def test_install_without_confirm_renders_confirm_page_registry_unchanged(server, cookie):
    before = fr.load_registry(server.state_dir)["schedule"]
    status, _headers, body = _post(
        server, update_page.INSTALL_ROUTE, cookie, {"version": _DOWNGRADE_VERSION})
    assert status == 200
    text = body.decode("utf-8")
    assert (i18n.t(update_page.INSTALL_CONFIRM_HEADING_TEMPLATE) % _DOWNGRADE_VERSION) in text
    assert 'name="version" value="%s"' % _DOWNGRADE_VERSION in text
    assert 'name="confirm" value="yes"' in text
    assert fr.load_registry(server.state_dir)["schedule"] == before


def test_install_confirm_page_offers_a_plain_cancel_link_not_a_second_form(server, cookie):
    status, _headers, body = _post(
        server, update_page.INSTALL_ROUTE, cookie, {"version": _DOWNGRADE_VERSION})
    assert status == 200
    text = body.decode("utf-8")
    assert text.count('action="%s"' % update_page.INSTALL_ROUTE) == 1, (
        "expected exactly one form posting to %r" % (update_page.INSTALL_ROUTE,))
    assert '<a class="text-label" href="%s">' % layout.UPDATE_ROUTE in text


# ==========================================================================
# POST /update/install confirm=yes: the real schedule, including a
# voluntary downgrade rendered with no special-cased wording.
# ==========================================================================


def test_install_confirm_yes_schedules_and_get_shows_scheduled(server, cookie):
    status, headers, _body = _post(
        server, update_page.INSTALL_ROUTE, cookie,
        {"version": _DOWNGRADE_VERSION, "confirm": "yes"})
    assert status == 303
    assert headers.get("Location") == layout.UPDATE_ROUTE
    registry = fr.load_registry(server.state_dir)
    assert registry["schedule"]["state"] == "scheduled"
    assert registry["schedule"]["version"] == _DOWNGRADE_VERSION

    status, _headers, body = get(server, layout.UPDATE_ROUTE, cookie=cookie)
    assert status == 200
    text = body.decode("utf-8")
    assert i18n.t(update_page.STATE_LABELS["scheduled"]) in text
    assert 'action="%s"' % update_page.CANCEL_ROUTE in text


def test_install_confirm_yes_downgrade_reads_the_same_as_any_other_install(server, cookie):
    """fw-v1.1.0 is older than the running fw-v1.2.0 -- this is a
    first-class install, not a special "downgrade" flow: the confirm
    page and the scheduled outcome carry no extra wording.
    """
    status, _headers, body = _post(
        server, update_page.INSTALL_ROUTE, cookie, {"version": _DOWNGRADE_VERSION})
    assert status == 200
    text = body.decode("utf-8")
    assert "downgrade" not in text.lower()
    status, _headers, _body = _post(
        server, update_page.INSTALL_ROUTE, cookie,
        {"version": _DOWNGRADE_VERSION, "confirm": "yes"})
    assert status == 303
    registry = fr.load_registry(server.state_dir)
    assert registry["schedule"]["version"] == _DOWNGRADE_VERSION


# ==========================================================================
# POST /update/install confirm=yes: every rejection schedule_release()
# itself can return, plus an implausible version value, all flash the
# same generic failure and leave the registry untouched.
# ==========================================================================


@pytest.mark.parametrize("version", [_UNKNOWN_VERSION, ""], ids=["unknown", "empty"])
def test_install_confirm_yes_unknown_version_flashes_failure(server, cookie, version):
    before = fr.load_registry(server.state_dir)["schedule"]
    status, headers, _body = _post(
        server, update_page.INSTALL_ROUTE, cookie, {"version": version, "confirm": "yes"})
    assert status == 303
    assert headers.get("Location", "").startswith(layout.UPDATE_ROUTE + "?flash=")
    assert fr.load_registry(server.state_dir)["schedule"] == before


def test_install_confirm_yes_below_floor_flashes_failure(server, cookie):
    _set_floor(server.state_dir, _DOWNGRADE_VERSION)
    before = fr.load_registry(server.state_dir)["schedule"]
    status, headers, _body = _post(
        server, update_page.INSTALL_ROUTE, cookie,
        {"version": _FLOOR_VERSION, "confirm": "yes"})
    assert status == 303
    assert headers.get("Location", "").startswith(layout.UPDATE_ROUTE + "?flash=")
    assert fr.load_registry(server.state_dir)["schedule"] == before


def test_install_confirm_yes_same_as_running_flashes_failure(server, cookie):
    before = fr.load_registry(server.state_dir)["schedule"]
    status, headers, _body = _post(
        server, update_page.INSTALL_ROUTE, cookie,
        {"version": _RUNNING_VERSION, "confirm": "yes"})
    assert status == 303
    assert headers.get("Location", "").startswith(layout.UPDATE_ROUTE + "?flash=")
    assert fr.load_registry(server.state_dir)["schedule"] == before


def test_install_confirm_yes_while_busy_flashes_failure_original_schedule_unchanged(
        server, cookie):
    """Once a schedule has been acknowledged (the device started), a second
    Install must not silently replace it -- schedule_release()'s own
    "busy" outcome.
    """
    status, _headers, _body = _post(
        server, update_page.INSTALL_ROUTE, cookie,
        {"version": _DOWNGRADE_VERSION, "confirm": "yes"})
    assert status == 303
    schedule_id = fr.load_registry(server.state_dir)["schedule"]["id"]
    _mark_offered(server.state_dir, schedule_id)

    status, headers, _body = _post(
        server, update_page.INSTALL_ROUTE, cookie,
        {"version": _FLOOR_VERSION, "confirm": "yes"})
    assert status == 303
    location = headers.get("Location", "")
    assert location.startswith(layout.UPDATE_ROUTE + "?flash=")
    assert urllib.parse.unquote(location.split("flash=", 1)[1]) == update_page.FLASH_UPDATE_BUSY, (
        "expected the busy-specific flash key, not the generic schedule-failed one")
    registry = fr.load_registry(server.state_dir)
    assert registry["schedule"]["id"] == schedule_id
    assert registry["schedule"]["version"] == _DOWNGRADE_VERSION


@pytest.mark.parametrize(
    "hostile", ["<script>alert(1)</script>", "fw-v9999.9999.9999-" + "a" * 24],
    ids=["script-tag", "over-length"])
def test_install_implausible_version_treated_as_unknown_never_echoed(server, cookie, hostile):
    before = fr.load_registry(server.state_dir)["schedule"]
    status, headers, body = _post(
        server, update_page.INSTALL_ROUTE, cookie, {"version": hostile})
    assert status == 303
    # A 303 always carries Content-Length: 0 -- checking the empty body
    # proves nothing about what the handler did with the value. Check
    # what can actually carry it: the redirect target itself.
    assert hostile not in body.decode("utf-8", errors="replace")
    location = headers.get("Location", "")
    assert hostile not in location
    assert location == "%s?flash=%s" % (
        layout.UPDATE_ROUTE, urllib.parse.quote(update_page.FLASH_UPDATE_SCHEDULE_FAILED))
    assert fr.load_registry(server.state_dir)["schedule"] == before

    # Follow the redirect: neither the raw value nor its escaped form may
    # appear on the served page either.
    status, _headers, followed_body = get(server, location, cookie=cookie)
    assert status == 200
    followed_html = followed_body.decode("utf-8", errors="replace")
    assert hostile not in followed_html
    assert layout.escape_html(hostile) not in followed_html


# ==========================================================================
# POST /update/cancel: cancellable only until the device has acknowledged
# the offer.
# ==========================================================================


def test_cancel_with_no_offered_event_redirects_and_clears_schedule(server, cookie):
    _post(
        server, update_page.INSTALL_ROUTE, cookie,
        {"version": _DOWNGRADE_VERSION, "confirm": "yes"})
    status, headers, _body = _post(server, update_page.CANCEL_ROUTE, cookie)
    assert status == 303
    assert headers.get("Location") == layout.UPDATE_ROUTE
    assert fr.load_registry(server.state_dir)["schedule"] is None


def test_cancel_with_nothing_scheduled_is_a_no_op_redirect(server, cookie):
    status, headers, _body = _post(server, update_page.CANCEL_ROUTE, cookie)
    assert status == 303
    assert headers.get("Location") == layout.UPDATE_ROUTE
    assert fr.load_registry(server.state_dir)["schedule"] is None


def test_cancel_after_offered_event_flashes_failure_schedule_unchanged(server, cookie):
    _post(
        server, update_page.INSTALL_ROUTE, cookie,
        {"version": _DOWNGRADE_VERSION, "confirm": "yes"})
    schedule_id = fr.load_registry(server.state_dir)["schedule"]["id"]
    _mark_offered(server.state_dir, schedule_id)

    status, headers, _body = _post(server, update_page.CANCEL_ROUTE, cookie)
    assert status == 303
    assert headers.get("Location", "").startswith(layout.UPDATE_ROUTE + "?flash=")
    registry = fr.load_registry(server.state_dir)
    assert registry["schedule"]["id"] == schedule_id
    assert registry["schedule"]["state"] == "scheduled"


# ==========================================================================
# Both routes sit behind the session gate; cross-origin POST is already
# proven for every route (including these two) by
# companion/test_post_origin.py's own parametrized sweep.
# ==========================================================================


def test_both_routes_without_a_session_redirect_to_login(server):
    for path, data in (
            (update_page.INSTALL_ROUTE, {"version": _DOWNGRADE_VERSION}),
            (update_page.CANCEL_ROUTE, {})):
        status, headers, _body = _post(server, path, cookie=None, data=data)
        assert status == 303
        assert headers.get("Location", "").startswith("/login")
        assert fr.load_registry(server.state_dir)["schedule"] is None


# ==========================================================================
# French: the confirm page and both new flash messages.
# ==========================================================================


def test_confirm_page_renders_in_french(server, cookie):
    fr_cookie = cookie + "; %s=fr" % auth.UI_LANG_COOKIE_NAME
    status, _headers, body = _post(
        server, update_page.INSTALL_ROUTE, fr_cookie, {"version": _DOWNGRADE_VERSION})
    assert status == 200
    try:
        prefs.set_request_prefs(lang="fr")
        expected_heading = i18n.t(update_page.INSTALL_CONFIRM_HEADING_TEMPLATE) % _DOWNGRADE_VERSION
    finally:
        prefs.set_request_prefs(lang="en")
    assert expected_heading in body.decode("utf-8")


def test_confirm_page_shows_bench_note_for_a_bench_release(server, cookie):
    """POST /update/install (no confirm) against a real server shows the bench note when the
    posted version was published with bench=True, proving the handler's own registry lookup
    (not just the page module's own rendering) wires the flag through"""
    bench_version = "fw-v1.2.0-bench1"
    image_path = os.path.join(server.state_dir, bench_version + ".bin")
    image_bytes = build_image(bench_version)
    with open(image_path, "wb") as fh:
        fh.write(image_bytes)
    manifest = {
        "version": bench_version, "sha256": hashlib.sha256(image_bytes).hexdigest(),
        "size": len(image_bytes), "released_at": _NOW, "commit": "a" * 40, "notes": [],
        "hardware_type": fr.hardware.LEGACY_KEY,
    }
    fr.publish_release(server.state_dir, manifest, image_path, bench=True, now=_NOW)

    status, _headers, body = _post(
        server, update_page.INSTALL_ROUTE, cookie, {"version": bench_version})
    assert status == 200
    assert i18n.t(update_page.BENCH_CONFIRM_NOTE_TEXT) in body.decode("utf-8")

    status, _headers, body = _post(
        server, update_page.INSTALL_ROUTE, cookie, {"version": _DOWNGRADE_VERSION})
    assert status == 200
    assert i18n.t(update_page.BENCH_CONFIRM_NOTE_TEXT) not in body.decode("utf-8")


def test_schedule_failed_flash_renders_in_french(server, cookie):
    fr_cookie = cookie + "; %s=fr" % auth.UI_LANG_COOKIE_NAME
    status, headers, _body = _post(
        server, update_page.INSTALL_ROUTE, fr_cookie,
        {"version": _UNKNOWN_VERSION, "confirm": "yes"})
    assert status == 303
    location = headers["Location"]
    status, _headers, body = get(server, location, cookie=fr_cookie)
    assert status == 200
    try:
        prefs.set_request_prefs(lang="fr")
        expected_flash = i18n.t(update_page.FLASH_UPDATE_SCHEDULE_FAILED_TEXT)
    finally:
        prefs.set_request_prefs(lang="en")
    assert flash_toast_title_detail(body.decode("utf-8")) == (
        layout.split_toast_message(expected_flash))


# ==========================================================================
# Per-hardware-type scheduling: a type chooser appears only when more than
# one type is relevant, and every action is scoped to the chosen type.
# ==========================================================================

_LEGACY = fr.hardware.LEGACY_KEY
_OTHER = fr.hardware.SIM_CLONE_KEY
_OTHER_RUNNING = "fw-v1.4.0"
_OTHER_ROLLBACK = "fw-v1.3.0"
_SIM_ENV = {fr.hardware.SIM_ENV_VAR: "1"}


def _seed_two_types(state_dir):
    """The legacy fixture plus a second type with its own releases and its
    own running device, written straight into that type's registry."""
    _seed_releases(state_dir)
    registry = fr.load_registry(state_dir, _OTHER)
    registry["releases"] = [
        {
            "version": version, "sha256": hashlib.sha256(("other" + version).encode()).hexdigest(),
            "size": 10, "released_at": _NOW, "published_at": _NOW,
            "commit": "b" * 40, "notes": ["other " + version], "bench": False,
            "installed_at": [],
        }
        for version in (_FLOOR_VERSION, _OTHER_ROLLBACK, _OTHER_RUNNING)]
    fr._save_registry(state_dir, registry, _OTHER)
    report = fr.load_device_report(state_dir)
    report["devices"]["dev2"] = {
        "fw_version": _OTHER_RUNNING, "reported_at": _NOW, "events": [],
        "hardware_type": _OTHER}
    atomic_io.atomic_write(fr.device_report_path(state_dir), json.dumps(report))


@pytest.fixture
def two_type_server(make_app_server, monkeypatch):
    # The seeding below runs in this process, where the second type is
    # only usable while the simulation gate is on.
    monkeypatch.setenv(fr.hardware.SIM_ENV_VAR, "1")
    return make_app_server(seed=_seed_two_types, env_overrides=_SIM_ENV)


@pytest.fixture
def two_type_cookie(two_type_server):
    return login(two_type_server)


def _type_buttons(html):
    from companion_markup import parse_html
    return [
        (button.attrs["value"], button.attrs["aria-pressed"], button.text())
        for button in parse_html(html).select('form[method="get"] button[name="type"]')]


def _hidden_types(html):
    from companion_markup import parse_html
    return [node.attrs["value"] for node in
            parse_html(html).select('input[name="hardware_type"]')]


def test_one_relevant_type_shows_no_chooser_and_no_type_field(server, cookie):
    status, _headers, body = get(server, layout.UPDATE_ROUTE, cookie=cookie)
    assert status == 200
    html = body.decode("utf-8")
    assert _type_buttons(html) == []
    assert _hidden_types(html) == []
    assert "hardware_type" not in html
    status, _headers, other = get(
        server, layout.UPDATE_ROUTE + "?type=" + _OTHER, cookie=cookie)
    assert status == 200
    assert _type_buttons(other.decode("utf-8")) == []


def test_chooser_lists_each_relevant_type_and_defaults_to_legacy(
        two_type_server, two_type_cookie):
    status, _headers, body = get(two_type_server, layout.UPDATE_ROUTE, cookie=two_type_cookie)
    assert status == 200
    html = body.decode("utf-8")
    labels = {key: fr.hardware.get_profile(key, _SIM_ENV).label for key in (_LEGACY, _OTHER)}
    assert _type_buttons(html) == [
        (_LEGACY, "true", labels[_LEGACY]), (_OTHER, "false", labels[_OTHER])]
    assert _RUNNING_VERSION in html
    assert _OTHER_RUNNING not in html
    assert set(_hidden_types(html)) == {_LEGACY}


def test_other_type_page_shows_only_that_types_releases_and_schedule(
        two_type_server, two_type_cookie):
    fr.schedule_release(
        two_type_server.state_dir, _OTHER_ROLLBACK, _OTHER_RUNNING, _NOW, hardware_type=_OTHER)
    status, _headers, body = get(
        two_type_server, layout.UPDATE_ROUTE + "?type=" + _OTHER, cookie=two_type_cookie)
    html = body.decode("utf-8")
    assert status == 200
    assert _OTHER_ROLLBACK in html and _OTHER_RUNNING in html
    assert _DOWNGRADE_VERSION not in html
    assert i18n.t(update_page.STATE_LABELS["scheduled"]) in html
    assert 'action="%s"' % update_page.CANCEL_ROUTE in html
    assert set(_hidden_types(html)) == {_OTHER}
    _status, _headers, legacy = get(two_type_server, layout.UPDATE_ROUTE, cookie=two_type_cookie)
    assert 'action="%s"' % update_page.CANCEL_ROUTE not in legacy.decode("utf-8")


def test_unknown_or_malformed_query_type_falls_back_to_legacy(two_type_server, two_type_cookie):
    for value in ("nope", "../x", "", _OTHER + "x"):
        status, _headers, body = get(
            two_type_server, layout.UPDATE_ROUTE + "?type=" + urllib.parse.quote(value),
            cookie=two_type_cookie)
        assert status == 200
        assert _RUNNING_VERSION in body.decode("utf-8"), value


def test_install_in_the_other_type_leaves_the_legacy_schedule_alone(
        two_type_server, two_type_cookie):
    status, headers, _body = _post(
        two_type_server, update_page.INSTALL_ROUTE, two_type_cookie,
        {"version": _OTHER_ROLLBACK, "hardware_type": _OTHER, "confirm": "yes"})
    assert status == 303
    assert "type=" + _OTHER in headers["Location"]
    state_dir = two_type_server.state_dir
    assert fr.load_registry(state_dir, _OTHER)["schedule"]["version"] == _OTHER_ROLLBACK
    assert fr.load_registry(state_dir)["schedule"] is None
    status, headers, _body = _post(
        two_type_server, update_page.CANCEL_ROUTE, two_type_cookie, {"hardware_type": _OTHER})
    assert status == 303
    assert fr.load_registry(state_dir, _OTHER)["schedule"] is None


def test_cancel_in_one_type_keeps_the_other_types_schedule(two_type_server, two_type_cookie):
    state_dir = two_type_server.state_dir
    fr.schedule_release(state_dir, _DOWNGRADE_VERSION, _RUNNING_VERSION, _NOW)
    fr.schedule_release(state_dir, _OTHER_ROLLBACK, _OTHER_RUNNING, _NOW, hardware_type=_OTHER)
    _post(two_type_server, update_page.CANCEL_ROUTE, two_type_cookie, {"hardware_type": _OTHER})
    assert fr.load_registry(state_dir, _OTHER)["schedule"] is None
    assert fr.load_registry(state_dir)["schedule"]["version"] == _DOWNGRADE_VERSION


def test_post_without_a_type_field_means_legacy(two_type_server, two_type_cookie):
    state_dir = two_type_server.state_dir
    _post(two_type_server, update_page.INSTALL_ROUTE, two_type_cookie,
          {"version": _DOWNGRADE_VERSION, "confirm": "yes"})
    assert fr.load_registry(state_dir)["schedule"]["version"] == _DOWNGRADE_VERSION
    assert fr.load_registry(state_dir, _OTHER)["schedule"] is None


@pytest.mark.parametrize("hostile", [
    "nope", "../../etc", "", _OTHER + "/../x", "A" * 500, "sim-ee02-landscape%00"])
def test_post_with_an_invalid_type_is_rejected_and_changes_nothing(
        two_type_server, two_type_cookie, hostile):
    state_dir = two_type_server.state_dir
    for route, data in (
            (update_page.INSTALL_ROUTE,
             {"version": _DOWNGRADE_VERSION, "confirm": "yes", "hardware_type": hostile}),
            (update_page.INSTALL_ROUTE, {"version": _DOWNGRADE_VERSION, "hardware_type": hostile}),
            (update_page.CANCEL_ROUTE, {"hardware_type": hostile})):
        status, headers, body = _post(two_type_server, route, two_type_cookie, data)
        assert status == 303, (route, hostile)
        assert "flash=" in headers["Location"]
        assert hostile.strip() == "" or urllib.parse.quote(hostile) not in headers["Location"]
    assert fr.load_registry(state_dir)["schedule"] is None
    assert fr.load_registry(state_dir, _OTHER)["schedule"] is None


def test_an_unavailable_type_is_rejected_without_the_simulation_gate(server, cookie):
    status, headers, _body = _post(
        server, update_page.INSTALL_ROUTE, cookie,
        {"version": _DOWNGRADE_VERSION, "confirm": "yes", "hardware_type": _OTHER})
    assert status == 303
    assert "flash=" in headers["Location"]
    assert fr.load_registry(server.state_dir)["schedule"] is None


def test_confirm_page_names_the_type_and_carries_it_only_with_the_chooser(
        two_type_server, two_type_cookie, server, cookie):
    status, _headers, body = _post(
        two_type_server, update_page.INSTALL_ROUTE, two_type_cookie,
        {"version": _OTHER_ROLLBACK, "hardware_type": _OTHER})
    html = body.decode("utf-8")
    assert status == 200
    assert _hidden_types(html) == [_OTHER]
    assert fr.hardware.get_profile(_OTHER, _SIM_ENV).label in html
    _status, _headers, one_type = _post(
        server, update_page.INSTALL_ROUTE, cookie, {"version": _DOWNGRADE_VERSION})
    assert _hidden_types(one_type.decode("utf-8")) == []


def test_older_release_above_the_floor_can_be_scheduled_in_each_type(
        two_type_server, two_type_cookie):
    state_dir = two_type_server.state_dir
    _post(two_type_server, update_page.INSTALL_ROUTE, two_type_cookie,
          {"version": _DOWNGRADE_VERSION, "confirm": "yes"})
    _post(two_type_server, update_page.INSTALL_ROUTE, two_type_cookie,
          {"version": _OTHER_ROLLBACK, "hardware_type": _OTHER, "confirm": "yes"})
    assert fr.load_registry(state_dir)["schedule"]["version"] == _DOWNGRADE_VERSION
    assert fr.load_registry(state_dir, _OTHER)["schedule"]["version"] == _OTHER_ROLLBACK


def test_chooser_renders_in_french(two_type_server, two_type_cookie):
    fr_cookie = two_type_cookie + "; %s=fr" % auth.UI_LANG_COOKIE_NAME
    status, _headers, body = get(two_type_server, layout.UPDATE_ROUTE, cookie=fr_cookie)
    html = body.decode("utf-8")
    assert status == 200
    assert "Hardware type" not in html
    assert "Type de matériel" in html
