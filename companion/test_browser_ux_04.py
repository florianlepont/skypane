#!/usr/bin/env python3
"""Part 04 of `companion/test_browser_ux.py` (33-24-PLAN.md, TST-11), the
FOURTH AND FINAL plan of the browser_ux chain (33-21..33-24). This plan's
own second task deletes `companion/test_browser_ux.py` outright, closing the
chain: after this module lands, no browser check anywhere is monolithic.

Covers the original file's check() calls #63-#75 (its last 13): the
scripts-blocked accordion's own operability/save floor, the Touch Targets
measurement sweep over the palette/usage-row/rule-add controls, the no-JS
floor's own save-to-disk proof after the `.js`-gate simplification, the
restored dirty bar's settle contract, a server-side validation rejection's
inline-error/echo/no-toast floor, the bar's own document-order section
naming, a real Annuler click's restore-every-surface proof, the settings-
card-title consistency probe (CFG-72), the single-submit-affordance audit
(CFG-78), the runway radios' cross-tree `form="settings-form"` regression
check, and the artwork drop zone's own upload/equivalence/geometry family
(CFG-51/D19).

Every test below drives a real headless Chromium against a real
`companion/app.py` subprocess, through the guarded `page`/`new_context`
fixtures (`companion/conftest.py`), and never constructs or navigates to any
URL outside `server.base_url()` — a `127.0.0.1:<ephemeral-port>` origin the
guarded fixture itself created. A missing/unlaunchable Chromium is a hard
failure under CI / `SKYPANE_REQUIRE_BROWSER=1` (the `browser` fixture
override in `companion/conftest.py`), never a silent skip.

Read-only checks (no test below persists a real setting through the bar or
the fallback Save) share one module-scoped, read-only `server` fixture
(33-MIGRATION-RULES.md section 2): the palette Touch Targets sweep, the
rejected-value floor (the rejection never reaches disk), the bar's
document-order section-naming check and the Annuler restore check (both
discard their own edit rather than saving it), the settings-card-title
probe and the single-submit-affordance audit. Every check that DOES persist
a setting — the scripts-blocked accordion save, the no-JS tracked_runway
floor, the bar's own settle-and-hide save, and the runway cross-tree save —
gets its own function-scoped `make_app_server` server. The artwork drop
zone's three checks need a DIFFERENT seed (a `needs-artwork` manual
resolution entry the default fixture never creates): the two that actually
upload a file get their own function-scoped server each; the one that only
measures the zone at rest shares a second, dedicated module-scoped
`artwork_server` fixture.
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
    UI_THEMES_EXPLICIT, VIEWPORT_MIN_SUPPORTED,
    _assert_hit_target, _assert_js_gate, _assert_no_page_overflow,
    _assert_surfaces_agree, _await_upload_zone, _bar_text, _click_control,
    _commit_field, _drop_files, _handle_sel, _in_both_themes, _login,
    _no_js_page, _persist_without_js, _quiet_arc_minutes, _save_via_bar,
    _SUBMIT_PROBE, _set_ui_theme, _upload_without_js, _upload_zone_state,
    _wait_for_bar, _wait_for_bar_hidden, seed_state_dir,
)

pytestmark = pytest.mark.browser

# 30-08-PLAN.md Task 2 (CFG-85): the live preview element (unchanged by
# this phase) — also defined in companion/test_browser_ux_03.py, since that
# part's own checks read it too; kept local to each module rather than
# promoted into the shared helpers file, matching 33-23's own precedent for
# this exact constant.
THEME_PREVIEW_SEL = ".theme-live-preview__image"


@pytest.fixture(scope="module")
def server(module_app_server_factory):
    """The shared, read-only 22-AUDIT.md-methodology fixture every read-only
    check in this module measures against — module-scoped because none of
    them persists a real setting (the two checks that edit a field discard
    it via Annuler or a server-side rejection rather than saving it).
    """
    return module_app_server_factory(seed=seed_state_dir, fake_providers=True)


# ===========================================================================
# 25-07-PLAN.md Task 3 (CFG-51/D19): THE ARTWORK DROP ZONE fixture family.
#
# A manual resolution with NO artwork yet ("needs-artwork") is the one state
# where both the in-page no-JS fallback panel and the dialog's own copy of
# the upload form render at once — the same reason the legacy harness chose
# it. `seed_state_dir()` alone never creates this entry, so this seed layers
# it on top.
# ===========================================================================

ARTWORK_PREFIX = "NEW"
ARTWORK_NAME = "Totally Novel Airline"
ARTWORK_KEY = manual_resolutions.illustration_key_for_name(ARTWORK_NAME)
ARTWORK_ROUTE = "/airlines?resolve=" + ARTWORK_PREFIX
ARTWORK_SERVE = "/illustration/%s.png" % ARTWORK_KEY
FALLBACK_ZONE = "[data-resolve-fallback] [data-upload-drop]"
# 29-01-PLAN.md (CFG-81): the dialog's Replace form renders
# UNCONDITIONALLY, so #panel-lookup-dialog carries BOTH upload-drop zones at
# once — this one (the needs-artwork resolve zone, id_suffix="-dialog") and
# REPLACE_INPUT_ID's own. Disambiguated by the same UPLOAD_DROP_INPUT_ATTR
# value panel-lookup.js itself reads to decide which to hide.
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
    """A second, dedicated module-scoped server seeded with the
    needs-artwork manual entry, for the ONE artwork check that never
    uploads anything (it only measures the zone at rest) — the two that
    actually store a file each get their own function-scoped server
    instead (below).
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
    """The stored override's BYTES, or None. The verdict for every upload
    below, read off the real state directory rather than off the page — a
    POST this app rejected redirects to a page that looks exactly like
    success."""
    path = illustrations.override_path_for_key(ARTWORK_KEY, server.tmpdir)
    if not path or not os.path.isfile(path):
        return None
    with open(path, "rb") as fh:
        return fh.read()


