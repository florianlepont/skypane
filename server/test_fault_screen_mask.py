#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Florian Lepont
# SPDX-License-Identifier: Apache-2.0
"""Byte-for-byte drift test between `firmware/tools/gen_fault_screen.py`'s
output and the committed `firmware/main/fault_screen_mask.h`. If this
fails, the header was hand-edited or `server/plane/render.py`'s
calm status composition changed without regenerating
it - the fix is always to rerun the generator, never to hand-patch the
header.

Loads the generator module via `importlib.util.spec_from_file_location`
(not a package import) because `firmware/tools/` is not part of the
`server` package and has no `__init__.py`, keeping the generator itself
free of any package-layout assumption.
"""
import importlib.util
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)

if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

GEN_SCRIPT_PATH = os.path.join(REPO_ROOT, "firmware", "tools", "gen_fault_screen.py")
HEADER_PATH = os.path.join(REPO_ROOT, "firmware", "main", "fault_screen_mask.h")


def _load_gen_module():
    spec = importlib.util.spec_from_file_location("gen_fault_screen", GEN_SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_fault_screen_mask_header_matches_generator_output():
    """firmware/main/fault_screen_mask.h is byte-for-byte identical to what firmware/tools/gen_fault_screen.py's render_header_text() produces right now - rerun the generator (server/.venv/bin/python3 firmware/tools/gen_fault_screen.py) and commit its output if this fails"""
    gen = _load_gen_module()
    expected = gen.render_header_text().encode("utf-8")

    if not os.path.isfile(HEADER_PATH):
        pytest.fail(
            "firmware/main/fault_screen_mask.h does not exist - run "
            "server/.venv/bin/python3 firmware/tools/gen_fault_screen.py to generate it"
        )

    with open(HEADER_PATH, "rb") as f:
        actual = f.read()

    if actual != expected:
        pytest.fail(
            "firmware/main/fault_screen_mask.h has drifted from "
            "firmware/tools/gen_fault_screen.py's current output (%d bytes committed vs "
            "%d bytes generated) - rerun: server/.venv/bin/python3 firmware/tools/gen_fault_screen.py, "
            "then commit the regenerated header" % (len(actual), len(expected))
        )


def test_fault_flat_canvas_has_exactly_two_colours():
    """the flat canvas the mask is cut from holds only black and white"""
    from server.plane.render.giant import status

    canvas = status.build_status("no_connection", (1200, 1600), flat=True)
    used = {idx for _count, idx in canvas.getcolors()}
    assert len(used) == 2


_PANEL_HEADERS = {
    "1200x1600": "fault_screen_mask.h",
    "800x480": "fault_screen_mask_800x480.h",
}


@pytest.mark.parametrize("panel", sorted(_PANEL_HEADERS))
def test_no_connection_header_matches_generator_for_each_panel(panel):
    """each committed no_connection header (portrait and 800x480) is byte-for-byte what the generator produces for that panel size"""
    gen = _load_gen_module()
    path = os.path.join(REPO_ROOT, "firmware", "main", _PANEL_HEADERS[panel])
    if not os.path.isfile(path):
        pytest.fail("%s does not exist - run firmware/tools/gen_fault_screen.py for this panel" % path)
    with open(path, "rb") as f:
        actual = f.read()
    expected = gen.render_header_text(panel=panel).encode("utf-8")
    assert actual == expected


def test_no_connection_default_panel_is_portrait_and_other_guard_is_distinct():
    """the default panel is the portrait one and the 800x480 header has its own include guard but the same symbol names"""
    gen = _load_gen_module()
    assert gen.DEFAULT_PANEL == "1200x1600"
    portrait = gen.render_header_text("no-connection")
    small = gen.render_header_text("no-connection", panel="800x480")
    guard_p = [ln for ln in portrait.splitlines() if ln.startswith("#ifndef")]
    guard_s = [ln for ln in small.splitlines() if ln.startswith("#ifndef")]
    assert guard_p != guard_s
    assert "800X480_H" in guard_s[0]
    for line in (ln for ln in portrait.splitlines() if ln.startswith("static const")):
        assert line in small.splitlines()


def test_no_connection_800x480_flat_canvas_has_two_colours_and_ink_fits():
    """the 800x480 flat canvas holds only black and white and its ink bounding box lies inside the panel"""
    from server.plane.render.giant import status

    canvas = status.build_status("no_connection", (800, 480), flat=True)
    assert canvas.size == (800, 480)
    used = {idx for _count, idx in canvas.getcolors()}
    assert len(used) == 2
    gen = _load_gen_module()
    x, y, w, h, _bits = gen.render_mask("no-connection", "800x480")
    assert x >= 0 and y >= 0 and x + w <= 800 and y + h <= 480
