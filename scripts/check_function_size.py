#!/usr/bin/env python3
"""Measures the size (and, for `report`, nothing more than the size) of every
function in a Python source tree. Stdlib only.

Definition:
  - Code line: a physical line holding at least one token other than
    COMMENT, NL, NEWLINE, INDENT, DEDENT or ENDMARKER, minus every line that
    belongs to a module, class or function docstring (the first statement of
    that body, when it is a bare string-constant expression).
  - Function size: the count of code lines within a function's own line
    range (`def` line through its last line, inclusive), counting a nested
    def's lines toward the outer function as well as toward itself.
  - Scope: `.py` files under the given roots, skipping any path segment
    named `.venv`, `__pycache__` or `node_modules`, and any file named
    `test_*.py` or `conftest.py`.

Subcommands:
  check   fail (exit 1) if any function's size exceeds --max
  report  print a markdown table of the largest functions
"""
import argparse
import ast
import io
import os
import sys
import tokenize

_IGNORED_TOKEN_TYPES = frozenset((
    tokenize.COMMENT,
    tokenize.NL,
    tokenize.NEWLINE,
    tokenize.INDENT,
    tokenize.DEDENT,
    tokenize.ENDMARKER,
))

_SKIPPED_DIR_NAMES = frozenset(("__pycache__", "node_modules"))


def code_lines(source):
    """Return the set of physical line numbers holding at least one token
    other than a comment, blank-line marker or structural whitespace token.
    Docstring lines are still included here; callers exclude them with
    `docstring_lines`."""
    lines = set()
    for tok in tokenize.generate_tokens(io.StringIO(source).readline):
        if tok.type in _IGNORED_TOKEN_TYPES:
            continue
        for lineno in range(tok.start[0], tok.end[0] + 1):
            lines.add(lineno)
    return lines


def docstring_lines(tree):
    """Return every line number that belongs to a module, class or function
    docstring: the first body statement, when it is a bare string-constant
    expression. A string literal anywhere else in the body is ordinary code."""
    lines = set()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        body = getattr(node, "body", None)
        if not body:
            continue
        first = body[0]
        if (
            isinstance(first, ast.Expr)
            and isinstance(first.value, ast.Constant)
            and isinstance(first.value.value, str)
        ):
            lines.update(range(first.value.lineno, first.value.end_lineno + 1))
    return lines


def _walk_functions(node, prefix, out):
    """Depth-first walk collecting (function_node, qualname) pairs, where
    qualname joins enclosing class/function names with '.'."""
    for child in ast.iter_child_nodes(node):
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
            qualname = prefix + child.name
            out.append((child, qualname))
            _walk_functions(child, qualname + ".", out)
        elif isinstance(child, ast.ClassDef):
            qualname = prefix + child.name
            _walk_functions(child, qualname + ".", out)
        else:
            _walk_functions(child, prefix, out)


def measure_source(source, path):
    """Return (path, lineno, qualname, size) for every function/async
    function defined in `source`, size being its code-line count (nested
    defs included)."""
    tree = ast.parse(source)
    real_code_lines = code_lines(source) - docstring_lines(tree)
    functions = []
    _walk_functions(tree, "", functions)
    results = []
    for node, qualname in functions:
        span = range(node.lineno, node.end_lineno + 1)
        size = sum(1 for lineno in span if lineno in real_code_lines)
        results.append((path, node.lineno, qualname, size))
    return results


def _is_skipped_file(path):
    parts = path.replace(os.sep, "/").split("/")
    if any(part in _SKIPPED_DIR_NAMES or part == ".venv" for part in parts):
        return True
    basename = os.path.basename(path)
    return basename.startswith("test_") or basename == "conftest.py"


def iter_sources(roots):
    """Yield every in-scope `.py` path under `roots`. Each root may be a
    directory or a single `.py` file."""
    for root in roots:
        if os.path.isfile(root):
            if root.endswith(".py") and not _is_skipped_file(root):
                yield root
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [
                d for d in dirnames if d not in _SKIPPED_DIR_NAMES and d != ".venv"
            ]
            for filename in filenames:
                if not filename.endswith(".py"):
                    continue
                full_path = os.path.join(dirpath, filename)
                if _is_skipped_file(full_path):
                    continue
                yield full_path


def _scan(roots):
    rows = []
    for path in iter_sources(roots):
        with open(path, encoding="utf-8") as fh:
            source = fh.read()
        try:
            rows.extend(measure_source(source, path))
        except SyntaxError:
            continue
    return rows


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    parser = argparse.ArgumentParser(prog="check_function_size.py", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p_check = sub.add_parser("check", help="fail if any function exceeds --max code lines")
    p_check.add_argument("--max", type=int, required=True)
    p_check.add_argument("roots", nargs="+")

    p_report = sub.add_parser("report", help="print a markdown table of the largest functions")
    p_report.add_argument("--top", type=int, default=15)
    p_report.add_argument("roots", nargs="+")

    args = parser.parse_args(argv)

    if args.command == "check":
        rows = _scan(args.roots)
        offenders = sorted(
            (row for row in rows if row[3] > args.max),
            key=lambda row: row[3],
            reverse=True,
        )
        for path, lineno, qualname, size in offenders:
            print("%s:%d %s %d" % (path, lineno, qualname, size))
        if offenders:
            return 1
        print("%d functions scanned, none over %d" % (len(rows), args.max))
        return 0

    if args.command == "report":
        rows = sorted(_scan(args.roots), key=lambda row: row[3], reverse=True)
        print("| Code lines | Location | Function |")
        print("|---|---|---|")
        for path, lineno, qualname, size in rows[: args.top]:
            print("| %d | %s:%d | %s |" % (size, path, lineno, qualname))
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
