"""Browser checks for the Update page's Install/Cancel action flows: the
JS `data-confirm` misclick guard versus the no-JS-safe server
confirmation gate, the full install -> scheduled -> cancel round
trip, and the mobile-fit gate for the tab bar's More sheet
(375px/390px, English/French) plus the >=960px sidebar Advanced group.

Real Playwright browser throughout -- never markup-string assertions
(companion/test_suite_guards.py's behaviour-over-source rule).
companion/test_update_page.py and companion/test_update_actions.py
already cover the served markup and the plain-request POST behaviour
in-process; this module proves the JS-driven interaction and the
measured hit-target/overflow geometry neither of those can.

Read-only checks (the mobile-fit gate, the desktop sidebar) share one
module-scoped, read-only `server` fixture -- companion/test_browser_ux_02.py's
own module docstring documents the same rule. Every check that installs
or cancels a real update gets its own function-scoped server via
`make_app_server`, since it mutates the registry.
"""
import hashlib
import json
import os

import pytest

from companion import auth, layout
from companion.pages import update_page
from companion.test_browser_ux_helpers import (
    RELEASE_SEED_AVAILABLE_VERSION, RELEASE_SEED_NOW, RELEASE_SEED_RUNNING_VERSION,
    VIEWPORT_DESKTOP, VIEWPORT_MIN_SUPPORTED, VIEWPORT_PHONE, _assert_hit_target, _login, _no_js_page,
    seed_two_releases as _seed_two_releases,
)
from server import atomic_io
from server import firmware_registry as fr

pytestmark = pytest.mark.browser

# The Update page's mobile-fit requirement names these two exact viewports.
# 375x812 is not one of companion/test_browser_ux_helpers.py's shared
# named constants (whose own
# "minimum supported" floor is 360px), so it is declared here rather than
# reusing VIEWPORT_MIN_SUPPORTED, which is a different, narrower viewport.
VIEWPORT_375 = {"width": 375, "height": 812}

_NOW = RELEASE_SEED_NOW
_RUNNING_VERSION = RELEASE_SEED_RUNNING_VERSION
_AVAILABLE_VERSION = RELEASE_SEED_AVAILABLE_VERSION


_THIRD_VERSION = "fw-v1.2.0"


def _seed_three_releases_with_realistic_notes(state_dir):
    """Three published releases (one running, two available), each with two
    realistic-length notes -- wide enough, in aggregate, that a plain
    desktop table would measure roughly twice a 375px viewport's own
    width if rendered unstacked.
    """
    os.makedirs(str(state_dir), exist_ok=True)
    releases = (
        (_RUNNING_VERSION, ["Initial factory image."]),
        (_AVAILABLE_VERSION, [
            "Fixes the OTA netif double-init panic that blocked every remote update.",
            "Adds a watchdog feed between the HTTPS OTA begin call and the first perform.",
        ]),
        (_THIRD_VERSION, [
            "Improves battery telemetry accuracy under low-temperature conditions.",
            "Reworks the panel refresh-spacing guard so it survives a mid-wake reset.",
        ]),
    )
    for version, notes in releases:
        image_path = os.path.join(str(state_dir), version + ".bin")
        image_bytes = ("fake-firmware-" + version).encode()
        with open(image_path, "wb") as fh:
            fh.write(image_bytes)
        manifest = {
            "version": version, "sha256": hashlib.sha256(image_bytes).hexdigest(),
            "size": len(image_bytes), "released_at": _NOW, "commit": "a" * 40,
            "notes": notes,
        }
        fr.publish_release(str(state_dir), manifest, image_path, now=_NOW)
    device_report = {
        "schema": 1, "next_seq": 1,
        "devices": {
            "dev1": {"fw_version": _RUNNING_VERSION, "reported_at": _NOW, "events": []}},
    }
    atomic_io.atomic_write(fr.device_report_path(str(state_dir)), json.dumps(device_report))


_BENCH_VERSION = "fw-v1.0.5-bench1"


