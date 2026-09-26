"""Finds project-history references in source comments and docstrings, and
proves that a comment-only edit left the code unchanged. Stdlib only.

Subcommands:
  check      scan tracked files for history references in comments
  ratio      per-file comment-line ratio, as a TSV or a before/after table
  same-code  prove two revisions of a file differ only in comments
"""
import argparse
import ast
import gzip
import io
import os
import re
import shutil
import subprocess
import sys
import tokenize
from collections import Counter

# ---------------------------------------------------------------------------
# Pattern set: each entry finds one shape of history reference. Prefix ids
# use an explicit allowlist rather than a generic letters-then-digits shape,
# so that unrelated short codes are never mistaken for one.
# ---------------------------------------------------------------------------

ALLOWLISTED_PREFIXES = [
    "CFG", "TST", "FW", "INT", "CMP", "SEC", "DEVICE", "HYG", "EFF", "ARC",
    "RER", "PLANE", "DOC", "VIS", "MSG", "UXA", "UIR", "MR", "CP", "DP",
    "SEED", "UAT", "QT", "WR", "CR", "IN", "BL",
]

_ARTIFACT_SUFFIXES = (
    "PLAN", "SUMMARY", "CONTEXT", "RESEARCH", "REVIEW", "VERIFICATION",
    "UI-SPEC", "PATTERNS", "VALIDATION", "UAT",
)

PATTERNS = [
    ("plan-artifact", re.compile(
        r"\b\d{1,3}(?:\.\d+){0,2}(?:-\d{1,2}[a-z]?)?-"
        r"(?:" + "|".join(_ARTIFACT_SUFFIXES) + r")(?:\.md)?\b"
    )),
    ("d-id", re.compile(r"\bD-(?:A\d{1,2}|\d{2}-\d{2}|\d{1,3})\b")),
    ("prefix-id", re.compile(
        r"\b(?:" + "|".join(ALLOWLISTED_PREFIXES) + r")-\d{1,3}\b"
    )),
    ("threat-id", re.compile(r"\bT-\d{2}(?:-\d{2}){1,3}\b")),
    ("quick-task", re.compile(r"\b\d{6}-[a-z0-9]{3}\b")),
    ("phase-word", re.compile(r"\bPhase \d+\b")),
    ("planning-path", re.compile(r"\.planning/")),
    ("bare-plan-id", re.compile(
        r"\b(?:plan|Plan) \d{1,3}-\d{2}[a-z]?\b"
        r"|\b\d{1,3}-\d{2}[a-z]?\b(?= Task)"
    )),
]


def find_pattern_hits(text):
    """Return every (pattern_name, start_offset, matched_text) in a text blob."""
    hits = []
    for name, pattern in PATTERNS:
        for m in pattern.finditer(text):
            hits.append((name, m.start(), m.group(0)))
    hits.sort(key=lambda h: h[1])
    return hits


# ---------------------------------------------------------------------------
# Per-language extraction: each function returns a list of
# (start_line, comment_or_docstring_text) spans, aware of strings so that an
# id inside quoted text is never mistaken for a comment.
# ---------------------------------------------------------------------------

def extract_python(source):
    spans = []
    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(source).readline))
    except (tokenize.TokenizeError, IndentationError, SyntaxError):
        tokens = []
    for tok in tokens:
        if tok.type == tokenize.COMMENT:
            spans.append((tok.start[0], tok.string))
    try:
        tree = ast.parse(source)
    except SyntaxError:
        tree = None
    if tree is not None:
        nodes = [tree] + [
            n for n in ast.walk(tree)
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
        ]
        for node in nodes:
            body = getattr(node, "body", None)
            if not body:
                continue
            first = body[0]
            if (
                isinstance(first, ast.Expr)
                and isinstance(first.value, ast.Constant)
                and isinstance(first.value.value, str)
            ):
                spans.append((first.value.lineno, first.value.value))
    return spans


