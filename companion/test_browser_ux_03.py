#!/usr/bin/env python3
"""Part 03 of `companion/test_browser_ux.py` (33-23-PLAN.md, TST-11), the
third of the browser_ux chain's four migration plans (33-21..33-24).

Covers the original file's check() calls #38-#62: the expired-countdown
wording floor, Home's D1 swap rules (focus-holding region, [data-pending]
region, dirty-settings-form stand-down, hidden-tab zero-requests, the
frame picture's fade-only-on-change), the Display fallback save at 360px,
the D2 optimistic Frame-strip switch family (flips before the answer,
rolls back and announces on failure, survives a mid-flip refresh, saves
with scripts blocked), the Flights live-list family (new-detection
highlight, refresh-preserves-open-row, refresh-never-interrupts-the-
filter, a collapsed detail row's keyboard floor, the phone card's tap-
anywhere disclosure), the restored dirty bar's own dirty-count/save-every-
field/fallback-save family, the retired runway map's replacement
relationship check, Display's recorded page height, the theme/arrivals
scripts-blocked save floors, and the palette preview's keyboard/hover/
focus behaviour.

Every test below drives a real headless Chromium against a real
`companion/app.py` subprocess, through the guarded `page`/`new_context`
fixtures (`companion/conftest.py`), and never constructs or navigates to
any URL outside `server.base_url()` — a `127.0.0.1:<ephemeral-port>`
origin the guarded fixture itself created. A missing/unlaunchable
Chromium is a hard failure under CI / `SKYPANE_REQUIRE_BROWSER=1` (the
`browser` fixture override in `companion/conftest.py`), never a silent
skip.

Read-only checks (no test below saves a real setting through the bar or
the fallback Save) share one module-scoped, read-only `server` fixture
(33-MIGRATION-RULES.md section 2). Every check that DOES persist a
setting — the Display/fallback/theme/arrivals scripts-blocked saves, all
four switch checks, the bar's own save check, and the two Flights checks
that write a new runway_events row directly to the database — gets its
own function-scoped `make_app_server` server, so no xdist worker ever
sees another test's leftover on-disk state.

Request-count assertions (the D1/D-12 "zero requests" family) are
counted through `page.on("request", ...)` on the guarded context, never
inferred from the DOM: a page that fetched and then declined to swap is a
different and worse behaviour than a page that never fetched at all.
"""
import pytest

from companion import auth, i18n, layout
from companion.pages import config_page, history_page
from server import device_config, history_db
from companion.test_browser_ux_helpers import (
    VIEWPORT_DESKTOP, VIEWPORT_MIN_SUPPORTED,
    _login, _no_js_page, seed_state_dir,
)

pytestmark = pytest.mark.browser


@pytest.fixture(scope="module")
def server(module_app_server_factory):
    """The shared, read-only 22-AUDIT.md-methodology fixture every read-only
    check in this module measures against — module-scoped because none of
    them persists a real setting.
    """
    return module_app_server_factory(seed=seed_state_dir, fake_providers=True)


# ===========================================================================
# Shared helpers for this part's D1/D2/D7 swap-and-request-counting checks
# (23-06/23-07/23-08-PLAN.md). Local to this module: no later part of this
# chain calls any of them.
# ===========================================================================

REFRESH_SETTLE_MS = 1200
SWITCH_SEL = 'form[action="/quick/display"] button[role="switch"]'
FLIGHT_ID_ATTR = layout.REFRESH_ROW_ID_ATTR
NEW_ROW_CLASS = layout.REFRESH_NEW_ROW_CLASS


def _force_refresh(page):
    """Drive freshness.js's own visibilitychange catch-up path by
    shifting Date.now forward for the duration of one dispatch — the
    shipped listener's own elapsed comparison and guards run unmodified.
    """
    page.evaluate(
        "() => {"
        "  var real = Date.now;"
        "  Date.now = function () { return real() + 600000; };"
        "  try {"
        "    document.dispatchEvent(new Event('visibilitychange'));"
        "  } finally {"
        "    Date.now = real;"
        "  }"
        "}")


def _count_document_requests(page, url):
    """A live counter of fetches of `url` made by the page itself.
    Returns a zero-argument reader."""
    seen = []
    page.on("request", lambda request: (
        seen.append(request.url)
        if request.url.split("?")[0] == url else None))
    return lambda: len(seen)


def _mark(page, selector, name):
    """Tag a live node with a JS expando — the only handle that proves
    NODE IDENTITY across a swap."""
    page.eval_on_selector(
        selector, "el => { el.__skypaneProbe = %r; }" % name)


def _marked(page, selector, name):
    return page.eval_on_selector(
        selector, "el => el.__skypaneProbe === %r" % name)


def _dirty_the_region(page, selector):
    """Make a live region DIFFER from its freshly-fetched counterpart, so
    the "this region did not change" skip cannot be what leaves it
    alone."""
    page.eval_on_selector(
        selector, "el => el.setAttribute('data-probe-dirty', '1')")


def _hold_fetch(page):
    """Wrap window.fetch so the next POST hangs until _release_fetch() is
    called. POSTs ONLY: freshness.js's own refresh loop is a GET through
    the same window.fetch, and holding it too would stop the very
    refresh some of these checks need to land."""
    page.evaluate(
        "() => {"
        "  var realFetch = window.fetch;"
        "  window.__skypaneHeld = null;"
        "  window.fetch = function (url, opts) {"
        "    if (!opts || opts.method !== 'POST') {"
        "      return realFetch(url, opts);"
        "    }"
        "    return new Promise(function (resolve, reject) {"
        "      window.__skypaneHeld = function () {"
        "        realFetch(url, opts).then(resolve, reject);"
        "      };"
        "    });"
        "  };"
        "}")


