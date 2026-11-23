"""The Fleet page's list of frames, the frame switch and the pages of a pending
or retired frame.

Pure markup built from the `FleetView` rows: the list shows live frames, then
pending and retired ones, each as a link to `/fleet?frame=<id>`; a pending or
retired frame opens its own page with only its useful action and never appears
on another frame's page. The switch is a bounded chip row (a phone) that starts
with "All frames". Every dynamic part is escaped.
"""
import datetime

from companion import frame_status, i18n, ui_filter, ui_groups, ui_modal, ui_time
from companion.pages import fleet_page
from companion.ui_base import escape_html, icon_html

FRAME_HREF_PREFIX = "/fleet?frame="
LIST_HREF = "/fleet"
SEARCH_FROM = 8
CHIP_LIMIT = 8
SEARCH_ID = "fleet-frame-search"

_FRAMES = i18n.msg("admin_fleet.frames", "Frames")
_GROUP_LIVE = i18n.msg("admin_fleet.group_live", "Live")
_GROUP_PENDING = i18n.msg("admin_fleet.group_pending", "Waiting to be paired")
_GROUP_RETIRED = i18n.msg("admin_fleet.group_retired", "Retired")
_SEARCH = i18n.msg("admin_fleet.search_frames", "Search %d frames")
_ALL_FRAMES = i18n.msg("admin_fleet.all_frames_n", "All frames (%d)")
_NO_MATCH = i18n.msg("admin_fleet.no_frame_found", "No frame found")
_SWITCH_ARIA = i18n.msg("nav.frame_strip_aria", "Your frames")
_RETIRED_ON = i18n.msg("admin_fleet.retired_on", "Retired %s")
_BELONGED_TO = i18n.msg("admin_fleet.belonged_to", "Belonged to %s")
_CODE_SHOWN = i18n.msg("admin_fleet.code_shown_ago", "Code shown %s")
_REACTIVATE_HINT = i18n.msg(
    "admin_fleet.reactivate_wake_hint",
    "The frame shows its pairing code at its next wake (up to 24 h). Press "
    "Reset to restart it now.")


def _esc(value):
    return escape_html(value)


def _t(message):
    return _esc(i18n.t(message))


def frame_href(frame_id):
    return FRAME_HREF_PREFIX + frame_id


def find_row(view, frame_id):
    """The row of `view` with id `frame_id`, whatever its kind, or None. The
    id comes from the request and is only compared, never used as a path."""
    return next((r for r in view.rows if r.frame_id == frame_id), None)


def live_rows(view):
    return [r for r in view.rows if r.kind == fleet_page.KIND_LIVE]


def first_to_watch(view):
    """The live row to show when no frame is chosen: the first one in the
    list order (a frame with a problem comes first)."""
    live = live_rows(view)
    return live[0] if live else None


def _status_word(row):
    return i18n.t(frame_status.frame_status(row).word)


def _seen(row, view):
    from companion import ui_shell
    if row.kind != fleet_page.KIND_LIVE or row.last_seen is None:
        return ""
    return ui_shell.seen_text(row, view.now.timestamp())


def _retired_day(row, now):
    """The day a retired frame was retired as "12 Oct" (the year is added when
    it is not the current one), on the Paris clock; "" without a stored date."""
    if row.retired_at is None:
        return ""
    try:
        local = datetime.datetime.fromtimestamp(row.retired_at, ui_time.LOCAL_TZ)
    except (OverflowError, OSError, ValueError):
        return ""
    day = "%d %s" % (local.day, ui_time.month_abbr(local.month))
    if local.year != now.astimezone(ui_time.LOCAL_TZ).year:
        day += " %d" % local.year
    return day


def _row_detail(row, view):
    """The second line of a row: status and owner for a live frame; for a
    retired frame its owner and retirement day; for a pending frame how long
    ago its code was shown. A row without the stored moment keeps the plain
    wording (Formerly owner, Waiting for pairing)."""
    owner = fleet_page.owner_line(row)
    if row.kind == fleet_page.KIND_LIVE:
        return "%s · %s" % (_status_word(row), owner) if row.owner_email else _status_word(row)
    if row.kind == fleet_page.KIND_PENDING and row.code_issued_at is not None:
        age = ui_time.relative_age_text(view.now.timestamp() - row.code_issued_at)
        return i18n.t(_CODE_SHOWN) % age
    day = _retired_day(row, view.now) if row.kind == fleet_page.KIND_RETIRED else ""
    if day:
        retired = i18n.t(_RETIRED_ON) % day
        return "%s · %s" % (row.owner_email, retired) if row.owner_email else retired
    return owner


