"""scripts/check_cert_chain.py -- proves the TLS certificate chain a host
serves still leads to one of the trusted roots compiled into the firmware
(firmware/main/certs). Stdlib + the openssl CLI via subprocess, argument
lists only, with no shell interpretation of any input.

Subcommands:
  fetch   fetch the chain a host serves at its own TLS handshake, as
          concatenated PEM blocks, and write it to a file (network)
  verify  offline: does a chain file lead to one of a roots directory's
          trust anchors (no network)
  check   fetch then verify, in one step (network)
"""
import argparse
import glob
import os
import re
import subprocess
import sys
import tempfile

# RFC 1123 hostname shape: letters, digits, dots and dashes only. Rejects
# anything a shell or URL could misinterpret before it ever reaches the
# subprocess call below, which passes an argument list, not a shell string.
_HOST_RE = re.compile(r"^[A-Za-z0-9.-]{1,253}$")

_PEM_BLOCK_RE = re.compile(
    r"-----BEGIN CERTIFICATE-----.*?-----END CERTIFICATE-----\r?\n?",
    re.DOTALL,
)

_OPENSSL_TIMEOUT_S = 20


def split_pem_blocks(text):
    """Return every PEM certificate block found in text, top to bottom."""
    return _PEM_BLOCK_RE.findall(text)


def fetch_chain_to_file(host, out_path, timeout_s=_OPENSSL_TIMEOUT_S):
    """Fetch the certificate chain `host` serves on 443 and write every PEM
    block it contains to out_path. Raises ValueError for a malformed host
    name, RuntimeError if the connection fails or no certificate is
    returned.
    """
    if not _HOST_RE.match(host):
        raise ValueError("invalid host name: %r" % host)
    try:
        result = subprocess.run(
            [
                "openssl", "s_client",
                "-connect", "%s:443" % host,
                "-servername", host,
                "-showcerts",
            ],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=timeout_s,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("timed out connecting to %s:443" % host) from exc
    blocks = split_pem_blocks(result.stdout)
    if not blocks:
        raise RuntimeError("no certificate returned by %s:443" % host)
    with open(out_path, "w", encoding="ascii") as fh:
        fh.write("".join(blocks))


def _roots_bundle_paths(roots_dir):
    return sorted(glob.glob(os.path.join(roots_dir, "*.pem")))


def _cert_field(pem_block, field):
    """One field ("-subject" or "-issuer") of a single PEM block, via
    `openssl x509 -noout`. Never returns certificate body bytes -- only the
    one-line field text openssl itself prints.
    """
    result = subprocess.run(
        ["openssl", "x509", "-noout", field],
        input=pem_block,
        capture_output=True,
        text=True,
        timeout=10,
    )
    text = result.stdout.strip()
    return text if text else "<unreadable certificate>"


def verify_chain(chain_text, roots_dir):
    """Offline decision: does chain_text (one or more concatenated PEM
    certificate blocks, leaf first) lead to one of the trust anchors in
    roots_dir? Returns (exit_code, message). The message never contains a
    certificate body -- only field text openssl itself prints (subject,
    issuer) and file names.
    """
    blocks = split_pem_blocks(chain_text)
    if not blocks:
        return 1, "check_cert_chain.py: verify: chain file has no certificate"

    root_paths = _roots_bundle_paths(roots_dir)
    if not root_paths:
        return 1, "check_cert_chain.py: verify: no .pem file in roots dir %s" % roots_dir

    leaf = blocks[0]
    rest = blocks[1:]

    with tempfile.TemporaryDirectory() as tmp:
        leaf_path = os.path.join(tmp, "leaf.pem")
        untrusted_path = os.path.join(tmp, "untrusted.pem")
        bundle_path = os.path.join(tmp, "roots-bundle.pem")

        with open(leaf_path, "w", encoding="ascii") as fh:
            fh.write(leaf)
        with open(untrusted_path, "w", encoding="ascii") as fh:
            fh.write("".join(rest))
        with open(bundle_path, "w", encoding="ascii") as fh:
            for root_path in root_paths:
                with open(root_path, encoding="ascii") as rf:
                    fh.write(rf.read())

        # -x509_strict for stricter path validation. The path must run all
        # the way to one of the compiled roots in the CA file -- openssl's
        # own flag that would accept stopping partway there is deliberately
        # never passed.
        cmd = ["openssl", "verify", "-x509_strict", "-CAfile", bundle_path]
        if rest:
            cmd += ["-untrusted", untrusted_path]
        cmd.append(leaf_path)

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=_OPENSSL_TIMEOUT_S)
        if result.returncode == 0:
            return 0, "ok"

        reason = (result.stderr + result.stdout).lower()
        top_issuer = _cert_field(blocks[-1], "-issuer")
        root_names = ", ".join(os.path.basename(p) for p in root_paths)

        if "has expired" in reason or "expired" in reason:
            return 1, (
                "check_cert_chain.py: verify: leaf certificate has expired "
                "(top issuer: %s)" % top_issuer
            )
        return 1, (
            "check_cert_chain.py: verify: no path to a trusted root "
            "(top issuer: %s; roots tried: %s)" % (top_issuer, root_names)
        )


def cmd_fetch(args):
    try:
        fetch_chain_to_file(args.host, args.out)
    except (ValueError, RuntimeError) as exc:
        print("check_cert_chain.py: fetch: %s" % exc, file=sys.stderr)
        return 1
    return 0


def cmd_verify(args):
    try:
        with open(args.chain, encoding="ascii", errors="replace") as fh:
            chain_text = fh.read()
    except OSError as exc:
        print("check_cert_chain.py: verify: cannot read chain file: %s" % exc, file=sys.stderr)
        return 1
    code, message = verify_chain(chain_text, args.roots)
    if code != 0:
        print(message, file=sys.stderr)
    return code


def cmd_check(args):
    with tempfile.TemporaryDirectory() as tmp:
        chain_path = os.path.join(tmp, "chain.pem")
        try:
            fetch_chain_to_file(args.host, chain_path)
        except (ValueError, RuntimeError) as exc:
            print("check_cert_chain.py: check: %s" % exc, file=sys.stderr)
            return 1
        with open(chain_path, encoding="ascii") as fh:
            chain_text = fh.read()
    code, message = verify_chain(chain_text, args.roots)
    if code != 0:
        print(message, file=sys.stderr)
    return code


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    parser = argparse.ArgumentParser(prog="check_cert_chain.py")
    sub = parser.add_subparsers(dest="command", required=True)

    p_fetch = sub.add_parser("fetch", help="fetch the chain a host serves over TLS (network)")
    p_fetch.add_argument("--host", required=True)
    p_fetch.add_argument("--out", required=True)

    p_verify = sub.add_parser("verify", help="offline: does a chain lead to a trusted root")
    p_verify.add_argument("--chain", required=True)
    p_verify.add_argument("--roots", required=True)

    p_check = sub.add_parser("check", help="fetch then verify, in one step (network)")
    p_check.add_argument("--host", required=True)
    p_check.add_argument("--roots", required=True)

    args = parser.parse_args(argv)

    if args.command == "fetch":
        return cmd_fetch(args)
    if args.command == "verify":
        return cmd_verify(args)
    if args.command == "check":
        return cmd_check(args)
    return 1


if __name__ == "__main__":
    sys.exit(main())
