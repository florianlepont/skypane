#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Florian Lepont
# SPDX-License-Identifier: Apache-2.0
"""Byte-for-byte drift test between `firmware/tools/gen_fault_screen.py
--screen updating`'s output and the committed
`firmware/main/updating_screen_mask.h`. If this fails, the header was
hand-edited or calm status composition
changed without regenerating it - the fix is always to rerun the
generator, never to hand-patch the header. The generator embeds
Pillow-rendered text, so it must be rerun in a Linux container with
libraqm installed (python:3.14 + `apt-get install libraqm0`), matching
CI -- this host's own venv (no libraqm on macOS) renders the same text a
pixel off and would only fail CI again. Mirrors
server/test_fault_screen_mask.py's shape for the sibling NO CONNECTION
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
HEADER_PATH = os.path.join(REPO_ROOT, "firmware", "main", "updating_screen_mask.h")


def _load_gen_module():
    spec = importlib.util.spec_from_file_location("gen_fault_screen", GEN_SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_REGEN_HINT = (
    "regenerate in a Linux container with libraqm installed (python:3.14, "
    "apt-get install libraqm0), matching CI -- never this host's own venv "
    "(no libraqm on macOS renders the same text a pixel off and would only "
    "fail CI again): run `firmware/tools/gen_fault_screen.py --screen "
    "updating` inside that container, then commit the regenerated header"
)


def test_updating_screen_mask_header_matches_generator_output():
    """firmware/main/updating_screen_mask.h is byte-for-byte identical to what firmware/tools/gen_fault_screen.py's render_header_text("updating") produces right now - regenerate in the CI-equivalent container (never this host's own venv) and commit its output if this fails"""
    gen = _load_gen_module()
    expected = gen.render_header_text("updating").encode("utf-8")

    if not os.path.isfile(HEADER_PATH):
        pytest.fail(
            "firmware/main/updating_screen_mask.h does not exist - %s" % _REGEN_HINT)

    with open(HEADER_PATH, "rb") as f:
        actual = f.read()

    if actual != expected:
        pytest.fail(
            "firmware/main/updating_screen_mask.h has drifted from "
            "firmware/tools/gen_fault_screen.py --screen updating's current output "
            "(%d bytes committed vs %d bytes generated) - %s"
            % (len(actual), len(expected), _REGEN_HINT)
        )


def test_updating_flat_canvas_has_exactly_two_colours():
    """the flat canvas the mask is cut from holds only black and white"""
    from server.plane.render.giant import status

    canvas = status.build_status("updating", (1200, 1600), flat=True)
    used = {idx for _count, idx in canvas.getcolors()}
    assert len(used) == 2


_PANEL_HEADERS = {
    "1200x1600": "updating_screen_mask.h",
    "800x480": "updating_screen_mask_800x480.h",
}


@pytest.mark.parametrize("panel", sorted(_PANEL_HEADERS))
def test_updating_header_matches_generator_for_each_panel(panel):
    """each committed updating header (portrait and 800x480) is byte-for-byte what the generator produces for that panel size"""
    gen = _load_gen_module()
    path = os.path.join(REPO_ROOT, "firmware", "main", _PANEL_HEADERS[panel])
    if not os.path.isfile(path):
        pytest.fail("%s does not exist - run firmware/tools/gen_fault_screen.py for this panel" % path)
    with open(path, "rb") as f:
        actual = f.read()
    expected = gen.render_header_text("updating", panel=panel).encode("utf-8")
    assert actual == expected


def test_updating_default_panel_is_portrait_and_other_guard_is_distinct():
    """the default panel is the portrait one and the 800x480 header has its own include guard but the same symbol names"""
    gen = _load_gen_module()
    assert gen.DEFAULT_PANEL == "1200x1600"
    portrait = gen.render_header_text("updating")
    small = gen.render_header_text("updating", panel="800x480")
    guard_p = [ln for ln in portrait.splitlines() if ln.startswith("#ifndef")]
    guard_s = [ln for ln in small.splitlines() if ln.startswith("#ifndef")]
    assert guard_p != guard_s
    assert "800X480_H" in guard_s[0]
    for line in (ln for ln in portrait.splitlines() if ln.startswith("static const")):
        assert line in small.splitlines()


def test_updating_800x480_flat_canvas_has_two_colours_and_ink_fits():
    """the 800x480 flat canvas holds only black and white and its ink bounding box lies inside the panel"""
    from server.plane.render.giant import status

    canvas = status.build_status("updating", (800, 480), flat=True)
    assert canvas.size == (800, 480)
    used = {idx for _count, idx in canvas.getcolors()}
    assert len(used) == 2
    gen = _load_gen_module()
    x, y, w, h, _bits = gen.render_mask("updating", "800x480")
    assert x >= 0 and y >= 0 and x + w <= 800 and y + h <= 480
