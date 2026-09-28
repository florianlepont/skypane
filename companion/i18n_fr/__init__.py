"""The French translation catalogue package: one module per page, merged
into BY_ID (stable-ID-keyed) at import time.

Each sibling module exports MESSAGES = {msg_id: french}, merged into
this package's BY_ID — walked by pkgutil.iter_modules() over this
package. companion/i18n.py's t()/t_lang() are the intended readers;
nothing else should import BY_ID directly. Raises ValueError, naming
the duplicated id and the two modules involved, on a duplicate
MESSAGES id across sibling modules — merging silently would make one
translation unreachable.
"""
import importlib
import pkgutil


def _build_by_id():
    by_id = {}
    by_id_sources = {}
    for module_info in pkgutil.iter_modules(__path__):
        module = importlib.import_module(
            "%s.%s" % (__name__, module_info.name))

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
    return by_id


BY_ID = _build_by_id()
