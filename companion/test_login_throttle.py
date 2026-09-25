"""companion/test_login_throttle.py — SEC-01 (audit ledger 2026-09-23):
the keyed, bounded LoginThrottle and the client_ip()/login_throttle_key()
helpers it is built on.

Native pytest (Phase 32's conftest.py fixtures and no-network socket
guard apply automatically to this module).

Section 1 is pure in-process unit coverage of companion/auth.py. Section
2 is HTTP integration coverage proving the same property end to end
against a real companion/app.py subprocess: failed logins from one IP
never lock another (ROADMAP SC-1), and --bind (SEC-01/D-22). The
subprocess itself, and the HTTP client that talks to it, come from
companion/conftest.py's app_server/make_app_server fixtures and
test-support/companion_app_server.py (Phase 33, TST-10) — this module
owns no subprocess-launching code of its own.
"""
import socket
import urllib.parse

import companion_app_server
from companion import app, auth


class _FakeClock:
    """A small mutable callable clock: LoginThrottle(clock=fake_clock)
    advances only when a test calls .advance() — no real sleeping, and
    no test reaches into LoginThrottle's private attributes to fake time
    passing.
    """

    def __init__(self, start=0.0):
        self._now = start

    def __call__(self):
        return self._now

    def advance(self, seconds):
        self._now += seconds


# --- Section 1: LoginThrottle (unit) ------------------------------------

def test_throttle_locks_only_the_offending_key():
    throttle = auth.LoginThrottle(limit=3)
    for _ in range(3):
        throttle.record_failure("203.0.113.5")
    assert throttle.locked_out("203.0.113.5") is True
    assert throttle.locked_out("198.51.100.7") is False


def test_record_success_clears_only_its_own_key():
    throttle = auth.LoginThrottle(limit=3)
    for _ in range(3):
        throttle.record_failure("203.0.113.5")
    for _ in range(3):
        throttle.record_failure("198.51.100.7")
    throttle.record_success("203.0.113.5")
    assert throttle.locked_out("203.0.113.5") is False
    assert throttle.locked_out("198.51.100.7") is True


def test_lockout_releases_and_next_failure_starts_a_fresh_count():
    clock = _FakeClock()
    throttle = auth.LoginThrottle(limit=3, lockout_s=60, clock=clock)
    for _ in range(3):
        throttle.record_failure("203.0.113.5")
    assert throttle.locked_out("203.0.113.5") is True
    clock.advance(61)
    assert throttle.locked_out("203.0.113.5") is False
    throttle.record_failure("203.0.113.5")
    assert throttle.locked_out("203.0.113.5") is False  # 1 of 3, a fresh count


def test_seconds_remaining_is_an_int_and_zero_when_not_locked():
    clock = _FakeClock()
    throttle = auth.LoginThrottle(limit=3, lockout_s=60, clock=clock)
    assert throttle.seconds_remaining("203.0.113.5") == 0
    for _ in range(3):
        throttle.record_failure("203.0.113.5")
    remaining = throttle.seconds_remaining("203.0.113.5")
    assert isinstance(remaining, int)
    assert remaining > 0


