"""The Audit log page body: a read-only, newest-first table of platform
events with filter chips and pagination.

Pure markup: it takes an `AuditView` and reads nothing else. Each event is a
compact row (when, who, action, outcome) whose native <details> chevron
reveals target, source address, exact date, author and reason. Rows carry
display text only (actor, plain-language action label, target, outcome,
source address); the stored `detail` JSON is never rendered, and the audit
store cannot hold a code, guess or secret. A co-manager row also carries the
person's e-mail and a reason key picked from a fixed whitelist by the caller;
a reason outside the whitelist shows a generic label. Every value is
HTML-escaped.
There is no form and no button on this page.
"""
import datetime
from typing import NamedTuple

from companion import i18n, ui_filter, ui_time
from companion.ui_base import LOCAL_TZ, escape_html, icon_html

PAGE_SIZE = 50
CATEGORY_QUERY = "category"
PAGE_QUERY = "page"

_COL_WHEN = i18n.msg("admin_lifecycle.when", "When")
_COL_WHO = i18n.msg("admin_lifecycle.who", "Who")
_COL_ACTION = i18n.msg("admin_lifecycle.action", "Action")
_COL_TARGET = i18n.msg("admin_lifecycle.target", "Target")
_COL_TARGET_ID = i18n.msg("admin_lifecycle.target_id", "Internal ID")
_COL_OUTCOME = i18n.msg("admin_lifecycle.outcome", "Outcome")
_COL_FROM = i18n.msg("admin_lifecycle.from", "From")
_COL_PERSON = i18n.msg("admin_lifecycle.audit_person", "Person")
_COL_REASON = i18n.msg("admin_lifecycle.audit_reason", "Reason")
_COL_EXACT = i18n.msg("admin_lifecycle.exact_date", "Exact date")
_COL_AUTHOR = i18n.msg("admin_lifecycle.author", "Author")

_UNKNOWN_USER = i18n.msg("admin_lifecycle.audit_unknown_user", "Unknown user")
_REASON_OTHER = i18n.msg("admin_lifecycle.audit_reason_other", "Other reason")
_ADD_ACTION = "device.co_manager_add"
_REMOVE_ACTION = "device.co_manager_remove"
# (action, via) -> why the co-manager row exists; any other pair is "other".
REASON_LABELS = {
    (_ADD_ACTION, "owner"): i18n.msg(
        "admin_lifecycle.audit_reason_add_owner", "Added by the frame owner"),
    (_ADD_ACTION, "admin"): i18n.msg(
        "admin_lifecycle.audit_reason_add_admin", "Added by an administrator"),
    (_REMOVE_ACTION, "self"): i18n.msg(
        "admin_lifecycle.audit_reason_remove_self", "Left the frame"),
    (_REMOVE_ACTION, "owner"): i18n.msg(
        "admin_lifecycle.audit_reason_remove_owner", "Removed by the frame owner"),
    (_REMOVE_ACTION, "admin"): i18n.msg(
        "admin_lifecycle.audit_reason_remove_admin", "Removed by an administrator"),
    (_REMOVE_ACTION, "reassign"): i18n.msg(
        "admin_lifecycle.audit_reason_remove_reassign",
        "Frame reassigned to a new owner"),
    (_REMOVE_ACTION, "retire"): i18n.msg(
        "admin_lifecycle.audit_reason_remove_retire", "Frame retired"),
    (_REMOVE_ACTION, "delete"): i18n.msg(
        "admin_lifecycle.audit_reason_remove_delete", "Frame deleted"),
    (_REMOVE_ACTION, "user_deleted"): i18n.msg(
        "admin_lifecycle.audit_reason_remove_user_deleted", "Person was deleted"),
    (_REMOVE_ACTION, "owner_disabled"): i18n.msg(
        "admin_lifecycle.audit_reason_remove_owner_disabled",
        "Frame owner was disabled"),
}

_ACTOR_SYSTEM = i18n.msg("admin_lifecycle.system", "System")
_ACTOR_FRAME = i18n.msg("admin_lifecycle.frame_actor", "Frame")

