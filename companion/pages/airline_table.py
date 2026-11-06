"""The Console Airlines editor as one table.

One `<tbody>` per airline: the airline's row (name edited in place, callsign
prefixes as read-only text, the artwork thumbnail that replaces the artwork
enlarged when tapped, views, last seen, a "..." menu) and, behind a native
`<details>` chevron, one sub-row per aircraft type seen for it. Unidentified
prefixes sit above as highlighted rows with a "Name it" link. Below 70rem
every row is a card.

Every control posts to a route that already existed: the rename and reset
routes, the illustration upload route, the manual-name delete route. A
sub-row offers its own artwork menu only for a type that has an artwork slot
of its own (the curated list's aircraft variants); every other type shows
that it uses the airline's artwork. Changing an image is always the "Change
artwork" item of a "..." menu. Stored text reaches the markup only through
`escape_html`.
"""
from dataclasses import dataclass, field

import companion.device_scope as device_scope
import companion.i18n as i18n
import companion.layout as layout
from companion.layout import csrf_field, escape_html
from companion.pages import airline_sheet
from server.plane import illustrations
from server.plane import render as panel_render

NO_VALUE = "—"
# The manual-name fields of a trigger that carries none (see
# airlines_page._airline_card_manual_fields()).
_NO_MANUAL_FIELDS = ("art", False, False, "", "", "", "", "", "", "", "", "")
SUB_ROW_TYPE_SEP = " · "

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
NAME_IT_TEXT = i18n.msg("airlines.name_it", "Name it")
NAME_IT_ARIA = i18n.msg("airlines.name_it_aria", "Name the unidentified prefix %s")
UNIDENTIFIED_TEXT = i18n.msg("airlines.unidentified_label", "Unidentified")
VIEWS_ONE = i18n.msg("airlines.views_one", "1 view")
VIEWS_MANY = i18n.msg("airlines.views_many", "%d views")
NOT_SEEN_TEXT = i18n.msg("airlines.table_not_seen", "Not seen yet")


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
        'loading="lazy" decoding="async" alt="">'
    ) % (page._illustration_url(key), page._illustration_cache_buster(key, state_dir),
         page.ILLUSTRATION_TARGET_WIDTH, page.ILLUSTRATION_TARGET_HEIGHT)


def _change_art_form(page, key):
    """The "Change artwork" menu item: a label wrapping the file input of a
    form that posts to the illustration upload route. With a script it sends
    on change; without one the Upload button sends it."""
    return (
        '<form class="airlines-art" method="post" '
        'enctype="multipart/form-data" action="%s">'
        '<label class="row-menu__item">%s'
        '<input type="file" name="image" accept="image/png" class="visually-hidden" '
        'required data-autosubmit></label>'
        '<noscript><button type="submit" class="airlines-art__upload">%s</button></noscript>'
        "</form>"
    ) % (page._illustration_url(key, "POST"), escape_html(i18n.t(MENU_CHANGE_ART)),
         escape_html(i18n.t(ART_UPLOAD_TEXT)))


def _name_cell(row):
    """The airline's name: a form posting to the rename route for an airline
    the built-in prefix table knows, plain text for any other."""
    name = row["name"]
    sheet = row["sheet"]
    if sheet is None:
        return '<span class="airlines-name airlines-name--fixed">%s</span>' % escape_html(name)
    return (
        '<form class="airlines-name" method="post" action="%s">'
        '<input type="hidden" name="airline" value="%s">%s'
        '<input type="text" name="airline_name" value="%s" maxlength="100" required '
        'autocomplete="off" aria-label="%s" data-autosubmit%s>'
        '<noscript><button type="submit" class="airlines-name__save">%s</button></noscript>'
        "</form>"
    ) % (device_scope.scoped(airline_sheet.RENAME_ROUTE, "POST"), escape_html(sheet["builtin"]),
         csrf_field(), escape_html(name), escape_html(i18n.t(NAME_ARIA) % name),
         " autofocus" if row["focus"] else "", escape_html(i18n.t(SAVE_NAME_TEXT)))


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
    elif manual is not None and not manual[1]:
        action = page._manual_delete_action(manual[0])
        hidden = ""
    else:
        return ""
    return (
        '<form class="airlines-menu__form" method="post" action="%s">%s%s'
        '<button type="submit" class="row-menu__item">%s</button></form>'
    ) % (action, hidden, csrf_field(), escape_html(i18n.t(MENU_RESET)))


