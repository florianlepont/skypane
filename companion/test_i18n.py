#!/usr/bin/env python3
"""Contract harness for companion/i18n.py, companion/prefs.py and the
companion/i18n_fr/ catalogue package (D-01..D-04, 20-01-PLAN.md
Task 1), plus D-08's completeness/dead-translation/render/D-09
mechanical checks (20-12-PLAN.md Task 1).

Covers: t_lang()'s round-trip and fallback behaviour, t()'s own
per-request resolution through prefs.set_request_prefs(), prefs'
membership-tested degrade-to-default contract, the catalogue's
completeness against its own sibling modules, a value-shape/no-dead-
translation spot check, a source-level import-boundary check on
i18n.py/prefs.py, and (20-12-PLAN.md Task 1) the phase-closing D-08
guard: a mechanical `ast`-based scan of the D-05 page-module set
proving every user-visible string has a French catalogue entry (Check
1) and every catalogue entry is actually read by some scanned source
(Check 2), a real render of every page in French against a running
service (Check 3), and D-09's two mechanical copy rules — the
typographic apostrophe and the non-breaking space before ":;?!"
(Check 4).

Stdlib-only (ast, os, re, sys). No pytest.

Usage:
    server/.venv/bin/python3 companion/test_i18n.py
"""
import ast
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import companion.i18n as i18n  # noqa: E402
import companion.i18n_fr as i18n_fr  # noqa: E402
import companion.i18n_fr.common as i18n_fr_common  # noqa: E402
import companion.i18n_fr.nav as i18n_fr_nav  # noqa: E402
import companion.i18n_fr.registry as i18n_fr_registry  # noqa: E402
import companion.prefs as prefs  # noqa: E402

# 20-12-PLAN.md Task 1
EXPECTED_CHECK_COUNT = 24
# 21-01-PLAN.md Task 1: -2 (the two prefs mode-membership checks,
# _check_prefs_unknown_mode_leaves_simple_mode_false and
# _check_prefs_simple_mode_true_for_simple, are deleted along with
# prefs.simple_mode()/set_request_prefs()'s mode= parameter, D-17).
EXPECTED_CHECK_COUNT = 22


# ==========================================================================
# D-08's mechanical completeness/dead-translation scanner (20-12-PLAN.md
# Task 1) — an ast.parse()-based scan, never an import of the scanned
# module (T-20-33: a scan must have no side effect on the app).
#
# The D-05 scan-target set: every page module (home/config/health/
# history/airlines) plus companion/layout.py and companion/auth.py.
# companion/app.py is deliberately NOT scanned (it sits outside the
# page-module boundary companion/pages/__init__.py documents); the
# small, stable set of strings it renders through i18n.t() for the
# pre-session login/404 pages is instead a short, documented exception
# list for Check 2 below, exactly as this Task's own spec allows ("one
# documented exception list for the strings that are legitimately
# owned elsewhere").
#
# What counts as a "producible" string, found by walking each module's
# source with `ast`:
#   (a) every string literal assigned directly to a name that looks
#       like a module constant — one or more leading underscores (this
#       codebase's own "private module constant" convention, e.g.
#       health_page._CORROBORATION_ROWS) followed by an UPPERCASE
#       start — including a `"a" + OTHER` concatenation or a
#       `TEMPLATE % (...)` formatting fully resolvable from constants
#       already seen earlier in the same file (source order), exactly
#       how Python itself would evaluate it at import time (never by
#       importing the module and reading the resulting attribute).
#   (b) every string found inside an ALL_CAPS-or-leading-underscore
#       dict literal's OWN values (including the trailing element of a
#       tuple-shaped value, e.g. `_CORROBORATION_LABELS`' `(status,
#       label)` pairs) — but ONLY for a dict actually proven to feed a
#       real `i18n.t()`/`i18n.t_lang()` call (by Name reference inside
#       that call's argument expression, or as the object of a
#       `.get(key, DEFAULT)` whose result is unpacked into more than
#       one name) — never a blind sweep of every dict in the file,
#       which would demand a catalogue entry for CSS-class/id lookup
#       tables that never reach a translation call at all.
#   (c) every literal or statically-resolvable argument actually passed
#       to `i18n.t()`/`i18n.t_lang()` anywhere in the module — a bare
#       literal (`i18n.t("Close")`), a Name resolved via (a)/(b) above,
#       a `NAME[<int>]`/`NAME.get(key, "literal")` lookup into a known
#       constant, or a `for x in TABLE` / `for a, b in zip(TABLE_A,
#       TABLE_B)` loop variable resolved back to TABLE's own matching
#       position.
#
# Five explicit, named exclusion rules keep the mechanical scan from
# demanding a translation for something that is not language content:
#   - route-or-static-path: starts with "/" or ends in a static-asset
#     extension (.js/.png/.css/.ico/.svg) — a URL, not prose.
#   - html-markup-or-comment: the value itself IS markup (starts with
#     "<") — a whole <link>/<svg> literal or an HTML comment marker.
#   - lowercase-identifier (rule (a) only): a bare token with no space,
#     matching this codebase's own convention for a flash key, a field/
#     query-param name, a checkbox/signal sentinel value, a CSS class/
#     id, or an aria-role token — never applied to rule (b)/(c), where a
#     bare lowercase English NOUN (e.g. "warning") is exactly what
#     get()'s own into-a-t()-call values legitimately look like.
#   - hyphenated-lowercase-identifier (rule (b) only): a dict value
#     that is itself a CSS class/id fragment (kebab-case, e.g.
#     "dot--ok") — the one shape rule (a)'s narrower lowercase-
#     identifier rule would miss (a leading "--" is not itself a valid
#     identifier start).
#   - css-class-list (rule (a) only): a space-joined value where every
#     token is its own hyphenated identifier (e.g. "text-label cell-
#     unresolved-link") — a multi-class attribute value, never a real
#     English phrase (which never joins two hyphenated words with a
#     bare space in this codebase's own copy).
#   - uppercase-code: no lowercase letter at all (env-var names, the
#     "__N__" client-side substitution token, ICAO/hex/callsign
#     placeholder examples like "AFR1234") — an identifier or example
#     code, never prose.
#   - no-letters (after stripping "%s"/"%d"): pure punctuation/spacing
#     with nothing for a translator to translate (e.g. "≈ %s").
#   - python-keyword-sentinel: the literal spellings "True"/"False"/
#     "None" — history_db's own on-disk corroboration vocabulary,
#     stored as a string but never displayed (its own comment in
#     health_page.py names this explicitly).
#   - empty-or-blank: nothing to translate.
_SCAN_RELATIVE_PATHS = (
    "pages/home_page.py",
    "pages/config_page.py",
    "pages/health_page.py",
    "pages/history_page.py",
    "pages/airlines_page.py",
    "layout.py",
    "auth.py",
)

