"""Real-browser checks of the Users page rows: an email cut with an ellipsis instead of broken
mid-word, a status pill (Active, Invited) and a You mark with readable ink, an explained disabled
switch on the signed-in administrator's own row, a co-manager's frame count, and the Copy
invitation message button (Clipboard API, selection fallback, hidden without script)."""
import io

import pytest
from PIL import Image

import fleet_console_support as fx
from companion import auth
from companion.test_browser_ux_helpers import (
    VIEWPORT_DESKTOP, VIEWPORT_MIN_SUPPORTED, _assert_no_page_overflow, _no_js_page)
from companion_app_server import session_cookie_for_state_dir
from server import fleet_db
from skypane_contrast_check import WCAG_AA_NORMAL_TEXT, contrast_ratio

pytestmark = pytest.mark.browser

LONG_EMAIL = "a" * 46 + "@example.test"
ACTIVE_EMAIL = "signed.in@example.test"

_SETTLED = """() => document.readyState === 'complete' && document.getAnimations().every(
  (a) => a.playState !== 'running' || a.effect.getComputedTiming().iterations === Infinity)"""
_OWNS_CENTRE = (
    "s => { const e = document.querySelector(s); if (!e) return false;"
    " const r = e.getBoundingClientRect();"
    " const hit = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);"
    " return hit === e || e.contains(hit); }")


def _seed(state_dir):
    seed = fx.seed_fleet(state_dir)
    conn = fleet_db.connect(state_dir)
    try:
        fleet_db.add_co_manager(conn, seed.live_id, seed.user_id, seed.admin_id)
        fleet_db.add_user(conn, LONG_EMAIL, "user")
        signed_in = fleet_db.add_user(conn, ACTIVE_EMAIL, "user")
        conn.execute(
            "UPDATE users SET iss = ?, sub = ? WHERE id = ?",
            ("https://issuer.example.test/", "subject-1", signed_in))
        conn.commit()
    finally:
        conn.close()
    return seed


@pytest.fixture(scope="module")
def server(module_app_server_factory):
    return module_app_server_factory(seed=_seed)


def _open(new_context, server, viewport, lang="en", scheme="light", **context_args):
    context = new_context(viewport=viewport, color_scheme=scheme, **context_args)
    context.add_cookies([{
        "name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": server.base_url()}])
    name, value = session_cookie_for_state_dir(server.state_dir, fx.ADMIN_EMAIL).split("=", 1)
    context.add_cookies([{
        "name": name, "value": value, "url": server.base_url(), "httpOnly": True,
        "sameSite": "Strict"}])
    page = context.new_page()
    page.goto(server.base_url() + "/users")
    page.locator("main").wait_for(state="visible")
    page.wait_for_function(_SETTLED)
    page.wait_for_function(_OWNS_CENTRE, arg="a.page-header__action", timeout=10000)
    return context, page


def _row(page, email):
    return page.locator(".users-row", has=page.locator(".users-email", has_text=email))


def _rgb(css):
    """#RRGGBB of an opaque computed colour, in rgb() or color(srgb ...) notation."""
    inner = css[css.index("(") + 1:-1]
    scale = 255.0
    if css.startswith("color(srgb"):
        inner = inner[len("srgb"):]
    else:
        scale = 1.0
    parts = [p for p in inner.replace("/", " ").replace(",", " ").split() if p]
    numbers = [float(p) for p in parts]
    assert len(numbers) == 3 or numbers[3] == 1, css
    return "#%02X%02X%02X" % tuple(round(n * (255.0 if scale == 255.0 else 1.0)) for n in numbers[:3])