def _fetch_was_issued(page):
    return page.evaluate("() => !!window.__skypaneHeld")


def _release_fetch(page):
    page.evaluate("() => { window.__skypaneHeld(); }")


def _switch_state(page, selector=None):
    return page.eval_on_selector(
        selector or SWITCH_SEL, "el => el.getAttribute('aria-checked')")


def _record_a_new_detection(state_dir, callsign, hex_value, ts):
    """One more runway_events row, written through the same module
    server/poll_loop.py writes them with — never a hand-built INSERT, so
    the row this check calls "a new detection" is the shape a real
    detection has."""
    with history_db.open_db(state_dir) as conn:
        history_db.record_runway_event(
            conn, ts=ts, hex=hex_value, callsign=callsign,
            aircraft_type="A320", confirmed_state="confirmed",
            corroborated=True, route_source="adsb",
            airline="Air France", origin="LFPO", destination="LFPG",
            tracked_runway=device_config.RUNWAY_IDS[0])


def _row_ids(page):
    return page.evaluate(
        "(attr) => [...document.querySelectorAll('tr[data-flight-row][' + attr"
        " + ']')].map(el => el.getAttribute(attr))", FLIGHT_ID_ATTR)


def _highlighted(page):
    return page.evaluate(
        "(cls) => [...document.querySelectorAll('.' + cls)].length",
        NEW_ROW_CLASS)


# ===========================================================================
# 23-05-PLAN.md Task 3 (D14/CFG-34): the expired-countdown wording floor.
# ===========================================================================

def test_an_expired_countdown_reads_waiting_and_never_a_warning(new_context, server):
    """a countdown whose instant has already passed reads the server's own translated
    waiting wording in BOTH languages, never an age, gains the breathing class and no
    warn/error/alert class at all, and that class resolves to the one animation the
    stylesheet defines (D14/CFG-34, 23-05-PLAN.md Task 3)"""
    tick_settle_ms = 2200
    freshness_age = ".page-header__freshness time[data-relative]"
    base_url = server.base_url()
    for lang in ("en", "fr"):
        context = new_context()
        try:
            context.add_cookies([{
                "name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": base_url}])
            page = context.new_page()
            _login(page, base_url)
            page.goto(base_url + "/health")
            page.locator(freshness_age).first.wait_for(state="attached")
            page.evaluate(
                "() => {"
                "  var el = document.createElement('time');"
                "  el.setAttribute('id', 'seeded-countdown');"
                "  el.setAttribute('data-relative', '');"
                "  el.setAttribute('data-relative-countdown', '');"
                "  el.setAttribute('datetime',"
                "    new Date(Date.now() - 120000).toISOString());"
                "  el.textContent = 'seeded';"
                "  document.querySelector('main').appendChild(el);"
                "}")
            page.wait_for_timeout(tick_settle_ms)
            seen = page.eval_on_selector(
                "#seeded-countdown",
                "el => [el.textContent, el.getAttribute('class') || '']")
            text, klass = seen[0], seen[1]
            expected = page.eval_on_selector(
                "body", "el => el.getAttribute('data-relative-waiting')")
            if not expected:
                raise AssertionError(
                    "lang=%s: the page renders no waiting wording on <body> for "
                    "the script to read" % lang)
            if text != expected:
                raise AssertionError(
                    "lang=%s: expected a countdown whose instant has passed to "
                    "read the server's own waiting wording %r, got %r — it must "
                    "not turn itself into an age"
                    % (lang, expected, text))
            if " ago" in text or "il y a" in text:
                raise AssertionError(
                    "lang=%s: an expired countdown became an age: %r" % (lang, text))
            if "is-breathing" not in klass.split():
                raise AssertionError(
                    "lang=%s: expected an expired countdown to breathe, got "
                    "class=%r" % (lang, klass))
            for verdict in ("warn", "error", "alert", "danger", "late"):
                if verdict in klass:
                    raise AssertionError(
                        "lang=%s: an expired countdown carries NO warn class — "
                        "a wake that has not happened yet is not a fault (the "
                        "false alarm X2 removed), got class=%r" % (lang, klass))
            animation = page.eval_on_selector(
                "#seeded-countdown", "el => getComputedStyle(el).animationName")
            if animation != "skypane-pulse":
                raise AssertionError(
                    "lang=%s: expected the breathing class to resolve to the "
                    "stylesheet's one animation, got %r" % (lang, animation))
        finally:
            context.close()


# ===========================================================================
# 23-06-PLAN.md Task 3 (D1/CFG-35): the three skips, and the number D-12
# was written to protect.
# ===========================================================================

