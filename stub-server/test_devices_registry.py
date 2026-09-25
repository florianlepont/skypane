#!/usr/bin/env python3
"""Contract harness for byos_server.py's per-device enrolment registry and
devices_cli.py, the operator CLI that manages it.

Every top-level test_* function below is a plain pytest test (plain
`assert`, no return value) that takes pytest's `tmp_path` as its
--state-dir - each server test owns a self-contained Harness (free port,
that state dir, a generated panel image).

Proves the enrolment rules:
    - a registered MAC presenting its own secret gets a fresh token, and
      re-enrolling revokes the previous token
    - a registered MAC presenting the wrong secret (zeros, another
      device's secret, the retired shared secret, a missing or
      non-string provision_secret) is refused and the existing token
      keeps working
    - an unregistered MAC is refused and no state is created
    - a missing, corrupt, or non-dict devices.json refuses every
      enrolment (fail closed)
    - a malformed mac is rejected before any registry lookup; an
      uppercase mac in the request body matches its lowercase registry
      entry
    - devices.json never contains the plaintext secret
    - the retired --secret flag grants nothing
    - devices_cli.py's add/remove/list/revoke-token subcommands

Usage:
    python3 stub-server/test_devices_registry.py
"""
import hashlib
import importlib.util
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
SERVER_PATH = os.path.join(HERE, "byos_server.py")
CLI_PATH = os.path.join(HERE, "devices_cli.py")
MAKE_PANEL_PATH = os.path.join(HERE, "make_test_panel.py")
STARTUP_DEADLINE_S = 10.0

# Fixed 64-lowercase-hex enrolment secrets used across scenarios below -
# never a real device's secret, just deterministic test fixtures.
SECRET_A = "1" * 64
SECRET_B = "2" * 64
OLD_SHARED_SECRET = "dev-setup-secret"


def _sha256_hex(secret_hex):
    return hashlib.sha256(secret_hex.encode("ascii")).hexdigest()


