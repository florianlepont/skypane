"""Served JavaScript without its comments.

The scripts under `companion/static/` keep their long explanatory comments in
the source; the browser has no use for them, and they are a third of the
bytes. `strip_comments()` removes line and block comments and the blank lines
they leave, and nothing else: string, template and regular-expression
literals are copied verbatim (a `//` inside `"http://x"` or a `/*` inside a
regex is not a comment), and indentation is kept, so a multi-line template
literal reads the same. A block comment that spans lines leaves a newline
behind, so automatic semicolon insertion sees the same line breaks.

The result depends only on the input bytes, so the version token derived
from it is stable. The lexer is deliberately conservative: where a `/` could
be a division or the start of a regular expression it decides from the
previous token the way JavaScript's own grammar does for code written in this
repository's style.
"""

_IDENT = frozenset(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_$")
# After one of these words a "/" starts a regular expression, not a division.
_REGEX_KEYWORDS = frozenset((
    "return", "typeof", "case", "do", "else", "in", "of", "new", "delete", "void",
    "throw", "instanceof", "yield", "await"))
# After one of these characters a "/" starts a regular expression.
_REGEX_AFTER = frozenset("(,=:[!&|?{};+-*%<>~^")


def _skip_string(text, index, quote):
    """The index just past the string literal that opens at `index`."""
    end = len(text)
    index += 1
    while index < end:
        char = text[index]
        if char == "\\":
            index += 2
            continue
        index += 1
        if char == quote or char == "\n":
            break
    return index


def _skip_regex(text, index):
    """The index just past the regular-expression literal opening at `index`,
    flags included."""
    end = len(text)
    index += 1
    in_class = False
    while index < end:
        char = text[index]
        if char == "\\":
            index += 2
            continue
        index += 1
        if char == "\n":
            break
        if char == "[":
            in_class = True
        elif char == "]":
            in_class = False
        elif char == "/" and not in_class:
            while index < end and text[index] in _IDENT:
                index += 1
            break
    return index


def _previous_word(text, end):
    """The identifier ending just before `end` (possibly empty)."""
    start = end
    while start > 0 and text[start - 1] in _IDENT:
        start -= 1
    return text[start:end]


def _regex_allowed(code):
    """Whether a "/" after the code written so far starts a regular expression."""
    stripped = code.rstrip()
    if not stripped:
        return True
    last = stripped[-1]
    if last in _REGEX_AFTER:
        return True
    if last in _IDENT:
        return _previous_word(stripped, len(stripped)) in _REGEX_KEYWORDS
    return False


def strip_comments(source):
    """`source` (text) without comments and the blank lines they leave."""
    text = source
    end = len(text)
    out = []
    # Template literals in progress: each entry is the count of braces opened
    # inside its current `${ ... }`.
    templates = []
    index = 0
    line_start = 0  # index in `out` where the current output line starts

    def current_line_blank():
        return "".join(out[line_start:]).strip() == ""

    while index < end:
        char = text[index]
        nxt = text[index + 1] if index + 1 < end else ""
        if char == "/" and nxt == "/":
            newline = text.find("\n", index)
            index = end if newline < 0 else newline
            if current_line_blank():
                # A whole-line comment: the line goes away with its newline.
                del out[line_start:]
                if index < end:
                    index += 1
            else:
                while out and out[-1] in (" ", "\t"):
                    out.pop()
            continue
        if char == "/" and nxt == "*":
            close = text.find("*/", index + 2)
            stop = end if close < 0 else close + 2
            had_newline = "\n" in text[index:stop]
            index = stop
            if current_line_blank():
                rest = text.find("\n", index)
                tail = text[index:end if rest < 0 else rest]
                if tail.strip() == "":
                    # Nothing else on the line it started or ended on: drop the line.
                    del out[line_start:]
                    index = end if rest < 0 else rest + 1
                    continue
            if had_newline:
                while out and out[-1] in (" ", "\t"):
                    out.pop()
                out.append("\n")
                line_start = len(out)
            else:
                out.append(" ")
            continue
        if char in "\"'":
            stop = _skip_string(text, index, char)
            out.append(text[index:stop])
            index = stop
            continue
        if char == "`":
            out.append(char)
            index += 1
            index = _copy_template(text, index, out, templates)
            continue
        if char == "/" and _regex_allowed("".join(out[-40:]) if out else ""):
            stop = _skip_regex(text, index)
            out.append(text[index:stop])
            index = stop
            continue
        if templates and char == "{":
            templates[-1] += 1
        elif templates and char == "}":
            if templates[-1] == 0:
                templates.pop()
                out.append(char)
                index += 1
                index = _copy_template(text, index, out, templates)
                continue
            templates[-1] -= 1
        out.append(char)
        index += 1
        if char == "\n":
            line_start = len(out)
    return "".join(out)


def _copy_template(text, index, out, templates):
    """Copy template-literal text from `index` up to the closing backtick or
    the next `${` (which pushes onto `templates` and returns to code)."""
    end = len(text)
    start = index
    while index < end:
        char = text[index]
        if char == "\\":
            index += 2
            continue
        if char == "`":
            index += 1
            out.append(text[start:index])
            return index
        if char == "$" and text[index + 1:index + 2] == "{":
            index += 2
            out.append(text[start:index])
            templates.append(0)
            return index
        index += 1
    out.append(text[start:end])
    return end


def minify_js(payload):
    """The served form of a script (bytes in, bytes out)."""
    return strip_comments(payload.decode("utf-8")).encode("utf-8")
