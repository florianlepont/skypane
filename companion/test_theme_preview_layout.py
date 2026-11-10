"""Layout-aware theme and frame previews: the picture differs per layout,
the caches never share a file across layouts, and the routes accept a
layout only from the allow-list.

Asserted on served PNG bytes and on cache directory contents.
"""
import os

import pytest

from companion import theme_preview
from companion_app_server import get, login
from server import screen_layouts


@pytest.fixture(scope="module")
def server(module_app_server_factory):
    return module_app_server_factory()


@pytest.fixture(scope="module")
def cookie(server):
    return login(server)


def test_frame_preview_route_serves_a_different_picture_for_layout_b(server, cookie):
    """layout=b is a PNG that differs from the same request without a layout"""
    base = "/frame-preview/white.png?state=departing&size=small"
    plain_status, _h, plain = get(server, base, cookie=cookie)
    b_status, _h, with_b = get(server, base + "&layout=b", cookie=cookie)
    classic_status, _h, with_classic = get(server, base + "&layout=classic", cookie=cookie)
    assert plain_status == b_status == classic_status == 200
    assert with_b[:8] == b"\x89PNG\r\n\x1a\n"
    assert with_b != plain
    assert with_classic == plain


def test_theme_preview_route_serves_a_different_picture_for_layout_b(server, cookie):
    """the chip crop also differs per layout"""
    _s, _h, plain = get(server, "/theme-preview/white.png", cookie=cookie)
    status, _h, with_b = get(server, "/theme-preview/white.png?layout=b", cookie=cookie)
    assert status == 200 and with_b != plain


@pytest.mark.parametrize("path", [
    "/frame-preview/white.png?layout=../x",
    "/frame-preview/white.png?layout=nope",
    "/frame-preview/white.png?layout=",
    "/theme-preview/white.png?layout=../x",
    "/theme-preview/white.png?layout=B",
])
def test_unknown_layout_is_refused_like_an_unknown_theme(server, cookie, path):
    """a layout outside the allow-list gets the same 404 an unknown theme gets"""
    refused, _h, refused_body = get(server, path, cookie=cookie)
    unknown_theme, _h, theme_body = get(server, "/frame-preview/nope.png", cookie=cookie)
    assert refused == unknown_theme == 404
    assert refused_body == theme_body


def test_frame_cache_keeps_one_file_per_layout(tmp_path):
    """each layout has its own file and signature; an unknown layout has none"""
    state_dir = str(tmp_path)
    paths = {
        layout_id: theme_preview.frame_cache_path(state_dir, "white", "departing", "small", layout_id)
        for layout_id in screen_layouts.LAYOUT_IDS}
    assert len(set(paths.values())) == len(paths)
    assert theme_preview.frame_cache_path(state_dir, "white", "departing", "small") == paths["classic"]
    assert theme_preview.frame_cache_path(state_dir, "white", "departing", "small", "../x") is None
    first = theme_preview.cached_frame_preview_bytes(state_dir, "white", "departing", "small", "b")
    second = theme_preview.cached_frame_preview_bytes(state_dir, "white", "departing", "small")
    assert first != second
    assert os.path.isfile(paths["b"]) and os.path.isfile(paths["classic"])


def test_theme_cache_keeps_one_file_per_layout(tmp_path):
    """the chip cache path and signature change with the layout"""
    state_dir = str(tmp_path)
    classic = theme_preview.cache_path(state_dir, "white")
    layout_b = theme_preview.cache_path(state_dir, "white", layout="b")
    assert classic != layout_b
    assert theme_preview.cache_path(state_dir, "white", layout="x/y") is None
    assert theme_preview.preview_signature("white", None, "b") != theme_preview.preview_signature("white")


def test_cache_bounds_fit_every_theme_state_size_and_layout():
    """the file-count bounds are not smaller than the reachable file count"""
    from server import device_config
    themes = len(device_config.THEME_IDS)
    layouts = len(screen_layouts.LAYOUT_IDS)
    assert theme_preview.FRAME_PREVIEW_CACHE_MAX_FILES >= themes * layouts * 2 * 2
    assert theme_preview.THEME_PREVIEW_CACHE_MAX_FILES >= themes * layouts


def test_frame_preview_src_adds_layout_only_when_given():
    """the page-side URL is unchanged without a layout"""
    assert "layout" not in theme_preview.frame_preview_src("white")
    assert theme_preview.frame_preview_src("white", layout="b").endswith("&layout=b")
