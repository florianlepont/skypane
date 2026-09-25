"""The TST-10/12/13/14 behaviour-over-source-text guard: a meta-test that
fails if a migrated companion test module reads a `.planning`/UI-SPEC
file, reads a production source file as text, inspects source with
`inspect`/`ast`/`tokenize`/`linecache`, reads a `__doc__`, redefines the
shared `Harness`/`http_request`/`_NoRedirectHandler` machinery, writes
outside `tmp_path` or uses a literal `/nonexistent` host path, runs
`os.chmod` outside a root-safety marker, still carries the legacy
`EXPECTED_CHECK_COUNT`/`check()`/`main()` shape, drives Playwright's
`browser` fixture directly instead of the guarded `new_context`/`page`
fixtures from `companion/conftest.py`, runs a regex, `in` test or str
search over the served stylesheet's text instead of parsing it (G11), or
imports another test module instead of a `*_helpers.py` module (G12).

The guard is strict: it scans every `companion/test_*.py` module and
`companion/conftest.py`, with no exemption other than this file itself,
which spells out the forbidden shapes on purpose as self-test samples.
"""

import ast
import collections
import os

import pytest

from skypane_test_support import REPO_ROOT

Violation = collections.namedtuple("Violation", ["rule", "lineno", "detail"])

_COMPANION_DIR = os.path.join(REPO_ROOT, "companion")

_GUARD_MODULE = "companion/test_suite_guards.py"


def scanned_files():
    """Every `companion/test_*.py` module plus `companion/conftest.py`,
    minus this guard module - the set the guard enforces its rules
    against.
    """
    return sorted(
        os.path.join("companion", name)
        for name in os.listdir(_COMPANION_DIR)
        if name == "conftest.py" or (name.startswith("test_") and name.endswith(".py"))
        if os.path.join("companion", name) != _GUARD_MODULE
    )


# --- G3 helpers: source-suffixed paths and __file__/HERE/REPO_ROOT-style
#     names -------------------------------------------------------------

SOURCE_SUFFIXES = (".py", ".js", ".css", ".html", ".htm")

_RELEVANT_NAME_EXACT = ("HERE", "REPO_ROOT", "__file__")
_RELEVANT_NAME_SUFFIXES = ("_DIR", "_ROOT")

_FORBIDDEN_CLASS_NAMES = frozenset({"Harness", "_InProcessHarness", "_NoRedirectHandler"})

_G2_MODULES = frozenset({"inspect", "ast", "tokenize", "linecache"})


def _is_route_or_url(value):
    return value.startswith("/") or value.startswith("http")


def _is_source_suffixed_str(value):
    return any(value.endswith(suf) for suf in SOURCE_SUFFIXES) and not _is_route_or_url(value)


def _tree_has_source_suffixed_constant(node):
    return any(
        isinstance(sub, ast.Constant) and isinstance(sub.value, str) and _is_source_suffixed_str(sub.value)
        for sub in ast.walk(node)
    )


def _tree_has_dunder_file(node):
    return any(isinstance(sub, ast.Name) and sub.id == "__file__" for sub in ast.walk(node))


def _tree_has_relevant_name(node):
    for sub in ast.walk(node):
        if isinstance(sub, ast.Name):
            name = sub.id
            if name.startswith("tmp"):
                continue
            if name in _RELEVANT_NAME_EXACT or name.endswith(_RELEVANT_NAME_SUFFIXES):
                return True
    return False


def _call_mode_is_write(call):
    """True when `call` (an `open`/`.open` Call node) carries an explicit
    write/append/exclusive-create mode, positionally or as `mode=`.
    """
    mode_value = None
    if len(call.args) >= 2 and isinstance(call.args[1], ast.Constant):
        mode_value = call.args[1].value
    for kw in call.keywords:
        if kw.arg == "mode" and isinstance(kw.value, ast.Constant):
            mode_value = kw.value.value
    if not isinstance(mode_value, str):
        return False
    return any(c in mode_value for c in "wax")


