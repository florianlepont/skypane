"""The render CLI's --layout option: classic by default, any layout id on request."""
import pytest

from server import screen_layouts
from server.plane.render import cli

FLIGHT_ARGS = ["--state", "departing", "--callsign", "AFR1789", "--hex", "3946a1"]


def _digest(capsys, *extra):
    assert cli.main(FLIGHT_ARGS + list(extra)) == 0
    out = capsys.readouterr().out
    return [line for line in out.splitlines() if "sha256" in line][-1].split("sha256")[-1].strip().split()[0]


def test_default_output_is_the_classic_layout(capsys):
    """omitting --layout and passing --layout classic produce the same bytes"""
    assert _digest(capsys) == _digest(capsys, "--layout", "classic")


def test_layout_b_differs_from_classic(capsys):
    """a giant layout draws a different packed image"""
    assert _digest(capsys, "--layout", "b") != _digest(capsys)


@pytest.mark.parametrize("layout_id", screen_layouts.LAYOUT_IDS)
def test_every_layout_id_is_accepted_and_writes_the_packed_image(tmp_path, layout_id):
    """--layout works together with theme and state options and writes --out"""
    out = tmp_path / "panel.bin"
    code = cli.main(FLIGHT_ARGS + ["--theme", "blue_light", "--layout", layout_id, "--out", str(out)])
    assert code == 0 and out.stat().st_size > 0


def test_unknown_layout_exits_nonzero_listing_valid_ids(capsys):
    """an invalid id is a usage error that names every valid id"""
    with pytest.raises(SystemExit) as raised:
        cli.main(FLIGHT_ARGS + ["--layout", "../x"])
    assert raised.value.code != 0
    err = capsys.readouterr().err
    for layout_id in screen_layouts.LAYOUT_IDS:
        assert layout_id in err