def _seed_running_bench_and_newer(state_dir):
    """The real-hardware shape: fw-v1.0.0 running with about 30 notes, a
    bench build published (and once installed over the air) that the owner
    must never be offered, and a newer installable fw-v1.1.0. Published through
    firmware_registry's write API; the bench install time is set on the
    saved registry because only a device result appends to it.
    """
    os.makedirs(str(state_dir), exist_ok=True)
    releases = (
        (_RUNNING_VERSION, "2026-09-20T09:00:00+00:00", False,
         ["Note %02d: a realistic commit summary that runs to a full line of text." % n
          for n in range(30)]),
        (_BENCH_VERSION, "2026-09-27T09:00:00+00:00", True, ["Bench build."]),
        (_AVAILABLE_VERSION, "2026-09-28T09:00:00+00:00", False, ["Fixes the OTA netif panic."]),
    )
    for version, published_at, bench, notes in releases:
        image_path = os.path.join(str(state_dir), version + ".bin")
        image_bytes = ("fake-firmware-" + version).encode()
        with open(image_path, "wb") as fh:
            fh.write(image_bytes)
        manifest = {
            "version": version, "sha256": hashlib.sha256(image_bytes).hexdigest(),
            "size": len(image_bytes), "released_at": published_at, "commit": "a" * 40,
            "notes": notes,
        }
        fr.publish_release(str(state_dir), manifest, image_path, bench=bench, now=published_at)
    registry = fr.load_registry(str(state_dir))
    for release in registry["releases"]:
        if release["version"] == _BENCH_VERSION:
            release["installed_at"] = ["2026-09-28T07:30:00+00:00"]
    fr._save_registry(str(state_dir), registry)
    device_report = {
        "schema": 1, "next_seq": 1,
        "devices": {
            "dev1": {"fw_version": _RUNNING_VERSION, "reported_at": _NOW, "events": []}},
    }
    atomic_io.atomic_write(fr.device_report_path(str(state_dir)), json.dumps(device_report))


@pytest.fixture(scope="module")
def server(module_app_server_factory):
    """The shared, read-only seeded fixture the mobile-fit and sidebar
    checks measure against -- module-scoped because neither ever
    schedules or cancels a real update.
    """
    return module_app_server_factory(seed=_seed_two_releases)


def _install_submit(page):
    return page.locator(
        'form[action="%s"] button[type="submit"]' % update_page.INSTALL_ROUTE).first


# A DOM `.click()` inside page.evaluate(), never Playwright's own
# pointer-based click: at 390px the header's expanded no-JS fallback nav
# (companion/static/nav-dropdown.js normally collapses it) pushes page
# content down far enough that the Install button's real screen position
# sits under the fixed tab bar, which a pointer-based click correctly
# refuses to punch through. companion/test_browser_ux_helpers.py's own
# _SUBMIT_PROBE uses the identical technique for every other no-JS form
# submission in this test suite -- page.evaluate() runs via CDP, not as
# a page <script>, so it is unaffected by java_script_enabled=False.
_CLICK_FORM_SUBMIT_PROBE = (
    "action => {"
    "  const form = document.querySelector('form[action=\"' + action + '\"]');"
    "  if (!form) return 'no-form';"
    "  const btn = form.querySelector('button[type=\"submit\"]');"
    "  if (!btn) return 'no-button';"
    "  btn.click();"
    "  return 'clicked';"
    "}")


def _click_install_form_no_js(page):
    with page.expect_navigation():
        result = page.evaluate(_CLICK_FORM_SUBMIT_PROBE, update_page.INSTALL_ROUTE)
    assert result == "clicked", (
        "expected the Install form's submit button, got %r" % (result,))


# ==========================================================================
# JS confirm-dialog misclick guard versus the server-side gate.
# ==========================================================================


def test_js_confirm_accept_lands_on_server_confirm_page_then_schedules(
        new_context, make_app_server):
    server = make_app_server(seed=_seed_two_releases)
    context = new_context(viewport=VIEWPORT_PHONE)
    try:
        page = context.new_page()
        base_url = server.base_url()
        _login(page, base_url)
        page.goto(base_url + layout.UPDATE_ROUTE)

        page.once("dialog", lambda dialog: dialog.accept())
        _install_submit(page).click()
        page.wait_for_load_state("networkidle")
        assert page.url == base_url + update_page.INSTALL_ROUTE, (
            "expected accepting the native confirm() to submit the form "
            "with no 'confirm' field, landing on the server confirm page")
        assert fr.load_registry(server.state_dir)["schedule"] is None, (
            "the server confirm page must not have scheduled anything yet")

        page.locator(
            'form[action="%s"] button[type="submit"]' % update_page.INSTALL_ROUTE
        ).click()
        page.wait_for_load_state("networkidle")
        assert page.url == base_url + layout.UPDATE_ROUTE
        registry = fr.load_registry(server.state_dir)
        assert registry["schedule"]["state"] == "scheduled"
        assert registry["schedule"]["version"] == _AVAILABLE_VERSION
        assert page.locator('form[action="%s"]' % update_page.CANCEL_ROUTE).count() == 1
    finally:
        context.close()


