#!/usr/bin/env python3
"""Browser checks for the scripts-blocked accordion's own operability/save floor, the Touch
Targets measurement sweep over the palette/usage-row/rule-add controls, the no-JS floor's
save-to-disk proof, the restored dirty bar's settle contract, a server-side validation
rejection's inline-error/echo/no-toast floor, the bar's own document-order section naming, a
real Annuler click's restore-every-surface proof, the settings-card-title consistency probe,
the single-submit-affordance audit, the theme radios' cross-tree `form="settings-form"`
regression check, and the artwork drop zone's own upload/equivalence/geometry family.

Read-only checks share one module-scoped, read-only `server` fixture: the palette Touch
Targets sweep, the rejected-value floor (the rejection never reaches disk), the bar's
document-order section-naming check and the Annuler restore check (both discard their own
edit rather than saving it), the settings-card-title probe and the single-submit-affordance
audit. Every check that persists a setting gets its own function-scoped `make_app_server`
server. The artwork drop zone's three checks need a different seed (a `needs-artwork` manual
resolution entry the default fixture never creates): the two that actually upload a file get
their own function-scoped server each; the one that only measures the zone at rest shares a
second, dedicated module-scoped `artwork_server` fixture.
"""
import collections
import io
import os

import pytest
from PIL import Image

from companion import auth, illustration_normalize
from companion.pages import airlines_page, config_page
from server import device_config
from server.plane import illustrations, manual_resolutions
from companion.test_browser_ux_helpers import (
    UI_THEMES_EXPLICIT, VIEWPORT_DESKTOP, VIEWPORT_MIN_SUPPORTED, VIEWPORT_PHONE,
    _assert_hit_target, _assert_js_gate, _assert_no_page_overflow,
    _assert_surfaces_agree, _await_upload_zone, _bar_text, _click_control,
    _drop_files, _in_both_themes, _login,
    _no_js_page, _persist_without_js, _POINTER_RECORDER_ARM,
    _POINTER_RECORDER_READ, _save_via_bar,
    _SUBMIT_PROBE, _set_ui_theme, _upload_without_js, _upload_zone_state,
    _wait_for_bar, _wait_for_bar_hidden, seed_state_dir,
)

pytestmark = pytest.mark.browser

# Also defined in companion/test_browser_ux_03.py, since that module's own checks read it too;
# kept local to each module rather than promoted into the shared helpers file.
THEME_PREVIEW_SEL = '[data-look-usage="departures"] img.look-frame__image'


@pytest.fixture(scope="module")
def server(module_app_server_factory):
    """The shared, read-only seeded fixture every read-only check in this module measures
    against — module-scoped because none of them persists a real setting (the two checks
    that edit a field discard it via Annuler or a server-side rejection rather than saving it).
    """
    return module_app_server_factory(seed=seed_state_dir, fake_providers=True)


# The artwork drop zone fixture family.
#
# A manual resolution with no artwork yet ("needs-artwork") is the one state where both the
# in-page no-JS fallback panel and the dialog's own copy of the upload form render at once.
# `seed_state_dir()` alone never creates this entry, so this seed layers it on top.

ARTWORK_PREFIX = "NEW"
ARTWORK_NAME = "Totally Novel Airline"
ARTWORK_KEY = manual_resolutions.illustration_key_for_name(ARTWORK_NAME)
ARTWORK_ROUTE = "/airlines/manage?resolve=" + ARTWORK_PREFIX
ARTWORK_SERVE = "/illustration/%s.png" % ARTWORK_KEY
FALLBACK_ZONE = "[data-resolve-fallback] [data-upload-drop]"
# The dialog's Replace form renders unconditionally, so #panel-lookup-dialog carries both
# upload-drop zones at once — this one (the needs-artwork resolve zone, id_suffix="-dialog")
# and REPLACE_INPUT_ID's own. Disambiguated by the same UPLOAD_DROP_INPUT_ATTR value
# panel-lookup.js itself reads to decide which to hide.
DIALOG_ZONE = "#panel-lookup-dialog [%s='%s']" % (
    airlines_page.UPLOAD_DROP_INPUT_ATTR,
    airlines_page.MANUAL_UPLOAD_INPUT_ID + "-dialog",
)


def _seed_with_needs_artwork_entry(state_dir):
    seed_state_dir(state_dir)
    if manual_resolutions.add_entry(
            state_dir, ARTWORK_PREFIX, ARTWORK_NAME) != manual_resolutions.ADD_OK:
        raise AssertionError("could not seed the Step-B manual entry")


@pytest.fixture(scope="module")
def artwork_server(module_app_server_factory):
    """A second, dedicated module-scoped server seeded with the needs-artwork manual entry,
    for the one artwork check that never uploads anything (it only measures the zone at
    rest) — the two that actually store a file each get their own function-scoped server
    instead.
    """
    return module_app_server_factory(seed=_seed_with_needs_artwork_entry, fake_providers=True)


def _write_artwork_fixtures(tmp_path):
    """A real, plausible illustration (a landscape PNG with transparent
    padding, the shape every vendored file has and the shape
    illustration_normalize.py crops), a non-image file, and an oversized
    PNG (incompressible noise on purpose, so it cannot compress under the
    server's own cap) — all written under `tmp_path`, never
    `tempfile.mkdtemp()`.
    """
    art_path = tmp_path / "artwork.png"
    art = Image.new("RGBA", (1200, 300), (0, 0, 0, 0))
    for ax in range(200, 1000):
        for ay in range(80, 220):
            art.putpixel((ax, ay), (200, 40, 40, 255))
    art.save(art_path)

    not_png_path = tmp_path / "not-an-image.txt"
    not_png_path.write_bytes(b"this is not a png\n")

    oversized_path = tmp_path / "oversized.png"
    Image.frombytes(
        "RGBA", (1200, 1200), os.urandom(1200 * 1200 * 4)).save(oversized_path)

    return {
        "art_path": str(art_path),
        "not_png_path": str(not_png_path),
        "oversized_path": str(oversized_path),
        "art_bytes": os.path.getsize(art_path),
        "oversized_bytes": os.path.getsize(oversized_path),
    }


def _stored_artwork(server):
    """The stored override's bytes, or None. The verdict for every upload below, read off
    the real state directory rather than off the page — a POST this app rejected redirects
    to a page that looks exactly like success.
    """
    path = illustrations.override_path_for_key(ARTWORK_KEY, server.tmpdir)
    if not path or not os.path.isfile(path):
        return None
    with open(path, "rb") as fh:
        return fh.read()


def _clear_stored_artwork(server):
    path = illustrations.override_path_for_key(ARTWORK_KEY, server.tmpdir)
    if path and os.path.isfile(path):
        os.unlink(path)


