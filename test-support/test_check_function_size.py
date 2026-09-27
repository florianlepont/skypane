"""Tests for scripts/check_function_size.py, the function-size gate.

Loads the tool by file path (it is a standalone script, not a package),
same pattern as test_check_comment_history.py, and exercises the
code-line counter, the docstring exclusion, qualname nesting, the scope
rules and the two CLI subcommands directly on synthetic sources.
"""
import importlib.util
import os
import subprocess
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOL_PATH = os.path.join(REPO_ROOT, "scripts", "check_function_size.py")


def _load_tool():
    spec = importlib.util.spec_from_file_location("check_function_size", TOOL_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


cfs = _load_tool()


def _sizes(source):
    """Return {qualname: size} for every function in a source string."""
    rows = cfs.measure_source(source, "m.py")
    return {qualname: size for _path, _lineno, qualname, size in rows}


# ---------------------------------------------------------------------------
# Behavior: statements, docstring, comments and blanks
# ---------------------------------------------------------------------------

def test_statements_docstring_comments_and_blanks_measure_def_plus_statements():
    source = (
        "def f():\n"
        '    """One\n'
        "    Two\n"
        "    Three\n"
        '    Four"""\n'
        "    # comment a\n"
        "\n"
        "    x = 1\n"
        "    # comment b\n"
        "\n"
        "    y = 2\n"
        "    return x + y\n"
    )
    assert _sizes(source) == {"f": 4}


# ---------------------------------------------------------------------------
# Behavior: nested def counts toward the outer function and itself
# ---------------------------------------------------------------------------

def test_nested_def_counts_toward_outer_and_itself():
    source = (
        "def outer():\n"
        "    def inner():\n"
        "        return 1\n"
        "    return inner()\n"
    )
    sizes = _sizes(source)
    assert sizes["outer"] == 4
    assert sizes["outer.inner"] == 2


# ---------------------------------------------------------------------------
# Behavior: module/class docstrings excluded; a non-first string literal
# is ordinary code
# ---------------------------------------------------------------------------

def test_module_and_class_docstrings_excluded_but_non_first_string_counted():
    source = (
        '"""Module doc."""\n'
        "\n"
        "\n"
        "class C:\n"
        '    """Class doc."""\n'
        "\n"
        "    def m(self):\n"
        "        x = 1\n"
        '        "just a string, not the first statement"\n'
        "        return x\n"
    )
    sizes = _sizes(source)
    # def line + x = 1 + the non-first string literal + return x
    assert sizes["C.m"] == 4


# ---------------------------------------------------------------------------
# Behavior: a multi-line expression counts every physical line it spans
# ---------------------------------------------------------------------------

def test_multiline_call_counts_every_line_it_spans():
    source = (
        "def f():\n"
        "    foo(\n"
        "        1,\n"
        "        2,\n"
        "        3,\n"
        "    )\n"
    )
    # def line + the 5 lines of the call spread across foo(/1,/2,/3,/)
    assert _sizes(source) == {"f": 6}


# ---------------------------------------------------------------------------
# check subcommand: exit code and offender line format
# ---------------------------------------------------------------------------

def test_check_max_below_size_exits_1_and_prints_offender(tmp_path):
    (tmp_path / "big.py").write_text(
        "def big():\n"
        "    a = 1\n"
        "    b = 2\n"
        "    c = 3\n"
        "    d = 4\n"
        "    return a + b + c + d\n"
    )
    exit_code = cfs.main(["check", "--max", "5", str(tmp_path)])
    assert exit_code == 1


def test_check_max_at_or_above_size_exits_0(tmp_path):
    (tmp_path / "big.py").write_text(
        "def big():\n"
        "    a = 1\n"
        "    b = 2\n"
        "    c = 3\n"
        "    d = 4\n"
        "    return a + b + c + d\n"
    )
    exit_code = cfs.main(["check", "--max", "6", str(tmp_path)])
    assert exit_code == 0


def test_check_prints_path_line_qualname_size_for_each_offender(tmp_path, capsys):
    (tmp_path / "big.py").write_text(
        "def big():\n"
        "    a = 1\n"
        "    b = 2\n"
        "    c = 3\n"
        "    d = 4\n"
        "    return a + b + c + d\n"
    )
    exit_code = cfs.main(["check", "--max", "5", str(tmp_path)])
    out = capsys.readouterr().out
    assert exit_code == 1
    expected_path = os.path.join(str(tmp_path), "big.py")
    assert ("%s:1 big 6" % expected_path) in out


def test_check_prints_scanned_summary_line_when_none_over_max(tmp_path, capsys):
    (tmp_path / "small.py").write_text("def f():\n    return 1\n")
    exit_code = cfs.main(["check", "--max", "80", str(tmp_path)])
    out = capsys.readouterr().out
    assert exit_code == 0
    assert "functions scanned, none over 80" in out


# ---------------------------------------------------------------------------
# Scope rules
# ---------------------------------------------------------------------------

def test_iter_sources_skips_test_files_conftest_and_dot_venv_dir(tmp_path):
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "mod.py").write_text("def f():\n    return 1\n")
    (pkg / "test_mod.py").write_text("def test_f():\n    assert True\n")
    (pkg / "conftest.py").write_text("def fixture_helper():\n    return 1\n")
    venv_dir = pkg / ".venv" / "lib"
    venv_dir.mkdir(parents=True)
    (venv_dir / "vendored.py").write_text("def g():\n    return 1\n")

    found = sorted(cfs.iter_sources([str(tmp_path)]))
    assert found == [str(pkg / "mod.py")]


