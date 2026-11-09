"""Served scripts lose their comments and nothing else."""
import glob
import os
import shutil
import subprocess

import pytest

from companion import js_minify, static_files

NODE = shutil.which("node")


def _strip(source):
    return js_minify.strip_comments(source)


def test_comments_go_and_code_stays():
    source = "// header\nvar a = 1; // trailing\n/* block */\nvar b = a /* inline */ + 2;\n"
    stripped = _strip(source)
    assert "header" not in stripped and "trailing" not in stripped
    assert "block" not in stripped and "inline" not in stripped
    assert stripped.splitlines() == ["var a = 1;", "var b = a   + 2;"]


def test_comment_markers_inside_literals_are_kept():
    source = (
        'var url = "http://example.test/a"; // real comment\n'
        "var star = '/* not a comment */';\n"
        "var re = /\\/\\/ x[/*]/g;\n"
        "var tpl = `a // b ${ \"//\" + `/* ${1} */` } c`;\n"
        "var half = total / 2 / 3; // division, not a regex\n")
    stripped = _strip(source)
    assert '"http://example.test/a"' in stripped
    assert "'/* not a comment */'" in stripped
    assert "/\\/\\/ x[/*]/g" in stripped
    assert "`a // b ${ \"//\" + `/* ${1} */` } c`" in stripped
    assert "real comment" not in stripped and "division" not in stripped
    assert "total / 2 / 3;" in stripped


def test_a_regex_after_return_or_an_operator_is_not_mistaken_for_division():
    source = "function f(x) { return /a\\/b'/.test(x); } // note\nvar g = x ? /'/ : /\"/;\n"
    stripped = _strip(source)
    assert "return /a\\/b'/.test(x);" in stripped and "/'/ : /\"/" in stripped
    assert "note" not in stripped


def test_a_multi_line_block_comment_keeps_the_line_break_between_statements():
    source = "var a = 1\n/* one\n two */\nvar b = 2\nvar c = a /* x\n y */ + b\n"
    stripped = _strip(source)
    assert stripped.splitlines() == ["var a = 1", "var b = 2", "var c = a", " + b"]


def test_indentation_and_multi_line_templates_are_untouched():
    source = "function f() {\n  // explain\n  return `line one\n    line two // kept`;\n}\n"
    assert _strip(source) == "function f() {\n  return `line one\n    line two // kept`;\n}\n"


def test_the_result_depends_only_on_the_input():
    source = "// a\nvar x = 1; /* b */\n"
    assert _strip(source) == _strip(source)
    assert js_minify.minify_js(source.encode()) == _strip(source).encode()


def _shipped_scripts():
    return sorted(glob.glob(os.path.join(static_files.STATIC_DIR, "*.js")))


def test_every_script_is_served_without_its_comments_and_smaller():
    for path in _shipped_scripts():
        served = static_files.static_entry(path).payload
        with open(path, "rb") as handle:
            source = handle.read()
        assert len(served) < len(source), path
        assert served == js_minify.minify_js(source), path


@pytest.mark.skipif(NODE is None, reason="node is not installed")
@pytest.mark.parametrize("path", _shipped_scripts(), ids=os.path.basename)
def test_every_served_script_still_parses(path, tmp_path):
    served = static_files.static_entry(path).payload
    target = tmp_path / "served.js"
    target.write_bytes(served)
    result = subprocess.run([NODE, "--check", str(target)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
