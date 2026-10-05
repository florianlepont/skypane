#!/usr/bin/env python3
"""The shared test server must be serving from ITS OWN process when start() returns, even when
the port it was given is already held by another server."""
import companion_app_server


def test_a_server_whose_port_is_taken_moves_to_a_free_port_and_serves_its_own_state(
        tmp_path):
    first = companion_app_server.AppServer(str(tmp_path / "first"))
    second = companion_app_server.AppServer(str(tmp_path / "second"))
    try:
        first.start()
        second.port = first.port
        second.start()
        assert second.port != first.port
        assert second.proc.poll() is None
        status, _headers, _body = companion_app_server.http_request(second.url("/login"))
        assert status == 200
        assert (":%d (state_dir=" % second.port) in second.read_stdout()
    finally:
        second.stop()
        first.stop()
