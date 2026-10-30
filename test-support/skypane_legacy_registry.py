"""Registry documents in the pre-fleet on-disk shape: no hardware_type and
no build on any release, no top-level hardware_type.

Tests use these to prove a registry written before per-type documents
existed still loads and behaves identically.
"""

from __future__ import annotations

import hashlib
import json
import os

DEFAULT_VERSIONS = ("fw-v1.0.0", "fw-v1.0.1", "fw-v1.0.2")


def legacy_release(version, *, installed_at=()):
    sha = hashlib.sha256(version.encode()).hexdigest()
    return {
        "version": version, "sha256": sha, "size": 1000,
        "released_at": "2026-09-01", "published_at": "2026-09-01T00:00:00+00:00",
        "commit": "a" * 40, "notes": [], "bench": False,
        "installed_at": list(installed_at),
    }


def legacy_shaped_registry(releases=DEFAULT_VERSIONS, *, schedule=None, reconciled_seq=0):
    """The document dict; `releases` is a version list or ready entries."""
    entries = [legacy_release(r) if isinstance(r, str) else r for r in releases]
    return {
        "schema": 1, "floor_version": "fw-v1.0.0", "releases": entries,
        "schedule": schedule, "last_outcome": None,
        "reconciled_seq": reconciled_seq,
    }


def write_legacy_registry(state_dir, **kwargs):
    """Write registry.json in the legacy shape; returns its exact bytes."""
    directory = os.path.join(state_dir, "firmware")
    os.makedirs(directory, exist_ok=True)
    data = json.dumps(legacy_shaped_registry(**kwargs), indent=1, sort_keys=True)
    path = os.path.join(directory, "registry.json")
    with open(path, "w") as fh:
        fh.write(data)
    with open(path, "rb") as fh:
        return fh.read()