def test_a_swap_leaves_the_region_holding_focus_alone(new_context, server):
    """a Home refresh swaps the regions that changed while leaving the one holding
    keyboard focus untouched — asserted on NODE IDENTITY through a JS expando, not on
    a selector match, because a replaced node matching the same selector is exactly
    the defect — against a control proving another region really was swapped in the
    same cycle (D1/CFG-35, 23-06-PLAN.md Task 3)"""
    context = new_context(viewport=VIEWPORT_DESKTOP)
    try:
        page = context.new_page()
        base_url = server.base_url()
        _login(page, base_url)
        page.goto(base_url + "/")
        page.wait_for_load_state("networkidle")
        region = ".frame-strip"
        focus_target = ".frame-strip button[type=\"submit\"]"
        page.eval_on_selector(focus_target, "el => el.focus()")
        _mark(page, region, "focused-region")
        _mark(page, focus_target, "focused")
        _dirty_the_region(page, region)
        _mark(page, ".page-header__freshness", "elsewhere")
        with page.expect_response(lambda r: r.url.split("?")[0] == base_url + "/"):
            _force_refresh(page)
        page.wait_for_timeout(REFRESH_SETTLE_MS)
        if _marked(page, ".page-header__freshness", "elsewhere"):
            raise AssertionError(
                "control: no region was swapped at all, so the focus assertion "
                "below would prove nothing — the freshness line's own node "
                "survived a refresh it should not have")
        if not _marked(page, region, "focused-region"):
            raise AssertionError(
                "the region holding keyboard focus was REPLACED — a refresh that "
                "silently moves focus to the top of the document while someone "
                "is tabbing through a card is A-20's own harm, smaller (D1)")
        active = page.evaluate(
            "() => document.activeElement.__skypaneProbe === 'focused'")
        if not active:
            raise AssertionError(
                "focus left the element the user was in: document.activeElement "
                "is no longer that node")
        page.evaluate("() => document.activeElement.blur()")
        _mark(page, region, "unfocused-region")
        _dirty_the_region(page, region)
        with page.expect_response(lambda r: r.url.split("?")[0] == base_url + "/"):
            _force_refresh(page)
        page.wait_for_timeout(REFRESH_SETTLE_MS)
        if _marked(page, region, "unfocused-region"):
            raise AssertionError(
                "control: the same changed region survived with NOTHING focused "
                "inside it, so the assertion above was not measuring the focus "
                "rule at all")
    finally:
        context.close()


def test_a_swap_leaves_a_pending_region_alone(new_context, server):
    """a region containing a [data-pending] element survives a refresh untouched, by
    node identity, while another region on the same page is swapped in the same
    cycle — the reconciliation rule plan 23-07 sets its marker for, proven before it
    has a marker to set (T-23-21, 23-06-PLAN.md Task 3)"""
    context = new_context(viewport=VIEWPORT_DESKTOP)
    try:
        page = context.new_page()
        base_url = server.base_url()
        _login(page, base_url)
        page.goto(base_url + "/")
        page.wait_for_load_state("networkidle")
        region = ".home-status-grid"
        page.eval_on_selector(
            region,
            "el => { var probe = document.createElement('span');"
            "  probe.setAttribute('data-pending', '');"
            "  el.appendChild(probe); el.__skypaneProbe = 'pending'; }")
        _mark(page, ".page-header__freshness", "elsewhere")
        with page.expect_response(lambda r: r.url.split("?")[0] == base_url + "/"):
            _force_refresh(page)
        page.wait_for_timeout(REFRESH_SETTLE_MS)
        if _marked(page, ".page-header__freshness", "elsewhere"):
            raise AssertionError(
                "control: no region was swapped at all, so the pending assertion "
                "below would prove nothing")
        if not _marked(page, region, "pending"):
            raise AssertionError(
                "a region holding an element marked data-pending was replaced — "
                "that repaints an optimistic control with the server's older "
                "answer and makes it bounce back under the user's finger "
                "(T-23-21, the D1-races-D2 rule plan 23-07 depends on)")
        still_there = page.eval_on_selector_all(
            region + " [data-pending]", "els => els.length")
        if still_there != 1:
            raise AssertionError(
                "expected the pending marker itself to survive the cycle, found "
                "%d" % (still_there,))
        page.eval_on_selector(
            region,
            "el => { el.querySelector('[data-pending]').removeAttribute("
            "  'data-pending');"
            "  el.__skypaneProbe = 'unmarked'; }")
        with page.expect_response(lambda r: r.url.split("?")[0] == base_url + "/"):
            _force_refresh(page)
        page.wait_for_timeout(REFRESH_SETTLE_MS)
        if _marked(page, region, "unmarked"):
            raise AssertionError(
                "control: the same changed region survived with the marker "
                "REMOVED, so the assertion above was not measuring the pending "
                "rule at all")
    finally:
        context.close()


def test_a_dirty_settings_form_stands_the_whole_cycle_down(new_context, server):
    """a Display page with a typed-but-uncommitted edit issues ZERO requests when the
    same trigger that fetched on the clean page fires — counted as REQUESTS, not
    inferred from the DOM, because a page that fetched and then declined to swap is a
    different and worse behaviour — against a control proving the clean page does
    fetch (T-23-20/T-23-21, 23-06-PLAN.md Task 3; retargeted from the retired save
    bar's own gate by 27-04-PLAN.md Task 4, CFG-63)"""
    context = new_context(viewport=VIEWPORT_DESKTOP)
    try:
        page = context.new_page()
        base_url = server.base_url()
        _login(page, base_url)
        page.goto(base_url + "/display")
        page.wait_for_load_state("networkidle")
        count = _count_document_requests(page, base_url + "/display")
        _force_refresh(page)
        page.wait_for_timeout(REFRESH_SETTLE_MS)
        clean_requests = count()
        if clean_requests < 1:
            raise AssertionError(
                "control: a clean Display page issued no request at all (%d), so "
                "the dirty-form assertion below would measure nothing"
                % (clean_requests,))
        quiet_sel = 'input[name="quiet_hours_start"]'
        page.eval_on_selector(quiet_sel, "el => el.focus()")
        page.keyboard.press("ControlOrMeta+A")
        page.keyboard.type("03:33")
        uncommitted = page.evaluate(
            "() => !!(window.SkyPaneDirtyState "
            "&& window.SkyPaneDirtyState.hasUncommittedEdits())")
        if not uncommitted:
            raise AssertionError(
                "expected the typed-but-uncommitted edit to report unsaved edits "
                "— this check gates on that same predicate, so a page that never "
                "reports one would make it vacuous")
        before = count()
        _force_refresh(page)
        page.wait_for_timeout(REFRESH_SETTLE_MS)
        during_edit = count() - before
        if during_edit != 0:
            raise AssertionError(
                "expected ZERO requests while the settings form has unsaved "
                "edits, counted %d — a page mid-edit should not be fetching and "
                "diffing itself at all, and a swap landing on a half-edited form "
                "is B1 with a new cause" % (during_edit,))
    finally:
        context.close()


