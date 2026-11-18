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
import companion.i18n as i18n
import companion.ui_modal as ui_modal
from companion.layout import escape_html
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
UNIDENTIFIED_TEXT = i18n.msg("airlines.unidentified_label", "Unidentified")
NAME_ARIA = i18n.msg("airlines.name_aria", "Airline name: %s")
NAME_PLACEHOLDER = i18n.msg("airlines.resolve_name_placeholder", "Airline name")
NAME_FOR_PREFIX_ARIA = i18n.msg(
    "airlines.resolve_name_aria", "Airline name for the prefix %s")
VALIDATE_TEXT = i18n.msg("airlines.resolve_validate", "Validate")
COL_DEFAULT_TYPE = i18n.msg("airlines.col_default_type", "Default type")
CHIP_ALL = i18n.msg("airlines.chip_all", "All")
CHIP_UNIDENTIFIED = i18n.msg("airlines.chip_unidentified", "Unidentified")
CHIP_NO_ARTWORK = i18n.msg("airlines.chip_no_artwork", "No artwork")
CHIP_SEEN = i18n.msg("airlines.chip_seen", "Seen")
CHIP_NOT_SEEN = i18n.msg("airlines.chip_not_seen", "Not seen yet")
CHIPS_LEGEND = i18n.msg("airlines.chips_legend", "Filter the airlines")

KIND_UNIDENTIFIED = "unidentified"
KIND_NO_ARTWORK = "noart"
KIND_SEEN = "seen"
KIND_NOT_SEEN = "unseen"

# The chip order and labels; the first chip (every row) carries the empty kind.
_CHIPS = (
    (KIND_UNIDENTIFIED, CHIP_UNIDENTIFIED), (KIND_NO_ARTWORK, CHIP_NO_ARTWORK),
    (KIND_SEEN, CHIP_SEEN), (KIND_NOT_SEEN, CHIP_NOT_SEEN))

KNOWN_NAMES_LIST_ID = "airlines-known-names"


def row_kinds(has_art, views):
    """The filter kinds of an identified airline: its picture and whether it
    was ever seen."""
    kinds = [KIND_SEEN if views else KIND_NOT_SEEN]
    if not has_art:
        kinds.append(KIND_NO_ARTWORK)
    return " ".join(kinds)


def chips(counts, total):
    """The `(kind, label)` chips for `ui_filter.filter_bar_html`, each label
    followed by the number of rows of that kind; `counts` maps a kind to it."""
    pairs = [("", "%s (%d)" % (i18n.t(CHIP_ALL), total))]
    for kind, label in _CHIPS:
        pairs.append((kind, "%s (%d)" % (i18n.t(label), counts.get(kind, 0))))
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


def rename_dialog_html(index, builtin, name, action, csrf_html, dismiss_href, open_=False):
    """The dialog behind "Rename": the airline's name in one field, posted to
    the rename route with the airline's built-in name."""
    aria = i18n.t(NAME_ARIA) % name
    body = '<input type="hidden" name="airline" value="%s">%s' % (
        escape_html(builtin), _name_field("airline_name", aria, value=name))
    return ui_modal.dialog_html(
        rename_dialog_id(index), i18n.t(RENAME_TITLE), action, csrf_html, body,
        i18n.t(DIALOG_SAVE), i18n.t(DIALOG_CANCEL), dismiss_href,
        subtitle=i18n.t(RENAME_HINT), open_=open_, secondary_dismiss=True)


def gap_group_html(index, prefix, meta_html, filter_text, action, csrf_html, dismiss_href):
    """One unidentified prefix as a `<tbody>`: a compact row with its "Name it"
    button and, in the same cell, the dialog that names it (the resolve route
    with `inline`, so the editor comes back with the row identified).
    `meta_html` is the caller's already-escaped second line."""
    body = (
        '<input type="hidden" name="prefix" value="%s">'
        '<input type="hidden" name="inline" value="1">%s'
    ) % (escape_html(prefix), _name_field(
        "airline_name", i18n.t(NAME_FOR_PREFIX_ARIA) % prefix,
        i18n.t(NAME_PLACEHOLDER)).replace(
            "<input ", '<input list="%s" ' % KNOWN_NAMES_LIST_ID, 1))
    dialog = ui_modal.dialog_html(
        name_dialog_id(index), "%s · %s" % (prefix, i18n.t(NAME_IT_TITLE)), action,
        csrf_html, body, i18n.t(VALIDATE_TEXT), i18n.t(DIALOG_CANCEL), dismiss_href,
        subtitle=i18n.t(NAME_IT_HINT), secondary_dismiss=True)
    trigger = ui_modal.trigger_html(
        name_dialog_id(index), escape_html(i18n.t(NAME_IT_TEXT)), "btn btn--secondary",
        aria_label="%s: %s" % (i18n.t(NAME_IT_TEXT), i18n.t(NAME_IT_ARIA) % prefix))
    return (
        '<tbody class="airline-group airline-group--gap" data-filter-text="%s" '
        'data-filter-group="gap%d" data-filter-kind="%s"><tr class="airlines-row airlines-row--gap">'
        '<th scope="row" colspan="6" class="airlines-cell airlines-cell--resolve">'
        '<div class="airlines-gap"><span class="airlines-gap__prefix mono">%s</span>'
        '<span class="airlines-gap__body"><span class="airlines-gap-chip">%s</span>'
        '<span class="airlines-gap__meta">%s</span></span>%s</div>%s</th></tr></tbody>'
    ) % (escape_html(filter_text), index, KIND_UNIDENTIFIED, escape_html(prefix),
         escape_html(i18n.t(UNIDENTIFIED_TEXT)), meta_html, trigger, dialog)
