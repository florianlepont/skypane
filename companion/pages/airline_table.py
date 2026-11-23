"""The Console Airlines editor as one table.

One `<tbody>` per airline: the airline's row (its name as plain text, callsign
prefixes, the code of its default aircraft type, views, last seen, a "..."
menu) and, behind a native `<details>` chevron, one sub-row per aircraft type
the airline has a picture for or was seen with. An airline has no picture of
its own: the pictures belong to its aircraft types
(`illustrations.type_pictures`, the legacy `{airline}.png` being the picture
of its airframe type). A type row says whether it has a picture or follows the
default type's, offers one upload entry, and its menu makes the type the
airline's default picture or deletes the uploaded picture. Unidentified prefixes sit above as compact rows (`airline_rows`)
named in a dialog. The table lists only airlines with artwork: one without
(the application's own name for a prefix, or a name the owner typed or
accepted) is a row of the "Known by name only" block above it, with the
"..." menu of its row, and moves here once it has artwork. Below 70rem every
row is a card.

Every control posts to a route of the editor: the rename and reset routes,
the illustration upload route, the manual-name delete route, the resolve
route, the artwork-delete route and the default-type route. Stored text
reaches the markup only through `escape_html`.
"""
import os
import time
from dataclasses import dataclass, field

import companion.airline_display as airline_display
import companion.device_scope as device_scope
import companion.i18n as i18n
import companion.illustration_normalize as illustration_normalize
import companion.layout as layout
from companion.layout import csrf_field, escape_html
from companion.pages import airline_known_rows, airline_rows, airline_sheet
from server.plane import airline_default_types
from server.plane import airline_suggest
from server.plane import illustrations
from server.plane import render as panel_render

# The list thumbnail is 88 CSS px wide; 264 covers a 3x screen.
THUMB_WIDTH = 264
NO_VALUE = "—"
# The manual-name fields of a trigger that carries none (see
# airlines_page._airline_card_manual_fields()).
_NO_MANUAL_FIELDS = ("art", False, False, "", "", "", "", "", "", "", "", "")
SUB_ROW_TYPE_SEP = " · "
KNOWN_NAMES_LIST_ID = airline_rows.KNOWN_NAMES_LIST_ID

CAPTION_TEXT = i18n.msg("airlines.table_caption", "Airlines")
COL_AIRLINE = i18n.msg("airlines.col_airline", "Airline")
COL_PREFIXES = i18n.msg("airlines.col_prefixes", "Prefixes")
COL_DEFAULT_TYPE = airline_rows.COL_DEFAULT_TYPE
COL_VIEWS = i18n.msg("airlines.col_views", "Views")
COL_LAST_SEEN = i18n.msg("airlines.col_last_seen", "Last seen")
ENLARGE_ARIA = i18n.msg("airlines.enlarge_artwork_of", "Enlarge the artwork of %s")
ART_UPLOAD_TEXT = i18n.msg("airlines.table_upload", "Upload")
EXPAND_ARIA = i18n.msg("airlines.expand_types_aria", "Aircraft types seen for %s")
MENU_ARIA = i18n.msg("airlines.row_menu_aria", "Actions for %s")
MENU_RESET = i18n.msg("airlines.reset_original_name", "Reset to the original name")
MENU_CHANGE_ART = i18n.msg("airlines.change_artwork", "Change artwork")
STATE_OWN = i18n.msg("airlines.state_own_artwork", "Own artwork")
ACTION_ADD_ART = i18n.msg("airlines.add_artwork", "Add artwork")
MENU_DELETE_ART = i18n.msg("airlines.menu_delete_artwork", "Delete the artwork")
MENU_SET_DEFAULT_TYPE = i18n.msg(
    "airlines.menu_set_default_type", "Use as the airline's default picture")
MENU_CLEAR_DEFAULT_TYPE = i18n.msg(
    "airlines.menu_clear_default_type", "Stop using as the airline's default picture")
