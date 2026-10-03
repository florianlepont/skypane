#!/usr/bin/env python3
"""Browser checks for the expired-countdown wording floor, Home's swap rules
(focus-holding region, [data-pending] region, dirty-settings-form stand-down, hidden-tab
zero-requests, the frame picture's fade-only-on-change), the Display fallback save at 360px,
the optimistic Frame-strip switch family (flips before the answer, rolls back and announces
on failure, survives a mid-flip refresh, saves with scripts blocked), the Flights live-list
family (new-detection highlight, refresh-preserves-open-row, refresh-never-interrupts-the-
filter, a collapsed detail row's keyboard floor, the phone card's tap-anywhere disclosure),
the restored dirty bar's own dirty-count/save-every-field/fallback-save family, Display's
recorded page height, the theme/arrivals scripts-blocked save floors, and the palette
preview's keyboard/hover/focus behaviour.

Read-only checks share one module-scoped, read-only `server` fixture. Every check that
persists a setting gets its own function-scoped `make_app_server` server, so no xdist worker
sees another test's leftover on-disk state.

Request-count assertions are counted through `page.on("request", ...)` on the guarded
context, never inferred from the DOM: a page that fetched and then declined to swap is a
different and worse behaviour than a page that never fetched at all.
"""
from datetime import datetime, timedelta, timezone

import pytest

from companion import auth, layout
from companion.pages import config_page, history_page
from server import device_config, history_db, state_store
from server.plane import calendar_rules
from companion.test_browser_ux_helpers import (
    VIEWPORT_DESKTOP, VIEWPORT_MIN_SUPPORTED, VIEWPORT_PHONE,
    _assert_hit_target, _assert_no_page_overflow, _click_control,
    _display_page_height, _in_both_themes, _login, _no_js_page,
    _persist_without_js, _save_via_bar, _wait_for_bar, seed_state_dir,
)

pytestmark = pytest.mark.browser


@pytest.fixture(scope="module")
def server(module_app_server_factory):
    """The shared, read-only seeded fixture every read-only check in this module measures
    against — module-scoped because none of them persists a real setting.
    """
    return module_app_server_factory(seed=seed_state_dir, fake_providers=True)


# Shared helpers for this module's swap-and-request-counting checks. Local to this module: no
# other file calls any of them.

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


def _release_fetch(page):
    page.evaluate("() => { window.__skypaneHeld(); }")