def test_a_hidden_tab_issues_zero_requests_on_all_three_pages(new_context, server):
    """a tab reporting itself hidden issues ZERO requests on ALL THREE pages that now
    run the loop — counted as requests, each against a control proving the same page
    and the same trigger DO fetch while visible — which is the number D-12 was
    written to protect and the reason three pages polling is acceptable at all
    (T-23-20, 23-06-PLAN.md Task 3)"""
    base_url = server.base_url()
    for route in ("/", "/display", "/health"):
        context = new_context(viewport=VIEWPORT_DESKTOP)
        try:
            page = context.new_page()
            _login(page, base_url)
            page.goto(base_url + route)
            page.wait_for_load_state("networkidle")
            count = _count_document_requests(page, base_url + route)
            _force_refresh(page)
            page.wait_for_timeout(REFRESH_SETTLE_MS)
            if count() < 1:
                raise AssertionError(
                    "control: %s issued no request when visible (%d), so the "
                    "hidden-tab assertion below would measure nothing — this "
                    "page is not running the loop at all"
                    % (route, count()))
            page.evaluate(
                "() => {"
                "  Object.defineProperty(document, 'hidden',"
                "    {configurable: true, get: () => true});"
                "  Object.defineProperty(document, 'visibilityState',"
                "    {configurable: true, get: () => 'hidden'});"
                "}")
            before = count()
            _force_refresh(page)
            page.wait_for_timeout(REFRESH_SETTLE_MS)
            hidden_requests = count() - before
            if hidden_requests != 0:
                raise AssertionError(
                    "%s issued %d request(s) while reporting itself hidden — "
                    "zero from a backgrounded tab is the number D-12 was written "
                    "to protect, and three pages polling instead of one is only "
                    "acceptable because of it (T-23-20)"
                    % (route, hidden_requests))
        finally:
            context.close()


def test_the_picture_fades_only_when_the_picture_changed(new_context, server):
    """the frame picture fades in when a NEW render arrives and does NOT animate when
    the same picture is swapped back in — both phases in one check, against a control
    proving a swap happened at all, with the class proven to resolve to the
    stylesheet's own fade-in block (D1+D3, 23-06-PLAN.md Task 3)"""
    context = new_context(viewport=VIEWPORT_DESKTOP)
    try:
        page = context.new_page()
        base_url = server.base_url()
        _login(page, base_url)
        page.goto(base_url + "/")
        page.wait_for_load_state("networkidle")
        image = ".preview-frame__image"
        _mark(page, ".page-header__freshness", "elsewhere")
        with page.expect_response(lambda r: r.url.split("?")[0] == base_url + "/"):
            _force_refresh(page)
        page.wait_for_timeout(REFRESH_SETTLE_MS)
        if _marked(page, ".page-header__freshness", "elsewhere"):
            raise AssertionError(
                "control: nothing was swapped, so 'it did not fade' below would "
                "prove nothing")
        klass = page.eval_on_selector(image, "el => el.getAttribute('class') || ''")
        if "is-fading-in" in klass.split():
            raise AssertionError(
                "the picture faded in on a cycle that brought back the SAME "
                "picture (class=%r) — a flash every 45 seconds for no "
                "information is worse than no fade at all" % (klass,))
        page.eval_on_selector(
            image, "el => { el.setAttribute('src', el.getAttribute('src')"
                   " + '?stale=1'); }")
        with page.expect_response(lambda r: r.url.split("?")[0] == base_url + "/"):
            _force_refresh(page)
        page.wait_for_timeout(REFRESH_SETTLE_MS)
        klass = page.eval_on_selector(image, "el => el.getAttribute('class') || ''")
        if "is-fading-in" not in klass.split():
            raise AssertionError(
                "a NEW picture arrived and did not fade in (class=%r) — the fade "
                "is the only thing that says a render happened" % (klass,))
        animation = page.eval_on_selector(
            image, "el => getComputedStyle(el).animationName")
        if animation != "skypane-fade-in":
            raise AssertionError(
                "expected the fade class to resolve to the stylesheet's own "
                "fade-in block, got %r" % (animation,))
    finally:
        context.close()