def _is_main_guard(test):
    if not (isinstance(test, ast.Compare) and len(test.ops) == 1 and isinstance(test.ops[0], ast.Eq)):
        return False
    names, consts = [], []
    for side in (test.left, test.comparators[0]):
        if isinstance(side, ast.Name):
            names.append(side.id)
        elif isinstance(side, ast.Constant):
            consts.append(side.value)
    return "__name__" in names and "__main__" in consts


def _mentions_requires_non_root(nodes):
    for node in nodes:
        for sub in ast.walk(node):
            if isinstance(sub, ast.Name) and sub.id == "requires_non_root":
                return True
            if isinstance(sub, ast.Attribute) and sub.attr == "requires_non_root":
                return True
    return False


def _module_mentions_requires_non_root(tree):
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "pytestmark":
                    if _mentions_requires_non_root([node.value]):
                        return True
    return False


def _collect_docstring_ids(tree):
    """Every `ast.Constant` node id() that is a real docstring (the first
    `Expr` statement of a module, class or function body) - G1 never
    flags these.
    """
    ids = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            body = getattr(node, "body", None)
            if body and isinstance(body[0], ast.Expr):
                value = body[0].value
                if isinstance(value, ast.Constant) and isinstance(value.value, str):
                    ids.add(id(value))
    return ids


def _is_helpers_filename(filename):
    return os.path.basename(filename).endswith("_helpers.py")


def _is_test_module_name(dotted):
    last = dotted.rsplit(".", 1)[-1]
    return last.startswith("test_") and not last.endswith("_helpers")


def _has_module_level_test_false(tree):
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "__test__":
                    if isinstance(node.value, ast.Constant) and node.value.value is False:
                        return True
    return False


