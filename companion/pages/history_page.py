"""companion/pages/history_page.py — CFG-06 (flight-history log),
06-CONTEXT.md.

This plan (06-05) ships the CFG-06 empty state as a contract-complete
stub; plan 06-09 replaces it with a real
server.history_db.recent_runway_events() read rendered via
companion.layout.data_table().
"""
from companion.layout import empty_state

_NO_FLIGHTS_HEADING = "No flights yet."
_NO_FLIGHTS_BODY = (
    "No flights detected yet — check back after the next poll cycle.")


def render(ctx):
    return (
        '<h1 class="text-heading">History</h1>'
        + empty_state(_NO_FLIGHTS_HEADING, _NO_FLIGHTS_BODY)
    )