def _clear_stored_artwork(server):
    path = illustrations.override_path_for_key(ARTWORK_KEY, server.tmpdir)
    if path and os.path.isfile(path):
        os.unlink(path)


# ===========================================================================
# 30-08-PLAN.md Task 2 (CFG-85): the accordion's own operability/save floor.
# ===========================================================================

def test_the_accordion_is_operable_and_saves_with_scripts_blocked(new_context, make_app_server):
    """with scripts blocked, in BOTH languages, at 360px: all 4 usage rows carry their own
    <summary>; every registry theme's radio (theme/theme_arriving/calendar_theme_id/
    rule_theme_id) is present in the DOM at full registry size regardless of which row is
    open; a REAL pointer click on a closed row's own <summary> opens it and closes the
    previously-open sibling (the native grouped <details name="aspect-rows"> mechanism); and
    a palette selection made INSIDE the row the visitor just opened themselves reaches disk,
    read back via device_config.load_device_config(), with the restore leg putting the old
    value back - CFG-85's own "every row open" wording is unachievable alongside the
    grouped, mutually-exclusive accordion the developer already approved, and this check's
    own comment states that discrepancy plainly rather than narrowing the claim
    (_ASPECT_REPIN_LEDGER, 30-08-PLAN.md Task 2, CFG-85)"""
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

            rows = page.query_selector_all("details.usage-row")
            if len(rows) != 4:
                raise AssertionError(
                    "lang=%s: expected 4 usage rows, found %d" % (lang, len(rows)))
            for row in rows:
                if row.query_selector("summary") is None:
                    raise AssertionError(
                        "lang=%s: a usage row carries no <summary>" % (lang,))

            for field, expected in (
                    ("theme", n_themes),
                    ("theme_arriving", n_themes + 1),
                    ("calendar_theme_id", n_themes + 1),
                    ("rule_theme_id", n_themes)):
                count = page.eval_on_selector_all(
                    'input[name="%s"]' % field, "els => els.length")
                if count != expected:
                    raise AssertionError(
                        "lang=%s: expected %d radios named %r in the DOM regardless of "
                        "which row is open, found %d" % (lang, expected, field, count))

            calendar_row = page.query_selector(
                'details.usage-row[data-usage="calendar"]')
            departures_row = page.query_selector(
                'details.usage-row[data-usage="departures"]')
            if calendar_row.get_attribute("open") is not None:
                raise AssertionError(
                    "lang=%s: expected the calendar row closed at load" % (lang,))
            if departures_row.get_attribute("open") is None:
                raise AssertionError(
                    "lang=%s: expected the departures row open at load" % (lang,))
            calendar_row.query_selector("summary").click()
            if calendar_row.get_attribute("open") is None:
                raise AssertionError(
                    "lang=%s: a real pointer click on a closed row's own <summary> did "
                    "not open it, with scripts blocked" % (lang,))
            if departures_row.get_attribute("open") is not None:
                raise AssertionError(
                    "lang=%s: opening the calendar row did not close its previously-open "
                    "sibling - the native grouped-<details> behaviour CFG-85's zero-script "
                    "floor rests on" % (lang,))

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
            with page.expect_navigation():
                via = page.evaluate(_SUBMIT_PROBE, {"field": "calendar_theme_id"})

        stored = read_back()
        if str(stored) != str(target):
            raise AssertionError(
                "lang=%s: a selection made inside a row the visitor opened themselves "
                "(via the %s) did NOT reach disk - expected %r, got %r"
                % (lang, via, target, stored))

        device_config.save_device_config(
            server.tmpdir, calendar_theme_id=before if before is not None else "")
        restored = read_back()
        if restored != before:
            raise AssertionError(
                "restoring calendar_theme_id failed: wanted %r, disk reads %r"
                % (before, restored))


