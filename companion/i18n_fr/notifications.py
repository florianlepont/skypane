# -*- coding: utf-8 -*-
"""companion/i18n_fr/notifications.py — French strings for the
Notifications group (companion/pages/config_page.py's
notifications_group()/notifications_test_section(), D-26/D-28),
20-11-PLAN.md Task 1.

One sibling module of the companion/i18n_fr package (see that
package's __init__.py for the auto-merge/duplicate-key contract this
module participates in). Every key here is the exact English source
string a call site in companion/pages/config_page.py passes to
companion.i18n.t() — including any "%s" placeholder shape, unchanged.

Deliberately absent: the four notification transition bodies
("Battery low — %s mV (≈ %d%%)", "Battery back to normal", "The frame
has not checked in for %s", "The frame is back") and the "Send a test"
button's own fixed title/body pair ("SkyPane", "This is a test
notification from SkyPane.") — all six already have their French forms
in server/notify.py's own _BODY_FR dict (20-02-PLAN.md), read through
that module's body_for_lang(), never through companion.i18n.t(). The
auto-merge package raises ValueError on a duplicate key across sibling
modules (see companion/i18n_fr/__init__.py); these six strings are not
duplicated here.

Copy follows D-09: sentence case, the typographic apostrophe (U+2019,
never a straight quote), and a non-breaking space (U+00A0) before ":"
";" "?" "!". Every value below matching 20-UI-SPEC.md's Copywriting
Contract copy table G is copied verbatim from that table.
"""

CATALOG = {
    # --- Heading and caption (D-26) --------------------------------------
    "Notifications": "Notifications",
    "Get a push alert when the battery runs low or the frame stops "
    "checking in.":
        "Recevez une alerte quand la batterie est faible ou que le "
        "cadre arrête de se connecter.",

    # --- The write-only topic-URL field (D-26 amended: never rendered
    #     back, status row instead of a masked value) -------------------
    "Configured": "Configuré",
    "Not configured": "Non configuré",
    "Push topic URL": "URL du sujet de notification",
    "Paste your ntfy.sh topic URL (or a self-hosted one). Stored on "
    "the server and never shown back here — pasting a new one "
    "replaces the old.":
        "Collez l’URL de votre sujet ntfy.sh (ou d’un serveur ntfy "
        "personnel). Stockée sur le serveur et jamais réaffichée ici — "
        "en coller une nouvelle remplace l’ancienne.",
    "Replace the URL": "Remplacer l’URL",

    # --- The two checkboxes (D-26) ---------------------------------------
    "Battery low": "Batterie faible",
    "Frame silent": "Cadre silencieux",

    # --- "Send a test" and its two flash outcomes (D-26) -----------------
    "Send a test": "Envoyer un test",
    "Test notification sent.": "Notification de test envoyée.",
    "Couldn't reach that topic — check the URL.":
        "Impossible d’atteindre ce sujet — vérifiez l’URL.",
}
