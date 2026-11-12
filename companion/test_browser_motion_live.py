#!/usr/bin/env python3
"""Browser checks for the live Home and the phone's pull to refresh on Flights.

Every check reads the real served page in a real browser: the text the countdown shows over
time, the animations the script starts, the boxes the browser lays out and the requests the
page makes.
"""
import re
from datetime import datetime, timedelta, timezone

import pytest

from companion.test_browser_ux_helpers import (
    VIEWPORT_PHONE, _login, _no_js_page, seed_state_dir,
)
from server import device_config, history_db

pytestmark = pytest.mark.browser

COUNTDOWN = ".home-state__next [data-relative-countdown]"
HOME_ROWS = 'section[aria-labelledby="home-flights"] li.recent-flight'

# Records what the page's script does, from the first line of the document: every text the
# countdown shows and every Element.animate call (target, keyframes, options).
_RECORDER = """() => {
  window.__texts = [];
  window.__animations = [];
  const realAnimate = Element.prototype.animate;
  Element.prototype.animate = function (frames, options) {
    window.__animations.push({
      cls: String(this.getAttribute('class') || ''), tag: this.tagName,
      first: (this.textContent || '').trim().slice(0, 40),
      frames: JSON.stringify(frames),
      delay: options && options.delay || 0,
      duration: options && options.duration || 0});
    return realAnimate.call(this, frames, options);
  };
  document.addEventListener('DOMContentLoaded', () => {
    const el = document.querySelector('%s');
    if (!el) { return; }
    window.__texts.push(el.textContent);
    new MutationObserver(() => window.__texts.push(el.textContent))
      .observe(el, {childList: true, characterData: true, subtree: true});
  });
}""" % COUNTDOWN


def _seed_checkin(minutes_ago):
    """A frame that checked in `minutes_ago` minutes ago on a five-minute cadence."""
    def seed(state_dir):
        seed_state_dir(state_dir)
        device_config.save_device_config(
            state_dir, display_enabled=True, quiet_hours_enabled=False, wake_interval_s=300)
        stamp = datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)
        with history_db.open_db(state_dir) as conn:
            history_db.record_device_health(
                conn, stamp.isoformat(), battery_mv=4100, fw_version="1.0.0",
                boot_reason="wake", rssi="-60")
    return seed


def _wait(page, body, arg=None, timeout=15000):
    """wait_for_function on a function form: the page's CSP refuses string evaluation."""
    page.wait_for_function("(a) => " + body, arg=arg, timeout=timeout)


def _eval(page, body, arg=None):
    return page.evaluate("(a) => " + body, arg)


def _open(new_context, server, route, reduced=False, **extra):
    """A signed-in phone-sized context (`route` is where the caller will go next)."""
    context = new_context(
        viewport=VIEWPORT_PHONE, reduced_motion="reduce" if reduced else "no-preference",
        **extra)
    page = context.new_page()
    _login(page, server.base_url())
    return context, page


def _goto_recorded(page, url):
    page.context.add_init_script("(" + _RECORDER + ")()")
    page.goto(url)
    _wait(page, "document.readyState === 'complete'")


def _number(text):
    found = re.search(r"\d+", text)
    return int(found.group()) if found else None


def _served_countdown(page, url):
    html = page.request.get(url).text()
    found = re.search(r"<time[^>]*data-relative-countdown[^>]*>([^<]*)</time>", html)
    assert found, "the served Home has no countdown"
    return found.group(1)


# ---- live Home ----------------------------------------------------------------------


