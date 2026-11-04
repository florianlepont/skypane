"""Real-browser proof of the Console / My frame switch: visible on a Console
page and on a personal page for an administrator at 360 and 1280 px in English
and French, light and dark; both segments 44px high and hit-testable, the
current one marked by aria-current and a different fill; no wrapping and no
horizontal overflow; one tap moves between the spaces; a user never sees it."""
import time
import pytest

from nav_spaces_support import (
    MIN_TAP_PX, admin_page as _admin_page, assert_bar as _assert_bar,
    own_frame_home as _own_frame_home, user_page as _user_page)
from companion.test_browser_ux_helpers import (
    VIEWPORT_DESKTOP, VIEWPORT_MIN_SUPPORTED, _assert_no_page_overflow)

pytestmark = pytest.mark.browser

_SEGMENTS = (
    "() => [...document.querySelectorAll('.space-switch')]"
    ".filter(n => n.getClientRects().length > 0)"
    ".map(n => [...n.querySelectorAll('.space-switch__segment')].map(a => {"
    " const b = a.getBoundingClientRect();"
    " const hit = document.elementFromPoint(b.left + b.width / 2, b.top + b.height / 2);"
    " const range = document.createRange(); range.selectNodeContents(a.querySelector('span'));"
    " return {text: a.textContent.trim(), h: b.height, w: b.width, left: b.left,"
    " right: b.right, current: a.getAttribute('aria-current'),"
    " bg: getComputedStyle(a).backgroundColor, hit: !!hit && a.contains(hit),"
    " lines: new Set([...range.getClientRects()].map(r => Math.round(r.top))).size,"
    " hasCheck: !!a.querySelector('.space-switch__check')}; }))")

_VIEWPORTS = (("phone", VIEWPORT_MIN_SUPPORTED), ("desktop", VIEWPORT_DESKTOP))
_LABELS = {"en": ("Console", "My frame"), "fr": ("Console", "Mon cadre")}


def _visible_switch(page):
    """The segments of the one visible switch, read once every visible segment
    owns its own centre and no animation runs (a view transition after
    navigation can still be running)."""
    page.wait_for_function(
        "() => { if (document.readyState !== 'complete') return false;"
        " const all = [...document.querySelectorAll('.space-switch__segment')]"
        ".filter(n => n.getClientRects().length > 0); if (!all.length) return false;"
        " if (document.getAnimations().some((x) => x.playState === 'running' && x.effect.getComputedTiming().iterations !== Infinity)) return false;"
        " return all.every((a) => { const b = a.getBoundingClientRect();"
        " const hit = document.elementFromPoint(b.left + b.width / 2, b.top + b.height / 2);"
        " return !!hit && a.contains(hit); }); }")
    groups = page.evaluate(_SEGMENTS)
    assert len(groups) == 1, groups
    return groups[0]


def _check_switch(page, lang, current_label, where):
    """Assert the switch's resting state, retrying while the browser settles
    (a page change can leave a transition running for a moment); the last
    failure is raised if it never settles."""
    deadline = time.monotonic() + 10
    while True:
        try:
            _assert_switch(page, lang, current_label, where)
            return
        except AssertionError:
            if time.monotonic() > deadline:
                raise
            page.wait_for_timeout(200)


def _assert_switch(page, lang, current_label, where):
    segments = _visible_switch(page)
    assert [seg["text"] for seg in segments] == list(_LABELS[lang]), (where, segments)
    for seg in segments:
        assert seg["h"] >= MIN_TAP_PX, (where, seg)
        assert seg["hit"], (where, seg)
        assert seg["lines"] <= 1, (where, seg)
        assert seg["left"] >= -0.5 and seg["right"] <= page.viewport_size["width"] + 0.5
        is_current = seg["text"] == current_label
        assert (seg["current"] == "page") is is_current, (where, seg)
        assert seg["hasCheck"] is is_current, (where, seg)
    assert segments[0]["bg"] != segments[1]["bg"], (where, segments)
    assert not _assert_no_page_overflow(page, where, page.viewport_size["width"])


@pytest.mark.parametrize("scheme", ["light", "dark"])
@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("name,viewport", _VIEWPORTS)
@pytest.mark.parametrize("space", ["console", "personal"])
def test_the_switch_shows_both_spaces_and_marks_the_current_one(
        new_context, app_server_in_process, space, name, viewport, lang, scheme):
    path = "/fleet" if space == "console" else _own_frame_home
    context, page = _admin_page(
        new_context, app_server_in_process, path, viewport, lang, scheme)
    try:
        current = _LABELS[lang][0 if space == "console" else 1]
        _check_switch(page, lang, current, "%s/%s/%s/%s" % (space, name, lang, scheme))
        if name == "phone":
            # The strip sits under the header and the bar cells stay equal.
            strip = page.locator(".space-strip").bounding_box()
            header = page.locator("header.site-header").bounding_box()
            assert strip["y"] >= header["y"] + header["height"] - 0.5
            assert 59 <= strip["height"] <= 61 + 16
            _assert_bar(page, 5, "bar/%s/%s/%s" % (space, lang, scheme))
        else:
            first = page.locator(".dashboard-sidebar > *:not(.brand)").first
            assert "space-switch" in first.get_attribute("class")
            assert page.locator(".space-strip").is_hidden()
    finally:
        context.close()


@pytest.mark.parametrize("name,viewport", _VIEWPORTS)
def test_one_tap_moves_between_the_two_spaces(
        new_context, app_server_in_process, name, viewport):
    context, page = _admin_page(new_context, app_server_in_process, "/fleet", viewport)
    try:
        _visible_switch(page)
        page.locator(".space-switch__segment:visible", has_text="My frame").click()
        page.wait_for_function(
            "() => !location.pathname.endsWith('/fleet')"
            " && !!document.querySelector('.space-switch__segment[aria-current=page]')"
            " && document.querySelector('.space-switch__segment[aria-current=page]')"
            ".textContent.includes('My frame')")
        _check_switch(page, "en", "My frame", "personal/%s" % name)
        page.locator(".space-switch__segment:visible", has_text="Console").click()
        page.wait_for_function(
            "() => location.pathname === '/fleet'"
            " && document.querySelector('.space-switch__segment[aria-current=page]')"
            ".textContent.includes('Console')")
        _check_switch(page, "en", "Console", "console/%s" % name)
    finally:
        context.close()


@pytest.mark.parametrize("name,viewport", _VIEWPORTS)
@pytest.mark.parametrize("path", ["/", "/flights", "/account"])
def test_a_user_never_sees_the_switch(
        new_context, app_server_in_process, name, viewport, path):
    context, page = _user_page(new_context, app_server_in_process, viewport)
    try:
        if path != "/":
            page.goto(page.url.rstrip("/") + path if path != "/account"
                      else app_server_in_process.base_url() + path)
            page.locator("main").wait_for(state="visible")
        assert page.locator(".space-switch").count() == 0
        assert page.locator(".space-strip").count() == 0
    finally:
        context.close()