DEFAULT_TYPE_PILL = i18n.msg("airlines.default_type_pill", "Default type")
VIEWS_ONE = i18n.msg("airlines.views_one", "1 view")
VIEWS_MANY = i18n.msg("airlines.views_many", "%d views")
NOT_SEEN_TEXT = i18n.msg("airlines.table_not_seen", "Not seen yet")
TYPES_HEAD_TEXT = i18n.msg("airlines.types_seen_head", "Aircraft types seen")
SHOW_TYPES_TEXT = i18n.msg(
    "airlines.show_all_types", "Show the aircraft types of every airline")
TYPES_PARAM = "types"
TYPES_ALL = "all"
# At most this many rows of one page show the pending lookup; the script
# asks for them one at a time, the others are asked on a later visit.
MAX_PENDING_ROWS = 3


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
    # The fleet root, where the suggestion cache lives ("" shows no suggestion).
    root_state_dir: str = ""
    known_rows: tuple = ()
    promoted_prefixes: dict = field(default_factory=dict)
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


def _upload_action(page, key, code):
    """The upload address of the artwork `key`, naming the aircraft type `code`
    the picture is for (an upload always says which type it shows)."""
    action = page._illustration_url(key, "POST")
    if not code:
        return action
    return "%s%s%s=%s" % (
        action, "&" if "?" in action else "?", page.DEFAULT_TYPE_QUERY_PARAM, escape_html(code))


def _change_art_form(page, key, text=None, css="row-menu__item", code=""):
    """The "Change artwork" control: a label wrapping the file input of a
    form that posts to the illustration upload route. With a script it sends
    on change; without one the Upload button sends it."""
    label = escape_html(text or i18n.t(MENU_CHANGE_ART))
    if css == "airlines-act":
        label = '<span class="airlines-act__text">%s</span>' % label
    return (
        '<form class="airlines-art" method="post" '
        'enctype="multipart/form-data" action="%s">%s'
        '<label class="%s">%s'
        '<input type="file" name="image" accept="image/png" class="visually-hidden" '
        'required data-autosubmit></label>'
        '<noscript><button type="submit" class="airlines-art__upload">%s</button></noscript>'
        "</form>"
    ) % (_upload_action(page, key, code), csrf_field(), css, label,
         escape_html(i18n.t(ART_UPLOAD_TEXT)))


def _post_form(route, fields, text, css="row-menu__item"):
    """A one-button form posting `fields` (name -> value) to `route`."""
    hidden = "".join(
        '<input type="hidden" name="%s" value="%s">' % (escape_html(name), escape_html(value))
        for name, value in fields)
    return (
        '<form class="airlines-menu__form" method="post" action="%s">%s%s'
        '<button type="submit" class="%s">%s</button></form>'
    ) % (device_scope.scoped(route, "POST"), hidden, csrf_field(), css, escape_html(text))


def _delete_art_form(row_key):
    """Removes the owner's uploaded picture of `row_key`: the type then shows
    the default type's picture (or the vendored one) again."""
    return _post_form(
        airline_sheet.ARTWORK_DELETE_ROUTE, (("key", row_key),), i18n.t(MENU_DELETE_ART),
        "row-menu__item row-menu__item--destructive")


def _name_cell(row):
    """The airline's name as plain text; renaming is an action of the row's menu."""
    return '<span class="airlines-name airlines-name--fixed">%s</span>' % escape_html(row["name"])


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
        hidden = '<p class="text-label section-caption airlines-menu__note">%s</p>' % (
            escape_html(i18n.t(page.MANUAL_DELETE_CAPTION)))
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
    ) % (escape_html(aria), layout.icon_html("icon-more", size=20), items)


def _rename_dialog(row):
    page = _page()
    sheet = row["sheet"]
    if sheet is None:
        return airline_rows.manual_rename_dialog_html(
            row["index"], row["manual_info"][0], row["name"],
            device_scope.scoped(page.RENAME_MANUAL_ROUTE, "POST"), csrf_field(),
            device_scope.scoped(page.MANAGE_ROUTE), open_=row["focus"])
    return airline_rows.rename_dialog_html(
        row["index"], sheet["builtin"], row["name"],
        device_scope.scoped(airline_sheet.RENAME_ROUTE, "POST"), csrf_field(),
        device_scope.scoped(page.MANAGE_ROUTE), open_=row["focus"])