def test_the_palette_meets_its_floors_at_360px_in_both_themes(new_context, server):
    """30-UI-SPEC.md's Touch Targets table, MEASURED (never declared) in each control's own
    container, in both UI themes, at the 360px contract floor: the open row's first and last
    .palette-chip, the usage-row's own <summary>, the arrivals row's leading "Same as
    departures" option, and the nested rule-add disclosure's own <summary> all clear 44px;
    the palette grid never scrolls horizontally, the page itself never overflows sideways,
    and the swatch paints visibly distinct from its own surrounding chip surface in both
    themes (_ASPECT_REPIN_LEDGER, 30-08-PLAN.md Task 2, CFG-85)"""
    base_url = server.base_url()
    context = new_context(viewport=VIEWPORT_MIN_SUPPORTED)
    try:
        page = context.new_page()
        _login(page, base_url)
        page.goto(base_url + "/display")

        def open_row(usage):
            # IDEMPOTENT, deliberately: a grouped <details name="aspect-
            # rows"> summary click TOGGLES, so clicking an already-open row
            # would close it rather than leave it open.
            row = page.query_selector(
                'details.usage-row[data-usage="%s"]' % usage)
            if row.get_attribute("open") is None:
                row.query_selector("summary").click()

        recorded = {}
        for theme in UI_THEMES_EXPLICIT:
            _set_ui_theme(page, theme)
            theme_record = {}

            open_row("departures")
            chip_count = page.eval_on_selector_all(
                'details.usage-row[data-usage="departures"] label.palette-chip',
                "els => els.length")
            if chip_count < 2:
                raise AssertionError(
                    "theme=%s: expected at least 2 .palette-chip in the open departures "
                    "row, found %d" % (theme, chip_count))
            theme_record["chip_first"] = _assert_hit_target(
                page,
                'details.usage-row[data-usage="departures"] '
                'label.palette-chip:first-of-type',
                "theme=%s: the FIRST palette-chip in the open departures row" % theme)
            theme_record["chip_last"] = _assert_hit_target(
                page,
                'details.usage-row[data-usage="departures"] '
                'label.palette-chip:last-of-type',
                "theme=%s: the LAST palette-chip in the open departures row" % theme)

            theme_record["row_summary"] = _assert_hit_target(
                page, 'details.usage-row[data-usage="departures"] > summary',
                "theme=%s: the departures row's own <summary>" % theme)

            open_row("arrivals")
            theme_record["leading_option"] = _assert_hit_target(
                page, 'details.usage-row[data-usage="arrivals"] .leading-option',
                "theme=%s: the arrivals row's \"Same as departures\" leading option"
                % theme)

            open_row("rules")
            theme_record["rule_add_summary"] = _assert_hit_target(
                page, ".rule-add > summary",
                "theme=%s: the nested \"+ Add rule\" disclosure's own <summary>" % theme)

            for usage in ("departures", "arrivals"):
                open_row(usage)
                grid = page.eval_on_selector(
                    'details.usage-row[data-usage="%s"] .palette' % usage,
                    "el => ({scrollWidth: el.scrollWidth, clientWidth: el.clientWidth})")
                if grid["scrollWidth"] > grid["clientWidth"]:
                    raise AssertionError(
                        "theme=%s: the %s row's own .palette grid scrolls horizontally - "
                        "scrollWidth %r > clientWidth %r, exactly the strip CFG-85 retires"
                        % (theme, usage, grid["scrollWidth"], grid["clientWidth"]))

            msg = _assert_no_page_overflow(
                page, "the Aspect card on /display (theme=%s)" % theme,
                VIEWPORT_MIN_SUPPORTED["width"])
            if msg:
                raise AssertionError(msg)

            # Deliberately the "black" theme, not the FIRST chip: THEME_IDS[0]
            # is "white" (a solid #FFFFFF fill), and --color-dominant is
            # ALSO #FFFFFF in light mode — a white swatch on a white card
            # surface is a real, correct product fact, never the "invisible
            # swatch" defect this clause exists to catch.
            open_row("departures")
            paint = page.eval_on_selector(
                'details.usage-row[data-usage="departures"] '
                'label.palette-chip:has(input[type=radio][value="black"])',
                "el => { var swatch = el.querySelector('.palette-swatch');"
                " var chip = getComputedStyle(el);"
                " return {swatch: getComputedStyle(swatch).backgroundColor,"
                " chipSurface: chip.backgroundColor}; }")
            if paint["swatch"] == paint["chipSurface"]:
                raise AssertionError(
                    "theme=%s: the 'black' palette-chip's own swatch paints IDENTICALLY "
                    "to its surrounding chip surface (%r) - a swatch invisible against "
                    "its own card is the defect a hit-target measurement cannot see"
                    % (theme, paint["swatch"]))
            theme_record["paint"] = paint
            recorded[theme] = theme_record

        for theme, rec in recorded.items():
            for control in (
                    "chip_first", "chip_last", "row_summary", "leading_option",
                    "rule_add_summary"):
                seen = rec[control]
                print(
                    "        [30-08 T2] theme=%s %s: hit=%r visual=%r"
                    % (theme, control, seen["hit"], seen["visual"]))
    finally:
        context.close()


# ===========================================================================
# 27-03-PLAN.md Task 3 (CFG-64): the no-JS floor under the simplified gate.
# ===========================================================================

def test_the_floor_saves_to_disk_with_scripts_blocked_after_the_gate_simplifies(
        new_context, make_app_server):
    """the no-JS floor still SAVES TO DISK after the gate simplifies to the plain .js rule
    (CFG-64) — tracked_runway operated natively, submitted through the real form, re-read
    FROM DISK after a fresh GET, in BOTH shipped languages, at 360px, restored as the last
    act (the same field and mutation 25-03's own M20 recorded) — and the
    data-static-save-fallback submit is present and VISIBLE on that scripts-blocked page
    AFTER the save, so a rendering can never stand in for it (CFG-64, 27-03-PLAN.md Task 3)"""
    server = make_app_server(seed=seed_state_dir, fake_providers=True)
    base_url = server.base_url()

    def read_back():
        return device_config.load_device_config(server.tmpdir)["tracked_runway"]

    before = read_back()
    target = next(r for r in device_config.RUNWAY_IDS if r != before)
    seen = {}
    # BOTH SHIPPED LANGUAGES, at the 360px floor: the UI language is a
    # cookie the FIRST rendered document already has to honour, and "it
    # saves in English" is not the D-09 floor.
    for lang in ("en", "fr"):
        seen[lang] = _persist_without_js(
            new_context, base_url, "/display", "tracked_runway", target, read_back,
            viewport=VIEWPORT_MIN_SUPPORTED,
            cookies=[{"name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": base_url}])
    after = read_back()
    if str(after) != str(before):
        raise AssertionError(
            "the scripts-blocked save left tracked_runway at %r, it started at %r - a "
            "harness that changes a real setting is a test that edits its neighbours' "
            "subject" % (after, before))
    for lang, result in seen.items():
        if str(result["stored"]) != str(target):
            raise AssertionError(
                "lang=%s: tracked_runway did not reach disk, it reads %r"
                % (lang, result["stored"]))
        if str(result["restored"]) != str(before):
            raise AssertionError(
                "lang=%s: the restore leg did not put %r back, disk reads %r"
                % (lang, before, result["restored"]))

    # AND THE SUBMIT ITSELF, ASSERTED AFTER THE SAVE ABOVE — never before,
    # and never in its place. A rendering can never stand in for the save
    # this check just proved.
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


