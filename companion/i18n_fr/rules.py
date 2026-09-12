# -*- coding: utf-8 -*-
"""companion/i18n_fr/rules.py — French strings for the rebuilt Flight
colours section (companion/pages/config_page.py's _rule_add_form_html()/
_rule_row_html()/_rules_section_html(), D-15a..e), 20-09-PLAN.md Task 3.

One sibling module of the companion/i18n_fr package (see that
package's __init__.py for the auto-merge/duplicate-key contract this
module participates in). Every key here is the exact English source
string a call site in companion/pages/config_page.py passes to
companion.i18n.t() — including any "%s" placeholder shape, unchanged.

Deliberately absent: "Match by", "Value", "Add rule", "Callsign",
"ICAO24 hex", "Callsign prefix" and "Theme" — all still defined in
companion/i18n_fr/display.py (Match by/Value/Add rule/the three
technical titles, from 20-07-PLAN.md's own Rules section, unchanged text
and unchanged meaning: D-15b keeps every one of these exact English
strings, only the surrounding markup changed) or companion/i18n_fr/
nav.py ("Theme") — the auto-merge package raises ValueError on a
duplicate key across sibling modules (see companion/i18n_fr/__init__.py).
The value input's placeholder ("AFR1234") and every rule's own key/theme
data are never translated (identifiers/data, not copy, D-05).

Copy follows D-09: sentence case, the typographic apostrophe (U+2019,
never a straight quote), and a non-breaking space (U+00A0) before ":"
";" "?" "!". Every value below matching 20-UI-SPEC.md's Copywriting
Contract Section D/H is copied verbatim from that table.
"""

CATALOG = {
    # --- Heading and caption (D-15a) -------------------------------------
    "Flight colours": "Couleurs de vol",
    "Give one flight, one aircraft or one airline its own theme.":
        "Donnez son propre thème à un vol, un avion ou une compagnie.",

    # --- "How rules combine" disclosure (D-15a) -------------------------
    "How rules combine": "Comment les règles se combinent",
    "The most specific match wins — a flight rule beats an aircraft "
    "rule, which beats an airline rule — and adding a key that's "
    "already in use replaces the existing rule for it.":
        "La règle la plus précise l’emporte — un vol l’emporte sur un "
        "avion, qui l’emporte sur une compagnie — et l’ajout d’une clé "
        "déjà utilisée remplace la règle existante pour cette clé.",

    # --- The segmented "Match by" control's plain-language labels
    #     (D-15b) — a SEPARATE mapping from the technical titles above,
    #     which keep their existing display.py translations unchanged.
    "Flight": "Vol",
    "Aircraft": "Avion",
    "Airline": "Compagnie",

    # --- The rule list (D-15c/d) -----------------------------------------
    "No flight colours yet.": "Encore aucune couleur de vol.",
    "Add one above to give a flight, aircraft or airline its own theme.":
        "Ajoutez-en une ci-dessus pour donner son propre thème à un vol, "
        "un avion ou une compagnie.",
    "Remove": "Retirer",
    "Remove this rule?": "Retirer cette règle ?",

    # D-17 (21-01-PLAN.md Task 2): the collapsed disclosure sentence's
    # French entry is deleted in this same commit as its English
    # constant (RULES_HOW_RULES_COMBINE_SIMPLE, companion/pages/
    # config_page.py) — the display mode that selected it is gone.

    # --- Suggestion chips (D-15e) ----------------------------------------
    "Recent:": "Récents :",
}
