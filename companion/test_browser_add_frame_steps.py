"""Real-browser checks of the two-step Add a frame page: Step 1 names the
frame, Step 2 takes its pairing code, one Add frame button; English and French
at 360 and 1280px in both themes, 44px targets, no sideways scroll, readable
text, no motion under reduced motion, the typed name kept after a refusal and
applied after a success, and the administrator-only Owner field."""
import re

import animation_settle
import pytest

import fleet_console_support as fx
from co_manager_browser_support import MIN_TAP_PX, _no_sideways_scroll
from companion import auth
from companion.test_browser_ux_helpers import VIEWPORT_MIN_SUPPORTED, _set_ui_theme
from server import fleet_db

pytestmark = pytest.mark.browser

VIEWPORTS = (VIEWPORT_MIN_SUPPORTED, {"width": 1280, "height": 900})
HOME_URL = re.compile(r".*/devices/[^/?]+/(\?.*)?$")
TEXT = {
    "en": {"title": "Add a frame", "step1": "Step 1: name it",
           "step2": "Step 2: enter its pairing code", "submit": "Add frame",
           "back": "Cancel", "invalid": "Enter a name of 1 to 40 characters."},
    "fr": {"title": "Ajouter un cadre", "step1": "Étape 1 : nommez-le",
           "step2": "Étape 2 : saisissez son code d’association",
           "submit": "Ajouter le cadre", "back": "Annuler",
           "invalid": "Saisissez un nom de 1 à 40 caractères."},
}


def _open(new_context, server, cookie, lang="en", theme=None,
          viewport=VIEWPORT_MIN_SUPPORTED, **context_kwargs):
    context = new_context(viewport=viewport, **context_kwargs)
    name, value = cookie.split("=", 1)
    context.add_cookies([
        {"name": name, "value": value, "url": server.base_url(), "httpOnly": True,
         "sameSite": "Strict"},
        {"name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": server.base_url()}])
    page = context.new_page()
    page.goto(server.base_url() + "/pair-frame")
    page.locator("main").wait_for(state="visible")
    page.wait_for_function("() => document.readyState === 'complete'")
    if theme is not None:
        _set_ui_theme(page, theme)
    return context, page


def _height(page, selector):
    return round(page.locator(selector).first.bounding_box()["height"], 2)


def _luminance(rgb):
    def part(value):
        value /= 255
        return value / 12.92 if value <= 0.03928 else ((value + 0.055) / 1.055) ** 2.4
    return 0.2126 * part(rgb[0]) + 0.7152 * part(rgb[1]) + 0.0722 * part(rgb[2])


def _rgb(css_colour):
    return tuple(float(n) for n in re.findall(r"[\d.]+", css_colour)[:3])


@pytest.fixture
def seeded(app_server_in_process):
    server = app_server_in_process
    seed = fx.seed_fleet(server.state_dir)
    fx.issue_code(server.state_dir, seed.pending_id)
    return server, seed


def _name_of_pending(server):
    conn = fleet_db.connect(server.state_dir)
    try:
        return fleet_db.get_device_by_mac(conn, fx.MAC_PENDING)["name"]
    finally:
        conn.close()


@pytest.mark.parametrize("theme", ["light", "dark"])
@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("viewport", VIEWPORTS, ids=["360", "1280"])
@pytest.mark.parametrize("role", ["user", "admin"])
def test_the_page_is_two_numbered_steps_that_fit(new_context, seeded, role, viewport, lang, theme):
    server, _seed = seeded
    cookie = fx.user_cookie(server.state_dir) if role == "user" else fx.admin_cookie(
        server.state_dir)
    context, page = _open(new_context, server, cookie, lang, theme, viewport)
    try:
        text = TEXT[lang]
        assert page.locator("main h1").inner_text() == text["title"]
        steps = page.locator("form.pair-card .pair-step")
        assert steps.count() == 2
        assert steps.nth(0).locator("h2").inner_text() == text["step1"]
        assert steps.nth(1).locator("h2").inner_text() == text["step2"]
        assert steps.nth(0).locator("#pair-name").count() == 1
        assert steps.nth(1).locator("#pair-code").count() == 1
        assert page.locator("label[for=pair-name]").count() == 1
        assert page.locator("label[for=pair-code]").count() == 1
        assert page.locator("form.pair-card button[type=submit]").inner_text() == text["submit"]
        assert page.locator("form.pair-card button[type=submit]").count() == 1
        assert (page.locator("#pair-owner").count() == 1) == (role == "admin")
        for selector in ("#pair-name", "#pair-code", "button[type=submit]",
                         "a.pair-form__cancel"):
            assert _height(page, selector) >= MIN_TAP_PX, selector
        assert page.locator("#pair-code").evaluate(
            "e => getComputedStyle(e).textTransform") == "uppercase"
        assert page.locator("#pair-name").evaluate(
            "e => getComputedStyle(e).textTransform") == "none"
        card = page.locator("form.pair-card").bounding_box()
        assert card["x"] >= -1 and card["x"] + card["width"] <= viewport["width"] + 1
        assert _no_sideways_scroll(page)
    finally:
        context.close()


