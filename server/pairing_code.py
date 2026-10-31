"""Pairing codes: issue, normalise, hash and match.

A pairing code is the only secret of the frame pairing flow. It is shown on
the frame's panel, typed once by an administrator and stored only as a
salted SHA-256 hash. This module is pure: no database, no HTTP, no logging.
A code is never formatted into an exception message.
"""
from __future__ import annotations

import hashlib
import hmac
import secrets
from collections.abc import Mapping, Sequence

# Digits and letters without 0, 1, I, L, O, U: the look-alike pairs
# (0/O, 1/I/L) and U (easily read as V) cannot be misread off a panel.
# 30 symbols over 8 positions is about 39 bits.
ALPHABET = "23456789ABCDEFGHJKMNPQRSTVWXYZ"
CODE_LENGTH = 8
GROUP_LENGTH = 4

# Seconds a code stays claimable.
CODE_TTL_S = 1800
# Seconds an unpaired frame sleeps between pairing polls.
PENDING_SLEEP_S = 300
# Seconds a retired frame sleeps: the firmware's inclusive sleep ceiling.
RETIRED_SLEEP_S = 86400

_SALT_BYTES = 8
_DUMMY_SALT = "0" * (_SALT_BYTES * 2)
_DUMMY_HASH = "0" * 64

# Look-alike characters a person may type for an issued symbol. They are
# never in an issued code, so a folded guess simply fails to match.
_FOLD = str.maketrans({"O": "0", "I": "1", "L": "1"})


def generate_code() -> str:
    """A fresh code of CODE_LENGTH symbols from ALPHABET, upper case."""
    return "".join(secrets.choice(ALPHABET) for _ in range(CODE_LENGTH))


def format_code(code: str) -> str:
    """The display form XXXX-XXXX of an 8-character code."""
    return f"{code[:GROUP_LENGTH]}-{code[GROUP_LENGTH:]}"


def normalise_code(raw: str) -> str | None:
    """The 8-character upper-case code for what a person typed, or None.

    Case, spaces and the hyphen are ignored. O, I and L fold to 0 and 1,
    which are outside the alphabet, so a folded guess cannot match.
    """
    folded = "".join(raw.split()).replace("-", "").upper().translate(_FOLD)
    if len(folded) != CODE_LENGTH:
        return None
    if any(ch not in ALPHABET for ch in folded):
        return None
    return folded


def new_salt() -> str:
    """A random per-row salt, 16 hex characters."""
    return secrets.token_hex(_SALT_BYTES)


def hash_code(salt: str, code: str) -> str:
    """Lowercase hex SHA-256 over the salt then the code."""
    return hashlib.sha256((salt + code).encode("utf-8")).hexdigest()


def match_candidates(
    rows: Sequence[Mapping[str, object]], code: str, now: int
) -> Mapping[str, object] | None:
    """The one row whose hash matches `code` and whose expiry is after `now`.

    Every row is compared with hmac.compare_digest and the loop never exits
    early, so timing does not reveal which row (if any) matched. An empty
    candidate list still performs one compare, so "no pending frames" and
    "wrong code" take the same path.
    """
    if not rows:
        hmac.compare_digest(
            hash_code(_DUMMY_SALT, code).encode("ascii"), _DUMMY_HASH.encode("ascii")
        )
        return None
    matched: Mapping[str, object] | None = None
    for row in rows:
        expected = str(row["code_hash"]).encode("utf-8", "surrogateescape")
        presented = hash_code(str(row["code_salt"]), code).encode("ascii")
        equal = hmac.compare_digest(presented, expected)
        expires = row["code_expires_at"]
        live = isinstance(expires, int) and expires > now
        if equal and live and matched is None:
            matched = row
    return matched
