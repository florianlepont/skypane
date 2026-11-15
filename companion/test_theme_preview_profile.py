"""Theme and frame previews follow the frame's hardware profile and read
exactly as before on the legacy profile."""
import hashlib
import io

import pytest
from PIL import Image

from companion import theme_preview
from server import hardware

LEGACY = hardware.REGISTRY[hardware.LEGACY_KEY]
LANDSCAPE = hardware.REGISTRY[hardware.EVALUATION_KEY]

# sha256 of the legacy output, captured from the code before the profile
# parameter existed.
LEGACY_GOLDEN = {
    "chip": "a9d404d3f5e1963c20802a35a215f47f4b1954ac1ce2300357e3f5ba1b0cc9f6",
    "chip_layout_b": "d624446ddfa6443bb41baefcf2e75d0d23fafd47780862bcf7390a9e0bb86670",
    ("large", "departing"): "b8f45708ebffc04a65ffdad74aeb50cdf086a8ebd0705ae5f98c8e5bb48378f1",
    ("large", "arriving"): "eb0d938789b4911bf528200d900f69c34cd826bdaa44d1bc20aa8b09c0255ebc",
    ("small", "departing"): "2caa74226986bcd445cd9ed4cda07276dba539f94e715a9ee2a085179f2e3025",
    ("small", "arriving"): "0f996d999eaa5a6382c7fa69e62cea5be1e905e7669fabd8fc17b3bd15780065",
}
LEGACY_FRAME_NAME = "white-departing-small-classic-654ae085ed89.png"
LEGACY_CHIP_NAME = "white-sample-classic-4fe2d5fe6104.png"


def _sha(payload):
    return hashlib.sha256(payload).hexdigest()


def _size(payload):
    return Image.open(io.BytesIO(payload)).size


@pytest.mark.parametrize("profile", [None, LEGACY])
def test_legacy_output_is_byte_identical(profile):
    """the legacy profile (or none) renders the bytes it rendered before profiles existed"""
    kwargs = {} if profile is None else {"profile": profile}
    assert _sha(theme_preview.preview_png_bytes("white", **kwargs)) == LEGACY_GOLDEN["chip"]
    assert _sha(theme_preview.preview_png_bytes("white", layout="b", **kwargs)) == (
        LEGACY_GOLDEN["chip_layout_b"])
    # The overhead picture came later and has no pre-profile bytes.
    for size in theme_preview.FRAME_PREVIEW_SIZES:
        for state in (theme_preview.FRAME_PREVIEW_STATE_DEPARTING,
                      theme_preview.FRAME_PREVIEW_STATE_ARRIVING):
            payload = theme_preview.frame_preview_png_bytes("white", state, size, **kwargs)
            assert _sha(payload) == LEGACY_GOLDEN[(size, state)]


@pytest.mark.parametrize("profile", [None, LEGACY])
def test_legacy_cache_names_are_unchanged(profile):
    assert theme_preview.frame_cache_path(
        "/s", "white", "departing", "small", profile=profile).endswith(
        "/s/frame_previews/" + LEGACY_FRAME_NAME)
    assert theme_preview.cache_path("/s", "white", profile=profile).endswith(
        "/s/theme_previews/" + LEGACY_CHIP_NAME)


@pytest.mark.parametrize("size", theme_preview.FRAME_PREVIEW_SIZES)
def test_pixel_size_for_legacy_is_the_old_table(size):
    assert theme_preview.frame_preview_pixel_size(LEGACY, size) == (
        theme_preview.FRAME_PREVIEW_PIXEL_SIZES[size])
    assert theme_preview.frame_preview_pixel_size(None, size) == (
        theme_preview.FRAME_PREVIEW_PIXEL_SIZES[size])


@pytest.mark.parametrize("size", theme_preview.FRAME_PREVIEW_SIZES)
def test_a_portrait_clone_keeps_the_portrait_shape(size):
    clone = hardware.REGISTRY[hardware.SIM_CLONE_KEY]
    assert theme_preview.frame_preview_pixel_size(clone, size) == (
        theme_preview.FRAME_PREVIEW_PIXEL_SIZES[size])
    assert theme_preview.chip_crop_box(clone) == theme_preview.THEME_PREVIEW_CROP_BOX


@pytest.mark.parametrize("size", theme_preview.FRAME_PREVIEW_SIZES)
@pytest.mark.parametrize("state", theme_preview.FRAME_PREVIEW_STATES)
def test_landscape_frame_preview_png_has_the_landscape_size(size, state):
    width, height = theme_preview.frame_preview_pixel_size(LANDSCAPE, size)
    assert width > height
    assert width * LANDSCAPE.height == height * LANDSCAPE.width
    payload = theme_preview.frame_preview_png_bytes("white", state, size, profile=LANDSCAPE)
    assert _size(payload) == (width, height)


def test_landscape_chip_keeps_the_chip_size_and_a_crop_inside_the_canvas():
    payload = theme_preview.preview_png_bytes("white", profile=LANDSCAPE)
    assert _size(payload) == theme_preview.THEME_PREVIEW_SIZE
    x0, y0, x1, y1 = theme_preview.chip_crop_box(LANDSCAPE)
    assert 0 <= x0 < x1 <= LANDSCAPE.width and 0 <= y0 < y1 <= LANDSCAPE.height
    chip_w, chip_h = theme_preview.THEME_PREVIEW_SIZE
    assert (x1 - x0) * chip_h == (y1 - y0) * chip_w
    assert theme_preview.chip_crop_box(LEGACY) == theme_preview.THEME_PREVIEW_CROP_BOX