class _Scanner(ast.NodeVisitor):
    def __init__(self, docstring_ids, module_chmod_exempt):
        self.docstring_ids = docstring_ids
        self.module_chmod_exempt = module_chmod_exempt
        self.violations = []
        self._function_stack = []

    def _add(self, node, rule, detail):
        self.violations.append(Violation(rule, node.lineno, detail))

    # G1 (planning/UI-SPEC strings) and G6 (a /nonexistent literal)
    def visit_Constant(self, node):
        if isinstance(node.value, str) and id(node) not in self.docstring_ids:
            value = node.value
            if "/nonexistent" in value:
                self._add(node, "G6", "/nonexistent literal: %r" % (value,))
            if not _is_route_or_url(value) and (".planning" in value or "UI-SPEC" in value):
                self._add(node, "G1", "planning/UI-SPEC string: %r" % (value,))
        self.generic_visit(node)

    # G2 (inspect/ast/tokenize/linecache), G4 (__doc__), G6 (tempfile.*)
    def visit_Attribute(self, node):
        if node.attr == "__doc__":
            self._add(node, "G4", "...__doc__")
        if isinstance(node.value, ast.Name):
            if node.value.id in _G2_MODULES:
                self._add(node, "G2", "%s.%s" % (node.value.id, node.attr))
            if node.value.id == "tempfile":
                self._add(node, "G6", "tempfile.%s" % (node.attr,))
        self.generic_visit(node)

    # G5 (Harness / _InProcessHarness / _NoRedirectHandler / a
    # HTTPRedirectHandler subclass)
    def visit_ClassDef(self, node):
        if node.name in _FORBIDDEN_CLASS_NAMES:
            self._add(node, "G5", "class %s" % (node.name,))
        for base in node.bases:
            base_name = base.id if isinstance(base, ast.Name) else (
                base.attr if isinstance(base, ast.Attribute) else None)
            if base_name == "HTTPRedirectHandler":
                self._add(node, "G5", "class %s(HTTPRedirectHandler)" % (node.name,))
        self.generic_visit(node)

    def visit_FunctionDef(self, node):
        self._visit_function(node)

    def visit_AsyncFunctionDef(self, node):
        self._visit_function(node)

    def _visit_function(self, node):
        if node.name == "http_request":
            self._add(node, "G5", "def http_request(...)")
        if node.name in ("check", "main") and not self._function_stack:
            self._add(node, "G8", "module-level def %s(...)" % (node.name,))
        self._function_stack.append(node)
        self.generic_visit(node)
        self._function_stack.pop()

    # G12: a test module importing another test module (shared code
    # lives in a `*_helpers.py` module or in test-support/)
    def visit_Import(self, node):
        for alias in node.names:
            if _is_test_module_name(alias.name):
                self._add(node, "G12", "import %s" % (alias.name,))
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        module = node.module or ""
        if _is_test_module_name(module):
            self._add(node, "G12", "from %s import ..." % (module,))
        else:
            for alias in node.names:
                if _is_test_module_name(alias.name):
                    self._add(node, "G12", "from %s import %s" % (module, alias.name))
        self.generic_visit(node)

    # G8 (EXPECTED_CHECK_COUNT)
    def visit_Assign(self, node):
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == "EXPECTED_CHECK_COUNT":
                self._add(node, "G8", "EXPECTED_CHECK_COUNT assignment")
        self.generic_visit(node)

    # G8 (if __name__ == "__main__")
    def visit_If(self, node):
        if _is_main_guard(node.test):
            self._add(node, "G8", 'if __name__ == "__main__"')
        self.generic_visit(node)

    # G3(c): a Path `/` BinOp
    def visit_BinOp(self, node):
        if isinstance(node.op, ast.Div):
            if _tree_has_source_suffixed_constant(node) and _tree_has_relevant_name(node):
                self._add(node, "G3", "path built with / over a source-suffixed component")
        self.generic_visit(node)

    def visit_Call(self, node):
        func = node.func

        # G5: build_opener(...)
        if (isinstance(func, ast.Name) and func.id == "build_opener") or (
                isinstance(func, ast.Attribute) and func.attr == "build_opener"):
            self._add(node, "G5", "build_opener(...)")

        # G10: browser.new_context(...) / browser.new_page(...) / sync_playwright(...)
        if isinstance(func, ast.Attribute) and func.attr in ("new_context", "new_page") and \
                isinstance(func.value, ast.Name) and func.value.id == "browser":
            self._add(node, "G10", "browser.%s(...)" % (func.attr,))
        if (isinstance(func, ast.Name) and func.id == "sync_playwright") or (
                isinstance(func, ast.Attribute) and func.attr == "sync_playwright"):
            self._add(node, "G10", "sync_playwright(...)")

        # G7: os.chmod(...) without @requires_non_root
        if isinstance(func, ast.Attribute) and func.attr == "chmod" and \
                isinstance(func.value, ast.Name) and func.value.id == "os":
            if not self._chmod_is_exempt():
                self._add(node, "G7", "os.chmod(...) without @requires_non_root")

        # G3(a): open() / io.open() / codecs.open() over a source-suffixed
        # path or __file__, with no mode or a read mode
        is_open = (isinstance(func, ast.Name) and func.id == "open") or (
            isinstance(func, ast.Attribute) and func.attr == "open" and
            isinstance(func.value, ast.Name) and func.value.id in ("io", "codecs"))
        if is_open and not _call_mode_is_write(node):
            if _tree_has_source_suffixed_constant(node) or _tree_has_dunder_file(node):
                self._add(node, "G3", "open(...) over a source-suffixed path or __file__")

        # G3(b): .read_text() / .read_bytes() / .open() over a
        # source-suffixed receiver
        if isinstance(func, ast.Attribute) and func.attr in ("read_text", "read_bytes", "open"):
            already_excluded = func.attr == "open" and _call_mode_is_write(node)
            if not already_excluded:
                if _tree_has_source_suffixed_constant(func.value) or _tree_has_dunder_file(func.value):
                    self._add(node, "G3", "%s() over a source-suffixed path" % (func.attr,))

        # G3(c): os.path.join(...) / Path(...) building a source path
        is_join = isinstance(func, ast.Attribute) and func.attr == "join" and \
            isinstance(func.value, ast.Attribute) and func.value.attr == "path" and \
            isinstance(func.value.value, ast.Name) and func.value.value.id == "os"
        is_path_call = (isinstance(func, ast.Name) and func.id == "Path") or (
            isinstance(func, ast.Attribute) and func.attr == "Path")
        if is_join or is_path_call:
            if _tree_has_source_suffixed_constant(node) and _tree_has_relevant_name(node):
                label = "os.path.join" if is_join else "Path"
                self._add(node, "G3", "%s(...) building a source path" % (label,))

        self.generic_visit(node)

    def _chmod_is_exempt(self):
        if self.module_chmod_exempt:
            return True
        return any(_mentions_requires_non_root(fn.decorator_list) for fn in self._function_stack)


