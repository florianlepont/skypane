"""Stdlib-only structural parsers for the markup and stylesheets
`companion/app.py` serves, plus a small JS comment/string stripper.

These helpers operate on SERVED bytes - text a test fetches over HTTP with
`test-support/companion_app_server.py`'s `get()` / `served_stylesheet()` /
`served_asset()` - never on a file opened from disk (TST-12). A migrated
companion test asserts on the parsed structure, the resolved declaration,
or the delivery contract of what the server actually sent, not on the
source text that produced it.

Three independent pieces:

- `parse_html()` / `Node`: a tiny DOM over `html.parser.HTMLParser`, with
  `select()` supporting the CSS-selector subset every migrated test needs
  (tag, `.class`, `#id`, `[attr]`, `[attr="v"]`, the descendant combinator,
  the child combinator `>`). An unsupported selector raises `ValueError`
  rather than silently matching nothing.
- `css_rules()` and friends: a brace/string-aware CSS tokenizer that
  understands nested at-rules (`@media`, `@supports`), comma-separated
  selector lists, `@keyframes` (recorded separately, never returned as a
  rule), and declaration values that themselves contain `;`, `}`, commas
  or nested parens (a quoted string, or `color-mix(in srgb, ...)`).
- `strip_js_comments_and_strings()`: a small state machine that removes
  `//` and `/* */` comments and every quoted/backtick string, so a
  behaviour assertion over served JS never depends on a comment's
  wording. Regex literals are out of scope: a `/` that starts a regex is
  not distinguished from a division operator, so a source relying on a
  `/regex/` literal may be mis-tokenized by this function.
"""

import re
from html.parser import HTMLParser
from typing import NamedTuple

__all__ = [
    "Node",
    "parse_html",
    "css_rules",
    "declarations_for",
    "rules_with_selector",
    "rule_indices",
    "keyframes",
    "at_rule_blocks",
    "custom_properties",
    "strip_js_comments_and_strings",
]


# --- HTML ------------------------------------------------------------------

# HTML5 void elements: never pushed onto the open-element stack, so a
# following sibling attaches to the void element's own parent instead of
# being (wrongly) nested inside it.
_VOID_ELEMENTS = frozenset({
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "param", "source", "track", "wbr",
})


class Node:
    """A parsed HTML element, or the synthetic ``#document`` root
    `parse_html()` returns. ``children`` holds a mix of child `Node`
    instances and raw text `str` fragments, in document order.
    """

    def __init__(self, tag, attrs=None, parent=None):
        self.tag = tag
        self.attrs = dict(attrs or {})
        self.parent = parent
        self.children = []

    def _descendants(self):
        for child in self.children:
            if isinstance(child, Node):
                yield child
                yield from child._descendants()

    def text(self):
        """All descendant text, whitespace collapsed to single spaces and
        stripped at both ends.
        """
        parts = []

        def walk(node):
            for child in node.children:
                if isinstance(child, str):
                    parts.append(child)
                else:
                    walk(child)

        walk(self)
        return re.sub(r"\s+", " ", "".join(parts)).strip()

    def find_all(self, tag=None, cls=None, attrs=None):
        """Every descendant matching `tag` (exact tag name), `cls` (a
        single class name that must be present in the element's `class`
        attribute) and/or `attrs` (a dict every entry of which must match
        exactly), in document order.
        """
        results = []
        for node in self._descendants():
            if tag is not None and node.tag != tag:
                continue
            if cls is not None:
                node_classes = node.attrs.get("class", "").split()
                if cls not in node_classes:
                    continue
            if attrs is not None:
                if not all(node.attrs.get(k) == v for k, v in attrs.items()):
                    continue
            results.append(node)
        return results

    def find(self, tag=None, cls=None, attrs=None):
        """The first descendant matching, or raises `LookupError`."""
        results = self.find_all(tag=tag, cls=cls, attrs=attrs)
        if not results:
            raise LookupError(
                "no element matching tag=%r cls=%r attrs=%r" % (tag, cls, attrs))
        return results[0]

    def select(self, selector):
        """Every descendant matching `selector` (see module docstring for
        the supported subset), in document order. Raises `ValueError` for
        an unsupported selector - never a silent empty list.
        """
        return _select(self, selector)

    def select_one(self, selector):
        """The first descendant matching `selector`, or raises
        `LookupError`.
        """
        results = self.select(selector)
        if not results:
            raise LookupError("no element matching selector %r" % (selector,))
        return results[0]

    def __repr__(self):
        return "<Node %s %r>" % (self.tag, self.attrs)


