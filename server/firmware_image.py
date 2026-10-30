#!/usr/bin/env python3
"""Stdlib parser and target validator for ESP application images.

The layout follows the ESP-IDF v5.3.1 application image format: a 24-byte
header, segments (each an 8-byte header plus data), the first of which
begins with the 256-byte app descriptor, a checksum byte padding the image
to a 16-byte block, an appended SHA-256 and, for signed images, a single
4 KiB signature sector on the next 4 KiB boundary.

This module checks structure and identity only. It does not verify the
RSA-PSS signature: that is done by espsecure in CI and by the device at
boot. The embedded modulus is exposed solely so a caller can compare key
identity.

Every malformation raises ValueError whose text starts with the field
name ("image", "descriptor", "signature", "chip", "project_name",
"version", "size").
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import os
import re
import struct
import zlib
from dataclasses import dataclass

from server import hardware

_IMAGE_MAGIC = 0xE9
_APP_DESC_MAGIC = 0xABCD5432
_HEADER_LEN = 24
_SEGMENT_HEADER_LEN = 8
_DESC_LEN = 256
_DESC_OFFSET = _HEADER_LEN + _SEGMENT_HEADER_LEN
_MIN_LEN = _DESC_OFFSET + _DESC_LEN
_VERSION_OFFSET = _DESC_OFFSET + 16
_PROJECT_OFFSET = _DESC_OFFSET + 48
_STRING_LEN = 32
_SECTOR = 4096
_SIG_MAGIC = (0xE7, 0x02)
_SIG_DIGEST = (4, 36)
_SIG_MODULUS = (36, 420)
_SIG_CRC_OFFSET = 1196

# DER constants for an RSA SubjectPublicKeyInfo.
_DER_SEQUENCE = 0x30
_DER_INTEGER = 0x02
_DER_BIT_STRING = 0x03
_DER_OID = 0x06
_OID_RSA_ENCRYPTION = bytes.fromhex("2a864886f70d010101")
_RSA_MODULUS_BYTES = 384  # RSA-3072
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_PEM_RE = re.compile(
    rb"-----BEGIN PUBLIC KEY-----\s*([A-Za-z0-9+/=\s]+?)\s*-----END PUBLIC KEY-----"
)

CHIP_IDS: dict[str, int] = {
    "esp32": 0x0000,
    "esp32s2": 0x0002,
    "esp32c3": 0x0005,
    "esp32s3": 0x0009,
    "esp32c2": 0x000C,
    "esp32c6": 0x000D,
    "esp32h2": 0x0010,
    "esp32p4": 0x0012,
}

# Mirrors firmware_registry.RELEASE_TAG_RE / VERSION_RE, which stay the
# single source for version ordering; kept local so this module is a leaf.
_RELEASE_TAG_RE = re.compile(
    r"\Afw-v(0|[1-9][0-9]{0,3})\.(0|[1-9][0-9]{0,3})\.(0|[1-9][0-9]{0,3})\Z"
)
_BENCH_VERSION_RE = re.compile(
    r"\Afw-v(0|[1-9][0-9]{0,3})\.(0|[1-9][0-9]{0,3})\.(0|[1-9][0-9]{0,3})"
    r"(?:-[a-z0-9][a-z0-9.-]{0,23})?\Z"
)


@dataclass(frozen=True)
class AppImage:
    chip_id: int
    version: str
    project_name: str
    image_end: int
    signature_offset: int | None
    modulus: bytes | None  # big-endian, None when unsigned
    size: int


def _cstr(raw: bytes, what: str) -> str:
    """NUL-terminated ASCII string within a fixed field."""
    if b"\0" not in raw:
        raise ValueError(f"descriptor: unterminated {what}")
    try:
        return raw.split(b"\0", 1)[0].decode("ascii")
    except UnicodeDecodeError:
        raise ValueError(f"descriptor: non-ASCII {what}") from None


def _image_end(data: bytes) -> int:
    """Offset just past the appended SHA-256, walking every segment."""
    segments = data[1]
    if segments == 0:
        raise ValueError("image: no segments")
    offset = _HEADER_LEN
    for _ in range(segments):
        if offset + _SEGMENT_HEADER_LEN > len(data):
            raise ValueError("image: segment header past end of file")
        length = struct.unpack_from("<I", data, offset + 4)[0]
        offset += _SEGMENT_HEADER_LEN + length
        if offset > len(data):
            raise ValueError("image: segment past end of file")
    end = (offset + 1 + 15) & ~15
    if data[23] == 1:
        if end + 32 > len(data):
            raise ValueError("image: appended SHA-256 past end of file")
        if hashlib.sha256(data[:end]).digest() != data[end:end + 32]:
            raise ValueError("image: appended SHA-256 mismatch")
        end += 32
    elif end > len(data):
        raise ValueError("image: checksum past end of file")
    return end


def _signature_block(data: bytes, end: int) -> tuple[int | None, bytes | None]:
    """Locate and structurally check the signature sector, if any."""
    pos = (end + _SECTOR - 1) & ~(_SECTOR - 1)
    if len(data) == end:
        return None, None
    if len(data) != pos + _SECTOR:
        raise ValueError("signature: trailing bytes are not one signature sector")
    sector = data[pos:pos + _SECTOR]
    if (sector[0], sector[1]) != _SIG_MAGIC:
        raise ValueError("signature: bad signature block magic")
    if sector[_SIG_DIGEST[0]:_SIG_DIGEST[1]] != hashlib.sha256(data[:pos]).digest():
        raise ValueError("signature: embedded digest does not match image")
    crc = struct.unpack_from("<I", sector, _SIG_CRC_OFFSET)[0]
    if zlib.crc32(sector[:_SIG_CRC_OFFSET]) & 0xFFFFFFFF != crc:
        raise ValueError("signature: block CRC mismatch")
    modulus = bytes(reversed(sector[_SIG_MODULUS[0]:_SIG_MODULUS[1]]))
    return pos, modulus


def parse_app_image(data: bytes) -> AppImage:
    """Parse an ESP application image; ValueError on any malformation."""
    if len(data) < _MIN_LEN:
        raise ValueError("image: too short to be an ESP application image")
    if data[0] != _IMAGE_MAGIC:
        raise ValueError("image: bad header magic")
    chip_id = struct.unpack_from("<H", data, 12)[0]
    if struct.unpack_from("<I", data, _DESC_OFFSET)[0] != _APP_DESC_MAGIC:
        raise ValueError("descriptor: missing app descriptor")
    version = _cstr(data[_VERSION_OFFSET:_VERSION_OFFSET + _STRING_LEN], "version")
    project = _cstr(data[_PROJECT_OFFSET:_PROJECT_OFFSET + _STRING_LEN], "project_name")
    end = _image_end(data)
    sig_offset, modulus = _signature_block(data, end)
    return AppImage(chip_id, version, project, end, sig_offset, modulus, len(data))


def _check_version(found: str, manifest_version: str | None, bench: bool) -> None:
    pattern = _BENCH_VERSION_RE if bench else _RELEASE_TAG_RE
    if not pattern.match(found):
        raise ValueError(f"version: descriptor version {found!r} is not a release version")
    if manifest_version is not None and found != manifest_version:
        raise ValueError(
            f"version: descriptor {found!r} differs from manifest {manifest_version!r}"
        )


def validate_for_target(
    data: bytes,
    target: hardware.FirmwareTarget,
    manifest_version: str | None = None,
    bench: bool = False,
    require_signature: bool = True,
    expected_modulus: bytes | None = None,
    max_bytes: int | None = None,
) -> AppImage:
    """Parse `data` and check it is a release for `target`."""
    expected_chip = CHIP_IDS.get(target.idf_target)
    if expected_chip is None:
        raise ValueError(f"chip: unknown idf_target {target.idf_target!r}")
    image = parse_app_image(data)
    if image.chip_id != expected_chip:
        raise ValueError(
            f"chip: image chip id {image.chip_id:#06x} is not {target.idf_target}"
        )
    if image.project_name != target.project_name:
        raise ValueError(
            f"project_name: {image.project_name!r} is not {target.project_name!r}"
        )
    _check_version(image.version, manifest_version, bench)
    if require_signature and image.signature_offset is None:
        raise ValueError("signature: image is not signed")
    if (expected_modulus is not None and image.modulus is not None
            and image.modulus != expected_modulus):
        raise ValueError("signature: key mismatch")
    limit = target.max_app_bytes if max_bytes is None else max_bytes
    if image.size > limit:
        raise ValueError(f"size: {image.size} bytes exceeds the {limit} byte bound")
    return image


def _der_read(data: bytes, offset: int, tag: int, what: str) -> tuple[bytes, int]:
    """Read one DER element of `tag` at `offset`; (content, next offset)."""
    if offset + 2 > len(data) or data[offset] != tag:
        raise ValueError(f"public_key: unexpected DER structure at {what}")
    first = data[offset + 1]
    pos = offset + 2
    if first < 0x80:
        length = first
    else:
        count = first & 0x7F
        if count == 0 or count > 3 or pos + count > len(data):
            raise ValueError(f"public_key: bad DER length at {what}")
        length = int.from_bytes(data[pos:pos + count], "big")
        pos += count
    if pos + length > len(data):
        raise ValueError(f"public_key: DER {what} runs past the end of the key")
    return data[pos:pos + length], pos + length


def public_key_modulus(pem: str | bytes) -> bytes:
    """Big-endian RSA-3072 modulus of a PEM SubjectPublicKeyInfo key.

    Reads only the public half with a minimal DER walk; raises ValueError
    starting with "public_key" for malformed, non-RSA or non-3072-bit input.
    """
    raw = pem.encode("ascii", "replace") if isinstance(pem, str) else pem
    match = _PEM_RE.search(raw)
    if match is None:
        raise ValueError("public_key: no PEM PUBLIC KEY block found")
    try:
        der = base64.b64decode(b"".join(match.group(1).split()), validate=True)
    except binascii.Error:
        raise ValueError("public_key: PEM body is not valid base64") from None
    spki, end = _der_read(der, 0, _DER_SEQUENCE, "SubjectPublicKeyInfo")
    if end != len(der):
        raise ValueError("public_key: trailing bytes after the key")
    alg, pos = _der_read(spki, 0, _DER_SEQUENCE, "algorithm")
    oid, _ = _der_read(alg, 0, _DER_OID, "algorithm identifier")
    if oid != _OID_RSA_ENCRYPTION:
        raise ValueError("public_key: not an RSA key")
    bits, _ = _der_read(spki, pos, _DER_BIT_STRING, "key bit string")
    if not bits or bits[0] != 0:
        raise ValueError("public_key: bad key bit string padding")
    rsa, _ = _der_read(bits[1:], 0, _DER_SEQUENCE, "RSAPublicKey")
    number, _ = _der_read(rsa, 0, _DER_INTEGER, "modulus")
    modulus = number.lstrip(b"\0")
    if len(modulus) != _RSA_MODULUS_BYTES:
        raise ValueError(
            f"public_key: modulus is {len(modulus) * 8} bits, expected RSA-3072"
        )
    return modulus


def load_public_key_modulus(path: str) -> bytes:
    """`public_key_modulus` of the PEM file at `path`."""
    try:
        with open(path, "rb") as fh:
            return public_key_modulus(fh.read())
    except OSError as exc:
        raise ValueError(f"public_key: cannot read {path}: {exc.strerror}") from None


def signing_policy(target: hardware.FirmwareTarget) -> tuple[bool, bytes | None]:
    """(require_signature, expected_modulus) for images of `target`.

    The expected modulus is read from the target's repo-relative public key
    path; an unreadable or malformed key raises ValueError (fail closed).
    """
    if target.signing_pubkey is None:
        return target.require_signature, None
    modulus = load_public_key_modulus(os.path.join(_REPO_ROOT, target.signing_pubkey))
    return target.require_signature, modulus
