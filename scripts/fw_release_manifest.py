"""scripts/fw_release_manifest.py -- generates the release manifest
`server.firmware_registry.publish_release` expects (version, sha256,
size, released_at, commit, notes), plus an optional Markdown release
body for the GitHub Release text. Every field comes from git and the
image file itself: there is no hand-written text anywhere in the
output. Stdlib only, argument lists to subprocess only -- never a raw
shell string.
"""
import argparse
import hashlib
import json
import re
import subprocess
import sys

# A CI-tagged release, e.g. "fw-v1.3.0" -- the same shape
# server.firmware_registry.RELEASE_TAG_RE requires.
RELEASE_TAG_RE = re.compile(
    r"\Afw-v(0|[1-9][0-9]{0,3})\.(0|[1-9][0-9]{0,3})\.(0|[1-9][0-9]{0,3})\Z"
)

# One OTA slot (firmware/partitions.csv): ota_0/ota_1 are each 0x250000
# -- the same bound server.firmware_registry.MAX_IMAGE_BYTES enforces.
MAX_IMAGE_BYTES = 0x250000

# Matches server.firmware_registry's own release-note limits: at most
# 60 notes, each truncated to 200 characters.
MAX_NOTES = 60
NOTE_MAX_LEN = 200

_GIT_TIMEOUT_S = 30


def _version_tuple(tag):
    """(major, minor, patch) for a valid release tag, else None."""
    match = RELEASE_TAG_RE.match(tag)
    if not match:
        return None
    return tuple(int(group) for group in match.groups())


def _git(repo, args):
    """Run `git -C repo <args>` and return stdout. Raises RuntimeError
    (never a bare CalledProcessError) so callers can report one clean
    message instead of a traceback.
    """
    result = subprocess.run(
        ["git", "-C", repo] + args,
        capture_output=True, text=True, timeout=_GIT_TIMEOUT_S,
    )
    if result.returncode != 0:
        raise RuntimeError("git %s failed: %s" % (args, result.stderr.strip()))
    return result.stdout


def previous_tag(repo, tag):
    """The highest fw-v* tag, by version order, among the tags
    reachable from `tag` and strictly below it -- never the most
    recently *created* tag, since a bench or backport tag can exist out
    of version order. None if `tag` is the first release.
    """
    target = _version_tuple(tag)
    if target is None:
        raise ValueError("tag: %r does not match fw-vX.Y.Z" % tag)
    raw = _git(repo, ["tag", "--list", "fw-v*", "--merged", tag])
    best_tag = None
    best_version = None
    for candidate in raw.splitlines():
        candidate = candidate.strip()
        if not candidate or candidate == tag:
            continue
        version = _version_tuple(candidate)
        if version is None or version >= target:
            continue
        if best_version is None or version > best_version:
            best_version = version
            best_tag = candidate
    return best_tag


def commit_notes(repo, prev_tag, tag):
    """Newest-first `firmware/` commit subjects strictly after
    `prev_tag` up to and including `tag` (all of them, for the first
    release), no merges, each truncated to NOTE_MAX_LEN characters.
    Capped at MAX_NOTES entries; when more exist, the last kept entry
    is replaced by "and N earlier commits" naming the true remaining
    count.
    """
    range_arg = "%s..%s" % (prev_tag, tag) if prev_tag else tag
    raw = _git(repo, ["log", "--no-merges", "--format=%s", range_arg, "--", "firmware/"])
    subjects = [line[:NOTE_MAX_LEN] for line in raw.splitlines() if line.strip()]
    if len(subjects) <= MAX_NOTES:
        return subjects
    kept = subjects[: MAX_NOTES - 1]
    remaining = len(subjects) - len(kept)
    kept.append("and %d earlier commits" % remaining)
    return kept


def _commit_and_date(repo, tag):
    commit = _git(repo, ["rev-list", "-n", "1", tag]).strip()
    released_at = _git(repo, ["show", "-s", "--format=%cI", commit]).strip()
    return commit, released_at


def _hash_and_size(image_path):
    """SHA-256 hex digest and byte size of the image file, read in
    64 KiB chunks so this never depends on how large the image is.
    """
    digest = hashlib.sha256()
    size = 0
    with open(image_path, "rb") as fh:
        while True:
            chunk = fh.read(65536)
            if not chunk:
                break
            digest.update(chunk)
            size += len(chunk)
    return digest.hexdigest(), size


def build_manifest(repo, tag, image_path):
    """The release manifest dict for `tag`'s image at `image_path`.
    Raises ValueError for a malformed tag or an oversized image, and
    RuntimeError for a git failure (for example an unknown tag) -- both
    are caller errors the release job must fail on before anything is
    published, never silently coerced.
    """
    if _version_tuple(tag) is None:
        raise ValueError("tag: %r does not match fw-vX.Y.Z" % tag)

    sha256, size = _hash_and_size(image_path)
    if size > MAX_IMAGE_BYTES:
        raise ValueError(
            "image: %r is %d bytes, over the %d byte OTA slot" % (image_path, size, MAX_IMAGE_BYTES)
        )

    prev_tag = previous_tag(repo, tag)
    notes = commit_notes(repo, prev_tag, tag)
    commit, released_at = _commit_and_date(repo, tag)

    return {
        "version": tag,
        "sha256": sha256,
        "size": size,
        "released_at": released_at,
        "commit": commit,
        "notes": notes,
    }


def render_notes_md(tag, notes):
    """A Markdown release body: a heading naming the tag, then a bullet
    per note -- the exact text `gh release create --notes-file` posts.
    """
    lines = ["## %s" % tag, ""]
    if notes:
        lines += ["- %s" % note for note in notes]
    else:
        lines.append("- No firmware/ changes recorded for this release.")
    return "\n".join(lines) + "\n"


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    parser = argparse.ArgumentParser(prog="fw_release_manifest.py")
    parser.add_argument("--tag", required=True, help="release tag, e.g. fw-v1.3.0")
    parser.add_argument("--image", required=True, help="path to the signed image")
    parser.add_argument("--out", required=True, help="path to write the manifest JSON")
    parser.add_argument("--repo", default=".", help="git repository root (default: cwd)")
    parser.add_argument("--notes-md", help="also write a Markdown release body here")
    args = parser.parse_args(argv)

    try:
        manifest = build_manifest(args.repo, args.tag, args.image)
    except (ValueError, RuntimeError, OSError) as exc:
        print("fw_release_manifest.py: %s" % exc, file=sys.stderr)
        return 2

    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(manifest, indent=1, sort_keys=True))
        fh.write("\n")

    if args.notes_md:
        with open(args.notes_md, "w", encoding="utf-8") as fh:
            fh.write(render_notes_md(args.tag, manifest["notes"]))

    return 0


if __name__ == "__main__":
    sys.exit(main())
