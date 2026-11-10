#!/usr/bin/env python3
"""Browser checks that, on a phone, the Location sheet is one compact card: the airport (name on
one line, its codes under it) with Cancel and Save at the right of the same row while something is
unsaved, the runway chips in one row under it, and no separate unsaved-changes strip over the map.
In My position mode the coordinates and the radius take two rows and the same actions. The map keeps
the share of the window the owner asked for, and nothing the card shares the window with is covered.

Both external hosts are answered by `page.route`; waits are on the page's own state.
"""
import pytest

from companion import auth
from companion.test_browser_ux_helpers import _login
from place_map_support import CLEAR_BOX, SETTLED, Hosts, seed as _seed

pytestmark = pytest.mark.browser

PHONES = [
    pytest.param({"width": 390, "height": 844}, 0.55, id="390x844"),
    pytest.param({"width": 360, "height": 740}, 0.47, id="360x740"),
]
READY = "() => document.documentElement.classList.contains('map-ready')"
TILES_LOADED = "() => document.querySelectorAll('#place-map .leaflet-tile-loaded').length >= 1"
ANIMATIONS_DONE = (
    "() => document.getAnimations().every("
    "(a) => a.playState !== 'running' || a.effect.getComputedTiming().iterations === Infinity)")
BAR_SHOWN = (
    "() => { const b = document.querySelector('.place-panel > .dirty-bar');"
    " return !!b && !b.hidden && getComputedStyle(b).display !== 'none'"
    " && b.getBoundingClientRect().height > 0; }")
SECTION = ".place-panel__runway, .place-panel__area"

# The boxes the card must not touch, and its own parts, as [left, top, right, bottom].
BOXES = """() => {
  const box = (el) => { if (!el) return null; const r = el.getBoundingClientRect();
    return [r.left, r.top, r.right, r.bottom]; };
  const all = (sel) => Array.from(document.querySelectorAll(sel));
  const shown = (el) => el.getBoundingClientRect().width > 0 && !el.hidden;
  const sheet = document.querySelector('.place-sheet');
  const bar = document.querySelector('.place-panel > .dirty-bar');
  const map = document.getElementById('place-map');
  const pin = document.querySelector('#place-map .place-pin');
  const clipped = (el) => el.scrollWidth > el.clientWidth + 1;
  const chosen = document.querySelector('.place-chosen');
  const name = document.querySelector('.place-chosen__name');
  const area = document.querySelector('.place-panel__area');
  const coords = document.getElementById('place-coords');
  const hint = document.getElementById('place-tap-hint');
  return {
    sheet: box(sheet), bar: box(bar), tab: box(document.querySelector('.tab-bar')),
    chips: box(document.querySelector('.place-modes')),
    search: box(document.querySelector('.place-search__row')),
    pin: box(pin), win: [innerWidth, innerHeight], mapBox: box(map),
    tools: all('.place-france, .place-locate, .place-nearest__button').filter(shown).map(box),
    save: box(bar.querySelector('.dirty-bar__save')),
    cancel: box(bar.querySelector('.dirty-bar__cancel')),
    buttonsClipped: Array.from(bar.querySelectorAll('.btn')).some(clipped),
    runways: all('.runway-card').map(box),
    runwayClipped: all('.runway-card').some((el) => Array.from(el.children).some((c) =>
      !c.classList.contains('runway-card__check') && c.getBoundingClientRect().width > 2
      && (clipped(c) || c.getBoundingClientRect().right > el.getBoundingClientRect().right))),
    chosen: box(chosen), name: box(name),
    nameLines: name ? Math.round(name.getBoundingClientRect().height
      / parseFloat(getComputedStyle(name).lineHeight)) : 0,
    nameTitle: name ? name.getAttribute('title') : null,
    nameText: name ? name.textContent : null,
    codes: box(document.querySelector('.place-chosen__codes')),
    codesClipped: document.querySelector('.place-chosen__codes')
      ? clipped(document.querySelector('.place-chosen .section-caption')) : false,
    area: area && shown(area) ? box(area) : null,
    coordsBox: coords && shown(coords) ? box(coords) : null,
    hintBox: hint && shown(hint) ? box(hint) : null,
    radiusRow: box(document.querySelector('.place-radius__range')),
    radiusInput: box(document.getElementById('place-radius')),
    radiusLabel: box(document.querySelector('.place-radius__head label')),
    barPosition: getComputedStyle(bar).position,
    message: bar.querySelector('.dirty-bar__message').textContent,
    messageLive: bar.querySelector('.dirty-bar__message').getAttribute('role'),
  };
}"""


