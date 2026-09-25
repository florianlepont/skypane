# -*- coding: utf-8 -*-
"""French strings for server/device_config.py's THEMES/RUNWAYS
registries and companion/screens.py's screen label.

`theme_label()`/`runway_label()` and each screen's "label" field
return plain English registry text meant for people to read, distinct
from the theme/runway/screen ids, which are identifiers and are never
translated. config_page.py and history_page.py call i18n.t() on the
label at the display site; this module supplies the French text those
calls resolve to. Kept as one cross-page catalogue, since the same
theme/runway/screen label can reach the screen from several pages.

Copy follows sentence case, the typographic apostrophe (U+2019, never
a straight quote), and a non-breaking space (U+00A0) before
":" ";" "?" "!". None of the strings below need one.
"""

CATALOG = {
    # --- Theme names (server/device_config.py's THEMES, in registry order)
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
