"""Shared test contracts used both by pytest (in-process) and by child
interpreters launched from a test (companion/app.py, stub-server/byos_server.py,
and any other subprocess a harness starts). A guard installed only in the
parent pytest process never reaches a subprocess's own fresh interpreter
state, so the same logical guard - "no non-loopback network access, an
injectable ADS-B/adsbdb provider" - needs one implementation two call
sites can share rather than two independent ones that could drift apart.
This module has no pytest-specific import at module scope other than
`pytest` itself (for the `requires_non_root` marker), so a child process
that only needs the network guard or the fake provider does not pay for
importing the rest of pytest's plugin machinery.
"""

import contextlib
import copy
import ipaddress
import json
import os
import socket
import urllib.parse

import pytest
import requests

# --- Paths -------------------------------------------------------------

TEST_SUPPORT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(TEST_SUPPORT_DIR)

# --- Env vars a child interpreter reads (sitecustomize.py) --------------

NO_NETWORK_ENV_VAR = "SKYPANE_TEST_NO_NETWORK"
FAKE_PROVIDER_ENV_VAR = "SKYPANE_TEST_FAKE_PROVIDER"

# --- Non-loopback network guard -----------------------------------------

ALLOWED_HOSTS = ("127.0.0.1", "::1", "localhost")


class NetworkAccessBlocked(RuntimeError):
    """Raised by a guarded_resolvers() function for any DNS lookup whose
    host is not loopback. Named separately from pytest-socket's own
    SocketConnectBlockedError so a caller can tell "a connect was
    attempted" apart from "a lookup was attempted" without inspecting the
    message string.
    """


def _stripped_host(host):
    """Undo IPv6 literal decoration ("[::1]", "fe80::1%eth0") so the bare
    address is what reaches ipaddress.ip_address().
    """
    candidate = host
    if candidate.startswith("[") and candidate.endswith("]"):
        candidate = candidate[1:-1]
    candidate = candidate.split("%", 1)[0]
    return candidate


def _is_allowed_host(host):
    if not host:
        return True
    if host == "localhost" or host.endswith(".localhost"):
        return True
    try:
        ipaddress.ip_address(_stripped_host(host))
        return True
    except ValueError:
        return False


def guarded_resolvers():
    """Return {"getaddrinfo": fn, "gethostbyname": fn, "gethostbyname_ex": fn},
    each raising NetworkAccessBlocked for a non-loopback host BEFORE
    calling the real resolver captured at the moment this function runs
    (so installing the guard twice does not chain through a
    previously-installed guard).
    """
    real_getaddrinfo = socket.getaddrinfo
    real_gethostbyname = socket.gethostbyname
    real_gethostbyname_ex = socket.gethostbyname_ex

    def _check(host):
        if not _is_allowed_host(host):
            raise NetworkAccessBlocked(
                "non-loopback DNS lookup for %r is blocked in tests" % (host,)
            )

    def guarded_getaddrinfo(host, *args, **kwargs):
        _check(host)
        return real_getaddrinfo(host, *args, **kwargs)

    def guarded_gethostbyname(host):
        _check(host)
        return real_gethostbyname(host)

    def guarded_gethostbyname_ex(host):
        _check(host)
        return real_gethostbyname_ex(host)

    return {
        "getaddrinfo": guarded_getaddrinfo,
        "gethostbyname": guarded_gethostbyname,
        "gethostbyname_ex": guarded_gethostbyname_ex,
    }


def install_child_network_guard():
    """Guard a CHILD interpreter's socket module the same way the parent
    pytest process is guarded: connect() restricted to loopback (via
    pytest-socket's own socket_allow_hosts, never disable_socket - a
    disabled socket module could not even bind a listening
    ThreadingHTTPServer) plus DNS resolution restricted the same way
    (guarded_resolvers(), since socket_allow_hosts() alone does not patch
    getaddrinfo/gethostbyname).
    """
    from pytest_socket import socket_allow_hosts

    socket_allow_hosts(list(ALLOWED_HOSTS), allow_unix_socket=True)
    resolvers = guarded_resolvers()
    socket.getaddrinfo = resolvers["getaddrinfo"]
    socket.gethostbyname = resolvers["gethostbyname"]
    socket.gethostbyname_ex = resolvers["gethostbyname_ex"]


