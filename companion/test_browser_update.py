"""Browser checks for the Update page's Install/Cancel action flows: the
JS `data-confirm` misclick guard versus the no-JS-safe server
confirmation gate (D-04), the full install -> scheduled -> cancel round
trip, and the D-02 mobile-fit gate for the tab bar's More sheet
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
    VIEWPORT_DESKTOP, VIEWPORT_PHONE, _assert_hit_target, _login, _no_js_page,
)
from server import atomic_io
from server import firmware_registry as fr

pytestmark = pytest.mark.browser

# D-02's own mobile-fit gate names these two exact viewports (42-UI-SPEC.md's
# executor verification checklist) -- 375x812 is not one of
# companion/test_browser_ux_helpers.py's shared named constants (whose own
# "minimum supported" floor is 360px), so it is declared here rather than
# reusing VIEWPORT_MIN_SUPPORTED, which is a different, narrower viewport.
VIEWPORT_375 = {"width": 375, "height": 812}

_NOW = "2026-09-28T12:00:00+00:00"
_RUNNING_VERSION = "fw-v1.0.0"
_AVAILABLE_VERSION = "fw-v1.1.0"


def _seed_two_releases(state_dir):
    """Two published releases (fw-v1.0.0 running, fw-v1.1.0 available)
    through firmware_registry's own write API, plus a hand-written
    device_report.json -- byos-owned in production, matching
    companion/test_update_page.py's own _seed_update_state().
    """
    os.makedirs(str(state_dir), exist_ok=True)
    for version in (_RUNNING_VERSION, _AVAILABLE_VERSION):
        image_path = os.path.join(str(state_dir), version + ".bin")
        image_bytes = ("fake-firmware-" + version).encode()
        with open(image_path, "wb") as fh:
            fh.write(image_bytes)
        manifest = {
            "version": version, "sha256": hashlib.sha256(image_bytes).hexdigest(),
            "size": len(image_bytes), "released_at": _NOW, "commit": "a" * 40,
            "notes": ["release " + version],
        }
        fr.publish_release(str(state_dir), manifest, image_path, now=_NOW)
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
# JS confirm-dialog misclick guard versus the server-side gate (D-04).
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
# D-02's mobile-fit gate: measured, not assumed.
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

        print(
            "D-02 mobile-fit: %dpx/%s More-sheet link heights=%r (floor 44px)"
            % (viewport["width"], lang, heights))
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
