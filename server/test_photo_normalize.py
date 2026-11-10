"""Upload normaliser: rejections, accepted inputs, orientation, metadata, limits."""

from __future__ import annotations

import io
import time

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
    # The decode half is exercised by the accept tests; header checks pass.
    nz._open_checked(raw)
