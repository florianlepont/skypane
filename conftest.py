# Repo-root conftest.py: collected before any test file, so this is where
# the shared contract from test-support/ (network guard, fake provider,
# legacy-companion collection exclusion) is wired into every pytest run
# regardless of which subdirectory it targets.
import os
import socket
import sys

# pythonpath in pyproject.toml's [tool.pytest.ini_options] already puts
# test-support/ on sys.path once pytest has finished reading its config -
# but this file itself is imported during collection, potentially before
# that ini option has taken effect, so the same directory is inserted here
# too, computed directly from __file__ rather than assumed.
_TEST_SUPPORT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test-support")
if _TEST_SUPPORT_DIR not in sys.path:
    sys.path.insert(0, _TEST_SUPPORT_DIR)

import pytest  # noqa: E402

import skypane_test_support  # noqa: E402

# Legacy companion harnesses (and their shared helper module) are run
# through companion/test_legacy_harness_shim.py as subprocesses - pytest
# must never import them directly as test modules in their own right.
collect_ignore = list(skypane_test_support.LEGACY_COMPANION_COLLECT_IGNORE)


@pytest.fixture(autouse=True)
def _block_non_loopback_dns(request, monkeypatch):
    """Close the one gap --allow-hosts leaves open (T-32-01-02): pytest-socket
    only guards socket.socket.connect() in allow-hosts mode, never DNS
    resolution. Every test gets this unless it opts out with
    @pytest.mark.enable_socket, the same marker that opts a test out of
    pytest-socket's own connect() guard.
    """
    if request.node.get_closest_marker("enable_socket"):
        yield
        return
    resolvers = skypane_test_support.guarded_resolvers()
    monkeypatch.setattr(socket, "getaddrinfo", resolvers["getaddrinfo"])
    monkeypatch.setattr(socket, "gethostbyname", resolvers["gethostbyname"])
    monkeypatch.setattr(socket, "gethostbyname_ex", resolvers["gethostbyname_ex"])
    yield


@pytest.fixture
def fake_providers(monkeypatch):
    """An installed FakeProviders instance, ready for a test to call
    .respond()/.fail() on. Also zeroes detect.py's inter-call sleep so a
    test exercising poll_current_aircraft()'s two-provider cross-validation
    stays fast (the same convention server/test_plane_detection.py's own
    _with_stubbed_providers() helper already uses).
    """
    from server.plane import detect

    monkeypatch.setattr(detect, "MIN_SECONDS_BETWEEN_CALLS", 0)
    fake = skypane_test_support.FakeProviders()
    fake.install(monkeypatch.setattr)
    return fake
