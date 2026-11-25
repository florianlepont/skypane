"""Row markup of the Airlines editor that the table assembles.

An unidentified prefix is one compact row: the prefix, what was seen on its
second line and a "Name it" button. The name is typed in a dialog (a centred
card on desktop, a bottom sheet on a phone, see `ui_modal`) that posts to the
resolve route, so the keyboard never hides the field and the row never
carries an edit form of its own. An airline's row shows its name as plain
text; "Rename" in its "..." menu opens the same kind of dialog and posts to
the rename route. Nothing here stores anything: every form posts to a route
of the editor, and every stored text reaches the markup through
`escape_html` (or `ui_modal`, which escapes its own arguments).

The filter kinds a row can carry for the chips above the table are
defined here too: a row's `data-filter-kind` holds the space-separated kinds
it belongs to and `list-filter.js` matches one chip against that list.
"""
from dataclasses import dataclass

import companion.i18n as i18n
import companion.ui_modal as ui_modal
from companion.layout import escape_html, icon_html
from companion.ui_base import validation_attrs

NAME_IT_TEXT = i18n.msg("airlines.name_it", "Name it")
NAME_IT_ARIA = i18n.msg("airlines.name_it_aria", "Name the prefix %s")
NAME_IT_TITLE = i18n.msg("airlines.name_it_title", "Name the airline")
NAME_IT_HINT = i18n.msg(
    "airlines.name_it_hint", "Its aircraft types come from the flights seen.")
DIALOG_CANCEL = i18n.msg("airlines.dialog_cancel", "Cancel")
DIALOG_SAVE = i18n.msg("airlines.dialog_save", "Save")
MENU_RENAME = i18n.msg("airlines.menu_rename", "Rename")
RENAME_TITLE = i18n.msg("airlines.rename_title", "Rename the airline")
RENAME_HINT = i18n.msg(
    "airlines.rename_hint",
    "The new name replaces the original on the companion and on the frame.")
RENAME_MANUAL_HINT = i18n.msg(
    "airlines.rename_manual_hint",
    "The new name applies to every frame. Flights already stored keep their name.")
NAME_ARIA = i18n.msg("airlines.name_aria", "Airline name: %s")
NAME_PLACEHOLDER = i18n.msg("airlines.resolve_name_placeholder", "Airline name")
NAME_FOR_PREFIX_ARIA = i18n.msg(
    "airlines.resolve_name_aria", "Airline name for the prefix %s")
VALIDATE_TEXT = i18n.msg("airlines.resolve_validate", "Validate")
SUGGEST_TAG = i18n.msg("airlines.suggest_tag", "Suggestion")
SUGGEST_PENDING = i18n.msg("airlines.suggest_pending", "Looking for a name")
SUGGEST_EDIT = i18n.msg("airlines.suggest_edit", "Edit")
SUGGEST_EDIT_ARIA = i18n.msg("airlines.suggest_edit_aria", "Edit the suggested name for %s")
SUGGEST_USE_ARIA = i18n.msg("airlines.suggest_use_aria", "Use the suggestion %s for %s")
SUGGEST_EDIT_TITLE = i18n.msg("airlines.suggest_edit_title", "Edit the name")
SUGGEST_HINT = i18n.msg(
    "airlines.suggest_hint",
    "Suggested automatically from the callsign. Check it before using it.")
SUGGEST_REMOVE = i18n.msg("airlines.suggest_remove", "Remove the suggestion")
COL_DEFAULT_TYPE = i18n.msg("airlines.col_default_type", "Default type")
CHIP_ALL = i18n.msg("airlines.chip_all", "All")
CHIP_UNIDENTIFIED = i18n.msg("airlines.chip_unidentified", "Unidentified")
CHIP_MISSING = i18n.msg("airlines.chip_missing", "Missing illustrations")
CHIP_SEEN = i18n.msg("airlines.chip_seen", "Seen")
CHIP_NOT_SEEN = i18n.msg("airlines.chip_not_seen", "Not seen yet")
CHIPS_LEGEND = i18n.msg("airlines.chips_legend", "Filter the airlines")

KIND_UNIDENTIFIED = "unidentified"
KIND_MISSING = "missing"
KIND_SEEN = "seen"
KIND_NOT_SEEN = "unseen"

# The chip order and labels; the first chip (every row) carries the empty kind.
_CHIPS = (
    (KIND_UNIDENTIFIED, CHIP_UNIDENTIFIED), (KIND_MISSING, CHIP_MISSING),
    (KIND_SEEN, CHIP_SEEN), (KIND_NOT_SEEN, CHIP_NOT_SEEN))

KNOWN_NAMES_LIST_ID = "airlines-known-names"


