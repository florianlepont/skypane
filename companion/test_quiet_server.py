"""The companion's server stays quiet when a browser aborts a response and
still reports every other exception."""
from http.server import BaseHTTPRequestHandler

import pytest

from companion import quiet_server


@pytest.fixture
def server():
    httpd = quiet_server.QuietHTTPServer(("127.0.0.1", 0), BaseHTTPRequestHandler)
    yield httpd
    httpd.server_close()


def _report(httpd, error):
    try:
        raise error
    except Exception:
        httpd.handle_error(None, ("127.0.0.1", 1))


@pytest.mark.parametrize("error", (
    BrokenPipeError(32, "Broken pipe"), ConnectionResetError(104, "reset"),
    ConnectionAbortedError(103, "aborted")))
def test_a_client_abort_leaves_no_traceback(server, capsys, error):
    _report(server, error)
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == ""


def test_any_other_exception_is_still_reported(server, capsys):
    _report(server, ValueError("a real bug"))
    err = capsys.readouterr().err
    assert "Traceback" in err and "a real bug" in err
