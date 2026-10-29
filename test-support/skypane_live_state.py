"""Synthetic, production-shaped state directory for migration tests.

Every value generated here is synthetic. The shapes match the files a live
frame leaves in its state directory (registry, token store, device config,
poll state, battery reading, firmware device report, panel image). Real
state files live only on the VPS; an owner may export a sanitised copy and
point SKYPANE_LIVE_STATE_COPY at it to replay against that instead. Unset
(the default, and always in CI) means the synthetic fixture.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
from types import SimpleNamespace

from server import atomic_io, state_store

COPY_ENV_VAR = "SKYPANE_LIVE_STATE_COPY"

DEFAULT_MAC = "aa:bb:cc:dd:ee:01"
DEFAULT_SECRET_HEX = "0123456789abcdef" * 4
DEFAULT_TOKEN = "tok-" + "f" * 40

_PANEL_BYTES = 960000


def secret_hash(secret_hex: str) -> str:
    """The registry stores the SHA-256 hex digest of the enrolment secret."""
    return hashlib.sha256(secret_hex.encode("ascii")).hexdigest()


def _write_json(path: str, doc: object) -> None:
    atomic_io.atomic_write(path, json.dumps(doc, indent=1))


def _copy_identity(src: str, state_dir: str) -> SimpleNamespace:
    shutil.copytree(src, state_dir, dirs_exist_ok=True)
    with open(os.path.join(state_dir, "devices.json"), encoding="utf-8") as fh:
        registry = json.load(fh)
    with open(os.path.join(state_dir, "byos_state.json"), encoding="utf-8") as fh:
        tokens = json.load(fh)["tokens"]
    mac = sorted(registry["devices"])[0]
    return _namespace(state_dir, mac, None, tokens.get(mac))


def _namespace(
    state_dir: str, mac: str, secret_hex: str | None, token: str | None
) -> SimpleNamespace:
    return SimpleNamespace(
        state_dir=state_dir,
        mac=mac,
        secret_hex=secret_hex,
        token=token,
        devices_path=os.path.join(state_dir, "devices.json"),
        state_path=os.path.join(state_dir, "byos_state.json"),
    )


def seed_live_like_state(
    state_dir: str,
    mac: str = DEFAULT_MAC,
    secret_hex: str = DEFAULT_SECRET_HEX,
    token: str = DEFAULT_TOKEN,
) -> SimpleNamespace:
    """Populate `state_dir` like a live frame's state directory."""
    copy = os.environ.get(COPY_ENV_VAR)
    if copy:
        return _copy_identity(copy, state_dir)
    os.makedirs(state_dir, exist_ok=True)
    _write_json(
        os.path.join(state_dir, "devices.json"),
        {"devices": {mac: {"secret_sha256": secret_hash(secret_hex)}}},
    )
    _write_json(os.path.join(state_dir, "byos_state.json"), {"tokens": {mac: token}})
    _write_json(os.path.join(state_dir, "device_config.json"), {"wake_interval_s": 1800})
    state_store.save_poll_state(state_dir, {"hold": None})
    _write_json(
        os.path.join(state_dir, "battery_state.json"),
        {"battery_mv": 3987, "received_at": 1790000000.0},
    )
    fw_dir = os.path.join(state_dir, "firmware")
    os.makedirs(fw_dir, exist_ok=True)
    _write_json(
        os.path.join(fw_dir, "device_report.json"),
        {
            "schema": 1,
            "next_seq": 0,
            "devices": {"default": {"events": []}, mac: {"events": []}},
        },
    )
    pattern = bytes(range(1, 251))
    panel = (pattern * (_PANEL_BYTES // len(pattern) + 1))[:_PANEL_BYTES]
    atomic_io.atomic_write(os.path.join(state_dir, "panel.bin"), panel)
    return _namespace(state_dir, mac, secret_hex, token)


def snapshot_dir(path: str) -> dict[str, tuple[str, int]]:
    """Relative file path -> (sha256, mtime_ns) for every file under `path`."""
    out: dict[str, tuple[str, int]] = {}
    for root, _dirs, files in os.walk(path):
        for name in files:
            full = os.path.join(root, name)
            with open(full, "rb") as fh:
                digest = hashlib.sha256(fh.read()).hexdigest()
            out[os.path.relpath(full, path)] = (digest, os.stat(full).st_mtime_ns)
    return out
