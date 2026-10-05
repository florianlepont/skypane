#!/usr/bin/env python3
"""Real-browser checks of the calendar status row's layout on the Display page: at every width the
"Manage" (or "Connect") button sits on the right of the same row as the text, vertically centred,
and never makes the row taller than its tile plus two text lines. Covers 360/390 px phones and the
1280 px desktop (where the special-looks column is narrow), English and French, light and dark,
and every state the row can show; also with scripts blocked, where the button is a plain link.
"""
from datetime import datetime

import pytest

import companion.test_companion_app_helpers as cah
from companion import auth
from companion.test_browser_ux_helpers import (
    VIEWPORT_DESKTOP, VIEWPORT_MIN_SUPPORTED, VIEWPORT_PHONE, _assert_no_page_overflow,
    _in_both_themes, _login, _no_js_page,
)
from server.plane import calendar_rules

pytestmark = pytest.mark.browser

ROW = ".calendar-status"
BUTTON = ROW + " a.calendar-manage"
URL = "https://old-calendar.example/published/2/OLDSECRET?auth=OLDTOKEN"
STATES = ("none", "pending", "ok", "zero", "stale", "failed", "ignored")


@pytest.fixture
def server(app_server_in_process):
    return app_server_in_process


def _connect(server, entries, age_s=0, url=URL, host="old-calendar.example"):
    body = cah.ics_body(entries)
    with cah.stubbed_calendar_transport(cah.make_calendar_transport(body=body)), \
            cah.fake_public_hostname(host):
        assert calendar_rules.save_calendar_url(server.state_dir, url)
        calendar_rules.refresh_calendar_registry(
            server.state_dir, datetime.now().timestamp() - age_s, min_interval_s=0)


def _arrange(server, state, monkeypatch):
    """Put the calendar into `state` through the real save and refresh paths."""
    if state == "pending":
        with cah.fake_public_hostname("old-calendar.example"):
            assert calendar_rules.save_calendar_url(server.state_dir, URL)
    elif state == "ok":
        _connect(server, [("AF1234", "CDG", "ORY", 2), ("BA5678", "LHR", "CDG", 4)])
    elif state == "zero":
        _connect(server, [])
    elif state == "stale":
        _connect(server, [("AF1234", "CDG", "ORY", 2)], age_s=3 * 3600)
    elif state == "failed":
        _connect(server, [("AF1234", "CDG", "ORY", 2)], age_s=1500)
        failing = cah.make_calendar_transport(raise_exc=ConnectionError("boom"))
        with cah.stubbed_calendar_transport(failing), cah.fake_public_hostname("old-calendar.example"):
            calendar_rules.refresh_calendar_registry(
                server.state_dir, datetime.now().timestamp(), min_interval_s=0)
    elif state == "ignored":
        monkeypatch.setattr(calendar_rules, "calendar_secret_mode_is_unsafe", lambda *a, **k: True)


def _measure(page):
    return page.evaluate("""() => {
      const r = e => { const b = e.getBoundingClientRect();
        return {x: b.x, y: b.y, w: b.width, h: b.height, r: b.right, b: b.bottom}; };
      const row = document.querySelector('.calendar-status');
      const text = row.querySelector('.calendar-status__main');
      const btn = row.querySelector('a.calendar-manage');
      const tile = row.querySelector('.calendar-status__tile');
      const line = e => parseFloat(getComputedStyle(e).lineHeight) ||
        1.4 * parseFloat(getComputedStyle(e).fontSize);
      const title = row.querySelector('.calendar-status__title');
      const detail = row.querySelector('.calendar-status__detail');
      return {row: r(row), text: r(text), btn: r(btn), tile: r(tile),
              lines: Math.round(r(text).h / line(detail)),
              textH: r(text).h, rowPadTop: parseFloat(getComputedStyle(row).paddingTop),
              titleH: r(title).h};
    }""")