_OUTCOME_OK = i18n.msg("admin_lifecycle.outcome_success", "Success")
_OUTCOME_DENIED = i18n.msg("admin_lifecycle.outcome_refused", "Refused")
_OUTCOME_FAILED = i18n.msg("admin_lifecycle.outcome_failed", "Failed")
_OUTCOMES = {"ok": _OUTCOME_OK, "denied": _OUTCOME_DENIED, "failed": _OUTCOME_FAILED}

_ACTION_OTHER = i18n.msg("admin_lifecycle.action_other", "Other action")
ACTION_LABELS = {
    "frame.register": i18n.msg("admin_lifecycle.action_frame_register", "Frame registered"),
    "pairing.issue": i18n.msg("admin_lifecycle.action_pairing_issue", "Pairing code issued"),
    "pairing.claim": i18n.msg("admin_lifecycle.action_pairing_claim", "Pairing code claimed"),
    "device.reassign": i18n.msg("admin_lifecycle.action_device_reassign", "Frame reassigned"),
    "device.retire": i18n.msg("admin_lifecycle.action_device_retire", "Frame retired"),
    "device.rename": i18n.msg("admin_lifecycle.action_device_rename", "Frame renamed"),
    "device.reactivate": i18n.msg(
        "admin_lifecycle.action_device_reactivate", "Frame re-activated"),
    "device.co_manager_add": i18n.msg(
        "admin_lifecycle.action_device_co_manager_add", "Co-manager added"),
    "device.co_manager_remove": i18n.msg(
        "admin_lifecycle.action_device_co_manager_remove", "Co-manager removed"),
    "user.invite": i18n.msg("admin_lifecycle.action_user_invite", "User invited"),
    "user.role": i18n.msg("admin_lifecycle.action_user_role", "Role changed"),
    "user.disable": i18n.msg("admin_lifecycle.action_user_disable", "User disabled"),
    "user.enable": i18n.msg("admin_lifecycle.action_user_enable", "User enabled"),
    "user.unlink": i18n.msg("admin_lifecycle.action_user_unlink", "Identity unlinked"),
    "user.delete": i18n.msg("admin_lifecycle.action_user_delete", "User deleted"),
    "location.add": i18n.msg("admin_lifecycle.action_location_add", "Location added"),
    "location.update": i18n.msg("admin_lifecycle.action_location_update", "Location updated"),
    "location.delete": i18n.msg("admin_lifecycle.action_location_delete", "Location deleted"),
    "airline.resolve": i18n.msg("admin_lifecycle.action_airline_resolve", "Airline named"),
    "airline.artwork_delete": i18n.msg(
        "admin_lifecycle.action_airline_artwork_delete", "Airline artwork removed"),
    "airline.default_type": i18n.msg(
        "admin_lifecycle.action_airline_default_type", "Default aircraft type changed"),
    "release.install": i18n.msg(
        "admin_lifecycle.action_release_install", "Release install scheduled"),
    "release.cancel": i18n.msg(
        "admin_lifecycle.action_release_cancel", "Release install cancelled"),
}

# (category key, label) in display order; keys are `fleet_db.AUDIT_CATEGORIES`.
CATEGORY_CHIPS = (
    ("all", i18n.msg("admin_lifecycle.chip_all", "All")),
    ("pairing", i18n.msg("admin_lifecycle.chip_pairing", "Pairing")),
    ("frames", i18n.msg("admin_lifecycle.chip_frames", "Frames")),
    ("users", i18n.msg("admin_lifecycle.chip_users", "Users")),
    ("locations", i18n.msg("admin_lifecycle.chip_locations", "Locations")),
    ("releases", i18n.msg("admin_lifecycle.chip_releases", "Releases")),
    ("failed", i18n.msg("admin_lifecycle.chip_failed", "Failed")),
)
_CHIPS_LABEL = i18n.msg("admin_lifecycle.filter_events", "Filter events")

_COUNT_MANY = i18n.msg("admin_lifecycle.n_events", "%d events")
_COUNT_ONE = i18n.msg("admin_lifecycle.one_event", "1 event")
_NO_TARGET = "-"

_EMPTY_HEADING = i18n.msg("admin_lifecycle.nothing_recorded_yet", "Nothing recorded yet")
_EMPTY_BODY = i18n.msg(
    "admin_lifecycle.actions_such_as_pairing_role_changes_and_releases",
    "Actions such as pairing, role changes and releases will appear here.")
