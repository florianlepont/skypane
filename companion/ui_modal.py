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


_VARIANT_CLASSES = {
    "": "modal",
    "compact": "modal modal--compact",
    "compact-top": "modal modal--compact modal--top",
}


def _dialog_classes(variant):
    if variant not in _VARIANT_CLASSES:
        raise ValueError("ui_modal: unknown dialog variant %r" % (variant,))
    return _VARIANT_CLASSES[variant]


def _head_html(slug, title, subtitle, href, title_attrs, title_only):
    """The dialog's header: the title, then the subtitle and the close cross
    (`href` is already escaped), or the title alone for a compact dialog."""
    heading = (
        '<h2 class="modal__title text-heading" id="%s-title"%s>%s</h2>'
        % (slug, title_attrs, escape_html(title)))
    if title_only:
        return '<header class="modal__head">%s</header>' % heading
    subtitle_html = (
        '<p class="modal__subtitle text-label">%s</p>' % escape_html(subtitle)
        if subtitle else "")
    return (
        '<header class="modal__head"><div>%s%s</div>'
        '<a class="modal__close" href="%s" data-modal-close aria-label="%s">'
        '%s</a></header>' % (
            heading, subtitle_html, href,
            escape_html(i18n.t(_CLOSE_LABEL_TEXT)), icon_html("icon-close", size=20)))