def _c_like_chunks(source):
    """Split C/H source into ("code" | "comment", text) chunks, string-aware."""
    chunks = []
    i = 0
    n = len(source)
    code_start = 0

    def flush(end):
        if end > code_start:
            chunks.append(("code", source[code_start:end]))

    while i < n:
        c = source[i]
        if c in "\"'":
            i += 1
            while i < n and source[i] != c:
                if source[i] == "\\":
                    i += 2
                    continue
                i += 1
            i += 1
            continue
        if c == "/" and i + 1 < n and source[i + 1] == "/":
            flush(i)
            start = i
            while i < n and source[i] != "\n":
                i += 1
            chunks.append(("comment", source[start:i]))
            code_start = i
            continue
        if c == "/" and i + 1 < n and source[i + 1] == "*":
            flush(i)
            start = i
            i += 2
            while i + 1 < n and not (source[i] == "*" and source[i + 1] == "/"):
                i += 1
            i += 2
            chunks.append(("comment", source[start:i]))
            code_start = i
            continue
        i += 1
    flush(n)
    return chunks


def extract_c(source):
    spans = []
    line = 1
    for kind, text in _c_like_chunks(source):
        if kind == "comment":
            spans.append((line, text))
        line += text.count("\n")
    return spans


def _strip_c_comments(source):
    return "".join(
        text if kind == "code" else " " for kind, text in _c_like_chunks(source)
    )


_JS_REGEX_CONTEXT_KEYWORDS = {
    "return", "typeof", "instanceof", "in", "of", "new", "delete",
    "void", "throw", "case", "do", "else", "yield", "await",
}


def _js_last_word(text):
    m = re.search(r"([A-Za-z_$][\w$]*)\s*$", text)
    return m.group(1) if m else ""


def _js_chunks(source):
    """Split JS source into ("code" | "comment", text) chunks: string,
    template-literal and regex-literal aware, so a `//` inside a URL string
    or a `/.../.` regex literal never starts a comment."""
    chunks = []
    i = 0
    n = len(source)
    code_start = 0

    def flush(end):
        if end > code_start:
            chunks.append(("code", source[code_start:end]))

    while i < n:
        c = source[i]
        if c in "\"'":
            i += 1
            while i < n and source[i] != c:
                if source[i] == "\\":
                    i += 2
                    continue
                i += 1
            i += 1
            continue
        if c == "`":
            i += 1
            depth = 0
            while i < n:
                if source[i] == "\\":
                    i += 2
                    continue
                if source[i] == "`" and depth == 0:
                    i += 1
                    break
                if source[i] == "$" and i + 1 < n and source[i + 1] == "{":
                    depth += 1
                    i += 2
                    continue
                if source[i] == "}" and depth > 0:
                    depth -= 1
                    i += 1
                    continue
                i += 1
            continue
        if c == "/" and i + 1 < n and source[i + 1] == "/":
            flush(i)
            start = i
            while i < n and source[i] != "\n":
                i += 1
            chunks.append(("comment", source[start:i]))
            code_start = i
            continue
        if c == "/" and i + 1 < n and source[i + 1] == "*":
            flush(i)
            start = i
            i += 2
            while i + 1 < n and not (source[i] == "*" and source[i + 1] == "/"):
                i += 1
            i += 2
            chunks.append(("comment", source[start:i]))
            code_start = i
            continue
        if c == "/":
            tail = source[max(0, i - 30):i].rstrip()
            is_regex_context = (
                tail == ""
                or tail[-1] in "(,=:[!&|?{};"
                or _js_last_word(tail) in _JS_REGEX_CONTEXT_KEYWORDS
            )
            if is_regex_context:
                i += 1
                in_class = False
                while i < n:
                    if source[i] == "\\":
                        i += 2
                        continue
                    if source[i] == "[":
                        in_class = True
                    elif source[i] == "]":
                        in_class = False
                    elif source[i] == "/" and not in_class:
                        i += 1
                        break
                    elif source[i] == "\n":
                        break
                    i += 1
                while i < n and source[i].isalpha():
                    i += 1
                continue
            i += 1
            continue
        i += 1
    flush(n)
    return chunks


