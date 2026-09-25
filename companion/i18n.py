"""The per-request language lookup for the SkyPane companion service.
Page-independent: imports only companion.i18n_fr and companion.prefs.

t() returns plain text, never markup — every call site still wraps its
return value in layout.escape_html(), like any other dynamic string.
"""
import companion.i18n_fr as i18n_fr
import companion.prefs as prefs


def t(text):
    """Return i18n_fr.CATALOG[text] when the current request language
    is French AND text is a key in that dict; otherwise return text
    unchanged. Never raises, never logs — a missing key degrades to
    the English source string exactly like a request in English would
    render.
    """
    if prefs.current_lang() == "fr":
        return i18n_fr.CATALOG.get(text, text)
    return text


def t_lang(text, lang):
    """t()'s test-only sibling: looks up `text` for an explicit `lang`
    without touching prefs' per-request ContextVar. Same contract as t().
    """
    if lang == "fr":
        return i18n_fr.CATALOG.get(text, text)
    return text
