"""The Console Airlines editor as one table.

One `<tbody>` per airline: the airline's row (name edited in place, callsign
prefixes as read-only text, the artwork thumbnail that replaces the artwork
enlarged when tapped, views, last seen, a "..." menu) and, behind a native
`<details>` chevron, one sub-row per aircraft type seen for it. Every type
row is editable: it starts as "Same as the airline" and can take a picture of
its own, go back to the default, or be starred as the airline's default type.
Unidentified prefixes sit above as highlighted rows that are resolved in
place: a name field with suggestions, an optional default aircraft type, and
Validate / Ignore. A name typed by hand keeps its row, marked "Named by
hand". Below 70rem every row is a card.

Every control posts to a route of the editor: the rename and reset routes,
the illustration upload route, the manual-name delete route, the resolve
route, the artwork-delete route and the default-type route. Stored text
reaches the markup only through `escape_html`.
"""
from dataclasses import dataclass, field

import companion.airline_display as airline_display
import companion.device_scope as device_scope
import companion.i18n as i18n
import companion.illustration_normalize as illustration_normalize
import companion.layout as layout
import companion.ui_components as ui_components
from companion.layout import csrf_field, escape_html
from companion.ui_base import validation_attrs
from companion.pages import airline_sheet
from server.plane import airline_default_types
from server.plane import illustrations
from server.plane import render as panel_render

# The list thumbnail is 88 CSS px wide; 264 covers a 3x screen.
THUMB_WIDTH = 264
NO_VALUE = "—"
# The manual-name fields of a trigger that carries none (see
# airlines_page._airline_card_manual_fields()).
_NO_MANUAL_FIELDS = ("art", False, False, "", "", "", "", "", "", "", "", "")
SUB_ROW_TYPE_SEP = " · "
KNOWN_NAMES_LIST_ID = "airlines-known-names"

CAPTION_TEXT = i18n.msg("airlines.table_caption", "Airlines")
COL_AIRLINE = i18n.msg("airlines.col_airline", "Airline")
COL_PREFIXES = i18n.msg("airlines.col_prefixes", "Prefixes")
COL_ARTWORK = i18n.msg("airlines.col_artwork", "Artwork")
COL_VIEWS = i18n.msg("airlines.col_views", "Views")
COL_LAST_SEEN = i18n.msg("airlines.col_last_seen", "Last seen")
NAME_ARIA = i18n.msg("airlines.name_aria", "Airline name: %s")
SAVE_NAME_TEXT = i18n.msg("airlines.table_save_name", "Save")
ENLARGE_ARIA = i18n.msg("airlines.enlarge_artwork_of", "Enlarge the artwork of %s")
ART_UPLOAD_TEXT = i18n.msg("airlines.table_upload", "Upload")
USES_AIRLINE_ART = i18n.msg("airlines.uses_airline_artwork", "Uses the airline’s artwork")
EXPAND_ARIA = i18n.msg("airlines.expand_types_aria", "Aircraft types seen for %s")
MENU_ARIA = i18n.msg("airlines.row_menu_aria", "Actions for %s")
MENU_RESET = i18n.msg("airlines.reset_original_name", "Reset to the original name")
MENU_CHANGE_ART = i18n.msg("airlines.change_artwork", "Change artwork")
RESOLVE_NAME_ARIA = i18n.msg("airlines.resolve_name_aria", "Airline name for the prefix %s")
RESOLVE_NAME_PLACEHOLDER = i18n.msg("airlines.resolve_name_placeholder", "Airline name")
RESOLVE_TYPE_ARIA = i18n.msg("airlines.resolve_type_aria", "Default aircraft type for %s")
RESOLVE_TYPE_NONE = i18n.msg("airlines.resolve_type_none", "Aircraft type")
RESOLVE_VALIDATE = i18n.msg("airlines.resolve_validate", "Validate")
RESOLVE_IGNORE = i18n.msg("airlines.resolve_ignore", "Ignore")
HAND_NAMED_TEXT = i18n.msg("airlines.named_by_hand", "Named by hand")
STATE_DEFAULT = i18n.msg("airlines.state_airline_default", "Same as the airline")
STATE_OWN = i18n.msg("airlines.state_own_artwork", "Own artwork")
ACTION_CUSTOMISE = i18n.msg("airlines.customise_artwork", "Customise")
MENU_REVERT = i18n.msg("airlines.menu_revert_artwork", "Back to the default")
MENU_DELETE_ART = i18n.msg("airlines.menu_delete_artwork", "Delete the illustration")
MENU_SET_DEFAULT_TYPE = i18n.msg("airlines.menu_set_default_type", "Set as the default type")
MENU_CLEAR_DEFAULT_TYPE = i18n.msg(
    "airlines.menu_clear_default_type", "Remove as the default type")