def row_kinds(views):
    """The filter kind of an airline of the table (one with artwork): whether
    it was ever seen. An airline without artwork has no row in the table."""
    return KIND_SEEN if views else KIND_NOT_SEEN


def chips(counts, total):
    """The `(kind, label, count)` chips for `ui_filter.filter_bar_html`;
    `counts` maps a kind to the number of rows of that kind."""
    pairs = [("", i18n.t(CHIP_ALL), total)]
    for kind, label in _CHIPS:
        pairs.append((kind, i18n.t(label), counts.get(kind, 0)))
    return pairs


def chips_legend():
    return i18n.t(CHIPS_LEGEND)


def rename_dialog_id(index):
    return "rename-airline-%d" % index


def name_dialog_id(index):
    return "name-prefix-%d" % index


def rename_item_html(index):
    """The "Rename" entry of an airline's "..." menu: the link that opens its dialog."""
    return ui_modal.trigger_html(
        rename_dialog_id(index), escape_html(i18n.t(MENU_RENAME)), "row-menu__item")


def _name_field(name, aria, placeholder="", value=""):
    return (
        '<label class="field"><input type="text" name="%s" value="%s" maxlength="100" required '
        'autocomplete="off" placeholder="%s" aria-label="%s"%s></label>'
    ) % (name, escape_html(value), escape_html(placeholder), escape_html(aria),
         validation_attrs("text"))


def _rename_dialog(index, identity, name, action, csrf_html, dismiss_href, hint, open_):
    """One rename dialog: the airline's name in one field and the hidden
    `identity` field `(field name, value)` saying which airline it renames."""
    aria = i18n.t(NAME_ARIA) % name
    body = '<input type="hidden" name="%s" value="%s">%s' % (
        identity[0], escape_html(identity[1]), _name_field("airline_name", aria, value=name))
    return ui_modal.dialog_html(
        rename_dialog_id(index), i18n.t(RENAME_TITLE), action, csrf_html, body,
        i18n.t(DIALOG_SAVE), i18n.t(DIALOG_CANCEL), dismiss_href,
        subtitle=i18n.t(hint), open_=open_, secondary_dismiss=True)


def rename_dialog_html(index, builtin, name, action, csrf_html, dismiss_href, open_=False):
    """The dialog behind "Rename": the airline's name in one field, posted to
    the rename route with the airline's built-in name."""
    return _rename_dialog(
        index, ("airline", builtin), name, action, csrf_html, dismiss_href, RENAME_HINT, open_)


def manual_rename_dialog_html(index, prefix, name, action, csrf_html, dismiss_href, open_=False):
    """The same dialog for an airline the owner named by hand: it posts the
    stored prefix, and says the new name applies to the whole fleet."""
    return _rename_dialog(
        index, ("prefix", prefix), name, action, csrf_html, dismiss_href, RENAME_MANUAL_HINT, open_)


@dataclass(frozen=True)
class Suggestion:
    """What an unidentified row shows besides "Name it": a proposed `name`
    (with the `reject_action` its dialog posts the removal to), or, with an
    empty name, the pending state the script resolves by posting to
    `ask_action`."""
    name: str = ""
    reject_action: str = ""
    ask_action: str = ""


def _suggest_tag_html(suggestion):
    if suggestion.name:
        return '<span class="airlines-tag">%s%s</span>' % (
            icon_html("icon-spark", 14), escape_html(i18n.t(SUGGEST_TAG)))
    return (
        '<span class="airlines-tag airlines-tag--pending" role="status">'
        '<span class="airlines-tag__dot is-breathing" aria-hidden="true"></span>%s</span>'
    ) % escape_html(i18n.t(SUGGEST_PENDING))


def _check_form_html(prefix, name, action, csrf_html):
    """The round check: a real form to the resolve route, so naming works
    without script and goes through the same validation as typing the name."""
    label = i18n.t(SUGGEST_USE_ARIA) % (name, prefix)
    return (
        '<form method="post" action="%s" class="airlines-gap__check">%s'
        '<input type="hidden" name="prefix" value="%s">'
        '<input type="hidden" name="inline" value="1">'
        '<input type="hidden" name="airline_name" value="%s">'
        '<button type="submit" class="airlines-check" aria-label="%s" title="%s">%s</button></form>'
    ) % (escape_html(action), csrf_html, escape_html(prefix), escape_html(name),
         escape_html(label), escape_html(label), icon_html("icon-check", 22))


