"""The Settings page: theme/runway/LED/quiet-hours/wake-interval/
calendar/notifications controls, rendered and validated against
`server.device_config`'s own registries, plus the per-flight
colour-rules editor and the manual "Trigger poll now" control (its
route, cooldown gate and poll trigger are owned by companion/app.py;
this module only renders its button/copy).
"""
import re

from companion import i18n
from companion.layout import escape_html
import companion.layout as layout
from companion import screens
from companion import wake
from server import device_config
from server.plane import calendar_rules

# Every settings-group module's names, re-exported here (explicit,
# aliased imports so ruff's F401 does not flag a name this module
# never calls itself but companion/app.py and the test suite read as
# config_page.X) so this split changes no external attribute path.
from companion.settings.form import (
    CALENDAR_HOW_IT_WORKS_SUMMARY as CALENDAR_HOW_IT_WORKS_SUMMARY,
    CURRENT_BADGE_ATTR as CURRENT_BADGE_ATTR,
    CURRENT_BADGE_LABEL as CURRENT_BADGE_LABEL,
    DIRTY_SECTION_ATTR as DIRTY_SECTION_ATTR,
    NEXT_WAKE_CAPTION_SUFFIX_TEMPLATE as NEXT_WAKE_CAPTION_SUFFIX_TEMPLATE,
    SETTINGS_FORM_ID as SETTINGS_FORM_ID,
    _describedby_attr as _describedby_attr,
    _field_error_attrs as _field_error_attrs,
    _field_error_html as _field_error_html,
    _submitted_checkbox_checked as _submitted_checkbox_checked,
    _submitted_or_current as _submitted_or_current,
    _with_next_wake as _with_next_wake)
from companion.settings.theme import (
    ASPECT_HEADING as ASPECT_HEADING,
    ASPECT_HEADING_ID as ASPECT_HEADING_ID,
    ASPECT_ROWS_GROUP_NAME as ASPECT_ROWS_GROUP_NAME,
    ASPECT_ROW_SUMMARY_TEMPLATE as ASPECT_ROW_SUMMARY_TEMPLATE,
    COLOUR_USAGES as COLOUR_USAGES,
    COLOUR_USAGE_ARRIVALS as COLOUR_USAGE_ARRIVALS,
    COLOUR_USAGE_CALENDAR as COLOUR_USAGE_CALENDAR,
    COLOUR_USAGE_DEPARTURES as COLOUR_USAGE_DEPARTURES,
    COLOUR_USAGE_RULES as COLOUR_USAGE_RULES,
    FRAME_COLOURS_ROW_LABELS as FRAME_COLOURS_ROW_LABELS,
    SAME_AS_DEPARTURES_LABEL as SAME_AS_DEPARTURES_LABEL,
    THEME_CHIP_SWATCH_LEGEND as THEME_CHIP_SWATCH_LEGEND,
    THEME_LIVE_PREVIEW_ALT_TEMPLATE as THEME_LIVE_PREVIEW_ALT_TEMPLATE,
    THEME_LIVE_PREVIEW_CAPTION_SAMPLE as THEME_LIVE_PREVIEW_CAPTION_SAMPLE,
    THEME_LIVE_PREVIEW_CAPTION_WITH_FLIGHT_TEMPLATE as THEME_LIVE_PREVIEW_CAPTION_WITH_FLIGHT_TEMPLATE,
    THEME_LIVE_PREVIEW_HEIGHT as THEME_LIVE_PREVIEW_HEIGHT,
    THEME_LIVE_PREVIEW_WIDTH as THEME_LIVE_PREVIEW_WIDTH,
    THEME_PREVIEW_ALT_TEMPLATE as THEME_PREVIEW_ALT_TEMPLATE,
    THEME_PREVIEW_ROUTE_PREFIX as THEME_PREVIEW_ROUTE_PREFIX,
    _aspect_card_html as _aspect_card_html,
    _palette_chip_html as _palette_chip_html,
    _palette_grid_html as _palette_grid_html,
    _palette_hex as _palette_hex,
    _palette_swatch_html as _palette_swatch_html,
    _same_as_departures_chip_html as _same_as_departures_chip_html,
    _theme_chip_grid_html as _theme_chip_grid_html,
    _theme_live_preview_html as _theme_live_preview_html,
    _usage_row_html as _usage_row_html,
    _usage_row_summary_html as _usage_row_summary_html,
    departures_safe_theme_id as departures_safe_theme_id)
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
    calendar_usage_row_html as calendar_usage_row_html)
