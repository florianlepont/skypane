"""Part 03 of the `companion/test_config_page.py` migration chain
(33-11-PLAN.md): the original harness's `check()` calls #85-#145, covering
handle_post()'s field-level `errors` dict (19-07-PLAN.md), the retired
LED-route/helper-symbol guards, runway-image detection and
runway_fieldset() image emission, several cross-file DOM-contract guards
between config_page.py and its two static assets (dirty-state.js,
style.css), the theme-chip grid's markup/selection-state contract
(including the live `:has(input:checked)` treatment and its saved-but-
unchecked "Current" badge), the arrivals/calendar theme override's
clearable contract, and the Aspect card's own accordion shape and its
per-flight rules editor markup.

Every check calls `companion.pages.config_page`'s own functions directly,
in-process, against a `tmp_path`-backed state directory — this slice
still needs no running `companion/app.py` server for its handle_post()/
render() checks. The checks that used to read `companion/static/style.css`
or a served JS asset (`dirty-state.js`, `theme-preview.js`) from disk
instead fetch them from a running `companion/app.py`
(`module_app_server_factory` + `served_stylesheet()`/`served_asset()`)
and assert on `companion_markup`'s parsed CSS structure or the served
text itself — never a file opened from disk (TST-12). Two checks
(STATIC_SAVE_FALLBACK_ATTR / the retired `.save-status` region) assert
that NO rule selector anywhere references the retired token, using
`companion_markup.css_rules()` over the served stylesheet rather than a
raw index scan, per this plan's own hotspot. Runtime state files this
slice writes under `tmp_path` (never production source) are read back
with `pathlib.Path.read_bytes()`.
"""
import re
from pathlib import Path

import pytest

import companion.i18n as i18n
import companion.test_config_page_helpers as cp
from companion import app as companion_app
from companion.layout import escape_html
from companion.pages import config_page
from companion_app_server import served_asset, served_stylesheet
from companion_markup import css_rules, declarations_for
from server import device_config
from server.plane import colour_rules


@pytest.fixture(scope="module")
def app(module_app_server_factory):
    """A read-only companion/app.py server this module's checks fetch the
    served stylesheet/JS assets from, instead of opening them from disk
    (TST-12)."""
    return module_app_server_factory()


@pytest.fixture(scope="module")
def served_css(app):
    """The stylesheet companion/app.py actually serves."""
    return served_stylesheet(app)


@pytest.fixture(scope="module")
def dirty_state_js(app):
    """companion/static/dirty-state.js's served text, fetched over HTTP
    instead of opened from disk (TST-12)."""
    return served_asset(app, "/static/dirty-state.js")


@pytest.fixture(scope="module")
def theme_preview_js(app):
    """companion/static/theme-preview.js's served text, fetched over HTTP
    instead of opened from disk (TST-12)."""
    return served_asset(app, "/static/theme-preview.js")


# ======================================================================
# Section 1: 19-07-PLAN.md Task 1-3 (D-07/A-25) - handle_post()'s new
# optional `errors` dict parameter.
# ======================================================================

def test_handle_post_wake_interval_empty_or_absent_leaves_unchanged(tmp_path):
    """after a save that stored wake_interval_s 120, a later submission with wake_interval_s as
    the empty string, and another with the key absent entirely, both return the saved flash key
    and leave the stored value at 120 (11-RESEARCH.md Open Question 2)"""
    tmpdir = str(tmp_path)
    ctx = {"state_dir": tmpdir}
    seed_flash = config_page.handle_post({"wake_interval_s": "120"}, ctx)
    assert seed_flash == config_page.FLASH_SAVED, (
        "expected the seeding save to succeed, got %r" % (seed_flash,))
    empty_flash = config_page.handle_post({"wake_interval_s": ""}, ctx)
    assert empty_flash == config_page.FLASH_SAVED, (
        "expected an empty-string wake_interval_s to succeed (leave unchanged), got %r" % (empty_flash,))
    on_disk = device_config.load_device_config(tmpdir)
    assert on_disk["wake_interval_s"] == 120, (
        "expected wake_interval_s to remain 120 after an empty-string submission, got %r"
        % (on_disk["wake_interval_s"],))
    absent_flash = config_page.handle_post({}, ctx)
    assert absent_flash == config_page.FLASH_SAVED, (
        "expected an absent wake_interval_s key to succeed (leave unchanged), got %r" % (absent_flash,))
    on_disk = device_config.load_device_config(tmpdir)
    assert on_disk["wake_interval_s"] == 120, (
        "expected wake_interval_s to remain 120 after an absent-key submission, got %r"
        % (on_disk["wake_interval_s"],))


