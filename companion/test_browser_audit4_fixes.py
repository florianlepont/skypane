"""Real-browser checks of the fourth audit's visual findings: the form-page Save bar that appears
only on a change, user cards (e-mail wrapping, role select), the sidebar (one line per item, a
focus ring hugging its item), the System column, the hero ring, the tab strip insets, the picture
placeholders and the colour dots. Every read waits for a settled page first."""
import pytest

import fleet_console_support as fx
from companion import auth
from companion.test_browser_ux_helpers import (
    VIEWPORT_DESKTOP, VIEWPORT_MIN_SUPPORTED, VIEWPORT_PHONE, _login)
from server import device_config

pytestmark = pytest.mark.browser

_SETTLED = (
    "() => document.readyState === 'complete' && document.getAnimations().every("
    "a => !a.effect || a.effect.getTiming().iterations === Infinity || a.playState !== 'running')")


def _open(new_context, server, path, viewport, lang="en", who="admin", theme="light",
          js_enabled=True, seed=None):
    seed = seed or fx.seed_fleet(server.state_dir)
    context = new_context(
        viewport=viewport, color_scheme=theme, java_script_enabled=js_enabled)
    context.add_cookies([{
        "name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": server.base_url()}])
    page = context.new_page()
    if who == "admin":
        _login(page, server.base_url())
    else:
        name, value = fx.user_cookie(server.state_dir, email=fx.OWNER_EMAIL).split("=", 1)
        context.add_cookies([{
            "name": name, "value": value, "url": server.base_url(), "httpOnly": True,
            "sameSite": "Strict"}])
    page.goto(server.base_url() + path.replace("{owned}", seed.owned_id))
    if js_enabled:
        page.wait_for_function(_SETTLED, timeout=15000)
    return context, page, seed


def _bar_hidden(page):
    return page.evaluate("() => document.querySelector('.dirty-bar').hidden")


@pytest.mark.parametrize("path,field,who", [
    ("/devices/{owned}/frame/name", "#frame-name", "owner"),
    ("/display/special-looks/new", "[name=rule_key]", "admin")], ids=["rename", "special-look"])
def test_a_form_page_bar_appears_only_once_a_field_changed(
        new_context, app_server_in_process, path, field, who):
    server = app_server_in_process
    device_config.save_device_config(server.state_dir, layout="classic")
    context, page, _seed = _open(new_context, server, path, VIEWPORT_PHONE, who=who)
    try:
        page.wait_for_function(
            "() => document.querySelector('.dirty-bar') && document.readyState === 'complete'")
        assert _bar_hidden(page)
        original = page.input_value(field)
        page.fill(field, original + "X")
        page.wait_for_function("() => !document.querySelector('.dirty-bar').hidden", timeout=5000)
        page.fill(field, original)
        page.wait_for_function("() => document.querySelector('.dirty-bar').hidden", timeout=5000)
    finally:
        context.close()


def test_a_form_page_bar_is_in_the_page_without_script(new_context, app_server_in_process):
    server = app_server_in_process
    context, page, _seed = _open(
        new_context, server, "/devices/{owned}/frame/name", VIEWPORT_PHONE, who="owner",
        js_enabled=False)
    try:
        assert page.locator(".dirty-bar button.dirty-bar__save").is_visible()
    finally:
        context.close()


@pytest.mark.parametrize("lang", ["en", "fr"])
def test_user_cards_wrap_addresses_at_separators_and_show_the_whole_role(
        new_context, app_server_in_process, lang):
    server = app_server_in_process
    context, page, _seed = _open(
        new_context, server, "/users", VIEWPORT_MIN_SUPPORTED, lang, theme="dark")
    try:
        breaks = page.evaluate("""() => [...document.querySelectorAll('.users-email')].map(el => {
            const node = el.firstChild; const text = el.textContent; const range = document.createRange();
            const bad = []; let top = null;
            const walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT); const nodes = [];
            while (walker.nextNode()) nodes.push(walker.currentNode);
            let offset = 0, previous = null, previousTop = null;
            for (const n of nodes) { for (let i = 0; i < n.length; i++) {
                range.setStart(n, i); range.setEnd(n, i + 1);
                const rect = range.getBoundingClientRect();
                if (previousTop !== null && rect.top > previousTop + 4 && !'@.'.includes(previous))
                    bad.push(text.slice(Math.max(0, offset - 3), offset + 3));
                previous = text[offset]; previousTop = rect.top; offset += 1; } }
            return bad; })""")
        assert breaks and all(not bad for bad in breaks), breaks
        clipped = page.evaluate("""() => [...document.querySelectorAll('.users-role-form select')].map(s => {
            const c = document.createElement('canvas').getContext('2d'); const cs = getComputedStyle(s);
            c.font = cs.fontWeight + ' ' + cs.fontSize + ' ' + cs.fontFamily;
            const widest = Math.max(...[...s.options].map(o => c.measureText(o.text).width));
            return s.getBoundingClientRect().width - widest - parseFloat(cs.paddingLeft)
              - parseFloat(cs.paddingRight); })""")
        assert clipped and min(clipped) >= 8, clipped
        assert not page.evaluate(
            "() => document.documentElement.scrollWidth > document.documentElement.clientWidth")
    finally:
        context.close()


