"""The head metadata of every page shell variant: the viewport covers the device (so the
safe-area insets are non-zero on a notched phone), and both theme-color tags are present and
match the page background the stylesheet paints, so the Safari bars never show a near-black
strip. Assertions parse the rendered documents and the served stylesheet."""
import re

import pytest

import companion_markup
from companion import layout, login_page, prefs
from companion_app_server import served_stylesheet
from companion_markup import custom_properties

_DARK_AT_RULE = ("@media (prefers-color-scheme: dark)",)


@pytest.fixture(autouse=True)
def _reset_request_state():
    prefs.set_request_prefs("en")
    prefs.set_request_principal(None)
    yield
    prefs.set_request_prefs("en")
    prefs.set_request_principal(None)


@pytest.fixture(scope="module")
def served_css(module_app_server_factory):
    return served_stylesheet(module_app_server_factory())


def _documents(theme):
    """Every distinct shell: the authenticated page shell, the login shell (login page, refusal
    and error pages) and the script-free interstitial."""
    return {
        "page_shell": layout.page_shell("T", "home", "<p>b</p>", ui_theme=theme),
        "page_shell_console": layout.page_shell(
            "T", "health", "<p>b</p>", ui_theme=theme, health_alert="warn",
            device_config={"a": 1}),
        "login": login_page.render_login_page(theme, auth0_enabled=True),
        "not_invited": login_page.not_invited_page(theme),
        "unverified": login_page.unverified_email_page(theme),
        "sign_in_error": login_page.sign_in_error_page("expired", theme),
        "interstitial": login_page.interstitial_page(
            "in", "/", login_page.CONTINUE_TARGET_HOME, ui_theme=theme),
        "not_found": login_page.not_found_page(theme, None),
        "forbidden": login_page.forbidden_page(theme, None),
        "unavailable": login_page.unavailable_page(theme),
    }


def _metas(html):
    doc = companion_markup.parse_html(html)
    viewport = [n for n in doc.select("meta") if n.attrs.get("name") == "viewport"]
    colours = [n for n in doc.select("meta") if n.attrs.get("name") == "theme-color"]
    return viewport, colours


@pytest.mark.parametrize("theme", ("auto", "light", "dark"))
def test_every_shell_covers_the_device_and_carries_both_theme_colours(theme):
    for name, html in _documents(theme).items():
        viewport, colours = _metas(html)
        assert len(viewport) == 1, name
        content = viewport[0].attrs["content"]
        assert "viewport-fit=cover" in content, name
        assert "width=device-width" in content and "initial-scale=1" in content, name
        assert sorted(n.attrs.get("media") for n in colours) == [
            "(prefers-color-scheme: dark)", "(prefers-color-scheme: light)"], name
        assert all(re.fullmatch(r"#[0-9A-F]{6}", n.attrs["content"]) for n in colours), name


def test_auto_lets_each_scheme_pick_its_own_colour_and_explicit_themes_override_both():
    by_theme = {}
    for theme in ("auto", "light", "dark"):
        _, colours = _metas(_documents(theme)["page_shell"])
        by_theme[theme] = {n.attrs["media"]: n.attrs["content"] for n in colours}
    light, dark = "(prefers-color-scheme: light)", "(prefers-color-scheme: dark)"
    assert by_theme["auto"][light] != by_theme["auto"][dark]
    assert set(by_theme["light"].values()) == {by_theme["auto"][light]}
    assert set(by_theme["dark"].values()) == {by_theme["auto"][dark]}


def test_theme_colours_are_the_top_stop_of_the_page_background(served_css):
    """the chrome tint is the very colour the page background starts with, in each scheme"""
    _, colours = _metas(_documents("auto")["page_shell"])
    by_media = {n.attrs["media"]: n.attrs["content"].upper() for n in colours}
    light = custom_properties(served_css, ":root")["--sky-top"].upper()
    dark = custom_properties(served_css, ":root", at_rules=_DARK_AT_RULE)["--sky-top"].upper()
    assert by_media["(prefers-color-scheme: light)"] == light
    assert by_media["(prefers-color-scheme: dark)"] == dark


def test_a_page_with_a_tab_bar_holds_its_first_paint_until_the_bar_is_parsed():
    """the head asks the browser to wait for the marker that follows the tab bar, so a page
    change's new snapshot holds the whole bar; a page with no bar asks for nothing"""
    html = layout.page_shell("T", "home", "<p>b</p>", ui_theme="light", device_config={"a": 1})
    assert layout.page_shell("T", "home", "<p>b</p>", ui_theme="light").count("rel=\"expect\"") == 0
    assert html.count('<link rel="expect" href="#tab-bar-end" blocking="render">') == 1
    assert html.index('rel="expect"') < html.index("</head>")
    assert html.index("</nav><span id=\"tab-bar-end\" hidden></span>") > html.index('class="tab-bar"')
    assert html.count('id="tab-bar-end"') == 1
