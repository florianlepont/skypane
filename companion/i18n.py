"""companion/i18n.py — the per-request language lookup for the SkyPane
companion service (D-01..D-09, 20-01-PLAN.md Task 1).

Sits beside auth.py, battery.py, layout.py, prefs.py, screens.py and
wake.py in this same package — a shared, page-independent module,
never living inside the per-tab pages sub-package itself (that
sub-package's own "pages/__init__.py" states the rule: no page
module imports another page module). Imports only companion.i18n_fr
and companion.prefs — nothing under the pages sub-package, nothing
under the top-level "server" tree.

t() returns plain text, never markup — every call site still wraps
its return value in layout.escape_html(), exactly like any other
dynamic string. Translated strings are never special-cased as
already-safe.
"""
import companion.i18n_fr as i18n_fr
import companion.prefs as prefs


def t(text):
    """Return i18n_fr.CATALOG[text] when the current request language
    is French AND text is a key in that dict; otherwise return text
    unchanged. Never raises, never logs — a missing key degrades to
    the English source string exactly like a request in English would
    render, per D-04.
    """
    if prefs.current_lang() == "fr":
        return i18n_fr.CATALOG.get(text, text)
    return text


def t_lang(text, lang):
    """t()'s test-only sibling: look up `text` for an explicit `lang`
    without touching prefs' per-request ContextVar — companion/
    test_i18n.py's own round-trip checks use this so they never depend
    on set_request_prefs() leaking state between checks in the same
    process. Same never-raises, degrade-to-English contract as t().
    """
    if lang == "fr":
        return i18n_fr.CATALOG.get(text, text)
    return text
