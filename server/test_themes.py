#!/usr/bin/env python3
"""Contract tests for server/themes.py (the theme registry and its
presentation accessors) and for server/device_config.py's re-export of
that same registry/accessors by identity.

Never re-derives THEMES' own values here - device_config.THEMES is
supposed to be the exact same object as themes.THEMES, not an equal
copy, so every check below is an `is` identity check, not `==`.
"""
import json
import subprocess
import sys

import pytest

from skypane_test_support import REPO_ROOT, child_env

import server.device_config as device_config
import server.panel_format as panel_format
import server.themes as themes

_ACCESSOR_NAMES = (
    "theme_background_index",
    "theme_ink_index",
    "theme_label",
    "theme_dithered",
    "theme_weight",
    "theme_is_band",
    "theme_band_index",
    "theme_band_dithered",
)


def test_device_config_registry_names_are_themes_registry_names_by_identity():
    """device_config.THEMES is themes.THEMES; device_config.THEME_IDS is
    themes.THEME_IDS; device_config.DEFAULT_THEME_ID equals
    themes.DEFAULT_THEME_ID - the registry has exactly one owner."""
    if device_config.THEMES is not themes.THEMES:
        pytest.fail("device_config.THEMES is not themes.THEMES by identity")
    if device_config.THEME_IDS is not themes.THEME_IDS:
        pytest.fail("device_config.THEME_IDS is not themes.THEME_IDS by identity")
    if device_config.DEFAULT_THEME_ID != themes.DEFAULT_THEME_ID:
        pytest.fail(
            "device_config.DEFAULT_THEME_ID (%r) != themes.DEFAULT_THEME_ID (%r)"
            % (device_config.DEFAULT_THEME_ID, themes.DEFAULT_THEME_ID)
        )


def test_device_config_accessors_are_themes_accessors_by_identity():
    """Every one of the eight presentation accessors resolves to the exact
    same function object through device_config as through themes."""
    for name in _ACCESSOR_NAMES:
        via_device_config = getattr(device_config, name)
        via_themes = getattr(themes, name)
        if via_device_config is not via_themes:
            pytest.fail(
                "device_config.%s is not themes.%s by identity" % (name, name)
            )


def test_theme_background_index_matches_panel_format_constant_and_rejects_unknown_state():
    """themes.theme_background_index('departing'/'arriving', 'white') returns
    panel_format.IDX_WHITE either way, and an unknown state raises ValueError
    naming both the rejected value and the two accepted ones."""
    if themes.theme_background_index("departing", "white") != panel_format.IDX_WHITE:
        pytest.fail(
            "theme_background_index('departing', 'white') != IDX_WHITE, got %r"
            % (themes.theme_background_index("departing", "white"),)
        )
    if themes.theme_background_index("arriving", "white") != panel_format.IDX_WHITE:
        pytest.fail(
            "theme_background_index('arriving', 'white') != IDX_WHITE, got %r"
            % (themes.theme_background_index("arriving", "white"),)
        )
    raised = False
    try:
        themes.theme_background_index("hovering", "white")
    except ValueError as exc:
        raised = True
        message = str(exc)
        if "hovering" not in message or "departing" not in message or "arriving" not in message:
            pytest.fail("ValueError message %r did not name the rejected state and the two accepted ones" % (message,))
    if not raised:
        pytest.fail("theme_background_index('hovering', 'white') did not raise ValueError")


def test_importing_server_themes_in_a_subprocess_never_imports_pil():
    """`import server.themes` in a fresh subprocess never pulls PIL into
    sys.modules - themes.py is a leaf module over stdlib plus
    server.panel_format only, and panel_format itself has no imports."""
    script = (
        "import json, sys\n"
        "import server.themes\n"
        "banned = sorted(\n"
        "    m for m in sys.modules\n"
        "    if m == 'PIL' or m.startswith('PIL.')\n"
        ")\n"
        "print(json.dumps(banned))\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", script], env=child_env(), cwd=REPO_ROOT,
        capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stdout + result.stderr
    banned = json.loads(result.stdout.strip().splitlines()[-1])
    assert banned == [], (
        "importing server.themes pulled %r into sys.modules - this module "
        "must never import PIL" % (banned,))
