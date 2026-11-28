# SPDX-License-Identifier: AGPL-3.0-only
"""Shared outbound-network helpers, used by more than one leaf module.

Currently one submodule, `safe_fetch`, holding the SSRF gate the
calendar feed fetch in `server.plane.calendar_rules` calls.
"""