def test_the_accordion_is_operable_and_saves_with_scripts_blocked(new_context, make_app_server):
    """With scripts blocked, in both languages, at 360px: each of the three looks that keep a
    table (arrivals, calendar flights, a new special look) carries its own native <details>
    with a <summary>, the departures look being the grid of radio cards; every registry theme's radio (theme/theme_arriving/calendar_theme_id/
    rule_theme_id) is present in the DOM at full registry size whether or not its disclosure is
    open; a real pointer click on the calendar row's own <summary> opens its table; and a
    selection made inside it reaches disk, read back via device_config.load_device_config(),
    with the restore leg putting the old value back.
    """
    server = make_app_server(seed=seed_state_dir, fake_providers=True)
    base_url = server.base_url()
    n_themes = len(device_config.THEME_IDS)

    def read_back():
        return device_config.load_device_config(server.tmpdir).get("calendar_theme_id")

    for lang in ("en", "fr"):
        with _no_js_page(new_context, base_url, "/display",
                         viewport=VIEWPORT_MIN_SUPPORTED) as page:
            page.context.add_cookies([{
                "name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": base_url}])
            page.goto(base_url + "/display")

            # The looks live on three views: Look (departures cards, arrivals table), the new
            # special look page (the add form) and the calendar look page (its own table).
            disclosures = []
            counts = {}
            for route in ("/display", "/display/special-looks/new", "/display/calendar-look"):
                page.goto(base_url + route)
                for disclosure in page.query_selector_all("details.look-edit"):
                    if disclosure.query_selector("summary") is None:
                        raise AssertionError(
                            "lang=%s: a look disclosure carries no <summary>" % (lang,))
                    if disclosure.get_attribute("open") is not None:
                        raise AssertionError(
                            "lang=%s: expected every look closed at load" % (lang,))
                    disclosures.append(disclosure)
                for field in ("theme", "theme_arriving", "calendar_theme_id", "rule_theme_id"):
                    counts[field] = counts.get(field, 0) + page.eval_on_selector_all(
                        'input[name="%s"]' % field, "els => els.length")
            if len(disclosures) != 2:
                raise AssertionError(
                    "lang=%s: expected 2 look disclosures, found %d" % (lang, len(disclosures)))

            for field, expected in (
                    ("theme", n_themes),
                    ("theme_arriving", n_themes + 1),
                    ("calendar_theme_id", n_themes + 1),
                    ("rule_theme_id", n_themes)):
                if counts[field] != expected:
                    raise AssertionError(
                        "lang=%s: expected %d radios named %r in the DOM whether or not its "
                        "disclosure is open, found %d" % (lang, expected, field, counts[field]))

            page.goto(base_url + "/display/calendar-look")
            calendar = page.query_selector('[data-look-usage="calendar"] details.look-edit')
            # Centred first: left to itself the scroll can park the summary under the
            # fixed bottom tab bar, which then swallows the click.
            calendar.query_selector("summary").evaluate(
                "el => el.scrollIntoView({block: 'center'})")
            calendar.query_selector("summary").click()
            if calendar.get_attribute("open") is None:
                raise AssertionError(
                    "lang=%s: a real pointer click on the calendar look's own <summary> did "
                    "not open it, with scripts blocked" % (lang,))

            before = read_back()
            target = next(t for t in device_config.THEME_IDS if t != before)
            _click_control(
                page, 'input[name="calendar_theme_id"][value="%s"]' % target)
            held = page.eval_on_selector(
                'input[name="calendar_theme_id"][value="%s"]' % target, "el => el.checked")
            if not held:
                raise AssertionError(
                    "lang=%s: the browser refused to check calendar_theme_id=%r with "
                    "scripts blocked" % (lang, target))
            with page.expect_navigation(timeout=30000):
                via = page.evaluate(_SUBMIT_PROBE, {"field": "calendar_theme_id"})

        stored = read_back()
        if str(stored) != str(target):
            raise AssertionError(
                "lang=%s: a selection made inside the calendar look's table (via the %s) did "
                "NOT reach disk - expected %r, got %r" % (lang, via, target, stored))

        device_config.save_device_config(
            server.tmpdir, calendar_theme_id=before if before is not None else "")
        restored = read_back()
        if restored != before:
            raise AssertionError(
                "restoring calendar_theme_id failed: wanted %r, disk reads %r"
                % (before, restored))


def _assert_floor_without_scripts(page, selector, where):
    """The 44px floor and the centre hit-test, measured with synchronous reads only (the shared
    hit-area helper awaits animation frames, which a scripts-blocked page never delivers)."""
    handle = page.locator(selector).first
    handle.evaluate("el => el.scrollIntoView({block: 'center'})")
    box = handle.bounding_box()
    if box is None or box["width"] < 44 - 0.5 or box["height"] < 44 - 0.5:
        raise AssertionError("%s: %r measures %r, under the 44px floor" % (where, selector, box))
    owns = handle.evaluate(
        "el => { const r = el.getBoundingClientRect();"
        " const hit = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);"
        " return !!hit && (hit === el || el.contains(hit) || hit.contains(el)); }")
    if not owns:
        raise AssertionError("%s: %r does not own its own centre" % (where, selector))


def test_the_palette_meets_its_floors_at_360px_in_both_themes(new_context, server):
    """The Touch Targets floor, measured (never declared) in each control's own container,
    in both UI themes, at the 360px contract floor. With scripts blocked: the departures look's
    first and last radio card, the Arrivals view's leading "Same as departures" option and the
    "Add a special look" <summary> all clear 44px, no table scrolls horizontally, the page never
    overflows sideways and a card's preview paints a real box. With scripts: the Departures and
    Arrivals links, the first and last colour dot, every background and stripe option, Reset and
    Save clear 44px and the page never overflows sideways.
    """
    base_url = server.base_url()
    with _no_js_page(new_context, base_url, "/display", viewport=VIEWPORT_MIN_SUPPORTED) as page:
        # Without a script the "Change" summaries open their table in place, closed by default;
        # opened here directly so the tables can be measured.
        page.eval_on_selector_all("details.look-edit", "ds => ds.forEach(d => { d.open = true; })")
        for theme in UI_THEMES_EXPLICIT:
            _set_ui_theme(page, theme)
            cells = '[data-look-usage="departures"] label.look-pick__card'
            if page.eval_on_selector_all(cells, "els => els.length") < 2:
                raise AssertionError("theme=%s: expected the departures table's cells" % theme)
            _assert_floor_without_scripts(
                page, '[data-look-usage="departures"] .look-pick__grid > label:first-child',
                "theme=%s: the FIRST radio card of the departures look" % theme)
            _assert_floor_without_scripts(
                page, '[data-look-usage="departures"] .look-pick__grid > label:last-child',
                "theme=%s: the LAST radio card of the departures look" % theme)
            scrolling = page.eval_on_selector_all(
                ".look-table__scroll",
                "els => els.filter(e => e.getClientRects().length"
                " && e.scrollWidth > e.clientWidth).length")
            if scrolling:
                raise AssertionError(
                    "theme=%s: %d look table(s) scroll horizontally at 360px" % (theme, scrolling))
            msg = _assert_no_page_overflow(
                page, "the look view on /display (theme=%s)" % theme,
                VIEWPORT_MIN_SUPPORTED["width"])
            if msg:
                raise AssertionError(msg)
            # The black card's own preview picture must paint a real box, never collapse.
            paint = page.eval_on_selector(
                '[data-look-usage="departures"] label.look-pick__card:has(input[value="black"]) img',
                "el => { var r = el.getBoundingClientRect();"
                " return {width: r.width, height: r.height}; }")
            if paint["width"] < 60 or paint["height"] < 80:
                raise AssertionError(
                    "theme=%s: the 'black' card's preview collapsed to %r" % (theme, paint))
        page.goto(base_url + "/display/arrivals")
        page.eval_on_selector_all("details.look-edit", "ds => ds.forEach(d => { d.open = true; })")
        for theme in UI_THEMES_EXPLICIT:
            _set_ui_theme(page, theme)
            _assert_floor_without_scripts(
                page, '[data-look-usage="arrivals"] label.look-option:has(input[value=""])',
                "theme=%s: the arrivals \"Same as departures\" option" % theme)
        page.goto(base_url + "/display/special-looks")
        for theme in UI_THEMES_EXPLICIT:
            _set_ui_theme(page, theme)
            _assert_floor_without_scripts(
                page, ".special-add__summary",
                "theme=%s: the \"Add a special look\" link" % theme)

    context = new_context(viewport=VIEWPORT_MIN_SUPPORTED)
    try:
        page = context.new_page()
        _login(page, base_url)
        page.goto(base_url + "/display")
        page.locator("[data-look-sheet][data-look-inline]").wait_for(state="visible")
        picker = "[data-look-sheet][data-look-inline] "
        for theme in UI_THEMES_EXPLICIT:
            _set_ui_theme(page, theme)
            for selector, what in (
                    ('[data-pers-view="departures"]', "the Departures link"),
                    ('[data-pers-view="arrivals"]', "the Arrivals link"),
                    (picker + ".look-dot:first-of-type", "the first colour dot"),
                    (picker + ".look-dot:last-of-type", "the last colour dot"),
                    (picker + ".look-seg__option", "a background or stripe option")):
                _assert_hit_target(page, selector, "theme=%s: %s" % (theme, what))
            msg = _assert_no_page_overflow(
                page, "the look picker on /display (theme=%s)" % theme,
                VIEWPORT_MIN_SUPPORTED["width"])
            if msg:
                raise AssertionError(msg)
    finally:
        context.close()


def test_the_floor_saves_to_disk_with_scripts_blocked_after_the_gate_simplifies(
        new_context, make_app_server):
    """The no-JS floor still saves to disk after the gate simplifies to the plain .js rule:
    theme operated natively, submitted through the real form, re-read from disk
    after a fresh GET, in both shipped languages, at 360px, restored as the last act. The
    data-static-save-fallback submit is present and visible on that scripts-blocked page
    after the save, so a rendering can never stand in for it.
    """
    server = make_app_server(seed=seed_state_dir, fake_providers=True)
    base_url = server.base_url()

    def read_back():
        return device_config.load_device_config(server.tmpdir)["theme"]

    before = read_back()
    target = next(r for r in device_config.THEME_IDS if r != before)
    seen = {}
    # Both shipped languages, at the 360px floor: the UI language is a cookie the first
    # rendered document already has to honour, and "it saves in English" is not the floor.
    for lang in ("en", "fr"):
        seen[lang] = _persist_without_js(
            new_context, base_url, "/display", "theme", target, read_back,
            viewport=VIEWPORT_MIN_SUPPORTED,
            cookies=[{"name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": base_url}])
    after = read_back()
    if str(after) != str(before):
        raise AssertionError(
            "the scripts-blocked save left theme at %r, it started at %r - a "
            "harness that changes a real setting is a test that edits its neighbours' "
            "subject" % (after, before))
    for lang, result in seen.items():
        if str(result["stored"]) != str(target):
            raise AssertionError(
                "lang=%s: theme did not reach disk, it reads %r"
                % (lang, result["stored"]))
        if str(result["restored"]) != str(before):
            raise AssertionError(
                "lang=%s: the restore leg did not put %r back, disk reads %r"
                % (lang, before, result["restored"]))

    # The submit itself, asserted after the save above, never before and never in its place: a
    # rendering can never stand in for the save this check just proved.
    with _no_js_page(new_context, base_url, "/display",
                     viewport=VIEWPORT_MIN_SUPPORTED) as page:
        submit = page.locator("[%s]" % config_page.STATIC_SAVE_FALLBACK_ATTR)
        if submit.count() != 1:
            raise AssertionError(
                "expected exactly one fallback submit with scripts blocked AFTER the "
                "save above, found %d" % submit.count())
        if not submit.is_visible():
            raise AssertionError(
                "the fallback submit rendered but is not VISIBLE with scripts blocked "
                "after the save - this is precisely the shape Phase 22's P0 took")