def test_handle_post_no_errors_arg_returns_identical_flash_keys(tmp_path):
    """handle_post(form, ctx) with no errors argument still returns exactly the same flash keys
    it did before this plan, for both a representative valid save and a representative invalid
    save"""
    ctx = {"state_dir": str(tmp_path)}
    valid_flash = config_page.handle_post({"theme": "white"}, ctx)
    assert valid_flash == config_page.FLASH_SAVED, (
        "expected FLASH_SAVED for a representative valid save, got %r" % (valid_flash,))
    invalid_flash = config_page.handle_post({"theme": "not-a-real-theme"}, ctx)
    assert invalid_flash == config_page.FLASH_SAVE_FAILED, (
        "expected FLASH_SAVE_FAILED for a representative invalid save, got %r" % (invalid_flash,))


@pytest.mark.parametrize(
    "form, field, expected_message",
    [
        ({"wake_interval_s": "7"}, "wake_interval_s", config_page.ERROR_WAKE_INTERVAL_RANGE),
        ({"wake_interval_s": "abc"}, "wake_interval_s", config_page.ERROR_WAKE_INTERVAL_RANGE),
        ({"quiet_hours_start": "24:00"}, "quiet_hours_start", config_page.ERROR_QUIET_HOURS_TIME_SHAPE),
        ({"quiet_hours_start": ""}, "quiet_hours_start", config_page.ERROR_QUIET_HOURS_TIME_SHAPE),
        ({"quiet_hours_end": "not-a-time"}, "quiet_hours_end", config_page.ERROR_QUIET_HOURS_TIME_SHAPE),
        (
            {
                "calendar_url": "https://example.com/feed.ics",
                "calendar_disconnect": config_page.CALENDAR_DISCONNECT_CHECKBOX_VALUE,
            },
            "calendar_url", config_page.ERROR_CALENDAR_URL_INVALID,
        ),
    ],
    ids=[
        "wake-interval-out-of-range",
        "wake-interval-non-numeric",
        "quiet-hours-start-invalid-hour",
        "quiet-hours-start-empty",
        "quiet-hours-end-not-a-time",
        "calendar-url-and-disconnect-contradiction",
    ],
)
def test_handle_post_errors_dict_filled_for_each_real_user_error_field(tmp_path, form, field, expected_message):
    """handle_post(form, ctx, errors=d) fills d with exactly one field-keyed message for each
    real-user-error case (wake_interval_s non-numeric/out-of-range, quiet_hours_start/
    quiet_hours_end malformed including empty, and a contradictory calendar_url+
    calendar_disconnect submission)"""
    ctx = {"state_dir": str(tmp_path)}
    errors = {}
    flash_key = config_page.handle_post(form, ctx, errors=errors)
    assert flash_key == config_page.FLASH_SAVE_FAILED, (
        "expected FLASH_SAVE_FAILED for form=%r, got %r" % (form, flash_key))
    assert errors == {field: expected_message}, (
        "expected errors == {%r: %r} for form=%r, got %r" % (field, expected_message, form, errors))


def test_handle_post_errors_dict_stays_empty_on_a_valid_save(tmp_path):
    """handle_post(form, ctx, errors=d) leaves d empty when the save succeeds"""
    ctx = {"state_dir": str(tmp_path)}
    errors = {}
    flash_key = config_page.handle_post(
        {
            "theme": "white", "quiet_hours_start": "22:30",
            "quiet_hours_end": "06:15", "wake_interval_s": "120",
        },
        ctx, errors=errors)
    assert flash_key == config_page.FLASH_SAVED, "expected FLASH_SAVED, got %r" % (flash_key,)
    assert errors == {}, "expected errors to stay empty on a valid save, got %r" % (errors,)


def test_handle_post_empty_quiet_hours_start_writes_nothing(tmp_path):
    """handle_post({"theme": "white", "quiet_hours_start": ""}, ctx, errors=d) rejects the whole
    save, writes nothing (the theme must not persist either), and reports the error on
    quiet_hours_start alone

    The all-or-nothing contract's own direct pin for the NEW pre-check: an empty
    quiet_hours_start must reject before save_device_config() is ever called, leaving a
    pre-existing config byte-identical - not merely returning the right flash key.
    """
    tmpdir = str(tmp_path)
    cp.write_device_config(tmpdir, "black", "3")
    before = Path(device_config.device_config_path(tmpdir)).read_bytes()
    ctx = {"state_dir": tmpdir}
    errors = {}
    flash_key = config_page.handle_post(
        {"theme": "white", "quiet_hours_start": ""}, ctx, errors=errors)
    after = Path(device_config.device_config_path(tmpdir)).read_bytes()
    assert flash_key == config_page.FLASH_SAVE_FAILED, (
        "expected FLASH_SAVE_FAILED for an empty quiet_hours_start, got %r" % (flash_key,))
    assert before == after, "expected device_config.json to stay byte-identical, it changed"
    assert errors == {"quiet_hours_start": config_page.ERROR_QUIET_HOURS_TIME_SHAPE}, (
        "expected exactly one quiet_hours_start error, got %r" % (errors,))


