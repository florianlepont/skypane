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
                                      named, published as a real release,
                                      in ascending build order.
  import-bench --file F --version V  one locally built bench image,
                                      published with bench=True and a
                                      generated note -- used only in the
                                      hardware session, never by a
                                      deploy. V must carry a bench
                                      suffix (e.g. "-bench1"); a bare
                                      release tag is refused.
                                      --allow-foreign-key skips the
                                      signing-key comparison (bench
                                      only). --commit
                                      is required when run from a
                                      checkout with no .git (a release
                                      directory such as
                                      /opt/skypane/current), optional
                                      from an ordinary git checkout.
  list [--hardware-type T]           one line per published release; with
                                      more than one type holding releases,
                                      a [type] heading per type.
  check-image [--hardware-type T] F  validate image file F against type T
                                      (the parser publishing uses); writes
                                      nothing.

Per-type import-dir: beside the legacy pair a tag directory may hold
release-<key>.json and skypane-<key>-<tag>.bin for any other hardware
type; an older importer ignores those files. import-bench takes
--hardware-type (default: the legacy type).

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

from server import firmware_image, firmware_registry, hardware
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


def _load_manifest(path, label="release.json"):
    """(manifest_dict, None) on success, or (None, error_message).
    Never raises -- the caller reports the message and moves on to the
    next subdirectory rather than aborting the whole run.
    """
    try:
        size = os.path.getsize(path)
    except OSError as exc:
        return None, "%s missing or unreadable (%s)" % (label, exc)
    if size > _MAX_MANIFEST_BYTES:
        return None, "%s is %d bytes, over the %d byte cap" % (label, size, _MAX_MANIFEST_BYTES)
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError) as exc:
        return None, "%s is not valid JSON (%s)" % (label, exc)
    if not isinstance(data, dict):
        return None, "%s must be a JSON object" % label
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


# release-<key>.json plus skypane-<key>-<tag>.bin: the per-type pair
# that sits beside the legacy release.json / skypane-<tag>.bin pair. The
# key group is deliberately loose here and validated before any path is
# built from it.
_TYPED_MANIFEST_RE = re.compile(r"\Arelease-(.+)\.json\Z")
_TYPE_KEY_RE = re.compile(r"\A[a-z0-9-]{1,64}\Z")


def _import_order(names):
    """Release tags in ascending build order, then every name that is not
    a release tag (rejected later) in plain name order. Publishing is
    gated on a monotonic build, so a lexicographic walk (fw-v1.10.0
    before fw-v1.9.0) would refuse a legitimate release.
    """
    def key(name):
        if firmware_registry.RELEASE_TAG_RE.match(name):
            return (0, firmware_registry.build_number(name), name)
        return (1, 0, name)

    return sorted(names, key=key)


def _publish_item(args, name, manifest, image_path, key):
    """Publish one item; (outcome, None) or (None, error message)."""
    if manifest.get("version") != name:
        return None, "release.json version %r does not match directory" % (manifest.get("version"),)
    try:
        outcome = firmware_registry.publish_release(
            args.state_dir, manifest, image_path, bench=False, hardware_type=key)
    except (ValueError, firmware_registry.RegistryCorruptError) as exc:
        return None, str(exc)
    return outcome, None


def _import_legacy_pair(args, name, subdir):
    """Publish <subdir>/{skypane-<name>.bin,release.json} for the legacy
    type; (outcome, error).
    """
    if not firmware_registry.RELEASE_TAG_RE.match(name):
        return None, "not a release tag"
    image_path = os.path.join(subdir, "skypane-%s.bin" % name)
    error = _reject_symlink_image(image_path)
    if error is not None:
        return None, error
    manifest, error = _load_manifest(os.path.join(subdir, "release.json"))
    if error is not None:
        return None, error
    # The directory name picked the image file, but publish_release()
    # registers manifest["version"]; a disagreeing release.json would
    # publish this directory's image under a different label.
    return _publish_item(args, name, manifest, image_path, hardware.LEGACY_KEY)


def _typed_keys(subdir):
    """Type keys (as written in the file names) of the release-<key>.json
    files in a tag directory, sorted.
    """
    keys = []
    for entry in os.listdir(subdir):
        match = _TYPED_MANIFEST_RE.match(entry)
        if match:
            keys.append(match.group(1))
    return sorted(keys)


def _typed_key_error(key):
    if not _TYPE_KEY_RE.match(key):
        return "invalid hardware type key %r" % (key,)
    if not hardware.is_known(key) or key not in hardware.available_types():
        return "unknown hardware type %r" % (key,)
    if key == hardware.LEGACY_KEY:
        return "hardware type %r is published through release.json" % (key,)
    return None