def extract_js(source):
    spans = []
    line = 1
    for kind, text in _js_chunks(source):
        if kind == "comment":
            spans.append((line, text))
        line += text.count("\n")
    return spans


def _strip_js_comments(source):
    return "".join(text if kind == "code" else " " for kind, text in _js_chunks(source))


def _css_chunks(source):
    """Split CSS source into ("code" | "comment", text) chunks: string and
    url() aware, so an id inside a quoted string or url() is not a comment."""
    chunks = []
    i = 0
    n = len(source)
    code_start = 0

    def flush(end):
        if end > code_start:
            chunks.append(("code", source[code_start:end]))

    while i < n:
        c = source[i]
        if c in "\"'":
            i += 1
            while i < n and source[i] != c:
                if source[i] == "\\":
                    i += 2
                    continue
                i += 1
            i += 1
            continue
        if source[i:i + 4].lower() == "url(":
            i += 4
            while i < n and source[i] != ")":
                if source[i] in "\"'":
                    quote = source[i]
                    i += 1
                    while i < n and source[i] != quote:
                        if source[i] == "\\":
                            i += 2
                            continue
                        i += 1
                    i += 1
                    continue
                i += 1
            i += 1
            continue
        if c == "/" and i + 1 < n and source[i + 1] == "*":
            flush(i)
            start = i
            i += 2
            while i + 1 < n and not (source[i] == "*" and source[i + 1] == "/"):
                i += 1
            i += 2
            chunks.append(("comment", source[start:i]))
            code_start = i
            continue
        i += 1
    flush(n)
    return chunks


def extract_css(source):
    spans = []
    line = 1
    for kind, text in _css_chunks(source):
        if kind == "comment":
            spans.append((line, text))
        line += text.count("\n")
    return spans


def _strip_css_comments(source):
    return "".join(text if kind == "code" else " " for kind, text in _css_chunks(source))


def extract_hash(source, path):
    """`#`-comment formats: a `#` starting a token outside quotes begins a
    comment. In an sdkconfig file, a disabled-symbol line is configuration,
    not a comment, and is excluded."""
    spans = []
    is_sdkconfig = "sdkconfig" in os.path.basename(path)
    for idx, raw_line in enumerate(source.split("\n"), start=1):
        in_squote = False
        in_dquote = False
        comment_start = None
        i = 0
        n = len(raw_line)
        while i < n:
            ch = raw_line[i]
            if in_squote:
                if ch == "'":
                    in_squote = False
                i += 1
                continue
            if in_dquote:
                if ch == "\\":
                    i += 2
                    continue
                if ch == '"':
                    in_dquote = False
                i += 1
                continue
            if ch == "'":
                in_squote = True
                i += 1
                continue
            if ch == '"':
                in_dquote = True
                i += 1
                continue
            if ch == "#" and (i == 0 or raw_line[i - 1] in " \t"):
                comment_start = i
                break
            i += 1
        if comment_start is None:
            continue
        text = raw_line[comment_start:]
        if is_sdkconfig and re.match(r"^#\s*CONFIG_\w+\s+is not set\s*$", text):
            continue
        spans.append((idx, text))
    return spans


def _hash_code_lines(source, path):
    spans = dict(extract_hash(source, path))
    lines = source.split("\n")
    out = []
    for idx, raw in enumerate(lines, start=1):
        comment_text = spans.get(idx)
        if comment_text is None:
            out.append(raw.rstrip())
            continue
        pos = raw.find(comment_text)
        out.append(raw[:pos if pos != -1 else len(raw)].rstrip())
    # Blank and comment-only lines carry no configuration, so dropping them
    # lets a comment shrink without shifting the lines that follow it.
    return [line for line in out if line.strip()]


def _same_code_xml(base_text, working_text):
    def code_lines(text):
        text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
        return [line.rstrip() for line in text.split("\n") if line.strip()]
    return code_lines(base_text) == code_lines(working_text)


