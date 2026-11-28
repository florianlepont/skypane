# SPDX-License-Identifier: AGPL-3.0-only
"""Real-browser checks of who sees which airlines: the administrator's editor
lists the airlines and the merged unidentified prefixes of the whole fleet, a
user's Airlines page lists only what their own frame saw and never carries
another user's airline, prefix or callsign (page text, hidden dialogs
included). English and French, at 360 and 1280 px, no horizontal overflow."""
import animation_settle
import pytest

from companion import auth
from companion.airline_fleet_world import World
from companion.test_browser_ux_helpers import _assert_no_page_overflow

pytestmark = pytest.mark.browser

SIZES = ((360, 740), (1280, 900))
_SETTLED = animation_settle.SETTLED
WORLD = {}
PURPOSE = {"en": "Airlines your frame has seen", "fr": "Les compagnies vues par votre cadre"}
SEEN_CARD = "li.collection-item:not(:has(.collection-card--unseen)) .collection-card__name"
OTHER_USER = {
    "a": ("Quux", "QUX", "VLG", "BBB", "Bravo", "Echo", "Balcony", "E190"),
    "b": ("Zorro", "ZOR", "AAA", "Kitchen", "B738")}


def _seed(state_dir):
    WORLD["world"] = World(state_dir)


@pytest.fixture(scope="module")
def server(module_app_server_factory):
    return module_app_server_factory(seed=_seed)


def _open(new_context, server, cookie, path, size, lang):
    context = new_context(viewport={"width": size[0], "height": size[1]})
    name, value = cookie.split("=", 1)
    context.add_cookies([
        {"name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": server.base_url()},
        {"name": name, "value": value, "url": server.base_url(),
         "httpOnly": True, "sameSite": "Strict"}])
    page = context.new_page()
    page.goto(server.base_url() + path)
    page.wait_for_function(_SETTLED, timeout=15000)
    return context, page


@pytest.mark.parametrize("lang", ("en", "fr"))
@pytest.mark.parametrize("size", SIZES)
def test_admin_editor_shows_the_whole_fleet(new_context, server, size, lang):
    world = WORLD["world"]
    context, page = _open(new_context, server, world.admin, "/airlines/manage", size, lang)
    try:
        assert page.locator(".airlines-gap__prefix").all_inner_texts() == [
            "AAA", "BBB", "CCC", "LLL"]
        samples = [text[:6] for text in page.locator(".airlines-gap__meta").all_inner_texts()]
        assert samples == ["AAA101", "BBB301", "CCC302", "LLL601"]
        known = page.locator(".airlines-missing__name").all_inner_texts()
        assert {"Quux Air", "Zorro Air"} <= set(known)
        assert page.locator("tbody.airline-group--gap").first.is_visible()
        assert not _assert_no_page_overflow(page, "the editor", size[0])
    finally:
        context.close()


@pytest.mark.parametrize("lang", ("en", "fr"))
@pytest.mark.parametrize("size", SIZES)
@pytest.mark.parametrize("who", ("a", "b"))
def test_user_page_lists_only_what_their_frame_saw(new_context, server, size, lang, who):
    world = WORLD["world"]
    cookie, frame = (world.user_a, world.a_id) if who == "a" else (world.user_b, world.b_id)
    context, page = _open(
        new_context, server, cookie, "/devices/%s/airlines" % frame, size, lang)
    try:
        seen = sorted(page.locator(SEEN_CARD).all_inner_texts())
        assert seen == (["Air France", "Zorro Air"] if who == "a"
                        else ["Air France", "Quux Air", "Vueling Airlines"])
        assert PURPOSE[lang] in page.locator("main, body").first.inner_text()
        assert page.locator(".airlines-gap, [data-view-panel-resolve-prefix]").count() == 0
        content = page.content()
        for needle in OTHER_USER[who]:
            assert needle not in content, needle
        assert not _assert_no_page_overflow(page, "the user's Airlines page", size[0])
    finally:
        context.close()