# ===========================================================================
# 27-04-PLAN.md Task 4 / 28-10-PLAN.md Tasks 2-3 (CFG-63/CFG-71/CFG-77/
# CFG-78): the bar's own settle contract, and its failure proven honest.
# ===========================================================================

def test_the_bar_settles_the_field_disk_agree_and_the_bar_hides(new_context, make_app_server):
    """the bar's own settle contract: changing a field REVEALS the bar, names the changed
    section, updates the field's own DOM value, and leaves DISK UNTOUCHED (the bar means
    unsaved, stronger than anything the retired check asserted); clicking Enregistrer causes
    a real navigation; and after it lands the field, the bar (now HIDDEN) and disk all agree
    on the requested value — three surfaces, on different surfaces than before
    (CFG-63/CFG-71/CFG-77/CFG-78, 27-04-PLAN.md Task 4; retargeted onto the restored bar by
    28-10-PLAN.md Task 2, which also retires the CFG-63 'no save button visible' clause this
    check used to assert)"""
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
            device_config.load_device_config(server.tmpdir)["tracked_runway"])
        target = next(r for r in device_config.RUNWAY_IDS if r != before)

        # a. CHANGE A FIELD: the bar reveals, the count names the section,
        # the field shows the new value, and disk STILL shows the OLD
        # value — the bar means *unsaved*.
        _click_control(page, 'input[name="tracked_runway"][value="%s"]' % target)
        _wait_for_bar(page)
        if not _bar_text(page):
            raise AssertionError(
                "expected [data-dirty-count] to name the changed section once the bar "
                "reveals")
        field_now = str(page.eval_on_selector(
            'input[name="tracked_runway"]:checked', "el => el.value"))
        if field_now != target:
            raise AssertionError(
                "expected the field's own DOM value to already read %r, got %r"
                % (target, field_now))
        disk_before_save = str(
            device_config.load_device_config(server.tmpdir)["tracked_runway"])
        if disk_before_save != before:
            raise AssertionError(
                "expected disk to still read %r while the bar is visible and unsaved, "
                "got %r - the bar means UNSAVED" % (before, disk_before_save))

        # b. CLICK ENREGISTRER — a real navigation.
        _save_via_bar(page)

        # c. AFTER THE NAVIGATION: field, bar and disk all agree on the new
        # value.
        _assert_surfaces_agree(
            page,
            {
                "the field's own DOM value": lambda: str(page.eval_on_selector(
                    'input[name="tracked_runway"]:checked', "el => el.value")),
                "the value on disk": lambda: str(device_config.load_device_config(
                    server.tmpdir)["tracked_runway"]),
            },
            requested=target, before=before,
            where="Display's runway card after the bar's own save settles")
        if page.locator("[data-dirty-bar]").is_visible():
            raise AssertionError(
                "expected the bar to be HIDDEN after the navigation lands - a bar still "
                "visible after a successful save means the save was never recorded as "
                "settled")
    finally:
        context.close()


def test_a_rejected_value_claims_nothing_the_field_echoes_it_and_disk_is_untouched(
        new_context, server):
    """a value the server's own validation rejects (wake_interval_s below its floor)
    re-renders the SAME page with the field's OWN inline error, programmatically associated
    via aria-describedby and naming the field; echoes the user's rejected input back into
    the field rather than the on-disk value (D-07's echo rule); leaves disk UNCHANGED; and
    raises NO .quick-toast at all on this path — the explicit negative that keeps this
    failure surface and quick-switch.js's own toast from merging (CFG-63/CFG-71,
    27-04-PLAN.md Task 4; retargeted from the toast onto the native inline-error path by
    28-10-PLAN.md Task 3, CFG-77/CFG-78)"""
    context = new_context()
    try:
        page = context.new_page()
        base_url = server.base_url()
        _login(page, base_url)
        page.goto(base_url + "/device")

        before = str(device_config.load_device_config(server.tmpdir)["wake_interval_s"])
        # Below server/device_config.py's own WAKE_INTERVAL_MIN_S (60) — a
        # genuine server-side rejection, exercising the 200-is-not-a-
        # redirect branch, never a client-side shortcut.
        rejected = "30"

        wake_sel = 'input[name="wake_interval_s"]'
        page.eval_on_selector(wake_sel, "el => el.focus()")
        page.keyboard.press("ControlOrMeta+A")
        page.keyboard.type(rejected)
        page.keyboard.press("Tab")
        _wait_for_bar(page)
        # noValidate disables only the BROWSER's own pre-flight check for
        # this one native submit — the request that follows is still a
        # REAL native POST, so the server's own validation is exercised.
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


