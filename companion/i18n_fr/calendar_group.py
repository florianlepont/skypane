# -*- coding: utf-8 -*-
"""French strings for the Calendar row's connection block
(companion/settings/calendar.py's _calendar_connection_html()), keyed
by stable message id (see companion/i18n.py's Message/msg()). Every id
is declared at its own display site in companion/settings/calendar.py —
this module only carries each id's French translation.

"Calendar", its feed-URL field/hint, "Cancel", "Theme" and the
disconnect action's own strings are deliberately absent, declared
instead in sibling modules the auto-merge package would otherwise
reject as duplicate ids.
"""

MESSAGES = {
    "calendar_group.how_it_works": "Comment ça marche",
    "calendar_group.it_can_only_colour_a_flight_that_happens_to_be":
        "Il ne peut colorer qu’un vol déjà affiché à l’écran — il ne "
        "suit ni n’annonce rien de lui-même. S’applique lors de la "
        "prochaine vérification programmée du cadre, pas immédiatement.",
    "calendar_group.connected": "Connecté",
    "calendar_group.not_connected": "Non connecté",
    "calendar_group.1_upcoming_flight_checked": "1 vol à venir · vérifié %s",
    "calendar_group.upcoming_flights_checked": "%d vols à venir · vérifié %s",
    "calendar_group.the_feed_could_not_be_read": "Impossible de lire le flux",
    "calendar_group.connect_calendar": "Connecter le calendrier",
    "calendar_group.replace_the_feed_url": "Remplacer l’URL du flux",
    "calendar_group.replace": "Remplacer",
    "calendar_group.disconnect": "Déconnecter",
}