def test_js_confirm_dismiss_sends_no_request_registry_unchanged(new_context, make_app_server):
    server = make_app_server(seed=_seed_two_releases)
    context = new_context(viewport=VIEWPORT_PHONE)
    try:
        page = context.new_page()
        base_url = server.base_url()
        _login(page, base_url)
        page.goto(base_url + layout.UPDATE_ROUTE)

        page.once("dialog", lambda dialog: dialog.dismiss())
        _install_submit(page).click()
        page.wait_for_timeout(300)
        assert page.url == base_url + layout.UPDATE_ROUTE, (
            "a dismissed confirm() must never submit the form")
        assert fr.load_registry(server.state_dir)["schedule"] is None
    finally:
        context.close()


def test_no_js_install_goes_straight_to_confirm_page_and_completes(
        new_context, make_app_server):
    server = make_app_server(seed=_seed_two_releases)
    base_url = server.base_url()
    with _no_js_page(new_context, base_url, layout.UPDATE_ROUTE) as page:
        _click_install_form_no_js(page)
        assert page.url == base_url + update_page.INSTALL_ROUTE, (
            "with scripts blocked, the Install click submits the form "
            "directly to the confirm page (no data-confirm handler ran)")
        assert fr.load_registry(server.state_dir)["schedule"] is None

        _click_install_form_no_js(page)
        assert page.url == base_url + layout.UPDATE_ROUTE
        registry = fr.load_registry(server.state_dir)
        assert registry["schedule"]["state"] == "scheduled"
        assert registry["schedule"]["version"] == _AVAILABLE_VERSION


def test_full_flow_install_then_scheduled_then_cancel_returns_to_available(
        new_context, make_app_server):
    server = make_app_server(seed=_seed_two_releases)
    context = new_context(viewport=VIEWPORT_PHONE)
    try:
        page = context.new_page()
        base_url = server.base_url()
        _login(page, base_url)
        page.goto(base_url + layout.UPDATE_ROUTE)

        page.once("dialog", lambda dialog: dialog.accept())
        _install_submit(page).click()
        page.wait_for_load_state("networkidle")
        page.locator(
            'form[action="%s"] button[type="submit"]' % update_page.INSTALL_ROUTE
        ).click()
        page.wait_for_load_state("networkidle")

        cancel_form = page.locator('form[action="%s"]' % update_page.CANCEL_ROUTE)
        assert cancel_form.count() == 1
        cancel_form.locator('button[type="submit"]').click()
        page.wait_for_load_state("networkidle")

        assert fr.load_registry(server.state_dir)["schedule"] is None
        assert page.locator('form[action="%s"]' % update_page.CANCEL_ROUTE).count() == 0
    finally:
        context.close()


# ==========================================================================
# The mobile-fit gate: measured, not assumed.
# ==========================================================================

_MORE_SHEET_LINK_SELECTOR = ".tab-bar__more-panel a.mobile-nav__link"

# Line count is read from the rendered text's own line boxes
# (Range.getClientRects(), one rect per line, deduplicated by their
# rounded top), never el.clientHeight / line-height -- the 44px tap
# target's own vertical padding makes that ratio come out above 1 even
# for a single line of text sized well under the box.
_OVERFLOW_PROBE = (
    "sel => [...document.querySelectorAll(sel)].map(el => {"
    "  const range = document.createRange();"
    "  range.selectNodeContents(el);"
    "  const tops = new Set("
    "    [...range.getClientRects()].map(r => Math.round(r.top)));"
    "  return {scrollWidth: el.scrollWidth, clientWidth: el.clientWidth,"
    "          lines: tops.size};"
    "})"
)


@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize(
    "viewport", [VIEWPORT_375, VIEWPORT_PHONE], ids=["375", "390"])
