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
    # A separate mapping from the technical titles above, which keep
    # their existing display.py translations unchanged.
    "rules.flight": "Vol",
    "rules.aircraft": "Avion",
    "rules.airline": "Compagnie",

    "rules.remove": "Retirer",
    "rules.remove_this_rule": "Retirer cette règle ?",
    "rules.recent": "Récents :",
}
