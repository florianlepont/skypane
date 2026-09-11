"""companion/i18n_fr/ — the French translation catalogue package
(D-01/D-04, 20-01-PLAN.md Task 1).

A package, not a single module, because this phase's plans run in
parallel worktrees per wave and each page's own plan owns its own
catalogue file — auto-discovery below means no plan ever has to edit
a shared registration list, so no two plans in one wave can conflict
over one.

CATALOG is built once, at import time, by walking this package's own
sibling modules with pkgutil.iter_modules() and merging each module's
own CATALOG dict, keyed by the exact English source string (including
any %s/%d placeholder) — mirroring server/device_config.py's
THEMES/RUNWAYS "one registry, no framework" idiom, here flattened to
one dict since the id here is the English string itself, not a short
code.

companion/i18n.py's t()/t_lang() are the intended readers of this
dict; nothing else in this codebase should import CATALOG directly.

Raises ValueError, naming the duplicated key, if two sibling modules
define the same English key — merging silently would make one
translation unreachable.
"""
import importlib
import pkgutil


def _build_catalog():
    catalog = {}
    for module_info in pkgutil.iter_modules(__path__):
        module = importlib.import_module(
            "%s.%s" % (__name__, module_info.name))
        module_catalog = getattr(module, "CATALOG", None)
        if not isinstance(module_catalog, dict):
            continue
        for key, value in module_catalog.items():
            if key in catalog:
                raise ValueError(
                    "companion.i18n_fr: duplicate catalogue key %r found "
                    "in %s — merging silently would make one of the two "
                    "translations unreachable." % (key, module.__name__))
            catalog[key] = value
    return catalog


CATALOG = _build_catalog()
