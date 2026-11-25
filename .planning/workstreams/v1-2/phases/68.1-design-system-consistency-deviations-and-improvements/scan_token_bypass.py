"""Report hard-coded values in the companion that bypass the design tokens.

Re-run from the repository root:

    python3 -I .planning/workstreams/v1-2/phases/68.1-design-system-consistency-deviations-and-improvements/scan_token_bypass.py

Optional: --css-dir DIR reads style*.css from DIR instead of companion/static
(used to scan a copy of the stylesheets from another git ref); --summary
prints only the counts.

Categories reported, one line per finding:

  COLOUR     a #hex, rgb(), rgba(), hsl() or hsla() literal in a declaration
             that is not a token definition in the shared theme blocks of
             style.css (a token definition in an area sheet or inside a
             component rule is reported too)
  DURATION   a ms/s literal in a transition or animation declaration, or a
             motion-token-like custom property outside style.css :root
             (a literal 0s is not a finding)
  RADIUS     a px literal in border-radius; TOKEN-EXISTS when it equals a
             --radius-* value, otherwise NO-TOKEN (0, 1px, 2px, 3px and 50%
             forms are hairline or circle values and are not reported)
  SPACING    a px literal in padding, margin, gap, inset or a top/right/
             bottom/left offset; TOKEN-EXISTS when it equals a --space-*
             value, otherwise NO-TOKEN (0 to 3px are not reported)
  FONT-SIZE  a px literal in font-size; TOKEN-EXISTS when it equals a
             --font-*-size value, otherwise NO-TOKEN
  IMPORTANT  a declaration carrying !important
  INLINE     an inline style attribute (style="..."), setAttribute("style")
             or .style.cssText in companion Python sources (not tests) and
             companion/static/*.js
  JS-STYLE   a .style.<prop> = ... or .style.setProperty(...) call in
             companion/static/*.js (a script writing a style at run time)
"""
import glob
import os
import re
import sys

ROOT = os.getcwd()
STATIC = os.path.join(ROOT, "companion", "static")

COLOUR_RE = re.compile(r"#[0-9a-fA-F]{3,8}\b|\b(?:rgba?|hsla?)\(")
DURATION_RE = re.compile(r"(?<![\w.-])(\d*\.?\d+)(ms|s)\b")
PX_RE = re.compile(r"(?<![\w.#-])(-?\d*\.?\d+)px\b")
SPACING_PROPS = re.compile(
    r"^(?:padding|margin|gap|row-gap|column-gap|inset|top|right|bottom|left"
    r"|(?:padding|margin)-(?:top|right|bottom|left|inline|block)(?:-start|-end)?"
    r"|inset-(?:inline|block)(?:-start|-end)?)$")
HAIRLINE_MAX = 3


def strip_comments(text):
    """Remove /* */ comments but keep every newline so line numbers hold."""
    return re.sub(
        r"/\*.*?\*/", lambda m: "\n" * m.group(0).count("\n"), text, flags=re.S)


def parse_declarations(text):
    """Yield (line, header_stack, prop, value) for every declaration."""
    stack = []
    buf = []
    line = 1
    start_line = 1
    in_str = None
    paren = 0
    for ch in text:
        if in_str:
            buf.append(ch)
            if ch == in_str:
                in_str = None
        elif ch in "\"'":
            in_str = ch
            buf.append(ch)
        elif ch == "(":
            paren += 1
            buf.append(ch)
        elif ch == ")":
            paren -= 1
            buf.append(ch)
        elif ch == "{" and paren == 0:
            stack.append(" ".join("".join(buf).split()))
            buf = []
        elif ch in ";}" and paren == 0:
            decl = "".join(buf).strip()
            buf = []
            if decl and ":" in decl and not decl.startswith("@"):
                prop, _, value = decl.partition(":")
                prop = prop.strip()
                if re.fullmatch(r"-{0,2}[\w-]+", prop):
                    yield start_line, list(stack), prop, " ".join(value.split())
            if ch == "}" and stack:
                stack.pop()
        else:
            if not ch.isspace() and not any(not c.isspace() for c in buf):
                start_line = line
            buf.append(ch)
        if ch == "\n":
            line += 1


def token_values(css_dir):
    """Read the px values of the radius, space and font-size tokens."""
    with open(os.path.join(css_dir, "style.css"), encoding="utf-8") as handle:
        text = strip_comments(handle.read())
    tokens = {"RADIUS": {}, "SPACING": {}, "FONT-SIZE": {}}
    for _line, stack, prop, value in parse_declarations(text):
        if not stack or not stack[0].startswith(":root"):
            continue
        match = re.fullmatch(r"(\d+)px", value)
        if not match:
            continue
        if prop.startswith("--radius-"):
            tokens["RADIUS"].setdefault(match.group(1), prop)
        elif prop.startswith("--space-"):
            tokens["SPACING"].setdefault(match.group(1), prop)
        elif re.fullmatch(r"--font-[\w-]*size", prop):
            tokens["FONT-SIZE"].setdefault(match.group(1), prop)
    return tokens


