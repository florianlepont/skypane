"""The Settings page: theme/runway/LED/quiet-hours/wake-interval/
calendar controls, rendered and validated against
`server.device_config`'s own registries, plus the per-flight
colour-rules editor and the manual "Trigger poll now" control (its
route, cooldown gate and poll trigger are owned by companion/app.py;
this module only renders its button/copy).
"""
from companion import i18n
from companion.layout import escape_html
import companion.layout as layout
import companion.page_context as page_context
from companion import screens
from companion import wake
from server import device_config
from server.plane import calendar_rules

from companion.settings import form_post

# Every settings-group module's names, re-exported here (explicit,
# aliased imports so ruff's F401 does not flag a name this module
# never calls itself but companion/app.py and the test suite read as
# config_page.X) so this split changes no external attribute path.
from companion.settings.form import (
    CALENDAR_HOW_IT_WORKS_SUMMARY as CALENDAR_HOW_IT_WORKS_SUMMARY,
    CURRENT_BADGE_ATTR as CURRENT_BADGE_ATTR,
    CURRENT_BADGE_LABEL as CURRENT_BADGE_LABEL,
    DIRTY_SECTION_ATTR as DIRTY_SECTION_ATTR,
    SETTINGS_FORM_ID as SETTINGS_FORM_ID,
    _describedby_attr as _describedby_attr,
    _field_error_attrs as _field_error_attrs,
    _field_error_html as _field_error_html,
    _submitted_checkbox_checked as _submitted_checkbox_checked,
    _submitted_or_current as _submitted_or_current)
from companion.settings.theme import (
    ASPECT_HEADING as ASPECT_HEADING,
    ASPECT_HEADING_ID as ASPECT_HEADING_ID,
    COLOUR_USAGE_ARRIVALS as COLOUR_USAGE_ARRIVALS,
    COLOUR_USAGE_CALENDAR as COLOUR_USAGE_CALENDAR,
    COLOUR_USAGE_DEPARTURES as COLOUR_USAGE_DEPARTURES,
    COLOUR_USAGE_RULES as COLOUR_USAGE_RULES,
    FRAME_COLOURS_ROW_LABELS as FRAME_COLOURS_ROW_LABELS,
    FRAME_PREVIEW_ROUTE_PREFIX as FRAME_PREVIEW_ROUTE_PREFIX,
    LOOK_FIELDS as LOOK_FIELDS,
    LOOK_SHEET_ID as LOOK_SHEET_ID,
    SAME_AS_DEPARTURES_LABEL as SAME_AS_DEPARTURES_LABEL,
    THEME_PREVIEW_ROUTE_PREFIX as THEME_PREVIEW_ROUTE_PREFIX,
    departures_safe_theme_id as departures_safe_theme_id,
    look_card_html as look_card_html)
from companion.settings.runway_led import (
    LED_SECTION_CAPTION as LED_SECTION_CAPTION,
    LED_SECTION_CAPTION_ID as LED_SECTION_CAPTION_ID,
    LED_SECTION_HEADING as LED_SECTION_HEADING,
    QUICK_LED_FORM_ID as QUICK_LED_FORM_ID,
    QUICK_LED_LABEL_ID as QUICK_LED_LABEL_ID,
    QUICK_LED_STATE_ID as QUICK_LED_STATE_ID,
    RUNWAY_GROUP_HEADING_ID as RUNWAY_GROUP_HEADING_ID,
    RUNWAY_IMAGE_ALT_TEMPLATE as RUNWAY_IMAGE_ALT_TEMPLATE,
    RUNWAY_IMAGE_ROUTE_PREFIX as RUNWAY_IMAGE_ROUTE_PREFIX,
    RUNWAY_SECTION_CAPTION as RUNWAY_SECTION_CAPTION,
    RUNWAY_SECTION_CAPTION_ID as RUNWAY_SECTION_CAPTION_ID,
    led_group as led_group,
    quick_led_form_html as quick_led_form_html,
    runway_fieldset as runway_fieldset)