def test_more_sheet_fits_health_device_update_at_phone_widths(
        new_context, server, viewport, lang):
    """At 375px and 390px, in English and French: the tab bar's More sheet
    holds exactly Health, Device and Update, each with a measured hit box
    at least 44px tall, no wrapping or truncated text, the "More" summary
    cell's own box unchanged from another tab-bar cell's, and the header
    dropdown's preferences panel gains no /update link.
    """
    context = new_context(viewport=viewport)
    try:
        page = context.new_page()
        base_url = server.base_url()
        context.add_cookies([{
            "name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": base_url}])
        _login(page, base_url)
        page.goto(base_url + layout.UPDATE_ROUTE)
        if page.viewport_size["width"] != viewport["width"]:
            raise AssertionError("expected the measurement to be taken at %dpx" % (viewport["width"],))

        page.locator(".tab-bar__more > .tab-bar__link").click()
        page.locator(_MORE_SHEET_LINK_SELECTOR).first.wait_for(state="visible")

        links = page.locator(_MORE_SHEET_LINK_SELECTOR)
        count = links.count()
        assert count == 3, (
            "expected exactly 3 links (Health, Device, Update) in the More "
            "sheet at %dpx/%s, got %d" % (viewport["width"], lang, count))

        heights = []
        for index in range(count):
            # :nth-of-type (1-based), not Playwright's ">> nth=" chaining
            # syntax -- _assert_hit_target()'s underlying _hit_area() runs
            # this selector through document.querySelector() directly.
            selector = "%s:nth-of-type(%d)" % (_MORE_SHEET_LINK_SELECTOR, index + 1)
            seen = _assert_hit_target(
                page, selector,
                "More sheet link %d at %dpx/%s" % (index, viewport["width"], lang))
            heights.append(seen["hit"][1])

        overflow = page.evaluate(_OVERFLOW_PROBE, _MORE_SHEET_LINK_SELECTOR)
        for index, entry in enumerate(overflow):
            assert entry["scrollWidth"] <= entry["clientWidth"] + 0.5, (
                "More sheet link %d truncated at %dpx/%s: scrollWidth %r > "
                "clientWidth %r" % (
                    index, viewport["width"], lang, entry["scrollWidth"],
                    entry["clientWidth"]))
            assert entry["lines"] <= 1, (
                "More sheet link %d wraps to %d line(s) at %dpx/%s"
                % (index, entry["lines"], viewport["width"], lang))

        summary_box = page.locator(".tab-bar__more > .tab-bar__link").bounding_box()
        other_cell_box = page.locator("nav.tab-bar > a.tab-bar__link").first.bounding_box()
        assert abs(summary_box["height"] - other_cell_box["height"]) < 0.5, (
            "expected the More summary cell's height to match the other "
            "tab-bar cells' at %dpx/%s, got %r vs %r"
            % (viewport["width"], lang, summary_box["height"], other_cell_box["height"]))

        header_dropdown = page.locator("#%s" % layout.MOBILE_NAV_ID)
        assert header_dropdown.locator('a[href="%s"]' % layout.UPDATE_ROUTE).count() == 0
        assert header_dropdown.locator(".nav-status").count() == 0
        assert page.locator(".dashboard-sidebar .nav-status").count() == 0
        assert page.locator(
            '%s[href="%s"][aria-current="page"]'
            % (_MORE_SHEET_LINK_SELECTOR, layout.UPDATE_ROUTE)).count() == 1

        print(
            "D-02 mobile-fit: %dpx/%s More-sheet link heights=%r (floor 44px)"
            % (viewport["width"], lang, heights))
    finally:
        context.close()


@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize(
    "viewport", [VIEWPORT_375, VIEWPORT_PHONE], ids=["375", "390"])
