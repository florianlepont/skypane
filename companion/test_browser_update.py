"""Browser checks for the Update page: its call-to-action card and compact
version rows at every supported width, and the Install/Cancel action flows: the
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
from skypane_fw_image import build_image

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
        image_bytes = build_image(version)
        with open(image_path, "wb") as fh:
            fh.write(image_bytes)
        manifest = {
            "version": version, "sha256": hashlib.sha256(image_bytes).hexdigest(),
            "size": len(image_bytes), "released_at": _NOW, "commit": "a" * 40,
            "hardware_type": fr.hardware.LEGACY_KEY,
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
         [("Note %02d: a realistic commit summary that runs to a full line of text and then well past "
          "the end of the widest line a dialog allows, so it is always cut." % n)
          for n in range(30)]),
        (_BENCH_VERSION, "2026-09-27T09:00:00+00:00", True, ["Bench build."]),
        (_AVAILABLE_VERSION, "2026-09-28T09:00:00+00:00", False, ["Fixes the OTA netif panic."]),
    )
    for version, published_at, bench, notes in releases:
        image_path = os.path.join(str(state_dir), version + ".bin")
        image_bytes = build_image(version)
        with open(image_path, "wb") as fh:
            fh.write(image_bytes)
        manifest = {
            "version": version, "sha256": hashlib.sha256(image_bytes).hexdigest(),
            "size": len(image_bytes), "released_at": published_at, "commit": "a" * 40,
            "hardware_type": fr.hardware.LEGACY_KEY,
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


_MANY_OLDEST = "fw-v1.0.0"
_MANY_RUNNING = "fw-v1.6.0"
_MANY_NEWEST = "fw-v1.11.0"
_UNBROKEN_NOTE = "x" * 90


def _seed_many_releases(state_dir, scenario=None):
    """Twelve releases fw-v1.0.0..fw-v1.11.0, published a day apart, the frame running
    fw-v1.6.0 (so five are older and five newer) and the oldest carrying five notes, one of
    them an unbroken 90-character token. `scenario` adds a schedule on the newest release:
    "scheduled", "in_progress" (acknowledged by the device) or "failed".
    """
    os.makedirs(str(state_dir), exist_ok=True)
    for minor in range(12):
        version = "fw-v1.%d.0" % minor
        published_at = "2026-09-%02dT09:00:00+00:00" % (minor + 1)
        notes = ["Change %d for %s" % (n, version) for n in range(1 if minor else 5)]
        if minor == 0:
            notes[-1] = _UNBROKEN_NOTE
        image_path = os.path.join(str(state_dir), version + ".bin")
        image_bytes = build_image(version)
        with open(image_path, "wb") as fh:
            fh.write(image_bytes)
        fr.publish_release(str(state_dir), {
            "version": version, "sha256": hashlib.sha256(image_bytes).hexdigest(),
            "size": len(image_bytes), "released_at": published_at, "commit": "a" * 40,
            "hardware_type": fr.hardware.LEGACY_KEY,
            "notes": notes,
        }, image_path, now=published_at)
    registry = fr.load_registry(str(state_dir))
    for release in registry["releases"]:
        if release["version"] == _MANY_RUNNING:
            release["installed_at"] = ["2026-09-07T12:00:00+00:00"]
    events = []
    if scenario:
        newest = [r for r in registry["releases"] if r["version"] == _MANY_NEWEST][0]
        registry["schedule"] = {
            "id": "s1", "version": _MANY_NEWEST, "sha256": newest["sha256"],
            "scheduled_at": _NOW, "state": "failed" if scenario == "failed" else "scheduled",
            "attempts": 3 if scenario == "failed" else 0,
            "failed_at": _NOW if scenario == "failed" else None, "last_result": None,
        }
    if scenario == "in_progress":
        events = [{"seq": 1, "at": _NOW, "kind": "offered", "schedule_id": "s1",
                   "token": None, "version": _MANY_NEWEST}]
    fr._save_registry(str(state_dir), registry)
    device_report = {
        "schema": 1, "next_seq": 2,
        "devices": {"dev1": {
            "fw_version": _MANY_RUNNING, "reported_at": _NOW, "events": events}},
    }
    atomic_io.atomic_write(fr.device_report_path(str(state_dir)), json.dumps(device_report))


FLEET_ROUTE = "/fleet"


def _reveal(page, which):
    """The Fleet page shows the update card and the version table inline: nothing to open.
    The table waits for its first row so a read right after navigation is settled."""
    if which == "versions":
        page.wait_for_function(
            "() => document.querySelectorAll('tr.update-table__row').length > 0", timeout=10000)


def _dismiss(page):
    """Nothing to close: the card and the list are part of the page."""
FLEET_FRAME_HREF = "/fleet?frame=live"


def _page_has_no_horizontal_overflow(page):
    return page.evaluate(
        "() => document.documentElement.scrollWidth <= "
        "document.documentElement.clientWidth + 0.5")


# Every monospace version identifier on the page, reported when its text lays out on more
# than one line (read from the text's own line boxes, like _OVERFLOW_PROBE below).
_WRAPPED_VERSION_PROBE = (
    "() => [...document.querySelectorAll('main .mono')].filter(el => {"
    "  const range = document.createRange();"
    "  range.selectNodeContents(el);"
    "  return new Set([...range.getClientRects()].map(r => Math.round(r.top))).size > 1;"
    "}).map(el => el.textContent)"
)

# The resolved accent colour, read by painting a throwaway element with the token.
_ACCENT_PROBE = (
    "() => {"
    "  const probe = document.createElement('div');"
    "  probe.style.backgroundColor = 'var(--color-accent)';"
    "  document.body.appendChild(probe);"
    "  const colour = getComputedStyle(probe).backgroundColor;"
    "  probe.remove();"
    "  return colour;"
    "}"
)


def _background(locator):
    return locator.evaluate("el => getComputedStyle(el).backgroundColor")


# A DOM `.click()` on the submit button of the form matching `selector` (see
# _CLICK_FORM_SUBMIT_PROBE above for why a DOM click rather than a pointer click).
_CLICK_FORM_SUBMIT_PROBE_IN = (
    "selector => {"
    "  const form = document.querySelector(selector);"
    "  if (!form) return 'no-form';"
    "  form.querySelector('button[type=\"submit\"]').click();"
    "  return 'clicked';"
    "}")


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
# pointer-based click: at 390px the Install button's real screen position
# can sit under the fixed tab bar, which a pointer-based click correctly
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
# Install goes through the server-side confirmation page.
# ==========================================================================


def test_install_lands_on_server_confirm_page_then_schedules(
        new_context, make_app_server):
    server = make_app_server(seed=_seed_two_releases)
    context = new_context(viewport=VIEWPORT_PHONE)
    try:
        page = context.new_page()
        base_url = server.base_url()
        _login(page, base_url)
        page.goto(base_url + FLEET_ROUTE)

        _install_submit(page).click()
        page.wait_for_load_state("networkidle")
        assert page.url == base_url + update_page.INSTALL_ROUTE, (
            "expected the Install click to submit the form with no 'confirm' "
            "field, landing on the server confirm page")
        assert fr.load_registry(server.state_dir)["schedule"] is None, (
            "the server confirm page must not have scheduled anything yet")

        page.locator(
            'form[action="%s"] button[type="submit"]' % update_page.INSTALL_ROUTE
        ).click()
        page.wait_for_load_state("networkidle")
        assert page.url == base_url + "/fleet?frame=live"
        registry = fr.load_registry(server.state_dir)
        assert registry["schedule"]["state"] == "scheduled"
        assert registry["schedule"]["version"] == _AVAILABLE_VERSION
        assert page.locator('form[action="%s"]' % update_page.CANCEL_ROUTE).count() == 1
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
        assert page.url == base_url + "/fleet?frame=live"
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
        page.goto(base_url + FLEET_ROUTE)

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
def test_more_sheet_fits_the_console_overflow_links_at_phone_widths(
        new_context, server, viewport, lang):
    """At 375px and 390px, in English and French: the Console tab bar's More
    sheet on the Releases page holds exactly the Account row and the switch back to
    the personal space (every Console page is in the bar), with a measured hit box
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
        page.goto(base_url + FLEET_ROUTE)
        if page.viewport_size["width"] != viewport["width"]:
            raise AssertionError("expected the measurement to be taken at %dpx" % (viewport["width"],))

        page.locator(".tab-bar__more > .tab-bar__link").click()
        page.locator(_MORE_SHEET_LINK_SELECTOR).first.wait_for(state="visible")

        links = page.locator(_MORE_SHEET_LINK_SELECTOR)
        count = links.count()
        assert count == 2, (
            "expected exactly 2 links (Account, the space switch) in "
            "the More sheet at %dpx/%s, got %d" % (viewport["width"], lang, count))

        heights = []
        for index in range(count):
            # :nth-of-type (1-based), not Playwright's ">> nth=" chaining
            # syntax -- _assert_hit_target()'s underlying _hit_area() runs
            # this selector through document.querySelector() directly.
            # The Account row and the space switch row are in the settings block.
            selector = ".tab-bar__links a.mobile-nav__link:nth-child(%d)" % (index + 1)
            seen = _assert_hit_target(
                page, selector,
                "More sheet link %d at %dpx/%s" % (index, viewport["width"], lang))
            heights.append(seen["hit"][1])

        # A page row is an icon then its name: the name is what must not wrap or truncate.
        overflow = page.evaluate(
            _OVERFLOW_PROBE,
            ".tab-bar__more-panel a.mobile-nav__link:not(.tab-bar__nav-link),"
            " .tab-bar__more-panel a.tab-bar__nav-link > span")
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

        header = page.locator("header.site-header")
        assert header.locator('a[href="%s"]' % layout.UPDATE_ROUTE).count() == 0
        assert header.locator(".nav-status").count() == 0
        assert page.locator(".dashboard-sidebar .nav-status").count() == 0
        # The Update page has no navigation entry: Fleet is the current cell.
        assert page.locator(
            '%s[href="%s"]' % (_MORE_SHEET_LINK_SELECTOR, layout.UPDATE_ROUTE)).count() == 0
        assert page.locator('nav.tab-bar a[href="/fleet"][aria-current="page"]').count() == 1

        print(
            "D-02 mobile-fit: %dpx/%s More-sheet link heights=%r (floor 44px)"
            % (viewport["width"], lang, heights))
    finally:
        context.close()


