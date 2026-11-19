"""The airlines known by name only, as read-only rows of the Airlines editor.

An airline whose name the application knows from its callsign prefix but
that has no artwork has no row in the table: it is listed in its own block,
one row each with the name, the prefix and an "Artwork" button. The button
opens the shared add-artwork step (the same trigger an owner-named airline
without artwork uses), so nothing here stores anything and no route is
added: the rows have no form of their own. Names reach the markup only
through `escape_html`.
"""
import companion.i18n as i18n
import companion.layout as layout
from companion.layout import escape_html
from companion.pages import airline_rows
from server.plane import enrich, illustrations, manual_resolutions

KNOWN_TEXT = i18n.msg("airlines.known_by_name_label", "Known by name only")
ADD_TEXT = i18n.msg("airlines.known_add_artwork", "Artwork")
ADD_ARIA = i18n.msg("airlines.known_add_artwork_aria", "Add the first artwork for %s")

# The page's add-artwork step has no aircraft type of its own to name: it
# is the airline-level one.
_NO_MANUAL_FIELDS = ("art", False, False, "", "", "", "", "", "", "", "", "")


def rows(state_dir, registry):
    """The `(prefix, name)` pairs still known by name only, sorted by name:
    an airline that has artwork (its own or an uploaded one), or whose prefix
    the owner has named by hand, is no longer listed."""
    registry = registry or {}
    pairs = []
    for prefix, name in enrich.names_without_artwork():
        key = manual_resolutions.illustration_key_for_name(name)
        if prefix in registry or not key:
            continue
        if illustrations.resolved_illustration_path(key, state_dir) is not None:
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
        if illustrations.resolved_illustration_path(key, state_dir) is not None:
            found[name] = prefix
    return found


def caption_text(count):
    return "%s · %d" % (i18n.t(KNOWN_TEXT), count)


def _add_button(page, state_dir, name):
    key = manual_resolutions.illustration_key_for_name(name)
    card = {
        "name": name, "state_dir": state_dir, "sheet": None,
        "manual_fields": _NO_MANUAL_FIELDS, "types": [],
    }
    inner = '%s<span class="airlines-known__text">%s</span>' % (
        layout.icon_html("icon-plus", 20), escape_html(i18n.t(ADD_TEXT)))
    return page._type_trigger_html(
        card, page.ANY_TYPE_ID, name, key, "btn btn--secondary airlines-known__add", inner,
        i18n.t(ADD_ARIA) % name, extra_attrs='%s="" ' % page.ASK_TYPE_ATTR)


def group_html(page, index, state_dir, prefix, name):
    """One known-by-name airline as a `<tbody>`: the name over the prefix and
    the button that adds its first artwork."""
    return (
        '<tbody class="airline-group airline-group--known" data-filter-text="%s" '
        'data-filter-group="known%d" data-filter-kind="%s"><tr class="airlines-row airlines-row--gap">'
        '<th scope="row" colspan="6" class="airlines-cell airlines-cell--resolve">'
        '<div class="airlines-known"><span class="airlines-known__who">'
        '<span class="airlines-known__name">%s</span>'
        '<span class="airlines-known__prefix mono">%s</span></span>%s</div></th></tr></tbody>'
    ) % (escape_html(("%s %s" % (name, prefix)).lower()), index, airline_rows.KIND_KNOWN,
         escape_html(name), escape_html(prefix), _add_button(page, state_dir, name))


def table_html(page, state_dir, pairs):
    """The block of every known-by-name airline: a captioned table of rows."""
    if not pairs:
        return ""
    body = "".join(
        group_html(page, index, state_dir, prefix, name)
        for index, (prefix, name) in enumerate(pairs))
    return (
        '<table class="airlines-table airlines-table--gaps airlines-table--known">'
        '<caption class="airlines-label">%s</caption>%s</table>'
    ) % (escape_html(caption_text(len(pairs))), body)