from companion.settings.rules import (
    FRAME_COLOURS_RULES_COUNT_PLURAL_TEMPLATE as FRAME_COLOURS_RULES_COUNT_PLURAL_TEMPLATE,
    FRAME_COLOURS_RULES_COUNT_SINGULAR as FRAME_COLOURS_RULES_COUNT_SINGULAR,
    FRAME_COLOURS_RULES_EMPTY_META as FRAME_COLOURS_RULES_EMPTY_META,
    POLL_COOLDOWN_HELPER_TEXT as POLL_COOLDOWN_HELPER_TEXT,
    POLL_COOLDOWN_TEMPLATE_TOKEN as POLL_COOLDOWN_TEMPLATE_TOKEN,
    POLL_COOLDOWN_TEXT_ID as POLL_COOLDOWN_TEXT_ID,
    POLL_SECTION_CAPTION as POLL_SECTION_CAPTION,
    POLL_SUBMIT_PENDING_TEXT as POLL_SUBMIT_PENDING_TEXT,
    POLL_TRIGGER_BUTTON_ID as POLL_TRIGGER_BUTTON_ID,
    RULES_ADD_ROUTE as RULES_ADD_ROUTE,
    RULES_DELETE_ROUTE_PREFIX as RULES_DELETE_ROUTE_PREFIX,
    RULES_DELETE_ROUTE_SUFFIX as RULES_DELETE_ROUTE_SUFFIX,
    RULES_EMPTY_BODY as RULES_EMPTY_BODY,
    RULES_EMPTY_HEADING as RULES_EMPTY_HEADING,
    RULES_HOW_RULES_COMBINE_BODY as RULES_HOW_RULES_COMBINE_BODY,
    RULES_HOW_RULES_COMBINE_SUMMARY as RULES_HOW_RULES_COMBINE_SUMMARY,
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
    _rule_add_form_html as _rule_add_form_html,
    _rule_delete_action as _rule_delete_action,
    _rule_kind_radio_html as _rule_kind_radio_html,
    _rule_list_html as _rule_list_html,
    _rule_row_html as _rule_row_html,
    _rule_suggestion_chips_html as _rule_suggestion_chips_html,
    poll_trigger_section as poll_trigger_section,
    rules_usage_row_html as rules_usage_row_html)
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
from companion.settings.notifications import (
    ERROR_NOTIFICATIONS_URL_TOO_LONG as ERROR_NOTIFICATIONS_URL_TOO_LONG,
    NOTIFICATIONS_BATTERY_CHECKBOX_VALUE as NOTIFICATIONS_BATTERY_CHECKBOX_VALUE,
    NOTIFICATIONS_BATTERY_LABEL as NOTIFICATIONS_BATTERY_LABEL,
    NOTIFICATIONS_REPLACE_URL_SUMMARY as NOTIFICATIONS_REPLACE_URL_SUMMARY,
    NOTIFICATIONS_SECTION_CAPTION as NOTIFICATIONS_SECTION_CAPTION,
    NOTIFICATIONS_SECTION_CAPTION_ID as NOTIFICATIONS_SECTION_CAPTION_ID,
    NOTIFICATIONS_SECTION_HEADING as NOTIFICATIONS_SECTION_HEADING,
    NOTIFICATIONS_SILENT_CHECKBOX_VALUE as NOTIFICATIONS_SILENT_CHECKBOX_VALUE,
    NOTIFICATIONS_SILENT_LABEL as NOTIFICATIONS_SILENT_LABEL,
    NOTIFICATIONS_STATUS_CONFIGURED_VERDICT as NOTIFICATIONS_STATUS_CONFIGURED_VERDICT,
    NOTIFICATIONS_STATUS_NOT_CONFIGURED_VERDICT as NOTIFICATIONS_STATUS_NOT_CONFIGURED_VERDICT,
    NOTIFICATIONS_TEST_BUTTON_TEXT as NOTIFICATIONS_TEST_BUTTON_TEXT,
    NOTIFICATIONS_TEST_ROUTE as NOTIFICATIONS_TEST_ROUTE,
    NOTIFICATIONS_URL_FIELD_LABEL as NOTIFICATIONS_URL_FIELD_LABEL,
    NOTIFICATIONS_URL_HINT as NOTIFICATIONS_URL_HINT,
    NOTIFICATIONS_URL_HINT_ID as NOTIFICATIONS_URL_HINT_ID,
    NOTIFICATIONS_URL_HOW_IT_WORKS_BODY as NOTIFICATIONS_URL_HOW_IT_WORKS_BODY,
    NOTIFICATIONS_URL_MAX_LEN as NOTIFICATIONS_URL_MAX_LEN,
    _notifications_url_field_html as _notifications_url_field_html,
    notifications_group as notifications_group,
    notifications_test_section as notifications_test_section)


# The single definition of this route. companion/app.py rebinds its own
# SETTINGS_ROUTE constant to this value rather than re-typing the
# literal. The old "/config" path is retired: it 404s by design, no
# redirect.
SETTINGS_ROUTE = "/settings"


# The one settings form renders as two pages sharing the same POST
# route and the same handle_post(): the everyday "Display" page (theme,
# quiet hours, screen on/off) and the advanced "Device" page (runway,
# diagnostic LED, wake interval, calendar, colour rules, manual
# refresh). Which groups land on which page is declared per screen type
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

DISPLAY_PAGE_TITLE = "Display"
DISPLAY_PAGE_PURPOSE = "Everything about what the frame shows and when."
DEVICE_PAGE_TITLE = "Device"
DEVICE_PAGE_PURPOSE = "Hardware, data and diagnostics for the frame."
SCREEN_CAPTION_TEMPLATE = "Screen: %s"

# The three headed supersections Display's own groups render under, in
# this locked order. Each heading/intro pair renders through the shared
# section-intro helper in layout.py.
DISPLAY_LOOK_SECTION_ID = "display-look"
DISPLAY_LOOK_HEADING = "Look"
DISPLAY_LOOK_INTRO = (
    "— the theme, flight colours and calendar that decide how the "
    "picture looks.")
DISPLAY_WATCHES_SECTION_ID = "display-watches"
DISPLAY_WATCHES_HEADING = "What it watches"
DISPLAY_WATCHES_INTRO = "— which Orly runway the frame is watching."
DISPLAY_ON_SECTION_ID = "display-on"
DISPLAY_ON_HEADING = "When it is on"
DISPLAY_ON_INTRO = "— when the screen is lit and when it stays quiet."
# Device's own two supersections, the same section_intro_html() shape
# as the three above. The LED/Notifications pairing is a real shared
# subject: both cards are the frame's signalling channels — the LED
# reports on the device itself, notifications report on the reader's
# phone.
DEVICE_WAKES_SECTION_ID = "device-wakes"
DEVICE_WAKES_HEADING = "When it wakes"
DEVICE_WAKES_INTRO = "— how often the frame wakes up to fetch a new picture."
DEVICE_TELLS_SECTION_ID = "device-tells"
DEVICE_TELLS_HEADING = "How it tells you"
DEVICE_TELLS_INTRO = "— the light on the frame and the alerts on your phone."
DEVICE_POLL_SECTION_ID = "device-poll"
DEVICE_POLL_HEADING = "When you can't wait"
DEVICE_POLL_INTRO = "— fetch a new picture right now."
# An element id, not a class, since its own <label> targets it via for=.
SCREEN_SELECTOR_ID = "screen-id-selector"
SCREEN_SELECTOR_LABEL_TEXT = "Screen type"


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
        screens.GROUP_CALENDAR, screens.GROUP_NOTIFICATIONS)


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

