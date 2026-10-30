"""Shared setup for the per-device companion tests: an app subprocess serving
a seeded two-device fleet (plus a landscape device), and file snapshots that
ignore the harness's own bookkeeping files. Not a test module itself.
"""
import hashlib
import os
import sqlite3
from types import SimpleNamespace

from companion_app_server import http_request, login
from skypane_two_device_fleet import seed_two_device_fleet

__test__ = False

SIM_ENV = {"SKYPANE_SIM_HARDWARE": "1"}
# Written by the test harness or by SQLite itself, never by application code.
_IGNORED_NAMES = ("app.stdout.log",)
_IGNORED_PREFIXES = ("fake-providers.json",)
_IGNORED_SUFFIXES = ("-wal", "-shm")
_DEVICES_DIRNAME = "devices"


def _ignored(name):
    return (
        name in _IGNORED_NAMES or name.startswith(_IGNORED_PREFIXES)
        or name.endswith(_IGNORED_SUFFIXES))


def _database_digest(path):
    """Digest of a SQLite database's logical content. The main file's bytes and
    mtime change whenever SQLite checkpoints its write-ahead log, which can
    happen after a request has already answered, so they say nothing about
    whether any row changed."""
    conn = sqlite3.connect("file:%s?mode=ro" % path, uri=True, timeout=10)
    try:
        dump = "\n".join(conn.iterdump())
    finally:
        conn.close()
    return hashlib.sha256(dump.encode("utf-8")).hexdigest()


def snapshot(path):
    """Relative file path -> (sha256, mtime_ns) for the files under `path` (a database file: the digest of
    its rows and mtime 0),
    without harness logs, SQLite sidecar files (the app may create or delete
    them while this walks) and the `devices/` subtree: every device directory
    is snapshotted on its own, so the live root's snapshot covers only the
    live frame's own files."""
    out = {}
    for root, dirs, files in os.walk(path):
        if root == path and _DEVICES_DIRNAME in dirs:
            dirs.remove(_DEVICES_DIRNAME)
        for name in files:
            if _ignored(name):
                continue
            full = os.path.join(root, name)
            relative = os.path.relpath(full, path)
            if name.endswith(".db"):
                out[relative] = (_database_digest(full), 0)
                continue
            with open(full, "rb") as fh:
                digest = hashlib.sha256(fh.read()).hexdigest()
            out[relative] = (digest, os.stat(full).st_mtime_ns)
    return out


def snapshot_all(server, fleet):
    """Snapshots of the live root, device A and device B, in that order."""
    return (
        snapshot(server.state_dir), snapshot(fleet.dev_a.state_dir),
        snapshot(fleet.dev_b.state_dir))


def start_fleet_app(make_app_server, seed_extra=None, fake_providers=False):
    """(server, fleet, session cookie) for a freshly seeded fleet.

    `seed_extra(fleet)` runs after the fleet exists and before the server
    starts. The simulated hardware gate is on for the app process.
    """
    holder = {}

    def seed(state_dir):
        fleet = seed_two_device_fleet(state_dir, with_landscape=True)
        if seed_extra is not None:
            seed_extra(fleet)
        holder["fleet"] = fleet

    server = make_app_server(
        seed=seed, env_overrides=SIM_ENV, fake_providers=fake_providers)
    cookie = login(server)
    return SimpleNamespace(server=server, fleet=holder["fleet"], cookie=cookie)


def get(app, path):
    status, headers, body = http_request(app.server.base_url() + path, cookie=app.cookie)
    return status, headers, body.decode("utf-8", "replace")


def post(app, path, form=None, headers=None):
    import urllib.parse
    data = urllib.parse.urlencode(form or {}).encode()
    status, response_headers, body = http_request(
        app.server.base_url() + path, method="POST", data=data, cookie=app.cookie,
        extra_headers=headers)
    return status, response_headers, body.decode("utf-8", "replace")
