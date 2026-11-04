"""Real-browser checks of the Special looks and Calendar cards of Personalisation (/display): at 360
and 1280 px, in English and French, in both themes, nothing overflows sideways and each Remove
link, "New special look" summary and "Choose calendar" button is at least 44x44 and owns its centre.
The Remove dialog opens from its row with the focus on "Keep special look", keeps Tab inside, closes
on Escape with the focus back on the Remove link, deletes the rule from "Remove special look" with
the deleted notice, and changes nothing from "Keep special look". With scripts blocked the hash link
shows the dialog and its POST removes the rule.

State is always waited for (focus, open dialogs, navigations), never read right after a key press."""
import pytest

from companion import auth, layout
from companion.test_browser_ux_helpers import (
    UI_THEMES_EXPLICIT,
    VIEWPORT_DESKTOP,
    VIEWPORT_MIN_SUPPORTED,
    _assert_no_page_overflow,
    _login,
    _no_js_page,
    _set_ui_theme,
    seed_state_dir,
)
from server.plane import colour_rules

pytestmark = pytest.mark.browser

VIEWPORTS = (("360", VIEWPORT_MIN_SUPPORTED), ("1280", VIEWPORT_DESKTOP))
REMOVE = 'a.special-row__remove[aria-label$="TVF"]'
DIALOG = 'li.rule-row dialog.modal:has(form[action$="/prefix/TVF/delete"])'
DISMISS = DIALOG + " a.modal__dismiss"
SUBMIT = DIALOG + ' button[type="submit"]'
RULE = ("prefix", "TVF")

_SETTLED = (
    "() => document.readyState === 'complete'"
    " && document.getAnimations().every(a => a.effect && a.effect.getTiming().iterations !== Infinity"
    " ? a.playState !== 'running' : true)")
_OWNS_CENTRE = (
    "el => { const r = el.getBoundingClientRect();"
    " const hit = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);"
    " return !!hit && (hit === el || el.contains(hit) || hit.contains(el)); }")


def _seed(state_dir):
    seed_state_dir(state_dir)
    assert colour_rules.add_rule(state_dir, *RULE, "white") == colour_rules.ADD_OK_NEW


def _rules(server):
    return colour_rules.load_colour_rules(server.state_dir)["prefix"]


def _rule_count(server):
    return sum(len(entries) for entries in colour_rules.load_colour_rules(server.state_dir).values())


def _open(new_context, base_url, viewport, lang="en", theme="light"):
    context = new_context(viewport=viewport)
    context.add_cookies([{"name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": base_url}])
    page = context.new_page()
    _login(page, base_url)
    page.goto(base_url + layout.DISPLAY_ROUTE)
    page.wait_for_function(_SETTLED, timeout=15000)
    page.locator(REMOVE).wait_for(state="visible")
    _set_ui_theme(page, theme)
    _wait_owns_centre(page, REMOVE)
    return context, page


def _wait_owns_centre(page, selector):
    page.locator(selector).first.evaluate("el => el.scrollIntoView({block: 'center'})")
    page.wait_for_function(
        "sel => { const el = document.querySelector(sel); const r = el.getBoundingClientRect();"
        " const hit = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);"
        " return !!hit && (hit === el || el.contains(hit) || hit.contains(el)); }",
        arg=selector, timeout=10000)


def _open_dialog(page):
    page.locator(REMOVE).click()
    page.wait_for_function(
        "() => { const d = document.querySelector('%s');"
        " return d.open && d.classList.contains('is-modal')"
        " && document.activeElement === d.querySelector('a.modal__dismiss'); }" % DIALOG,
        timeout=10000)


@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("theme", UI_THEMES_EXPLICIT)
@pytest.mark.parametrize("label,viewport", VIEWPORTS, ids=[v[0] for v in VIEWPORTS])
def test_the_cards_do_not_overflow_and_their_controls_are_44px(
        new_context, make_app_server, label, viewport, theme, lang):
    server = make_app_server(seed=_seed)
    context, page = _open(new_context, server.base_url(), viewport, lang=lang, theme=theme)
    try:
        assert not _assert_no_page_overflow(page, "cards", viewport["width"])
        for selector in (
                REMOVE, "#personalisation-special-looks summary.special-add__summary",
                "#personalisation-calendar a.calendar-manage"):
            _wait_owns_centre(page, selector)
            box = page.locator(selector).first.bounding_box()
            assert box["width"] >= 44 - 0.5 and box["height"] >= 44 - 0.5, (selector, box)
            assert page.locator(selector).first.evaluate(_OWNS_CENTRE), selector
        remove = page.locator(REMOVE).first.bounding_box()
        card = page.locator("#personalisation-special-looks").bounding_box()
        assert remove["x"] >= card["x"] - 0.5 and remove["x"] + remove["width"] <= (
            card["x"] + card["width"] + 0.5)
        assert page.locator(
            "#personalisation-calendar .calendar-status__lead").inner_text().startswith(
            "Flights in your calendar" if lang == "en" else "Vols de votre calendrier")
    finally:
        context.close()