def test_the_countdown_counts_up_once_and_ends_at_the_servers_text(new_context, make_app_server):
    """Opening Home, the countdown's figure runs up from zero and its last text is the one the
    server rendered; the page without scripts shows that same text."""
    server = make_app_server(seed=_seed_checkin(0.4), fake_providers=True)
    context, page = _open(new_context, server, "/")
    try:
        served = _served_countdown(page, server.base_url() + "/")
        _goto_recorded(page, server.base_url() + "/")
        _wait(page, "window.__texts.length > 0")
        _wait(page, "window.__texts.length > 2 && document.querySelector(a.sel).textContent"
                    " === a.served", {"sel": COUNTDOWN, "served": served})
        seen = _eval(page, "window.__texts")
        target = _number(served)
        assert target and target > 1, served
        figures = [_number(text) for text in seen]
        assert min(figures) < target, "the figure never ran up: %r" % (seen,)
        final = page.locator(COUNTDOWN).inner_text()
        assert final == served, (final, served)
        # The rest of the line keeps its width while the figure runs.
        assert all(re.sub(r"\d+", "#", text) == re.sub(r"\d+", "#", served)
                   for text in seen), seen
    finally:
        context.close()

    with _no_js_page(new_context, server.base_url(), "/", viewport=VIEWPORT_PHONE) as page:
        assert page.locator(COUNTDOWN).inner_text() == served


_ROLLS = "window.__animations.filter(x => x.frames.indexOf('translateY(3px)') >= 0)"


def test_the_countdown_ticks_down_in_its_last_minute_without_any_roll(
        new_context, make_app_server):
    """Within the last minute the countdown loses seconds as the clock runs and never goes back
    up, as plain text: no roll plays on a tick, and the info button beside the line does not
    move while the figure keeps its number of digits."""
    server = make_app_server(seed=_seed_checkin(4.4), fake_providers=True)
    context, page = _open(new_context, server, "/")
    try:
        _goto_recorded(page, server.base_url() + "/")
        _wait(page, "window.__texts.length > 0")
        _wait(page, "(() => { const n = window.__texts.map(t => parseInt(t.match(/\\d+/)[0], 10));"
                    " let falls = 0; for (let i = 1; i < n.length; i++) { if (n[i] < n[i - 1]) falls++; }"
                    " return falls >= 1; })()", timeout=25000)
        info = ".home-state__next-row .info-tip"
        lefts = []
        figures = []
        for _ in range(3):
            shown = page.locator(COUNTDOWN).inner_text()
            _wait(page, "document.querySelector(a.sel).textContent !== a.was",
                  {"sel": COUNTDOWN, "was": shown}, timeout=10000)
            figures.append(_number(page.locator(COUNTDOWN).inner_text()))
            lefts.append(_eval(page, "document.querySelector(a).getBoundingClientRect().left", info))
        seen = [_number(text) for text in _eval(page, "window.__texts")]
        first_fall = next(i for i in range(1, len(seen)) if seen[i] < seen[i - 1])
        settled = seen[first_fall - 1:]
        assert len(settled) >= 3, seen
        steps = [a - b for a, b in zip(settled, settled[1:])]
        assert all(step >= 0 for step in steps), "the countdown went back up: %r" % (seen,)
        assert any(step >= 1 for step in steps), seen
        assert _eval(page, _ROLLS) == []
        if len({len(str(figure)) for figure in figures}) == 1:
            assert max(lefts) - min(lefts) < 0.01, (figures, lefts)
    finally:
        context.close()


def test_a_minute_less_rolls_the_countdown_once(new_context, make_app_server):
    """While more than a minute remains the countdown changes once a minute, and that change
    gets one short roll; the count-up of the page opening rolls nothing."""
    server = make_app_server(seed=_seed_checkin(2.8), fake_providers=True)
    context, page = _open(new_context, server, "/")
    try:
        _goto_recorded(page, server.base_url() + "/")
        _wait(page, "window.__texts.length > 0")
        served = _served_countdown(page, server.base_url() + "/")
        _wait(page, "document.querySelector(a.sel).textContent === a.served",
              {"sel": COUNTDOWN, "served": served})
        assert _number(served) == 2, served
        assert _eval(page, _ROLLS) == []
        _wait(page, "(() => { const m = document.querySelector(a).textContent.match(/\\d+/);"
                    " return m && parseInt(m[0], 10) === 1; })()", COUNTDOWN, timeout=30000)
        _wait(page, _ROLLS + ".length > 0")
        rolls = _eval(page, _ROLLS)
        assert len(rolls) == 1 and rolls[0]["tag"] == "TIME", rolls
    finally:
        context.close()