def test_local_quiet_hours_regex_agrees_with_save_device_config(tmp_path):
    """config_page._QUIET_HOURS_TIME_RE agrees with server.device_config.save_device_config()'s
    own HH:MM shape gate over the table ""/"7:00"/"07:00"/"24:00"/"abc"/"23:59"/"00:00"

    19-07-PLAN.md Task 1: this module's own local HH:MM shape gate (_QUIET_HOURS_TIME_RE) is a
    UX pre-check only - save_device_config()'s identical gate stays authoritative. This pins the
    two never silently drifting apart, over the exact table the plan names.
    """
    tmpdir = str(tmp_path)
    for candidate in ("", "7:00", "07:00", "24:00", "abc", "23:59", "00:00"):
        pre_check_says_ok = bool(config_page._QUIET_HOURS_TIME_RE.match(candidate))
        try:
            device_config.save_device_config(tmpdir, quiet_hours_start=candidate)
            save_device_config_says_ok = True
        except ValueError:
            save_device_config_says_ok = False
        assert pre_check_says_ok == save_device_config_says_ok, (
            "disagreement for %r: pre-check says ok=%r, save_device_config() says ok=%r"
            % (candidate, pre_check_says_ok, save_device_config_says_ok))


# ======================================================================
# Section 2: 19-07-PLAN.md Task 2 (D-07/A-25) - render() repopulates
# every control from a rejected save's own submission.
# ======================================================================

_TASK2_BASE_CTX = {
    "device_config": {"theme": "white", "tracked_runway": "3"},
    "poll_cooldown_remaining": 0,
    "now": "2026-09-07T09:12:04+00:00",
}


def test_render_no_new_args_byte_identical_and_no_field_error_markup():
    """render(ctx) with no new arguments is byte-identical to render(ctx, errors=None,
    submitted=None) and contains no field-error markup"""
    plain = config_page.render(_TASK2_BASE_CTX)
    explicit_none = config_page.render(_TASK2_BASE_CTX, errors=None, submitted=None)
    assert plain == explicit_none, (
        "expected render(ctx) to be byte-identical to render(ctx, errors=None, submitted=None)")
    assert "field-error" not in plain, "expected no field-error markup when no errors are passed"


def test_render_wake_interval_error_shows_message_value_and_aria():
    """render(ctx, errors={"wake_interval_s": "msg"}, submitted={"wake_interval_s": "7"}) renders
    the message once, echoes value="7" back into the input, and sets aria-invalid plus a
    matching aria-describedby"""
    rendered = config_page.render(
        _TASK2_BASE_CTX, errors={"wake_interval_s": "msg"},
        submitted={"wake_interval_s": "7"})
    assert rendered.count("msg") == 1, (
        "expected the error message to render exactly once, got %d" % rendered.count("msg"))
    assert 'value="7"' in rendered, "expected the submitted value 7 to be echoed back into the input"
    # 22-10-PLAN.md Task 3 (B17): retargeted in place for the new id=.
    input_match = re.search(
        r'<input type="number" id="[^"]*" name="wake_interval_s"[^>]*>', rendered)
    assert input_match, "expected the wake_interval_s input to still be present"
    assert 'aria-invalid="true"' in input_match.group(0), "expected aria-invalid=\"true\" on the errored input"
    describedby_match = re.search(r'aria-describedby="([^"]+)"', input_match.group(0))
    assert describedby_match, "expected an aria-describedby attribute on the errored input"
    # 19-11-PLAN.md Task 3 (D-12/A-30): the value is a SPACE-SEPARATED list
    # (the hint id first, then the error id), not a single id.
    ids = describedby_match.group(1).split(" ")
    assert len(ids) == 2, "expected exactly two space-separated ids (hint, then error), got %r" % (ids,)
    assert ids[0] == config_page.WAKE_INTERVAL_SECTION_CAPTION_ID, (
        "expected the hint id to come first, got %r" % (ids,))
    for token in ids:
        assert ('id="%s"' % token) in rendered, (
            "expected an element carrying id=%r matching aria-describedby" % (token,))


def test_render_submitted_theme_id_checked_even_when_differs_from_stored():
    """a submitted theme id is rendered as the CHECKED radio even when it differs from the
    stored theme (D-07 repopulation)"""
    rendered = config_page.render(
        dict(_TASK2_BASE_CTX, device_config={"theme": "white", "tracked_runway": "3"}),
        submitted={"theme": "black"}, scope=config_page.SCOPE_DISPLAY)
    assert re.search(r'name="theme" value="black"[^>]*checked', rendered), (
        "expected the submitted theme (black) to render checked even though the stored theme is white")
    assert not re.search(r'name="theme" value="white"[^>]*checked', rendered), (
        "expected the stored theme (white) to NOT render checked once a different submission is being repopulated")


