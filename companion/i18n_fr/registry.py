# -*- coding: utf-8 -*-
"""French strings for server/device_config.py's THEMES/RUNWAYS
registries and companion/screens.py's screen label.

`theme_label()`/`runway_label()` and each screen's "label" field
return plain English registry text meant for people to read, distinct
from the theme/runway/screen ids, which are identifiers and are never
translated. config_page.py and history_page.py declare the Message
that wraps the label at their own display site (each in its own file's
scope); this module only carries each id's French translation. Kept as
one cross-page catalogue, since the same theme/runway/screen label can
reach the screen from several pages.

The runway labels are migrated onto stable ids (history_page.py already
declares their Message); the theme names and the screen label stay
legacy English-keyed CATALOG entries for now — their only consumer,
companion/pages/config_page.py, has not migrated yet, so there is
nowhere in this phase's scope to declare their Message. A later plan
converts them once config_page.py does.

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

    # --- Screen label (companion/screens.py's per-screen "label") -----
    "Plane frame": "Cadre avion",
}

MESSAGES = {
    # --- Runway labels (server/device_config.py's RUNWAYS) ------------
    "registry.runway_3_07_25": "Piste 3 (07/25)",
    "registry.runway_4_06_24": "Piste 4 (06/24)",
    "registry.runway_2_02_20": "Piste 2 (02/20)",
}
