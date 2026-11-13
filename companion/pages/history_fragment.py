"""The Flights list served as a bare fragment: list-filter.js asks for the
list alone when a search, a chip or the sort changes, and for the next
flights alone on Load more, so neither answer carries the page around the
list or the flights already on screen. Any other request is the page."""
from urllib.parse import parse_qs, urlsplit

import companion.layout as layout
from companion.pages import history_page


def requested_part(path):
    """The part `?part=` names, or None for the plain page (no value, or one
    that is not a known part)."""
    values = parse_qs(urlsplit(path).query).get(history_page.PART_PARAM, [])
    return values[0] if values and values[0] in history_page.PARTS else None


def get(handler, device):
    """GET Flights: the fragment for `?part=<known part>`, the page otherwise."""
    part = requested_part(handler.path)
    if part is None:
        return handler._render_tab(layout.FLIGHTS_ROUTE, history_page.render, device)
    return handler.send_html(
        200, history_page.render_part(handler.page_context(device), part))