def test_render_both_quiet_hours_time_inputs_carry_required():
    """both quiet-hours time inputs carry required in the rendered Settings page"""
    rendered = config_page.render(_TASK2_BASE_CTX)
    start_match = re.search(r'<input type="time" name="quiet_hours_start"[^>]*>', rendered)
    end_match = re.search(r'<input type="time" name="quiet_hours_end"[^>]*>', rendered)
    assert start_match and "required" in start_match.group(0), (
        "expected the quiet_hours_start input to carry required")
    assert end_match and "required" in end_match.group(0), (
        "expected the quiet_hours_end input to carry required")


def test_calendar_connection_url_error_never_echoes_the_submitted_secret():
    """_calendar_connection_html(..., errors={"calendar_url": "msg"}) renders the error message
    under the field while the write-only field itself still carries no value attribute at all
    (D-07/T-19-12/D-13, retargeted after _calendar_connection_html()'s retirement,
    30-06-PLAN.md Task 3)

    The write-only calendar_url field's own `errors` parameter now lives directly on
    _calendar_connection_html() - it never accepts `submitted` at all (nothing to repopulate:
    the one field it renders is write-only), so there is no submitted URL for it to echo.
    """
    rendered, _disconnect_form_html = config_page._calendar_connection_html(
        False, False, None, None, "2026-09-07T09:12:04+00:00", 0,
        errors={"calendar_url": "msg"})
    assert "msg" in rendered, "expected the calendar_url error message to render"
    assert 'name="calendar_url"' in rendered, "expected the calendar_url field itself to still render"
    after_name = rendered.split('name="calendar_url"', 1)[1].split(">", 1)[0]
    assert "value=" not in after_name, (
        "expected no value attribute on the calendar_url field even with an error present")


def test_style_css_styles_field_error(served_css):
    """companion/static/style.css styles .field-error using the existing --color-status-error
    token (cross-file DOM contract guard)"""
    declarations = declarations_for(served_css, ".field-error")
    joined = " ".join(declarations.values())
    assert "--color-status-error" in joined, (
        "expected .field-error to read the existing --color-status-error token, got declarations %r"
        % (declarations,))


# ======================================================================
# Section 3: 19-07-PLAN.md Task 3 (D-07/A-25) - the legacy no-errors-arg
# contract is intact even for a rejected save.
# ======================================================================

def test_handle_post_rejected_save_without_errors_arg_still_returns_save_failed(tmp_path):
    """a rejected save still returns FLASH_SAVE_FAILED from handle_post() when no errors dict is
    passed (the legacy contract is intact)"""
    ctx = {"state_dir": str(tmp_path)}
    flash_key = config_page.handle_post({"theme": "not-a-real-theme"}, ctx)
    assert flash_key == config_page.FLASH_SAVE_FAILED, (
        "expected FLASH_SAVE_FAILED with no errors argument, got %r" % (flash_key,))


# ======================================================================
# Section 4: 06.6.4.1-07 (D-05) - the retired separate LED route/helper
# symbols stay gone; quick task 260901-re6 Task 3 - five retired helper
# constants stay gone too.
# ======================================================================

def test_render_has_no_action_pointing_at_retired_led_route():
    """render() emits no action pointing at the retired separate LED form path (D-05)

    The LED group is merged into the single settings form - render() must never emit a second,
    independently-submittable <form action="/config-led"> at all. The separate POST /config-led
    route and its handler no longer exist anywhere in the app, so this is now a pure markup
    regression guard.
    """
    rendered = config_page.render({
        "device_config": {"theme": "sky", "tracked_runway": "3", "led_enabled": True},
        "poll_cooldown_remaining": 0,
    })
    assert 'action="%s"' % config_page.SETTINGS_ROUTE in rendered, (
        "expected the settings form action to be present")
    assert 'action="/config-led"' not in rendered, (
        "expected no action=\"/config-led\" in render()'s output (D-05 merge)")


def test_config_page_exposes_no_retired_led_symbols():
    """companion.pages.config_page exposes neither led_fieldset, led_section, nor
    handle_led_post (all three retired, D-05)"""
    for name in ("led_fieldset", "led_section", "handle_led_post"):
        assert not hasattr(config_page, name), (
            "expected config_page to expose no %r attribute" % name)


def test_config_page_exposes_no_retired_helper_or_description_symbols():
    """companion.pages.config_page exposes none of THEME_HELPER_TEXT/THEME_SECTION_DESCRIPTION/
    RUNWAY_HELPER_TEXT/RUNWAY_SECTION_DESCRIPTION/LED_HELPER_TEXT (all five retired, quick task
    260901-re6)"""
    retired = (
        "THEME_HELPER_TEXT", "THEME_SECTION_DESCRIPTION",
        "RUNWAY_HELPER_TEXT", "RUNWAY_SECTION_DESCRIPTION",
        "LED_HELPER_TEXT")
    for name in retired:
        assert not hasattr(config_page, name), (
            "expected config_page to expose no %r attribute" % name)