def _open(new_context, server, viewport, lang, theme, route):
    context = new_context(viewport=viewport, color_scheme=theme)
    Hosts(context)
    context.add_cookies([
        {"name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": server.base_url()}])
    page = context.new_page()
    _login(page, server.base_url())
    page.goto(server.base_url() + route)
    page.wait_for_function(READY, timeout=15000)
    page.wait_for_function(TILES_LOADED, timeout=15000)
    page.wait_for_function(ANIMATIONS_DONE, timeout=10000)
    page.wait_for_function(SETTLED, timeout=10000)
    return context, page


def _settle(page):
    page.wait_for_function(BAR_SHOWN, timeout=5000)
    page.wait_for_function(ANIMATIONS_DONE, timeout=10000)
    page.wait_for_function(SETTLED, timeout=10000)


def _apart(a, b, what):
    """The two boxes ([left, top, right, bottom]) share no area."""
    separate = a[2] <= b[0] + 0.5 or b[2] <= a[0] + 0.5 or a[3] <= b[1] + 0.5 or b[3] <= a[1] + 0.5
    assert separate, (what, a, b)


def _inside(inner, outer, what):
    assert (inner[0] >= outer[0] - 0.5 and inner[1] >= outer[1] - 0.5
            and inner[2] <= outer[2] + 0.5 and inner[3] <= outer[3] + 0.5), (what, inner, outer)


def _assert_card_is_clear(boxes):
    sheet = boxes["sheet"]
    assert boxes["barPosition"] == "static", boxes
    _inside(boxes["bar"], sheet, "the actions sit in the card")
    _apart(sheet, boxes["tab"], "card and tab bar")
    assert sheet[3] <= boxes["tab"][1] + 0.5, boxes
    for tool in boxes["tools"]:
        _apart(sheet, tool, "card and map tools")
    if boxes["pin"]:
        _apart(sheet, boxes["pin"], "card and pin")
    assert not boxes["buttonsClipped"], boxes
    assert boxes["save"][2] <= sheet[2] and boxes["cancel"][0] >= sheet[0], boxes
    for button in (boxes["save"], boxes["cancel"]):
        assert button[3] - button[1] >= 44 - 0.5 and button[2] - button[0] >= 44, boxes
    assert boxes["messageLive"] == "status" and boxes["message"].strip(), boxes


def _clear_share(boxes):
    """The part of the window height between the chips and the card, as a fraction."""
    return (boxes["sheet"][1] - boxes["chips"][3]) / boxes["win"][1]


@pytest.mark.parametrize("theme", ["light", "dark"])
@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("viewport,share", PHONES)
def test_the_airport_sheet_is_one_compact_card_with_its_actions(
        new_context, make_app_server, viewport, share, lang, theme):
    """choosing another runway shows Cancel and Save at the right of the airport's name row of one
    compact card (no strip over the map), the codes under the one-line name, the three chips in
    one row of at least 44px, and nothing of the card covers the tab bar, the map tools or the pin;
    the map keeps its share of the window"""
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page = _open(new_context, server, viewport, lang, theme, "/detection?airport=LFPO")
    try:
        assert page.evaluate("() => !document.querySelector('.dirty-bar') "
                             "|| document.querySelector('.dirty-bar').hidden")
        page.click(".runway-card:nth-of-type(1)")
        _settle(page)
        boxes = page.evaluate(BOXES)
        _assert_card_is_clear(boxes)
        sheet = boxes["sheet"]
        assert sheet[3] - sheet[1] <= 135, boxes
        assert boxes["nameLines"] == 1 and boxes["nameTitle"] == boxes["nameText"], boxes
        assert not boxes["codesClipped"], boxes
        _apart(boxes["name"], boxes["bar"], "name and actions")
        _apart(boxes["codes"], boxes["bar"], "codes and actions")
        assert boxes["bar"][1] < boxes["runways"][0][1], boxes
        _apart(boxes["bar"], [sheet[0], boxes["runways"][0][1], sheet[2], sheet[3]], "actions, chips")
        assert len(boxes["runways"]) >= 3
        tops = {round(r[1]) for r in boxes["runways"]}
        assert len(tops) == 1, boxes
        for chip in boxes["runways"]:
            assert chip[3] - chip[1] >= 44 and chip[3] - chip[1] <= 52, boxes
            _inside(chip, sheet, "chip in card")
        assert not boxes["runwayClipped"], boxes
        assert _clear_share(boxes) >= share, (_clear_share(boxes), boxes)
        assert page.evaluate("() => document.scrollingElement.scrollHeight - innerHeight") <= 0
    finally:
        context.close()


