"""The French translation catalogue package: one module per page, merged
into a single CATALOG at import time.

CATALOG is built by walking this package's sibling modules with
pkgutil.iter_modules() and merging each module's own CATALOG dict, keyed
by the exact English source string (including any %s/%d placeholder).
companion/i18n.py's t()/t_lang() are the intended readers; nothing else
should import CATALOG directly. Raises ValueError, naming the
duplicated key, if two sibling modules define the same English key —
merging silently would make one translation unreachable.
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