def test_history_cards_fit_at_phone_widths_with_no_overflow(
        new_context, make_app_server, viewport, lang):
    """At 375px and 390px, in English and French, with three releases and two realistic
    notes each: the Version history renders as stacked cards (the desktop table stays
    hidden), nothing overflows the viewport horizontally, and the first Install button is
    fully inside the viewport and enabled.
    """
    server = make_app_server(seed=_seed_three_releases_with_realistic_notes)
    context = new_context(viewport=viewport)
    try:
        page = context.new_page()
        base_url = server.base_url()
        context.add_cookies([{
            "name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": base_url}])
        _login(page, base_url)
        page.goto(base_url + layout.UPDATE_ROUTE)
        if page.viewport_size["width"] != viewport["width"]:
            raise AssertionError("expected the measurement to be taken at %dpx" % (viewport["width"],))

        cards = page.locator("ul.data-cards > li.data-card")
        assert cards.count() == 3, (
            "expected 3 stacked release cards at %dpx/%s, got %d"
            % (viewport["width"], lang, cards.count()))
        table = page.locator("table.data-table--firmware-history")
        assert table.count() == 1
        assert not table.is_visible(), (
            "expected the desktop table to stay hidden below the 960px breakpoint "
            "at %dpx/%s" % (viewport["width"], lang))

        no_overflow = page.evaluate(
            "() => document.documentElement.scrollWidth <= "
            "document.documentElement.clientWidth + 0.5")
        assert no_overflow, "expected no horizontal overflow at %dpx/%s" % (viewport["width"], lang)

        install_button = _install_submit(page)
        box = install_button.bounding_box()
        assert box is not None, (
            "expected a visible Install button on at least one card at %dpx/%s"
            % (viewport["width"], lang))
        assert box["x"] >= -0.5, (
            "Install button's left edge (%r) sits off-screen at %dpx/%s"
            % (box["x"], viewport["width"], lang))
        assert box["x"] + box["width"] <= viewport["width"] + 0.5, (
            "Install button's right edge (%r) exceeds the %dpx viewport at %s"
            % (box["x"] + box["width"], viewport["width"], lang))
        assert install_button.is_enabled()

        desc = page.locator("li.data-card p.data-card__desc").first
        desc_box = desc.bounding_box()
        assert desc_box is not None, "expected a visible notes paragraph in at least one card"
        assert desc_box["width"] <= viewport["width"] + 0.5, (
            "notes paragraph wider than the %dpx viewport at %s" % (viewport["width"], lang))
    finally:
        context.close()


@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize(
    "viewport", [VIEWPORT_375, VIEWPORT_DESKTOP], ids=["375", "1280"])
def test_running_badge_and_collapsed_notes_work_at_phone_and_desktop_widths(
        new_context, make_app_server, viewport, lang):
    """At 375x812 and 1280x900, in English and French, with a running release carrying about
    30 notes, an earlier bench install and a newer release: the Running badge is visible on
    the running row/card, the notes toggle starts closed with its list hidden, its summary is
    at least 44px tall and inside the viewport, clicking it reveals the list, nothing overflows
    horizontally and the first Install button stays visible and enabled.
    """
    server = make_app_server(seed=_seed_running_bench_and_newer)
    context = new_context(viewport=viewport)
    try:
        page = context.new_page()
        base_url = server.base_url()
        context.add_cookies([{
            "name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": base_url}])
        _login(page, base_url)
        page.goto(base_url + layout.UPDATE_ROUTE)
        if page.viewport_size["width"] != viewport["width"]:
            raise AssertionError("expected the measurement to be taken at %dpx" % (viewport["width"],))
        phone = viewport["width"] < 960
        where = "%dpx/%s" % (viewport["width"], lang)

        badge = page.locator(".update-history__running-badge:visible")
        assert badge.count() == 1, "expected one visible Running badge at %s" % where
        assert badge.inner_text().strip().lower() == ("running" if lang == "en" else "en cours")

        visible_notes = page.locator("details.update-history__notes:visible")
        assert visible_notes.count() == 1, (
            "expected only the running release's notes to need a toggle at %s" % where)
        assert visible_notes.evaluate("el => el.open") is False
        summary = visible_notes.locator("summary")
        list_locator = visible_notes.locator("ul.update-history__notes-list")
        assert not list_locator.is_visible(), "notes list should start closed at %s" % where
        box = summary.bounding_box()
        assert box["height"] >= 44 - 0.5, "summary is %r tall at %s" % (box["height"], where)
        assert box["x"] >= -0.5 and box["x"] + box["width"] <= viewport["width"] + 0.5
        assert box["y"] >= 0

        summary.click()
        assert visible_notes.evaluate("el => el.open") is True
        assert list_locator.is_visible()
        assert list_locator.locator("li").count() == 30

        assert page.evaluate(
            "() => document.documentElement.scrollWidth <= "
            "document.documentElement.clientWidth + 0.5"), (
            "expected no horizontal overflow at %s" % where)
        # :visible, not _install_submit(): at desktop the hidden phone card list comes
        # first in the DOM and would answer with an invisible button.
        install_button = page.locator(
            'form[action="%s"]:visible button[type="submit"]' % update_page.INSTALL_ROUTE
        ).first
        install_box = install_button.bounding_box()
        assert install_box is not None and install_button.is_enabled()
        assert install_box["x"] + install_box["width"] <= viewport["width"] + 0.5
        if phone:
            assert page.locator("p.data-card__desc").first.is_visible()
    finally:
        context.close()


