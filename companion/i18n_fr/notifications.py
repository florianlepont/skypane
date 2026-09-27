# -*- coding: utf-8 -*-
"""French strings for the Notifications group
(companion/settings/notifications.py's notifications_group()/
notifications_test_section()), keyed by stable message id (see
companion/i18n.py's Message/msg()). Every id is declared at its own
display site in companion/settings/notifications.py — this module only
carries each id's French translation.

Deliberately absent: the four notification transition bodies and
the "Send a test" button's fixed title/body pair — all six already
have their French forms in server/notify.py's own _BODY_FR dict,
read through that module's body_for_lang(), never through
companion.i18n.t().

Copy follows sentence case, the typographic apostrophe (U+2019,
never a straight quote), and a non-breaking space (U+00A0) before
":" ";" "?" "!".
"""

MESSAGES = {
    "notifications.notifications": "Notifications",
    "notifications.get_a_push_alert_about_battery_or_connection":
        "Recevez une alerte pour les problèmes de batterie ou de "
        "connexion.",

    "notifications.configured": "Configuré",
    "notifications.not_configured": "Non configuré",
    "notifications.push_topic_url": "URL du sujet de notification",
    "notifications.paste_your_ntfy_sh_topic_url_or_a_self_hosted":
        "Collez l’URL de votre sujet ntfy.sh (ou d’un serveur ntfy "
        "personnel).",
    "notifications.stored_on_the_server_and_never_shown_back_here":
        "Stockée sur le serveur et jamais réaffichée ici — en coller "
        "une nouvelle remplace l’ancienne.",
    "notifications.replace_the_url": "Remplacer l’URL",

    "notifications.battery_low": "Batterie faible",
    "notifications.frame_silent": "Cadre silencieux",

    "notifications.send_a_test": "Envoyer un test",
    "notifications.test_notification_sent": "Notification de test envoyée.",
    "notifications.couldn_t_reach_that_topic_check_the_url":
        "Impossible d’atteindre ce sujet — vérifiez l’URL.",
}
