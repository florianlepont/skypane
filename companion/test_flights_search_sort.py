#!/usr/bin/env python3
"""Behaviour checks of the Flights page's server-side view, read from the markup `render()`
produces: the search covers the whole history (an old call sign beyond the first page is
found, with the number of matches), the direction chips count the whole history under the
search, a search or direction that matches nothing shows the empty card with no table header,
no count line to load more from and no Load more, the sort orders the list and rides along in
every link, and Load more lands on the first new row in both the phone list and the table.
"""
import pytest

import companion.test_view_pages_helpers as vp
from companion import history_query, prefs
from companion.pages import history_page
from companion_markup import parse_html

LIMIT = history_page.HISTORY_ROW_LIMIT
TOTAL = LIMIT + 14
OLD_CALLSIGN = "OLDONE1"


def _events():
    """TOTAL flights, one a minute (newest last seeded), alternating departures and arrivals;
    the oldest of them is OLD_CALLSIGN, past the first page."""
    events = []
    for index in range(TOTAL):
        events.append({
            "ts": "2026-09-03T%02d:%02d:00+00:00" % (10 + index // 60, index % 60),
            "hex": "4b%04x" % index, "callsign": "AFR%03d" % index,
            "airline": "Air France" if index % 2 else "Transavia France",
            "origin": "ORY" if index % 2 == 0 else "NCE",
            "destination": "NCE" if index % 2 == 0 else "ORY",
            "confirmed_state": "departing" if index % 2 == 0 else "arriving"})
    events.append({
        "ts": "2026-08-01T08:00:00+00:00", "hex": "aa0001", "callsign": OLD_CALLSIGN,
        "airline": "Iberia", "origin": "MAD", "destination": "ORY",
        "confirmed_state": "arriving"})
    return events


@pytest.fixture(scope="module")
def state_dir(tmp_path_factory):
    path = tmp_path_factory.mktemp("flights_search")
    vp.seed_runway_events(path, _events())
    return path


def _doc(state_dir, query=None, more=None, lang="en"):
    prefs.set_request_prefs(lang=lang)
    try:
        return parse_html(history_page.render(
            vp.history_ctx(state_dir, history_query=query, history_more=more)))
    finally:
        prefs.set_request_prefs(lang="en")


def _chips(doc):
    return {
        c.attrs["value"] or "all": c.parent.select_one(".filter-chip__count").text()
        for c in doc.select("input") if c.attrs.get("name") == "kind"}


def _callsigns(doc):
    return [li.select_one(".history-card__callsign").text() for li in doc.select("li.history-card")]


def test_an_old_call_sign_beyond_the_first_page_is_found(state_dir):
    """the first page holds LIMIT flights and not the oldest one, yet searching its call sign
    lists it, says one flight matches and counts it under its direction"""
    plain = _doc(state_dir)
    assert len(plain.select("li.history-card")) == LIMIT
    assert OLD_CALLSIGN not in _callsigns(plain)
    found = _doc(state_dir, {"q": "oldone1"})
    assert _callsigns(found) == [OLD_CALLSIGN]
    assert found.select_one("[data-filter-count]").text() == "1 flight matches"
    assert _chips(found) == {"all": "1", "departing": "0", "arriving": "1"}
    assert not found.select(".history-more")


def test_the_search_covers_airline_airport_and_aircraft_words(state_dir):
    """every word of the search must match the flight's own words: airline as displayed and
    airport code, here narrowing the page to Iberia's one flight"""
    doc = _doc(state_dir, {"q": "iberia mad"})
    assert _callsigns(doc) == [OLD_CALLSIGN]
    assert _callsigns(_doc(state_dir, {"q": "iberia nce"})) == []


def test_the_chips_count_the_whole_history_under_the_search(state_dir):
    """without a search the chips count every stored flight, not the rows a page shows; a
    chosen direction filters the list but leaves the counts of the search alone"""
    assert _chips(_doc(state_dir)) == {
        "all": str(TOTAL + 1), "departing": str(TOTAL // 2),
        "arriving": str(TOTAL - TOTAL // 2 + 1)}
    doc = _doc(state_dir, {"kind": "departing"})
    assert _chips(doc) == _chips(_doc(state_dir))
    assert [n.attrs["value"] or "all" for n in doc.select("input")
            if n.attrs.get("name") == "kind" and "checked" in n.attrs] == ["departing"]
    assert all("Transavia" in li.select_one(".history-card__airline").text()
               for li in doc.select("li.history-card"))


def test_a_search_with_no_match_shows_only_the_empty_card(state_dir):
    """no table, no table header, no day groups, no Load more and no shown-count line under
    the card; the chips show the whole history's counts (never 0 / 0 / 0), the body quotes it and the
    Clear link is a plain address keeping the sort"""
    doc = _doc(state_dir, {"q": "zzzz", "sort": "airline"})
    assert not doc.select("table") and not doc.select("thead") and not doc.select("th")
    assert not doc.select("li.history-card") and not doc.select(".history-more")
    card = doc.select_one("[data-flights-empty]")
    assert card.select_one(".empty-state__heading").text() == "No matching flights"
    assert "all %d flights" % (TOTAL + 1) in card.select_one(".empty-state__body").text()
    clear = card.select_one("a")
    assert clear.text() == "Clear" and clear.attrs["href"] == "/flights?sort=airline"
    chips = _chips(doc)
    assert chips["all"] == str(TOTAL + 1) and chips["departing"] != "0" and chips["arriving"] != "0"
    assert doc.select_one("[data-filter-count]").text() == "No flight matches"


def test_a_direction_with_no_flights_shows_the_empty_card_in_french(tmp_path):
    """a history of departures only, asked for arrivals: the empty card in French, the chips
    still counting what exists, and no table header"""
    vp.seed_runway_events(tmp_path, [
        {"ts": "2026-09-03T10:00:00+00:00", "hex": "d1", "callsign": "D1",
         "confirmed_state": "departing"}])
    doc = _doc(tmp_path, {"kind": "arriving"}, lang="fr")
    assert doc.select_one("[data-flights-empty] .empty-state__heading").text() == (
        "Aucun vol correspondant")
    assert doc.select_one("[data-flights-empty] a").text() == "Effacer"
    assert not doc.select("thead") and not doc.select(".history-more")
    assert _chips(doc) == {"all": "1", "departing": "1", "arriving": "0"}


def test_an_empty_history_has_no_controls_at_all(tmp_path):
    """a history with no flights shows the plain "no flights yet" card: no search, no chips,
    no sort"""
    doc = _doc(tmp_path)
    assert "No flights yet." in doc.text()
    assert not doc.select("form") and not doc.select("select")
    assert not doc.select(".filter-chip") and not doc.select("[data-flights-empty]")


@pytest.mark.parametrize("sort,first,last", [
    ("newest", "AFR%03d" % (TOTAL - 1), None),
    ("oldest", OLD_CALLSIGN, None),
])
def test_the_date_sorts_order_the_list_by_time(state_dir, sort, first, last):
    """newest first starts with the latest flight, oldest first with the oldest, both keeping
    their day groups and the clock-only values"""
    doc = _doc(state_dir, {"sort": sort}, more=str(TOTAL // LIMIT))
    assert _callsigns(doc)[0] == first
    assert doc.select(".history-cards h2.section-label")
    assert doc.select("tr.flight-day-row")


def test_the_airline_sort_groups_by_airline_name(state_dir):
    """sorted by airline the names run alphabetically in one group per airline, each named by it,
    each row dates itself and the table has no day separator"""
    doc = _doc(state_dir, {"sort": "airline"}, more=str(TOTAL // LIMIT))
    names = [li.select_one(".history-card__airline").text() for li in doc.select("li.history-card")]
    assert names == sorted(names, key=str.casefold)
    assert names[0] == "Air France" and names[-1] == "Transavia France"
    groups = doc.select(".history-cards > section")
    titles = [group.select_one("h2").text() for group in groups]
    assert titles == sorted(set(names), key=str.casefold) and "Airline" not in titles
    for group in groups:
        assert {li.select_one(".history-card__airline").text()
                for li in group.select("li.history-card")} == {group.select_one("h2").text()}
    assert not doc.select("tr.flight-day-row")
    assert "3 Sep" in doc.select_one("li.history-card .history-card__when").text()


def test_the_direction_sort_lists_departures_before_arrivals(state_dir):
    """sorted by direction every departure precedes every arrival"""
    doc = _doc(state_dir, {"sort": "direction"}, more=str(TOTAL // LIMIT))
    kinds = [li.attrs["data-filter-kind"] for li in doc.select("li.history-card")]
    assert kinds == sorted(kinds, key=["departing", "arriving"].index)


def test_an_unknown_sort_or_direction_falls_back_to_the_defaults(state_dir):
    """a hand-edited ?sort= or ?kind= is the default view; the text is trimmed and capped"""
    doc = _doc(state_dir, {"sort": "bogus", "kind": "sideways", "q": "  "})
    assert len(doc.select("li.history-card")) == LIMIT
    assert history_query.parse_view({"q": "x" * 200}).q == "x" * history_query.QUERY_MAX_CHARS


def test_load_more_keeps_the_view_and_lands_on_the_first_new_row_on_both_lists(state_dir):
    """the Load more links carry the search and the sort; one is for the
    phone list (its anchor on the first new card) and one for the table (its anchor on the
    first new table row), and each anchor exists exactly once in the page"""
    query = {"q": "afr", "sort": "oldest"}
    first = _doc(state_dir, query)
    links = first.select("a[data-flights-more]")
    assert len(links) == 2
    expected = "/flights?q=afr&sort=oldest&more=1"
    assert sorted(a.attrs["href"] for a in links) == [
        expected + "#flights-new", expected + "#flights-new-card"]
    assert first.select_one(".history-more__count").text() == "%d flights shown" % LIMIT
    second = _doc(state_dir, query, more="1")
    cards = second.select("li.history-card")
    anchored_card = second.select("li#flights-new-card")
    anchored_row = second.select("tr#flights-new")
    assert len(anchored_card) == 1 and len(anchored_row) == 1
    assert cards.index(anchored_card[0]) == LIMIT
    rows = second.select("tr[data-flight-row]")
    assert rows.index(anchored_row[0]) == LIMIT
    assert not first.select("#flights-new") and not first.select("#flights-new-card")