def _record_a_new_detection(state_dir, callsign, hex_value, ts):
    """One more runway_events row, written through the same module
    server/poll_cycle.py writes them with — never a hand-built INSERT, so
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


def test_a_dirty_settings_form_stands_the_whole_cycle_down(new_context, server):
    """A Display page with a typed-but-uncommitted edit issues zero requests when the same
    trigger that fetched on the clean page fires — counted as requests, not inferred from the
    DOM, since a page that fetched and then declined to swap is a different and worse
    behaviour — against a control proving the clean page does fetch.
    """
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


def test_display_still_saves_with_scripts_blocked_at_360px(new_context, make_app_server):
    """With scripts blocked at 360px, in both languages, a Display setting still saves
    through the fallback Save and persists to disk, with the freshness line rendering
    beside it.
    """
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
            # The Save button's entrance animation is unconditional on script, so a coordinate
            # click during it fails Playwright's own stability check against a button still
            # translating into place.
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


def test_a_new_detection_is_highlighted_and_an_existing_row_is_not(new_context, make_app_server):
    """A detection recorded while the Flights page is open arrives at the top of the live
    list on the next refresh and is the only thing highlighted — in both the table and the
    phone card list — while a row that was already there is not, nothing at all is
    highlighted on first load, and a refresh that brings nothing new announces nothing; the
    class resolves to the stylesheet's own single-run arrival animation on --motion-slow.
    """
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


def test_a_refresh_keeps_every_picture_action_working(new_context, make_app_server):
    """A refresh keeps the Flights picture action on every row: after a new detection lands
    and the loop swaps the list in, every desktop row and phone card still carries exactly one
    picture link, the new flight at the top has its own, and a link in the swapped markup
    still opens the shared lightbox (the click handler is delegated, so it survives the swap).
    """
    server = make_app_server(seed=seed_state_dir, fake_providers=True)
    context = new_context(viewport=VIEWPORT_DESKTOP)
    try:
        page = context.new_page()
        base_url = server.base_url()
        _login(page, base_url)
        page.goto(base_url + "/flights")
        page.wait_for_load_state("networkidle")
        before = page.locator("tr[data-flight-row]").count()

        _record_a_new_detection(
            server.tmpdir, "OPENSRV", "39fffe", "2026-08-02T00:15:00+00:00")
        _force_refresh(page)
        page.wait_for_timeout(REFRESH_SETTLE_MS)

        seen = page.evaluate(
            "() => ({rows: document.querySelectorAll('tr[data-flight-row]').length,"
            "        cards: document.querySelectorAll('li.history-card').length,"
            "        rowLinks: document.querySelectorAll("
            "          'tr[data-flight-row] a[data-view-panel-src]').length,"
            "        cardLinks: document.querySelectorAll("
            "          'li.history-card a[data-view-panel-src]').length,"
            "        topName: document.querySelector("
            "          'tr[data-flight-row] a[data-view-panel-src]').getAttribute('aria-label')})")
        if seen["rows"] != before:
            raise AssertionError(
                "expected the swapped list to keep its page size (%d rows before, %d after)"
                % (before, seen["rows"]))
        if seen["rowLinks"] != seen["rows"] or seen["cardLinks"] != seen["cards"]:
            raise AssertionError(
                "expected one picture link per row and per card after the swap, got %r" % (seen,))
        if seen["topName"] != "View picture of OPENSRV":
            raise AssertionError(
                "expected the newest flight to head the list with its own picture link, got %r"
                % (seen["topName"],))
        page.locator("tr[data-flight-row] a[data-view-panel-src]").first.click()
        if not page.locator("#panel-lookup-dialog").evaluate("el => el.open"):
            raise AssertionError("expected a swapped-in picture link to open the lightbox")
    finally:
        context.close()


def test_a_refresh_never_interrupts_or_undoes_the_filter(new_context, server):
    """A refresh never interrupts the filter and never undoes it: with the caret in the box
    the loop issues zero requests (counted, against a control proving the same trigger does
    fetch with focus moved off), and the swap that then happens leaves the typed query
    applied — same visible rows, same live count, same input value.
    """
    context = new_context(viewport=VIEWPORT_DESKTOP)
    try:
        page = context.new_page()
        base_url = server.base_url()
        _login(page, base_url)
        page.goto(base_url + "/flights")
        page.wait_for_load_state("networkidle")
        requests = _count_document_requests(page, base_url + "/flights")

        query = page.eval_on_selector(
            "tr[data-flight-row]", "el => el.getAttribute('data-filter-text')")
        if not query:
            raise AssertionError(
                "expected the first rendered row to carry a non-empty "
                "data-filter-text to filter by — with none, this check has "
                "nothing to type")
        page.click("[data-filter-input]")
        page.type("[data-filter-input]", query)
        visible = page.evaluate(
            "() => [...document.querySelectorAll('tr[data-flight-row]')]"
            ".filter(el => !el.hidden).length")
        if visible != 1:
            raise AssertionError(
                "expected the query to narrow the table to one row before "
                "anything else is measured, got %d" % visible)
        count_text = page.eval_on_selector("[data-filter-count]", "el => el.textContent")

        before = requests()
        _force_refresh(page)
        page.wait_for_timeout(REFRESH_SETTLE_MS)
        if requests() != before:
            raise AssertionError(
                "the loop fetched while the caret was in the filter box — "
                "userIsInteracting() exists so a half-typed query is never "
                "swapped out from under the person typing it (%d request(s))"
                % (requests() - before))

        page.evaluate("() => document.activeElement.blur()")
        before = requests()
        _force_refresh(page)
        page.wait_for_timeout(REFRESH_SETTLE_MS)
        if requests() == before:
            raise AssertionError(
                "control: the same trigger issued no request with focus off the "
                "input either — this page's loop is not running, so phase 1 "
                "proved nothing")

        visible = page.evaluate(
            "() => [...document.querySelectorAll('tr[data-flight-row]')]"
            ".filter(el => !el.hidden).length")
        if visible != 1:
            raise AssertionError(
                "a refresh handed back %d visible rows under a query that "
                "matches one — the server renders the list unfiltered, so a swap "
                "that is not followed by a re-filter silently undoes what the "
                "reader asked for" % visible)
        if page.eval_on_selector(
                "[data-filter-count]", "el => el.textContent") != count_text:
            raise AssertionError(
                "the live count reverted to the server's own unfiltered sentence "
                "after a refresh, expected it to still read %r" % (count_text,))
        if page.eval_on_selector("[data-filter-input]", "el => el.value") != query:
            raise AssertionError("the typed query itself did not survive the refresh")
    finally:
        context.close()


def test_the_dirty_count_arrives_and_moves_only_when_the_word_does(new_context, server):
    """[data-dirty-count] arrives rather than appearing, and stays silent for anything that
    is not a genuine change: clicking an already-checked radio writes nothing (measured live
    to fire no native change at all, never reaching updateBar()); a real change writes the
    section's own name exactly once, read off the bar's own data-* attributes never
    hardcoded in English, and carries the changed-value class; and changing to a second,
    different theme inside the identical data-dirty-section wrapper, a real change that
    resolves to the textually identical label, writes nothing further, which is
    setCountText()'s own changed-text gate genuinely exercised.
    """
    context = new_context()
    try:
        page = context.new_page()
        base_url = server.base_url()
        _login(page, base_url)
        page.goto(base_url + "/display")
        current_theme = page.eval_on_selector(
            'input[name="theme"]:checked', "el => el.value")
        theme_target, theme_target2 = [
            t for t in device_config.THEME_IDS if t != current_theme][:2]

        page.evaluate(
            "() => {"
            " window.__countWords = [];"
            " var el = document.querySelector('[data-dirty-count]');"
            " new MutationObserver(function () {"
            "   window.__countWords.push(el.textContent);"
            " }).observe(el, {childList: true, characterData: true,"
            "                 subtree: true});"
            "}")

        _click_control(page, 'input[name="theme"][value="%s"]' % current_theme)
        page.wait_for_timeout(150)
        after_noop = page.evaluate("() => window.__countWords.slice()")
        if after_noop:
            raise AssertionError(
                "re-clicking the ALREADY-selected theme wrote to "
                "[data-dirty-count]: %r — a click that changed no value must not "
                "announce one" % (after_noop,))

        expected_label = page.evaluate(
            "() => {"
            " var field = document.querySelector('input[name=\"theme\"]');"
            " var wrapper = field.closest('[data-dirty-section]');"
            " var bar = document.querySelector('[data-dirty-bar]');"
            " return wrapper.getAttribute('data-dirty-section')"
            "   + bar.getAttribute('data-dirty-changed-suffix');"
            "}")
        _click_control(page, 'input[name="theme"][value="%s"]' % theme_target)
        _wait_for_bar(page)
        words = page.evaluate("() => window.__countWords.slice()")
        if len(words) != 1:
            raise AssertionError(
                "expected exactly ONE text mutation to [data-dirty-count] for a "
                "real change, got %r" % (words,))
        if words[0] != expected_label:
            raise AssertionError(
                "expected [data-dirty-count] to read %r after the real change, "
                "got %r" % (expected_label, words[0]))
        if "is-fading-in" not in (
                page.locator("[data-dirty-count]").get_attribute("class") or ""):
            raise AssertionError(
                "expected [data-dirty-count] to carry the changed-value class "
                "after a real change")

        _click_control(page, 'input[name="theme"][value="%s"]' % theme_target2)
        page.wait_for_timeout(150)
        after_second = page.evaluate("() => window.__countWords.slice()")
        if after_second != words:
            raise AssertionError(
                "changing to a DIFFERENT theme inside the same section wrote a "
                "new mutation to [data-dirty-count]: %r became %r — the two "
                "renders are textually IDENTICAL, so a write here is "
                "setCountText()'s own changed-text gate failing to suppress a "
                "no-op text assignment" % (words, after_second))
    finally:
        context.close()


def test_the_bars_save_persists_every_field_never_only_the_touched_one(new_context, make_app_server):
    """The bar's own Save persists every field to disk, never only the touched one: reading
    the full on-disk config before and after a single-field (tracked_runway) save, in both
    languages, and asserting the two dicts differ in exactly the one key touched — a
    stronger surface than reading the request body, since a server that posts the whole
    form but only writes the touched key would still pass a request-body check and fail
    this one.
    """
    server = make_app_server(seed=seed_state_dir, fake_providers=True)
    base_url = server.base_url()
    for lang in ("en", "fr"):
        context = new_context()
        try:
            page = context.new_page()
            _login(page, base_url)
            context.add_cookies([{
                "name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": base_url}])
            before = device_config.load_device_config(server.tmpdir)
            target = next(
                r for r in device_config.RUNWAY_IDS
                if str(r) != str(before["tracked_runway"]))

            page.goto(base_url + "/display")
            _click_control(page, 'input[name="tracked_runway"][value="%s"]' % target)
            _wait_for_bar(page)
            _save_via_bar(page)

            after = device_config.load_device_config(server.tmpdir)
            if str(after["tracked_runway"]) != str(target):
                raise AssertionError(
                    "lang=%s: the save did not persist — expected "
                    "tracked_runway %r, got %r"
                    % (lang, target, after["tracked_runway"]))
            changed_keys = [k for k in before if before[k] != after.get(k)]
            if changed_keys != ["tracked_runway"]:
                raise AssertionError(
                    "lang=%s: saving ONE field (tracked_runway) changed %r on "
                    "disk — a save that clobbers an untouched field is CFG-36's "
                    "own hazard; before=%r after=%r"
                    % (lang, changed_keys, before, after))
        finally:
            context.close()


def test_with_no_script_the_fallback_save_is_the_only_way(new_context, make_app_server):
    """With scripts blocked at 360px, in both languages, the fallback Save is visible with a
    real box and still saves to disk.
    """
    server = make_app_server(seed=seed_state_dir, fake_providers=True)
    base_url = server.base_url()
    for lang in ("en", "fr"):
        with _no_js_page(new_context, base_url, "/display",
                         viewport=VIEWPORT_MIN_SUPPORTED) as page:
            page.context.add_cookies([{
                "name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": base_url}])
            # The Save button's entrance animation runs regardless of scripts, so reduced
            # motion is requested here to avoid clicking a button still translating into place.
            page.emulate_media(reduced_motion="reduce")
            page.goto(base_url + "/display")
            if page.viewport_size["width"] != VIEWPORT_MIN_SUPPORTED["width"]:
                raise AssertionError("expected the measurement at the 360px contract floor")
            fallback = page.locator("[%s]" % config_page.STATIC_SAVE_FALLBACK_ATTR)
            if fallback.count() != 1:
                raise AssertionError(
                    "lang=%s: expected exactly one fallback Save, got %d — with "
                    "no script it is the ONLY way to save this page"
                    % (lang, fallback.count()))
            if not fallback.is_visible():
                raise AssertionError(
                    "lang=%s: the fallback Save is rendered but not visible — "
                    "which is precisely the shape B1 took, and a check that only "
                    "asked whether it EXISTS would have passed through it"
                    % (lang,))
            box = fallback.bounding_box()
            if not box or box["width"] <= 0 or box["height"] <= 0:
                raise AssertionError(
                    "lang=%s: the fallback Save has no box at 360px (%r)"
                    % (lang, box))
            current = device_config.load_device_config(server.tmpdir)["theme"]
            target = next(t for t in device_config.THEME_IDS if t != current)
            page.eval_on_selector(
                'input[name="theme"][value="%s"]' % target, "el => el.checked = true")
            fallback.wait_for(state="visible")
            with page.expect_navigation():
                fallback.click()
            saved = device_config.load_device_config(server.tmpdir)["theme"]
            if saved != target:
                raise AssertionError(
                    "lang=%s: a Display save did not persist through the "
                    "fallback Save with scripts blocked at 360px — expected "
                    "theme %r, got %r. This is the P0 Phase 22 existed to fix"
                    % (lang, target, saved))


def test_the_map_is_gone_the_radios_and_photographs_remain_and_meet_their_floor(new_context, server):
    """The schematic runway map is gone, the radios and the photographs are not — asserted
    as one relationship rather than three separate facts: zero .runway-map elements resolve
    on /display, exactly RUNWAY_IDS' own count of tracked_runway radios and of
    .runway-card__image photographs still resolve, the runway row does not scroll the page
    sideways at 360px, and every runway card clears the 44px hit-target floor in its own
    container at 360px in both themes, measured now that the map strip no longer provides
    the box.
    """
    base_url = server.base_url()
    ids = device_config.RUNWAY_IDS
    context = new_context(viewport=VIEWPORT_MIN_SUPPORTED)
    try:
        page = context.new_page()
        _login(page, base_url)
        page.goto(base_url + "/display")

        maps = page.locator(".runway-card .runway-map").count()
        if maps != 0:
            raise AssertionError(
                "expected ZERO .runway-map elements on /display after CFG-66's "
                "removal, found %d — the drawing is supposed to be gone" % (maps,))
        radios = page.locator('input[name="tracked_runway"]').count()
        if radios != len(ids):
            raise AssertionError(
                "expected %d tracked_runway radios, found %d — the map coming "
                "out must not take the control it was wrapped around with it"
                % (len(ids), radios))
        photos = page.locator(".runway-card .runway-card__image").count()
        if photos != len(ids):
            raise AssertionError(
                "expected %d runway photographs (.runway-card__image), found %d "
                "— the developer objected to the drawn map, not to the "
                "pictures, and this relationship must also fail if they vanish"
                % (len(ids), photos))

        message = _assert_no_page_overflow(
            page, "the runway row on /display", VIEWPORT_MIN_SUPPORTED["width"])
        if message:
            raise AssertionError(message)

        themes_measured = []
        for state in _in_both_themes(page):
            for index in range(len(ids)):
                selector = ".runway-row > .runway-card:nth-child(%d)" % (index + 1)
                _assert_hit_target(
                    page, selector,
                    "the runway card %d of %d on /display in the %s theme, "
                    "now that its map is gone"
                    % (index + 1, len(ids), state["theme"]))
            themes_measured.append(state["theme"])
        if len(themes_measured) != 2:
            raise AssertionError(
                "expected a hit-target measurement in each of two themes, got "
                "%d (%r)" % (len(themes_measured), themes_measured))
    finally:
        context.close()


THEME_PREVIEW_SEL = '[data-look-usage="departures"] img.look-frame__image'


def test_displays_page_height_is_recorded_at_both_phone_widths(new_context, server):
    """Display's full rendered document height is recorded at 390px and at 360px by one
    instrument, proved to be pointed at the authenticated Display page (its Aspect heading
    and a full THEME_IDS-sized departures radiogroup, never merely "a page rendered"), at
    the width the caller asked for, and taller than the viewport. Asserts no target, because
    the number is the verdict, and no cross-width relationship either, because the obvious
    one (narrower cannot be shorter) was measured false on this page.
    """
    base_url = server.base_url()
    heights = {}
    for viewport in (VIEWPORT_PHONE, VIEWPORT_MIN_SUPPORTED):
        seen = _display_page_height(new_context, base_url, viewport)
        heights[viewport["width"]] = seen["height"]
        print(
            "        [25-06 T1] Display document height at %dpx: "
            "%d px (client %dx%d, %d theme radios)"
            % (viewport["width"], seen["height"],
               seen["clientWidth"], seen["clientHeight"], seen["themeRadios"]))
    # No target is asserted here, deliberately, and no cross-width relationship either: the
    # obvious one (narrower cannot be shorter) was measured false on this page (a stack of
    # independently-rounding cards).
    if not heights:
        raise AssertionError("no viewport was measured at all")


def test_the_theme_still_saves_with_scripts_blocked(new_context, make_app_server):
    """The theme still saves with scripts blocked, at 360px and in both shipped languages:
    operated natively by field name, submitted through the real form, re-read from disk
    after a fresh GET and restored the same way.
    """
    server = make_app_server(seed=seed_state_dir, fake_providers=True)
    base_url = server.base_url()

    def read_back():
        return device_config.load_device_config(server.tmpdir)["theme"]

    before = read_back()
    target = next(t for t in device_config.THEME_IDS if t != before)
    seen = {}
    for lang in ("en", "fr"):
        seen[lang] = _persist_without_js(
            new_context, base_url, "/display", "theme", target, read_back,
            viewport=VIEWPORT_MIN_SUPPORTED,
            cookies=[{"name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": base_url}])
    after = read_back()
    if str(after) != str(before):
        raise AssertionError(
            "the scripts-blocked save left the theme at %r, it started at %r — "
            "a harness that changes a real setting edits its neighbours' "
            "subject" % (after, before))
    for lang, result in seen.items():
        if str(result["stored"]) != str(target):
            raise AssertionError(
                "lang=%s: the theme did not reach disk, it reads %r"
                % (lang, result["stored"]))
        if str(result["restored"]) != str(before):
            raise AssertionError(
                "lang=%s: the restore leg did not put %r back, disk reads %r"
                % (lang, before, result["restored"]))

    n_themes = len(device_config.THEME_IDS)
    with _no_js_page(new_context, base_url, "/display",
                     viewport=VIEWPORT_MIN_SUPPORTED) as page:
        for field, usage, state, expected in (
                ("theme", "departures", "open", n_themes),
                ("calendar_theme_id", "calendar", "closed", n_themes + 1)):
            count = page.eval_on_selector_all(
                'input[name="%s"]' % field, "els => els.length")
            if count != expected:
                raise AssertionError(
                    "with scripts blocked, expected %d radios named %r (the "
                    "%s row's own palette, %s by default) with no script "
                    "involvement in rendering it - found %d"
                    % (expected, field, usage, state, count))


def test_arrivals_still_saves_with_scripts_blocked(new_context, make_app_server):
    """The arrivals grid still saves with scripts blocked, at 360px and in both shipped
    languages: operated natively by field name, submitted through the real form, re-read
    from disk after a fresh GET and restored the same way. Seeded through the validated
    save_device_config() API rather than a raw file write, since theme_arriving's own None
    state would otherwise defeat the shared helper's stored-is-None save-floor guard.
    """
    server = make_app_server(seed=seed_state_dir, fake_providers=True)
    base_url = server.base_url()

    def read_back():
        return device_config.load_device_config(server.tmpdir).get("theme_arriving")

    original_arriving = read_back()
    current_theme = device_config.load_device_config(server.tmpdir)["theme"]
    seed = next(t for t in device_config.THEME_IDS if t != current_theme)
    device_config.save_device_config(server.tmpdir, theme_arriving=seed)
    before = read_back()
    if before != seed:
        raise AssertionError(
            "the seeded theme_arriving did not read back as written: %r" % (before,))
    target = next(t for t in device_config.THEME_IDS if t != before)

    try:
        seen = {}
        for lang in ("en", "fr"):
            seen[lang] = _persist_without_js(
                new_context, base_url, "/display", "theme_arriving", target,
                read_back, viewport=VIEWPORT_MIN_SUPPORTED,
                cookies=[{"name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": base_url}])
        after = read_back()
        if str(after) != str(before):
            raise AssertionError(
                "the scripts-blocked save left theme_arriving at %r, it "
                "started (seeded) at %r — a harness that changes a real "
                "setting edits its neighbours' subject" % (after, before))
        for lang, result in seen.items():
            if str(result["stored"]) != str(target):
                raise AssertionError(
                    "lang=%s: theme_arriving did not reach disk, it reads %r"
                    % (lang, result["stored"]))
            if str(result["restored"]) != str(before):
                raise AssertionError(
                    "lang=%s: the restore leg did not put %r back, disk "
                    "reads %r" % (lang, before, result["restored"]))

        n_themes = len(device_config.THEME_IDS)
        with _no_js_page(new_context, base_url, "/display",
                         viewport=VIEWPORT_MIN_SUPPORTED) as page:
            for field, usage, state, expected in (
                    ("theme_arriving", "arrivals", "closed", n_themes + 1),
                    ("theme", "departures", "open", n_themes)):
                count = page.eval_on_selector_all(
                    'input[name="%s"]' % field, "els => els.length")
                if count != expected:
                    raise AssertionError(
                        "with scripts blocked, expected %d radios named %r "
                        "(the %s row's own palette, %s by default) with no "
                        "script involvement in rendering it - found %d"
                        % (expected, field, usage, state, count))
    finally:
        if original_arriving is None:
            device_config.save_device_config(
                server.tmpdir, theme_arriving=device_config.CLEAR_THEME_ARRIVING)
        else:
            device_config.save_device_config(server.tmpdir, theme_arriving=original_arriving)
        final = read_back()
        if final != original_arriving:
            raise AssertionError(
                "restoring theme_arriving failed: wanted %r, disk reads %r"
                % (original_arriving, final))


# The palette preview's keyboard/hover/focus behaviour, over the static wrapping grid the
# carousel was rebuilt into.

def test_keying_the_palette_moves_the_preview(new_context, server):
    """Arrow-keying the look sheet's colour radiogroup (no click at all, the sheet itself opened
    from the keyboard) moves the departures look to a real theme of the next colour, and the
    departures picture follows it through theme-preview.js's own delegated change listener,
    settled on that theme's own preview and fully opaque.
    """
    context = new_context(viewport=VIEWPORT_PHONE)
    try:
        page = context.new_page()
        base_url = server.base_url()
        _login(page, base_url)
        page.goto(base_url + "/display")
        page.wait_for_load_state("networkidle")
        checked = 'input[name="theme"]:checked'
        checked_value = page.eval_on_selector(checked, "el => el.value")
        page.focus('[data-look-usage="departures"] summary.look-edit__summary')
        page.keyboard.press("Enter")
        page.locator("[data-look-sheet]").wait_for(state="visible")
        page.keyboard.press("ArrowRight")
        page.wait_for_timeout(200)
        new_value = page.eval_on_selector(checked, "el => el.value")
        if new_value == checked_value:
            raise AssertionError(
                "ArrowRight inside the look sheet's colour radiogroup did not move the "
                "departures look off %r" % (checked_value,))
        expected_src = page.eval_on_selector(
            'input[name="theme"][value="%s"]' % new_value,
            "el => el.parentNode.getAttribute('data-preview-src')")
        try:
            page.wait_for_function(
                "args => { var img = document.querySelector(args.sel);"
                " return !!img && img.getAttribute('src') === args.expected"
                " && parseFloat(getComputedStyle(img).opacity) === 1; }",
                arg={"sel": THEME_PREVIEW_SEL, "expected": expected_src},
                timeout=3000)
        except Exception:
            live_src = page.eval_on_selector(
                THEME_PREVIEW_SEL, "el => el.getAttribute('src')")
            raise AssertionError(
                "expected the departures picture to settle on %r (the newly selected theme's "
                "own preview), fully opaque, after keying the sheet with no click at all - it "
                "reads %r" % (expected_src, live_src))
    finally:
        context.close()


def test_the_preview_follows_hover_and_focus_and_selects_nothing(new_context, server):
    """Hovering and keyboard-focusing the pictures and the look sheet's choices select nothing:
    opening the sheet, moving focus through its choices with Tab and closing it again leaves
    the checked departures radio, the picture's src and the value on disk exactly as they were;
    only a real choice changes the look.
    """
    context = new_context(viewport=VIEWPORT_PHONE)
    try:
        page = context.new_page()
        base_url = server.base_url()
        _login(page, base_url)
        page.goto(base_url + "/display")
        page.wait_for_load_state("networkidle")

        def state():
            return {
                "disk": device_config.load_device_config(server.tmpdir)["theme"],
                "checked": page.eval_on_selector('input[name="theme"]:checked', "el => el.value"),
                "src": page.eval_on_selector(THEME_PREVIEW_SEL, "el => el.getAttribute('src')"),
            }

        before = state()
        page.hover('[data-look-usage="arrivals"] button.look-frame__open')
        page.hover('[data-look-usage="departures"] button.look-frame__open')
        page.focus('[data-look-usage="departures"] summary.look-edit__summary')
        page.keyboard.press("Enter")
        page.locator("[data-look-sheet]").wait_for(state="visible")
        for _ in range(6):
            page.keyboard.press("Tab")
        page.hover('[data-look-sheet] .look-dot:has(input[value="green"])')
        page.keyboard.press("Escape")
        page.locator("[data-look-sheet]").wait_for(state="hidden")
        after = state()
        if after != before:
            raise AssertionError(
                "opening the sheet and moving through its choices without choosing changed "
                "the look: %r -> %r" % (before, after))
    finally:
        context.close()


# --- The three converted static ages tick in a real browser ---------------
#
# Each site is seeded relative to the REAL wall clock (never a fixed past
# date like seed_state_dir()'s), so its age lands in the minutes bucket at
# the moment the page loads. Playwright's clock is installed BEFORE
# navigation, freezing Date.now() at the real instant it was installed, so
# the server-rendered text and the script's own first read agree; run_for()
# then advances it 65 virtual seconds without any real wall-clock wait,
# firing relative-time.js's once-a-second interval enough times to cross
# the two-minute boundary.

_TICK_MINUTES_AGO = 2
_TICK_ADVANCE_MS = 65_000


def _seed_flights_ticker(state_dir):
    seen = datetime.now(timezone.utc) - timedelta(minutes=_TICK_MINUTES_AGO)
    with history_db.open_db(state_dir) as conn:
        history_db.record_runway_event(
            conn, ts=seen.isoformat(), hex="3c6444", callsign="AFR1380",
            aircraft_type="A320", confirmed_state="confirmed",
            corroborated=True, route_source="adsb", airline="Air France",
            origin="ORY", destination="TLS",
            tracked_runway=device_config.RUNWAY_IDS[0])


def _seed_calendar_ticker(state_dir):
    now = datetime.now(timezone.utc)
    synced = now - timedelta(minutes=_TICK_MINUTES_AGO)
    calendar_rules.save_calendar_url(
        state_dir, "https://example.invalid/roster.ics", now=now.timestamp())
    entry_start = now + timedelta(hours=3)
    entry_end = entry_start + timedelta(hours=2)
    calendar_rules.write_calendar_registry(
        state_dir,
        [{"airline_iata": "AF", "origin_iata": "ORY", "destination_iata": "NCE",
          "start_at": entry_start.timestamp(), "end_at": entry_end.timestamp()}],
        last_attempt_at=now.timestamp(),
        last_synced_at=synced.isoformat(timespec="seconds"),
        now=now.timestamp())


def _seed_health_ticker(state_dir):
    seen = (datetime.now(timezone.utc) - timedelta(minutes=_TICK_MINUTES_AGO)).isoformat()
    state_store.save_poll_state(state_dir, {"unresolved_prefixes": {
        "TVF": {"count": 5, "first_seen": seen, "last_seen": seen,
                "example_callsign": "TVF123"},
    }})


_TICKER_SITES = (
    ("flights", "/flights",
     'table.data-table--flights tr[data-filter-group="0"] time[data-relative]',
     _seed_flights_ticker),
    ("display-calendar", "/display",
     '[data-look-usage="calendar"] time[data-relative]',
     _seed_calendar_ticker),
    ("health-registry", "/health",
     '.data-table--registry tr[data-filter-group="0"] time[data-relative]',
     _seed_health_ticker),
)


@pytest.mark.parametrize(
    "name, path, selector, seed_fn", _TICKER_SITES,
    ids=[site[0] for site in _TICKER_SITES])
def test_cfg34_live_age_ticks_at_each_converted_site(
        new_context, make_app_server, name, path, selector, seed_fn):
    """Each of the three converted ages (Flights' When cell, Display's Calendar status
    detail, Health's registry First-seen cell) is a genuine <time data-relative> element that
    relative-time.js's once-a-second ticker advances in a visible tab: read once right after
    load, read again with the clock UNMOVED (the control an element that never changes for any
    reason would also pass — see below), then again after the virtual clock runs forward past
    a minute boundary, where the text must have moved to the next bucket.
    """
    server = make_app_server(seed=seed_fn, fake_providers=True)
    base_url = server.base_url()
    context = new_context(viewport=VIEWPORT_DESKTOP)
    try:
        page = context.new_page()
        # Installed before navigation: Date.now() freezes at the real instant
        # of install() until explicitly advanced, so relative-time.js's first
        # repaint (on load) reads the same instant the server itself rendered
        # from — no race between the two clocks.
        page.clock.install()
        _login(page, base_url)
        page.goto(base_url + path)
        locator = page.locator(selector).first
        locator.wait_for(state="attached")
        before = locator.text_content()
        if not before or not before.strip():
            raise AssertionError(
                "%s: expected the converted age to already carry text at load, got %r"
                % (name, before))
        control = locator.text_content()
        if control != before:
            raise AssertionError(
                "%s: control failed — the text moved (%r -> %r) with the clock "
                "never advanced at all, so the assertion below would prove "
                "nothing about the ticker specifically" % (name, before, control))
        page.clock.run_for(_TICK_ADVANCE_MS)
        after = locator.text_content()
        if after == before:
            raise AssertionError(
                "%s: expected the age to ADVANCE to the next bucket after the "
                "clock ran forward %dms, still reads %r — a dead element would "
                "read exactly this way" % (name, _TICK_ADVANCE_MS, before))
    finally:
        context.close()


# Display polish: faithful swatches, an uncropped live preview, and the saved confirmation.

SWATCH_VIEWPORTS = (
    ("desktop", VIEWPORT_DESKTOP), ("phone", VIEWPORT_PHONE),
    ("min", VIEWPORT_MIN_SUPPORTED))
SAVED_WORD = {"en": "Saved", "fr": "Enregistr"}


def _lang_cookie(base_url, lang):
    return [{"name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": base_url}]


def test_swatches_tell_solid_light_and_band_themes_apart(new_context, server):
    """Every theme's swatch in the departures table is drawn from its own metadata: a light
    (dithered) theme paints its ink translucent over paper where its solid sibling paints it
    opaque in the same colour, and a band theme paints a band the plain fields lack.
    """
    context = new_context(viewport=VIEWPORT_DESKTOP)
    try:
        page = context.new_page()
        base_url = server.base_url()
        _login(page, base_url)
        page.goto(base_url + "/display")
        page.wait_for_load_state("networkidle")
        painted = page.evaluate(
            "() => { var out = {};"
            " document.querySelectorAll("
            "'[data-look-usage=\"departures\"] .look-table-block label').forEach(function (cell) {"
            "  var svg = cell.querySelector('svg.look-swatch');"
            "  if (!svg) return;"
            "  var rects = svg.querySelectorAll('rect');"
            "  var field = rects[rects.length - 1];"
            "  var band = svg.querySelector('polygon');"
            "  out[cell.querySelector('input').value] = {"
            "   fill: getComputedStyle(field).fill,"
            "   field: getComputedStyle(field).fillOpacity,"
            "   band: band ? getComputedStyle(band).fillOpacity : null};"
            " }); return out; }")
        assert len(painted) == len(device_config.THEME_IDS), sorted(painted)
        for solid, light in (
                ("yellow", "yellow_light"), ("red", "red_light"),
                ("green", "green_light"), ("blue", "blue_light")):
            if painted[solid]["field"] != "1" or painted[light]["field"] == "1":
                raise AssertionError(
                    "%s must paint solid and %s must paint translucent: %r / %r"
                    % (solid, light, painted[solid], painted[light]))
            if painted[solid]["fill"] != painted[light]["fill"]:
                raise AssertionError("%s and %s must share one ink colour" % (solid, light))
        if painted["band_blue"]["band"] != "1":
            raise AssertionError("a solid band must be opaque: %r" % painted["band_blue"])
        if painted["band_blue_light"]["band"] in (None, "1"):
            raise AssertionError("a light band must be translucent: %r" % painted["band_blue_light"])
        if painted["band_blue_field"]["band"] != "1" or painted["band_blue_field"]["field"] == "1":
            raise AssertionError(
                "a band-field theme tints its field around a solid band: %r"
                % painted["band_blue_field"])
        if painted["white"]["band"] is not None:
            raise AssertionError("a plain theme carries no band")
    finally:
        context.close()


@pytest.mark.parametrize("lang", ("en", "fr"))
@pytest.mark.parametrize("label,viewport", SWATCH_VIEWPORTS)
def test_the_live_preview_is_contained_keyed_focusable_and_saves(
        new_context, make_app_server, label, viewport, lang):
    """At 1280, 390 and 360 px in both languages the departures picture sits whole inside its
    frame and the page, the look sheet opened from the keyboard moves the look with the arrow
    keys behind a visible focus ring, and the native save lands on the persisted theme with the
    saved confirmation.
    """
    server = make_app_server(seed=seed_state_dir, fake_providers=True)
    base_url = server.base_url()
    context = new_context(viewport=viewport)
    try:
        context.add_cookies(_lang_cookie(base_url, lang))
        page = context.new_page()
        _login(page, base_url)
        page.goto(base_url + "/display")
        page.wait_for_load_state("networkidle")
        box = page.evaluate(
            "() => { var img = document.querySelector('%s');"
            " var fig = img.closest('.look-frame__picture'); var i = img.getBoundingClientRect();"
            " var f = fig.getBoundingClientRect();"
            " return {iw: i.width, ih: i.height, il: i.left, ir: i.right,"
            "  fl: f.left, fr: f.right, ft: f.top, fb: f.bottom, it: i.top, ib: i.bottom,"
            "  vw: document.documentElement.clientWidth,"
            "  natural: img.complete && img.naturalWidth > 0,"
            "  fit: getComputedStyle(img).objectFit}; }" % THEME_PREVIEW_SEL)
        if not box["natural"] or box["iw"] <= 0 or box["ih"] <= 0:
            raise AssertionError("%s: the picture did not render: %r" % (label, box))
        if box["il"] < box["fl"] - 0.5 or box["ir"] > box["fr"] + 0.5 or \
                box["it"] < box["ft"] - 0.5 or box["ib"] > box["fb"] + 0.5 or \
                box["il"] < 0 or box["ir"] > box["vw"]:
            raise AssertionError("%s: the picture is clipped: %r" % (label, box))
        if box["fit"] != "contain":
            raise AssertionError("%s: the picture must never crop its render: %r" % (label, box))
        problem = _assert_no_page_overflow(page, "display %s %s" % (label, lang))
        if problem:
            raise AssertionError(problem)

        selector = 'input[name="theme"]'
        start = page.eval_on_selector(selector + ":checked", "el => el.value")
        page.focus('[data-look-usage="departures"] summary.look-edit__summary')
        page.keyboard.press("Enter")
        page.locator("[data-look-sheet]").wait_for(state="visible")
        page.keyboard.press("ArrowRight")
        moved = page.eval_on_selector(selector + ":checked", "el => el.value")
        if moved == start:
            raise AssertionError("%s: arrow keys did not move the look" % label)
        ring = page.evaluate(
            "() => { var dot = document.activeElement.closest('.look-dot');"
            " var cs = getComputedStyle(dot);"
            " return cs.outlineStyle + '|' + cs.outlineWidth; }")
        if ring.startswith("none|") or ring.endswith("|0px"):
            raise AssertionError("%s: the focused colour shows no focus ring: %r" % (label, ring))
        page.keyboard.press("Escape")
        _save_via_bar(page, timeout=30000)
        stored = device_config.load_device_config(server.tmpdir)["theme"]
        if stored != moved:
            raise AssertionError("%s: saved %r but disk reads %r" % (label, moved, stored))
        if SAVED_WORD[lang].lower() not in page.inner_text("body").lower():
            raise AssertionError("%s/%s: no saved confirmation after the save" % (label, lang))
    finally:
        context.close()


