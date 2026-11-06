"""companion/frame_menu.py: the frame button and its popover.

A glass button in the top bar of every device-scoped page (phone: the right
side of the app bar; desktop: the top right of the content area) names the
frame in view and opens a popover with one row per frame, then an "Add a
frame" row (and, in the Console, a "System" row). It replaces the strip of
tiles. The whole control is a native `<details>`, so it opens, closes and
every row navigates with no script; modal.js adds Escape, outside-tap and
focus return, and keeps `aria-expanded` in step.

Rows are plain links to the same page of each frame under its own
/devices/<id> prefix, built from the request scope's own frame list and
never from request text. A frame has no MAC, token or secret to leak.
"""
import contextvars

from companion import access, device_scope, frame_status, i18n, prefs
from companion.ui_base import escape_html

MENU_CLASS = "frame-menu"
ROW_CLASS = "frame-row"

_ARIA_TEXT = i18n.msg("nav.frame_strip_aria", "Your frames")
_SEEN_TEXT = i18n.msg("nav.frame_tile_seen", "Seen %s")
_ADD_TEXT = i18n.msg("nav.frame_tile_add", "Add a frame")
_SHARED_BY_TEXT = i18n.msg("account.shared_by", "Shared by %s")
_BUTTON_TEXT = i18n.msg("nav.frame_button", "Choose a frame")

# Where the Add a frame row leads: an administrator's pairing dialog on the
# Fleet page, anyone else's own Add a frame page.
_ADMIN_ADD_FRAME_HREF = "/fleet?pair=1"
_USER_ADD_FRAME_HREF = "/pair-frame"

# The Fleet page builds its own menu while it builds its body; the page shell
# reads it back when it draws the top bar.
_CONSOLE_MENU = contextvars.ContextVar("skypane_console_frame_menu", default=None)


def _shell():
    # Imported on use: companion.ui_shell imports this module.
    from companion import ui_shell
    return ui_shell


def _note(entry):
    """The muted owner line of a row: who shared the frame, or the owner of a
    frame the viewer does not own; "" for a frame of their own."""
    if entry.owner_email is None:
        return ""
    if entry.co_managed:
        return i18n.t(_SHARED_BY_TEXT) % entry.owner_email
    return entry.owner_email


def _seen_word(row, now):
    return _shell().seen_text(row, now)


def _check_html():
    return '<span class="%s__check" aria-hidden="true"></span>' % ROW_CLASS


def _frame_row_html(device, href, is_current, now, note=""):
    """One frame row: the CSS-drawn frame, the name, the last-seen word, the
    owner line when there is one, the status dot and, on the frame in view,
    a check. `href` is built by the caller from a fixed path and a validated
    frame id."""
    shell = _shell()
    row = shell._switcher_status_row(device, now)
    return (
        '<li><a class="%(cls)s" href="%(href)s"%(current)s>'
        '%(pic)s'
        '<span class="%(cls)s__text">'
        '<span class="%(cls)s__name">%(name)s</span>'
        '<span class="%(cls)s__seen">%(seen)s</span>%(note)s</span>'
        '<span class="%(cls)s__dot">%(dot)s</span>%(check)s</a></li>') % {
            "cls": ROW_CLASS,
            "pic": shell.frame_pic_html(ROW_CLASS),
            "href": escape_html(href),
            "current": ' aria-current="true"' if is_current else "",
            "dot": frame_status.status_dot_html(row),
            "name": escape_html(shell.device_display_name(device)),
            "seen": escape_html(_seen_word(row, now)),
            "note": (
                '<span class="%s__note">%s</span>' % (ROW_CLASS, escape_html(note))
                if note else ""),
            "check": _check_html() if is_current else "",
        }


def _action_row_html(modifier, href, label, glyph_html, detail="", is_current=False,
                     opener=False):
    return (
        '<li><a class="%(cls)s %(cls)s--%(mod)s" href="%(href)s"%(cur)s%(open)s>'
        '<span class="%(cls)s__icon" aria-hidden="true">%(glyph)s</span>'
        '<span class="%(cls)s__text"><span class="%(cls)s__name">%(label)s</span>'
        '%(detail)s</span>%(check)s</a></li>') % {
            "cls": ROW_CLASS, "mod": modifier, "href": escape_html(href),
            "cur": ' aria-current="true"' if is_current else "",
            "open": " data-modal-open" if opener else "",
            "glyph": glyph_html, "label": escape_html(label),
            "detail": (
                '<span class="%s__seen">%s</span>' % (ROW_CLASS, escape_html(detail))
                if detail else ""),
            "check": _check_html() if is_current else "",
        }


