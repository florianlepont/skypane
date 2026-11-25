"""The "Missing illustrations" section of the Airlines editor.

One row is one airline x aircraft family that has no picture of its own: a
dashed picture slot, the family's name, the designators seen with the views,
and a "+ Illustration" button that opens the shared add-illustration dialog
with the family fixed. An airline with no sighting and no artwork has one
"Type to choose" row whose dialog asks for the type first. An airline that
has artwork for some families is listed for its other seen families only; one
with artwork and no sighting is not listed. Rows sit under a small header per
airline (name, prefix, state, rows to do); the header carries the "..." menu of
an airline that has no row in the table (named by hand or renamed). Nothing
here stores anything and no route is added: the buttons post to the existing
illustration upload route, and an airline whose family gets a picture loses
that row on the next render. Names reach the markup only through `escape_html`.
"""
import companion.i18n as i18n
import companion.layout as layout
from companion.layout import escape_html
from companion.pages import airline_families, airline_rows
from server.plane import enrich, illustrations, manual_resolutions

TITLE_TEXT = i18n.msg("airlines.missing_title", "Missing illustrations")
CAPTION_TEXT = i18n.msg(
    "airlines.missing_caption",
    "One row per airline and aircraft family still to illustrate.")
EMPTY_TITLE = i18n.msg("airlines.missing_empty_title", "All illustrations are in place")
EMPTY_BODY = i18n.msg(
    "airlines.missing_empty_body",
    "Every airline has an illustration for each aircraft family seen.")
STATE_NONE = i18n.msg("airlines.missing_state_none", "No artwork yet")
STATE_DONE = i18n.msg("airlines.missing_state_done", "%s already done")
STATE_DONE_MANY = i18n.msg("airlines.missing_state_done_many", "%d families already done")
STATE_HAS = i18n.msg("airlines.missing_state_has", "Has artwork")
TODO_TEXT = i18n.msg("airlines.missing_todo", "%d to do")
ASK_TITLE = i18n.msg("airlines.missing_ask_title", "Type to choose")
ASK_HINT = i18n.msg(
    "airlines.missing_ask_hint", "No sighting yet: you pick the type in the dialog")
ADD_TEXT = i18n.msg("airlines.missing_add", "Illustration")
ADD_ARIA = i18n.msg("airlines.missing_add_aria", "Add an illustration for %s, %s")
ADD_ASK_ARIA = i18n.msg(
    "airlines.missing_add_ask_aria", "Add an illustration for %s, type to choose")

SEP = " · "
# The page's add-illustration step has no aircraft type of its own to name: it
# is the airline-level one.
_NO_MANUAL_FIELDS = ("art", False, False, "", "", "", "", "", "", "", "", "")
ASK_KIND = "ask"


def _table():
    """`airline_table`, imported late: it imports this module to render."""
    from companion.pages import airline_table
    return airline_table


def rows(state_dir, registry):
    """The `(prefix, name)` pairs the application knows by name and that have
    no artwork, sorted by name: not an airline whose prefix the owner named by
    hand (that airline is in the editor's data already)."""
    registry = registry or {}
    pairs = []
    for prefix, name in enrich.names_without_artwork():
        key = manual_resolutions.illustration_key_for_name(name)
        if prefix in registry or not key:
            continue
        if illustrations.has_pictures(key, state_dir):
            continue
        pairs.append((prefix, name))
    return tuple(pairs)


def promoted(state_dir, registry, taken):
    """`{name: prefix}` of the airlines named by the application whose
    uploaded artwork gives them a row of the main table: not hand-named (that
    row exists already) and not in `taken`, the names the table lists."""
    registry = registry or {}
    found = {}
    for prefix, name in enrich.names_without_artwork():
        key = manual_resolutions.illustration_key_for_name(name)
        if prefix in registry or not key or name in taken or name in found:
            continue
        if illustrations.has_pictures(key, state_dir):
            found[name] = prefix
    return found


def title_text(count):
    return "%s%s%d" % (i18n.t(TITLE_TEXT), SEP, count)


def _family_label(sub):
    return airline_families.family_label(sub["slug"]) or sub["code"]


def todo_items(row):
    """The rows an airline needs: one per seen aircraft family with no picture
    of its own (most seen first), else the single "type to choose" row of an
    airline with no artwork at all, else none."""
    subs = sorted(
        (sub for sub in row["sub_rows"] if sub["views"] and not sub["has_own"] and sub["slot"]),
        key=lambda sub: (-sub["views"], sub["code"]))
    if subs:
        return subs
    return [ASK_KIND] if not row["has_art"] else []


def state_text(row, count):
    """`No artwork yet · 2 to do` or `Airbus A320 family already done · 1 to
    do`: what the airline already has, and how many rows it is listed with."""
    done = []
    for sub in row["sub_rows"]:
        label = airline_families.family_label(sub["slug"]) if sub["has_own"] else ""
        if label and label not in done:
            done.append(label)
    if not row["has_art"]:
        have = i18n.t(STATE_NONE)
    elif len(done) == 1:
        have = i18n.t(STATE_DONE) % done[0]
    elif done:
        have = i18n.t(STATE_DONE_MANY) % len(done)
    else:
        have = i18n.t(STATE_HAS)
    return have + SEP + i18n.t(TODO_TEXT) % count


def _slot_html():
    return '<span class="airlines-missing__slot" aria-hidden="true">%s</span>' % layout.icon_html(
        "icon-plane", 22)


def _add_inner():
    return '%s<span class="airlines-missing__text">%s</span>' % (
        layout.icon_html("icon-plus", 20), escape_html(i18n.t(ADD_TEXT)))