_ALL_CAPS_NAME_RE = re.compile(r"^_*[A-Z][A-Z0-9_]*$")
_LOWERCASE_IDENTIFIER_RE = re.compile(r"^[a-z0-9_][a-z0-9_-]*$")
_HYPHENATED_IDENTIFIER_RE = re.compile(r"^[a-z0-9_-]+$")
_UPPERCASE_CODE_RE = re.compile(r"^[A-Z0-9_]+$")
_HAS_LETTER_RE = re.compile(r"[^\W\d_]", re.UNICODE)
_FORMAT_SPEC_RE = re.compile(r"%[sd]")
_PY_KEYWORD_LITERALS = {"True", "False", "None"}

# Check 2's documented exception list, part 1: companion/app.py's own
# pre-session login/404 copy — app.py sits outside the D-05 AST-scan
# target set (a page module may never import another page module, and
# app.py is neither a page module nor layout.py/auth.py), but Check 3
# below exercises both pages directly against the real running
# service, so these ARE genuinely alive, not stale.
_APP_PY_OWNED_STRINGS = frozenset({
    "Back to Home", "Incorrect password. Try again.", "Page not found.",
    "Password", "Sign in", "Sign in to manage this device's settings.",
    "The page you requested doesn't exist or may have moved.",
    "Too many attempts — try again in %ds.",
})
# Check 2's documented exception list, part 2: two Notifications flash
# strings defined for a POST /settings/notifications/test outcome that
# has no flash-message translation wiring anywhere in companion/app.py
# yet (20-11-SUMMARY.md's own "Flagged for 20-12" note: every flash key
# in this codebase has the identical, pre-existing gap — flash-message
# translation is simply not wired up, not something this plan expands
# or is scoped to fix).
_FLASH_AWAITING_TRANSLATION_WIRING = frozenset({
    "Test notification sent.", "Couldn't reach that topic — check the URL.",
})
# Check 2's documented exception list, part 3: a single proper noun
# (the product's own brand name) that is never translated anywhere in
# this codebase, by design (D-05: "route names ... are not translated"
# extends naturally to a brand name, which is not a common noun either).
_PROPER_NOUNS_NEVER_TRANSLATED = frozenset({"SkyPane"})


def _is_route_or_path(value):
    return value.startswith("/") or value.endswith((".js", ".png", ".css", ".ico", ".svg"))


def _is_html_markup_or_comment(value):
    return value.strip().startswith("<")


def _has_no_letters(value):
    stripped = _FORMAT_SPEC_RE.sub("", value)
    return not _HAS_LETTER_RE.search(stripped)


def _is_css_class_list(value):
    """A space-separated attribute value where every token is itself a
    hyphenated lowercase identifier (e.g. "text-label cell-unresolved-
    link") — a multi-class CSS attribute, never prose (a real English
    phrase in this codebase never joins two hyphenated words with a
    bare space)."""
    tokens = value.split(" ")
    return len(tokens) > 1 and all(
        t and _HYPHENATED_IDENTIFIER_RE.match(t) and "-" in t for t in tokens)


