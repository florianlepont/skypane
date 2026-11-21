"""A loopback stand-in for the Anthropic Messages API, for tests.

It answers POST /v1/messages with scripted statuses and bodies in the real
response and error shapes, and records every request (path, headers, parsed
body) in memory for assertions; it never prints them. A request the script
does not cover gets a valid answer naming `default_airline`.

Standard library only; no pytest import, so subprocess and in-process app
fixtures can both use it. Placeholder values only.
"""

import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

DUMMY_KEY = "test-key-not-a-secret"


def message_body(text):
    """A Messages API success body whose first block is `text`."""
    return {
        "id": "msg_test", "type": "message", "role": "assistant",
        "model": "claude-haiku-5-5",
        "content": [{"type": "text", "text": text}],
        "stop_reason": "end_turn", "stop_sequence": None,
        "usage": {"input_tokens": 40, "output_tokens": 12},
    }


def airline_body(name):
    """A success body in which the model names `name` (None: it is not sure)."""
    return message_body(json.dumps({"airline": name}))


def error_body(kind, message="test error"):
    """The error shape: {"type": "error", "error": {...}, "request_id": ...}."""
    return {"type": "error", "error": {"type": kind, "message": message},
            "request_id": "req_test"}


class Scripted:
    """One scripted answer: status, JSON body (or raw bytes) and headers."""

    def __init__(self, status=200, body=None, headers=None, raw=None):
        self.status = status
        self.body = body
        self.headers = dict(headers or {})
        self.raw = raw


class FakeAnthropic:
    def __init__(self, default_airline="Example Air"):
        self.default_airline = default_airline
        self.requests = []
        self._script = []
        self._lock = threading.Lock()
        self._server = None
        self._thread = None
        self.delay_s = 0.0
        self.active = 0
        self.max_active = 0

    def start(self):
        handler = _make_handler(self)
        self._server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        return self

    def stop(self):
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
            self._server = None

    @property
    def url(self):
        return "http://127.0.0.1:%d" % self._server.server_address[1]

    def env(self, key=DUMMY_KEY, env=None):
        """`env` plus the two variables that point a server at this fake."""
        merged = dict(env or {})
        merged["SKYPANE_ANTHROPIC_API_KEY"] = key
        merged["SKYPANE_ANTHROPIC_BASE_URL"] = self.url
        return merged

    def script(self, *answers):
        """Queue answers (Scripted) used one per request, in order."""
        with self._lock:
            self._script.extend(answers)

    def next_answer(self, body):
        with self._lock:
            if self._script:
                return self._script.pop(0)
        return Scripted(200, airline_body(self.default_airline))

    def record(self, path, headers, body):
        with self._lock:
            self.requests.append({"path": path, "headers": headers, "body": body})

    def enter(self):
        with self._lock:
            self.active += 1
            self.max_active = max(self.max_active, self.active)

    def leave(self):
        with self._lock:
            self.active -= 1

    @property
    def call_count(self):
        with self._lock:
            return len(self.requests)


def _make_handler(fake):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length)
            try:
                body = json.loads(raw)
            except ValueError:
                body = None
            fake.record(self.path, {k.lower(): v for k, v in self.headers.items()}, body)
            fake.enter()
            try:
                time.sleep(fake.delay_s)
                answer = fake.next_answer(body)
            finally:
                fake.leave()
            payload = answer.raw if answer.raw is not None else json.dumps(answer.body).encode()
            self.send_response(answer.status)
            self.send_header("Content-Type", "application/json")
            self.send_header("request-id", "req_test")
            for name, value in answer.headers.items():
                self.send_header(name, value)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

    return Handler
