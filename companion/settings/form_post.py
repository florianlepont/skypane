"""Per-settings-group validate-and-resolve helpers for the settings
page module's handle_post().

Each function below owns one settings group's own submitted-field
checks and, once they pass, that group's own resolved keyword
argument(s) for server.device_config.save_device_config() — a dict
handle_post() merges into the single call it makes once every group
has passed. A function that finds an invalid submitted value notes the
error (via companion.settings.form's _note_error) and returns FAILED
instead, so handle_post() can return the same save-failed flash key
immediately, without calling the groups after it — exactly the
all-or-nothing, first-error-wins behaviour the unmodified, unsplit
handle_post() had.

handle_post() calls these in the exact sequence the unmodified
function checked the same fields in, so a submission with several
invalid fields at once still reports the same one, in the same order,
as before the split. Where the unmodified code checked a group's
fields at two separate points (a field checked early, its value
resolved — or a sibling field checked — later), that group gets two
functions here (a "check" one and a resolve one, or two check
functions), called from handle_post() at those same two points; every
other group's check and resolve happened together in one place
already, so one function covers it.

Never imports the settings page module: a page module may never be
imported back by a module it itself imports.
"""
import re

from companion import i18n
from companion import screens
from companion.settings.form import _note_error
from server import device_config


# The single sentinel every resolver below returns instead of a kwargs
# dict when its own field(s) failed validation — `_note_error()` has
# already recorded the message. Identity-compared only, never a value a
# real kwargs dict could be mistaken for.
FAILED = object()

# handle_post()'s per-field error messages, one constant per rejected
# field, so the copy exists in exactly one place. Sentence case, no
# stack-trace vocabulary, matching the settings page's label voice.
# Moved here (rather than staying in the settings page module) because
# this module's own resolvers are the ones that raise them, and that
# module may never be imported back into this one.
ERROR_INVALID_CHOICE = i18n.msg(
    "display.that_is_not_one_of_the_available_choices",
    "That is not one of the available choices.")
ERROR_UNEXPECTED_SWITCH_VALUE = i18n.msg(
    "display.that_switch_sent_an_unexpected_value",
    "That switch sent an unexpected value.")
ERROR_WAKE_INTERVAL_RANGE = i18n.msg(
    "display.enter_a_whole_number_of_seconds_between_60_and",
    "Enter a whole number of seconds between 60 and 3600.")
ERROR_QUIET_HOURS_TIME_SHAPE = i18n.msg(
    "display.enter_a_time_as_hh_mm_for_example_23_00",
    "Enter a time as HH:MM, for example 23:00.")
# Covers both the over-length and the contradictory (calendar_url +
# calendar_disconnect together) cases; deliberately never echoes any
# part of the submitted URL back.
ERROR_CALENDAR_URL_INVALID = i18n.msg(
    "display.that_link_is_too_long_or_conflicts_with_the",
    "That link is too long, or conflicts with the disconnect option below.")

# The sole accepted submitted value for each checkbox — shared by the
# group's own markup (companion/settings/*.py) and this module's own
# validators so the two can never drift apart.
LED_CHECKBOX_VALUE = "on"
QUIET_HOURS_CHECKBOX_VALUE = "on"
DISPLAY_CHECKBOX_VALUE = "on"
# submitted_calendar_signal()'s gates compare a submitted
# calendar_disconnect field against this value, kept deliberately
# reachable for a hostile client crafting that field into a /settings
# POST. The dedicated CALENDAR_DISCONNECT_ROUTE never reads this value
# at all — it always means "disconnect", once its own confirm gate
# passes.
CALENDAR_DISCONNECT_CHECKBOX_VALUE = "on"

# The four outcomes of resolving the submitted calendar fields (the
# settings page's own submitted_calendar_signal()'s return values). Plain
# strings, never rendered and never travel in a URL. Four distinct
# sentinels (not e.g. two bools) so a caller cannot mistake one outcome
# for another by falsy-comparing the wrong pair.
CALENDAR_URL_SIGNAL_CARRY_FORWARD = "carry_forward"
CALENDAR_URL_SIGNAL_SET = "set"
CALENDAR_URL_SIGNAL_CLEAR = "clear"
CALENDAR_URL_SIGNAL_INVALID = "invalid"