@pytest.mark.parametrize("viewport", [VIEWPORT_MIN_SUPPORTED, VIEWPORT_DESKTOP], ids=["360", "1280"])
@pytest.mark.parametrize("lang", ["en", "fr"])
def test_a_long_email_wraps_inside_its_cell_and_keeps_its_full_value_as_the_title(
        new_context, server, viewport, lang):
    context, page = _open(new_context, server, viewport, lang)
    try:
        email = _row(page, LONG_EMAIL).locator(".users-email")
        facts = email.evaluate(
            """el => { const cs = getComputedStyle(el);
              return {over: cs.textOverflow, wrap: cs.overflowWrap, scroll: el.scrollWidth,
                      client: el.clientWidth, title: el.title, text: el.textContent,
                      cell: el.closest('.users-cell').getBoundingClientRect().right,
                      right: el.getBoundingClientRect().right}; }""")
        assert facts["over"] != "ellipsis" and facts["wrap"] == "anywhere"
        assert facts["scroll"] <= facts["client"] + 1, "the address must wrap, not overflow"
        assert facts["right"] <= facts["cell"] + 0.5
        assert facts["title"] == facts["text"] == LONG_EMAIL
        assert not _assert_no_page_overflow(page, "users")
    finally:
        context.close()


@pytest.mark.parametrize("scheme", ["light", "dark"])
def test_status_pills_say_active_invited_and_you_with_readable_ink(
        new_context, server, scheme):
    context, page = _open(new_context, server, VIEWPORT_MIN_SUPPORTED, "en", scheme)
    try:
        page.evaluate("t => document.documentElement.setAttribute('data-ui-theme', t)", scheme)
        page.wait_for_function(_SETTLED)
        for row in page.locator(".users-row").all():
            assert row.locator(".users-status .users-pill:visible").count() == 1
        status = {}
        for email, expected in ((ACTIVE_EMAIL, "Active"), (LONG_EMAIL, "Invited, not signed in yet")):
            pill = _row(page, email).locator(".users-status .users-pill:visible")
            assert pill.inner_text() == expected
            status[email] = pill
        invited = status[LONG_EMAIL]
        assert "has not signed in yet" in invited.get_attribute("title")
        assert invited.get_attribute("aria-label").startswith("Invited, not signed in yet.")
        own = _row(page, "admin@example.test").locator(".users-pills .users-pill")
        assert own.inner_text() == "You"
        looks = {}
        for name, email in (("active", ACTIVE_EMAIL), ("invited", LONG_EMAIL)):
            pill = status[email]
            pill.scroll_into_view_if_needed()
            page.wait_for_function(_SETTLED)
            page.wait_for_timeout(300)
            box = pill.bounding_box()
            shot = Image.open(io.BytesIO(page.screenshot())).convert("RGB")
            fill = shot.getpixel((round(box["x"] + 4), round(box["y"] + box["height"] / 2)))
            looks[name] = (pill.evaluate("el => getComputedStyle(el).color"), fill)
        assert looks["active"][1] != looks["invited"][1]
        for ink, fill in looks.values():
            assert contrast_ratio(_rgb(ink), "#%02X%02X%02X" % fill) >= WCAG_AA_NORMAL_TEXT, (
                ink, fill)
    finally:
        context.close()


def test_the_own_switch_is_disabled_and_says_why(new_context, server):
    context, page = _open(new_context, server, VIEWPORT_MIN_SUPPORTED)
    try:
        row = _row(page, "admin@example.test")
        switch = row.locator("button.switch")
        assert switch.is_disabled()
        ids = switch.get_attribute("aria-describedby").split()
        assert ids
        hint = " ".join(page.locator("#" + i).inner_text() for i in ids)
        assert "You cannot disable or demote yourself." in hint
        assert all(page.locator("#" + i).evaluate("el => el.checkVisibility()") for i in ids)
        assert _row(page, ACTIVE_EMAIL).locator("button.switch").is_enabled()
        assert _row(page, ACTIVE_EMAIL).locator("button.switch").get_attribute(
            "aria-describedby") is None
    finally:
        context.close()


@pytest.mark.parametrize("lang,expected,none", [
    ("en", "1 frame · co-manager", "0 frames"),
    ("fr", "1 cadre · co-gestionnaire", "0 cadres")])