@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize(
    "viewport", [VIEWPORT_DESKTOP, VIEWPORT_PHONE, VIEWPORT_MIN_SUPPORTED],
    ids=["1280", "390", "360"])
def test_summary_and_eligible_releases_at_every_width(
        new_context, make_app_server, viewport, lang):
    """At 1280, 390 and 360px in English and French, with a bench build published beside
    real releases: the installed-software summary names the running version once, the bench
    version is nowhere on the page, nothing overflows, the eligible Install button is a
    full-size target with a visible focus ring, and activating it reaches the server
    confirmation page whose Cancel link returns to Update with nothing scheduled.
    """
    server = make_app_server(seed=_seed_running_bench_and_newer)
    context = new_context(viewport=viewport)
    try:
        page = context.new_page()
        base_url = server.base_url()
        context.add_cookies([{
            "name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": base_url}])
        _login(page, base_url)
        page.goto(base_url + layout.UPDATE_ROUTE)
        where = "%dpx/%s" % (viewport["width"], lang)

        summary = page.locator("section.update-summary")
        assert summary.count() == 1 and summary.is_visible()
        headline = summary.locator(".update-summary__headline")
        assert _RUNNING_VERSION in headline.inner_text()
        assert headline.locator("svg").count() == 1
        assert summary.locator("time").count() == 1, "one relevant time at %s" % where
        assert "bench" not in page.locator("main").inner_text().lower(), (
            "a bench build must not be shown to the owner at %s" % where)
        assert page.locator('input[name="version"][value="%s"]' % _BENCH_VERSION).count() == 0

        assert page.evaluate(
            "() => document.documentElement.scrollWidth <= "
            "document.documentElement.clientWidth + 0.5"), "overflow at %s" % where

        container = (
            "ul.data-cards" if viewport["width"] < 960 else "table.data-table--firmware-history")
        selector = '%s form[action="%s"] button[type="submit"]' % (
            container, update_page.INSTALL_ROUTE)
        install = page.locator(selector).first
        _assert_hit_target(page, selector, where)
        install.focus()
        outline = install.evaluate(
            "el => { const s = getComputedStyle(el);"
            " return [s.outlineStyle, parseFloat(s.outlineWidth)]; }")
        assert outline[0] != "none" and outline[1] >= 2, "no focus ring at %s: %r" % (where, outline)

        page.on("dialog", lambda dialog: dialog.accept())
        with page.expect_navigation():
            install.click()
        assert update_page.INSTALL_ROUTE in page.url
        cancel = page.locator('main a[href="%s"]' % layout.UPDATE_ROUTE)
        with page.expect_navigation():
            cancel.click()
        assert page.url.endswith(layout.UPDATE_ROUTE)
        assert page.locator('form[action="%s"]' % update_page.CANCEL_ROUTE).count() == 0, (
            "cancelling at the confirmation page must leave nothing scheduled at %s" % where)
    finally:
        context.close()


def test_desktop_sidebar_advanced_group_fits_with_no_overlap(new_context, server):
    """At 1280px, the sidebar's Advanced group renders three links (Health,
    Device, Update), stacked with no overlap.
    """
    context = new_context(viewport=VIEWPORT_DESKTOP)
    try:
        page = context.new_page()
        _login(page, server.base_url())
        page.goto(server.base_url() + layout.UPDATE_ROUTE)
        group = page.locator(".nav-group--advanced")
        links = group.locator("a.sidebar-link")
        count = links.count()
        assert count == 3, "expected exactly 3 sidebar Advanced links, got %d" % (count,)
        boxes = [links.nth(i).bounding_box() for i in range(count)]
        for index in range(count - 1):
            upper, lower = boxes[index], boxes[index + 1]
            assert upper["y"] + upper["height"] <= lower["y"] + 0.5, (
                "expected sidebar Advanced links to stack without overlap, "
                "got %r then %r" % (upper, lower))
    finally:
        context.close()
