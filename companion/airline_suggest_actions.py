"""The Airlines editor's two suggestion routes (administrators only).

POST /airlines/suggest asks for the proposed name of one unidentified prefix
and answers with JSON `{"state", "html"}`: `html` is the prefix's row as the
page itself renders it, which the script swaps into place. The service is
called here, in the request's own thread, never while a page renders. The
prefix is checked against the live unresolved registry exactly like the
resolve route, and the row position is a bounded integer; anything else
answers `stale` and calls nothing.

POST /airlines/suggest/reject removes a suggestion (the editor's dialog
posts it as a plain form) and redirects back to the editor.

Neither route writes a manual name: only the resolve route does, after a
person pressed the check or typed a name. The response never carries the
key, the model's raw reply or the request.
"""
import json

from companion import airline_actions, device_scope
from companion.pages import airline_rows, airline_table, airlines_page
from server.plane import airline_suggest

# The row position a request may name (the editor shows far fewer rows).
MAX_INDEX = 999

STATE_STALE = "stale"
_ANSWER_STATES = (
    airline_suggest.STATE_SUGGESTED, airline_suggest.STATE_NONE,
    airline_suggest.STATE_FAILED, airline_suggest.STATE_BUSY, airline_suggest.STATE_OFF)

ACTION_REJECT = "airline.suggest_reject"


def _row_index(raw):
    if isinstance(raw, str) and raw.isascii() and raw.isdigit() and len(raw) <= 3:
        value = int(raw)
        if value <= MAX_INDEX:
            return value
    return None


def _send(handler, state, html=""):
    payload = json.dumps({"state": state, "html": html}).encode("utf-8")
    handler.send_bytes(200, "application/json; charset=utf-8", payload)


def handle_suggest(handler, match):
    """POST /airlines/suggest: the row of one unidentified prefix, with its
    suggestion when the service has one."""
    device = match.device
    form = handler.read_form()
    row = airlines_page.unresolved_row_for_prefix(device.state_dir, form.get("prefix"))
    index = _row_index(form.get("index"))
    if row is None or index is None:
        return _send(handler, STATE_STALE)
    prefix = row[0]
    root = handler.args.state_dir
    samples = airline_suggest.sample_callsigns(device.state_dir, prefix, row[4])
    result = airline_suggest.suggest_for_prefix(root, prefix, samples)
    suggestion = None
    if result.state == airline_suggest.STATE_SUGGESTED:
        suggestion = airline_rows.Suggestion(
            name=result.name,
            reject_action=device_scope.scoped(airlines_page.AIRLINE_SUGGEST_REJECT_ROUTE, "POST"))
    html = airline_table.suggest_row_html(
        airlines_page, index, row, handler.page_context(device).now, suggestion)
    state = result.state if result.state in _ANSWER_STATES else airline_suggest.STATE_NONE
    return _send(handler, state, html)


def handle_reject(handler, match):
    """POST /airlines/suggest/reject: drop the suggestion of a prefix; it is
    never asked again. Back to the editor either way."""
    device = match.device
    row = airlines_page.unresolved_row_for_prefix(
        device.state_dir, handler.read_form().get("prefix"))
    if row is not None and airline_suggest.reject(handler.args.state_dir, row[0]):
        airline_actions.record(handler, ACTION_REJECT, row[0])
    return handler._scoped_redirect(airlines_page.MANAGE_ROUTE)