def is_shared_theme_block(stack):
    head = stack[0] if stack else ""
    return (head.startswith(":root") or head.startswith("html[data-ui-theme")
            or head.startswith("@media (prefers-color-scheme: dark)"))


def scan_css(css_dir, tokens):
    findings = []
    for path in sorted(glob.glob(os.path.join(css_dir, "style*.css"))):
        name = os.path.basename(path)
        with open(path, encoding="utf-8") as handle:
            text = strip_comments(handle.read())
        for line, stack, prop, value in parse_declarations(text):
            selector = stack[-1] if stack else ""
            in_reduce = any("prefers-reduced-motion: reduce" in head
                            for head in stack)
            where = "%s:%d" % (name, line)
            note = "reduced-motion block" if in_reduce else ""
            if prop.startswith("--"):
                shared = name == "style.css" and is_shared_theme_block(stack)
                if COLOUR_RE.search(value) and not shared:
                    findings.append(("COLOUR", where, selector, prop, value,
                                     "NO-TOKEN", note))
                if (prop.startswith("--motion") and name != "style.css"
                        and DURATION_RE.search(value)):
                    findings.append(("DURATION", where, selector, prop, value,
                                     "NO-TOKEN", note))
                continue
            if COLOUR_RE.search(value):
                findings.append(("COLOUR", where, selector, prop, value,
                                 "NO-TOKEN", note))
            if (prop.startswith(("transition", "animation"))
                    and prop != "animation-name"):
                for match in DURATION_RE.finditer(value):
                    if match.group(1) in ("0", "0.0") and match.group(2) == "s":
                        continue
                    findings.append(("DURATION", where, selector, prop, value,
                                     "NO-TOKEN", note))
                    break
            if "!important" in value:
                findings.append(("IMPORTANT", where, selector, prop, value,
                                 "", note))
            kind = None
            if prop == "border-radius" or re.fullmatch(
                    r"border-(?:top|bottom)-(?:left|right)-radius", prop):
                kind = "RADIUS"
            elif SPACING_PROPS.match(prop):
                kind = "SPACING"
            elif prop == "font-size":
                kind = "FONT-SIZE"
            if kind:
                for match in PX_RE.finditer(value):
                    number = match.group(1)
                    if kind != "FONT-SIZE" and abs(float(number)) <= HAIRLINE_MAX:
                        continue
                    if number.lstrip("-") in tokens[kind] and not number.startswith("-"):
                        verdict = "TOKEN-EXISTS " + tokens[kind][number]
                    else:
                        verdict = "NO-TOKEN"
                    findings.append((kind, where, selector, prop, value,
                                     verdict, note))
                    break
    return findings


INLINE_RE = re.compile(
    r"""style\s*=\s*\\?["']|setAttribute\(\s*["']style["']|\.style\.cssText""")
JS_STYLE_RE = re.compile(r"\.style\.(?:setProperty\(|[a-zA-Z]+\s*=[^=])")


def scan_inline():
    findings = []
    sources = [p for p in glob.glob(os.path.join(ROOT, "companion", "*.py"))
               if not os.path.basename(p).startswith("test_")]
    sources += [p for p in glob.glob(
        os.path.join(ROOT, "companion", "pages", "**", "*.py"), recursive=True)
        if not os.path.basename(p).startswith("test_")]
    sources += glob.glob(os.path.join(STATIC, "*.js"))
    for path in sorted(sources):
        with open(path, encoding="utf-8") as handle:
            for number, text in enumerate(handle, 1):
                if INLINE_RE.search(text):
                    findings.append((
                        "INLINE", "%s:%d" % (os.path.relpath(path, ROOT), number),
                        "", "style", text.strip()[:110], "", ""))
                elif path.endswith(".js") and JS_STYLE_RE.search(text):
                    findings.append((
                        "JS-STYLE", "%s:%d" % (os.path.relpath(path, ROOT), number),
                        "", "style", text.strip()[:110], "", ""))
    return findings


def main(argv):
    css_dir = STATIC
    summary_only = "--summary" in argv
    if "--css-dir" in argv:
        css_dir = os.path.abspath(argv[argv.index("--css-dir") + 1])
    tokens = token_values(css_dir)
    findings = scan_css(css_dir, tokens)
    if css_dir == STATIC:
        findings += scan_inline()
    if not summary_only:
        print("%-10s %-28s %-14s %s" % ("CATEGORY", "WHERE", "PROPERTY", "VALUE -> VERDICT"))
        for cat, where, selector, prop, value, verdict, note in findings:
            print("%-10s %-28s %-14s %s -> %s%s | %s" % (
                cat, where, prop, value[:90], verdict or "-",
                " [%s]" % note if note else "", selector[:70]))
    counts = {}
    for cat, _where, _sel, _prop, _val, verdict, _note in findings:
        key = (cat, verdict.split(" ")[0] if verdict else "-")
        counts[key] = counts.get(key, 0) + 1
    print()
    print("SUMMARY (category, verdict, count)")
    for key in sorted(counts):
        print("  %-10s %-13s %d" % (key[0], key[1], counts[key]))
    print("  TOTAL %d" % len(findings))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