from companion.settings.quiet_hours import (
    QUIET_DIAL_ARC_CLASS as QUIET_DIAL_ARC_CLASS,
    QUIET_DIAL_CLASS as QUIET_DIAL_CLASS,
    QUIET_DIAL_CLEARANCE as QUIET_DIAL_CLEARANCE,
    QUIET_DIAL_DAY_CLASS as QUIET_DIAL_DAY_CLASS,
    QUIET_DIAL_END_LABEL as QUIET_DIAL_END_LABEL,
    QUIET_DIAL_HANDLE_CLASS as QUIET_DIAL_HANDLE_CLASS,
    QUIET_DIAL_HANDLE_LAYER_CLASS as QUIET_DIAL_HANDLE_LAYER_CLASS,
    QUIET_DIAL_HANDLE_MAX as QUIET_DIAL_HANDLE_MAX,
    QUIET_DIAL_HANDLE_MIN as QUIET_DIAL_HANDLE_MIN,
    QUIET_DIAL_HANDLE_STEP as QUIET_DIAL_HANDLE_STEP,
    QUIET_DIAL_HANDLE_TRACK_CLASS as QUIET_DIAL_HANDLE_TRACK_CLASS,
    QUIET_DIAL_HOUR_CLASS as QUIET_DIAL_HOUR_CLASS,
    QUIET_DIAL_LABELLED_HOURS as QUIET_DIAL_LABELLED_HOURS,
    QUIET_DIAL_PAIR_ATTR as QUIET_DIAL_PAIR_ATTR,
    QUIET_DIAL_PAIR_PROPERTIES as QUIET_DIAL_PAIR_PROPERTIES,
    QUIET_DIAL_PAIR_PROPERTY_ATTR as QUIET_DIAL_PAIR_PROPERTY_ATTR,
    QUIET_DIAL_RADIUS as QUIET_DIAL_RADIUS,
    QUIET_DIAL_READOUT_CLASS as QUIET_DIAL_READOUT_CLASS,
    QUIET_DIAL_READOUT_TEMPLATE as QUIET_DIAL_READOUT_TEMPLATE,
    QUIET_DIAL_RING_CLASS as QUIET_DIAL_RING_CLASS,
    QUIET_DIAL_SIZE as QUIET_DIAL_SIZE,
    QUIET_DIAL_START_LABEL as QUIET_DIAL_START_LABEL,
    QUIET_DIAL_STROKE as QUIET_DIAL_STROKE,
    QUIET_HOURS_GROUP_HEADING_ID as QUIET_HOURS_GROUP_HEADING_ID,
    QUIET_HOURS_PRESET_ALWAYS_ON_LABEL as QUIET_HOURS_PRESET_ALWAYS_ON_LABEL,
    QUIET_HOURS_PRESET_ATTR as QUIET_HOURS_PRESET_ATTR,
    QUIET_HOURS_PRESET_NIGHT_END as QUIET_HOURS_PRESET_NIGHT_END,
    QUIET_HOURS_PRESET_NIGHT_LABEL as QUIET_HOURS_PRESET_NIGHT_LABEL,
    QUIET_HOURS_PRESET_NIGHT_START as QUIET_HOURS_PRESET_NIGHT_START,
    QUIET_HOURS_PRESET_WORKDAY_END as QUIET_HOURS_PRESET_WORKDAY_END,
    QUIET_HOURS_PRESET_WORKDAY_LABEL as QUIET_HOURS_PRESET_WORKDAY_LABEL,
    QUIET_HOURS_PRESET_WORKDAY_START as QUIET_HOURS_PRESET_WORKDAY_START,
    QUIET_HOURS_SECTION_CAPTION as QUIET_HOURS_SECTION_CAPTION,
    QUIET_HOURS_SECTION_CAPTION_ID as QUIET_HOURS_SECTION_CAPTION_ID,
    QUIET_HOURS_SECTION_HEADING as QUIET_HOURS_SECTION_HEADING,
    QUIET_NORMALISED_TIME_ATTR as QUIET_NORMALISED_TIME_ATTR,
    QUIET_PRESET_ROW_CLASS as QUIET_PRESET_ROW_CLASS,
    QUIET_TIMES_ROW_CLASS as QUIET_TIMES_ROW_CLASS,
    QUIET_WINDOW_MINUTES_PER_DAY as QUIET_WINDOW_MINUTES_PER_DAY,
    QuietWindowSpan as QuietWindowSpan,
    _HHMM_RE as _HHMM_RE,
    _QUIET_DIAL_DURATION_TEXTS as _QUIET_DIAL_DURATION_TEXTS,
    _QUIET_DIAL_FULL_TURN_DEG as _QUIET_DIAL_FULL_TURN_DEG,
    _QUIET_DIAL_TWELVE_OCLOCK_DEG as _QUIET_DIAL_TWELVE_OCLOCK_DEG,
    _normalised_time_html as _normalised_time_html,
    quiet_dial_handle_fraction as quiet_dial_handle_fraction,
    quiet_dial_handles_html as quiet_dial_handles_html,
    quiet_dial_html as quiet_dial_html,
    quiet_dial_readout_html as quiet_dial_readout_html,
    quiet_dial_svg as quiet_dial_svg,
    quiet_hours_group as quiet_hours_group,
    quiet_window_minute_of_day as quiet_window_minute_of_day,
    quiet_window_span as quiet_window_span)
from companion.settings.calendar import (
    CALENDAR_CONNECT_BUTTON_TEXT as CALENDAR_CONNECT_BUTTON_TEXT,
    CALENDAR_DISCONNECT_BUTTON_TEXT as CALENDAR_DISCONNECT_BUTTON_TEXT,
    CALENDAR_DISCONNECT_CANCEL_TEXT as CALENDAR_DISCONNECT_CANCEL_TEXT,
    CALENDAR_DISCONNECT_CONFIRM_BUTTON_TEXT as CALENDAR_DISCONNECT_CONFIRM_BUTTON_TEXT,
    CALENDAR_DISCONNECT_CONFIRM_FIELD as CALENDAR_DISCONNECT_CONFIRM_FIELD,
    CALENDAR_DISCONNECT_CONFIRM_HEADING as CALENDAR_DISCONNECT_CONFIRM_HEADING,
    CALENDAR_DISCONNECT_CONFIRM_QUESTION as CALENDAR_DISCONNECT_CONFIRM_QUESTION,
    CALENDAR_DISCONNECT_CONFIRM_SENTENCE as CALENDAR_DISCONNECT_CONFIRM_SENTENCE,
    CALENDAR_DISCONNECT_CONFIRM_VALUE as CALENDAR_DISCONNECT_CONFIRM_VALUE,
    CALENDAR_DISCONNECT_FORM_ID as CALENDAR_DISCONNECT_FORM_ID,
    CALENDAR_DISCONNECT_ROUTE as CALENDAR_DISCONNECT_ROUTE,
    CALENDAR_HOW_IT_WORKS_BODY as CALENDAR_HOW_IT_WORKS_BODY,
    CALENDAR_REPLACE_BUTTON_TEXT as CALENDAR_REPLACE_BUTTON_TEXT,
    CALENDAR_REPLACE_URL_SUMMARY as CALENDAR_REPLACE_URL_SUMMARY,
    CALENDAR_STATUS_CONNECTED_VERDICT as CALENDAR_STATUS_CONNECTED_VERDICT,
    CALENDAR_STATUS_DETAIL_SINGULAR_TEMPLATE as CALENDAR_STATUS_DETAIL_SINGULAR_TEMPLATE,
    CALENDAR_STATUS_DETAIL_TEMPLATE as CALENDAR_STATUS_DETAIL_TEMPLATE,
    CALENDAR_STATUS_FETCH_FAILED_DETAIL as CALENDAR_STATUS_FETCH_FAILED_DETAIL,
    CALENDAR_STATUS_NOT_CONNECTED_VERDICT as CALENDAR_STATUS_NOT_CONNECTED_VERDICT,
    CALENDAR_STATUS_PERMISSION_UNSAFE as CALENDAR_STATUS_PERMISSION_UNSAFE,
    CALENDAR_URL_FIELD_LABEL as CALENDAR_URL_FIELD_LABEL,
    CALENDAR_URL_HINT as CALENDAR_URL_HINT,
    CALENDAR_URL_HINT_ID as CALENDAR_URL_HINT_ID,
    CALENDAR_URL_MAX_LEN as CALENDAR_URL_MAX_LEN,
    _calendar_connection_html as _calendar_connection_html,
    _masked_calendar_url as _masked_calendar_url,
    calendar_disconnect_confirm_page as calendar_disconnect_confirm_page,
    calendar_special_row_html as calendar_special_row_html)