def _assert_inline(m, where, phone):
    row, text, btn, tile = m["row"], m["text"], m["btn"], m["tile"]
    assert btn["x"] >= text["r"] - 0.5, (where, "button is not to the right of the text", m)
    assert btn["r"] <= row["r"] + 0.5 and btn["x"] >= row["x"], (where, "button leaves the row", m)
    # Vertically inside the row and centred on the tile/text content band.
    assert btn["y"] >= row["y"] - 0.5 and btn["b"] <= row["b"] + 0.5, (where, m)
    content_mid = row["y"] + m["rowPadTop"] + (row["h"] - m["rowPadTop"]) / 2
    assert abs((btn["y"] + btn["h"] / 2) - content_mid) <= 1.5, (where, "not centred", m)
    # No second line for the button: the row is only as tall as its tallest item (+ its padding).
    tallest = max(tile["h"], text["h"], btn["h"])
    assert row["h"] <= tallest + m["rowPadTop"] + 1, (where, "row taller than its content", m)
    assert btn["y"] < text["b"] - 1 or btn["h"] >= text["h"] - 1, (where, m)
    if phone:
        assert btn["h"] >= 44 - 0.5 and btn["w"] >= 44, (where, "touch target", m)


@pytest.mark.parametrize("state", STATES)
@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize(
    "viewport", [VIEWPORT_MIN_SUPPORTED, VIEWPORT_PHONE, VIEWPORT_DESKTOP], ids=["360", "390", "1280"])
def test_manage_sits_on_the_right_of_the_same_row(
        new_context, server, monkeypatch, viewport, lang, state):
    """the button is right of the text, centred, inside the row, the row is no taller than its
    content (no second line), nothing overflows and the phone target is >= 44 px - every state,
    both languages, both themes"""
    _arrange(server, state, monkeypatch)
    context = new_context(viewport=viewport)
    context.add_cookies([{"name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": server.base_url()}])
    page = context.new_page()
    try:
        _login(page, server.base_url())
        page.goto(server.base_url() + "/display")
        page.locator(BUTTON).wait_for(state="visible")
        assert page.locator(ROW).get_attribute("data-calendar-state") == state
        for theme in _in_both_themes(page):
            where = "calendar row (%s, %s, %s, %d)" % (state, lang, theme["theme"], viewport["width"])
            _assert_inline(_measure(page), where, phone=viewport["width"] < 960)
            assert _assert_no_page_overflow(page, where) == ""
            assert page.locator(ROW).evaluate("e => e.scrollWidth - e.clientWidth") <= 0, where
    finally:
        context.close()


def test_with_scripts_blocked_the_button_is_still_a_link_on_the_right(new_context, server):
    """no script: the same row layout, and the button stays the plain link to the open sheet"""
    _connect(server, [("AF1234", "CDG", "ORY", 2)])
    for viewport in (VIEWPORT_PHONE, VIEWPORT_DESKTOP):
        with _no_js_page(new_context, server.base_url(), "/display", viewport=viewport,
                         reduced_motion="reduce") as page:
            page.wait_for_load_state("load")
            page.locator(BUTTON).wait_for(state="visible")
            assert page.locator(BUTTON).get_attribute("href") == "/display?calendar=manage#calendar-sheet"
            _assert_inline(_measure(page), "no-js %d" % viewport["width"], phone=viewport["width"] < 960)


ICLOUD_URL = "https://p12-caldav.icloud.com/published/2/ICLOUDSECRET"


@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("viewport", [VIEWPORT_PHONE, VIEWPORT_DESKTOP], ids=["390", "1280"])
def test_an_icloud_row_is_as_short_as_its_tile_and_two_text_lines(
        new_context, server, viewport, lang):
    """the real-world row (provider name, pill, detail) is a one-line title plus a detail of at
    most two lines, with the button beside it rather than under it"""
    _connect(server, [("AF1234", "CDG", "ORY", 2)], url=ICLOUD_URL, host="p12-caldav.icloud.com")
    context = new_context(viewport=viewport)
    context.add_cookies([{"name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": server.base_url()}])
    page = context.new_page()
    try:
        _login(page, server.base_url())
        page.goto(server.base_url() + "/display")
        page.locator(BUTTON).wait_for(state="visible")
        assert page.locator(".calendar-status__title b").inner_text() == "iCloud"
        m = _measure(page)
        _assert_inline(m, "icloud %s %d" % (lang, viewport["width"]), phone=viewport["width"] < 960)
        detail = page.locator(".calendar-status__detail").evaluate(
            "e => e.getBoundingClientRect().height / parseFloat(getComputedStyle(e).lineHeight)")
        assert detail <= 2.05, ("detail wraps past two lines", detail, m)
    finally:
        context.close()
