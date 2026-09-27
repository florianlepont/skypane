"""Shared outbound-network helpers, used by more than one leaf module.

Currently one submodule, `safe_fetch`, holding the SSRF gate shared by
`server.plane.calendar_rules` (the calendar feed) and `server.notify`
(the ntfy topic).
"""
