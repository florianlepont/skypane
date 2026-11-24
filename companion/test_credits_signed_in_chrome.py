"""The credits page for a signed-in person carries no navigation at all (no sidebar, tab bar,
space switch, frame button or Console entries): only a back link to Account. A visitor with no
session still gets the page as before. Every assertion reads the served page or a browser."""
import pytest

import fleet_console_support as fx
from co_manager_browser_support import LONG_OWNER, Rig, _no_sideways_scroll
from companion import auth, prefs
from companion.test_browser_ux_helpers import VIEWPORT_MIN_SUPPORTED
from companion_markup import parse_html

NAVIGATION = (
    "dashboard-sidebar", "sidebar-nav", "tab-bar", "frame-menu", "space-switch",
    "mobile-nav", "brand__link")


@pytest.fixture(autouse=True)
def _english():
    prefs.set_request_prefs(lang="en")
    yield


@pytest.fixture
def rig(app_server_in_process):
    return Rig(app_server_in_process)


def _credits(rig, who, lang="en"):
    cookie = {"admin": fx.admin_cookie(rig.state_dir),
              "owner": fx.user_cookie(rig.state_dir, email=LONG_OWNER)}.get(who)
    return fx.get(rig.server, cookie, "/credits", headers={"Accept-Language": lang})[2]


@pytest.mark.parametrize("who", ["owner", "admin"])
@pytest.mark.parametrize("lang, back", [("en", "Back to Account"), ("fr", "Retour au compte")])
def test_a_signed_in_person_sees_no_navigation_only_a_back_link_to_account(rig, who, lang, back):
    body = _credits(rig, who, lang)
    for marker in NAVIGATION:
        assert marker not in body, marker
    tree = parse_html(body)
    assert tree.select("nav") == [] and tree.select("aside") == []
    assert tree.select_one("main h1").text().strip() == ("Credits" if lang == "en" else "Crédits")
    hrefs = [a.attrs["href"] for a in tree.select("a") if "href" in a.attrs
             and not a.attrs["href"].startswith("#") and "credit" not in a.attrs.get("class", "")
             and a.attrs.get("target") != "_blank"]
    assert hrefs == ["/account"], hrefs
    assert back in tree.select_one(".credits-back").text()
    assert tree.select("form[action='/logout']") == []


def test_a_visitor_with_no_session_keeps_the_public_page(rig):
    body = _credits(rig, None)
    tree = parse_html(body)
    assert tree.select_one(".credits-back a").attrs["href"] == "/login"
    assert "Back to sign in" in body


@pytest.mark.browser
@pytest.mark.parametrize("who", ["owner", "admin"])
@pytest.mark.parametrize("viewport", [VIEWPORT_MIN_SUPPORTED, {"width": 1280, "height": 900}],
                         ids=["360", "1280"])
def test_the_signed_in_credits_page_draws_no_navigation_in_a_browser(
        new_context, rig, who, viewport):
    context = new_context(viewport=viewport)
    context.add_cookies([
        rig.cookie(who),
        {"name": auth.UI_LANG_COOKIE_NAME, "value": "fr", "url": rig.server.base_url()}])
    page = context.new_page()
    page.goto(rig.url("/credits"))
    page.locator("main h1").wait_for(state="visible")
    visible = page.evaluate(
        """() => ['.dashboard-sidebar', '.tab-bar', '.frame-menu', '.brand__link',
                  'nav'].filter(sel => [...document.querySelectorAll(sel)].some(
                      el => el.checkVisibility() && el.getBoundingClientRect().width > 0))""")
    assert visible == [], visible
    back = page.locator(".credits-back a")
    assert back.get_attribute("href") == "/account"
    box = back.bounding_box()
    assert box["height"] >= 44 - 0.5 and box["x"] >= 0
    content = page.locator("main").bounding_box()
    assert content["x"] >= 0 and content["x"] + content["width"] <= viewport["width"]
    assert _no_sideways_scroll(page)
    back.click()
    page.wait_for_url("**/account")

