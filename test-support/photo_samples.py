"""Procedural upload samples for the photo pipeline tests.

Everything is generated in memory from Pillow primitives and a seeded
``random.Random``; no binary fixture is committed and no image shows a
real person.
"""

from __future__ import annotations

import io
import random

from PIL import Image, ImageCms

HTML_BYTES = b"<!DOCTYPE html><html><body><script>alert(1)</script></body></html>"
GIF_BYTES = b"GIF89a\x01\x00\x01\x00\x00\x00\x00;"
BMP_BYTES = b"BM" + b"\x00" * 60
TIFF_BYTES = b"II*\x00\x08\x00\x00\x00" + b"\x00" * 40
SVG_BYTES = b'<svg xmlns="http://www.w3.org/2000/svg" width="400" height="400"></svg>'
PDF_BYTES = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF\n"

_MODE_COLOURS: dict[str, object] = {
    "RGB": (200, 120, 60),
    "RGBA": (200, 120, 60, 255),
    "P": 7,
    "L": 128,
    "CMYK": (0, 120, 200, 20),
    "I;16": 40000,
}


def gradient_image(width: int, height: int, mode: str = "RGB") -> Image.Image:
    """Return a smooth two-axis gradient of the given size and mode."""
    base = Image.new("RGB", (width, height))
    px = base.load()
    assert px is not None
    for y in range(height):
        for x in range(width):
            px[x, y] = (x * 255 // max(1, width - 1), y * 255 // max(1, height - 1), 90)
    if mode == "RGB":
        return base
    if mode == "RGBA":
        return base.convert("RGBA")
    if mode == "P":
        return base.convert("P", palette=Image.Palette.ADAPTIVE, colors=64)
    if mode == "L":
        return base.convert("L")
    if mode == "CMYK":
        return base.convert("CMYK")
    raise ValueError(mode)


def flat_image(width: int, height: int, mode: str = "RGB") -> Image.Image:
    """Return a single-colour image; mode ``I;16`` is a mid-grey 16-bit canvas."""
    if mode == "I;16":
        img = Image.new("I;16", (width, height), 40000)
        return img
    return Image.new(mode, (width, height), _MODE_COLOURS[mode])  # type: ignore[arg-type]


def encode(img: Image.Image, fmt: str, **kwargs: object) -> bytes:
    """Serialise an image with Pillow in the given format."""
    buf = io.BytesIO()
    img.save(buf, fmt, **kwargs)  # type: ignore[arg-type]
    return buf.getvalue()


def jpeg_bytes(width: int = 640, height: int = 480, mode: str = "RGB", **kwargs: object) -> bytes:
    """Make a baseline JPEG of a gradient (RGB, L or CMYK modes)."""
    return encode(gradient_image(width, height, mode), "JPEG", **kwargs)


def png_bytes(width: int = 640, height: int = 480, mode: str = "RGB", **kwargs: object) -> bytes:
    """Make a PNG of the given mode (RGB, RGBA, P, L or 16-bit I;16)."""
    if mode == "I;16":
        return encode(flat_image(width, height, mode), "PNG", **kwargs)
    return encode(gradient_image(width, height, mode), "PNG", **kwargs)


def webp_bytes(width: int = 640, height: int = 480, **kwargs: object) -> bytes:
    """Make a still lossy WebP of a gradient."""
    return encode(gradient_image(width, height), "WEBP", **kwargs)


def animated_webp_bytes(width: int = 320, height: int = 320) -> bytes:
    """Make a two-frame animated WebP."""
    first = Image.new("RGB", (width, height), (255, 0, 0))
    second = Image.new("RGB", (width, height), (0, 0, 255))
    return encode(first, "WEBP", save_all=True, append_images=[second], duration=100)


def animated_png_bytes(width: int = 320, height: int = 320) -> bytes:
    """Make a two-frame animated PNG."""
    first = Image.new("RGB", (width, height), (255, 0, 0))
    second = Image.new("RGB", (width, height), (0, 0, 255))
    return encode(first, "PNG", save_all=True, append_images=[second], duration=100)


def mpo_bytes(width: int = 640, height: int = 480) -> bytes:
    """Make a two-frame MPO phone-style JPEG (``format == "MPO"``)."""
    first = gradient_image(width, height)
    second = gradient_image(width // 2, height // 2)
    return encode(first, "MPO", save_all=True, append_images=[second])


def noise_image(width: int, height: int, seed: int = 1) -> Image.Image:
    """Return deterministic RGB noise, the worst case for JPEG size."""
    rng = random.Random(seed)
    return Image.frombytes("RGB", (width, height), rng.randbytes(width * height * 3))


def noise_jpeg_bytes(width: int, height: int, seed: int = 1) -> bytes:
    """Make a high-quality JPEG of deterministic noise."""
    return encode(noise_image(width, height, seed), "JPEG", quality=95)


def bomb_png_bytes(width: int, height: int) -> bytes:
    """Make a tiny 1-bit PNG whose header declares a huge canvas.

    The IDAT stream is compressed zeros, so the file stays a few KB while
    the declared size implies a very large decode.
    """
    import struct
    import zlib

    def chunk(tag: bytes, data: bytes) -> bytes:
        body = tag + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body))

    ihdr = struct.pack(">IIBBBBB", width, height, 1, 0, 0, 0, 0)
    row = b"\x00" * (1 + (width + 7) // 8)
    comp = zlib.compressobj(9)
    data = comp.compress(row) + comp.flush()
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", data) + chunk(b"IEND", b"")


def truncated_jpeg_bytes(width: int = 800, height: int = 600) -> bytes:
    """Make a JPEG whose entropy-coded data is cut in half."""
    full = encode(noise_image(width, height, 3), "JPEG", quality=90)
    return full[: len(full) // 2]


def heic_bytes(brand: bytes = b"heic") -> bytes:
    """Make bytes that begin with an ISO-BMFF ``ftyp`` box of a HEIF brand."""
    box = b"ftyp" + brand + b"\x00\x00\x00\x00" + brand + b"mif1"
    return (len(box) + 4).to_bytes(4, "big") + box + b"\x00" * 64


def marker_image(width: int = 400, height: int = 300) -> Image.Image:
    """Return a white image with a red block in the top-left corner only."""
    img = Image.new("RGB", (width, height), (255, 255, 255))
    img.paste((255, 0, 0), (0, 0, width // 4, height // 4))
    return img


def orient_for_exif(upright: Image.Image, orientation: int) -> Image.Image:
    """Return the pixel layout a camera stores for the given EXIF orientation.

    Applying the matching EXIF transpose to the result gives ``upright``.
    """
    ops = {
        1: [],
        2: [Image.Transpose.FLIP_LEFT_RIGHT],
        3: [Image.Transpose.ROTATE_180],
        4: [Image.Transpose.FLIP_TOP_BOTTOM],
        5: [Image.Transpose.TRANSPOSE],
        6: [Image.Transpose.ROTATE_90],
        7: [Image.Transpose.TRANSVERSE],
        8: [Image.Transpose.ROTATE_270],
    }[orientation]
    img = upright
    for op in ops:
        img = img.transpose(op)
    return img


def jpeg_with_orientation(upright: Image.Image, orientation: int) -> bytes:
    """Make a JPEG that stores ``upright`` rotated per EXIF ``orientation``."""
    exif = Image.Exif()
    exif[0x0112] = orientation
    return encode(orient_for_exif(upright, orientation), "JPEG", quality=95, exif=exif)


def jpeg_with_metadata(
    sentinel_exif: bytes = b"SENTINEL-EXIF-MAKER",
    sentinel_gps: bytes = b"SENTINEL-GPS-REF",
    sentinel_comment: bytes = b"SENTINEL-COMMENT",
    sentinel_icc: bytes = b"SENTINEL-ICC-DESC",
    trailer: bytes = b"SENTINEL-TRAILER",
) -> bytes:
    """Make a JPEG carrying EXIF (incl. a GPS IFD), XMP, comment, ICC and a trailer."""
    exif = Image.Exif()
    exif[0x010F] = sentinel_exif.decode()
    gps = exif.get_ifd(0x8825)
    gps[0x0001] = sentinel_gps.decode()
    xmp = b"<x:xmpmeta SENTINEL-XMP></x:xmpmeta>"
    img = gradient_image(480, 360)
    icc = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()
    icc = icc + sentinel_icc
    data = encode(img, "JPEG", exif=exif, comment=sentinel_comment, icc_profile=icc, xmp=xmp)
    return data + trailer


def png_with_text(text: str = "SENTINEL-PNGTEXT") -> bytes:
    """Make a PNG with a tEXt chunk."""
    from PIL.PngImagePlugin import PngInfo

    info = PngInfo()
    info.add_text("Comment", text)
    return encode(gradient_image(400, 300), "PNG", pnginfo=info)


def srgb_profile_bytes() -> bytes:
    """Return the ICC bytes of the standard sRGB profile."""
    return ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()


def swapped_primaries_profile() -> bytes:
    """Return an RGB profile whose red and green primaries are exchanged.

    Converting an image from this profile to sRGB changes its pixel values
    strongly, which makes a colour-managed path observable.
    """
    data = bytearray(srgb_profile_bytes())
    count = int.from_bytes(data[128:132], "big")
    tags = {}
    for i in range(count):
        sig = bytes(data[132 + 12 * i : 136 + 12 * i])
        off = int.from_bytes(data[136 + 12 * i : 140 + 12 * i], "big")
        tags[sig] = off
    red, green = tags[b"rXYZ"], tags[b"gXYZ"]
    red_body = bytes(data[red + 8 : red + 20])
    data[red + 8 : red + 20] = data[green + 8 : green + 20]
    data[green + 8 : green + 20] = red_body
    return bytes(data)
