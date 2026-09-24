"""Shared seeding helpers for the `companion/test_config_page*.py`
migration chain (33-09..33-13). Not a test module itself — `__test__ =
False` keeps pytest from ever collecting it directly, and
`companion/test_suite_guards.py`'s G9 rule enforces that this marker is
present.

The original `companion/test_config_page.py`'s subprocess-lifecycle
plumbing (the legacy harness class, its HTTP client and its
non-redirect-following opener) is deliberately NOT ported here: migrated
tests that need a real `companion/app.py` server get one from
`companion/conftest.py`'s `app_server` / `module_app_server_factory`
fixtures instead, and every other check in this chain calls
`companion.pages.config_page`'s own functions directly, in-process,
against a `tmp_path`-backed state directory.
"""
import json
import os

from server import device_config

__test__ = False


def write_device_config(state_dir, theme, tracked_runway, led_enabled=None):
    """Write a minimal device_config.json directly (bypassing
    handle_post(), the code path most checks in this chain exercise) so a
    check can seed a starting on-disk state before calling the function
    under test."""
    state_dir = str(state_dir)
    os.makedirs(state_dir, exist_ok=True)
    doc = {"theme": theme, "tracked_runway": tracked_runway}
    if led_enabled is not None:
        doc["led_enabled"] = led_enabled
    with open(device_config.device_config_path(state_dir), "w") as fh:
        json.dump(doc, fh)
