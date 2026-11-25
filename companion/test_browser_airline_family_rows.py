#!/usr/bin/env python3
"""Real-browser checks of the type rows of the airline editor: the row is labelled with its aircraft
family name (no "(famille)" suffix, interface font), the default type is a star with no text but an
accessible name, and the designators seen are a tooltip on hover and keyboard focus in the table and a
two-line secondary line that a tap expands in a card, in English and French, light and dark, at 360,
390 and 1280 px, and without scripts."""
from datetime import datetime, timedelta, timezone

import animation_settle
import pytest

from companion import auth
from companion.test_browser_airline_helpers import seed_airline_editor
from companion.test_browser_ux_helpers import (
    VIEWPORT_DESKTOP, VIEWPORT_MIN_SUPPORTED, VIEWPORT_PHONE, _assert_no_page_overflow, _login,
    _no_js_page,
)
from server import history_db
from server.plane import airline_default_types, manual_resolutions

pytestmark = pytest.mark.browser

_SETTLED = animation_settle.SETTLED
TRANSAVIA = "#airline-transavia-france"
STAR = {"en": "Default type", "fr": "Type par défaut"}
FAMILIES = {
    "en": ["Airbus A320", "Boeing 737", "Airbus A330", "Other"],
    "fr": ["Airbus A320", "Boeing 737", "Airbus A330", "Autre"],
}
# The rare designators of the "other" row: more than two lines of a card's secondary line.
RARE = tuple("ZZ%02d" % number for number in range(1, 13))
VIEWPORTS = (("360", VIEWPORT_MIN_SUPPORTED), ("390", VIEWPORT_PHONE), ("1280", VIEWPORT_DESKTOP))
THEMES = ("light", "dark")


def _seed(state_dir):
    seed_airline_editor(state_dir)
    manual_resolutions.add_entry(state_dir, "ZEP", "Zephyr Air")
    assert airline_default_types.set_default_type(
        state_dir, "transavia-france", "A320") == airline_default_types.SET_OK
    now = datetime.now(timezone.utc)
    with history_db.open_db(state_dir) as conn:
        for index, code in enumerate(("B38M",) + RARE):
            history_db.record_runway_event(
                conn, ts=(now - timedelta(hours=index + 1)).isoformat(), hex="fm%04d" % index,
                callsign="TVF9%02d" % index, aircraft_type=code, confirmed_state="departing",
                airline="Transavia France")


@pytest.fixture(scope="module")
def server(module_app_server_factory):
    return module_app_server_factory(seed=_seed, fake_providers=True)


def _open(new_context, server, viewport, lang="fr", theme="light", path="/airlines/manage"):
    context = new_context(viewport=viewport, color_scheme=theme)
    context.add_cookies([{
        "name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": server.base_url()}])
    page = context.new_page()
    _login(page, server.base_url())
    page.goto(server.base_url() + path)
    page.wait_for_function(_SETTLED, timeout=15000)
    _expand(page)
    return context, page


def _expand(page):
    chevron = page.locator(TRANSAVIA + " .airlines-expand > summary")
    chevron.scroll_into_view_if_needed()
    chevron.click()
    page.locator(TRANSAVIA + " .airlines-subrow").first.wait_for(state="visible")
    page.wait_for_function(_SETTLED, timeout=15000)


def _label(page, index):
    return page.locator(TRANSAVIA + " .airlines-subrow").nth(index).locator(".airlines-type")


def _row_index(page, family):
    names = page.locator(TRANSAVIA + " .airlines-subrow .airlines-type").all_inner_texts()
    return names.index(family)


def _box(locator):
    return locator.evaluate(
        "el => { const r = el.getBoundingClientRect();"
        " return {x: r.x, y: r.y, right: r.right, bottom: r.bottom, w: r.width, h: r.height}; }")


def _overlap(a, b):
    return a["x"] < b["right"] and b["x"] < a["right"] and a["y"] < b["bottom"] and b["y"] < a["bottom"]


@pytest.mark.parametrize("theme", THEMES)
@pytest.mark.parametrize("lang", ("en", "fr"))
@pytest.mark.parametrize("name,viewport", VIEWPORTS, ids=[v[0] for v in VIEWPORTS])
def test_a_type_row_is_labelled_with_its_family_name_and_a_text_free_star(
        new_context, server, name, viewport, lang, theme):
    context, page = _open(new_context, server, viewport, lang, theme)
    try:
        names = page.locator(TRANSAVIA + " .airlines-subrow .airlines-type").all_inner_texts()
        assert sorted(names) == sorted(FAMILIES[lang])
        assert "(famille)" not in page.content() and "(family)" not in page.content()
        label = _label(page, _row_index(page, "Airbus A320"))
        style = label.evaluate(
            "el => { const s = getComputedStyle(el); return {font: s.fontFamily, size: s.fontSize,"
            " weight: s.fontWeight, color: s.color}; }")
        assert "mono" not in style["font"].lower() and style["weight"] == "600"
        assert style["color"] == page.evaluate("() => getComputedStyle(document.body).color")
        if name == "1280":
            assert style["size"] == "16px", style
            assert _box(label)["h"] >= 44
        star = page.locator(TRANSAVIA + " .airlines-star")
        assert star.count() == 1
        assert star.inner_text().strip() == "" and star.get_attribute("aria-label") == STAR[lang]
        assert star.locator("xpath=ancestor::tr").locator(".airlines-type").inner_text() == (
            "Airbus A320")
        assert not _assert_no_page_overflow(page, "editor", viewport["width"])
    finally:
        context.close()