@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize(
    "viewport", [VIEWPORT_375, VIEWPORT_PHONE], ids=["375", "390"])
def test_version_rows_fit_at_phone_widths_with_no_overflow(
        new_context, make_app_server, viewport, lang):
    """At 375px and 390px, in English and French, with three releases and two realistic
    notes each: the table renders one row per release, nothing overflows the viewport
    horizontally, every row's action button is a full-size target inside the viewport, and
    the call-to-action Install button is fully inside the viewport and enabled.
    """
    server = make_app_server(seed=_seed_three_releases_with_realistic_notes)
    context = new_context(viewport=viewport)
    try:
        page = context.new_page()
        base_url = server.base_url()
        context.add_cookies([{
            "name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": base_url}])
        _login(page, base_url)
        page.goto(base_url + FLEET_ROUTE)
        where = "%dpx/%s" % (viewport["width"], lang)
        assert page.locator("details.update-all").count() == 0
        _reveal(page, "versions")

        rows = page.locator("tr.update-table__row")
        assert rows.count() == 3, "expected 3 release rows at %s, got %d" % (where, rows.count())
        assert _page_has_no_horizontal_overflow(page), "overflow at %s" % where
        for index in range(rows.count()):
            box = rows.nth(index).bounding_box()
            assert box["x"] >= -0.5 and box["x"] + box["width"] <= viewport["width"] + 0.5
            for button in rows.nth(index).locator("form button[type=submit]").all():
                button_box = button.bounding_box()
                assert button_box["height"] >= 44 - 0.5, (
                    "row %d action is %r tall at %s" % (index, button_box["height"], where))
                assert button_box["x"] + button_box["width"] <= viewport["width"] + 0.5

        install_button = page.locator(".update-cta form button[type=submit]")
        box = install_button.bounding_box()
        assert box is not None and install_button.is_enabled()
        assert box["x"] >= -0.5 and box["x"] + box["width"] <= viewport["width"] + 0.5
        _assert_hit_target(page, ".update-cta form button[type=submit]", where)
    finally:
        context.close()