from companion.settings.rules import (
    POLL_COOLDOWN_HELPER_TEXT as POLL_COOLDOWN_HELPER_TEXT,
    POLL_COOLDOWN_TEMPLATE_TOKEN as POLL_COOLDOWN_TEMPLATE_TOKEN,
    POLL_COOLDOWN_TEXT_ID as POLL_COOLDOWN_TEXT_ID,
    POLL_SECTION_CAPTION as POLL_SECTION_CAPTION,
    POLL_SUBMIT_PENDING_TEXT as POLL_SUBMIT_PENDING_TEXT,
    POLL_TRIGGER_BUTTON_ID as POLL_TRIGGER_BUTTON_ID,
    RULES_ADD_ROUTE as RULES_ADD_ROUTE,
    RULES_DELETE_ROUTE_PREFIX as RULES_DELETE_ROUTE_PREFIX,
    RULES_DELETE_ROUTE_SUFFIX as RULES_DELETE_ROUTE_SUFFIX,
    RULES_SECTION_CAPTION as RULES_SECTION_CAPTION,
    RULE_ADD_BUTTON_TEXT as RULE_ADD_BUTTON_TEXT,
    RULE_KIND_FIELD_LABEL as RULE_KIND_FIELD_LABEL,
    RULE_KIND_HEADING_ID as RULE_KIND_HEADING_ID,
    RULE_KIND_LABELS as RULE_KIND_LABELS,
    RULE_KIND_TITLES as RULE_KIND_TITLES,
    RULE_REMOVE_BUTTON_TEXT as RULE_REMOVE_BUTTON_TEXT,
    RULE_REMOVE_CONFIRM_QUESTION as RULE_REMOVE_CONFIRM_QUESTION,
    RULE_SUGGESTIONS_LABEL as RULE_SUGGESTIONS_LABEL,
    RULE_THEME_HEADING_ID as RULE_THEME_HEADING_ID,
    RULE_VALUE_FIELD_LABEL as RULE_VALUE_FIELD_LABEL,
    RULE_VALUE_PLACEHOLDER as RULE_VALUE_PLACEHOLDER,
    SPECIAL_LOOKS_HEADING as SPECIAL_LOOKS_HEADING,
    _rule_add_form_html as _rule_add_form_html,
    _rule_delete_action as _rule_delete_action,
    _rule_kind_radio_html as _rule_kind_radio_html,
    _rule_list_html as _rule_list_html,
    _rule_row_html as _rule_row_html,
    _rule_suggestion_chips_html as _rule_suggestion_chips_html,
    poll_trigger_section as poll_trigger_section,
    special_looks_html as special_looks_html)
from companion.settings.wake_interval import (
    WAKE_BATTERY_DAYS_TEXT as WAKE_BATTERY_DAYS_TEXT,
    WAKE_BATTERY_DAY_TEXT as WAKE_BATTERY_DAY_TEXT,
    WAKE_BATTERY_INSTEAD_TEXT as WAKE_BATTERY_INSTEAD_TEXT,
    WAKE_BATTERY_SCREEN_OFF_TEXT as WAKE_BATTERY_SCREEN_OFF_TEXT,
    WAKE_BATTERY_UNKNOWN_TEXT as WAKE_BATTERY_UNKNOWN_TEXT,
    WAKE_BATTERY_WINDOW_DAYS as WAKE_BATTERY_WINDOW_DAYS,
    WAKE_FRESHNESS_TEXT as WAKE_FRESHNESS_TEXT,
    WAKE_GAUGE_BATTERY_ID as WAKE_GAUGE_BATTERY_ID,
    WAKE_GAUGE_CLASS as WAKE_GAUGE_CLASS,
    WAKE_GAUGE_FRESHNESS_ID as WAKE_GAUGE_FRESHNESS_ID,
    WAKE_GAUGE_SECONDS_PER_MINUTE as WAKE_GAUGE_SECONDS_PER_MINUTE,
    WAKE_INTERVAL_FIELD_NAME as WAKE_INTERVAL_FIELD_NAME,
    WAKE_INTERVAL_INPUT_ID as WAKE_INTERVAL_INPUT_ID,
    WAKE_INTERVAL_PLACEHOLDER_TEXT as WAKE_INTERVAL_PLACEHOLDER_TEXT,
    WAKE_INTERVAL_SECTION_CAPTION as WAKE_INTERVAL_SECTION_CAPTION,
    WAKE_INTERVAL_SECTION_CAPTION_ID as WAKE_INTERVAL_SECTION_CAPTION_ID,
    WAKE_INTERVAL_SECTION_HEADING as WAKE_INTERVAL_SECTION_HEADING,
    WAKE_INTERVAL_UNIT_LABEL as WAKE_INTERVAL_UNIT_LABEL,
    WAKE_SLIDER_CLASS as WAKE_SLIDER_CLASS,
    WAKE_SLIDER_INPUT_CLASS as WAKE_SLIDER_INPUT_CLASS,
    WAKE_SLIDER_LABEL as WAKE_SLIDER_LABEL,
    WAKE_SLIDER_STEP_S as WAKE_SLIDER_STEP_S,
    _wake_battery_cutoff_iso as _wake_battery_cutoff_iso,
    _wake_minutes as _wake_minutes,
    wake_battery_observed_text as wake_battery_observed_text,
    wake_battery_relative_template as wake_battery_relative_template,
    wake_battery_relative_text as wake_battery_relative_text,
    wake_battery_rows as wake_battery_rows,
    wake_freshness_text as wake_freshness_text,
    wake_gauge_interval_s as wake_gauge_interval_s,
    wake_gauges_html as wake_gauges_html,
    wake_interval_group as wake_interval_group,
    wake_screen_off_text as wake_screen_off_text,
    wake_slider_html as wake_slider_html)