# --- Fake ADS-B / adsbdb provider ---------------------------------------

# Real production URL hosts (server/plane/detect.py PROVIDERS,
# server/plane/enrich.py ADSBDB_URL), mapped to the provider name this
# fixture keys its canned responses by. A drift-guard test proves this
# table stays in sync with the production source.
PROVIDER_HOSTS = {
    "opendata.adsb.fi": "adsbfi",
    "api.adsb.lol": "adsblol",
    "api.airplanes.live": "airplaneslive",
    "api.adsbdb.com": "adsbdb",
}

# What each provider "naturally" returns when a test has not configured
# a canned response for it - an empty aircraft list in that provider's
# own key shape, or adsbdb's real unknown-callsign shape.
DEFAULT_RESPONSES = {
    "adsbfi": (200, {"aircraft": []}),
    "adsblol": (200, {"ac": []}),
    "airplaneslive": (200, {"ac": []}),
    "adsbdb": (404, {"response": "unknown callsign"}),
}


class FakeResponse:
    """Stands in for a requests.Response: only the surface
    detect.query_provider()/enrich.default_transport() actually use.
    """

    def __init__(self, status_code, body):
        self.status_code = status_code
        self._body = body
        self.headers = {}
        self.url = ""

    def json(self):
        if self._body is None:
            raise ValueError("FakeResponse has no JSON body")
        return copy.deepcopy(self._body)

    @property
    def text(self):
        if self._body is None:
            return ""
        return json.dumps(self._body)

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(
                "%s Error for url: %s" % (self.status_code, self.url), response=self
            )


class FakeProviders:
    """An injectable stand-in for requests.get(), routed by hostname to
    one of the four known providers. Every URL that is NOT one of the
    four known provider hosts falls through to the real requests.get
    captured at install time, so it still hits the socket guard instead
    of silently succeeding against an unrecognised host.
    """

    def __init__(self):
        self._responses = {}
        self._failures = {}
        self.calls = []
        self.calls_log_path = None
        self._real_get = None

    def respond(self, name, body, status=200):
        self._responses[name] = (status, body)
        self._failures.pop(name, None)

    def fail(self, name, exc):
        self._failures[name] = exc
        self._responses.pop(name, None)

    def get(self, url, params=None, headers=None, timeout=None, **kwargs):
        hostname = urllib.parse.urlsplit(url).hostname
        name = PROVIDER_HOSTS.get(hostname)
        if name is None:
            if self._real_get is None:
                raise RuntimeError(
                    "FakeProviders.get() saw an unrecognised host %r before "
                    "install()/installed() captured a real requests.get to "
                    "fall back to" % (hostname,)
                )
            return self._real_get(
                url, params=params, headers=headers, timeout=timeout, **kwargs
            )

        self.calls.append({"provider": name, "url": url})
        if self.calls_log_path:
            with open(self.calls_log_path, "a") as fh:
                fh.write(json.dumps({"provider": name, "url": url}) + "\n")

        if name in self._failures:
            raise self._failures[name]
        status, body = self._responses.get(name, DEFAULT_RESPONSES[name])
        response = FakeResponse(status, body)
        response.url = url
        return response

    def install(self, setattr_fn=setattr):
        """Patch requests.get with self.get. Pass monkeypatch.setattr from
        a pytest fixture so teardown restores the original automatically;
        the default plain `setattr` is for a child interpreter that has no
        monkeypatch fixture and exits (discarding the patch) at process end.
        """
        if self._real_get is None:
            self._real_get = requests.get
        setattr_fn(requests, "get", self.get)

    @contextlib.contextmanager
    def installed(self):
        """Context-manager form of install(), for callers with no
        monkeypatch fixture available (e.g. a plain `with` block).
        """
        original = requests.get
        self._real_get = original
        requests.get = self.get
        try:
            yield self
        finally:
            requests.get = original

    def to_file(self, path):
        """Serialise responses/failures to a JSON file a child interpreter
        can reload via from_file(), and point calls_log_path at a sibling
        file every served call is appended to as one JSON line - the only
        way a parent process can observe what a CHILD process's own
        FakeProviders instance actually served.
        """
        spec = {
            "responses": {
                name: {"status": status, "body": body}
                for name, (status, body) in self._responses.items()
            },
            "failures": {
                name: {"error": type(exc).__name__, "message": str(exc)}
                for name, exc in self._failures.items()
            },
        }
        with open(path, "w") as fh:
            json.dump(spec, fh)
        self.calls_log_path = path + ".calls.jsonl"
        open(self.calls_log_path, "w").close()
        return path

    @classmethod
    def from_file(cls, path):
        with open(path) as fh:
            spec = json.load(fh)
        fake = cls()
        for name, entry in spec.get("responses", {}).items():
            fake.respond(name, entry["body"], status=entry["status"])
        for name, entry in spec.get("failures", {}).items():
            error_name = entry["error"]
            # Only ever reconstruct a real requests exception class - never
            # an arbitrary name out of a file a test wrote, even though
            # that file is test-controlled, not attacker-controlled.
            if not hasattr(requests.exceptions, error_name):
                raise ValueError(
                    "refusing to reconstruct unknown requests.exceptions "
                    "class %r" % (error_name,)
                )
            exc_cls = getattr(requests, error_name)
            fake.fail(name, exc_cls(entry["message"]))
        fake.calls_log_path = path + ".calls.jsonl"
        return fake

    @staticmethod
    def read_calls_log(spec_path):
        log_path = spec_path + ".calls.jsonl"
        if not os.path.exists(log_path):
            return []
        calls = []
        with open(log_path) as fh:
            for line in fh:
                line = line.strip()
                if line:
                    calls.append(json.loads(line))
        return calls


