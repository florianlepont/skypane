"""companion/ui_modal.py: the shared modal dialog component.

A dialog is a native `<dialog class="modal">` rendered into the page next to
its host content, opened by a plain `<a href="#id" data-modal-open>` link.
With script, `static/modal.js` upgrades the link to `showModal()`; without
script the `:target` CSS shows the same dialog as an in-page card and the
form still posts normally. Every interpolated value is escaped here; the
only markup a caller supplies is `body_html`, `csrf_html` and `label_html`,
which the caller has already escaped.
"""
import re

import companion.i18n as i18n
from companion.ui_base import escape_html, icon_html

_CLOSE_LABEL_TEXT = i18n.msg("common.close", "Close")

# Dialog ids end up in `id=`, `href="#..."` and `aria-labelledby`, so they
# are restricted to a lowercase slug instead of being escaped into shape.
_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")

# The first form control that is not a hidden input, and the first one
# marked invalid; either takes the dialog's initial focus.
_CONTROL_RE = re.compile(r"<(?:input|select|textarea)\b[^>]*>")
_HIDDEN_RE = re.compile(r'\btype\s*=\s*"hidden"')
_INVALID_RE = re.compile(r'\baria-invalid\s*=\s*"true"')


def validated_slug(dialog_id):
    """`dialog_id` unchanged when it is a lowercase slug, else ValueError."""
    if not isinstance(dialog_id, str) or not _SLUG_RE.match(dialog_id):
        raise ValueError("ui_modal: dialog id %r is not a lowercase slug" % (dialog_id,))
    return dialog_id


def error_id(dialog_id, field):
    """The id of the `.field-error` paragraph for `field` inside a dialog."""
    return "%s-%s-error" % (validated_slug(dialog_id), validated_slug(field))


def field_error_html(dialog_id, field, message):
    """The `.field-error` paragraph a control's `aria-describedby` points at."""
    return '<p class="field-error" id="%s" role="alert">%s</p>' % (
        escape_html(error_id(dialog_id, field)), escape_html(message))


def trigger_html(dialog_id, label_html, extra_class="", aria_label=""):
    """The link that opens dialog `dialog_id`. A link rather than a button so
    the hash navigation works without script. `label_html` is pre-escaped;
    `aria_label` is plain text and overrides the visible label for assistive
    technology."""
    css = ' class="%s"' % escape_html(extra_class) if extra_class else ""
    aria = ' aria-label="%s"' % escape_html(aria_label) if aria_label else ""
    return '<a href="#%s"%s%s data-modal-open>%s</a>' % (
        validated_slug(dialog_id), css, aria, label_html)


def _autofocus_first_control(body_html):
    """`body_html` with ` autofocus` added to the invalid control if there is
    one, else to the first visible control. Returns (html, found)."""
    controls = [m for m in _CONTROL_RE.finditer(body_html)
                if not _HIDDEN_RE.search(m.group(0))]
    if not controls:
        return body_html, False
    chosen = next((m for m in controls if _INVALID_RE.search(m.group(0))), controls[0])
    tag = chosen.group(0)
    if "autofocus" not in tag:
        tag = tag[:-1].rstrip("/").rstrip() + " autofocus>"
    return body_html[:chosen.start()] + tag + body_html[chosen.end():], True


def _autofocus_named_control(body_html, focus_id):
    """`body_html` with ` autofocus` added to the control whose id is
    `focus_id`, unless a control is marked invalid: the invalid one takes
    the focus then, so a refused value is announced first. Returns
    (html, found); `found` is False when no such control exists."""
    controls = [m for m in _CONTROL_RE.finditer(body_html)
                if not _HIDDEN_RE.search(m.group(0))]
    named = next((m for m in controls
                  if 'id="%s"' % focus_id in m.group(0)), None)
    if named is None:
        return body_html, False
    chosen = next((m for m in controls if _INVALID_RE.search(m.group(0))), named)
    tag = chosen.group(0)
    if "autofocus" not in tag:
        tag = tag[:-1].rstrip("/").rstrip() + " autofocus>"
    return body_html[:chosen.start()] + tag + body_html[chosen.end():], True


