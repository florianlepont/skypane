"""Reusable non-plumbing test doubles for the `companion/test_companion_
app*.py` migration chain (33-14..33-18): calendar-transport fakes, a
public-hostname DNS fake, and a poll-state seeding helper. Not a test
module itself — `__test__ = False` keeps pytest from ever collecting it
directly, and `companion/test_suite_guards.py`'s G9 rule enforces that
this marker is present.

Deliberately excludes the legacy subprocess-lifecycle plumbing (the
harness class, its HTTP client, its non-redirect-following opener, its
cookie/login helpers, and any use of the standard-library temp-directory
module): a migrated test that needs a real `companion/app.py` server
gets one from `companion/conftest.py`'s `app_server`/`make_app_server`/
`module_app_server_factory` fixtures and `test-support/companion_app_
server.py`'s HTTP client instead — that plumbing is not a reusable test
double, it is the fixture family every migrated module already shares.

33-14 itself needs none of these (part 01's checks are all in-process
`companion.auth`/`companion.layout` calls plus two served-stylesheet
checks) — this module is created now, ahead of its first use, so the
later parts of this same chain (the calendar-sync and manual-resolution
sections) never have to duplicate these doubles a second time.
"""
import socket
from datetime import datetime, timedelta, timezone

from server.plane import calendar_rules
import server.poll_loop as poll_loop

__test__ = False


class FakeCalendarResponse:
    """Hermetic stand-in for `requests.Response`, `server/test_calendar_
    rules.py`'s own class of the same shape exactly — no check using this
    ever makes a real network call.
    """

    def __init__(self, status_code=200, body=b""):
        self.status_code = status_code
        self._body = body
        self.headers = {}
        self.is_redirect = False
        self.closed = False

    def iter_content(self, chunk_size=8192):
        yield self._body

    def close(self):
        self.closed = True


def make_calendar_transport(status_code=200, body=b"", raise_exc=None, calls=None):
    """Build a fake `fetch_ics()`-shaped transport — `server/test_
    calendar_rules.py`'s own `make_calendar_transport()` helper, adapted
    for `FakeCalendarResponse`. Records every URL it was invoked with
    (or raises `raise_exc` instead of returning), simulating success or
    failure without ever touching a real socket.
    """
    def transport(url, timeout):
        if calls is not None:
            calls.append(url)
        if raise_exc is not None:
            raise raise_exc
        return FakeCalendarResponse(status_code, body)
    return transport


class stubbed_calendar_transport:
    """Context manager: monkeypatches `calendar_rules.default_calendar_
    transport` to `transport_fn` for the duration of the block,
    restoring the real function on exit. `fetch_ics()` looks up
    `default_calendar_transport` as a bare name in its own module's
    global namespace when its `transport` parameter is `None` (the
    companion's real call site never passes one), so patching the
    attribute on the imported `calendar_rules` module object — the SAME
    module object a `companion/app.py` server started in-process
    (`InProcessAppServer`) or in this test's own interpreter runs
    against — is sufficient; no reload, no subprocess env var, no
    second definition of the fetch path.
    """

    def __init__(self, transport_fn):
        self.transport_fn = transport_fn
        self._real = None

    def __enter__(self):
        self._real = calendar_rules.default_calendar_transport
        calendar_rules.default_calendar_transport = self.transport_fn
        return self

    def __exit__(self, *exc_info):
        calendar_rules.default_calendar_transport = self._real


class fake_public_hostname:
    """Context manager: monkeypatches `socket.getaddrinfo` so `hostname`
    resolves to a genuinely public-looking address for the duration of
    the block, restoring the real resolver on exit — `server/test_
    calendar_rules.py`'s own technique for getting a fabricated URL past
    `calendar_rules._url_is_safe()`'s SSRF gate without a real DNS answer
    or a real network call.
    """

    def __init__(self, hostname, address="93.184.216.34"):
        self.hostname = hostname
        self.address = address
        self._real = None

    def __enter__(self):
        self._real = socket.getaddrinfo
        real, hostname, address = self._real, self.hostname, self.address

        def fake(host, port=None, *a, **k):
            if host == hostname:
                return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (address, port or 443))]
            return real(host, port, *a, **k)
        socket.getaddrinfo = fake
        return self

    def __exit__(self, *exc_info):
        socket.getaddrinfo = self._real


def ics_body(entries):
    """Build a minimal, real-shaped iCal body from `entries` — a list of
    `(flight, origin, destination, hours_from_now)` tuples — matching
    `calendar_rules._build_entry()`'s exact accepted shape (CATEGORIES:
    FLT, a `FLIGHT ORI-DST` summary, bare-UTC DTSTART/DTEND). Every
    DTSTART is computed from real wall-clock time at call time, since the
    settings-post handler under test calls `poll_loop.now_s()` (real
    `time.time()`) for its own `now` — there is no injectable clock on
    this path.
    """
    def stamp(hours):
        when = datetime.now(timezone.utc) + timedelta(hours=hours)
        return when.strftime("%Y%m%dT%H%M%SZ")

    lines = ["BEGIN:VCALENDAR"]
    for flight, origin, destination, hours in entries:
        lines += [
            "BEGIN:VEVENT",
            "SUMMARY:%s %s-%s" % (flight, origin, destination),
            "CATEGORIES:FLT",
            "DTSTART:%s" % stamp(hours),
            "DTEND:%s" % stamp(hours + 1),
            "END:VEVENT",
        ]
    lines.append("END:VCALENDAR")
    return ("\r\n".join(lines) + "\r\n").encode("utf-8")


def seed_unresolved_prefixes(state_dir, registry):
    """Write `registry` as `poll_state.json`'s `unresolved_prefixes` value
    — mirrors `companion/test_status_pages.py`'s own helper of the same
    name exactly (phase 13 plan 13-06), since that is the exact D-11
    membership set `unresolved_row_for_prefix()` reads.
    """
    poll_loop.save_poll_state(state_dir, {"unresolved_prefixes": registry})


def encode_multipart(
        payload, boundary=b"SkyPaneTestBoundary7Q2vpH",
        filename="upload.png", field_name="file", content_type="image/png"):
    """Hand-build a single-file `multipart/form-data` body (quick task
    260902-v26's own helper, renamed without its leading underscore now
    that 33-15..33-18 all need it): this module deliberately does not
    import a multipart-encoding library, matching
    `companion.app.parse_single_uploaded_file()`'s own zero-third-party-
    dependency discipline. Returns `(body_bytes, content_type_header)`.
    """
    boundary_str = boundary.decode("ascii")
    header = (
        'Content-Disposition: form-data; name="%s"; filename="%s"\r\n'
        'Content-Type: %s\r\n\r\n'
    ) % (field_name, filename, content_type)
    body = (
        b"--" + boundary + b"\r\n"
        + header.encode("utf-8")
        + payload
        + b"\r\n--" + boundary + b"--\r\n"
    )
    return body, "multipart/form-data; boundary=%s" % boundary_str
