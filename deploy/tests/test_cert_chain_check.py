"""deploy/tests/test_cert_chain_check.py -- offline proof of
scripts/check_cert_chain.py's `verify` decision, against throwaway
fixture chains this file generates itself with the `openssl` CLI (no
committed private keys, no network). `fetch`/`check` reach a real host
and are exercised only by the workflow that runs them in CI, never here
-- the pytest-socket non-loopback guard would block them anyway.
"""
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_SCRIPT = _REPO_ROOT / "scripts" / "check_cert_chain.py"

_LEAF_EXT = [
    "basicConstraints=critical,CA:false",
    "keyUsage=critical,digitalSignature,keyEncipherment",
    "extendedKeyUsage=serverAuth",
]
_CA_EXT = [
    "basicConstraints=critical,CA:true",
    "keyUsage=critical,keyCertSign,cRLSign",
]


def _openssl(args):
    result = subprocess.run(
        ["openssl"] + args, capture_output=True, text=True, timeout=30
    )
    assert result.returncode == 0, "openssl %s failed: %s" % (args, result.stderr)
    return result


def _make_root(dir_, stem, cn):
    key = dir_ / ("%s.key" % stem)
    cert = dir_ / ("%s.pem" % stem)
    _openssl([
        "req", "-x509", "-newkey", "rsa:2048", "-keyout", str(key), "-out", str(cert),
        "-days", "3650", "-nodes", "-subj", "/CN=%s" % cn,
        "-addext", "basicConstraints=critical,CA:true",
        "-addext", "keyUsage=critical,keyCertSign,cRLSign",
    ])
    return key, cert


def _make_signed(dir_, stem, cn, ca_key, ca_cert, ext_lines, not_before=None, not_after=None):
    key = dir_ / ("%s.key" % stem)
    csr = dir_ / ("%s.csr" % stem)
    cert = dir_ / ("%s.pem" % stem)
    extfile = dir_ / ("%s.ext" % stem)
    extfile.write_text("\n".join(ext_lines) + "\n")
    _openssl([
        "req", "-newkey", "rsa:2048", "-keyout", str(key), "-out", str(csr),
        "-nodes", "-subj", "/CN=%s" % cn,
    ])
    args = [
        "x509", "-req", "-in", str(csr),
        "-CA", str(ca_cert), "-CAkey", str(ca_key),
        "-CAcreateserial", "-CAserial", str(dir_ / ("%s.srl" % stem)),
        "-out", str(cert), "-extfile", str(extfile),
    ]
    if not_before is not None and not_after is not None:
        args += ["-not_before", not_before, "-not_after", not_after]
    else:
        args += ["-days", "1000"]
    _openssl(args)
    return key, cert


