import pytest

from server import screen_layouts as sl


def test_layout_ids():
    assert sl.LAYOUT_IDS == ("classic", "a", "b", "c", "a_diagonal")
    assert sl.CLASSIC_LAYOUT_ID == "classic"


def test_default_layout_is_b():
    assert sl.DEFAULT_LAYOUT_ID == "b", (
        "frames that chose no layout now show the whole aircraft centred, not the classic screen"
    )


@pytest.mark.parametrize("value", [None, "", "nope", "B", 3, b"a", ["a"], {}])
def test_unknown_input_gets_default(value):
    assert sl.normalise_layout_id(value) == sl.DEFAULT_LAYOUT_ID


@pytest.mark.parametrize("layout_id", sl.LAYOUT_IDS)
def test_known_ids_unchanged(layout_id):
    assert sl.normalise_layout_id(layout_id) == layout_id


def test_is_giant_layout():
    assert sl.is_giant_layout("classic") is False
    for layout_id in ("a", "b", "c", "a_diagonal"):
        assert sl.is_giant_layout(layout_id) is True