DEFAULT_TYPE_PILL = i18n.msg("airlines.default_type_pill", "Default type")
UNIDENTIFIED_TEXT = i18n.msg("airlines.unidentified_label", "Unidentified")
VIEWS_ONE = i18n.msg("airlines.views_one", "1 view")
VIEWS_MANY = i18n.msg("airlines.views_many", "%d views")
NOT_SEEN_TEXT = i18n.msg("airlines.table_not_seen", "Not seen yet")
SHOW_TYPES_TEXT = i18n.msg(
    "airlines.show_all_types", "Show the aircraft types of every airline")
TYPES_PARAM = "types"
TYPES_ALL = "all"


@dataclass
class TableData:
    """What the table renders, gathered once by `airlines_page.render()`."""
    pairs: list
    state_dir: str
    now: str
    sheets_by_name: dict = field(default_factory=dict)
    manual_info_by_name: dict = field(default_factory=dict)
    entries_by_slug: dict = field(default_factory=dict)
    gap_rows: list = field(default_factory=list)
    focus_key: str = ""
    default_types: dict = field(default_factory=dict)
    # True when the aircraft-type rows are part of the table itself (the
    # no-script view, `?types=all`); otherwise they wait inside a <template>
    # that airline-types.js opens with the airline's chevron.
    types_open: bool = False


def _page():
    """`airlines_page`, imported late: it imports this module to render."""
    from companion.pages import airlines_page
    return airlines_page


def _views_text(count):
    return i18n.t(VIEWS_ONE) if count == 1 else i18n.t(VIEWS_MANY) % count


def _hidden_label(text):
    return '<span class="visually-hidden">%s </span>' % escape_html(text)


def _thumb_html(page, key, state_dir):
    """The artwork picture for `key`, or the dashed frame when it has none."""
    has_builtin, has_override = page._artwork_files(key, state_dir)
    if not (has_builtin or has_override):
        return '<span class="airline-card__placeholder" aria-hidden="true"></span>'
    return (
        '<img class="airlines-thumb__image" src="%s%s" width="%d" height="%d" '
        'loading="lazy" decoding="async" fetchpriority="low" alt="">'
    ) % (page._illustration_url(key),
         illustration_normalize.thumbnail_query(
             page._illustration_cache_buster(key, state_dir), THUMB_WIDTH),
         page.ILLUSTRATION_TARGET_WIDTH, page.ILLUSTRATION_TARGET_HEIGHT)


def _change_art_form(page, key, text=None, css="row-menu__item"):
    """The "Change artwork" control: a label wrapping the file input of a
    form that posts to the illustration upload route. With a script it sends
    on change; without one the Upload button sends it."""
    return (
        '<form class="airlines-art" method="post" '
        'enctype="multipart/form-data" action="%s">%s'
        '<label class="%s">%s'
        '<input type="file" name="image" accept="image/png" class="visually-hidden" '
        'required data-autosubmit></label>'
        '<noscript><button type="submit" class="airlines-art__upload">%s</button></noscript>'
        "</form>"
    ) % (page._illustration_url(key, "POST"), csrf_field(), css,
         escape_html(text or i18n.t(MENU_CHANGE_ART)), escape_html(i18n.t(ART_UPLOAD_TEXT)))


def _post_form(route, fields, text, css="row-menu__item"):
    """A one-button form posting `fields` (name -> value) to `route`."""
    hidden = "".join(
        '<input type="hidden" name="%s" value="%s">' % (escape_html(name), escape_html(value))
        for name, value in fields)
    return (
        '<form class="airlines-menu__form" method="post" action="%s">%s%s'
        '<button type="submit" class="%s">%s</button></form>'
    ) % (device_scope.scoped(route, "POST"), hidden, csrf_field(), css, escape_html(text))


