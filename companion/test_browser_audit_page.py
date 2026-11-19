"""Real-browser checks of the Audit log page: no sideways scroll at the
smallest phone width, cards on a phone and the table on a desktop, chips and
pager links with a 44px touch target."""
import time

import pytest

import fleet_console_support as fx
from companion.test_browser_ux_helpers import (
    _login)
from server import fleet_db

pytestmark = pytest.mark.browser

MIN_TAP_PX = 44


def _open(new_context, server, viewport):
    fx.seed_fleet(server.state_dir)
    conn = fleet_db.connect(server.state_dir)
    try:
        with fleet_db.transaction(conn):
            for index in range(60):
                fleet_db.audit_append(
                    conn, fx.ACTOR, "pairing.claim", "device", "d_00000001", "ok",
                    None, now=int(time.time()) + 1000 + index)
    finally:
        conn.close()
    context = new_context(viewport=viewport)
    page = context.new_page()
    _login(page, server.base_url())
    page.goto(server.base_url() + "/audit")
    page.locator("main").wait_for(state="visible")
    return context, page


def _no_sideways_scroll(page):
    return page.evaluate(
        "document.documentElement.scrollWidth <= document.documentElement.clientWidth")


def _wait_ready(page):
    page.wait_for_function("document.readyState === 'complete'")
    page.wait_for_function(
        "() => { const s = document.querySelector('.audit-event__row');"
        " if (!s) return false; const r = s.getBoundingClientRect();"
        " return document.elementFromPoint(r.x + r.width / 2, r.y + r.height / 2) !== document.documentElement; }")


@pytest.mark.parametrize("viewport", [
    {"width": 360, "height": 740}, {"width": 390, "height": 844},
    {"width": 1280, "height": 900}, {"width": 1440, "height": 900}])
def test_rows_are_compact_expand_and_never_overflow(
        new_context, app_server_in_process, viewport):
    context, page = _open(new_context, app_server_in_process, viewport)
    try:
        _wait_ready(page)
        assert _no_sideways_scroll(page)
        assert page.locator(".audit-event").count() == 50
        first = page.locator(".audit-event").first
        assert first.locator(".audit-event__detail").is_hidden()
        assert first.locator("summary").bounding_box()["height"] >= MIN_TAP_PX
        first.locator("summary").click()
        page.wait_for_function(
            "() => document.querySelector('.audit-event details').open")
        detail = first.locator(".audit-event__detail")
        assert detail.is_visible()
        for label in ("Target", "From", "Exact date", "Author"):
            assert first.locator("dt", has_text=label).is_visible()
        box = detail.bounding_box()
        assert box["x"] >= 0 and box["x"] + box["width"] <= viewport["width"]
        assert _no_sideways_scroll(page)
        head_visible = page.locator(".audit-head").is_visible()
        assert head_visible == (viewport["width"] >= 1000)
        for selector in (".filter-bar__chips--links .filter-chip__box", ".audit-pager .text-link"):
            assert page.locator(selector).first.bounding_box()["height"] >= MIN_TAP_PX
    finally:
        context.close()


def _relative_luminance(rgb):
    def channel(value):
        value /= 255
        return value / 12.92 if value <= 0.03928 else ((value + 0.055) / 1.055) ** 2.4
    red, green, blue = (channel(v) for v in rgb[:3])
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def _ink_contrast(page, locator):
    """Contrast of an element's text as drawn: the most common pixel is the
    surface, the pixel farthest from it is the ink."""
    import io
    from collections import Counter

    from PIL import Image
    image = Image.open(io.BytesIO(locator.screenshot())).convert("RGB")
    raw = image.tobytes()
    pixels = list(zip(raw[0::3], raw[1::3], raw[2::3]))
    surface = Counter(pixels).most_common(1)[0][0]
    ink = max(pixels, key=lambda p: sum((a - b) ** 2 for a, b in zip(p, surface)))
    light, dark = sorted((_relative_luminance(ink), _relative_luminance(surface)), reverse=True)
    return (light + 0.05) / (dark + 0.05)


