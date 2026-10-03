# -*- coding: utf-8 -*-
"""French strings for server/device_config.py's RUNWAYS registry and
companion/screens.py's screen label. Theme names are not shown here:
the Display page describes a theme by its look (companion/i18n_fr/
look.py).

`runway_label()` and each screen's "label" field return plain English
registry text meant for people to read, distinct from the runway/screen
ids, which are identifiers and are never translated.
companion/settings/runway_led.py and companion/pages/config_page.py
declare the Message that wraps the
label at their own display site (each in its own file's scope); this
module only carries each id's French translation. Kept as one
cross-page catalogue, since the same runway/screen label can
reach the screen from several pages.

Copy follows sentence case, the typographic apostrophe (U+2019, never
a straight quote), and a non-breaking space (U+00A0) before
":" ";" "?" "!". None of the strings below need one.
"""

MESSAGES = {
    # --- Runway labels (server/device_config.py's RUNWAYS); the
    #     Message for each is companion/pages/history_page.py's and
    #     companion/settings/runway_led.py's own _RUNWAY_LABEL_MESSAGES
    "registry.runway_3_07_25": "Piste 3 (07/25)",
    "registry.runway_4_06_24": "Piste 4 (06/24)",
    "registry.runway_2_02_20": "Piste 2 (02/20)",

    # --- Screen label (companion/screens.py's per-screen "label"); the
    #     Message is companion/pages/config_page.py's own
    #     _SCREEN_LABEL_MESSAGES -------------------------------------
}
