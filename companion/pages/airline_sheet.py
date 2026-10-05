"""The airline sheet's data and vocabulary: what a row on the Airlines
page opens, so the owner edits an airline's name, sees its callsign
prefixes and replaces its artwork, one aircraft type at a time, in one
place.

Pure helpers and constants only; the markup lives in `airlines_page.py`
beside the forms it reuses. A "sheet" exists for a built-in airline, one
whose name the built-in prefix table knows, and is identified in every
form and route by that BUILT-IN name, never by anything the browser
could invent: the server re-derives the airline's prefixes from it.

Artwork follows the name. Every image lookup in the app is keyed on the
airline name a flight is shown with, so a renamed airline looks for the
new name's artwork. A rename therefore copies the current
artwork to the new key when that key has none (`companion/post_actions.py`),
and the tile shows and edits the artwork of the name flights now carry.
"""
import companion.i18n as i18n
from companion.layout import escape_html
from server.plane import enrich, illustrations, name_overrides

RENAME_ROUTE = "/airlines/rename"
RENAME_RESET_ROUTE = "/airlines/rename/reset"
SHEET_QUERY_PARAM = "sheet"
SHEET_ANCHOR_ID = "airline-sheet"

# The trigger vocabulary this sheet adds to panel-lookup.js's
# data-view-panel-* attributes. Every trigger carries all six, empty
# where unused, so a click can never inherit the previous card's values.
AIRLINE_ATTR = "data-view-panel-airline"
AIRLINE_NAME_ATTR = "data-view-panel-airline-name"
AIRLINE_PREFIXES_ATTR = "data-view-panel-airline-prefixes"
RENAMED_ATTR = "data-view-panel-renamed"
SHEET_KEY_ATTR = "data-view-panel-sheet-key"
# The aircraft types of the row, as `key:label` items joined by "|", the
# type this trigger shows prefixed with "*". Independent of the sheet: an
# owner-named airline (no sheet) still names its one type here.
TYPES_ATTR = "data-view-panel-airline-types"
SHEET_ATTRS = (
    AIRLINE_ATTR, AIRLINE_NAME_ATTR, AIRLINE_PREFIXES_ATTR, RENAMED_ATTR, SHEET_KEY_ATTR,
    TYPES_ATTR)
RENAMED_ACTIVE = "active"
EMPTY_ATTR_VALUES = ("", "", "", "", "", "")
TYPES_ITEM_SEP = "|"
TYPES_KEY_SEP = ":"
TYPES_CURRENT_MARK = "*"
TYPES_NAV_CLASS = "airline-sheet__types"
TYPES_ITEM_CLASS = "airline-sheet__type"

FLASH_RENAMED = "airline_renamed"
FLASH_RENAME_RESET = "airline_rename_reset"
FLASH_RENAME_STALE = "airline_rename_stale"
FLASH_RENAME_FULL = "airline_rename_full"
FLASH_RENAME_TAKEN = "airline_rename_taken"
FLASH_RENAME_SAVE_FAILED = "airline_rename_save_failed"
# The refusals a reopened sheet answers with focus on the name field: the
# owner has to change what they typed.
NAME_REFUSAL_FLASHES = (
    "manual_name_empty", "manual_name_too_long", "manual_name_reserved",
    "manual_name_unusable", FLASH_RENAME_TAKEN,
)

SHEET_SAVE_TEXT = i18n.msg("airlines.save_name", "Save name")
SHEET_PREFIXES_LABEL = i18n.msg("airlines.callsign_prefixes", "Callsign prefixes")
SHEET_RESET_TEXT = i18n.msg("airlines.reset_to_skypane_s_name", "Reset to SkyPane’s name")
SHEET_RESET_CAPTION_TEMPLATE = i18n.msg(
    "airlines.skypane_s_own_name_for_this_airline",
    "SkyPane’s own name for this airline is “%s”.")


def card_sheet(builtin_name, overrides):
    """The sheet's facts for the curated airline `builtin_name`, or `None`
    when the built-in table has no prefix for it (nothing to rename by).

    `{"builtin": name, "name": the name flights now carry, "prefixes":
    sorted built-in prefixes, "renamed": bool}`. The name is the owner's
    override for the airline's first overridden prefix. Never raises.
    """
    prefixes = enrich.static_prefixes_for_name(builtin_name)
    if not prefixes:
        return None
    shown = None
    for prefix in prefixes:
        shown = name_overrides.name_for_prefix(prefix, overrides)
        if shown:
            break
    renamed = bool(shown) and shown != builtin_name
    return {
        "builtin": builtin_name, "name": shown if renamed else builtin_name,
        "prefixes": prefixes, "renamed": renamed,
    }


def attr_values(sheet, sheet_key, types_value=""):
    """The six trigger attribute values, in `SHEET_ATTRS` order, for a
    card with `sheet` (or none) on the slide whose artwork key is
    `sheet_key`; `types_value` is `types_attr_value()`'s string. Unescaped;
    the caller escapes once at interpolation."""
    if sheet is None:
        return EMPTY_ATTR_VALUES[:-1] + (types_value,)
    return (
        sheet["builtin"], sheet["name"], " ".join(sheet["prefixes"]),
        RENAMED_ACTIVE if sheet["renamed"] else "", sheet_key, types_value,
    )


