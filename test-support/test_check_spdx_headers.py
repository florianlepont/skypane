"""Tests for scripts/check_spdx_headers.py, the SPDX header gate.

The script is run as a subprocess over throwaway git repositories; each test
asserts on exit codes, output and the resulting file bytes.
"""
import ast
import os
import subprocess
import sys

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOL = os.path.join(REPO_ROOT, "scripts", "check_spdx_headers.py")
HEADER = b"# SPDX-License-Identifier: AGPL-3.0-only"


def _git(repo, *args):
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path):
    _git(tmp_path, "init", "-q")
    return tmp_path


def _add(repo, name, data):
    path = repo / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    _git(repo, "add", name)
    return path


def _run(repo, *args):
    return subprocess.run(
        [sys.executable, TOOL, "--root", str(repo), *args],
        capture_output=True, text=True,
    )


def _stamp(repo, name, data):
    path = _add(repo, name, data)
    result = _run(repo, "write")
    assert result.returncode == 0, result.stderr
    return path.read_bytes()


def test_check_reports_exactly_the_unheaded_file(repo):
    _add(repo, "good.py", HEADER + b"\nx = 1\n")
    _add(repo, "bad.py", b"x = 1\n")
    result = _run(repo, "check")
    assert result.returncode == 1
    assert "bad.py" in result.stdout
    assert "good.py" not in result.stdout


def test_check_passes_when_all_headed(repo):
    _add(repo, "a.py", HEADER + b"\nx = 1\n")
    assert _run(repo, "check").returncode == 0


@pytest.mark.parametrize("ident", ["Apache-2.0", "MIT", "0BSD"])
def test_other_spdx_identifier_is_kept(repo, ident):
    original = f"# SPDX-License-Identifier: {ident}\nx = 1\n".encode()
    path = _add(repo, "other.py", original)
    assert _run(repo, "check").returncode == 0
    assert _run(repo, "write").returncode == 0
    assert path.read_bytes() == original


def test_plain_file_gets_header_first(repo):
    assert _stamp(repo, "p.py", b"x = 1\n") == HEADER + b"\nx = 1\n"


def test_shebang_stays_on_line_one(repo):
    out = _stamp(repo, "s.py", b"#!/usr/bin/env python3\nx = 1\n")
    assert out == b"#!/usr/bin/env python3\n" + HEADER + b"\nx = 1\n"


def test_shebang_only_file_without_newline(repo):
    out = _stamp(repo, "s.py", b"#!/usr/bin/env python3")
    assert out == b"#!/usr/bin/env python3\n" + HEADER + b"\n"


def test_encoding_cookie_stays_in_first_two_lines(repo):
    out = _stamp(repo, "e.py", b"# -*- coding: latin-1 -*-\nx = 1\n")
    assert out == b"# -*- coding: latin-1 -*-\n" + HEADER + b"\nx = 1\n"


def test_shebang_then_cookie_then_header(repo):
    src = b"#!/usr/bin/python3\n# coding: utf-8\nx = 1\n"
    out = _stamp(repo, "se.py", src)
    assert out == b"#!/usr/bin/python3\n# coding: utf-8\n" + HEADER + b"\nx = 1\n"


def test_docstring_stays_the_module_docstring(repo):
    src = b'"""Module doc."""\nx = 1\n'
    out = _stamp(repo, "d.py", src)
    assert out.startswith(HEADER + b"\n")
    assert ast.get_docstring(ast.parse(out)) == "Module doc."
    assert ast.dump(ast.parse(out)) == ast.dump(ast.parse(src))


def test_future_import_still_first_statement(repo):
    src = b"from __future__ import annotations\nx: int = 1\n"
    out = _stamp(repo, "f.py", src)
    compile(out, "f.py", "exec")
    assert ast.dump(ast.parse(out)) == ast.dump(ast.parse(src))


def test_empty_file_gets_header_and_newline(repo):
    assert _stamp(repo, "empty.py", b"") == HEADER + b"\n"


def test_crlf_file_keeps_crlf(repo):
    out = _stamp(repo, "c.py", b"#!/usr/bin/env python3\r\nx = 1\r\n")
    assert out == b"#!/usr/bin/env python3\r\n" + HEADER + b"\r\nx = 1\r\n"
    assert b"\n" not in out.replace(b"\r\n", b"")


def test_bom_stays_first(repo):
    out = _stamp(repo, "b.py", b"\xef\xbb\xbfx = 1\n")
    assert out == b"\xef\xbb\xbf" + HEADER + b"\nx = 1\n"


def test_write_is_idempotent(repo):
    _add(repo, "a.py", b"x = 1\n")
    _add(repo, "b.py", b'"""Doc."""\n')
    assert _run(repo, "write").returncode == 0
    first = {n: (repo / n).read_bytes() for n in ("a.py", "b.py")}
    assert _run(repo, "write").returncode == 0
    assert {n: (repo / n).read_bytes() for n in first} == first
    assert _run(repo, "check").returncode == 0


def test_dry_run_changes_nothing_and_counts(repo):
    _add(repo, "a.py", b"x = 1\n")
    _add(repo, "b.py", b'"""Doc."""\n')
    result = _run(repo, "write", "--dry-run")
    assert result.returncode == 0
    assert (repo / "a.py").read_bytes() == b"x = 1\n"
    assert "would stamp: 2" in result.stdout
    assert "placement plain: 2" in result.stdout
    assert "first statement docstring-first: 1" in result.stdout


@pytest.mark.parametrize("name", [
    "firmware/tools/gen.py",
    "stub-server/byos_server.py",
    ".planning/spikes/x.py",
])
def test_excluded_paths_are_skipped_even_when_unheaded(repo, name):
    path = _add(repo, name, b"x = 1\n")
    assert _run(repo, "check").returncode == 0
    assert _run(repo, "write").returncode == 0
    assert path.read_bytes() == b"x = 1\n"


def test_non_python_files_are_ignored(repo):
    _add(repo, "notes.txt", b"hello\n")
    assert _run(repo, "check").returncode == 0


def test_untracked_file_is_not_checked(repo):
    (repo / "new.py").write_bytes(b"x = 1\n")
    assert _run(repo, "check").returncode == 0


def test_spdx_text_inside_a_docstring_is_not_a_header(repo):
    src = b'"""Doc.\n\n# SPDX-License-Identifier: MIT\n"""\nx = 1\n'
    _add(repo, "d.py", src)
    assert _run(repo, "check").returncode == 1
    out = _stamp(repo, "d.py", src)
    assert out == HEADER + b"\n" + src
