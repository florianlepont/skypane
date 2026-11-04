# -*- coding: utf-8 -*-
"""French strings for the nav labels and the nav-footer switches.

The nav labels are fixed: Accueil, Historique des vols, Lieu et détection,
Personnalisation, Collection de compagnies, État, Appareil, Versions. "FR"/"EN" are identifiers, not
translated, and therefore have no entry here.

Copy follows sentence case, the typographic apostrophe (U+2019,
never a straight quote), and a non-breaking space (U+00A0) before
":" ";" "?" "!".

Also carries the one nav-landmark accessible name shared by
companion/ui_nav.py's sidebar_nav()/_mobile_nav_html(), and the
theme-picker's three segment labels — grouped here because the
theme picker sits in this same sidebar/mobile-nav footer region.

Every entry is migrated onto a stable message id: the source-side
Message is declared where the English constant already lives
(companion/ui_base.py, companion/ui_nav.py), never here — this module
only carries each id's French translation.
"""

MESSAGES = {
    "nav.home": "Accueil",
    "nav.flight_history": "Historique des vols",
    "nav.flights_short": "Vols",
    "nav.detection": "Lieu et détection",
    "nav.detection_short": "Lieu",
    "nav.personalisation": "Personnalisation",
    "nav.display_short": "Style",
    "nav.airline_collection": "Collection de compagnies",
    "nav.airline_editor": "Éditeur de compagnies",
    "nav.frame_tools": "Outils du cadre",
    "nav.health": "État",
    "nav.device": "Appareil",
    "nav.update": "Versions",
    "nav.locations": "Lieux",

    # The bottom tab bar's fifth cell; its <details> sheet holds the
    # destinations that do not fit in the bar.
    "nav.more": "Plus",

    # The Console bar's short label for the Audit log page, and the space
    # switch between the Console and the administrator's own views.
    "nav.audit_short": "Audit",
    "nav.airlines_short": "Compagnies",
    "nav.my_frame": "Mon cadre",
    "nav.console": "Console",
    "nav.space": "Espace",
    "nav.switch_to_personal": "Passer aux pages de votre cadre",
    "nav.switch_to_console": "Passer à la console d’administration",

    # The strip an administrator sees on a personal page of someone else's frame.
    "nav.frame_notice_viewing": "Cadre de %s en consultation",
    "nav.frame_notice_back": "Retour à la flotte",

    "nav.language": "Langue",
    "nav.theme": "Thème",

    # The hamburger toggle's accessible name, describing what the
    # panel holds, and the nav Health dot's hidden suffix.
    "nav.account_menu": "Menu du compte",
    "nav.attention_needed": " — attention requise",

    "nav.primary_navigation": "Navigation principale",

    "nav.auto": "Auto",
    "nav.auto_full": "Auto (suit le système)",
    "nav.light": "Clair",
    "nav.dark": "Sombre",

    # The frame tile strip above the page title (two or more frames).
    "nav.frame_strip_aria": "Vos cadres",
    "nav.frame_tile_seen": "Vu %s",
    "nav.frame_tile_add": "Ajouter un écran",
    "nav.device_default_name": "Cadre d’Orly",
    "nav.skip_to_content": "Aller au contenu",
}
