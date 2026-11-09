"""Browser proof of the Home notification for an amber or red dot, in Chromium at 360 and
1280 px, in English and French, in both themes, for an owner, a co-manager and an administrator:
it is visible, unclipped and free of horizontal overflow, the Contact an administrator link is a
44px target after the tip and carries a mailto address, a Home with no administrator shows plain
text and no anchor, and the next refresh after a check-in removes it without a reload.

Reads happen only after the document is complete, the notification and its link own their centres
and the finite animations have ended: right after a navigation a cross-document view transition
answers `elementFromPoint` with the root element.
"""
import urllib.parse
from datetime import datetime, timedelta, timezone

import pytest

from companion import auth
from companion_app_server import session_cookie_for_state_dir
from provisioned_fleet import (
    ADMIN_EMAIL, NAME_A1, USER_A_EMAIL, USER_B_EMAIL, device_dir, provision_fleet)
from server import fleet_db, history_db

pytestmark = pytest.mark.browser

NOTICE = ".home-facts .home-notice"
LINK = NOTICE + " a.toast__action"
TIP = NOTICE + " .home-notice__tip"
MIN_PX = 43.5
VIEWPORTS = (("360", {"width": 360, "height": 800}), ("1280", {"width": 1280, "height": 900}))

# Finite animations only: the live pulse never ends and must not hold the test.
_ANIMATIONS_DONE = (
    "document.getAnimations().every((a) => a.effect && "
    "a.effect.getComputedTiming().iterations === Infinity || a.playState !== 'running')")

_OVERFLOW = """() => {
  const doc = document.documentElement;
  const notice = document.querySelector('%s');
  const clipped = Array.from(notice.querySelectorAll('*')).filter(
    (el) => !el.closest('.visually-hidden') && el.scrollWidth > el.clientWidth + 1 && getComputedStyle(el).display !== 'inline'
      && getComputedStyle(el).overflow !== 'visible');
  return {page: doc.scrollWidth - doc.clientWidth, clipped: clipped.map((e) => e.tagName + '.' + e.className.toString() + ':' + e.scrollWidth + '>' + e.clientWidth).join(' '),
          right: notice.getBoundingClientRect().right, viewport: doc.clientWidth};
}""" % NOTICE


def _record(directory, minutes_ago, mv=4000):
    stamp = datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)
    with history_db.open_db(directory) as conn:
        history_db.record_device_health(
            conn, stamp.isoformat(), battery_mv=mv, fw_version="1.0.0",
            boot_reason="wake", rssi="-60")


def _seed_for(state, administrator=True):
    """A provisioned fleet whose first frame is in `state`: not_seen, low_battery or
    no_contact, with user B a co-manager of it; overdue is on the live frame (a non-live
    frame past its overdue point is already without contact)."""
    def seed(state_dir):
        fleet = provision_fleet(state_dir)
        directory = device_dir(state_dir, fleet.a1)
        if state == "low_battery":
            _record(directory, 0, mv=3381)
        elif state == "no_contact":
            _record(directory, 320)
        elif state == "overdue":
            _record(state_dir, 50)
        conn = fleet_db.connect(state_dir)
        try:
            fleet_db.add_co_manager(conn, fleet.a1, fleet.b_id, fleet.a_id)
            if not administrator:
                fleet_db.set_user_disabled(conn, ADMIN_EMAIL, True)
        finally:
            conn.close()
        seed.fleet = fleet
    return seed


def _open(new_context, server, who, path, lang="en", viewport=None, scheme="light"):
    email = {"owner": USER_A_EMAIL, "co": USER_B_EMAIL, "admin": ADMIN_EMAIL}[who]
    context = new_context(viewport=viewport, color_scheme=scheme)
    base = server.base_url()
    name, value = session_cookie_for_state_dir(server.state_dir, email).split("=", 1)
    context.add_cookies([
        {"name": name, "value": value, "url": base, "httpOnly": True, "sameSite": "Strict"},
        {"name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": base}])
    page = context.new_page()
    page.goto(base + path)
    page.wait_for_function("() => document.readyState === 'complete'", timeout=10000)
    page.locator(NOTICE).wait_for(state="visible")
    return context, page


def _wait_at_rest(page, selector):
    page.eval_on_selector(selector, "el => el.scrollIntoView({block: 'center'})")
    page.wait_for_function(
        """sel => {
          if (!(%s)) return false;
          const e = document.querySelector(sel);
          if (!e) return false;
          const r = e.getBoundingClientRect();
          const hit = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
          return !!hit && (hit === e || e.contains(hit));
        }""" % _ANIMATIONS_DONE, arg=selector, timeout=10000)


def _geometry(page, selector):
    return page.eval_on_selector(selector, """el => {
      const r = el.getBoundingClientRect();
      return {width: r.width, height: r.height, top: r.top, bottom: r.bottom,
              left: r.left, right: r.right};
    }""")


def _assert_order(page, where):
    """The notification, then the hero that carries the frame-name title, top to bottom."""
    tops = page.evaluate(
        "() => ['%s', '.home-state', 'main h1'].map("
        "(s) => document.querySelector(s).getBoundingClientRect().top)" % NOTICE)
    assert tops[0] < tops[1] <= tops[2], (where, tops)
    title_word, dot_word = page.evaluate(
        "() => [document.querySelector('.home-state__title').textContent.trim(),"
        " document.querySelector('.home-state__dot').getAttribute('aria-label')]")
    assert title_word == dot_word, (where, title_word, dot_word)


def _assert_notice_fits(page, where):
    seen = page.evaluate(_OVERFLOW)
    assert seen["page"] <= 0, (where, seen)
    assert seen["clipped"] == "", (where, seen)
    assert seen["right"] <= seen["viewport"] + 0.5, (where, seen)
    assert _geometry(page, NOTICE)["height"] >= MIN_PX, where


