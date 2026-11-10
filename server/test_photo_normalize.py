"""Upload normaliser: rejections, accepted inputs, orientation, metadata, limits."""

from __future__ import annotations

import inspect
import io
import time
from pathlib import Path

import pytest
from PIL import Image

import photo_samples as ps
from server.photo import normalize as nz
from server.photo.normalize import PhotoRejected, normalize_upload


def _reason(raw: bytes) -> str:
    with pytest.raises(PhotoRejected) as exc:
        normalize_upload(raw)
    assert str(exc.value) == exc.value.reason
    return exc.value.reason


REJECTIONS = [
    ("empty", b"", "empty"),
    ("oversized", b"\xff" * (nz.MAX_UPLOAD_BYTES + 1), "too_large"),
    ("heic", ps.heic_bytes(b"heic"), "heic_unsupported"),
    ("heif_mif1", ps.heic_bytes(b"mif1"), "heic_unsupported"),
    ("avif", ps.heic_bytes(b"avif"), "heic_unsupported"),
    ("html", ps.HTML_BYTES, "not_an_image"),
    ("gif", ps.GIF_BYTES, "not_an_image"),
    ("bmp", ps.BMP_BYTES, "not_an_image"),
    ("tiff", ps.TIFF_BYTES, "not_an_image"),
    ("svg", ps.SVG_BYTES, "not_an_image"),
    ("pdf", ps.PDF_BYTES, "not_an_image"),
    ("truncated_jpeg", ps.truncated_jpeg_bytes(), "corrupt"),
    ("bomb_9000", ps.bomb_png_bytes(9000, 9000), "too_many_pixels"),
    ("bomb_30000", ps.bomb_png_bytes(30000, 30000), "too_many_pixels"),
    ("animated_webp", ps.animated_webp_bytes(), "animated"),
    ("animated_png", ps.animated_png_bytes(), "animated"),
    ("tiny", ps.jpeg_bytes(100, 100), "too_small"),
    ("thin", ps.png_bytes(2000, 150), "too_small"),
]


@pytest.mark.parametrize(("raw", "reason"), [c[1:] for c in REJECTIONS], ids=[c[0] for c in REJECTIONS])
def test_reject_reason(raw: bytes, reason: str) -> None:
    assert _reason(raw) == reason


def test_reject_bomb_is_fast() -> None:
    started = time.monotonic()
    _reason(ps.bomb_png_bytes(9000, 9000))
    assert time.monotonic() - started < 1.0


def test_reject_message_is_only_the_code() -> None:
    raw = ps.HTML_BYTES + b"secret-name.jpg"
    with pytest.raises(PhotoRejected) as exc:
        normalize_upload(raw)
    assert exc.value.args == ("not_an_image",)
    assert exc.value.__cause__ is None
    assert exc.value.__suppress_context__


def test_mpo_is_not_rejected_as_animated() -> None:
    raw = ps.mpo_bytes()
    assert Image.open(io.BytesIO(raw)).format == "MPO"
    assert Image.open(io.BytesIO(raw)).n_frames == 2
    assert normalize_upload(raw).width > 0


def _open(stored: nz.StoredPhoto) -> Image.Image:
    img = Image.open(io.BytesIO(stored.jpeg))
    img.load()
    return img


ACCEPTED = [
    ("jpeg", ps.jpeg_bytes(1000, 700)),
    ("jpeg_l", ps.jpeg_bytes(800, 600, "L")),
    ("jpeg_cmyk", ps.jpeg_bytes(800, 600, "CMYK")),
    ("png_rgb", ps.png_bytes(900, 600, "RGB")),
    ("png_rgba", ps.png_bytes(900, 600, "RGBA")),
    ("png_palette", ps.png_bytes(900, 600, "P")),
    ("png_grey", ps.png_bytes(900, 600, "L")),
    ("png_16bit", ps.png_bytes(900, 600, "I;16")),
    ("webp", ps.webp_bytes(900, 600)),
    ("mpo", ps.mpo_bytes(1000, 700)),
    ("large", ps.jpeg_bytes(4000, 3000)),
]


@pytest.mark.parametrize(("raw",), [(c[1],) for c in ACCEPTED], ids=[c[0] for c in ACCEPTED])
def test_accept_yields_one_baseline_srgb_jpeg(raw: bytes) -> None:
    stored = normalize_upload(raw)
    img = _open(stored)
    assert img.format == "JPEG"
    assert img.mode == "RGB"
    assert "progressive" not in img.info and "progression" not in img.info
    assert max(img.size) <= nz.STORE_MAX_SIDE
    assert (stored.width, stored.height) == img.size
    assert len(stored.jpeg) <= nz.STORE_MAX_BYTES


def test_accept_never_upscales() -> None:
    stored = normalize_upload(ps.jpeg_bytes(500, 300))
    assert (stored.width, stored.height) == (500, 300)


