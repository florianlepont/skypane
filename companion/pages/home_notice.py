"""The notification Home shows while the frame's dot is amber or red.

It says what is wrong in one short sentence from figures the server already holds
(battery percent, time since the last check-in), gives one short actionable sentence,
and ends with a way to reach an administrator: a mailto link to the first
active administrator, or plain text when there is none. Nothing is sent by
the server and no route is involved.

The notification states only what the server knows. A frame that has lost
contact could have a Wi-Fi, an internet or a server problem and the server
cannot tell them apart, so no cause is ever named for it. A figure that is
not known (no percent, no last check-in) drops its line.
"""
import re
import sqlite3
from urllib.parse import quote

import companion.frame_status as frame_status
import companion.i18n as i18n
import companion.layout as layout
import companion.ui_time as ui_time
from companion.layout import escape_html
from server import fleet_db

EXPLAIN_NOT_SEEN = i18n.msg(
    "home.notice_explain_not_seen", "Your frame has not contacted SkyPane yet.")
EXPLAIN_OVERDUE = i18n.msg(
    "home.notice_explain_overdue", "Your frame has not checked in on time.")
EXPLAIN_LOW_BATTERY = i18n.msg(
    "home.notice_explain_low_battery", "Your frame's battery is low.")
EXPLAIN_NO_CONTACT = i18n.msg(
    "home.notice_explain_no_contact", "Your frame has no contact with the server.")

LINE_BATTERY = i18n.msg("home.notice_line_battery", "Frame battery at %d%%")
LINE_CHARGING = i18n.msg(
    "home.notice_line_charging", "The frame may be charging.")
LINE_LAST_CHECK_IN = i18n.msg("home.notice_line_last_check_in", "Last check-in %s")
LINE_LAST_CONTACT = i18n.msg("home.notice_line_last_contact", "Last contact %s")

TIP_LOW_BATTERY = i18n.msg(
    "home.notice_tip_low_battery", "Charge it or plug it in.")
TIP_OVERDUE = i18n.msg(
    "home.notice_tip_overdue",
    "Wait one cycle; if it stays silent, contact an administrator.")
TIP_NOT_SEEN = i18n.msg(
    "home.notice_tip_not_seen",
    "Check it is powered; if it stays silent, contact an administrator.")
TIP_NO_CONTACT = i18n.msg(
    "home.notice_tip_no_contact",
    "Check its power and your Wi-Fi; if it stays silent, contact an administrator.")

CONTACT_LABEL = i18n.msg("home.notice_contact_label", "Contact an administrator")
MAIL_SUBJECT = i18n.msg(
    "home.notice_mail_subject", "SkyPane: help with the frame %s (%s)")
MAIL_BODY = i18n.msg(
    "home.notice_mail_body",
    "Hello,\n\nMy frame %s shows the state %s in SkyPane.\n%s\nCould you take "
    "a look?\n")

_EXPLANATIONS = {
    frame_status.KEY_NOT_SEEN: EXPLAIN_NOT_SEEN,
    frame_status.KEY_OVERDUE: EXPLAIN_OVERDUE,
    frame_status.KEY_LOW_BATTERY: EXPLAIN_LOW_BATTERY,
    frame_status.KEY_NO_CONTACT: EXPLAIN_NO_CONTACT,
}
_TIPS = {
    frame_status.KEY_NOT_SEEN: TIP_NOT_SEEN,
    frame_status.KEY_OVERDUE: TIP_OVERDUE,
    frame_status.KEY_LOW_BATTERY: TIP_LOW_BATTERY,
    frame_status.KEY_NO_CONTACT: TIP_NO_CONTACT,
}

# A conservative address: a plain local part, one at sign, a dotted host.
# Anything else (whitespace, control characters, comma, angle brackets,
# quote, a second at sign, a query separator) is refused.
_ADDRESS = re.compile(
    r"^[A-Za-z0-9._%+-]{1,64}@[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?"
    r"(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?)+$")
_ADDRESS_MAX = 254


