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


# ======================================================================
# Section 8: 06.6.4.1.1-05 - the theme-chip grid's markup contract.
# ======================================================================

def test_theme_chip_preview_src_points_at_the_real_route_prefix_for_every_theme():
    """every theme chip's <img src> points at THEME_PREVIEW_ROUTE_PREFIX + the theme's own
    registry id, for every entry in device_config.THEME_IDS (06.6.4.1.1-05)"""
    rendered = config_page._theme_chip_grid_html("theme", "white")
    for theme_id in device_config.THEME_IDS:
        expected_src = 'src="%s%s.png"' % (
            config_page.THEME_PREVIEW_ROUTE_PREFIX, escape_html(theme_id))
        assert expected_src in rendered, "expected chip %r to carry %r" % (theme_id, expected_src)


def test_theme_chip_swatch_dots_carry_real_palette_hex_values():
    """every theme chip carries exactly two .theme-chip__dot swatches whose inline background
    values equal _palette_hex() computed from that theme's own departing_index/arriving_index
    (06.6.4.1.1-05, retargeted onto _theme_chip_grid_html() directly by 21-05-PLAN.md Task 1 D-06
    once theme_fieldset() is retired)"""
    rendered = config_page._theme_chip_grid_html("theme", "white")
    assert rendered.count("theme-chip__dot") == len(device_config.THEME_IDS) * 2, (
        "expected exactly %d .theme-chip__dot occurrences (2 per theme), got %d"
        % (len(device_config.THEME_IDS) * 2, rendered.count("theme-chip__dot")))
    for theme_id in device_config.THEME_IDS:
        theme = device_config.THEMES[theme_id]
        departing_hex = config_page._palette_hex(theme["departing_index"])
        arriving_hex = config_page._palette_hex(theme["arriving_index"])
        assert ('theme-chip__dot" style="background:%s"' % departing_hex) in rendered, (
            "expected theme %r's departing swatch dot to carry %r" % (theme_id, departing_hex))
        assert ('theme-chip__dot" style="background:%s"' % arriving_hex) in rendered, (
            "expected theme %r's arriving swatch dot to carry %r" % (theme_id, arriving_hex))


def test_theme_chip_radio_hidden_and_check_glyph_present_on_every_chip():
    """every theme chip's radio carries class="visually-hidden" (never display:none) and every
    chip carries a .theme-chip__check glyph with visually-hidden "Selected" text, present on all
    chips regardless of selection (06.6.4.1.1-05, retargeted onto _theme_chip_grid_html()
    directly by 21-05-PLAN.md Task 1 D-06 once theme_fieldset() is retired)

    The radio is visually-hidden (never display:none), so keyboard/no-JS selection keeps working
    natively.
    """
    rendered = config_page._theme_chip_grid_html("theme", "white")
    theme_count = len(device_config.THEME_IDS)
    assert rendered.count('name="theme" value="') == theme_count, (
        "expected %d theme radios, got %d" % (theme_count, rendered.count('name="theme" value="')))
    assert rendered.count('class="visually-hidden"') >= theme_count, (
        "expected every chip's radio to carry class=\"visually-hidden\"")
    assert "display:none" not in rendered and "display: none" not in rendered, (
        "expected the radio hidden via the visually-hidden utility class, never display:none")
    assert rendered.count('<span class="theme-chip__check">') == theme_count, (
        "expected exactly %d .theme-chip__check occurrences (one per chip, regardless of "
        "selection), got %d" % (theme_count, rendered.count('<span class="theme-chip__check">')))
    assert rendered.count('<span class="visually-hidden">Selected</span>') == theme_count, (
        "expected every chip's check glyph to carry the visually-hidden \"Selected\" text")


# ======================================================================
# Section 9: 15-04-PLAN.md (D-04/D-05) - the arrivals-override control,
# its revealed second chip grid, and handle_post()'s clearable-checkbox
# contract (15-VALIDATION.md row 7).
# ======================================================================

def test_aspect_arrivals_row_carries_leading_option_no_checkbox():
    """the arrivals row carries a leading Same-as-departures option submitting the empty string
    (class="leading-option", form=settings-form), and no checkbox-based override control exists
    anywhere on the page (D-06/D-09, 30-05-PLAN.md Task 1, replacing the retired
    _frame_colours_arrivals_grid_carries_leading_chip_no_checkbox)

    This control used to be a checkbox; the empty-string radio is what keeps the clear signal
    honest now.
    """
    rendered = config_page.render({
        "device_config": {"theme": "white", "tracked_runway": "3"},
        "colour_rules": {kind: {} for kind in colour_rules.RULE_KINDS},
        "poll_cooldown_remaining": 0,
    }, scope=config_page.SCOPE_DISPLAY)
    leading_needle = (
        '<label class="leading-option">'
        '<input type="radio" name="theme_arriving" value="" class="visually-hidden" form="%s"'
        % config_page.SETTINGS_FORM_ID)
    assert leading_needle in rendered, (
        "expected the arrivals row's leading option to carry class=\"leading-option\" and "
        "form=%r" % (config_page.SETTINGS_FORM_ID,))
    assert 'type="checkbox"' not in rendered, "expected no <input type=\"checkbox\"> anywhere in the Aspect card"


def test_aspect_arrivals_override_preselects_the_override_not_same_as_departures():
    """a stored theme_arriving override pre-selects the OVERRIDE (not Same-as-departures, not the
    departures theme) in the arrivals row, names the override's own label in the row's summary
    meta, and leaves the calendar row's own Same-as-departures state unaffected in the same
    render (D-06/D-09, 30-05-PLAN.md Task 1, replacing the retired
    _frame_colours_arrivals_override_preselects_the_override_not_same_as_departures)

    Locates the arrivals row by its own data-usage attribute (never
    COLOUR_USAGE_PANEL_TARGET_ATTR, retired), and asserts the calendar row is unaffected in the
    same render - that cross-row independence is the relationship this check is really
    protecting.
    """
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
        "expected the arrivals row's checked radio to be the stored override (black)")
    assert not re.search(r'name="theme_arriving" value=""[^>]*checked', arrivals_segment), (
        "expected the leading Same-as-departures option to NOT be checked once an override is set")
    assert not re.search(r'name="theme_arriving" value="white"[^>]*checked', arrivals_segment), (
        "expected the departures theme (white) to NOT be marked selected in the arrivals row "
        "once an override is set")
    summary_segment = arrivals_segment.split("</summary>", 1)[0]
    override_label = escape_html(i18n.t(device_config.theme_label("black")))
    assert override_label in summary_segment, (
        "expected the arrivals row's summary meta to name the override's own label")
    same_as_label = escape_html(i18n.t(config_page.SAME_AS_DEPARTURES_LABEL))
    assert same_as_label not in summary_segment, (
        "expected the arrivals row's summary meta to NOT read Same-as-departures once an "
        "override is set")
    calendar_start, calendar_end = cp.aspect_usage_row_bounds(
        rendered, config_page.COLOUR_USAGE_CALENDAR)
    calendar_segment = rendered[calendar_start:calendar_end]
    assert re.search(r'name="calendar_theme_id" value=""[^>]*checked', calendar_segment), (
        "expected the calendar row's leading Same-as-departures option to still be checked, "
        "unaffected by the arrivals override")