def extract_xml(source):
    spans = []
    i = 0
    n = len(source)
    line = 1
    while i < n:
        c = source[i]
        if c == "\n":
            line += 1
            i += 1
            continue
        if source[i:i + 4] == "<!--":
            start_line = line
            start = i
            i += 4
            while i + 2 < n and source[i:i + 3] != "-->":
                if source[i] == "\n":
                    line += 1
                i += 1
            i += 3
            spans.append((start_line, source[start:i]))
            continue
        i += 1
    return spans


# ---------------------------------------------------------------------------
# File dispatch and exclusions
# ---------------------------------------------------------------------------

_HASH_EXTENSIONS = {".sh", ".service", ".timer", ".yml", ".yaml", ".toml", ".in"}
_HASH_BASENAMES = {"Caddyfile", "CMakeLists.txt", "partitions.csv", ".gitignore"}


def extractor_for_path(path):
    base = os.path.basename(path)
    ext = os.path.splitext(path)[1]
    if ext == ".py":
        return extract_python
    if ext in (".c", ".h"):
        return extract_c
    if ext == ".js":
        return extract_js
    if ext == ".css":
        return extract_css
    if base.endswith(".plist.template"):
        return extract_xml
    if (
        ext in _HASH_EXTENSIONS
        or base in _HASH_BASENAMES
        or base.startswith("Kconfig")
        or base.startswith("sdkconfig")
        or base.endswith(".env.example")
    ):
        return lambda src: extract_hash(src, path)
    return None


_EXCLUDED_BASENAMES = {"LICENSE", "NOTICE"}


def is_excluded(path):
    p = path.replace(os.sep, "/")
    if p.startswith(".planning/") or p.startswith(".claude/"):
        return True
    if p.endswith(".md"):
        return True
    if os.path.basename(p) in _EXCLUDED_BASENAMES:
        return True
    if p.startswith("server/fixtures/") or p.startswith("hardware/fixtures/") or p.startswith("hardware/logs/"):
        return True
    if re.match(r"^server/requirements.*\.txt$", p):
        return True
    if extractor_for_path(p) is None:
        return True
    return False


# ---------------------------------------------------------------------------
# check
# ---------------------------------------------------------------------------

def git_ls_files(root="."):
    result = subprocess.run(
        ["git", "ls-files"], cwd=root, capture_output=True, text=True, check=True
    )
    return [line for line in result.stdout.splitlines() if line]


def check(paths=None, root="."):
    if paths is None:
        files = [f for f in git_ls_files(root) if not is_excluded(f)]
    else:
        files = list(paths)

    hits = []
    for rel in files:
        full = os.path.join(root, rel)
        if not os.path.isfile(full):
            continue
        extractor = extractor_for_path(rel)
        if extractor is None:
            continue
        with open(full, encoding="utf-8", errors="replace") as fh:
            source = fh.read()
        for start_line, text in extractor(source):
            for name, mstart, matched in find_pattern_hits(text):
                line_no = start_line + text[:mstart].count("\n")
                hits.append((rel, line_no, name, matched))
    return hits


# ---------------------------------------------------------------------------
# ratio
# ---------------------------------------------------------------------------

RATIO_COLUMNS = ["path", "lines", "comment_lines", "ratio", "history_hits", "bytes", "gzip_bytes"]


def _resolve(root, p):
    full = p if os.path.isabs(p) else os.path.join(root, p)
    display = os.path.relpath(full, root)
    return full, display


def _ratio_rows(paths, root):
    rows = []
    for p in paths:
        full, display = _resolve(root, p)
        if not os.path.isfile(full):
            continue
        with open(full, "rb") as fh:
            raw = fh.read()
        source = raw.decode("utf-8", errors="replace")
        total_lines = source.count("\n") + (1 if source and not source.endswith("\n") else 0)
        extractor = extractor_for_path(display)
        comment_line_set = set()
        history_hits = 0
        if extractor is not None:
            for start_line, text in extractor(source):
                for i in range(text.count("\n") + 1):
                    comment_line_set.add(start_line + i)
                history_hits += len(find_pattern_hits(text))
        ratio = (len(comment_line_set) / total_lines) if total_lines else 0.0
        rows.append((
            display, total_lines, len(comment_line_set), "%.4f" % ratio,
            history_hits, len(raw), len(gzip.compress(raw, 9)),
        ))
    return rows