class _TreeBuilder(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node("#document")
        self._stack = [self.root]

    def handle_starttag(self, tag, attrs):
        node = Node(tag, attrs, parent=self._stack[-1])
        self._stack[-1].children.append(node)
        if tag not in _VOID_ELEMENTS:
            self._stack.append(node)

    def handle_startendtag(self, tag, attrs):
        # An explicitly self-closed tag (<img ... />) is never pushed,
        # exactly like a void element.
        node = Node(tag, attrs, parent=self._stack[-1])
        self._stack[-1].children.append(node)

    def handle_endtag(self, tag):
        # Close back to (and including) the nearest matching open tag. An
        # unmatched end tag is ignored. An unclosed tag is simply never
        # popped - its children are already attached, so it "closes at
        # its parent's end" for free once feed()/close() finishes.
        for i in range(len(self._stack) - 1, 0, -1):
            if self._stack[i].tag == tag:
                del self._stack[i:]
                return

    def handle_data(self, data):
        if data:
            self._stack[-1].children.append(data)


def parse_html(text):
    """Parse `text` (served HTML) into a `Node` tree. The returned root's
    `tag` is the synthetic ``"#document"``.
    """
    builder = _TreeBuilder()
    builder.feed(text)
    builder.close()
    return builder.root


# --- HTML selector engine ---------------------------------------------------

_SIMPLE_SELECTOR_RE = re.compile(
    r"^(?P<tag>[A-Za-z][A-Za-z0-9]*|\*)?"
    r"(?P<qualifiers>(?:\.[\w-]+|#[\w-]+|\[[\w-]+(?:=(?:\"[^\"]*\"|'[^']*'))?\])*)$"
)
_QUALIFIER_RE = re.compile(
    r"\.([\w-]+)|#([\w-]+)|\[([\w-]+)(?:=(?:\"([^\"]*)\"|'([^']*)'))?\]"
)


def _parse_simple_selector(token):
    match = _SIMPLE_SELECTOR_RE.match(token)
    if not match or (not match.group("tag") and not match.group("qualifiers")):
        raise ValueError("unsupported selector fragment: %r" % (token,))
    classes = []
    id_ = None
    attr_conditions = []
    # finditer (not findall) so a non-participating group reads as None,
    # not '' - findall would make a bare `[attr]` indistinguishable from
    # `[attr=""]`.
    for qualifier_match in _QUALIFIER_RE.finditer(match.group("qualifiers")):
        cls, idv, aname, aval_d, aval_s = qualifier_match.groups()
        if cls:
            classes.append(cls)
        elif idv:
            id_ = idv
        elif aname:
            value = aval_d if aval_d is not None else aval_s
            attr_conditions.append((aname, value))
    return {
        "tag": match.group("tag"),
        "classes": classes,
        "id": id_,
        "attrs": attr_conditions,
    }


def _matches_simple(node, simple):
    if simple["tag"] and simple["tag"] != "*" and node.tag != simple["tag"]:
        return False
    if simple["classes"]:
        node_classes = node.attrs.get("class", "").split()
        if not all(c in node_classes for c in simple["classes"]):
            return False
    if simple["id"] is not None and node.attrs.get("id") != simple["id"]:
        return False
    for name, value in simple["attrs"]:
        if name not in node.attrs:
            return False
        if value is not None and node.attrs[name] != value:
            return False
    return True


def _tokenize_selector(selector):
    selector = selector.strip()
    if not selector:
        raise ValueError("empty selector: %r" % (selector,))
    raw_parts = re.split(r"(>)", selector)
    tokens = []
    pending_combinator = None
    for raw in raw_parts:
        raw = raw.strip()
        if not raw:
            continue
        if raw == ">":
            pending_combinator = "child"
            continue
        for part in raw.split():
            comb = pending_combinator or ("descendant" if tokens else None)
            tokens.append((comb, part))
            pending_combinator = None
    if not tokens:
        raise ValueError("empty selector: %r" % (selector,))
    return tokens


def _select(root, selector):
    tokens = _tokenize_selector(selector)
    simples = [(comb, _parse_simple_selector(tok)) for comb, tok in tokens]

    first_simple = simples[0][1]
    matched = [n for n in root._descendants() if _matches_simple(n, first_simple)]

    for comb, simple in simples[1:]:
        next_matched = []
        seen = set()
        for n in matched:
            pool = (
                [c for c in n.children if isinstance(c, Node)]
                if comb == "child" else list(n._descendants())
            )
            for cand in pool:
                if _matches_simple(cand, simple) and id(cand) not in seen:
                    seen.add(id(cand))
                    next_matched.append(cand)
        matched = next_matched

    return matched


# --- CSS ---------------------------------------------------------------

class Rule(NamedTuple):
    selectors: tuple
    declarations: list
    at_rules: tuple


def _normalise(text):
    return re.sub(r"\s+", " ", text.strip())


def _strip_css_comments(text):
    """Remove every ``/* ... */`` comment, honoring quoted strings so a
    comment marker inside a string is left alone.
    """
    out = []
    i, n = 0, len(text)
    in_string = None
    while i < n:
        ch = text[i]
        if in_string:
            out.append(ch)
            if ch == "\\" and i + 1 < n:
                out.append(text[i + 1])
                i += 2
                continue
            if ch == in_string:
                in_string = None
            i += 1
            continue
        if ch in ("\"", "'"):
            in_string = ch
            out.append(ch)
            i += 1
            continue
        if ch == "/" and i + 1 < n and text[i + 1] == "*":
            end = text.find("*/", i + 2)
            i = n if end == -1 else end + 2
            continue
        out.append(ch)
        i += 1
    return "".join(out)


def _extract_block_body(text, start):
    """`text[start]` is the character right after an opening ``{``.
    Returns ``(body_text, index_after_the_matching_closing_"}")``,
    honoring quoted strings and further-nested braces.
    """
    depth = 1
    in_string = None
    i, n = start, len(text)
    buf = []
    while i < n:
        ch = text[i]
        if in_string:
            buf.append(ch)
            if ch == "\\" and i + 1 < n:
                buf.append(text[i + 1])
                i += 2
                continue
            if ch == in_string:
                in_string = None
            i += 1
            continue
        if ch in ("\"", "'"):
            in_string = ch
            buf.append(ch)
            i += 1
            continue
        if ch == "{":
            depth += 1
            buf.append(ch)
            i += 1
            continue
        if ch == "}":
            depth -= 1
            if depth == 0:
                return "".join(buf), i + 1
            buf.append(ch)
            i += 1
            continue
        buf.append(ch)
        i += 1
    return "".join(buf), i


def _tokenize_css_top_level(text):
    """Splits `text` (comments already stripped) into top-level
    ``("stmt", prelude)`` / ``("block", prelude, body)`` tokens, honoring
    quoted strings so a quoted ``;``/``{``/``}`` never acts as a
    delimiter.
    """
    tokens = []
    buf = []
    i, n = 0, len(text)
    in_string = None
    while i < n:
        ch = text[i]
        if in_string:
            buf.append(ch)
            if ch == "\\" and i + 1 < n:
                buf.append(text[i + 1])
                i += 2
                continue
            if ch == in_string:
                in_string = None
            i += 1
            continue
        if ch in ("\"", "'"):
            in_string = ch
            buf.append(ch)
            i += 1
            continue
        if ch == "{":
            prelude = "".join(buf).strip()
            buf = []
            body, i = _extract_block_body(text, i + 1)
            tokens.append(("block", prelude, body))
            continue
        if ch == ";":
            stmt = "".join(buf).strip()
            buf = []
            if stmt:
                tokens.append(("stmt", stmt))
            i += 1
            continue
        buf.append(ch)
        i += 1
    tail = "".join(buf).strip()
    if tail:
        tokens.append(("stmt", tail))
    return tokens


def _split_selector_list(prelude):
    return tuple(_normalise(part) for part in prelude.split(",") if part.strip())


def _parse_declarations(body):
    declarations = []
    for token in _tokenize_css_top_level(body):
        if token[0] != "stmt":
            continue
        content = token[1]
        if ":" not in content:
            continue
        prop, _, value = content.partition(":")
        declarations.append((prop.strip(), value.strip()))
    return declarations


def _walk_css(tokens, at_rules, rules, keyframe_names, blocks):
    for token in tokens:
        if token[0] == "stmt":
            continue
        _, prelude, body = token
        if prelude.startswith("@"):
            blocks.append(_normalise(prelude))
            at_keyword = prelude.split(None, 1)[0].lower()
            if at_keyword == "@keyframes":
                keyframe_names.add(prelude[len("@keyframes"):].strip())
                continue
            inner_tokens = _tokenize_css_top_level(body)
            _walk_css(inner_tokens, at_rules + (_normalise(prelude),), rules, keyframe_names, blocks)
        else:
            rules.append(Rule(
                selectors=_split_selector_list(prelude),
                declarations=_parse_declarations(body),
                at_rules=at_rules,
            ))


class _ParsedCSS(NamedTuple):
    rules: list
    keyframe_names: set
    at_rule_blocks: list


def _parse_css(css_text):
    stripped = _strip_css_comments(css_text)
    tokens = _tokenize_css_top_level(stripped)
    rules = []
    keyframe_names = set()
    blocks = []
    _walk_css(tokens, (), rules, keyframe_names, blocks)
    return _ParsedCSS(rules=rules, keyframe_names=keyframe_names, at_rule_blocks=blocks)


def css_rules(css_text):
    """Every non-``@keyframes`` rule in `css_text`, as a list of `Rule`.
    A `Rule.selectors` entry is exactly one comma-separated selector,
    whitespace-normalised. `Rule.at_rules` is the tuple of enclosing
    at-rule preludes (e.g. ``("@media (max-width: 959.98px)",)``),
    whitespace-normalised, outermost first.
    """
    return _parse_css(css_text).rules


def declarations_for(css_text, selector, at_rules=()):
    """Merge, in source order, the declarations of every rule whose
    selectors include `selector` exactly and whose `at_rules` tuple
    equals `at_rules` (last declaration for a given property wins).
    Returns ``{}`` when `selector` exists somewhere in `css_text` but not
    under this `at_rules` context. Raises `KeyError` when `selector`
    matches no rule anywhere in `css_text`.
    """
    selector = _normalise(selector)
    at_rules = tuple(_normalise(a) for a in at_rules)
    rules = css_rules(css_text)
    if not any(selector in rule.selectors for rule in rules):
        raise KeyError(selector)
    merged = {}
    for rule in rules:
        if selector in rule.selectors and rule.at_rules == at_rules:
            for prop, value in rule.declarations:
                merged[prop] = value
    return merged


def rules_with_selector(css_text, selector):
    """Every rule (in any at-rule context) whose selectors include
    `selector` exactly.
    """
    selector = _normalise(selector)
    return [rule for rule in css_rules(css_text) if selector in rule.selectors]


def rule_indices(css_text, selector, at_rules=None):
    """Source-order positions, as indices into `css_rules(css_text)`, of
    every rule whose selectors include `selector` exactly. With `at_rules`
    given, only rules in exactly that at-rule context count. Comparing two
    selectors' indices answers "which rule comes later", the tie-breaker
    between declarations of equal specificity.
    """
    selector = _normalise(selector)
    if at_rules is not None:
        at_rules = tuple(_normalise(a) for a in at_rules)
    return [
        index for index, rule in enumerate(css_rules(css_text))
        if selector in rule.selectors and (at_rules is None or rule.at_rules == at_rules)
    ]


def keyframes(css_text):
    """The set of ``@keyframes`` names declared in `css_text`."""
    return set(_parse_css(css_text).keyframe_names)


def at_rule_blocks(css_text):
    """The whitespace-normalised prelude of every at-rule block in
    `css_text` (``@media``, ``@supports``, ``@keyframes``,
    ``@starting-style``, ...), in source order, nested blocks included and
    repeats kept, so a caller can count how many separate blocks share a
    prelude. Comments are ignored.
    """
    return list(_parse_css(css_text).at_rule_blocks)


def custom_properties(css_text, selector=":root", at_rules=()):
    """The subset of `declarations_for(css_text, selector, at_rules)`
    whose property name starts with ``--``. Returns ``{}`` (rather than
    raising) when `selector` matches no rule at all.
    """
    try:
        decls = declarations_for(css_text, selector, at_rules=at_rules)
    except KeyError:
        return {}
    return {prop: value for prop, value in decls.items() if prop.startswith("--")}


# --- JS ---------------------------------------------------------------

def strip_js_comments_and_strings(js):
    """Remove every ``//`` line comment, ``/* */`` block comment, and
    every single/double-quoted or backtick-delimited string/template
    literal from `js`. See the module docstring for the regex-literal
    caveat.
    """
    out = []
    i, n = 0, len(js)
    while i < n:
        two = js[i:i + 2]
        if two == "//":
            end = js.find("\n", i + 2)
            i = n if end == -1 else end
            continue
        if two == "/*":
            end = js.find("*/", i + 2)
            i = n if end == -1 else end + 2
            continue
        ch = js[i]
        if ch in ("\"", "'", "`"):
            quote = ch
            i += 1
            while i < n:
                if js[i] == "\\" and i + 1 < n:
                    i += 2
                    continue
                if js[i] == quote:
                    i += 1
                    break
                i += 1
            continue
        out.append(ch)
        i += 1
    return "".join(out)
