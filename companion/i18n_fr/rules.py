# -*- coding: utf-8 -*-
"""French strings for the Flight colours section
(companion/pages/config_page.py's _rule_add_form_html()/_rule_row_html()
and frame_colours_section_html()'s rules usage panel). Every key is the
exact English source string a call site passes to companion.i18n.t(),
including any "%s" placeholder shape.

Deliberately absent: "Match by", "Value", "Add rule", "Callsign",
"ICAO24 hex", "Callsign prefix" and "Theme" — all still defined in
companion/i18n_fr/display.py or companion/i18n_fr/nav.py, since the
auto-merge package raises ValueError on a duplicate key across sibling
modules. The value input's placeholder and every rule's own key/theme
data are never translated (identifiers/data, not copy).

Copy follows sentence case, the typographic apostrophe (U+2019, never
a straight quote), and a non-breaking space (U+00A0) before ":"
";" "?" "!".
"""

CATALOG = {
    "Give one flight, one aircraft or one airline its own theme.":
        "Donnez son propre thème à un vol, un avion ou une compagnie.",
    "How rules combine": "Comment les règles se combinent",
    "The most specific match wins — a flight rule beats an aircraft "
    "rule, which beats an airline rule — and adding a key that's "
    "already in use replaces the existing rule for it.":
        "La règle la plus précise l’emporte — un vol l’emporte sur un "
        "avion, qui l’emporte sur une compagnie — et l’ajout d’une clé "
        "déjà utilisée remplace la règle existante pour cette clé.",

    # A separate mapping from the technical titles above, which keep
    # their existing display.py translations unchanged.
    "Flight": "Vol",
    "Aircraft": "Avion",
    "Airline": "Compagnie",

    "No flight colours yet.": "Encore aucune couleur de vol.",
    "Add one above to give a flight, aircraft or airline its own theme.":
        "Ajoutez-en une ci-dessus pour donner son propre thème à un vol, "
        "un avion ou une compagnie.",
    "Remove": "Retirer",
    "Remove this rule?": "Retirer cette règle ?",
    "Recent:": "Récents :",
}