def test_reduced_motion_leaves_the_countdown_as_text_only(new_context, make_app_server):
    """With reduced motion the countdown still ticks as text, but it never counts up and no
    animation is started on the page."""
    server = make_app_server(seed=_seed_checkin(4.4), fake_providers=True)
    context, page = _open(new_context, server, "/", reduced=True)
    try:
        served = _served_countdown(page, server.base_url() + "/")
        _goto_recorded(page, server.base_url() + "/")
        _wait(page, "window.__texts.length >= 3", timeout=20000)
        seen = _eval(page, "window.__texts")
        assert _number(seen[0]) >= _number(served) - 2, (seen, served)
        assert _eval(page, "window.__animations") == []
    finally:
        context.close()


_WAITING = COUNTDOWN + ".is-breathing"
_WAITING_ANIMATIONS = """(sel) => document.getAnimations()
  .filter((a) => a.effect && a.effect.target === document.querySelector(sel))
  .map((a) => { const t = a.effect.getComputedTiming();
    return {name: a.animationName, iterations: t.iterations, end: t.endTime}; })"""
_ENDLESS = """() => document.getAnimations()
  .filter((a) => !a.effect || a.effect.getComputedTiming().iterations === Infinity)
  .map((a) => a.animationName || a.transitionProperty || '')"""


def test_an_overdue_refresh_pulses_for_a_while_then_rests(new_context, make_app_server):
    """Once the countdown has run out the line reads as waiting and pulses; the pulse is a
    finite run (under a minute), never an endless loop."""
    server = make_app_server(seed=_seed_checkin(5.2), fake_providers=True)
    context, page = _open(new_context, server, "/")
    try:
        page.goto(server.base_url() + "/")
        _wait(page, "!!document.querySelector(a)", _WAITING)
        _wait(page, "document.getAnimations().some(x => x.effect"
                    " && x.effect.target === document.querySelector(a))", _WAITING)
        pulses = page.evaluate(_WAITING_ANIMATIONS, _WAITING)
        assert pulses and all(pulse["name"] == "skypane-pulse" for pulse in pulses), pulses
        for pulse in pulses:
            assert pulse["iterations"] is not None and pulse["iterations"] < 100, pulse
            assert 0 < pulse["end"] <= 60000, pulse
    finally:
        context.close()


def test_reduced_motion_shows_an_overdue_refresh_without_any_pulse(new_context, make_app_server):
    """With reduced motion the waiting line is text only: nothing animates on it and no
    animation on the page loops for ever."""
    server = make_app_server(seed=_seed_checkin(5.2), fake_providers=True)
    context, page = _open(new_context, server, "/", reduced=True)
    try:
        page.goto(server.base_url() + "/")
        _wait(page, "document.readyState === 'complete'")
        _wait(page, "!!document.querySelector(a)", _WAITING)
        assert page.evaluate(_WAITING_ANIMATIONS, _WAITING) == []
        assert page.evaluate(_ENDLESS) == []
        assert _eval(page, "getComputedStyle(document.querySelector(a)).animationName",
                     _WAITING) == "none"
    finally:
        context.close()


def _record_a_detection(state_dir, callsign, hex_value, stamp):
    with history_db.open_db(state_dir) as conn:
        history_db.record_runway_event(
            conn, ts=stamp, hex=hex_value, callsign=callsign, aircraft_type="A320",
            confirmed_state="confirmed", corroborated=True, route_source="adsb",
            airline="Air France", origin="LFPO", destination="LFPG",
            tracked_runway=device_config.RUNWAY_IDS[0])


_ROW_BOXES = """() => [...document.querySelectorAll('%s, .recent-flight-all')].map(el => {
  const box = el.getBoundingClientRect();
  return {name: (el.querySelector('.mono') || el).textContent.trim(),
          top: box.top, height: box.height};
})""" % HOME_ROWS