def usable_address(value):
    """The address itself when it has a safe shape, else None."""
    if isinstance(value, str) and len(value) <= _ADDRESS_MAX and _ADDRESS.match(value):
        return value
    return None


def administrator_contact(conn):
    """The email of the first active administrator by user id, or None when
    there is none, the address is unusable or the database cannot be read.
    A disabled administrator and a plain user are never chosen."""
    try:
        for row in fleet_db.list_users(conn):
            if row["role"] == "admin" and not row["disabled"]:
                return usable_address(row["email"])
    except (sqlite3.Error, KeyError, IndexError, TypeError):
        return None
    return None


def contact_for_state_dir(state_dir):
    """`administrator_contact()` over a short-lived read-only handle on the
    fleet database; None when it is absent or unreadable."""
    if not state_dir:
        return None
    try:
        conn = fleet_db.connect_readonly(state_dir)
    except (sqlite3.Error, fleet_db.FleetDbError, OSError):
        return None
    try:
        return administrator_contact(conn)
    finally:
        conn.close()


def _age_text(facts):
    """"3h ago" for the last check-in, or None when it is unknown."""
    age = ui_time.age_seconds(facts.last_seen, facts.now) if facts.last_seen else None
    return None if age is None else ui_time.relative_age_text(age)


def _battery_lines(facts):
    lines = []
    if isinstance(facts.percent, (int, float)):
        lines.append(i18n.t(LINE_BATTERY) % int(facts.percent))
    if facts.charging:
        lines.append(i18n.t(LINE_CHARGING))
    return lines


def _check_in_lines(facts):
    age = _age_text(facts)
    return [] if age is None else [i18n.t(LINE_LAST_CHECK_IN) % age]


def _contact_lines(facts):
    age = _age_text(facts)
    lines = [] if age is None else [i18n.t(LINE_LAST_CONTACT) % age]
    return lines


_LINES = {
    frame_status.KEY_NOT_SEEN: lambda facts: [],
    frame_status.KEY_OVERDUE: _check_in_lines,
    frame_status.KEY_LOW_BATTERY: _battery_lines,
    frame_status.KEY_NO_CONTACT: _contact_lines,
}


def applies(status):
    """Whether `status` (a FrameStatus) is amber or red."""
    return status.key in _EXPLANATIONS and status.dot_state in (
        frame_status.STATUS_WARN, frame_status.STATUS_ERROR)


def mailto_href(address, facts, status):
    """`mailto:` to `address` with a percent-encoded subject and body that
    carry the frame name, the state and the known figures. `address` must
    already have passed usable_address()."""
    name = facts.frame_name or ""
    state_word = i18n.t(status.word)
    figures = "".join("%s\n" % line for line in _LINES[status.key](facts))
    subject = i18n.t(MAIL_SUBJECT) % (name, state_word)
    body = i18n.t(MAIL_BODY) % (name, state_word, figures)
    return "mailto:%s?subject=%s&body=%s" % (
        quote(address, safe="@"), quote(subject, safe=""), quote(body, safe=""))


def _lines_html(lines, tip):
    parts = ['<span class="home-notice__line">%s</span>' % escape_html(line)
             for line in lines]
    parts.append('<span class="home-notice__tip">%s</span>' % escape_html(tip))
    return "".join(parts)


def notification_html(facts, status, contact):
    """The notification for `status`, or "" when the dot is neither amber
    nor red. `facts` carries frame_name, percent, charging, last_seen and
    now; `contact` is an administrator address or None."""
    if not applies(status):
        return ""
    tone = (layout.TOAST_TONE_ERROR if status.dot_state == frame_status.STATUS_ERROR
            else layout.TOAST_TONE_WARNING)
    lines = _LINES[status.key](facts)
    extra = _lines_html(lines, i18n.t(_TIPS[status.key]))
    address = usable_address(contact)
    action = (layout.toast_link_action_html(
        mailto_href(address, facts, status), i18n.t(CONTACT_LABEL))
        if address else "")
    return layout.toast_html(
        i18n.t(_EXPLANATIONS[status.key]), tone=tone, role="", docked=True,
        extra_html=extra, action_html=action, extra_class="home-notice")
