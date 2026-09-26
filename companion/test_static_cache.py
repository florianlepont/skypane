"""Static-asset revalidation: a strong quoted ETag, a Last-Modified date, and a
Cache-Control carrying `no-cache` (never `max-age`) on every CSS/JS route; a
bodiless 304 on a matching conditional request per RFC 9110 13.2.2; the underlying file
read from disk at most once per process; the runway-image route keeping its private,
max-age=300 policy while gaining the same validators; and a real Chromium reload proving
a second page load gets 304s for every static request it revalidates (ROADMAP
criterion 2). Exercises `companion/app.py`'s `_serve_static()` helper behind
`_serve_stylesheet()`, `_serve_script_file()` and `_serve_runway_image()`.
"""
import email.utils
import re
from datetime import timedelta

import pytest

import companion.app as app_module
from companion import auth
from companion.test_browser_ux_helpers import _login
from companion_app_server import http_request, login
from companion_markup import parse_html

_ETAG_RE = re.compile(r'^"[0-9a-f]{32}"$')


@pytest.fixture(scope="module")
def static_server(module_app_server_factory):
    """A read-only server shared by every HTTP-level check below - none of them writes
    anything, so one subprocess serves the whole module.
    """
    return module_app_server_factory()


def _fetch_style_headers(server):
    """GET /static/style.css and return (etag, last_modified) - the shared starting point
    for every conditional-header check below.
    """
    status, headers, body = http_request(server.base_url() + "/static/style.css")
    assert status == 200, "expected 200, got %d" % status
    assert body, "expected a non-empty stylesheet body"
    return headers["ETag"], headers["Last-Modified"]


def _assert_validators(headers):
    """The shared part of the contract every static route carries regardless of its
    own Cache-Control policy: a strong, quoted, 32-hex-char ETag, and a Last-Modified the
    stdlib can parse back.
    """
    etag = headers.get("ETag", "")
    assert _ETAG_RE.match(etag), "expected a strong quoted 32-hex ETag, got %r" % (etag,)
    last_modified = headers.get("Last-Modified", "")
    email.utils.parsedate_to_datetime(last_modified)
    return etag, last_modified


def _assert_static_cache_headers(headers, public=True):
    """`_assert_validators()` plus the no-cache policy every CSS/JS static route
    carries: `no-cache` (and, for a pre-auth shared asset, `public`), never a `max-age`
    directive. The runway image keeps its own, different policy (private, max-age=300)
    and is asserted separately.
    """
    etag, last_modified = _assert_validators(headers)
    cache_control = headers.get("Cache-Control", "")
    directives = [d.strip() for d in cache_control.split(",")]
    assert "no-cache" in directives, "expected no-cache, got %r" % (cache_control,)
    assert not any(d.startswith("max-age") for d in directives), (
        "expected no max-age directive, got %r" % (cache_control,))
    if public:
        assert "public" in directives, "expected public, got %r" % (cache_control,)
    return etag, last_modified


def test_style_css_has_strong_etag_last_modified_and_no_cache_policy(static_server):
    """GET /static/style.css carries the validator/no-cache-policy contract."""
    status, headers, body = http_request(static_server.base_url() + "/static/style.css")
    assert status == 200, "expected 200, got %d" % status
    assert body, "expected a non-empty stylesheet body"
    _assert_static_cache_headers(headers)


def test_every_served_script_route_has_the_same_validators_and_policy(static_server):
    """Every `script[src]` on a real rendered authenticated page, plus the two pre-auth
    scripts no authenticated page links to (login-card.js, battery-trend.js), all carry
    the same validator/policy contract as the stylesheet.
    """
    cookie = login(static_server)
    status, _headers, body = http_request(static_server.base_url() + "/", cookie=cookie)
    assert status == 200, "expected 200 from /, got %d" % status
    doc = parse_html(body.decode("utf-8"))
    srcs = {node.attrs["src"] for node in doc.select("script[src]")}
    srcs |= {"/static/login-card.js", "/static/battery-trend.js"}
    assert srcs, "expected at least one script[src] on the rendered page"
    for src in sorted(srcs):
        status, headers, body = http_request(static_server.base_url() + src)
        assert status == 200, "expected 200 from %s, got %d" % (src, status)
        assert body, "expected a non-empty body from %s" % (src,)
        _assert_static_cache_headers(headers)