# --- G11: regex/substring checks over the served stylesheet's text -----
#
# A stylesheet check parses what the app serves (`companion_markup`'s
# `css_rules` / `declarations_for` / `rules_with_selector` /
# `custom_properties`), so a comment, a reordering or a whitespace change
# can never make it pass or fail. G11 follows the text `served_stylesheet()`
# returns (or the body of a GET of the style route) through assignments,
# fixtures, string transforms, slices and calls to the module's own
# functions, and flags any regex, `in` test or str search method over it.

_CSS_TEXT_SOURCES = frozenset({"served_stylesheet"})
_STYLE_ROUTE_FETCHERS = frozenset({"get", "http_request"})
_STR_TRANSFORMS = frozenset({
    "lower", "upper", "casefold", "strip", "lstrip", "rstrip", "replace",
    "expandtabs", "translate", "removeprefix", "removesuffix", "decode",
})
_STR_SEARCHES = frozenset({
    "count", "index", "rindex", "find", "rfind", "startswith", "endswith",
    "split", "rsplit", "splitlines", "partition", "rpartition", "__contains__",
})
_RE_METHODS = frozenset({"search", "match", "fullmatch", "findall", "finditer", "sub", "subn", "split"})

# (module, top-level function) -> why that one function may scan the
# served stylesheet's raw characters.
G11_ALLOWLIST = {
    ("companion/test_status_pages_07.py", "test_style_css_carries_no_stray_comment_terminator"): (
        "an unterminated or stray comment delimiter changes which rules exist at all, so a "
        "parser reading the stylesheet cannot see the defect; only the raw served characters "
        "show it"
    ),
}


def _is_fixture_decorator(node):
    target = node.func if isinstance(node, ast.Call) else node
    return (isinstance(target, ast.Name) and target.id == "fixture") or (
        isinstance(target, ast.Attribute) and target.attr == "fixture")


def _names_in_target(target):
    if isinstance(target, ast.Name):
        return [target.id]
    if isinstance(target, (ast.Tuple, ast.List)):
        return [name for elt in target.elts for name in _names_in_target(elt)]
    if isinstance(target, ast.Starred):
        return _names_in_target(target.value)
    return []


def _is_style_route_fetch(call):
    func = call.func
    name = func.id if isinstance(func, ast.Name) else (
        func.attr if isinstance(func, ast.Attribute) else None)
    if name not in _STYLE_ROUTE_FETCHERS:
        return False
    for sub in ast.walk(call):
        if isinstance(sub, ast.Constant) and isinstance(sub.value, str) and sub.value.endswith("style.css"):
            return True
        if isinstance(sub, ast.Name) and "STYLE_ROUTE" in sub.id:
            return True
        if isinstance(sub, ast.Attribute) and "STYLE_ROUTE" in sub.attr:
            return True
    return False