def test_display_still_saves_with_scripts_blocked_at_360px(new_context, make_app_server):
    """with scripts blocked at 360px, in BOTH languages, a Display setting still
    saves through the fallback Save and persists to disk, with the freshness line
    this plan added rendering beside it — the one assertion here that would catch the
    Phase 22 P0 recurring (B1/CFG-38, 23-06-PLAN.md Task 3)"""
    server = make_app_server(seed=seed_state_dir, fake_providers=True)
    base_url = server.base_url()
    for lang in ("en", "fr"):
        with _no_js_page(new_context, base_url, "/display",
                         viewport=VIEWPORT_MIN_SUPPORTED) as page:
            page.context.add_cookies([{
                "name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": base_url}])
            page.goto(base_url + "/display")
            if page.viewport_size["width"] != VIEWPORT_MIN_SUPPORTED["width"]:
                raise AssertionError("expected the measurement at the 360px contract floor")
            current = device_config.load_device_config(server.tmpdir)["theme"]
            other = next(t for t in device_config.THEME_IDS if t != current)
            page.eval_on_selector(
                'input[name="theme"][value="%s"]' % other, "el => el.checked = true")
            save = page.query_selector("[%s]" % config_page.STATIC_SAVE_FALLBACK_ATTR)
            if save is None:
                raise AssertionError(
                    "lang=%s: the fallback Save is the ONLY way to save this page "
                    "with scripts blocked, and it is not rendered" % (lang,))
            # The relocated Save button's entrance animation
            # (skypane-bar-arrive) is unconditional on script, so a
            # coordinate click during it fails Playwright's own
            # stability check against a button still translating into
            # place.
            page.wait_for_timeout(600)
            with page.expect_navigation():
                save.click()
            saved = device_config.load_device_config(server.tmpdir)["theme"]
            if saved != other:
                raise AssertionError(
                    "lang=%s: a Display save did not persist with scripts blocked "
                    "at 360px — expected theme %r, got %r. This is the P0 Phase "
                    "22 existed to fix" % (lang, other, saved))
            if page.locator(".page-header__freshness").count() != 1:
                raise AssertionError(
                    "lang=%s: expected exactly one freshness line on a "
                    "scripts-blocked Display page" % (lang,))


# ===========================================================================
# 23-07-PLAN.md Task 3 (D2/CFG-36): the optimistic Frame-strip switch,
# proven in a real browser.
# ===========================================================================

def test_a_switch_flips_before_the_server_answers(new_context, make_app_server):
    """a switch flips its aria-checked BEFORE the server answers — proven against a
    held request that has genuinely been issued and genuinely has no answer, with the
    stored value still unchanged at that instant — marks exactly one region pending
    while in flight, and on a 204 keeps the flip and clears the marker (D2/CFG-36,
    23-07-PLAN.md Task 3)"""
    server = make_app_server(seed=seed_state_dir, fake_providers=True)
    context = new_context(viewport=VIEWPORT_DESKTOP)
    try:
        page = context.new_page()
        base_url = server.base_url()
        _login(page, base_url)
        page.goto(base_url + "/")
        page.wait_for_load_state("networkidle")
        before = _switch_state(page)
        if before not in ("true", "false"):
            raise AssertionError(
                "expected a server-rendered aria-checked on the Screen switch, "
                "got %r" % (before,))
        on_disk_before = device_config.load_device_config(server.tmpdir)["display_enabled"]
        _hold_fetch(page)
        page.click(SWITCH_SEL)
        if not _fetch_was_issued(page):
            raise AssertionError(
                "control: no fetch was issued at all, so the assertion below "
                "would prove nothing about ORDER")
        during = _switch_state(page)
        if during == before:
            raise AssertionError(
                "aria-checked was still %r while the request had no answer — the "
                "flip is not optimistic, it is waiting for the server, which is "
                "the whole of what D2 asks for (23-07-PLAN.md Task 3)" % (during,))
        if device_config.load_device_config(
                server.tmpdir)["display_enabled"] is not on_disk_before:
            raise AssertionError(
                "the stored value changed before the held request was released — "
                "the hold is not holding and this check is measuring nothing")
        pending = page.eval_on_selector_all(
            ".frame-strip [data-pending]", "els => els.length")
        if pending != 1:
            raise AssertionError(
                "expected exactly one pending-marked region while the request is "
                "in flight, found %d — this is the marker 23-06's swap skips and "
                "the only thing this plan owes that contract" % (pending,))
        _release_fetch(page)
        page.wait_for_timeout(600)
        if _switch_state(page) != during:
            raise AssertionError(
                "a CONFIRMED flip must stay where it was put, got %r"
                % _switch_state(page))
        if page.eval_on_selector_all(
                ".frame-strip [data-pending]", "els => els.length") != 0:
            raise AssertionError(
                "the pending marker survived a successful answer — a region whose "
                "control is settled must go back to being refreshable")
        if device_config.load_device_config(
                server.tmpdir)["display_enabled"] is on_disk_before:
            raise AssertionError("expected the confirmed flip to have persisted to disk")
    finally:
        context.close()