def _scalar_exclusion_reason(value):
    """Exclusion rules for rule (a): a direct top-level scalar constant
    (or its Add/Mod-folded value)."""
    if value is None or value.strip() == "":
        return "empty-or-blank"
    if value in _PY_KEYWORD_LITERALS:
        return "python-keyword-sentinel"
    if _is_route_or_path(value):
        return "route-or-static-path"
    if _is_html_markup_or_comment(value):
        return "html-markup-or-comment"
    if _LOWERCASE_IDENTIFIER_RE.match(value):
        return "lowercase-identifier"
    if _is_css_class_list(value):
        return "css-class-list"
    if _UPPERCASE_CODE_RE.match(value):
        return "uppercase-code"
    if _has_no_letters(value):
        return "no-letters"
    return None


def _container_exclusion_reason(value):
    """Exclusion rules for rule (b): a dict's own values (or a nested
    tuple/list value's trailing element) — narrower than rule (a)'s
    lowercase-identifier check so a bare lowercase English noun (a
    dict's own legitimate content) is never mistaken for a flash key."""
    if value is None or value.strip() == "":
        return "empty-or-blank"
    if value in _PY_KEYWORD_LITERALS:
        return "python-keyword-sentinel"
    if _is_route_or_path(value):
        return "route-or-static-path"
    if _is_html_markup_or_comment(value):
        return "html-markup-or-comment"
    if _HYPHENATED_IDENTIFIER_RE.match(value) and "-" in value:
        return "hyphenated-lowercase-identifier"
    if _UPPERCASE_CODE_RE.match(value):
        return "uppercase-code"
    if _has_no_letters(value):
        return "no-letters"
    return None


def _traced_exclusion_reason(value):
    """Exclusion rules for rule (c): a value traced all the way to a
    real i18n.t()/t_lang() call argument — proof of translatability
    already exists, so only the empty/no-letters safety nets apply."""
    if value is None or value.strip() == "":
        return "empty-or-blank"
    if _has_no_letters(value):
        return "no-letters"
    return None


def _fold_string(node, scalars):
    """Recursively resolve `node` to the final string Python itself
    would compute at import time, using only `scalars` (this module's
    own already-resolved constants, built in source order) — handles
    string concatenation (`"a" + OTHER`) and %-formatting (`TEMPLATE %
    (a, b)` or `TEMPLATE % a`). Returns None for anything else (a
    function call, a runtime value) rather than guessing."""
    if isinstance(node, ast.Constant):
        return node.value if isinstance(node.value, str) else None
    if isinstance(node, ast.Name):
        v = scalars.get(node.id)
        return v if isinstance(v, str) else None
    if isinstance(node, ast.BinOp):
        if isinstance(node.op, ast.Add):
            left = _fold_string(node.left, scalars)
            right = _fold_string(node.right, scalars)
            if left is not None and right is not None:
                return left + right
            return None
        if isinstance(node.op, ast.Mod):
            left = _fold_string(node.left, scalars)
            if left is None:
                return None
            right_node = node.right
            if isinstance(right_node, ast.Tuple):
                values = []
                for elt in right_node.elts:
                    v = _fold_any_scalar(elt, scalars)
                    if v is None:
                        return None
                    values.append(v)
                try:
                    return left % tuple(values)
                except (TypeError, ValueError):
                    return None
            v = _fold_any_scalar(right_node, scalars)
            if v is None:
                return None
            try:
                return left % v
            except (TypeError, ValueError):
                return None
    return None


def _fold_any_scalar(node, scalars):
    """Like _fold_string(), but also accepts a bare numeric constant —
    needed for a %-formatting operand that is not itself a string."""
    if isinstance(node, ast.Constant) and isinstance(node.value, (str, int, float)):
        return node.value
    if isinstance(node, ast.Name):
        return scalars.get(node.id)
    return _fold_string(node, scalars)


def _is_i18n_call(node, attr_names):
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr in attr_names
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "i18n"
        and node.args
    )


