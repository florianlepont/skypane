# -*- coding: utf-8 -*-
"""French strings for the Flight colours section
(companion/settings/rules.py's _rule_add_form_html()/_rule_row_html()
and rules_usage_row_html()'s rules usage panel), keyed by stable
message id (see companion/i18n.py's Message/msg()). Every id is
declared at its own display site in companion/settings/rules.py — this
module only carries each id's French translation.

Deliberately absent: "Match by", "Value", "Add rule", "Callsign",
"ICAO24 hex", "Callsign prefix" and "Theme" — all still declared in
companion/i18n_fr/display.py or companion/i18n_fr/nav.py, since the
auto-merge package raises ValueError on a duplicate id across sibling
modules. The value input's placeholder and every rule's own key/theme
data are never translated (identifiers/data, not copy).

Copy follows sentence case, the typographic apostrophe (U+2019, never
a straight quote), and a non-breaking space (U+00A0) before ":"
";" "?" "!".
"""

MESSAGES = {
    "rules.give_one_flight_one_aircraft_or_one_airline_its":
        "Donnez son propre thème à un vol, un avion ou une compagnie.",
    "rules.how_rules_combine": "Comment les règles se combinent",
    "rules.the_most_specific_match_wins_a_flight_rule":
        "La règle la plus précise l’emporte — un vol l’emporte sur un "
        "avion, qui l’emporte sur une compagnie — et l’ajout d’une clé "
        "déjà utilisée remplace la règle existante pour cette clé.",

    # A separate mapping from the technical titles above, which keep
    # their existing display.py translations unchanged.
    "rules.flight": "Vol",
    "rules.aircraft": "Avion",
    "rules.airline": "Compagnie",

    "rules.no_flight_colours_yet": "Encore aucune couleur de vol.",
    "rules.add_one_above_to_give_a_flight_aircraft_or":
        "Ajoutez-en une ci-dessus pour donner son propre thème à un vol, "
        "un avion ou une compagnie.",
    "rules.remove": "Retirer",
    "rules.remove_this_rule": "Retirer cette règle ?",
    "rules.recent": "Récents :",
}
