"""The per-request language lookup for the SkyPane companion service.
Page-independent: imports only companion.i18n_fr and companion.prefs.

t() returns plain text, never markup — every call site still wraps its
return value in layout.escape_html(), like any other dynamic string.

Message/msg()/REGISTRY are the stable-ID translation mechanism: a Message
is the English text wrapped with a `.msg_id` that never changes when the
English is reworded, so its French translation (looked up by ID, not by
text, in companion.i18n_fr.BY_ID) survives a copy edit. A plain str is
still accepted everywhere a Message is, for call sites and catalogue
modules not yet migrated onto the ID scheme.
"""
import re

import companion.i18n_fr as i18n_fr
import companion.prefs as prefs

# "<area>.<slug>": area is the i18n_fr module owning the French text,
# slug is a deterministic, one-time derivation from the English (see
# test-support/i18n_ids.py's slug_for()). Both halves are
# lowercase/digits/underscores only.
_ID_RE = re.compile(r"^[a-z][a-z0-9_]*\.[a-z0-9_]+$")

# msg_id -> the English text it was last declared with. Read by
# i18n_fr's derived English->French view; also the single source of
# truth a duplicate-ID-different-English declaration is checked against.
REGISTRY = {}


class Message(str):
    """An English UI string carrying a stable translation-lookup ID.

    Subclasses str, so every existing call site (%, escape_html(),
    concatenation, dict keys) treats it exactly like the plain str it
    wraps; `.msg_id` is the only addition, and only i18n.t()/t_lang()
    read it.
    """

    def __new__(cls, msg_id, english):
        instance = str.__new__(cls, english)
        instance.msg_id = msg_id
        return instance


def msg(msg_id, english):
    """Declare a Message: record REGISTRY[msg_id] = english and return
    the Message. Declaring the same ID again with the SAME English is
    idempotent (harmless if a module is imported more than once);
    declaring it again with DIFFERENT English raises ValueError — that
    is almost always two call sites accidentally sharing one ID.
    """
    if not _ID_RE.match(msg_id):
        raise ValueError(
            "companion.i18n.msg: invalid message id %r — expected "
            "'<area>.<slug>' (lowercase letters/digits/underscores, "
            "area and slug separated by a single '.')" % (msg_id,))
    existing = REGISTRY.get(msg_id)
    if existing is not None and existing != english:
        raise ValueError(
            "companion.i18n.msg: message id %r already registered with "
            "different English text (%r != %r) — two call sites are "
            "sharing one ID by mistake" % (msg_id, existing, english))
    REGISTRY[msg_id] = english
    return Message(msg_id, english)


def _derived_english_to_french():
    """An English->French view built from REGISTRY+BY_ID, for a plain
    str call site whose text happens to equal a registered Message's
    English — it still translates, even though the str it holds has no
    `.msg_id` to look up directly. Rebuilt on every call: catalogues are
    small (hundreds of entries) and i18n_fr.CATALOG itself has no
    caching either.
    """
    view = {}
    for msg_id, english in REGISTRY.items():
        french = i18n_fr.BY_ID.get(msg_id)
        if french is not None:
            view[english] = french
    return view


def _translate_fr(text):
    msg_id = getattr(text, "msg_id", None)
    if msg_id is not None:
        french = i18n_fr.BY_ID.get(msg_id)
        if french is not None:
            return french
        # Not migrated on the catalogue side yet — fall back to the
        # legacy English-keyed lookup.
        return i18n_fr.CATALOG.get(str(text), str(text))
    french = i18n_fr.CATALOG.get(text)
    if french is not None:
        return french
    return _derived_english_to_french().get(text, text)


def t(text):
    """Return the French translation of `text` when the current
    request language is French; otherwise the English source unchanged
    (as a plain str). Never raises, never logs — a missing key degrades
    to the English source string exactly like a request in English
    would render.
    """
    if prefs.current_lang() == "fr":
        return _translate_fr(text)
    return str(text)


def t_lang(text, lang):
    """t()'s test-only sibling: looks up `text` for an explicit `lang`
    without touching prefs' per-request ContextVar. Same contract as t().
    """
    if lang == "fr":
        return _translate_fr(text)
    return str(text)