# The sole accepted submitted value for each checkbox — shared by the
# group's own markup and handle_post()'s validator so the two can never
# drift apart.
LED_CHECKBOX_VALUE = "on"
QUIET_HOURS_CHECKBOX_VALUE = "on"
DISPLAY_CHECKBOX_VALUE = "on"


POLL_SECTION_HEADING = "Manual refresh"


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
DIRTY_BAR_INITIAL_TEXT = "Unsaved changes"
DIRTY_CHANGED_SUFFIX = " changed"
DIRTY_AND = " and "
DIRTY_LIST_AND = ", and "
DIRTY_UNSAVED_SINGULAR = "1 unsaved change"
DIRTY_UNSAVED_PLURAL = " unsaved changes"
# The ellipsis is the single U+2026 character, matching this module's
# "Polling…" and layout.py's "Reconnecting…" — never three periods.
DIRTY_SAVING_TEXT = "Saving…"


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
# cooldown and both call `poll_loop.run_once()`.
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


# The Aspect card's copy floor exempts these two: DISPLAY_LOOK_INTRO
# (a different card's own intro) and CALENDAR_URL_HINT (its wording is
# never to be shortened). Kept here, beside the strings they exempt,
# rather than in a second harness-side list that could drift from this
# one.
ASPECT_CAPTION_EXEMPTIONS = (
    DISPLAY_LOOK_INTRO,
    CALENDAR_URL_HINT,
)
# submitted_calendar_signal()'s gates still compare a submitted
# calendar_disconnect field against this value, kept deliberately
# reachable for a hostile client crafting that field into a /settings
# POST. The dedicated CALENDAR_DISCONNECT_ROUTE never reads this value
# at all — it always means "disconnect", once its own confirm gate
# passes.
CALENDAR_DISCONNECT_CHECKBOX_VALUE = "on"


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

# The two outcomes POST /settings/notifications/test can produce.
FLASH_NOTIFICATIONS_TEST_OK = "notifications_test_ok"
FLASH_NOTIFICATIONS_TEST_FAILED = "notifications_test_failed"


def _nested_wrapper_html(html_fragment, base_class, nested_class):
    """Appends a `--nested` modifier class to a group builder's own
    outer wrapper, so a card rendered under a supersection heading
    renders one heading rung below it instead of Device's un-nested tier.

    `nested_class` is a literal string at every call site, never
    derived from `base_class`, so it stays grep-visible. Each builder
    emits its wrapper class exactly once as `class="{base_class}"`, so a
    single count-limited `str.replace()` is the whole mechanism.
    """
    needle = 'class="%s"' % base_class
    replacement = 'class="%s %s"' % (base_class, nested_class)
    return html_fragment.replace(needle, replacement, 1)


def _display_groups_html(builders, groups):
    """Display scope's two headed supersections: "What it watches"
    (Runway) and "When it is on" (Quiet hours) — each card gets the
    `--nested` modifier (`_nested_wrapper_html()`). Returns
    `(watches_html, on_html)`.

    Both cards render as siblings of the settings `<form>`, not inside
    it: their own inputs cross-submit via `form="{SETTINGS_FORM_ID}"`,
    since their instant-switch controls would otherwise need to nest a
    `<form>` inside another `<form>`, which HTML forbids.
    """
    runway_html = (
        _nested_wrapper_html(builders[screens.GROUP_RUNWAY](), "theme-status", "theme-status--nested")
        if screens.GROUP_RUNWAY in groups else "")
    watches_supersection_html = (
        layout.section_intro_html(
            DISPLAY_WATCHES_SECTION_ID, i18n.t(DISPLAY_WATCHES_HEADING),
            i18n.t(DISPLAY_WATCHES_INTRO))
        + runway_html
    )
    quiet_hours_html = (
        _nested_wrapper_html(
            builders[screens.GROUP_QUIET_HOURS](), "theme-status", "theme-status--nested")
        if screens.GROUP_QUIET_HOURS in groups else "")
    on_supersection_html = (
        layout.section_intro_html(
            DISPLAY_ON_SECTION_ID, i18n.t(DISPLAY_ON_HEADING), i18n.t(DISPLAY_ON_INTRO))
        + quiet_hours_html
    )
    return watches_supersection_html, on_supersection_html


def _device_groups_html(builders, groups):
    """Device scope's two headed supersections: "When it wakes" (Wake
    interval alone) and "How it tells you" (Diagnostic LED and
    Notifications together).

    Unlike `_display_groups_html()`, a supersection's heading is
    omitted entirely when every card under it is absent — an intro
    sentence introducing nothing is worse than no heading at all.
    """
    wake_interval_html = (
        _nested_wrapper_html(
            builders[screens.GROUP_WAKE_INTERVAL](), "theme-status", "theme-status--nested")
        if screens.GROUP_WAKE_INTERVAL in groups and screens.GROUP_WAKE_INTERVAL in builders
        else "")
    wakes_supersection_html = (
        (layout.section_intro_html(
            DEVICE_WAKES_SECTION_ID, i18n.t(DEVICE_WAKES_HEADING), i18n.t(DEVICE_WAKES_INTRO))
         + wake_interval_html)
        if wake_interval_html else "")

    led_html = (
        _nested_wrapper_html(
            builders[screens.GROUP_LED](), "theme-status", "theme-status--nested")
        if screens.GROUP_LED in groups and screens.GROUP_LED in builders else "")
    notifications_html = (
        _nested_wrapper_html(
            builders[screens.GROUP_NOTIFICATIONS](), "theme-status", "theme-status--nested")
        if screens.GROUP_NOTIFICATIONS in groups and screens.GROUP_NOTIFICATIONS in builders
        else "")
    tells_cards_html = led_html + notifications_html
    tells_supersection_html = (
        (layout.section_intro_html(
            DEVICE_TELLS_SECTION_ID, i18n.t(DEVICE_TELLS_HEADING), i18n.t(DEVICE_TELLS_INTRO))
         + tells_cards_html)
        if tells_cards_html else "")

    return wakes_supersection_html + tells_supersection_html