def _request_refresh(page):
    page.evaluate("() => document.dispatchEvent(new Event('skypane-refresh-request'))")


def test_a_new_flight_slides_in_at_the_top_and_everything_ends_in_place(
        new_context, make_app_server):
    """A flight the refresh brings to Recent flights slides in at the top while the rows below
    glide down by whole pixels from where they were; when the motion ends every row sits where a
    page rendered in one go puts it, and the list below the insertion has not moved."""
    server = make_app_server(seed=_seed_checkin(1), fake_providers=True)
    context, page = _open(new_context, server, "/")
    try:
        _goto_recorded(page, server.base_url() + "/")
        _wait(page, "document.getAnimations().every(a => !Number.isFinite(a.effect.getComputedTiming().endTime) || a.playState !== 'running')")
        before = page.evaluate(_ROW_BOXES)
        _record_a_detection(server.tmpdir, "NEWDET", "39ffff", "2026-08-01T23:30:00+00:00")
        _request_refresh(page)
        _wait(page, "document.querySelector(a).textContent.includes('NEWDET')", HOME_ROWS)
        moves = [a for a in _eval(page, "window.__animations") if a["tag"] == "LI"]
        entering = [a for a in moves if "translateY(-14px)" in a["frames"]]
        assert len(entering) == 1 and "NEWDET" in entering[0]["first"], moves
        gliding = [a for a in moves if "translateY(-14px)" not in a["frames"]]
        assert gliding, "the rows below did not glide: %r" % (moves,)
        for glide in gliding:
            shift = re.search(r"translateY\((-?[\d.]+)px\)", glide["frames"]).group(1)
            assert float(shift) == int(float(shift)) and float(shift) < 0, glide
        _wait(page, "document.getAnimations().every(a => !Number.isFinite(a.effect.getComputedTiming().endTime) || a.playState !== 'running')")
        after = page.evaluate(_ROW_BOXES)
        assert after[0]["name"] == "NEWDET"
        assert len(after) == len(before)
        assert after[0]["top"] == before[0]["top"]
        assert after[-1]["top"] == before[-1]["top"], "the list below moved"
        rows = [row for row in after[1:-1]]
        olds = [row for row in before[:-1]]
        for now, was in zip(rows, olds):
            assert now["name"] == was["name"]
            assert abs(now["top"] - (was["top"] + after[0]["height"])) <= 1, (now, was)
        assert _eval(page, "document.getAnimations().filter("
                          "a => a.effect.target.tagName === 'LI').length") == 0
    finally:
        context.close()


def test_reduced_motion_brings_a_new_flight_in_without_any_slide(new_context, make_app_server):
    server = make_app_server(seed=_seed_checkin(1), fake_providers=True)
    context, page = _open(new_context, server, "/", reduced=True)
    try:
        _goto_recorded(page, server.base_url() + "/")
        _record_a_detection(server.tmpdir, "NEWDET", "39ffff", "2026-08-01T23:30:00+00:00")
        _request_refresh(page)
        _wait(page, "document.querySelector(a).textContent.includes('NEWDET')", HOME_ROWS)
        assert _eval(page, "window.__animations") == []
    finally:
        context.close()


# Every CSS animation the page starts, by name and target class.
_CSS_RECORDER = """() => {
  window.__css = [];
  document.addEventListener('animationstart', (e) => window.__css.push(
    {name: e.animationName, cls: String(e.target.className || '')}), true);
}"""
_ENTRANCES_SINCE = ("window.__css.slice(a).filter(e => e.name.indexOf('skypane-reveal') === 0)")
_QUIET = "document.getAnimations().every(a => !Number.isFinite(" \
    "a.effect.getComputedTiming().endTime) || a.playState !== 'running')"