def _delete_art_form(row_key, delete=False, css="row-menu__item"):
    """Removes the owner's uploaded picture of `row_key`: the type or airline
    shows its default again (the vendored picture, else the airline's own or
    the generic one). "Back to the default" and "Delete the illustration" are
    the same change worded two ways."""
    if delete:
        return _post_form(
            airline_sheet.ARTWORK_DELETE_ROUTE, (("key", row_key),), i18n.t(MENU_DELETE_ART),
            css + " row-menu__item--destructive")
    return _post_form(
        airline_sheet.ARTWORK_DELETE_ROUTE, (("key", row_key),), i18n.t(MENU_REVERT), css)


def _name_cell(row):
    """The airline's name: a form posting to the rename route for an airline
    the built-in prefix table knows, plain text for any other."""
    name = row["name"]
    sheet = row["sheet"]
    if sheet is None:
        manual = row["manual_info"]
        pill = (
            '<span class="airlines-pill">%s</span>' % escape_html(i18n.t(HAND_NAMED_TEXT))
            if manual is not None and not manual[1] else "")
        return '<span class="airlines-name airlines-name--fixed">%s</span>%s' % (
            escape_html(name), pill)
    return (
        '<form class="airlines-name" method="post" action="%s">'
        '<input type="hidden" name="airline" value="%s">%s'
        '<input type="text" name="airline_name" value="%s" maxlength="100" required '
        'autocomplete="off" aria-label="%s" data-autosubmit%s%s>'
        '<noscript><button type="submit" class="airlines-name__save">%s</button></noscript>'
        "</form>"
    ) % (device_scope.scoped(airline_sheet.RENAME_ROUTE, "POST"), escape_html(sheet["builtin"]),
         csrf_field(), escape_html(name), escape_html(i18n.t(NAME_ARIA) % name),
         " autofocus" if row["focus"] else "", validation_attrs("text"),
         escape_html(i18n.t(SAVE_NAME_TEXT)))


def _enlarge_html(page, row, key, label):
    """The thumbnail of `key` as the trigger that opens the shared lightbox on
    the artwork; a real link to the picture without a script. It carries the
    manual-name state so a superseded name keeps its note in the dialog."""
    image_url = page._illustration_url(key)
    busted = image_url + page._illustration_cache_buster(key, row["state_dir"])
    (_mode, _has_manual, _superseded, manual_value, _resolve_prefix, _heading, _upload,
     delete_action, manual_note, _first, _last, _count) = row["manual_fields"]
    return page._airline_card_zoom_html(
        label, page._VIEW_PANEL_MODE_ART, _thumb_html(page, key, row["state_dir"]), busted,
        page._illustration_url(key, "POST"), manual_value, "", escape_html(row["name"]),
        "", delete_action, manual_note, "", "", "",
        aria_label=i18n.t(ENLARGE_ARIA) % label, css_class="airlines-thumb",
        sheet_href=busted)


def _reset_form(page, row):
    """The reset item: the rename reset for a renamed airline, the manual
    name's delete for an owner-named one."""
    sheet = row["sheet"]
    manual = row["manual_info"]
    if sheet is not None and sheet["renamed"]:
        action = device_scope.scoped(airline_sheet.RENAME_RESET_ROUTE, "POST")
        hidden = '<input type="hidden" name="airline" value="%s">' % escape_html(sheet["builtin"])
        text = i18n.t(MENU_RESET)
    elif manual is not None and not manual[1]:
        action = page._manual_delete_action(manual[0])
        hidden = ""
        text = i18n.t(page.DELETE_BUTTON_TEXT)
    else:
        return ""
    return (
        '<form class="airlines-menu__form" method="post" action="%s">%s%s'
        '<button type="submit" class="row-menu__item">%s</button></form>'
    ) % (action, hidden, csrf_field(), escape_html(text))


def _menu_html(items, aria):
    return (
        '<details class="row-menu"><summary class="row-menu__toggle" aria-label="%s">%s</summary>'
        '<div class="row-menu__panel">%s</div></details>'
    ) % (escape_html(aria), layout.icon_html("icon-more-vertical", size=20), items)