def _hand_named(row):
    """An airline the owner named by hand and the built-in tables do not cover."""
    manual = row["manual_info"]
    return (row["sheet"] is None and manual is not None and not manual[1]
            and _page().manual_prefix_renamable(manual[0]))


def _menu_parts(page, row):
    """`(menu, rename dialog)` of an airline: Rename for an airline the
    built-in prefix table knows or the owner named by hand, the way back to the original name after a
    rename (or Delete my name for an owner-named one). The artwork items are
    on the type rows. Both empty when nothing applies."""
    renamable = row["sheet"] is not None or _hand_named(row)
    items = airline_rows.rename_item_html(row["index"]) if renamable else ""
    items += _reset_form(page, row)
    if not items:
        return "", ""
    return (_menu_html(items, i18n.t(MENU_ARIA) % row["name"]),
            _rename_dialog(row) if renamable else "")


def _menu_cell(page, row):
    return "".join(_menu_parts(page, row))


def _default_type_text(row):
    code = row["default_type"]
    return '<span class="airlines-deftype mono">%s</span>' % escape_html(code or NO_VALUE)


def _artwork_cell(row):
    """The airline's default aircraft type, as its code: the airline has no
    picture of its own, the pictures are on the type rows."""
    return '<span class="airlines-deftype-cell">%s</span>' % _default_type_text(row)


def _meta_html(row, prefixes):
    """The phone row's second line, `AFR · A320 · 37 views`: the prefixes, the
    default type and the views of the row's separate cells (which a phone
    hides, so nothing is read twice)."""
    parts = (prefixes or NO_VALUE, row["default_type"] or NO_VALUE, _views_text(row["views"]))
    return '<span class="airlines-meta mono">%s</span>' % escape_html(
        SUB_ROW_TYPE_SEP.join(parts))


def _expand_cell(row):
    if not row["sub_rows"]:
        return '<span class="airlines-expand airlines-expand--none" aria-hidden="true"></span>'
    return (
        '<details class="airlines-expand"><summary aria-label="%s"></summary></details>'
    ) % escape_html(i18n.t(EXPAND_ARIA) % row["name"])


def _row_prefixes(row):
    return " ".join(row["sheet"]["prefixes"]) if row["sheet"] else (
        row["manual_info"][0] if row["manual_info"] else row["promoted_prefix"])


def _main_row_html(page, row):
    prefixes = _row_prefixes(row)
    return (
        '<tr class="airlines-row">'
        '<th scope="row" class="airlines-cell airlines-cell--name">'
        '<div class="airlines-namebox">%s%s%s</div></th>'
        '<td class="airlines-cell airlines-cell--prefixes mono">%s%s</td>'
        '<td class="airlines-cell airlines-cell--art">%s</td>'
        '<td class="airlines-cell airlines-cell--views">%s</td>'
        '<td class="airlines-cell airlines-cell--seen">%s%s</td>'
        '<td class="airlines-cell airlines-cell--menu">%s</td></tr>'
    ) % (
        _expand_cell(row), _name_cell(row), _meta_html(row, prefixes),
        _hidden_label(i18n.t(COL_PREFIXES)), escape_html(prefixes or NO_VALUE),
        _artwork_cell(row), escape_html(_views_text(row["views"])),
        _hidden_label(i18n.t(COL_LAST_SEEN)), row["last_seen_html"],
        _menu_cell(page, row))


def _sub_art_html(page, sub, row):
    """The type's picture (enlargeable) with "Own artwork" beside it, else the
    picture the airline's default type gives it, dimmed and no words."""
    label = "%s, %s" % (row["name"], sub["code"])
    if sub["picture"] is not None:
        # The airline's legacy picture keeps the airline's manual-name state
        # in the dialog (its delete action and superseded note).
        shown = row if sub["picture"].key == row["key"] else dict(row, manual_fields=_NO_MANUAL_FIELDS)
        thumb = _enlarge_html(page, shown, sub["picture"].key, label)
        return '%s<span class="airlines-state text-label">%s</span>' % (
            thumb, escape_html(i18n.t(STATE_OWN)))
    if row["default_key"]:
        return '<span class="airlines-thumb airlines-thumb--inherited">%s</span>' % (
            _thumb_html(page, row["default_key"], row["state_dir"]))
    return ""


