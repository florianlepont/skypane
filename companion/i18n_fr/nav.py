# -*- coding: utf-8 -*-
"""French strings for the nav labels and the nav-footer switches.

The seven nav labels are fixed: Accueil, Affichage, Vols, Compagnies,
Avancé, État, Appareil. "FR"/"EN" are identifiers, not translated,
and therefore have no entry here.

Copy follows sentence case, the typographic apostrophe (U+2019,
never a straight quote), and a non-breaking space (U+00A0) before
":" ";" "?" "!".

Also carries the one nav-landmark accessible name shared by
companion/layout.py's sidebar_nav()/_mobile_nav_html(), and the
theme-picker's three segment labels — grouped here because the
theme picker sits in this same sidebar/mobile-nav footer region.
"""

CATALOG = {
    "Home": "Accueil",
    "Display": "Affichage",
    "Flights": "Vols",
    "Airlines": "Compagnies",
    "Advanced": "Avancé",
    "Health": "État",
    "Device": "Appareil",

    # The bottom tab bar's fifth cell; its <details> sheet holds the
    # Advanced group's two destinations.
    "More": "Plus",

    "Language": "Langue",
    "Theme": "Thème",

    # The hamburger toggle's accessible name, describing what the
    # panel holds, and the nav Health dot's hidden suffix.
    "Account and preferences": "Compte et préférences",
    " — attention needed": " — attention requise",

    # Fully French. "Activées"/"désactivées" matches this app's
    # existing "Activer"/"Désactiver" verb pair.
    "Screen on": "Écran allumé",
    "Screen off": "Écran éteint",
    "Quiet hours on": "Heures calmes activées",
    "Quiet hours off": "Heures calmes désactivées",
    "Screen and quiet hours status — go to Home":
        "État de l’écran et des heures calmes — aller à l’accueil",

    "Primary navigation": "Navigation principale",

    "Auto": "Automatique",
    "Light": "Clair",
    "Dark": "Sombre",
}
