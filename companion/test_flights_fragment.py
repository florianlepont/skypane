"""The Flights list as a bare fragment, over real HTTP: a search, a chip or a sort is answered
with the list only (no page shell), and Load more with the next flights only, so neither
downloads again what the page already shows. The plain page addresses are unchanged."""
import re

import pytest

import companion.test_view_pages_helpers as vp
from companion.pages import history_page
from companion_app_server import http_request, session_cookie_for_state_dir

LIMIT = history_page.HISTORY_ROW_LIMIT
TOTAL = 2 * LIMIT + 20
_CARD_ID = re.compile(r'<li[^>]*class="[^"]*history-card[^"]*"[^>]*data-flight-id="([^"]+)"')
_ROW_ID = re.compile(r'<tr[^>]*data-flight-row[^>]*data-flight-id="([^"]+)"')


def _seed(state_dir):
    """TOTAL departures five minutes apart over one evening and the next morning (two Paris
    days), alternating two airlines."""
    vp.seed_runway_events(state_dir, [
        {"ts": "2026-09-0%dT%02d:%02d:00+00:00" % (3 + n // 100, 10 + (n % 100) // 12,
                                                    (n % 100) % 12 * 5),
         "hex": "4c%04x" % n, "callsign": "%s%d" % (("AFR", "TVF")[n % 2], 100 + n),
         "airline": ("Air France", "Transavia France")[n % 2], "origin": "ORY",
         "destination": "NCE", "confirmed_state": ("departing", "arriving")[n % 3 == 0]}
        for n in range(TOTAL)])


@pytest.fixture(scope="module")
def rig(module_app_server_factory):
    server = module_app_server_factory(seed=_seed, fake_providers=True)
    return server, session_cookie_for_state_dir(server.state_dir)


def _get(rig, path):
    server, cookie = rig
    status, headers, body = http_request(server.base_url() + path, cookie=cookie)
    if status in (301, 302, 303):
        status, headers, body = http_request(
            server.base_url() + headers["Location"], cookie=cookie)
    return status, headers, body.decode("utf-8")


def _flights_path(rig):
    """The frame's own Flights address (the bare route redirects to it)."""
    server, cookie = rig
    _status, headers, _body = http_request(server.base_url() + "/flights", cookie=cookie)
    return headers.get("Location", "/flights").partition("?")[0]


def _ids(markup):
    return _CARD_ID.findall(markup), _ROW_ID.findall(markup)


@pytest.mark.parametrize("query", ["", "q=tvf", "kind=arriving", "sort=oldest", "sort=airline",
                                   "q=afr&kind=departing&sort=direction"])
def test_the_list_fragment_holds_the_same_list_as_the_page_without_the_shell(rig, query):
    base = _flights_path(rig)
    _s, _h, page = _get(rig, base + ("?" + query if query else ""))
    status, headers, part = _get(rig, base + "?" + (query + "&" if query else "") + "part=list")
    assert status == 200 and headers["Content-Type"].startswith("text/html")
    assert "no-store" in headers["Cache-Control"]
    assert _ids(part) == _ids(page) and _ids(part)[0], "the fragment lists other flights"
    for shell in ("<html", "<head", "tab-bar", "icon-defs", "<script", "data-flights-form"):
        assert shell not in part, shell
    # The whole run the script swaps is there: the chips, both lists and Load more.
    assert part.count("data-flights-view") == page.count("data-flights-view")
    assert "part=" not in part, "the fragment's own links must stay plain page addresses"
    assert len(part) < 0.9 * len(page)


def test_a_search_with_no_match_answers_the_empty_card_as_a_fragment(rig):
    base = _flights_path(rig)
    _s, _h, part = _get(rig, base + "?q=zzzz&part=list")
    assert "data-flights-empty" in part and "<html" not in part
    assert _ids(part) == ([], [])


@pytest.mark.parametrize("query", ["", "sort=oldest", "sort=airline", "kind=departing"])
@pytest.mark.parametrize("pages", [1, 2])
def test_the_new_fragment_holds_only_the_next_flights(rig, query, pages):
    """`part=new` answers the flights of the last Load more step, led by the last flight already
    shown (the script finds its group by it), with the Load more block the full page has."""
    base = _flights_path(rig)
    prefix = base + "?" + (query + "&" if query else "")
    _s, _h, page = _get(rig, prefix + "more=%d" % pages)
    status, _h, part = _get(rig, prefix + "more=%d&part=new" % pages)
    assert status == 200 and "<html" not in part
    cards, rows = _ids(page)
    start = pages * LIMIT - 1
    if len(cards) <= start + 1:
        # Nothing lies beyond what the step before showed: the script loads the plain page.
        assert part == ""
        return
    assert _ids(part) == (cards[start:], rows[start:])
    assert len(_ids(part)[0]) <= LIMIT + 1
    assert ("data-history-more" in part) == ("data-history-more" in page)
    more = re.search(r'<div class="history-more".*?</div>', page, re.S)
    if more:
        assert more.group(0) in part, "the Load more block differs from the page's"
    # The row the no-script link lands on keeps its anchor, and no group id repeats one of
    # the groups the page already shows.
    assert part.count('id="flights-new-card"') == 1 and part.count('id="flights-new"') == 1
    shown_groups = set(re.findall(r'id="(history-day-\d+)"', _get(
        rig, prefix + ("more=%d" % (pages - 1) if pages > 1 else "x=1"))[2]))
    new_groups = re.findall(r'id="(history-day-\d+)"', part)
    assert len(new_groups) == len(set(new_groups))
    assert not shown_groups.intersection(new_groups[1:]), (shown_groups, new_groups)
    assert len(part) < 0.6 * len(page)


def test_ten_load_more_steps_download_a_constant_amount_each(rig):
    """each step weighs about the same, instead of the whole list again"""
    base = _flights_path(rig)
    first = len(_get(rig, base + "?more=1&part=new")[2])
    second = len(_get(rig, base + "?more=2&part=new")[2])
    whole = len(_get(rig, base + "?more=2")[2])
    assert second <= first * 1.1 and first + second < whole


def test_an_unknown_part_is_the_plain_page(rig):
    base = _flights_path(rig)
    _s, _h, page = _get(rig, base + "?part=everything")
    assert "<html" in page and "data-flights-form" in page


def test_the_fragment_is_refused_without_a_session(rig):
    server, _cookie = rig
    status, headers, _body = http_request(server.base_url() + _flights_path(rig) + "?part=list")
    assert status == 303 and headers["Location"].startswith("/login")


def test_the_fragment_of_another_persons_frame_is_not_served(rig):
    server, _cookie = rig
    stranger = session_cookie_for_state_dir(
        server.state_dir, email="stranger@example.test", role="user")
    status, _headers, body = http_request(
        server.base_url() + _flights_path(rig) + "?part=list", cookie=stranger)
    assert status in (303, 404) and b"history-card" not in body