def render(ctx, scope=SCOPE_ALL, errors=None, submitted=None):
    """Render one settings page (SCOPE_ALL/SCOPE_DISPLAY/SCOPE_DEVICE).

    `errors`/`submitted` are passed together only by a rejected save,
    threaded into each group builder so a field can repopulate itself.
    `submitted` is deliberately not defaulted to `{}`: `None` (an
    ordinary load) and an actual dict mean different things to
    `_submitted_checkbox_checked()` — collapsing them would render
    every checkbox unchecked on every ordinary load.
    """
    if errors is None:
        errors = {}
    device_cfg = ctx.get("device_config") or {}
    current_theme_id = device_cfg.get("theme", device_config.DEFAULT_THEME_ID)
    # Explicit `.get()`, no `or` fallback: `None` is a meaningful value
    # (no arrivals-theme override), not an oversight.
    current_theme_arriving = device_cfg.get("theme_arriving")
    current_runway_id = device_cfg.get(
        "tracked_runway", device_config.DEFAULT_RUNWAY_ID)
    current_led_enabled = device_cfg.get(
        "led_enabled", device_config.DEFAULT_LED_ENABLED)
    current_quiet_start = device_cfg.get(
        "quiet_hours_start", device_config.DEFAULT_QUIET_HOURS_START)
    current_quiet_end = device_cfg.get(
        "quiet_hours_end", device_config.DEFAULT_QUIET_HOURS_END)
    # `is None`, not `or`: 0 is never a valid wake_interval_s. Falls back
    # to the deployed SKYPANE_SLEEP_S env default when device_config has
    # no value yet (e.g. a fresh install with no systemd unit).
    current_wake_interval_s = device_cfg.get("wake_interval_s")
    if current_wake_interval_s is None:
        current_wake_interval_s = ctx.get("wake_interval_env_default")
    # Explicit `.get()`, no `or` fallback: `None` means no calendar
    # theme chosen yet, defaulting to the base theme.
    current_calendar_theme_id = device_cfg.get("calendar_theme_id")
    calendar_configured = ctx.get("calendar_configured")
    calendar_last_synced_at = ctx.get("calendar_last_synced_at")
    # last_attempt_at distinguishes "just connected, no sync yet" from
    # "has been failing"; entry_count feeds the status detail template.
    calendar_last_attempt_at = ctx.get("calendar_last_attempt_at")
    calendar_entry_count = ctx.get("calendar_entry_count") or 0
    calendar_drift = ctx.get("calendar_drift")
    # A device_config.json predating this field resolves through
    # device_config.DEFAULT_NOTIFICATIONS, never a KeyError.
    current_notifications = device_cfg.get("notifications") or device_config.DEFAULT_NOTIFICATIONS
    notifications_configured = bool(current_notifications.get("topic_url"))
    current_notifications_battery = current_notifications.get(
        "battery_low", device_config.DEFAULT_NOTIFICATIONS["battery_low"])
    current_notifications_silent = current_notifications.get(
        "frame_silent", device_config.DEFAULT_NOTIFICATIONS["frame_silent"])
    cooldown_remaining = ctx.get("poll_cooldown_remaining", 0)
    # next_wake_clock is the shared next-wake clock string threaded into
    # every group's caption and the Device header slot; None when
    # unknown (no check-in yet, or no known interval), and every
    # consumer omits the suffix/line in that case rather than show a
    # placeholder.
    next_wake_clock = None
    next_wake_iso, _, _ = wake.next_wake_status(
        ctx.get("last_checkin_ts"), device_cfg)
    if next_wake_iso:
        next_wake_parsed = layout.parse_iso(next_wake_iso)
        if next_wake_parsed is not None:
            next_wake_clock = layout.local_clock_text(
                next_wake_parsed, now_parsed=layout.parse_iso(ctx.get("now")))

    # data-dirty-form marks the form dirty-state.js watches to drive the
    # save bar below. The native Save button (STATIC_SAVE_FALLBACK_ATTR)
    # is the one save affordance on the page — an AST check pins it
    # reaching this function's own return as a bare name, so it can
    # never accidentally duplicate or vanish.
    #
    # No `hidden` attribute: this bar is the only save affordance for a
    # scripts-blocked visitor, so it must render visible by default.
    # dirty-state.js hides it at init and reveals it on real changes.
    # Cancel is a native `type="reset"` (works without script);
    # `[data-dirty-count]` starts empty to avoid a false "Unsaved
    # changes" announcement on every fresh, unscripted page load.
    dirty_changed_suffix_html = escape_html(i18n.t(DIRTY_CHANGED_SUFFIX))
    dirty_and_html = escape_html(i18n.t(DIRTY_AND))
    dirty_list_and_html = escape_html(i18n.t(DIRTY_LIST_AND))
    dirty_unsaved_singular_html = escape_html(i18n.t(DIRTY_UNSAVED_SINGULAR))
    dirty_unsaved_plural_html = escape_html(i18n.t(DIRTY_UNSAVED_PLURAL))
    dirty_saving_html = escape_html(i18n.t(DIRTY_SAVING_TEXT))
    dirty_initial_text_html = escape_html(i18n.t(DIRTY_BAR_INITIAL_TEXT))

    screen_id = screens.current_screen_id(ctx)
    screen = screens.screen_type(screen_id)
    if scope not in SCOPES:
        scope = SCOPE_ALL
    groups = scope_groups(scope, screen_id)

    # screens.GROUP_THEME/GROUP_CALENDAR have no entry here: their own
    # renderer (the Aspect card, built by render()'s Display branch)
    # contains real <form> elements that must never render as a literal
    # descendant of <form id="{SETTINGS_FORM_ID}">.
    builders = {
        screens.GROUP_RUNWAY: lambda: runway_fieldset(
            current_runway_id, ctx.get("runway_images") or (),
            errors=errors, submitted=submitted, next_wake_clock=next_wake_clock),
        screens.GROUP_LED: lambda: led_group(
            current_led_enabled, errors=errors, submitted=submitted,
            next_wake_clock=next_wake_clock),
        screens.GROUP_QUIET_HOURS: lambda: quiet_hours_group(
            current_quiet_start, current_quiet_end,
            errors=errors, submitted=submitted),
        # Read inside the lambda so it costs nothing unless this group
        # is actually in scope.
        screens.GROUP_WAKE_INTERVAL: lambda: wake_interval_group(
            current_wake_interval_s, errors=errors, submitted=submitted,
            next_wake_clock=next_wake_clock,
            battery_rows=wake_battery_rows(ctx.get("state_dir"), ctx.get("now"))),
        screens.GROUP_NOTIFICATIONS: lambda: notifications_group(
            notifications_configured, current_notifications_battery,
            current_notifications_silent, errors=errors, submitted=submitted),
    }
    # Its own immediate-POST form; must render after </form> closes so
    # it never nests inside the settings form.
    notifications_test_html = (
        notifications_test_section() if screens.GROUP_NOTIFICATIONS in groups else "")
    # The LED switch's own instant-toggle form, for the same reason.
    quick_led_html = (
        quick_led_form_html(current_led_enabled) if screens.GROUP_LED in groups else "")
    if scope == SCOPE_DISPLAY:
        # The strip and this freshness line are the only elements this
        # page declares swappable (layout.REFRESH_SWAP_SELECTORS_BY_PAGE);
        # everything else here is a <form>, and a swap mid-edit would
        # corrupt it. The refresh loop also stands down while the save
        # bar reports unsaved edits.
        header = layout.page_header(
            i18n.t(DISPLAY_PAGE_TITLE), purpose=i18n.t(DISPLAY_PAGE_PURPOSE),
            freshness_html=layout.freshness_line_html(ctx.get("now")),
            action_html=_screen_caption_html(screen) + _screen_selector_html(screen_id, errors=errors))
        frame_strip_section_html = layout.frame_strip_html(
            ctx, return_to=layout.DISPLAY_ROUTE, next_wake_iso=next_wake_iso)
        hidden_html = _scope_fields_html(scope, layout.DISPLAY_ROUTE)
        show_poll = False
        # groups_html stays empty on Display: every saved control here
        # cross-submits from outside the form via
        # form="{SETTINGS_FORM_ID}".
        # submits from outside the form via `form="{SETTINGS_FORM_ID}"`,
        # exactly like Runway/Calendar already do (Structural Note 2's
        # own "the physical form becomes a pure submission target").
        #
        # Gated on GROUP_THEME alone: safe only because
        # companion/screens.py's one registered screen type lists
        # GROUP_THEME and GROUP_CALENDAR together (always both true or
        # both false today). A future screen type with only one of the
        # two must split this gate.
        if screens.GROUP_THEME in groups:
            # departures_safe_theme_id() is resolved once here (Calendar's
            # own usage row needs it for its "same as departures" swatch
            # fallback, the same resolution _aspect_card_html() applies to
            # its own departures/arrivals rows) and threaded through,
            # rather than each of the three usage-row builders
            # recomputing it with slightly different rounding.
            departures_safe_id = departures_safe_theme_id(current_theme_id, submitted)
            calendar_row_html, calendar_disconnect_form_html = calendar_usage_row_html(
                departures_safe_id, current_calendar_theme_id, calendar_configured,
                calendar_drift, calendar_last_synced_at, calendar_last_attempt_at,
                ctx.get("now"), calendar_entry_count,
                errors=errors, submitted=submitted, state_dir=ctx.get("state_dir"))
            rules_row_html = rules_usage_row_html(ctx)
            aspect_section_html = (
                layout.section_intro_html(
                    DISPLAY_LOOK_SECTION_ID, i18n.t(DISPLAY_LOOK_HEADING),
                    i18n.t(DISPLAY_LOOK_INTRO))
                + _nested_wrapper_html(
                    _aspect_card_html(
                        current_theme_id, current_theme_arriving,
                        calendar_row_html, calendar_disconnect_form_html, rules_row_html,
                        errors=errors, submitted=submitted, state_dir=ctx.get("state_dir")),
                    "page-section aspect-card", "page-section--nested"))
        else:
            aspect_section_html = ""
        groups_html = ""
        (display_watches_supersection_html,
            display_on_supersection_html) = _display_groups_html(builders, groups)
    elif scope == SCOPE_DEVICE:
        header = layout.page_header(
            i18n.t(DEVICE_PAGE_TITLE), purpose=i18n.t(DEVICE_PAGE_PURPOSE),
            action_html=(
                _screen_caption_html(screen) + _screen_selector_html(screen_id, errors=errors)
                + _next_wake_caption_html(next_wake_clock)))
        hidden_html = _scope_fields_html(scope, layout.DEVICE_ROUTE)
        # The Frame strip renders only on Home and Display, never Device.
        frame_strip_section_html = ""
        show_poll = bool(screen.get("has_manual_poll"))
        groups_html = _device_groups_html(builders, groups)
        aspect_section_html = ""
        display_watches_supersection_html = ""
        display_on_supersection_html = ""
    else:
        header = layout.page_header(i18n.t("Settings"))
        hidden_html = ""
        frame_strip_section_html = ""
        show_poll = True
        # SCOPE_ALL is the legacy, never-served whole-page render, kept
        # byte-identical to its pre-existing output for harness checks
        # against the full form; no live app.py route uses it.
        groups_html = "".join(builders[g]() for g in groups if g in builders)
        aspect_section_html = ""
        display_watches_supersection_html = ""
        display_on_supersection_html = ""

    poll_section_html = (
        '<section class="page-section">'
        '<h2 class="text-heading">%s</h2>'
        "%s"
        "</section>" % (escape_html(i18n.t(POLL_SECTION_HEADING)), poll_trigger_section(cooldown_remaining))
        if show_poll else "")
    # Device-scope-only: wraps the Poll card under its own supersection,
    # "When you can't wait". "" on Display/SCOPE_ALL, which never set
    # show_poll for this branch.
    poll_supersection_html = (
        (layout.section_intro_html(
            DEVICE_POLL_SECTION_ID, i18n.t(DEVICE_POLL_HEADING), i18n.t(DEVICE_POLL_INTRO))
         + _nested_wrapper_html(poll_section_html, "page-section", "page-section--nested"))
        if scope == SCOPE_DEVICE and poll_section_html else "")

    return (
        header
        # The Frame strip renders after the header and before the
        # form; "" on Device and SCOPE_ALL.
        + frame_strip_section_html
        + '<form class="config-form" id="%s" data-dirty-form method="post" action="%s">'
        "%s"
        "%s"
        "</form>"
        "%s"
        "%s"
        "%s"
        "%s"
        "%s"
        "%s"
        # The dirty bar is last, after </form> and the Poll section, so
        # its position: fixed sits outside the short settings form.
        # A native type="reset" Cancel and an empty-until-JS count span
        # keep this bar usable with no script (see local-variable
        # comment above).
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
        hidden_html,
        groups_html,
        # "" on the Device/SCOPE_ALL paths (both set it to "" above).
        aspect_section_html,
        display_watches_supersection_html,
        notifications_test_html,
        quick_led_html,
        display_on_supersection_html,
        poll_supersection_html if scope == SCOPE_DEVICE else poll_section_html,
        dirty_changed_suffix_html,
        dirty_and_html,
        dirty_list_and_html,
        dirty_unsaved_singular_html,
        dirty_unsaved_plural_html,
        dirty_saving_html,
        dirty_initial_text_html,
        # STATIC_SAVE_FALLBACK_ATTR must reach here as a bare name for
        # the AST invariant checked elsewhere.
        SETTINGS_FORM_ID,
        STATIC_SAVE_FALLBACK_ATTR,
        escape_html(i18n.t("Save settings")),
        # The Cancel button: form=, then its label.
        SETTINGS_FORM_ID,
        escape_html(i18n.t("Cancel")),
    )


