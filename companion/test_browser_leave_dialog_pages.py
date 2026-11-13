"""Real-browser checks that the unsaved-changes dialog belongs to the save
bar, not to one page: every page family with a bar (Style, a Style form page,
Calendar connect, Location and detection, the Fleet settings) asks the same
question before an in-app link takes the edit away, by touch tap and by click,
at 360 and 1280 px, in both languages and both themes. Save and continue lands
on the tapped page where that page's save can return there, and saves and
stays where it cannot; Discard leaves without saving; a post of another form
(the theme switch) asks too."""
import pytest

from companion import auth, layout
from companion.test_browser_ux_helpers import (
    UI_THEMES_EXPLICIT,
    VIEWPORT_DESKTOP,
    VIEWPORT_MIN_SUPPORTED,
    _assert_no_page_overflow,
    _login,
    _set_ui_theme,
    seed_state_dir,
)
from companion_app_server import TEST_ADMIN_EMAIL, session_cookie_for_state_dir
from place_map_support import Hosts
from server import device_config, device_dirs, fleet_db, hardware
from server.plane import colour_rules

pytestmark = pytest.mark.browser

DIALOG = "dialog[data-leave-dialog]"
PRIMARY = DIALOG + " [data-leave-dialog-primary]"
SECONDARY = DIALOG + " [data-leave-dialog-secondary]"
QUIET = DIALOG + " [data-leave-dialog-quiet]"
BAR = ".dirty-bar"
WORDS = {
    "en": ("Unsaved changes", "You have changes that are not saved. What do you want to do?",
           "Save and continue", "Discard", "Stay here"),
    "fr": ("Modifications non enregistrées",
           "Vous avez des modifications non enregistrées. Que souhaitez-vous faire ?",
           "Enregistrer et continuer", "Abandonner", "Rester ici"),
}
SETTLED = (
    "() => document.readyState === 'complete' && document.getAnimations().every("
    "a => !a.effect || a.effect.getTiming().iterations === Infinity || a.playState !== 'running')")


def _seed(state_dir):
    """The administrator owns the live frame and one location, with a look, a
    special look and a runway detection already stored."""
    seed_state_dir(state_dir)
    session_cookie_for_state_dir(state_dir)
    conn = fleet_db.connect(state_dir)
    try:
        owner = fleet_db.get_user_by_email(conn, TEST_ADMIN_EMAIL)["id"]
        fleet_db.meta_set(conn, fleet_db.META_MIGRATED, "1")
        fleet_db.add_device(
            conn, "aa:bb:cc:00:00:04", "d" * 64, hardware.LEGACY_KEY, owner,
            name="Live frame", state_path=device_dirs.LIVE_STATE_PATH)
        fleet_db.add_location(conn, "Home", 48.8566, 2.3522, "Europe/Paris", owner_user_id=owner)
    finally:
        conn.close()
    device_config.save_device_config(
        state_dir, theme="band_red_field", layout="classic",
        detection={"mode": "runway", "airport": "LFPG", "runway": "08L/26R"})
    colour_rules.add_rule(state_dir, "prefix", "TVF", "white")


@pytest.fixture(scope="module")
def server(module_app_server_factory):
    return module_app_server_factory(seed=_seed, fake_providers=True)


def _fleet_route(server):
    conn = fleet_db.connect(server.state_dir)
    try:
        frame = conn.execute("SELECT id FROM devices LIMIT 1").fetchone()[0]
    finally:
        conn.close()
    return "/fleet?tab=settings&frame=%s" % frame


def _pick_look(page):
    page.locator(".look-dot:has(input:not(:checked):not(:disabled)):visible").first.click()


def _type_key(page):
    page.locator("[name=rule_key]").fill("AFR")


def _type_calendar_url(page):
    page.locator("#calendar-connect-url").fill("https://calendar.example/feed.ics")


def _pick_mode(page):
    page.click("label:has(#place-mode-area)")


def _change_wake(page):
    page.locator("#wake-interval-s").fill("900")


