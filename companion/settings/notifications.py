"""The Notifications settings group (Device scope only): the
write-only push-topic URL field, the battery-low/frame-silent
checkboxes, and the "Send a test" immediate-POST form.
"""
from companion import i18n
from companion.layout import escape_html
import companion.layout as layout

from companion.settings.form import (
    CALENDAR_HOW_IT_WORKS_SUMMARY, DIRTY_SECTION_ATTR, _field_error_attrs,
    _field_error_html, _submitted_checkbox_checked)


NOTIFICATIONS_SECTION_HEADING = i18n.msg("notifications.notifications", "Notifications")
NOTIFICATIONS_SECTION_CAPTION = i18n.msg(
    "notifications.get_a_push_alert_about_battery_or_connection",
    "Get a push alert about battery or connection issues.")
NOTIFICATIONS_SECTION_CAPTION_ID = "notifications-caption"
# Write-only, like the calendar feed URL — never rendered back, not
# partially masked. The status row reports only whether a URL is stored.
NOTIFICATIONS_STATUS_CONFIGURED_VERDICT = i18n.msg("notifications.configured", "Configured")
NOTIFICATIONS_STATUS_NOT_CONFIGURED_VERDICT = i18n.msg(
    "notifications.not_configured", "Not configured")
NOTIFICATIONS_URL_FIELD_LABEL = i18n.msg("notifications.push_topic_url", "Push topic URL")
NOTIFICATIONS_URL_HINT = i18n.msg(
    "notifications.paste_your_ntfy_sh_topic_url_or_a_self_hosted",
    "Paste your ntfy.sh topic URL (or a self-hosted one).")
NOTIFICATIONS_URL_HINT_ID = "notifications-url-hint"
NOTIFICATIONS_URL_HOW_IT_WORKS_BODY = i18n.msg(
    "notifications.stored_on_the_server_and_never_shown_back_here",
    "Stored on the server and never shown back here — pasting a new "
    "one replaces the old.")
NOTIFICATIONS_REPLACE_URL_SUMMARY = i18n.msg(
    "notifications.replace_the_url", "Replace the URL")
# A shape bound against an absurd paste; the arbiter of an acceptable
# topic URL stays server/notify.py's send-time gate, not this bound.
NOTIFICATIONS_URL_MAX_LEN = 2048
NOTIFICATIONS_BATTERY_LABEL = i18n.msg("notifications.battery_low", "Battery low")
NOTIFICATIONS_SILENT_LABEL = i18n.msg("notifications.frame_silent", "Frame silent")
NOTIFICATIONS_TEST_BUTTON_TEXT = i18n.msg("notifications.send_a_test", "Send a test")
NOTIFICATIONS_BATTERY_CHECKBOX_VALUE = "on"
NOTIFICATIONS_SILENT_CHECKBOX_VALUE = "on"
NOTIFICATIONS_TEST_ROUTE = "/settings/notifications/test"
# Owned by companion/i18n_fr/display.py, not this module's own
# notifications.py — the calendar URL field's own longer error
# (companion.settings.form_post.ERROR_CALENDAR_URL_INVALID) shares that
# catalogue, and this is its shorter Notifications-URL sibling.
ERROR_NOTIFICATIONS_URL_TOO_LONG = i18n.msg("display.that_link_is_too_long", "That link is too long.")


def _notifications_url_field_html(errors=None):
    """The write-only push-topic URL field, wrapped in a "Replace the
    URL" disclosure once a URL is already stored — split out of
    `notifications_group()` to keep that function under this project's
    function-length ceiling.
    """
    url_error_attrs = _field_error_attrs(
        errors, "notifications_topic_url", "notifications-topic-url",
        hint_id=NOTIFICATIONS_URL_HINT_ID)
    url_error_html = _field_error_html(
        errors, "notifications_topic_url", "notifications-topic-url")
    # Reuses the Calendar card's "How it works" summary label rather
    # than a second, near-duplicate string. Unconditional: the
    # storage/replacement fact is true whether or not a URL is stored yet.
    how_it_works_html = (
        '<details><summary>%s</summary><p class="text-body">%s</p></details>'
    ) % (
        escape_html(i18n.t(CALENDAR_HOW_IT_WORKS_SUMMARY)),
        escape_html(i18n.t(NOTIFICATIONS_URL_HOW_IT_WORKS_BODY)),
    )
    return (
        '<div class="rule-add-form__field">'
        '<label for="notifications-topic-url">%s</label>'
        '<input type="text" id="notifications-topic-url" '
        'name="notifications_topic_url" autocomplete="off" '
        'spellcheck="false" maxlength="%s"%s>'
        '<p class="text-label section-caption" id="%s">%s</p>'
        "%s"
        "%s"
        "</div>"
    ) % (
        escape_html(i18n.t(NOTIFICATIONS_URL_FIELD_LABEL)),
        NOTIFICATIONS_URL_MAX_LEN, url_error_attrs,
        escape_html(NOTIFICATIONS_URL_HINT_ID), escape_html(i18n.t(NOTIFICATIONS_URL_HINT)),
        url_error_html,
        how_it_works_html,
    )


