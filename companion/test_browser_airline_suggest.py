"""Real-browser checks of the suggested airline names in the Airlines editor
(administrator, Chromium): a pending row becomes a suggestion row without a
page load, one request at a time and at most three per load; the check names
the airline with the flash of manual naming and the row leaves the
unidentified list; a failing service leaves "Name it" working; at 390 and
1440 px, in English and French, in both themes, nothing overflows, every
control is a 44 px target with an accessible name and a 100-character name is
cut inside its row. The service is a loopback fake the app server is pointed
at through its environment; with scripts blocked the page still shows
suggestions already cached and "Name it".

State is always waited for (settled page, row text), never read right after
an input."""
import json
import time

import animation_settle
import pytest
from fake_anthropic import DUMMY_KEY, FakeAnthropic, Scripted, airline_body, error_body

import companion.test_status_pages_helpers as shp
from companion import auth
from companion.test_browser_ux_helpers import (
    VIEWPORT_PHONE, _assert_hit_target, _assert_no_page_overflow, _in_both_themes, _login, _no_js_page,
    seed_state_dir,
)
from server.plane import airline_suggest as ais
from server.plane import manual_resolutions

pytestmark = pytest.mark.browser

VIEWPORT_WIDE = {"width": 1440, "height": 900}
VIEWPORTS = (("390", VIEWPORT_PHONE), ("1440", VIEWPORT_WIDE))
STAMP = "2026-11-17T10:29:00+00:00"
ORDER = ("OCN", "ITI", "ZLN", "CMA", "QQQ")
LONG_NAME = ("Oceanair Regional Passenger and Freight Services of the Southern Atlantic "
             "Coast Holding Company Ltd")[:100]
GAP = "tbody.airline-group--gap"
PENDING = GAP + "[data-suggest-prefix]"
CHECK = GAP + " .airlines-check"


def _seed(prefixes=ORDER, cache=None):
    def seed(state_dir):
        seed_state_dir(state_dir)
        shp.seed_unresolved_prefixes(state_dir, {
            prefix: {"count": 20 - index, "first_seen": STAMP, "last_seen": STAMP,
                     "example_callsign": prefix + "1"} for index, prefix in enumerate(prefixes)})
        if cache:
            entries = {p: {"state": "suggested", "name": name, "model": ais.MODEL_ID, "asked_at": STAMP}
                       for p, name in cache.items()}
            with open(ais.cache_path(state_dir), "w") as handle:
                json.dump({"entries": entries, "calls": []}, handle)
    return seed


@pytest.fixture
def fake():
    server = FakeAnthropic("Oceanair").start()
    yield server
    server.stop()


def _open(new_context, server, viewport, lang="en", **context_args):
    context = new_context(viewport=viewport, **context_args)
    context.add_cookies([{"name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": server.base_url()}])
    page = context.new_page()
    _login(page, server.base_url())
    page.goto(server.base_url() + "/airlines/manage")
    page.wait_for_selector(GAP)
    return context, page


def _row(prefix):
    """The row of one prefix, as a plain CSS selector (the filter text ends with it)."""
    return '%s[data-filter-text$=" %s"]' % (GAP, prefix.lower())


def test_pending_rows_are_asked_one_at_a_time_and_at_most_three_per_load(
        new_context, make_app_server, fake):
    fake.delay_s = 0.4
    server = make_app_server(seed=_seed(), fake_providers=True, env_overrides=fake.env())
    context, page = _open(new_context, server, VIEWPORT_WIDE)
    try:
        assert page.locator(PENDING).count() == 3
        assert page.locator(GAP + " .airlines-tag--pending").count() == 3
        page.wait_for_function(
            "n => document.querySelectorAll('.airlines-check').length === n", arg=3, timeout=20000)
        assert page.locator(PENDING).count() == 0
        assert fake.call_count == 3 and fake.max_active == 1
        assert [r["body"]["messages"][0]["content"].split("\n")[0] for r in fake.requests] == [
            "Designator: OCN", "Designator: ITI", "Designator: ZLN"]
        time.sleep(0.8)
        assert fake.call_count == 3
        assert page.locator(_row("OCN") + " .airlines-gap__name").inner_text() == "Oceanair"
        assert page.locator(_row("CMA") + " .airlines-tag").count() == 0
        page.reload()
        page.wait_for_function(
            "n => document.querySelectorAll('.airlines-check').length === n", arg=5, timeout=20000)
        assert fake.call_count == 5
    finally:
        context.close()