# handle_post()'s own per-group resolvers moved to form_post.py (that
# module never imports this one back), so its shared error/checkbox
# constants and the calendar-signal sentinels live there now too;
# re-exported here so companion/app.py and the test suite keep reading
# them as config_page.X.
from companion.settings.form_post import (
    CALENDAR_DISCONNECT_CHECKBOX_VALUE as CALENDAR_DISCONNECT_CHECKBOX_VALUE,
    CALENDAR_URL_SIGNAL_CARRY_FORWARD as CALENDAR_URL_SIGNAL_CARRY_FORWARD,
    CALENDAR_URL_SIGNAL_CLEAR as CALENDAR_URL_SIGNAL_CLEAR,
    CALENDAR_URL_SIGNAL_INVALID as CALENDAR_URL_SIGNAL_INVALID,
    CALENDAR_URL_SIGNAL_SET as CALENDAR_URL_SIGNAL_SET,
    DISPLAY_CHECKBOX_VALUE as DISPLAY_CHECKBOX_VALUE,
    ERROR_CALENDAR_URL_INVALID as ERROR_CALENDAR_URL_INVALID,
    ERROR_INVALID_CHOICE as ERROR_INVALID_CHOICE,
    ERROR_QUIET_HOURS_TIME_SHAPE as ERROR_QUIET_HOURS_TIME_SHAPE,
    ERROR_UNEXPECTED_SWITCH_VALUE as ERROR_UNEXPECTED_SWITCH_VALUE,
    ERROR_WAKE_INTERVAL_RANGE as ERROR_WAKE_INTERVAL_RANGE,
    LED_CHECKBOX_VALUE as LED_CHECKBOX_VALUE,
    QUIET_HOURS_CHECKBOX_VALUE as QUIET_HOURS_CHECKBOX_VALUE,
    _QUIET_HOURS_TIME_RE as _QUIET_HOURS_TIME_RE)


# The single definition of this route. companion/app.py rebinds its own
# SETTINGS_ROUTE constant to this value rather than re-typing the
# literal. The old "/config" path is retired: it 404s by design, no
# redirect.
SETTINGS_ROUTE = "/settings"


# The one settings form renders as two pages sharing the same POST
# route and the same handle_post(): the everyday "Display" page (theme,
# quiet hours, screen on/off) and the advanced "Device" page (diagnostic
# LED, wake interval and manual refresh). Which groups land on which page is declared per screen type
# in companion/screens.py, not hard-coded here.
#
# `render(ctx)` with no scope renders the whole legacy page, every
# group, for existing harness checks against the full form;
# companion/app.py never uses that scope for a live route.
SCOPE_ALL = "all"
SCOPE_DISPLAY = "display"
SCOPE_DEVICE = "device"
SCOPES = (SCOPE_ALL, SCOPE_DISPLAY, SCOPE_DEVICE)

# Hidden form fields a scoped page submits so handle_post() knows which
# groups were on the page (absent checkbox => leave unchanged for a
# group that was never rendered, never switch it off) and where to
# redirect back to.
SCOPE_FIELD_NAME = "scope"
RETURN_TO_FIELD_NAME = "return_to"

# "Display"/"Device" reuse companion/ui_base.py's own nav-tab ids —
# msg() is idempotent on a repeat (id, English) pair, and a settings
# page module may not import a page-independent shell module's private
# constants, so the id is redeclared here rather than imported.
DISPLAY_PAGE_TITLE = i18n.msg("nav.display", "Display")
DEVICE_PAGE_TITLE = i18n.msg("nav.device", "Device")

# Display has one appearance flow. The base sources come first; flight
# rules are an optional override inside that flow, followed by the two
# separate scheduling controls below it.
DISPLAY_LOOK_SECTION_ID = "display-look"
DISPLAY_LOOK_INTRO = i18n.msg(
    "display.the_theme_flight_colours_and_calendar_that",
    "— the theme, flight colours and calendar that decide how the "
    "picture looks.")
DISPLAY_WATCHES_SECTION_ID = "display-watches"
DISPLAY_WATCHES_HEADING = i18n.msg("display.what_it_watches", "What it watches")
DISPLAY_WATCHES_INTRO = i18n.msg(
    "display.which_orly_runway_the_frame_is_watching",
    "— which Orly runway the frame is watching.")
DISPLAY_ON_SECTION_ID = "display-on"
DISPLAY_ON_HEADING = i18n.msg("display.when_it_is_on", "When it is on")
DISPLAY_ON_INTRO = i18n.msg(
    "display.when_the_screen_is_lit_and_when_it_stays_quiet",
    "— when the screen is lit and when it stays quiet.")


def scope_groups(scope, screen_id=None):
    """The ordered tuple of settings-group ids the given scope renders
    for the given screen type. SCOPE_ALL preserves the historical
    single-page order; the two live scopes read the screen type's own
    declaration in companion/screens.py.
    """
    screen = screens.screen_type(screen_id)
    if scope == SCOPE_DISPLAY:
        return tuple(screen["everyday_groups"])
    if scope == SCOPE_DEVICE:
        return tuple(screen["advanced_groups"])
    # Every registered group must appear somewhere in this fixed tuple:
    # a test pins the invariant that the two live scopes' groups are
    # disjoint and their union equals this tuple's own set exactly.
    return (
        screens.GROUP_THEME, screens.GROUP_RUNWAY, screens.GROUP_LED,
        screens.GROUP_QUIET_HOURS, screens.GROUP_WAKE_INTERVAL,
        screens.GROUP_CALENDAR)


def submitted_scope(form):
    """The scope a submitted settings form was rendered with — SCOPE_ALL
    when the field is absent (the legacy single-page form) or carries
    anything outside SCOPES (a crafted value degrades to the widest,
    most conservative reading rather than being rejected: every group's
    own validation still runs).
    """
    value = form.get(SCOPE_FIELD_NAME)
    return value if value in SCOPES else SCOPE_ALL


def submitted_return_route(form):
    """Where a settings POST redirects back to: the page it came from,
    validated byte-for-byte against the two scoped page routes, else
    the Display page. Never a raw form value.
    """
    value = form.get(RETURN_TO_FIELD_NAME)
    if value in (layout.DISPLAY_ROUTE, layout.DEVICE_ROUTE):
        return value
    return layout.DISPLAY_ROUTE


POLL_SECTION_HEADING = i18n.msg("display.refresh_now", "Refresh now")


# The Screen on/off and Quiet hours routes the Frame strip's switches
# post to. Home's own route constants are byte-for-byte duplicates,
# never imported: a page module may never import another page module.
QUICK_DISPLAY_ROUTE = "/quick/display"
QUICK_QUIET_HOURS_ROUTE = "/quick/quiet-hours"

# Names the native fallback Save button; companion/static/dirty-state.js
# does not import this module, so the value must be kept equal by hand
# (its sibling, DIRTY_SECTION_ATTR, moved to companion.settings.form —
# imported back below for this module's own remaining group builders).
STATIC_SAVE_FALLBACK_ATTR = "data-static-save-fallback"

