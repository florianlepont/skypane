#!/usr/bin/env python3
"""Behaviour checks for Home's statistics card builder: the Day and Week views as native
radios (no script), the per-hour timeline, the seven bars, the most seen airline, the
zero state, English and French, and escaping. Parsed from the markup, never read as source."""
import pytest

from companion import prefs
from companion.pages import home_stats
from companion_markup import parse_html

PARIS = "Europe/Paris"


def _timeline(ticks=(), arriving=0, departing=0):
    return {"day": "2026-09-03", "arriving": arriving, "departing": departing,
            "hours": [{"hour": h, "arriving": 0, "departing": 0} for h in range(24)],
            "ticks": [{"at": at, "state": state} for at, state in ticks]}


def _week(totals=(0, 0, 0, 0, 0, 0, 0)):
    days = ["2026-08-28", "2026-08-29", "2026-08-30", "2026-08-31",
            "2026-09-01", "2026-09-02", "2026-09-03"]
    return [{"day": d, "arriving": t // 2 + t % 2, "departing": t // 2, "total": t}
            for d, t in zip(days, totals)]


def _card(timeline=None, week=None, highlights=None, lang="en", **kwargs):
    prefs.set_request_prefs(lang=lang)
    try:
        return parse_html(home_stats.stats_card_html(
            timeline or _timeline(), week or _week(), highlights, **kwargs))
    finally:
        prefs.set_request_prefs()


def test_day_and_week_are_native_radios_with_both_panels_in_the_markup():
    """the switch is two radios with their labels (Day checked), so it works without script,
    and both panels are present for the stylesheet to show the checked one"""
    doc = _card()
    radios = doc.select("input")
    assert [(r.attrs["id"], r.attrs["value"]) for r in radios] == [
        ("home-stats-day", "day"), ("home-stats-week", "week")]
    assert "checked" in radios[0].attrs and "checked" not in radios[1].attrs
    assert [label.text() for label in doc.select("label")] == ["Day", "Week"]
    assert len(doc.select(".home-stats__panel--day")) == 1
    assert len(doc.select(".home-stats__panel--week")) == 1
    assert doc.select("script") == [] and doc.select("[style]") == []


def test_day_panel_shows_the_total_split_timeline_and_hours():
    doc = _card(
        _timeline(ticks=[(6.4, "departing"), (7.1, "arriving"), (7.5, "arriving")],
                  arriving=2, departing=1),
        quiet_windows=[(23.0, 6.0)], now_hour=14.5)
    panel = doc.select_one(".home-stats__panel--day")
    assert panel.select_one(".home-stats__big").text() == "3"
    assert panel.select_one(".home-stats__caption").text() == "flights today"
    assert panel.select_one(".home-stats__split").text() == "2 arrivals" "1 departure"
    assert len(panel.select(".home-stats__tick--departing")) == 1
    assert len(panel.select(".home-stats__tick--arriving")) == 2
    assert len(panel.select(".home-stats__quiet")) == 2
    assert float(panel.select_one(".home-stats__now").attrs["x"]) == pytest.approx(14.5 * 12 - 1)
    assert [s.text() for s in panel.select(".home-stats__hours span")] == [
        "0 h", "6 h", "12 h", "18 h", "24 h"]
    assert panel.select_one("svg").attrs["role"] == "img"


def test_departures_are_drawn_above_the_axis_and_arrivals_below_it():
    doc = _card(_timeline(ticks=[(8.0, "departing"), (9.0, "arriving")], arriving=1, departing=1))
    up = doc.select_one(".home-stats__tick--departing").attrs
    down = doc.select_one(".home-stats__tick--arriving").attrs
    assert float(up["y2"]) == 32 and float(up["y1"]) < 32
    assert float(down["y1"]) == 32 and float(down["y2"]) > 32
    assert "opacity" not in up and down["opacity"] == "0.55"


def test_week_panel_has_seven_bars_scaled_to_the_tallest_with_today_marked():
    doc = _card(week=_week((52, 38, 47, 58, 29, 31, 14)),
                highlights={"most_seen": {"airline": "Air France", "count": 41},
                            "new_airlines": ["A", "B"]})
    panel = doc.select_one(".home-stats__panel--week")
    cols = panel.select(".home-stats__bar-col")
    assert [c.select_one(".home-stats__value").text() for c in cols] == [
        "52", "38", "47", "58", "29", "31", "14"]
    heights = [int(c.select_one("svg").attrs["height"]) for c in cols]
    assert heights[3] == 60 and heights[6] == round(14 / 58 * 60)
    assert [c.attrs["class"].endswith("--today") for c in cols] == [False] * 6 + [True]
    assert [c.text()[-3:] for c in cols] == ["Fri", "Sat", "Sun", "Mon", "Tue", "Wed", "Thu"]
    assert panel.select_one(".home-stats__big").text() == "269"
    facts = panel.select_one(".home-stats__facts").text()
    assert "Air France" in facts and "most seen · 41" in facts
    assert "+2" in facts and "new airlines" in facts


def test_a_single_new_airline_is_singular_and_none_shows_no_new_fact():
    one = _card(highlights={"most_seen": {"airline": "Air France", "count": 3},
                            "new_airlines": ["A"]})
    assert "new airline" in one.select_one(".home-stats__facts").text()
    assert "new airlines" not in one.select_one(".home-stats__facts").text()
    none = _card(highlights={"most_seen": {"airline": "Air France", "count": 3},
                             "new_airlines": []})
    assert "+" not in none.select_one(".home-stats__facts").text()


def test_no_flight_at_all_is_the_card_at_zero_without_airline_facts():
    """an empty history zero-fills every hour and day: zero totals, flat bars, no facts"""
    doc = _card()
    assert [b.text() for b in doc.select(".home-stats__big")] == ["0", "0"]
    assert doc.select(".home-stats__tick--departing") == []
    heights = {c.select_one("svg").attrs["height"] for c in doc.select(".home-stats__bar-col")}
    assert len(doc.select(".home-stats__bar-col")) == 7 and heights == {"2"}
    assert doc.select(".home-stats__facts") == []


def test_card_in_french():
    doc = _card(
        _timeline(ticks=[(8.0, "arriving")], arriving=1), week=_week((0, 0, 0, 0, 0, 0, 1)),
        highlights={"most_seen": {"airline": "Air France", "count": 1}, "new_airlines": ["A"]},
        lang="fr")
    assert [label.text() for label in doc.select("label")] == ["Jour", "Semaine"]
    assert doc.select_one(".home-stats__caption").text() == "vol aujourd’hui"
    assert doc.select_one(".home-stats__split").text() == "1 arrivée" "0 départ"
    week = doc.select_one(".home-stats__panel--week")
    assert "la plus vue · 1" in week.select_one(".home-stats__facts").text()
    assert "nouvelle compagnie" in week.select_one(".home-stats__facts").text()
    assert [c.text()[-3:] for c in week.select(".home-stats__bar-col")][:2] == ["Ven", "Sam"]


def test_a_hostile_airline_name_is_escaped():
    hostile = '"><script>alert(1)</script>'
    html = home_stats.stats_card_html(
        _timeline(), _week(), {"most_seen": {"airline": hostile, "count": 1}, "new_airlines": []})
    assert "<script>" not in html and hostile not in html
    assert parse_html(html).select("script") == []
