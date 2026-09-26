#!/usr/bin/env python3
"""byos_server.py's listen address and the absence of any secret in its
argv or environment.

Production runs byos behind Caddy with `--bind 127.0.0.1`; the default
stays 0.0.0.0 so the LAN stub flow keeps working. Enrolment is gated by
the per-device registry (devices.json, SHA-256 hashes only), so byos
needs no secret on its command line or in its environment - these tests
start it with neither and prove a registered frame still enrols.

The listening socket is read from /proc/net/tcp{,6}, so the socket tests
are Linux-only.
"""
import importlib.util
import json
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))

MAC = "aa:bb:cc:dd:ee:42"
# Deterministic 64-hex test fixture, never a real device's secret.
SECRET = "4" * 64

linux_only = pytest.mark.skipif(
    not sys.platform.startswith("linux"), reason="reads /proc")


def _load_registry_harness():
    # --import-mode=importlib keeps sibling test modules off sys.path, so
    # the registry test's Harness is loaded by path instead of imported.
    spec = importlib.util.spec_from_file_location(
        "test_devices_registry_harness", os.path.join(HERE, "test_devices_registry.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


registry = _load_registry_harness()


def _listen_addresses(port):
    """Return the hex local addresses of every TCP LISTEN socket on
    `port`, as /proc/net/tcp and /proc/net/tcp6 print them (for example
    '0100007F' for 127.0.0.1, '00000000' for 0.0.0.0)."""
    port_hex = "%04X" % port
    found = []
    for table in ("/proc/net/tcp", "/proc/net/tcp6"):
        try:
            with open(table) as fh:
                lines = fh.read().splitlines()[1:]
        except OSError:
            continue
        for line in lines:
            fields = line.split()
            local, state = fields[1], fields[3]
            addr, _, lport = local.rpartition(":")
            if lport == port_hex and state == "0A":  # 0A = TCP_LISTEN
                found.append(addr)
    return found


def _enrol(harness, secret):
    return registry.http_request(
        harness.base_url() + "/device/v1/setup", method="POST",
        json_body={"mac": MAC, "hw_rev": "test", "provision_secret": secret})


@pytest.fixture
def loopback_byos(tmp_path, monkeypatch):
    # The shared secret was retired; make sure nothing leaks one into the
    # child through the inherited environment either.
    monkeypatch.delenv("SKYPANE_BYOS_SECRET", raising=False)
    h = registry.Harness(tmp_path)
    h.register(MAC, SECRET)
    h.start(["--bind", "127.0.0.1"])
    try:
        yield h
    finally:
        h.stop()


@linux_only
def test_bind_loopback_listens_on_127_0_0_1_only(loopback_byos):
    assert _listen_addresses(loopback_byos.port) == ["0100007F"]
    assert "127.0.0.1:%d" % loopback_byos.port in loopback_byos.read_stdout()


@linux_only
def test_default_bind_is_all_interfaces(tmp_path):
    h = registry.Harness(tmp_path)
    h.start()
    try:
        assert _listen_addresses(h.port) == ["00000000"]
    finally:
        h.stop()


@linux_only
def test_no_secret_in_cmdline_or_environment(loopback_byos):
    pid = loopback_byos.proc.pid
    with open("/proc/%d/cmdline" % pid, "rb") as fh:
        argv = fh.read().split(b"\0")
    assert b"--secret" not in argv
    assert not any(SECRET.encode() in arg for arg in argv)
    with open("/proc/%d/environ" % pid, "rb") as fh:
        environ = fh.read()
    assert b"SKYPANE_BYOS_SECRET" not in environ
    assert SECRET.encode() not in environ


def test_registry_enrolment_works_on_loopback_bound_server(loopback_byos):
    status, _, body = _enrol(loopback_byos, SECRET)
    assert status == 200, body[:200]
    token = json.loads(body.decode())["device_token"]
    assert len(token) == 64

    status, _, _ = _enrol(loopback_byos, "5" * 64)
    assert status == 401