# ===========================================================================
# 28-11-PLAN.md Tasks 1-2 (CFG-77): document-order section naming, and
# Cancel's side effects read off the resulting DOM.
# ===========================================================================

def test_section_naming_reflects_the_fields_actually_changed_in_document_order(
        new_context, server):
    """the bar's own [data-dirty-count] names which section(s) actually changed, built from
    the bar's own data-dirty-* attributes plus each section wrapper's own label — never
    hardcoded English/French, never merely 'the bar is visible' or 'the text is non-empty':
    a single changed Runway field reads exactly that wrapper's own label plus the
    changed-suffix, and a second, different-section change (Quiet hours) reads the two-item
    join with Runway BEFORE Quiet hours in BOTH click orders — the reversed-order pass is
    what proves DOCUMENT order rather than click order, since dirtySectionLabels() walks the
    document and Runway's own wrapper precedes Quiet hours' on Display regardless of which
    the visitor touches first; run in both site languages (CFG-77, 28-11-PLAN.md Task 1)"""
    base_url = server.base_url()
    for lang in ("en", "fr"):
        context = new_context()
        try:
            page = context.new_page()
            _login(page, base_url)
            context.add_cookies([{
                "name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": base_url}])
            page.goto(base_url + "/display")

            def wait_for_bar_text(expected, timeout=5000):
                page.wait_for_function(
                    "args => {"
                    " var el = document.querySelector('[data-dirty-count]');"
                    " return !!el && el.textContent === args.expected;}",
                    arg={"expected": expected}, timeout=timeout)

            runway_sel = 'input[name="tracked_runway"]'
            current_runway = page.eval_on_selector(
                "%s:checked" % runway_sel, "el => el.value")
            target_runway = next(
                r for r in device_config.RUNWAY_IDS if r != current_runway)

            current_quiet_start = page.input_value(
                'input[name="quiet_hours_start"]')
            target_quiet_start = (
                "05:00" if current_quiet_start != "05:00" else "06:00")

            # Built from the bar's OWN data-dirty-* words and each section
            # wrapper's OWN label — never a hardcoded English/French
            # literal, so this check works unchanged in either language.
            runway_label = page.eval_on_selector(
                runway_sel,
                "el => el.closest('[data-dirty-section]')"
                ".getAttribute('data-dirty-section')")
            quiet_label = page.eval_on_selector(
                'input[name="quiet_hours_start"]',
                "el => el.closest('[data-dirty-section]')"
                ".getAttribute('data-dirty-section')")
            changed_suffix = page.eval_on_selector(
                "[data-dirty-bar]",
                "el => el.getAttribute('data-dirty-changed-suffix')")
            and_word = page.eval_on_selector(
                "[data-dirty-bar]", "el => el.getAttribute('data-dirty-and')")

            expected_one = runway_label + changed_suffix
            expected_two = (
                runway_label + and_word + quiet_label + changed_suffix)

            # Phase A: ONE changed field (Runway). The bar names ONLY it.
            _click_control(
                page, '%s[value="%s"]' % (runway_sel, target_runway))
            _wait_for_bar(page)
            actual_one = _bar_text(page)
            if actual_one != expected_one:
                raise AssertionError(
                    "lang=%s: expected [data-dirty-count] to read %r for a single "
                    "changed field (Runway), got %r" % (lang, expected_one, actual_one))

            # Phase B: ALSO change a Quiet hours field. The bar names
            # BOTH, Runway before Quiet hours — DOCUMENT order.
            page.fill(
                'input[name="quiet_hours_start"]', target_quiet_start)
            _commit_field(page, 'input[name="quiet_hours_start"]')
            wait_for_bar_text(expected_two)

            # Fresh load, REVERSED click order: Quiet hours first, Runway
            # second. dirtySectionLabels() walks the DOCUMENT, so the bar
            # must still read Runway before Quiet hours.
            page.goto(base_url + "/display")
            page.fill(
                'input[name="quiet_hours_start"]', target_quiet_start)
            _commit_field(page, 'input[name="quiet_hours_start"]')
            _wait_for_bar(page)
            _click_control(
                page, '%s[value="%s"]' % (runway_sel, target_runway))
            wait_for_bar_text(expected_two)
        finally:
            context.close()


