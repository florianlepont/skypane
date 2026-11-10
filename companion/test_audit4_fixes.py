"""Served-page checks for fixes that need no browser: below-the-fold pictures,
the refused special look redrawn from its own address."""
import re
import urllib.parse

from companion_app_server import http_request, login


def _images(server, session, path):
    _status, _headers, body = http_request(server.base_url() + path, cookie=session)
    return re.findall(r"<img[^>]*>", body.decode("utf-8"))


def test_pictures_below_the_first_screen_are_lazy_async_sized_and_low_priority(make_app_server):
    server = make_app_server(fake_providers=True)
    session = login(server)
    checked = 0
    for path in ("/airlines", "/display/calendar", "/display/special-looks"):
        for tag in _images(server, session, path):
            if "layout-card__thumb" in tag:
                continue
            checked += 1
            assert 'loading="lazy"' in tag and 'decoding="async"' in tag, tag
            assert 'fetchpriority="low"' in tag, tag
            assert re.search(r'width="\d+"', tag) and re.search(r'height="\d+"', tag), tag
    assert checked > 10


def test_the_refused_key_query_only_carries_a_known_kind_and_look(make_app_server):
    server = make_app_server(fake_providers=True)
    session = login(server)
    query = urllib.parse.urlencode({
        "rule_refused": "1", "rule_kind": "<script>", "rule_theme_id": "nope",
        "rule_key": "x" * 500})
    _status, _headers, body = http_request(
        server.base_url() + "/display/special-looks/new?" + query, cookie=session)
    page = body.decode("utf-8")
    assert 'value="%s"' % ("x" * 80) in page and "x" * 81 not in page
    assert 'id="rule-key-error"' in page
    _status, _headers, body = http_request(
        server.base_url() + "/display/special-looks/new?rule_key=abc", cookie=session)
    assert b'id="rule-key-error"' not in body and b'value="abc"' not in body


def test_credits_offers_a_way_back_that_fits_who_is_looking(make_app_server):
    server = make_app_server(fake_providers=True)
    _status, _headers, anonymous = http_request(server.base_url() + "/credits")
    assert b">Back to sign in<" in anonymous and b'href="/login"' in anonymous
    session = login(server)
    _status, _headers, signed_in = http_request(server.base_url() + "/credits", cookie=session)
    assert b"Back to sign in" not in signed_in
    assert b">Back to Home<" in signed_in or b">Back to Account<" in signed_in


def test_the_flights_direction_chips_carry_a_label_and_no_count(make_app_server):
    import companion.test_view_pages_helpers as vp
    server = make_app_server(
        fake_providers=True,
        seed=lambda d: vp.seed_runway_events(d, [
            {"ts": "2026-09-03T10:%02d:00+00:00" % minute, "hex": "4c%04x" % minute,
             "callsign": "AFR%d" % (100 + minute), "airline": "Air France", "origin": "ORY",
             "destination": "NCE", "confirmed_state": state}
            for minute, state in ((1, "departing"), (2, "arriving"))]))
    session = login(server)
    _status, _headers, body = http_request(server.base_url() + "/flights", cookie=session)
    page = body.decode("utf-8")
    chips = re.findall(r'<span class="filter-chip__text">([^<]*)</span>', page)
    assert len(chips) == 3
    assert not any(re.search(r"\d", text) for text in chips), chips


def test_a_recorded_sign_in_means_the_person_is_active_not_invited():
    from companion.pages import users_page
    Row = users_page.UserRow
    base = dict.fromkeys(Row._fields)
    base.update(disabled=False, has_identity=False, last_seen=None)
    assert users_page.status_of(Row(**base)) == users_page.STATUS_INVITED
    base["last_seen"] = 1_700_000_000
    assert users_page.status_of(Row(**base)) == users_page.STATUS_ACTIVE
    base.update(last_seen=None, has_identity=True)
    assert users_page.status_of(Row(**base)) == users_page.STATUS_ACTIVE