def test_the_check_names_the_airline_with_the_flash_of_manual_naming(new_context, make_app_server, fake):
    server = make_app_server(
        seed=_seed(("OCN", "ITI"), cache={"OCN": "Oceanair", "ITI": "Itavia Express"}),
        fake_providers=True, env_overrides=fake.env())
    context, page = _open(new_context, server, VIEWPORT_PHONE)
    try:
        with page.expect_navigation():
            page.locator(_row("OCN") + " .airlines-check").click()
        page.locator(".toast").first.wait_for(state="visible")
        assert "Airline name saved" in page.locator(".toast").first.inner_text()
        page.wait_for_function(
            "() => !document.querySelector('tbody.airline-group--gap[data-filter-text$=\" ocn\"]')")
        assert page.locator(_row("OCN")).count() == 0 and page.locator(_row("ITI")).count() == 1
        names = manual_resolutions.load_manual_resolutions(server.state_dir)
        assert names["OCN"]["airline_name"] == "Oceanair" and "ITI" not in names
        assert ais.cached(server.state_dir, "OCN")["state"] == "accepted"
        assert fake.call_count == 0
    finally:
        context.close()


def test_a_failing_service_leaves_name_it_working(new_context, make_app_server, fake):
    fake.script(*[Scripted(529, error_body("overloaded_error")) for _ in range(5)])
    server = make_app_server(seed=_seed(("OCN", "ITI")), fake_providers=True, env_overrides=fake.env())
    context, page = _open(new_context, server, VIEWPORT_PHONE)
    try:
        page.wait_for_function(
            "() => !document.querySelector('[data-suggest-prefix]')"
            " && !document.querySelector('.airlines-tag--pending')", timeout=20000)
        assert fake.call_count == 1
        assert page.locator(GAP + " .airlines-tag").count() == 0
        assert page.locator(GAP + " a[data-modal-open]").count() == 2
        page.locator(_row("OCN") + " a[data-modal-open]").click()
        page.locator(_row("OCN") + " dialog input[name=airline_name]").fill("Ocean Wings")
        with page.expect_navigation():
            page.locator(_row("OCN") + " dialog button[type=submit]").click()
        page.locator(".toast").first.wait_for(state="visible")
        assert manual_resolutions.load_manual_resolutions(server.state_dir)["OCN"]["airline_name"] == "Ocean Wings"
    finally:
        context.close()


def test_an_unknown_airline_gives_the_plain_row(new_context, make_app_server, fake):
    fake.script(Scripted(200, airline_body(None)))
    server = make_app_server(seed=_seed(("OCN",)), fake_providers=True, env_overrides=fake.env())
    context, page = _open(new_context, server, VIEWPORT_PHONE)
    try:
        page.wait_for_function("() => !document.querySelector('[data-suggest-prefix]')", timeout=20000)
        assert page.locator(GAP + " .airlines-tag").count() == 0
        assert page.locator(GAP + " a[data-modal-open]").inner_text() == "Name it"
    finally:
        context.close()


def test_removing_a_suggestion_in_its_dialog_returns_the_row_to_name_it(new_context, make_app_server, fake):
    server = make_app_server(
        seed=_seed(("OCN",), cache={"OCN": "Oceanair"}), fake_providers=True, env_overrides=fake.env())
    context, page = _open(new_context, server, VIEWPORT_WIDE)
    try:
        page.locator(_row("OCN") + " .airlines-gap__edit").click()
        field = page.locator(_row("OCN") + " dialog input[name=airline_name]")
        field.wait_for(state="visible")
        assert field.input_value() == "Oceanair"
        with page.expect_navigation():
            page.locator(_row("OCN") + " .airlines-remove").click()
        page.wait_for_selector(GAP)
        assert page.locator(GAP + " .airlines-tag").count() == 0
        assert page.locator(GAP + " a[data-modal-open]").inner_text() == "Name it"
        assert ais.cached(server.state_dir, "OCN")["state"] == "rejected"
        assert fake.call_count == 0
    finally:
        context.close()


