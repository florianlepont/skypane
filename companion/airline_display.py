"""How the companion spells a built-in airline name on screen.

The built-in name is a key: it feeds the frame's render and the illustration
file names, so it never changes. The page shows the proper spelling instead,
where the data source of the History page already uses it. Presentation only;
anything posted back is mapped to the built-in name with `builtin_name()`.
"""

_SHOWN = {"Air Algerie": "Air Algérie"}
_BUILTIN = {shown: builtin for builtin, shown in _SHOWN.items()}


def shown_name(name):
    """The spelling the pages display for the airline name `name`."""
    return _SHOWN.get(name, name)


def builtin_name(name):
    """The built-in name for a name typed or posted as shown on a page."""
    return _BUILTIN.get(name, name)