def test_a_live_update_of_home_never_replays_the_page_opening(new_context, make_app_server):
    """Home opens with the shared entrance once. A refresh that swaps its regions in place and
    a switch flipped in place (which refreshes the headline) bring the new content in without
    any block fading or rising again."""
    server = make_app_server(seed=_seed_checkin(1), fake_providers=True)
    context, page = _open(new_context, server, "/")
    try:
        page.context.add_init_script("(" + _CSS_RECORDER + ")()")
        _goto_recorded(page, server.base_url() + "/")
        _wait(page, "window.__css.some(e => e.name === 'skypane-reveal-fade')")
        _wait(page, "!document.querySelector('main[data-page-open]') && " + _QUIET)
        mark = _eval(page, "window.__css.length")
        _record_a_detection(server.tmpdir, "NEWDET", "39ffff", "2026-08-01T23:30:00+00:00")
        _request_refresh(page)
        _wait(page, "document.querySelector(a).textContent.includes('NEWDET')", HOME_ROWS)
        _wait(page, _QUIET)
        assert _eval(page, _ENTRANCES_SINCE, mark) == []

        mark = _eval(page, "window.__css.length")
        button = page.locator(".home-switch button[role='switch']").first
        was = button.get_attribute("aria-checked")
        with page.expect_response(lambda r: r.request.method == "GET"
                                  and r.url.rstrip("/") == server.base_url()):
            button.click()
        _wait(page, "document.querySelector(\".home-switch button[role='switch']\")"
                    ".getAttribute('aria-checked') !== a"
                    " && !document.querySelector('[data-quick-region][data-pending]')", was)
        _wait(page, _QUIET)
        assert _eval(page, _ENTRANCES_SINCE, mark) == []
    finally:
        context.close()


# ---- pull to refresh ----------------------------------------------------------------

CARD = "li.history-card"


def _count_refreshes(page, base_url):
    seen = []
    page.on("request", lambda request: seen.append(request.url) if (
        request.url.split("?")[0] == base_url + "/flights"
        and request.headers.get("x-requested-with") == "freshness") else None)
    return seen


def _flights_ready(page, base_url):
    _goto_recorded(page, base_url + "/flights")
    _wait(page, "document.querySelector(a) !== null", CARD)
    # A cross-document view transition may still own the pixels just after the navigation.
    _wait(page, "(() => { const card = document.querySelector(a);"
                " const box = card.getBoundingClientRect();"
                " const hit = document.elementFromPoint(box.left + box.width / 2, box.top + 8);"
                " return !!hit && card.contains(hit); })()", CARD)
    box = page.locator(CARD).first.bounding_box()
    return box["x"] + box["width"] / 2, box["y"] + 8


def _drag(page, x, y, distance, steps=12):
    page.mouse.move(x, y)
    page.mouse.down()
    for step in range(1, steps + 1):
        page.mouse.move(x, y + distance * step / steps)
    return page.mouse


def test_a_pull_past_the_threshold_refreshes_once_and_the_list_comes_back(
        new_context, make_app_server):
    """Dragging the list down from the top shows the indicator, a release past the threshold
    asks for exactly one refresh, then the indicator goes and the cards enter one after the
    other; a short pull does nothing."""
    server = make_app_server(seed=seed_state_dir, fake_providers=True)
    context, page = _open(new_context, server, "/flights")
    try:
        refreshes = _count_refreshes(page, server.base_url())
        x, y = _flights_ready(page, server.base_url())
        mouse = _drag(page, x, y, 60)
        mouse.up()
        _wait(page, "document.querySelector('.history-cards').style.transform === ''")
        assert refreshes == [], "a short pull refreshed"

        mouse = _drag(page, x, y, 160)
        _wait(page, "document.querySelector('.pull-indicator').textContent.trim()"
                    " === document.body.getAttribute('data-pull-release-text')")
        shifted = _eval(page, "document.querySelector('.history-cards').style.transform")
        assert re.fullmatch(r"translateY\(\d+px\)", shifted), shifted
        assert int(re.search(r"\d+", shifted).group()) >= 56
        mouse.up()
        _wait(page, "window.__animations.some(x => x.cls.includes('history-card'))")
        _wait(page, "document.getAnimations().every(a => !Number.isFinite(a.effect.getComputedTiming().endTime) || a.playState !== 'running')")
        assert len(refreshes) == 1, refreshes
        stagger = [a["delay"] for a in _eval(page, "window.__animations")
                   if "history-card" in a["cls"]]
        assert stagger == sorted(stagger) and stagger[0] == 0 and stagger[1] > 0, stagger
        _wait(page, "document.querySelector('.history-cards').style.transform === ''"
                    " && getComputedStyle(document.querySelector('.pull-indicator')).opacity"
                    " === '0'")
    finally:
        context.close()