# name, route (or a callable of the server), element to wait for, the edit, the
# address the person leaves for (the Console has its own navigation), and
# whether this page's save accepts that address as its return target.
PAGES = [
    ("style", layout.DISPLAY_ROUTE, ".look-dot", _pick_look, "/flights", True),
    ("special-look-new", layout.DISPLAY_SPECIAL_LOOK_NEW_ROUTE, "label.look-pick__card",
     _type_key, "/flights", False),
    ("calendar-connect", layout.DISPLAY_CALENDAR_CONNECT_ROUTE, "#calendar-connect-url",
     _type_calendar_url, "/flights", False),
    ("location", "/detection", "#place-mode-area", _pick_mode, "/flights", False),
    ("fleet", _fleet_route, "#wake-interval-s", _change_wake, "/users", False),
]
PAGE_IDS = [case[0] for case in PAGES]


def _open(new_context, server, page_case, viewport=VIEWPORT_MIN_SUPPORTED, lang="en", edit=True):
    name, route, ready, change = page_case[:4]
    # has_touch: the phone leaves a page with a touch tap, the owner's path.
    context = new_context(viewport=viewport, has_touch=True)
    Hosts(context)
    context.add_cookies([{
        "name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": server.base_url()}])
    page = context.new_page()
    prompts = []
    page.on("dialog", lambda d: (prompts.append(d.type), d.accept()))
    _login(page, server.base_url())
    page.goto(server.base_url() + (route(server) if callable(route) else route))
    page.locator(ready).first.wait_for(state="attached", timeout=15000)
    if name == "location":
        page.wait_for_function(
            "() => document.documentElement.classList.contains('map-ready')", timeout=15000)
    page.wait_for_function(SETTLED, timeout=20000)
    if edit:
        change(page)
        page.locator(BAR).first.wait_for(state="visible", timeout=10000)
        page.wait_for_function(SETTLED, timeout=20000)
    return context, page, prompts


def _leave_link(page_case):
    """The way out of the page: whichever navigation shows it, the phone's
    bottom tab bar or the wide screen's sidebar."""
    return 'a[href$="%s"]:visible' % page_case[4]


def _press(page, selector, how="tap"):
    """Touch tap or mouse click on a control that already owns its own centre:
    right after a page change a view transition can still cover it."""
    target = page.locator(selector).first
    target.wait_for(state="visible", timeout=10000)
    target.scroll_into_view_if_needed()
    page.wait_for_function(
        "(el) => { const r = el.getBoundingClientRect();"
        " const hit = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);"
        " return !!hit && el.contains(hit); }",
        arg=target.element_handle(), timeout=10000)
    if how == "tap":
        target.tap()
    else:
        target.click()


def _wait_dialog_open(page):
    page.wait_for_function(
        "() => { const d = document.querySelector('%s'); return !!d && d.open; }" % DIALOG,
        timeout=5000)


@pytest.mark.parametrize("how", ["tap", "click"])
@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize(
    "viewport", [VIEWPORT_MIN_SUPPORTED, VIEWPORT_DESKTOP], ids=["360", "1280"])
@pytest.mark.parametrize("page_case", PAGES, ids=PAGE_IDS)
def test_every_save_bar_page_asks_before_an_in_app_link(
        new_context, server, page_case, viewport, lang, how):
    """with an unsaved edit, the navigation out of the page opens the shared question in the
    reader's language instead of leaving, and the browser's own prompt never appears"""
    context, page, prompts = _open(new_context, server, page_case, viewport, lang)
    try:
        here = page.url
        _press(page, _leave_link(page_case), how)
        _wait_dialog_open(page)
        assert page.url == here
        assert prompts == []
        title, text, primary, secondary, quiet = WORDS[lang]
        assert page.locator(DIALOG + " .modal__title").inner_text() == title
        assert page.locator(DIALOG + " .modal__body").inner_text() == text
        assert page.locator(PRIMARY).inner_text() == primary
        assert page.locator(SECONDARY).inner_text() == secondary
        assert page.locator(QUIET).inner_text() == quiet
        page.wait_for_function(
            "() => document.activeElement"
            " && document.activeElement.hasAttribute('data-leave-dialog-quiet')",
            timeout=5000)
    finally:
        context.close()


