"""The Audit log page body: a read-only, newest-first table of platform
events with filter chips and pagination.

Pure markup: it takes an `AuditView` and reads nothing else. Rows carry
display text only (actor, plain-language action label, target, outcome,
source address); the stored `detail` JSON is never rendered, and the audit
store cannot hold a code, guess or secret. Every value is HTML-escaped.
There is no form and no button on this page.
"""
import datetime
from typing import NamedTuple

from companion import i18n, ui_time
from companion.ui_base import escape_html

AUDIT_PURPOSE = i18n.msg(
    "admin_lifecycle.what_happened_on_the_platform_newest_first",
    "What happened on the platform, newest first.")

PAGE_SIZE = 50
CATEGORY_QUERY = "category"
PAGE_QUERY = "page"

_COL_WHEN = i18n.msg("admin_lifecycle.when", "When")
_COL_WHO = i18n.msg("admin_lifecycle.who", "Who")
_COL_ACTION = i18n.msg("admin_lifecycle.action", "Action")
_COL_TARGET = i18n.msg("admin_lifecycle.target", "Target")
_COL_OUTCOME = i18n.msg("admin_lifecycle.outcome", "Outcome")
_COL_FROM = i18n.msg("admin_lifecycle.from", "From")

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
    "device.reactivate": i18n.msg(
        "admin_lifecycle.action_device_reactivate", "Frame re-activated"),
    "user.invite": i18n.msg("admin_lifecycle.action_user_invite", "User invited"),
    "user.role": i18n.msg("admin_lifecycle.action_user_role", "Role changed"),
    "user.disable": i18n.msg("admin_lifecycle.action_user_disable", "User disabled"),
    "user.enable": i18n.msg("admin_lifecycle.action_user_enable", "User enabled"),
    "user.unlink": i18n.msg("admin_lifecycle.action_user_unlink", "Identity unlinked"),
    "location.add": i18n.msg("admin_lifecycle.action_location_add", "Location added"),
    "location.update": i18n.msg("admin_lifecycle.action_location_update", "Location updated"),
    "location.delete": i18n.msg("admin_lifecycle.action_location_delete", "Location deleted"),
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


def _when_html(event, now):
    seen = datetime.datetime.fromtimestamp(event.ts, datetime.timezone.utc)
    return (
        '<span class="time-value">%s</span><span class="cell-inline-sep">·</span>'
        '<span class="time-value__age">(%s)</span>' % (
            _esc(ui_time.local_clock_text(seen, now_parsed=now)),
            ui_time.relative_time_html(seen.isoformat(), now.isoformat())))


def _target_html(event):
    if event.target_id is None:
        return '<span class="cell-primary">%s</span>' % _esc(_NO_TARGET)
    primary = event.target_primary or event.target_id
    secondary = (
        '<span class="cell-secondary mono">%s</span>' % _esc(event.target_id)
        if event.target_primary else "")
    return '<span class="cell-primary">%s</span>%s' % (_esc(primary), secondary)


def _outcome_html(event):
    label = _OUTCOMES.get(event.outcome, _OUTCOME_FAILED)
    return '<span class="banner__pill">%s</span>' % _t(label)


def _from_html(event):
    return '<span class="mono">%s</span>' % _esc(event.source_ip) if event.source_ip else ""


def _row_html(event, now):
    return (
        "<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>" % (
            _when_html(event, now), _esc(actor_text(event)), _esc(action_text(event.action)),
            _target_html(event), _outcome_html(event), _from_html(event)))


def _pair(label, value_html):
    return (
        '<span class="data-card__label">%s</span> '
        '<span class="data-card__value">%s</span>' % (_t(label), value_html))


def _card_html(event, now):
    return (
        '<li class="data-card">'
        '<div class="data-card__primary"><span>%s</span><span>%s</span></div>'
        '<div class="data-card__secondary">%s</div>'
        '<div class="data-card__secondary">%s</div>'
        '<div class="data-card__secondary">%s</div>'
        '<div class="data-card__secondary">%s</div></li>' % (
            _esc(action_text(event.action)), _outcome_html(event),
            _pair(_COL_WHEN, _when_html(event, now)),
            _pair(_COL_WHO, _esc(actor_text(event))),
            _pair(_COL_TARGET, _target_html(event)),
            _pair(_COL_FROM, _from_html(event))))


def _table_html(view):
    heads = "".join("<th>%s</th>" % _t(label) for label in (
        _COL_WHEN, _COL_WHO, _COL_ACTION, _COL_TARGET, _COL_OUTCOME, _COL_FROM))
    body = "".join(_row_html(event, view.now) for event in view.events)
    cards = "".join(_card_html(event, view.now) for event in view.events)
    # Cards first: style.css hides the table behind `.data-cards ~
    # .data-table-wrap` below 960px by sibling order.
    return (
        '<ul class="data-cards">%s</ul>'
        '<div class="data-table-wrap"><table class="data-table data-table--flights">'
        "<thead><tr>%s</tr></thead><tbody>%s</tbody></table></div>" % (cards, heads, body))


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
    chips = []
    for key, label in CATEGORY_CHIPS:
        current = key == view.category
        chips.append(
            '<a class="filter-chip%s" href="%s"%s>'
            '<span class="filter-chip__box"><span class="filter-chip__text">%s</span></span>'
            "</a>" % (
                " filter-chip--current" if current else "", _esc(audit_href(key, 1)),
                ' aria-current="true"' if current else "", _t(label)))
    return '<nav class="filter-bar__chips audit-chips" aria-label="%s">%s</nav>' % (
        _t(_CHIPS_LABEL), "".join(chips))


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
            parts.append(_ui().empty_state(i18n.t(_EMPTY_HEADING), i18n.t(_EMPTY_BODY)))
        else:
            parts.append(_ui().empty_state(
                i18n.t(_EMPTY_FILTER_HEADING), i18n.t(_EMPTY_FILTER_BODY)))
            parts[-1] = parts[-1].replace(
                'class="empty-state"', 'class="empty-state empty-state--filter"', 1)
    else:
        parts.append(_table_html(view))
        parts.append(_pager_html(view))
    return "".join(parts)
