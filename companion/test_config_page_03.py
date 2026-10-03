"""Tests handle_post()'s field-level `errors` dict, the retired LED-route/
helper-symbol guards, runway-image detection and runway_fieldset() image
emission, cross-file DOM-contract guards between config_page.py and its
static assets (dirty-state.js, style.css), the theme-chip grid's markup/
selection-state contract, the arrivals/calendar theme override's
clearable contract, and the Aspect card's accordion shape and per-flight
rules editor markup. Some checks fetch style.css or a served JS asset
from a running companion/app.py server rather than reading a file from
disk.
"""
import re
from pathlib import Path

import pytest

import companion.i18n as i18n
import companion.test_config_page_helpers as cp
from companion import app as companion_app
from companion.layout import escape_html
from companion.pages import config_page
from companion.settings import form_post, look
from companion.settings import rules as rules_settings
from companion_app_server import served_asset, served_stylesheet
from companion_markup import (
    at_rule_blocks,
    parse_html,
    css_rules,
    declarations_for,
    rule_indices,
    rules_with_selector,
)
from server import device_config
from server.plane import colour_rules


@pytest.fixture(scope="module")
def app(module_app_server_factory):
    """A read-only companion/app.py server this module's checks fetch the
    served stylesheet/JS assets from, instead of opening them from disk."""
    return module_app_server_factory()


@pytest.fixture(scope="module")
def served_css(app):
    """The stylesheet companion/app.py actually serves."""
    return served_stylesheet(app)


@pytest.fixture(scope="module")
def dirty_state_js(app):
    """companion/static/dirty-state.js's served text, fetched over HTTP
    instead of opened from disk."""
    return served_asset(app, "/static/dirty-state.js")


@pytest.fixture(scope="module")
def theme_preview_js(app):
    """companion/static/theme-preview.js's served text, fetched over HTTP
    instead of opened from disk."""
    return served_asset(app, "/static/theme-preview.js")


# ======================================================================
# Section 1: handle_post()'s optional `errors` dict parameter.
# ======================================================================

def test_handle_post_wake_interval_empty_or_absent_leaves_unchanged(tmp_path):
    """after a save that stored wake_interval_s 120, a later submission with wake_interval_s as
    the empty string, and another with the key absent entirely, both return the saved flash key
    and leave the stored value at 120"""
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

    This module's own local HH:MM shape gate (_QUIET_HOURS_TIME_RE) is a
    UX pre-check only - save_device_config()'s identical gate stays authoritative. This pins the
    two never silently drifting apart, over the exact table above.
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
# Section 2: render() repopulates every control from a rejected save's
# own submission.
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
    """render(ctx, errors={"wake_interval_s": ERROR_WAKE_INTERVAL_RANGE}, submitted={"wake_interval_s": "7"})
    renders the message once, echoes value="7" back into the input, and sets aria-invalid plus a
    matching aria-describedby"""
    error_message = form_post.ERROR_WAKE_INTERVAL_RANGE
    rendered = config_page.render(
        _TASK2_BASE_CTX, errors={"wake_interval_s": error_message},
        submitted={"wake_interval_s": "7"})
    assert rendered.count(error_message) == 1, (
        "expected the error message to render exactly once, got %d" % rendered.count(error_message))
    assert 'value="7"' in rendered, "expected the submitted value 7 to be echoed back into the input"
    input_match = re.search(
        r'<input type="number" id="[^"]*" name="wake_interval_s"[^>]*>', rendered)
    assert input_match, "expected the wake_interval_s input to still be present"
    assert 'aria-invalid="true"' in input_match.group(0), "expected aria-invalid=\"true\" on the errored input"
    describedby_match = re.search(r'aria-describedby="([^"]+)"', input_match.group(0))
    assert describedby_match, "expected an aria-describedby attribute on the errored input"
    # The value is a SPACE-SEPARATED list (the hint id first, then the
    # error id), not a single id.
    ids = describedby_match.group(1).split(" ")
    assert len(ids) == 2, "expected exactly two space-separated ids (hint, then error), got %r" % (ids,)
    assert ids[0] == config_page.WAKE_INTERVAL_SECTION_CAPTION_ID, (
        "expected the hint id to come first, got %r" % (ids,))
    for token in ids:
        assert ('id="%s"' % token) in rendered, (
            "expected an element carrying id=%r matching aria-describedby" % (token,))


def test_render_submitted_theme_id_checked_even_when_differs_from_stored():
    """a submitted theme id is rendered as the CHECKED radio even when it differs from the
    stored theme"""
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
    """_calendar_connection_html(..., errors={"calendar_url": ERROR_CALENDAR_URL_INVALID}) renders
    the error message under the field while the write-only field itself still carries no value
    attribute at all

    The write-only calendar_url field's own `errors` parameter now lives directly on
    _calendar_connection_html() - it never accepts `submitted` at all (nothing to repopulate:
    the one field it renders is write-only), so there is no submitted URL for it to echo.
    """
    error_message = form_post.ERROR_CALENDAR_URL_INVALID
    rendered, _disconnect_form_html = config_page._calendar_connection_html(
        False, False, None, None, "2026-09-07T09:12:04+00:00", 0,
        errors={"calendar_url": error_message})
    assert error_message in rendered, "expected the calendar_url error message to render"
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
# Section 3: the legacy no-errors-arg contract is intact even for a
# rejected save.
# ======================================================================

def test_handle_post_rejected_save_without_errors_arg_still_returns_save_failed(tmp_path):
    """a rejected save still returns FLASH_SAVE_FAILED from handle_post() when no errors dict is
    passed (the legacy contract is intact)"""
    ctx = {"state_dir": str(tmp_path)}
    flash_key = config_page.handle_post({"theme": "not-a-real-theme"}, ctx)
    assert flash_key == config_page.FLASH_SAVE_FAILED, (
        "expected FLASH_SAVE_FAILED with no errors argument, got %r" % (flash_key,))


# ======================================================================
# Section 4: the retired separate LED route/helper symbols stay gone;
# five retired helper constants stay gone too.
# ======================================================================

def test_render_has_no_action_pointing_at_retired_led_route():
    """render() emits no action pointing at the retired separate LED form path

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
    handle_led_post (all three retired)"""
    for name in ("led_fieldset", "led_section", "handle_led_post"):
        assert not hasattr(config_page, name), (
            "expected config_page to expose no %r attribute" % name)


def test_config_page_exposes_no_retired_helper_or_description_symbols():
    """companion.pages.config_page exposes none of THEME_HELPER_TEXT/THEME_SECTION_DESCRIPTION/
    RUNWAY_HELPER_TEXT/RUNWAY_SECTION_DESCRIPTION/LED_HELPER_TEXT (all five retired)"""
    retired = (
        "THEME_HELPER_TEXT", "THEME_SECTION_DESCRIPTION",
        "RUNWAY_HELPER_TEXT", "RUNWAY_SECTION_DESCRIPTION",
        "LED_HELPER_TEXT")
    for name in retired:
        assert not hasattr(config_page, name), (
            "expected config_page to expose no %r attribute" % name)


