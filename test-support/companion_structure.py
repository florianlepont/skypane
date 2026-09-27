"""AST-based structural measurement of the companion app's production
source: file line counts and per-function code-line counts.

This module lives outside `companion/` on purpose: `companion/test_suite_guards.py`
rule G2 bans `ast`/`inspect`/`tokenize`/`linecache` imports inside any
`companion/test_*.py` module or `companion/conftest.py`, because those tests
are meant to assert on served behaviour, never on source text. Measuring
file and function size IS a source-text measurement by nature, so it is
built here, in `test-support/` (outside the guard's scan, outside
`[tool.coverage.run] source`), and `companion/test_structure_guards.py`
only imports this module's already-computed results — it never touches
`ast` itself.

Stdlib only: `ast`, `os`.
"""

import ast
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(_HERE)
COMPANION_DIR = os.path.join(REPO_ROOT, "companion")
STATIC_DIR = os.path.join(COMPANION_DIR, "static")

_STATIC_SUFFIXES = (".js", ".css")


def _to_repo_relative(path):
    return os.path.relpath(path, REPO_ROOT).replace(os.sep, "/")


def production_files():
    """Every `companion/**/*.py` (including `companion/pages/`,
    `companion/i18n_fr/` and any future subpackage), plus
    `companion/static/*.js` and `companion/static/*.css` — excluding
    `test_*.py` and `conftest.py`. Repo-relative paths, sorted, `/`-separated.
    """
    found = []
    for dirpath, dirnames, filenames in os.walk(COMPANION_DIR):
        dirnames[:] = sorted(d for d in dirnames if d != "__pycache__")
        for name in sorted(filenames):
            full = os.path.join(dirpath, name)
            if name.endswith(".py"):
                if name.startswith("test_") or name == "conftest.py":
                    continue
                found.append(_to_repo_relative(full))
            elif os.path.normpath(dirpath) == os.path.normpath(STATIC_DIR) and name.endswith(_STATIC_SUFFIXES):
                found.append(_to_repo_relative(full))
    return sorted(found)


def file_line_counts():
    """{repo-relative path: physical line count} for every `production_files()` entry."""
    counts = {}
    for path in production_files():
        abs_path = os.path.join(REPO_ROOT, path)
        with open(abs_path, "r", encoding="utf-8") as handle:
            counts[path] = sum(1 for _ in handle)
    return counts


def _docstring_line_range(node):
    """The (start, end) inclusive line range of `node`'s own docstring
    statement, or `None` if it has none. Only the first statement of the
    body counts — never a later string literal, never a nested
    function/class's own docstring.
    """
    body = getattr(node, "body", None)
    if not body:
        return None
    first = body[0]
    if not isinstance(first, ast.Expr):
        return None
    value = first.value
    if not (isinstance(value, ast.Constant) and isinstance(value.value, str)):
        return None
    return first.lineno, getattr(first, "end_lineno", first.lineno)


def _code_line_count(node, lines):
    """Lines in `node`'s own span (its `lineno`..`end_lineno`) that are not
    blank, not comment-only, and not part of `node`'s own docstring.
    Lines belonging to a NESTED function/class (including that nested
    function's own docstring) are counted here too — a nested function is
    counted inside its parent's total AND reported separately.
    """
    start = node.lineno
    end = getattr(node, "end_lineno", start)
    doc_range = _docstring_line_range(node)
    doc_lines = set(range(doc_range[0], doc_range[1] + 1)) if doc_range else set()
    count = 0
    for lineno in range(start, end + 1):
        if lineno in doc_lines:
            continue
        text = lines[lineno - 1] if 0 <= lineno - 1 < len(lines) else ""
        stripped = text.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            continue
        count += 1
    return count


def _walk_functions(node, qualname_stack, lines, path, result):
    for child in ast.iter_child_nodes(node):
        if isinstance(child, ast.ClassDef):
            _walk_functions(child, qualname_stack + [child.name], lines, path, result)
        elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
            qualname = ".".join(qualname_stack + [child.name])
            key = "%s::%s" % (path, qualname)
            result[key] = _code_line_count(child, lines)
            # Recurse so a nested function is ALSO reported under its own
            # key, in addition to being counted inside this one's total.
            _walk_functions(child, qualname_stack + [child.name], lines, path, result)
        else:
            _walk_functions(child, qualname_stack, lines, path, result)


def function_code_lines():
    """{"path::Qualified.name": n} for every `FunctionDef`/`AsyncFunctionDef`
    in every production `.py` file. Methods carry their class as a prefix
    (e.g. `"companion/app.py::Handler._dispatch_get"`).
    """
    result = {}
    for path in production_files():
        if not path.endswith(".py"):
            continue
        abs_path = os.path.join(REPO_ROOT, path)
        with open(abs_path, "r", encoding="utf-8") as handle:
            source = handle.read()
        lines = source.splitlines()
        tree = ast.parse(source, filename=path)
        _walk_functions(tree, [], lines, path, result)
    return result


def oversized_files(limit=1500):
    """Sorted list of production files whose physical line count exceeds `limit`."""
    return sorted(path for path, n in file_line_counts().items() if n > limit)


def long_functions(limit=80):
    """Sorted list of `"path::Qualified.name"` keys whose code-line count exceeds `limit`."""
    return sorted(key for key, n in function_code_lines().items() if n > limit)