def _menu_cell(page, row):
    """Change artwork, back to the default or delete it when the owner
    uploaded one, then the name item when the airline has an owner name."""
    items = _change_art_form(page, row["key"])
    if row["has_override"]:
        items += _delete_art_form(row["key"]) + _delete_art_form(row["key"], delete=True)
    return _menu_html(items + _reset_form(page, row), i18n.t(MENU_ARIA) % row["name"])


def _artwork_cell(page, row):
    """The airline's artwork: a link to the resolve step for an owner-named
    airline still without artwork, the tap-to-enlarge thumbnail when there is
    a picture, else the empty frame."""
    if row["needs_artwork"]:
        inner = _thumb_html(page, row["key"], row["state_dir"])
        card = {
            "name": row["name"], "state_dir": row["state_dir"], "sheet": None,
            "manual_fields": row["manual_fields"], "types": [],
        }
        return page._type_trigger_html(
            card, page.ANY_TYPE_ID, row["name"], row["key"], "airlines-thumb", inner,
            i18n.t(page.ACTION_LABEL_TEMPLATE) % (i18n.t(page.ADD_ACTION_TEXT), row["name"]))
    if row["has_art"]:
        return _enlarge_html(page, row, row["key"], row["name"])
    return '<span class="airlines-thumb">%s</span>' % _thumb_html(
        page, row["key"], row["state_dir"])


def _expand_cell(row):
    if not row["sub_rows"]:
        return '<span class="airlines-expand airlines-expand--none" aria-hidden="true"></span>'
    return (
        '<details class="airlines-expand"><summary aria-label="%s"></summary></details>'
    ) % escape_html(i18n.t(EXPAND_ARIA) % row["name"])


def _main_row_html(page, row):
    prefixes = " ".join(row["sheet"]["prefixes"]) if row["sheet"] else (
        row["manual_info"][0] if row["manual_info"] else "")
    return (
        '<tr class="airlines-row">'
        '<th scope="row" class="airlines-cell airlines-cell--name">'
        '<div class="airlines-namebox">%s%s</div></th>'
        '<td class="airlines-cell airlines-cell--prefixes mono">%s%s</td>'
        '<td class="airlines-cell airlines-cell--art">%s</td>'
        '<td class="airlines-cell airlines-cell--views">%s</td>'
        '<td class="airlines-cell airlines-cell--seen">%s%s</td>'
        '<td class="airlines-cell airlines-cell--menu">%s</td></tr>'
    ) % (
        _expand_cell(row), _name_cell(row),
        _hidden_label(i18n.t(COL_PREFIXES)), escape_html(prefixes or NO_VALUE),
        _artwork_cell(page, row), escape_html(_views_text(row["views"])),
        _hidden_label(i18n.t(COL_LAST_SEEN)), row["last_seen_html"],
        _menu_cell(page, row))


def _sub_art_html(page, sub, row):
    """The type's own picture (enlargeable), else the airline's picture
    dimmed, with the state in words beside it."""
    if sub["slot"] is None:
        return '<span class="airlines-uses text-label">%s</span>' % escape_html(
            i18n.t(USES_AIRLINE_ART))
    label = "%s, %s" % (row["name"], sub["code"])
    if sub["has_own"]:
        sub_row = dict(row, manual_fields=_NO_MANUAL_FIELDS)
        thumb = _enlarge_html(page, sub_row, sub["slot"], label)
        state = STATE_OWN
    else:
        thumb = (
            '<span class="airlines-thumb airlines-thumb--inherited" title="%s">%s</span>' % (
                escape_html(i18n.t(STATE_DEFAULT)),
                _thumb_html(page, row["key"], row["state_dir"])))
        state = STATE_DEFAULT
    # A type that shows its airline's picture says so as a tooltip and to
    # assistive technology; the dimmed picture is the visible cue, so every
    # type row keeps the height of the airline row.
    state_class = "airlines-state text-label" + (
        "" if sub["has_own"] else " visually-hidden")
    return '%s<span class="%s">%s</span>' % (
        thumb, state_class, escape_html(i18n.t(state)))


def _sub_action_html(page, sub):
    """The row's one inline action: back to the default for a type with an
    uploaded picture, else customise it; nothing for a vendored picture."""
    if sub["slot"] is None:
        return ""
    if sub["has_override"]:
        return _delete_art_form(sub["slot"], css="airlines-act")
    if sub["has_builtin"]:
        return ""
    return _change_art_form(page, sub["slot"], i18n.t(ACTION_CUSTOMISE), "airlines-act")