def test_a_co_manager_shows_the_frame_they_manage(new_context, server, lang, expected, none):
    context, page = _open(new_context, server, VIEWPORT_MIN_SUPPORTED, lang)
    try:
        assert _row(page, "plain@example.test").locator(
            ".users-cell--frames").inner_text() == expected
        assert none in _row(page, ACTIVE_EMAIL).locator(".users-cell--frames").inner_text()
        assert "co-" not in _row(page, ACTIVE_EMAIL).locator(".users-cell--frames").inner_text()
    finally:
        context.close()


def _expected_message(server, email, lang):
    url = server.base_url()
    if lang == "fr":
        return ("Bonjour, vous êtes invité(e) sur SkyPane. Ouvrez %s et connectez-vous "
                "avec l’adresse %s." % (url, email))
    return "Hello, you have been invited to SkyPane. Open %s and sign in with %s." % (url, email)


@pytest.mark.parametrize("lang", ["en", "fr"])
def test_copy_invitation_message_writes_the_clipboard(new_context, server, lang):
    context, page = _open(
        new_context, server, VIEWPORT_MIN_SUPPORTED, lang,
        permissions=["clipboard-read", "clipboard-write"])
    try:
        row = _row(page, LONG_EMAIL)
        button = row.locator("button.users-copy")
        assert button.bounding_box()["height"] >= 44
        assert _row(page, ACTIVE_EMAIL).locator("button.users-copy").count() == 0
        button.click()
        want = _expected_message(server, LONG_EMAIL, lang)
        page.wait_for_function(
            "w => navigator.clipboard.readText().then((t) => t === w)", arg=want)
        page.wait_for_function(
            "([el, t]) => el.querySelector('.copy-btn__label').textContent === t",
            arg=[button.element_handle(), "Copied" if lang == "en" else "Copié"])
        assert button.locator(".copy-btn__label").is_visible()
        assert "secret" not in want and "token" not in want
    finally:
        context.close()


def test_copy_falls_back_to_a_text_selection_when_the_clipboard_api_refuses(
        new_context, server):
    context, page = _open(new_context, server, VIEWPORT_MIN_SUPPORTED)
    try:
        page.add_init_script(
            """Object.defineProperty(navigator, 'clipboard', {value: {
                 writeText: () => Promise.reject(new Error('refused'))}});
               window.__copied = null;
               const original = document.execCommand.bind(document);
               document.execCommand = function (name) {
                 if (name === 'copy') {
                   window.__copied = document.getSelection().toString(); return true; }
                 return original.apply(document, arguments); };""")
        page.reload()
        page.wait_for_function(_SETTLED)
        page.wait_for_function(_OWNS_CENTRE, arg="a.page-header__action", timeout=10000)
        _row(page, LONG_EMAIL).locator("button.users-copy").click()
        want = _expected_message(server, LONG_EMAIL, "en")
        page.wait_for_function("w => window.__copied === w", arg=want)
    finally:
        context.close()


def test_the_copy_button_is_hidden_without_script(new_context, server):
    with _no_js_page(new_context, server.base_url(), "/users", VIEWPORT_MIN_SUPPORTED) as page:
        assert page.locator("button.users-copy").count() >= 1
        assert not page.locator("button.users-copy").first.is_visible()
        assert page.locator(".users-row").first.is_visible()


def test_the_desktop_table_keeps_the_pills_and_the_copy_button_in_their_columns(
        new_context, server):
    context, page = _open(new_context, server, VIEWPORT_DESKTOP, permissions=["clipboard-read"])
    try:
        row = _row(page, LONG_EMAIL)
        box = row.locator(".users-cell--invite").bounding_box()
        button = row.locator("button.users-copy").bounding_box()
        assert button["x"] >= box["x"] - 0.5
        assert button["x"] + button["width"] <= box["x"] + box["width"] + 0.5
        assert row.locator(".users-status .users-pill:visible").inner_text() == "Invited, not signed in yet"
        _assert_no_page_overflow(page, "users")
    finally:
        context.close()