def test_the_user_status_follows_the_last_sign_in(new_context, app_server_in_process):
    server = app_server_in_process
    context, page, seed = _open(new_context, server, "/users", VIEWPORT_DESKTOP)
    try:
        row = page.locator("#user-%d" % seed.admin_id)
        assert row.locator(".users-pill--invited:visible").count() == 0
        assert row.locator(".users-pill--active:visible").count() == 1
        assert page.locator("#user-%d .users-pill--invited:visible" % seed.owner_id).count() == 1
    finally:
        context.close()


@pytest.mark.parametrize("lang", ["en", "fr"])
def test_every_sidebar_item_is_one_line_of_the_same_height(
        new_context, app_server_in_process, lang):
    server = app_server_in_process
    context, page, _seed = _open(new_context, server, "/airlines/manage", VIEWPORT_DESKTOP, lang)
    try:
        sizes = page.evaluate("""() => [...document.querySelectorAll('.sidebar-nav .sidebar-link')]
            .map(a => [Math.round(a.getBoundingClientRect().height),
                       Math.round(parseFloat(getComputedStyle(a).lineHeight) || 0), a.textContent.trim()])""")
        assert len({height for height, _line, _text in sizes}) == 1, sizes
        assert sizes[0][0] <= 48
    finally:
        context.close()


def test_the_sidebar_focus_ring_hugs_its_item(new_context, app_server_in_process):
    server = app_server_in_process
    context, page, _seed = _open(new_context, server, "/fleet", VIEWPORT_DESKTOP)
    try:
        page.keyboard.press("Tab")
        for _ in range(20):
            if page.evaluate("() => !!document.activeElement.closest('.sidebar-nav')"):
                break
            page.keyboard.press("Tab")
        page.wait_for_function("() => !!document.activeElement.closest('.sidebar-nav')")
        assert page.evaluate(
            "() => getComputedStyle(document.activeElement).outlineOffset") == "-2px"
    finally:
        context.close()


def test_system_cards_start_at_the_page_column(new_context, app_server_in_process):
    server = app_server_in_process
    context, page, _seed = _open(
        new_context, server, "/fleet?view=system", VIEWPORT_DESKTOP, "fr", theme="dark")
    try:
        lefts = page.evaluate(
            "() => [document.querySelector('h1').getBoundingClientRect().left,"
            " ...[...document.querySelectorAll('.system-topic')].map(e => e.getBoundingClientRect().left)]")
        assert len(lefts) > 1 and all(abs(left - lefts[0]) <= 1 for left in lefts), lefts
    finally:
        context.close()


def test_the_phone_tab_bar_caret_sits_clear_of_the_bar_edge(new_context, app_server_in_process):
    server = app_server_in_process
    context, page, _seed = _open(new_context, server, "/users", VIEWPORT_PHONE)
    try:
        gap = page.evaluate("""() => { const bar = document.querySelector('.tab-bar');
            const link = document.querySelector('.tab-bar__more > .tab-bar__link');
            return link.getBoundingClientRect().top + parseFloat(
              getComputedStyle(link, '::before').top) - bar.getBoundingClientRect().top; }""")
        assert gap >= 8, gap
    finally:
        context.close()


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_pictures_that_have_not_arrived_show_a_tint_of_the_ink(
        new_context, app_server_in_process, theme):
    server = app_server_in_process
    device_config.save_device_config(server.state_dir, layout="classic")
    context, page, _seed = _open(
        new_context, server, "/display", VIEWPORT_DESKTOP, theme=theme)
    try:
        colour = page.evaluate(
            "() => getComputedStyle(document.querySelector('.look-frame__image')).backgroundColor")
        channels = [float(part) for part in colour[colour.index("(") + 1:-1].split(",")]
        assert len(channels) == 4 and 0 < channels[3] < 0.2, colour
        assert (channels[0] > 128) == (theme == "dark"), colour
    finally:
        context.close()


def test_the_picture_dialog_caption_uses_the_body_font(new_context, app_server_in_process):
    server = app_server_in_process
    context, page, _seed = _open(new_context, server, "/airlines", VIEWPORT_PHONE)
    try:
        assert page.evaluate(
            "() => document.querySelector('.lightbox__caption') === null || "
            "getComputedStyle(document.querySelector('.lightbox__caption')).fontFamily"
            ".indexOf('mono') < 0")
    finally:
        context.close()


