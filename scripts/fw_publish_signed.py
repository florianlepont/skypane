#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
"""Sign and publish a firmware release on the owner's own machine.

CI builds both boards' images for a fw-v* tag and uploads them unsigned,
with a checksum list, as the run artifact ``fw-unsigned-<tag>``. This
script downloads exactly those bytes (the build is not reproducible, so a
rebuild would differ), checks where they came from, signs them with the
local private key inside the digest-pinned signing container, verifies the
signatures against the committed public key, builds the manifests and
publishes the GitHub Release with the seven fixed asset names.

The private key is only ever bind-mounted read-only into a container that
has no network. It is never read, copied or printed by this script.

--dry-run does everything up to publishing and then proves the result can
be imported by the server into a scratch state directory. Standard library
only; every subprocess call uses an argument list.
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

TAG_RE = re.compile(
    r"\Afw-v(0|[1-9][0-9]{0,3})\.(0|[1-9][0-9]{0,3})\.(0|[1-9][0-9]{0,3})\Z"
)
SIGNING_IMAGE = (
    "espressif/idf@sha256:"
    "55ab243e87584859c9af3acc124b0b9423a9d8b44fc99a5d5055d7bd7312722d"
)
LIVE_TYPE = "xiao-ee02-13in3-spectra6"
SECOND_TYPE = "seeed-ee04-7in3-spectra6"
WORKFLOW = "firmware-release.yml"
PUBKEY_REL = "firmware/signing/skypane-signing-pubkey.pem"
UNSIGNED_FILES = (
    "ee02-skypane.bin",
    "second-skypane.bin",
    "bootloader.bin",
    "partition-table.bin",
    "ota_data_initial.bin",
)
SUMS_NAME = "SHA256SUMS"


class PublishError(Exception):
    """A refusal or a failed step; the message is shown to the operator."""


def run(argv, cwd=None, env=None, check=True):
    """Run one external command (argument list only) and capture output.

    Tests replace this function; it is the only place subprocess is used.
    """
    proc = subprocess.run(
        argv, cwd=cwd, env=env, capture_output=True, text=True, check=False
    )
    if check and proc.returncode != 0:
        raise PublishError(
            "%s failed (exit %d): %s"
            % (argv[0], proc.returncode, (proc.stderr or proc.stdout).strip()[-400:])
        )
    return proc


def asset_names(tag):
    """The seven release asset names, in publication order."""
    return [
        "skypane-%s.bin" % tag,
        "release.json",
        "bootloader-%s.bin" % tag,
        "partition-table-%s.bin" % tag,
        "ota_data_initial-%s.bin" % tag,
        "skypane-%s-%s.bin" % (SECOND_TYPE, tag),
        "release-%s.json" % SECOND_TYPE,
    ]


def check_tag(tag):
    if not TAG_RE.match(tag):
        raise PublishError("tag %r does not match fw-vMAJOR.MINOR.PATCH" % tag)


def resolve_tag_commit(repo, tag):
    """Fetch tags and main, and require the tag commit to be on main."""
    run(["git", "-C", repo, "fetch", "--tags", "--force", "origin"])
    run(["git", "-C", repo, "fetch", "origin", "main"])
    commit = run(["git", "-C", repo, "rev-list", "-n", "1", tag]).stdout.strip()
    if not commit:
        raise PublishError("tag %s does not exist in %s" % (tag, repo))
    onmain = run(
        ["git", "-C", repo, "merge-base", "--is-ancestor", commit, "origin/main"],
        check=False,
    )
    if onmain.returncode != 0:
        raise PublishError("tag commit %s is not an ancestor of origin/main" % commit)
    return commit


def find_ci_run(repo, tag, commit):
    """Id of the successful firmware-release run built for this tag and commit."""
    out = run(
        [
            "gh", "run", "list", "--workflow", WORKFLOW, "--limit", "50",
            "--json", "databaseId,headSha,headBranch,conclusion",
        ],
        cwd=repo,
    ).stdout
    try:
        runs = json.loads(out)
    except ValueError as exc:
        raise PublishError("gh run list returned invalid JSON") from exc
    for item in runs:
        if (
            item.get("conclusion") == "success"
            and item.get("headSha") == commit
            and item.get("headBranch") == tag
        ):
            return str(item["databaseId"])
    raise PublishError(
        "no successful %s run for tag %s at commit %s" % (WORKFLOW, tag, commit)
    )


def sha256_of(path):
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_checksums(unsigned_dir):
    """Recompute every hash and require the exact expected file set."""
    present = {p.name for p in Path(unsigned_dir).iterdir() if p.is_file()}
    expected = set(UNSIGNED_FILES) | {SUMS_NAME}
    if present != expected:
        raise PublishError(
            "artifact file set differs: unexpected %s, missing %s"
            % (sorted(present - expected), sorted(expected - present))
        )
    listed = {}
    sums_text = (Path(unsigned_dir) / SUMS_NAME).read_text()
    for line in sums_text.splitlines():
        match = re.match(r"\A([0-9a-f]{64}) [ *]([A-Za-z0-9._-]+)\Z", line)
        if not match:
            raise PublishError("malformed line in %s" % SUMS_NAME)
        listed[match.group(2)] = match.group(1)
    if set(listed) != set(UNSIGNED_FILES):
        raise PublishError("%s does not list exactly the expected files" % SUMS_NAME)
    for name in UNSIGNED_FILES:
        if sha256_of(Path(unsigned_dir) / name) != listed[name]:
            raise PublishError("checksum mismatch for %s" % name)


def check_key_file(key_file):
    """Only metadata is inspected; the key bytes are never read."""
    path = Path(key_file)
    try:
        info = path.stat()
    except OSError as exc:
        raise PublishError("key file %s is not accessible" % key_file) from exc
    if not stat.S_ISREG(info.st_mode):
        raise PublishError("key file %s is not a regular file" % key_file)
    if info.st_mode & 0o077:
        raise PublishError("key file %s must be mode 0600 or stricter" % key_file)


def _docker_base(work_dir, platform):
    return [
        "docker", "run", "--rm", "--platform", platform, "--network", "none",
        "-v", "%s:/work" % work_dir,
    ]


def sign_images(work_dir, key_file, platform):
    """Sign both boards' images; the key is mounted read-only."""
    pairs = (
        ("ee02-skypane.bin", "ee02-signed.bin"),
        ("second-skypane.bin", "second-signed.bin"),
    )
    uid = ["-u", "%d:%d" % (os.getuid(), os.getgid())]
    for src, dst in pairs:
        run(
            _docker_base(work_dir, platform)
            + ["-v", "%s:/key.pem:ro" % key_file]
            + uid
            + [
                SIGNING_IMAGE, "espsecure.py", "sign_data", "--version", "2",
                "--keyfile", "/key.pem",
                "--output", "/work/%s" % dst, "/work/%s" % src,
            ]
        )