# ======================================================================
# Section 5: runway-image existence detection (Task 1, D-03) - each check
# uses its own tmp_path image_dir and never touches the real
# companion/static/ (06.4-RESEARCH.md Pitfall 1).
# ======================================================================

def test_runway_images_available_empty_dir_yields_empty_set(tmp_path):
    """runway_images_available() returns the empty set when the image directory has no files"""
    result = companion_app.runway_images_available(image_dir=str(tmp_path))
    assert result == set(), "expected an empty set for an empty directory, got %r" % (result,)


def test_runway_images_available_detects_single_present_file(tmp_path):
    """runway_images_available() returns exactly {'3'} when only runway-3.png exists"""
    (tmp_path / "runway-3.png").write_bytes(b"not-a-real-png-just-test-bytes")
    result = companion_app.runway_images_available(image_dir=str(tmp_path))
    assert result == {"3"}, "expected {'3'}, got %r" % (result,)


def test_runway_images_available_missing_dir_yields_empty_set_no_raise(tmp_path):
    """runway_images_available() returns the empty set (does not raise) when image_dir does not
    exist

    The path is a never-created subpath of tmp_path (not a directory that is created and then
    removed): the property under test is that a MISSING directory never raises, and writing
    nothing at all under tmp_path is the more direct way to prove that (TST-13).
    """
    nonexistent = tmp_path / "does-not-exist"
    result = companion_app.runway_images_available(image_dir=str(nonexistent))
    assert result == set(), "expected an empty set for a non-existent directory, got %r" % (result,)


def test_runway_images_available_bounded_by_registry_not_directory_listing(tmp_path):
    """runway_images_available() ignores files that are not RUNWAY_IDS members, proving it is
    registry-bounded not directory-listing-bounded"""
    (tmp_path / "runway-99.png").write_bytes(b"not-a-registry-member")
    (tmp_path / "style.css").write_text("/* not a runway image */")
    result = companion_app.runway_images_available(image_dir=str(tmp_path))
    assert result == set(), (
        "expected an empty set (non-registry files must be ignored), got %r" % (result,))


# ======================================================================
# Section 6: runway_fieldset() image emission (Task 2, D-01/D-03) - unit
# checks against the string output only, no filesystem/subprocess
# involved.
# ======================================================================

def test_runway_fieldset_emits_img_only_for_available_runway():
    """runway_fieldset(images_available={'3'}) emits exactly one <img, for runway 3 only"""
    rendered = config_page.runway_fieldset("3", {"3"})
    assert rendered.count("<img") == 1, (
        "expected exactly one <img occurrence, got %d" % rendered.count("<img"))
    assert "/runway-image/3.png" in rendered, "expected the src to point at /runway-image/3.png"
    assert "runway-image/06-24" not in rendered and "runway-image/02-20" not in rendered, (
        "expected no image reference for runways not in images_available")


def test_runway_fieldset_graceful_fallback_no_images():
    """runway_fieldset(images_available=set()) renders zero <img tags and all three
    number/heading labels (D-03 graceful fallback)"""
    rendered = config_page.runway_fieldset("3", set())
    assert "<img" not in rendered, "expected zero <img occurrences with an empty images_available set"
    assert rendered.count('name="tracked_runway"') == 3, "expected all three runway radios still present"
    for runway_id in device_config.RUNWAY_IDS:
        assert escape_html(device_config.runway_label(runway_id)) in rendered, (
            "expected the label text for runway %r" % (runway_id,))


def test_render_forwards_ctx_runway_images_key():
    """render() forwards ctx['runway_images'] to runway_fieldset() rather than relying on the
    parameter default"""
    rendered = config_page.render({
        "device_config": {"theme": "black", "tracked_runway": "3"},
        "poll_cooldown_remaining": 0,
        "runway_images": {"06-24"},
    })
    assert "/runway-image/06-24.png" in rendered, (
        "expected render() to forward ctx['runway_images'] into the <img> src")
    # 06.6.4.1.1-05: scoped to the runway-card image class specifically -
    # the page now also carries one theme-chip preview <img> per THEME_IDS
    # entry, so a bare "<img" count is no longer exclusive to the runway
    # picker.
    assert rendered.count('<img class="runway-card__image"') == 1, (
        "expected exactly one runway-card__image <img occurrence, got %d"
        % rendered.count('<img class="runway-card__image"'))


# ======================================================================
# Section 7: cross-file DOM-contract guards between config_page.py's
# constants and the two static assets that read them by literal value,
# dirty-state.js and style.css (06.6.4.1 Task 3, D-03/D-04/D-06).
# ======================================================================