@pytest.mark.parametrize("theme", THEMES)
@pytest.mark.parametrize("lang", ("en", "fr"))
def test_the_designators_are_a_tooltip_on_hover_and_keyboard_focus_on_a_desktop(
        new_context, server, lang, theme):
    context, page = _open(new_context, server, VIEWPORT_DESKTOP, lang, theme)
    try:
        boeing = _row_index(page, "Boeing 737")
        label = _label(page, boeing)
        tip = page.locator(TRANSAVIA + " .airlines-subrow").nth(boeing).locator(".airlines-codes")
        assert tip.is_hidden()
        label.hover()
        assert tip.is_visible()
        assert "B38M, B738" in tip.inner_text()
        box, label_box = _box(tip), _box(label)
        # Beside the label, wrapped inside 320px, inside the viewport, over no other row's name.
        assert box["x"] >= label_box["right"] and box["w"] <= 320
        assert 0 <= box["x"] and box["right"] <= VIEWPORT_DESKTOP["width"]
        for other in page.locator(TRANSAVIA + " .airlines-type").all():
            if _box(other) != label_box:
                assert not _overlap(box, _box(other))
        page.mouse.move(0, 0)
        assert tip.is_hidden()
        label.focus()
        page.keyboard.press("Shift+Tab")
        page.keyboard.press("Tab")
        assert page.evaluate("() => document.activeElement.className") == "airlines-type"
        assert tip.is_visible()
        ring = label.evaluate(
            "el => { const s = getComputedStyle(el); return [s.outlineStyle, s.outlineWidth,"
            " s.outlineColor]; }")
        accent = page.evaluate(
            "() => { const p = document.createElement('i'); p.style.color = 'var(--color-accent)';"
            " document.body.appendChild(p); const c = getComputedStyle(p).color; p.remove(); return c; }")
        assert ring == ["solid", "2px", accent], ring
        # Assistive technology reads the designators as the label's description.
        described = label.get_attribute("aria-describedby")
        assert described and "B38M, B738" in page.locator("#" + described).text_content()
    finally:
        context.close()


@pytest.mark.parametrize("lang", ("en", "fr"))
def test_a_single_designator_family_shows_its_code_then_its_model_name(new_context, server, lang):
    context, page = _open(new_context, server, VIEWPORT_DESKTOP, lang)
    try:
        index = _row_index(page, "Airbus A330")
        _label(page, index).hover()
        tip = page.locator(TRANSAVIA + " .airlines-subrow").nth(index).locator(".airlines-codes")
        assert tip.is_visible() and tip.inner_text().split("\n")[-1] == "A333 · A330-300"
    finally:
        context.close()


@pytest.mark.parametrize("lang", ("en", "fr"))
def test_the_default_star_has_a_tooltip_on_hover_and_focus_and_hides_no_name(
        new_context, server, lang):
    context, page = _open(new_context, server, VIEWPORT_DESKTOP, lang)
    try:
        star = page.locator(TRANSAVIA + " .airlines-star")
        tip = star.locator(".airlines-tip")
        assert tip.is_hidden()
        star.hover()
        assert tip.is_visible() and tip.inner_text() == STAR[lang]
        assert _box(tip)["x"] >= _box(star)["right"]
        page.mouse.move(0, 0)
        assert tip.is_hidden()
        page.keyboard.press("Tab")
        _label(page, _row_index(page, "Airbus A320")).focus()
        page.keyboard.press("Tab")
        assert page.evaluate("() => document.activeElement.className") == "airlines-star"
        assert tip.is_visible()
        # The designators' tooltip is not shown with the star's.
        assert page.locator(TRANSAVIA + " .airlines-codes:visible").count() == 0
    finally:
        context.close()


@pytest.mark.parametrize("theme", THEMES)
@pytest.mark.parametrize("name,viewport", VIEWPORTS[:2], ids=[v[0] for v in VIEWPORTS[:2]])
def test_a_card_shows_the_designators_under_the_name_in_two_lines_and_a_tap_expands_them(
        new_context, server, name, viewport, theme):
    context, page = _open(new_context, server, viewport, "fr", theme)
    try:
        index = _row_index(page, "Autre")
        row = page.locator(TRANSAVIA + " .airlines-subrow").nth(index)
        codes = row.locator(".airlines-codes")
        assert codes.is_visible()
        assert codes.locator(".airlines-codes__label").is_hidden()
        style = codes.evaluate(
            "el => { const s = getComputedStyle(el); return {font: s.fontFamily, size: s.fontSize,"
            " color: s.color, lines: s.webkitLineClamp}; }")
        assert "mono" in style["font"].lower() and style["size"] == "13px" and style["lines"] == "2"
        line = codes.evaluate("el => parseFloat(getComputedStyle(el).lineHeight)")
        assert _box(codes)["h"] <= 2 * line + 1
        assert codes.evaluate("el => el.scrollHeight > el.clientHeight")
        # The full list stays in the page for assistive technology.
        assert all(code in codes.text_content() for code in RARE)
        assert row.locator(".airlines-tip").count() == 0 or row.locator(".airlines-tip").is_hidden()
        _label(page, index).click()
        assert _box(codes)["h"] > 2 * line + 1
        assert codes.evaluate("el => el.scrollHeight <= el.clientHeight")
        _label(page, index).click()
        assert _box(codes)["h"] <= 2 * line + 1
        assert not _assert_no_page_overflow(page, "editor", viewport["width"])
        star = page.locator(TRANSAVIA + " .airlines-star")
        assert _box(star)["y"] < _box(star.locator("xpath=ancestor::tr").locator(".airlines-codes"))["y"]
    finally:
        context.close()