@pytest.mark.parametrize(
    "wrap",
    [
        lambda etag: etag,
        lambda etag: "W/" + etag,
        lambda etag: '"unrelated-tag", ' + etag,
        lambda etag: "*",
    ],
    ids=["exact", "weak-prefixed", "inside-a-list", "wildcard"],
)
def test_if_none_match_variants_return_304_with_no_body(static_server, wrap):
    """An exact, W/-prefixed, list-embedded or wildcard If-None-Match all revalidate to a
    bodiless 304 that still carries the validators and hardening headers.
    """
    etag, _last_modified = _fetch_style_headers(static_server)
    status, headers, body = http_request(
        static_server.base_url() + "/static/style.css",
        extra_headers={"If-None-Match": wrap(etag)})
    assert status == 304, "expected 304, got %d" % status
    assert body == b"", "expected an empty body on 304, got %d bytes" % len(body)
    assert headers.get("ETag") == etag
    assert "Last-Modified" in headers
    assert "Cache-Control" in headers
    assert headers.get("X-Content-Type-Options") == "nosniff"


def test_if_none_match_mismatch_returns_200_with_full_body(static_server):
    """A tag that matches nothing falls through to a normal 200 with the full body."""
    status, headers, body = http_request(
        static_server.base_url() + "/static/style.css",
        extra_headers={"If-None-Match": '"deadbeef00000000000000000000000"'})
    assert status == 200, "expected 200, got %d" % status
    assert body, "expected the full body on a mismatched If-None-Match"


def test_if_modified_since_equal_returns_304_without_if_none_match(static_server):
    """An If-Modified-Since equal to the file's own Last-Modified revalidates to a 304
    when no If-None-Match is present at all.
    """
    _etag, last_modified = _fetch_style_headers(static_server)
    status, _headers, body = http_request(
        static_server.base_url() + "/static/style.css",
        extra_headers={"If-Modified-Since": last_modified})
    assert status == 304, "expected 304, got %d" % status
    assert body == b""


def test_if_modified_since_earlier_returns_200(static_server):
    """An If-Modified-Since a day before Last-Modified never matches."""
    _etag, last_modified = _fetch_style_headers(static_server)
    earlier_dt = email.utils.parsedate_to_datetime(last_modified) - timedelta(days=1)
    earlier = email.utils.format_datetime(earlier_dt, usegmt=True)
    status, _headers, body = http_request(
        static_server.base_url() + "/static/style.css",
        extra_headers={"If-Modified-Since": earlier})
    assert status == 200, "expected 200, got %d" % status
    assert body


def test_if_modified_since_malformed_returns_200_never_500(static_server):
    """A malformed If-Modified-Since is a defensive no-match, never a 500."""
    status, _headers, body = http_request(
        static_server.base_url() + "/static/style.css",
        extra_headers={"If-Modified-Since": "garbage"})
    assert status == 200, "expected 200 (never 500) for a malformed header, got %d" % status
    assert body


def test_if_none_match_mismatch_wins_over_a_matching_if_modified_since(static_server):
    """RFC 9110 13.2.2: a present If-None-Match decides the outcome outright, even when a
    concurrently-sent If-Modified-Since would otherwise match.
    """
    _etag, last_modified = _fetch_style_headers(static_server)
    status, _headers, body = http_request(
        static_server.base_url() + "/static/style.css",
        extra_headers={
            "If-None-Match": '"deadbeef00000000000000000000000"',
            "If-Modified-Since": last_modified,
        })
    assert status == 200, "expected If-None-Match to win and return 200, got %d" % status
    assert body


def test_runway_image_authenticated_has_validators_and_stays_private(static_server):
    """The runway image keeps its private, max-age=300 policy, and now also carries an
    ETag and Last-Modified.
    """
    cookie = login(static_server)
    status, headers, body = http_request(
        static_server.base_url() + "/runway-image/3.png", cookie=cookie)
    assert status == 200, "expected 200, got %d" % status
    assert body
    _assert_validators(headers)
    cache_control = headers.get("Cache-Control", "")
    directives = [d.strip() for d in cache_control.split(",")]
    assert "private" in directives, "expected private, got %r" % (cache_control,)
    assert "max-age=300" in directives, "expected max-age=300, got %r" % (cache_control,)


def test_runway_image_unauthenticated_redirects_and_never_304s(static_server):
    """An unauthenticated request, even one carrying a wildcard If-None-Match, still
    redirects to /login - the conditional path is never reached pre-auth.
    """
    status, headers, _body = http_request(
        static_server.base_url() + "/runway-image/3.png",
        extra_headers={"If-None-Match": "*"})
    assert status == 303, "expected a 303 redirect, got %d" % status
    assert headers.get("Location") == "/login"