def _menu_html(items, aria):
    return (
        '<details class="row-menu"><summary class="row-menu__toggle" aria-label="%s">%s</summary>'
        '<div class="row-menu__panel">%s</div></details>'
    ) % (escape_html(aria), layout.icon_html("icon-more-vertical", size=20), items)


def _menu_cell(page, row):
    """Change artwork, then the reset item when the airline has an owner name."""
    return _menu_html(
        _change_art_form(page, row["key"]) + _reset_form(page, row),
        i18n.t(MENU_ARIA) % row["name"])


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
    if sub["slot"] is None:
        return '<span class="airlines-uses text-label">%s</span>' % escape_html(
            i18n.t(USES_AIRLINE_ART))
    label = "%s, %s" % (row["name"], sub["code"])
    has_builtin, has_override = page._artwork_files(sub["slot"], row["state_dir"])
    if has_builtin or has_override:
        sub_row = dict(row, manual_fields=_NO_MANUAL_FIELDS)
        return _enlarge_html(page, sub_row, sub["slot"], label)
    return '<span class="airlines-thumb">%s</span>' % _thumb_html(
        page, sub["slot"], row["state_dir"])


def _sub_menu_html(page, sub, row):
    if sub["slot"] is None:
        return ""
    return _menu_html(
        _change_art_form(page, sub["slot"]),
        i18n.t(MENU_ARIA) % ("%s, %s" % (row["name"], sub["code"])))


def _sub_row_html(page, sub, row):
    label = sub["code"] if sub["model"] == sub["code"] else (
        "%s%s%s" % (sub["code"], SUB_ROW_TYPE_SEP, sub["model"]))
    return (
        '<tr class="airlines-subrow">'
        '<th scope="row" class="airlines-cell airlines-cell--name airlines-cell--type">%s</th>'
        '<td class="airlines-cell airlines-cell--prefixes"></td>'
        '<td class="airlines-cell airlines-cell--art">%s</td>'
        '<td class="airlines-cell airlines-cell--views">%s</td>'
        '<td class="airlines-cell airlines-cell--seen"></td>'
        '<td class="airlines-cell airlines-cell--menu">%s</td></tr>'
    ) % (escape_html(label), _sub_art_html(page, sub, row),
         escape_html(_views_text(sub["views"])), _sub_menu_html(page, sub, row))


def _sub_rows(entry, builtin_name, shapes, key):
    """One dict per aircraft type: seen types first (most seen first), then
    the curated variants never seen. `slot` is the artwork key of a type that
    has a picture of its own, else `None`."""
    subs = []
    used = set()
    shapes = shapes or []
    counts = entry.type_counts if entry is not None else ()
    for code, views in counts:
        slot = None
        for slug in (illustrations._TYPE_VARIANT_SLUGS.get(code),
                     illustrations.classify_aircraft_type(code)):
            if slug and slug in shapes:
                slot = "%s-%s" % (key, slug)
                used.add(slug)
                break
        subs.append({
            "code": code, "views": views, "slot": slot,
            "model": panel_render._TYPE_DISPLAY_LABELS.get(code, code)})
    for shape in shapes:
        if shape not in used:
            label = illustrations.aircraft_label(builtin_name, shape) or shape.upper()
            subs.append({
                "code": label, "model": label, "views": 0, "slot": "%s-%s" % (key, shape)})
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
    return {
        "index": index, "builtin": builtin_name, "name": name, "key": key, "sheet": sheet,
        "manual_info": manual_info, "manual_fields": manual_fields,
        "needs_artwork": manual_fields[0] == page._VIEW_PANEL_MODE_NEEDS_ARTWORK,
        "has_art": has_builtin or has_override, "state_dir": data.state_dir,
        "views": entry.times_seen if entry is not None else 0,
        "last_seen_html": (
            layout.concise_timestamp_html(entry.last_ts, data.now, fallback="")
            if seen else escape_html(i18n.t(NOT_SEEN_TEXT))),
        "sub_rows": _sub_rows(entry, builtin_name, shapes, key),
        "focus": bool(data.focus_key) and sheet is not None and data.focus_key == key,
    }