# A local copy of device_config's private HH:MM pattern — not imported,
# since it is private to that module. UX pre-check only:
# save_device_config()'s own identical gate is authoritative; a test
# pins the two patterns against the same input table so they cannot
# silently drift apart.
_QUIET_HOURS_TIME_RE = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)\Z")


def resolve_theme(form, errors):
    """Theme group, step 1: the submitted theme id's membership check.
    theme_arriving is a separate function (`resolve_theme_arriving`),
    called later — the unmodified code checked several other groups'
    fields between the two.
    """
    submitted_theme = form.get("theme")
    if submitted_theme is not None and submitted_theme not in device_config.THEME_IDS:
        _note_error(errors, "theme", ERROR_INVALID_CHOICE)
        return FAILED
    return {"theme": submitted_theme}


def resolve_screen(form, errors):
    """Screen group: the submitted screen_id's membership check."""
    submitted_screen_id = form.get("screen_id")
    if submitted_screen_id is not None and submitted_screen_id not in screens.SCREEN_IDS:
        _note_error(errors, "screen_id", ERROR_INVALID_CHOICE)
        return FAILED
    return {"screen_id": submitted_screen_id}


def resolve_calendar_signal(calendar_signal, errors):
    """Calendar group, step 1: rejects an already-resolved INVALID
    signal (the settings page's own submitted_calendar_signal() computes
    it from the raw form). No kwargs of its own — the actual calendar_theme_id
    save field is a separate group field (`resolve_calendar_theme_id`),
    and the URL write itself happens after save_device_config(), never
    through this dict.
    """
    if calendar_signal == CALENDAR_URL_SIGNAL_INVALID:
        _note_error(errors, "calendar_url", ERROR_CALENDAR_URL_INVALID)
        return FAILED
    return {}


def resolve_calendar_theme_id(form, errors):
    """Calendar group, step 2: the submitted calendar_theme_id's
    membership check. Exempts "" in addition to a real theme id: the
    "Same as departures" chip submits "" for this field, and rejecting
    it would reject the whole save whenever a user picks that option.
    """
    submitted_calendar_theme_id = form.get("calendar_theme_id")
    if (
        submitted_calendar_theme_id is not None
        and submitted_calendar_theme_id not in ("",) + device_config.THEME_IDS
    ):
        _note_error(errors, "calendar_theme_id", ERROR_INVALID_CHOICE)
        return FAILED
    return {"calendar_theme_id": submitted_calendar_theme_id}


def resolve_theme_arriving(form, in_scope, errors):
    """Theme group, step 2: theme_arriving's own membership check, plus
    its final resolved value — the resolution half never fails (every
    value it can produce here has already passed the membership check
    above), so combining it with the check does not change which field
    an invalid submission reports.

    Out of scope or genuinely absent -> unchanged; "" -> CLEAR_THEME_ARRIVING;
    anything else has already passed the membership gate above, so it is a
    real theme id.
    """
    submitted_theme_arriving = form.get("theme_arriving")
    if (
        submitted_theme_arriving is not None
        and submitted_theme_arriving not in ("",) + device_config.THEME_IDS
    ):
        _note_error(errors, "theme_arriving", ERROR_INVALID_CHOICE)
        return FAILED
    if screens.GROUP_THEME not in in_scope:
        theme_arriving = None
    elif submitted_theme_arriving is None:
        theme_arriving = None
    elif submitted_theme_arriving == "":
        theme_arriving = device_config.CLEAR_THEME_ARRIVING
    else:
        theme_arriving = submitted_theme_arriving
    return {"theme_arriving": theme_arriving}


def resolve_runway(form, errors):
    """Runway group: the submitted tracked_runway's membership check."""
    submitted_runway = form.get("tracked_runway")
    if submitted_runway is not None and submitted_runway not in device_config.RUNWAY_IDS:
        _note_error(errors, "tracked_runway", ERROR_INVALID_CHOICE)
        return FAILED
    return {"tracked_runway": submitted_runway}


