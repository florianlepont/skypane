"""The Airlines resolve dialog used from another page (Health).

The dialog, its data-view-panel-* trigger vocabulary and the two-step flow (name, then artwork)
are owned by `companion/pages/airlines_page.py` and `companion/static/panel-lookup.js`. This
module adds only what a second page needs: triggers for its own links, the same dialog with a
hidden `return` field on the name form, a hidden trigger that reopens the dialog on the artwork
step, and the allow-list that says where a finished flow returns to. Stdlib plus the companion
modules below; no server package import beyond the manual-resolutions and illustrations stores
airlines_page already reads.
"""
import companion.i18n as i18n
import companion.layout as layout
from companion.layout import escape_html
from companion.pages import airline_sheet, airlines_page as ap
from server.plane import enrich, illustrations, manual_resolutions

# Where a finished resolve flow lands. The value travels as a hidden form field (name step) or a
# query parameter (artwork step) and is only ever looked up in `_RETURN_ROUTES`; a value outside
# it means Airlines, so no request can choose its own redirect target.
RETURN_FIELD = "return"
RETURN_HEALTH = "health"
_RETURN_ROUTES = {RETURN_HEALTH: layout.HEALTH_ROUTE}

# Which page started the flow; panel-lookup.js copies it into the name form's return field.
RETURN_ATTR = "data-view-panel-return"

_TRIGGER_VOCABULARY = (
    ap._VIEW_PANEL_SRC_ATTR, ap._VIEW_PANEL_CAPTION_ATTR, ap._VIEW_PANEL_HEADING_ATTR,
    ap._VIEW_PANEL_MODE_ATTR, ap._VIEW_PANEL_REPLACE_ACTION_ATTR, ap._VIEW_PANEL_MANUAL_ATTR,
    ap._VIEW_PANEL_SCOPE_ATTR, ap._VIEW_PANEL_RESOLVE_PREFIX_ATTR, ap._VIEW_PANEL_FIRST_SEEN_ATTR,
    ap._VIEW_PANEL_LAST_SEEN_ATTR, ap._VIEW_PANEL_COUNT_ATTR, ap._VIEW_PANEL_UPLOAD_ACTION_ATTR,
    ap._VIEW_PANEL_DELETE_ACTION_ATTR, ap._VIEW_PANEL_MANUAL_NOTE_ATTR, RETURN_ATTR,
) + airline_sheet.SHEET_ATTRS


def return_route(value):
    """The page a resolve flow returns to: the route `value` names in the fixed allow-list,
    otherwise Airlines. Never echoes `value`."""
    if isinstance(value, str) and value in _RETURN_ROUTES:
        return _RETURN_ROUTES[value]
    return ap.AIRLINES_ROUTE


def _return_query(return_target):
    """`return=<target>` for an upload action, or `""` when the target is Airlines."""
    return "%s=%s" % (RETURN_FIELD, return_target) if return_target in _RETURN_ROUTES else ""


def _trigger_attrs_html(escaped_values):
    """Every attribute of the trigger vocabulary, in a fixed order. Those `escaped_values`
    (already escaped, keyed by attribute name) does not name are present and empty, never
    omitted, so no earlier open can leak into this one."""
    unknown = set(escaped_values) - set(_TRIGGER_VOCABULARY)
    if unknown:
        raise KeyError(sorted(unknown))
    return "".join(
        '%s="%s" ' % (name, escaped_values.get(name, "")) for name in _TRIGGER_VOCABULARY)


def trigger_attrs_html(row, now, return_target):
    """The attributes that make an element open the dialog on the name step for the
    unresolved-prefix `row` (a registry tuple of prefix, count, first seen, last seen, example
    callsign). The values are the ones an Airlines gap card writes."""
    prefix, count, first_seen, last_seen, example_callsign = row
    escaped_prefix = escape_html(prefix)
    return _trigger_attrs_html({
        ap._VIEW_PANEL_CAPTION_ATTR: escape_html(example_callsign),
        ap._VIEW_PANEL_HEADING_ATTR: i18n.t(ap.RESOLVE_HEADING),
        ap._VIEW_PANEL_MODE_ATTR: ap._VIEW_PANEL_MODE_GAP,
        ap._VIEW_PANEL_SCOPE_ATTR: i18n.t(ap.RESOLVE_CAPTION_TEMPLATE) % escaped_prefix,
        ap._VIEW_PANEL_RESOLVE_PREFIX_ATTR: escaped_prefix,
        ap._VIEW_PANEL_FIRST_SEEN_ATTR: escape_html(ap._seen_attribute_text(first_seen, now)),
        ap._VIEW_PANEL_LAST_SEEN_ATTR: escape_html(ap._seen_attribute_text(last_seen, now)),
        ap._VIEW_PANEL_COUNT_ATTR: escape_html(count),
        RETURN_ATTR: escape_html(return_target),
    })


def step_b_trigger_html(state_dir, prefix_raw, return_target):
    """A hidden trigger that reopens the dialog on the artwork step for a prefix the owner has
    just named, or `""`. Emitted only for a prefix with an active manual entry whose artwork is
    still missing, judged from the registry alone; the query value is never echoed, so an
    unknown one matches nothing."""
    prefix = manual_resolutions.normalise_prefix(prefix_raw)
    if prefix is None:
        return ""
    entry = manual_resolutions.load_manual_resolutions(state_dir).get(prefix)
    if not isinstance(entry, dict) or enrich.static_airline_name_for_prefix(prefix):
        return ""
    name = entry.get("airline_name")
    key = manual_resolutions.illustration_key_for_name(name)
    if not key or illustrations.resolved_illustration_path(key, state_dir) is not None:
        return ""
    query = _return_query(return_target)
    upload_action = "%s%s.png%s" % (
        ap.ILLUSTRATION_ROUTE_PREFIX, escape_html(key), "?" + query if query else "")
    heading = i18n.t(ap.STEP_B_HEADING_TEMPLATE) % escape_html(name)
    attrs = _trigger_attrs_html({
        ap._VIEW_PANEL_HEADING_ATTR: heading,
        ap._VIEW_PANEL_MODE_ATTR: ap._VIEW_PANEL_MODE_NEEDS_ARTWORK,
        ap._VIEW_PANEL_MANUAL_ATTR: ap._VIEW_PANEL_MANUAL_ACTIVE,
        ap._VIEW_PANEL_RESOLVE_PREFIX_ATTR: escape_html(prefix),
        ap._VIEW_PANEL_UPLOAD_ACTION_ATTR: upload_action,
        ap._VIEW_PANEL_DELETE_ACTION_ATTR: ap._manual_delete_action(prefix),
        RETURN_ATTR: escape_html(return_target),
    })
    return '<a hidden href="%s?%s=%s" %saria-label="%s">%s</a>' % (
        ap.AIRLINES_ROUTE, ap.RESOLVE_QUERY_PARAM, escape_html(prefix), attrs, heading,
        escape_html(name))


def dialog_html():
    """The shared dialog for a page other than Airlines: the markup Airlines emits, plus the
    hidden return field on its name form, empty until a trigger fills it."""
    return ap._lightbox_html(
        name_form_hidden_html='<input type="hidden" name="%s" value="">' % RETURN_FIELD)