def test_handle_post_theme_arriving_valid_id_persists_chosen_id(tmp_path):
    """handle_post with a valid theme_arriving id persists it, with no checkbox field involved
    (D-06/D-09, retargeted from the retired arrivals-override checkbox)"""
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
    """handle_post with theme_arriving='' clears a previously-set override back to None (D-06/
    D-09, retargeted from the retired arrivals-override checkbox's own absence)"""
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
    theme_arriving's own empty-string clear signal (D-06/D-09)

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
    nothing - the empty-string exemption does not widen the gate to anything else
    (D-09/Pitfall 1)"""
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
    explicitly exempted from this rejection (D-09)"""
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
    unchanged (retargeted from the retired arrivals-override checkbox, D-09)"""
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
    """the clearable contract (15-VALIDATION.md row 7): a save with a chosen arrivals theme
    persists it, then a save with theme_arriving='' clears it back to None while every other
    setting survives unchanged (D-06/D-09, retargeted from the retired arrivals-override
    checkbox's own absence)

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


def test_settings_page_has_zero_fieldsets_and_five_dirty_sections():
    """the rendered Settings page contains no <fieldset> and no <legend>, and exactly five
    data-dirty-section groups (Runway/Diagnostic LED/Quiet hours/Wake interval/Notifications -
    Theme's own entry retired along with theme_fieldset(), 21-05-PLAN.md Task 1 D-06; Calendar's
    own entry retired from this legacy scope by 21-07-PLAN.md Task 1 D-13/Pitfall 2; Display's
    own entry retired outright by 22-05-PLAN.md Task 1 X1/D-04/D-12.1)

    06.6.4.1.1-05: the rendered Settings page contains no <fieldset and no <legend anywhere - so
    dirty-state.js's section-aware walk still finds each group as one addressable unit.
    """
    rendered = config_page.render({
        "device_config": {"theme": "white", "tracked_runway": "3", "led_enabled": True},
        "poll_cooldown_remaining": 0,
    })
    assert "<fieldset" not in rendered, "expected zero <fieldset> elements on the rendered Settings page"
    assert "<legend" not in rendered, "expected zero <legend> elements on the rendered Settings page"
    assert rendered.count(config_page.DIRTY_SECTION_ATTR) == 5, (
        "expected exactly 5 %s occurrences (Runway/Diagnostic LED/Quiet hours/Wake interval/"
        "Notifications), got %d" % (config_page.DIRTY_SECTION_ATTR, rendered.count(config_page.DIRTY_SECTION_ATTR)))


# ======================================================================
# Section 10: 06.6.4.1.1-06 / quick task 260904-bbi / 22-15-PLAN.md
# Task 1 (T6) / 23-10-PLAN.md Task 1 (D3/CFG-32) - the selected-card
# visual treatment, live vs. saved-but-not-live, style.css structural
# checks fetched from the served stylesheet rather than opened from disk.
# ======================================================================

def test_selected_runway_card_and_theme_chip_carry_a_background_wash(served_css):
    """both .runway-card--selected and .theme-chip--selected .theme-chip__body carry a
    12%-accent background wash (color-mix), matching .theme-form .theme-option--active's
    established active-state idiom, added alongside (not replacing) their check glyph and their
    now-constant 1px border, whose 2px accent signal moved to an inset ring (06.6.4.1.1-06,
    retargeted by 22-15-PLAN.md Task 1 for T6)

    The developer reported that, across the whole site, the selected element was "very hard to
    see" - a border-only + check-glyph treatment was too subtle at density.
    """
    source = served_css
    wash = "background: color-mix(in srgb, var(--color-accent) 12%, transparent);"

    runway_selector = ".runway-card--selected {"
    assert runway_selector in source, "expected style.css to still declare a .runway-card--selected rule"
    idx = source.index(runway_selector)
    window = source[idx:idx + 1600]
    # T6 (22-15-PLAN.md Task 1): the border is constant at 1px and only
    # recolours; the 2px accent signal moved to an inset ring, which
    # occupies no layout space at all (a 2px border still widens the
    # OUTER box of a flex: 1 1 0 card under box-sizing: border-box).
    assert "border-color: var(--color-accent);" in window, (
        ".runway-card--selected must recolour its constant 1px border to the accent")
    assert "box-shadow: inset 0 0 0 2px var(--color-accent);" in window, (
        ".runway-card--selected must carry T6's inset accent ring - the selection signal that "
        "replaced the layout-shifting 2px border")
    assert "border: 2px" not in window, (
        ".runway-card--selected must never declare a 2px border again - that is T6, the 2px "
        "layout shift this treatment exists to avoid")
    assert wash in window, (
        "expected .runway-card--selected to carry the same 12%-accent background wash "
        ".theme-form .theme-option--active uses")

    # .theme-chip--selected itself must stay border-only (no background) -
    # the wash must be scoped to .theme-chip__body only, so it never sits
    # behind the rendered preview band and tints it.
    chip_selected_selector = ".theme-chip--selected {"
    assert chip_selected_selector in source, "expected style.css to still declare a .theme-chip--selected rule"
    idx = source.index(chip_selected_selector) + len(chip_selected_selector)
    rule_body = source[idx:source.index("}", idx)]
    assert "background:" not in rule_body, (
        "expected .theme-chip--selected itself to stay border-only - the wash must be scoped to "
        ".theme-chip__body, not the whole chip (which would tint the preview band)")

    theme_chip_body_selector = ".theme-chip--selected .theme-chip__body {"
    assert theme_chip_body_selector in source, "expected style.css to declare a %r rule" % (theme_chip_body_selector,)
    idx = source.index(theme_chip_body_selector)
    window = source[idx:idx + 200]
    assert wash in window, (
        "expected .theme-chip--selected .theme-chip__body to carry the same 12%-accent "
        "background wash .theme-form .theme-option--active uses")


def test_strong_selected_treatment_is_keyed_to_the_live_checked_radio(served_css):
    """the strong selected-card treatment (border, wash, check glyph, and a D-03a hover restore)
    is keyed to live :has(input:checked) state inside one @supports selector(:has(*)) block, for
    both .theme-chip and .runway-card, with every pre-existing --selected fallback rule surviving
    verbatim (quick task 260904-bbi) - and, since 23-10-PLAN.md Task 1 (D3/CFG-32), selection
    ANSWERS: a fast transition naming the transform, the border colour, the shadow and the wash
    is declared on each selectable surface's BASE rule, the live rules and their --selected
    fallbacks carry the SAME scale, saved-but-not-live clears it, and the ONE feature-query block
    declares no transition at all - asserted together so moving one inside fails once

    quick task 260904-bbi: the developer found that the strong "this is your selection" treatment
    followed the SAVED config, not the user's LIVE choice, because every selected-state rule keyed
    off the server-computed --selected class alone. Also proves the D-03a hover guard (which would
    otherwise clear the newly-checked chip's border) is answered with a positive restore rule
    rather than a re-scoped guard.
    """
    source = served_css

    supports_marker = "@supports selector(:has(*)) {"
    assert source.count(supports_marker) == 1, (
        "expected exactly one %r block (the live-selection-state one), got %d"
        % (supports_marker, source.count(supports_marker)))
    supports_idx = source.index(supports_marker)

    wash = "background: color-mix(in srgb, var(--color-accent) 12%, transparent);"

    def _rule_body(selector):
        assert selector in source, "expected style.css to declare %r" % (selector,)
        idx = source.index(selector)
        assert idx > supports_idx, (
            "expected %r to live inside the @supports selector(:has(*)) block" % (selector,))
        return source[idx + len(selector):source.index("}", idx)]

    def _assert_constant_border_and_inset_ring(body, label):
        assert "border-color: var(--color-accent);" in body, (
            "%s must recolour its constant 1px border to the accent" % (label,))
        assert "box-shadow: inset 0 0 0 2px var(--color-accent);" in body, (
            "%s must carry T6's inset accent ring" % (label,))
        assert "border: 2px" not in body, (
            "%s must never declare a 2px border again (T6's layout shift)" % (label,))

    body = _rule_body(".theme-chip:has(input:checked) {")
    _assert_constant_border_and_inset_ring(body, ".theme-chip:has(input:checked)")

    body = _rule_body(".theme-chip:has(input:checked) .theme-chip__body {")
    assert wash in body, ".theme-chip:has(input:checked) .theme-chip__body must carry the 12%-accent wash"

    body = _rule_body(".theme-chip:has(input:checked) .theme-chip__check {")
    assert "display: inline-flex;" in body, ".theme-chip:has(input:checked) .theme-chip__check must be shown"

    hover_selector = ".theme-chip:has(input:checked):hover,"
    assert hover_selector in source, "expected a live-state hover restore selector for .theme-chip"
    idx = source.index(hover_selector)
    assert idx > supports_idx, "expected the .theme-chip live-state hover restore rule inside @supports"
    window = source[idx:idx + 250]
    assert "border-color: var(--color-accent);" in window, (
        ".theme-chip:has(input:checked):hover must restore the accent border-color")
    # T6 (22-15-PLAN.md Task 1): the hover clause used to require
    # `box-shadow: none;`, whose only job was to suppress the hover
    # elevation shadow - once selection IS a box-shadow, `none` erases
    # the ring the instant a pointer crosses a selected chip.
    assert "box-shadow: inset 0 0 0 2px var(--color-accent);" in window, (
        ".theme-chip:has(input:checked):hover must RESTATE T6's inset ring, which suppresses "
        "the hover elevation without erasing the selection signal")
    assert "box-shadow: none;" not in window, (
        ".theme-chip:has(input:checked):hover must not clear the shadow - that would erase T6's "
        "selection ring on hover")

    body = _rule_body(".runway-card:has(input:checked) {")
    _assert_constant_border_and_inset_ring(body, ".runway-card:has(input:checked)")
    assert wash in body, ".runway-card:has(input:checked) must carry the 12%-accent wash directly (no body wrapper)"

    body = _rule_body(".runway-card:has(input:checked) .runway-card__check {")
    assert "display: inline-flex;" in body, ".runway-card:has(input:checked) .runway-card__check must be shown"

    hover_selector = ".runway-card:has(input:checked):hover,"
    assert hover_selector in source, "expected a live-state hover restore selector for .runway-card"
    idx = source.index(hover_selector)
    assert idx > supports_idx, "expected the .runway-card live-state hover restore rule inside @supports"
    window = source[idx:idx + 250]
    assert "border-color: var(--color-accent);" in window, (
        ".runway-card:has(input:checked):hover must restore the accent border-color")
    assert "box-shadow: inset 0 0 0 2px var(--color-accent);" in window, (
        ".runway-card:has(input:checked):hover must RESTATE T6's inset ring rather than clearing "
        "the shadow")
    assert "box-shadow: none;" not in window, (
        ".runway-card:has(input:checked):hover must not clear the shadow - that would erase T6's "
        "selection ring on hover")

    # Fallback intact: all four pre-existing server-class rules must
    # still exist verbatim.
    for selector in (
        ".theme-chip--selected {",
        ".theme-chip--selected .theme-chip__body {",
        ".runway-card--selected {",
        ".theme-chip--selected .theme-chip__check {",
        ".runway-card--selected .runway-card__check {",
    ):
        assert selector in source, "expected the pre-existing fallback rule %r to survive verbatim" % (selector,)

    # --- 23-10-PLAN.md Task 1 (D3/CFG-32): SELECTION ANSWERS -----------
    # A `transition` is a property of the ELEMENT, not of the state.
    # Declared on the BASE rule it animates the property however the
    # state that changes it is reached - live `:has(input:checked)`
    # inside the query, and the server-rendered `--selected` fallback
    # outside it, from one declaration.
    def _base_rule_body(selector):
        # Newline-anchored, not a bare substring search: this selector's
        # own text also occurs as a substring inside a more specific
        # selector declared EARLIER in the file.
        anchored = "\n" + selector
        assert anchored in source, "expected style.css to declare the base rule %r" % (selector,)
        idx = source.index(anchored)
        assert idx < supports_idx, (
            "expected the base rule %r to be declared BEFORE (outside) the one @supports "
            "selector(:has(*)) block" % (selector,))
        start = idx + len(anchored)
        return source[start:source.index("}", start)]

    def _assert_transition(body, label, properties):
        assert "transition:" in body, (
            "%s must declare the selection transition on its OWN base rule - a transition "
            "declared on the base rule animates the property however the state is reached, "
            "which is why the live :has() treatment needs no second feature query (D3, "
            "23-10-PLAN.md Task 1)" % (label,))
        decl = body[body.index("transition:"):]
        decl = decl[:decl.index(";") + 1] if ";" in decl else decl
        for prop in properties:
            assert prop in decl, (
                "%s's transition must name %r - it is one of the properties that actually "
                "changes on selection, and a property absent from the list switches instantly "
                "(got %r)" % (label, prop, decl.strip()))
        assert "var(--motion-fast)" in decl, (
            "%s's transition must spend var(--motion-fast), the phase's REACTION token - a "
            "selection is a state change the user just caused and is watching for confirmation "
            "of (got %r)" % (label, decl.strip()))

    for selector, properties in (
        (".theme-chip {", ("transform", "border-color", "box-shadow")),
        (".theme-chip__body {", ("background-color",)),
        (".runway-card {", ("transform", "border-color", "box-shadow", "background-color")),
    ):
        body = _base_rule_body(selector)
        _assert_transition(body, selector.rstrip(" {"), properties)

    # The scale itself, and the fallback parity that is the whole reason
    # one transition declaration is enough: the live rule and the
    # --selected fallback must carry the SAME transform, or a browser
    # without :has() gets a differently-sized selected card.
    def _scale_of(selector, inside):
        assert selector in source, "expected style.css to declare %r" % (selector,)
        idx = source.index(selector)
        if inside:
            assert idx > supports_idx, "expected %r to live inside the feature query" % (selector,)
        else:
            assert idx < supports_idx, "expected %r to live outside the feature query" % (selector,)
        start = idx + len(selector)
        body = source[start:source.index("}", start)]
        match = re.search(r"transform:\s*scale\(([^)]+)\)", body)
        assert match, (
            "expected %r to carry the selection scale (`transform: scale(...)`) - the wash's "
            "fade is the primary signal and the scale is its punctuation, and a transform "
            "changes no layout box so T6 cannot recur through it" % (selector,))
        return match.group(1).strip()

    scales = {}
    for selector, inside in (
        (".theme-chip:has(input:checked) {", True),
        (".theme-chip--selected {", False),
        (".runway-card:has(input:checked) {", True),
        (".runway-card--selected {", False),
    ):
        scales[selector] = _scale_of(selector, inside)
    assert len(set(scales.values())) == 1, (
        "the live :has(input:checked) rules and their --selected fallbacks must carry the SAME "
        "scale, or a browser without :has() renders a different-sized selected card - the "
        "identical parity contract T6 already holds for the border and the ring, got %r" % (scales,))

    # Saved-but-not-live must CLEAR the scale, exactly as it already
    # clears the accent ring and the wash: a chip can be saved while its
    # neighbour is the live choice, and two scaled chips would claim two
    # selections.
    for selector in (
        ".theme-chip--selected:not(:has(input:checked)) {",
        ".runway-card--selected:not(:has(input:checked)) {",
    ):
        assert selector in source, "expected style.css to declare %r" % (selector,)
        start = source.index(selector) + len(selector)
        body = source[start:source.index("}", start)]
        assert "transform: none;" in body, (
            "%s must clear the selection scale with `transform: none;` - it already clears the "
            "accent ring and the wash for the same reason, and a saved-but-not-live chip that "
            "stays scaled claims a selection it does not have" % (selector,))

    # And the block itself carries NO transition. Measured on
    # comment-stripped source, because the paragraphs inside that block
    # discuss the very word this scan counts.
    stripped = re.sub(r"/\*.*?\*/", "", source, flags=re.DOTALL)
    assert stripped.count(supports_marker) == 1, (
        "expected exactly one %r block in comment-stripped source, got %d"
        % (supports_marker, stripped.count(supports_marker)))
    open_idx = stripped.index(supports_marker) + len(supports_marker) - 1
    depth = 0
    close_idx = None
    for pos in range(open_idx, len(stripped)):
        if stripped[pos] == "{":
            depth += 1
        elif stripped[pos] == "}":
            depth -= 1
            if depth == 0:
                close_idx = pos
                break
    assert close_idx is not None, "the @supports selector(:has(*)) block is never closed"
    assert "transition" not in stripped[open_idx:close_idx], (
        "the ONE @supports selector(:has(*)) block declares a `transition` - it must not. A "
        "transition belongs on each selectable surface's BASE rule, where it animates the live "
        ":has() treatment and the --selected fallback identically from one declaration; moving "
        "it inside the query is the first step toward the second feature-query block Phase 15's "
        "D-05 already had retired (D3, 23-10-PLAN.md Task 1)")


def test_destructive_disconnect_is_secondary_and_selection_is_free_and_focusable_after_the_accordion_rebuild(served_css):
    """the destructive Disconnect control keeps its secondary, element-qualified specificity AND
    its source-order relationship against button[type="submit"] (T2/T15, re-proven as a
    RELATIONSHIP rather than a bare presence check, since the recorded defect was a rule whose
    every declaration was dead for a phase and a half), and the selected-chip mechanism is
    re-keyed from the retired 'input:checked + .frame-colours__row' sibling selector to
    .palette-chip:has(input:checked) inside the file's one @supports selector(:has(*)) block,
    carrying the accent border, inset ring, 12%% wash and check-glyph declarations (T6,
    30-07-PLAN.md Task 3)"""
    source = served_css

    # (a) T2/T15: the specificity RELATIONSHIP, not merely presence.
    # button[type="submit"] and button.calendar-disconnect-btn are both
    # (0,1,1) - equal specificity - so which one wins is decided by
    # SOURCE ORDER alone.
    submit_selector = 'button[type="submit"] {'
    disconnect_selector = "button.calendar-disconnect-btn {"
    assert submit_selector in source, "expected style.css to declare %r" % (submit_selector,)
    assert disconnect_selector in source, (
        "expected style.css to declare %r (element-qualified - a bare '.calendar-disconnect-btn' "
        "is only (0,1,0) and loses to button[type=\"submit\"]'s (0,1,1) regardless of source "
        "order)" % (disconnect_selector,))
    submit_idx = source.index(submit_selector)
    disconnect_idx = source.index(disconnect_selector)
    assert disconnect_idx > submit_idx, (
        "expected %r to appear AFTER %r in source order - at equal (0,1,1) specificity the LATER "
        "rule wins, and this is the exact relationship that let the destructive control render "
        "as the page's primary accent-filled CTA for a phase and a half"
        % (disconnect_selector, submit_selector))

    # (b) T6, re-keyed: the palette chip's checked-state declarations
    # must live inside the ONE @supports selector(:has(*)) block - the
    # new selection mechanism, replacing the retired
    # `input:checked + .frame-colours__row` sibling selector.
    supports_marker = "@supports selector(:has(*)) {"
    assert source.count(supports_marker) == 1, (
        "expected exactly one %r block, got %d" % (supports_marker, source.count(supports_marker)))
    supports_idx = source.index(supports_marker)

    def _rule_body(selector):
        assert selector in source, "expected style.css to declare %r" % (selector,)
        idx = source.index(selector)
        assert idx > supports_idx, (
            "expected %r to live inside the @supports selector(:has(*)) block" % (selector,))
        return source[idx + len(selector):source.index("}", idx)]

    base_body = _rule_body(".palette-chip:has(input:checked) {")
    assert "border-color: var(--color-accent);" in base_body, (
        ".palette-chip:has(input:checked) must recolour its own border to accent")
    assert "box-shadow: inset 0 0 0 2px var(--color-accent);" in base_body, (
        ".palette-chip:has(input:checked) must carry the inset accent ring")

    name_body = _rule_body(".palette-chip:has(input:checked) .palette-chip__name {")
    assert "background: color-mix(in srgb, var(--color-accent) 12%, transparent);" in name_body, (
        "expected the 12%% accent wash on .palette-chip__name")

    check_body = _rule_body(".palette-chip:has(input:checked) .palette-chip__check {")
    assert "display: inline-flex;" in check_body, "expected the check glyph to switch to inline-flex"


def test_calendar_fusion_css_retired_from_the_stylesheet(served_css):
    """style.css carries neither retired Calendar-card fusion selector
    (.page-section:has(+ .calendar-disconnect-form), .calendar-disconnect-form) anywhere
    (D-13/R-08/Pitfall 2)

    Both retired fusion rules must be gone from the real stylesheet, not merely dead-but-present
    - a plan that deletes the merged card's separate-siblings markup while leaving this CSS
    behind would ship dead rules that no longer match anything (Pitfall 2).
    """
    source = served_css
    for retired_selector in (
            ".page-section:has(+ .calendar-disconnect-form)",
            ".calendar-disconnect-form {"):
        assert retired_selector not in source, (
            "expected %r to be retired from style.css entirely" % (retired_selector,))


def test_saved_but_unchecked_card_degrades_to_a_quiet_current_marker(served_css):
    """the saved-but-no-longer-live --selected card degrades to an accent-free dashed 70%-muted
    ring with its wash/check glyph cleared and a "Current" ::after tag whose text is read from
    the server-rendered, translated data-current-label attribute (exactly 2 occurrences
    site-wide, zero hard-coded English declarations, zero French copy in the stylesheet), reusing
    the established muted-text strength rather than inventing a new one (quick task 260904-bbi;
    retargeted by 22-10-PLAN.md Task 1, T10)

    The server-rendered --selected class is demoted from driving the strong treatment to an
    honest, quiet "this is what is saved" marker once it is no longer the live choice.
    """
    source = served_css
    muted = "color-mix(in srgb, var(--color-text) 70%, transparent)"

    for prefix in (".theme-chip--selected:not(:has(input:checked))", ".runway-card--selected:not(:has(input:checked))"):
        base_selector = prefix + " {"
        assert base_selector in source, "expected style.css to declare %r" % (base_selector,)
        idx = source.index(base_selector)
        body = source[idx + len(base_selector):source.index("}", idx)]
        assert "dashed" in body, "%r must use a dashed ring, not a solid one" % (base_selector,)
        assert muted in body, "%r must use the established 70%%-muted-text colour, not a new strength" % (base_selector,)
        assert "var(--color-accent)" not in body, (
            "%r must be accent-free - the quiet marker signals 'saved', not 'selected'" % (base_selector,))

    chip_body_selector = ".theme-chip--selected:not(:has(input:checked)) .theme-chip__body {"
    assert chip_body_selector in source, "expected style.css to declare %r" % (chip_body_selector,)
    idx = source.index(chip_body_selector)
    window = source[idx:idx + 100]
    assert "background: transparent;" in window, "%r must clear the wash back to transparent" % (chip_body_selector,)

    for check_selector in (
        ".theme-chip--selected:not(:has(input:checked)) .theme-chip__check {",
        ".runway-card--selected:not(:has(input:checked)) .runway-card__check {",
    ):
        assert check_selector in source, "expected style.css to declare %r" % (check_selector,)
        idx = source.index(check_selector)
        window = source[idx:idx + 100]
        assert "display: none;" in window, "%r must hide the check glyph" % (check_selector,)

    # 22-10-PLAN.md Task 1 (T10): the badge's text used to be the
    # hard-coded English literal `content: "Current";`, twice, in an app
    # that ships in two languages. It is now `content:
    # attr(data-current-label)`, with the translated string
    # server-rendered onto the element.
    current_literal = "content: attr(%s)" % config_page.CURRENT_BADGE_ATTR
    assert source.count(current_literal) == 2, (
        "expected exactly 2 occurrences of %r, got %d" % (current_literal, source.count(current_literal)))
    hard_coded = 'content: "Current"'
    # Comment-filtered deliberately, and this filter is load-bearing
    # rather than convenient: the DECLARATION is gone, but the rule's own
    # comment block still quotes `content: "Current"` while recording the
    # justification for keeping a pseudo-element instead of a <span>.
    declarations = "\n".join(
        line for line in source.splitlines() if not line.lstrip().startswith(("*", "/")))
    assert hard_coded not in declarations, (
        "expected zero hard-coded English %r DECLARATIONS - T10 moves the badge's text to a "
        "server-rendered, translated attribute" % (hard_coded,))

    for after_selector in (
        ".theme-chip--selected:not(:has(input:checked))::after {",
        ".runway-card--selected:not(:has(input:checked))::after {",
    ):
        assert after_selector in source, "expected style.css to declare %r" % (after_selector,)
        idx = source.index(after_selector)
        window = source[idx:idx + 250]
        assert current_literal in window, "%r must render the English 'Current' tag" % (after_selector,)

    assert "actuel" not in source.lower(), (
        "expected zero occurrences of the French word for 'current' - DP-2 requires English copy")

    muted_count = source.count(muted)
    assert muted_count >= 17, (
        "expected the established 70%%-muted-text mix to appear at least 17 times (16 "
        "pre-existing plus the new quiet-marker rules), got %d - a new muted strength must not "
        "be invented" % (muted_count,))


def test_style_css_carries_section_caption_and_the_restored_dirty_bar_rules(served_css):
    """style.css declares .section-caption (70% muted color-mix) AND the restored .dirty-bar -
    fixed-positioned at both breakpoints, its [hidden] override and its Cancel button's own
    quiet-wash override all present (CFG-77/CFG-78, 28-08-PLAN.md Task 2)"""
    source = served_css

    caption_selector = ".section-caption {"
    assert caption_selector in source, "expected style.css to declare a .section-caption rule"
    idx = source.index(caption_selector)
    window = source[idx:idx + 200]
    assert "color-mix(in srgb, var(--color-text) 70%, transparent)" in window, (
        "expected .section-caption's rule body to carry the 70% color-mix muted idiom")

    # Three `.dirty-bar {` rule bodies: the base rule (flex row, entrance
    # animation - no position declared) plus one per breakpoint (each
    # setting position: fixed with its own geometry). Assert the COUNT
    # that actually carries position: fixed is exactly two - never zero
    # (a breakpoint left position: static) and never three (the base
    # rule itself should not be the one setting it).
    dirty_bar_blocks = re.findall(r"\.dirty-bar \{[^}]*\}", source)
    assert len(dirty_bar_blocks) == 3, (
        "expected exactly three `.dirty-bar { ... }` rule bodies (the base rule plus one per "
        "breakpoint), got %d" % len(dirty_bar_blocks))
    fixed_count = sum(1 for block in dirty_bar_blocks if "position: fixed" in block)
    assert fixed_count == 2, (
        "expected exactly two of the three `.dirty-bar { ... }` rule bodies to set position: "
        "fixed (one per breakpoint), got %d" % fixed_count)
    assert ".dirty-bar[hidden]" in source, "expected the `.dirty-bar[hidden] { display: none; }` override to survive"
    assert ".dirty-bar__cancel {" in source, "expected `.dirty-bar__cancel`'s own quiet-wash override to survive"


def test_skypane_bar_arrive_keyframes_is_referenced_again_by_the_restored_bar(served_css):
    """the @keyframes skypane-bar-arrive block - kept deliberately orphaned by 27-04 specifically
    so a future restoration would not need to move the file's pinned @keyframes count - is
    REFERENCED again by the restored .dirty-bar base rule's own animation: declaration, reused
    rather than reinvented (CFG-77/CFG-78, 28-08-PLAN.md Task 2)"""
    source = served_css
    keyframes_marker = "@keyframes skypane-bar-arrive {"
    assert source.count(keyframes_marker) == 1, (
        "expected exactly one %s block (still the same one, never duplicated), got %d"
        % (keyframes_marker, source.count(keyframes_marker)))
    assert "animation: skypane-bar-arrive" in source, (
        "expected the restored .dirty-bar base rule to declare animation: skypane-bar-arrive "
        "var(--motion-fast) ease-out - REUSING the block 27-04 deliberately kept orphaned for "
        "exactly this restoration, rather than leaving the bar with no entrance or reinventing a "
        "second block")
    assert source.count("animation: skypane-bar-arrive") == 1, (
        "expected exactly ONE rule to reference animation: skypane-bar-arrive, got %d - a second "
        "consumer would be a genuinely new use this plan did not intend"
        % source.count("animation: skypane-bar-arrive"))


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
    event's own default action - and the file's header states both the standing constraint AND
    this one named exception in the same breath (CFG-77/CFG-78, 28-08-PLAN.md Task 3)

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
    assert "never introduce a network call" in source, (
        "expected the header to restore its 'never introduce a network call' constraint")
    assert "ONE NAMED EXCEPTION" in source, (
        "expected the header to name the ONE timer exception explicitly, in the same breath as "
        "the constraint")


# ======================================================================
# Section 11: 15-05-PLAN.md Task 3 (D-10, D-11, 15-VALIDATION.md row 10)
# - the per-flight colour-rules editor's markup/copy checks, relocated
# into the Aspect card's own "Per-flight rules" usage panel by
# 21-05/30-05-PLAN.md.
# ======================================================================

def test_aspect_card_full_shape_checklist():
    """the Aspect card's full shape, as a relationship rather than a list of endpoints: one card
    after the Look section intro, its four accordion rows' data-usage values in COLOUR_USAGES'
    own locked order, exactly one row open (departures), only the last row secondary, exactly one
    .palette grid per theme row and none in the rules row, zero occurrences of any retired
    mechanism's markup, and no section-caption paragraph immediately after the heading (CFG-85,
    30-05-PLAN.md Task 1, replacing the retired _frame_colours_card_full_shape_checklist)"""
    ctx = {
        "device_config": {"theme": "white", "tracked_runway": "3"},
        "colour_rules": {kind: {} for kind in colour_rules.RULE_KINDS},
        "poll_cooldown_remaining": 0,
    }
    rendered = config_page.render(ctx, scope=config_page.SCOPE_DISPLAY)

    # Exactly one Aspect card, positioned after the Look section intro.
    look_pos = rendered.index('id="%s"' % config_page.DISPLAY_LOOK_SECTION_ID)
    assert rendered.count('class="page-section aspect-card') == 1, (
        "expected exactly one .aspect-card, got %d" % rendered.count('class="page-section aspect-card'))
    aspect_pos = rendered.index('class="page-section aspect-card')
    assert look_pos < aspect_pos, "expected the Aspect card after the Look section intro"

    # Exactly len(COLOUR_USAGES) accordion rows, data-usage values in
    # document order equal to COLOUR_USAGES itself.
    row_pattern = re.compile(
        r'<details class="([^"]*)" name="%s" data-usage="([^"]*)"( open)?>'
        % re.escape(config_page.ASPECT_ROWS_GROUP_NAME))
    rows = row_pattern.findall(rendered)
    usages_in_order = [usage for _cls, usage, _open in rows]
    assert usages_in_order == list(config_page.COLOUR_USAGES), (
        "expected the accordion rows' data-usage values, in document order, to equal "
        "COLOUR_USAGES exactly, got %r" % (usages_in_order,))

    # Exactly one row carries `open`, and it is departures.
    open_usages = [usage for _cls, usage, is_open in rows if is_open]
    assert open_usages == [config_page.COLOUR_USAGE_DEPARTURES], (
        "expected only the departures row open by default, got %r" % (open_usages,))

    # The last row, and only it, carries usage-row--secondary.
    secondary_usages = [
        usage for cls, usage, _open in rows if "usage-row--secondary" in cls.split()]
    assert secondary_usages == [config_page.COLOUR_USAGES[-1]], (
        "expected only the last row (%r) to carry usage-row--secondary, got %r"
        % (config_page.COLOUR_USAGES[-1], secondary_usages))

    # Each of the three theme rows holds exactly one .palette grid; the
    # rules row holds none.
    for usage in config_page.COLOUR_USAGES:
        start, end = cp.aspect_usage_row_bounds(rendered, usage)
        palette_count = rendered[start:end].count('class="palette" role="radiogroup"')
        expected = 0 if usage == config_page.COLOUR_USAGE_RULES else 1
        assert palette_count == expected, (
            "expected %d .palette grid(s) inside the %r row, got %d" % (expected, usage, palette_count))

    # Zero occurrences of every retired mechanism's own markup, page-wide.
    for token in cp.ASPECT_RETIRED_MARKUP_TOKENS:
        count = rendered.count(token)
        assert count == 0, "expected zero occurrences of the retired token %r, got %d" % (token, count)

    # The <h2> immediately inside the card is ASPECT_HEADING at
    # ASPECT_HEADING_ID, and the element right after it is NOT a
    # section-caption paragraph - the no-caption half of CFG-85.
    heading_needle = '<h2 class="text-heading" id="%s">%s</h2>' % (
        config_page.ASPECT_HEADING_ID, escape_html(i18n.t(config_page.ASPECT_HEADING)))
    assert heading_needle in rendered, "expected the Aspect <h2> at ASPECT_HEADING_ID"
    after_heading = rendered[rendered.index(heading_needle) + len(heading_needle):]
    assert not after_heading.startswith('<p class="text-label section-caption"'), (
        "expected no section-caption paragraph immediately after the Aspect heading - CFG-85 "
        "retires the caption")


def test_rules_row_renders_inside_aspect_after_form():
    """render() places the Aspect card, holding the rules row, after the settings </form> and
    before the Calendar card, with every theme/theme_arriving/calendar_theme_id radio still
    carrying form=settings-form (Phase 15 D-10, replacing the retired
    _rules_section_renders_inside_frame_colours_after_form)

    The rules row holds real <form> elements (the add form), and HTML forbids a nested <form>, so
    the whole Aspect card must be a sibling of #settings-form while every theme radio still
    reaches it through form="settings-form".
    """
    rendered = config_page.render({
        "device_config": {"theme": "white", "tracked_runway": "3", "led_enabled": True},
        "colour_rules": {kind: {} for kind in colour_rules.RULE_KINDS},
        "poll_cooldown_remaining": 0,
    }, scope=config_page.SCOPE_DISPLAY)
    # The settings form's OWN closing tag - never the bare first
    # `</form>` in the whole document, which would instead match the
    # Frame strip's own quick-switch <form>...</form> (it renders BEFORE
    # <form id="settings-form"> opens) and pass vacuously regardless of
    # where the real form actually closes.
    form_start = rendered.index('<form class="config-form" id="%s"' % config_page.SETTINGS_FORM_ID)
    form_end = rendered.index("</form>", form_start)
    aspect_pos = rendered.index('class="page-section aspect-card')
    rules_start, rules_end = cp.aspect_usage_row_bounds(rendered, config_page.COLOUR_USAGE_RULES)
    assert form_end < aspect_pos < rules_start, (
        "expected </form> < the Aspect card < the rules row, got positions %d/%d/%d"
        % (form_end, aspect_pos, rules_start))
    for field in ("theme", "theme_arriving", "calendar_theme_id"):
        total = rendered.count('name="%s" value="' % field)
        with_form = len(re.findall(
            r'name="%s" value="[^"]*" class="visually-hidden"( form="%s")'
            % (re.escape(field), re.escape(config_page.SETTINGS_FORM_ID)), rendered))
        assert with_form == total, (
            "expected every %s radio to carry form=%r, got %d/%d"
            % (field, config_page.SETTINGS_FORM_ID, with_form, total))


def test_rules_section_empty_state_then_list_once_a_rule_exists(tmp_path):
    """the rules section renders the empty state with no rules, and the empty state is replaced
    by the .rule-list once a rule exists (D-15c/d, retargeted from the retired
    cards-then-table shape)"""
    empty_ctx = {
        "device_config": {"theme": "white", "tracked_runway": "3"},
        "colour_rules": {kind: {} for kind in colour_rules.RULE_KINDS},
        "poll_cooldown_remaining": 0,
    }
    rendered = config_page.render(empty_ctx, scope=config_page.SCOPE_DISPLAY)
    rules_segment = cp.rules_row_segment(rendered)
    assert config_page.RULES_EMPTY_HEADING in rules_segment, "expected the empty-state heading with no rules"
    # 20-09-PLAN.md Task 3 (D-15c/d): the retired table/card split is
    # gone outright - a plain .rule-list, never a table.
    assert "rule-list" not in rules_segment and "<table" not in rules_segment, (
        "expected no list markup in the empty-state branch")

    result = colour_rules.add_rule(
        str(tmp_path), "callsign", "AFR1234", "white", now="2026-01-01T00:00:00+00:00")
    assert result == colour_rules.ADD_OK_NEW, "test setup failure: add_rule() returned %r" % (result,)
    registry = colour_rules.load_colour_rules(str(tmp_path))

    filled_ctx = dict(empty_ctx)
    filled_ctx["colour_rules"] = registry
    filled_ctx["now"] = "2026-01-02T00:00:00+00:00"
    rendered = config_page.render(filled_ctx, scope=config_page.SCOPE_DISPLAY)
    rules_segment = cp.rules_row_segment(rendered)
    assert config_page.RULES_EMPTY_HEADING not in rules_segment, "expected the empty state to be replaced once a rule exists"
    assert '<ul class="rule-list">' in rules_segment, "expected the .rule-list once a rule exists"
    assert "AFR1234" in rules_segment, "expected the seeded rule's key to appear in the rendered list"


def test_rules_list_orders_most_specific_first_then_alphabetically(tmp_path):
    """a seeded set of rules of every kind renders most-specific first (callsign, then hex, then
    prefix), alphabetically within each kind (D-15c)

    colour_rules.rule_rows() itself already guarantees this order (RULE_KINDS order, then sorted
    value) - this check pins _rule_list_html()'s own consumption of that order at the
    rendered-markup level, not just at the data layer.
    """
    tmpdir = str(tmp_path)
    for kind, value, theme_id in (
        ("prefix", "AFR", "red"),
        ("callsign", "BAW1234", "blue"),
        ("hex", "3944F2", "white"),
        ("callsign", "AFR1234", "black"),
    ):
        result = colour_rules.add_rule(tmpdir, kind, value, theme_id, now="2026-01-01T00:00:00+00:00")
        assert result == colour_rules.ADD_OK_NEW, "test setup failure: add_rule(%r) returned %r" % (kind, result)
    registry = colour_rules.load_colour_rules(tmpdir)
    rendered = config_page.render({
        "device_config": {"theme": "white", "tracked_runway": "3"},
        "colour_rules": registry,
        "poll_cooldown_remaining": 0,
        "now": "2026-01-02T00:00:00+00:00",
    }, scope=config_page.SCOPE_DISPLAY)
    list_match = re.search(r'<ul class="rule-list">(.*?)</ul>', rendered, re.S)
    assert list_match, "expected a .rule-list"
    list_segment = list_match.group(1)
    expected_order = ["AFR1234", "BAW1234", "3944F2", "AFR"]
    positions = [
        list_segment.index('<span class="rule-row__key mono">%s</span>' % value)
        for value in expected_order
    ]
    assert positions == sorted(positions), (
        "expected callsign(alpha)/hex/prefix order %r, got positions %r" % (expected_order, positions))


def test_aspect_rules_copy_appears_escaped_verbatim():
    """every rules-editor copy string - heading, caption, field labels, kind labels/titles,
    empty-state heading/body, and the How-rules-combine disclosure - appears escaped-verbatim,
    matching 20-UI-SPEC.md's Copywriting Contract byte for byte (30-05-PLAN.md Task 3, replacing
    the retired _rules_copy_appears_escaped_verbatim)"""
    rendered = config_page.render({
        "device_config": {"theme": "white", "tracked_runway": "3"},
        "colour_rules": {kind: {} for kind in colour_rules.RULE_KINDS},
        "poll_cooldown_remaining": 0,
    }, scope=config_page.SCOPE_DISPLAY)
    copy_strings = (
        config_page.FRAME_COLOURS_ROW_LABELS[config_page.COLOUR_USAGE_RULES],
        config_page.RULES_SECTION_CAPTION,
        config_page.RULE_KIND_FIELD_LABEL,
        config_page.RULE_VALUE_FIELD_LABEL,
        config_page.RULE_ADD_BUTTON_TEXT,
        config_page.RULES_EMPTY_HEADING,
        config_page.RULES_EMPTY_BODY,
        config_page.RULES_HOW_RULES_COMBINE_SUMMARY,
        config_page.RULES_HOW_RULES_COMBINE_BODY,
    )
    for text in copy_strings:
        assert escape_html(text) in rendered, "expected %r to appear escaped-verbatim in the rendered page" % (text,)
    for kind, label in config_page.RULE_KIND_LABELS.items():
        assert escape_html(label) in rendered, "expected the kind label %r (for %r) to appear escaped-verbatim" % (label, kind)
    for kind, title in config_page.RULE_KIND_TITLES.items():
        assert escape_html(title) in rendered, "expected the kind title %r (for %r) to appear escaped-verbatim" % (title, kind)


def test_aspect_rules_row_label_locked_verbatim():
    """the rules row label equals 21-UI-SPEC.md's locked "Per-flight rules" text exactly, and its
    empty-state meta reads FRAME_COLOURS_RULES_EMPTY_META's real value, never ROADMAP's own
    paraphrase (D-06/D-07, 30-05-PLAN.md Task 2, replacing the retired
    _frame_colours_rules_row_label_locked_verbatim)

    Keeps the original lock - FRAME_COLOURS_ROW_LABELS[COLOUR_USAGE_RULES] is still exactly
    "Per-flight rules" - and adds a second lock 30-UI-SPEC.md's own copy table corrects: the
    rules row's empty-state meta must read FRAME_COLOURS_RULES_EMPTY_META's real value ("No rules
    yet"), never a plausible-sounding paraphrase.
    """
    assert config_page.FRAME_COLOURS_ROW_LABELS[config_page.COLOUR_USAGE_RULES] == "Per-flight rules", (
        "expected the rules row label to equal the locked \"Per-flight rules\" text exactly, "
        "got %r" % (config_page.FRAME_COLOURS_ROW_LABELS[config_page.COLOUR_USAGE_RULES],))
    rendered = config_page.render({
        "device_config": {"theme": "white", "tracked_runway": "3"},
        "colour_rules": {kind: {} for kind in colour_rules.RULE_KINDS},
        "poll_cooldown_remaining": 0,
    }, scope=config_page.SCOPE_DISPLAY)
    rules_start, rules_end = cp.aspect_usage_row_bounds(rendered, config_page.COLOUR_USAGE_RULES)
    summary_segment = rendered[rules_start:rules_end].split("</summary>", 1)[0]
    empty_meta_needle = escape_html(config_page.FRAME_COLOURS_RULES_EMPTY_META)
    assert empty_meta_needle in summary_segment, (
        "expected the rules row's empty-state meta to read FRAME_COLOURS_RULES_EMPTY_META (%r) "
        "verbatim, not a paraphrase" % (config_page.FRAME_COLOURS_RULES_EMPTY_META,))
    assert "Aucune règle" not in summary_segment, (
        "expected the rules row's meta to NEVER read ROADMAP's own paraphrase 'Aucune règle · Ajouter'")


def test_rules_no_select_and_three_named_radios_one_checked():
    """the Flight-colours section carries no <select>, and its add form's three rule_kind radios
    carry the three kind ids and the three technical titles, exactly one checked by default
    (D-15b)"""
    rendered = config_page.render({
        "device_config": {"theme": "white", "tracked_runway": "3"},
        "colour_rules": {kind: {} for kind in colour_rules.RULE_KINDS},
        "poll_cooldown_remaining": 0,
    }, scope=config_page.SCOPE_DISPLAY)
    rules_segment = cp.rules_row_segment(rendered)
    assert "<select" not in rules_segment, "expected no <select> anywhere in the Flight-colours section (D-15b)"
    radio_count = rules_segment.count('name="rule_kind"')
    assert radio_count == len(colour_rules.RULE_KINDS), (
        "expected %d rule_kind radios, got %d" % (len(colour_rules.RULE_KINDS), radio_count))
    for kind in colour_rules.RULE_KINDS:
        assert 'id="rule-kind-%s"' % kind in rules_segment, "expected a rule_kind radio with id rule-kind-%s" % kind
        assert 'title="%s"' % escape_html(config_page.RULE_KIND_TITLES[kind]) in rules_segment, (
            "expected the %s radio's label to carry the technical title" % kind)
    # Scoped to just the three rule_kind <input> tags themselves - the
    # compact theme-chip grid immediately below also uses " checked" for
    # its own selected chip, which a whole-segment count would wrongly
    # fold in.
    kind_inputs = re.findall(r'<input type="radio" name="rule_kind"[^>]*>', rules_segment)
    assert len(kind_inputs) == len(colour_rules.RULE_KINDS), (
        "expected %d rule_kind <input> tags, got %d" % (len(colour_rules.RULE_KINDS), len(kind_inputs)))
    checked_inputs = [tag for tag in kind_inputs if " checked" in tag]
    assert len(checked_inputs) == 1, "expected exactly one checked rule_kind radio by default, got %d" % len(checked_inputs)
    assert 'value="%s"' % colour_rules.RULE_KIND_CALLSIGN in checked_inputs[0], (
        "expected the callsign/Flight radio to be the one checked by default")


def test_rules_row_carries_pill_badge_and_confirmed_remove_form(tmp_path):
    """a rendered rule row carries a .banner__pill kind badge with the plain-language word, a
    computed _palette_hex() swatch dot, and a data-confirm Remove form (D-15c)"""
    result = colour_rules.add_rule(
        str(tmp_path), "callsign", "AFR1234", "white", now="2026-01-01T00:00:00+00:00")
    assert result == colour_rules.ADD_OK_NEW, "test setup failure: add_rule() returned %r" % (result,)
    registry = colour_rules.load_colour_rules(str(tmp_path))
    rendered = config_page.render({
        "device_config": {"theme": "white", "tracked_runway": "3"},
        "colour_rules": registry,
        "poll_cooldown_remaining": 0,
        "now": "2026-01-02T00:00:00+00:00",
    }, scope=config_page.SCOPE_DISPLAY)
    row_match = re.search(r'<li class="rule-row">(.*?)</li>', rendered, re.S)
    assert row_match, "expected a .rule-row list item"
    row = row_match.group(1)
    assert 'class="rule-row__kind banner__pill"' in row, "expected the kind badge to compose .banner__pill"
    assert escape_html(config_page.RULE_KIND_LABELS["callsign"]) in row, "expected the plain-language kind word in the badge"
    assert "data-confirm=" in row, "expected the Remove form to carry data-confirm (D-15c, locked)"
    assert escape_html(config_page.RULE_REMOVE_BUTTON_TEXT) in row, (
        "expected the Remove button's own text, not the airlines gallery's Delete")
    expected_hex = config_page._palette_hex(device_config.THEMES["white"]["departing_index"])
    assert 'class="theme-chip__dot" style="background:%s"' % escape_html(expected_hex) in row, (
        "expected the row's swatch dot to carry the real _palette_hex() value")


def test_rules_empty_state_carries_no_heading_element():
    """the empty state is muted sans copy in .empty-state-plain and carries no <h*> heading
    element, never the serif empty_state() heading (D-15d)"""
    rendered = config_page.render({
        "device_config": {"theme": "white", "tracked_runway": "3"},
        "colour_rules": {kind: {} for kind in colour_rules.RULE_KINDS},
        "poll_cooldown_remaining": 0,
    }, scope=config_page.SCOPE_DISPLAY)
    rules_segment = cp.rules_row_segment(rendered)
    empty_match = re.search(r'<div class="empty-state-plain">(.*?)</div>', rules_segment, re.S)
    assert empty_match, "expected the .empty-state-plain wrapper"
    assert "<h" not in empty_match.group(1), "expected the empty state to carry no heading element, muted sans only (D-15d)"
    assert escape_html(config_page.RULES_EMPTY_HEADING) in empty_match.group(1), "expected the empty-state heading sentence"
