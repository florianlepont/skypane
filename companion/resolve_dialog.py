# SPDX-License-Identifier: AGPL-3.0-only
"""The Airlines resolve dialog used from another page (Health).

The dialog, its data-view-panel-* trigger vocabulary and the two-step flow (name, then artwork)
are owned by `companion/pages/airlines_page.py` and `companion/static/panel-lookup.js`. This
module adds only what a second page needs: triggers for its own links, the same dialog with a
hidden `return` field on the name form, and the allow-list that says where a finished flow
returns to. Stdlib plus the companion modules below.
"""
from companion.pages import airline_sheet, airlines_page as ap

# Where a finished resolve flow lands. The value travels as a hidden form field (name step) or a
# query parameter (artwork step) and is only ever looked up in `_RETURN_ROUTES`; a value outside
# it means the Airline editor, so no request can choose its own redirect target.
RETURN_FIELD = "return"
RETURN_HEALTH = "health"
_RETURN_ROUTES = {RETURN_HEALTH: "/fleet?view=system"}

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
    otherwise the Airline editor. Never echoes `value`."""
    if isinstance(value, str) and value in _RETURN_ROUTES:
        return _RETURN_ROUTES[value]
    return ap.MANAGE_ROUTE


def with_query(route, query):
    """`route` (which may already carry a query) with `query` appended."""
    return "%s%s%s" % (route, "&" if "?" in route else "?", query)


def _return_query(return_target):
    """`return=<target>` for an upload action, or `""` when the target is the Airline editor."""
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


def dialog_html():
    """The shared dialog for a page other than Airlines: the markup Airlines emits, plus the
    hidden return field on its name form, empty until a trigger fills it."""
    return ap._lightbox_html(
        name_form_hidden_html='<input type="hidden" name="%s" value="">' % RETURN_FIELD)