def verify_signatures(work_dir, pubkey, platform):
    uid = ["-u", "%d:%d" % (os.getuid(), os.getgid())]
    for signed in ("ee02-signed.bin", "second-signed.bin"):
        run(
            _docker_base(work_dir, platform)
            + ["-v", "%s:/pubkey.pem:ro" % pubkey]
            + uid
            + [
                SIGNING_IMAGE, "espsecure.py", "verify_signature",
                "--version", "2", "--keyfile", "/pubkey.pem",
                "/work/%s" % signed,
            ]
        )


def _manifest_cmd(worktree, hardware_type, tag, image, extra):
    return [
        sys.executable, os.path.join(worktree, "scripts", "fw_release_manifest.py"),
        "--hardware-type", hardware_type, "--tag", tag, "--image", image,
        "--repo", worktree,
    ] + extra


def build_manifests(worktree, tag, work_dir, stage_dir):
    """Check both signed images, then write manifests and notes into stage_dir."""
    env = dict(os.environ, PYTHONPATH=worktree)
    ee02 = os.path.join(work_dir, "ee02-signed.bin")
    second = os.path.join(work_dir, "second-signed.bin")
    for hw, image in ((LIVE_TYPE, ee02), (SECOND_TYPE, second)):
        run(_manifest_cmd(worktree, hw, tag, image, ["--check-only"]), env=env)
    run(
        _manifest_cmd(
            worktree, LIVE_TYPE, tag, ee02,
            ["--out", os.path.join(stage_dir, "release.json"),
             "--notes-md", os.path.join(stage_dir, "notes.md")],
        ),
        env=env,
    )
    run(
        _manifest_cmd(
            worktree, SECOND_TYPE, tag, second,
            ["--out", os.path.join(stage_dir, "release-%s.json" % SECOND_TYPE)],
        ),
        env=env,
    )


def stage_assets(tag, work_dir, unsigned_dir, stage_dir):
    names = asset_names(tag)
    copies = {
        names[0]: os.path.join(work_dir, "ee02-signed.bin"),
        names[2]: os.path.join(unsigned_dir, "bootloader.bin"),
        names[3]: os.path.join(unsigned_dir, "partition-table.bin"),
        names[4]: os.path.join(unsigned_dir, "ota_data_initial.bin"),
        names[5]: os.path.join(work_dir, "second-signed.bin"),
    }
    for name, src in copies.items():
        shutil.copyfile(src, os.path.join(stage_dir, name))
    for name in names:
        if not os.path.isfile(os.path.join(stage_dir, name)):
            raise PublishError("staged asset %s is missing" % name)


def scratch_import(worktree, tag, stage_dir, state_dir):
    """Import the staged release into a scratch registry and list it."""
    imports = os.path.join(state_dir, "imports")
    tag_dir = os.path.join(imports, tag)
    os.makedirs(tag_dir, exist_ok=True)
    for name in asset_names(tag):
        shutil.copyfile(os.path.join(stage_dir, name), os.path.join(tag_dir, name))
    scratch = os.path.join(state_dir, "scratch-state")
    os.makedirs(scratch, exist_ok=True)
    env = dict(os.environ, PYTHONPATH=worktree)
    base = [sys.executable, "-m", "server.firmware_cli", "--state-dir", scratch]
    run(base + ["import-dir", imports], cwd=worktree, env=env)
    listing = run(base + ["list"], cwd=worktree, env=env).stdout
    print("Scratch import succeeded:\n%s" % listing.rstrip())