def test_cancel_restores_the_field_the_preview_and_the_dial_from_the_resulting_dom(
        new_context, server):
    """a real Annuler click restores every surface, read off the RESULTING DOM: the theme
    chip's checked state is back to the original, the live preview <img>'s resolved src is
    back to the ORIGINALLY-selected theme's own (never the discarded one) — proving
    window.SkyPaneLivePreview.refresh() actually ran, since form.reset() fires no change
    event — and the quiet-hours dial's decoded arc and its handles' aria-valuenow are back
    to the pre-edit window, proving 28-08's own explicit deferred repaint of
    value-controls.js's repaintAll() landed; both edits are confirmed to have actually MOVED
    both surfaces before Cancel is ever clicked, and every post-Cancel read waits for
    28-08's setTimeout(fn, 0) deferred tick rather than reading synchronously after the
    click; asserting that refresh()/repaintAll() was CALLED is explicitly not acceptable and
    this check never does — the dial-repaints-for-free claim CONTEXT.md made is false by
    specification (already refuted in writing by 28-08) and this check does not re-litigate
    it (CFG-77, 28-11-PLAN.md Task 2; re-pointed to .palette-chip by 30-08-PLAN.md Task 2,
    CFG-85)"""
    context = new_context()
    try:
        page = context.new_page()
        base_url = server.base_url()
        _login(page, base_url)
        page.goto(base_url + "/display")

        def handle_values():
            return (
                int(page.get_attribute(
                    _handle_sel("quiet_hours_start"), "aria-valuenow")),
                int(page.get_attribute(
                    _handle_sel("quiet_hours_end"), "aria-valuenow")),
            )

        def preview_src():
            return page.eval_on_selector(
                THEME_PREVIEW_SEL, "el => el.getAttribute('src')")

        # --- Setup: record the pre-edit state of every surface, off the DOM.
        original_theme = page.eval_on_selector(
            'input[name="theme"]:checked', "el => el.value")
        original_preview_src = preview_src()
        original_arc = _quiet_arc_minutes(page, "before the edit")
        original_handles = handle_values()

        target_theme = next(
            t for t in device_config.THEME_IDS if t != original_theme)
        target_preview_src = page.eval_on_selector(
            'input[name="theme"][value="%s"]' % target_theme,
            "el => el.closest('.palette-chip').getAttribute('data-preview-src')")

        current_start = page.input_value(
            'input[name="quiet_hours_start"]')
        target_start = "05:00" if current_start != "05:00" else "06:00"

        # --- Edit: a DIFFERENT theme via a carousel chip, AND a different
        # quiet-hours window. Confirm both surfaces actually MOVED before
        # Cancel — a no-op edit would make every assertion below vacuous.
        _click_control(
            page, 'input[name="theme"][value="%s"]' % target_theme)
        _wait_for_bar(page)
        page.wait_for_function(
            "args => { var img = document.querySelector(args.sel);"
            " return !!img && img.getAttribute('src') === args.expected; }",
            arg={"sel": THEME_PREVIEW_SEL, "expected": target_preview_src})

        page.fill('input[name="quiet_hours_start"]', target_start)
        _commit_field(page, 'input[name="quiet_hours_start"]')

        moved_arc = _quiet_arc_minutes(page, "after the edit, before Cancel")
        moved_handles = handle_values()
        if moved_arc == original_arc or moved_handles == original_handles:
            raise AssertionError(
                "the quiet-hours edit did not move the dial before Cancel: arc %r -> %r, "
                "handles %r -> %r - a no-op edit proves nothing about Cancel"
                % (original_arc, moved_arc, original_handles, moved_handles))

        # --- Cancel: a real click on the native type="reset" button,
        # exercising both the native reset and 28-08's scripted
        # enhancement at once.
        page.click("[data-dirty-cancel]")
        _wait_for_bar_hidden(page)

        # a. The theme chip's checked state is back to the original.
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

        # b. The live preview's <img> resolved src is back to the
        #    ORIGINALLY-selected theme's own — the clause that proves
        #    window.SkyPaneLivePreview.refresh() actually ran, since
        #    form.reset() fires no change event and the preview cannot
        #    repaint on its own.
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

        # c. The quiet-hours dial's decoded arc AND its handles'
        #    aria-valuenow are back to the PRE-EDIT window.
        try:
            page.wait_for_function(
                "args => {"
                " var s = document.querySelector(args.sSel);"
                " var e = document.querySelector(args.eSel);"
                " return !!s && !!e"
                "   && s.getAttribute('aria-valuenow') === String(args.s)"
                "   && e.getAttribute('aria-valuenow') === String(args.e); }",
                arg={
                    "sSel": _handle_sel("quiet_hours_start"),
                    "eSel": _handle_sel("quiet_hours_end"),
                    "s": original_handles[0], "e": original_handles[1]},
                timeout=3000)
        except Exception:
            raise AssertionError(
                "expected the quiet-hours handles' aria-valuenow to be back to %r after "
                "Annuler (28-08's deferred repaint of value-controls.js's repaintAll()), "
                "still read %r" % (original_handles, handle_values()))
        restored_arc = _quiet_arc_minutes(
            page, "after Annuler, once the deferred tick has run")
        if restored_arc != original_arc:
            raise AssertionError(
                "expected the quiet-hours dial's decoded arc to be back to %r after "
                "Annuler, got %r" % (original_arc, restored_arc))
    finally:
        context.close()


# ===========================================================================
# 28-04-PLAN.md Task 2 (CFG-72): the settings-card-title consistency probe.
# ===========================================================================

_SETTINGS_CARD_TITLE_SELECTOR = (
    ".theme-status > h2.text-heading, .page-section > h2.text-heading")


def _settings_card_title_probe(page):
    """Every settings-card title on the CURRENTLY LOADED settings page,
    addressed by STRUCTURAL POSITION — the `<h2>` that is a direct child of
    a `.theme-status`/`.page-section` settings-card wrapper — never by
    class name. A supersection's own intro heading (`.section-intro > h2`)
    is EXCLUDED, structurally rather than by an explicit `:not()`: it lives
    under `.section-intro`, never directly under
    `.theme-status`/`.page-section`, so the selector above never reaches
    it — a deliberate exclusion (companion/test_config_page.py's own
    title-form inventory, 27-06-PLAN.md Task 1, and SKILL.md's three-rung
    heading ladder), not an oversight this check should "fix" into
    asserting the ladder away.
    """
    return page.evaluate(
        "sel => Array.from(document.querySelectorAll(sel)).map(h => {"
        "  var s = getComputedStyle(h);"
        "  return {text: h.textContent, fontSize: s.fontSize,"
        "          fontWeight: s.fontWeight, fontFamily: s.fontFamily};"
        "})", _SETTINGS_CARD_TITLE_SELECTOR)


