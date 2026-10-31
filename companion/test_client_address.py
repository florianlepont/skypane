"""Tests the client_ip()/login_throttle_key() helpers behind the sign-in
start throttle, and the companion's bind address handling.

Native pytest (conftest.py fixtures and the no-network socket guard
apply automatically to this module).
"""
import socket

from companion import app, auth


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


def test_build_parser_bind_default_and_override():
    assert app.build_parser().parse_args([]).bind == "0.0.0.0"
    assert app.build_parser().parse_args(["--bind", "127.0.0.1"]).bind == "127.0.0.1"


def test_bind_127_accepts_a_loopback_connection_and_names_it_at_startup(make_app_server):
    server = make_app_server(extra_args=["--bind", "127.0.0.1"])
    with socket.create_connection(("127.0.0.1", server.port), timeout=2):
        pass
    assert "127.0.0.1" in server.read_stdout()