def publish(repo, tag, stage_dir):
    existing = run(["gh", "release", "view", tag], cwd=repo, check=False)
    if existing.returncode == 0:
        raise PublishError("a release for %s already exists; refusing to replace it" % tag)
    files = [os.path.join(stage_dir, n) for n in asset_names(tag)]
    run(
        ["gh", "release", "create", tag] + files
        + ["--title", tag, "--notes-file", os.path.join(stage_dir, "notes.md"),
           "--verify-tag"],
        cwd=repo,
    )
    print("Published release %s with %d assets." % (tag, len(files)))


def offer_deploy(repo, assume_yes):
    main_sha = run(["git", "-C", repo, "rev-parse", "origin/main"]).stdout.strip()[:7]
    cmd = ["gh", "workflow", "run", "deploy.yml", "--ref", "main",
           "-f", "confirm_sha=%s" % main_sha]
    print("To import the release into production run:\n  %s" % " ".join(cmd))
    answer = "y" if assume_yes else input("Start the production deploy now? [y/N] ")
    if answer.strip().lower() == "y":
        run(cmd, cwd=repo)
        print("Deploy started.")
    else:
        print("Deploy not started.")


def prepare(args, state_dir):
    """Provenance, download and checksum checks; returns (commit, unsigned_dir)."""
    check_tag(args.tag)
    commit = resolve_tag_commit(args.repo, args.tag)
    run_id = find_ci_run(args.repo, args.tag, commit)
    unsigned_dir = os.path.join(state_dir, "unsigned")
    run(["gh", "run", "download", run_id, "-n", "fw-unsigned-%s" % args.tag,
         "-D", unsigned_dir], cwd=args.repo)
    verify_checksums(unsigned_dir)
    check_key_file(args.key_file)
    print("Provenance and checksums verified for %s (%s)." % (args.tag, commit[:12]))
    return unsigned_dir


def execute(args, state_dir):
    unsigned_dir = prepare(args, state_dir)
    work_dir = os.path.join(state_dir, "work")
    stage_dir = os.path.join(state_dir, "stage")
    worktree = os.path.join(state_dir, "tree")
    os.makedirs(work_dir, exist_ok=True)
    os.makedirs(stage_dir, exist_ok=True)
    for name in ("ee02-skypane.bin", "second-skypane.bin"):
        shutil.copyfile(os.path.join(unsigned_dir, name), os.path.join(work_dir, name))
    run(["git", "-C", args.repo, "worktree", "add", "--detach", worktree, args.tag])
    try:
        sign_images(work_dir, args.key_file, args.platform)
        verify_signatures(work_dir, os.path.join(worktree, PUBKEY_REL), args.platform)
        print("Signatures verified against %s." % PUBKEY_REL)
        build_manifests(worktree, args.tag, work_dir, stage_dir)
        stage_assets(args.tag, work_dir, unsigned_dir, stage_dir)
        if args.dry_run:
            scratch_import(worktree, args.tag, stage_dir, state_dir)
            print("Dry run complete; nothing was published.")
            return
        print("Review the release notes before publishing:\n%s"
              % Path(stage_dir, "notes.md").read_text())
        publish(args.repo, args.tag, stage_dir)
    finally:
        run(["git", "-C", args.repo, "worktree", "remove", "--force", worktree],
            check=False)
    offer_deploy(args.repo, args.yes)


def build_parser():
    ap = argparse.ArgumentParser(
        prog="fw_publish_signed.py",
        description="Verify, sign and publish a firmware release on this machine.",
    )
    ap.add_argument("tag", help="release tag, e.g. fw-v1.3.0")
    ap.add_argument("--key-file", required=True,
                    help="path to the private signing key (mode 0600; never read here)")
    ap.add_argument("--repo", default=".", help="full git clone with tags (default: cwd)")
    ap.add_argument("--state-dir", default=None,
                    help="working directory (default: a fresh temporary directory)")
    ap.add_argument("--platform", default="linux/amd64",
                    help="docker platform for the signing container")
    ap.add_argument("--dry-run", action="store_true",
                    help="sign and verify, import into a scratch registry, publish nothing")
    ap.add_argument("--yes", action="store_true",
                    help="answer yes to the deploy question after a real run")
    return ap


def main(argv=None):
    args = build_parser().parse_args(argv)
    state_dir = args.state_dir or tempfile.mkdtemp(prefix="fw-publish-")
    os.makedirs(state_dir, exist_ok=True)
    try:
        execute(args, state_dir)
    except PublishError as exc:
        print("fw_publish_signed.py: %s" % exc, file=sys.stderr)
        return 1
    finally:
        if args.state_dir is None:
            shutil.rmtree(state_dir, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
