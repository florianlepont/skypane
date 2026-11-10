"""An unknown asset-like path gets an empty, briefly cacheable 404; an unknown page keeps the 404 page."""
from companion_app_server import InProcessAppServer, http_request


def test_unknown_asset_paths_get_an_empty_404_and_pages_keep_the_404_page(tmp_path):
    server = InProcessAppServer(str(tmp_path / "state"))
    try:
        for path in ("/favicon.ico", "/static/missing.js", "/static/app.js.map",
                     "/robots.txt", "/static/sw.js", "/x/y.PNG?v=1"):
            status, headers, body = http_request(server.url(path))
            assert status == 404 and body == b"", path
            assert headers["Content-Length"] == "0"
            assert "max-age=300" in headers["Cache-Control"]
        status, headers, body = http_request(server.url("/no-such-page-anywhere"))
        assert status == 404 and b"</html>" in body
        assert "no-store" in headers["Cache-Control"]
    finally:
        server.stop()