def test_dirty_state_js_delegates_change_and_input_at_document_level_and_has_no_forbidden_syntax(dirty_state_js):
    """dirty-state.js references DIRTY_SECTION_ATTR again (dirtySectionLabels() restored) but
    carries neither the retired dirty-ready nor dirty-shown marker, delegates BOTH change AND
    input at document level gated on e.target.form === form with no surviving
    form.addEventListener("change"/"input" registration (B1), and contains none of
    innerHTML/let /const /=>/backtick (CFG-77/CFG-78, 28-08-PLAN.md Task 3)

    28-08-PLAN.md Task 3 restores dirtySectionLabels()'s own [data-dirty-section] reader and the
    dual change/input delegation (6dea46a's own pre-27-04 shape). The dirty-ready/dirty-shown
    MARKERS do NOT return - this restoration's own clearance mechanism is :has(.dirty-bar),
    which needs no script-written marker class.
    """
    source = dirty_state_js
    assert config_page.DIRTY_SECTION_ATTR in source, (
        "expected dirty-state.js to reference DIRTY_SECTION_ATTR's value again - "
        "dirtySectionLabels() is restored and reads it")
    assert "dirty-ready" not in source and "dirty-shown" not in source, (
        "expected dirty-state.js to carry neither the dirty-ready nor the dirty-shown marker - "
        "this restoration's own clearance mechanism is :has(.dirty-bar), which needs no "
        "script-written marker class")
    assert 'form.addEventListener("change"' not in source and 'form.addEventListener("input"' not in source, (
        "expected no surviving form.addEventListener(\"change\"/\"input\" registration (B1 "
        "regression) - delegation must stay document-level")
    for kind in ("change", "input"):
        call = 'document.addEventListener("%s"' % kind
        assert call in source, "expected a document.addEventListener(%r registration" % (kind,)
    assert "e.target.form === form" in source or "e.target.form===form" in source, (
        "expected the document-level delegation to gate on e.target.form === form")
    for forbidden in ("innerHTML", "let ", "const ", "=>", "`"):
        assert forbidden not in source, (
            "forbidden ES5-unsafe/HTML-writing construct found in dirty-state.js: %r" % (forbidden,))


def test_live_preview_crossfades_through_one_class_shared_by_css_and_js(served_css, theme_preview_js):
    """the live theme preview CROSSFADES rather than cuts: .theme-live-preview__image declares an
    opacity transition at var(--motion-fast) on its own base rule, a
    .theme-live-preview__image--swapping class carries the opacity-0 half, theme-preview.js
    drives that same class literal from transitionend and the image's own load/error (never a
    timer) while consulting the computed opacity so a swap can never wait on a transition that
    never runs, and T8's window.SkyPaneLivePreview.refresh() survives (D3/CFG-32,
    23-10-PLAN.md Task 2)

    The mechanism must be EVENT-DRIVEN, never timed: a crossfade on a timer is the specific way
    this goes wrong (the swap and the fade drift apart, and the preview settles on whichever the
    timer happened to win). `transitionend` is when the fade-out is genuinely over, and the
    image's own `load`/`error` is when the new frame is genuinely there.
    """
    fade_class = "theme-live-preview__image--swapping"
    css = served_css
    # Comment-stripped structurally, via css_rules()/declarations_for(),
    # so a comment that merely discusses the timer ban can never satisfy
    # (or trip) this assertion.
    base = declarations_for(css, ".theme-live-preview__image")
    assert "transition" in base, (
        "expected .theme-live-preview__image to declare the crossfade transition on its own base "
        "rule, so the fade runs in BOTH directions from one declaration")
    decl = base["transition"]
    assert "opacity" in decl, (
        "expected the live preview's transition to name opacity, got %r" % (decl,))
    assert "var(--motion-fast)" in decl, (
        "expected the live preview crossfade to spend var(--motion-fast) - somebody just clicked "
        "a chip and is watching for the preview to answer, got %r" % (decl,))

    fade_decls = declarations_for(css, ".%s" % fade_class)
    assert fade_decls.get("opacity") == "0", (
        "expected .%s to be the opacity-0 half of the crossfade, got %r" % (fade_class, fade_decls))

    # theme-preview.js's own comment/string stripper must NOT erase
    # string literals: fade_class and the "load"/"error" event names are
    # all quoted strings this check searches for verbatim.
    js = cp.strip_js_line_and_block_comments(theme_preview_js)
    assert fade_class in js, (
        "theme-preview.js must drive the crossfade through the same %r class style.css declares "
        "- neither file imports the other, and this literal is the only thing keeping them in "
        "step" % (fade_class,))
    for token in ("transitionend", '"load"', '"error"'):
        assert token in js, (
            "expected theme-preview.js to listen for %s - the crossfade must be driven by the "
            "events that actually mark the fade-out ending and the new frame arriving, never by "
            "a timer" % (token,))
    # The one stall an event-driven crossfade can have, pinned as a
    # structural fact because its browser-level reproduction is
    # probabilistic (measured 4 stalls in 14 runs before the fix, 0 in 14
    # after). A transitionend only arrives if a transition actually RAN.
    assert "getComputedStyle" in js, (
        "theme-preview.js must consult the COMPUTED opacity before waiting on transitionend: a "
        "transition that never runs never ends, and the preview then sits invisible on the "
        "discarded theme forever (measured: 4 stalls in 14 runs without this)")
    for banned in ("setTimeout", "setInterval", "requestAnimationFrame"):
        assert banned not in js, (
            "theme-preview.js must stay timer-free (%r found): a timed crossfade lets the swap "
            "and the fade drift apart, and the preview settles on whichever won" % (banned,))
    # T8 survives: dirty-state.js's Cancel handler calls this, and a
    # crossfade that bypassed refresh() would leave Cancel showing the
    # discarded theme again.
    assert "SkyPaneLivePreview" in js and "refresh" in js, (
        "expected theme-preview.js to keep exposing window.SkyPaneLivePreview.refresh() - "
        "dirty-state.js's Cancel handler calls it after form.reset(), and T8 exists because "
        "reset() fires no change event")