def test_the_bar_settles_the_field_disk_agree_and_the_bar_hides(new_context, make_app_server):
    """The bar's own settle contract: changing a field reveals the bar, names the changed
    section, updates the field's own DOM value, and leaves disk untouched (the bar means
    unsaved); clicking Enregistrer causes a real navigation; and after it lands the field,
    the bar (now hidden) and disk all agree on the requested value.
    """
    server = make_app_server(seed=seed_state_dir, fake_providers=True)
    context = new_context()
    try:
        page = context.new_page()
        _login(page, server.base_url())
        base_url = server.base_url()
        page.goto(base_url + "/display")

        # Precondition: the bar starts hidden (script has proven itself live).
        bar = page.locator("[data-dirty-bar]")
        if bar.is_visible():
            raise AssertionError("expected the bar to be hidden before any edit")

        before = str(
            device_config.load_device_config(server.tmpdir)["theme"])
        target = next(r for r in device_config.THEME_IDS if r != before)

        # Change a field: the bar reveals, the count names the section, the field shows the
        # new value, and disk still shows the old value — the bar means unsaved.
        _click_control(page, 'input[name="theme"][value="%s"]' % target)
        _wait_for_bar(page)
        if not _bar_text(page):
            raise AssertionError(
                "expected [data-dirty-count] to name the changed section once the bar "
                "reveals")
        field_now = str(page.eval_on_selector(
            'input[name="theme"]:checked', "el => el.value"))
        if field_now != target:
            raise AssertionError(
                "expected the field's own DOM value to already read %r, got %r"
                % (target, field_now))
        disk_before_save = str(
            device_config.load_device_config(server.tmpdir)["theme"])
        if disk_before_save != before:
            raise AssertionError(
                "expected disk to still read %r while the bar is visible and unsaved, "
                "got %r - the bar means UNSAVED" % (before, disk_before_save))

        # Click Enregistrer: a real navigation.
        _save_via_bar(page)

        # After the navigation: field, bar and disk all agree on the new value.
        _assert_surfaces_agree(
            page,
            {
                "the field's own DOM value": lambda: str(page.eval_on_selector(
                    'input[name="theme"]:checked', "el => el.value")),
                "the value on disk": lambda: str(device_config.load_device_config(
                    server.tmpdir)["theme"]),
            },
            requested=target, before=before,
            where="Display's theme chips after the bar's own save settles")
        if page.locator("[data-dirty-bar]").is_visible():
            raise AssertionError(
                "expected the bar to be HIDDEN after the navigation lands - a bar still "
                "visible after a successful save means the save was never recorded as "
                "settled")
    finally:
        context.close()


def test_a_rejected_value_claims_nothing_the_field_echoes_it_and_disk_is_untouched(
        new_context, server):
    """A value the server's own validation rejects (wake_interval_s below its floor)
    re-renders the same page with the field's own inline error, programmatically associated
    via aria-describedby and naming the field; echoes the user's rejected input back into
    the field rather than the on-disk value; leaves disk unchanged; and raises no
    .quick-toast at all on this path, keeping this failure surface and quick-switch.js's
    own toast from merging.
    """
    context = new_context()
    try:
        page = context.new_page()
        base_url = server.base_url()
        _login(page, base_url)
        page.goto(base_url + "/fleet")

        before = str(device_config.load_device_config(server.tmpdir)["wake_interval_s"])
        # Below server/device_config.py's own WAKE_INTERVAL_MIN_S (60): a genuine server-side
        # rejection, exercising the 200-is-not-a-redirect branch, never a client-side shortcut.
        rejected = "30"

        wake_sel = 'input[name="wake_interval_s"]'
        page.eval_on_selector(wake_sel, "el => el.focus()")
        page.keyboard.press("ControlOrMeta+A")
        page.keyboard.type(rejected)
        page.keyboard.press("Tab")
        _wait_for_bar(page)
        # noValidate disables only the browser's own pre-flight check for this one native
        # submit; the request that follows is still a real native POST, so the server's own
        # validation is exercised.
        page.eval_on_selector(
            "#%s" % config_page.SETTINGS_FORM_ID, "el => { el.noValidate = true; }")
        _save_via_bar(page)

        # 1. THE INLINE ERROR IS PRESENT AND NAMES THE FIELD.
        described_by = page.get_attribute(wake_sel, "aria-describedby") or ""
        if "wake-interval-s-error" not in described_by:
            raise AssertionError(
                "expected %r's own aria-describedby to name its error anchor "
                "(wake-interval-s-error), got %r" % (wake_sel, described_by))
        error_el = page.locator("#wake-interval-s-error")
        if not error_el.count() or not (error_el.inner_text() or "").strip():
            raise AssertionError(
                "expected a non-empty inline error at #wake-interval-s-error")

        # 2. THE USER'S REJECTED INPUT IS ECHOED BACK.
        echoed = page.input_value(wake_sel)
        if echoed != rejected:
            raise AssertionError(
                "expected the field to echo back the user's own rejected input %r, got "
                "%r" % (rejected, echoed))

        # 3. DISK IS UNTOUCHED.
        stored = str(device_config.load_device_config(server.tmpdir)["wake_interval_s"])
        if stored == rejected:
            raise AssertionError(
                "the rejected value %r reached disk - a validation failure must never be "
                "mistaken for a save" % (rejected,))
        if stored != before:
            raise AssertionError(
                "expected the stored wake interval to stay UNCHANGED at %r after a "
                "rejected save, got %r" % (before, stored))

        # 4. THE EXPLICIT NEGATIVE — no .quick-toast on this path at all.
        toast_class = page.eval_on_selector(
            "body", "el => { var t = el.querySelector('[data-quick-toast]'); "
            "return t ? t.className : null; }")
        if toast_class and "is-visible" in toast_class.split():
            raise AssertionError(
                "expected NO .quick-toast on the settings form's own rejected-value path "
                "- announceFailure() is exclusively quick-switch.js's now, got class=%r"
                % (toast_class,))
    finally:
        context.close()


def test_section_naming_reflects_the_fields_actually_changed_in_document_order(
        new_context, server):
    """The bar's own [data-dirty-count] names which section(s) actually changed, built from
    the bar's own data-dirty-* attributes plus each section wrapper's own label, never
    hardcoded English/French: a single changed Frame colours field reads exactly that wrapper's own
    label plus the changed-suffix, run in both site languages. Display now holds one section
    (the schedule is edited in Home's dialog), so the two-item join has no second section here.
    """
    base_url = server.base_url()
    for lang in ("en", "fr"):
        context = new_context()
        try:
            page = context.new_page()
            _login(page, base_url)
            context.add_cookies([{
                "name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": base_url}])
            page.goto(base_url + "/display")

            theme_sel = 'input[name="theme"]'
            current_theme = page.eval_on_selector(
                "%s:checked" % theme_sel, "el => el.value")
            target_theme = next(
                r for r in device_config.THEME_IDS if r != current_theme)

            # Built from the bar's own data-dirty-* words, never a hardcoded English/French
            # literal, so this check works unchanged in either language: one changed area
            # reads the plain "Unsaved changes", whatever its name.
            expected_one = page.eval_on_selector(
                "[data-dirty-bar]",
                "el => el.getAttribute('data-dirty-initial-text')")

            # Phase A: one changed field (the theme). The bar names only it.
            _click_control(
                page, '%s[value="%s"]' % (theme_sel, target_theme))
            _wait_for_bar(page)
            actual_one = _bar_text(page)
            if actual_one != expected_one:
                raise AssertionError(
                    "lang=%s: expected [data-dirty-count] to read %r for a single "
                    "changed field (the theme), got %r" % (lang, expected_one, actual_one))
        finally:
            context.close()


