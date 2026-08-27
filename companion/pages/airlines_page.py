"""companion/pages/airlines_page.py — CFG-04 (unresolved-prefix registry,
read-only) and CFG-08 (resolution statistics), 06-CONTEXT.md.

D-16: read-only by design. This module must never emit a form element or
a button element — there is no "mark resolved" action, now or in a later
plan; the user resolves entries manually elsewhere (the existing
quick-task runbook), and this page only makes the registry visible. This plan
(06-05) ships the CFG-04 good-news empty state and a Resolution
Statistics section heading as a contract-complete stub; plan 06-08
replaces both with real reads of poll_state.json's unresolved_prefixes
registry and server.history_db.route_source_counts().
"""
from companion.layout import empty_state

_NO_GAPS_HEADING = "No coverage gaps."
_NO_GAPS_BODY = (
    "No unresolved callsign prefixes — airline coverage looks complete.")


def render(ctx):
    return (
        '<h1 class="text-heading">Airlines</h1>'
        + empty_state(_NO_GAPS_HEADING, _NO_GAPS_BODY)
        + '<section class="page-section">'
        '<h2 class="text-heading">Resolution statistics</h2>'
        '<p class="text-body">Not yet wired.</p>'
        "</section>"
    )
