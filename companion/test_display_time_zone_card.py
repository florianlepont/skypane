#!/usr/bin/env python3
"""Served Display markup: the Time zone select lives in the Location and detection card, the Quiet
hours card points to it, and the field keeps its name, form association and dirty section."""
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


def _cards(page):
    start = page.index('id="location-detection"')
    end = page.index("</section>", start)
    return page[start:end], page[end:]


def test_the_select_is_in_the_merged_card_only(app):
    _status, _, page = get(app, _prefix(app.fleet.dev_a) + "/display")
    card, rest = _cards(page)
    assert page.count('name="timezone"') == 1
    assert 'name="timezone"' in card
    assert 'form="settings-form"' in card[card.index('name="timezone"') - 80:]
    assert re.search(r'data-dirty-section="Time zone"[^>]*><label for="quiet-hours-timezone">', card)
    assert card.index("location-picker") < card.index('name="timezone"')
    assert card.index('name="timezone"') < card.index("detection-link")
    quiet = rest[rest.index('data-dirty-section="Quiet hours"'):]
    assert 'name="timezone"' not in quiet
    assert 'href="#location-detection">Location and detection</a>' in quiet
    assert "Quiet hours follow the time zone set in" in quiet


def test_french_note_and_dirty_section(app):
    cookie = "%s; %s=fr" % (app.cookie, auth.UI_LANG_COOKIE_NAME)
    status, _, body = http_request(
        app.server.base_url() + _prefix(app.fleet.dev_a) + "/display", cookie=cookie)
    assert status == 200
    page = body.decode("utf-8")
    assert 'data-dirty-section="Fuseau horaire"' in page
    assert "Les heures calmes suivent le fuseau horaire choisi dans" in page
    assert 'href="#location-detection">Lieu et détection</a>' in page