def notifications_group(
        configured, current_battery_low, current_frame_silent,
        errors=None, submitted=None):
    """The Notifications settings card (Device scope only): battery-low
    and frame-silent checkboxes plus a write-only push-topic URL field.
    `configured` is a bare bool: the status row and the input (no
    `value` attribute, ever) never reveal the stored secret.

    The URL field waits on the page-wide Save; only "Send a test" is
    its own immediate-POST form, a sibling of `#settings-form`, since
    an immediate action must never nest inside the Save form.
    `errors`/`submitted` repopulate both checkboxes on a rejected save.
    """
    status_html = layout.status_row(
        "",
        i18n.t(
            NOTIFICATIONS_STATUS_CONFIGURED_VERDICT if configured
            else NOTIFICATIONS_STATUS_NOT_CONFIGURED_VERDICT),
        "",
        "ok" if configured else "warn")

    field_html = _notifications_url_field_html(errors)
    if configured:
        field_html = (
            '<details class="calendar-url-disclosure"><summary>%s</summary>%s</details>'
        ) % (escape_html(i18n.t(NOTIFICATIONS_REPLACE_URL_SUMMARY)), field_html)

    battery_checked = _submitted_checkbox_checked(
        submitted, "notifications_battery", NOTIFICATIONS_BATTERY_CHECKBOX_VALUE,
        current_battery_low)
    battery_error_attrs = _field_error_attrs(
        errors, "notifications_battery", "notifications-battery")
    battery_error_html = _field_error_html(
        errors, "notifications_battery", "notifications-battery")

    silent_checked = _submitted_checkbox_checked(
        submitted, "notifications_silent", NOTIFICATIONS_SILENT_CHECKBOX_VALUE,
        current_frame_silent)
    silent_error_attrs = _field_error_attrs(
        errors, "notifications_silent", "notifications-silent")
    silent_error_html = _field_error_html(
        errors, "notifications_silent", "notifications-silent")

    return (
        '<div class="theme-status" %s="%s">'
        '<h2 class="text-heading">%s</h2>'
        '<p class="text-label section-caption" id="%s">%s</p>'
        "%s"
        "%s"
        '<label class="settings-checkbox">'
        '<input type="checkbox" name="notifications_battery" value="%s"%s%s> %s'
        "</label>"
        "%s"
        '<label class="settings-checkbox">'
        '<input type="checkbox" name="notifications_silent" value="%s"%s%s> %s'
        "</label>"
        "%s"
        # Cross-DOM form= binds this button to the sibling
        # notifications-test form (notifications_test_section() below).
        '<button type="submit" form="notifications-test">%s</button>'
        "</div>"
    ) % (
        DIRTY_SECTION_ATTR, escape_html(i18n.t(NOTIFICATIONS_SECTION_HEADING)),
        escape_html(i18n.t(NOTIFICATIONS_SECTION_HEADING)),
        escape_html(NOTIFICATIONS_SECTION_CAPTION_ID), escape_html(i18n.t(NOTIFICATIONS_SECTION_CAPTION)),
        status_html,
        field_html,
        escape_html(NOTIFICATIONS_BATTERY_CHECKBOX_VALUE), " checked" if battery_checked else "",
        battery_error_attrs, escape_html(i18n.t(NOTIFICATIONS_BATTERY_LABEL)),
        battery_error_html,
        escape_html(NOTIFICATIONS_SILENT_CHECKBOX_VALUE), " checked" if silent_checked else "",
        silent_error_attrs, escape_html(i18n.t(NOTIFICATIONS_SILENT_LABEL)),
        silent_error_html,
        escape_html(i18n.t(NOTIFICATIONS_TEST_BUTTON_TEXT)),
    )


def notifications_test_section():
    """The "Send a test" button's own empty `<form>`, a sibling of
    `<form id="{SETTINGS_FORM_ID}">` — an immediate action must never
    nest inside the page-wide Save form. `render()` emits this after
    `</form>` closes, on the Device scope only.

    Carries no `data-confirm`: the handler reads the stored URL from
    disk and never trusts the request body, which is the real
    mitigation, not a confirmation dialog.
    """
    # The action and id are literal path/attribute text, not a %s
    # interpolation: this module's acceptance gate greps them.
    # The form stays a sibling of #settings-form, since a <form> can
    # never nest inside another <form>; the button reaches it via
    # form="notifications-test".
    return (
        '<form method="post" action="/settings/notifications/test" '
        'id="notifications-test" class="notifications-test-form"></form>'
    )