def test_throttle_table_never_exceeds_max_entries_under_a_spray():
    throttle = auth.LoginThrottle(limit=5, max_entries=64)
    for i in range(10000):
        throttle.record_failure("10.%d.%d.%d" % (i // 65536, (i // 256) % 256, i % 256))
        assert len(throttle._entries) <= 64
    assert len(throttle._entries) <= 64


def test_throttle_evicts_stale_unlocked_entries_before_least_recently_seen():
    clock = _FakeClock()
    throttle = auth.LoginThrottle(limit=5, lockout_s=100, max_entries=3, clock=clock)
    throttle.record_failure("A")  # last_seen=0, unlocked (1 failure < limit 5)
    clock.advance(200)  # A is now stale: 200 > lockout_s (100)
    throttle.record_failure("B")
    throttle.record_failure("C")
    assert set(throttle._entries.keys()) == {"A", "B", "C"}
    throttle.record_failure("D")  # table is at max_entries=3: must evict first
    assert "A" not in throttle._entries
    assert set(throttle._entries.keys()) == {"B", "C", "D"}


# --- Section 1: client_ip() / login_throttle_key() (unit) ---------------

def test_client_ip_prefers_rightmost_xff_entry_from_a_loopback_peer():
    assert auth.client_ip("127.0.0.1", "10.0.0.1, 203.0.113.5") == "203.0.113.5"


def test_client_ip_treats_ipv4_mapped_loopback_as_loopback():
    assert auth.client_ip("::ffff:127.0.0.1", "203.0.113.5") == "203.0.113.5"


def test_client_ip_ignores_xff_from_a_non_loopback_peer():
    assert auth.client_ip("198.51.100.9", "203.0.113.5") == "198.51.100.9"


def test_client_ip_falls_back_to_the_peer_on_bad_or_missing_xff():
    assert auth.client_ip("127.0.0.1", "not-an-ip") == "127.0.0.1"
    assert auth.client_ip("127.0.0.1", None) == "127.0.0.1"
    assert auth.client_ip("127.0.0.1", "") == "127.0.0.1"


def test_login_throttle_key_collapses_ipv6_to_its_own_64_network():
    assert (
        auth.login_throttle_key("127.0.0.1", "2001:db8:1:2:3:4:5:6")
        == "2001:db8:1:2::/64"
    )


def test_login_throttle_key_is_the_bare_address_for_ipv4():
    assert auth.login_throttle_key("127.0.0.1", "203.0.113.5") == "203.0.113.5"


# --- Section 2: HTTP integration, real companion/app.py subprocess ------
#
# app_server/make_app_server (companion/conftest.py) are function-scoped
# on purpose: LOGIN_THROTTLE is a process-global singleton inside
# companion/app.py, so two tests sharing one server would see each
# other's failed-login counts.

def _post_login(server, password, xff=None):
    """POST /login and return just the status code — the HTTP status is
    all these tests need. An X-Forwarded-For header, when given, spoofs
    the client IP companion/app.py's LOGIN_THROTTLE keys on.
    """
    status, _, _ = companion_app_server.http_request(
        server.url("/login"), method="POST",
        data=urllib.parse.urlencode({"password": password}).encode(),
        extra_headers={"X-Forwarded-For": xff} if xff is not None else None)
    return status


def test_five_wrong_passwords_from_one_ip_lock_only_that_ip(app_server):
    attacker_xff = "203.0.113.5"
    victim_xff = "198.51.100.7"
    for _ in range(auth.LOGIN_FAILURE_LIMIT):
        status = _post_login(app_server, "wrong-password", xff=attacker_xff)
        assert status in (401, 429)
    # The lockout has now engaged for the attacker's key.
    status = _post_login(app_server, "wrong-password", xff=attacker_xff)
    assert status == 429
    # A different X-Forwarded-For, same server, logs in normally (SC-1).
    status = _post_login(app_server, companion_app_server.TEST_PASSWORD, xff=victim_xff)
    assert status == 303
    # The attacker's own key is still locked, even with the right password.
    status = _post_login(app_server, companion_app_server.TEST_PASSWORD, xff=attacker_xff)
    assert status == 429


def test_build_parser_bind_default_and_override():
    assert app.build_parser().parse_args([]).bind == "0.0.0.0"
    assert app.build_parser().parse_args(["--bind", "127.0.0.1"]).bind == "127.0.0.1"


def test_bind_127_accepts_a_loopback_connection_and_names_it_at_startup(make_app_server):
    server = make_app_server(extra_args=["--bind", "127.0.0.1"])
    with socket.create_connection(("127.0.0.1", server.port), timeout=2):
        pass
    assert "127.0.0.1" in server.read_stdout()