def child_env(base=None, *, fake_providers=None, state_dir=None):
    """Build the env dict for a subprocess.Popen()/subprocess.run() call
    that should run under the same guard as this pytest process: the
    no-network var, TEST_SUPPORT_DIR prepended to PYTHONPATH (so
    sitecustomize.py is found and imported at child interpreter startup),
    and, optionally, a fake-provider instruction the child's own
    sitecustomize.py installs before any application code runs.
    """
    env = dict(base if base is not None else os.environ)
    env[NO_NETWORK_ENV_VAR] = "1"
    existing = env.get("PYTHONPATH")
    env["PYTHONPATH"] = os.pathsep.join(
        [TEST_SUPPORT_DIR] + ([existing] if existing else [])
    )
    if fake_providers is not None:
        if fake_providers == "default":
            env[FAKE_PROVIDER_ENV_VAR] = "default"
        else:
            if state_dir is None:
                raise ValueError(
                    "child_env(fake_providers=<FakeProviders>) needs "
                    "state_dir to write the spec file into"
                )
            spec_path = fake_providers.to_file(
                os.path.join(state_dir, "fake-providers.json")
            )
            env[FAKE_PROVIDER_ENV_VAR] = spec_path
    return env


# --- Legacy companion harnesses (pytest shim until Phase 33) -----------

LEGACY_COMPANION_HARNESSES = (
    "companion/test_companion_app.py",
    "companion/test_config_page.py",
    "companion/test_contrast_check.py",
    "companion/test_i18n.py",
    "companion/test_status_pages.py",
    "companion/test_view_pages.py",
    "companion/test_browser_ux.py",
    "companion/test_browser_ux_health_drawings.py",
    "companion/test_browser_ux_quiet_wake.py",
)

# Same list, plus the one helper module the browser harnesses import
# (not itself a runnable harness) - pytest must never try to collect
# either group as test modules in their own right.
LEGACY_COMPANION_COLLECT_IGNORE = LEGACY_COMPANION_HARNESSES + (
    "companion/test_browser_ux_helpers.py",
)


# --- Root-safety skip -----------------------------------------------------

requires_non_root = pytest.mark.skipif(
    hasattr(os, "geteuid") and os.geteuid() == 0,
    reason="root ignores permission bits; needs a non-root euid",
)
