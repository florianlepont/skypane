# -*- coding: utf-8 -*-
"""French strings for the Calendar row's connection block
(companion/pages/config_page.py's _calendar_connection_html()).

"Calendar", its feed-URL field/hint, "Cancel", "Theme" and the
disconnect action's own strings are deliberately absent, defined
instead in sibling modules the auto-merge package would otherwise
reject as duplicate keys.
"""

CATALOG = {
    "How it works": "Comment ça marche",
    "It can only colour a flight that happens to be on screen — it "
    "does not track or announce anything on its own. Applies on the "
    "frame's next scheduled poll, not immediately.":
        "Il ne peut colorer qu’un vol déjà affiché à l’écran — il ne "
        "suit ni n’annonce rien de lui-même. S’applique lors de la "
        "prochaine vérification programmée du cadre, pas immédiatement.",
    "Connected": "Connecté",
    "Not connected": "Non connecté",
    "1 upcoming flight · checked %s": "1 vol à venir · vérifié %s",
    "%d upcoming flights · checked %s": "%d vols à venir · vérifié %s",
    "The feed could not be read": "Impossible de lire le flux",
    "Connect calendar": "Connecter le calendrier",
    "Replace the feed URL": "Remplacer l’URL du flux",
    "Replace": "Remplacer",
    "Disconnect": "Déconnecter",
}