def _sub_menu_html(page, sub, row):
    if sub["slot"] is None and not sub["code_ok"]:
        return ""
    items = _change_art_form(page, sub["slot"]) if sub["slot"] else ""
    if sub["slot"] and sub["has_override"]:
        items += _delete_art_form(sub["slot"])
    if sub["code_ok"]:
        items += _post_form(
            airline_sheet.DEFAULT_TYPE_ROUTE,
            (("airline_key", row["key"]), ("type", "" if sub["is_default"] else sub["code_ok"])),
            i18n.t(MENU_CLEAR_DEFAULT_TYPE if sub["is_default"] else MENU_SET_DEFAULT_TYPE))
    if sub["slot"] and sub["has_override"]:
        items += '<hr class="row-menu__sep">' + _delete_art_form(sub["slot"], delete=True)
    return _menu_html(items, i18n.t(MENU_ARIA) % ("%s, %s" % (row["name"], sub["code"])))


def _sub_row_html(page, sub, row):
    label = sub["code"] if sub["model"] == sub["code"] else (
        "%s%s%s" % (sub["code"], SUB_ROW_TYPE_SEP, sub["model"]))
    star = (
        '<span class="airlines-pill airlines-pill--star">%s%s</span>' % (
            layout.icon_html("icon-star", size=14), escape_html(i18n.t(DEFAULT_TYPE_PILL)))
        if sub["is_default"] else "")
    return (
        '<tr class="airlines-subrow">'
        '<th scope="row" class="airlines-cell airlines-cell--name airlines-cell--type">'
        '<span class="airlines-type">%s</span>%s</th>'
        '<td class="airlines-cell airlines-cell--prefixes"></td>'
        '<td class="airlines-cell airlines-cell--art">%s</td>'
        '<td class="airlines-cell airlines-cell--views">%s</td>'
        '<td class="airlines-cell airlines-cell--seen airlines-cell--act">%s</td>'
        '<td class="airlines-cell airlines-cell--menu">%s</td></tr>'
    ) % (escape_html(label), star, _sub_art_html(page, sub, row),
         escape_html(_views_text(sub["views"])), _sub_action_html(page, sub),
         _sub_menu_html(page, sub, row))


def _slot_for(code, key):
    """The artwork key of the picture an aircraft type `code` is shown with
    (`{airline}-{slug}`, the file the exact-type tier of
    `illustrations.select_illustration()` looks for), or `None` for a type no
    picture slot exists for."""
    slug = illustrations._TYPE_VARIANT_SLUGS.get(code) or illustrations.classify_aircraft_type(code)
    return "%s-%s" % (key, slug) if slug else None


def _sub_rows(page, entry, builtin_name, shapes, row):
    """One dict per aircraft type: seen types first (most seen first), then
    the curated variants never seen. `slot` is the artwork key of the type's
    own picture (`None` for a type that has no slot), `has_own` whether
    that picture exists, `has_override` whether the owner uploaded it."""
    key = row["key"]
    subs = []
    used = set()
    counts = entry.type_counts if entry is not None else ()
    for code, views in counts:
        slot = _slot_for(code, key)
        used.add(slot)
        subs.append({
            "code": code, "views": views, "slot": slot,
            "model": panel_render._TYPE_DISPLAY_LABELS.get(code, code)})
    for shape in shapes or []:
        slot = "%s-%s" % (key, shape)
        if slot not in used:
            label = illustrations.aircraft_label(builtin_name, shape) or shape.upper()
            subs.append({"code": label, "model": label, "views": 0, "slot": slot})
    for sub in subs:
        has_builtin, has_override = (
            page._artwork_files(sub["slot"], row["state_dir"]) if sub["slot"] else (False, False))
        code_ok = airline_default_types.normalise_code(sub["code"]) or ""
        sub.update(
            has_builtin=has_builtin, has_override=has_override,
            has_own=has_builtin or has_override, code_ok=code_ok,
            is_default=bool(code_ok) and code_ok == row["default_type"])
    return subs


