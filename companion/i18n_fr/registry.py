# -*- coding: utf-8 -*-
"""French strings for server/device_config.py's THEMES/RUNWAYS
registries and companion/screens.py's screen label.

`theme_label()`/`runway_label()` and each screen's "label" field
return plain English registry text meant for people to read, distinct
from the theme/runway/screen ids, which are identifiers and are never
translated. companion/settings/theme.py, companion/settings/runway_led.py
and companion/pages/config_page.py declare the Message that wraps the
label at their own display site (each in its own file's scope); this
module only carries each id's French translation. Kept as one
cross-page catalogue, since the same theme/runway/screen label can
reach the screen from several pages.

Copy follows sentence case, the typographic apostrophe (U+2019, never
a straight quote), and a non-breaking space (U+00A0) before
":" ";" "?" "!". None of the strings below need one.
"""

MESSAGES = {
    # --- Theme names (server/device_config.py's THEMES, in registry
    #     order); the Message for each is companion/settings/theme.py's
    #     own _THEME_LABEL_MESSAGES ------------------------------------
    "registry.white": "Blanc",
    "registry.black": "Noir",
    "registry.grey": "Gris",
    "registry.yellow": "Jaune",
    "registry.yellow_light": "Jaune clair",
    "registry.red": "Rouge",
    "registry.red_light": "Rouge clair",
    "registry.green": "Vert",
    "registry.green_light": "Vert clair",
    "registry.blue": "Bleu",
    "registry.blue_light": "Bleu clair",
    "registry.band_blue": "Bande bleue",
    "registry.band_blue_light": "Bande bleue claire",
    "registry.band_green_light": "Bande verte claire",
    "registry.band_red": "Bande rouge",
    "registry.band_black": "Bande noire",
    "registry.band_blue_field": "Bande bleue pleine",
    "registry.band_red_field": "Bande rouge pleine",

    # --- Runway labels (server/device_config.py's RUNWAYS); the
    #     Message for each is companion/pages/history_page.py's and
    #     companion/settings/runway_led.py's own _RUNWAY_LABEL_MESSAGES
    "registry.runway_3_07_25": "Piste 3 (07/25)",
    "registry.runway_4_06_24": "Piste 4 (06/24)",
    "registry.runway_2_02_20": "Piste 2 (02/20)",

    # --- Screen label (companion/screens.py's per-screen "label"); the
    #     Message is companion/pages/config_page.py's own
    #     _SCREEN_LABEL_MESSAGES -------------------------------------
    "registry.plane_frame": "Cadre avion",
}