@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize(
    "viewport", [VIEWPORT_375, VIEWPORT_DESKTOP], ids=["375", "1280"])
def test_running_row_and_its_notes_work_at_phone_and_desktop_widths(
        new_context, make_app_server, viewport, lang):
    """At 375x812 and 1280x900, in English and French, with a running release carrying about
    30 notes, an earlier bench install and a newer release: the Running badge is visible on
    the running row only, its notes sit behind one disclosure that is at least 44px tall and
    closed, opening it lists all 30 notes inside the viewport, nothing overflows
    horizontally and the card's Install button stays visible and enabled.
    """
    server = make_app_server(seed=_seed_running_bench_and_newer)
    context = new_context(viewport=viewport)
    try:
        page = context.new_page()
        base_url = server.base_url()
        context.add_cookies([{
            "name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": base_url}])
        _login(page, base_url)
        page.goto(base_url + FLEET_ROUTE)
        _reveal(page, "versions")
        where = "%dpx/%s" % (viewport["width"], lang)

        badge = page.locator(".update-row__badge:visible")
        assert badge.count() == 1, "expected one visible Running badge at %s" % where
        assert badge.inner_text().strip().lower() == ("running" if lang == "en" else "en cours")
        row = page.locator("tr.update-table__row--running")
        assert row.count() == 1 and row.locator(".mono").first.inner_text() == _RUNNING_VERSION

        notes = row.locator("details.update-table__notes")
        assert notes.evaluate("el => el.open") is False
        notes_list = notes.locator("ul")
        assert not notes_list.is_visible(), "notes list should start closed at %s" % where
        summary = notes.locator("summary")
        box = summary.bounding_box()
        assert box["height"] >= 44 - 0.5, "summary is %r tall at %s" % (box["height"], where)
        assert box["x"] >= -0.5 and box["x"] + box["width"] <= viewport["width"] + 0.5

        summary.click()
        page.wait_for_function("d => d.open", arg=notes.element_handle())
        assert notes_list.is_visible()
        assert notes_list.locator("li").count() == 30
        list_box = notes_list.bounding_box()
        assert list_box["x"] >= -0.5 and list_box["x"] + list_box["width"] <= viewport["width"] + 0.5
        assert row.locator("time").count() >= 1
        assert _page_has_no_horizontal_overflow(page), "overflow at %s" % where
        install_button = page.locator(".update-cta form button[type=submit]")
        install_box = install_button.bounding_box()
        assert install_box is not None and install_button.is_enabled()
        assert install_box["x"] + install_box["width"] <= viewport["width"] + 0.5

        summary.click()
        page.wait_for_function("d => !d.open", arg=notes.element_handle())
    finally:
        context.close()