def test_two_profiles_never_share_a_cache_file(tmp_path):
    state_dir = str(tmp_path)
    legacy = theme_preview.frame_cache_path(state_dir, "white", "departing", "small")
    landscape = theme_preview.frame_cache_path(
        state_dir, "white", "departing", "small", profile=LANDSCAPE)
    assert legacy != landscape and hardware.EVALUATION_KEY in landscape
    legacy_chip = theme_preview.cache_path(state_dir, "white")
    landscape_chip = theme_preview.cache_path(state_dir, "white", profile=LANDSCAPE)
    assert legacy_chip != landscape_chip and hardware.EVALUATION_KEY in landscape_chip
    assert theme_preview.frame_preview_signature(
        "white", "departing", "small", None, LANDSCAPE) != theme_preview.frame_preview_signature(
        "white", "departing", "small")


def test_cached_previews_are_served_per_profile(tmp_path):
    """a landscape frame is never handed the cached portrait picture, nor the reverse"""
    state_dir = str(tmp_path)
    portrait = theme_preview.cached_frame_preview_bytes(state_dir, "white", "departing", "small")
    landscape = theme_preview.cached_frame_preview_bytes(
        state_dir, "white", "departing", "small", profile=LANDSCAPE)
    assert _size(portrait) == theme_preview.FRAME_PREVIEW_PIXEL_SIZES["small"]
    assert _size(landscape) == theme_preview.frame_preview_pixel_size(LANDSCAPE, "small")
    again = theme_preview.cached_frame_preview_bytes(
        state_dir, "white", "departing", "small", profile=LANDSCAPE)
    assert again == landscape
    chip_p = theme_preview.cached_preview_bytes(state_dir, "white")
    chip_l = theme_preview.cached_preview_bytes(state_dir, "white", profile=LANDSCAPE)
    assert chip_p != chip_l


def test_a_profile_outside_the_registry_is_refused(tmp_path):
    class Fake:
        key = "../../etc"
        width, height = 800, 480

    assert theme_preview.frame_cache_path(
        str(tmp_path), "white", "departing", "small", profile=Fake()) is None
    assert theme_preview.cache_path(str(tmp_path), "white", profile=Fake()) is None


# --- routes and settings pages -----------------------------------------------

def _png(app, path):
    from companion.test_device_helpers import http_request
    status, _headers, body = http_request(app.server.base_url() + path, cookie=app.cookie)
    return status, body


def _fleet_app(make_app_server):
    from companion.test_device_helpers import start_fleet_app
    return start_fleet_app(make_app_server)


def test_preview_routes_follow_the_stored_frame_type(make_app_server):
    """a landscape frame gets landscape pictures, a portrait one is unchanged"""
    app = _fleet_app(make_app_server)
    portrait = "/devices/%s" % app.fleet.dev_a.id
    landscape = "/devices/%s" % app.fleet.landscape.id
    path = "/frame-preview/white.png?state=departing&size=%s"
    for size in theme_preview.FRAME_PREVIEW_SIZES:
        status, body = _png(app, portrait + path % size)
        assert status == 200
        assert _size(body) == theme_preview.FRAME_PREVIEW_PIXEL_SIZES[size]
        status, body = _png(app, landscape + path % size)
        assert status == 200
        assert _size(body) == theme_preview.frame_preview_pixel_size(
            hardware.REGISTRY[hardware.SIM_LANDSCAPE_KEY], size)
    _status, chip_portrait = _png(app, portrait + "/theme-preview/white.png")
    _status, chip_landscape = _png(app, landscape + "/theme-preview/white.png")
    assert _size(chip_portrait) == _size(chip_landscape) == theme_preview.THEME_PREVIEW_SIZE
    assert chip_portrait != chip_landscape
    assert _sha(chip_portrait) == LEGACY_GOLDEN["chip"]


def _frame_images(body):
    import re
    import urllib.parse
    found = []
    for tag in re.findall(r"<img[^>]*>", body):
        src = re.search(r'src="([^"]*)"', tag)
        width = re.search(r'width="(\d+)"', tag)
        height = re.search(r'height="(\d+)"', tag)
        if not (src and width and height) or "frame-preview" not in src.group(1):
            continue
        query = urllib.parse.parse_qs(urllib.parse.urlsplit(src.group(1).replace("&amp;", "&")).query)
        found.append((query.get("size", ["large"])[0], (int(width.group(1)), int(height.group(1)))))
    return found


@pytest.mark.parametrize("page", ["/display", "/display/calendar", "/display/special-looks"])
def test_settings_pages_size_pictures_from_the_frame_profile(make_app_server, page):
    app = _fleet_app(make_app_server)
    from companion.test_device_helpers import get
    landscape_profile = hardware.REGISTRY[hardware.SIM_LANDSCAPE_KEY]
    for device, profile in ((app.fleet.dev_a, hardware.REGISTRY[hardware.SIM_CLONE_KEY]),
                            (app.fleet.landscape, landscape_profile)):
        status, _headers, body = get(app, "/devices/%s%s" % (device.id, page))
        assert status == 200
        images = _frame_images(body)
        assert images, page
        for size, dims in images:
            assert dims == theme_preview.frame_preview_pixel_size(profile, size), (page, size)