def test_cancel_restores_the_field_and_the_preview_from_the_resulting_dom(
        new_context, server):
    """A real Annuler click restores every surface, read off the resulting DOM: the theme
    chip's checked state is back to the original, the live preview <img>'s resolved src is
    back to the originally-selected theme's own (never the discarded one), proving
    window.SkyPaneLivePreview.refresh() actually ran since form.reset() fires no change
    event. The edit is confirmed to have actually moved the preview before Cancel is ever
    clicked, and every post-Cancel read waits for the deferred tick rather than reading
    synchronously after the click. Asserting that refresh()/repaintAll() was called is
    explicitly not acceptable and this check never does; it observes only the DOM.
    """
    context = new_context()
    try:
        page = context.new_page()
        base_url = server.base_url()
        _login(page, base_url)
        page.goto(base_url + "/display")

        def preview_src():
            return page.eval_on_selector(
                THEME_PREVIEW_SEL, "el => el.getAttribute('src')")

        # Setup: record the pre-edit state of every surface, off the DOM.
        original_theme = page.eval_on_selector(
            'input[name="theme"]:checked', "el => el.value")
        original_preview_src = preview_src()

        target_theme = next(
            t for t in device_config.THEME_IDS if t != original_theme)
        target_preview_src = page.eval_on_selector(
            'input[name="theme"][value="%s"]' % target_theme,
            "el => el.parentNode.getAttribute('data-preview-src')")

        # Edit: a different theme via a look-table radio.
        # Confirm the preview actually moved before Cancel — a no-op edit would make every
        # assertion below vacuous.
        _click_control(
            page, 'input[name="theme"][value="%s"]' % target_theme)
        _wait_for_bar(page)
        page.wait_for_function(
            "args => { var img = document.querySelector(args.sel);"
            " return !!img && img.getAttribute('src') === args.expected; }",
            arg={"sel": THEME_PREVIEW_SEL, "expected": target_preview_src})

        # Cancel: a real click on the native type="reset" button, exercising both the native
        # reset and the scripted enhancement at once.
        page.click("[data-dirty-cancel]")
        _wait_for_bar_hidden(page)

        # The theme radio's checked state is back to the original.
        try:
            page.wait_for_function(
                "args => {"
                " var f = document.querySelector("
                "   'input[name=\"theme\"]:checked');"
                " return !!f && f.value === args.expected; }",
                arg={"expected": original_theme}, timeout=3000)
        except Exception:
            restored_theme = page.eval_on_selector(
                'input[name="theme"]:checked', "el => el.value")
            raise AssertionError(
                "expected the theme radio to be restored to %r after Annuler, got %r"
                % (original_theme, restored_theme))

        # The live preview's <img> resolved src is back to the originally-selected theme's
        # own: the clause that proves window.SkyPaneLivePreview.refresh() actually ran, since
        # form.reset() fires no change event and the preview cannot repaint on its own.
        try:
            page.wait_for_function(
                "args => { var img = document.querySelector(args.sel);"
                " return !!img && img.getAttribute('src') === args.expected; }",
                arg={
                    "sel": THEME_PREVIEW_SEL, "expected": original_preview_src},
                timeout=3000)
        except Exception:
            raise AssertionError(
                "expected the live preview's src to be back to the originally-selected "
                "theme's own %r after Annuler (proving window.SkyPaneLivePreview.refresh() "
                "actually ran), it still reads %r" % (original_preview_src, preview_src()))
    finally:
        context.close()


_SETTINGS_CARD_TITLE_SELECTOR = (
    ".theme-status > h2.text-heading, .page-section > h2.text-heading")


def _settings_card_title_probe(page):
    """Every settings-card title on the currently loaded settings page, addressed by
    structural position — the `<h2>` that is a direct child of a
    `.theme-status`/`.page-section` settings-card wrapper — never by class name. A
    supersection's own intro heading (`.section-intro > h2`) is excluded structurally
    rather than by an explicit `:not()`: it lives under `.section-intro`, never directly
    under `.theme-status`/`.page-section`, so the selector above never reaches it — a
    deliberate exclusion, matching the three-rung heading ladder, not an oversight this
    check should "fix" into asserting the ladder away.
    """
    return page.evaluate(
        "sel => Array.from(document.querySelectorAll(sel)).map(h => {"
        "  var s = getComputedStyle(h);"
        "  return {text: h.textContent, fontSize: s.fontSize,"
        "          fontWeight: s.fontWeight, fontFamily: s.fontFamily,"
        "          underSectionHeading: !!h.closest('.display-appearance')};"
        "})", _SETTINGS_CARD_TITLE_SELECTOR)


def test_a_settings_card_title_renders_identically_on_both_settings_pages(new_context, server):
    """The real proof, not a grep: one probe renders both settings pages (Display and
    Device) in one session, addresses every settings-card title by structural position
    rather than by class name, reads its getComputedStyle font-size/font-weight/font-family,
    and asserts the combined set across both pages has cardinality 1. Fails naming the empty
    side if either page contributes zero titles; every Device title must be one of the two
    named cards; the failure message names the offending page, the offending title's text and both
    triples. Supersection intro headings (.section-intro > h2) are excluded structurally,
    deliberately: a different, generically-worded tier, not an inconsistency this check
    should assert away. Display's four Personalisation cards are ordinary settings cards and join
    the set. Both themes exercised via
    _set_ui_theme(), at the 360px floor.
    """
    context = new_context(viewport=VIEWPORT_MIN_SUPPORTED)
    try:
        page = context.new_page()
        _login(page, server.base_url())
        base_url = server.base_url()

        # Every (page, theme) combination this app can paint a settings-card title in, all
        # folded into one combined set below.
        entries = []
        nested_titles = []
        by_page = {"/display": [], "/device": []}
        for theme in UI_THEMES_EXPLICIT:
            # Personalisation's cards are on its Special looks and Calendar views.
            for route in ("/display/special-looks", "/display/calendar", "/device"):
                page.goto(base_url + route)
                _set_ui_theme(page, theme)
                key = "/device" if route == "/device" else "/display"
                for title in _settings_card_title_probe(page):
                    if title["underSectionHeading"]:
                        nested_titles.append(title["text"])
                        continue
                    triple = (
                        title["fontSize"], title["fontWeight"], title["fontFamily"])
                    entry = {
                        "page": key, "theme": theme,
                        "text": title["text"], "triple": triple}
                    entries.append(entry)
                    by_page[key].append(entry)

        # Clause (a): both pages have settings-card titles to compare.
        for route, side in by_page.items():
            if not side:
                raise AssertionError(
                    "expected at least one settings-card title on %s, got NONE - a "
                    "comparator with an empty side would pass vacuously" % route)

        # Device must contribute exactly the two NAMED cards.
        allowed_device_texts = {
            config_page.LED_SECTION_HEADING,
            config_page.WAKE_INTERVAL_SECTION_HEADING}
        device_texts = {e["text"] for e in by_page["/device"]}
        unexpected = device_texts - allowed_device_texts
        if unexpected:
            raise AssertionError(
                "expected every Device settings-card title to be one of %r, found "
                "unexpected title(s) %r - a probe addressing titles by class name rather "
                "than structural position would pick up supersection intro headings too, "
                "which is exactly the 27-06-shaped mistake this check exists to avoid"
                % (sorted(allowed_device_texts), sorted(unexpected)))
        # Display contributes exactly the two Personalisation cards, in the same voice (the
        # look views are the picker itself and have no card title).
        display_texts = {e["text"] for e in by_page["/display"]}
        if display_texts != {"Special looks", "Calendar"}:
            raise AssertionError(
                "expected the two Personalisation card titles on its card views, got %r"
                % (sorted(display_texts),))
        if nested_titles:
            raise AssertionError("expected no nested settings card, got %r" % (nested_titles,))

        # The combined set's own cardinality is 1.
        triples = sorted({e["triple"] for e in entries})
        if len(triples) != 1:
            majority = collections.Counter(
                e["triple"] for e in entries).most_common(1)[0][0]
            offender = next(e for e in entries if e["triple"] != majority)
            # The message names the offending page, the offending title's text, and both
            # triples.
            raise AssertionError(
                "expected exactly one (font-size, font-weight, font-family) triple across "
                "every settings-card title on both settings pages, got %d distinct triples "
                "- %r on %s (theme=%s) renders %r, while the rest render %r"
                % (len(triples), offender["text"], offender["page"], offender["theme"],
                   offender["triple"], majority))
    finally:
        context.close()


# The single-affordance audit, and the theme radios' cross-tree form= regression check.