def _filter_text(row):
    parts = [row["name"].lower()]
    parts.extend(sub["code"].lower() + " " + sub["model"].lower() for sub in row["sub_rows"])
    sheet = row["sheet"]
    if sheet is not None:
        parts.extend(prefix.lower() for prefix in sheet["prefixes"])
        if sheet["renamed"]:
            parts.append(sheet["builtin"].lower())
    elif row["manual_info"] is not None:
        parts.append(str(row["manual_info"][0]).lower())
    return " ".join(parts)


def _airline_group_html(page, row):
    subs = "".join(_sub_row_html(page, sub, row) for sub in row["sub_rows"])
    return (
        '<tbody class="airline-group" data-filter-text="%s" data-filter-group="%d">%s%s</tbody>'
    ) % (escape_html(_filter_text(row)), row["index"], _main_row_html(page, row), subs)


def _gap_group_html(page, index, gap_row, now):
    """One unidentified prefix: a highlighted row whose "Name it" link opens
    the resolve flow (the shared dialog with a script, the in-page section
    without)."""
    prefix, count, _first_seen, last_seen, callsign = gap_row
    callsign = callsign if isinstance(callsign, str) else str(callsign)
    link = '<a class="airlines-name-it" href="%s?%s=%s" %saria-label="%s">%s</a>' % (
        device_scope.scoped(page.MANAGE_ROUTE), page.RESOLVE_QUERY_PARAM, escape_html(prefix),
        page._gap_trigger_attrs_html(gap_row, now),
        escape_html(i18n.t(NAME_IT_ARIA) % prefix), escape_html(i18n.t(NAME_IT_TEXT)))
    return (
        '<tbody class="airline-group airline-group--gap" data-filter-text="%s" '
        'data-filter-group="gap%d"><tr class="airlines-row airlines-row--gap">'
        '<th scope="row" class="airlines-cell airlines-cell--name"><div class="airlines-namebox">'
        '<span class="airlines-expand airlines-expand--none" aria-hidden="true"></span>'
        '<span class="airlines-name airlines-name--fixed">'
        '<span class="airlines-gap-chip">%s</span> '
        '<span class="mono">%s</span></span></div></th>'
        '<td class="airlines-cell airlines-cell--prefixes mono">%s%s</td>'
        '<td class="airlines-cell airlines-cell--art">'
        '<span class="airline-card__placeholder" aria-hidden="true"></span></td>'
        '<td class="airlines-cell airlines-cell--views">%s</td>'
        '<td class="airlines-cell airlines-cell--seen">%s%s</td>'
        '<td class="airlines-cell airlines-cell--menu airlines-cell--action">%s</td></tr></tbody>'
    ) % (
        escape_html("%s %s" % (callsign.lower(), prefix.lower())), index,
        escape_html(i18n.t(UNIDENTIFIED_TEXT)), escape_html(callsign),
        _hidden_label(i18n.t(COL_PREFIXES)), escape_html(prefix),
        escape_html(_views_text(count)),
        _hidden_label(i18n.t(COL_LAST_SEEN)),
        layout.concise_timestamp_html(last_seen, now, fallback=""), link)


def _head_html():
    cells = "".join(
        '<th scope="col" class="airlines-col airlines-col--%s">%s</th>' % (
            name, escape_html(i18n.t(label)))
        for name, label in (
            ("name", COL_AIRLINE), ("prefixes", COL_PREFIXES), ("art", COL_ARTWORK),
            ("views", COL_VIEWS), ("seen", COL_LAST_SEEN)))
    return '<thead><tr>%s<td class="airlines-col airlines-col--menu"></td></tr></thead>' % cells


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
            groups.append(_airline_group_html(page, row))
    return (
        '<table class="airlines-table"><caption class="visually-hidden">%s</caption>%s%s%s</table>'
    ) % (escape_html(i18n.t(CAPTION_TEXT)), _head_html(), gaps, "".join(groups))
