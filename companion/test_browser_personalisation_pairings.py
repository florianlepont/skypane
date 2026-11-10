"""Real-browser checks of the five pairing cards on the special look form and the
Calendar look page of a frame on a giant layout, in English and French, at desktop
and phone widths: a stored theme that is no pairing shows the pairing it maps to,
picking another card and saving stores that pairing's theme id, the lists name the
look by its pairing, and a reload shows the saved pairing selected."""
import pytest

from companion import auth, layout
from companion.test_browser_ux_helpers import (
    VIEWPORT_DESKTOP,
    VIEWPORT_PHONE,
    _assert_no_page_overflow,
    _login,
    seed_state_dir,
)
from server import device_config
from server.plane import colour_rules

pytestmark = pytest.mark.browser

EDIT_RULE_ROUTE = layout.DISPLAY_SPECIAL_LOOK_EDIT_ROUTE + "?rule_kind=prefix&rule_key=TVF"
CHECKED_RULE = "form#special-look-form input[name=rule_theme_id]:checked"
CHECKED_CALENDAR = "input[name=calendar_theme_id]:checked"
PAIRING_NAMES = {
    "en": {"grey": "Grey", "red_light": "Light red", "blue_light": "Light blue"},
    "fr": {"grey": "Gris", "red_light": "Rouge clair", "blue_light": "Bleu clair"},
}
VIEWPORTS = (("desktop", VIEWPORT_DESKTOP), ("phone", VIEWPORT_PHONE))


def _seed(state_dir):
    seed_state_dir(state_dir)
    device_config.save_device_config(state_dir, layout="b", theme="grey", calendar_theme_id="green")
    colour_rules.add_rule(state_dir, "prefix", "TVF", "green")


def _open(new_context, base_url, route, lang, viewport):
    context = new_context(viewport=viewport)
    context.add_cookies([{"name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": base_url}])
    page = context.new_page()
    _login(page, base_url)
    page.goto(base_url + route)
    page.wait_for_function("() => document.readyState === 'complete'", timeout=15000)
    return context, page


def _save(page):
    page.wait_for_selector("button.dirty-bar__save", state="visible")
    with page.expect_navigation(timeout=30000):
        page.click("button.dirty-bar__save")
    page.wait_for_function("() => document.readyState === 'complete'", timeout=15000)


def _rule_theme(state_dir):
    rows = colour_rules.rule_rows(colour_rules.load_colour_rules(state_dir))
    return [theme for kind, key, theme, _created in rows if (kind, key) == ("prefix", "TVF")][0]


@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("name,viewport", VIEWPORTS, ids=["desktop", "phone"])
def test_a_special_look_picks_a_pairing_saves_and_shows_it_after_a_reload(
        new_context, make_app_server, lang, name, viewport):
    """the edit page of a rule stored as green checks the grey card, no table or three-choice
    picker is shown, picking light red and saving stores red_light, the list row is named by the
    pairing, and the reopened page has light red checked"""
    server = make_app_server(seed=_seed)
    context, page = _open(new_context, server.base_url(), EDIT_RULE_ROUTE, lang, viewport)
    try:
        assert page.locator("form#special-look-form input[name=rule_theme_id]").count() == 5
        assert page.locator(CHECKED_RULE).get_attribute("value") == "grey"
        assert page.locator("form#special-look-form table.look-table").count() == 0
        assert page.locator("form#special-look-form [data-look-axes]:visible").count() == 0
        assert not _assert_no_page_overflow(page, "special-look-pairings", viewport["width"])
        assert _rule_theme(server.state_dir) == "green"
        page.locator('form#special-look-form label:has(input[value="red_light"])').click()
        assert "layout=b" in page.locator("form#special-look-form img[data-look-image]").get_attribute("src")
        assert "red_light" in page.locator("form#special-look-form img[data-look-image]").get_attribute("src")
        _save(page)
        assert _rule_theme(server.state_dir) == "red_light"
        assert page.locator("li.rule-row:has(.rule-row__key:text-is('TVF')) p.rule-row__theme").inner_text().strip() == (
            PAIRING_NAMES[lang]["red_light"])
        page.goto(server.base_url() + EDIT_RULE_ROUTE)
        assert page.locator(CHECKED_RULE).get_attribute("value") == "red_light"
    finally:
        context.close()


@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("name,viewport", VIEWPORTS, ids=["desktop", "phone"])
def test_the_calendar_look_picks_a_pairing_saves_and_shows_it_after_a_reload(
        new_context, make_app_server, lang, name, viewport):
    """the Calendar look of a frame whose calendar theme is green checks the grey card next to
    "Same as departures", picking light blue and saving stores blue_light, the Calendar row is
    named by the pairing, and a reload of the look page has light blue checked"""
    server = make_app_server(seed=_seed)
    context, page = _open(new_context, server.base_url(), layout.DISPLAY_CALENDAR_LOOK_ROUTE, lang, viewport)
    try:
        assert page.locator("input[name=calendar_theme_id]").count() == 6
        assert page.locator(CHECKED_CALENDAR).get_attribute("value") == "grey"
        assert page.locator("table.look-table").count() == 0
        assert not _assert_no_page_overflow(page, "calendar-pairings", viewport["width"])
        assert device_config.load_device_config(server.state_dir)["calendar_theme_id"] == "green"
        page.locator('label:has(input[name=calendar_theme_id][value="blue_light"])').click()
        _save(page)
        assert device_config.load_device_config(server.state_dir)["calendar_theme_id"] == "blue_light"
        assert PAIRING_NAMES[lang]["blue_light"] in page.locator("#calendar-row").inner_text()
        page.goto(server.base_url() + layout.DISPLAY_CALENDAR_LOOK_ROUTE)
        assert page.locator(CHECKED_CALENDAR).get_attribute("value") == "blue_light"
    finally:
        context.close()