def _submit_shaped_controls(page):
    return page.evaluate(
        "() => {"
        " var sel = 'input[type=\"submit\"], button[type=\"submit\"], "
        "button:not([type])';"
        " var els = Array.prototype.slice.call(document.querySelectorAll(sel));"
        " return els.map(function (el) {"
        "   var text = (el.textContent || el.value || '').trim().slice(0, 60);"
        "   return {"
        "     tag: el.tagName.toLowerCase(),"
        "     type: el.getAttribute('type') || '(default submit)',"
        "     formId: el.form ? el.form.id : null,"
        "     text: text,"
        "     fallback: el.hasAttribute('%s'),"
        "     inBar: !!el.closest('[data-dirty-bar]')"
        "   };"
        " });"
        "}" % config_page.STATIC_SAVE_FALLBACK_ATTR)


def test_exactly_one_submit_shaped_control_resolves_to_the_settings_form(new_context, server):
    """Exactly one submit-shaped control on the whole settings page resolves its own .form.id
    to config_page.SETTINGS_FORM_ID, on both /display and /device, in both site languages,
    resolved via the browser's own .form property, never a count of <button occurrences in
    the HTML string and never a hand-maintained allow-list. Covers input[type=submit],
    button[type=submit] and a bare <button> with no type attribute (the HTML default is
    submit); the bar's native type="reset" Cancel is deliberately excluded (form-associated
    but not submit-shaped, and it saves nothing). The one settings-form control must carry
    data-static-save-fallback and be a descendant of [data-dirty-bar]; the failure message
    names every collected control as a tagName/type/form-id/text tuple so a regression says
    which control drifted; and the complement is asserted too: every other submit-shaped
    control this scope renders resolves to a non-settings-form id.
    """
    base_url = server.base_url()
    for scope_route in ("/display", "/device"):
        for lang in ("en", "fr"):
            context = new_context()
            try:
                page = context.new_page()
                _login(page, base_url)
                context.add_cookies([{
                    "name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": base_url}])
                page.goto(base_url + scope_route)

                controls = _submit_shaped_controls(page)
                settings_controls = [
                    c for c in controls
                    if c["formId"] == config_page.SETTINGS_FORM_ID]

                if len(controls) < 2:
                    raise AssertionError(
                        "%s lang=%s: expected MORE than one submit-shaped control on the "
                        "page (the bar's own Save plus at least one other form's own "
                        "submit control), found only %r - with only one candidate ever "
                        "considered the exactly-one assertion below would be vacuous"
                        % (scope_route, lang, controls))

                if len(settings_controls) != 1:
                    offenders = "; ".join(
                        "%s[type=%s] form=%r text=%r"
                        % (c["tag"], c["type"], c["formId"], c["text"])
                        for c in controls)
                    raise AssertionError(
                        "%s lang=%s: expected exactly ONE submit-shaped control whose own "
                        ".form.id resolves to %r, got %d - every collected submit-shaped "
                        "control on this page: %s"
                        % (scope_route, lang, config_page.SETTINGS_FORM_ID,
                           len(settings_controls), offenders))

                the_one = settings_controls[0]
                if not the_one["fallback"]:
                    raise AssertionError(
                        "%s lang=%s: the one settings-form submit control does not carry "
                        "%s - %r"
                        % (scope_route, lang, config_page.STATIC_SAVE_FALLBACK_ATTR, the_one))
                if not the_one["inBar"]:
                    raise AssertionError(
                        "%s lang=%s: the one settings-form submit control is not a "
                        "descendant of [data-dirty-bar] - %r" % (scope_route, lang, the_one))

                # The complement, the relationship half, not merely the endpoint: every other
                # submit-shaped control this scope renders resolves to a form id that is not
                # the settings form.
                bad = [
                    c for c in controls
                    if c is not the_one
                    and c["formId"] == config_page.SETTINGS_FORM_ID]
                if bad:
                    raise AssertionError(
                        "%s lang=%s: expected every OTHER submit-shaped control to "
                        "resolve to a NON-settings-form id, found a second one pointed at "
                        "settings-form: %r" % (scope_route, lang, bad))
            finally:
                context.close()


