# -*- coding: utf-8 -*-
"""French strings for the Flight colours section
(companion/settings/rules.py's rule_form_html()/_rule_row_html()
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
    # A separate mapping from the technical titles above, which keep
    # their existing display.py translations unchanged.
    "rules.flight": "Vol",
    "rules.aircraft": "Avion",
    "rules.airline": "Compagnie",

    "rules.remove": "Retirer",
    "rules.edit": "Modifier",
    "rules.edit_rule_aria": "Modifier l’allure spéciale pour %s",
    "rules.remove_this_special_look": "Supprimer ce look spécial ?",
    "rules.remove_special_look_body":
        "%s retrouve votre look habituel. Vous pouvez rajouter le look spécial à tout moment.",
    "rules.remove_special_look": "Supprimer le look spécial",
    "rules.keep_special_look": "Garder le look spécial",
    "rules.remove_rule_aria": "Supprimer le look spécial pour %s",
    "rules.recent": "Récents :",
}
