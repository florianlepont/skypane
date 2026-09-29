#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Florian Lepont
# SPDX-License-Identifier: Apache-2.0
"""Byte-for-byte drift test between `firmware/tools/gen_fault_screen.py
--screen updating`'s output and the committed
`firmware/main/updating_screen_mask.h`. If this fails, the header was
hand-edited or `server/plane/render`'s `_build_updating_canvas` composition
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
    """firmware/main/updating_screen_mask.h is byte-for-byte identical to what firmware/tools/gen_fault_screen.py's render_header_text('updating') produces right now - regenerate in the CI-equivalent container (never this host's own venv) and commit its output if this fails"""
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
