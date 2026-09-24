"""Self-tests for skypane_test_support.py / sitecustomize.py: prove the
non-loopback network guard actually trips (connect and DNS, in-process and
in a child interpreter), loopback stays usable, and the fake provider
fixture serves canned/default/failure responses both in-process and across
a process boundary.
"""

import json
import os
import socket
import subprocess
import sys

import pytest
import requests

import skypane_test_support as sts
from skypane_test_support import (
    REPO_ROOT,
    FakeResponse,
    NetworkAccessBlocked,
    child_env,
)

from server.plane import detect, enrich


# --- In-process guard -----------------------------------------------------


def test_non_loopback_connect_is_blocked_in_process():
    from pytest_socket import SocketConnectBlockedError

    with pytest.raises(SocketConnectBlockedError):
        socket.create_connection(("192.0.2.1", 80), timeout=2)


def test_non_loopback_dns_is_blocked_in_process():
    with pytest.raises(NetworkAccessBlocked):
        socket.getaddrinfo("example.com", 80)


def test_loopback_is_allowed_in_process():
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind(("127.0.0.1", 0))
    listener.listen(1)
    try:
        port = listener.getsockname()[1]
        with socket.create_connection(("127.0.0.1", port), timeout=2):
            pass
        assert socket.getaddrinfo("localhost", port)
    finally:
        listener.close()


# --- Cross-process guard --------------------------------------------------


def test_child_guard_blocks_connect():
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import socket; socket.create_connection(('192.0.2.1', 80), timeout=2)",
        ],
        env=child_env(),
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode != 0
    assert "SocketConnectBlockedError" in result.stderr


def test_child_guard_blocks_dns():
    result = subprocess.run(
        [sys.executable, "-c", "import socket; socket.getaddrinfo('example.com', 80)"],
        env=child_env(),
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode != 0
    assert "NetworkAccessBlocked" in result.stderr


def test_child_guard_allows_loopback():
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind(("127.0.0.1", 0))
    listener.listen(1)
    try:
        port = listener.getsockname()[1]
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "import socket; socket.create_connection(('127.0.0.1', %d), timeout=2)"
                % port,
            ],
            env=child_env(),
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert result.returncode == 0, result.stdout + result.stderr
    finally:
        listener.close()


def test_child_without_guard_env_is_inert():
    env = dict(os.environ)
    env.pop("SKYPANE_TEST_NO_NETWORK", None)
    existing = env.get("PYTHONPATH")
    env["PYTHONPATH"] = os.pathsep.join(
        [sts.TEST_SUPPORT_DIR] + ([existing] if existing else [])
    )
    result = subprocess.run(
        [sys.executable, "-c", "import socket; print(type(socket.socket.connect).__name__)"],
        env=env,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.strip() == "method_descriptor"


def test_proxy_env_is_stripped_in_process():
    leaked = [var for var in sts.PROXY_ENV_VARS if var in os.environ]
    assert leaked == []


def test_child_env_strips_proxy_vars():
    base = {var: "http://127.0.0.1:9" for var in sts.PROXY_ENV_VARS}
    env = child_env(base)
    assert [var for var in sts.PROXY_ENV_VARS if var in env] == []


def test_child_guard_ignores_loopback_proxy():
    # A loopback proxy would tunnel the request past both guards if it
    # were honoured (the client would only resolve/connect 127.0.0.1:9 and
    # fail with a ConnectionError); install_child_network_guard() must
    # strip it so the real host's DNS lookup is what gets blocked. Plain
    # http:// so the result never depends on the environment's CA bundle
    # (a proxied http:// request is tunnelled through the proxy all the same).
    env = dict(os.environ)
    env.update({var: "http://127.0.0.1:9" for var in sts.PROXY_ENV_VARS})
    env[sts.NO_NETWORK_ENV_VAR] = "1"
    existing = env.get("PYTHONPATH")
    env["PYTHONPATH"] = os.pathsep.join(
        [sts.TEST_SUPPORT_DIR] + ([existing] if existing else [])
    )
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import requests; requests.get('http://api.adsbdb.com/v0/callsign/AFR1234', timeout=5)",
        ],
        env=env,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode != 0
    assert "NetworkAccessBlocked" in result.stderr, result.stderr


# --- Provider-host drift guard --------------------------------------------


def test_provider_hosts_match_production_urls():
    from urllib.parse import urlsplit

    hosts_to_names = {}
    for provider_name, spec in detect.PROVIDERS.items():
        host = urlsplit(spec["url_template"]).hostname
        hosts_to_names[host] = provider_name
    hosts_to_names[urlsplit(enrich.ADSBDB_URL).hostname] = "adsbdb"

    assert set(hosts_to_names) == set(sts.PROVIDER_HOSTS)
    assert hosts_to_names == sts.PROVIDER_HOSTS