def test_a_pull_that_starts_scrolled_down_does_not_refresh(new_context, make_app_server):
    server = make_app_server(seed=seed_state_dir, fake_providers=True)
    context, page = _open(new_context, server, "/flights")
    try:
        refreshes = _count_refreshes(page, server.base_url())
        x, y = _flights_ready(page, server.base_url())
        page.evaluate("() => window.scrollTo(0, 300)")
        _wait(page, "window.scrollY > 100")
        box = page.locator(CARD).nth(3).bounding_box()
        mouse = _drag(page, box["x"] + box["width"] / 2, box["y"] + 8, 160)
        mouse.up()
        page.wait_for_timeout(400)
        assert refreshes == []
        assert _eval(page, "document.querySelector('.history-cards').style.transform") == ""
    finally:
        context.close()


def test_a_touch_drag_at_the_top_refreshes_once(new_context, make_app_server):
    """The same gesture with a finger: the browser leaves a downward drag at the top to the
    page."""
    server = make_app_server(seed=seed_state_dir, fake_providers=True)
    context, page = _open(new_context, server, "/flights", has_touch=True)
    try:
        refreshes = _count_refreshes(page, server.base_url())
        x, y = _flights_ready(page, server.base_url())
        cdp = context.new_cdp_session(page)
        cdp.send("Input.dispatchTouchEvent", {
            "type": "touchStart", "touchPoints": [{"x": x, "y": y}]})
        for step in range(1, 13):
            cdp.send("Input.dispatchTouchEvent", {
                "type": "touchMove", "touchPoints": [{"x": x, "y": y + 14 * step}]})
        cdp.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
        _wait(page, "window.__animations.some(x => x.cls.includes('history-card'))")
        assert len(refreshes) == 1, refreshes
    finally:
        context.close()


def test_reduced_motion_pulls_without_any_animation(new_context, make_app_server):
    """With reduced motion the gesture still refreshes once, but the list never moves and no
    animation is started."""
    server = make_app_server(seed=seed_state_dir, fake_providers=True)
    context, page = _open(new_context, server, "/flights", reduced=True)
    try:
        refreshes = _count_refreshes(page, server.base_url())
        x, y = _flights_ready(page, server.base_url())
        mouse = _drag(page, x, y, 160)
        assert _eval(page, "document.querySelector('.history-cards').style.transform") == ""
        mouse.up()
        _wait(page, "getComputedStyle(document.querySelector('.pull-indicator')).opacity"
                    " === '0'")
        assert len(refreshes) == 1, refreshes
        assert _eval(page, "window.__animations") == []
    finally:
        context.close()


def test_a_pull_inside_an_open_dialog_page_does_nothing(new_context, make_app_server):
    """With a dialog open the page behind it does not take the drag."""
    server = make_app_server(seed=seed_state_dir, fake_providers=True)
    context, page = _open(new_context, server, "/flights")
    try:
        refreshes = _count_refreshes(page, server.base_url())
        x, y = _flights_ready(page, server.base_url())
        page.evaluate("() => { const d = document.createElement('dialog');"
                      " document.body.appendChild(d); d.show(); }")
        mouse = _drag(page, x, y, 160)
        mouse.up()
        page.wait_for_timeout(400)
        assert refreshes == []
    finally:
        context.close()
