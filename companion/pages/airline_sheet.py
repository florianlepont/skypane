"""The airline sheet's data and vocabulary: what the pencil on an Airlines
tile opens, so the owner edits an airline's name, sees its callsign
prefixes and replaces its artwork in one place.

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
# data-view-panel-* attributes. Every trigger carries all five, empty
# where unused, so a click can never inherit the previous card's values.
AIRLINE_ATTR = "data-view-panel-airline"
AIRLINE_NAME_ATTR = "data-view-panel-airline-name"
AIRLINE_PREFIXES_ATTR = "data-view-panel-airline-prefixes"
RENAMED_ATTR = "data-view-panel-renamed"
SHEET_KEY_ATTR = "data-view-panel-sheet-key"
SHEET_ATTRS = (AIRLINE_ATTR, AIRLINE_NAME_ATTR, AIRLINE_PREFIXES_ATTR, RENAMED_ATTR, SHEET_KEY_ATTR)
RENAMED_ACTIVE = "active"
EMPTY_ATTR_VALUES = ("", "", "", "", "")

FLASH_RENAMED = "airline_renamed"
FLASH_RENAME_RESET = "airline_rename_reset"
FLASH_RENAME_STALE = "airline_rename_stale"
FLASH_RENAME_FULL = "airline_rename_full"
FLASH_RENAME_SAVE_FAILED = "airline_rename_save_failed"

SHEET_HEADING_TEMPLATE = i18n.msg("airlines.edit_airline", "Edit %s")
SHEET_NAME_HINT = i18n.msg(
    "airlines.new_flights_use_this_name",
    "Shown on every past and new flight with these prefixes.")
SHEET_SAVE_TEXT = i18n.msg("airlines.save_name", "Save name")
SHEET_PREFIXES_LABEL = i18n.msg("airlines.callsign_prefixes", "Callsign prefixes")
SHEET_PREFIXES_HINT = i18n.msg(
    "airlines.built_in_prefixes_are_fixed",
    "Built into SkyPane, so they can’t be changed here.")
SHEET_RESET_TEXT = i18n.msg("airlines.reset_to_skypane_s_name", "Reset to SkyPane’s name")
SHEET_RESET_CAPTION_TEMPLATE = i18n.msg(
    "airlines.skypane_s_own_name_for_this_airline",
    "SkyPane’s own name for this airline is “%s”.")
SHEET_ARTWORK_LABEL = i18n.msg("airlines.artwork", "Artwork")
RENAMED_CHIP_TEXT = i18n.msg("airlines.renamed", "Renamed")


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


def attr_values(sheet, sheet_key):
    """The five trigger attribute values, in `SHEET_ATTRS` order, for a
    card with `sheet` (or none) on the slide whose artwork key is
    `sheet_key`. Unescaped; the caller escapes once at interpolation."""
    if sheet is None:
        return EMPTY_ATTR_VALUES
    return (
        sheet["builtin"], sheet["name"], " ".join(sheet["prefixes"]),
        RENAMED_ACTIVE if sheet["renamed"] else "", sheet_key,
    )


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


def sheet_html(values, id_suffix, datalist_id, name_label, in_dialog):
    """The airline sheet: name form, read-only prefix chips, the reset form
    and the artwork label that heads the upload form after it. One
    definition, two call sites: the shared dialog (`in_dialog`, values all
    empty, panel-lookup.js fills every field per click) and the no-script
    in-page section (values real, the reset form only when renamed).

    `values` is `attr_values()`'s tuple; `name_label` is the already-translated
    label of the name field and `datalist_id` the id of a datalist in the page. The prefix chips and
    the reset caption are real text here; in the dialog the script rewrites
    them with `textContent` from the trigger's attributes.
    """
    builtin, name, prefixes, renamed, _sheet_key = values
    name_id = SHEET_NAME_INPUT_ID + id_suffix
    chips = "".join(
        '<li class="airline-card__chip mono">%s</li>' % escape_html(prefix)
        for prefix in prefixes.split())
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
        '<section class="%s" id="%s" data-sheet-title-template="%s">'
        '<form class="airline-sheet__name" id="%s" method="post" action="%s">'
        '<input type="hidden" name="airline" value="%s">'
        '<label for="%s">%s</label>'
        '<input type="text" id="%s" name="airline_name" list="%s" maxlength="100" '
        'required autocomplete="off" value="%s">'
        '<p class="text-label section-caption">%s</p>'
        '<button type="submit">%s</button>'
        "</form>"
        '<div class="airline-sheet__prefixes">'
        '<p class="text-label">%s</p><ul class="airline-sheet__chips">%s</ul>'
        '<p class="text-label section-caption">%s</p></div>'
        "%s"
        '<p class="text-label airline-sheet__artwork-label">%s</p>'
        "</section>"
    ) % (
        SHEET_CLASS, "airline-sheet-body" + id_suffix,
        escape_html(i18n.t(SHEET_HEADING_TEMPLATE) % "#"),
        SHEET_RENAME_FORM_ID + id_suffix, RENAME_ROUTE,
        escape_html(builtin),
        name_id, name_label,
        name_id, datalist_id, escape_html(name),
        i18n.t(SHEET_NAME_HINT),
        i18n.t(SHEET_SAVE_TEXT),
        i18n.t(SHEET_PREFIXES_LABEL), chips,
        i18n.t(SHEET_PREFIXES_HINT),
        reset_form,
        i18n.t(SHEET_ARTWORK_LABEL),
    )