def test_iter_sources_accepts_a_single_py_file_as_a_root(tmp_path):
    single = tmp_path / "solo.py"
    single.write_text("def f():\n    return 1\n")
    assert list(cfs.iter_sources([str(single)])) == [str(single)]


def test_iter_sources_rejects_a_single_test_file_root(tmp_path):
    single = tmp_path / "test_solo.py"
    single.write_text("def test_f():\n    assert True\n")
    assert list(cfs.iter_sources([str(single)])) == []


# ---------------------------------------------------------------------------
# report subcommand
# ---------------------------------------------------------------------------

def test_report_top_prints_markdown_table_sorted_by_size_descending(tmp_path, capsys):
    (tmp_path / "m.py").write_text(
        "def small():\n"
        "    return 1\n"
        "\n"
        "\n"
        "def large():\n"
        "    a = 1\n"
        "    b = 2\n"
        "    c = 3\n"
        "    return a + b + c\n"
    )
    exit_code = cfs.main(["report", "--top", "3", str(tmp_path)])
    out = capsys.readouterr().out
    lines = out.splitlines()
    assert exit_code == 0
    assert lines[0] == "| Code lines | Location | Function |"
    assert lines[1] == "|---|---|---|"
    # "large" (5 code lines) must be listed before "small" (2 code lines)
    large_row_index = next(i for i, line in enumerate(lines) if "large" in line)
    small_row_index = next(i for i, line in enumerate(lines) if "small" in line)
    assert large_row_index < small_row_index


# ---------------------------------------------------------------------------
# stdlib-only, same convention as test_check_comment_history's own guard
# ---------------------------------------------------------------------------

def test_stdlib_only_imports():
    import ast as _ast

    with open(TOOL_PATH) as fh:
        tree = _ast.parse(fh.read())
    third_party = []
    for node in _ast.walk(tree):
        if isinstance(node, _ast.Import):
            names = [n.name.split(".")[0] for n in node.names]
        elif isinstance(node, _ast.ImportFrom) and node.level == 0:
            names = [node.module.split(".")[0]] if node.module else []
        else:
            continue
        for name in names:
            if name in sys.builtin_module_names:
                continue
            spec = importlib.util.find_spec(name)
            if spec is None or spec.origin is None:
                continue
            if "site-packages" in spec.origin or "dist-packages" in spec.origin:
                third_party.append(name)
    assert third_party == [], "non-stdlib imports found: %r" % third_party


# ---------------------------------------------------------------------------
# Tree-wide gate: the same assertion CI's blocking step makes, as a test so
# removing that one CI line still fails the suite
# ---------------------------------------------------------------------------

def test_no_function_in_server_or_stub_server_exceeds_80_code_lines(capsys):
    server_root = os.path.join(REPO_ROOT, "server")
    stub_server_root = os.path.join(REPO_ROOT, "stub-server")
    exit_code = cfs.main(["check", "--max", "80", server_root, stub_server_root])
    out = capsys.readouterr().out
    assert exit_code == 0, "function(s) over 80 code lines in server/ or stub-server/:\n%s" % out


def test_tool_own_source_passes_comment_history_check():
    result = subprocess.run(
        [sys.executable, os.path.join(REPO_ROOT, "scripts", "check_comment_history.py"),
         "check", "--paths", "scripts/check_function_size.py"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