def test_a_switch_rolls_back_and_announces_on_both_failure_branches(new_context, make_app_server):
    """a switch rolls its aria-checked back, clears its pending marker, leaves the
    stored value alone and announces the TRANSLATED generic failure in a visible
    toast — on a 500 AND on a network-level failure, in English and in French, each
    against a control phase proving the same switch DOES flip and does NOT announce
    on a working request (D2/CFG-36, T-23-26/T-23-27, 23-07-PLAN.md Task 3)"""
    server = make_app_server(seed=seed_state_dir, fake_providers=True)
    base_url = server.base_url()
    for lang, failure_copy in (
            ("en", layout.QUICK_SWITCH_FAILED_TEXT),
            ("fr", i18n.t_lang(layout.QUICK_SWITCH_FAILED_TEXT, "fr"))):
        context = new_context(viewport=VIEWPORT_DESKTOP)
        try:
            page = context.new_page()
            _login(page, base_url)
            context.add_cookies([{
                "name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": base_url}])
            page.goto(base_url + "/")
            page.wait_for_load_state("networkidle")
            start = _switch_state(page)
            page.click(SWITCH_SEL)
            page.wait_for_timeout(600)
            landed = _switch_state(page)
            if landed == start:
                raise AssertionError(
                    "lang=%s control: the switch did not move on a WORKING "
                    "request, so the rollback assertions below would pass on a "
                    "control that simply never flips" % (lang,))
            toast_sel = "[%s]" % layout.QUICK_TOAST_ATTR
            if page.eval_on_selector(toast_sel, "el => el.textContent") != "":
                raise AssertionError(
                    "lang=%s control: the toast announced something on a "
                    "SUCCESSFUL flip — it is a failure announcement only"
                    % (lang,))
            for branch, handler in (
                    ("a 500 from the server",
                     lambda route: route.fulfill(status=500, body="")),
                    ("a network-level failure",
                     lambda route: route.abort())):
                page.goto(base_url + "/")
                page.wait_for_load_state("networkidle")
                page.route("**/quick/display", handler)
                try:
                    known = _switch_state(page)
                    stored = device_config.load_device_config(
                        server.tmpdir)["display_enabled"]
                    page.click(SWITCH_SEL)
                    page.wait_for_timeout(800)
                    if _switch_state(page) != known:
                        raise AssertionError(
                            "lang=%s, %s: aria-checked stayed at %r instead of "
                            "rolling back to %r — an optimistic switch that keeps "
                            "a state the server never accepted is a switch that "
                            "lies (T-23-26)"
                            % (lang, branch, _switch_state(page), known))
                    if page.eval_on_selector_all(
                            ".frame-strip [data-pending]", "els => els.length") != 0:
                        raise AssertionError(
                            "lang=%s, %s: the pending marker was left behind — a "
                            "region whose control never confirmed would hold "
                            "itself stale forever" % (lang, branch))
                    if device_config.load_device_config(
                            server.tmpdir)["display_enabled"] is not stored:
                        raise AssertionError(
                            "lang=%s, %s: the stored value moved on a failed "
                            "request" % (lang, branch))
                    announced = page.eval_on_selector(toast_sel, "el => el.textContent")
                    if announced != failure_copy:
                        raise AssertionError(
                            "lang=%s, %s: expected the translated failure copy "
                            "%r in the toast, got %r"
                            % (lang, branch, failure_copy, announced))
                    for internal in ("500", "http", "/quick/", "TypeError"):
                        if internal in announced:
                            raise AssertionError(
                                "lang=%s, %s: the toast carries %r — a user-facing "
                                "failure names no status code, no URL and no "
                                "server internal" % (lang, branch, internal))
                    visible = page.eval_on_selector(
                        toast_sel, "el => getComputedStyle(el).opacity")
                    if visible == "0":
                        raise AssertionError(
                            "lang=%s, %s: the toast carries the right words but "
                            "is not visible — a live region nobody can see is "
                            "half an announcement" % (lang, branch))
                finally:
                    page.unroute("**/quick/display")
        finally:
            context.close()


def test_a_refresh_landing_mid_flip_does_not_repaint_the_switch(new_context, make_app_server):
    """a Home refresh landing while a flip is unconfirmed leaves the Frame strip
    untouched — by NODE IDENTITY and by the optimistic aria-checked surviving —
    against one control proving another region really was swapped in the same cycle
    and a second proving the same changed strip IS replaced once the marker has
    cleared, with focus deliberately moved off the strip so the focus skip cannot be
    what satisfies it (D1+D2, T-23-26, 23-07-PLAN.md Task 3)"""
    server = make_app_server(seed=seed_state_dir, fake_providers=True)
    context = new_context(viewport=VIEWPORT_DESKTOP)
    try:
        page = context.new_page()
        base_url = server.base_url()
        _login(page, base_url)
        page.goto(base_url + "/")
        page.wait_for_load_state("networkidle")
        before = _switch_state(page)
        _hold_fetch(page)
        page.click(SWITCH_SEL)
        if not _fetch_was_issued(page):
            raise AssertionError("control: no fetch was issued, so nothing is in flight")
        optimistic = _switch_state(page)
        if optimistic == before:
            raise AssertionError("control: the switch did not flip, so nothing is pending")
        page.evaluate("() => document.activeElement.blur()")
        _mark(page, ".frame-strip", "strip")
        _mark(page, ".page-header__freshness", "elsewhere")
        with page.expect_response(lambda r: r.url.split("?")[0] == base_url + "/"):
            _force_refresh(page)
        page.wait_for_timeout(REFRESH_SETTLE_MS)
        if _marked(page, ".page-header__freshness", "elsewhere"):
            raise AssertionError(
                "control: no region was swapped at all, so the assertions below "
                "would prove nothing")
        if not _marked(page, ".frame-strip", "strip"):
            raise AssertionError(
                "the strip was REPLACED while a flip was unconfirmed — the "
                "fetched document still carries the server's older state, so the "
                "switch would bounce back under the user's finger (T-23-26, the "
                "D1-races-D2 rule)")
        if _switch_state(page) != optimistic:
            raise AssertionError(
                "the optimistic state was repainted by a refresh: expected %r, "
                "got %r" % (optimistic, _switch_state(page)))
        _release_fetch(page)
        page.wait_for_timeout(600)
        if page.eval_on_selector_all(
                ".frame-strip [data-pending]", "els => els.length") != 0:
            raise AssertionError("expected the marker to clear once the answer arrived")
        _mark(page, ".frame-strip", "settled-strip")
        _dirty_the_region(page, ".frame-strip")
        with page.expect_response(lambda r: r.url.split("?")[0] == base_url + "/"):
            _force_refresh(page)
        page.wait_for_timeout(REFRESH_SETTLE_MS)
        if _marked(page, ".frame-strip", "settled-strip"):
            raise AssertionError(
                "control: the same changed strip survived with NO marker on it, "
                "so the assertion above was not measuring the pending rule at all")
    finally:
        context.close()