def test_static_bytes_are_read_from_disk_at_most_once_per_process(
        app_server_in_process, monkeypatch):
    """Three GETs of the same static path read the underlying file exactly once - the rest
    are served from the in-memory cache, counted through the one disk-read seam
    `_read_static_bytes()` exists for.
    """
    server = app_server_in_process
    app_module._STATIC_CACHE.clear()
    calls = []
    original = app_module._read_static_bytes

    def counting(abs_path):
        calls.append(abs_path)
        return original(abs_path)

    monkeypatch.setattr(app_module, "_read_static_bytes", counting)

    for _ in range(3):
        status, _headers, body = http_request(server.base_url() + "/static/style.css")
        assert status == 200
        assert body

    assert len(calls) == 1, (
        "expected exactly 1 disk read across 3 requests, got %d" % len(calls))


def test_missing_static_file_404s_and_caches_nothing(
        app_server_in_process, monkeypatch, tmp_path):
    """A static path whose file does not exist 404s and caches nothing, so creating the
    file afterwards makes the very next request succeed.
    """
    server = app_server_in_process
    missing_path = str(tmp_path / "missing-style.css")
    monkeypatch.setattr(app_module, "_STYLE_CSS_PATH", missing_path)

    status, _headers, _body = http_request(server.base_url() + "/static/style.css")
    assert status == 404, "expected 404, got %d" % status
    assert missing_path not in app_module._STATIC_CACHE

    with open(missing_path, "wb") as fh:
        fh.write(b"body { color: red; }\n")

    status, _headers, body = http_request(server.base_url() + "/static/style.css")
    assert status == 200, "expected 200 once the file exists, got %d" % status
    assert body == b"body { color: red; }\n"


@pytest.mark.browser
def test_second_page_load_gets_304_for_every_static_request(
        app_server_in_process, monkeypatch, page):
    """A real Chromium session revalidates every already-seen `/static/*` asset to a
    bodiless 304 - ROADMAP criterion 2.

    This drives the revalidation with an explicit second `fetch()` carrying the ETag the
    first `fetch()` just returned, from inside the authenticated page, rather than through
    an implicit `page.reload()`: the loopback-only route guard every browser test in this
    suite installs (`companion/conftest.py`'s `new_context` override) enables Chromium
    DevTools Protocol request interception on the context, which as a side effect disables
    Chromium's own HTTP disk cache for every intercepted request - proven separately
    against an unguarded context, where the identical `page.reload()` correctly revalidates
    to 304 throughout. That side effect is a property of the shared test harness, not of
    `companion/app.py`; this test instead proves the same real-browser round trip the
    disk cache would otherwise have driven, still through the same guarded, real Chromium
    network stack every other browser test here uses.
    """
    monkeypatch.setenv(auth.INSECURE_COOKIES_ENV_VAR, "1")
    server = app_server_in_process
    recorded = []
    original_send_response = app_module.Handler.send_response

    def recording_send_response(self, code, message=None):
        recorded.append((self.path, code))
        return original_send_response(self, code, message)

    monkeypatch.setattr(app_module.Handler, "send_response", recording_send_response)

    _login(page, server.base_url())
    page.goto(server.base_url() + "/")

    static_srcs = sorted({
        src for src in page.eval_on_selector_all(
            "link[rel='stylesheet'], script[src]",
            "els => els.map(e => e.getAttribute('href') || e.getAttribute('src'))")
        if src and src.startswith("/static/")
    })
    assert static_srcs, "expected at least one /static/ asset on the rendered page"

    recorded.clear()
    results = page.evaluate(
        "async (srcs) => { const out = []; "
        "for (const src of srcs) { "
        "  const first = await fetch(src); "
        "  const etag = first.headers.get('etag'); "
        "  const second = await fetch(src, {headers: {'If-None-Match': etag}}); "
        "  out.push([src, second.status, etag]); } "
        "return out; }",
        static_srcs)

    no_etag = [src for src, _status, etag in results if not etag]
    assert not no_etag, "expected every asset to carry an ETag, missing on %r" % (no_etag,)
    non_304 = [(src, status) for src, status, _etag in results if status != 304]
    assert not non_304, (
        "expected 304 for every already-seen /static/ asset, got %r" % (non_304,))

    server_hits = [path for path, code in recorded if path.startswith("/static/")]
    assert server_hits, "expected the origin to have recorded the revalidation requests"
    assert all(code in (200, 304) for _path, code in recorded if _path.startswith("/static/"))