# The words dirty-state.js's updateBar()/dirtySectionLabels() carry as
# translated data-* attributes on the save bar. Each constant's own
# English value is also dirty-state.js's documented `|| "English
# fallback"` literal, so the two can never silently disagree about what
# the bar renders without the attribute.
#
# DIRTY_BAR_INITIAL_TEXT is carried only as a data-* attribute, never
# used to seed [data-dirty-count]'s markup: the bar itself renders
# visible (not `hidden`), so seeding the count span with this text
# would announce a false "Unsaved changes" claim via `role="status"` on
# every page load before anything changed. dirty-state.js writes it
# only once it actually finds a difference.
DIRTY_BAR_INITIAL_TEXT = i18n.msg("display.unsaved_changes", "Unsaved changes")
DIRTY_CHANGED_SUFFIX = i18n.msg("display.changed", " changed")
DIRTY_AND = i18n.msg("display.and", " and ")
DIRTY_LIST_AND = i18n.msg("display.and_2", ", and ")
DIRTY_UNSAVED_SINGULAR = i18n.msg("display.1_unsaved_change", "1 unsaved change")
DIRTY_UNSAVED_PLURAL = i18n.msg("display.unsaved_changes_2", " unsaved changes")
# The ellipsis is the single U+2026 character, matching this module's
# "Polling…" and layout.py's "Reconnecting…" — never three periods.
DIRTY_SAVING_TEXT = i18n.msg("display.saving", "Saving…")


# The flash keys this module's handle_post() can return — the single
# source of truth companion/app.py's own flash-key constants and
# FLASH_MESSAGES dict reference.
FLASH_SAVED = "saved"
FLASH_SAVE_FAILED = "save_failed"
FLASH_POLL_TRIGGERED = "poll_triggered"
FLASH_POLL_COOLDOWN = "poll_cooldown"
# Distinct from FLASH_SAVE_FAILED: a run_once() exception inside
# POST /poll-now must not show "Couldn't save settings" for a failure
# unrelated to saving settings.
FLASH_POLL_FAILED = "poll_failed"
# Distinct from FLASH_POLL_COOLDOWN: this key means a poll is executing
# on this exact request right now, in another thread —
# `_POLL_LOCK.acquire(blocking=False)` failing is the only producer,
# closing the window where two requests could both observe zero
# cooldown and both call `poll_cycle.run_once()`.
FLASH_POLL_ALREADY_RUNNING = "poll_already_running"


# The flash keys this module's rule-add/rule-delete routes (owned by
# companion/app.py) can produce; app.py rebinds each under its own
# FLASH_KEY_RULE_* name and owns the message text/ARIA role.
FLASH_RULE_ADDED = "rule_added"
FLASH_RULE_REPLACED = "rule_replaced"
FLASH_RULE_KEY_INVALID = "rule_key_invalid"
FLASH_RULE_REGISTRY_FULL = "rule_registry_full"
FLASH_RULE_SAVE_FAILED = "rule_save_failed"
FLASH_RULE_DELETED = "rule_deleted"
FLASH_RULE_DELETE_FAILED = "rule_delete_failed"


CALENDAR_CONNECT_ROUTE = "/settings/calendar/connect"


# The look card's copy floor exempts these two: DISPLAY_LOOK_INTRO
# (a different card's own intro) and CALENDAR_URL_HINT (its wording is
# never to be shortened). Kept here, beside the strings they exempt,
# rather than in a second harness-side list that could drift from this
# one.
ASPECT_CAPTION_EXEMPTIONS = (
    DISPLAY_LOOK_INTRO,
    CALENDAR_URL_HINT,
)

# The flash keys the save-triggered immediate sync can produce;
# companion/app.py rebinds each under its own FLASH_KEY_CALENDAR_* name.
FLASH_CALENDAR_CONNECTED = "calendar_connected"
FLASH_CALENDAR_SYNC_FAILED = "calendar_sync_failed"
FLASH_CALENDAR_DISCONNECTED = "calendar_disconnected"
FLASH_CALENDAR_SYNC_DEFERRED = "calendar_sync_deferred"
# The two outcomes only POST /settings/calendar/connect can produce.
# The failure path reuses FLASH_CALENDAR_SYNC_FAILED rather than a
# third calendar failure message.
FLASH_CALENDAR_CONNECT_OK = "calendar_connect_ok"
FLASH_CALENDAR_CONNECT_INVALID = "calendar_connect_invalid"


def _display_groups_html(builders, groups):
    """Display scope's independent Runway and Quiet hours cards.

    The cards carry their own headings, so the former supersection
    headings repeated the same information. Both are siblings of the
    settings form and keep their fields associated with it via `form=`.
    """
    runway_html = (
        builders[screens.GROUP_RUNWAY]()
        if screens.GROUP_RUNWAY in groups else "")
    quiet_hours_html = (
        builders[screens.GROUP_QUIET_HOURS]()
        if screens.GROUP_QUIET_HOURS in groups else "")
    return runway_html, quiet_hours_html


def _device_groups_html(builders, groups):
    """Device shows only the controls that change its behaviour.

    Each card names its own task, so intermediate headings would only
    repeat information a person needs to scan and act on.
    """
    return "".join(
        builders[group]()
        for group in (screens.GROUP_WAKE_INTERVAL, screens.GROUP_LED)
        if group in groups and group in builders)


def _render_current_values(ctx):
    """The device_config-derived "current" values render() threads into
    every group builder, header slot and the look card — resolved
    once here from ctx's own device_config snapshot. `ctx` arrives
    already a `PageContext`, coerced once by render() itself.
    """
    device_cfg = ctx.device_config or {}
    # `is None`, not `or`: 0 is never a valid wake_interval_s. Falls back
    # to the deployed SKYPANE_SLEEP_S env default when device_config has
    # no value yet (e.g. a fresh install with no systemd unit).
    wake_interval_s = device_cfg.get("wake_interval_s")
    if wake_interval_s is None:
        wake_interval_s = ctx.wake_interval_env_default
    return {
        "device_cfg": device_cfg,
        # Explicit `.get()`, no `or` fallback below: `None` is a
        # meaningful value (no arrivals-theme override / no calendar
        # theme chosen yet), not an oversight.
        "theme_id": device_cfg.get("theme", device_config.DEFAULT_THEME_ID),
        "theme_arriving": device_cfg.get("theme_arriving"),
        "runway_id": device_cfg.get("tracked_runway", device_config.DEFAULT_RUNWAY_ID),
        "led_enabled": device_cfg.get("led_enabled", device_config.DEFAULT_LED_ENABLED),
        "quiet_start": device_cfg.get("quiet_hours_start", device_config.DEFAULT_QUIET_HOURS_START),
        "quiet_end": device_cfg.get("quiet_hours_end", device_config.DEFAULT_QUIET_HOURS_END),
        "wake_interval_s": wake_interval_s,
        "calendar_theme_id": device_cfg.get("calendar_theme_id"),
    }