def _sub_action_html(page, sub):
    """The type row's one upload entry: "Add artwork" for a type with no
    picture, "Change artwork" for one that has it; nothing for a type no
    picture slot exists for. The upload names the row's type."""
    if sub["slot"] is None:
        return ""
    return _change_art_form(
        page, sub["slot"], i18n.t(MENU_CHANGE_ART if sub["has_own"] else ACTION_ADD_ART),
        "airlines-act", sub["code_ok"])


def _sub_menu_html(page, sub, row):
    """The type's menu: set it as the airline's default type (only a type with
    a picture of its own for this airline), clear it when it is the default,
    and delete the uploaded picture, which only exists as an owner's upload."""
    items = ""
    stored = sub["code_ok"] and sub["code_ok"] == row["stored_default"]
    if sub["code_ok"] and (stored or (sub["has_own"] and not sub["is_default"])):
        items += _post_form(
            airline_sheet.DEFAULT_TYPE_ROUTE,
            (("airline_key", row["key"]), ("type", "" if stored else sub["code_ok"])),
            i18n.t(MENU_CLEAR_DEFAULT_TYPE if stored else MENU_SET_DEFAULT_TYPE))
    if sub["has_override"]:
        items += _delete_art_form(sub["picture"].key)
    if not items:
        return ""
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


def _sub_row(code, views, model, picture, slot, row):
    """One type row. `picture` is the type's `illustrations.TypePicture` (or
    `None`), `slot` the artwork key an upload for the type goes to."""
    code_ok = airline_default_types.normalise_code(code) or ""
    override = picture is not None and bool(
        illustrations.override_path_for_key(picture.key, row["state_dir"])
        and os.path.isfile(illustrations.override_path_for_key(picture.key, row["state_dir"])))
    return {
        "code": code, "views": views, "model": model, "picture": picture,
        "slot": picture.key if picture is not None else slot,
        "has_own": picture is not None, "has_override": override, "code_ok": code_ok,
        "is_default": bool(code_ok) and code_ok == row["default_type"]}


