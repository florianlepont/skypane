"""The answer to an error no handler expected: a 500 page instead of a
dropped connection.

`ErrorPageMixin.dispatch_guarded()` wraps the handler's one dispatch. An
exception that escapes it is logged once (method, path without its query
string, and the traceback) and answered with the translated error page in the
app's chrome and a link back. Nothing about the error reaches the page. When
the chrome itself cannot be built (the store may be what failed) the page
comes without the signed-in navigation; when a response was already on its
way, the connection is closed, since a second response cannot follow.
"""
import sys
import traceback
from urllib.parse import urlsplit

from companion import login_page, prefs, quiet_server

_PLAIN_BODY = b"Internal Server Error\n"


class ErrorPageMixin:
    # True once this request's status line and headers left for the client.
    _headers_flushed = False

    def end_headers(self):
        self._headers_flushed = True
        super().end_headers()

    def dispatch_guarded(self, method):
        self._headers_flushed = False
        try:
            return self._dispatch(method)
        except quiet_server.CLIENT_ABORTS:
            raise
        except Exception:
            self._log_unexpected(method)
            return self._answer_unexpected()

    def _log_unexpected(self, method):
        """One log entry per failure: never a header, a cookie, a form body
        or a query string."""
        sys.stderr.write("500 %s %s\n" % (method, urlsplit(self.path).path))
        traceback.print_exc(file=sys.stderr)

    def _answer_unexpected(self):
        # The request body may be unread and the response half-built: the
        # connection is not reused either way.
        self.close_connection = True
        if self._headers_flushed:
            return None
        # Headers a handler queued before failing are dropped.
        self._headers_buffer = []
        try:
            page = self._server_error_page()
        except Exception:
            page = None
        if page is None:
            try:
                page = self._bare_server_error_page()
            except Exception:
                return self._send_plain_error()
        return self.send_html(500, page)

    def _server_error_page(self):
        """The page in the caller's own chrome, like the 404 page."""
        prefs.set_request_prefs(lang=self._lang_from_request())
        prefs.set_request_csrf("")
        self._scope_for_chrome()
        health_alert = self._health_alert_for_admin()
        back, home_route = self._back_target()
        return login_page.server_error_page(
            self._resolved_ui_theme(), health_alert, back=back, home_route=home_route)

    def _bare_server_error_page(self):
        """The page for nobody in particular: no store is read."""
        prefs.set_request_principal(None)
        prefs.set_request_prefs(lang=self._lang_from_request())
        prefs.set_request_csrf("")
        return login_page.server_error_page(
            self._resolved_ui_theme(), None, back=login_page.BACK_HOME)

    def _send_plain_error(self):
        self.send_response(500)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(_PLAIN_BODY)))
        self.send_header("Cache-Control", "no-store")
        self._send_hardening_headers()
        self.end_headers()
        self.wfile.write(_PLAIN_BODY)
        return None