def _family_button(page, sub, row):
    """The family row's button: the dialog with the family named in its chip
    and the upload address already carrying the designator; a plain upload
    form without a script."""
    label = _family_label(sub)
    return _table().add_art_trigger(
        page, sub, row, inner=_add_inner(), css="btn btn--secondary airlines-missing__add",
        aria=i18n.t(ADD_ARIA) % (row["name"], label), chip=label,
        plain_css="btn btn--secondary")


def _ask_nojs(page, key):
    """The no-script upload of a row that asks for the type: the type select
    comes first in the multipart body, as the upload route reads it."""
    table = _table()
    options = "".join(
        '<option value="%s">%s</option>' % (escape_html(code), escape_html(code))
        for code in page.ask_type_options())
    select = (
        '<select name="%s" required class="%s" aria-label="%s"><option value="">%s</option>%s</select>'
    ) % (page.DEFAULT_TYPE_QUERY_PARAM, page.ASK_TYPE_CLASS, escape_html(i18n.t(page.ASK_TYPE_LABEL)),
         escape_html(i18n.t(page.ASK_TYPE_LABEL)), options)
    form = table.change_art_form(page, key, i18n.t(ADD_TEXT), "btn btn--secondary", "")
    return form.replace("<label", select + "<label", 1)


def _ask_button(page, state_dir, row):
    """The "type to choose" row's button: the dialog asks for the aircraft type
    first (Upload stays disabled until it is chosen)."""
    name, key = row["name"], row["key"]
    card = {
        "name": name, "state_dir": state_dir, "sheet": None,
        "manual_fields": _NO_MANUAL_FIELDS, "types": [],
    }
    trigger = page._type_trigger_html(
        card, page.ANY_TYPE_ID, name, key, "btn btn--secondary airlines-missing__add", _add_inner(),
        i18n.t(ADD_ASK_ARIA) % name, extra_attrs='%s="" ' % page.ASK_TYPE_ATTR)
    return '<span class="js-gate airlines-act-gate">%s</span><span class="airlines-act-nojs">%s</span>' % (
        trigger, _ask_nojs(page, key))


def _item_html(page, state_dir, row, prefix, item, number):
    """One airline x family row (or the airline's "type to choose" row)."""
    if item == ASK_KIND:
        title, detail = i18n.t(ASK_TITLE), i18n.t(ASK_HINT)
        button = _ask_button(page, state_dir, row)
    else:
        title = _family_label(item)
        detail = SEP.join((
            ", ".join(item["codes"]), _table().views_text(item["views"])))
        button = _family_button(page, item, row)
    filter_text = " ".join((row["name"], prefix, title, detail)).lower()
    return (
        '<li class="airlines-missing__item" data-filter-text="%s" data-filter-kind="%s" '
        'data-filter-group="missing-%d">%s<div class="airlines-missing__what">'
        '<span class="airlines-missing__family">%s</span>'
        '<span class="airlines-missing__seen">%s</span></div>%s</li>'
    ) % (escape_html(filter_text), airline_rows.KIND_MISSING, number, _slot_html(),
         escape_html(title), escape_html(detail), button)


def _head_html(row, prefix, count, anchor, menu_html, dialog_html):
    attr = ' id="airline-%s"' % escape_html(row["key"]) if anchor else ""
    return (
        '<li class="airlines-missing__head" data-filter-day%s>'
        '<span class="airlines-missing__who"><span class="airlines-missing__name">%s</span>'
        '<span class="airlines-missing__prefix mono">%s</span></span>'
        '<span class="airlines-missing__state">%s</span>%s%s</li>'
    ) % (attr, escape_html(row["name"]), escape_html(prefix), escape_html(state_text(row, count)),
         menu_html, dialog_html)


def group_html(page, state_dir, airline, first_number):
    """`(markup, rows)` of one airline: a list of its header and its rows, numbered from
    `first_number` for the filter's row groups. `airline` is a dict with the
    airline's table facts (`row`), its `prefix`, its `items`, and, for an
    airline with no row in the table (`anchor`), the "..." menu and the
    dialog of that menu."""
    row, items = airline["row"], airline["items"]
    head = _head_html(
        row, airline["prefix"], len(items), airline["anchor"], airline["menu"], airline["dialog"])
    body = "".join(
        _item_html(page, state_dir, row, airline["prefix"], item, first_number + offset)
        for offset, item in enumerate(items))
    return '<ul class="airlines-missing__airline">%s%s</ul>' % (head, body)


def section_html(page, state_dir, airlines):
    """`(markup, rows)` of the section for the airlines `airlines` (dicts of
    `group_html`, in order): the title with the number of rows, the caption and
    the list, or the empty state when nothing is missing."""
    parts = []
    count = 0
    for airline in airlines:
        parts.append(group_html(page, state_dir, airline, count))
        count += len(airline["items"])
    if count:
        body = '<div class="airlines-missing__list">%s</div>' % "".join(parts)
        modifier = ""
    else:
        body = (
            '<div class="airlines-missing__empty"><span class="airlines-missing__ok" '
            'aria-hidden="true">%s</span><p class="airlines-missing__empty-title">%s</p>'
            '<p class="text-label section-caption">%s</p></div>'
        ) % (layout.icon_html("icon-check", 24), escape_html(i18n.t(EMPTY_TITLE)),
             escape_html(i18n.t(EMPTY_BODY)))
        modifier = " airlines-missing--done"
    markup = (
        '<section class="airlines-missing%s" id="airlines-missing" aria-labelledby="airlines-missing-title">'
        '<h2 id="airlines-missing-title" class="text-heading airlines-missing__title">%s</h2>'
        '<p class="text-label section-caption">%s</p>%s</section>'
    ) % (modifier, escape_html(title_text(count)), escape_html(i18n.t(CAPTION_TEXT)), body)
    return markup, count