def _render_calendar_and_poll_context(ctx):
    """The calendar-status and poll-cooldown values read straight from
    `ctx` (not `device_config`) that the Display scope's look card
    and the Poll section each need.
    """
    return {
        "calendar_configured": ctx.calendar_configured,
        "calendar_last_synced_at": ctx.calendar_last_synced_at,
        # last_attempt_at distinguishes "just connected, no sync yet"
        # from "has been failing"; entry_count feeds the status detail
        # template.
        "calendar_last_attempt_at": ctx.calendar_last_attempt_at,
        "calendar_entry_count": ctx.calendar_entry_count or 0,
        "calendar_drift": ctx.calendar_drift,
        "cooldown_remaining": (
            ctx.poll_cooldown_remaining if ctx.poll_cooldown_remaining is not None else 0),
    }


def _next_wake_clock_and_iso(ctx, device_cfg):
    """The shared next-wake clock string threaded into every group's
    caption and the Device header slot, plus the raw ISO timestamp
    `layout.frame_strip_html()` needs. `(None, next_wake_iso)` when the
    clock cannot be resolved (no check-in yet, or no known interval) —
    every consumer omits the suffix/line in that case rather than show
    a placeholder.
    """
    next_wake_clock = None
    next_wake_iso, _, _ = wake.next_wake_status(ctx.last_checkin_ts, device_cfg)
    if next_wake_iso:
        next_wake_parsed = layout.parse_iso(next_wake_iso)
        if next_wake_parsed is not None:
            next_wake_clock = layout.local_clock_text(
                next_wake_parsed, now_parsed=layout.parse_iso(ctx.now))
    return next_wake_clock, next_wake_iso


def _dirty_bar_strings():
    """The words dirty-state.js's own updateBar()/dirtySectionLabels()
    carry as translated data-* attributes on the save bar — resolved
    once here rather than inline in the final HTML assembly.
    """
    return {
        "changed_suffix": escape_html(i18n.t(DIRTY_CHANGED_SUFFIX)),
        "and_word": escape_html(i18n.t(DIRTY_AND)),
        "list_and": escape_html(i18n.t(DIRTY_LIST_AND)),
        "unsaved_singular": escape_html(i18n.t(DIRTY_UNSAVED_SINGULAR)),
        "unsaved_plural": escape_html(i18n.t(DIRTY_UNSAVED_PLURAL)),
        "saving": escape_html(i18n.t(DIRTY_SAVING_TEXT)),
        "initial_text": escape_html(i18n.t(DIRTY_BAR_INITIAL_TEXT)),
    }


def _group_builders(ctx, values, errors, submitted, next_wake_clock):
    """The lazy, scope-independent per-group builder table render()'s
    scope branches read from. screens.GROUP_THEME/GROUP_CALENDAR have
    no entry here: their own renderer (the look card, built by the
    Display branch) contains real <form> elements that must never
    render as a literal descendant of <form id="{SETTINGS_FORM_ID}">.
    """
    return {
        screens.GROUP_RUNWAY: lambda: runway_fieldset(
            values["runway_id"], ctx.runway_images or (),
            errors=errors, submitted=submitted),
        screens.GROUP_LED: lambda: led_group(
            values["led_enabled"], errors=errors, submitted=submitted,
            next_wake_clock=next_wake_clock),
        screens.GROUP_QUIET_HOURS: lambda: quiet_hours_group(
            values["quiet_start"], values["quiet_end"],
            errors=errors, submitted=submitted),
        # Read inside the lambda so it costs nothing unless this group
        # is actually in scope.
        screens.GROUP_WAKE_INTERVAL: lambda: wake_interval_group(
            values["wake_interval_s"], errors=errors, submitted=submitted,
            next_wake_clock=next_wake_clock,
            battery_rows=wake_battery_rows(ctx.state_dir, ctx.now)),
    }


def _render_display_scope(ctx, screen, screen_id, groups, builders, errors, submitted, values, calendar_status, next_wake_iso):
    """Display scope's own header, hidden scope fields, appearance flow,
    and scheduling cards. `groups_html` stays empty: every saved
    control here cross-submits from outside the physical form via
    `form="{SETTINGS_FORM_ID}"`, exactly like Runway/Calendar's own
    cards already do.

    Gated on GROUP_THEME alone: safe only because companion/screens.py's
    one registered screen type lists GROUP_THEME and GROUP_CALENDAR
    together (always both true or both false today). A future screen
    type with only one of the two must split this gate.
    """
    # Appearance controls are form-backed, so the refresh loop must not
    # replace this page while a visitor is editing them. The silent marker
    # keeps the frame strip on freshness.js's background refresh without a
    # visible freshness line, as on Home and Flights.
    header = layout.page_header(
        i18n.t(DISPLAY_PAGE_TITLE), freshness_html=layout.refresh_marker_html(ctx.now))
    frame_strip_section_html = ""
    if screens.GROUP_THEME in groups:
        # Resolved once here and shared: the calendar row falls back to
        # the departures look for its "same as departures" picture, the
        # same resolution look_card_html() applies to Arrivals.
        departures_safe_id = departures_safe_theme_id(values["theme_id"], submitted)
        calendar_row_html, calendar_disconnect_form_html = calendar_special_row_html(
            departures_safe_id, values["calendar_theme_id"], calendar_status["calendar_configured"],
            calendar_status["calendar_drift"], calendar_status["calendar_last_synced_at"],
            calendar_status["calendar_last_attempt_at"], ctx.now, calendar_status["calendar_entry_count"],
            errors=errors, submitted=submitted, state_dir=ctx.state_dir)
        # The section's own opening tag is formatted on its own: the card
        # carries literal "%s" alt-text templates for the picker script.
        aspect_section_html = (
            '<section id="%s" class="display-appearance" aria-labelledby="%s">' % (
                escape_html(DISPLAY_LOOK_SECTION_ID), escape_html(ASPECT_HEADING_ID))
            + look_card_html(
                values["theme_id"], values["theme_arriving"],
                special_looks_html(ctx, calendar_row_html), calendar_disconnect_form_html,
                errors=errors, submitted=submitted)
            + "</section>")
    else:
        aspect_section_html = ""
    display_watches_html, display_on_html = _display_groups_html(builders, groups)
    return {
        "header": header, "frame_strip_section_html": frame_strip_section_html,
        "hidden_html": _scope_fields_html(SCOPE_DISPLAY, layout.DISPLAY_ROUTE),
        "show_poll": False, "groups_html": "",
        "aspect_section_html": aspect_section_html,
        "display_watches_supersection_html": display_watches_html,
        "display_on_supersection_html": display_on_html,
    }


