# -*- coding: utf-8 -*-
"""companion/i18n_fr/common.py — French strings for the login page, the
404 page and the shared "Sign out" control (D-01/D-04/D-05,
20-01-PLAN.md Task 1).

One sibling module of the companion/i18n_fr package (see that
package's __init__.py for the auto-merge/duplicate-key contract this
module participates in). Every key here is the exact English source
string a call site in companion/app.py or companion/layout.py passes
to companion.i18n.t() — including the "%d"/"%s" placeholder shape,
unchanged.

Copy follows D-09: sentence case, the typographic apostrophe (U+2019,
never a straight quote), and a non-breaking space (U+00A0) before
":" ";" "?" "!".
"""

CATALOG = {
    # --- Login page (companion/app.py's _login_body()) -----------------
    "Sign in to manage this device's settings.":
        "Connectez-vous pour gérer les réglages de cet appareil.",
    "Too many attempts — try again in %ds.":
        "Trop de tentatives — réessayez dans %d s.",
    "Password": "Mot de passe",
    "Sign in": "Se connecter",
    "Incorrect password. Try again.":
        "Mot de passe incorrect. Réessayez.",

    # --- 404 page (companion/app.py's _not_found_page(), NOT_FOUND_TITLE
    #     / NOT_FOUND_PURPOSE_TEXT) -----------------------------------
    "Page not found.": "Page introuvable.",
    "The page you requested doesn't exist or may have moved.":
        "La page demandée n’existe pas ou a peut-être été déplacée.",
    "Back to Home": "Retour à l’accueil",

    # --- Shared footer control (companion/layout.py's
    #     _logout_form_html()) -----------------------------------------
    "Sign out": "Se déconnecter",
}
