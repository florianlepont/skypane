# -*- coding: utf-8 -*-
"""companion/i18n_fr/registry.py — French strings for server/device_
config.py's THEMES/RUNWAYS registries and companion/screens.py's screen
label (Polish fix 5, D-05).

One sibling module of the companion/i18n_fr package (see that
package's __init__.py for the auto-merge/duplicate-key contract this
module participates in).

`server/device_config.py`'s `theme_label()`/`runway_label()` and
`companion/screens.py`'s per-screen `"label"` field return plain
English registry text meant for people to read (theme names, runway
names, the screen's own name) — distinct from the theme/runway/screen
*ids*, which are identifiers (D-05) and are never translated and never
changed by this module. `companion/pages/config_page.py` and
`companion/pages/history_page.py` call `i18n.t()` on the label AT THE
DISPLAY SITE, after reading it off the registry; this module supplies
the French text those `t()` calls resolve to. Kept as ONE cross-page
catalogue here (rather than duplicated per consuming page module)
because a theme/runway/screen label is a single cross-page concern —
the same value can reach the screen from Display, Home, Flights or
Health, and a single source of French truth is what keeps all of them
in step.

Copy follows D-09: sentence case, the typographic apostrophe (U+2019,
never a straight quote), and a non-breaking space (U+00A0) before
":" ";" "?" "!". None of the strings below need one.
"""

CATALOG = {
    # --- Theme names (server/device_config.py's THEMES, in registry
    # order) ----------------------------------------------------------
    "White": "Blanc",
    "Black": "Noir",
    "Grey": "Gris",
    "Yellow": "Jaune",
    "Yellow Light": "Jaune clair",
    "Red": "Rouge",
    "Red Light": "Rouge clair",
    "Green": "Vert",
    "Green Light": "Vert clair",
    "Blue": "Bleu",
    "Blue Light": "Bleu clair",
    "Band Blue": "Bande bleue",
    "Band Blue Light": "Bande bleue claire",
    "Band Green Light": "Bande verte claire",
    "Band Red": "Bande rouge",
    "Band Black": "Bande noire",
    "Band Blue Field": "Bande bleue pleine",
    "Band Red Field": "Bande rouge pleine",

    # --- Runway labels (server/device_config.py's RUNWAYS) ------------
    "Runway 3 (07/25)": "Piste 3 (07/25)",
    "Runway 4 (06/24)": "Piste 4 (06/24)",
    "Runway 2 (02/20)": "Piste 2 (02/20)",

    # --- Screen label (companion/screens.py's per-screen "label") -----
    "Plane frame": "Cadre avion",
}