_EMPTY_FILTER_HEADING = i18n.msg(
    "admin_lifecycle.no_events_match_this_filter", "No events match this filter")
_EMPTY_FILTER_BODY = i18n.msg(
    "admin_lifecycle.choose_all_to_see_every_event", "Choose All to see every event.")

_OLDER = i18n.msg("admin_lifecycle.older", "Older")
_NEWER = i18n.msg("admin_lifecycle.newer", "Newer")
_PAGER_LABEL = i18n.msg("admin_lifecycle.audit_pages", "Audit log pages")


class CoManagerNote(NamedTuple):
    """The person and reason of a co-manager row. `email` is the user's
    address or "" when the id is missing or unknown; `via` is the stored
    reason word, mapped through `REASON_LABELS` and never shown itself."""
    email: str
    via: str


class AuditEvent(NamedTuple):
    """One row as shown. `ts` is epoch seconds; `actor_label` and
    `actor_is_user` come from the audit row (`actor_is_user` is True when the
    row carries a user id); `target_primary` is a name, an email or "" and
    `target_id` the stored id or None."""
    ts: int
    actor_label: str
    actor_is_user: bool
    action: str
    target_primary: str
    target_id: str | None
    outcome: str
    source_ip: str | None
    note: CoManagerNote | None = None


class AuditView(NamedTuple):
    events: tuple
    category: str
    total: int
    page: int
    now: datetime.datetime


def _ui():
    # Imported on use: this page loads while the navigation is still importing.
    from companion import ui_components
    return ui_components


def _esc(value):
    return escape_html(value)


def _t(message):
    return _esc(i18n.t(message))


def actor_text(event):
    """The Who text: a user's email, "System" for the CLI, "Frame" for a
    frame's own label."""
    if event.actor_is_user:
        return event.actor_label
    if event.actor_label == "cli":
        return i18n.t(_ACTOR_SYSTEM)
    if event.actor_label.startswith("frame:"):
        return i18n.t(_ACTOR_FRAME)
    return event.actor_label


def action_text(action):
    """The plain-language label; an unknown key gives a generic label, never
    the raw key."""
    return i18n.t(ACTION_LABELS.get(action, _ACTION_OTHER))


def note_texts(event):
    """(person, reason) display texts of a co-manager row, or None."""
    if event.note is None:
        return None
    person = event.note.email or i18n.t(_UNKNOWN_USER)
    label = REASON_LABELS.get((event.action, event.note.via), _REASON_OTHER)
    return person, i18n.t(label)


def _when_html(event, now):
    seen = datetime.datetime.fromtimestamp(event.ts, datetime.timezone.utc)
    return (
        '<span class="time-value">%s</span>'
        '<span class="time-value__age">%s</span>' % (
            _esc(ui_time.local_clock_text(seen, now_parsed=now)),
            ui_time.relative_time_html(seen.isoformat(), now.isoformat())))


def _exact_date_text(event):
    """"D Mon YYYY, HH:MM" in Europe/Paris, in the request's language."""
    local = datetime.datetime.fromtimestamp(event.ts, datetime.timezone.utc).astimezone(
        LOCAL_TZ)
    return "%d %s %d, %s" % (
        local.day, ui_time.month_abbr(local.month), local.year, local.strftime("%H:%M"))


def _target_html(event):
    if event.target_id is None:
        return '<span class="cell-primary">%s</span>' % _esc(_NO_TARGET)
    return '<span class="cell-primary">%s</span>' % _esc(
        event.target_primary or event.target_id)


def _target_id_item(event):
    """The target's stored id as an item of its own, labelled and secondary,
    only when the Target item shows a name or an address instead of it."""
    if event.target_id is None or not event.target_primary:
        return []
    return [_detail_item(
        _COL_TARGET_ID, '<span class="cell-secondary mono">%s</span>' % _esc(event.target_id),
        " audit-event__item--secondary")]


def _outcome_html(event):
    label = _OUTCOMES.get(event.outcome, _OUTCOME_FAILED)
    # Imported on use: this page loads while the navigation is still importing.
    from companion import ui_components
    return ui_components.pill_html(i18n.t(label))


def _detail_item(label, value_html, extra_class=""):
    return '<div class="audit-event__item%s"><dt>%s</dt><dd>%s</dd></div>' % (
        extra_class, _t(label), value_html)