def _import_typed_pair(args, name, subdir, key):
    """Publish <subdir>/{skypane-<key>-<name>.bin,release-<key>.json};
    (outcome, error). The key is validated before it joins a path.
    """
    error = _typed_key_error(key)
    if error is not None:
        return None, error
    image_path = os.path.join(subdir, "skypane-%s-%s.bin" % (key, name))
    manifest_path = os.path.join(subdir, "release-%s.json" % key)
    error = _reject_symlink_image(image_path)
    if error is None and os.path.islink(manifest_path):
        error = "%s is a symlink, refusing to publish from it" % manifest_path
    if error is not None:
        return None, error
    manifest, error = _load_manifest(manifest_path, "release-%s.json" % key)
    if error is not None:
        return None, error
    if manifest.get("hardware_type") != key:
        return None, "release-%s.json declares hardware_type %r, expected %r" % (
            key, manifest.get("hardware_type"), key)
    return _publish_item(args, name, manifest, image_path, key)


def _registered_versions(state_dir, key, cache):
    if key not in cache:
        releases = firmware_registry.load_registry(state_dir, key).get("releases", [])
        cache[key] = {release.get("version") for release in releases}
    return cache[key]


def _report_item(label, outcome, error, is_new):
    """Print one item's result; True if it must fail the command."""
    if error is None:
        print("%s %s" % (outcome, label))
        return False
    print("firmware_cli: %s: %s" % (label, error), file=sys.stderr)
    if is_new:
        return True
    print("firmware_cli: %s: already registered -- not blocking this deploy over it" % label,
          file=sys.stderr)
    return False


def _import_tag_dir(args, name, subdir, cache):
    """Import everything one tag directory holds; True if all items are
    fine (or are old news).
    """
    ok = True
    typed = _typed_keys(subdir)
    has_legacy_files = any(
        os.path.lexists(os.path.join(subdir, f)) for f in ("release.json", "skypane-%s.bin" % name))
    if has_legacy_files or not typed:
        is_new = name not in _registered_versions(args.state_dir, hardware.LEGACY_KEY, cache)
        outcome, error = _import_legacy_pair(args, name, subdir)
        ok = not _report_item(name, outcome, error, is_new)
    for key in typed:
        # A key that cannot name a registry has no registered tags.
        known = _typed_key_error(key) is None
        is_new = not known or name not in _registered_versions(args.state_dir, key, cache)
        outcome, error = _import_typed_pair(args, name, subdir, key)
        label = "%s %s" % (name, key) if error is None else "%s [%s]" % (name, key)
        if _report_item(label, outcome, error, is_new):
            ok = False
    return ok


def cmd_import_dir(args):
    base = args.dir
    if not os.path.isdir(base):
        print("firmware_cli: not a directory: %s" % base, file=sys.stderr)
        return 1

    # This command re-imports every subdirectory on every deploy, whether
    # or not that deploy touched firmware at all. A tag never registered
    # here before is new to *this* deploy, so its own failure is this
    # run's problem and must block the swap. A tag already registered is
    # old news: a release.json that no longer parses, an image that no
    # longer matches its recorded sha256 (most often a GitHub Release
    # deleted and re-signed -- RSA-PSS signatures are randomized, so
    # re-signing always changes the hash), or a manifest whose version no
    # longer matches its directory, is reported loudly but never fails
    # the whole command: nothing about an unrelated, already-published
    # release should be able to block every future code deploy until
    # someone performs registry surgery.
    cache = {}
    ok = True
    for name in _import_order(os.listdir(base)):
        subdir = os.path.join(base, name)
        if not os.path.isdir(subdir):
            continue
        if not _import_tag_dir(args, name, subdir, cache):
            ok = False
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


def _resolve_type(args):
    """The --hardware-type key if it names a type usable here, else None
    after reporting it.
    """
    key = args.hardware_type
    if key in hardware.available_types():
        return key
    print("firmware_cli: unknown hardware type %r (available: %s)" % (
        key, ", ".join(hardware.available_types())), file=sys.stderr)
    return None


def cmd_import_bench(args):
    key = _resolve_type(args)
    if key is None:
        return 2
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
        "hardware_type": key,
    }
    try:
        outcome = firmware_registry.publish_release(
            args.state_dir, manifest, args.file, bench=True, hardware_type=key,
            allow_foreign_key=args.allow_foreign_key)
    except (ValueError, firmware_registry.RegistryCorruptError) as exc:
        print("firmware_cli: %s" % exc, file=sys.stderr)
        return 1
    print("%s %s" % (outcome, args.version))
    return 0