# --- Fake provider fixture -------------------------------------------------


def test_fake_providers_fixture_serves_canned_and_default(fake_providers):
    fake_providers.respond("adsbfi", {"aircraft": [{"hex": "abc123"}]})

    assert detect.query_provider("adsbfi", 48.72, 2.37, 5) == [{"hex": "abc123"}]
    assert detect.query_provider("adsblol", 48.72, 2.37, 5) == []
    assert enrich.default_transport("AFR123") == (404, {"response": "unknown callsign"})

    providers_called = [c["provider"] for c in fake_providers.calls]
    assert providers_called == ["adsbfi", "adsblol", "adsbdb"]


def test_fake_providers_failure_is_raised(fake_providers):
    fake_providers.fail("adsblol", requests.ConnectionError("down"))
    with pytest.raises(requests.ConnectionError):
        detect.query_provider("adsblol", 48.72, 2.37, 5)


def test_fake_providers_cross_process(fake_providers, tmp_path):
    fake_providers.respond("adsbfi", {"aircraft": [{"hex": "c0ffee"}]})
    spec_path = fake_providers.to_file(str(tmp_path / "fake-providers.json"))

    env = child_env(fake_providers=fake_providers, state_dir=str(tmp_path))
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import json, server.plane.detect as d\n"
            "print(json.dumps(d.query_provider('adsbfi', 48.72, 2.37, 5)))",
        ],
        env=env,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(result.stdout.strip()) == [{"hex": "c0ffee"}]

    logged = sts.FakeProviders.read_calls_log(spec_path)
    adsbfi_calls = [c for c in logged if c["provider"] == "adsbfi"]
    assert len(adsbfi_calls) == 1


@pytest.mark.parametrize(
    "exc",
    [
        requests.exceptions.SSLError("tls"),
        requests.exceptions.ProxyError("proxy"),
        requests.exceptions.ChunkedEncodingError("chunked"),
        requests.exceptions.ReadTimeout("slow"),
    ],
)
def test_fake_providers_failure_round_trips_through_file(tmp_path, exc):
    fake = sts.FakeProviders()
    fake.fail("adsbfi", exc)
    spec_path = fake.to_file(str(tmp_path / "fake-providers.json"))

    reloaded = sts.FakeProviders.from_file(spec_path)
    with pytest.raises(type(exc)):
        reloaded.get("https://opendata.adsb.fi/api/v2/lat/0/lon/0/dist/1")


def test_fake_providers_to_file_rejects_non_requests_failure(tmp_path):
    fake = sts.FakeProviders()
    fake.fail("adsbfi", ValueError("not a requests error"))
    with pytest.raises(ValueError, match="cannot serialise"):
        fake.to_file(str(tmp_path / "fake-providers.json"))


def test_fake_providers_from_file_rejects_non_exception_name(tmp_path):
    spec_path = tmp_path / "fake-providers.json"
    spec_path.write_text(
        json.dumps({"failures": {"adsbfi": {"error": "BaseHTTPError", "message": "x"}}})
    )
    with pytest.raises(ValueError, match="refusing to reconstruct"):
        sts.FakeProviders.from_file(str(spec_path))


# --- FakeResponse -----------------------------------------------------


def test_fake_response_raise_for_status_and_json():
    ok = FakeResponse(200, {"a": 1})
    ok.raise_for_status()
    assert ok.json() == {"a": 1}

    err = FakeResponse(404, {"response": "unknown callsign"})
    with pytest.raises(requests.HTTPError):
        err.raise_for_status()

    empty = FakeResponse(404, None)
    with pytest.raises(ValueError):
        empty.json()


# --- legacy_companion_harnesses() ---------------------------------------


def test_legacy_companion_harnesses_marker_presence_absence_and_missing_file(tmp_path, monkeypatch):
    """legacy_companion_harnesses() reads REPO_ROOT/ORIGINAL_COMPANION_
    HARNESSES from the module globals, so both can be monkeypatched to
    point at a disposable fake tree: a harness with the
    EXPECTED_CHECK_COUNT marker is legacy, one without it is not, and a
    listed-but-missing path is not.
    """
    companion_dir = tmp_path / "companion"
    companion_dir.mkdir()
    (companion_dir / "test_with_marker.py").write_text("EXPECTED_CHECK_COUNT = 3\n")
    (companion_dir / "test_without_marker.py").write_text("# no marker here\n")

    monkeypatch.setattr(sts, "REPO_ROOT", str(tmp_path))
    monkeypatch.setattr(sts, "ORIGINAL_COMPANION_HARNESSES", (
        "companion/test_with_marker.py",
        "companion/test_without_marker.py",
        "companion/test_missing_entirely.py",
    ))

    assert sts.legacy_companion_harnesses() == ("companion/test_with_marker.py",)