def test_dirty_state_js_beforeunload_guard_reuses_count_differences(dirty_state_js):
    """dirty-state.js registers a beforeunload listener whose body references countDifferences
    and sets returnValue/calls preventDefault, and a submit listener clears the guard; contains
    none of innerHTML/let /const /=>/backtick"""
    source = dirty_state_js
    assert "beforeunload" in source, "expected dirty-state.js to register a beforeunload listener"
    assert "returnValue" in source, "expected dirty-state.js's beforeunload guard to set evt.returnValue"
    assert "preventDefault" in source, "expected dirty-state.js's beforeunload guard to call evt.preventDefault()"
    # Located by the LISTENER REGISTRATION itself, not the bare word - the
    # file's own header prose discusses the leave-guard by name before the
    # registration appears in source.
    listener_marker = 'addEventListener("beforeunload"'
    assert listener_marker in source, "expected dirty-state.js to call addEventListener(\"beforeunload\", ...)"
    beforeunload_idx = source.index(listener_marker)
    listener_body = source[beforeunload_idx:beforeunload_idx + 400]
    assert "countDifferences" in listener_body, (
        "expected the beforeunload listener's body to reference countDifferences")
    assert 'addEventListener("submit"' in source, "expected dirty-state.js to register a submit listener on the form"
    for forbidden in ("innerHTML", "let ", "const ", "=>", "`"):
        assert forbidden not in source, (
            "forbidden ES5-unsafe/HTML-writing construct found in dirty-state.js: %r" % (forbidden,))


def test_dirty_state_js_references_quiet_preset_attrs(dirty_state_js):
    """dirty-state.js references config_page.QUIET_HOURS_PRESET_ATTR's literal value and the
    three data-preset-* attribute names, and contains none of innerHTML/let /const /=>/backtick"""
    source = dirty_state_js
    for literal in (
            config_page.QUIET_HOURS_PRESET_ATTR, "data-preset-start",
            "data-preset-end", "data-preset-enabled"):
        assert literal in source, "expected dirty-state.js to reference the literal %r" % (literal,)
    for forbidden in ("innerHTML", "let ", "const ", "=>", "`"):
        assert forbidden not in source, (
            "forbidden ES5-unsafe/HTML-writing construct found in dirty-state.js: %r" % (forbidden,))


def test_style_css_carries_no_hide_rule_for_static_save_fallback_attr(served_css):
    """style.css carries NO rule selector referencing STATIC_SAVE_FALLBACK_ATTR any more - the
    hide rule is retired outright, its button now the restored bar's own visible Save - while
    the B1/P0 contract and the dated 27-03/28-08 SUPERSEDED paragraphs all survive in writing
    (CFG-77/CFG-78, 28-08-PLAN.md Task 2)

    The button STATIC_SAVE_FALLBACK_ATTR's hide rule used to target is now the restored bar's
    own visible Save (relocated by Task 1) and its visibility is the bar's OWN `hidden`
    attribute, never a second, independent CSS hide mechanism for the same element. This check
    asserts the RELATIONSHIP (no SELECTOR references it) rather than a raw text count - comments
    MAY (indeed do) still name it in prose, recording the history.
    """
    source = served_css
    assert config_page.STATIC_SAVE_FALLBACK_ATTR in source, (
        "expected style.css to still mention STATIC_SAVE_FALLBACK_ATTR's literal value somewhere "
        "(in prose, recording the history)")
    for rule in css_rules(source):
        for selector in rule.selectors:
            assert config_page.STATIC_SAVE_FALLBACK_ATTR not in selector, (
                "expected NO rule selector anywhere in style.css to still reference %r, but found "
                "one - the hide rule this check used to require is retired outright "
                "(28-08-PLAN.md Task 2, CFG-77/CFG-78); selector: %r"
                % (config_page.STATIC_SAVE_FALLBACK_ATTR, selector))
    # THE SUPERSEDED CONTRACT IS AMENDED IN WRITING, NOT ERASED: the
    # original comment's own distinctive sentences must still be present.
    for distinctive in (
            "PROVEN its own replacement bar is actually live",
            "turned out to still be element PRESENCE, not proven liveness (B1)",
            "B1's proven-liveness fix"):
        assert distinctive in source, (
            "expected the ORIGINAL comment's own sentence %r to survive verbatim - the B1/P0 "
            "contract must be superseded in writing, not deleted" % (distinctive,))
    assert "27-03-PLAN.md" in source and "SUPERSEDED" in source, (
        "expected a dated 27-03-PLAN.md paragraph stating the contract is SUPERSEDED, not merely "
        "that the rule changed")
    assert "28-08-PLAN.md Task 2" in source, (
        "expected a dated 28-08-PLAN.md Task 2 paragraph stating the hide rule itself is now "
        "retired - the button it hid became the bar's own visible Save")