class _ServedCssTaint:
    """Flow-insensitive taint analysis of one module for G11."""

    def __init__(self, tree):
        self.functions = {}
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self.functions[node.name] = node
            elif isinstance(node, ast.ClassDef):
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        self.functions["%s.%s" % (node.name, item.name)] = item
        self.returns_css = set(_CSS_TEXT_SOURCES)
        self.css_fixtures = set()
        self.css_params = collections.defaultdict(set)
        self.tainted = {}
        self._solve()

    def is_css(self, node, names):
        if isinstance(node, ast.Name):
            return node.id in names
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name):
                if func.id in self.returns_css:
                    return True
                return func.id == "str" and bool(node.args) and self.is_css(node.args[0], names)
            if isinstance(func, ast.Attribute):
                if func.attr in _CSS_TEXT_SOURCES:
                    return True
                if func.attr in _STR_TRANSFORMS or func.attr in _STR_SEARCHES:
                    return self.is_css(func.value, names)
                is_re = (isinstance(func.value, ast.Name) and func.value.id == "re") or \
                    func.attr in _RE_METHODS
                if is_re:
                    args = list(node.args) + [kw.value for kw in node.keywords]
                    return any(self.is_css(a, names) for a in args)
            return False
        if isinstance(node, ast.Subscript):
            return self.is_css(node.value, names)
        if isinstance(node, ast.BinOp):
            return self.is_css(node.left, names) or self.is_css(node.right, names)
        if isinstance(node, ast.JoinedStr):
            return any(isinstance(v, ast.FormattedValue) and self.is_css(v.value, names)
                       for v in node.values)
        if isinstance(node, ast.IfExp):
            return self.is_css(node.body, names) or self.is_css(node.orelse, names)
        if isinstance(node, ast.BoolOp):
            return any(self.is_css(v, names) for v in node.values)
        if isinstance(node, ast.NamedExpr):
            return self.is_css(node.value, names)
        return False

    def _seed(self, key, fn):
        params = [a.arg for a in fn.args.posonlyargs + fn.args.args + fn.args.kwonlyargs]
        names = {p for p in params if p in self.css_fixtures}
        names |= self.css_params[key]
        return names

    def _analyse(self, key, fn):
        """One pass over `fn`; returns True when any shared fact grew."""
        grew = False
        names = self.tainted.get(key, set()) | self._seed(key, fn)
        while True:
            before = len(names)
            for node in ast.walk(fn):
                if isinstance(node, ast.Assign):
                    if isinstance(node.value, ast.Call) and _is_style_route_fetch(node.value):
                        for target in node.targets:
                            if isinstance(target, ast.Tuple) and len(target.elts) == 3:
                                names.update(_names_in_target(target.elts[2]))
                            else:
                                names.update(_names_in_target(target))
                    elif self.is_css(node.value, names):
                        for target in node.targets:
                            names.update(_names_in_target(target))
                elif isinstance(node, (ast.AugAssign, ast.AnnAssign)):
                    if node.value is not None and self.is_css(node.value, names):
                        names.update(_names_in_target(node.target))
                elif isinstance(node, ast.NamedExpr):
                    if self.is_css(node.value, names):
                        names.update(_names_in_target(node.target))
                elif isinstance(node, (ast.For, ast.AsyncFor, ast.comprehension)):
                    if self.is_css(node.iter, names):
                        names.update(_names_in_target(node.target))
                elif isinstance(node, ast.withitem):
                    if node.optional_vars is not None and self.is_css(node.context_expr, names):
                        names.update(_names_in_target(node.optional_vars))
            if len(names) == before:
                break
        self.tainted[key] = names

        for node in ast.walk(fn):
            if isinstance(node, (ast.Return, ast.Yield)) and node.value is not None:
                if self.is_css(node.value, names) and key not in self.returns_css and "." not in key:
                    self.returns_css.add(key)
                    grew = True
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and \
                    node.func.id in self.functions:
                callee = self.functions[node.func.id]
                params = [a.arg for a in callee.args.posonlyargs + callee.args.args]
                hits = {params[i] for i, arg in enumerate(node.args)
                        if i < len(params) and self.is_css(arg, names)}
                hits |= {kw.arg for kw in node.keywords if kw.arg and self.is_css(kw.value, names)}
                if not hits <= self.css_params[node.func.id]:
                    self.css_params[node.func.id] |= hits
                    grew = True
        if key in self.returns_css and key not in self.css_fixtures and \
                any(_is_fixture_decorator(d) for d in fn.decorator_list):
            self.css_fixtures.add(key)
            grew = True
        return grew

    def _solve(self):
        changed = True
        while changed:
            changed = False
            for key, fn in self.functions.items():
                if self._analyse(key, fn):
                    changed = True

    def violations(self, filename, allowlist=None):
        allowlist = G11_ALLOWLIST if allowlist is None else allowlist
        found = []
        for key, fn in self.functions.items():
            if (filename, key) in allowlist:
                continue
            names = self.tainted.get(key, set())
            for node in ast.walk(fn):
                detail = self._sink(node, names)
                if detail:
                    found.append(Violation("G11", node.lineno, "%s over served stylesheet text" % detail))
        return found

    def _sink(self, node, names):
        if isinstance(node, ast.Compare):
            for op, right in zip(node.ops, node.comparators):
                if isinstance(op, (ast.In, ast.NotIn)) and self.is_css(right, names):
                    return "`in` test"
            return None
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            return None
        func = node.func
        args = list(node.args) + [kw.value for kw in node.keywords]
        if isinstance(func.value, ast.Name) and func.value.id == "re":
            if any(self.is_css(a, names) for a in args):
                return "re.%s()" % func.attr
            return None
        if func.attr in _STR_SEARCHES and self.is_css(func.value, names):
            return ".%s()" % func.attr
        if func.attr in _RE_METHODS and not self.is_css(func.value, names) and \
                any(self.is_css(a, names) for a in args):
            return "pattern.%s()" % func.attr
        return None