def _row_facts(page, data, index, builtin_name, shapes):
    """Everything one airline's rows need, or `None` for an unusable name."""
    sheet = data.sheets_by_name.get(builtin_name)
    name = sheet["name"] if sheet is not None else builtin_name
    key = illustrations.normalise_airline_key(name)
    if not key:
        return None
    manual_info = data.manual_info_by_name.get(builtin_name)
    manual_fields = page._airline_card_manual_fields(
        manual_info, name, key, data.state_dir, data.now)
    has_builtin, has_override = page._artwork_files(key, data.state_dir)
    entry = data.entries_by_slug.get(illustrations.normalise_airline_key(builtin_name))
    seen = entry is not None and entry.last_ts
    facts = {
        "index": index, "builtin": builtin_name, "name": airline_display.shown_name(name), "key": key, "sheet": sheet,
        "manual_info": manual_info, "manual_fields": manual_fields,
        "needs_artwork": manual_fields[0] == page._VIEW_PANEL_MODE_NEEDS_ARTWORK,
        "has_art": has_builtin or has_override, "state_dir": data.state_dir,
        "has_builtin": has_builtin, "has_override": has_override,
        "default_type": data.default_types.get(key, ""),
        "views": entry.times_seen if entry is not None else 0,
        "last_seen_html": (
            layout.concise_timestamp_html(entry.last_ts, data.now, fallback="")
            if seen else escape_html(i18n.t(NOT_SEEN_TEXT))),
        "focus": bool(data.focus_key) and sheet is not None and data.focus_key == key,
    }
    facts["sub_rows"] = _sub_rows(page, entry, builtin_name, shapes, facts)
    return facts


def _filter_text(row):
    parts = [row["builtin"].lower()]
    if row["name"].lower() != parts[0]:
        parts.append(row["name"].lower())
    parts.extend(sub["code"].lower() + " " + sub["model"].lower() for sub in row["sub_rows"])
    sheet = row["sheet"]
    if sheet is not None:
        parts.extend(prefix.lower() for prefix in sheet["prefixes"])
        if sheet["renamed"]:
            parts.append(sheet["builtin"].lower())
    elif row["manual_info"] is not None:
        parts.append(str(row["manual_info"][0]).lower())
    return " ".join(parts)


def row_facts(data, index, builtin_name, shapes):
    """`_row_facts` for the airline at `index` of `data.pairs`."""
    return _row_facts(_page(), data, index, builtin_name, shapes)


def sub_rows_html(row):
    """The aircraft-type rows of one airline group."""
    page = _page()
    return "".join(_sub_row_html(page, sub, row) for sub in row["sub_rows"])


def _types_source(row):
    """The address that serves the group's aircraft-type rows."""
    return "%s?%s=%d" % (device_scope.scoped(_page().MANAGE_ROUTE), TYPES_PARAM, row["index"])


def _airline_group_html(page, row, types_open=False):
    subs = "".join(_sub_row_html(page, sub, row) for sub in row["sub_rows"])
    source = ""
    if subs and not types_open:
        # The rows are fetched when the airline's chevron first opens.
        subs = ""
        source = ' data-types-src="%s"' % escape_html(_types_source(row))
    return (
        '<tbody class="airline-group" id="airline-%s" data-filter-text="%s" data-filter-group="%d"%s>%s%s</tbody>'
    ) % (escape_html(row["key"]), escape_html(_filter_text(row)), row["index"], source,
         _main_row_html(page, row), subs)


def known_type_codes():
    """The aircraft designators the curated pictures show, sorted, for the
    default-type pick of an unidentified row."""
    codes = set(illustrations.PRIMARY_AIRCRAFT_LABELS.values())
    codes |= set(illustrations.VARIANT_AIRCRAFT_LABELS.values())
    return sorted(code for code in codes if airline_default_types.normalise_code(code))


def _type_select_html(prefix):
    options = '<option value="">%s</option>' % escape_html(i18n.t(RESOLVE_TYPE_NONE))
    options += "".join(
        '<option value="%s">%s</option>' % (escape_html(code), escape_html(code))
        for code in known_type_codes())
    return '<select name="default_type" aria-label="%s">%s</select>' % (
        escape_html(i18n.t(RESOLVE_TYPE_ARIA) % prefix), options)