def test_style_css_carries_no_rule_for_the_retired_save_status_region(served_css):
    """style.css carries no live RULE selector for the retired .save-status auto-save status
    region while the comment prose narrating its own retirement survives verbatim - the
    .save-status half of the orphan-rule clause the STATIC_SAVE_FALLBACK_ATTR check above does
    not already cover (CFG-78, 28-09-PLAN.md Task 1)

    `.save-status` (27-04-PLAN.md, CFG-63) - the retired auto-save status region's own selector -
    is deleted outright, not relocated. Uses `css_rules()` over the SERVED stylesheet, checking
    every rule's own selector list rather than a raw substring scan, so a comment merely
    mentioning the class can never trip this.
    """
    source = served_css
    assert "save-status" in source, (
        "expected style.css to still mention save-status somewhere, in prose, narrating its own "
        "retirement")
    save_status_re = re.compile(r"\.save-status\b")
    for rule in css_rules(source):
        for selector in rule.selectors:
            assert not save_status_re.search(selector), (
                "expected NO rule selector anywhere in style.css to still target .save-status - "
                "its own retired region is gone outright (27-04-PLAN.md, CFG-63) and no rule "
                "should still reach for it; selector: %r" % (selector,))


def test_style_css_carries_theme_status_runway_row_and_settings_checkbox_selectors(served_css):
    """style.css declares .theme-status (card-surface token + hover selector), .runway-row (flex
    display), .settings-checkbox input[type="checkbox"] (cleared min-height), and
    .theme-chip-grid/.theme-chip/.theme-chip--selected/.theme-chip__preview (flex display, card
    surface + 160px width, accent border, 56px preview band) - the selectors config_page.py's new
    markup depends on

    quick task 260901-qif / 06.6.4.1.1-05: no Python constant carries these class-name literals,
    so they are asserted directly here, structurally via declarations_for() over the served
    stylesheet rather than a raw index-plus-window scan.
    """
    css = served_css

    theme_status = declarations_for(css, ".theme-status")
    assert "var(--color-dominant)" in " ".join(theme_status.values()), (
        "expected .theme-status's rule body to carry the --color-dominant card-surface token, "
        "got %r" % (theme_status,))
    assert css_rules(css) and any(
        ".theme-status:hover" in rule.selectors for rule in css_rules(css)), (
        "expected style.css to declare a .theme-status:hover selector")

    runway_row = declarations_for(css, ".runway-row")
    assert runway_row.get("display") == "flex", (
        "expected .runway-row's rule body to set display: flex, got %r" % (runway_row,))

    checkbox_decls = declarations_for(css, '.settings-checkbox input[type="checkbox"]')
    assert checkbox_decls.get("min-height") == "0", (
        "expected .settings-checkbox input[type=\"checkbox\"]'s rule body to clear the global "
        "rule's min-height, got %r" % (checkbox_decls,))

    # 06.6.4.1.1-05: the fourth cross-file guard, covering the new
    # .theme-chip* selectors theme_fieldset()'s D-01 chip-grid markup
    # depends on.
    chip_grid = declarations_for(css, ".theme-chip-grid")
    assert chip_grid.get("display") == "flex", (
        "expected .theme-chip-grid's rule body to set display: flex, got %r" % (chip_grid,))

    chip = declarations_for(css, ".theme-chip")
    chip_joined = " ".join(chip.values())
    assert "var(--color-dominant)" in chip_joined, (
        "expected .theme-chip's rule body to carry the --color-dominant card-surface token")
    assert chip.get("width") == "160px", (
        "expected .theme-chip's rule body to set width: 160px, got %r" % (chip,))

    chip_selected = declarations_for(css, ".theme-chip--selected")
    assert "var(--color-accent)" in " ".join(chip_selected.values()), (
        "expected .theme-chip--selected's rule body to carry var(--color-accent)")

    chip_preview = declarations_for(css, ".theme-chip__preview")
    assert chip_preview.get("height") == "56px", (
        "expected .theme-chip__preview's rule body to set height: 56px, got %r" % (chip_preview,))