def add_row_html(admin=True, dialog_id=None):
    """The Add a frame row. With `dialog_id` it opens that dialog on the page
    (the Fleet page's pairing dialog; the hash link works without script);
    otherwise it leads to the administrator's Fleet pairing dialog or to
    everyone else's own Add a frame page."""
    if dialog_id is not None:
        from companion import ui_modal
        href = "#" + ui_modal.validated_slug(dialog_id)
    else:
        href = _ADMIN_ADD_FRAME_HREF if admin else _USER_ADD_FRAME_HREF
    return _action_row_html(
        "add", href, i18n.t(_ADD_TEXT), "+", opener=dialog_id is not None)


def _add_row_for_viewer(active):
    """The Add a frame row for the signed-in person, or "" with none: an
    administrator pairs from the Fleet page when on a Console page; everyone
    else, and an administrator in the personal space, from their own Add a
    frame page (the personal space is the same for both)."""
    principal = prefs.current_principal()
    if principal is None:
        return ""
    console = _shell().current_space(active) == _shell().CONSOLE_SPACE
    return add_row_html(admin=console and principal[1] == access.ADMIN)


def _button_html(name, dot_html):
    return (
        '<summary class="%(cls)s__button" aria-haspopup="true" title="%(hint)s">'
        '<span class="%(cls)s__dot">%(dot)s</span>'
        '<span class="%(cls)s__name">%(name)s</span>'
        '<span class="%(cls)s__chevron" aria-hidden="true"></span></summary>') % {
            "cls": MENU_CLASS, "dot": dot_html, "name": escape_html(name),
            "hint": escape_html(i18n.t(_BUTTON_TEXT))}


def menu_html(name, dot_html, frame_rows, tail_rows):
    """The `<details>` holding the button and the popover. `frame_rows` and
    `tail_rows` are prebuilt `<li>` markup; the tail sits under a separator."""
    return (
        '<details class="%(cls)s">%(button)s'
        '<div class="%(cls)s__panel"><ul class="%(cls)s__list" aria-label="%(aria)s">'
        '%(frames)s%(tail)s</ul></div></details>') % {
            "cls": MENU_CLASS, "button": _button_html(name, dot_html),
            "aria": escape_html(i18n.t(_ARIA_TEXT)), "frames": frame_rows,
            "tail": tail_rows.replace("<li>", '<li class="%s__tail">' % MENU_CLASS, 1)
            if tail_rows else ""}


def personal_menu_html(active):
    """The frame button of a device-scoped page, or "" when it would be out of
    place: a global page (Update, the airline editor), no request scope, or a
    single frame and no way to add another."""
    shell = _shell()
    page = shell._device_page_path(active)
    current = device_scope.current_device()
    if page is None or current is None:
        return ""
    now = device_scope.now_epoch()
    entries = shell._sheet_entries(active, now)
    tail = _add_row_for_viewer(active)
    if len(entries) < 2 and not tail:
        return ""
    # The owner line tells frames apart: a lone frame needs none.
    rows = "".join(
        _frame_row_html(
            e.device, device_scope.target_path(page, e.device),
            e.device.id == current.id, now, _note(e) if len(entries) > 1 else "")
        for e in entries)
    dot = frame_status.status_dot_html(shell._switcher_status_row(current, now))
    return menu_html(shell.device_display_name(current), dot, rows, tail)


def _system_row_html(href, is_current, label, detail):
    return _action_row_html(
        "system", href, label, "<i></i>", detail=detail, is_current=is_current)


def console_menu_html(entries, selected, is_system, system, add_dialog_id, frame_href):
    """The Fleet page's button: every frame of the platform (problems first),
    then "System" and "Add a frame". `system` is `(href, label, detail)`;
    `frame_href(device)` gives a frame's row link."""
    shell = _shell()
    now = device_scope.now_epoch()
    rows = "".join(
        _frame_row_html(
            e.device, frame_href(e.device),
            selected is not None and e.device.id == selected.id, now, _note(e))
        for e in shell.console_ordered(entries, now))
    tail = _system_row_html(system[0], is_system, system[1], system[2]) + add_row_html(
        dialog_id=add_dialog_id)
    if is_system:
        name, dot = system[1], ""
    elif selected is not None:
        name = shell.device_display_name(selected)
        dot = frame_status.status_dot_html(shell._switcher_status_row(selected, now))
    else:
        name, dot = i18n.t(_ADD_TEXT), ""
    return menu_html(name, dot, rows, tail)


def stash_console_menu(html):
    """Remember the Fleet page's button for the page shell of this request."""
    _CONSOLE_MENU.set(html)


def header_menu_html(active):
    """The button the shell draws in the top bar for the page `active`: the
    Fleet page's own (taken once), else the device-scoped one."""
    stashed = _CONSOLE_MENU.get()
    if stashed is not None and _shell()._device_page_path(active) is None:
        from companion import console_routes
        if active == _shell().nav_slug(console_routes.FLEET_ROUTE):
            _CONSOLE_MENU.set(None)
            return stashed
    return personal_menu_html(active)