@pytest.mark.parametrize("scheme", ["light", "dark"])
@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("viewport_name,viewport", VIEWPORTS, ids=[v[0] for v in VIEWPORTS])
@pytest.mark.parametrize("state,path_for,who", [
    ("not_seen", "frame", "owner"),
    ("low_battery", "frame", "co"),
    ("no_contact", "frame", "admin"),
    ("overdue", "live", "admin"),
])
def test_notification_fits_and_the_link_is_a_44px_target_after_the_tip(
        new_context, make_app_server, state, path_for, who, viewport_name, viewport, lang, scheme):
    seed = _seed_for(state)
    server = make_app_server(seed=seed)
    path = "/devices/%s/" % seed.fleet.a1 if path_for == "frame" else "/"
    context, page = _open(new_context, server, who, path, lang, viewport, scheme)
    try:
        where = "%s/%s/%s/%s/%s" % (state, who, viewport_name, lang, scheme)
        _wait_at_rest(page, LINK)
        _assert_notice_fits(page, where)
        _assert_order(page, where)
        link = _geometry(page, LINK)
        assert link["height"] >= MIN_PX and link["width"] >= MIN_PX, where
        tip = _geometry(page, TIP)
        assert tip["height"] > 0, where
        # The link follows the tip in reading order and sits under it on a phone or beside
        # the text column on a wide screen.
        assert page.evaluate(
            "([a, b]) => !!(document.querySelector(a).compareDocumentPosition("
            "document.querySelector(b)) & Node.DOCUMENT_POSITION_FOLLOWING)", [TIP, LINK]), where
        assert tip["bottom"] <= link["top"] + 1 or tip["right"] <= link["left"] + 1, where
        text = page.inner_text(NOTICE)
        for word in ("Health", "Device", "Console", "Santé", "Console"):
            assert word not in text, where
        if state == "no_contact":
            for word in ("broken", "down", "failed", "panne", "hors service"):
                assert word not in text.lower(), where
            assert ("Wi-Fi" in text), where
        assert page.get_attribute(LINK, "href").startswith("mailto:" + ADMIN_EMAIL + "?subject=")
    finally:
        context.close()


def test_the_mailto_names_the_frame_and_the_state(new_context, make_app_server):
    seed = _seed_for("no_contact")
    server = make_app_server(seed=seed)
    context, page = _open(
        new_context, server, "owner", "/devices/%s/" % seed.fleet.a1, "en", VIEWPORTS[1][1])
    try:
        href = page.get_attribute(LINK, "href")
        parts = urllib.parse.urlsplit(href)
        assert parts.path == ADMIN_EMAIL
        query = urllib.parse.parse_qs(parts.query)
        assert query["subject"][0] == "SkyPane: help with the frame %s (No contact)" % NAME_A1
        assert "Last contact 5h ago" in query["body"][0]
    finally:
        context.close()


@pytest.mark.parametrize("viewport_name,viewport", VIEWPORTS, ids=[v[0] for v in VIEWPORTS])
def test_without_an_administrator_the_notification_is_plain_text(
        new_context, make_app_server, viewport_name, viewport):
    seed = _seed_for("not_seen", administrator=False)
    server = make_app_server(seed=seed)
    context, page = _open(
        new_context, server, "owner", "/devices/%s/" % seed.fleet.a1, "en", viewport)
    try:
        assert page.locator(NOTICE + " a").count() == 0
        assert "contact an administrator." in page.inner_text(
            NOTICE)
        assert "@" not in page.inner_text(NOTICE)
        _assert_notice_fits(page, "plain/" + viewport_name)
    finally:
        context.close()


def test_the_next_refresh_after_a_check_in_removes_the_notification(
        new_context, make_app_server):
    seed = _seed_for("not_seen")
    server = make_app_server(seed=seed)
    context = new_context(viewport=VIEWPORTS[1][1])
    base = server.base_url()
    name, value = session_cookie_for_state_dir(server.state_dir, USER_A_EMAIL).split("=", 1)
    context.add_cookies([{"name": name, "value": value, "url": base, "httpOnly": True,
                          "sameSite": "Strict"}])
    page = context.new_page()
    page.clock.install()
    try:
        page.goto(base + "/devices/%s/" % seed.fleet.a1)
        page.wait_for_function("() => document.readyState === 'complete'", timeout=10000)
        page.locator(NOTICE).wait_for(state="visible")
        page.evaluate("() => { window.__loaded = true; }")
        _record(device_dir(server.state_dir, seed.fleet.a1), 0)
        page.clock.run_for(46000)
        page.wait_for_function(
            "() => !document.querySelector('%s')" % NOTICE, timeout=15000)
        assert page.evaluate("() => window.__loaded === true"), "the page reloaded"
    finally:
        context.close()


@pytest.mark.parametrize("lang", ["en", "fr"])
def test_the_banner_starts_clear_of_the_frame_button_on_desktop(
        new_context, make_app_server, lang):
    """The attention banner never touches the frame button that sits level with the hero."""
    seed = _seed_for("not_seen")
    server = make_app_server(seed=seed)
    context, page = _open(
        new_context, server, "owner", "/devices/%s/" % seed.fleet.a1, lang, VIEWPORTS[1][1])
    try:
        page.wait_for_function("() => " + _ANIMATIONS_DONE, timeout=10000)
        assert page.evaluate("() => window.scrollY") == 0
        button = _geometry(page, ".frame-menu")
        banner = _geometry(page, ".home-facts")
        assert button["height"] > 0 and banner["height"] > 0, (button, banner)
        assert banner["top"] >= button["bottom"] + 8, (button, banner)
    finally:
        context.close()