def write_ratio_tsv(paths, out_path, root="."):
    rows = _ratio_rows(paths, root)
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write("\t".join(RATIO_COLUMNS) + "\n")
        for row in rows:
            fh.write("\t".join(str(v) for v in row) + "\n")


def markdown_ratio_table(paths, before_tsv_path, root="."):
    before_rows = {}
    with open(before_tsv_path, encoding="utf-8") as fh:
        next(fh, None)
        for line in fh:
            cols = line.rstrip("\n").split("\t")
            if len(cols) < len(RATIO_COLUMNS):
                continue
            before_rows[cols[0]] = cols

    after_rows = {row[0]: row for row in _ratio_rows(paths, root)}
    display_paths = [_resolve(root, p)[1] for p in paths]

    lines = [
        "| path | lines | comment_lines before | comment_lines after | "
        "history_hits before | history_hits after |",
        "|---|---|---|---|---|---|",
    ]
    for display in display_paths:
        b = before_rows.get(display)
        a = after_rows.get(display)
        lines.append("| %s | %s | %s | %s | %s | %s |" % (
            display,
            a[1] if a else (b[1] if b else "0"),
            b[2] if b else "0",
            a[2] if a else "0",
            b[4] if b else "0",
            a[4] if a else "0",
        ))
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# same-code
# ---------------------------------------------------------------------------

_PRAGMA_RE = re.compile(
    r"^\s*#!.*$"
    r"|#\s*noqa\b.*$"
    r"|#\s*type:\s*ignore\b.*$"
    r"|#\s*pragma:\s*no cover\b.*$"
    r"|#\s*shellcheck\s+(?:disable|enable|source|shell|external-sources)=.*$"
    r"|#\s*fmt:\s*\S+.*$"
    r"|#\s*ruff:\s*\S+.*$"
    r"|SPDX-License-Identifier:.*$"
    r"|Copyright\b.*$",
    re.MULTILINE,
)


def _pragma_spdx_multiset(text):
    return Counter(m.group(0).strip() for m in _PRAGMA_RE.finditer(text))


def git_show(root, rev, path):
    result = subprocess.run(
        ["git", "show", "%s:%s" % (rev, path)], cwd=root, capture_output=True, text=True
    )
    if result.returncode != 0:
        return None
    return result.stdout


def git_changed_files(root, base_rev):
    result = subprocess.run(
        ["git", "diff", "--name-only", base_rev], cwd=root, capture_output=True, text=True, check=True
    )
    return [line for line in result.stdout.splitlines() if line]


def _strip_docstrings(tree, keep_module_doc):
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if isinstance(node, ast.Module) and keep_module_doc:
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
            del node.body[0]


def _python_ast_dump(source, keep_module_doc):
    tree = ast.parse(source)
    _strip_docstrings(tree, keep_module_doc)
    return ast.dump(tree, annotate_fields=True, include_attributes=False)


