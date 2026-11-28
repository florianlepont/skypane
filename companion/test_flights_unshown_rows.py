#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
"""A flight the poll cycle detected but dropped before it was drawn is stored
without a direction, a route or a picture. The Flights page lists it like any
other flight and the page does not fail on it.
"""
import pytest

import companion.test_view_pages_helpers as vp
from companion import prefs
from companion.pages import history_page
from companion_markup import parse_html


def _events():
    return [
        {"ts": "2026-11-15T10:36:05+00:00", "hex": "495155", "callsign": "TAP43JD",
         "airline": "TAP Air Portugal", "origin": "ORY", "destination": "LIS",
         "confirmed_state": "departing", "route_source": "fresh_hit", "gallery_name": "a.png"},
        {"ts": "2026-11-15T10:37:05+00:00", "hex": "39dd00", "callsign": "TVF87XA",
         "airline": "Transavia France", "origin": None, "destination": None,
         "confirmed_state": None, "route_source": "airline_only", "gallery_name": ""},
        {"ts": "2026-11-15T10:38:05+00:00", "hex": "0a0079", "callsign": None,
         "airline": None, "origin": None, "destination": None,
         "confirmed_state": None, "route_source": "miss", "gallery_name": ""},
    ]


@pytest.fixture(scope="module")
def state_dir(tmp_path_factory):
    path = tmp_path_factory.mktemp("flights_unshown")
    vp.seed_runway_events(path, _events())
    return path


def _doc(state_dir, lang="en"):
    prefs.set_request_prefs(lang=lang)
    try:
        return parse_html(history_page.render(vp.history_ctx(state_dir)))
    finally:
        prefs.set_request_prefs(lang="en")


@pytest.mark.parametrize("lang", ["en", "fr"])
def test_the_page_lists_a_flight_stored_without_a_direction_or_picture(state_dir, lang):
    text = _doc(state_dir, lang).text()
    assert "TAP43JD" in text
    assert "TVF87XA" in text


def test_a_flight_with_no_callsign_and_no_airline_does_not_break_the_page(state_dir):
    doc = _doc(state_dir)
    assert doc.select(".filter-chip")