def _scan_module_for_i18n_strings(rel_path):
    """Parse `companion/{rel_path}` from SOURCE (never by importing it
    — T-20-33) and return (produced, excluded):
    - produced: {string: [source description, ...]} — every string this
      scan proves is real, user-visible content needing a French
      catalogue entry.
    - excluded: {string: (exclusion reason, source description)} — every
      candidate string this scan found but ruled out, and why, for a
      developer auditing the scan's own judgement calls.
    """
    fp = os.path.join(HERE, rel_path)
    with open(fp, "r", encoding="utf-8") as fh:
        src = fh.read()
    tree = ast.parse(src, filename=fp)

    produced = {}
    excluded = {}

    def record(value, source_desc, exclusion_fn):
        reason = exclusion_fn(value)
        if reason:
            excluded.setdefault(value, (reason, source_desc))
        else:
            produced.setdefault(value, []).append(source_desc)

    scalars = {}      # name -> resolved scalar (str/int/float)
    containers = {}   # name -> ast.Dict / ast.Tuple / ast.List

    # Pass 1a: top-level assigns, in source order — rule (a) is recorded
    # here, module-level constant-naming-convention names only.
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if not (isinstance(target, ast.Name) and _ALL_CAPS_NAME_RE.match(target.id)):
                continue
            name = target.id
            value_node = node.value
            if isinstance(value_node, (ast.Dict, ast.Tuple, ast.List)):
                containers[name] = value_node
            folded = _fold_string(value_node, scalars)
            if folded is not None:
                scalars[name] = folded
                record(folded, "constant:%s" % name, _scalar_exclusion_reason)
            elif isinstance(value_node, ast.Constant) and isinstance(value_node.value, (int, float)):
                scalars[name] = value_node.value

    # Pass 1b: ALSO collect container literals assigned to a local
    # (function-scoped) name anywhere in the module — a builder that
    # constructs its own small lookup table function-locally, then
    # indexes it with a runtime loop variable inside i18n.t(), still
    # needs its string values proven live. Nothing here is scanned for
    # completeness on its own (rule (a) above stays module-level); a
    # local container only ever contributes a produced string if Pass
    # 2/3 below prove it is actually read from inside an i18n.t()/
    # t_lang() call. (D-17, 21-01-PLAN.md Task 1: layout.py's own
    # former example of this pattern, _mode_form_html()'s "simple"/
    # "full" labels dict, is deleted along with the function — this
    # pass's mechanism itself is unaffected and still exercised by
    # other builders' local lookup tables.)
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            if (isinstance(target, ast.Name) and target.id not in containers
                    and isinstance(node.value, (ast.Dict, ast.Tuple, ast.List))):
                containers[target.id] = node.value

    # Pass 2: bindings (for-loop/comprehension targets, zip() targets,
    # and a tuple-unpacked `X.get(key, DEFAULT)`) and the set of dicts
    # proven scan-eligible for rule (b).
    bindings = {}
    dict_scan_eligible = set()

    def _record_binding(target, container_name, kind):
        if isinstance(target, ast.Name):
            bindings.setdefault(target.id, []).append((container_name, None, kind))
        elif isinstance(target, (ast.Tuple, ast.List)):
            for pos, elt in enumerate(target.elts):
                if isinstance(elt, ast.Name):
                    bindings.setdefault(elt.id, []).append((container_name, pos, kind))

    for node in ast.walk(tree):
        if isinstance(node, (ast.For, ast.comprehension)):
            it = node.iter
            if isinstance(it, ast.Name) and it.id in containers:
                # Iterating a container directly: each loop pass sees
                # ONE element (a "row"), so an unpacked position is read
                # from EVERY row (health_page._CORROBORATION_ROWS' own
                # shape: "for _key, label, _status, explanation in
                # _CORROBORATION_ROWS").
                _record_binding(node.target, it.id, "row")
            elif (isinstance(it, ast.Call) and isinstance(it.func, ast.Name)
                    and it.func.id == "zip" and isinstance(node.target, (ast.Tuple, ast.List))
                    and len(node.target.elts) == len(it.args)):
                # `for label, dd in zip(RESOLVE_CONTEXT_LABELS, pairs)` —
                # each unpacked name binds to the SAME position in its
                # own zip() argument, not a position within a shared
                # tuple-of-tuples (airlines_page.py's resolve-context dl).
                for elt, zip_arg in zip(node.target.elts, it.args):
                    if (isinstance(elt, ast.Name) and isinstance(zip_arg, ast.Name)
                            and zip_arg.id in containers):
                        _record_binding(elt, zip_arg.id, "row")
        elif isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
            call = node.value
            if (isinstance(call.func, ast.Attribute) and call.func.attr == "get"
                    and len(call.args) >= 2 and isinstance(call.args[1], ast.Name)
                    and call.args[1].id in containers and len(node.targets) == 1):
                # `a, b = SOME_DICT.get(key, DEFAULT_TUPLE)` —
                # DEFAULT_TUPLE is itself ONE (status, label)-shaped
                # row, not a list of rows, so a bound position reads
                # directly off its own elements ("single"), never
                # per-element like the "row" case above (history_page's
                # own _CORROBORATION_LABELS/_DEFAULT_CORROBORATION
                # pairing).
                _record_binding(node.targets[0], call.args[1].id, "single")
                if (isinstance(node.targets[0], (ast.Tuple, ast.List))
                        and isinstance(call.func.value, ast.Name)
                        and isinstance(containers.get(call.func.value.id), ast.Dict)):
                    dict_scan_eligible.add(call.func.value.id)

    for node in ast.walk(tree):
        if _is_i18n_call(node, ("t", "t_lang")):
            for n in ast.walk(node.args[0]):
                if isinstance(n, ast.Name) and isinstance(containers.get(n.id), ast.Dict):
                    dict_scan_eligible.add(n.id)

    # Pass 3: record dict values for scan-eligible dicts only (rule b).
    for name in dict_scan_eligible:
        dict_node = containers[name]
        for v in dict_node.values:
            folded_v = _fold_string(v, scalars)
            if folded_v is not None:
                record(folded_v, "dict-value:%s" % name, _container_exclusion_reason)
            elif isinstance(v, (ast.Tuple, ast.List)) and v.elts:
                # Only the TRAILING element of a tuple-valued dict entry
                # is prose in this codebase's one such shape
                # (_CORROBORATION_LABELS: status code, then label) —
                # leading elements are internal state codes, never
                # displayed, mirroring _CORROBORATION_ROWS/_SOURCE_ROWS's
                # own leading key/source field.
                folded_elt = _fold_string(v.elts[-1], scalars)
                if folded_elt is not None:
                    record(folded_elt, "dict-value-nested:%s" % name, _container_exclusion_reason)

    def _resolve_binding_values(container_name, position, kind):
        node = containers.get(container_name)
        if node is None:
            return []
        elts = getattr(node, "elts", [])
        out = []
        if kind == "single":
            if position is None:
                candidates = list(elts)
            elif 0 <= position < len(elts):
                candidates = [elts[position]]
            else:
                candidates = []
            for candidate in candidates:
                folded = _fold_string(candidate, scalars)
                if folded is not None:
                    out.append(folded)
            return out
        for elt in elts:
            if position is None:
                candidate = elt
            elif isinstance(elt, (ast.Tuple, ast.List)) and 0 <= position < len(elt.elts):
                candidate = elt.elts[position]
            else:
                candidate = None
            if candidate is not None:
                folded = _fold_string(candidate, scalars)
                if folded is not None:
                    out.append(folded)
        return out

    def _resolve_t_arg(arg_node):
        folded = _fold_string(arg_node, scalars)
        if folded is not None:
            return [folded]
        if (isinstance(arg_node, ast.Call) and isinstance(arg_node.func, ast.Attribute)
                and arg_node.func.attr == "get" and len(arg_node.args) >= 2):
            # i18n.t(SOME_DICT.get(key, "literal default")) — the
            # dict's own values are already covered by rule (b) via
            # dict_scan_eligible (this exact call site is what makes it
            # eligible); the fallback default is a second, independent
            # literal the dict's own values can never stand in for.
            default_folded = _fold_string(arg_node.args[1], scalars)
            if default_folded is not None:
                return [default_folded]
        if isinstance(arg_node, ast.Name) and arg_node.id in bindings:
            out = []
            for cname, pos, kind in bindings[arg_node.id]:
                out.extend(_resolve_binding_values(cname, pos, kind))
            return out
        if isinstance(arg_node, ast.Subscript):
            value_node = arg_node.value
            idx_node = arg_node.slice
            if (isinstance(idx_node, ast.Constant) and isinstance(idx_node.value, int)
                    and isinstance(value_node, ast.Name) and value_node.id in containers):
                elts = getattr(containers[value_node.id], "elts", [])
                i = idx_node.value
                if -len(elts) <= i < len(elts):
                    f = _fold_string(elts[i], scalars)
                    if f is not None:
                        return [f]
        return []

    # Pass 4: every i18n.t()/i18n.t_lang() call site, anywhere — rule (c).
    for node in ast.walk(tree):
        if _is_i18n_call(node, ("t", "t_lang")):
            for value in _resolve_t_arg(node.args[0]):
                record(value, "i18n.%s(...)" % node.func.attr, _traced_exclusion_reason)

    return produced, excluded


