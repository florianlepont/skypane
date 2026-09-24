#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Florian Lepont
# SPDX-License-Identifier: Apache-2.0
"""Quick task 260924-u7n (DEVICE-06): byte-for-byte drift test between
`firmware/tools/gen_fault_screen.py`'s output and the committed
`firmware/main/fault_screen_mask.h` (T-u7n-03). If this fails, the header
was hand-edited or `server/plane/render.py`'s `_build_no_connection_canvas`
composition changed without regenerating it - the fix is always to rerun
the generator, never to hand-patch the header.

Loads the generator module via `importlib.util.spec_from_file_location`
(not a package import) because `firmware/tools/` is not part of the
`server` package and has no `__init__.py` - this is the same loading
technique the plan calls for, and it keeps the generator itself free of
any package-layout assumption.
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
