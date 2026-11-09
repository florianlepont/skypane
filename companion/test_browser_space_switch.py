"""Real-browser proof of the Console / My frame switch. Desktop: the two-segment
switch at the top of the sidebar, both segments 44px high and hit-testable, the
current one marked by aria-current and a different fill, no wrapping and no
horizontal overflow. Phone: the first cell of the tab bar, naming the space it
leads to, set apart by an accent outline and a divider, at least 44px, legible
at 360 px. Both in English and French, light and dark; one tap moves between
the spaces; a user never sees it."""
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
_DESKTOP = (("desktop", VIEWPORT_DESKTOP),)
_OTHER_SPACE = {"console": {"en": "My frame", "fr": "Mon cadre"}, "personal": {"en": "Console", "fr": "Console"}}
_BAR_SWITCH = (
    "() => { const a = document.querySelector('.tab-bar > .tab-bar__link--switch');"
    " if (!a) return null; const all = [...document.querySelectorAll('.tab-bar > a, .tab-bar > details')];"
    " const b = a.getBoundingClientRect(); const label = a.querySelector('.tab-bar__label');"
    " const pill = a.querySelector('.tab-bar__pill');"
    " const hit = document.elementFromPoint(b.left + b.width / 2, b.top + b.height / 2);"
    " const range = document.createRange(); range.selectNodeContents(label);"
    " return {first: all[0] === a, text: label.textContent.trim(), w: b.width, h: b.height,"
    " left: b.left, hit: !!hit && a.contains(hit), href: a.getAttribute('href'),"
    " dividerPx: parseFloat(getComputedStyle(a).borderRightWidth),"
    " pillBorder: getComputedStyle(pill).borderTopColor,"
    " pillBorderPx: parseFloat(getComputedStyle(pill).borderTopWidth),"
    " color: getComputedStyle(a).color, sw: label.scrollWidth, cw: label.clientWidth,"
    " lines: new Set([...range.getClientRects()].map(r => Math.round(r.top))).size,"
    " icon: !!a.querySelector('svg'),"
    " big: !!document.querySelector('.space-strip'),"
    " moreHasSwitch: !!document.querySelector('.tab-bar__more-panel .mobile-nav__link--space')}; }")


def _check_bar_switch(page, lang, space, where):
    """The tab bar's leading switch cell, read once it owns its centre."""
    page.wait_for_function(
        "() => { if (document.readyState !== 'complete') return false;"
        " const a = document.querySelector('.tab-bar > .tab-bar__link--switch'); if (!a) return false;"
        " if (document.getAnimations().some((x) => x.playState === 'running' && x.effect.getComputedTiming().iterations !== Infinity)) return false;"
        " const b = a.getBoundingClientRect();"
        " const hit = document.elementFromPoint(b.left + b.width / 2, b.top + b.height / 2);"
        " return !!hit && a.contains(hit); }")
    cell = page.evaluate(_BAR_SWITCH)
    assert cell["first"], (where, cell)
    assert cell["text"] == _OTHER_SPACE[space][lang], (where, cell)
    assert cell["h"] >= MIN_TAP_PX and cell["w"] >= MIN_TAP_PX, (where, cell)
    assert cell["hit"] and cell["icon"], (where, cell)
    assert cell["sw"] <= cell["cw"] and cell["lines"] <= 1, (where, cell)
    assert cell["pillBorderPx"] >= 1, (where, cell)
    assert cell["pillBorder"] == cell["color"], (where, cell)
    assert not cell["big"] and not cell["moreHasSwitch"], (where, cell)
    assert not _assert_no_page_overflow(page, where, page.viewport_size["width"])
    return cell
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
@pytest.mark.parametrize("name,viewport", _DESKTOP)
@pytest.mark.parametrize("space", ["console", "personal"])
def test_the_sidebar_switch_shows_both_spaces_and_marks_the_current_one(
        new_context, app_server_in_process, space, name, viewport, lang, scheme):
    path = "/fleet" if space == "console" else _own_frame_home
    context, page = _admin_page(
        new_context, app_server_in_process, path, viewport, lang, scheme)
    try:
        current = _LABELS[lang][0 if space == "console" else 1]
        _check_switch(page, lang, current, "%s/%s/%s/%s" % (space, name, lang, scheme))
        first = page.locator(".dashboard-sidebar > *:not(.brand)").first
        assert "space-switch" in first.get_attribute("class")
    finally:
        context.close()