@pytest.mark.parametrize("theme", ["light", "dark"])
@pytest.mark.parametrize("lang", ["en", "fr"])
def test_the_step_titles_are_readable(new_context, seeded, lang, theme):
    server, _seed = seeded
    context, page = _open(new_context, server, fx.user_cookie(server.state_dir), lang, theme)
    try:
        page.wait_for_function(animation_settle.SETTLED, timeout=15000)
        for selector in (".pair-step h2", ".pair-step .text-label"):
            colours = page.eval_on_selector(
                selector, "e => { const s = getComputedStyle(e);"
                " return [s.color, getComputedStyle(e.closest('.pair-card')).backgroundColor]; }")
            lighter, darker = sorted((_luminance(_rgb(c)) for c in colours), reverse=True)
            assert (lighter + 0.05) / (darker + 0.05) >= 4.5, (selector, colours)
    finally:
        context.close()


def test_the_steps_add_no_motion_under_reduced_motion(new_context, seeded):
    server, _seed = seeded
    context, page = _open(
        new_context, server, fx.user_cookie(server.state_dir), reduced_motion="reduce")
    try:
        assert page.evaluate(
            "() => document.querySelector('form.pair-card').getAnimations({subtree: true})"
            ".filter(a => a.playState === 'running').length") == 0
        assert page.locator(".pair-step").first.evaluate(
            "e => getComputedStyle(e).animationName") == "none"
    finally:
        context.close()


@pytest.mark.parametrize("lang", ["en", "fr"])
def test_a_named_frame_is_paired_under_its_name(new_context, seeded, lang):
    server, seed = seeded
    context, page = _open(new_context, server, fx.user_cookie(server.state_dir), lang)
    try:
        page.fill("#pair-name", "Orly kitchen")
        page.fill("#pair-code", fx.FAKE_CODE)
        page.locator("form.pair-card button[type=submit]").click()
        page.wait_for_url(HOME_URL)
        assert _name_of_pending(server) == "Orly kitchen"
        assert "Orly kitchen" in page.locator("body").inner_text()
    finally:
        context.close()


@pytest.mark.parametrize("scripts", [True, False])
def test_a_refused_code_keeps_the_name_for_the_retry_and_stores_nothing(
        new_context, seeded, scripts):
    server, _seed = seeded
    context, page = _open(
        new_context, server, fx.user_cookie(server.state_dir), java_script_enabled=scripts)
    try:
        page.fill("#pair-name", 'Kitchen "<b>"')
        page.fill("#pair-code", "kkkk-2222")
        page.locator("form.pair-card button[type=submit]").click()
        page.locator(".pair-form .field-error").wait_for(state="visible")
        assert page.input_value("#pair-name") == 'Kitchen "<b>"'
        assert page.locator("form.pair-card b").count() == 0
        assert "Kitchen" not in page.url
        assert [c for c in context.cookies() if c["name"] == "sp_pair_code"] == []
        assert not _name_of_pending(server)
        page.fill("#pair-code", fx.FAKE_CODE)
        page.locator("form.pair-card button[type=submit]").click()
        page.wait_for_url(HOME_URL)
        assert _name_of_pending(server) == 'Kitchen "<b>"'
    finally:
        context.close()


@pytest.mark.parametrize("lang", ["en", "fr"])
def test_an_invalid_name_is_refused_in_words_beside_the_name_field(new_context, seeded, lang):
    server, _seed = seeded
    context, page = _open(new_context, server, fx.user_cookie(server.state_dir), lang)
    try:
        page.evaluate("document.querySelector('#pair-name').removeAttribute('maxlength')")
        page.fill("#pair-name", "z" * 41)
        page.fill("#pair-code", fx.FAKE_CODE)
        page.locator("form.pair-card button[type=submit]").click()
        error = page.locator("#pair-name-error")
        error.wait_for(state="visible")
        assert error.inner_text() == TEXT[lang]["invalid"]
        assert page.locator("#pair-name").get_attribute("aria-describedby") == "pair-name-error"
        assert page.locator("#pair-name").get_attribute("aria-invalid") == "true"
        assert _no_sideways_scroll(page)
        assert not _name_of_pending(server)
    finally:
        context.close()


def test_the_name_field_limits_what_can_be_typed(new_context, seeded):
    server, _seed = seeded
    context, page = _open(new_context, server, fx.user_cookie(server.state_dir))
    try:
        page.fill("#pair-name", "y" * 60)
        assert page.input_value("#pair-name") == "y" * 40
    finally:
        context.close()