def test_the_type_rows_work_without_scripts(new_context, server):
    with _no_js_page(new_context, server.base_url(), "/airlines/manage?types=all",
                     viewport=VIEWPORT_DESKTOP, reduced_motion="reduce") as page:
        page.locator(TRANSAVIA + " .airlines-expand > summary").click()
        page.locator(TRANSAVIA + " .airlines-subrow").first.wait_for(state="visible")
        boeing = _row_index(page, "Boeing 737")
        tip = page.locator(TRANSAVIA + " .airlines-subrow").nth(boeing).locator(".airlines-codes")
        assert tip.is_hidden()
        _label(page, boeing).hover()
        assert tip.is_visible() and "B38M, B738" in tip.inner_text()
        page.mouse.move(0, 0)
        _label(page, boeing).focus()
        page.keyboard.press("Shift+Tab")
        page.keyboard.press("Tab")
        assert tip.is_visible()
    with _no_js_page(new_context, server.base_url(), "/airlines/manage?types=all",
                     viewport=VIEWPORT_PHONE, reduced_motion="reduce") as page:
        page.locator(TRANSAVIA + " .airlines-expand > summary").click()
        page.locator(TRANSAVIA + " .airlines-subrow").first.wait_for(state="visible")
        codes = page.locator(TRANSAVIA + " .airlines-subrow").nth(
            _row_index(page, "Other")).locator(".airlines-codes")
        assert codes.is_visible()
        line = codes.evaluate("el => parseFloat(getComputedStyle(el).lineHeight)")
        assert _box(codes)["h"] <= 2 * line + 1


@pytest.mark.parametrize("lang,one,many", (("en", "1 view", "views"), ("fr", "1 vue", "vues")))
@pytest.mark.parametrize("name,viewport", VIEWPORTS[:2], ids=[v[0] for v in VIEWPORTS[:2]])
def test_a_card_shows_the_views_in_its_state_line_once(
        new_context, server, name, viewport, lang, one, many):
    context, page = _open(new_context, server, viewport, lang)
    try:
        rows = page.locator(TRANSAVIA + " .airlines-subrow")
        for index in range(rows.count()):
            row = rows.nth(index)
            column = row.locator(".airlines-cell--views")
            expected = column.text_content().strip()
            assert expected == one or expected.endswith(many), expected
            inline = row.locator(".airlines-views-inline")
            assert inline.is_visible() and inline.inner_text() == expected
            assert column.is_hidden()
            assert row.locator(".airlines-state-line").inner_text() == expected
            assert "propre" not in row.inner_text() and "Own artwork" not in row.inner_text()
        # Nothing is read twice: the hidden column and the table copy are out of the accessibility tree.
        assert page.locator(TRANSAVIA + " .airlines-subrow").nth(0).get_by_text(expected).count() <= 1
    finally:
        context.close()


def test_a_table_row_shows_its_views_in_their_column_only(new_context, server):
    context, page = _open(new_context, server, VIEWPORT_DESKTOP, "en")
    try:
        row = page.locator(TRANSAVIA + " .airlines-subrow").first
        assert row.locator(".airlines-views-inline").is_hidden()
        assert row.locator(".airlines-cell--views").is_visible()
    finally:
        context.close()


@pytest.mark.parametrize("theme", THEMES)
@pytest.mark.parametrize("name,viewport", VIEWPORTS[:2], ids=[v[0] for v in VIEWPORTS[:2]])
def test_the_last_type_card_leaves_the_gap_between_cards_under_it(
        new_context, server, name, viewport, theme):
    context, page = _open(new_context, server, viewport, "fr", theme)
    try:
        spaces = page.evaluate(
            """() => { const group = document.querySelector('#airline-transavia-france');
            const rows = [...group.querySelectorAll('.airlines-subrow')].map(
              row => row.getBoundingClientRect());
            const edge = group.getBoundingClientRect();
            return {under: edge.bottom - rows[rows.length - 1].bottom,
                    between: rows[1].top - rows[0].bottom, side: rows[0].left - edge.left}; }""")
        assert spaces["between"] > 0
        assert spaces["between"] > 0 and abs(spaces["under"] - spaces["between"]) < 0.5, spaces
    finally:
        context.close()
