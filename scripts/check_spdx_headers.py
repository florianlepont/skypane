#!/usr/bin/env python3
"""Every tracked Python file declares its licence with an SPDX line. Stdlib only.

The project's own code is AGPL-3.0-only, so a file without any SPDX line gets

    # SPDX-License-Identifier: AGPL-3.0-only

Placement (the header is a comment, so it changes neither the module
docstring nor `from __future__` handling nor the AST):
  - after a shebang line, which must stay on line 1;
  - after a PEP 263 encoding cookie on line 1 or 2, which must stay within
    the first two lines;
  - otherwise as the first line;
  - the file's own line ending is used (CRLF stays CRLF; LF when the file
    has no line ending at all) and a UTF-8 byte order mark stays first.
  - An empty (zero-byte) file receives the header and one newline.

A file counts as headed when its leading comment block (within the first
HEAD_LINES lines, before any statement) holds an `SPDX-License-Identifier:`
comment, whatever the identifier (Apache-2.0,
MIT, 0BSD, AGPL-3.0-only), so files that carry another licence keep it.

Excluded paths (never checked, never stamped):
  - firmware/: Apache-2.0 tree derived from the reference frame project;
  - stub-server/byos_server.py: Apache-2.0 derived device server;
  - the two dot-prefixed directories of working notes and agent tooling
    (EXCLUDED_PREFIXES): not shipped code.

Subcommands:
  check   list tracked, unheaded Python files; exit 1 when any exists
  write   stamp them in place (--dry-run only prints the counts); idempotent
"""
import argparse
import ast
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

HEADER = "# SPDX-License-Identifier: AGPL-3.0-only"
HEAD_LINES = 10
EXCLUDED_PREFIXES = ("firmware/", ".planning/", ".claude/")
EXCLUDED_FILES = ("stub-server/byos_server.py",)

_SPDX_RE = re.compile(rb"^\s*#\s*SPDX-License-Identifier:\s*\S")
_CODING_RE = re.compile(rb"^[ \t\f]*#.*?coding[:=][ \t]*[-\w.]+")
_BOM = b"\xef\xbb\xbf"


def is_excluded(path: str) -> bool:
    return path in EXCLUDED_FILES or path.startswith(EXCLUDED_PREFIXES)


def tracked_python_files(root: Path) -> list[str]:
    out = subprocess.run(
        ["git", "ls-files", "-z", "--", "*.py"],
        cwd=root, capture_output=True, check=True,
    ).stdout
    names = sorted(n.decode() for n in out.split(b"\0") if n)
    return [n for n in names if not is_excluded(n) and (root / n).is_file()]


def has_spdx(data: bytes) -> bool:
    """True when the leading comment block carries an SPDX line.

    Only comment and blank lines before the first statement count, so an
    SPDX text inside a docstring or string literal is not a header.
    """
    lines = data.removeprefix(_BOM).splitlines()[:HEAD_LINES]
    for line in lines:
        if _SPDX_RE.match(line):
            return True
        if line.strip() and not line.lstrip().startswith(b"#"):
            return False
    return False


def _eol_of(lines: list[bytes]) -> bytes:
    for line in lines:
        if line.endswith(b"\r\n"):
            return b"\r\n"
        if line.endswith(b"\n"):
            return b"\n"
    return b"\n"


def _insertion_index(lines: list[bytes]) -> tuple[int, str]:
    """Index of the line the header goes before, and the placement reason."""
    idx = 0
    reason = "plain"
    if lines and lines[0].startswith(b"#!"):
        idx, reason = 1, "shebang"
    for pos in range(min(2, len(lines))):
        if _CODING_RE.match(lines[pos]):
            idx = max(idx, pos + 1)
            reason = "shebang+encoding" if reason == "shebang" else "encoding"
    return idx, reason


def stamp_bytes(data: bytes) -> tuple[bytes, str]:
    """Return the stamped content and the placement reason."""
    if not data:
        return HEADER.encode() + b"\n", "empty"
    bom = _BOM if data.startswith(_BOM) else b""
    lines = data[len(bom):].splitlines(keepends=True)
    eol = _eol_of(lines)
    idx, reason = _insertion_index(lines)
    if idx and idx == len(lines) and not lines[-1].endswith((b"\n", b"\r")):
        lines[-1] += eol
    lines.insert(idx, HEADER.encode() + eol)
    return bom + b"".join(lines), reason


def first_statement_kind(data: bytes) -> str:
    """Classify the first statement: docstring, future-import or other."""
    try:
        body = ast.parse(data).body
    except (SyntaxError, ValueError):
        return "unparsable"
    if not body:
        return "empty"
    first = body[0]
    if (isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant)
            and isinstance(first.value.value, str)):
        return "docstring-first"
    if isinstance(first, ast.ImportFrom) and first.module == "__future__":
        return "future-import-first"
    return "other"


def _unheaded(root: Path) -> list[str]:
    return [n for n in tracked_python_files(root)
            if not has_spdx((root / n).read_bytes())]


def cmd_check(root: Path) -> int:
    missing = _unheaded(root)
    for name in missing:
        print(f"missing SPDX header: {name}")
    if missing:
        print(f"{len(missing)} file(s) without '{HEADER}'", file=sys.stderr)
        return 1
    return 0


def cmd_write(root: Path, dry_run: bool) -> int:
    placement: Counter[str] = Counter()
    first: Counter[str] = Counter()
    names = tracked_python_files(root)
    stamped = 0
    for name in names:
        path = root / name
        data = path.read_bytes()
        if has_spdx(data):
            continue
        new, reason = stamp_bytes(data)
        placement[reason] += 1
        first[first_statement_kind(data)] += 1
        stamped += 1
        if not dry_run:
            path.write_bytes(new)
    print(f"tracked non-excluded files: {len(names)}")
    print(f"already headed: {len(names) - stamped}")
    print(f"{'would stamp' if dry_run else 'stamped'}: {stamped}")
    for key, count in sorted(placement.items()):
        print(f"  placement {key}: {count}")
    for key, count in sorted(first.items()):
        print(f"  first statement {key}: {count}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, default=Path.cwd(),
                        help="git working tree to scan (default: cwd)")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("check")
    write = sub.add_parser("write")
    write.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    if args.command == "check":
        return cmd_check(args.root)
    return cmd_write(args.root, args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