def _gap_group_html(page, index, gap_row, now):
    """One unidentified prefix: a highlighted row resolved in place. A name
    (suggestions from the known airlines), an optional default aircraft type,
    Validate to save the name and Ignore to clear the fields. The form posts
    to the resolve route with `inline`, so the editor comes back with the
    row identified."""
    prefix, count, _first_seen, last_seen, callsign = gap_row
    callsign = callsign if isinstance(callsign, str) else str(callsign)
    form = (
        '<form class="airlines-resolve" method="post" action="%s">'
        '<input type="hidden" name="prefix" value="%s">'
        '<input type="hidden" name="inline" value="1">%s'
        '<p class="airlines-resolve__cap"><span class="airlines-gap-chip">%s</span>'
        '<span class="mono">%s</span><span class="cell-inline-sep">·</span>%s'
        '<span class="cell-inline-sep">·</span>%s</p>'
        '<div class="airlines-resolve__fields">'
        '<input type="text" name="airline_name" list="%s" maxlength="100" required '
        'autocomplete="off" placeholder="%s" aria-label="%s"%s>%s'
        '<div class="airlines-resolve__actions">'
        '%s%s</div></div></form>'
    ) % (
        device_scope.scoped(page.RESOLVE_ROUTE, "POST"), escape_html(prefix), csrf_field(),
        escape_html(i18n.t(UNIDENTIFIED_TEXT)), escape_html(callsign),
        escape_html(_views_text(count)), layout.concise_timestamp_html(last_seen, now, fallback=""),
        KNOWN_NAMES_LIST_ID, escape_html(i18n.t(RESOLVE_NAME_PLACEHOLDER)),
        escape_html(i18n.t(RESOLVE_NAME_ARIA) % prefix), validation_attrs("text"),
        _type_select_html(prefix),
        ui_components.button_html(i18n.t(RESOLVE_VALIDATE), "primary", button_type="submit"),
        ui_components.button_html(i18n.t(RESOLVE_IGNORE), "secondary", button_type="reset"))
    return (
        '<tbody class="airline-group airline-group--gap" data-filter-text="%s" '
        'data-filter-group="gap%d"><tr class="airlines-row airlines-row--gap">'
        '<th scope="row" colspan="6" class="airlines-cell airlines-cell--resolve">%s</th></tr></tbody>'
    ) % (escape_html("%s %s" % (callsign.lower(), prefix.lower())), index, form)


def _known_names_html():
    """One `<datalist>` of every known airline name, shared by the rows."""
    options = "".join(
        '<option value="%s">' % escape_html(name) for name in illustrations.target_airline_names())
    return '<datalist id="%s">%s</datalist>' % (KNOWN_NAMES_LIST_ID, options)


def _head_html():
    cells = "".join(
        '<th scope="col" class="airlines-col airlines-col--%s">%s</th>' % (
            name, escape_html(i18n.t(label)))
        for name, label in (
            ("name", COL_AIRLINE), ("prefixes", COL_PREFIXES), ("art", COL_ARTWORK),
            ("views", COL_VIEWS), ("seen", COL_LAST_SEEN)))
    return '<thead><tr>%s<td class="airlines-col airlines-col--menu"></td></tr></thead>' % cells


def show_types_link_html(data):
    """The script-free way to the aircraft-type rows: a link to the same page
    with every airline's rows in the table. Nothing when they already are."""
    if data.types_open or not data.pairs:
        return ""
    return (
        '<noscript><p class="text-label"><a href="%s?%s=%s">%s</a></p></noscript>'
    ) % (device_scope.scoped(_page().MANAGE_ROUTE), TYPES_PARAM, TYPES_ALL,
         escape_html(i18n.t(SHOW_TYPES_TEXT)))


def table_html(data):
    """The whole editor table for `data`: unidentified rows first, then one
    group per airline."""
    page = _page()
    gaps = "".join(
        _gap_group_html(page, index, gap_row, data.now)
        for index, gap_row in enumerate(data.gap_rows))
    groups = []
    for index, (builtin_name, shapes) in enumerate(data.pairs):
        row = _row_facts(page, data, index, builtin_name, shapes)
        if row is not None:
            groups.append(_airline_group_html(page, row, data.types_open))
    return (
        '<table class="airlines-table"><caption class="visually-hidden">%s</caption>%s%s%s</table>%s'
    ) % (escape_html(i18n.t(CAPTION_TEXT)), _head_html(), gaps, "".join(groups),
         _known_names_html() if gaps else "")
