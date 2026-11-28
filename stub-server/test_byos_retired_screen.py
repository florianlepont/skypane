#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
"""An already-retired frame picks up the current retired screen at its next
wake: an old cached retired.bin is never served, and the wake interval stays."""
import hashlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
for _p in (REPO_ROOT, HERE, os.path.join(REPO_ROOT, "test-support")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import byos_server  # noqa: E402
import pytest  # noqa: E402
import test_pending_pairing as pending  # noqa: E402
from server import fleet_ops, hardware, pairing_code, pairing_image  # noqa: E402

PANEL_BYTES = 960000
_fetch_image = pending._fetch_image


@pytest.fixture
def world(tmp_path):
    w = pending.World(str(tmp_path))
    yield w
    w.server.stop()


def _retire(world):
    world.enrol()
    world.sql("UPDATE pending_devices SET status = 'retired', retired_at = 5 "
              "WHERE id = ?", (world.pending_id,))


def _dir(world):
    return fleet_ops.pairing_dir(world.state_dir, world.pending_id)


def test_old_cached_retired_panel_is_replaced_and_interval_unchanged(world):
    _retire(world)
    directory = _dir(world)
    os.makedirs(directory, exist_ok=True)
    old = os.path.join(directory, "retired.bin")
    with open(old, "wb") as fh:
        fh.write(b"\x11" * PANEL_BYTES)
    status, doc = world.poll()
    assert status == 200
    assert doc["sleep_s"] == pairing_code.RETIRED_SLEEP_S == 86400
    profile = hardware.get_profile(hardware.LEGACY_KEY)
    expected = pairing_image.render_retired_image(profile)
    assert _fetch_image(world, doc) == expected
    assert doc["image_hash"] != hashlib.sha256(b"\x11" * PANEL_BYTES).hexdigest()
    assert not os.path.exists(old)
    assert os.path.exists(os.path.join(directory, byos_server.RETIRED_PANEL))


def test_second_poll_serves_the_cached_new_render(world):
    _retire(world)
    _, first = world.poll()
    cached = os.path.join(_dir(world), byos_server.RETIRED_PANEL)
    marker = b"\x00" * PANEL_BYTES
    with open(cached, "wb") as fh:
        fh.write(marker)
    _, second = world.poll()
    assert _fetch_image(world, second) == marker
    assert second["sleep_s"] == 86400
    assert first["image_hash"] != second["image_hash"]
