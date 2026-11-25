"""Real-browser checks that the "Missing illustrations" label is a sibling of the other two labels of
the Editor: the same size, weight and colour as the "Airlines" label at 390 and 1280 px in light and
dark, and the section sits between the unidentified table and the airlines table, in the markup and
on the screen."""
from datetime import datetime, timedelta, timezone

import animation_settle
import pytest

from companion import auth
from companion.test_browser_airline_helpers import seed_airline_editor
from companion.test_browser_ux_helpers import _login
from server import history_db

pytestmark = pytest.mark.browser

SECTION = "#airlines-missing"
SIGHTINGS = (("Emirates", "A388", 4), ("Emirates", "B77W", 2), ("Korean Air", "AN24", 1))


def _seed(state_dir):
    seed_airline_editor(state_dir)
    now = datetime.now(timezone.utc)
    number = 0
    with history_db.open_db(state_dir) as conn:
        for airline, code, count in SIGHTINGS:
            for _ in range(count):
                number += 1
                history_db.record_runway_event(
                    conn, ts=(now - timedelta(hours=number)).isoformat(), hex="ml%04d" % number,
                    callsign="XXX%03d" % number, aircraft_type=code,
                    confirmed_state="departing", airline=airline)


def _open(new_context, server, size, lang, theme):
    context = new_context(viewport={"width": size[0], "height": size[1]}, color_scheme=theme)
    context.add_cookies([{"name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": server.base_url()}])
    page = context.new_page()
    _login(page, server.base_url())
    page.goto(server.base_url() + "/airlines/manage")
    page.wait_for_function(animation_settle.SETTLED, timeout=15000)
    return context, page

STYLE = """el => { const s = getComputedStyle(el);
  return [s.fontSize, s.fontWeight, s.color, s.textAlign]; }"""
TABLES = "table.airlines-table"
LABEL = "caption.airlines-label"


@pytest.mark.parametrize("theme", ("light", "dark"))
@pytest.mark.parametrize("size", ((390, 844), (1280, 900)))
def test_the_label_matches_the_airlines_label_and_sits_between_the_tables(
        new_context, make_app_server, size, theme):
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page = _open(new_context, server, size, "fr", theme)
    try:
        label = page.locator("#airlines-missing-title")
        assert label.inner_text().startswith("Illustrations manquantes · ")
        assert label.evaluate("e => e.tagName") == "P"
        assert page.locator(SECTION + " > h2").count() == 0
        assert page.locator(SECTION + " > .section-caption").count() == 0
        airlines = page.locator(TABLES + ":not(.airlines-table--gaps) " + LABEL)
        assert label.evaluate(STYLE) == airlines.evaluate(STYLE)
        assert label.evaluate(STYLE)[:2] == ["13px", "600"]
        labelled = page.locator(SECTION).get_attribute("aria-labelledby")
        assert labelled == "airlines-missing-title"
        order = page.evaluate(
            """() => [...document.querySelectorAll('table.airlines-table--gaps, #airlines-missing, '
              + 'table.airlines-table:not(.airlines-table--gaps)')].map(e => e.id || e.className)""")
        assert order[0].endswith("airlines-table--gaps") and order[1] == "airlines-missing"
        tops = page.evaluate(
            """() => ['table.airlines-table--gaps', '#airlines-missing',
              'table.airlines-table:not(.airlines-table--gaps)'].map(
                s => document.querySelector(s).getBoundingClientRect().top)""")
        assert tops[0] < tops[1] < tops[2], tops
        label_box = label.bounding_box()
        list_box = page.locator(SECTION + " .airlines-missing__list").bounding_box()
        assert label_box["y"] + label_box["height"] <= list_box["y"]
        assert list_box["y"] - (label_box["y"] + label_box["height"]) < 16
    finally:
        context.close()