def resolve_quiet_hours_times(form, errors):
    """Quiet hours group, step 1: the start/end time fields' shape
    check. quiet_hours_enabled is a separate function
    (`resolve_quiet_hours_enabled`), called later — the unmodified code
    checked the LED group's field in between.

    A malformed value here is a real user error, reported at this
    field; absent still means unchanged (including structural absence
    on a scope that never rendered this group).
    """
    submitted_qh_start = form.get("quiet_hours_start")
    submitted_qh_end = form.get("quiet_hours_end")
    if submitted_qh_start is not None and not _QUIET_HOURS_TIME_RE.match(submitted_qh_start):
        _note_error(errors, "quiet_hours_start", ERROR_QUIET_HOURS_TIME_SHAPE)
        return FAILED
    if submitted_qh_end is not None and not _QUIET_HOURS_TIME_RE.match(submitted_qh_end):
        _note_error(errors, "quiet_hours_end", ERROR_QUIET_HOURS_TIME_SHAPE)
        return FAILED
    return {"quiet_hours_start": submitted_qh_start, "quiet_hours_end": submitted_qh_end}


def resolve_led(form, errors):
    """LED group: the diagnostic-LED checkbox's own shape+resolve step,
    combined (as the unmodified code had them)."""
    submitted_led = form.get("led_enabled")
    if submitted_led is None:
        led_enabled = None
    elif submitted_led == LED_CHECKBOX_VALUE:
        led_enabled = True
    else:
        _note_error(errors, "led_enabled", ERROR_UNEXPECTED_SWITCH_VALUE)
        return FAILED
    return {"led_enabled": led_enabled}


def resolve_quiet_hours_enabled(form, errors):
    """Quiet hours group, step 2: the enabled checkbox's own
    shape+resolve step, checked after the LED group (see
    `resolve_quiet_hours_times`'s own docstring)."""
    submitted_qh_enabled = form.get("quiet_hours_enabled")
    if submitted_qh_enabled is None:
        quiet_hours_enabled = None
    elif submitted_qh_enabled == QUIET_HOURS_CHECKBOX_VALUE:
        quiet_hours_enabled = True
    else:
        _note_error(errors, "quiet_hours_enabled", ERROR_UNEXPECTED_SWITCH_VALUE)
        return FAILED
    return {"quiet_hours_enabled": quiet_hours_enabled}


def resolve_wake_interval(form, errors):
    """Wake interval group: the string-to-int conversion, range check
    and resolve step, combined (as the unmodified code had them)."""
    submitted_wake_interval = form.get("wake_interval_s")
    if submitted_wake_interval is None or submitted_wake_interval == "":
        wake_interval_s = None
    else:
        try:
            wake_interval_s = int(submitted_wake_interval)
        except ValueError:
            _note_error(errors, "wake_interval_s", ERROR_WAKE_INTERVAL_RANGE)
            return FAILED
        # A syntactically valid but out-of-range value would otherwise
        # only surface via save_device_config()'s own generic
        # ValueError; checked here to report it at this field.
        if not (
            device_config.WAKE_INTERVAL_MIN_S
            <= wake_interval_s
            <= device_config.WAKE_INTERVAL_MAX_S
        ):
            _note_error(errors, "wake_interval_s", ERROR_WAKE_INTERVAL_RANGE)
            return FAILED
    return {"wake_interval_s": wake_interval_s}


def resolve_display(form, errors):
    """Display group: the screen on/off checkbox's own shape+resolve
    step, combined (as the unmodified code had them)."""
    submitted_display = form.get("display_enabled")
    if submitted_display is None:
        display_enabled = None
    elif submitted_display == DISPLAY_CHECKBOX_VALUE:
        display_enabled = True
    else:
        _note_error(errors, "display_enabled", ERROR_UNEXPECTED_SWITCH_VALUE)
        return FAILED
    return {"display_enabled": display_enabled}
