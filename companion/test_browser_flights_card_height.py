#!/usr/bin/env python3
"""Every Flights card has the one height the stylesheet declares (its content-visibility
intrinsic size), whatever the airline name, the route or the language, so the browser can skip
cards that are off screen without moving the scroll position."""
import pytest

from companion import auth
from companion import test_view_pages_helpers as vp
from companion.test_browser_ux_helpers import _login

pytestmark = pytest.mark.browser

CARD = "li.history-card"
_LONG_AIRLINE = (
    "Some Very Long Charter Operator Name Limited of the Greater Paris Region and Beyond")
_FLIGHTS = (
    ("AFR1", "Air France", "ORY", "NCE", "departing"),
    ("SMR2", _LONG_AIRLINE, "ORY", "KEF", "departing"),
    ("OBS3", None, "ORY", "OPO", "departing"),
    ("TVF4", "Transavia France", "NCE", "ORY", "arriving"),
    ("XYZ5", _LONG_AIRLINE, None, None, "departing"),
    ("LNG6", "Air Algerie", "ORY", "A-VERY-LONG-AIRPORT-CODE-THAT-CANNOT-FIT", "departing"),
    ("LNG7", "A", "A-VERY-LONG-AIRPORT-CODE-THAT-CANNOT-FIT", "ORY", "arriving"),
    ("NOC8", "Wizz Air Abu Dhabi", "ORY", "LTN", "overhead"),
)


def _seed(state_dir):
    vp.seed_runway_events(state_dir, [
        {"ts": "2026-09-03T%02d:%02d:00+00:00" % (20 - index // 4, 55 - index * 5), "hex": "4c%04x" % index,
         "callsign": callsign, "airline": airline, "origin": origin, "destination": destination,
         "confirmed_state": state, "aircraft_type": "A320" if index % 2 else "B788"}
        for index, (callsign, airline, origin, destination, state) in enumerate(_FLIGHTS)])


@pytest.fixture(scope="module")
def server(module_app_server_factory):
    return module_app_server_factory(seed=_seed, fake_providers=True)


_PROBE = """() => {
  const cards = [...document.querySelectorAll('li.history-card')];
  return cards.map(li => {
    const style = getComputedStyle(li);
    return {height: li.getBoundingClientRect().height - parseFloat(style.borderTopWidth)
                      - parseFloat(style.borderBottomWidth),
            declared: parseFloat(style.containIntrinsicBlockSize.replace('auto', '')),
            visibility: style.contentVisibility,
            overflowing: [...li.querySelectorAll('.row__label, .row__detail, .row__value')]
              .some(e => e.scrollHeight > e.clientHeight + 1)};
  });
}"""


@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("width", [360, 390, 768, 1280])
def test_every_card_is_exactly_its_declared_intrinsic_height(new_context, server, width, lang):
    context = new_context(viewport={"width": width, "height": 900})
    context.add_cookies([{
        "name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": server.base_url()}])
    page = context.new_page()
    try:
        _login(page, server.base_url())
        page.goto(server.base_url() + "/flights")
        page.wait_for_function("() => document.readyState === 'complete'")
        if width >= 960:
            # The desktop shows the table; show the cards to measure them at this width.
            page.evaluate("""() => {
                document.querySelector('.history-cards').style.display = 'block';
                document.querySelector('.history-cards ~ .data-table-wrap').style.display = 'none'; }""")
        page.locator(CARD).first.wait_for(state="visible")
        cards = page.evaluate(_PROBE)
        assert len(cards) == len(_FLIGHTS)
        for card in cards:
            assert card["visibility"] == "auto"
            assert card["declared"] > 40
            assert card["height"] == pytest.approx(card["declared"], abs=0.01), card
            assert not card["overflowing"]
        assert len({round(card["height"], 2) for card in cards}) == 1
    finally:
        context.close()
