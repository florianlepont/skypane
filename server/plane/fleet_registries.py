#!/usr/bin/env python3
"""The frame state directories of a fleet.

The three airline registries and the artwork directory live once, at the
fleet root (the live frame's directory); every reader resolves a frame's
directory to that root through `device_dirs.fleet_root_for`. What remains
here is the listing of the frame directories, used by the readers that add
up per-frame data (the sightings of every frame's history.db).
"""
from __future__ import annotations

import os

from server import device_dirs

LIVE_LABEL = "live"


def frame_state_dirs(root: str) -> list[tuple[str, str]]:
    """`(frame label, directory)`: the root (the live frame) first, then every
    valid `devices/<id>` directory in sorted id order. A directory whose name
    is not a device id, a symlink, or one resolving outside `devices/` is
    skipped through the same rules as `device_dirs.resolve_state_dir`."""
    frames = [(LIVE_LABEL, root)]
    devices = os.path.join(root, device_dirs.DEVICES_DIRNAME)
    try:
        names = sorted(os.listdir(devices))
    except OSError:
        return frames
    real_devices = device_dirs.real_devices_dir(root)
    for name in names:
        if not device_dirs.is_valid_device_id(name):
            continue
        try:
            directory = device_dirs.resolve_state_dir(
                root, device_dirs.state_path_for(name), real_devices)
        except ValueError:
            continue
        if os.path.isdir(directory):
            frames.append((name, directory))
    return frames