def _reads_module_dunder_doc(source):
    """True only if the module loads its own `__doc__` global (the
    `argparse.ArgumentParser(description=__doc__)` idiom), not merely
    mentions the word in a string, comment, or as an attribute of some
    other object (`mod.__doc__`)."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return False
    return any(
        isinstance(node, ast.Name) and node.id == "__doc__" and isinstance(node.ctx, ast.Load)
        for node in ast.walk(tree)
    )


def _same_code_python(base_text, working_text):
    keep_module_doc = (
        _reads_module_dunder_doc(base_text) or _reads_module_dunder_doc(working_text)
    )
    try:
        base_dump = _python_ast_dump(base_text, keep_module_doc)
        work_dump = _python_ast_dump(working_text, keep_module_doc)
    except SyntaxError:
        return base_text == working_text
    return base_dump == work_dump


def _cpp_normalize(text):
    cpp = shutil.which("cpp")
    if cpp is None:
        return None
    try:
        result = subprocess.run(
            [cpp, "-fpreprocessed", "-P", "-w", "-"],
            input=text, capture_output=True, text=True, timeout=10,
        )
    except OSError:
        return None
    if result.returncode != 0:
        return None
    return re.sub(r"\s+", " ", result.stdout).strip()


def _same_code_c(base_text, working_text):
    base_norm = _cpp_normalize(base_text)
    work_norm = _cpp_normalize(working_text)
    if base_norm is not None and work_norm is not None:
        return base_norm == work_norm
    fallback_base = re.sub(r"\s+", " ", _strip_c_comments(base_text)).strip()
    fallback_work = re.sub(r"\s+", " ", _strip_c_comments(working_text)).strip()
    return fallback_base == fallback_work


def _same_code_js_css(rel, base_text, working_text):
    strip = _strip_js_comments if os.path.splitext(rel)[1] == ".js" else _strip_css_comments
    return strip(base_text).split() == strip(working_text).split()


def _same_code_hash(rel, base_text, working_text):
    return _hash_code_lines(base_text, rel) == _hash_code_lines(working_text, rel)


def _same_code_one(rel, base_text, working_text):
    if _pragma_spdx_multiset(base_text) != _pragma_spdx_multiset(working_text):
        return False
    ext = os.path.splitext(rel)[1]
    if ext == ".py":
        return _same_code_python(base_text, working_text)
    if ext in (".c", ".h"):
        return _same_code_c(base_text, working_text)
    if ext in (".js", ".css"):
        return _same_code_js_css(rel, base_text, working_text)
    if os.path.basename(rel).endswith(".plist.template"):
        return _same_code_xml(base_text, working_text)
    if extractor_for_path(rel) is not None:
        return _same_code_hash(rel, base_text, working_text)
    return base_text == working_text


def same_code(root, base_rev, paths=None, allow=None):
    allow = set(allow or [])
    if paths is None:
        paths = git_changed_files(root, base_rev)
    differing = []
    for rel in paths:
        if rel in allow:
            continue
        full = os.path.join(root, rel)
        if not os.path.isfile(full):
            continue
        with open(full, encoding="utf-8", errors="replace") as fh:
            working_text = fh.read()
        base_text = git_show(root, base_rev, rel)
        if base_text is None:
            continue
        if not _same_code_one(rel, base_text, working_text):
            differing.append(rel)
    return differing


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    parser = argparse.ArgumentParser(prog="check_comment_history.py")
    sub = parser.add_subparsers(dest="command", required=True)

    p_check = sub.add_parser("check", help="scan for history references in comments")
    p_check.add_argument("--paths", nargs="*", default=None)

    p_ratio = sub.add_parser("ratio", help="per-file comment-line ratio")
    p_ratio.add_argument("--out")
    p_ratio.add_argument("--before")
    p_ratio.add_argument("--markdown", action="store_true")
    p_ratio.add_argument("paths", nargs="*")

    p_same = sub.add_parser("same-code", help="prove a revision pair differs only in comments")
    p_same.add_argument("--base", required=True)
    p_same.add_argument("--allow", action="append", default=[],
                        help="a path allowed to differ in code; repeat per path")
    p_same.add_argument("paths", nargs="*")

    args = parser.parse_args(argv)

    if args.command == "check":
        hits = check(paths=args.paths, root=".")
        for rel, line_no, name, matched in hits:
            print("%s:%d: %s: %s" % (rel, line_no, name, matched))
        return 1 if hits else 0

    if args.command == "ratio":
        paths = args.paths or [f for f in git_ls_files(".") if not is_excluded(f)]
        if args.before and args.markdown:
            print(markdown_ratio_table(paths, args.before, root="."))
            return 0
        write_ratio_tsv(paths, args.out or "/dev/stdout", root=".")
        return 0

    if args.command == "same-code":
        differing = same_code(".", args.base, paths=args.paths or None, allow=args.allow)
        for item in differing:
            print(item)
        return 1 if differing else 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