def test_a_settings_card_title_renders_identically_on_both_settings_pages(new_context, server):
    """THE real proof, not a grep: ONE probe renders BOTH settings pages (Display and
    Device) in one session, addresses every settings-card title by STRUCTURAL POSITION
    rather than by class name, reads its getComputedStyle font-size/font-weight/font-family,
    and asserts the combined set across both pages has cardinality 1 — CFG-72's literal
    wording. Fails naming the empty side if either page contributes zero titles; every
    Device title must be one of the four named cards (Diagnostic LED, Wake interval,
    Notifications, Manual refresh) and the Poll card's own title specifically must be among
    them — proving the probe's reach extends to the one .page-section card, not just the
    three .theme-status ones — while a genuinely SMALLER set (one Device card removed from
    `builders`) still passes, proving the comparator is not secretly counting; the failure
    message names the offending page, the offending title's text and BOTH triples.
    Supersection intro headings (.section-intro > h2) are excluded structurally,
    deliberately — a different, generically-worded tier (27-06-PLAN.md Task 1, SKILL.md's
    three-rung heading ladder), not an inconsistency this check should assert away. Both
    themes exercised via _set_ui_theme(), at the 360px floor (CFG-72, 28-04-PLAN.md Task 2)"""
    context = new_context(viewport=VIEWPORT_MIN_SUPPORTED)
    try:
        page = context.new_page()
        _login(page, server.base_url())
        base_url = server.base_url()

        # Every (page, theme) combination this app can paint a
        # settings-card title in, all folded into ONE combined set below.
        entries = []
        by_page = {"/display": [], "/device": []}
        for theme in UI_THEMES_EXPLICIT:
            for route in ("/display", "/device"):
                page.goto(base_url + route)
                _set_ui_theme(page, theme)
                for title in _settings_card_title_probe(page):
                    triple = (
                        title["fontSize"], title["fontWeight"], title["fontFamily"])
                    entry = {
                        "page": route, "theme": theme,
                        "text": title["text"], "triple": triple}
                    entries.append(entry)
                    by_page[route].append(entry)

        # Clause (a): BOTH sides non-empty, naming the empty one.
        for route, side in by_page.items():
            if not side:
                raise AssertionError(
                    "expected at least one settings-card title on %s, got NONE - a "
                    "comparator with an empty side would pass vacuously" % route)

        # Device must contribute exactly the four NAMED cards.
        allowed_device_texts = {
            config_page.LED_SECTION_HEADING,
            config_page.WAKE_INTERVAL_SECTION_HEADING,
            config_page.NOTIFICATIONS_SECTION_HEADING,
            config_page.POLL_SECTION_HEADING}
        device_texts = {e["text"] for e in by_page["/device"]}
        unexpected = device_texts - allowed_device_texts
        if unexpected:
            raise AssertionError(
                "expected every Device settings-card title to be one of %r, found "
                "unexpected title(s) %r - a probe addressing titles by class name rather "
                "than structural position would pick up supersection intro headings too, "
                "which is exactly the 27-06-shaped mistake this check exists to avoid"
                % (sorted(allowed_device_texts), sorted(unexpected)))
        if config_page.POLL_SECTION_HEADING not in device_texts:
            raise AssertionError(
                "expected the Poll card's own title (%r) among Device's settings-card "
                "titles - it reaches the page through a .page-section wrapper, not "
                ".theme-status like the other three, and a probe that silently misses it "
                "would pass this check while leaving CFG-72 unmet on a card the developer "
                "can see" % config_page.POLL_SECTION_HEADING)

        # Clause (b): the combined set's own cardinality is 1.
        triples = sorted({e["triple"] for e in entries})
        if len(triples) != 1:
            majority = collections.Counter(
                e["triple"] for e in entries).most_common(1)[0][0]
            offender = next(e for e in entries if e["triple"] != majority)
            # Clause (c): the message names the offending page, the
            # offending title's text, and BOTH triples.
            raise AssertionError(
                "expected exactly one (font-size, font-weight, font-family) triple across "
                "every settings-card title on both settings pages, got %d distinct triples "
                "- %r on %s (theme=%s) renders %r, while the rest render %r"
                % (len(triples), offender["text"], offender["page"], offender["theme"],
                   offender["triple"], majority))
    finally:
        context.close()


# ===========================================================================
# 28-09-PLAN.md Task 1 (CFG-78/CFG-74(c)): the single-affordance audit, and
# the runway radios' cross-tree form= regression check.
# ===========================================================================

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
    """exactly ONE submit-shaped control on the whole settings page resolves its own
    .form.id to config_page.SETTINGS_FORM_ID, on both /display and /device, in both site
    languages — resolved via the browser's OWN .form property, never a count of <button
    occurrences in the HTML string and never a hand-maintained allow-list; covers
    input[type=submit], button[type=submit] AND a bare <button> with no type attribute (the
    HTML default IS submit); the bar's native type="reset" Cancel is deliberately excluded
    (form-associated but not submit-shaped, and it saves nothing); the one settings-form
    control must carry data-static-save-fallback and be a descendant of [data-dirty-bar];
    the failure message NAMES every collected control as a tagName/type/form-id/text tuple
    so a regression says WHICH control drifted; and the complement is asserted too —
    calendar/rules/notifications-test/quick-LED/quick-switch controls, whichever this scope
    renders, each resolve to a NON-settings-form id (CFG-78, 28-09-PLAN.md Task 1)"""
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

                # The complement — the relationship half, not merely the
                # endpoint: every OTHER submit-shaped control this scope
                # renders resolves to a form id that is NOT the settings
                # form.
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


