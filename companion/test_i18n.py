#!/usr/bin/env python3
"""Contract harness for companion/i18n.py, companion/prefs.py and the
companion/i18n_fr/ catalogue package (D-01..D-04, 20-01-PLAN.md
Task 1).

Covers: t_lang()'s round-trip and fallback behaviour, t()'s own
per-request resolution through prefs.set_request_prefs(), prefs'
membership-tested degrade-to-default contract, the catalogue's
completeness against its own sibling modules, a value-shape/no-dead-
translation spot check, and a source-level import-boundary check on
i18n.py/prefs.py.

The D-08 completeness (every page-module constant covered) and dead-
translation (every catalogue entry used) checks are NOT this file's —
they land in 20-12, after every page has been rewritten (20-01-PLAN.md
Task 1's own <action> note).

Stdlib-only (os, sys). No pytest.

Usage:
    server/.venv/bin/python3 companion/test_i18n.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import companion.i18n as i18n  # noqa: E402
import companion.i18n_fr as i18n_fr  # noqa: E402
import companion.i18n_fr.common as i18n_fr_common  # noqa: E402
import companion.i18n_fr.nav as i18n_fr_nav  # noqa: E402
import companion.prefs as prefs  # noqa: E402

# 20-01-PLAN.md Task 1
EXPECTED_CHECK_COUNT = 11


def main():
    results = []

    def check(name, fn):
        try:
            ok, reason = fn()
        except Exception as exc:  # never let an exception be swallowed into a pass
            ok, reason = False, "exception: %r" % (exc,)
        results.append((name, ok))
        if ok:
            print("PASS %s" % name)
        else:
            print("FAIL %s - %s" % (name, reason))

    # ==================================================================
    # t_lang() round-trip and fallback
    # ==================================================================

    def _check_t_lang_fr():
        got = i18n.t_lang("Home", "fr")
        if got != "Accueil":
            return False, "t_lang('Home', 'fr') = %r, expected 'Accueil'" % (got,)
        return True, ""

    check("t_lang('Home', 'fr') == 'Accueil'", _check_t_lang_fr)

    def _check_t_lang_en():
        got = i18n.t_lang("Home", "en")
        if got != "Home":
            return False, "t_lang('Home', 'en') = %r, expected 'Home'" % (got,)
        return True, ""

    check("t_lang('Home', 'en') == 'Home'", _check_t_lang_en)

    def _check_t_lang_missing_key():
        text = "a string nobody translated"
        got = i18n.t_lang(text, "fr")
        if got != text:
            return False, "t_lang(missing key, 'fr') = %r, expected unchanged" % (got,)
        return True, ""

    check(
        "t_lang() degrades a missing key to the English source unchanged",
        _check_t_lang_missing_key)

    # ==================================================================
    # t() follows prefs.set_request_prefs()
    # ==================================================================

    def _check_t_follows_prefs_fr_then_back():
        try:
            prefs.set_request_prefs(lang="fr")
            fr_result = i18n.t("Home")
            prefs.set_request_prefs(lang="en")
            en_result = i18n.t("Home")
        finally:
            prefs.set_request_prefs(lang="en")
        if fr_result != "Accueil":
            return False, "t('Home') under lang='fr' = %r, expected 'Accueil'" % (fr_result,)
        if en_result != "Home":
            return False, "t('Home') under lang='en' = %r, expected 'Home'" % (en_result,)
        return True, ""

    check(
        "t() follows prefs.set_request_prefs(lang='fr') and back",
        _check_t_follows_prefs_fr_then_back)

    # ==================================================================
    # prefs: membership-tested degrade-to-default contract
    # ==================================================================

    def _check_prefs_unknown_lang_degrades_to_en():
        try:
            prefs.set_request_prefs(lang="de")
            got = prefs.current_lang()
        finally:
            prefs.set_request_prefs(lang="en")
        if got != "en":
            return False, "current_lang() after lang='de' = %r, expected 'en'" % (got,)
        return True, ""

    check(
        "prefs.set_request_prefs(lang='de') resolves to 'en'",
        _check_prefs_unknown_lang_degrades_to_en)

    def _check_prefs_unknown_mode_leaves_simple_mode_false():
        try:
            prefs.set_request_prefs(mode="nonsense")
            got = prefs.simple_mode()
        finally:
            prefs.set_request_prefs(mode="full")
        if got is not False:
            return False, "simple_mode() after mode='nonsense' = %r, expected False" % (got,)
        return True, ""

    check(
        "prefs.set_request_prefs(mode='nonsense') leaves simple_mode() False",
        _check_prefs_unknown_mode_leaves_simple_mode_false)

    def _check_prefs_simple_mode_true_for_simple():
        try:
            prefs.set_request_prefs(mode="simple")
            got = prefs.simple_mode()
        finally:
            prefs.set_request_prefs(mode="full")
        if got is not True:
            return False, "simple_mode() after mode='simple' = %r, expected True" % (got,)
        return True, ""

    check(
        "prefs.set_request_prefs(mode='simple') makes simple_mode() True",
        _check_prefs_simple_mode_true_for_simple)

    # ==================================================================
    # Catalogue completeness against its own sibling modules
    # ==================================================================

    def _check_catalog_contains_every_common_key():
        missing = [k for k in i18n_fr_common.CATALOG if k not in i18n_fr.CATALOG]
        if missing:
            return False, "keys missing from merged CATALOG: %r" % (missing,)
        return True, ""

    check(
        "i18n_fr.CATALOG contains every key defined in common.py",
        _check_catalog_contains_every_common_key)

    def _check_catalog_contains_every_nav_key():
        missing = [k for k in i18n_fr_nav.CATALOG if k not in i18n_fr.CATALOG]
        if missing:
            return False, "keys missing from merged CATALOG: %r" % (missing,)
        return True, ""

    check(
        "i18n_fr.CATALOG contains every key defined in nav.py",
        _check_catalog_contains_every_nav_key)

    # ==================================================================
    # Value shape and dead-translation spot check
    # ==================================================================

    # 20-UI-SPEC.md §F's own copy table states the French for the
    # simple-mode switch's "Simple" option is unchanged ("Simple" /
    # "Complet") — the one documented exception to "the French value
    # always differs from its English key" for this plan's own seeded
    # entries.
    _UNCHANGED_IN_FRENCH = frozenset({"Simple"})

    def _check_every_catalog_value_is_str_and_differs_from_key():
        bad_type = [k for k, v in i18n_fr.CATALOG.items() if not isinstance(v, str)]
        if bad_type:
            return False, "non-str CATALOG values for keys: %r" % (bad_type,)
        identical = [
            k for k, v in i18n_fr.CATALOG.items()
            if v == k and k not in _UNCHANGED_IN_FRENCH]
        if identical:
            return False, "CATALOG values identical to their English key: %r" % (identical,)
        return True, ""

    check(
        "every CATALOG value is a str and differs from its English key",
        _check_every_catalog_value_is_str_and_differs_from_key)

    # ==================================================================
    # Source-level import-boundary check
    # ==================================================================

    def _check_no_forbidden_imports():
        forbidden = ("companion.pages", "from server")
        offenders = []
        for rel_path in ("i18n.py", "prefs.py"):
            abs_path = os.path.join(HERE, rel_path)
            with open(abs_path, "r", encoding="utf-8") as fh:
                for line_no, line in enumerate(fh, start=1):
                    stripped = line.lstrip()
                    if stripped.startswith("#"):
                        continue
                    for needle in forbidden:
                        if needle in line:
                            offenders.append("%s:%d: %r" % (rel_path, line_no, needle))
        if offenders:
            return False, "forbidden import references found: %r" % (offenders,)
        return True, ""

    check(
        "companion/i18n.py and companion/prefs.py import neither "
        "companion.pages nor server",
        _check_no_forbidden_imports)

    passed = sum(1 for _name, ok in results if ok)
    total = len(results)
    print("%d/%d checks pass" % (passed, total))
    return 0 if (passed == total and total == EXPECTED_CHECK_COUNT) else 1


if __name__ == "__main__":
    sys.exit(main())