def _sub_rows(entry, row, builtin_name, shapes):
    """One dict per aircraft type: the types seen for the airline first (most
    seen first), then the other types it has a picture for, then the curated
    variants of its built-in original it has no picture of yet. `slot` is the
    artwork key of the type's picture (`None` for a type that has no slot)."""
    key = row["key"]
    counts = entry.type_counts if entry is not None else ()
    pictures = row["pictures"]
    subs = [
        _sub_row(code, views, panel_render._TYPE_DISPLAY_LABELS.get(code, code),
                 pictures.get(code.strip().upper()), _slot_for(code, key), row)
        for code, views in counts]
    seen = {code.strip().upper() for code, _views in counts}
    unseen = [
        _sub_row(code, 0, code, picture, _slot_for(code, key), row)
        for code, picture in pictures.items() if code not in seen]
    listed = {sub["code"] for sub in subs} | {sub["code"] for sub in unseen} | seen
    for shape in shapes or []:
        code = illustrations.aircraft_label(builtin_name, shape) or shape.upper()
        if code not in listed:
            unseen.append(_sub_row(code, 0, code, None, "%s-%s" % (key, shape), row))
    subs.extend(sorted(unseen, key=lambda sub: sub["code"]))
    legacy = illustrations.resolved_illustration_path(key, row["state_dir"])
    own = illustrations.TypePicture(key, legacy) if legacy else None
    if own is not None and all(
            sub["picture"] is None or sub["picture"].key != key for sub in subs):
        # The airline's legacy picture of an airframe nobody named: listed so
        # it is not hidden, under no type.
        subs.append(_sub_row(NO_VALUE, 0, NO_VALUE, own, key, row))
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
    entry = data.entries_by_slug.get(illustrations.normalise_airline_key(builtin_name))
    seen = entry is not None and entry.last_ts
    codes = [code for code, _views in entry.type_counts] if entry is not None else ()
    pictures = illustrations.type_pictures(key, data.state_dir, codes)
    default_type = illustrations.effective_default_type(key, data.state_dir, pictures) or ""
    default_picture = illustrations.default_picture(key, data.state_dir)
    facts = {
        "index": index, "builtin": builtin_name, "name": airline_display.shown_name(name), "key": key, "sheet": sheet,
        "manual_info": manual_info, "manual_fields": manual_fields,
        "needs_artwork": manual_fields[0] == page._VIEW_PANEL_MODE_NEEDS_ARTWORK,
        "has_art": default_picture is not None or bool(pictures), "state_dir": data.state_dir,
        "pictures": pictures, "default_type": default_type,
        "stored_default": data.default_types.get(key, ""),
        "default_key": default_picture.key if default_picture is not None else "",
        "views": entry.times_seen if entry is not None else 0,
        "last_seen_html": (
            layout.concise_timestamp_html(entry.last_ts, data.now, fallback="")
            if seen else escape_html(i18n.t(NOT_SEEN_TEXT))),
        "promoted_prefix": data.promoted_prefixes.get(builtin_name, ""),
        "focus": bool(data.focus_key) and sheet is not None and data.focus_key == key,
    }
    facts["sub_rows"] = _sub_rows(entry, facts, builtin_name, shapes)
    facts["kinds"] = airline_rows.row_kinds(facts["views"])
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
    elif row["promoted_prefix"]:
        parts.append(row["promoted_prefix"].lower())
    return " ".join(parts)


def row_facts(data, index, builtin_name, shapes):
    """`_row_facts` for the airline at `index` of `data.pairs`."""
    return _row_facts(_page(), data, index, builtin_name, shapes)


def _subhead_html(row):
    """The label over an airline's aircraft-type rows."""
    return (
        '<tr class="airlines-subhead"><th scope="colgroup" colspan="6" '
        'class="airlines-subhead__text">%s</th></tr>'
    ) % escape_html(i18n.t(TYPES_HEAD_TEXT))


def sub_rows_html(row):
    """The aircraft-type rows of one airline group, under their label."""
    page = _page()
    return _subhead_html(row) + "".join(_sub_row_html(page, sub, row) for sub in row["sub_rows"])


def _types_source(row):
    """The address that serves the group's aircraft-type rows."""
    return "%s?%s=%d" % (device_scope.scoped(_page().MANAGE_ROUTE), TYPES_PARAM, row["index"])


def _airline_group_html(page, row, types_open=False):
    subs = sub_rows_html(row) if row["sub_rows"] else ""
    source = ""
    if subs and not types_open:
        # The rows are fetched when the airline's chevron first opens.
        subs = ""
        source = ' data-types-src="%s"' % escape_html(_types_source(row))
    return (
        '<tbody class="airline-group" id="airline-%s" data-filter-text="%s" data-filter-group="%d" '
        'data-filter-kind="%s"%s>%s%s</tbody>'
    ) % (escape_html(row["key"]), escape_html(_filter_text(row)), row["index"], row["kinds"], source,
         _main_row_html(page, row), subs)


def suggestion_for(page, root_state_dir, prefix, pending_budget=None):
    """What the row of `prefix` shows besides "Name it": the cached suggestion,
    the pending lookup while `pending_budget` (a one-item list counted down
    here) allows one, else nothing. Reads the cache only: a page render
    never calls the service and never writes."""
    if not root_state_dir or not airline_suggest.enabled():
        return None
    entry = airline_suggest.cached(root_state_dir, prefix)
    if entry is not None and entry.get("state") == airline_suggest.STATE_SUGGESTED:
        return airline_rows.Suggestion(
            name=entry["name"],
            reject_action=device_scope.scoped(page.AIRLINE_SUGGEST_REJECT_ROUTE, "POST"))
    if pending_budget and airline_suggest.pending(root_state_dir, prefix, time.time()):
        pending_budget.pop()
        return airline_rows.Suggestion(
            ask_action=device_scope.scoped(page.AIRLINE_SUGGEST_ROUTE, "POST"))
    return None


