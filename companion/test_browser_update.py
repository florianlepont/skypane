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
        image_bytes = ("fake-firmware-" + version).encode()
        with open(image_path, "wb") as fh:
            fh.write(image_bytes)
        fr.publish_release(str(state_dir), {
            "version": version, "sha256": hashlib.sha256(image_bytes).hexdigest(),
            "size": len(image_bytes), "released_at": published_at, "commit": "a" * 40,
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
def test_version_rows_fit_at_phone_widths_with_no_overflow(
        new_context, make_app_server, viewport, lang):
    """At 375px and 390px, in English and French, with three releases and two realistic
    notes each: the list renders one closed row per release, nothing overflows the viewport
    horizontally, every row's summary is a full-size target inside the viewport, and the
    call-to-action Install button is fully inside the viewport and enabled.
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
        where = "%dpx/%s" % (viewport["width"], lang)

        rows = page.locator("details.update-row")
        assert rows.count() == 3, "expected 3 release rows at %s, got %d" % (where, rows.count())
        assert page.locator("details.update-row[open]").count() == 0
        assert _page_has_no_horizontal_overflow(page), "overflow at %s" % where
        for index in range(rows.count()):
            box = rows.nth(index).locator("summary").bounding_box()
            assert box["height"] >= 44 - 0.5, "row %d is %r tall at %s" % (index, box["height"], where)
            assert box["x"] >= -0.5 and box["x"] + box["width"] <= viewport["width"] + 0.5

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
    the running row only, the row starts closed with its first note on one ellipsised line,
    its summary is at least 44px tall and inside the viewport, opening it lists all 30 notes
    and the absolute dates, nothing overflows horizontally and the card's Install button
    stays visible and enabled.
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

        badge = page.locator(".update-row__badge:visible")
        assert badge.count() == 1, "expected one visible Running badge at %s" % where
        assert badge.inner_text().strip().lower() == ("running" if lang == "en" else "en cours")
        assert badge.locator("xpath=ancestor::details").locator(".update-row__version .mono").inner_text() == (
            _RUNNING_VERSION)

        row = page.locator("details.update-row--running")
        assert row.evaluate("el => el.open") is False
        note = row.locator("summary .update-row__note")
        assert note.is_visible()
        assert note.evaluate("el => el.scrollWidth > el.clientWidth"), (
            "the first note should be cut to one ellipsised line at %s" % where)
        assert note.evaluate("el => getComputedStyle(el).textOverflow") == "ellipsis"
        notes_list = row.locator("ul.update-row__notes")
        assert not notes_list.is_visible(), "notes list should start closed at %s" % where
        summary = row.locator("summary")
        box = summary.bounding_box()
        assert box["height"] >= 44 - 0.5, "summary is %r tall at %s" % (box["height"], where)
        assert box["x"] >= -0.5 and box["x"] + box["width"] <= viewport["width"] + 0.5

        summary.click()
        assert row.evaluate("el => el.open") is True
        assert notes_list.is_visible()
        assert notes_list.locator("li").count() == 30
        assert not note.is_visible(), "the one-line note gives way to the full list"
        meta = row.locator(".update-row__meta time:not([data-relative])")
        assert meta.count() >= 1 and meta.first.is_visible()
        assert _page_has_no_horizontal_overflow(page), "overflow at %s" % where
        install_button = page.locator(".update-cta form button[type=submit]")
        install_box = install_button.bounding_box()
        assert install_box is not None and install_button.is_enabled()
        assert install_box["x"] + install_box["width"] <= viewport["width"] + 0.5

        summary.click()
        assert row.evaluate("el => el.open") is False
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
        page.goto(base_url + layout.UPDATE_ROUTE)
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


_WIDTHS = (360, 390, 700, 1024, 1280)


@pytest.fixture(scope="module")
def many_server(module_app_server_factory):
    return module_app_server_factory(seed=_seed_many_releases)


@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("width", _WIDTHS)
def test_twelve_releases_fit_at_every_width_with_unbroken_versions_and_full_targets(
        new_context, many_server, width, lang):
    """With twelve releases (one carrying an unbroken 90-character token in its note) at 360,
    390, 700, 1024 and 1280px in both languages: the whole history is listed, nothing
    overflows horizontally, no version ever wraps mid-token, every row summary and every
    Install/rollback button measures at least 44px tall, and an opened row keeps its notes,
    dates and action inside the viewport.
    """
    context = new_context(viewport={"width": width, "height": 900})
    try:
        page = context.new_page()
        base_url = many_server.base_url()
        context.add_cookies([{
            "name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": base_url}])
        _login(page, base_url)
        page.goto(base_url + layout.UPDATE_ROUTE)
        where = "%dpx/%s" % (width, lang)

        rows = page.locator("details.update-row")
        assert rows.count() == 12, "the full history must be listed at %s" % where
        assert page.locator(".update-versions__count").inner_text() == "12"
        assert _page_has_no_horizontal_overflow(page), "overflow at %s" % where

        wrapped = page.evaluate(_WRAPPED_VERSION_PROBE)
        assert wrapped == [], "versions wrapped mid-token at %s: %r" % (where, wrapped)
        heights = page.evaluate(
            "() => [...document.querySelectorAll('details.update-row > summary')]"
            ".map(s => Math.round(s.getBoundingClientRect().height))")
        assert min(heights) >= 44, "a row summary is %r tall at %s" % (min(heights), where)

        for details in (rows.nth(0), rows.nth(3), rows.nth(11)):
            details.locator("summary").click()
            body = details.locator(".update-row__body")
            assert body.is_visible()
            box = body.bounding_box()
            assert box["x"] >= -0.5 and box["x"] + box["width"] <= width + 0.5, (
                "opened row body outside the viewport at %s: %r" % (where, box))
            for button in details.locator("form button[type=submit]").all():
                button_box = button.bounding_box()
                assert button_box["height"] >= 44 - 0.5, "button %r at %s" % (button_box, where)
                assert button_box["x"] + button_box["width"] <= width + 0.5
        assert _page_has_no_horizontal_overflow(page), "overflow with rows open at %s" % where
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
        page.goto(base_url + layout.UPDATE_ROUTE)
        accent = page.evaluate(_ACCENT_PROBE)

        primary = page.locator(".update-cta form button[type=submit]")
        assert primary.inner_text() == "Installer %s" % _MANY_NEWEST
        assert _background(primary) == accent

        older = page.locator("details.update-row").nth(11)
        older.locator("summary").click()
        rollback = older.locator("form button[type=submit]")
        assert rollback.inner_text() == "Revenir à %s" % _MANY_OLDEST
        assert _background(rollback) != accent

        newer = page.locator("details.update-row").nth(0)
        newer.locator("summary").click()
        assert _background(newer.locator("form button[type=submit]")) == accent
        assert newer.locator("form button[type=submit]").inner_text() == "Installer"
    finally:
        context.close()


def test_rows_open_and_the_install_flow_works_with_scripts_blocked(
        new_context, make_app_server):
    """With scripts blocked a row still opens on a click (native <details>), shows every note
    and its action, and the rollback button reaches the server confirmation page, which is the
    real gate; nothing depends on script."""
    server = make_app_server(seed=_seed_many_releases)
    base_url = server.base_url()
    with _no_js_page(
            new_context, base_url, layout.UPDATE_ROUTE, viewport=VIEWPORT_PHONE,
            reduced_motion="reduce") as page:
        rows = page.locator("details.update-row")
        assert rows.count() == 12
        oldest = rows.nth(11)
        assert oldest.evaluate("el => el.open") is False
        oldest.locator("summary").click()
        assert oldest.evaluate("el => el.open") is True
        assert oldest.locator(".update-row__notes li").first.is_visible()
        button = oldest.locator("form button[type=submit]")
        assert button.is_visible() and button.inner_text() == "Roll back to %s" % _MANY_OLDEST
        with page.expect_navigation():
            page.evaluate(_CLICK_FORM_SUBMIT_PROBE_IN, ".update-rows > li:last-child form")
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
        page.goto(base_url + layout.UPDATE_ROUTE)
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
