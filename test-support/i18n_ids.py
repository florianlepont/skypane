"""Migration tooling for the companion's stable message IDs — not
production code, imported only by one-off migration codemods (run from
the session scratchpad, never committed) and by this module's own unit
test.

slug_for() is the ONE deterministic rule shared across the i18n
migration effort to turn an English catalogue string into the "<slug>"
half of a "<area>.<slug>" message ID, so separate migration passes
converting different halves of one catalogue entry (the English constant
and its French translation) agree on the same ID without coordinating.
Once assigned, an ID never changes when the English is reworded — that
is the entire point of the ID scheme.
"""
import re

# A "%s"/"%d" placeholder contributes nothing beyond the "_" separator
# its surrounding punctuation would already produce — replaced with "_"
# BEFORE the generic non-alphanumeric collapse below, so the placeholder
# letter itself ("s"/"d") never survives into the slug.
_PLACEHOLDER_RE = re.compile(r"%[sd]")

# Any run of characters outside [a-z0-9] collapses to a single "_".
_NON_ALNUM_RUN_RE = re.compile(r"[^a-z0-9]+")

MAX_SLUG_LENGTH = 48


def slug_for(english):
    """Derive a slug from `english`: lowercase; every run of characters
    outside [a-z0-9] becomes "_"; strip leading/trailing "_"; truncate to
    MAX_SLUG_LENGTH characters at a "_" boundary.
    """
    text = _PLACEHOLDER_RE.sub("_", english.lower())
    text = _NON_ALNUM_RUN_RE.sub("_", text)
    text = text.strip("_")
    if len(text) > MAX_SLUG_LENGTH:
        truncated = text[:MAX_SLUG_LENGTH]
        cut = truncated.rfind("_")
        text = truncated[:cut] if cut > 0 else truncated
    return text


def ids_for_area(area, english_values):
    """Assign a "<area>.<slug>" ID to each string in `english_values`, in
    order. A slug collision within this one call (two different English
    strings deriving the same slug) is resolved by appending "_2", "_3",
    ... to the later entries, in the catalogue's current source order —
    the same rule a migration codemod applies when it walks a catalogue
    module top to bottom.
    """
    seen_counts = {}
    ids = []
    for english in english_values:
        slug = slug_for(english)
        seen_counts[slug] = seen_counts.get(slug, 0) + 1
        count = seen_counts[slug]
        if count == 1:
            ids.append("%s.%s" % (area, slug))
        else:
            ids.append("%s.%s_%d" % (area, slug, count))
    return ids