def _scan_all_d05_modules():
    """Scan every D-05 module and return the UNION of their produced
    sets, each value mapped to every (module, source description) pair
    that proves it — a key can legitimately be produced by more than
    one module (e.g. a nav label read by both layout.py and a page's
    own PAGE_TITLE constant); that is never a conflict."""
    all_produced = {}
    for rel_path in _SCAN_RELATIVE_PATHS:
        produced, _excluded = _scan_module_for_i18n_strings(rel_path)
        for value, sources in produced.items():
            all_produced.setdefault(value, []).extend(
                "%s:%s" % (rel_path, source) for source in sources)
    return all_produced


def main():
    results = []

    def check(name, fn):
        try:
            ok, reason = fn()
        except Exception as exc:  # never let an exception be swallowed into a pass
            ok, reason = False, "exception: %r" % (exc,)
        results.append((name, ok))
        if ok:
            print("PASS %s" % name)
        else:
            print("FAIL %s - %s" % (name, reason))

    # ==================================================================
    # t_lang() round-trip and fallback
    # ==================================================================

    def _check_t_lang_fr():
        got = i18n.t_lang("Home", "fr")
        if got != "Accueil":
            return False, "t_lang('Home', 'fr') = %r, expected 'Accueil'" % (got,)
        return True, ""

    check("t_lang('Home', 'fr') == 'Accueil'", _check_t_lang_fr)

    def _check_t_lang_en():
        got = i18n.t_lang("Home", "en")
        if got != "Home":
            return False, "t_lang('Home', 'en') = %r, expected 'Home'" % (got,)
        return True, ""

    check("t_lang('Home', 'en') == 'Home'", _check_t_lang_en)

    def _check_t_lang_missing_key():
        text = "a string nobody translated"
        got = i18n.t_lang(text, "fr")
        if got != text:
            return False, "t_lang(missing key, 'fr') = %r, expected unchanged" % (got,)
        return True, ""

    check(
        "t_lang() degrades a missing key to the English source unchanged",
        _check_t_lang_missing_key)

    # ==================================================================
    # t() follows prefs.set_request_prefs()
    # ==================================================================

    def _check_t_follows_prefs_fr_then_back():
        try:
            prefs.set_request_prefs(lang="fr")
            fr_result = i18n.t("Home")
            prefs.set_request_prefs(lang="en")
            en_result = i18n.t("Home")
        finally:
            prefs.set_request_prefs(lang="en")
        if fr_result != "Accueil":
            return False, "t('Home') under lang='fr' = %r, expected 'Accueil'" % (fr_result,)
        if en_result != "Home":
            return False, "t('Home') under lang='en' = %r, expected 'Home'" % (en_result,)
        return True, ""

    check(
        "t() follows prefs.set_request_prefs(lang='fr') and back",
        _check_t_follows_prefs_fr_then_back)

    # ==================================================================
    # prefs: membership-tested degrade-to-default contract
    # ==================================================================

    def _check_prefs_unknown_lang_degrades_to_en():
        try:
            prefs.set_request_prefs(lang="de")
            got = prefs.current_lang()
        finally:
            prefs.set_request_prefs(lang="en")
        if got != "en":
            return False, "current_lang() after lang='de' = %r, expected 'en'" % (got,)
        return True, ""

    check(
        "prefs.set_request_prefs(lang='de') resolves to 'en'",
        _check_prefs_unknown_lang_degrades_to_en)

    # D-17 (21-01-PLAN.md Task 1): _check_prefs_unknown_mode_leaves_
    # simple_mode_false and _check_prefs_simple_mode_true_for_simple
    # are deleted — prefs.simple_mode()/the mode= parameter they
    # exercised no longer exist.

    # ==================================================================
    # Catalogue completeness against its own sibling modules
    # ==================================================================

    def _check_catalog_contains_every_common_key():
        missing = [k for k in i18n_fr_common.CATALOG if k not in i18n_fr.CATALOG]
        if missing:
            return False, "keys missing from merged CATALOG: %r" % (missing,)
        return True, ""

    check(
        "i18n_fr.CATALOG contains every key defined in common.py",
        _check_catalog_contains_every_common_key)

    def _check_catalog_contains_every_nav_key():
        missing = [k for k in i18n_fr_nav.CATALOG if k not in i18n_fr.CATALOG]
        if missing:
            return False, "keys missing from merged CATALOG: %r" % (missing,)
        return True, ""

    check(
        "i18n_fr.CATALOG contains every key defined in nav.py",
        _check_catalog_contains_every_nav_key)

    # ==================================================================
    # Value shape and dead-translation spot check
    # ==================================================================

    # 20-03-PLAN.md Task 3 (D-05) adds three genuine French/English
    # cognates from the Health page's own catalogue entries —
    # "Corroboration" (a shared technical loanword), and "Source"/
    # "Description" (the resolution-statistics table's own headers,
    # identical in both languages) — the "real cognate, not a missed
    # translation" exception this frozenset exists for.
    # 20-11-PLAN.md Task 1 (D-26, 20-UI-SPEC.md copy table G): a fourth
    # genuine cognate — "Notifications" is spelled and pronounced
    # identically in French and English (a shared Latin-root loanword,
    # exactly the "Corroboration" precedent above), so the Notifications
    # group's own heading is intentionally byte-identical in both
    # languages, not a missed translation.
    # D-17 (21-01-PLAN.md Task 1): the simple-mode switch's "Simple"/
    # "Complet" cognate entry this frozenset used to document is
    # deleted along with the switch itself (companion/i18n_fr/nav.py) —
    # "Simple" is removed from this set, not left as dead documentation
    # for a key that no longer exists in the catalog.
    _UNCHANGED_IN_FRENCH = frozenset(
        {"Corroboration", "Source", "Description", "Notifications"})

    def _check_every_catalog_value_is_str_and_differs_from_key():
        bad_type = [k for k, v in i18n_fr.CATALOG.items() if not isinstance(v, str)]
        if bad_type:
            return False, "non-str CATALOG values for keys: %r" % (bad_type,)
        identical = [
            k for k, v in i18n_fr.CATALOG.items()
            if v == k and k not in _UNCHANGED_IN_FRENCH]
        if identical:
            return False, "CATALOG values identical to their English key: %r" % (identical,)
        return True, ""

    check(
        "every CATALOG value is a str and differs from its English key",
        _check_every_catalog_value_is_str_and_differs_from_key)

    # ==================================================================
    # Source-level import-boundary check
    # ==================================================================

    def _check_no_forbidden_imports():
        forbidden = ("companion.pages", "from server")
        offenders = []
        for rel_path in ("i18n.py", "prefs.py"):
            abs_path = os.path.join(HERE, rel_path)
            with open(abs_path, "r", encoding="utf-8") as fh:
                for line_no, line in enumerate(fh, start=1):
                    stripped = line.lstrip()
                    if stripped.startswith("#"):
                        continue
                    for needle in forbidden:
                        if needle in line:
                            offenders.append("%s:%d: %r" % (rel_path, line_no, needle))
        if offenders:
            return False, "forbidden import references found: %r" % (offenders,)
        return True, ""

    check(
        "companion/i18n.py and companion/prefs.py import neither "
        "companion.pages nor server",
        _check_no_forbidden_imports)

    # ==================================================================
    # D-08 Check 1: completeness — every scanned literal must be a key
    # of companion.i18n_fr.CATALOG.
    # ==================================================================

    all_produced = _scan_all_d05_modules()

    def _check_d08_completeness():
        missing = sorted(
            value for value in all_produced
            if value not in i18n_fr.CATALOG
            and value not in _PROPER_NOUNS_NEVER_TRANSLATED)
        if missing:
            lines = [
                "%r (from %s)" % (value, all_produced[value][0])
                for value in missing]
            return False, (
                "%d string(s) scanned from the D-05 module set have no "
                "companion.i18n_fr.CATALOG entry: %s"
                % (len(missing), "; ".join(lines)))
        return True, ""

    check(
        "D-08 Check 1: every scanned page-module string is a "
        "companion.i18n_fr.CATALOG key (ast-based, source-only scan)",
        _check_d08_completeness)

    # ==================================================================
    # D-08 Check 2: no dead translations — every CATALOG key must
    # appear in the scanned set, with a short, documented, named
    # exception list for the strings legitimately owned elsewhere.
    # ==================================================================

    def _check_d08_no_dead_translations():
        exceptions = (
            _APP_PY_OWNED_STRINGS
            | _FLASH_AWAITING_TRANSLATION_WIRING
            | _PROPER_NOUNS_NEVER_TRANSLATED
            | frozenset(i18n_fr_registry.CATALOG))
        orphaned = sorted(
            key for key in i18n_fr.CATALOG
            if key not in all_produced and key not in exceptions)
        if orphaned:
            return False, (
                "%d companion.i18n_fr.CATALOG key(s) are never produced "
                "by the D-05 module scan and are not in a documented "
                "exception list: %r" % (len(orphaned), orphaned))
        return True, ""

    check(
        "D-08 Check 2: every companion.i18n_fr.CATALOG key is produced "
        "by the D-05 module scan, server/notify.py's own bodies, or a "
        "documented exception",
        _check_d08_no_dead_translations)

    # ==================================================================
    # D-08 Check 3: render every page in French against a seeded
    # state, over a real running service — asserts each render
    # succeeds, carries the page's own French heading/copy, and shows
    # no Python-format artefact (a mistyped catalogue key's actual
    # failure mode).
    # ==================================================================

    import companion.auth as auth  # noqa: E402 (deferred: only Check 3 needs it)
    import companion.test_companion_app as _tca  # noqa: E402 (deferred: subprocess-free harness)

    _FORMAT_ARTEFACT_RE = re.compile(r"%s|%d|\{\}")

    def _no_format_artefact(body_text):
        return not _FORMAT_ARTEFACT_RE.search(body_text)

    _render_harness = [None]
    _render_cookies = [None]

    def _start_render_harness():
        if _render_harness[0] is None:
            harness = _tca._InProcessHarness()
            session_cookie = _tca._login(harness)
            lang_cookie = "%s; %s=fr" % (session_cookie, auth.UI_LANG_COOKIE_NAME)
            _render_harness[0] = harness
            _render_cookies[0] = (session_cookie, lang_cookie)
        return _render_harness[0], _render_cookies[0]

    def _make_authenticated_page_check(route, french_needle):
        def _fn():
            harness, (_session_cookie, lang_cookie) = _start_render_harness()
            status, _headers, body = _tca.http_request(
                harness.base_url() + route, cookie=lang_cookie)
            text = body.decode("utf-8", "replace")
            if status != 200:
                return False, "GET %s under lang=fr returned %d, expected 200" % (route, status)
            if french_needle not in text:
                return False, (
                    "GET %s under lang=fr did not contain %r" % (route, french_needle))
            if not _no_format_artefact(text):
                return False, "GET %s under lang=fr contains a stray %%s/%%d/{} artefact" % (route,)
            return True, ""
        return _fn

    for _route, _needle, _label in (
            ("/", "Accueil", "Home"),
            ("/display", "Affichage", "Display"),
            ("/device", "Appareil", "Device"),
            ("/flights", "Vols", "Flights"),
            ("/airlines", "Compagnies", "Airlines"),
            ("/health", "État", "Health")):
        check(
            "D-08 Check 3: %s renders in French (GET %s, lang=fr)" % (_label, _route),
            _make_authenticated_page_check(_route, _needle))

    def _check_login_page_in_french():
        harness, _cookies = _start_render_harness()
        status, _headers, body = _tca.http_request(
            harness.base_url() + "/login",
            cookie="%s=fr" % auth.UI_LANG_COOKIE_NAME)
        text = body.decode("utf-8", "replace")
        if status != 200:
            return False, "GET /login under lang=fr returned %d, expected 200" % status
        needle = "Connectez-vous pour gérer les réglages de cet appareil."
        if needle not in text:
            return False, "GET /login under lang=fr did not contain %r" % (needle,)
        if not _no_format_artefact(text):
            return False, "GET /login under lang=fr contains a stray %s/%d/{} artefact"
        return True, ""

    check("D-08 Check 3: the login page renders in French", _check_login_page_in_french)

    def _check_404_page_in_french():
        harness, (_session_cookie, lang_cookie) = _start_render_harness()
        status, _headers, body = _tca.http_request(
            harness.base_url() + "/this-route-does-not-exist", cookie=lang_cookie)
        text = body.decode("utf-8", "replace")
        if status != 404:
            return False, "GET of an unknown route under lang=fr returned %d, expected 404" % status
        needle = "Page introuvable."
        if needle not in text:
            return False, "The 404 page under lang=fr did not contain %r" % (needle,)
        if not _no_format_artefact(text):
            return False, "The 404 page under lang=fr contains a stray %s/%d/{} artefact"
        return True, ""

    check("D-08 Check 3: the 404 page renders in French", _check_404_page_in_french)

    def _check_calendar_disconnect_confirm_page_in_french():
        harness, (_session_cookie, lang_cookie) = _start_render_harness()
        status, _headers, body = _tca.http_request(
            harness.base_url() + "/settings/calendar/disconnect",
            method="POST", cookie=lang_cookie, data=b"")
        text = body.decode("utf-8", "replace")
        if status != 200:
            return False, (
                "A bare POST /settings/calendar/disconnect under lang=fr "
                "returned %d, expected 200 (the confirm page)" % status)
        needle = "Déconnecter le calendrier ?"
        if needle not in text:
            return False, (
                "The calendar-disconnect confirm page under lang=fr did "
                "not contain %r" % (needle,))
        if not _no_format_artefact(text):
            return False, (
                "The calendar-disconnect confirm page under lang=fr "
                "contains a stray %s/%d/{} artefact")
        return True, ""

    check(
        "D-08 Check 3: the calendar-disconnect confirmation page renders in French",
        _check_calendar_disconnect_confirm_page_in_french)

    if _render_harness[0] is not None:
        _render_harness[0].stop()

    # ==================================================================
    # D-08 Check 4 (D-09's mechanical half): every CATALOG value uses
    # the typographic apostrophe (U+2019, never a straight "'"), and
    # every value containing ":"/";"/"?"/"!" preceded by a space uses
    # U+00A0 (non-breaking) for that space, never a plain U+0020.
    # ==================================================================

    def _check_typographic_apostrophe():
        offenders = sorted(
            key for key, value in i18n_fr.CATALOG.items() if "'" in value)
        if offenders:
            return False, (
                "%d CATALOG value(s) contain a straight apostrophe "
                "instead of U+2019: %r" % (len(offenders), offenders))
        return True, ""

    check(
        "D-08 Check 4 (D-09): every CATALOG value uses the "
        "typographic apostrophe, never a straight quote",
        _check_typographic_apostrophe)

    _REGULAR_SPACE_BEFORE_PUNCT_RE = re.compile(r" [:;?!]")

    def _check_nbsp_before_punctuation():
        offenders = sorted(
            key for key, value in i18n_fr.CATALOG.items()
            if _REGULAR_SPACE_BEFORE_PUNCT_RE.search(value))
        if offenders:
            return False, (
                "%d CATALOG value(s) have a ':'/';'/'?'/'!' preceded by "
                "a plain space instead of U+00A0: %r"
                % (len(offenders), offenders))
        return True, ""

    check(
        "D-08 Check 4 (D-09): every CATALOG value uses U+00A0 (not a "
        "plain space) before ':'/';'/'?'/'!'",
        _check_nbsp_before_punctuation)

    passed = sum(1 for _name, ok in results if ok)
    total = len(results)
    print("%d/%d checks pass" % (passed, total))
    return 0 if (passed == total and total == EXPECTED_CHECK_COUNT) else 1


if __name__ == "__main__":
    sys.exit(main())
