"""Which airline an artwork file belongs to, for the message that names it.

The key comes from an address the person used to upload a picture; it is only
ever compared against the airlines the editor itself lists, never echoed.
"""
from companion import airline_display
from server.plane import illustrations, manual_resolutions, name_overrides

# The query parameter that carries the artwork key a refusal is about.
QUERY_PARAM = "artwork"


def _type_slugs():
    return tuple(illustrations.SHAPE_SLUGS) + tuple(illustrations._TYPE_VARIANT_SLUGS.values())


def base_key(key):
    """The airline's own artwork key for `key`: a per-type picture
    (`{airline}-{type slug}`) belongs to its airline's row."""
    if not isinstance(key, str):
        return ""
    for slug in _type_slugs():
        suffix = "-" + slug
        if key.endswith(suffix) and len(key) > len(suffix):
            return key[:-len(suffix)]
    return key


def _names(state_dir):
    names = list(illustrations.target_airline_names())
    names += [entry["airline_name"]
              for entry in manual_resolutions.load_manual_resolutions(state_dir).values()]
    names += [entry["airline_name"]
              for entry in name_overrides.load_name_overrides(state_dir).values()]
    return names


def airline_name_for_key(state_dir, key):
    """The shown name of the airline whose artwork key (or per-type key) is
    `key`, or None when no airline the editor lists has it."""
    candidates = {key, base_key(key)} - {""}
    for name in _names(state_dir):
        if manual_resolutions.illustration_key_for_name(name) in candidates:
            return airline_display.shown_name(name)
    return None
