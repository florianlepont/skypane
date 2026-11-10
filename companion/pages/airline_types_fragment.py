"""The Airlines editor's aircraft-type rows of one airline, served as a bare
fragment: the table lists each airline closed and airline-types.js asks for
the rows of a group when its chevron first opens, so the page does not carry
(and the server does not render) rows nobody opens."""
from urllib.parse import parse_qs, urlsplit

from companion.pages import airline_table, airlines_page

# Digits only and bounded: the value indexes the editor's airline list.
_MAX_DIGITS = 6


def requested_index(path):
    """The airline position asked for by `?types=<n>`, or None for any other
    request (no value, `all`, or anything that is not a short number)."""
    values = parse_qs(urlsplit(path).query).get(airline_table.TYPES_PARAM, [])
    value = values[0] if values else ""
    if value.isascii() and value.isdigit() and len(value) <= _MAX_DIGITS:
        return int(value)
    return None


def get(handler, device):
    """GET the editor: the fragment for `?types=<n>`, the page otherwise."""
    index = requested_index(handler.path)
    if index is None:
        return handler._render_tab(
            airlines_page.MANAGE_ROUTE, airlines_page.render, device)
    html = airlines_page.types_fragment(handler.page_context(device), index)
    return handler.send_html(200 if html else 404, html)