def test_the_runway_form_associated_path_reaches_the_bar_and_disk_end_to_end(
        new_context, make_app_server):
    """the runway radios' cross-tree form="settings-form" wiring drives the SAME
    bar-appears -> Enregistrer -> persisted-to-disk path every natively-nested control
    does — closing the path CFG-74(c) named before it was superseded, now against the real
    POST instead of the retired fetch: selecting a runway radio (rendered OUTSIDE the
    settings form) reveals the bar naming exactly its own Runway/Piste label, a real
    Enregistrer navigation writes tracked_runway to disk, and a reload shows the radio
    reflecting the saved value — both site languages (CFG-74(c)/CFG-78, 28-09-PLAN.md
    Task 1)"""
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

            runway_sel = 'input[name="tracked_runway"]'
            current_runway = page.eval_on_selector(
                "%s:checked" % runway_sel, "el => el.value")
            target_runway = next(
                r for r in device_config.RUNWAY_IDS if r != current_runway)

            runway_label = page.eval_on_selector(
                runway_sel,
                "el => el.closest('[data-dirty-section]')"
                ".getAttribute('data-dirty-section')")
            changed_suffix = page.eval_on_selector(
                "[data-dirty-bar]",
                "el => el.getAttribute('data-dirty-changed-suffix')")
            expected = runway_label + changed_suffix

            # 2. Select a runway radio whose value differs from disk, via
            #    a real element.click().
            _click_control(
                page, '%s[value="%s"]' % (runway_sel, target_runway))

            # 3. The bar becomes visible AND names EXACTLY Runway.
            _wait_for_bar(page)
            actual = _bar_text(page)
            if actual != expected:
                raise AssertionError(
                    "lang=%s: expected [data-dirty-count] to read %r after selecting a "
                    "cross-tree form=-associated runway radio, got %r - the "
                    "section-naming walk must resolve this control's own "
                    "[data-dirty-section] ancestor even though the radio is not a "
                    "literal descendant of <form id=\"settings-form\">"
                    % (lang, expected, actual))

            # 4. Click Enregistrer, wait for the REAL navigation.
            _save_via_bar(page)

            # 5. Re-read tracked_runway OFF DISK.
            saved = device_config.load_device_config(server.tmpdir)["tracked_runway"]
            if saved != target_runway:
                raise AssertionError(
                    "lang=%s: expected tracked_runway on disk to be %r after a real "
                    "Enregistrer navigation through the runway's own cross-tree form= "
                    "path, got %r" % (lang, target_runway, saved))

            # Reload: the round trip, not just the write.
            page.goto(base_url + "/display")
            checked = page.eval_on_selector(
                "%s:checked" % runway_sel, "el => el.value")
            if checked != target_runway:
                raise AssertionError(
                    "lang=%s: expected the reloaded page's checked runway radio to be "
                    "%r, got %r" % (lang, target_runway, checked))
        finally:
            context.close()


# ===========================================================================
# 25-07-PLAN.md Task 3 (CFG-51/D19): THE ARTWORK DROP ZONE.
#
# Each check below gets its own state (see the fixtures above): the
# needs-artwork manual entry is a precondition none of them may leave
# altered for a sibling, and under xdist there is no sibling to leave it
# for anyway — each test builds/tears down its own server and its own
# tmp_path fixture files.
# ===========================================================================

def test_artwork_uploads_and_is_served_with_scripts_blocked(new_context, make_app_server, tmp_path):
    """with scripts blocked at 360px, an artwork file chosen through the native <input
    type="file"> and submitted through the fallback panel's own form is STORED (read back
    off the real state directory, never off the page — a rejected upload redirects to a
    page that looks like success) and SERVED back by the illustration route as an image at
    illustration_normalize.ILLUSTRATION_TARGET_SIZE; and the drop zone beside it measures
    zero height and holds zero focusable descendants with scripts blocked while occupying a
    real box with them on (CFG-51/D-09, 25-07-PLAN.md Task 3)"""
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
    """the SAME source file stored byte-identically whether it was PICKED or DROPPED (with
    the stored file deleted between the two uploads, so a drop that never reached the server
    could not pass on the picked file left behind), the preview decoding to the source's own
    1200x300 through a data: URL (a blob: one is blocked by this app's own CSP); and the
    FLOOR measured against the INPUT rather than against a message — zero files, a wrong
    type, several at once and an oversized file each assign nothing, each say something, and
    each say something different, while a synthetic drop changes nothing at all and the
    drag-over state is sampled visible BETWEEN dragOver and drop (CFG-51/D19, 25-07-PLAN.md
    Task 3)"""
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
    """the artwork drop zone clears the 44px target by real hit-testing in ITS OWN
    container at 360px, the Airlines page does not scroll sideways there, the preview box
    reserves illustration_normalize.py's own aspect ratio (by getBoundingClientRect, never
    clientWidth) BEFORE any image exists with the <img> still hidden, and the paint is a
    FLOOR not a ceiling: the hint text is never the canvas colour, the preview frame is
    never its own fill, and the whole zone paints differently in the two themes
    (CFG-51/CFG-52, 25-07-PLAN.md Task 3)"""
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
