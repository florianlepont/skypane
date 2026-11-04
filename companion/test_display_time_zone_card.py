#!/usr/bin/env python3
"""Served Display markup: there is no Time zone select; the Quiet hours card keeps its controls and
says its hours follow the time zone, linking to the Location and detection page's details card."""
import re

import pytest

from companion import auth
from companion.test_device_helpers import get, start_fleet_app
from companion_app_server import http_request


@pytest.fixture
def app(make_app_server):
    return start_fleet_app(make_app_server)


def _prefix(device):
    return "/devices/%s" % device.id


def _quiet_card(page):
    return page[page.index('data-dirty-section="Quiet hours"'):]


def test_display_has_no_time_zone_select_and_links_to_the_details_card(app):
    prefix = _prefix(app.fleet.dev_a)
    _status, _, page = get(app, prefix + "/display")
    assert 'name="timezone"' not in page and 'id="quiet-hours-timezone"' not in page
    assert "Time zone" not in re.findall(r'data-dirty-section="([^"]*)"', page)
    quiet = _quiet_card(page)
    assert 'name="quiet_hours_start"' in quiet and 'name="quiet_hours_end"' in quiet
    assert 'href="%s/detection#details">Location and detection</a>' % prefix in quiet
    assert "Quiet hours follow the time zone set in" in quiet


def test_the_location_page_carries_the_time_zone_select(app):
    _status, _, page = get(app, _prefix(app.fleet.dev_a) + "/detection")
    assert page.count('name="timezone"') == 1
    assert 'id="details"' in page


def test_french_note(app):
    prefix = _prefix(app.fleet.dev_a)
    cookie = "%s; %s=fr" % (app.cookie, auth.UI_LANG_COOKIE_NAME)
    status, _, body = http_request(app.server.base_url() + prefix + "/display", cookie=cookie)
    assert status == 200
    page = body.decode("utf-8")
    assert 'name="timezone"' not in page
    assert "Les heures calmes suivent le fuseau horaire choisi dans" in page
    assert 'href="%s/detection#details">Lieu et détection</a>' % prefix in page