@pytest.mark.parametrize("theme", ["light", "dark"])
@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("viewport,share", PHONES)
def test_the_position_sheet_is_two_rows_with_the_actions_in_the_card(
        new_context, make_app_server, viewport, share, lang, theme):
    """in My position mode, with a pin placed and the radius changed, the coordinates row carries
    Cancel and Save at its right and the radius is one row (label, slider, number) under it, all in
    one card that covers neither the pin, the tab bar nor the map tools"""
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page = _open(new_context, server, viewport, lang, theme, "/detection?mode=area")
    try:
        box = page.evaluate(CLEAR_BOX)
        page.mouse.click(box["x"] + box["width"] * 0.5, box["y"] + box["height"] * 0.4)
        page.wait_for_function(
            "() => !!document.querySelector('#place-map .place-pin')", timeout=10000)
        page.fill("#place-radius", "15")
        _settle(page)
        boxes = page.evaluate(BOXES)
        _assert_card_is_clear(boxes)
        sheet = boxes["sheet"]
        assert sheet[3] - sheet[1] <= 135, boxes
        assert boxes["coordsBox"] is not None, boxes
        _apart(boxes["coordsBox"], boxes["bar"], "coordinates and actions")
        _inside(boxes["coordsBox"], sheet, "coordinates")
        for part in ("radiusLabel", "radiusRow", "radiusInput"):
            assert boxes[part] is not None, (part, boxes)
            _inside(boxes[part], sheet, part)
            _apart(boxes[part], boxes["bar"], part)
        centres = {round((boxes[p][1] + boxes[p][3]) / 2) for p in ("radiusLabel", "radiusRow")}
        assert max(centres) - min(centres) <= 3, boxes
        assert boxes["radiusRow"][2] <= boxes["radiusInput"][0] and boxes["radiusLabel"][2] <= boxes[
            "radiusRow"][0], boxes
        assert boxes["radiusInput"][3] - boxes["radiusInput"][1] >= 44, boxes
        assert _clear_share(boxes) >= share, (_clear_share(boxes), boxes)
    finally:
        context.close()


@pytest.mark.parametrize("viewport,share", PHONES[:1])
def test_the_compact_sheets_cancel_restores_the_saved_runway_and_hides_the_actions(
        new_context, make_app_server, viewport, share):
    """the card's Cancel puts the saved runway back and hides the actions again; the live message
    that announces the unsaved changes stays in the page for assistive technology"""
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page = _open(new_context, server, viewport, "en", "light", "/detection?airport=LFPO")
    try:
        page.click(".runway-card:nth-of-type(1)")
        _settle(page)
        assert page.evaluate(
            "() => document.querySelector('.dirty-bar__message').textContent.trim().length > 0")
        page.click(".place-panel > .dirty-bar button.dirty-bar__cancel")
        page.wait_for_function(
            "() => { const b = document.querySelector('.place-panel > .dirty-bar');"
            " return b.hidden || getComputedStyle(b).display === 'none'; }", timeout=5000)
        page.wait_for_function(
            "() => document.querySelector('.runway-card--selected input').checked", timeout=5000)
    finally:
        context.close()
