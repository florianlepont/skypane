import json
import os

import pytest

from server import device_config as dc
from server import screen_layouts as sl

# Bytes the saver wrote for a default configuration before the layout key existed.
GOLDEN_DEFAULT_BYTES = """{
 "theme": "white",
 "theme_arriving": null,
 "calendar_theme_id": null,
 "tracked_runway": "3",
 "led_enabled": true,
 "quiet_hours_enabled": false,
 "quiet_hours_start": "23:00",
 "quiet_hours_end": "07:00",
 "wake_interval_s": null,
 "display_enabled": true
}"""


def _read(state_dir):
    with open(dc.device_config_path(state_dir)) as fh:
        return fh.read()


def test_missing_file_loads_default_layout(tmp_path):
    assert dc.load_device_config(str(tmp_path))["layout"] == sl.DEFAULT_LAYOUT_ID


def test_file_without_key_loads_default_layout(tmp_path):
    with open(dc.device_config_path(str(tmp_path)), "w") as fh:
        json.dump({"theme": "white"}, fh)
    assert dc.load_device_config(str(tmp_path))["layout"] == sl.DEFAULT_LAYOUT_ID


@pytest.mark.parametrize("stored", ["nope", 5, None, ["a"]])
def test_unknown_stored_layout_normalises_on_load(tmp_path, stored):
    with open(dc.device_config_path(str(tmp_path)), "w") as fh:
        json.dump({"layout": stored}, fh)
    assert dc.load_device_config(str(tmp_path))["layout"] == sl.DEFAULT_LAYOUT_ID


def test_save_without_layout_keeps_golden_bytes(tmp_path):
    state_dir = str(tmp_path)
    dc.save_device_config(state_dir, theme=dc.DEFAULT_THEME_ID)
    assert _read(state_dir) == GOLDEN_DEFAULT_BYTES
    dc.save_device_config(state_dir, led_enabled=True)
    assert _read(state_dir) == GOLDEN_DEFAULT_BYTES


@pytest.mark.parametrize("layout_id", ["classic", "a", "c", "a_diagonal"])
def test_round_trip(tmp_path, layout_id):
    state_dir = str(tmp_path)
    dc.save_device_config(state_dir, layout=layout_id)
    assert dc.load_device_config(state_dir)["layout"] == layout_id
    assert '"layout": "%s"' % layout_id in _read(state_dir)


def test_layout_carries_forward(tmp_path):
    state_dir = str(tmp_path)
    dc.save_device_config(state_dir, layout="classic")
    dc.save_device_config(state_dir, led_enabled=False)
    assert dc.load_device_config(state_dir)["layout"] == "classic"


def test_saving_default_layout_removes_key(tmp_path):
    state_dir = str(tmp_path)
    dc.save_device_config(state_dir, layout="a")
    dc.save_device_config(state_dir, layout=sl.DEFAULT_LAYOUT_ID)
    assert '"layout"' not in _read(state_dir)


@pytest.mark.parametrize("bad", ["nope", "", 3, ["a"]])
def test_unknown_layout_rejected_without_writing(tmp_path, bad):
    state_dir = str(tmp_path)
    with pytest.raises(ValueError) as excinfo:
        dc.save_device_config(state_dir, layout=bad)
    if bad == "nope":
        assert "nope" not in str(excinfo.value)
    assert not os.path.exists(dc.device_config_path(state_dir))