def test_a_form_associated_radio_path_reaches_the_bar_and_disk_end_to_end(
        new_context, make_app_server):
    """The theme radios' cross-tree form="settings-form" wiring drives the same
    bar-appears -> Enregistrer -> persisted-to-disk path every natively-nested control
    does, against the real POST: selecting a theme radio (rendered outside the settings
    form) reveals the bar naming exactly its own section label, a real Enregistrer
    navigation writes theme to disk, and a reload shows the radio reflecting the
    saved value — both site languages.
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
            page.goto(base_url + "/display")

            # 1. Fresh load: script has run, nothing dirty.
            _wait_for_bar_hidden(page)

            theme_sel = 'input[name="theme"]'
            current_theme = page.eval_on_selector(
                "%s:checked" % theme_sel, "el => el.value")
            target_theme = next(
                r for r in device_config.THEME_IDS if r != current_theme)

            expected = page.eval_on_selector(
                "[data-dirty-bar]",
                "el => el.getAttribute('data-dirty-initial-text')")

            # 2. Select a theme radio whose value differs from disk, via
            #    a real element.click().
            _click_control(
                page, '%s[value="%s"]' % (theme_sel, target_theme))

            # 3. The bar becomes visible AND names EXACTLY the theme section.
            _wait_for_bar(page)
            actual = _bar_text(page)
            if actual != expected:
                raise AssertionError(
                    "lang=%s: expected [data-dirty-count] to read %r after selecting a "
                    "cross-tree form=-associated theme radio, got %r - the "
                    "section-naming walk must resolve this control's own "
                    "[data-dirty-section] ancestor even though the radio is not a "
                    "literal descendant of <form id=\"settings-form\">"
                    % (lang, expected, actual))

            # 4. Click Enregistrer, wait for the REAL navigation.
            _save_via_bar(page)

            # 5. Re-read theme OFF DISK.
            saved = device_config.load_device_config(server.tmpdir)["theme"]
            if saved != target_theme:
                raise AssertionError(
                    "lang=%s: expected theme on disk to be %r after a real "
                    "Enregistrer navigation through the theme radios' own cross-tree form= "
                    "path, got %r" % (lang, target_theme, saved))

            # Reload: the round trip, not just the write.
            page.goto(base_url + "/display")
            checked = page.eval_on_selector(
                "%s:checked" % theme_sel, "el => el.value")
            if checked != target_theme:
                raise AssertionError(
                    "lang=%s: expected the reloaded page's checked theme radio to be "
                    "%r, got %r" % (lang, target_theme, checked))
        finally:
            context.close()


# The artwork drop zone.
#
# Each check below gets its own state (see the fixtures above): the needs-artwork manual
# entry is a precondition none of them may leave altered for a sibling, so each test
# builds/tears down its own server and its own tmp_path fixture files.

def test_artwork_uploads_and_is_served_with_scripts_blocked(new_context, make_app_server, tmp_path):
    """With scripts blocked at 360px, an artwork file chosen through the native <input
    type="file"> and submitted through the fallback panel's own form is stored (read back
    off the real state directory, never off the page — a rejected upload redirects to a
    page that looks like success) and served back by the illustration route as an image at
    illustration_normalize.ILLUSTRATION_TARGET_SIZE; and the drop zone beside it measures
    zero height and holds zero focusable descendants with scripts blocked while occupying a
    real box with them on.
    """
    server = make_app_server(seed=_seed_with_needs_artwork_entry, fake_providers=True)
    fixtures = _write_artwork_fixtures(tmp_path)
    base_url = server.base_url()

    def unhide_fallback(page):
        # `?resolve=` deep-links auto-open the dialog and panel-lookup.js
        # hides the in-page fallback copy as a duplicate sitting behind
        # the backdrop — un-hide it so both directions of the gate
        # measure the SAME element.
        page.evaluate(
            "() => { const f = document.querySelector('[data-resolve-fallback]'); "
            "if (f) f.hidden = false; }")

    gate = _assert_js_gate(
        new_context, base_url, ARTWORK_ROUTE, FALLBACK_ZONE,
        viewport=VIEWPORT_MIN_SUPPORTED, prepare=unhide_fallback)
    if gate["blocked"]["candidates"] != 0:
        raise AssertionError(
            "the drop zone holds %d focusable descendant(s) - it is a hint, a preview "
            "and a message, and nothing in it should be reachable at all"
            % gate["blocked"]["candidates"])

    before = _stored_artwork(server)
    if before is not None:
        raise AssertionError(
            "the fixture already has stored artwork for %r, so an upload could not be "
            "told from the state before it" % ARTWORK_KEY)
    seen = _upload_without_js(
        new_context, base_url, ARTWORK_ROUTE,
        "#%s" % airlines_page.MANUAL_UPLOAD_INPUT_ID,
        "#%s button[type=\"submit\"]" % airlines_page.MANUAL_UPLOAD_FORM_ID,
        fixtures["art_path"], lambda: _stored_artwork(server), ARTWORK_SERVE,
        viewport=VIEWPORT_MIN_SUPPORTED)
    # "Stored and served" is two claims. The second one is what a visitor
    # sees, so it is measured as an IMAGE rather than as 200 plus a byte
    # count: the route normalises on the way out.
    served = Image.open(io.BytesIO(seen["served"]))
    if served.size != illustration_normalize.ILLUSTRATION_TARGET_SIZE:
        raise AssertionError(
            "%s serves a %r image after a scripts-blocked upload, but "
            "companion/illustration_normalize.py's frame is %r - the route is not the "
            "normaliser's output"
            % (ARTWORK_SERVE, served.size, illustration_normalize.ILLUSTRATION_TARGET_SIZE))
    _ = (seen["stored_len"], gate)


def test_dropped_and_picked_files_are_stored_identically(new_context, make_app_server, tmp_path):
    """The same source file stored byte-identically whether it was picked or dropped (with
    the stored file deleted between the two uploads, so a drop that never reached the server
    could not pass on the picked file left behind), the preview decoding to the source's own
    1200x300 through a data: URL (a blob: one is blocked by this app's own CSP); and the
    floor measured against the input rather than against a message: zero files, a wrong
    type, several at once and an oversized file each assign nothing, each say something, and
    each say something different, while a synthetic drop changes nothing at all and the
    drag-over state is sampled visible between dragOver and drop.
    """
    server = make_app_server(seed=_seed_with_needs_artwork_entry, fake_providers=True)
    fixtures = _write_artwork_fixtures(tmp_path)
    art_path = fixtures["art_path"]
    not_png_path = fixtures["not_png_path"]
    oversized_path = fixtures["oversized_path"]
    art_bytes = fixtures["art_bytes"]
    oversized_bytes = fixtures["oversized_bytes"]
    base_url = server.base_url()

    context = new_context(viewport=VIEWPORT_MIN_SUPPORTED)
    try:
        if _stored_artwork(server) is not None:
            raise AssertionError(
                "stored artwork for %r was already on disk when this check started"
                % (ARTWORK_KEY,))
        page = context.new_page()
        _login(page, base_url)
        page.goto(base_url + ARTWORK_ROUTE)
        _await_upload_zone(page, DIALOG_ZONE)
        submit = "#%s button[type=\"submit\"]" % (
            airlines_page.MANUAL_UPLOAD_FORM_ID + "-dialog")

        def upload_current_selection():
            """Submit, then read the stored bytes and put the fixture back
            into its needs-artwork state — required for THIS check's own
            later steps to measure a fresh upload rather than a stale one.
            """
            with page.expect_navigation():
                page.click(submit)
            written = _stored_artwork(server)
            _clear_stored_artwork(server)
            page.goto(base_url + ARTWORK_ROUTE)
            _await_upload_zone(page, DIALOG_ZONE)
            return written

        # THE FIXTURES, PROVED NON-VACUOUS AGAINST THE APP'S OWN NUMBER
        # before anything is dropped.
        cap = int(page.locator(DIALOG_ZONE).get_attribute(
            "data-upload-drop-max-bytes"))
        if oversized_bytes <= cap:
            raise AssertionError(
                "the oversized fixture is %d bytes and the app's own cap is %d - the "
                "oversized case would be measuring nothing" % (oversized_bytes, cap))
        if art_bytes >= cap:
            raise AssertionError(
                "the valid-artwork fixture is %d bytes, at or over the app's own %d cap "
                "- every acceptance below would be measuring the wrong thing"
                % (art_bytes, cap))

        # --- THE FLOOR, MEASURED BEFORE THE CEILING ---
        floor = {}
        _drop_files(page, DIALOG_ZONE, [])
        floor["zero-files"] = _upload_zone_state(page, DIALOG_ZONE)
        _drop_files(page, DIALOG_ZONE, [not_png_path])
        floor["wrong-type"] = _upload_zone_state(page, DIALOG_ZONE)
        _drop_files(page, DIALOG_ZONE, [art_path, art_path])
        floor["several"] = _upload_zone_state(page, DIALOG_ZONE)
        _drop_files(page, DIALOG_ZONE, [oversized_path])
        floor["oversized"] = _upload_zone_state(page, DIALOG_ZONE)
        for label, state in floor.items():
            if state["files"] != 0:
                raise AssertionError(
                    "a %s drop assigned %d file(s) to the form's input - the refusal "
                    "has to happen BEFORE the assignment or it refuses nothing (%r)"
                    % (label, state["files"], state))
            if not state["message"]:
                raise AssertionError(
                    "a %s drop was refused silently - a drop target that declines "
                    "without saying so is indistinguishable from one that is broken "
                    "(%r)" % (label, state))
            if not state["imageHidden"]:
                raise AssertionError(
                    "a %s drop still rendered a preview (%r)" % (label, state))
            if state["imageScheme"] != "":
                raise AssertionError(
                    "after a %s drop the preview <img> still holds a %r src - hidden "
                    "is not released, and the whole decoded file stays in the "
                    "document (%r)" % (label, state["imageScheme"], state))
        if floor["oversized"]["message"] == floor["wrong-type"]["message"]:
            raise AssertionError(
                "the oversized drop and the wrong-type drop say the same thing (%r) - "
                "the visitor cannot tell which rule they hit"
                % (floor["oversized"]["message"],))
        if floor["several"]["message"] == floor["wrong-type"]["message"]:
            raise AssertionError(
                "a several-files drop and a wrong-type drop say the same thing (%r)"
                % (floor["several"]["message"],))

        # REPLACING A PREVIEW AND THEN BEING REFUSED.
        _drop_files(page, DIALOG_ZONE, [art_path])
        page.wait_for_function(
            "sel => { const im = document.querySelector(sel)"
            ".querySelector('.upload-drop__image');"
            " return !im.hidden && !!im.getAttribute('src'); }",
            arg=DIALOG_ZONE, timeout=5000)
        shown = _upload_zone_state(page, DIALOG_ZONE)
        _drop_files(page, DIALOG_ZONE, [not_png_path])
        after = _upload_zone_state(page, DIALOG_ZONE)
        if after["imageScheme"] != "":
            raise AssertionError(
                "a refused drop left the previous preview's %r src on the <img> (%r) "
                "- the decoded file stays in the document for as long as the page does"
                % (after["imageScheme"], after))
        if after["files"] != 1 or after["size"] != shown["size"]:
            raise AssertionError(
                "a refused drop discarded the file the visitor had already chosen "
                "(%r was holding %r, now %r) - declining to perform its own act is "
                "the script doing nothing; removing somebody else's choice is the "
                "script doing harm" % (shown["name"], shown["size"], after))
        page.goto(base_url + ARTWORK_ROUTE)
        _await_upload_zone(page, DIALOG_ZONE)

        # --- THE EQUIVALENCE, WHICH IS THE WHOLE POINT ---
        _clear_stored_artwork(server)
        page.set_input_files(
            "#%s" % (airlines_page.MANUAL_UPLOAD_INPUT_ID + "-dialog"), art_path)
        page.wait_for_function(
            "sel => { const im = document.querySelector(sel)"
            ".querySelector('.upload-drop__image');"
            " return !im.hidden && !!im.getAttribute('src'); }",
            arg=DIALOG_ZONE, timeout=5000)
        picked_state = _upload_zone_state(page, DIALOG_ZONE)
        picked_bytes = upload_current_selection()
        if picked_bytes is None:
            raise AssertionError(
                "picking the file and submitting stored nothing - before comparing "
                "two paths, one of them has to work")
        if _stored_artwork(server) is not None:
            raise AssertionError("could not clear the stored artwork between uploads")
        dragged = _drop_files(page, DIALOG_ZONE, [art_path])
        page.wait_for_function(
            "sel => { const im = document.querySelector(sel)"
            ".querySelector('.upload-drop__image');"
            " return !im.hidden && !!im.getAttribute('src'); }",
            arg=DIALOG_ZONE, timeout=5000)
        dropped_state = _upload_zone_state(page, DIALOG_ZONE)
        if dropped_state["files"] != 1:
            raise AssertionError(
                "a trusted drop of a valid PNG assigned %d file(s) (%r)"
                % (dropped_state["files"], dropped_state))
        dropped_bytes = upload_current_selection()
        if dropped_bytes is None:
            raise AssertionError(
                "dropping the same file and submitting stored NOTHING, while picking "
                "it stored %d bytes - the drop path does not reach the server the "
                "picked file reaches" % (len(picked_bytes),))
        if dropped_bytes != picked_bytes:
            raise AssertionError(
                "the SAME source file stored %d bytes when picked and %d when "
                "dropped - a second transform crept into the drop path, which is "
                "exactly the drift no client-side crop was written to avoid"
                % (len(picked_bytes), len(dropped_bytes)))
        if picked_state["size"] != dropped_state["size"]:
            raise AssertionError(
                "the picked file measured %r bytes in the input and the dropped one "
                "%r - the script altered the file on the way in"
                % (picked_state["size"], dropped_state["size"]))
        if dropped_state["imageScheme"] != "data":
            raise AssertionError(
                "the preview's src scheme is %r - this app's own "
                "Content-Security-Policy is img-src 'self' data:, under which a blob: "
                "preview is blocked outright" % (dropped_state["imageScheme"],))
        if dropped_state["natural"] != [1200, 300]:
            raise AssertionError(
                "the preview decoded to %r, not the source file's own 1200x300 - the "
                "preview is the file, not a redrawing of it" % (dropped_state["natural"],))

        # A SYNTHETIC drop, the one a page script can construct, must
        # change nothing.
        _clear_stored_artwork(server)
        page.evaluate(
            "sel => { const z = document.querySelector(sel);"
            "  const dt = new DataTransfer();"
            "  const ev = new DragEvent('drop',"
            "    {bubbles: true, cancelable: true, dataTransfer: dt});"
            "  z.dispatchEvent(ev); }", DIALOG_ZONE)
        synthetic = _upload_zone_state(page, DIALOG_ZONE)
        if synthetic["message"]:
            raise AssertionError(
                "a synthetic (isTrusted: false) drop reached the handler and "
                "produced %r - the only way into it should be a gesture a person "
                "performed" % (synthetic["message"],))

        # And the drag state was really on, DURING the drag, and really
        # off after it.
        if not dragged["active_during_drag"]:
            raise AssertionError(
                "the drag-over state never appeared while the browser was in a drag "
                "- sampled between dragOver and drop, %r" % (dragged,))
        if dragged["active_after_drop"]:
            raise AssertionError(
                "the drag-over state survived the drop (%r)" % (dragged,))
        if dragged["paint_during_drag"] == dragged["paint_at_rest"]:
            raise AssertionError(
                "the zone paints identically at rest and mid-drag (%r) - the state "
                "is set but invisible, which is the same as not having one"
                % (dragged["paint_at_rest"],))
    finally:
        _clear_stored_artwork(server)
        context.close()


def test_the_artwork_drop_zone_meets_its_floors_at_360px_in_both_themes(
        new_context, artwork_server):
    """The artwork drop zone clears the 44px target by real hit-testing in its own
    container at 360px, the Airlines page does not scroll sideways there, the preview box
    reserves illustration_normalize.py's own aspect ratio (by getBoundingClientRect, never
    clientWidth) before any image exists with the <img> still hidden, and the paint is a
    floor not a ceiling: the hint text is never the canvas colour, the preview frame is
    never its own fill, and the whole zone paints differently in the two themes.
    """
    base_url = artwork_server.base_url()
    context = new_context(viewport=VIEWPORT_MIN_SUPPORTED)
    try:
        page = context.new_page()
        _login(page, base_url)
        page.goto(base_url + ARTWORK_ROUTE)
        _await_upload_zone(page, DIALOG_ZONE)

        hit = _assert_hit_target(
            page, DIALOG_ZONE, "the artwork drop zone on Airlines at 360px")
        msg = _assert_no_page_overflow(
            page, "the artwork drop zone on Airlines", VIEWPORT_MIN_SUPPORTED["width"])
        if msg:
            raise AssertionError(msg)

        # THE RESERVED BOX, before any image exists — a ratio, not a size.
        at_rest = _upload_zone_state(page, DIALOG_ZONE)
        want = (illustration_normalize.ILLUSTRATION_TARGET_WIDTH
                / illustration_normalize.ILLUSTRATION_TARGET_HEIGHT)
        got = at_rest["preview"][0] / at_rest["preview"][1]
        if abs(got - want) > 0.02:
            raise AssertionError(
                "the preview box reserves %.4f:1 (%r) before any image exists, but "
                "illustration_normalize.py's frame is %.4f:1 - a box reserved at the "
                "wrong shape still makes the card jump" % (got, at_rest["preview"], want))
        if not at_rest["imageHidden"]:
            raise AssertionError(
                "the preview <img> is showing before a file was chosen (%r)" % (at_rest,))

        painted = []
        for measured in _in_both_themes(page):
            paint = page.evaluate(
                "sel => { const z = document.querySelector(sel);"
                "  const n = z.querySelector('.upload-drop__note');"
                "  const p = z.querySelector('.upload-drop__preview');"
                "  return {note: getComputedStyle(n).color,"
                "          frame: getComputedStyle(p).borderTopColor,"
                "          surface: getComputedStyle(p).backgroundColor}; }",
                DIALOG_ZONE)
            if paint["note"] == measured["canvas"]:
                raise AssertionError(
                    "%s: the drop zone's hint text is the canvas colour (%r) - an "
                    "invisible instruction is no instruction" % (measured["theme"], paint["note"]))
            if paint["frame"] == paint["surface"]:
                raise AssertionError(
                    "%s: the preview frame (%r) is its own fill, so the reserved box "
                    "has no visible edge before an image arrives"
                    % (measured["theme"], paint["frame"]))
            painted.append((measured["theme"], paint))
        if painted[0][1] == painted[1][1]:
            raise AssertionError(
                "the drop zone paints identically in both themes (%r) - one of them "
                "is not reading the theme's tokens" % (painted[0][1],))
        _ = hit
    finally:
        context.close()


# The artwork drop zone's own keyboard-only recipe, previously
# unmeasured: `_operate_with_keyboard()` cannot drive a native
# `<input type="file">` (its picker is an OS surface it never touches),
# so this measures the real recipe instead — Tab alone to the input, a
# key press inside expect_file_chooser() to open the platform picker,
# Enter on the focused submit button to send it — with the pointer
# recorder armed for the whole sequence.
_MAX_TAB_PRESSES = 200


def _tab_until_focused(page, selector, theme, after_what):
    """Presses Tab, never anything else, up to `_MAX_TAB_PRESSES` times,
    until `document.activeElement` is the element `selector` matches.
    Raises, naming the last focused element, rather than looping forever.
    """
    is_focused = "sel => document.activeElement === document.querySelector(sel)"
    for _ in range(_MAX_TAB_PRESSES):
        if page.evaluate(is_focused, selector):
            return
        page.keyboard.press("Tab")
    last = page.evaluate(
        "() => { const a = document.activeElement;"
        " return a ? (a.id || a.tagName) : null; }")
    raise AssertionError(
        "theme=%s: Tab alone never reached %r within %d presses %s - the last "
        "focused element was %r"
        % (theme, selector, _MAX_TAB_PRESSES, after_what, last))


# Under the full suite's own concurrency, "Space" opening the platform file
# chooser can arrive after a long single wait would already have given up
# (measured: reliable in isolation, occasionally >10s under full-suite
# load) — so this retries a few short waits with a fresh "Space" press each
# time rather than one long one, still keyboard-only throughout.
_FILE_CHOOSER_ATTEMPTS = 3
_FILE_CHOOSER_ATTEMPT_TIMEOUT_MS = 10_000


def _open_file_chooser_with_space(page):
    from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

    last_error = None
    for _ in range(_FILE_CHOOSER_ATTEMPTS):
        try:
            with page.expect_file_chooser(
                    timeout=_FILE_CHOOSER_ATTEMPT_TIMEOUT_MS) as chooser_info:
                page.keyboard.press("Space")
            return chooser_info.value
        except PlaywrightTimeoutError as exc:
            last_error = exc
    raise AssertionError(
        "pressing Space never opened the platform file chooser within %d "
        "attempts of %dms each: %s"
        % (_FILE_CHOOSER_ATTEMPTS, _FILE_CHOOSER_ATTEMPT_TIMEOUT_MS, last_error))


@pytest.mark.parametrize("theme", UI_THEMES_EXPLICIT)
def test_the_artwork_drop_zone_is_operable_from_the_keyboard_alone(
        new_context, make_app_server, tmp_path, theme):
    """The artwork drop zone's previously-unmeasured keyboard clause: at
    360px, scripts enabled, in each explicit theme, with the pointer
    recorder armed before the first key press, pressing Tab alone from
    the top of the freshly-loaded document reaches the drop zone's own
    native `<input type="file">` (never `.click()`, never `.focus()` —
    focus moves only through `page.keyboard.press("Tab")`).

    "Enter" was tried first inside `page.expect_file_chooser()`;
    measured against this repo's real Chromium
    (`--only-shell-installed`) over 8 full runs it opened the platform
    chooser only 3/8 times, so this test uses the documented fallback
    instead: "Space" opens it 12/12 across the same measurement in
    isolation. Under the full suite's parallel load the same interception
    can still arrive a little late, so a short-timeout attempt retries
    once with a fresh "Space" press rather than waiting out one long
    timeout — still keyboard-only, still zero pointer events. The
    chosen file is then submitted by pressing "Enter"
    on the submit button (a real `<button>`, where Enter's default
    action is unambiguous), reached the same Tab-only way. Zero pointer
    events fire across the whole sequence, and the uploaded file lands
    on disk, read back through `illustrations.override_path_for_key()`
    the same way `test_dropped_and_picked_files_are_stored_identically()`
    does, and decodes to the source fixture's own 1200x300.
    """
    server = make_app_server(seed=_seed_with_needs_artwork_entry, fake_providers=True)
    fixtures = _write_artwork_fixtures(tmp_path)
    base_url = server.base_url()

    context = new_context(viewport=VIEWPORT_MIN_SUPPORTED)
    try:
        if _stored_artwork(server) is not None:
            raise AssertionError(
                "stored artwork for %r was already on disk when this check started"
                % (ARTWORK_KEY,))

        page = context.new_page()
        _login(page, base_url)
        page.goto(base_url + ARTWORK_ROUTE)
        _await_upload_zone(page, DIALOG_ZONE)
        _set_ui_theme(page, theme)

        input_sel = "#%s" % (airlines_page.MANUAL_UPLOAD_INPUT_ID + "-dialog")
        submit_sel = "#%s button[type=\"submit\"]" % (
            airlines_page.MANUAL_UPLOAD_FORM_ID + "-dialog")

        # Armed before the very first Tab press, so "zero pointer events"
        # is a measurement of the entire sequence below, not just its tail.
        page.evaluate(_POINTER_RECORDER_ARM)

        _tab_until_focused(page, input_sel, theme, "from the top of the document")

        chooser = _open_file_chooser_with_space(page)
        chooser.set_files(fixtures["art_path"])
        page.wait_for_function(
            "sel => { const i = document.querySelector(sel);"
            " return !!(i.files && i.files.length); }",
            arg=input_sel, timeout=5000)

        _tab_until_focused(page, submit_sel, theme, "after choosing a file")

        with page.expect_navigation():
            page.keyboard.press("Enter")

        fired = page.evaluate(_POINTER_RECORDER_READ)
        if fired:
            raise AssertionError(
                "theme=%s: the keyboard-only upload sequence fired %d pointer "
                "event(s) - %r. A keyboard proof that a pointer took part proves "
                "nothing about a keyboard-only visitor" % (theme, len(fired), fired))

        stored = _stored_artwork(server)
        if stored is None:
            raise AssertionError(
                "theme=%s: the keyboard-only upload sequence stored nothing - the "
                "browser navigated to %r, which is exactly what a REJECTED upload "
                "looks like from outside" % (theme, page.url))
        decoded = Image.open(io.BytesIO(stored))
        if decoded.size != (1200, 300):
            raise AssertionError(
                "theme=%s: the stored file decodes to %r, not the source fixture's "
                "own 1200x300 - the keyboard path reached a different file, or a "
                "second transform crept in" % (theme, decoded.size))
    finally:
        _clear_stored_artwork(server)
        context.close()


# Airlines: the aircraft types of a row, behind its chevron.

TYPES_CARD = "Transavia France"
TYPES_GROUP = 'tbody.airline-group:has(input[value="%s"])' % TYPES_CARD


def test_a_row_expands_to_its_types_and_each_type_has_its_own_replace(new_context, server):
    """At 1280, 390 and 360 px in English and French, a two-type airline is one row whose
    chevron expands one sub-row per aircraft type (the A320, never "Any aircraft"/"Tout
    appareil"), the sub-row's artwork uploads to that type's own address, the chevron and the
    artwork are 44px targets and nothing overflows horizontally."""
    for lang, forbidden in (("en", "Any aircraft"), ("fr", "Tout appareil")):
        for viewport in (VIEWPORT_DESKTOP, VIEWPORT_PHONE, VIEWPORT_MIN_SUPPORTED):
            where = "%s at %dpx" % (lang, viewport["width"])
            context = new_context(viewport=viewport)
            try:
                context.add_cookies([{
                    "name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": server.base_url()}])
                page = context.new_page()
                _login(page, server.base_url())
                page.goto(server.base_url() + "/airlines/manage")
                chevron = TYPES_GROUP + " .airlines-expand > summary"
                page.locator(chevron).wait_for(state="visible")
                page.wait_for_function("() => document.readyState === 'complete'", timeout=10000)
                if forbidden in page.content():
                    raise AssertionError("%r is back on the page (%s)" % (forbidden, where))
                _assert_hit_target(page, chevron, "chevron " + where)
                page.locator(chevron).click()
                subrow = page.locator(TYPES_GROUP + " .airlines-subrow")
                subrow.first.wait_for(state="visible")
                if subrow.all_inner_texts() == [] or not subrow.first.locator("th").inner_text().startswith("A320"):
                    raise AssertionError("unexpected types %r (%s)" % (subrow.all_inner_texts(), where))
                action = subrow.first.locator("form.airlines-art").get_attribute("action")
                if action != "/illustration/transavia-france-a320.png":
                    raise AssertionError("the A320 row targets %r (%s)" % (action, where))
                _assert_hit_target(page, TYPES_GROUP + " .airlines-subrow .airlines-thumb",
                                   "sub-row artwork " + where)
                problem = _assert_no_page_overflow(page, "airlines " + where)
                if problem:
                    raise AssertionError(problem)
            finally:
                context.close()


def test_every_type_stays_listed_and_reachable_without_scripts(new_context, server):
    """With scripts blocked the chevron still expands a multi-type row to its types as text,
    a single-type airline expands to its one seen type (editable, following the airline's artwork), all inside the narrowest supported viewport without
    overflow."""
    with _no_js_page(new_context, server.base_url(), "/airlines/manage",
                     viewport=VIEWPORT_MIN_SUPPORTED, reduced_motion="reduce") as page:
        with page.expect_navigation():
            page.get_by_role("link", name="Show the aircraft types of every airline").click()
        chevron = TYPES_GROUP + " .airlines-expand > summary"
        page.locator(chevron).wait_for(state="visible")
        page.locator(chevron).click()
        page.locator(TYPES_GROUP + " .airlines-subrow").first.wait_for(state="visible")
        if not page.locator(TYPES_GROUP + " .airlines-subrow th").first.inner_text().startswith("A320"):
            raise AssertionError("expected the Transavia A320 as text")
        single = page.locator('tbody.airline-group:has(input[value="Air France"])')
        single.locator(".airlines-expand > summary").click()
        row = single.locator(".airlines-subrow")
        row.first.wait_for(state="visible")
        if row.count() != 1 or "Same as the airline" not in row.first.inner_text() or (
                row.first.locator(".row-menu__toggle").count() != 1):
            raise AssertionError("expected one seen type, editable, following the airline's "
                                 "artwork, got %r" % row.all_inner_texts())
        problem = _assert_no_page_overflow(page, "airlines without scripts")
        if problem:
            raise AssertionError(problem)


def test_deleting_a_manual_name_states_its_outcome_and_removes_the_entry(
        new_context, make_app_server):
    """The delete control of a hand-named airline says what it does (flights become
    unidentified again, artwork stays), and submitting it removes the manual entry on disk and
    returns to the gallery."""
    server = make_app_server(seed=_seed_with_needs_artwork_entry, fake_providers=True)
    context = new_context(viewport=VIEWPORT_PHONE)
    try:
        page = context.new_page()
        _login(page, server.base_url())
        page.goto(server.base_url() + "/airlines/manage")
        page.locator('a.airlines-thumb[data-view-panel-resolve-prefix="%s"]'
                     % ARTWORK_PREFIX).click()
        dialog = page.locator("#panel-lookup-dialog")
        delete_form = dialog.locator("form.lightbox__delete")
        delete_form.wait_for(state="visible")
        if "become unidentified again" not in delete_form.text_content():
            raise AssertionError("delete form does not state its outcome: %r"
                                 % delete_form.text_content())
        button = delete_form.locator("button")
        if button.text_content().strip() != "Delete my name":
            raise AssertionError("unexpected delete button: %r" % button.text_content())
        with page.expect_navigation():
            button.click()
        if manual_resolutions.load_manual_resolutions(server.tmpdir).get(ARTWORK_PREFIX):
            raise AssertionError("the manual entry was not removed")
        if not page.url.rstrip("/").endswith("/airlines/manage"):
            raise AssertionError("expected to land on the gallery, got %r" % page.url)
    finally:
        context.close()