def load_byos_module():
    """Load byos_server.py directly via importlib.util, matching
    stub-server/test_poll_cycle.py's own pattern, so the registry
    helpers (register_device, load_registry, load_state, save_state)
    can be driven without going through HTTP. Safe because the module's
    top level is constants and defs only - main() sits behind an
    `if __name__ == "__main__"` guard.
    """
    spec = importlib.util.spec_from_file_location(
        "byos_server_registry_under_test", SERVER_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def http_request(url, method="GET", headers=None, json_body=None, timeout=10):
    data = None
    hdrs = dict(headers or {})
    if json_body is not None:
        data = json.dumps(json_body).encode("utf-8")
        hdrs.setdefault("Content-Type", "application/json")
    req = urllib.request.Request(url, data=data, headers=hdrs, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, dict(resp.headers), resp.read()
    except urllib.error.HTTPError as exc:
        return exc.code, dict(exc.headers or {}), exc.read()


class Harness:
    """Owns one byos_server.py subprocess: a free port, the caller's
    tmp_path as --state-dir, and a generated panel image. Callers must
    run stop() in a finally block - never leaves an orphaned server
    holding the port.
    """

    def __init__(self, state_dir):
        self.tmpdir = str(state_dir)
        self.port = self._pick_free_port()
        self.image_path = os.path.join(self.tmpdir, "panel.bin")
        self.stdout_path = os.path.join(self.tmpdir, "server.stdout.log")
        self.proc = None
        subprocess.run(
            [sys.executable, MAKE_PANEL_PATH, "--pattern", "palette", "--out", self.image_path],
            check=True, capture_output=True, text=True, env=child_env(),
        )

    @staticmethod
    def _pick_free_port():
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.bind(("127.0.0.1", 0))
            return s.getsockname()[1]
        finally:
            s.close()

    def base_url(self):
        return "http://127.0.0.1:%d" % self.port

    def registry_path(self):
        return os.path.join(self.tmpdir, "devices.json")

    def register(self, mac, secret_hex):
        """Register `mac` against this harness's own --state-dir before
        the subprocess starts, via the same register_device() the
        server and devices_cli.py both call - never hand-writes
        devices.json's shape.
        """
        module = load_byos_module()
        module.register_device(self.tmpdir, mac, _sha256_hex(secret_hex), replace=True)

    def start(self, extra_args=None):
        stdout_fh = open(self.stdout_path, "w")
        cmd = [sys.executable, SERVER_PATH,
               "--image", self.image_path,
               "--port", str(self.port),
               "--sleep", "300",
               "--state-dir", self.tmpdir]
        if extra_args:
            cmd += extra_args
        try:
            self.proc = subprocess.Popen(cmd, stdout=stdout_fh, stderr=subprocess.STDOUT, env=child_env())
        finally:
            stdout_fh.close()  # child holds its own duplicated fd

        deadline = time.time() + STARTUP_DEADLINE_S
        while time.time() < deadline:
            if self.proc.poll() is not None:
                raise RuntimeError(
                    "byos_server.py exited early (code %s) before accepting "
                    "connections:\n%s" % (self.proc.returncode, self.read_stdout()))
            try:
                with socket.create_connection(("127.0.0.1", self.port), timeout=0.5):
                    return
            except OSError:
                time.sleep(0.1)
        raise RuntimeError("server did not start listening within %.0fs" % STARTUP_DEADLINE_S)

    def stop(self):
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

    def read_stdout(self):
        try:
            with open(self.stdout_path) as fh:
                return fh.read()
        except OSError:
            return ""


def _run_cli(state_dir, *args):
    result = subprocess.run(
        [sys.executable, CLI_PATH, "--state-dir", state_dir] + list(args),
        capture_output=True, text=True, env=child_env(),
    )
    return result.returncode, result.stdout, result.stderr


# --- Enrolment rules, proven over real HTTP -------------------------------

def test_setup_with_registered_mac_and_matching_secret_issues_token_and_revokes_previous(tmp_path):
    h = Harness(tmp_path)
    try:
        h.register("aa:bb:cc:dd:ee:01", SECRET_A)
        h.start()
        status, _, body = http_request(
            h.base_url() + "/device/v1/setup", method="POST",
            json_body={"mac": "aa:bb:cc:dd:ee:01", "hw_rev": "test",
                       "provision_secret": SECRET_A})
        assert status == 200, "expected 200, got %d (%r)" % (status, body[:200])
        token1 = json.loads(body.decode())["device_token"]
        assert isinstance(token1, str) and len(token1) == 64 and \
            all(c in "0123456789abcdef" for c in token1), \
            "device_token not 64 lowercase hex chars: %r" % (token1,)

        status, _, _ = http_request(
            h.base_url() + "/device/v1/display", method="GET",
            headers={"Authorization": "Bearer %s" % token1})
        assert status == 200, "first token should authenticate, got %d" % status

        # Re-enrolling the same MAC with its own secret issues a NEW token.
        status, _, body = http_request(
            h.base_url() + "/device/v1/setup", method="POST",
            json_body={"mac": "aa:bb:cc:dd:ee:01", "hw_rev": "test",
                       "provision_secret": SECRET_A})
        assert status == 200, "re-enrolment expected 200, got %d" % status
        token2 = json.loads(body.decode())["device_token"]
        assert token2 != token1, "re-enrolment must issue a different token"

        status, _, _ = http_request(
            h.base_url() + "/device/v1/display", method="GET",
            headers={"Authorization": "Bearer %s" % token1})
        assert status == 401, "the previous token must stop authenticating after re-enrolment"

        status, _, _ = http_request(
            h.base_url() + "/device/v1/display", method="GET",
            headers={"Authorization": "Bearer %s" % token2})
        assert status == 200, "the new token must authenticate"
    finally:
        h.stop()


def test_setup_with_wrong_secret_returns_401_and_leaves_existing_token_working(tmp_path):
    h = Harness(tmp_path)
    try:
        h.register("aa:bb:cc:dd:ee:02", SECRET_A)
        h.register("aa:bb:cc:dd:ee:03", SECRET_B)
        h.start()
        status, _, body = http_request(
            h.base_url() + "/device/v1/setup", method="POST",
            json_body={"mac": "aa:bb:cc:dd:ee:02", "hw_rev": "test",
                       "provision_secret": SECRET_A})
        assert status == 200
        good_token = json.loads(body.decode())["device_token"]

        wrong_secrets = ["0" * 64, SECRET_B, OLD_SHARED_SECRET]
        for wrong in wrong_secrets:
            status, _, _ = http_request(
                h.base_url() + "/device/v1/setup", method="POST",
                json_body={"mac": "aa:bb:cc:dd:ee:02", "hw_rev": "test",
                           "provision_secret": wrong})
            assert status == 401, "wrong secret %r: expected 401, got %d" % (wrong, status)

        # Missing provision_secret entirely.
        status, _, _ = http_request(
            h.base_url() + "/device/v1/setup", method="POST",
            json_body={"mac": "aa:bb:cc:dd:ee:02", "hw_rev": "test"})
        assert status == 401, "missing provision_secret: expected 401, got %d" % status

        # Non-string provision_secret.
        status, _, _ = http_request(
            h.base_url() + "/device/v1/setup", method="POST",
            json_body={"mac": "aa:bb:cc:dd:ee:02", "hw_rev": "test", "provision_secret": 12345})
        assert status == 401, "non-string provision_secret: expected 401, got %d" % status

        status, _, _ = http_request(
            h.base_url() + "/device/v1/display", method="GET",
            headers={"Authorization": "Bearer %s" % good_token})
        assert status == 200, \
            "the existing token must keep working after every failed re-enrolment attempt"
    finally:
        h.stop()


def test_setup_with_unregistered_mac_returns_403_and_creates_no_state_entry(tmp_path):
    h = Harness(tmp_path)
    try:
        h.start()  # nothing registered
        status, _, body = http_request(
            h.base_url() + "/device/v1/setup", method="POST",
            json_body={"mac": "aa:bb:cc:dd:ee:09", "hw_rev": "test",
                       "provision_secret": SECRET_A})
        assert status == 403, "expected 403 for an unregistered MAC, got %d" % status
        assert not os.path.exists(os.path.join(h.tmpdir, "byos_state.json")), \
            "an unregistered MAC's setup attempt must not create byos_state.json"
    finally:
        h.stop()


def test_missing_registry_file_refuses_every_enrolment(tmp_path):
    h = Harness(tmp_path)
    try:
        assert not os.path.exists(h.registry_path())
        h.start()
        status, _, _ = http_request(
            h.base_url() + "/device/v1/setup", method="POST",
            json_body={"mac": "aa:bb:cc:dd:ee:01", "hw_rev": "test",
                       "provision_secret": SECRET_A})
        assert status == 403, "a missing devices.json must refuse enrolment, got %d" % status
    finally:
        h.stop()


def test_corrupt_registry_file_refuses_every_enrolment(tmp_path):
    h = Harness(tmp_path)
    try:
        h.register("aa:bb:cc:dd:ee:01", SECRET_A)
        with open(h.registry_path(), "w") as fh:
            fh.write("{not valid json")
        h.start()
        status, _, _ = http_request(
            h.base_url() + "/device/v1/setup", method="POST",
            json_body={"mac": "aa:bb:cc:dd:ee:01", "hw_rev": "test",
                       "provision_secret": SECRET_A})
        assert status == 403, \
            "a corrupt devices.json must fail closed, not fall back to open enrolment"
    finally:
        h.stop()


def test_non_dict_registry_file_refuses_every_enrolment(tmp_path):
    h = Harness(tmp_path)
    try:
        h.register("aa:bb:cc:dd:ee:01", SECRET_A)
        with open(h.registry_path(), "w") as fh:
            json.dump(["not", "a", "dict"], fh)
        h.start()
        status, _, _ = http_request(
            h.base_url() + "/device/v1/setup", method="POST",
            json_body={"mac": "aa:bb:cc:dd:ee:01", "hw_rev": "test",
                       "provision_secret": SECRET_A})
        assert status == 403, \
            "a non-dict devices.json document must fail closed, got %d" % status
    finally:
        h.stop()


def test_setup_with_a_malformed_mac_returns_422(tmp_path):
    h = Harness(tmp_path)
    try:
        h.start()
        for bad_mac in (12345, "zz:zz:zz:zz:zz:zz", "aabbccddeeff", "aa:bb:cc:dd:ee"):
            status, _, _ = http_request(
                h.base_url() + "/device/v1/setup", method="POST",
                json_body={"mac": bad_mac, "hw_rev": "test", "provision_secret": SECRET_A})
            assert status == 422, "mac=%r: expected 422, got %d" % (bad_mac, status)
    finally:
        h.stop()


def test_uppercase_mac_in_body_matches_its_lowercase_registry_entry(tmp_path):
    h = Harness(tmp_path)
    try:
        h.register("aa:bb:cc:dd:ee:01", SECRET_A)
        h.start()
        status, _, body = http_request(
            h.base_url() + "/device/v1/setup", method="POST",
            json_body={"mac": "AA:BB:CC:DD:EE:01", "hw_rev": "test",
                       "provision_secret": SECRET_A})
        assert status == 200, \
            "an uppercase MAC must match its lowercase registry entry, got %d" % status
    finally:
        h.stop()


def test_devices_json_never_contains_the_plaintext_secret(tmp_path):
    h = Harness(tmp_path)
    try:
        h.register("aa:bb:cc:dd:ee:01", SECRET_A)
        h.start()
        status, _, _ = http_request(
            h.base_url() + "/device/v1/setup", method="POST",
            json_body={"mac": "aa:bb:cc:dd:ee:01", "hw_rev": "test",
                       "provision_secret": SECRET_A})
        assert status == 200
        with open(h.registry_path()) as fh:
            registry_text = fh.read()
        assert SECRET_A not in registry_text, \
            "the plaintext enrolment secret must never appear in devices.json"
    finally:
        h.stop()


def test_secret_flag_grants_nothing_to_an_unregistered_mac(tmp_path):
    h = Harness(tmp_path)
    try:
        h.start(extra_args=["--secret", "anything-at-all"])
        status, _, _ = http_request(
            h.base_url() + "/device/v1/setup", method="POST",
            json_body={"mac": "aa:bb:cc:dd:ee:07", "hw_rev": "test",
                       "provision_secret": "anything-at-all"})
        assert status == 403, \
            "the retired --secret flag must not grant enrolment to an unregistered MAC"
    finally:
        h.stop()


# --- devices_cli.py -------------------------------------------------------

def test_devices_cli_add_list_remove_round_trip(tmp_path):
    tmpdir = str(tmp_path)
    secret_hash = _sha256_hex(SECRET_A)
    code, _, err = _run_cli(
        tmpdir, "add", "--mac", "aa:bb:cc:dd:ee:01", "--secret-sha256", secret_hash)
    assert code == 0, "add failed: %s" % err

    code, out, _ = _run_cli(tmpdir, "list")
    assert code == 0
    assert "aa:bb:cc:dd:ee:01" in out
    assert secret_hash not in out, "devices_cli.py list must never print the full hash"

    code, _, err = _run_cli(tmpdir, "remove", "--mac", "aa:bb:cc:dd:ee:01")
    assert code == 0, "remove failed: %s" % err

    module = load_byos_module()
    registry = module.load_registry(tmpdir)
    assert "aa:bb:cc:dd:ee:01" not in registry["devices"]


def test_devices_cli_add_rejects_a_malformed_mac_or_non_hex_hash(tmp_path):
    tmpdir = str(tmp_path)
    code, _, _ = _run_cli(
        tmpdir, "add", "--mac", "not-a-mac", "--secret-sha256", _sha256_hex(SECRET_A))
    assert code != 0, "a malformed mac must be rejected"

    code, _, _ = _run_cli(
        tmpdir, "add", "--mac", "aa:bb:cc:dd:ee:01", "--secret-sha256", "not-64-hex-chars")
    assert code != 0, "a non-64-hex hash must be rejected"


def test_devices_cli_add_over_existing_mac_without_replace_exits_nonzero(tmp_path):
    tmpdir = str(tmp_path)
    secret_hash = _sha256_hex(SECRET_A)
    code, _, err = _run_cli(
        tmpdir, "add", "--mac", "aa:bb:cc:dd:ee:01", "--secret-sha256", secret_hash)
    assert code == 0, "first add failed: %s" % err

    code, _, _ = _run_cli(
        tmpdir, "add", "--mac", "aa:bb:cc:dd:ee:01", "--secret-sha256", secret_hash)
    assert code != 0, "re-adding an existing MAC without --replace must fail"

    code, _, err = _run_cli(
        tmpdir, "add", "--mac", "aa:bb:cc:dd:ee:01",
        "--secret-sha256", _sha256_hex(SECRET_B), "--replace")
    assert code == 0, "--replace must allow overwriting an existing MAC: %s" % err


def test_devices_cli_revoke_token_removes_only_that_macs_token(tmp_path):
    tmpdir = str(tmp_path)
    module = load_byos_module()
    module.save_state(tmpdir, {"tokens": {
        "aa:bb:cc:dd:ee:01": "token-one",
        "aa:bb:cc:dd:ee:02": "token-two",
    }})
    code, _, err = _run_cli(tmpdir, "revoke-token", "--mac", "aa:bb:cc:dd:ee:01")
    assert code == 0, "revoke-token failed: %s" % err
    state = module.load_state(tmpdir)
    assert "aa:bb:cc:dd:ee:01" not in state["tokens"], \
        "revoke-token must remove the targeted MAC's token"
    assert state["tokens"].get("aa:bb:cc:dd:ee:02") == "token-two", \
        "revoke-token must leave every other MAC's token untouched"