def _autofocus_invalid_control(body_html):
    """`body_html` with ` autofocus` added to the invalid control, if any.
    Returns (html, found)."""
    invalid = next(
        (m for m in _CONTROL_RE.finditer(body_html)
         if _INVALID_RE.search(m.group(0)) and not _HIDDEN_RE.search(m.group(0))), None)
    if invalid is None:
        return body_html, False
    tag = invalid.group(0)
    if "autofocus" not in tag:
        tag = tag[:-1].rstrip("/").rstrip() + " autofocus>"
    return body_html[:invalid.start()] + tag + body_html[invalid.end():], True


def dialog_html(
        dialog_id, title, form_action, csrf_html, body_html, submit_label,
        dismiss_label, dismiss_href, destructive=False, confirm_only=False,
        open_=False, subtitle=None, focus_id=None, focus_title=False,
        return_on_close=False):
    """One modal dialog wrapping a POST form.

    `dismiss_href` is the host page path: the close and dismiss links go
    there, which clears the hash when script is off. A confirm-only dialog
    focuses its dismiss link first so Enter never confirms a destructive
    action; any other dialog focuses its invalid or first field, or the
    submit button when it has no field. `open_` renders the `open`
    attribute for a refused submission re-rendered with its errors.
    `focus_id` names the control (by its `id`) that takes the initial focus
    instead of the first one, for a dialog whose first control is a switch;
    an invalid control still wins, and a name that matches nothing is a
    ValueError. `focus_title` opens the dialog on its title instead of a
    field (a time or text field would raise the keyboard or the native
    picker unasked); an invalid control still takes the focus.
    `return_on_close` is for a dialog the address itself opened: closed in
    place, the address becomes `dismiss_href` so a reload does not ask again.
    """
    slug = validated_slug(dialog_id)
    title_id = slug + "-title"
    submit_focus = ""
    dismiss_focus = ""
    title_attrs = ""
    dialog_attrs = ""
    if focus_title and not confirm_only:
        body_html, found = _autofocus_invalid_control(body_html)
        if not found:
            title_attrs = ' tabindex="-1"'
            dialog_attrs = " data-focus-title"
    elif confirm_only:
        dismiss_focus = " autofocus"
    else:
        if focus_id is None:
            body_html, found = _autofocus_first_control(body_html)
        else:
            body_html, found = _autofocus_named_control(body_html, focus_id)
            if not found:
                raise ValueError("ui_modal: no control with id %r in the body" % (focus_id,))
        if not found:
            submit_focus = " autofocus"
    if return_on_close:
        dialog_attrs += ' data-modal-return="%s"' % escape_html(dismiss_href)
    submit_class = ' class="btn btn--danger"' if destructive else ""
    subtitle_html = (
        '<p class="modal__subtitle text-label">%s</p>' % escape_html(subtitle)
        if subtitle else "")
    close_text = escape_html(i18n.t(_CLOSE_LABEL_TEXT))
    href = escape_html(dismiss_href)
    return (
        '<dialog class="modal" id="%(id)s" aria-labelledby="%(title_id)s"%(open)s%(dialog_attrs)s>'
        '<form method="post" action="%(action)s">%(csrf)s'
        '<header class="modal__head"><div>'
        '<h2 class="modal__title text-heading" id="%(title_id)s"%(title_attrs)s>%(title)s</h2>'
        '%(subtitle)s</div>'
        '<a class="modal__close" href="%(href)s" data-modal-close aria-label="%(close)s">'
        '%(close_icon)s</a></header>'
        '<div class="modal__body">%(body)s</div>'
        '<div class="modal__actions">'
        '<button type="submit"%(submit_class)s%(submit_focus)s>%(submit)s</button>'
        '<a class="modal__dismiss" href="%(href)s" data-modal-close%(dismiss_focus)s>%(dismiss)s</a>'
        '</div></form></dialog>\n'
    ) % {
        "id": slug,
        "title_id": title_id,
        "open": " open" if open_ else "",
        "dialog_attrs": dialog_attrs,
        "title_attrs": title_attrs,
        "action": escape_html(form_action),
        "csrf": csrf_html,
        "title": escape_html(title),
        "subtitle": subtitle_html,
        "href": href,
        "close": close_text,
        "close_icon": icon_html("icon-close", size=20),
        "body": body_html,
        "submit_class": submit_class,
        "submit_focus": submit_focus,
        "submit": escape_html(submit_label),
        "dismiss_focus": dismiss_focus,
        "dismiss": escape_html(dismiss_label),
    }


