#!/usr/bin/env python3
"""Browser checks for how the Location page's map opens and how its airport pins are drawn:
it opens centred on the frame's airport, a zoomed-out view groups airports into numbered
bubbles that account for every airport, tapping a bubble zooms in, the followed airport is
always a tappable pin, and the runway cards' "Current" badge keeps clear of the designator."""
import pytest

from companion import auth
from companion.test_browser_ux_helpers import VIEWPORT_DESKTOP, VIEWPORT_MIN_SUPPORTED, _login
from place_map_support import CLEAR_BOX, SETTLED as _SETTLED, Hosts, seed as _seed

pytestmark = pytest.mark.browser

READY = "() => document.documentElement.classList.contains('map-ready')"
TILES = "() => document.querySelectorAll('#place-map .leaflet-tile-loaded').length >= 1"
IDLE = (
    "() => document.getAnimations().every((a) => a.playState !== 'running'"
    " || a.effect.getComputedTiming().iterations === Infinity)")
FRANCE = ".place-france"
# The zoom the map shows now: the highest zoom among the tiles it has loaded.
ZOOM = (
    "() => Math.max(0, ...[...document.querySelectorAll('#place-map .leaflet-tile-loaded')]"
    ".map((t) => parseInt(t.src.split('/').slice(-3)[0], 10)))")
CATALOGUE_SIZE = (
    "() => JSON.parse(document.getElementById('place-map').dataset.airports).length")
# The followed airport's pin centre, whether that point lies in the clear part of the map and
# whether the pin's own hit box owns it.
FOLLOWED = (
    "() => { const c = (" + CLEAR_BOX + ")();"
    " const d = document.querySelector('#place-map .place-dot--selected');"
    " if (!d) return null;"
    " const r = d.getBoundingClientRect(); const x = r.left + r.width / 2, y = r.top + r.height / 2;"
    " return {x: x, y: y, w: r.width, h: r.height,"
    "  clear: x > c.x && x < c.x + c.width && y > c.y && y < c.y + c.height,"
    "  owns: d.contains(document.elementFromPoint(x, y)),"
    "  label: !!d.querySelector('.place-dot__label') && "
    "   getComputedStyle(d.querySelector('.place-dot__label')).display !== 'none', box: c}; }")
COUNTS = (
    "() => ({pins: document.querySelectorAll('#place-map .place-dot').length,"
    " bubbles: [...document.querySelectorAll('#place-map .place-cluster__count')]"
    ".map((b) => parseInt(b.textContent, 10))})")
# The "Current" badge (the card's ::after) against the designator's box.
BADGE = (
    "() => { const card = document.querySelector('.place-sheet .runway-card--selected');"
    " const after = getComputedStyle(card, '::after');"
    " const cr = card.getBoundingClientRect();"
    " const num = card.querySelector('.runway-card__number').getBoundingClientRect();"
    " const px = (v) => parseFloat(v) || 0;"
    " const w = px(after.width) + (after.boxSizing === 'content-box' ?"
    "   px(after.paddingLeft) + px(after.paddingRight) + 2 * px(after.borderLeftWidth) : 0);"
    " const h = px(after.height) + (after.boxSizing === 'content-box' ?"
    "   px(after.paddingTop) + px(after.paddingBottom) + 2 * px(after.borderTopWidth) : 0);"
    " const right = cr.right - card.clientLeft - px(after.right);"
    " const top = cr.top + card.clientTop + px(after.top);"
    " return {shown: after.content !== 'none' && after.content !== 'normal',"
    "  left: right - w, right: right, top: top, bottom: top + h,"
    "  card: {left: cr.left, right: cr.right},"
    "  num: {left: num.left, right: num.right, top: num.top, bottom: num.bottom}}; }")


def _open(new_context, server, viewport, lang="en"):
    context = new_context(viewport=viewport)
    Hosts(context)
    context.add_cookies([
        {"name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": server.base_url()}])
    page = context.new_page()
    _login(page, server.base_url())
    page.goto(server.base_url() + "/detection")
    page.wait_for_function(READY, timeout=15000)
    page.wait_for_function(TILES, timeout=15000)
    page.wait_for_function(IDLE, timeout=10000)
    page.wait_for_function(_SETTLED, timeout=10000)
    return context, page



def test_the_map_opens_centred_on_the_airport_with_no_bubbles(new_context, make_app_server):
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page = _open(new_context, server, VIEWPORT_MIN_SUPPORTED)
    try:
        page.wait_for_function(
            "() => !!document.querySelector('#place-map .place-dot--selected')", timeout=10000)
        followed = page.evaluate(FOLLOWED)
        box = followed["box"]
        assert page.evaluate(ZOOM) >= 12, "the map did not open close to the airport"
        assert abs(followed["x"] - (box["x"] + box["width"] / 2)) < 40
        assert abs(followed["y"] - (box["y"] + box["height"] / 2)) < 60
        assert followed["label"] and followed["owns"]
        assert page.evaluate(COUNTS)["bubbles"] == []
    finally:
        context.close()


