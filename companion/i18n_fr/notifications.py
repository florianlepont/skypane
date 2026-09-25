# -*- coding: utf-8 -*-
"""French strings for the Notifications group
(companion/pages/config_page.py's notifications_group()/
notifications_test_section()). Every key is the exact English
source string a call site passes to companion.i18n.t(), including
any "%s" placeholder shape.

Deliberately absent: the four notification transition bodies and
the "Send a test" button's fixed title/body pair — all six already
have their French forms in server/notify.py's own _BODY_FR dict,
read through that module's body_for_lang(), never through
companion.i18n.t().

Copy follows sentence case, the typographic apostrophe (U+2019,
never a straight quote), and a non-breaking space (U+00A0) before
":" ";" "?" "!".
"""

CATALOG = {
    "Notifications": "Notifications",
    "Get a push alert about battery or connection issues.":
        "Recevez une alerte pour les problèmes de batterie ou de "
        "connexion.",

    "Configured": "Configuré",
    "Not configured": "Non configuré",
    "Push topic URL": "URL du sujet de notification",
    "Paste your ntfy.sh topic URL (or a self-hosted one).":
        "Collez l’URL de votre sujet ntfy.sh (ou d’un serveur ntfy "
        "personnel).",
    "Stored on the server and never shown back here — pasting a new "
    "one replaces the old.":
        "Stockée sur le serveur et jamais réaffichée ici — en coller "
        "une nouvelle remplace l’ancienne.",
    "Replace the URL": "Remplacer l’URL",

    "Battery low": "Batterie faible",
    "Frame silent": "Cadre silencieux",

    "Send a test": "Envoyer un test",
    "Test notification sent.": "Notification de test envoyée.",
    "Couldn't reach that topic — check the URL.":
        "Impossible d’atteindre ce sujet — vérifiez l’URL.",
}
