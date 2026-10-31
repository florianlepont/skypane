# -*- coding: utf-8 -*-
"""French strings for the nav labels and the nav-footer switches.

The eight nav labels are fixed: Accueil, Affichage, Vols, Compagnies,
Avancé, État, Appareil, Mise à jour. "FR"/"EN" are identifiers, not
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
    "nav.display": "Affichage",
    "nav.flights": "Vols",
    "nav.airlines": "Compagnies",
    "nav.advanced": "Avancé",
    "nav.health": "État",
    "nav.device": "Appareil",
    "nav.update": "Mise à jour",
    "nav.locations": "Lieux",

    # The bottom tab bar's fifth cell; its <details> sheet holds the
    # Advanced group's two destinations.
    "nav.more": "Plus",

    "nav.language": "Langue",
    "nav.theme": "Thème",

    # The hamburger toggle's accessible name, describing what the
    # panel holds, and the nav Health dot's hidden suffix.
    "nav.account_and_preferences": "Compte et préférences",
    "nav.attention_needed": " — attention requise",

    "nav.primary_navigation": "Navigation principale",

    "nav.auto": "Auto",
    "nav.auto_full": "Auto (suit le système)",
    "nav.light": "Clair",
    "nav.dark": "Sombre",

    # The device selector above the page title (several devices only).
    "nav.device_selector_label": "Cadre",
    "nav.device_selector_go": "Afficher le cadre",
    "nav.device_never_seen": "pas encore vu",
    "nav.device_offline": "hors ligne",
    "nav.device_pill_never_seen": "Pas encore vu",
    "nav.device_pill_offline": "Hors ligne",
    "nav.device_default_name": "Cadre d’Orly",
}