def _render_device_scope(screen, screen_id, groups, builders, errors, next_wake_clock):
    """Device's focused advanced controls and native form wiring."""
    header = layout.page_header(i18n.t(DEVICE_PAGE_TITLE))
    return {
        "header": header, "frame_strip_section_html": "",
        "hidden_html": _scope_fields_html(SCOPE_DEVICE, layout.DEVICE_ROUTE),
        "show_poll": bool(screen.get("has_manual_poll")),
        "groups_html": _device_groups_html(builders, groups),
        "aspect_section_html": "", "display_watches_supersection_html": "",
        "display_on_supersection_html": "",
    }


# SCOPE_ALL's own legacy page title, never rendered by a live route.
SCOPE_ALL_PAGE_TITLE = i18n.msg("display.settings", "Settings")


def _render_all_scope(groups, builders):
    """SCOPE_ALL's own legacy, never-served whole-page render, kept
    byte-identical to its pre-existing output for harness checks
    against the full form; no live app.py route uses it.
    """
    return {
        "header": layout.page_header(i18n.t(SCOPE_ALL_PAGE_TITLE)),
        "frame_strip_section_html": "", "hidden_html": "", "show_poll": True,
        "groups_html": "".join(builders[g]() for g in groups if g in builders),
        "aspect_section_html": "", "display_watches_supersection_html": "",
        "display_on_supersection_html": "",
    }


def _poll_html_for_scope(scope, show_poll, cooldown_remaining):
    """The native refresh action, with no redundant Device framing."""
    poll_section_html = (
        '<section class="page-section">'
        '<h2 class="text-heading">%s</h2>'
        "%s"
        "</section>" % (escape_html(i18n.t(POLL_SECTION_HEADING)), poll_trigger_section(cooldown_remaining))
        if show_poll else "")
    return poll_section_html


# The dirty-save-bar's own two button labels.
SAVE_BUTTON_TEXT = i18n.msg("display.save_settings", "Save settings")
# Same id as companion.settings.calendar.CALENDAR_DISCONNECT_CANCEL_TEXT
# — same English, same French translation, and msg() is idempotent for
# a repeat id/English pair.
CANCEL_BUTTON_TEXT = i18n.msg("display.cancel", "Cancel")


def _settings_page_html(pieces, quick_led_html, poll_html, dirty_strings):
    """The final HTML assembly: the physical `<form>` (hidden scope
    fields, groups_html), every scope's own extra sections in their
    locked order, and the dirty-bar save affordance last, after
    `</form>` and the Poll section, so its `position: fixed` sits
    outside the short settings form.

    A native `type="reset"` Cancel and an empty-until-JS count span
    keep the bar usable with no script; no `hidden` attribute, since it
    is the only save affordance for a scripts-blocked visitor —
    dirty-state.js hides it at init and reveals it on real changes.
    `STATIC_SAVE_FALLBACK_ATTR` must reach the format call below as a
    bare name, for the AST invariant checked elsewhere.
    """
    return (
        pieces["header"]
        # The Frame strip renders after the header and before the
        # form; "" on Device and SCOPE_ALL.
        + pieces["frame_strip_section_html"]
        + '<form class="config-form" id="%s" data-dirty-form method="post" action="%s">'
        "%s"
        "%s"
        "</form>"
        "%s"
        "%s"
        "%s"
        "%s"
        "%s"
        '<div class="dirty-bar" data-dirty-bar role="status" '
        'data-dirty-changed-suffix="%s" data-dirty-and="%s" '
        'data-dirty-list-and="%s" data-dirty-unsaved-singular="%s" '
        'data-dirty-unsaved-plural="%s" data-dirty-saving="%s" '
        'data-dirty-initial-text="%s">'
        "<span data-dirty-count></span>"
        '<button type="submit" class="dirty-bar__save" form="%s" %s>%s</button>'
        '<button type="reset" form="%s" class="dirty-bar__cancel" data-dirty-cancel>%s</button>'
        "</div>"
    ) % (
        SETTINGS_FORM_ID,
        SETTINGS_ROUTE,
        pieces["hidden_html"],
        pieces["groups_html"],
        # "" on the Device/SCOPE_ALL paths (both set it to "" above).
        pieces["aspect_section_html"],
        pieces["display_watches_supersection_html"],
        quick_led_html,
        pieces["display_on_supersection_html"],
        poll_html,
        dirty_strings["changed_suffix"],
        dirty_strings["and_word"],
        dirty_strings["list_and"],
        dirty_strings["unsaved_singular"],
        dirty_strings["unsaved_plural"],
        dirty_strings["saving"],
        dirty_strings["initial_text"],
        SETTINGS_FORM_ID,
        STATIC_SAVE_FALLBACK_ATTR,
        escape_html(i18n.t(SAVE_BUTTON_TEXT)),
        # The Cancel button: form=, then its label.
        SETTINGS_FORM_ID,
        escape_html(i18n.t(CANCEL_BUTTON_TEXT)),
    )