@pytest.mark.parametrize("lang", ("en", "fr"))
@pytest.mark.parametrize("name,viewport", VIEWPORTS, ids=[v[0] for v in VIEWPORTS])
def test_suggestion_rows_fit_and_every_control_is_a_44px_target_in_both_themes(
        new_context, make_app_server, fake, name, viewport, lang):
    server = make_app_server(
        seed=_seed(("OCN", "ITI", "CMA"), cache={"OCN": LONG_NAME, "ITI": "Itavia Express"}),
        fake_providers=True, env_overrides=fake.env())
    context, page = _open(new_context, server, viewport, lang)
    try:
        page.wait_for_function(
            "() => !document.querySelector('[data-suggest-prefix]')", timeout=20000)
        expected_use = ("Use the suggestion %s for OCN" if lang == "en"
                        else "Utiliser la suggestion %s pour OCN") % LONG_NAME
        assert page.locator(_row("OCN") + " .airlines-check").get_attribute("aria-label") == expected_use
        assert page.locator(_row("OCN") + " .airlines-gap__edit").get_attribute("aria-label")
        for _paint in _in_both_themes(page):
            assert not _assert_no_page_overflow(page, "suggestions", viewport["width"])
            for selector in (_row("OCN") + " .airlines-check", _row("OCN") + " .airlines-gap__edit",
                             _row("ITI") + " .airlines-check", _row("CMA") + " a[data-modal-open]"):
                _assert_hit_target(page, selector, "suggestions %s %s" % (name, lang))
            cut = page.evaluate(
                "sel => { const n = document.querySelector(sel + ' .airlines-gap__name');"
                " const r = document.querySelector(sel + ' .airlines-gap').getBoundingClientRect();"
                " const b = n.getBoundingClientRect();"
                " return {cut: n.scrollWidth > n.clientWidth, inside: b.left >= r.left && b.right <= r.right}; }",
                _row("OCN"))
            assert cut["inside"]
            if viewport["width"] < 700:
                assert cut["cut"]
    finally:
        context.close()


@pytest.mark.parametrize("name,viewport", VIEWPORTS, ids=[v[0] for v in VIEWPORTS])
def test_the_edit_dialog_is_a_sheet_on_a_phone_and_a_card_on_a_desktop(
        new_context, make_app_server, fake, name, viewport):
    server = make_app_server(
        seed=_seed(("OCN",), cache={"OCN": "Oceanair"}), fake_providers=True, env_overrides=fake.env())
    context, page = _open(new_context, server, viewport)
    try:
        page.locator(_row("OCN") + " .airlines-gap__edit").click()
        dialog = page.locator(_row("OCN") + " dialog")
        dialog.locator("input[name=airline_name]").wait_for(state="visible")
        animation_settle.wait_settled(page, "dialog[open]")
        box = dialog.bounding_box()
        if viewport["width"] < 700:
            assert box["y"] + box["height"] >= viewport["height"] - 1 and box["width"] >= viewport["width"] - 2
        else:
            assert abs(box["x"] + box["width"] / 2 - viewport["width"] / 2) < 2
            assert abs(box["y"] + box["height"] / 2 - viewport["height"] / 2) < 4
        remove = dialog.locator(".airlines-remove")
        assert remove.inner_text() == "Remove the suggestion"
        _assert_hit_target(page, _row("OCN") + " dialog .airlines-remove", "remove %s" % name)
    finally:
        context.close()


def test_with_scripts_blocked_cached_suggestions_and_name_it_still_work(
        new_context, make_app_server, fake):
    server = make_app_server(
        seed=_seed(("OCN", "ITI", "CMA"), cache={"OCN": "Oceanair"}),
        fake_providers=True, env_overrides=fake.env())
    with _no_js_page(new_context, server.base_url(), "/airlines/manage") as page:
        page.wait_for_selector(GAP)
        assert page.locator(_row("OCN") + " .airlines-gap__name").inner_text() == "Oceanair"
        assert page.locator(GAP + " .airlines-tag--pending").first.is_hidden()
        assert page.locator(_row("ITI") + " a[data-modal-open]").inner_text() == "Name it"
        with page.expect_navigation():
            page.locator(_row("OCN") + " .airlines-check").click()
        assert manual_resolutions.load_manual_resolutions(server.state_dir)["OCN"]["airline_name"] == "Oceanair"
    assert fake.call_count == 0


def test_the_dummy_key_never_reaches_the_page(new_context, make_app_server, fake):
    server = make_app_server(seed=_seed(("OCN",)), fake_providers=True, env_overrides=fake.env())
    context, page = _open(new_context, server, VIEWPORT_PHONE)
    try:
        page.wait_for_function("() => !document.querySelector('[data-suggest-prefix]')", timeout=20000)
        assert DUMMY_KEY not in page.content()
        assert fake.requests[0]["headers"]["x-api-key"] == DUMMY_KEY
    finally:
        context.close()
