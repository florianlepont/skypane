"""Shared outbound-network helpers, used by more than one leaf module.

Currently one submodule, `safe_fetch`, holding the SSRF gate the
calendar feed fetch in `server.plane.calendar_rules` calls.
"""
