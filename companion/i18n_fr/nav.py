# -*- coding: utf-8 -*-
"""French strings for the nav labels and the nav-footer switches.

The nav labels are fixed: Accueil, Historique des vols, Lieu et détection,
Style, Compagnies, État, Appareil, Versions. "FR"/"EN" are identifiers, not
translated, and therefore have no entry here.

Copy follows sentence case, the typographic apostrophe (U+2019,
never a straight quote), and a non-breaking space (U+00A0) before
":" ";" "?" "!".

Also carries the one nav-landmark accessible name shared by
companion/ui_nav.py's sidebar_nav()/_tab_bar_html(), and the
theme-picker's three segment labels — grouped here because the
theme picker sits in this same sidebar footer region.

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
    "nav.personalisation": "Style",
    "nav.airline_collection": "Compagnies",
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
    "nav.audit_short": "Journal",
    "nav.airlines_short": "Éditeur",
    "nav.users_short": "Équipe",
    "nav.my_frame": "Mon cadre",
    "nav.console": "Console",
    "nav.console_subtitle": "Flotte, utilisateurs, audit",
    "nav.space": "Espace",
    "nav.switch_to_personal": "Passer aux pages de votre cadre",
    "nav.switch_to_console": "Passer à la console d’administration",

    # The strip an administrator sees on a personal page of someone else's frame.
    "nav.frame_notice_viewing": "Cadre de %s en consultation",
    "nav.frame_notice_back": "Retour à la flotte",

    "nav.language": "Langue",
    "nav.theme": "Thème",

    # The nav Health dot's hidden suffix.
    "nav.attention_needed": " — attention requise",

    "nav.primary_navigation": "Navigation principale",

    "nav.auto": "Auto",
    "nav.auto_full": "Auto (suit le système)",
    "nav.light": "Clair",
    "nav.dark": "Sombre",

    # The frame button in the top bar and its popover.
    "nav.frame_strip_aria": "Vos cadres",
    "nav.frame_tile_seen": "Vu %s",
    "nav.frame_tile_add": "Ajouter un cadre",
    "nav.frame_button": "Choisir un cadre",
    "nav.device_default_name": "Cadre d’Orly",
    "nav.skip_to_content": "Aller au contenu",
}