def _detail_html(event):
    """The fields behind the chevron: target, source address, exact date,
    author and, for a co-manager row, the person and the reason."""
    items = [
        _detail_item(_COL_TARGET, _target_html(event)),
        *_target_id_item(event),
        _detail_item(_COL_FROM, '<span class="mono">%s</span>' % _esc(event.source_ip)
                     if event.source_ip else _esc(_NO_TARGET)),
        _detail_item(_COL_EXACT, _esc(_exact_date_text(event))),
        _detail_item(_COL_AUTHOR, _esc(actor_text(event))),
    ]
    texts = note_texts(event)
    if texts is not None:
        items.append(_detail_item(
            _COL_PERSON, '<span class="co-manager__email">%s</span>' % _esc(texts[0])))
        items.append(_detail_item(_COL_REASON, _esc(texts[1])))
    return '<dl class="audit-event__detail">%s</dl>' % "".join(items)


def _event_html(event, now):
    return (
        '<li class="audit-event"><details>'
        '<summary class="audit-event__row">'
        '<span class="audit-event__when">%s</span>'
        '<span class="audit-event__who">%s</span>'
        '<span class="audit-event__action">%s</span>'
        '<span class="audit-event__outcome">%s</span>%s</summary>%s</details></li>' % (
            _when_html(event, now), _esc(actor_text(event)),
            _esc(action_text(event.action)), _outcome_html(event),
            icon_html("icon-chevron-right", size=16, extra_class="audit-event__chevron"),
            _detail_html(event)))


def _table_html(view):
    heads = "".join(
        '<span class="audit-head__cell audit-head__cell--%s">%s</span>' % (name, _t(label))
        for name, label in (
            ("when", _COL_WHEN), ("who", _COL_WHO), ("action", _COL_ACTION),
            ("outcome", _COL_OUTCOME)))
    events = "".join(_event_html(event, view.now) for event in view.events)
    return (
        '<ul class="audit-cards"><li class="audit-head" aria-hidden="true">%s</li>%s</ul>' % (
            heads, events))


def audit_href(category, page):
    """`/audit` with the non-default query values only."""
    from companion import console_routes
    params = []
    if category != "all":
        params.append("%s=%s" % (CATEGORY_QUERY, category))
    if page > 1:
        params.append("%s=%d" % (PAGE_QUERY, page))
    return console_routes.AUDIT_ROUTE + ("?" + "&".join(params) if params else "")


def _chips_html(view):
    return ui_filter.chip_links_html(
        [(_esc(audit_href(key, 1)), i18n.t(label), key == view.category)
         for key, label in CATEGORY_CHIPS],
        i18n.t(_CHIPS_LABEL), tabs="audit")


def _count_html(total):
    text = i18n.t(_COUNT_ONE) if total == 1 else i18n.t(_COUNT_MANY) % total
    return '<p class="filter-bar__count" role="status">%s</p>' % _esc(text)


def _pager_html(view):
    links = []
    if view.page * PAGE_SIZE < view.total:
        links.append('<a class="text-link" rel="next" href="%s">%s</a>' % (
            _esc(audit_href(view.category, view.page + 1)), _t(_OLDER)))
    if view.page > 1:
        links.append('<a class="text-link" rel="prev" href="%s">%s</a>' % (
            _esc(audit_href(view.category, view.page - 1)), _t(_NEWER)))
    if not links:
        return ""
    return '<nav class="audit-pager" aria-label="%s">%s</nav>' % (
        _t(_PAGER_LABEL), "".join(links))


def render(view):
    """The Audit log page body (the shell supplies header and sub-nav)."""
    parts = [_chips_html(view), _count_html(view.total)]
    if not view.events:
        if view.category == "all":
            parts.append(_ui().empty_state(
                i18n.t(_EMPTY_HEADING), i18n.t(_EMPTY_BODY), compact=True))
        else:
            parts.append(_ui().empty_state(
                i18n.t(_EMPTY_FILTER_HEADING), i18n.t(_EMPTY_FILTER_BODY)))
            parts[-1] = parts[-1].replace(
                'class="empty-state"', 'class="empty-state empty-state--filter"', 1)
    else:
        parts.append(_table_html(view))
        parts.append(_pager_html(view))
    return "".join(parts)