@pytest.mark.parametrize("lang,label", [("en", "Show all of France"),
                                        ("fr", "Voir toute la France")])
def test_zoomed_out_the_airports_are_numbered_bubbles_that_account_for_every_airport(
        new_context, make_app_server, lang, label):
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page = _open(new_context, server, VIEWPORT_MIN_SUPPORTED, lang)
    try:
        assert page.inner_text(FRANCE).strip() == label
        assert page.locator(FRANCE).bounding_box()["height"] >= 44
        page.click(FRANCE)
        page.wait_for_function(
            "() => document.querySelectorAll('#place-map .place-cluster').length >= 3", timeout=10000)
        page.wait_for_function(IDLE, timeout=10000)
        total = page.evaluate(CATALOGUE_SIZE)
        counts = page.evaluate(COUNTS)
        assert all(n >= 2 for n in counts["bubbles"]), counts
        assert sum(counts["bubbles"]) + counts["pins"] == total, (counts, total)
        assert page.evaluate(ZOOM) <= 6
        followed = page.evaluate(FOLLOWED)
        assert followed["label"] and followed["clear"] and followed["owns"]
        assert followed["w"] >= 44 and followed["h"] >= 44
    finally:
        context.close()


def test_tapping_a_bubble_zooms_in_and_the_followed_pin_stays_tappable_at_every_zoom(
        new_context, make_app_server):
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page = _open(new_context, server, VIEWPORT_DESKTOP)
    try:
        page.click(FRANCE)
        page.wait_for_function(
            "() => document.querySelectorAll('#place-map .place-cluster').length >= 3", timeout=10000)
        page.wait_for_function(IDLE, timeout=10000)
        before = page.evaluate(ZOOM)
        bubble = page.evaluate(
            "() => { const c = (" + CLEAR_BOX + ")();"
            " for (const b of document.querySelectorAll('#place-map .place-cluster')) {"
            "  const r = b.getBoundingClientRect(); const x = r.left + 22, y = r.top + 22;"
            "  if (x > c.x + 20 && x < c.x + c.width - 60 && y > c.y + 20 && y < c.y + c.height - 20"
            "   && b.contains(document.elementFromPoint(x, y))) return {x: x, y: y}; }"
            " return null; }")
        assert bubble, "no bubble in the clear part of the map"
        page.mouse.click(bubble["x"], bubble["y"])
        page.wait_for_function(
            "z => (" + ZOOM + ")() > z", arg=before, timeout=10000)
        # A wheel turn over the followed pin zooms about it, keeping it under the pointer.
        page.click(FRANCE)
        page.wait_for_function(IDLE, timeout=10000)
        for delta in (-240, -240, -240, 240, 240, 240, 240):
            page.wait_for_function(IDLE, timeout=10000)
            page.wait_for_function(
                "() => { const f = (" + FOLLOWED + ")(); return !!f && f.owns && f.clear"
                " && f.w >= 44 && f.h >= 44; }", timeout=10000)
            followed = page.evaluate(FOLLOWED)
            level = page.evaluate(ZOOM)
            page.mouse.move(followed["x"], followed["y"])
            page.mouse.wheel(0, delta)
            page.wait_for_function(
                "z => (" + ZOOM + ")() !== z", arg=level, timeout=10000)
        page.click(FRANCE)
        page.wait_for_function(IDLE, timeout=10000)
        page.wait_for_function(
            "() => { const f = (" + FOLLOWED + ")();"
            " return !!f && f.owns && f.clear; }", timeout=10000)
    finally:
        context.close()


@pytest.mark.parametrize("lang", ["en", "fr"])
def test_the_current_badge_keeps_clear_of_the_runway_designator_at_360(
        new_context, make_app_server, lang):
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page = _open(new_context, server, VIEWPORT_MIN_SUPPORTED, lang)
    try:
        other = page.locator(
            ".place-sheet label.runway-card:not(.runway-card--selected)").first
        other.click()
        page.wait_for_function(
            "() => !document.querySelector('.place-sheet .runway-card--selected input').checked",
            timeout=5000)
        badge = page.evaluate(BADGE)
        assert badge["shown"]
        assert badge["right"] <= badge["card"]["right"] + 1
        num = badge["num"]
        apart_vertically = badge["bottom"] <= num["top"] + 1 or badge["top"] >= num["bottom"] - 1
        apart_sideways = badge["right"] <= num["left"] or badge["left"] >= num["right"]
        assert apart_vertically or apart_sideways, (badge, "the badge covers the designator")
    finally:
        context.close()