def test_a_hand_named_airline_keeps_its_row_one_line_tall(new_context, app_server_in_process):
    from server.plane import manual_resolutions
    server = app_server_in_process
    manual_resolutions.add_entry(
        server.state_dir, "RYR", "Ryanair", now="2026-01-01T00:00:00+00:00")
    context, page, _seed = _open(
        new_context, server, "/airlines/manage", VIEWPORT_DESKTOP, "fr", theme="dark")
    try:
        sizes = page.evaluate("""() => { const rows = [...document.querySelectorAll('tr.airlines-row')];
            const mine = rows.find(r => r.textContent.includes('Ryanair'));
            const other = rows.find(r => r.querySelector('.airlines-name input'));
            const left = el => el.querySelector('.airlines-name').getBoundingClientRect().left;
            return [mine.getBoundingClientRect().height, other.getBoundingClientRect().height,
                    left(mine), left(other)]; }""")
        assert abs(sizes[0] - sizes[1]) <= 2 and abs(sizes[2] - sizes[3]) <= 1, sizes
    finally:
        context.close()


@pytest.mark.parametrize("viewport", [VIEWPORT_MIN_SUPPORTED, VIEWPORT_DESKTOP], ids=["360", "1280"])
def test_the_first_and_last_choice_of_a_tab_strip_keep_the_same_inset(
        new_context, app_server_in_process, viewport):
    server = app_server_in_process
    context, page, _seed = _open(
        new_context, server, "/display/calendar", viewport, "fr", theme="dark")
    try:
        insets = page.evaluate("""() => { const strip = document.querySelector('[data-tabs]');
            const thumb = strip.querySelector('.tabs-thumb').getBoundingClientRect();
            const host = strip.getBoundingClientRect();
            return [thumb.left - host.left, host.right - thumb.right]; }""")
        assert insets[1] >= 2.5, insets
        first = page.evaluate("""() => { const strip = document.querySelector('[data-tabs]');
            const links = strip.querySelectorAll('a'); const host = strip.getBoundingClientRect();
            const a = links[0].getBoundingClientRect(); const z = links[links.length - 1].getBoundingClientRect();
            return [a.left - host.left, host.right - z.right]; }""")
        assert abs(first[0] - first[1]) <= 1.5, first
    finally:
        context.close()


def test_the_back_link_sits_the_same_way_on_the_rename_and_special_look_pages(
        new_context, app_server_in_process):
    server = app_server_in_process
    device_config.save_device_config(server.state_dir, layout="classic")
    gaps = []
    seed = None
    for path, who in (("/devices/{owned}/frame/name", "owner"), ("/display/special-looks/new", "admin")):
        context, page, seed = _open(new_context, server, path, VIEWPORT_PHONE, who=who, seed=seed)
        try:
            gaps.append(page.evaluate("""() => { const back = document.querySelector('.form-back');
                const after = back.nextElementSibling.getBoundingClientRect();
                const me = back.getBoundingClientRect();
                return [0, Math.round(after.top - me.bottom), Math.round(me.left)]; }"""))
        finally:
            context.close()
    assert gaps[0][2] == gaps[1][2] and abs(gaps[0][1] - gaps[1][1]) <= 4, gaps


@pytest.mark.parametrize("viewport", [VIEWPORT_PHONE, VIEWPORT_DESKTOP], ids=["390", "1280"])
def test_the_hero_picture_leaves_room_for_its_ring_inside_the_page_column(
        new_context, app_server_in_process, viewport):
    server = app_server_in_process
    context, page, _seed = _open(
        new_context, server, "/devices/{owned}/", viewport, who="owner")
    try:
        # The ring sits 5px outside the picture and strokes 2px: 6px of margin keeps
        # its outer edge on the column instead of beside the cards.
        gap = page.evaluate("""() => { const picture = document.querySelector('.hero__picture');
            const hero = picture.closest('.hero');
            return picture.getBoundingClientRect().left - hero.getBoundingClientRect().left; }""")
        assert gap >= 6, gap
    finally:
        context.close()


def test_the_pending_colour_dots_keep_their_colours(new_context, app_server_in_process):
    server = app_server_in_process
    device_config.save_device_config(server.state_dir, layout="classic")
    context, page, _seed = _open(new_context, server, "/display", VIEWPORT_DESKTOP)
    try:
        dots = page.evaluate("""() => [...document.querySelectorAll('.look-dot:has(input:disabled)')]
            .map(d => [getComputedStyle(d).filter, getComputedStyle(d.querySelector('circle')).fill])""")
        assert dots and all(f == "none" for f, _fill in dots), dots
        assert len({fill for _f, fill in dots}) > 1
        assert page.evaluate(
            "() => !!document.querySelector('fieldset[aria-describedby$=\"colour-why\"]')")
    finally:
        context.close()