@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize(
    "viewport", [VIEWPORT_DESKTOP, VIEWPORT_PHONE, VIEWPORT_MIN_SUPPORTED],
    ids=["1280", "390", "360"])
def test_card_and_eligible_releases_at_every_width(
        new_context, make_app_server, viewport, lang):
    """At 1280, 390 and 360px in English and French, with a bench build published beside
    real releases: the call-to-action card offers the newer release by name once, the bench
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
        page.goto(base_url + FLEET_ROUTE)
        _reveal(page, "device")
        where = "%dpx/%s" % (viewport["width"], lang)

        card = page.locator("section.update-cta")
        assert card.count() == 1 and card.is_visible()
        assert card.locator(".update-cta__title").inner_text() == (
            "Update available" if lang == "en" else "Mise à jour disponible")
        assert _AVAILABLE_VERSION in card.inner_text()
        assert card.locator("time").count() >= 1, "relative dates at %s" % where
        assert "bench" not in page.locator("main").inner_text().lower(), (
            "a bench build must not be shown to the owner at %s" % where)
        assert page.locator('input[name="version"][value="%s"]' % _BENCH_VERSION).count() == 0
        assert _page_has_no_horizontal_overflow(page), "overflow at %s" % where

        selector = ".update-cta form button[type=submit]"
        install = page.locator(selector)
        _assert_hit_target(page, selector, where)
        # A key press first: after the pointer opened the dialog, a script focus alone does
        # not match :focus-visible.
        page.keyboard.press("Tab")
        install.focus()
        outline = install.evaluate(
            "el => { const s = getComputedStyle(el);"
            " return [s.outlineStyle, parseFloat(s.outlineWidth)]; }")
        assert outline[0] != "none" and outline[1] >= 2, "no focus ring at %s: %r" % (where, outline)

        with page.expect_navigation():
            install.click()
        assert update_page.INSTALL_ROUTE in page.url
        cancel = page.locator('main a[href="%s"]' % FLEET_FRAME_HREF)
        with page.expect_navigation():
            cancel.click()
        assert page.url.endswith(FLEET_FRAME_HREF)
        assert page.locator('form[action="%s"]' % update_page.CANCEL_ROUTE).count() == 0, (
            "cancelling at the confirmation page must leave nothing scheduled at %s" % where)
    finally:
        context.close()


_WIDTHS = (360, 390, 700, 1024, 1280)


@pytest.fixture(scope="module")
def many_server(module_app_server_factory):
    return module_app_server_factory(seed=_seed_many_releases)


@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("width", _WIDTHS)
def test_twelve_releases_fit_at_every_width_with_unbroken_versions_and_full_targets(
        new_context, many_server, width, lang):
    """With twelve releases (one carrying an unbroken 90-character token in its note) at 360,
    390, 700, 1024 and 1280px in both languages: the whole history is one table, nothing
    overflows horizontally, no version ever wraps mid-token, every Install/rollback button
    measures at least 44px tall and sits inside the viewport, and an opened notes
    disclosure keeps its notes inside the viewport.
    """
    context = new_context(viewport={"width": width, "height": 900})
    try:
        page = context.new_page()
        base_url = many_server.base_url()
        context.add_cookies([{
            "name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": base_url}])
        _login(page, base_url)
        page.goto(base_url + FLEET_ROUTE)
        _reveal(page, "versions")
        where = "%dpx/%s" % (width, lang)

        rows = page.locator("tr.update-table__row")
        assert rows.count() == 12, "the full history must be listed at %s" % where
        assert page.locator(".update-versions__count").inner_text().strip() == "12"
        assert _page_has_no_horizontal_overflow(page), "overflow at %s" % where

        wrapped = page.evaluate(_WRAPPED_VERSION_PROBE)
        assert wrapped == [], "versions wrapped mid-token at %s: %r" % (where, wrapped)
        for button in page.locator(".update-table form button[type=submit]").all():
            button_box = button.bounding_box()
            assert button_box["height"] >= 44 - 0.5, "button %r at %s" % (button_box, where)
            assert button_box["x"] + button_box["width"] <= width + 0.5, (
                "action outside the viewport at %s: %r" % (where, button_box))

        for index in (0, 3, 11):
            details = rows.nth(index).locator("details.update-table__notes")
            if not details.count():
                continue
            page.wait_for_function("() => document.getAnimations().length === 0")
            details.locator("summary").click()
            page.wait_for_function("d => d.open", arg=details.element_handle())
            box = details.locator("ul").bounding_box()
            assert box["x"] >= -0.5 and box["x"] + box["width"] <= width + 0.5, (
                "opened notes outside the viewport at %s: %r" % (where, box))
        assert _page_has_no_horizontal_overflow(page), "overflow with notes open at %s" % where
    finally:
        context.close()


def test_older_release_rollback_button_is_quiet_and_only_newer_installs_use_the_accent(
        new_context, many_server):
    """In the browser, "Roll back to ..." renders on the quiet secondary button (the accent
    fill is not used for it), while the call-to-action Install and a newer release's own row
    button are the one accent-filled primary, in French wording."""
    context = new_context(viewport=VIEWPORT_DESKTOP)
    try:
        page = context.new_page()
        base_url = many_server.base_url()
        context.add_cookies([{
            "name": auth.UI_LANG_COOKIE_NAME, "value": "fr", "url": base_url}])
        _login(page, base_url)
        page.goto(base_url + FLEET_ROUTE)
        accent = page.evaluate(_ACCENT_PROBE)

        _reveal(page, "device")
        primary = page.locator(".update-cta form button[type=submit]")
        assert primary.inner_text() == "Installer %s" % _MANY_NEWEST
        assert _background(primary) == accent
        _dismiss(page)

        _reveal(page, "versions")
        older = page.locator("tr.update-table__row").nth(11)
        rollback = older.locator("form button[type=submit]")
        assert rollback.inner_text() == "Revenir"
        assert rollback.get_attribute("aria-label") == "Revenir à %s" % _MANY_OLDEST
        assert _background(rollback) != accent

        newer = page.locator("tr.update-table__row").nth(0)
        assert _background(newer.locator("form button[type=submit]")) == accent
        assert newer.locator("form button[type=submit]").inner_text() == "Installer"
    finally:
        context.close()


def test_rows_open_and_the_install_flow_works_with_scripts_blocked(
        new_context, make_app_server):
    """With scripts blocked every action is already in view, a notes disclosure still opens
    on a click (native <details>) and lists every note, and the rollback button reaches the
    server confirmation page, which is the real gate; nothing depends on script."""
    server = make_app_server(seed=_seed_many_releases)
    base_url = server.base_url()
    with _no_js_page(
            new_context, base_url, FLEET_ROUTE, viewport=VIEWPORT_PHONE,
            reduced_motion="reduce") as page:
        rows = page.locator("tr.update-table__row")
        assert rows.count() == 12
        oldest = rows.nth(11)
        notes = oldest.locator("details.update-table__notes")
        assert notes.evaluate("el => el.open") is False
        notes.locator("summary").click()
        assert notes.evaluate("el => el.open") is True
        assert oldest.locator(".update-table__notes li").first.is_visible()
        button = oldest.locator("form button[type=submit]")
        assert button.is_visible() and button.inner_text() == "Roll back"
        assert button.get_attribute("aria-label") == "Roll back to %s" % _MANY_OLDEST
        with page.expect_navigation():
            page.evaluate(
                _CLICK_FORM_SUBMIT_PROBE_IN, ".update-table tbody tr:last-child form")
        assert page.url == base_url + update_page.INSTALL_ROUTE
        assert _MANY_OLDEST in page.locator("main").inner_text()
        assert fr.load_registry(server.state_dir)["schedule"] is None, (
            "the server confirm page must not have scheduled anything yet")


@pytest.mark.parametrize("scenario", ["failed", "in_progress", "scheduled"])
@pytest.mark.parametrize("width", [360, 1280])
def test_in_flight_states_fit_and_offer_only_what_the_server_would_accept(
        new_context, make_app_server, scenario, width):
    """The failed, installing and scheduled cards fit at 360 and 1280px with no overflow; a
    failed install offers a retry, an installing frame shows no Install or Cancel button
    anywhere, and a scheduled one shows a quiet Cancel."""
    server = make_app_server(seed=lambda state_dir: _seed_many_releases(state_dir, scenario))
    context = new_context(viewport={"width": width, "height": 900})
    try:
        page = context.new_page()
        base_url = server.base_url()
        _login(page, base_url)
        page.goto(base_url + FLEET_ROUTE)
        _reveal(page, "device")
        where = "%s at %dpx" % (scenario, width)
        assert _page_has_no_horizontal_overflow(page), "overflow: " + where
        assert page.locator("section.update-cta").count() == 1
        installs = page.locator('form[action="%s"]' % update_page.INSTALL_ROUTE)
        cancels = page.locator('form[action="%s"]' % update_page.CANCEL_ROUTE)
        if scenario == "failed":
            assert page.locator(".update-cta--error").count() == 1
            assert page.locator(".update-cta form button[type=submit]").inner_text().startswith("Install")
            _assert_hit_target(page, ".update-cta form button[type=submit]", where)
        elif scenario == "in_progress":
            assert page.locator(".update-cta--warn").count() == 1
            assert installs.count() == 0 and cancels.count() == 0
        else:
            assert cancels.count() == 1
            _assert_hit_target(page, ".update-cta form button[type=submit]", where)
            assert cancels.locator("button").get_attribute("class") == update_page._QUIET_BUTTON_CLASS
    finally:
        context.close()


def test_desktop_sidebar_frame_tools_group_fits_with_no_overlap(new_context, server):
    """At 1280px, the Console sidebar has no Frame tools group (Health, Device and
    Releases are in the Fleet view) and its five links (Fleet, Users, Airline editor,
    Audit log, Account) stack with no overlap.
    """
    context = new_context(viewport=VIEWPORT_DESKTOP)
    try:
        page = context.new_page()
        _login(page, server.base_url())
        page.goto(server.base_url() + FLEET_ROUTE)
        assert page.locator(".nav-group--frame-tools").count() == 0
        links = page.locator(".sidebar-nav a.sidebar-link")
        count = links.count()
        assert count == 5, "expected exactly 5 Console sidebar links, got %d" % (count,)
        boxes = [links.nth(i).bounding_box() for i in range(count)]
        for index in range(count - 1):
            upper, lower = boxes[index], boxes[index + 1]
            assert upper["y"] + upper["height"] <= lower["y"] + 0.5, (
                "expected sidebar links to stack without overlap, "
                "got %r then %r" % (upper, lower))
    finally:
        context.close()


# ==========================================================================
# The hardware type chooser: present only with more than one relevant type.
# ==========================================================================

_OTHER_TYPE = fr.hardware.SIM_CLONE_KEY
_OTHER_AVAILABLE_VERSION = "fw-v1.2.0"
_SIM_ENV = {fr.hardware.SIM_ENV_VAR: "1"}
_CHOOSER = "form.update-type-chooser"


def _seed_two_types(state_dir):
    """The two-release legacy fixture plus a second hardware type with its
    own releases (one running, one available) and its own device."""
    _seed_two_releases(state_dir)
    registry = fr.load_registry(state_dir, _OTHER_TYPE)
    registry["releases"] = [
        {
            "version": version, "sha256": hashlib.sha256(("other" + version).encode()).hexdigest(),
            "size": 10, "released_at": _NOW, "published_at": _NOW, "commit": "b" * 40,
            "notes": ["other " + version], "bench": False, "installed_at": [],
        }
        for version in (_RUNNING_VERSION, _OTHER_AVAILABLE_VERSION)]
    fr._save_registry(state_dir, registry, _OTHER_TYPE)
    report = fr.load_device_report(state_dir)
    report["devices"]["dev2"] = {
        "fw_version": _RUNNING_VERSION, "reported_at": _NOW, "events": [],
        "hardware_type": _OTHER_TYPE}
    atomic_io.atomic_write(fr.device_report_path(state_dir), json.dumps(report))


@pytest.fixture
def two_type_server(make_app_server, monkeypatch):
    # The seeding runs in this process, where the second type is usable
    # only while the simulation gate is on.
    monkeypatch.setenv(fr.hardware.SIM_ENV_VAR, "1")
    return make_app_server(seed=_seed_two_types, env_overrides=_SIM_ENV)


def test_single_type_page_has_no_chooser(new_context, server):
    context = new_context(viewport=VIEWPORT_PHONE)
    try:
        page = context.new_page()
        _login(page, server.base_url())
        page.goto(server.base_url() + layout.UPDATE_ROUTE)
        assert page.locator(_CHOOSER).count() == 0
        assert page.locator('input[name="%s"]' % update_page.TYPE_FORM_FIELD).count() == 0
    finally:
        context.close()


def test_switching_type_shows_that_types_schedule_and_scheduling_is_independent(
        new_context, two_type_server):
    server = two_type_server
    context = new_context(viewport=VIEWPORT_PHONE)
    try:
        page = context.new_page()
        base_url = server.base_url()
        _login(page, base_url)
        page.goto(base_url + FLEET_ROUTE)
        other_label = fr.hardware.get_profile(_OTHER_TYPE, _SIM_ENV).label
        assert page.locator(_CHOOSER + " button").count() == 2
        assert page.locator(_CHOOSER + ' button[aria-pressed="true"]').count() == 1

        page.locator(_CHOOSER + " button", has_text=other_label).click()
        page.wait_for_load_state("networkidle")
        assert page.url == "%s%s?%s=%s" % (
            base_url, layout.UPDATE_ROUTE, update_page.TYPE_QUERY_PARAM, _OTHER_TYPE)
        assert page.locator(_CHOOSER + ' button[aria-pressed="true"]').inner_text() == other_label
        assert page.locator("section.update-cta").inner_text().count(_OTHER_AVAILABLE_VERSION) >= 1

        page.once("dialog", lambda dialog: dialog.accept())
        _install_submit(page).click()
        page.wait_for_load_state("networkidle")
        page.locator(
            'form[action="%s"] button[type="submit"]' % update_page.INSTALL_ROUTE).click()
        page.wait_for_load_state("networkidle")
        assert _OTHER_TYPE in page.url
        other = fr.load_registry(server.state_dir, _OTHER_TYPE)
        assert other["schedule"]["version"] == _OTHER_AVAILABLE_VERSION
        assert fr.load_registry(server.state_dir)["schedule"] is None
        assert page.locator('form[action="%s"]' % update_page.CANCEL_ROUTE).count() == 1

        page.locator(_CHOOSER + " button", has_text=fr.hardware.get_profile(
            fr.hardware.LEGACY_KEY).label).click()
        page.wait_for_load_state("networkidle")
        assert page.locator('form[action="%s"]' % update_page.CANCEL_ROUTE).count() == 0
        assert page.locator("section.update-cta").inner_text().count(_AVAILABLE_VERSION) >= 1
    finally:
        context.close()


def test_chooser_is_keyboard_operable(new_context, two_type_server):
    context = new_context(viewport=VIEWPORT_PHONE)
    try:
        page = context.new_page()
        base_url = two_type_server.base_url()
        _login(page, base_url)
        page.goto(base_url + FLEET_ROUTE)
        for _ in range(40):
            page.keyboard.press("Tab")
            if page.evaluate(
                    "sel => !!document.activeElement.closest(sel)", _CHOOSER):
                break
        else:
            raise AssertionError("Tab never reached the type chooser")
        page.keyboard.press("Tab")
        assert page.evaluate("sel => !!document.activeElement.closest(sel)", _CHOOSER)
        with page.expect_navigation():
            page.keyboard.press("Enter")
        assert "%s=%s" % (update_page.TYPE_QUERY_PARAM, _OTHER_TYPE) in page.url
    finally:
        context.close()


@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize(
    "viewport", [VIEWPORT_MIN_SUPPORTED, VIEWPORT_375, VIEWPORT_DESKTOP],
    ids=["360", "375", "1280"])
def test_chooser_fits_without_horizontal_overflow(
        new_context, two_type_server, viewport, lang):
    context = new_context(viewport=viewport)
    try:
        page = context.new_page()
        base_url = two_type_server.base_url()
        context.add_cookies([{
            "name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": base_url}])
        _login(page, base_url)
        page.goto(base_url + FLEET_ROUTE)
        _reveal(page, "device")
        assert page.locator(_CHOOSER).count() == 1
        sizes = page.evaluate(
            "() => ({doc: document.documentElement.scrollWidth,"
            " view: document.documentElement.clientWidth})")
        assert sizes["doc"] <= sizes["view"], sizes
        box = page.locator(_CHOOSER).bounding_box()
        assert box["x"] >= 0 and box["x"] + box["width"] <= viewport["width"] + 0.5, box
        for index in range(page.locator(_CHOOSER + " button").count()):
            button = page.locator(_CHOOSER + " button").nth(index)
            assert button.evaluate("el => el.scrollWidth <= el.clientWidth + 0.5")
        label = page.locator(_CHOOSER).get_attribute("aria-label")
        assert label == ("Hardware type" if lang == "en" else "Type de matériel")
    finally:
        context.close()