def _row_item(row, view, selected_id):
    """One frame as a list row: status dot, name, owner and status word, the
    last-seen word and a chevron; the whole row is a link."""
    name = fleet_page.display_name(row)
    current = row.frame_id == selected_id
    item = ui_groups.row(
        name, detail=_row_detail(row, view), value_html=_esc(_seen(row, view)),
        href=frame_href(row.frame_id), lead_html=frame_status.status_dot_html(row),
        extra_class="fleet-frame-row" + (" is-selected" if current else ""),
        attrs='data-filter-text="%s"' % _esc(
            ("%s %s %s" % (name, row.owner_email or "", _status_word(row))).lower()))
    if current:
        item = item.replace('<a class="row__main"', '<a class="row__main" aria-current="page"', 1)
    return item


def _group(label_msg, rows, view, selected_id, slug):
    if not rows:
        return ""
    return ui_groups.group(
        "".join(_row_item(r, view, selected_id) for r in rows),
        label="%s · %d" % (i18n.t(label_msg), len(rows)),
        label_id="fleet-list-" + slug, extra_class="fleet-list-group",
        attrs="data-filter-day-group")


def _heading_html(landing, with_frame):
    """The list's title. Beside a frame it is an `<h2>`. On the landing view
    a phone shows it as the page's `<h1>`; when a frame is shown beside the list
    (a wide screen), that frame's name is the `<h1>` and the list's title an `<h2>`."""
    text = _t(_FRAMES)
    if not landing:
        return '<h2 class="fleet-list__heading">%s</h2>' % text
    if not with_frame:
        return '<h1 class="fleet-list__heading">%s</h1>' % text
    return (
        '<h1 class="fleet-list__heading fleet-list__heading--narrow">%s</h1>'
        '<h2 class="fleet-list__heading fleet-list__heading--wide">%s</h2>' % (text, text))


def list_panel_html(view, selected_id="", landing=False, with_frame=False):
    """The list of frames: a header (title, Add a frame, search from
    `SEARCH_FROM` frames), then the Live, Waiting and Retired groups. `landing`
    is the view with no frame chosen; `with_frame` says a frame shows beside it."""
    rows = view.rows
    add = ui_modal.trigger_html(
        fleet_page.ADD_DIALOG_ID,
        icon_html("icon-plus", 20) + "<span>%s</span>" % _t(fleet_page.ADD_TITLE),
        "fleet-add-button")
    search = ""
    empty = ""
    if len(rows) >= SEARCH_FROM:
        search = (
            '<div class="filter-bar fleet-search">%s</div>'
            % ui_filter.search_field_html(
                SEARCH_ID, i18n.t(_SEARCH) % len(rows), i18n.t(_SEARCH) % len(rows)))
        empty = ui_filter.filter_empty_html(
            i18n.t(_NO_MATCH), "", "", "data-filter-empty hidden")
    kinds = {k: [r for r in rows if r.kind == k] for k in (
        fleet_page.KIND_LIVE, fleet_page.KIND_PENDING, fleet_page.KIND_RETIRED)}
    body = (
        _group(_GROUP_LIVE, kinds[fleet_page.KIND_LIVE], view, selected_id, "live")
        + _group(_GROUP_PENDING, kinds[fleet_page.KIND_PENDING], view, selected_id, "pending")
        + _group(_GROUP_RETIRED, kinds[fleet_page.KIND_RETIRED], view, selected_id, "retired"))
    return (
        '<div class="fleet-list"><div class="fleet-list__head">'
        '<div class="fleet-list__title">%s%s</div>%s'
        '</div><div class="fleet-list__body">%s%s</div></div>') % (
            _heading_html(landing, with_frame), add, search, body, empty)


def switch_html(view, selected_id=""):
    """The frame switch of a phone: "All frames" (the list), then the live
    frames, the one in view first, at most `CHIP_LIMIT`. Retired and pending
    frames are not here. Plain links, no script."""
    live = live_rows(view)
    chosen = [r for r in live if r.frame_id == selected_id] + [
        r for r in live if r.frame_id != selected_id]
    chips = [
        '<a class="fleet-chip fleet-chip--all" href="%s">%s</a>' % (
            LIST_HREF, _esc(i18n.t(_ALL_FRAMES) % len(view.rows)))]
    for row in chosen[:CHIP_LIMIT]:
        current = row.frame_id == selected_id
        chips.append(
            '<a class="fleet-chip" href="%s"%s>%s<span class="fleet-chip__name">%s'
            "</span></a>" % (
                _esc(frame_href(row.frame_id)),
                ' aria-current="page"' if current else "",
                frame_status.status_dot_html(row), _esc(fleet_page.display_name(row))))
    return '<nav class="fleet-switch" aria-label="%s">%s</nav>' % (
        _t(_SWITCH_ARIA), "".join(chips))