def _screen_caption_html(screen):
    """The small "Screen: Plane frame" line under a scoped page's title —
    the visible end of the companion/screens.py seam. Rendered as an
    already-safe block for page_header()'s `action_html` slot.
    """
    # screen["label"] is translated at this display site (i18n.t());
    # the screen id itself never changes.
    return (
        '<p class="page-header__screen text-label">%s</p>'
        % escape_html(i18n.t(SCREEN_CAPTION_TEMPLATE) % i18n.t(screen["label"])))


NEXT_WAKE_HEADER_LABEL = "Next wake"
NEXT_WAKE_HEADER_VALUE_TEMPLATE = "≈ %s"


def _next_wake_caption_html(next_wake_clock):
    """The Device page header's "Next wake ≈ HH:MM" line (Home's own
    copy lives in `home_page.py`). Returns "" when `next_wake_clock` is
    falsy — no placeholder, no "unknown".
    """
    if not next_wake_clock:
        return ""
    return (
        '<p class="page-header__screen text-label">%s</p>'
        % escape_html(
            "%s %s" % (
                i18n.t(NEXT_WAKE_HEADER_LABEL),
                i18n.t(NEXT_WAKE_HEADER_VALUE_TEMPLATE) % next_wake_clock)))


def _screen_selector_html(current_screen_id, errors=None):
    """A `<select name="screen_id">` for switching which registered
    screen type this settings page edits. Returns "" when only one
    screen type is registered, since a one-option choice has no real
    decision value.

    Rendered inside `page_header()`'s action slot, visually before
    `<form id="{SETTINGS_FORM_ID}">` opens, but must still submit with
    it — the `form="{SETTINGS_FORM_ID}"` attribute makes that possible.

    `errors` renders a rejected `screen_id` message; no `submitted`
    repopulation is needed, since `current_screen_id` already reflects
    any rejected submission.
    """
    if len(screens.SCREEN_IDS) <= 1:
        return ""
    options = []
    for screen_id in screens.SCREEN_IDS:
        selected = " selected" if screen_id == current_screen_id else ""
        label = screens.screen_type(screen_id)["label"]
        options.append(
            '<option value="%s"%s>%s</option>'
            % (escape_html(screen_id), selected, escape_html(label)))
    error_html = _field_error_html(errors, "screen_id", SCREEN_SELECTOR_ID)
    return (
        '<label class="visually-hidden" for="%s">%s</label>'
        '<select name="screen_id" id="%s" form="%s">%s</select>'
        "%s"
    ) % (
        SCREEN_SELECTOR_ID, escape_html(i18n.t(SCREEN_SELECTOR_LABEL_TEXT)),
        SCREEN_SELECTOR_ID, SETTINGS_FORM_ID, "".join(options),
        error_html,
    )


