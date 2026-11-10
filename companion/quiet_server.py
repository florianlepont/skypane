"""The companion's HTTP server: a `ThreadingHTTPServer` that stays quiet when
the browser aborts a response.

A tab closed or a navigation cancelled mid-response resets the connection;
the standard handler prints a traceback for it ("Exception occurred during
processing of request"). That is not an application error, so it is dropped
here; every other exception is still reported the standard way.
"""
import sys
from http.server import ThreadingHTTPServer

# A peer that went away while the response was being written or the request read.
CLIENT_ABORTS = (BrokenPipeError, ConnectionResetError, ConnectionAbortedError)


class QuietHTTPServer(ThreadingHTTPServer):
    def handle_error(self, request, client_address):
        if isinstance(sys.exc_info()[1], CLIENT_ABORTS):
            return
        super().handle_error(request, client_address)
