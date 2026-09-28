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
                                      deploy.
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

    ok = True
    for name in sorted(os.listdir(base)):
        subdir = os.path.join(base, name)
        if not os.path.isdir(subdir):
            continue
        if not firmware_registry.RELEASE_TAG_RE.match(name):
            print("firmware_cli: %s: not a release tag" % name, file=sys.stderr)
            ok = False
            continue

        image_path = os.path.join(subdir, "skypane-%s.bin" % name)
        image_error = _reject_symlink_image(image_path)
        if image_error is not None:
            print("firmware_cli: %s: %s" % (name, image_error), file=sys.stderr)
            ok = False
            continue

        manifest, manifest_error = _load_manifest(os.path.join(subdir, "release.json"))
        if manifest_error is not None:
            print("firmware_cli: %s: %s" % (name, manifest_error), file=sys.stderr)
            ok = False
            continue

        # The subdirectory name picked the image file above
        # (skypane-<name>.bin), but publish_release() only ever
        # registers manifest["version"] -- a release.json whose own
        # version disagrees with its directory would publish that
        # directory's image under a *different* label, and every
        # version-keyed check downstream (compute_offer's same-version
        # and floor checks) would then run against the wrong one.
        if manifest.get("version") != name:
            print(
                "firmware_cli: %s: release.json version %r does not match directory"
                % (name, manifest.get("version")), file=sys.stderr)
            ok = False
            continue

        try:
            outcome = firmware_registry.publish_release(args.state_dir, manifest, image_path, bench=False)
        except ValueError as exc:
            print("firmware_cli: %s: %s" % (name, exc), file=sys.stderr)
            ok = False
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

    commit = _current_commit()
    if commit is None:
        print("firmware_cli: could not resolve a git commit for this bench image", file=sys.stderr)
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
