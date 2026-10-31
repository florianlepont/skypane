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


_ALL_INKS = frozenset(range(6))

_THEME_SNAPSHOT = {
    "white": (1, 1, 0, None), "black": (0, 0, 1, None),
    "grey": (0, 0, 1, None), "yellow": (2, 2, 0, None),
    "yellow_light": (2, 2, 0, None), "red": (3, 3, 1, None),
    "red_light": (3, 3, 1, None), "green": (5, 5, 1, None),
    "green_light": (5, 5, 1, None), "blue": (4, 4, 1, None),
    "blue_light": (4, 4, 1, None), "band_blue": (1, 1, 0, 4),
    "band_blue_light": (1, 1, 0, 4), "band_green_light": (1, 1, 0, 5),
    "band_red": (1, 1, 0, 3), "band_black": (1, 1, 0, 0),
    "band_blue_field": (4, 4, 1, 4), "band_red_field": (3, 3, 1, 3),
}


def test_theme_ids_and_indices_match_pinned_snapshot():
    assert list(themes.THEME_IDS) == list(_THEME_SNAPSHOT)
    for tid, (dep, arr, ink, band) in _THEME_SNAPSHOT.items():
        assert (
            themes.theme_background_index("departing", tid),
            themes.theme_background_index("arriving", tid),
            themes.theme_ink_index(tid),
            themes.theme_band_index(tid),
        ) == (dep, arr, ink, band)


def test_required_inks_of_white_and_union_rule():
    assert themes.theme_required_inks("white") == {
        panel_format.IDX_BLACK, panel_format.IDX_WHITE}
    for tid in themes.THEME_IDS:
        expected = {
            themes.theme_background_index("departing", tid),
            themes.theme_background_index("arriving", tid),
            themes.theme_ink_index(tid),
            panel_format.IDX_WHITE,
        }
        band = themes.theme_band_index(tid)
        if band is not None:
            expected.add(band)
        assert themes.theme_required_inks(tid) == expected


def test_themes_for_inks_all_six_offers_every_theme_in_order():
    assert themes.themes_for_inks(_ALL_INKS) == themes.THEME_IDS
    assert len(themes.THEME_IDS) == len(_THEME_SNAPSHOT)


def test_reduced_ink_set_filters_and_falls_back_to_white():
    inks = frozenset({panel_format.IDX_BLACK, panel_format.IDX_WHITE})
    offered = themes.themes_for_inks(inks)
    assert "white" in offered and "black" in offered
    assert "red" not in offered and "band_blue" not in offered
    assert themes.theme_or_default("black", inks) == "black"
    assert themes.theme_or_default("red", inks) == "white"
    assert themes.theme_or_default("band_blue", inks) == "white"


def test_theme_or_default_handles_unknown_ids():
    assert themes.theme_or_default("sky", _ALL_INKS) == themes.DEFAULT_THEME_ID
    assert themes.theme_or_default("", _ALL_INKS) == themes.DEFAULT_THEME_ID
    assert themes.theme_or_default("red", _ALL_INKS) == "red"


def test_importing_server_themes_does_not_import_hardware():
    script = (
        "import sys\n"
        "import server.themes\n"
        "print('server.hardware' in sys.modules)\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", script], env=child_env(), cwd=REPO_ROOT,
        capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.strip().splitlines()[-1] == "False"
