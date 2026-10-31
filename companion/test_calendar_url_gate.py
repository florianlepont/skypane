"""The combined settings form applies the same calendar-address gate as the
calendar sheet's connect route: a private or loopback link is refused at
save and never reaches `calendar_url.secret`, over the real handlers."""
import os
import urllib.parse

import pytest

from companion import i18n
from companion.layout import escape_html
from companion.settings import form_post
from companion.test_user_view_http import Rig
from provisioned_fleet import device_dir
from server.net import safe_fetch
from server.plane import calendar_rules
from server.plane.calendar_rules import registry as calendar_registry

PRIVATE_URLS = (
    "https://127.0.0.1/x.ics",
    "http://127.0.0.1/x.ics",
    "https://10.0.0.1/x.ics",
    "https://192.168.1.10/x.ics",
    "https://169.254.169.254/latest/x.ics",
    "https://localhost/x.ics",
    "webcal://127.0.0.1/x.ics",
)


@pytest.fixture
def rig(tmp_path, monkeypatch):
    def refuse(url, timeout):
        raise OSError("no outbound connection in this test")

    monkeypatch.setattr(calendar_rules, "default_calendar_transport", refuse)
    built = Rig(str(tmp_path / "state"))
    yield built
    built.stop()


def _secret(rig, device_id):
    return os.path.join(
        device_dir(rig.state_dir, device_id), calendar_registry.CALENDAR_SECRET_FILENAME)


def _form(**fields):
    return urllib.parse.urlencode(fields).encode()


@pytest.mark.parametrize("url", PRIVATE_URLS)
def test_the_prefixed_settings_form_refuses_a_private_calendar_url(rig, url):
    own = rig.fleet.a1
    status, _headers, body = rig.request(
        "POST", "/devices/%s/settings" % own, "a", data=_form(calendar_url=url))
    assert status == 200
    assert escape_html(i18n.t(form_post.ERROR_CALENDAR_URL_INVALID)) in body.decode("utf-8")
    assert not os.path.exists(_secret(rig, own))


@pytest.mark.parametrize("url", PRIVATE_URLS[:3])
def test_the_unprefixed_settings_form_refuses_a_private_calendar_url(rig, url):
    status, _headers, _body = rig.request(
        "POST", "/settings", "admin", data=_form(calendar_url=url))
    assert status == 200
    assert not os.path.exists(os.path.join(
        rig.state_dir, calendar_registry.CALENDAR_SECRET_FILENAME))


def test_a_refused_link_leaves_the_stored_link_and_the_rest_of_the_form_unsaved(rig):
    own = rig.fleet.a1
    original = "https://calendar.example/feed.ics"
    calendar_rules.save_calendar_url(device_dir(rig.state_dir, own), original)
    rig.request(
        "POST", "/devices/%s/settings" % own, "a",
        data=_form(calendar_url="https://10.0.0.1/x.ics", quiet_hours_start="20:00"))
    with open(_secret(rig, own)) as fh:
        assert fh.read().strip() == original


def test_an_acceptable_link_is_still_saved_by_the_settings_form(rig, monkeypatch):
    monkeypatch.setattr(safe_fetch, "host_is_safe", lambda host, port: host == "calendar.example")
    own = rig.fleet.a1
    url = "https://calendar.example/feed.ics"
    status, _headers, _body = rig.request(
        "POST", "/devices/%s/settings" % own, "a", data=_form(calendar_url=url))
    assert status == 303
    with open(_secret(rig, own)) as fh:
        assert fh.read().strip() == url