def types_attr_value(types, current_key):
    """`TYPES_ATTR`'s value for the `(key, label)` pairs `types`, with the
    one whose key is `current_key` marked. Keys are artwork slugs and
    labels aircraft designators, so neither holds a separator."""
    return TYPES_ITEM_SEP.join(
        "%s%s%s%s" % (
            TYPES_CURRENT_MARK if key == current_key else "", key, TYPES_KEY_SEP, label)
        for key, label in types)


def sheet_href(airlines_route, sheet_key):
    """The no-script address of the sheet for the slide `sheet_key`."""
    return "%s?%s=%s#%s" % (airlines_route, SHEET_QUERY_PARAM, sheet_key, SHEET_ANCHOR_ID)


def artwork_shapes(builtin_name):
    """The aircraft-shape slugs the curated list carries artwork for under
    `builtin_name` (empty for a name it does not list)."""
    return list(dict(illustrations.target_variants_by_airline()).get(builtin_name, []))


SHEET_NAME_INPUT_ID = "airline-sheet-name"
SHEET_RENAME_FORM_ID = "airline-rename-form"
SHEET_CLASS = "airline-sheet"
SHEET_HEAD_CLASS = "airline-sheet__head"
SHEET_CHIPS_CLASS = "airline-sheet__chips"


def chips_html(prefixes, aria_label):
    """The read-only prefix chips, quiet, beside the title. `prefixes` is
    the space-joined text; empty gives an empty list (the dialog's copy,
    which panel-lookup.js fills per open). Not touch targets."""
    chips = "".join(
        '<li class="airline-card__chip mono">%s</li>' % escape_html(prefix)
        for prefix in prefixes.split())
    return '<ul class="%s" aria-label="%s">%s</ul>' % (
        SHEET_CHIPS_CLASS, escape_html(aria_label), chips)


def head_html(title_html, prefixes):
    """The sheet's one title with the airline's callsign prefixes as quiet
    chips beside it. `title_html` is the finished heading element: the
    shared dialog's own, or the in-page section's."""
    return '<div class="%s">%s%s</div>' % (
        SHEET_HEAD_CLASS, title_html, chips_html(prefixes, i18n.t(SHEET_PREFIXES_LABEL)))


def types_nav_html(types, current_key, href_for, aria_label):
    """The aircraft-type switcher for the in-page (no script) sheet: one
    link per `(key, label)` in `types`, the shown one `aria-current`. A
    single type is a plain label, not a link to itself. The dialog's copy
    is empty and filled by panel-lookup.js with the same structure."""
    if len(types) == 1:
        items = '<span class="%s" aria-current="true">%s</span>' % (
            TYPES_ITEM_CLASS, escape_html(types[0][1]))
    else:
        items = "".join(
            '<a class="%s" href="%s"%s>%s</a>' % (
                TYPES_ITEM_CLASS, escape_html(href_for(key)),
                ' aria-current="true"' if key == current_key else "", escape_html(label))
            for key, label in types)
    return '<nav class="%s" aria-label="%s">%s</nav>' % (
        TYPES_NAV_CLASS, escape_html(aria_label), items)


def sheet_html(values, id_suffix, name_label, in_dialog, focus_name=False):
    """The airline sheet's editing half: the name form and, for a renamed
    airline, the reset form. One definition, two call sites: the shared
    dialog (`in_dialog`, values all empty, panel-lookup.js fills every
    field per click) and the no-script in-page section (values real, the
    reset form only when renamed). The title, prefixes, picture, type
    switcher and upload zone sit above it.

    `values` is `attr_values()`'s tuple and `name_label` the already-translated
    label of the name field. The name field offers no datalist: suggesting
    other airlines' names would only invite a refused rename. The reset
    caption is real text here; in the dialog the script rewrites it with
    `textContent` from the trigger's attributes.

    Opening the sheet must not raise the phone keyboard, so the field is
    never `autofocus`ed, except in the no-script copy when `focus_name`
    says a refused rename reopened it (the owner has to fix the name).
    """
    builtin, name, _prefixes, renamed, _sheet_key, _types = values
    name_id = SHEET_NAME_INPUT_ID + id_suffix
    reset_caption = (
        i18n.t(SHEET_RESET_CAPTION_TEMPLATE) % escape_html(builtin)
        if builtin else "")
    reset_form = (
        '<form class="airline-sheet__reset" method="post" action="%s">'
        '<input type="hidden" name="airline" value="%s">'
        '<p class="text-label section-caption" data-sheet-reset-template="%s">%s</p>'
        '<button type="submit">%s</button>'
        "</form>"
    ) % (
        RENAME_RESET_ROUTE, escape_html(builtin),
        escape_html(i18n.t(SHEET_RESET_CAPTION_TEMPLATE) % "#"), reset_caption,
        i18n.t(SHEET_RESET_TEXT))
    if not in_dialog and not renamed:
        reset_form = ""
    return (
        '<section class="%s" id="%s">'
        '<form class="airline-sheet__name" id="%s" method="post" action="%s">'
        '<input type="hidden" name="airline" value="%s">'
        '<label for="%s">%s</label>'
        '<input type="text" id="%s" name="airline_name" maxlength="100" '
        'required autocomplete="off"%s value="%s">'
        '<button type="submit">%s</button>'
        "</form>"
        "%s"
        "</section>"
    ) % (
        SHEET_CLASS, "airline-sheet-body" + id_suffix,
        SHEET_RENAME_FORM_ID + id_suffix, RENAME_ROUTE,
        escape_html(builtin),
        name_id, name_label,
        name_id, " autofocus" if focus_name and not in_dialog else "", escape_html(name),
        i18n.t(SHEET_SAVE_TEXT),
        reset_form,
    )