def suggest_row_html(page, index, gap_row, now, suggestion=None):
    """One unidentified prefix: a compact row with a "Name it" button whose
    dialog names it through the resolve route, or, with a `suggestion`, the
    proposed name with Edit and the check. The one definition of the row,
    used by the page and by the answer to the suggestion script."""
    prefix, count, _first_seen, last_seen, callsign = gap_row
    callsign = callsign if isinstance(callsign, str) else str(callsign)
    meta = '%s<span class="cell-inline-sep">·</span>%s<span class="cell-inline-sep">·</span>%s' % (
        escape_html(callsign), escape_html(_views_text(count)),
        layout.concise_timestamp_html(last_seen, now, fallback=""))
    return airline_rows.gap_group_html(
        index, prefix, meta, "%s %s" % (callsign.lower(), prefix.lower()),
        device_scope.scoped(page.RESOLVE_ROUTE, "POST"), csrf_field(),
        device_scope.scoped(page.MANAGE_ROUTE), suggestion)


def _gap_group_html(page, index, gap_row, now, suggestion=None):
    return suggest_row_html(page, index, gap_row, now, suggestion)


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
            ("name", COL_AIRLINE), ("prefixes", COL_PREFIXES), ("art", COL_DEFAULT_TYPE),
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


def table_and_chips(data):
    """`(table markup, filter chips)` for `data`: unidentified rows first, then
    one group per airline; the chips carry the count of each kind of row."""
    page = _page()
    budget = [None] * MAX_PENDING_ROWS
    gaps = "".join(
        _gap_group_html(page, index, gap_row, data.now,
                        suggestion_for(page, data.root_state_dir, gap_row[0], budget))
        for index, gap_row in enumerate(data.gap_rows))
    groups = []
    known = [(name.casefold(), prefix, {"prefix": prefix, "name": name})
             for prefix, name in data.known_rows]
    counts = {airline_rows.KIND_UNIDENTIFIED: len(data.gap_rows)}
    for index, (builtin_name, shapes) in enumerate(data.pairs):
        row = _row_facts(page, data, index, builtin_name, shapes)
        if row is None:
            continue
        if not row["has_art"]:
            # An airline without artwork is listed by name, with the menu of its row.
            menu, dialog = _menu_parts(page, row)
            known.append((row["name"].casefold(), _row_prefixes(row), {
                "prefix": _row_prefixes(row), "name": row["name"], "key": row["key"],
                "filter_text": _filter_text(row), "menu_html": menu, "dialog_html": dialog}))
            continue
        groups.append(_airline_group_html(page, row, data.types_open))
        counts[row["kinds"]] = counts.get(row["kinds"], 0) + 1
    counts[airline_rows.KIND_KNOWN] = len(known)
    gap_table = (
        '<table class="airlines-table airlines-table--gaps"><caption class="airlines-label">%s</caption>%s</table>%s'
    ) % (escape_html("%s · %d" % (i18n.t(airline_rows.CHIP_UNIDENTIFIED), len(data.gap_rows))),
         gaps, _known_names_html()) if gaps else ""
    table = (
        '<table class="airlines-table"><caption class="airlines-label">%s</caption>%s%s</table>'
    ) % (escape_html("%s · %d" % (i18n.t(CAPTION_TEXT), len(groups))), _head_html(), "".join(groups))
    slot = any(args.get("menu_html") for _name, _prefix, args in known)
    known_table = airline_known_rows.table_html([
        airline_known_rows.group_html(page, data.state_dir, slot=slot, **args)
        for _name, _prefix, args in sorted(known, key=lambda item: item[:2])])
    table = gap_table + known_table + table
    return table, airline_rows.chips(counts, len(data.gap_rows) + len(known) + len(groups))


def table_html(data):
    """The whole editor table for `data`."""
    return table_and_chips(data)[0]