def _scope_fields_html(scope, return_route):
    return (
        '<input type="hidden" name="%s" value="%s">'
        '<input type="hidden" name="%s" value="%s">'
    ) % (
        SCOPE_FIELD_NAME, escape_html(scope),
        RETURN_TO_FIELD_NAME, escape_html(return_route),
    )


# The four outcomes of resolving the submitted calendar fields. Plain
# strings, never rendered and never travel in a URL. Four distinct
# sentinels (not e.g. two bools) so a caller cannot mistake one outcome
# for another by falsy-comparing the wrong pair.
CALENDAR_URL_SIGNAL_CARRY_FORWARD = "carry_forward"
CALENDAR_URL_SIGNAL_SET = "set"
CALENDAR_URL_SIGNAL_CLEAR = "clear"
CALENDAR_URL_SIGNAL_INVALID = "invalid"

# handle_post()'s per-field error messages, one constant per rejected
# field, so the copy exists in exactly one place. Sentence case, no
# stack-trace vocabulary, matching this file's label voice.
ERROR_INVALID_CHOICE = "That is not one of the available choices."
ERROR_UNEXPECTED_SWITCH_VALUE = "That switch sent an unexpected value."
ERROR_WAKE_INTERVAL_RANGE = "Enter a whole number of seconds between 60 and 3600."
ERROR_QUIET_HOURS_TIME_SHAPE = "Enter a time as HH:MM, for example 23:00."
# Covers both the over-length and the contradictory (calendar_url +
# calendar_disconnect together) cases; deliberately never echoes any
# part of the submitted URL back.
ERROR_CALENDAR_URL_INVALID = (
    "That link is too long, or conflicts with the disconnect option below.")

