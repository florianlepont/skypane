"""The one status dot of a frame.

`frame_status(row)` turns a frame row into a single dot class and a single
word, by a fixed priority: the first matching rule wins, so a frame that is
both offline and low on battery reads "No contact". Every list, switcher and
Home status dot renders through here so they can never disagree.

The resolver reads only server-side device state from the row (attributes
`kind`, `offline`, `last_seen`, `battery_percent`, `state`, `screen_off`);
nothing from a request reaches it. A missing attribute counts as "not set".
The words come from a fixed catalogue. Never raises.
"""
from typing import NamedTuple

from companion import frame_state, i18n
from companion.ui_base import escape_html

# Row kinds, matching the fleet page's rows.
KIND_LIVE = "live"
KIND_PENDING = "pending"
KIND_RETIRED = "retired"

KEY_RETIRED = "retired"
KEY_WAITING = "waiting"
KEY_NO_CONTACT = "no_contact"
KEY_NOT_SEEN = "not_seen"
KEY_OVERDUE = "overdue"
KEY_LOW_BATTERY = "low_battery"
KEY_RESTING = "resting"
KEY_UP_TO_DATE = "up_to_date"

# The dot state names status_dot() understands ("hollow" is the outlined
# ring used for the two states without a live device).
STATUS_HOLLOW = "hollow"
STATUS_ERROR = "error"
STATUS_WARN = "warn"
STATUS_OFF = "off"
STATUS_OK = "ok"

WORD_RETIRED = i18n.msg("frame_state.status_retired", "Retired")
WORD_WAITING = i18n.msg("frame_state.status_waiting", "Waiting for pairing")
WORD_NO_CONTACT = i18n.msg("frame_state.status_no_contact", "No contact")
WORD_NOT_SEEN = i18n.msg("frame_state.status_not_seen", "Not seen yet")
WORD_OVERDUE = i18n.msg("frame_state.status_overdue", "Overdue")
WORD_LOW_BATTERY = i18n.msg("frame_state.status_low_battery", "Low battery")
WORD_RESTING = i18n.msg("frame_state.status_resting", "Resting")
WORD_UP_TO_DATE = i18n.msg("frame_state.status_up_to_date", "Online")


class FrameStatus(NamedTuple):
    """`dot_state` is a status_dot() state, `word` the message for the
    state's name, `key` a stable identifier for callers and tests."""
    dot_state: str
    word: object
    key: str


_RETIRED = FrameStatus(STATUS_HOLLOW, WORD_RETIRED, KEY_RETIRED)
_WAITING = FrameStatus(STATUS_HOLLOW, WORD_WAITING, KEY_WAITING)
_NO_CONTACT = FrameStatus(STATUS_ERROR, WORD_NO_CONTACT, KEY_NO_CONTACT)
_NOT_SEEN = FrameStatus(STATUS_WARN, WORD_NOT_SEEN, KEY_NOT_SEEN)
_OVERDUE = FrameStatus(STATUS_WARN, WORD_OVERDUE, KEY_OVERDUE)
_LOW_BATTERY = FrameStatus(STATUS_WARN, WORD_LOW_BATTERY, KEY_LOW_BATTERY)
_RESTING = FrameStatus(STATUS_OFF, WORD_RESTING, KEY_RESTING)
_UP_TO_DATE = FrameStatus(STATUS_OK, WORD_UP_TO_DATE, KEY_UP_TO_DATE)


def _low_battery_percent():
    from companion import battery
    return battery.LOW_BATTERY_DISPLAY_PERCENT


def _is_low_battery(percent, threshold):
    return isinstance(percent, (int, float)) and percent <= threshold


def frame_status(row, low_battery_percent=None):
    """The FrameStatus of `row`, by the first matching rule: retired,
    waiting for pairing, no contact, not seen yet, overdue or low battery,
    resting (quiet hours or screen off), up to date."""
    kind = getattr(row, "kind", KIND_LIVE)
    if kind == KIND_RETIRED:
        return _RETIRED
    if kind == KIND_PENDING:
        return _WAITING
    if getattr(row, "offline", False):
        return _NO_CONTACT
    if getattr(row, "never_seen", False) or (
            hasattr(row, "last_seen") and row.last_seen is None):
        return _NOT_SEEN
    if getattr(row, "state", None) == frame_state.STATE_LATE:
        return _OVERDUE
    threshold = (
        _low_battery_percent() if low_battery_percent is None
        else low_battery_percent)
    if _is_low_battery(getattr(row, "battery_percent", None), threshold):
        return _LOW_BATTERY
    if getattr(row, "state", None) == frame_state.STATE_HELD or getattr(
            row, "screen_off", False):
        return _RESTING
    return _UP_TO_DATE


def status_dot_html(row, low_battery_percent=None):
    """The dot for `row`: no visible word, the word carried by `title`,
    `aria-label` and visually hidden text."""
    # Imported on use, page_context first: ui_components only loads
    # cleanly when page_context starts the import chain.
    import companion.page_context  # noqa: F401
    from companion.ui_components import status_dot
    status = frame_status(row, low_battery_percent)
    word = i18n.t(status.word)
    markup = status_dot(
        status.dot_state, word, title=word, visually_hide_label=True)
    return markup.replace(
        '<span class="dot ',
        '<span role="img" aria-label="%s" class="dot ' % escape_html(word), 1)