@pytest.mark.parametrize("scheme", ["light", "dark"])
@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("space", ["console", "personal"])
def test_the_phone_tab_bar_leads_with_the_switch_to_the_other_space(
        new_context, app_server_in_process, space, lang, scheme):
    path = "/fleet" if space == "console" else _own_frame_home
    context, page = _admin_page(
        new_context, app_server_in_process, path, VIEWPORT_MIN_SUPPORTED, lang, scheme)
    try:
        where = "bar/%s/%s/%s" % (space, lang, scheme)
        cell = _check_bar_switch(page, lang, space, where)
        assert cell["href"] == ("/" if space == "console" else "/fleet"), cell
        assert page.locator(".space-switch:visible").count() == 0
        assert page.locator("header.site-header").bounding_box()["height"] <= 56
        _assert_bar(page, 6, where)
    finally:
        context.close()


def test_one_tap_on_the_sidebar_switch_moves_between_the_two_spaces(
        new_context, app_server_in_process):
    context, page = _admin_page(new_context, app_server_in_process, "/fleet", VIEWPORT_DESKTOP)
    try:
        _visible_switch(page)
        page.locator(".space-switch__segment:visible", has_text="My frame").click()
        page.wait_for_function(
            "() => !location.pathname.endsWith('/fleet')"
            " && !!document.querySelector('.space-switch__segment[aria-current=page]')"
            " && document.querySelector('.space-switch__segment[aria-current=page]')"
            ".textContent.includes('My frame')")
        _check_switch(page, "en", "My frame", "personal/desktop")
        page.locator(".space-switch__segment:visible", has_text="Console").click()
        page.wait_for_function(
            "() => location.pathname === '/fleet'"
            " && !!document.querySelector('.space-switch__segment[aria-current=page]')"
            " && document.querySelector('.space-switch__segment[aria-current=page]')"
            ".textContent.includes('Console')")
        _check_switch(page, "en", "Console", "console/desktop")
    finally:
        context.close()


def test_one_tap_on_the_tab_bar_switch_moves_between_the_two_spaces(
        new_context, app_server_in_process):
    """The cell is a plain link to the other space."""
    context, page = _admin_page(
        new_context, app_server_in_process, "/fleet", VIEWPORT_MIN_SUPPORTED)
    try:
        _check_bar_switch(page, "en", "console", "console/phone")
        page.locator(".tab-bar > .tab-bar__link--switch").click()
        page.wait_for_function("() => !location.pathname.endsWith('/fleet')")
        _check_bar_switch(page, "en", "personal", "personal/phone")
        page.locator(".tab-bar > .tab-bar__link--switch").click()
        page.wait_for_function("() => location.pathname === '/fleet'")
        _check_bar_switch(page, "en", "console", "console/phone-again")
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
        assert page.locator(".tab-bar__link--switch").count() == 0
        assert page.locator(".space-strip").count() == 0
    finally:
        context.close()


@pytest.mark.parametrize("scheme", ["light", "dark"])
@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("name,viewport", _DESKTOP)
@pytest.mark.parametrize("space", ["console", "personal"])
def test_segments_share_the_pill_and_hold_their_labels(
        new_context, app_server_in_process, space, name, viewport, lang, scheme):
    """Each visible segment has the same width, its label box lies inside the segment and the
    pill, and nothing is clipped (scrollWidth <= clientWidth for the label)"""
    path = "/fleet" if space == "console" else _own_frame_home
    context, page = _admin_page(
        new_context, app_server_in_process, path, viewport, lang, scheme)
    try:
        _visible_switch(page)
        deadline = time.monotonic() + 10
        while True:
            data = page.evaluate("""() => {
                const nav = [...document.querySelectorAll('.space-switch')]
                    .find(n => n.getClientRects().length > 0);
                const pill = nav.getBoundingClientRect();
                return [...nav.querySelectorAll('.space-switch__segment')].map(a => {
                    const seg = a.getBoundingClientRect();
                    const label = a.querySelector('span');
                    const r = document.createRange(); r.selectNodeContents(label);
                    const t = r.getBoundingClientRect();
                    const l = label.getBoundingClientRect();
                    return {w: seg.width, segL: seg.left, segR: seg.right,
                            pillL: pill.left, pillR: pill.right, textL: t.left,
                            textR: t.right, labelL: l.left, labelR: l.right,
                            scroll: label.scrollWidth, client: label.clientWidth,
                            text: label.textContent};
                });
            }""")
            try:
                first, second = data
                assert abs(first["w"] - second["w"]) <= 1, data
                for seg in data:
                    assert seg["segL"] >= seg["pillL"] - 0.5 and seg["segR"] <= seg["pillR"] + 0.5, seg
                    assert seg["textL"] >= seg["segL"] - 0.5 and seg["textR"] <= seg["segR"] + 0.5, seg
                    assert seg["labelL"] >= seg["segL"] - 0.5 and seg["labelR"] <= seg["segR"] + 0.5, seg
                    assert seg["scroll"] <= seg["client"], seg
                return
            except AssertionError:
                if time.monotonic() > deadline:
                    raise
                page.wait_for_timeout(200)
    finally:
        context.close()