def _seen_html(text):
    """The detail after the status word; its dot separator is hidden where the
    detail takes its own line."""
    return (' <span class="fleet-head__seen"><span class="fleet-head__dot" '
            'aria-hidden="true">·</span> %s</span>' % _esc(text))


def _state_line(row, view):
    """The dot, the status word and, for a frame that is not simply online,
    when it was last seen."""
    word = _status_word(row)
    seen = _seen(row, view)
    quiet = frame_status.frame_status(row).key == frame_status.KEY_UP_TO_DATE
    tail = "" if quiet or not seen else _seen_html(seen)
    if row.kind == fleet_page.KIND_RETIRED:
        who = (i18n.t(_BELONGED_TO) % row.owner_email if row.owner_email
               else fleet_page.owner_line(row))
        tail = _seen_html(who)
    return '<p class="fleet-head__state">%s<span>%s</span>%s</p>' % (
        frame_status.status_dot_html(row), _esc(word), tail)


def head_html(row, view):
    """The title block of the selected frame: its name, its state and, for a
    live frame, the two icon buttons (personal view, Rename)."""
    from companion.pages import frame_name_page
    name = fleet_page.display_name(row)
    buttons = ""
    if row.kind == fleet_page.KIND_LIVE:
        buttons = (
            '<div class="fleet-head__buttons">'
            '<a class="fleet-icon-button" href="/devices/%s/" title="%s" aria-label="%s">%s</a>'
            '<a class="fleet-icon-button" href="%s" title="%s" aria-label="%s" '
            'data-modal-open>%s</a></div>' % (
                _esc(row.frame_id), _t(fleet_page.ACTION_PERSONAL_VIEW),
                _esc(i18n.t(fleet_page.OPEN_PERSONAL_ARIA) % name),
                icon_html("icon-device", 20),
                _esc(frame_name_page.opener_href(row.frame_id)),
                _t(frame_name_page.ACTION_TEXT),
                _esc(i18n.t(frame_name_page.ACTION_ARIA) % name),
                icon_html("icon-pencil", 20)))
    dialog = ""
    if row.kind == fleet_page.KIND_LIVE:
        dialog = frame_name_page.dialog_html(
            row.frame_id, "" if row.name == row.frame_id else name, frame_href(row.frame_id))
    return (
        '<div class="fleet-head"><div class="fleet-head__text">'
        '<h1 class="fleet-head__title">%s</h1>%s</div>%s%s</div>') % (
            _esc(name), _state_line(row, view), buttons, dialog)


def title_head_html(title, sub=""):
    """A title block with the page's one `<h1>` and, when given, one line of
    plain text under it: the System view, and a frame with no fleet row (the
    legacy single frame). `title` and `sub` are already-safe markup."""
    line = '<p class="fleet-head__sub">%s</p>' % sub if sub else ""
    return (
        '<div class="fleet-head"><div class="fleet-head__text">'
        '<h1 class="fleet-head__title">%s</h1>%s</div></div>') % (title, line)


def plain_head_html(device):
    """The title block of a frame with no fleet row, named by its device."""
    return title_head_html(_esc(device.name))


def other_page_html(row, view):
    """The page of a pending or retired frame: its title and the one useful
    action (Re-activate with what happens next, or Pair frame)."""
    if row.kind == fleet_page.KIND_RETIRED:
        label = i18n.t(fleet_page.ACTION_REACTIVATE)
        action = ui_modal.trigger_html(
            fleet_page.slug("dlg-reactivate", row.frame_id), _esc(label),
            "fleet-action-button row__trailing")
        item = ui_groups.row(label, detail=i18n.t(_REACTIVATE_HINT), trailing_html=action)
        block = ui_groups.group(item, label=label, label_id="fleet-other-action")
    else:
        label = i18n.t(fleet_page.PAIR_SUBMIT)
        action = ui_modal.trigger_html(
            fleet_page.ADD_DIALOG_ID, _esc(label), "fleet-action-button row__trailing")
        item = ui_groups.row(label, detail=i18n.t(fleet_page.WAITING_FOR_PAIRING),
                             trailing_html=action)
        block = ui_groups.group(item, label=label, label_id="fleet-other-action")
    return head_html(row, view) + '<div class="fleet-other">%s</div>' % block