@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize(
    "viewport", [VIEWPORT_MIN_SUPPORTED, VIEWPORT_DESKTOP], ids=["360", "1280"])
def test_the_question_fits_both_themes_on_a_form_page(new_context, server, viewport, lang):
    """44 px actions, no cut text and no sideways scroll, on a page-mode bar's own page"""
    context, page, _prompts = _open(new_context, server, PAGES[1], viewport, lang)
    try:
        _press(page, _leave_link(PAGES[1]))
        _wait_dialog_open(page)
        for theme in UI_THEMES_EXPLICIT:
            _set_ui_theme(page, theme)
            for selector in (PRIMARY, SECONDARY, QUIET):
                box = page.locator(selector).bounding_box()
                assert box["height"] >= 43.5 and box["width"] >= 43.5, (selector, box)
                assert box["x"] >= 0 and box["x"] + box["width"] <= viewport["width"] + 0.5, box
                assert page.eval_on_selector(
                    selector, "el => el.scrollWidth <= el.clientWidth + 1"), (selector, lang)
        _assert_no_page_overflow(page, "leave dialog on a form page")
    finally:
        context.close()


@pytest.mark.parametrize("page_case", PAGES, ids=PAGE_IDS)
def test_a_clean_page_never_asks(new_context, server, page_case):
    """with nothing changed the navigation is a plain link again"""
    context, page, _prompts = _open(new_context, server, page_case, edit=False)
    try:
        _press(page, _leave_link(page_case))
        page.wait_for_url("**" + page_case[4], timeout=15000)
    finally:
        context.close()


@pytest.mark.parametrize("page_case", PAGES, ids=PAGE_IDS)
def test_discard_leaves_the_page_without_saving(new_context, server, page_case):
    """Discard goes where the person tapped and the edit is dropped"""
    context, page, prompts = _open(new_context, server, page_case)
    try:
        _press(page, _leave_link(page_case))
        _wait_dialog_open(page)
        page.click(SECONDARY)
        page.wait_for_url("**" + page_case[4], timeout=15000)
        assert prompts == []
    finally:
        context.close()


@pytest.mark.parametrize("page_case", PAGES, ids=PAGE_IDS)
def test_save_and_continue_saves_then_lands_where_the_page_can(new_context, server, page_case):
    """Save and continue saves through the bar's own Save: it lands on the tapped page where
    that page's save accepts it as a return target, and stays on the page where it does not"""
    destination, returns = page_case[4], page_case[5]
    context, page, prompts = _open(new_context, server, page_case)
    try:
        _press(page, _leave_link(page_case))
        _wait_dialog_open(page)
        with page.expect_navigation(timeout=20000):
            page.click(PRIMARY)
        page.wait_for_function("() => document.readyState === 'complete'", timeout=15000)
        if returns:
            page.wait_for_url("**" + destination + "*", timeout=15000)
        else:
            # The save goes where this page's own save goes; the tapped
            # address is not one it accepts, so the person is not sent there.
            assert destination not in page.url, page.url
        assert prompts == []
    finally:
        context.close()


def test_a_post_of_another_form_asks_and_discard_lets_it_through(new_context, server):
    """the language switch in the More sheet is a post, not a link: with an unsaved edit it asks
    first, and Discard lets it through"""
    context, page, prompts = _open(new_context, server, PAGES[0])
    try:
        _press(page, "details.tab-bar__more > summary")
        switch = 'form[action="/ui-lang"] button[value="fr"]'
        page.locator(switch).first.wait_for(state="visible", timeout=5000)
        _press(page, switch)
        _wait_dialog_open(page)
        assert page.get_attribute("html", "lang") == "en"
        page.click(SECONDARY)
        page.wait_for_function("() => document.documentElement.lang === 'fr'", timeout=15000)
        assert prompts == []
    finally:
        context.close()
