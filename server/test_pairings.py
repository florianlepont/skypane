"""Behaviour tests for server/pairings.py: the theme-to-pairing mapping."""
import pytest

from server import panel_format
from server.pairings import PAIRING_FOR_THEME, PAIRINGS, pairing_for_theme
from server.themes import DEFAULT_THEME_ID, THEMES


def test_mapping_covers_every_theme_exactly():
    assert set(PAIRING_FOR_THEME) == set(THEMES)
    assert set(PAIRING_FOR_THEME.values()) <= set(PAIRINGS)


def test_every_registered_theme_has_a_pairing_by_colour():
    # Whatever the registry holds, a theme maps by its field or stripe colour.
    for theme_id, entry in THEMES.items():
        colour = entry["departing_index"]
        if colour == panel_format.IDX_WHITE:
            colour = entry.get("band_index", panel_format.IDX_WHITE)
        expected = {
            panel_format.IDX_WHITE: "white",
            panel_format.IDX_BLACK: "grey",
            panel_format.IDX_GREEN: "grey",
            panel_format.IDX_BLUE: "blue_light",
            panel_format.IDX_RED: "red_light",
            panel_format.IDX_YELLOW: "yellow_light",
        }[colour]
        assert pairing_for_theme(theme_id).id == expected, theme_id


def test_five_pairings_with_theme_ids():
    assert set(PAIRINGS) == {"grey", "blue_light", "red_light", "yellow_light", "white"}
    assert set(PAIRINGS) <= set(THEMES)
    assert set(PAIRING_FOR_THEME.values()) == set(PAIRINGS)


@pytest.mark.parametrize("theme_id,expected", [
    ("green", "grey"), ("green_light", "grey"), ("band_green_light", "grey"),
    ("black", "grey"), ("band_black", "grey"), ("grey", "grey"),
    ("blue", "blue_light"), ("blue_light", "blue_light"), ("band_blue", "blue_light"),
    ("band_blue_light", "blue_light"), ("band_blue_field", "blue_light"),
    ("red", "red_light"), ("red_light", "red_light"), ("band_red", "red_light"),
    ("band_red_field", "red_light"),
    ("yellow", "yellow_light"), ("yellow_light", "yellow_light"),
    ("white", "white"),
])
def test_theme_maps_to_expected_pairing(theme_id, expected):
    assert pairing_for_theme(theme_id).id == expected


@pytest.mark.parametrize("bad", [None, "", "sky", "nope"])
def test_unknown_theme_falls_back_to_default_pairing(bad):
    assert pairing_for_theme(bad) is pairing_for_theme(DEFAULT_THEME_ID)


def test_pairing_parameters():
    assert PAIRINGS["yellow_light"].field_lighten == 0.75
    assert PAIRINGS["white"].field_lighten is None
    assert PAIRINGS["white"].band_allowed is False
    for pid in ("grey", "blue_light", "red_light"):
        assert PAIRINGS[pid].field_lighten == 0.4
    assert [p.id for p in PAIRINGS.values() if p.small_text_dither_toward_black] == ["yellow_light"]
    assert [p.id for p in PAIRINGS.values() if not p.band_allowed] == ["white"]


def test_inks_are_panel_palette_names():
    for pairing in PAIRINGS.values():
        for name in (pairing.field_ink, pairing.lettering_ink):
            assert isinstance(getattr(panel_format, "IDX_" + name.upper(), None), int)
