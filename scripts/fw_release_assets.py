# SPDX-License-Identifier: AGPL-3.0-only
"""Select the GitHub Release assets the production deploy downloads.

Reads the asset names of one release (one per line on stdin) and prints,
one per line, the names to download for that release tag:

* the legacy pair ``skypane-<tag>.bin`` + ``release.json`` when both exist;
* every typed pair ``release-<key>.json`` + ``skypane-<key>-<tag>.bin``
  whose key passes the same allow-list the server applies.

Asset names are remote, attacker-influenceable strings, so only names
that this module builds itself from a validated key and tag are ever
printed; nothing from stdin is echoed unchecked. Exit status: 0 when at
least one pair is wanted, 1 when none is (nothing printed), 2 for a bad
tag. Standard library only.
"""
import re
import sys
from collections.abc import Iterable

# Same shape as server.firmware_cli._TYPE_KEY_RE.
_TYPE_KEY_RE = re.compile(r"\A[a-z0-9-]{1,64}\Z")
_TAG_RE = re.compile(r"\A[A-Za-z0-9][A-Za-z0-9._-]{0,63}\Z")
_MANIFEST_RE = re.compile(r"\Arelease-([^\n]*)\.json\Z")

LEGACY_MANIFEST = "release.json"


def valid_tag(tag: str) -> bool:
    return bool(_TAG_RE.match(tag))


def wanted_assets(tag: str, names: Iterable[str]) -> list[str]:
    """Return the asset names to download for ``tag`` given the release's
    ``names``: the legacy pair first (if complete), then complete typed
    pairs sorted by key.
    """
    if not valid_tag(tag):
        raise ValueError("invalid release tag")
    present = set(names)
    wanted: list[str] = []
    legacy_image = f"skypane-{tag}.bin"
    if legacy_image in present and LEGACY_MANIFEST in present:
        wanted.extend([legacy_image, LEGACY_MANIFEST])
    keys: list[str] = []
    for name in present:
        match = _MANIFEST_RE.match(name)
        if match is None:
            continue
        key = match.group(1)
        if not _TYPE_KEY_RE.match(key):
            continue
        if f"skypane-{key}-{tag}.bin" in present:
            keys.append(key)
    for key in sorted(keys):
        wanted.extend([f"release-{key}.json", f"skypane-{key}-{tag}.bin"])
    return wanted


def main(argv: list[str]) -> int:
    if len(argv) != 2 or not valid_tag(argv[1]):
        print("usage: fw_release_assets.py <tag> < asset-names", file=sys.stderr)
        return 2
    names = [line.rstrip("\n") for line in sys.stdin]
    wanted = wanted_assets(argv[1], names)
    if not wanted:
        return 1
    sys.stdout.write("".join(f"{name}\n" for name in wanted))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