def render(ctx, scope=SCOPE_ALL, errors=None, submitted=None):
    """Render one settings page (SCOPE_ALL/SCOPE_DISPLAY/SCOPE_DEVICE) —
    a short orchestrator over the per-scope/per-group assembly helpers
    above.

    `errors`/`submitted` are passed together only by a rejected save,
    threaded into each group builder so a field can repopulate itself.
    `submitted` is deliberately not defaulted to `{}`: `None` (an
    ordinary load) and an actual dict mean different things to
    `_submitted_checkbox_checked()` — collapsing them would render
    every checkbox unchecked on every ordinary load.
    """
    ctx = page_context.coerce(ctx)
    if errors is None:
        errors = {}
    values = _render_current_values(ctx)
    calendar_status = _render_calendar_and_poll_context(ctx)
    next_wake_clock, next_wake_iso = _next_wake_clock_and_iso(ctx, values["device_cfg"])
    dirty_strings = _dirty_bar_strings()

    screen_id = screens.current_screen_id(ctx)
    screen = screens.screen_type(screen_id)
    if scope not in SCOPES:
        scope = SCOPE_ALL
    groups = scope_groups(scope, screen_id)

    builders = _group_builders(ctx, values, errors, submitted, next_wake_clock)
    # Rendered after </form> closes so it never nests inside the settings
    # form: quick_led_html is the LED switch's own instant-toggle form.
    quick_led_html = (
        quick_led_form_html(values["led_enabled"]) if screens.GROUP_LED in groups else "")

    if scope == SCOPE_DISPLAY:
        pieces = _render_display_scope(
            ctx, screen, screen_id, groups, builders, errors, submitted, values,
            calendar_status, next_wake_iso)
    elif scope == SCOPE_DEVICE:
        pieces = _render_device_scope(screen, screen_id, groups, builders, errors, next_wake_clock)
    else:
        pieces = _render_all_scope(groups, builders)

    poll_html = _poll_html_for_scope(scope, pieces["show_poll"], calendar_status["cooldown_remaining"])
    return _settings_page_html(pieces, quick_led_html, poll_html, dirty_strings)


def _scope_fields_html(scope, return_route):
    return (
        '<input type="hidden" name="%s" value="%s">'
        '<input type="hidden" name="%s" value="%s">'
    ) % (
        SCOPE_FIELD_NAME, escape_html(scope),
        RETURN_TO_FIELD_NAME, escape_html(return_route),
    )


def submitted_calendar_signal(form):
    """The single definition of what a submitted `calendar_url` +
    `calendar_disconnect` pair means. Both `handle_post()` and the
    calendar-connect route call this, so the two can never disagree.

    An absent/empty URL with no checkbox resolves to carry-forward, not
    disconnect: the write-only URL field renders empty on every load
    regardless of state, so treating an ordinary save's empty
    submission as "disconnect" would silently wipe the calendar.

    Never raises, and never itself persists. The in-form checkbox these
    gates interpret no longer renders, but a crafted request can still
    send it, so the gates stay to keep `handle_post()`'s all-or-nothing
    rejection covering that shape.
    """
    # A page that never rendered the Calendar group cannot have meant
    # anything by the field's absence.
    if screens.GROUP_CALENDAR not in scope_groups(submitted_scope(form)):
        return CALENDAR_URL_SIGNAL_CARRY_FORWARD
    raw_url = form.get("calendar_url")
    stripped_url = raw_url.strip() if isinstance(raw_url, str) else ""
    disconnect = form.get("calendar_disconnect")

    if disconnect is not None and disconnect != CALENDAR_DISCONNECT_CHECKBOX_VALUE:
        return CALENDAR_URL_SIGNAL_INVALID
    if disconnect is not None and stripped_url:
        return CALENDAR_URL_SIGNAL_INVALID
    if disconnect is not None:
        return CALENDAR_URL_SIGNAL_CLEAR
    if not stripped_url:
        return CALENDAR_URL_SIGNAL_CARRY_FORWARD
    if len(stripped_url) > CALENDAR_URL_MAX_LEN:
        return CALENDAR_URL_SIGNAL_INVALID
    return CALENDAR_URL_SIGNAL_SET


def handle_post(form, ctx, errors=None):
    """Validate the submitted settings state against `device_config`'s
    own registries and validators, then persist all fields in one
    `save_device_config()` call. Rejection is all-or-nothing: a crafted
    or invalid value in any field aborts before any write.

    Delegates every group's own validation and value resolution to
    `companion.settings.form_post`, calling its resolvers in the exact
    sequence the pre-split version of this function checked the same
    fields in — see that module's own docstring for why some groups
    need two calls rather than one. Each resolver returns either that
    group's own `save_device_config()` keyword argument(s), or
    `form_post.FAILED` once it has already noted the error; this
    function stops at the first `FAILED` and returns the save-failed
    flash key immediately, exactly like the unsplit version's own
    per-field early returns.

    Every checkbox not rendered on the current scope resolves absent
    -> `None` (leave unchanged), never `False` — a scope with no control
    for a field must not silently turn it off.

    The calendar secret write is layered after the device-config write,
    only for the `set`/`clear` signals, since `carry_forward` would
    otherwise erase the fetched calendar registry.
    """
    ctx = page_context.coerce(ctx)
    state_dir = ctx.state_dir
    scope = submitted_scope(form)
    in_scope = set(scope_groups(scope, screens.current_screen_id(ctx)))
    calendar_signal = submitted_calendar_signal(form)
    submitted_calendar_url = form.get("calendar_url")

    # Each step is a zero-arg thunk, not a bare call, and the loop below
    # invokes them ONE AT A TIME, stopping at the first FAILED: a tuple
    # of already-evaluated call results would run every resolver up
    # front regardless of an earlier failure, noting every group's own
    # error at once instead of stopping at the first one, exactly the
    # behaviour change this split must not introduce.
    steps = (
        lambda: form_post.resolve_theme(form, errors),
        lambda: form_post.resolve_calendar_signal(calendar_signal, errors),
        lambda: form_post.resolve_calendar_theme_id(form, errors),
        lambda: form_post.resolve_theme_arriving(form, in_scope, errors),
        lambda: form_post.resolve_runway(form, errors),
        lambda: form_post.resolve_quiet_hours_times(form, errors),
        lambda: form_post.resolve_led(form, errors),
        lambda: form_post.resolve_quiet_hours_enabled(form, errors),
        lambda: form_post.resolve_wake_interval(form, errors),
        lambda: form_post.resolve_display(form, errors),
    )
    save_kwargs = {}
    for step in steps:
        step_result = step()
        if step_result is form_post.FAILED:
            return FLASH_SAVE_FAILED
        save_kwargs.update(step_result)

    try:
        device_config.save_device_config(state_dir, **save_kwargs)
    except (ValueError, OSError):
        return FLASH_SAVE_FAILED

    if calendar_signal == CALENDAR_URL_SIGNAL_CLEAR:
        if not calendar_rules.save_calendar_url(
                state_dir, calendar_rules.CLEAR_CALENDAR_URL):
            return FLASH_SAVE_FAILED
    elif calendar_signal == CALENDAR_URL_SIGNAL_SET:
        if not calendar_rules.save_calendar_url(
                state_dir, submitted_calendar_url.strip()):
            return FLASH_SAVE_FAILED

    return FLASH_SAVED
