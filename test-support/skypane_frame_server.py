"""Reusable byos_server.py subprocess harness.

Starts the real stub-server/byos_server.py on a free loopback port over a
state directory the caller prepared, and talks to it over HTTP. It never
enrols implicitly: tests call `setup` or reuse a token already in the
seeded state.
"""
from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

from skypane_test_support import child_env

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
SERVER_PATH = os.path.join(REPO_ROOT, "stub-server", "byos_server.py")
IMAGE_BYTES = 960000
STARTUP_DEADLINE_S = 10.0
START_PORT_ATTEMPTS = 5
DEFAULT_SLEEP_S = 30


def _pick_free_port() -> int:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("127.0.0.1", 0))
        port: int = s.getsockname()[1]
        return port
    finally:
        s.close()


def _http(url, method="GET", headers=None, json_body=None, timeout=10):
    data = None
    hdrs = dict(headers or {})
    if json_body is not None:
        data = json.dumps(json_body).encode("utf-8")
        hdrs.setdefault("Content-Type", "application/json")
    req = urllib.request.Request(url, data=data, headers=hdrs, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()


class FrameServer:
    """A byos_server.py subprocess serving `state_dir` on a loopback port."""

    def __init__(self, state_dir, extra_args=(), env_overrides=None):
        self.state_dir = state_dir
        self.extra_args = tuple(extra_args)
        self.env_overrides = dict(env_overrides or {})
        self.port = _pick_free_port()
        self.proc = None
        self.stdout_path = os.path.join(state_dir, "byos.stdout.log")

    @property
    def base_url(self) -> str:
        return "http://127.0.0.1:%d" % self.port

    def start(self) -> None:
        image_path = os.path.join(self.state_dir, "panel.bin")
        if not os.path.exists(image_path):
            with open(image_path, "wb") as fh:
                fh.write(bytes(IMAGE_BYTES))
        # The port is released before the child binds it, so a foreign
        # listener can take it in between; readiness is the child's own
        # "serving" line and a child that lost the port is relaunched.
        for _ in range(START_PORT_ATTEMPTS):
            if self._launch_and_wait(image_path):
                return
            self.port = _pick_free_port()
        raise RuntimeError("byos_server.py could not get a free port")

    def _launch_and_wait(self, image_path) -> bool:
        env = child_env()
        env["PYTHONUNBUFFERED"] = "1"
        env.update(self.env_overrides)
        with open(self.stdout_path, "w") as stdout_fh:
            self.proc = subprocess.Popen(
                [sys.executable, SERVER_PATH, "--image", image_path,
                 "--port", str(self.port), "--sleep", str(DEFAULT_SLEEP_S),
                 "--state-dir", self.state_dir, *self.extra_args],
                stdout=stdout_fh, stderr=subprocess.STDOUT, env=env)
        deadline = time.time() + STARTUP_DEADLINE_S
        while time.time() < deadline:
            output = self.stdout_text()
            if "serving" in output and (":%d" % self.port) in output:
                return True
            if self.proc.poll() is not None:
                if "Address already in use" in output:
                    self.proc = None
                    return False
                raise RuntimeError("byos_server.py exited early:\n%s" % output)
            time.sleep(0.05)
        raise RuntimeError("byos_server.py did not start:\n%s" % self.stdout_text())

    def stdout_text(self) -> str:
        try:
            with open(self.stdout_path) as fh:
                return fh.read()
        except OSError:
            return ""

    def stop(self) -> None:
        if self.proc is None:
            return
        if self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                self.proc.wait(timeout=5)
        self.proc = None

    def restart(self) -> None:
        self.stop()
        self.start()

    def setup(self, mac, secret_hex):
        """POST /device/v1/setup -> (status, parsed json)."""
        status, body = _http(
            self.base_url + "/device/v1/setup", method="POST",
            json_body={"mac": mac, "hw_rev": "harness",
                       "provision_secret": secret_hex})
        return status, json.loads(body.decode())

    def display(self, token, headers=None):
        """GET /device/v1/display -> (status, parsed json or None)."""
        hdrs = {"Authorization": "Bearer %s" % token}
        hdrs.update(headers or {})
        status, body = _http(self.base_url + "/device/v1/display", headers=hdrs)
        try:
            return status, json.loads(body.decode())
        except ValueError:
            return status, None
