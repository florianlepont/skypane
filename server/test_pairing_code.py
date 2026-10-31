"""Pairing code issue, normalisation, hashing and constant-time matching."""
from __future__ import annotations

import hashlib
import hmac
import importlib
import secrets
import sys

import pytest

from server import pairing_code

FAKE_CODE = "ABCD2345"


def test_alphabet_and_generate_use_secrets(monkeypatch: pytest.MonkeyPatch) -> None:
    assert len(pairing_code.ALPHABET) == 30
    assert len(set(pairing_code.ALPHABET)) == 30
    assert not set("01ILOU") & set(pairing_code.ALPHABET)
    calls: list[str] = []

    def fake_choice(seq: str) -> str:
        calls.append(seq)
        return seq[0]

    monkeypatch.setattr(secrets, "choice", fake_choice)
    code = pairing_code.generate_code()
    assert len(code) == 8
    assert len(calls) == 8
    assert set(code) <= set(pairing_code.ALPHABET)
    real = pairing_code
    monkeypatch.undo()
    for _ in range(50):
        assert set(real.generate_code()) <= set(real.ALPHABET)


def test_format_and_normalise() -> None:
    assert pairing_code.format_code(FAKE_CODE) == "ABCD-2345"
    for typed in ("abcd2345", "ABCD-2345", " abcd 2345 ", "abcd-2345"):
        assert pairing_code.normalise_code(typed) == FAKE_CODE
    assert pairing_code.normalise_code("ABCD234") is None
    assert pairing_code.normalise_code("ABCD23456") is None
    assert pairing_code.normalise_code("ABCD234U") is None
    assert pairing_code.normalise_code("ABCD234!") is None
    # O, I and L fold to 0 and 1, which are not in the alphabet.
    assert pairing_code.normalise_code("ABCD234O") is None
    assert pairing_code.normalise_code("ABCD234I") is None
    assert pairing_code.normalise_code("ABCD234l") is None


def test_hash_and_salt() -> None:
    expected = hashlib.sha256(("aa" + FAKE_CODE).encode()).hexdigest()
    assert pairing_code.hash_code("aa", FAKE_CODE) == expected
    assert pairing_code.hash_code("aa", FAKE_CODE) != pairing_code.hash_code("bb", FAKE_CODE)
    salt = pairing_code.new_salt()
    assert len(salt) == 16
    int(salt, 16)


def _row(salt: str, code: str, expires: int) -> dict[str, object]:
    return {
        "code_salt": salt,
        "code_hash": pairing_code.hash_code(salt, code),
        "code_expires_at": expires,
    }


def test_match_candidates_scans_every_row(monkeypatch: pytest.MonkeyPatch) -> None:
    rows = [
        _row("s1", "22222222", 2000),
        _row("s2", FAKE_CODE, 2000),
        _row("s3", "33333333", 2000),
    ]
    count = 0
    real = hmac.compare_digest

    def counting(a: bytes, b: bytes) -> bool:
        nonlocal count
        count += 1
        return real(a, b)

    monkeypatch.setattr(hmac, "compare_digest", counting)
    assert pairing_code.match_candidates(rows, FAKE_CODE, 1000) is rows[1]
    assert count == len(rows)
    count = 0
    assert pairing_code.match_candidates(rows, "44444444", 1000) is None
    assert count == len(rows)
    count = 0
    assert pairing_code.match_candidates([], FAKE_CODE, 1000) is None
    assert count == 1


def test_expired_match_is_none() -> None:
    rows = [_row("s1", FAKE_CODE, 1000)]
    assert pairing_code.match_candidates(rows, FAKE_CODE, 1000) is None
    assert pairing_code.match_candidates(rows, FAKE_CODE, 999) is rows[0]


def test_constants() -> None:
    assert pairing_code.CODE_TTL_S == 1800
    assert pairing_code.PENDING_SLEEP_S == 300
    assert pairing_code.RETIRED_SLEEP_S == 86400


def test_module_does_not_need_sqlite(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(sys.modules, "sqlite3", None)
    monkeypatch.delitem(sys.modules, "server.pairing_code", raising=False)
    fresh = importlib.import_module("server.pairing_code")
    assert fresh.format_code(FAKE_CODE) == "ABCD-2345"