# A local copy of device_config's private HH:MM pattern — not imported,
# since it is private to that module. UX pre-check only:
# save_device_config()'s own identical gate is authoritative; a test
# pins the two patterns against the same input table so they cannot
# silently drift apart.
_QUIET_HOURS_TIME_RE = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)\Z")


def _note_error(errors, field, message):
    """No-ops when `errors is None`. Otherwise sets `errors[field]`
    only if that field has no message yet, so a later, more generic
    gate can never overwrite an earlier, more specific one.
    """
    if errors is None:
        return
    if field not in errors:
        errors[field] = message


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

    Every checkbox not rendered on the current scope resolves absent
    -> `None` (leave unchanged), never `False` — a scope with no control
    for a field must not silently turn it off. The two Notifications
    checkboxes are the exception, since their card is always in scope
    when rendered.

    `wake_interval_s` needs a string-to-int conversion that the two
    quiet-hours time fields skip, since those stay strings in
    `device_config`. `errors`, if given, is filled via `_note_error()`.
    The calendar secret write is layered after the device-config write,
    only for the `set`/`clear` signals, since `carry_forward` would
    otherwise erase the fetched calendar registry.
    """
    state_dir = ctx["state_dir"]
    scope = submitted_scope(form)
    in_scope = set(scope_groups(scope, screens.current_screen_id(ctx)))
    submitted_theme = form.get("theme")
    submitted_theme_arriving = form.get("theme_arriving")
    submitted_runway = form.get("tracked_runway")
    submitted_led = form.get("led_enabled")
    submitted_qh_enabled = form.get("quiet_hours_enabled")
    submitted_qh_start = form.get("quiet_hours_start")
    submitted_qh_end = form.get("quiet_hours_end")
    submitted_wake_interval = form.get("wake_interval_s")
    submitted_display = form.get("display_enabled")
    submitted_calendar_theme_id = form.get("calendar_theme_id")
    submitted_calendar_url = form.get("calendar_url")
    submitted_screen_id = form.get("screen_id")
    submitted_notifications_topic_url = form.get("notifications_topic_url")
    submitted_notifications_battery = form.get("notifications_battery")
    submitted_notifications_silent = form.get("notifications_silent")
    calendar_signal = submitted_calendar_signal(form)

    if submitted_theme is not None and submitted_theme not in device_config.THEME_IDS:
        _note_error(errors, "theme", ERROR_INVALID_CHOICE)
        return FLASH_SAVE_FAILED
    if submitted_screen_id is not None and submitted_screen_id not in screens.SCREEN_IDS:
        _note_error(errors, "screen_id", ERROR_INVALID_CHOICE)
        return FLASH_SAVE_FAILED
    if calendar_signal == CALENDAR_URL_SIGNAL_INVALID:
        _note_error(errors, "calendar_url", ERROR_CALENDAR_URL_INVALID)
        return FLASH_SAVE_FAILED
    # A shape bound against an absurd paste, checked only when the field
    # is actually in scope.
    if (
        screens.GROUP_NOTIFICATIONS in in_scope
        and submitted_notifications_topic_url
        and len(submitted_notifications_topic_url.strip()) > NOTIFICATIONS_URL_MAX_LEN
    ):
        _note_error(errors, "notifications_topic_url", ERROR_NOTIFICATIONS_URL_TOO_LONG)
        return FLASH_SAVE_FAILED
    # Both gates below exempt "" in addition to a real theme id: the
    # "Same as departures" chip submits "" for this field, and rejecting
    # it would reject the whole save whenever a user picks that option.
    if (
        submitted_calendar_theme_id is not None
        and submitted_calendar_theme_id not in ("",) + device_config.THEME_IDS
    ):
        _note_error(errors, "calendar_theme_id", ERROR_INVALID_CHOICE)
        return FLASH_SAVE_FAILED
    if (
        submitted_theme_arriving is not None
        and submitted_theme_arriving not in ("",) + device_config.THEME_IDS
    ):
        _note_error(errors, "theme_arriving", ERROR_INVALID_CHOICE)
        return FLASH_SAVE_FAILED
    if submitted_runway is not None and submitted_runway not in device_config.RUNWAY_IDS:
        _note_error(errors, "tracked_runway", ERROR_INVALID_CHOICE)
        return FLASH_SAVE_FAILED
    # A malformed value here is a real user error, reported at this
    # field; absent still means unchanged (including structural absence
    # on a scope that never rendered this group).
    if submitted_qh_start is not None and not _QUIET_HOURS_TIME_RE.match(submitted_qh_start):
        _note_error(errors, "quiet_hours_start", ERROR_QUIET_HOURS_TIME_SHAPE)
        return FLASH_SAVE_FAILED
    if submitted_qh_end is not None and not _QUIET_HOURS_TIME_RE.match(submitted_qh_end):
        _note_error(errors, "quiet_hours_end", ERROR_QUIET_HOURS_TIME_SHAPE)
        return FLASH_SAVE_FAILED
    # theme_arriving: out of scope or genuinely absent -> unchanged; ""
    # -> CLEAR_THEME_ARRIVING; anything else has already passed the
    # membership gate above, so it is a real theme id.
    if screens.GROUP_THEME not in in_scope:
        theme_arriving = None
    elif submitted_theme_arriving is None:
        theme_arriving = None
    elif submitted_theme_arriving == "":
        theme_arriving = device_config.CLEAR_THEME_ARRIVING
    else:
        theme_arriving = submitted_theme_arriving
    if submitted_led is None:
        led_enabled = None
    elif submitted_led == LED_CHECKBOX_VALUE:
        led_enabled = True
    else:
        _note_error(errors, "led_enabled", ERROR_UNEXPECTED_SWITCH_VALUE)
        return FLASH_SAVE_FAILED
    if submitted_qh_enabled is None:
        quiet_hours_enabled = None
    elif submitted_qh_enabled == QUIET_HOURS_CHECKBOX_VALUE:
        quiet_hours_enabled = True
    else:
        _note_error(errors, "quiet_hours_enabled", ERROR_UNEXPECTED_SWITCH_VALUE)
        return FLASH_SAVE_FAILED
    if submitted_wake_interval is None or submitted_wake_interval == "":
        wake_interval_s = None
    else:
        try:
            wake_interval_s = int(submitted_wake_interval)
        except ValueError:
            _note_error(errors, "wake_interval_s", ERROR_WAKE_INTERVAL_RANGE)
            return FLASH_SAVE_FAILED
        # A syntactically valid but out-of-range value would otherwise
        # only surface via save_device_config()'s own generic
        # ValueError; checked here to report it at this field.
        if not (
            device_config.WAKE_INTERVAL_MIN_S
            <= wake_interval_s
            <= device_config.WAKE_INTERVAL_MAX_S
        ):
            _note_error(errors, "wake_interval_s", ERROR_WAKE_INTERVAL_RANGE)
            return FLASH_SAVE_FAILED
    if submitted_display is None:
        display_enabled = None
    elif submitted_display == DISPLAY_CHECKBOX_VALUE:
        display_enabled = True
    else:
        _note_error(errors, "display_enabled", ERROR_UNEXPECTED_SWITCH_VALUE)
        return FLASH_SAVE_FAILED
    # Unlike the fields above, these two checkboxes DO resolve absent ->
    # False: their card is always in scope when rendered (see docstring).
    if screens.GROUP_NOTIFICATIONS not in in_scope:
        notifications = None
    else:
        if submitted_notifications_battery is None:
            notifications_battery = False
        elif submitted_notifications_battery == NOTIFICATIONS_BATTERY_CHECKBOX_VALUE:
            notifications_battery = True
        else:
            _note_error(errors, "notifications_battery", ERROR_UNEXPECTED_SWITCH_VALUE)
            return FLASH_SAVE_FAILED
        if submitted_notifications_silent is None:
            notifications_silent = False
        elif submitted_notifications_silent == NOTIFICATIONS_SILENT_CHECKBOX_VALUE:
            notifications_silent = True
        else:
            _note_error(errors, "notifications_silent", ERROR_UNEXPECTED_SWITCH_VALUE)
            return FLASH_SAVE_FAILED
        # An empty submission means leave the stored URL unchanged,
        # never clear it — there is no UI affordance to clear a
        # configured topic URL. Read fresh from disk rather than from
        # ctx, so this is correct even with a stale ctx.
        current_notifications_on_disk = device_config.load_device_config(
            state_dir)["notifications"]
        stripped_notifications_url = (submitted_notifications_topic_url or "").strip()
        notifications_topic_url = (
            stripped_notifications_url if stripped_notifications_url
            else current_notifications_on_disk.get("topic_url"))
        notifications = {
            "topic_url": notifications_topic_url,
            "battery_low": notifications_battery,
            "frame_silent": notifications_silent,
            # Written from the session's resolved language at save
            # time; there is no language-picking control for this
            # group (the poll loop has no browser to ask).
            "lang": ctx.get("lang") or device_config.DEFAULT_NOTIFICATIONS["lang"],
        }

    try:
        device_config.save_device_config(
            state_dir, theme=submitted_theme, theme_arriving=theme_arriving,
            tracked_runway=submitted_runway,
            led_enabled=led_enabled, quiet_hours_enabled=quiet_hours_enabled,
            quiet_hours_start=submitted_qh_start, quiet_hours_end=submitted_qh_end,
            wake_interval_s=wake_interval_s, display_enabled=display_enabled,
            calendar_theme_id=submitted_calendar_theme_id,
            screen_id=submitted_screen_id, notifications=notifications)
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
