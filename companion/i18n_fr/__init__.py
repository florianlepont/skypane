"""The French translation catalogue package: one module per page, merged
into CATALOG (legacy, English-keyed) and BY_ID (stable-ID-keyed)
at import time.

Each sibling module may export CATALOG = {english: french} (the legacy
scheme, merged into this package's CATALOG) and/or MESSAGES =
{msg_id: french} (the stable-ID scheme, merged into BY_ID) — both walked
by pkgutil.iter_modules() over this package. A module mid-migration may
export both: MESSAGES for the entries already converted, a residual
CATALOG for the rest. companion/i18n.py's t()/t_lang() are the intended
readers; nothing else should import CATALOG or BY_ID directly. Raises
ValueError, naming the duplicated key/id and the two modules involved, on
a duplicate CATALOG key or a duplicate MESSAGES id across sibling
modules — merging silently would make one translation unreachable.
"""
import importlib
import pkgutil


def _build_catalogs():
    catalog = {}
    catalog_sources = {}
    by_id = {}
    by_id_sources = {}
    for module_info in pkgutil.iter_modules(__path__):
        module = importlib.import_module(
            "%s.%s" % (__name__, module_info.name))

        module_catalog = getattr(module, "CATALOG", None)
        if isinstance(module_catalog, dict):
            for key, value in module_catalog.items():
                if key in catalog:
                    raise ValueError(
                        "companion.i18n_fr: duplicate catalogue key %r "
                        "found in %s and %s — merging silently would "
                        "make one of the two translations unreachable."
                        % (key, catalog_sources[key], module.__name__))
                catalog[key] = value
                catalog_sources[key] = module.__name__

        module_messages = getattr(module, "MESSAGES", None)
        if isinstance(module_messages, dict):
            for msg_id, value in module_messages.items():
                if msg_id in by_id:
                    raise ValueError(
                        "companion.i18n_fr: duplicate message id %r "
                        "found in %s and %s — merging silently would "
                        "make one of the two translations unreachable."
                        % (msg_id, by_id_sources[msg_id], module.__name__))
                by_id[msg_id] = value
                by_id_sources[msg_id] = module.__name__
    return catalog, by_id


CATALOG, BY_ID = _build_catalogs()