def scan_source(source, filename):
    """Every `Violation` in `source` (a companion test module's own text,
    read by the guard itself - never by the modules it scans). `filename`
    is used for a `*_helpers.py` name check (G9) and the G11 allowlist; `ast.parse`
    receives it for accurate error messages.
    """
    tree = ast.parse(source, filename=filename)
    docstring_ids = _collect_docstring_ids(tree)
    module_chmod_exempt = _module_mentions_requires_non_root(tree)
    scanner = _Scanner(docstring_ids, module_chmod_exempt)
    scanner.visit(tree)
    violations = scanner.violations
    if _is_helpers_filename(filename) and not _has_module_level_test_false(tree):
        violations.append(Violation("G9", 1, "*_helpers.py without module-level __test__ = False"))
    violations.extend(_ServedCssTaint(tree).violations(filename))
    return violations


# --- Self-tests --------------------------------------------------------

# (rule, case_id, source, filename_or_None) - filename defaults to
# "synthetic_<case_id>.py" when None.
_POSITIVE_CASES = [
    ("G1", "planning_context_md",
     'X = os.path.join(REPO_ROOT, ".planning", "phases", "x", "06.6.3-CONTEXT.md")\n', None),
    ("G1", "ui_spec_md",
     'X = os.path.join(REPO_ROOT, ".planning", "phases", "x", "20-UI-SPEC.md")\n', None),
    ("G2", "inspect_getsource",
     "import inspect\nSRC = inspect.getsource(module)\n", None),
    ("G3", "self_read",
     'with open(os.path.join(HERE, "test_config_page.py")) as fh:\n    fh.read()\n', None),
    ("G3", "style_css_disk_open",
     'with open(os.path.join(HERE, "static", "style.css")) as fh:\n    fh.read()\n', None),
    ("G4", "dunder_doc",
     "X = SomeModule.__doc__\n", None),
    ("G5", "harness_class",
     "class Harness:\n    pass\n", None),
    ("G5", "http_request_def",
     "def http_request(url):\n    pass\n", None),
    ("G6", "nonexistent_path",
     'V = health_page.anomaly_active("/nonexistent/definitely-not-here")\n', None),
    ("G6", "tempfile_mkdtemp",
     'import tempfile\nD = tempfile.mkdtemp(prefix="x-")\n', None),
    ("G7", "chmod_without_marker",
     'import os\n\n\ndef test_x():\n    os.chmod("/tmp/x", 0o644)\n', None),
    ("G8", "expected_check_count",
     "EXPECTED_CHECK_COUNT = 5\n", None),
    ("G8", "module_level_check",
     "def check(name, fn):\n    pass\n", None),
    ("G8", "module_level_main",
     "def main():\n    pass\n", None),
    ("G8", "dunder_main_guard",
     'if __name__ == "__main__":\n    pass\n', None),
    ("G9", "helpers_without_test_false",
     "X = 1\n", "companion/test_something_helpers.py"),
    ("G10", "browser_new_context",
     "ctx = browser.new_context()\n", None),
    ("G10", "sync_playwright_call",
     "with sync_playwright() as p:\n    pass\n", None),
    ("G12", "import_sibling_test_module",
     "import companion.test_config_page_05 as tcp05\n", None),
    ("G12", "from_package_import_test_module",
     "from companion import test_config_page_05\n", None),
    ("G12", "from_test_module_import_name",
     "from companion.test_config_page_05 import _helper\n", None),
    ("G11", "re_search_over_served_stylesheet",
     "def test_x(server):\n    css = served_stylesheet(server)\n    assert re.search(r'a', css)\n", None),
    ("G11", "substring_via_css_fixture",
     "@pytest.fixture\ndef served_css(app):\n    return served_stylesheet(app)\n\n\n"
     "def test_x(served_css):\n    assert '.a {' in served_css\n", None),
    ("G11", "index_after_a_string_transform",
     "def test_x(server):\n    css = served_stylesheet(server).lower()\n    css.index('.a')\n", None),
    ("G11", "count_over_a_slice",
     "def test_x(server):\n    css = served_stylesheet(server)\n    css[10:].count('a')\n", None),
    ("G11", "regex_inside_a_helper_given_served_css",
     "def _body(css, selector):\n    return re.search(selector, css)\n\n\n"
     "def test_x(server):\n    _body(served_stylesheet(server), '.a')\n", None),
    ("G11", "compiled_pattern_over_comment_stripped_css",
     "PAT = re.compile('a')\n\n\ndef test_x(server):\n"
     "    stripped = re.sub('x', '', served_stylesheet(server))\n    PAT.findall(stripped)\n", None),
    ("G11", "substring_over_style_route_body",
     "def test_x(server):\n    status, headers, body = get(server, '/static/style.css')\n"
     "    assert b'.a' in body\n", None),
]