def test_all_three_switches_still_post_with_scripts_blocked_at_360px(new_context, make_app_server):
    """with scripts blocked at 360px, in BOTH languages, all THREE switches render
    with the server's own aria-checked, clear the 44px touch floor in both axes,
    submit their real form and PERSIST to disk — the assertion that would catch a
    control that renders and silently does nothing (D2/CFG-36, CFG-38, 23-07-PLAN.md
    Task 3)"""
    server = make_app_server(seed=seed_state_dir, fake_providers=True)
    base_url = server.base_url()
    switches = (
        ("/", "display_enabled", 'form[action="/quick/display"] button[role="switch"]'),
        ("/", "quiet_hours_enabled",
         'form[action="/quick/quiet-hours"] button[role="switch"]'),
        ("/device", "led_enabled",
         'button[role="switch"][form="%s"]' % config_page.QUICK_LED_FORM_ID),
    )
    for lang in ("en", "fr"):
        for route, field, selector in switches:
            with _no_js_page(new_context, base_url, route,
                             viewport=VIEWPORT_MIN_SUPPORTED) as page:
                page.context.add_cookies([{
                    "name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": base_url}])
                page.goto(base_url + route)
                if page.viewport_size["width"] != VIEWPORT_MIN_SUPPORTED["width"]:
                    raise AssertionError("expected the 360px contract floor")
                control = page.query_selector(selector)
                if control is None:
                    raise AssertionError(
                        "lang=%s, %s: the %s switch does not render at all with "
                        "scripts blocked" % (lang, route, field))
                stored = device_config.load_device_config(server.tmpdir)[field]
                rendered = control.get_attribute("aria-checked")
                if rendered != ("true" if stored is True else "false"):
                    raise AssertionError(
                        "lang=%s, %s: the scripts-blocked page claims "
                        "aria-checked=%r for a stored %r — role=switch is a "
                        "description of what the button does, not a promise the "
                        "script keeps" % (lang, field, rendered, stored))
                page.eval_on_selector(
                    selector, "el => el.scrollIntoView({block: 'center'})")
                box = control.bounding_box()
                if box["width"] < 44 or box["height"] < 44:
                    raise AssertionError(
                        "lang=%s, %s: the switch measures %sx%s at 360px, under "
                        "the 44px touch floor"
                        % (lang, field, box["width"], box["height"]))
                with page.expect_navigation():
                    control.click()
                after = device_config.load_device_config(server.tmpdir)[field]
                if after is stored:
                    raise AssertionError(
                        "lang=%s, %s: the switch did NOT persist with scripts "
                        "blocked — it rendered and did nothing, which is the "
                        "exact defect Phase 22 found on the login page (CFG-38)"
                        % (lang, field))
                if page.locator("[%s]" % layout.QUICK_TOAST_ATTR).count() != 1:
                    raise AssertionError(
                        "lang=%s, %s: expected the toast region to still render "
                        "(inert) with scripts blocked" % (lang, field))
                if page.eval_on_selector(
                        "[%s]" % layout.QUICK_TOAST_ATTR, "el => el.textContent") != "":
                    raise AssertionError(
                        "lang=%s, %s: the toast announced something on a page "
                        "with no script at all" % (lang, field))


# ===========================================================================
# 23-08-PLAN.md Task 3 (D7/CFG-37 + D3's two Flights clauses): the live
# list, proven live.
# ===========================================================================

