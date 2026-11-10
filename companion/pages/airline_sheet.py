"""The airline sheet's data and vocabulary: what a row of the Airlines
table edits (the airline's name, shown with its callsign prefixes) and the
`data-view-panel-*` attribute names the shared dialog reads.

Pure helpers and constants only; the markup lives in `airline_table.py` and
`airlines_page.py`. A "sheet" exists for a built-in airline, one whose name
the built-in prefix table knows, and is identified in every form and route
by that BUILT-IN name, never by anything the browser could invent: the
server re-derives the airline's prefixes from it.

Artwork follows the name. Every image lookup in the app is keyed on the
airline name a flight is shown with, so a renamed airline looks for the
new name's artwork. A rename therefore copies the current artwork to the
new key when that key has none (`companion/post_actions.py`), and the row
shows and edits the artwork of the name flights now carry.
"""
from companion import airline_display
from server.plane import enrich, illustrations, name_overrides

RENAME_ROUTE = "/airlines/rename"
RENAME_RESET_ROUTE = "/airlines/rename/reset"
ARTWORK_DELETE_ROUTE = "/airlines/artwork/delete"
DEFAULT_TYPE_ROUTE = "/airlines/default-type"
SHEET_QUERY_PARAM = "sheet"

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

FLASH_RENAMED = "airline_renamed"
FLASH_RENAME_RESET = "airline_rename_reset"
FLASH_RENAME_STALE = "airline_rename_stale"
FLASH_RENAME_FULL = "airline_rename_full"
FLASH_RENAME_TAKEN = "airline_rename_taken"
FLASH_RENAME_SAVE_FAILED = "airline_rename_save_failed"
FLASH_ARTWORK_DELETED = "airline_artwork_deleted"
FLASH_ARTWORK_STALE = "airline_artwork_stale"
FLASH_ARTWORK_DELETE_FAILED = "airline_artwork_delete_failed"
FLASH_DEFAULT_TYPE_SAVED = "airline_default_type_saved"
FLASH_DEFAULT_TYPE_FAILED = "airline_default_type_failed"
# The refusals a reopened sheet answers with focus on the name field: the
# owner has to change what they typed.
NAME_REFUSAL_FLASHES = (
    "manual_name_empty", "manual_name_too_long", "manual_name_reserved",
    "manual_name_unusable", FLASH_RENAME_TAKEN,
)



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
        sheet["builtin"], airline_display.shown_name(sheet["name"]), " ".join(sheet["prefixes"]),
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


def artwork_shapes(builtin_name):
    """The aircraft-shape slugs the curated list carries artwork for under
    `builtin_name` (empty for a name it does not list)."""
    return list(dict(illustrations.target_variants_by_airline()).get(builtin_name, []))
