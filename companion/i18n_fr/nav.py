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

    # The bottom tab bar's fifth cell; its <details> sheet holds the
    # Advanced group's two destinations.
    "nav.more": "Plus",

    "nav.language": "Langue",
    "nav.theme": "Thème",

    # The hamburger toggle's accessible name, describing what the
    # panel holds, and the nav Health dot's hidden suffix.
    "nav.account_and_preferences": "Compte et préférences",
    "nav.attention_needed": " — attention requise",

    # Fully French. "Activées"/"désactivées" matches this app's
    # existing "Activer"/"Désactiver" verb pair.
    "nav.screen_on": "Écran allumé",
    "nav.screen_off": "Écran éteint",
    "nav.quiet_hours_on": "Heures calmes activées",
    "nav.quiet_hours_off": "Heures calmes désactivées",
    "nav.screen_and_quiet_hours_status_go_to_home":
        "État de l’écran et des heures calmes — aller à l’accueil",

    "nav.primary_navigation": "Navigation principale",

    "nav.auto": "Automatique",
    "nav.light": "Clair",
    "nav.dark": "Sombre",
}
