"""Synthetic ESP application image builder for tests.

Produces structurally valid images (header, one segment holding the 256-byte
app descriptor, checksum, appended SHA-256 and, when signed, a 4 KiB
signature sector with a correct embedded digest and CRC32). The RSA
signature bytes are filler: these images pass the structural checks of
server.firmware_image but are not cryptographically signed.
"""

from __future__ import annotations

import hashlib
import struct
import zlib

APP_DESC_MAGIC = 0xABCD5432
SECTOR = 4096
MODULUS_BYTES = 384
CORRUPTIONS = (
    "digest",
    "signature_digest",
    "truncate",
    "unterminated_version",
    "magic",
    "descriptor_magic",
)


def default_modulus() -> bytes:
    """Deterministic 384-byte big-endian modulus (top bit set)."""
    out = b""
    counter = 0
    while len(out) < MODULUS_BYTES:
        out += hashlib.sha256(b"skypane-test-modulus-%d" % counter).digest()
        counter += 1
    return bytes([out[0] | 0x80]) + out[1:MODULUS_BYTES]


def _descriptor(version: str, project_name: str, corrupt: str | None) -> bytes:
    desc = bytearray(256)
    magic = 0 if corrupt == "descriptor_magic" else APP_DESC_MAGIC
    struct.pack_into("<I", desc, 0, magic)
    ver = b"A" * 32 if corrupt == "unterminated_version" else version.encode("ascii")
    desc[16:16 + len(ver[:32])] = ver[:32]
    name = project_name.encode("ascii")
    desc[48:48 + len(name[:32])] = name[:32]
    return bytes(desc)


def _body(
    descriptor: bytes, chip_id: int, seg_len: int, corrupt: str | None
) -> bytes:
    header = bytearray(24)
    header[0] = 0 if corrupt == "magic" else 0xE9
    header[1] = 1
    struct.pack_into("<H", header, 12, chip_id)
    header[23] = 1
    data = descriptor + bytes(seg_len - len(descriptor))
    segment = struct.pack("<II", 0x3C000000, seg_len) + data
    raw = bytes(header) + segment
    checksum_pos = ((len(raw) + 1 + 15) & ~15) - 1
    raw += bytes(checksum_pos - len(raw))
    check = 0xEF
    for byte in data:
        check ^= byte
    raw += bytes([check])
    digest = hashlib.sha256(raw).digest()
    if corrupt == "digest":
        digest = bytes([digest[0] ^ 0xFF]) + digest[1:]
    return raw + digest


def _signature_sector(prefix: bytes, modulus: bytes, corrupt: str | None) -> bytes:
    digest = hashlib.sha256(prefix).digest()
    if corrupt == "signature_digest":
        digest = bytes([digest[0] ^ 0xFF]) + digest[1:]
    sector = bytearray(b"\xff" * SECTOR)
    sector[0:4] = b"\xe7\x02\x00\x00"
    sector[4:36] = digest
    sector[36:36 + MODULUS_BYTES] = modulus[::-1]
    struct.pack_into("<I", sector, 36 + MODULUS_BYTES, 65537)
    crc = zlib.crc32(bytes(sector[:1196])) & 0xFFFFFFFF
    struct.pack_into("<I", sector, 1196, crc)
    return bytes(sector)


def _assemble(
    version: str,
    project_name: str,
    chip_id: int,
    seg_len: int,
    signed: bool,
    modulus: bytes,
    corrupt: str | None,
) -> bytes:
    descriptor = _descriptor(version, project_name, corrupt)
    body = _body(descriptor, chip_id, seg_len, corrupt)
    if not signed:
        return body
    pos = (len(body) + SECTOR - 1) & ~(SECTOR - 1)
    prefix = body + b"\xff" * (pos - len(body))
    return prefix + _signature_sector(prefix, modulus, corrupt)


def build_image(
    version: str,
    project_name: str = "skypane",
    chip_id: int = 0x0009,
    size: int | None = None,
    signed: bool = True,
    modulus: bytes | None = None,
    corrupt: str | None = None,
) -> bytes:
    """Build a synthetic image of at least `size` bytes.

    `modulus` is the big-endian RSA modulus to embed (384 bytes).
    `corrupt` names one defect from CORRUPTIONS for negative tests.
    """
    if corrupt is not None and corrupt not in CORRUPTIONS:
        raise ValueError("corrupt: unknown variant %r" % (corrupt,))
    mod = default_modulus() if modulus is None else modulus
    if len(mod) != MODULUS_BYTES:
        raise ValueError("modulus: must be %d bytes" % MODULUS_BYTES)
    seg_len = 256
    data = _assemble(version, project_name, chip_id, seg_len, signed, mod, corrupt)
    while size is not None and len(data) < size:
        seg_len += ((size - len(data)) + 3) & ~3
        data = _assemble(version, project_name, chip_id, seg_len, signed, mod, corrupt)
    if corrupt == "truncate":
        data = data[:-100]
    return data