def test_accept_large_is_reduced_to_long_edge() -> None:
    stored = normalize_upload(ps.jpeg_bytes(4000, 3000))
    assert stored.width == nz.STORE_MAX_SIDE
    assert abs(stored.height - 1536) <= 2


def test_accept_16bit_grey_is_mid_grey_not_white() -> None:
    img = _open(normalize_upload(ps.png_bytes(400, 400, "I;16")))
    r, g, b = img.getpixel((200, 200))
    assert 150 <= r <= 162 and abs(r - g) <= 2 and abs(r - b) <= 2


def test_accept_transparent_pixels_become_white() -> None:
    clear = Image.new("RGBA", (400, 400), (255, 0, 0, 0))
    img = _open(normalize_upload(ps.encode(clear, "PNG")))
    assert min(img.getpixel((200, 200))) >= 250


@pytest.mark.parametrize("orientation", range(1, 9))
def test_orientation_yields_upright_copy(orientation: int) -> None:
    upright = ps.marker_image(400, 300)
    img = _open(normalize_upload(ps.jpeg_with_orientation(upright, orientation)))
    assert img.size == (400, 300)
    r, g, b = img.getpixel((20, 20))
    assert r > 200 and g < 80 and b < 80
    assert min(img.getpixel((380, 280))) > 200
    assert min(img.getpixel((380, 20))) > 200
    assert min(img.getpixel((20, 280))) > 200


SENTINELS = [
    b"SENTINEL-EXIF-MAKER",
    b"SENTINEL-GPS-REF",
    b"SENTINEL-COMMENT",
    b"SENTINEL-ICC-DESC",
    b"SENTINEL-XMP",
    b"SENTINEL-TRAILER",
    b"SENTINEL-PNGTEXT",
    b"Exif",
    b"ICC_PROFILE",
    b"http://ns.adobe.com",
]


@pytest.mark.parametrize("raw", [ps.jpeg_with_metadata(), ps.png_with_text()], ids=["jpeg", "png"])
def test_metadata_is_absent_from_stored_bytes(raw: bytes) -> None:
    stored = normalize_upload(raw)
    for sentinel in SENTINELS:
        assert sentinel not in stored.jpeg
    img = _open(stored)
    assert len(img.getexif()) == 0
    assert "icc_profile" not in img.info
    assert "comment" not in img.info
    assert stored.jpeg.rstrip(b"\x00").endswith(b"\xff\xd9")


def test_metadata_input_really_carries_the_sentinels() -> None:
    raw = ps.jpeg_with_metadata()
    for sentinel in SENTINELS[:6]:
        assert sentinel in raw


def _centre_pixel(raw: bytes) -> tuple[int, int, int]:
    px = _open(normalize_upload(raw)).getpixel((200, 200))
    assert isinstance(px, tuple)
    return px[0], px[1], px[2]


def _tagged_png(icc: bytes | None) -> bytes:
    img = Image.new("RGB", (400, 400), (200, 60, 30))
    return ps.encode(img, "PNG", icc_profile=icc) if icc else ps.encode(img, "PNG")


def test_icc_garbage_profile_does_not_reject() -> None:
    plain = _centre_pixel(_tagged_png(None))
    junk = _centre_pixel(_tagged_png(b"not an icc profile at all" * 20))
    assert max(abs(a - b) for a, b in zip(plain, junk, strict=True)) <= 3


def test_icc_srgb_profile_leaves_pixels_unchanged() -> None:
    plain = _centre_pixel(_tagged_png(None))
    tagged = _centre_pixel(_tagged_png(ps.srgb_profile_bytes()))
    assert max(abs(a - b) for a, b in zip(plain, tagged, strict=True)) <= 4


def test_icc_other_profile_is_converted() -> None:
    plain = _centre_pixel(_tagged_png(None))
    tagged = _centre_pixel(_tagged_png(ps.swapped_primaries_profile()))
    assert max(abs(a - b) for a, b in zip(plain, tagged, strict=True)) > 30


def test_ladder_noise_ends_within_byte_budget() -> None:
    raw = ps.noise_jpeg_bytes(3000, 2000)
    assert len(raw) <= nz.MAX_UPLOAD_BYTES
    stored = normalize_upload(raw)
    assert len(stored.jpeg) <= nz.STORE_MAX_BYTES
    assert max(stored.width, stored.height) <= nz.STORE_MAX_SIDE


def test_ladder_flat_8000x6000_uses_draft_and_is_quick() -> None:
    raw = ps.encode(Image.new("RGB", (8000, 6000), (30, 90, 160)), "JPEG")
    started = time.monotonic()
    stored = normalize_upload(raw)
    assert time.monotonic() - started < 5.0
    assert stored.width == nz.STORE_MAX_SIDE


def test_original_not_kept(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    raw = ps.jpeg_with_metadata()
    stored = normalize_upload(raw)
    assert list(tmp_path.iterdir()) == []
    assert raw not in stored.jpeg
    assert raw[: len(raw) // 2] not in stored.jpeg
    assert list(inspect.signature(normalize_upload).parameters) == ["raw"]
