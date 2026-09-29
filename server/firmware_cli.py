#!/usr/bin/env python3
"""Deploy-time operator CLI for server/firmware_registry.py.

Run as `python3 -m server.firmware_cli` from a directory that has
`server/` importable (the release directory a deploy stages, exactly
like every other `-m server.*` invocation in this project). Publishes
release images into the registry so byos, the poll loop and the
companion's Update page can serve/track them -- this CLI never
schedules or offers anything itself, it only calls
server.firmware_registry.publish_release().

Subcommands:
  import-dir <dir>                   every <dir>/<tag>/{skypane-<tag>.bin,
                                      release.json} subdirectory, tag-
                                      named, published as a real release.
  import-bench --file F --version V  one locally built bench image,
                                      published with bench=True and a
                                      generated note -- used only in the
                                      hardware session, never by a
                                      deploy. V must carry a bench
                                      suffix (e.g. "-bench1"); a bare
                                      release tag is refused. --commit
                                      is required when run from a
                                      checkout with no .git (a release
                                      directory such as
                                      /opt/skypane/current), optional
                                      from an ordinary git checkout.
  list                                one line per published release.

--state-dir defaults to server.state_store.DEFAULT_STATE_DIR, the same
constant every other server entry point uses.

Exit codes: 0 on full success (import-dir: every subdirectory added or
already existed); 1 on any per-item failure; 2 on a usage error. Never
deletes a release entry or an image file -- publish_release() itself
guarantees that.
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone

from server import firmware_registry
from server.state_store import DEFAULT_STATE_DIR

# release.json is a small, trusted-at-publish-time document -- capped so
# a malformed or hostile file is never read past this size before being
# rejected.
_MAX_MANIFEST_BYTES = 65536

_COMMIT_SHA_RE = re.compile(r"\A[0-9a-f]{40}\Z")
_GIT_TIMEOUT_S = 30


def _repo_root():
    # server/firmware_cli.py -> server/ -> repo root.
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _hash_and_size(path):
    """SHA-256 hex digest and byte size, read in 64 KiB chunks so this
    never depends on how large the image happens to be.
    """
    digest = hashlib.sha256()
    size = 0
    with open(path, "rb") as fh:
        while True:
            chunk = fh.read(65536)
            if not chunk:
                break
            digest.update(chunk)
            size += len(chunk)
    return digest.hexdigest(), size


def _load_manifest(path):
    """(manifest_dict, None) on success, or (None, error_message).
    Never raises -- the caller reports the message and moves on to the
    next subdirectory rather than aborting the whole run.
    """
    try:
        size = os.path.getsize(path)
    except OSError as exc:
        return None, "release.json missing or unreadable (%s)" % exc
    if size > _MAX_MANIFEST_BYTES:
        return None, "release.json is %d bytes, over the %d byte cap" % (size, _MAX_MANIFEST_BYTES)
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError) as exc:
        return None, "release.json is not valid JSON (%s)" % exc
    if not isinstance(data, dict):
        return None, "release.json must be a JSON object"
    return data, None


def _reject_symlink_image(image_path):
    """None if image_path is a plain regular file -- else an error
    message. A symlink could point anywhere outside the staged release,
    so it is refused the same way a missing file is, never followed.
    """
    if os.path.islink(image_path):
        return "%s is a symlink, refusing to publish from it" % image_path
    if not os.path.isfile(image_path):
        return "%s is not a regular file" % image_path
    return None


def cmd_import_dir(args):
    base = args.dir
    if not os.path.isdir(base):
        print("firmware_cli: not a directory: %s" % base, file=sys.stderr)
        return 1

    # This command re-imports every subdirectory on every deploy, whether
    # or not that deploy touched firmware at all. A tag never registered
    # here before is new to *this* deploy, so its own failure is this
    # run's problem and must block the swap (the strict behaviour below).
    # A tag already registered is old news: a release.json that no longer
    # parses, an image that no longer matches its recorded sha256 (most
    # often a GitHub Release deleted and re-signed -- RSA-PSS signatures
    # are randomized, so re-signing always changes the hash), or a
    # manifest whose version no longer matches its directory, is reported
    # loudly but never fails the whole command: nothing about an
    # unrelated, already-published release should be able to block every
    # future code deploy until someone performs registry surgery.
    already_registered = {
        release.get("version") for release in firmware_registry.load_registry(args.state_dir).get("releases", [])
    }

    ok = True
    for name in sorted(os.listdir(base)):
        subdir = os.path.join(base, name)
        if not os.path.isdir(subdir):
            continue
        is_new = name not in already_registered

        error = None
        outcome = None
        if not firmware_registry.RELEASE_TAG_RE.match(name):
            error = "not a release tag"
        else:
            image_path = os.path.join(subdir, "skypane-%s.bin" % name)
            error = _reject_symlink_image(image_path)
            manifest = None
            if error is None:
                manifest, error = _load_manifest(os.path.join(subdir, "release.json"))
            # The subdirectory name picked the image file above
            # (skypane-<name>.bin), but publish_release() only ever
            # registers manifest["version"] -- a release.json whose own
            # version disagrees with its directory would publish that
            # directory's image under a *different* label, and every
            # version-keyed check downstream (compute_offer's same-
            # version and floor checks) would then run against the
            # wrong one.
            if error is None and manifest.get("version") != name:
                error = "release.json version %r does not match directory" % (manifest.get("version"),)
            if error is None:
                try:
                    outcome = firmware_registry.publish_release(args.state_dir, manifest, image_path, bench=False)
                except ValueError as exc:
                    error = str(exc)

        if error is not None:
            print("firmware_cli: %s: %s" % (name, error), file=sys.stderr)
            if is_new:
                ok = False
            else:
                print(
                    "firmware_cli: %s: already registered -- not blocking this deploy over it" % name,
                    file=sys.stderr)
            continue

        print("%s %s" % (outcome, name))

    return 0 if ok else 1


def _current_commit():
    """The repo's own HEAD commit, 40 lowercase hex characters, or None
    if this is not a git checkout or git is unavailable -- a bench
    image published without one is a visible failure, never a
    fabricated commit hash.
    """
    try:
        result = subprocess.run(
            ["git", "-C", _repo_root(), "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=_GIT_TIMEOUT_S,
        )
    except OSError:
        return None
    if result.returncode != 0:
        return None
    commit = result.stdout.strip()
    return commit if _COMMIT_SHA_RE.match(commit) else None


def cmd_import_bench(args):
    image_error = _reject_symlink_image(args.file)
    if image_error is not None:
        print("firmware_cli: %s" % image_error, file=sys.stderr)
        return 1

    # --commit is required outside a git checkout: /opt/skypane/current
    # (the only place a real deployed frame's poll loop and byos ever
    # read from) is `git archive` output with no .git, so
    # _current_commit() always fails there. Explicit --commit is the
    # only way to run this command against that layout; a bare git
    # checkout can still omit it.
    # A bare release-tag version (no bench suffix) would let a locally
    # built bench image squat a future release's version -- the real CI
    # release would then fail to import with a sha conflict. Bench
    # versions must additionally NOT match the stricter release-tag
    # pattern.
    if firmware_registry.RELEASE_TAG_RE.match(args.version):
        print(
            "firmware_cli: %r looks like a release tag, not a bench version -- "
            "bench versions must carry a suffix (e.g. fw-v1.3.0-bench1)" % (args.version,),
            file=sys.stderr)
        return 1

    commit = args.commit if args.commit is not None else _current_commit()
    if commit is None:
        print(
            "firmware_cli: could not resolve a git commit for this bench image "
            "-- pass --commit explicitly (this command's own checkout is not "
            "a git repository, e.g. /opt/skypane/current)", file=sys.stderr)
        return 1

    sha256, size = _hash_and_size(args.file)
    manifest = {
        "version": args.version,
        "sha256": sha256,
        "size": size,
        "released_at": datetime.now(timezone.utc).isoformat(),
        "commit": commit,
        "notes": ["Bench image (not a release)"],
    }
    try:
        outcome = firmware_registry.publish_release(args.state_dir, manifest, args.file, bench=True)
    except ValueError as exc:
        print("firmware_cli: %s" % exc, file=sys.stderr)
        return 1
    print("%s %s" % (outcome, args.version))
    return 0


def cmd_list(args):
    registry = firmware_registry.load_registry(args.state_dir)
    releases = sorted(registry.get("releases", []), key=lambda r: r.get("published_at") or "")
    if not releases:
        print("(no releases published)")
        return 0
    for release in releases:
        print("%s %s %d %d" % (
            release.get("version"),
            release.get("published_at"),
            release.get("size", 0),
            len(release.get("installed_at", [])),
        ))
    return 0


def build_parser():
    ap = argparse.ArgumentParser(
        prog="firmware_cli", description="Publish firmware releases into server.firmware_registry.")
    ap.add_argument("--state-dir", default=DEFAULT_STATE_DIR,
                     help="registry state directory (default: %s)" % DEFAULT_STATE_DIR)
    sub = ap.add_subparsers(dest="command", required=True)

    import_dir = sub.add_parser(
        "import-dir", help="publish every <dir>/<tag>/{skypane-<tag>.bin,release.json} subdirectory")
    import_dir.add_argument("dir")
    import_dir.set_defaults(func=cmd_import_dir)

    import_bench = sub.add_parser(
        "import-bench", help="publish one locally built bench image (hardware session only)")
    import_bench.add_argument("--file", required=True)
    import_bench.add_argument("--version", required=True)
    import_bench.add_argument(
        "--commit", default=None,
        help="40-hex-char commit the bench image was built from; required outside a git checkout")
    import_bench.set_defaults(func=cmd_import_bench)

    listp = sub.add_parser("list", help="list published releases")
    listp.set_defaults(func=cmd_list)

    return ap


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