def test_a_new_detection_is_highlighted_and_an_existing_row_is_not(new_context, make_app_server):
    """a detection recorded while the Flights page is open arrives at the top of the
    live list on the next refresh and is the ONLY thing highlighted — in both the
    table and the phone card list — while a row that was already there is not,
    nothing at all is highlighted on first load, and a refresh that brings nothing
    new announces nothing; the class resolves to the stylesheet's own single-run
    arrival animation on --motion-slow (D7/CFG-37, 23-08-PLAN.md Task 3)"""
    server = make_app_server(seed=seed_state_dir, fake_providers=True)
    context = new_context(viewport=VIEWPORT_DESKTOP)
    try:
        page = context.new_page()
        base_url = server.base_url()
        _login(page, base_url)
        page.goto(base_url + "/flights")
        page.wait_for_load_state("networkidle")

        before_ids = _row_ids(page)
        if len(before_ids) < 2:
            raise AssertionError(
                "expected the seeded fixture to render several rows, got %d — "
                "with fewer this check measures nothing" % len(before_ids))
        if len(set(before_ids)) != len(before_ids):
            raise AssertionError(
                "expected every rendered row identity to be distinct, got %r"
                % (before_ids,))
        if _highlighted(page):
            raise AssertionError(
                "a freshly LOADED page already highlights %d element(s) — the "
                "highlight means 'this arrived while you were watching', and on "
                "first paint nothing did" % _highlighted(page))

        _force_refresh(page)
        page.wait_for_timeout(REFRESH_SETTLE_MS)
        if _highlighted(page):
            raise AssertionError(
                "a refresh that brought nothing new highlighted %d element(s) — "
                "a list that announces itself every cycle has told the reader "
                "nothing, and is how they learn to ignore it"
                % _highlighted(page))

        _record_a_new_detection(
            server.tmpdir, "NEWDET", "39ffff", "2026-08-01T23:30:00+00:00")
        _force_refresh(page)
        page.wait_for_timeout(REFRESH_SETTLE_MS)

        after_ids = _row_ids(page)
        want_after = min(len(before_ids) + 1, history_page.FLIGHTS_PAGE_SIZE)
        if len(after_ids) != want_after:
            raise AssertionError(
                "expected the swap to bring the new detection into the live "
                "list: %d rows before, %d after, wanted %d (min(before+1, "
                "FLIGHTS_PAGE_SIZE=%d)) — with no new row this check "
                "would be asserting a highlight on nothing"
                % (len(before_ids), len(after_ids), want_after,
                   history_page.FLIGHTS_PAGE_SIZE))
        arrived = [rid for rid in after_ids if rid not in before_ids]
        if len(arrived) != 1:
            raise AssertionError(
                "expected exactly one identity to be new after the swap, got %r"
                % (arrived,))
        if after_ids[0] != arrived[0]:
            raise AssertionError(
                "expected the new detection at the TOP of the list, got %r at "
                "the top and %r as the new identity" % (after_ids[0], arrived[0]))

        marked = page.evaluate(
            "([attr, cls]) => [...document.querySelectorAll("
            "'tr[data-flight-row].' + cls)].map(el => el.getAttribute(attr))",
            [FLIGHT_ID_ATTR, NEW_ROW_CLASS])
        if marked != arrived:
            raise AssertionError(
                "expected exactly the arrived row %r to carry the highlight, "
                "got %r — a highlight on a row that was already there is a "
                "claim that it just landed, which is false" % (arrived, marked))
        card_marked = page.evaluate(
            "([attr, cls]) => [...document.querySelectorAll("
            "'li.history-card.' + cls)].map(el => el.getAttribute(attr))",
            [FLIGHT_ID_ATTR, NEW_ROW_CLASS])
        if card_marked != arrived:
            raise AssertionError(
                "expected the phone card for the same event to be marked too, "
                "got %r" % (card_marked,))
        animation = page.eval_on_selector(
            "tr[data-flight-row]." + NEW_ROW_CLASS,
            "el => [getComputedStyle(el).animationName,"
            " getComputedStyle(el).animationIterationCount,"
            " getComputedStyle(el).animationDuration]")
        if animation[0] != "skypane-row-arrive":
            raise AssertionError(
                "expected the highlight class to resolve to the stylesheet's own "
                "arrival block, got %r" % (animation[0],))
        if animation[1] != "1":
            raise AssertionError(
                "expected the highlight to run exactly once, got %r iterations"
                % (animation[1],))
        if animation[2] != "2s":
            raise AssertionError(
                "expected the highlight to spend --motion-slow (2s), got %r — a "
                "180ms flash on a row nobody was looking at is no signal at all"
                % (animation[2],))
    finally:
        context.close()


def test_a_refresh_neither_unfolds_the_table_nor_closes_what_you_opened(new_context, make_app_server):
    """a refresh neither unfolds the Flights table nor closes the row you opened:
    with focus deliberately blurred off the toggle (so the loop's focus skip cannot
    be what passes this) and a new detection renumbering every row below it, exactly
    the row that was opened is still open — by EVENT identity, not by position — and
    exactly one toggle still announces it (D7/CFG-37, 23-08-PLAN.md Task 3)"""
    server = make_app_server(seed=seed_state_dir, fake_providers=True)
    context = new_context(viewport=VIEWPORT_DESKTOP)
    try:
        page = context.new_page()
        base_url = server.base_url()
        _login(page, base_url)
        page.goto(base_url + "/flights")
        page.wait_for_load_state("networkidle")

        toggle = page.locator("[data-row-toggle]").first
        toggle.wait_for(state="visible")
        opened_id = page.eval_on_selector(
            "#" + toggle.get_attribute("aria-controls"),
            "(el, attr) => el.getAttribute(attr)", FLIGHT_ID_ATTR)
        if not opened_id:
            raise AssertionError("expected the detail row to carry its event identity")
        toggle.click()
        page.evaluate("() => document.activeElement.blur()")

        _record_a_new_detection(
            server.tmpdir, "OPENSRV", "39fffe", "2026-08-02T00:15:00+00:00")
        _force_refresh(page)
        page.wait_for_timeout(REFRESH_SETTLE_MS)

        seen = page.evaluate(
            "([idAttr, openId]) => {"
            "  const details = [...document.querySelectorAll("
            "    'tr.flight-detail-row')];"
            "  const open = details.filter(el =>"
            "    el.className.indexOf('flight-detail-row--collapsed') === -1);"
            "  return {total: details.length,"
            "          open: open.map(el => el.getAttribute(idAttr)),"
            "          expanded: [...document.querySelectorAll("
            "            '[data-row-toggle][aria-expanded=\\\"true\\\"]')].length,"
            "          stillThere: !!document.querySelector("
            "            'tr.flight-detail-row[' + idAttr + '=\\\"' + openId"
            "            + '\\\"]')};"
            "}", [FLIGHT_ID_ATTR, opened_id])
        if seen["total"] < 2:
            raise AssertionError(
                "expected the swapped list to still render its detail rows, got "
                "%d — with fewer this check measures nothing" % seen["total"])
        if not seen["stillThere"]:
            raise AssertionError(
                "the row that was opened is no longer in the list at all, so "
                "nothing below is a statement about it")
        if seen["open"] != [opened_id]:
            raise AssertionError(
                "after a refresh %d of %d detail rows are open (%r), expected "
                "exactly the one that was opened (%r). Every row open is the "
                "server's own markup arriving un-collapsed; the WRONG row open "
                "is a record keyed to a position that just renumbered"
                % (len(seen["open"]), seen["total"], seen["open"], opened_id))
        if seen["expanded"] != 1:
            raise AssertionError(
                "expected exactly one toggle to report aria-expanded=true after "
                "the refresh, got %d — the class and the announced state are "
                "written in one place precisely so they cannot drift"
                % seen["expanded"])
    finally:
        context.close()