def dialog_html(
        dialog_id, title, form_action, csrf_html, body_html, submit_label,
        dismiss_label, dismiss_href, destructive=False, confirm_only=False,
        open_=False, subtitle=None, focus_id=None, focus_title=False,
        return_on_close=False, return_focus_id=None, secondary_dismiss=False,
        extra_action_html="", variant="", scrim_close=False):
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
    `return_focus_id` names the control (by its `id`) that takes the focus when
    the dialog closes with no opener of its own to return to (a dialog the
    address opened); several ids separated by spaces name fallbacks, the
    first one on screen wins.
    `secondary_dismiss` draws the dismiss link as a secondary button under
    the submit button instead of a plain text link.
    `extra_action_html` (already escaped, empty by default) is a further
    control placed after the dismiss link in the action row, for a second
    submit button of the same form (one with its own `formaction`).
    `variant` is "compact" or "compact-top" for the short dialogs of the
    Users page: the title alone in the head (no close cross, no subtitle),
    even spacing, and the two buttons side by side with the dismiss first.
    "compact-top" sits in the upper part of a wide screen instead of its
    middle. The variant is a modifier class on that dialog only; every other
    dialog keeps its own spacing.
    `scrim_close` lets a tap outside close a dialog that holds a field (which
    otherwise ignores it so typed text is not lost): for a one-field dialog
    where cancelling discards.
    """
    slug = validated_slug(dialog_id)
    classes = _dialog_classes(variant)
    dismiss_class = (
        "modal__dismiss modal__dismiss--button"
        if secondary_dismiss or variant else "modal__dismiss")
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
    if scrim_close:
        dialog_attrs += " data-scrim-close"
    if return_focus_id:
        dialog_attrs += ' data-modal-return-focus="%s"' % escape_html(return_focus_id)
    submit_class = ' class="btn btn--danger"' if destructive else ""
    href = escape_html(dismiss_href)
    head_html = _head_html(
        slug, title, "" if variant else subtitle, href, title_attrs, bool(variant))
    return (
        '<dialog class="%(classes)s" id="%(id)s" aria-labelledby="%(title_id)s"%(open)s%(dialog_attrs)s>'
        '<form method="post" action="%(action)s">%(csrf)s'
        '%(head)s'
        '<div class="modal__body">%(body)s</div>'
        '<div class="modal__actions">'
        '<button type="submit"%(submit_class)s%(submit_focus)s>%(submit)s</button>'
        '<a class="%(dismiss_class)s" href="%(href)s" data-modal-close%(dismiss_focus)s>%(dismiss)s</a>'
        '%(extra_action)s</div></form></dialog>\n'
    ) % {
        "classes": classes,
        "id": slug,
        "title_id": title_id,
        "open": " open" if open_ else "",
        "dialog_attrs": dialog_attrs,
        "action": escape_html(form_action),
        "csrf": csrf_html,
        "head": head_html,
        "href": href,
        "body": body_html,
        "submit_class": submit_class,
        "submit_focus": submit_focus,
        "submit": escape_html(submit_label),
        "dismiss_focus": dismiss_focus,
        "dismiss_class": dismiss_class,
        "dismiss": escape_html(dismiss_label),
        "extra_action": extra_action_html,
    }


def result_dialog_html(
        dialog_id, title, body_html, done_label, dismiss_href, retry_form_html="",
        once=False):
    """A compact-top dialog, open, that reports the outcome of a submission:
    no form of its own, a Done link and optionally `retry_form_html` (an
    already-escaped form whose one submit button is the primary action).

    `once` is for a body that carries a one-time credential: the closing
    script removes the dialog from the page and puts `dismiss_href` in the
    address bar, so neither a reload nor the page itself holds the value
    afterwards. Done takes the initial focus so Enter never repeats the
    action."""
    slug = validated_slug(dialog_id)
    href = escape_html(dismiss_href)
    done_class = (
        "modal__dismiss modal__dismiss--button" if retry_form_html else "btn btn--primary")
    attrs = ' data-modal-return="%s"' % href
    if once:
        attrs += " data-modal-once"
    return (
        '<dialog class="modal modal--compact modal--top" id="%(id)s" '
        'aria-labelledby="%(id)s-title" open%(attrs)s>'
        '%(head)s<div class="modal__body">%(body)s</div>'
        '<div class="modal__actions">%(retry)s'
        '<a class="%(done_class)s modal__done" href="%(href)s" data-modal-close autofocus>'
        '%(done)s</a></div></dialog>\n'
    ) % {
        "id": slug, "attrs": attrs, "body": body_html, "retry": retry_form_html,
        "head": _head_html(slug, title, "", href, "", True),
        "done_class": done_class, "href": href, "done": escape_html(done_label),
    }


def choice_dialog_html(
        dialog_id, title, text, primary_label, secondary_label, quiet_label, hook_attr,
        alt_primary_label=None, note=None):
    """A modal dialog that asks a question and offers two actions plus a
    close cross, none of them a form post: a primary, a secondary and a
    quiet one (the cross at the top right) that closes the dialog and
    changes nothing. `quiet_label` is the cross's accessible name.

    The dialog is closed in the markup and only a script opens it (it has no
    opener link): a page uses it where a script intercepts a navigation, and
    without script the page keeps its plain links. `hook_attr` is a lowercase
    slug; the controls carry `data-<hook_attr>-primary`, `-secondary` and
    `-quiet` for that script. The cross takes the initial focus so Enter
    never confirms the primary action unasked, and Escape closes the dialog
    as it does the cross. The two buttons share one row of equal width from
    700px up and stack below it (CSS: `.modal--choice`).

    `alt_primary_label` and `note` are for a script that sometimes cannot do
    what the primary promises: the primary carries the alternative label as
    `data-<hook_attr>-primary-alt` and the hidden note paragraph is
    `data-<hook_attr>-note`; the script swaps the label and shows the note."""
    slug = validated_slug(dialog_id)
    hook = validated_slug(hook_attr)
    title_id = slug + "-title"
    alt = (' data-%s-primary-alt="%s"' % (hook, escape_html(alt_primary_label))
           if alt_primary_label else "")
    note_html = ('<p class="text-label" data-%s-note hidden>%s</p>' % (hook, escape_html(note))
                 if note else "")
    return (
        '<dialog class="modal modal--choice" id="%(id)s" aria-labelledby="%(title_id)s" data-%(hook)s>'
        '<header class="modal__head"><div>'
        '<h2 class="modal__title text-heading" id="%(title_id)s">%(title)s</h2>'
        '</div>'
        '<button type="button" class="modal__close" data-%(hook)s-quiet data-modal-close '
        'autofocus aria-label="%(quiet)s">%(close_icon)s</button></header>'
        '<div class="modal__body"><p class="text-body">%(text)s</p>%(note)s</div>'
        '<div class="modal__actions">'
        '<button type="button" class="btn btn--primary" data-%(hook)s-primary%(alt)s>%(primary)s</button>'
        '<button type="button" class="btn btn--secondary" data-%(hook)s-secondary>%(secondary)s</button>'
        '</div></dialog>\n'
    ) % {
        "id": slug,
        "title_id": title_id,
        "hook": hook,
        "title": escape_html(title),
        "text": escape_html(text),
        "alt": alt,
        "note": note_html,
        "primary": escape_html(primary_label),
        "secondary": escape_html(secondary_label),
        "quiet": escape_html(quiet_label),
        "close_icon": icon_html("icon-close", size=20),
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