@pytest.fixture(scope="module")
def certs(tmp_path_factory):
    """Two independent throwaway CA hierarchies (root A / intermediate A /
    leaf A, and root B / intermediate B / leaf B), plus an expired leaf
    reissued under intermediate A, all generated fresh in tmp_path with no
    network and no committed key material.
    """
    d = tmp_path_factory.mktemp("chain-certs")

    root_a_key, root_a_cert = _make_root(d, "rootA", "Test Root A")
    root_b_key, root_b_cert = _make_root(d, "rootB", "Test Root B")

    int_a_key, int_a_cert = _make_signed(
        d, "intA", "Test Intermediate A", root_a_key, root_a_cert, _CA_EXT
    )
    leaf_a_key, leaf_a_cert = _make_signed(
        d, "leafA", "leaf-a.example.test", int_a_key, int_a_cert, _LEAF_EXT
    )

    int_b_key, int_b_cert = _make_signed(
        d, "intB", "Test Intermediate B", root_b_key, root_b_cert, _CA_EXT
    )
    leaf_b_key, leaf_b_cert = _make_signed(
        d, "leafB", "leaf-b.example.test", int_b_key, int_b_cert, _LEAF_EXT
    )

    roots_dir = d / "roots"
    roots_dir.mkdir()
    (roots_dir / "rootA.pem").write_text(root_a_cert.read_text())

    good_chain = d / "good-chain.pem"
    good_chain.write_text(leaf_a_cert.read_text() + int_a_cert.read_text())

    foreign_chain = d / "foreign-chain.pem"
    foreign_chain.write_text(leaf_b_cert.read_text() + int_b_cert.read_text())

    empty_chain = d / "empty-chain.pem"
    empty_chain.write_text("")

    empty_roots_dir = d / "empty-roots"
    empty_roots_dir.mkdir()

    expired_chain = None
    try:
        _, expired_leaf_cert = _make_signed(
            d, "leafExpired", "leaf-expired.example.test", int_a_key, int_a_cert,
            _LEAF_EXT, not_before="20200101000000Z", not_after="20200102000000Z",
        )
    except AssertionError:
        expired_leaf_cert = None
    if expired_leaf_cert is not None:
        expired_chain = d / "expired-chain.pem"
        expired_chain.write_text(expired_leaf_cert.read_text() + int_a_cert.read_text())

    return SimpleNamespace(
        roots_dir=roots_dir,
        empty_roots_dir=empty_roots_dir,
        good_chain=good_chain,
        foreign_chain=foreign_chain,
        empty_chain=empty_chain,
        expired_chain=expired_chain,
    )


def _run_verify(chain_path, roots_dir):
    return subprocess.run(
        [sys.executable, str(_SCRIPT), "verify", "--chain", str(chain_path), "--roots", str(roots_dir)],
        capture_output=True, text=True, timeout=30,
    )


def test_good_chain_under_a_compiled_root_verifies(certs):
    result = _run_verify(certs.good_chain, certs.roots_dir)
    assert result.returncode == 0, result.stderr


def test_chain_under_a_foreign_root_fails_with_named_reason(certs):
    result = _run_verify(certs.foreign_chain, certs.roots_dir)
    assert result.returncode == 1
    assert "no path to a trusted root" in result.stderr
    # Names the top issuer (the foreign root itself, since the top block's
    # issuer is the certificate that signed it) and which roots were
    # tried, but never a certificate body.
    assert "Test Root B" in result.stderr
    assert "rootA.pem" in result.stderr
    assert "BEGIN CERTIFICATE" not in result.stdout
    assert "BEGIN CERTIFICATE" not in result.stderr


def test_expired_leaf_fails(certs):
    if certs.expired_chain is None:
        pytest.skip("local openssl could not backdate a certificate with -not_after")
    result = _run_verify(certs.expired_chain, certs.roots_dir)
    assert result.returncode == 1
    assert "BEGIN CERTIFICATE" not in result.stderr


def test_chain_file_with_no_certificate_fails(certs):
    result = _run_verify(certs.empty_chain, certs.roots_dir)
    assert result.returncode == 1
    assert "no certificate" in result.stderr


def test_roots_dir_with_no_pem_file_fails(certs):
    result = _run_verify(certs.good_chain, certs.empty_roots_dir)
    assert result.returncode == 1
    assert "no .pem file" in result.stderr


def test_fetch_rejects_a_malformed_host_name_before_touching_the_network(tmp_path):
    # The regex check runs before any subprocess reaches openssl s_client,
    # so this never attempts a connection -- safe under the pytest-socket
    # non-loopback guard.
    result = subprocess.run(
        [sys.executable, str(_SCRIPT), "fetch", "--host", "not a host!", "--out", str(tmp_path / "out.pem")],
        capture_output=True, text=True, timeout=10,
    )
    assert result.returncode == 1
    assert "invalid host name" in result.stderr


def test_verify_against_the_real_firmware_roots_directory_rejects_an_empty_chain():
    # /dev/null as --chain mirrors the plan's own acceptance check: an
    # empty chain against the real compiled roots exits 1.
    real_roots = _REPO_ROOT / "firmware" / "main" / "certs"
    result = _run_verify(Path("/dev/null"), real_roots)
    assert result.returncode == 1