_NEGATIVE_CASES = [
    ("route_style_css",
     'X = http_request(server, "/static/style.css")\n', None),
    ("docstring_mentions_style_and_spec",
     '"""Talks about style.css and 30-UI-SPEC.md."""\n', None),
    ("comment_mentions_style_and_spec",
     "# style.css and 30-UI-SPEC.md\nX = 1\n", None),
    ("no_such_route_literal",
     'ROUTE = "/no-such-route"\n', None),
    ("png_under_server_assets",
     'X = os.path.join(REPO_ROOT, "server", "assets", "icon.png")\n', None),
    ("tmp_path_probe_write",
     '(tmp_path / "test_probe.py").write_text("...")\n', None),
    ("chmod_with_requires_non_root_decorator",
     "import os\n\n\n@requires_non_root\ndef test_x():\n    os.chmod(\"/tmp/x\", 0o644)\n", None),
    ("helpers_with_test_false_marker",
     "__test__ = False\nX = 1\n", "companion/test_something_helpers.py"),
    ("import_helpers_module",
     "import companion.test_config_page_helpers as cp\n"
     "from companion.test_browser_ux_helpers import seed_state_dir\n", None),
    ("served_css_parsed_structurally",
     "def test_x(server):\n    css = served_stylesheet(server)\n"
     "    assert 'color' in declarations_for(css, '.a')\n"
     "    for rule in css_rules(css):\n        assert not re.search('b', rule.selectors[0])\n", None),
    ("served_js_substring",
     "def test_x(server):\n    js = served_asset(server, '/static/a.js')\n    assert 'x' in js\n", None),
    ("style_route_headers",
     "def test_x(server):\n    status, headers, body = get(server, '/static/style.css')\n"
     "    assert 'text/css' in headers['Content-Type']\n", None),
    ("allowlisted_raw_character_scan",
     "def test_style_css_carries_no_stray_comment_terminator(css_text):\n"
     "    css_text = served_stylesheet(server)\n    css_text.startswith('*/', 0)\n",
     "companion/test_status_pages_07.py"),
]