def choice_dialog_html(
        dialog_id, title, text, primary_label, secondary_label, quiet_label, hook_attr,
        data_name=None, data_value=""):
    """A modal dialog that asks a question and offers three actions, none of
    them a form post: a primary, a secondary and a quiet one that closes the
    dialog and changes nothing.

    The dialog is closed in the markup and only a script opens it (it has no
    opener link): a page uses it where a script intercepts a navigation, and
    without script the page keeps its plain links. `hook_attr` is a lowercase
    slug; the buttons carry `data-<hook_attr>-primary`, `-secondary` and
    `-quiet` for that script. The quiet button takes the initial focus so
    Enter never confirms the primary action unasked, and Escape closes the
    dialog as it does the quiet button.

    `data_name` is an optional extra lowercase slug the dialog carries as
    `data-<data_name>="<data_value>"`, for a script that needs one
    server-decided list alongside the question."""
    slug = validated_slug(dialog_id)
    hook = validated_slug(hook_attr)
    title_id = slug + "-title"
    extra = (
        ' data-%s="%s"' % (validated_slug(data_name), escape_html(data_value))
        if data_name else "")
    return (
        '<dialog class="modal" id="%(id)s" aria-labelledby="%(title_id)s" data-%(hook)s%(extra)s>'
        '<header class="modal__head"><div>'
        '<h2 class="modal__title text-heading" id="%(title_id)s">%(title)s</h2>'
        '</div></header>'
        '<div class="modal__body"><p class="text-body">%(text)s</p></div>'
        '<div class="modal__actions">'
        '<button type="button" data-%(hook)s-primary>%(primary)s</button>'
        '<button type="button" class="btn btn--secondary" data-%(hook)s-secondary>%(secondary)s</button>'
        '<button type="button" class="btn btn--ghost" data-%(hook)s-quiet data-modal-close '
        'autofocus>%(quiet)s</button>'
        '</div></dialog>\n'
    ) % {
        "id": slug,
        "title_id": title_id,
        "hook": hook,
        "extra": extra,
        "title": escape_html(title),
        "text": escape_html(text),
        "primary": escape_html(primary_label),
        "secondary": escape_html(secondary_label),
        "quiet": escape_html(quiet_label),
    }


def sections_dialog_html(
        dialog_id, title, subtitle, sections_html, dismiss_label, dismiss_href,
        open_=False, extra_class=""):
    """A modal dialog whose body is several independent forms.

    Unlike `dialog_html` it wraps no form of its own: `sections_html` holds
    one `<form>` per section (the caller has already escaped it) and the
    dialog only offers a dismiss link. The first visible control takes the
    initial focus, or the dismiss link when the sections have none. `open_`
    renders the `open` attribute for a dialog reopened after a change.
    `extra_class` adds one slug class to the dialog for page-specific styling.
    """
    slug = validated_slug(dialog_id)
    classes = "modal " + validated_slug(extra_class) if extra_class else "modal"
    title_id = slug + "-title"
    sections_html, found = _autofocus_first_control(sections_html)
    dismiss_focus = "" if found else " autofocus"
    subtitle_html = (
        '<p class="modal__subtitle text-label">%s</p>' % escape_html(subtitle)
        if subtitle else "")
    href = escape_html(dismiss_href)
    return (
        '<dialog class="%(classes)s" id="%(id)s" aria-labelledby="%(title_id)s"%(open)s>'
        '<header class="modal__head"><div>'
        '<h2 class="modal__title text-heading" id="%(title_id)s">%(title)s</h2>'
        '%(subtitle)s</div>'
        '<a class="modal__close" href="%(href)s" data-modal-close aria-label="%(close)s">'
        '%(close_icon)s</a></header>'
        '<div class="modal__body">%(body)s</div>'
        '<div class="modal__actions">'
        '<a class="modal__dismiss" href="%(href)s" data-modal-close%(focus)s>%(dismiss)s</a>'
        '</div></dialog>\n'
    ) % {
        "classes": classes,
        "id": slug,
        "title_id": title_id,
        "open": " open" if open_ else "",
        "title": escape_html(title),
        "subtitle": subtitle_html,
        "href": href,
        "close": escape_html(i18n.t(_CLOSE_LABEL_TEXT)),
        "close_icon": icon_html("icon-close", size=20),
        "body": sections_html,
        "focus": dismiss_focus,
        "dismiss": escape_html(dismiss_label),
    }