def _release_lines(releases):
    ordered = sorted(releases, key=lambda r: r.get("published_at") or "")
    return ["%s %s %d %d" % (
        release.get("version"),
        release.get("published_at"),
        release.get("size", 0),
        len(release.get("installed_at", [])),
    ) for release in ordered]


def cmd_list(args):
    if args.hardware_type is not None:
        key = _resolve_type(args)
        if key is None:
            return 2
        lines = _release_lines(firmware_registry.load_registry(args.state_dir, key).get("releases", []))
        print("\n".join(lines) if lines else "(no releases published)")
        return 0
    by_type = {}
    for key in hardware.available_types():
        releases = firmware_registry.load_registry(args.state_dir, key).get("releases", [])
        if releases:
            by_type[key] = _release_lines(releases)
    if not by_type:
        print("(no releases published)")
    elif list(by_type) == [hardware.LEGACY_KEY]:
        print("\n".join(by_type[hardware.LEGACY_KEY]))
    else:
        for key, lines in by_type.items():
            print("[%s]" % key)
            print("\n".join(lines))
    return 0


def cmd_check_image(args):
    key = _resolve_type(args)
    if key is None:
        return 2
    image_error = _reject_symlink_image(args.file)
    if image_error is not None:
        print("firmware_cli: %s" % image_error, file=sys.stderr)
        return 1
    target = hardware.get_profile(key).firmware
    require_signature, expected_modulus = firmware_registry._signing_policy(key)
    try:
        with open(args.file, "rb") as fh:
            # One byte past the bound is enough to report an oversize file.
            data = fh.read(target.max_app_bytes + 1)
        image = firmware_image.validate_for_target(
            data, target, require_signature=require_signature, expected_modulus=expected_modulus)
    except (OSError, ValueError) as exc:
        print("firmware_cli: %s" % exc, file=sys.stderr)
        return 1
    print("ok %s %s %d bytes" % (key, image.version, image.size))
    return 0


def build_parser():
    ap = argparse.ArgumentParser(
        prog="firmware_cli", description="Publish firmware releases into server.firmware_registry.")
    ap.add_argument("--state-dir", default=DEFAULT_STATE_DIR,
                     help="registry state directory (default: %s)" % DEFAULT_STATE_DIR)
    # --state-dir is also accepted after the subcommand, so both
    # `firmware_cli --state-dir D import-dir X` and
    # `firmware_cli import-dir X --state-dir D` work. SUPPRESS keeps a
    # subcommand that omits it from overwriting the top-level value.
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--state-dir", default=argparse.SUPPRESS,
                        help="registry state directory (default: %s)" % DEFAULT_STATE_DIR)
    sub = ap.add_subparsers(dest="command", required=True)

    import_dir = sub.add_parser(
        "import-dir", parents=[common],
        help="publish every <dir>/<tag>/{skypane-<tag>.bin,release.json} subdirectory")
    import_dir.add_argument("dir")
    import_dir.set_defaults(func=cmd_import_dir)

    import_bench = sub.add_parser(
        "import-bench", parents=[common], help="publish one locally built bench image (hardware session only)")
    import_bench.add_argument("--file", required=True)
    import_bench.add_argument("--version", required=True)
    import_bench.add_argument(
        "--commit", default=None,
        help="40-hex-char commit the bench image was built from; required outside a git checkout")
    import_bench.add_argument(
        "--hardware-type", default=hardware.LEGACY_KEY,
        help="hardware type key the bench image is for (default: %s)" % hardware.LEGACY_KEY)
    import_bench.add_argument(
        "--allow-foreign-key", action="store_true",
        help="skip the signing-key comparison so a wrongly signed bench image can be "
             "offered to a unit (the image must still carry a signature sector)")
    import_bench.set_defaults(func=cmd_import_bench)

    listp = sub.add_parser("list", parents=[common], help="list published releases")
    listp.add_argument(
        "--hardware-type", default=None,
        help="list only this hardware type (default: every type holding releases)")
    listp.set_defaults(func=cmd_list)

    check = sub.add_parser(
        "check-image", parents=[common],
        help="validate an image file against a hardware type; writes nothing")
    check.add_argument("file")
    check.add_argument(
        "--hardware-type", default=hardware.LEGACY_KEY,
        help="hardware type key to validate against (default: %s)" % hardware.LEGACY_KEY)
    check.set_defaults(func=cmd_check_image)

    return ap


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