@pytest.mark.parametrize(
    "rule,case_id,source,filename",
    _POSITIVE_CASES,
    ids=[case[1] for case in _POSITIVE_CASES],
)
def test_detector_flags_positive(rule, case_id, source, filename):
    fname = filename or ("synthetic_%s.py" % (case_id,))
    violations = scan_source(source, fname)
    rules_found = {v.rule for v in violations}
    assert rule in rules_found, (
        "expected rule %s to be flagged for case %r, got %r" % (rule, case_id, violations))


@pytest.mark.parametrize(
    "case_id,source,filename",
    _NEGATIVE_CASES,
    ids=[case[0] for case in _NEGATIVE_CASES],
)
def test_detector_accepts_negative(case_id, source, filename):
    fname = filename or ("synthetic_%s.py" % (case_id,))
    violations = scan_source(source, fname)
    assert violations == [], "expected no violations for case %r, got %r" % (case_id, violations)


@pytest.mark.parametrize("relpath", scanned_files(), ids=scanned_files())
def test_module_obeys_behaviour_over_source_rules(relpath):
    full_path = os.path.join(REPO_ROOT, relpath)
    with open(full_path, encoding="utf-8") as fh:
        source = fh.read()
    violations = scan_source(source, relpath)
    assert violations == [], "\n".join(
        "%s:%d %s %s" % (relpath, v.lineno, v.rule, v.detail) for v in violations)


@pytest.mark.parametrize("relpath,function", sorted(G11_ALLOWLIST), ids=[f for _, f in sorted(G11_ALLOWLIST)])
def test_g11_allowlist_entry_still_scans_raw_stylesheet_text(relpath, function):
    """Each G11 allowlist entry names a function that really does scan the
    served stylesheet's raw text, so a stale entry cannot linger and
    silently exempt a later rewrite of that function.
    """
    with open(os.path.join(REPO_ROOT, relpath), encoding="utf-8") as fh:
        tree = ast.parse(fh.read(), filename=relpath)
    taint = _ServedCssTaint(tree)
    assert function in taint.functions, "%s no longer defines %s" % (relpath, function)
    unallowed = taint.violations(relpath, allowlist={})
    fn = taint.functions[function]
    inside = [v for v in unallowed if fn.lineno <= v.lineno <= fn.end_lineno]
    assert inside, "%s::%s no longer scans raw stylesheet text; drop its allowlist entry" % (
        relpath, function)


def test_scanned_files_are_every_companion_test_module_but_the_guard():
    """No companion test module is exempt from the guard except this one."""
    on_disk = {
        os.path.join("companion", name)
        for name in os.listdir(_COMPANION_DIR)
        if name.startswith("test_") and name.endswith(".py")
    }
    assert set(scanned_files()) == (on_disk - {_GUARD_MODULE}) | {"companion/conftest.py"}


# The directories pytest collects tests from, each scanned for the
# pre-pytest runner shape (G8): an EXPECTED_CHECK_COUNT counter, a
# module-level check()/main(), or an `if __name__ == "__main__"` runner.
_RUNNER_SCAN_DIRS = ("server", "stub-server", "test-support", "companion", "deploy/tests")


def _test_files_under(reldir):
    full_dir = os.path.join(REPO_ROOT, reldir)
    return sorted(
        os.path.join(reldir, name)
        for name in os.listdir(full_dir)
        if name.startswith("test_") and name.endswith(".py")
    )


def test_no_legacy_runner_anywhere():
    """No test file in any collected directory keeps a hand-rolled runner:
    pytest discovery is the only way a test runs.
    """
    offenders = []
    for reldir in _RUNNER_SCAN_DIRS:
        for relpath in _test_files_under(reldir):
            if relpath == _GUARD_MODULE:
                continue
            with open(os.path.join(REPO_ROOT, relpath), encoding="utf-8") as fh:
                source = fh.read()
            for v in scan_source(source, relpath):
                if v.rule == "G8":
                    offenders.append("%s:%d %s" % (relpath, v.lineno, v.detail))
    assert offenders == [], "\n".join(offenders)