# ======================================================================
# Section 5: runway-image existence detection - each check uses its own
# tmp_path image_dir and never touches the real companion/static/.
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
    nothing at all under tmp_path is the more direct way to prove that.
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
# Section 6: runway_fieldset() image emission - unit checks against the
# string output only, no filesystem/subprocess involved.
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
    number/heading labels (graceful fallback)"""
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
# dirty-state.js and style.css.
# ======================================================================

def test_dirty_state_js_delegates_change_and_input_at_document_level_and_has_no_forbidden_syntax(dirty_state_js):
    """dirty-state.js references DIRTY_SECTION_ATTR again (dirtySectionLabels() restored) but
    carries neither the retired dirty-ready nor dirty-shown marker, delegates BOTH change AND
    input at document level gated on e.target.form === form with no surviving
    form.addEventListener("change"/"input" registration, and contains none of
    innerHTML/let /const /=>/backtick

    dirtySectionLabels() restores its own [data-dirty-section] reader and the dual change/input
    delegation. The dirty-ready/dirty-shown MARKERS do NOT return - this restoration's own
    clearance mechanism is :has(.dirty-bar), which needs no script-written marker class.
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
    """the live pictures follow the checked look without a timer: every look target carries a
    server-rendered data-preview-src-template the script fills with the theme id, the script
    swaps an <img> src only from that template, never through a timer, and keeps exposing
    window.SkyPaneLivePreview.refresh() for dirty-state.js's Cancel handler

    The swap must be EVENT-DRIVEN, never timed: a timed swap drifts from the selection it
    illustrates. `change` is when the selection genuinely changed.
    """
    rendered = config_page.render({
        "device_config": {"theme": "white", "tracked_runway": "3"},
        "colour_rules": {kind: {} for kind in colour_rules.RULE_KINDS},
        "poll_cooldown_remaining": 0,
    }, scope=config_page.SCOPE_DISPLAY)
    templates = re.findall(r'data-preview-src-template="([^"]+)"', rendered)
    assert len(templates) == 4, (
        "expected a preview template on each of the four look targets (departures, arrivals, "
        "calendar, a new special look), got %r" % (templates,))
    for template in templates:
        assert template.startswith(config_page.FRAME_PREVIEW_ROUTE_PREFIX + "__THEME__.png?"), template
    js = cp.strip_js_line_and_block_comments(theme_preview_js)
    for token in ("data-preview-src-template", "__THEME__", '"change"'):
        assert token in js, "expected theme-preview.js to use %r" % (token,)
    for banned in ("setTimeout", "setInterval", "requestAnimationFrame"):
        assert banned not in js, "theme-preview.js must stay timer-free (%r found)" % (banned,)
    assert "SkyPaneLivePreview" in js and "refresh" in js, (
        "expected theme-preview.js to keep exposing window.SkyPaneLivePreview.refresh() - "
        "dirty-state.js's Cancel handler calls it after form.reset(), which fires no change event")
    assert declarations_for(served_css, ".look-frame__image").get("display") == "block"


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


# --- Stylesheet vocabulary for the selection-state checks below ---------

_HAS_QUERY = ("@supports selector(:has(*))",)
_ACCENT_WASH = "color-mix(in srgb, var(--color-accent) 12%, transparent)"
_INSET_RING = "inset 0 0 0 2px var(--color-accent)"
_MUTED_TEXT = "color-mix(in srgb, var(--color-text) 70%, transparent)"


def _declared(css, selector, at_rules=()):
    """`declarations_for()` for `selector` in exactly the `at_rules`
    context, failing with a readable message when no rule declares it
    there."""
    decls = declarations_for(css, selector, at_rules=at_rules) if rules_with_selector(css, selector) else {}
    assert decls, "expected style.css to declare %r in the at-rule context %r" % (selector, at_rules)
    return decls


def _assert_constant_border_and_inset_ring(decls, label):
    assert decls.get("border-color") == "var(--color-accent)", (
        "%s must recolour its constant 1px border to the accent, got %r" % (label, decls))
    assert decls.get("box-shadow") == _INSET_RING, (
        "%s must carry T6's inset accent ring, got %r" % (label, decls))
    assert not decls.get("border", "").startswith("2px") and decls.get("border-width") != "2px", (
        "%s must never declare a 2px border again (T6's layout shift), got %r" % (label, decls))


def _assert_one_has_feature_query_block(css):
    count = at_rule_blocks(css).count(_HAS_QUERY[0])
    assert count == 1, "expected exactly one %s block, got %d" % (_HAS_QUERY[0], count)


def test_style_css_carries_no_hide_rule_for_static_save_fallback_attr(served_css):
    """style.css carries NO rule selector referencing STATIC_SAVE_FALLBACK_ATTR any more - the
    hide rule is retired outright, its button now the restored bar's own visible Save - while
    the older SUPERSEDED paragraphs all survive in writing

    The button STATIC_SAVE_FALLBACK_ATTR's hide rule used to target is now the restored bar's
    own visible Save (relocated by Task 1) and its visibility is the bar's OWN `hidden`
    attribute, never a second, independent CSS hide mechanism for the same element. This check
    asserts the RELATIONSHIP (no SELECTOR references it) over the parsed stylesheet. The
    label's "survive in writing" clauses were about stylesheet comments, which render
    nothing, so they are not asserted.
    """
    for rule in css_rules(served_css):
        for selector in rule.selectors:
            assert config_page.STATIC_SAVE_FALLBACK_ATTR not in selector, (
                "expected NO rule selector anywhere in style.css to still reference %r, but found "
                "one - the hide rule this check used to require is retired outright "
                "(28-08-PLAN.md Task 2, CFG-77/CFG-78); selector: %r"
                % (config_page.STATIC_SAVE_FALLBACK_ATTR, selector))


def test_style_css_carries_no_rule_for_the_retired_save_status_region(served_css):
    """style.css carries no live RULE selector for the retired .save-status auto-save status
    region while the comment prose narrating its own retirement survives verbatim - the
    .save-status half of the orphan-rule clause the STATIC_SAVE_FALLBACK_ATTR check above does
    not already cover

    `.save-status` - the retired auto-save status region's own selector -
    is deleted outright, not relocated. Uses `css_rules()` over the SERVED stylesheet, checking
    every rule's own selector list, so a comment merely mentioning the class can never trip
    this. The comment-prose clause of the label is not asserted: a comment renders nothing.
    """
    save_status_re = re.compile(r"\.save-status\b")
    for rule in css_rules(served_css):
        for selector in rule.selectors:
            assert not save_status_re.search(selector), (
                "expected NO rule selector anywhere in style.css to still target .save-status - "
                "its own retired region is gone outright (27-04-PLAN.md, CFG-63) and no rule "
                "should still reach for it; selector: %r" % (selector,))


def test_style_css_carries_theme_status_runway_row_and_settings_checkbox_selectors(served_css):
    """style.css declares .theme-status (card-surface token + hover selector), .runway-row (flex
    display), .settings-checkbox input[type="checkbox"] (cleared min-height), and the look
    card's own selectors: the two-column .look-card__grid, the 48px .look-cell target, and the
    .look-sheet popover on the card surface with the pop shadow token"""
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

    grid = declarations_for(css, ".look-card__grid")
    assert grid.get("display") == "grid", grid
    assert "repeat(2" in grid.get("grid-template-columns", ""), grid
    cell = declarations_for(css, ".look-cell")
    assert cell.get("width") == "48px" and cell.get("height") == "48px", (
        "expected every table cell to be a 48px target (over the 44px floor), got %r" % (cell,))
    sheet = declarations_for(css, ".look-sheet")
    assert sheet.get("background") == "var(--color-dominant)", sheet
    assert sheet.get("box-shadow") == "var(--shadow-pop)", sheet


# ======================================================================
# Section 8: 06.6.4.1.1-05 - the theme-chip grid's markup contract.
# ======================================================================

def test_theme_chip_preview_src_points_at_the_real_route_prefix_for_every_theme():
    """every theme radio in the departures table carries a data-preview-src pointing at
    FRAME_PREVIEW_ROUTE_PREFIX + its own registry id, departing state and large size, and the
    big departures picture's <img src> is that same URL for the saved theme"""
    rendered = config_page.render({
        "device_config": {"theme": "blue", "tracked_runway": "3"},
        "colour_rules": {kind: {} for kind in colour_rules.RULE_KINDS},
        "poll_cooldown_remaining": 0,
    }, scope=config_page.SCOPE_DISPLAY)
    start, end = cp.aspect_usage_row_bounds(rendered, config_page.COLOUR_USAGE_DEPARTURES)
    segment = rendered[start:end]
    for theme_id in device_config.THEME_IDS:
        expected_src = escape_html(
            "%s%s.png?state=departing&size=large" % (config_page.FRAME_PREVIEW_ROUTE_PREFIX, theme_id))
        assert 'data-preview-src="%s"' % expected_src in segment, (
            "expected the %r radio to carry %r" % (theme_id, expected_src))
    assert 'data-look-image src="%s"' % escape_html(
        "%sblue.png?state=departing&size=large" % config_page.FRAME_PREVIEW_ROUTE_PREFIX) in segment


def test_theme_chip_swatch_dots_carry_real_palette_hex_values():
    """every table cell's swatch fills carry the panel's own palette values: the theme's field
    ink, and for a band theme its band ink, each computed from server.panel_format's
    PALETTE_RGB through look.colour_hex(), never a literal"""
    rendered = look.look_table_html("theme", "white", "Departures", lambda theme_id: "")
    root = parse_html(rendered)
    for cell in root.find_all("label"):
        radio = cell.find("input")
        theme_id = radio.attrs["value"]
        theme = device_config.THEMES[theme_id]
        fills = [node.attrs.get("fill") for node in cell.find_all() if node.attrs.get("fill")]
        expected = {look._palette_hex(theme["departing_index"])}
        if "band_index" in theme:
            expected.add(look._palette_hex(theme["band_index"]))
        assert expected <= set(fills), (theme_id, fills)


def test_theme_chip_radio_hidden_and_check_glyph_present_on_every_chip():
    """every look table radio carries class="visually-hidden" (never display:none) inside its
    own <label>, and every grid cell names its look in visually-hidden text, so keyboard and
    no-script selection keep working natively"""
    rendered = look.look_table_html("theme", "white", "Departures", lambda theme_id: "")
    root = parse_html(rendered)
    radios = [node for node in root.find_all("input") if node.attrs.get("type") == "radio"]
    assert len(radios) == len(device_config.THEME_IDS)
    for radio in radios:
        assert radio.attrs.get("class") == "visually-hidden"
        assert radio.parent.tag == "label"
        assert radio.parent.text(), "expected every option to carry a text name"
    assert "display:none" not in rendered and "display: none" not in rendered


# ======================================================================
# Section 9: the arrivals-override control, its revealed second chip
# grid, and handle_post()'s clearable-checkbox contract.
# ======================================================================

def test_aspect_arrivals_row_carries_leading_option_no_checkbox():
    """the arrivals table carries a leading Same-as-departures radio submitting the empty string
    (form=settings-form), and no checkbox-based override control exists anywhere on the page

    This control used to be a checkbox; the empty-string radio is what keeps the clear signal
    honest now.
    """
    rendered = config_page.render({
        "device_config": {"theme": "white", "tracked_runway": "3"},
        "colour_rules": {kind: {} for kind in colour_rules.RULE_KINDS},
        "poll_cooldown_remaining": 0,
    }, scope=config_page.SCOPE_DISPLAY)
    root = parse_html(rendered)
    leading = [
        node for node in root.find_all("input")
        if node.attrs.get("name") == "theme_arriving" and node.attrs.get("value") == ""]
    assert len(leading) == 1
    assert leading[0].attrs.get("form") == config_page.SETTINGS_FORM_ID
    assert leading[0].parent.text() == i18n.t(config_page.SAME_AS_DEPARTURES_LABEL)
    assert 'type="checkbox"' not in rendered, "expected no <input type=\"checkbox\"> anywhere in the look card"


def test_aspect_arrivals_override_preselects_the_override_not_same_as_departures():
    """a stored theme_arriving override pre-selects the OVERRIDE (not Same-as-departures, not the
    departures theme) in the arrivals table, reads the override's own look back under the
    picture, and leaves the calendar row's own Same-as-departures state unaffected in the same
    render"""
    rendered = config_page.render({
        "device_config": {
            "theme": "white", "tracked_runway": "3", "theme_arriving": "black"},
        "colour_rules": {kind: {} for kind in colour_rules.RULE_KINDS},
        "poll_cooldown_remaining": 0,
    }, scope=config_page.SCOPE_DISPLAY)
    arrivals_start, arrivals_end = cp.aspect_usage_row_bounds(
        rendered, config_page.COLOUR_USAGE_ARRIVALS)
    arrivals_segment = rendered[arrivals_start:arrivals_end]
    assert re.search(r'name="theme_arriving" value="black"[^>]*checked', arrivals_segment), (
        "expected the arrivals table's checked radio to be the stored override (black)")
    assert not re.search(r'name="theme_arriving" value=""[^>]*checked', arrivals_segment), (
        "expected the leading Same-as-departures option to NOT be checked once an override is set")
    assert not re.search(r'name="theme_arriving" value="white"[^>]*checked', arrivals_segment), (
        "expected the departures theme (white) to NOT be marked selected in the arrivals table")
    sentence = re.search(r'data-look-sentence>([^<]*)<', arrivals_segment).group(1)
    assert sentence == escape_html(look.look_sentence("black")), sentence
    calendar_start, calendar_end = cp.aspect_usage_row_bounds(
        rendered, config_page.COLOUR_USAGE_CALENDAR)
    calendar_segment = rendered[calendar_start:calendar_end]
    assert re.search(r'name="calendar_theme_id" value=""[^>]*checked', calendar_segment), (
        "expected the calendar row's leading Same-as-departures option to still be checked, "
        "unaffected by the arrivals override")


def test_handle_post_theme_arriving_valid_id_persists_chosen_id(tmp_path):
    """handle_post with a valid theme_arriving id persists it, with no checkbox field involved"""
    tmpdir = str(tmp_path)
    ctx = {"state_dir": tmpdir}
    flash_key = config_page.handle_post(
        {
            "theme": "white", "tracked_runway": device_config.DEFAULT_RUNWAY_ID,
            "theme_arriving": "black",
        },
        ctx)
    assert flash_key == config_page.FLASH_SAVED, "expected FLASH_SAVED, got %r" % (flash_key,)
    on_disk = device_config.load_device_config(tmpdir)
    assert on_disk["theme_arriving"] == "black", (
        "expected theme_arriving 'black' on disk, got %r" % (on_disk["theme_arriving"],))


def test_handle_post_theme_arriving_empty_string_clears_previous_override(tmp_path):
    """handle_post with theme_arriving='' clears a previously-set override back to None"""
    tmpdir = str(tmp_path)
    ctx = {"state_dir": tmpdir}
    config_page.handle_post(
        {
            "theme": "white", "tracked_runway": device_config.DEFAULT_RUNWAY_ID,
            "theme_arriving": "black",
        },
        ctx)
    flash_key = config_page.handle_post(
        {
            "theme": "white", "tracked_runway": device_config.DEFAULT_RUNWAY_ID,
            "theme_arriving": "",
        },
        ctx)
    assert flash_key == config_page.FLASH_SAVED, "expected FLASH_SAVED, got %r" % (flash_key,)
    on_disk = device_config.load_device_config(tmpdir)
    assert on_disk["theme_arriving"] is None, (
        "submitting theme_arriving='' failed to clear the override, got %r" % (on_disk["theme_arriving"],))


def test_handle_post_calendar_theme_id_empty_string_saves_as_none(tmp_path):
    """handle_post with calendar_theme_id='' saves and reads back as None, mirroring
    theme_arriving's own empty-string clear signal

    calendar_theme_id never had a checkbox, so once its gate exempts "", the existing
    pass-through plus normalise_calendar_theme_id("")'s own documented None-degrade already does
    the right thing (no second resolution block needed).
    """
    tmpdir = str(tmp_path)
    cp.write_device_config(tmpdir, "black", "3")
    config_page.handle_post({"calendar_theme_id": "white"}, {"state_dir": tmpdir})
    flash_key = config_page.handle_post({"calendar_theme_id": ""}, {"state_dir": tmpdir})
    assert flash_key == config_page.FLASH_SAVED, "expected FLASH_SAVED, got %r" % (flash_key,)
    on_disk = device_config.load_device_config(tmpdir)
    assert on_disk["calendar_theme_id"] is None, (
        "submitting calendar_theme_id='' failed to clear the override, got %r" % (on_disk["calendar_theme_id"],))


@pytest.mark.parametrize(
    "field, payload",
    [
        ("theme_arriving", "nope"), ("theme_arriving", " "),
        ("theme_arriving", "WHITE "), ("calendar_theme_id", "nope"),
        ("calendar_theme_id", " "), ("calendar_theme_id", "WHITE "),
    ],
    ids=[
        "theme_arriving-invalid-id", "theme_arriving-bare-space",
        "theme_arriving-uppercase-trailing-space", "calendar_theme_id-invalid-id",
        "calendar_theme_id-bare-space", "calendar_theme_id-uppercase-trailing-space",
    ],
)
def test_handle_post_crafted_non_member_theme_and_calendar_values_still_rejected(tmp_path, field, payload):
    """handle_post still rejects a crafted non-member theme_arriving/calendar_theme_id value (a
    plain invalid id, a bare space, a near-miss uppercase/trailing-space variant) and writes
    nothing - the empty-string exemption does not widen the gate to anything else"""
    tmpdir = str(tmp_path)
    cp.write_device_config(tmpdir, "black", "3")
    before = Path(device_config.device_config_path(tmpdir)).read_bytes()
    flash_key = config_page.handle_post({field: payload}, {"state_dir": tmpdir})
    after = Path(device_config.device_config_path(tmpdir)).read_bytes()
    assert flash_key == config_page.FLASH_SAVE_FAILED, (
        "expected FLASH_SAVE_FAILED for %s=%r, got %r" % (field, payload, flash_key))
    assert before == after, "expected device_config.json to be byte-identical for %s=%r, it changed" % (field, payload)


@pytest.mark.parametrize(
    "payload",
    ["chartreuse", "../../etc/passwd", "sky'; DROP TABLE flights; --"],
    ids=["plain-invalid-id", "path-traversal-shaped", "sql-shaped"],
)
def test_handle_post_nonmember_theme_arriving_rejected(tmp_path, payload):
    """handle_post with a non-member theme_arriving (a plain invalid id, a path-traversal-shaped
    payload, and a SQL-shaped payload) rejects the whole submission and writes nothing - '' is
    explicitly exempted from this rejection"""
    tmpdir = str(tmp_path)
    cp.write_device_config(tmpdir, "black", "3")
    before = Path(device_config.device_config_path(tmpdir)).read_bytes()
    ctx = {"state_dir": tmpdir}
    flash_key = config_page.handle_post({"theme_arriving": payload}, ctx)
    after = Path(device_config.device_config_path(tmpdir)).read_bytes()
    assert flash_key == config_page.FLASH_SAVE_FAILED, (
        "expected FLASH_SAVE_FAILED for theme_arriving=%r, got %r" % (payload, flash_key))
    assert before == after, (
        "expected device_config.json to be byte-identical for theme_arriving=%r, it changed" % (payload,))


def test_handle_post_theme_arriving_partial_post_still_carries_other_fields(tmp_path):
    """a post carrying only theme_arriving still carries the existing theme/runway forward
    unchanged"""
    tmpdir = str(tmp_path)
    cp.write_device_config(tmpdir, "black", "06-24")
    ctx = {"state_dir": tmpdir}
    flash_key = config_page.handle_post({"theme_arriving": "white"}, ctx)
    assert flash_key == config_page.FLASH_SAVED, "expected FLASH_SAVED, got %r" % (flash_key,)
    on_disk = device_config.load_device_config(tmpdir)
    assert on_disk["tracked_runway"] == "06-24", (
        "expected the existing runway to be carried forward unchanged, got %r" % (on_disk,))
    assert on_disk["theme"] == "black", (
        "expected the existing theme to be carried forward unchanged, got %r" % (on_disk,))
    assert on_disk["theme_arriving"] == "white", (
        "expected theme_arriving 'white' on disk, got %r" % (on_disk["theme_arriving"],))


def test_theme_arriving_clearable_contract_full_round_trip(tmp_path):
    """the clearable contract: a save with a chosen arrivals theme
    persists it, then a save with theme_arriving='' clears it back to None while every other
    setting survives unchanged

    Named so a failure says plainly that the empty-string clear signal stopped working.
    """
    tmpdir = str(tmp_path)
    ctx = {"state_dir": tmpdir}
    first = config_page.handle_post(
        {
            "theme": "white", "tracked_runway": "06-24",
            "led_enabled": config_page.LED_CHECKBOX_VALUE,
            "theme_arriving": "black",
        },
        ctx)
    assert first == config_page.FLASH_SAVED, "expected the first save to return FLASH_SAVED, got %r" % (first,)
    after_first = device_config.load_device_config(tmpdir)
    assert after_first["theme_arriving"] == "black", (
        "expected theme_arriving 'black' to persist after the first save, got %r"
        % (after_first["theme_arriving"],))

    second = config_page.handle_post(
        {
            "theme": "white", "tracked_runway": "06-24",
            "led_enabled": config_page.LED_CHECKBOX_VALUE,
            "theme_arriving": "",
        },
        ctx)
    assert second == config_page.FLASH_SAVED, "expected the second (clearing) save to return FLASH_SAVED, got %r" % (second,)
    after_second = device_config.load_device_config(tmpdir)
    assert after_second["theme_arriving"] is None, (
        "theme_arriving='' failed to clear the override - expected theme_arriving None, got %r"
        % (after_second["theme_arriving"],))
    assert (
        after_second["theme"] == "white"
        and after_second["tracked_runway"] == "06-24"
        and after_second["led_enabled"] is True
    ), "expected every other setting to survive the second save unchanged, got %r" % (after_second,)


def test_settings_page_has_zero_fieldsets_and_four_dirty_sections():
    """the rendered Settings page contains no <fieldset> and no <legend>, and exactly four
    data-dirty-section groups (Runway/Diagnostic LED/Quiet hours/Wake interval -
    Theme, Calendar and Display each have no entry on this legacy scope)

    dirty-state.js's section-aware walk still finds each group as one addressable unit.
    """
    rendered = config_page.render({
        "device_config": {"theme": "white", "tracked_runway": "3", "led_enabled": True},
        "poll_cooldown_remaining": 0,
    })
    assert "<fieldset" not in rendered, "expected zero <fieldset> elements on the rendered Settings page"
    assert "<legend" not in rendered, "expected zero <legend> elements on the rendered Settings page"
    assert rendered.count(config_page.DIRTY_SECTION_ATTR) == 4, (
        "expected exactly 4 %s occurrences (Runway/Diagnostic LED/Quiet hours/Wake interval), "
        "got %d" % (config_page.DIRTY_SECTION_ATTR, rendered.count(config_page.DIRTY_SECTION_ATTR)))


# ======================================================================
# Section 10: the selected-card visual treatment, live vs.
# saved-but-not-live, style.css structural checks fetched from the served
# stylesheet rather than opened from disk.
# ======================================================================

def test_selected_runway_card_and_theme_chip_carry_a_background_wash(served_css):
    """both .runway-card--selected and a checked look-table cell carry a 12%-accent background
    wash (color-mix), matching .theme-form .theme-option--active's established active-state
    idiom, with a constant 1px border whose 2px accent signal is an inset ring

    The developer reported that, across the whole site, the selected element was "very hard to
    see" - a border-only + check-glyph treatment was too subtle at density.
    """
    css = served_css
    runway = _declared(css, ".runway-card--selected")
    _assert_constant_border_and_inset_ring(runway, ".runway-card--selected")
    assert runway.get("background") == _ACCENT_WASH, (
        "expected .runway-card--selected to carry the same 12%%-accent background wash "
        ".theme-form .theme-option--active uses, got %r" % (runway,))
    for selector in (".look-cell:has(input:checked)", ".look-option:has(input:checked)"):
        live = _declared(css, selector, at_rules=_HAS_QUERY)
        _assert_constant_border_and_inset_ring(live, selector)
        assert live.get("background") == _ACCENT_WASH, (
            "expected %s to carry the 12%%-accent wash, got %r" % (selector, live))


def test_strong_selected_treatment_is_keyed_to_the_live_checked_radio(served_css):
    """the strong selected treatment (border, wash, check glyph, and a hover restore) is keyed
    to live :has(input:checked) state inside one @supports selector(:has(*)) block for both
    .runway-card and the look table's cells and options, with the runway's --selected fallback
    surviving, its transition declared on the base rule and the feature-query block declaring no
    transition at all"""
    css = served_css
    _assert_one_has_feature_query_block(css)

    def _live(selector):
        return _declared(css, selector, at_rules=_HAS_QUERY)

    hover = _live(".runway-card:has(input:checked):hover")
    assert hover.get("border-color") == "var(--color-accent)"
    assert hover.get("box-shadow") == _INSET_RING
    runway_live = _live(".runway-card:has(input:checked)")
    _assert_constant_border_and_inset_ring(runway_live, ".runway-card:has(input:checked)")
    assert runway_live.get("background") == _ACCENT_WASH
    assert _live(".runway-card:has(input:checked) .runway-card__check").get("display") == "inline-flex"
    for selector in (".look-cell:has(input:checked)", ".look-option:has(input:checked)",
                     ".look-dot:has(input:checked)", ".look-seg__option:has(input:checked)"):
        _live(selector)
    for selector in (".runway-card--selected", ".runway-card--selected .runway-card__check"):
        _declared(css, selector)
    transition = _declared(css, ".runway-card").get("transition", "")
    for prop in ("transform", "border-color", "box-shadow", "background-color"):
        assert prop in transition, (".runway-card", prop, transition)
    assert "var(--motion-fast)" in transition
    runway_scale = _declared(css, ".runway-card--selected").get("transform")
    assert _live(".runway-card:has(input:checked)").get("transform") == runway_scale
    assert _live(".runway-card--selected:not(:has(input:checked))").get("transform") == "none"
    for rule in css_rules(css):
        if _HAS_QUERY[0] in rule.at_rules:
            for prop, value in rule.declarations:
                assert "transition" not in prop and "transition" not in value, (
                    "the ONE @supports selector(:has(*)) block declares a transition on %r"
                    % (rule.selectors,))


def test_destructive_disconnect_is_secondary_and_selection_is_free_and_focusable_after_the_accordion_rebuild(served_css):
    """the destructive Disconnect control keeps its secondary, element-qualified specificity AND
    its source-order relationship against button[type="submit"], and the look table's checked
    cell is keyed to .look-cell:has(input:checked) inside the file's one @supports
    selector(:has(*)) block with a visible focus ring on the hidden radio's label"""
    css = served_css
    submit = rule_indices(css, 'button[type="submit"]', at_rules=())
    disconnect = rule_indices(css, "button.calendar-disconnect-btn", at_rules=())
    assert submit, 'expected style.css to declare a top-level button[type="submit"] rule'
    assert disconnect, (
        "expected style.css to declare a top-level, element-qualified "
        "button.calendar-disconnect-btn rule")
    assert min(disconnect) > max(submit), (
        "expected every button.calendar-disconnect-btn rule to come AFTER every "
        'button[type="submit"] rule - at equal (0,1,1) specificity the LATER rule wins')
    _assert_one_has_feature_query_block(css)
    cell = _declared(css, ".look-cell:has(input:checked)", at_rules=_HAS_QUERY)
    assert cell.get("border-color") == "var(--color-accent)"
    assert cell.get("box-shadow") == _INSET_RING
    focus = _declared(css, ".look-cell:has(input:focus-visible)", at_rules=_HAS_QUERY)
    assert focus.get("outline", "").startswith("2px solid var(--color-accent)"), focus


def test_calendar_fusion_css_retired_from_the_stylesheet(served_css):
    """style.css carries neither retired Calendar-card fusion selector
    (.page-section:has(+ .calendar-disconnect-form), .calendar-disconnect-form) anywhere

    Both retired fusion rules must be gone from the real stylesheet, not merely dead-but-present
    - a plan that deletes the merged card's separate-siblings markup while leaving this CSS
    behind would ship dead rules that no longer match anything.
    """
    retired = re.compile(r"\.calendar-disconnect-form(?![-\w])")
    for rule in css_rules(served_css):
        for selector in rule.selectors:
            assert not retired.search(selector), (
                "expected the retired Calendar-card fusion selector to be gone from style.css, "
                "found %r" % (selector,))


def test_saved_but_unchecked_card_degrades_to_a_quiet_current_marker(served_css):
    """the saved-but-no-longer-live --selected runway card degrades to an accent-free dashed
    70%-muted ring with its check glyph cleared and a "Current" ::after tag read from the
    server-rendered, translated data-current-label attribute; the saved look-table option keeps
    an accent-free dashed muted ring of its own once another one is picked"""
    css = served_css
    rules = css_rules(css)
    for selector in (".runway-card--selected:not(:has(input:checked))",
                     ".look-cell--saved:not(:has(input:checked))",
                     ".look-option--saved:not(:has(input:checked))"):
        joined = " ".join(_declared(css, selector, at_rules=_HAS_QUERY).values())
        assert "dashed" in joined, "%r must use a dashed ring, not a solid one" % (selector,)
        assert _MUTED_TEXT in joined, (
            "%r must use the established 70%%-muted-text colour, not a new strength" % (selector,))
        assert "var(--color-accent)" not in joined, (
            "%r must be accent-free - the quiet marker signals 'saved', not 'selected'" % (selector,))
    assert _declared(
        css, ".runway-card--selected:not(:has(input:checked)) .runway-card__check",
        at_rules=_HAS_QUERY).get("display") == "none"
    current_value = "attr(%s)" % config_page.CURRENT_BADGE_ATTR
    contents = [(rule.selectors, value) for rule in rules
                for prop, value in rule.declarations if prop == "content"]
    assert [selectors for selectors, value in contents if value == current_value] == [
        (".runway-card--selected:not(:has(input:checked))::after",)], contents
    assert not [value for _, value in contents if value.strip("\"'") == "Current"]
    french = [value for rule in rules for _, value in rule.declarations if "actuel" in value.lower()]
    assert not french, "expected zero French copy for 'current' in any declaration, got %r" % (french,)
    rendered = look.look_table_html("theme", "red", "Departures", lambda theme_id: "")
    root = parse_html(rendered)
    saved = root.find_all("label", cls="look-cell--saved")
    assert len(saved) == 1 and saved[0].find("input").attrs["value"] == "red"


def test_style_css_carries_section_caption_and_the_restored_dirty_bar_rules(served_css):
    """style.css declares .section-caption (70% muted color-mix) AND the restored .dirty-bar -
    fixed-positioned at both breakpoints, its [hidden] override and its Cancel button's own
    quiet-wash override all present"""
    css = served_css

    caption = _declared(css, ".section-caption")
    assert _MUTED_TEXT in " ".join(caption.values()), (
        "expected .section-caption to carry the 70%% color-mix muted idiom, got %r" % (caption,))

    # Three `.dirty-bar` rules: the base rule (flex row, entrance
    # animation - no position declared) plus one per breakpoint (each
    # setting position: fixed with its own geometry). Exactly two carry
    # position: fixed - never zero (a breakpoint left position: static)
    # and never three (the base rule itself should not set it).
    dirty_bar_rules = rules_with_selector(css, ".dirty-bar")
    assert len(dirty_bar_rules) == 3, (
        "expected exactly three `.dirty-bar` rules (the base rule plus one per breakpoint), "
        "got %r" % ([rule.at_rules for rule in dirty_bar_rules],))
    fixed = [rule.at_rules for rule in dirty_bar_rules
             if dict(rule.declarations).get("position") == "fixed"]
    assert len(fixed) == 2 and () not in fixed, (
        "expected exactly the two breakpoint `.dirty-bar` rules to set position: fixed, got %r"
        % (fixed,))
    assert _declared(css, ".dirty-bar[hidden]").get("display") == "none", (
        "expected the `.dirty-bar[hidden] { display: none; }` override to survive")
    assert _declared(css, ".dirty-bar__cancel"), (
        "expected `.dirty-bar__cancel`'s own quiet-wash override to survive")


def test_skypane_bar_arrive_keyframes_is_referenced_again_by_the_restored_bar(served_css):
    """the @keyframes skypane-bar-arrive block - kept deliberately orphaned specifically
    so a future restoration would not need to move the file's pinned @keyframes count - is
    REFERENCED again by the restored .dirty-bar base rule's own animation: declaration, reused
    rather than reinvented"""
    css = served_css
    blocks = at_rule_blocks(css).count("@keyframes skypane-bar-arrive")
    assert blocks == 1, (
        "expected exactly one @keyframes skypane-bar-arrive block (still the same one, never "
        "duplicated), got %d" % (blocks,))
    consumers = [
        (rule.selectors, rule.at_rules)
        for rule in css_rules(css)
        for prop, value in rule.declarations
        if prop in ("animation", "animation-name") and "skypane-bar-arrive" in value.split()
    ]
    assert consumers == [((".dirty-bar",), ())], (
        "expected exactly ONE rule, the restored .dirty-bar base rule, to reference "
        "skypane-bar-arrive - REUSING the block 27-04 kept orphaned for exactly this "
        "restoration; got %r" % (consumers,))


def test_dirty_state_js_has_no_hardcoded_section_names(dirty_state_js):
    """dirty-state.js contains no hardcoded occurrence of "Theme", "Runway", or "Diagnostic LED"
    (labels come from the DOM)"""
    for literal in ("Theme", "Runway", "Diagnostic LED"):
        assert literal not in dirty_state_js, (
            "expected no hardcoded occurrence of %r - section labels must come from the DOM" % (literal,))


def test_dirty_state_js_is_network_free_again_with_one_named_timer_exception(dirty_state_js):
    """dirty-state.js is network-free and poll-free again (no fetch(/XMLHttpRequest/setInterval/
    requestAnimationFrame anywhere) with exactly ONE setTimeout in the whole file - a literal
    setTimeout(fn, 0) sitting INSIDE the form's own reset-event handler, never cancelling that
    event's own default action

    setTimeout is permitted EXACTLY ONCE, and pinned STRUCTURALLY, not by count alone: the single
    occurrence must be a setTimeout(fn, 0) - a literal zero delay, never a duration - scheduled
    from INSIDE the form's own reset-event handler and nowhere else in the file. This is a
    reset-event side-effect flush: the reset event fires BEFORE the browser restores the form's
    fields, so the theme-preview refresh and the dial repaint must run on the next tick to read
    restored values.
    """
    source = dirty_state_js
    for forbidden in ("fetch(", "XMLHttpRequest", "setInterval", "requestAnimationFrame"):
        assert forbidden not in source, (
            "forbidden network/timer construct found in dirty-state.js: %r" % (forbidden,))
    assert source.count("setTimeout") == 1, (
        "expected exactly one setTimeout occurrence anywhere in the file (the reset-event "
        "side-effect flush), got %d" % source.count("setTimeout"))
    # Locate the reset-event handler's own function body by reading, from
    # its opening brace to its matching close - never by a file-wide
    # grep, which would not prove CONTAINMENT.
    handler_marker = 'form.addEventListener("reset", function () {'
    assert handler_marker in source, "expected a form.addEventListener(\"reset\", function () { ... }) handler"
    body_start = source.index(handler_marker) + len(handler_marker)
    depth = 1
    i = body_start
    while depth > 0:
        assert i < len(source), "reset handler's opening brace was never matched by a closing one"
        if source[i] == "{":
            depth += 1
        elif source[i] == "}":
            depth -= 1
        i += 1
    handler_body = source[body_start:i - 1]
    assert "setTimeout" in handler_body, (
        "expected the file's one setTimeout occurrence to sit INSIDE the reset handler's own "
        "function body, but it was found outside it")
    timeout_idx = handler_body.index("setTimeout")
    timeout_call = handler_body[timeout_idx:timeout_idx + 400]
    assert re.search(r"setTimeout\(function \(\) \{.*?\}, 0\);", timeout_call, re.DOTALL), (
        "expected the reset handler's own setTimeout call to read setTimeout(function () { ... "
        "}, 0) - a literal zero delay, never a duration; got %r" % (timeout_call[:120],))
    assert "preventDefault" not in handler_body and "returnValue" not in handler_body, (
        "expected the reset handler's own function body to contain neither preventDefault nor "
        "returnValue - cancelling the reset event's own default action would silently turn "
        "Annuler into a no-op for every JS-running visitor")


# ======================================================================
# Section 11: the per-flight colour-rules editor's markup/copy checks,
# relocated into the Aspect card's own "Per-flight rules" usage panel.
# ======================================================================

def test_aspect_card_full_shape_checklist():
    """the Display page's look card carries its full shape: the heading, two framed pictures
    each with a "Change" disclosure holding the no-script table, the Special looks list with the
    calendar row, the "Add a special look" disclosure holding the rules add form, the hidden
    look sheet (a labelled, modal dialog), and none of the retired accordion markup"""
    rendered = config_page.render({
        "device_config": {"theme": "white", "tracked_runway": "3"},
        "colour_rules": {kind: {} for kind in colour_rules.RULE_KINDS},
        "poll_cooldown_remaining": 0,
    }, scope=config_page.SCOPE_DISPLAY)
    root = parse_html(rendered)
    card = root.select_one("div.look-card")
    assert card.select_one("h2").attrs.get("id") == config_page.ASPECT_HEADING_ID
    frames = card.select("div.look-frame")
    assert [frame.attrs.get("data-look-usage") for frame in frames] == ["departures", "arrivals"]
    for frame in frames:
        assert frame.select_one("details.look-edit table.look-table")
        assert frame.select_one("img.look-frame__image")
    special = card.select_one("div.special-looks")
    assert special.select_one("li.special-row--calendar").attrs.get("data-look-usage") == "calendar"
    add_form = special.select_one("details.special-add form")
    assert add_form.attrs.get("action") == config_page.RULES_ADD_ROUTE
    sheet = card.select_one("div.look-sheet")
    assert "hidden" in sheet.attrs
    assert sheet.attrs.get("role") == "dialog" and sheet.attrs.get("aria-modal") == "true"
    assert root.select_one("#" + sheet.attrs["aria-labelledby"])
    for token in cp.ASPECT_RETIRED_MARKUP_TOKENS + ("usage-row", "theme-chip", "palette-chip"):
        assert token not in rendered, "expected the retired %r markup to be gone" % (token,)


def test_rules_row_renders_inside_aspect_after_form():
    """render() places the look card, holding the special looks, after the settings </form>,
    with every theme/theme_arriving/calendar_theme_id radio still carrying form=settings-form

    The special looks hold real <form> elements (the add form), and HTML forbids a nested
    <form>, so the whole look card must be a sibling of #settings-form while every theme radio
    still reaches it through form="settings-form".
    """
    rendered = config_page.render({
        "device_config": {"theme": "white", "tracked_runway": "3", "led_enabled": True},
        "colour_rules": {kind: {} for kind in colour_rules.RULE_KINDS},
        "poll_cooldown_remaining": 0,
    }, scope=config_page.SCOPE_DISPLAY)
    form_start = rendered.index('<form class="config-form" id="%s"' % config_page.SETTINGS_FORM_ID)
    form_end = rendered.index("</form>", form_start)
    aspect_pos = rendered.index('class="page-section aspect-card')
    rules_start, rules_end = cp.aspect_usage_row_bounds(rendered, config_page.COLOUR_USAGE_RULES)
    assert form_end < aspect_pos < rules_start, (
        "expected </form> < the look card < the rules, got positions %d/%d/%d"
        % (form_end, aspect_pos, rules_start))
    root = parse_html(rendered)
    for field in ("theme", "theme_arriving", "calendar_theme_id"):
        radios = [node for node in root.find_all("input") if node.attrs.get("name") == field]
        assert radios and all(
            node.attrs.get("form") == config_page.SETTINGS_FORM_ID for node in radios), field


def test_rules_section_empty_state_then_list_once_a_rule_exists(tmp_path):
    """with no rules the Special looks list holds only the calendar row and the add row, and a
    rule row appears, carrying its key, once a rule exists"""
    empty_ctx = {
        "device_config": {"theme": "white", "tracked_runway": "3"},
        "colour_rules": {kind: {} for kind in colour_rules.RULE_KINDS},
        "poll_cooldown_remaining": 0,
    }
    rendered = config_page.render(empty_ctx, scope=config_page.SCOPE_DISPLAY)
    rules_segment = cp.rules_row_segment(rendered)
    assert "rule-row" not in rules_segment and "<table" not in rules_segment.split("special-add")[0]

    result = colour_rules.add_rule(
        str(tmp_path), "callsign", "AFR1234", "white", now="2026-01-01T00:00:00+00:00")
    assert result == colour_rules.ADD_OK_NEW, "test setup failure: add_rule() returned %r" % (result,)
    filled_ctx = dict(empty_ctx)
    filled_ctx["colour_rules"] = colour_rules.load_colour_rules(str(tmp_path))
    filled_ctx["now"] = "2026-01-02T00:00:00+00:00"
    rendered = config_page.render(filled_ctx, scope=config_page.SCOPE_DISPLAY)
    rules_segment = cp.rules_row_segment(rendered)
    assert '<li class="special-row rule-row">' in rules_segment
    assert "AFR1234" in rules_segment


def test_rules_list_orders_most_specific_first_then_alphabetically(tmp_path):
    """a seeded set of rules of every kind renders most-specific first (callsign, then hex, then
    prefix), alphabetically within each kind"""
    tmpdir = str(tmp_path)
    for kind, value, theme_id in (
        ("prefix", "AFR", "red"),
        ("callsign", "BAW1234", "blue"),
        ("hex", "3944F2", "white"),
        ("callsign", "AFR1234", "black"),
    ):
        result = colour_rules.add_rule(tmpdir, kind, value, theme_id, now="2026-01-01T00:00:00+00:00")
        assert result == colour_rules.ADD_OK_NEW, "test setup failure: add_rule(%r) returned %r" % (kind, result)
    rendered = config_page.render({
        "device_config": {"theme": "white", "tracked_runway": "3"},
        "colour_rules": colour_rules.load_colour_rules(tmpdir),
        "poll_cooldown_remaining": 0,
        "now": "2026-01-02T00:00:00+00:00",
    }, scope=config_page.SCOPE_DISPLAY)
    list_segment = cp.rules_row_segment(rendered)
    expected_order = ["AFR1234", "BAW1234", "3944F2", "AFR"]
    positions = [
        list_segment.index('<span class="rule-row__key mono">%s</span>' % value)
        for value in expected_order
    ]
    assert positions == sorted(positions), (
        "expected callsign(alpha)/hex/prefix order %r, got positions %r" % (expected_order, positions))


def test_aspect_rules_copy_appears_escaped_verbatim():
    """every special-looks copy string - heading, caption, field labels, kind labels/titles, the
    add action and the precedence line - appears escaped-verbatim"""
    rendered = config_page.render({
        "device_config": {"theme": "white", "tracked_runway": "3"},
        "colour_rules": {kind: {} for kind in colour_rules.RULE_KINDS},
        "poll_cooldown_remaining": 0,
    }, scope=config_page.SCOPE_DISPLAY)
    copy_strings = (
        config_page.SPECIAL_LOOKS_HEADING,
        config_page.RULES_SECTION_CAPTION,
        config_page.RULE_KIND_FIELD_LABEL,
        config_page.RULE_VALUE_FIELD_LABEL,
        config_page.RULE_ADD_BUTTON_TEXT,
        rules_settings.ADD_SPECIAL_LOOK_LABEL,
        rules_settings.SPECIAL_LOOKS_ORDER,
    )
    for text in copy_strings:
        assert escape_html(i18n.t(text)) in rendered, "expected %r to appear escaped-verbatim in the rendered page" % (text,)
    for kind, label in config_page.RULE_KIND_LABELS.items():
        assert escape_html(label) in rendered, "expected the kind label %r (for %r) to appear escaped-verbatim" % (label, kind)
    for kind, title in config_page.RULE_KIND_TITLES.items():
        assert escape_html(title) in rendered, "expected the kind title %r (for %r) to appear escaped-verbatim" % (title, kind)


def test_aspect_rules_row_label_locked_verbatim():
    """the special looks heading and the precedence line keep their exact wording, which states
    the resolver's real order: calendar, then flight, aircraft, airline"""
    assert i18n.t(config_page.SPECIAL_LOOKS_HEADING) == "Special looks"
    assert i18n.t(rules_settings.SPECIAL_LOOKS_ORDER).startswith(
        "Most specific wins: calendar, then flight, aircraft, airline.")


def test_rules_no_select_and_three_named_radios_one_checked():
    """the add form carries no <select>, and its three rule_kind radios carry the three kind ids
    and the three technical titles, exactly one checked by default"""
    rendered = config_page.render({
        "device_config": {"theme": "white", "tracked_runway": "3"},
        "colour_rules": {kind: {} for kind in colour_rules.RULE_KINDS},
        "poll_cooldown_remaining": 0,
    }, scope=config_page.SCOPE_DISPLAY)
    rules_segment = cp.rules_row_segment(rendered)
    assert "<select" not in rules_segment
    kind_inputs = re.findall(r'<input type="radio" name="rule_kind"[^>]*>', rules_segment)
    assert len(kind_inputs) == len(colour_rules.RULE_KINDS)
    for kind in colour_rules.RULE_KINDS:
        assert 'id="rule-kind-%s"' % kind in rules_segment
        assert 'title="%s"' % escape_html(config_page.RULE_KIND_TITLES[kind]) in rules_segment
    checked_inputs = [tag for tag in kind_inputs if " checked" in tag]
    assert len(checked_inputs) == 1
    assert 'value="%s"' % colour_rules.RULE_KIND_CALLSIGN in checked_inputs[0]


def test_rules_row_carries_pill_badge_and_confirmed_remove_form(tmp_path):
    """a rendered rule row carries a kind tag with the plain-language word, a mini render of its
    look, its look read back, and a data-confirm Remove form"""
    result = colour_rules.add_rule(
        str(tmp_path), "callsign", "AFR1234", "green_light", now="2026-01-01T00:00:00+00:00")
    assert result == colour_rules.ADD_OK_NEW, "test setup failure: add_rule() returned %r" % (result,)
    rendered = config_page.render({
        "device_config": {"theme": "white", "tracked_runway": "3"},
        "colour_rules": colour_rules.load_colour_rules(str(tmp_path)),
        "poll_cooldown_remaining": 0,
        "now": "2026-01-02T00:00:00+00:00",
    }, scope=config_page.SCOPE_DISPLAY)
    row = parse_html(rendered).select_one("li.rule-row")
    assert row.select_one("span.rule-row__kind").text() == config_page.RULE_KIND_LABELS["callsign"]
    assert row.select_one("img.special-row__image").attrs["src"].startswith(
        config_page.FRAME_PREVIEW_ROUTE_PREFIX + "green_light.png?")
    assert row.select_one("p.rule-row__theme").text() == look.look_sentence("green_light")
    form = row.select_one("form")
    assert "data-confirm" in form.attrs
    assert form.select_one("button").text() == config_page.RULE_REMOVE_BUTTON_TEXT


def test_rules_empty_state_carries_no_heading_element():
    """with no rules, the Special looks list carries its own h3 heading and no other heading
    element, and the add row's summary names the action"""
    rendered = config_page.render({
        "device_config": {"theme": "white", "tracked_runway": "3"},
        "colour_rules": {kind: {} for kind in colour_rules.RULE_KINDS},
        "poll_cooldown_remaining": 0,
    }, scope=config_page.SCOPE_DISPLAY)
    special = parse_html(rendered).select_one("div.special-looks")
    headings = [node for node in special.find_all() if re.fullmatch(r"h[1-6]", node.tag)]
    assert [node.tag for node in headings] == ["h3", "h3"], (
        "expected only the list heading and the add form's dialog heading")
    assert special.select_one("summary.special-add__summary").text() == i18n.t(
        rules_settings.ADD_SPECIAL_LOOK_LABEL)