@pytest.mark.parametrize("label,viewport", VIEWPORTS, ids=[v[0] for v in VIEWPORTS])
def test_remove_opens_the_dialog_on_keep_and_escape_returns_to_remove(
        new_context, make_app_server, label, viewport):
    server = make_app_server(seed=_seed)
    context, page = _open(new_context, server.base_url(), viewport)
    try:
        _open_dialog(page)
        assert page.locator(DIALOG + " h2").inner_text() == "Remove this special look?"
        assert page.locator(DISMISS).inner_text() == "Keep special look"
        page.evaluate(
            """() => { window.__inside = [];
              const dialog = document.querySelector('%s');
              document.addEventListener('focusin', (e) => window.__inside.push(
                dialog.contains(e.target))); }""" % DIALOG)
        inside_or_nowhere = (
            "() => { const a = document.activeElement; return !a || a === document.body"
            " || document.querySelector('%s').contains(a); }" % DIALOG)
        for key in ["Tab"] * 8 + ["Shift+Tab"] * 2:
            page.keyboard.press(key)
            page.wait_for_function(inside_or_nowhere, timeout=5000)
        page.wait_for_function(
            "() => window.__inside.length >= 3 && window.__inside.every(Boolean)", timeout=5000)
        page.keyboard.press("Escape")
        page.wait_for_function(
            "() => !document.querySelector('%s').open && document.activeElement"
            " && document.activeElement.matches('%s')" % (DIALOG, REMOVE), timeout=10000)
        assert RULE[1] in _rules(server)
    finally:
        context.close()


def test_keep_special_look_changes_nothing(new_context, make_app_server):
    server = make_app_server(seed=_seed)
    context, page = _open(new_context, server.base_url(), VIEWPORT_DESKTOP)
    try:
        _open_dialog(page)
        page.locator(DISMISS).click()
        page.wait_for_function(
            "() => !document.querySelector('%s').open" % DIALOG, timeout=10000)
        assert RULE[1] in _rules(server)
        assert page.locator("li.rule-row").count() == _rule_count(server)
    finally:
        context.close()


@pytest.mark.parametrize("label,viewport", VIEWPORTS, ids=[v[0] for v in VIEWPORTS])
def test_remove_special_look_deletes_the_rule_and_shows_the_notice(
        new_context, make_app_server, label, viewport):
    server = make_app_server(seed=_seed)
    before = _rule_count(server)
    context, page = _open(new_context, server.base_url(), viewport)
    try:
        _open_dialog(page)
        with page.expect_navigation():
            page.locator(SUBMIT).click()
        toast = page.locator(".toast").first
        toast.wait_for(state="visible")
        assert "Rule deleted" in toast.inner_text()
        assert RULE[1] not in _rules(server) and _rule_count(server) == before - 1
        page.wait_for_function(
            "n => document.querySelectorAll('li.rule-row').length === n",
            arg=before - 1, timeout=10000)
    finally:
        context.close()


def test_without_scripts_the_hash_link_shows_the_dialog_and_its_post_removes_the_rule(
        new_context, make_app_server):
    server = make_app_server(seed=_seed)
    before = _rule_count(server)
    with _no_js_page(new_context, server.base_url(), layout.DISPLAY_ROUTE,
                     viewport=VIEWPORT_MIN_SUPPORTED, reduced_motion="reduce") as page:
        page.wait_for_load_state("load")
        page.locator(REMOVE).wait_for(state="visible")
        page.locator(REMOVE).click()
        page.wait_for_function(
            "() => location.hash.startsWith('#remove-look-')", timeout=10000)
        dialog = page.locator(DIALOG)
        dialog.locator("button[type=submit]").wait_for(state="visible")
        assert dialog.locator("a.modal__dismiss").inner_text() == "Keep special look"
        with page.expect_navigation():
            dialog.locator("button[type=submit]").click()
        page.wait_for_function(
            "n => document.querySelectorAll('li.rule-row').length === n", arg=before - 1,
            timeout=10000)
        assert RULE[1] not in _rules(server)