def _name_dialog_html(index, prefix, action, csrf_html, dismiss_href, suggestion):
    """The dialog behind "Name it" or, for a suggestion, "Edit": the name
    field (prefilled with the suggestion and a note that it was made
    automatically) and, for a suggestion, the action that removes it."""
    field = _name_field(
        "airline_name", i18n.t(NAME_FOR_PREFIX_ARIA) % prefix, i18n.t(NAME_PLACEHOLDER),
        suggestion.name if suggestion else "").replace(
            "<input ", '<input list="%s" ' % KNOWN_NAMES_LIST_ID, 1)
    body = (
        '<input type="hidden" name="prefix" value="%s">'
        '<input type="hidden" name="inline" value="1">%s'
    ) % (escape_html(prefix), field)
    if not (suggestion and suggestion.name):
        return ui_modal.dialog_html(
            name_dialog_id(index), "%s · %s" % (prefix, i18n.t(NAME_IT_TITLE)), action,
            csrf_html, body, i18n.t(VALIDATE_TEXT), i18n.t(DIALOG_CANCEL), dismiss_href,
            subtitle=i18n.t(NAME_IT_HINT), secondary_dismiss=True)
    body += '<p class="airlines-hint">%s<span>%s</span></p>' % (
        icon_html("icon-info", 18), escape_html(i18n.t(SUGGEST_HINT)))
    remove = (
        '<button type="submit" class="btn btn--ghost airlines-remove" formaction="%s" '
        'formnovalidate>%s</button>'
    ) % (escape_html(suggestion.reject_action), escape_html(i18n.t(SUGGEST_REMOVE)))
    return ui_modal.dialog_html(
        name_dialog_id(index), "%s · %s" % (prefix, i18n.t(SUGGEST_EDIT_TITLE)), action,
        csrf_html, body, i18n.t(VALIDATE_TEXT), i18n.t(DIALOG_CANCEL), dismiss_href,
        secondary_dismiss=True, extra_action_html=remove)


def _gap_row_parts(index, prefix, meta_html, action, csrf_html, suggestion):
    """`(body, actions)` of the row: the second line, with the tag and name
    above it for a suggestion or a pending lookup, and the controls at the
    end (Edit and the check, or Name it)."""
    meta = '<span class="airlines-gap__meta">%s</span>' % meta_html
    suggested = suggestion is not None and suggestion.name
    if suggestion is None:
        top = ""
    elif suggested:
        top = '<span class="airlines-gap__top">%s<span class="airlines-gap__name">%s</span></span>' % (
            _suggest_tag_html(suggestion), escape_html(suggestion.name))
    else:
        top = '<span class="airlines-gap__top">%s</span>' % _suggest_tag_html(suggestion)
    if suggested:
        edit = ui_modal.trigger_html(
            name_dialog_id(index), escape_html(i18n.t(SUGGEST_EDIT)), "airlines-gap__edit",
            aria_label=i18n.t(SUGGEST_EDIT_ARIA) % prefix)
        actions = '<span class="airlines-gap__actions">%s%s</span>' % (
            edit, _check_form_html(prefix, suggestion.name, action, csrf_html))
    else:
        actions = ui_modal.trigger_html(
            name_dialog_id(index), escape_html(i18n.t(NAME_IT_TEXT)), "btn btn--secondary",
            aria_label="%s: %s" % (i18n.t(NAME_IT_TEXT), i18n.t(NAME_IT_ARIA) % prefix))
    return top + meta, actions


def gap_group_html(index, prefix, meta_html, filter_text, action, csrf_html, dismiss_href,
                   suggestion=None):
    """One unidentified prefix as a `<tbody>`: a compact row with its "Name it"
    button and, in the same cell, the dialog that names it (the resolve route
    with `inline`, so the editor comes back with the row identified).
    `meta_html` is the caller's already-escaped second line. A `suggestion`
    adds the tag and name with Edit and the check in place of "Name it", or
    the pending marker the suggestion script looks for."""
    dialog = _name_dialog_html(index, prefix, action, csrf_html, dismiss_href, suggestion)
    body, actions = _gap_row_parts(index, prefix, meta_html, action, csrf_html, suggestion)
    pending = ""
    if suggestion is not None and not suggestion.name:
        pending = ' data-suggest-prefix="%s" data-suggest-index="%d" data-suggest-url="%s"' % (
            escape_html(prefix), index, escape_html(suggestion.ask_action))
    return (
        '<tbody class="airline-group airline-group--gap" data-filter-text="%s" '
        'data-filter-group="gap%d" data-filter-kind="%s"%s><tr class="airlines-row airlines-row--gap">'
        '<th scope="row" colspan="6" class="airlines-cell airlines-cell--resolve">'
        '<div class="airlines-gap%s"><span class="airlines-gap__prefix mono">%s</span>'
        '<span class="airlines-gap__body">%s</span>%s</div>%s</th></tr></tbody>'
    ) % (escape_html(filter_text), index, KIND_UNIDENTIFIED, pending,
         " airlines-gap--suggest" if suggestion is not None else "", escape_html(prefix),
         body, actions, dialog)