@pytest.mark.parametrize("scheme", ["light", "dark"])
def test_phone_filter_is_one_scrolling_row_with_the_chosen_chip_marked(
        new_context, app_server_in_process, scheme):
    server = app_server_in_process
    fx.seed_fleet(server.state_dir)
    context = new_context(
        viewport={"width": 360, "height": 740}, color_scheme=scheme)
    page = context.new_page()
    try:
        _login(page, server.base_url())
        page.goto(server.base_url() + "/audit?category=failed")
        page.locator("main").wait_for(state="visible")
        page.wait_for_function("document.readyState === 'complete'")
        assert _no_sideways_scroll(page)
        strip = page.locator("nav.filter-bar__chips--links")
        boxes = page.locator("nav.filter-bar__chips--links .filter-chip__box")
        assert boxes.count() == 7
        tops = boxes.evaluate_all("els => els.map(e => Math.round(e.getBoundingClientRect().top))")
        assert len(set(tops)) == 1, "the chips share one line"
        assert strip.evaluate("e => e.scrollWidth > e.clientWidth"), "the row scrolls sideways"
        assert strip.evaluate("e => getComputedStyle(e).overflowX") == "auto"
        for height in boxes.evaluate_all("els => els.map(e => e.getBoundingClientRect().height)"):
            assert height >= MIN_TAP_PX
        current = page.locator("nav.filter-bar__chips--links a[aria-current='true']")
        assert current.count() == 1 and current.inner_text().strip() == "Failed"
        # The chosen chip opens in view, so a chosen category is never hidden off the edge.
        inside = current.evaluate(
            "e => { const r = e.getBoundingClientRect(), s = e.parentElement.getBoundingClientRect();"
            " return r.left >= s.left && r.right <= s.right; }")
        assert inside
        # Its text is centred in the filled box.
        offset = current.evaluate(
            "e => { const t = e.querySelector('.filter-chip__text').getBoundingClientRect(),"
            " b = e.querySelector('.filter-chip__box').getBoundingClientRect();"
            " return [Math.abs((t.left + t.right) / 2 - (b.left + b.right) / 2),"
            " Math.abs((t.top + t.bottom) / 2 - (b.top + b.bottom) / 2)]; }")
        assert offset[0] <= 1 and offset[1] <= 2
    finally:
        context.close()


@pytest.mark.parametrize("scheme", ["light", "dark"])
def test_opened_event_is_a_tinted_label_and_value_panel(
        new_context, app_server_in_process, scheme):
    context, page = None, None
    server = app_server_in_process
    fx.seed_fleet(server.state_dir)
    conn = fleet_db.connect(server.state_dir)
    try:
        with fleet_db.transaction(conn):
            fleet_db.audit_append(
                conn, fx.ACTOR, "frame.register", "device", "d_00000001", "ok",
                None, now=int(time.time()) + 1000)
    finally:
        conn.close()
    context = new_context(viewport={"width": 390, "height": 844}, color_scheme=scheme)
    page = context.new_page()
    try:
        _login(page, server.base_url())
        page.goto(server.base_url() + "/audit")
        _wait_ready(page)
        first = page.locator(".audit-event").first
        first.locator("summary").click()
        page.wait_for_function("() => document.querySelector('.audit-event details').open")
        panel = first.locator(".audit-event__detail")
        assert panel.evaluate(
            "e => getComputedStyle(e).backgroundColor !== 'rgba(0, 0, 0, 0)'"), "the panel is tinted"
        labels = first.locator("dt")
        for index in range(labels.count()):
            label, value = labels.nth(index), first.locator("dd").nth(index)
            lbox, vbox = label.bounding_box(), value.bounding_box()
            assert vbox["x"] > lbox["x"] + lbox["width"] - 1, "the value sits right of its label"
            assert abs(vbox["y"] - lbox["y"]) < 8, "label and value share a line"
            assert label.evaluate("e => parseFloat(getComputedStyle(e).fontSize)") >= 13
            assert _ink_contrast(page, label) >= 4.5
            assert _ink_contrast(page, value) >= 4.5
        gaps = first.locator("dt").evaluate_all(
            "els => els.map(e => e.getBoundingClientRect().top)")
        assert all(b - a >= 20 for a, b in zip(gaps, gaps[1:])), "rows are spaced apart"
    finally:
        context.close()
