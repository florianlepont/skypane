# -*- coding: utf-8 -*-
"""companion/i18n_fr/calendar_group.py — French strings for the rebuilt
Calendar card (companion/pages/config_page.py's calendar_group()/
calendar_connect_section(), D-14a..d), 20-09-PLAN.md Task 1.

One sibling module of the companion/i18n_fr package (see that
package's __init__.py for the auto-merge/duplicate-key contract this
module participates in). Every key here is the exact English source
string a call site in companion/pages/config_page.py passes to
companion.i18n.t() — including any "%d"/"%s" placeholder shape,
unchanged.

Deliberately absent: "Calendar" (the card's own heading), "Calendar
feed URL", its hint sentence, "Cancel", and every one of the disconnect
action's own strings (checkbox label, confirm question/heading/
sentence/button text) — all still defined in companion/i18n_fr/
display.py from 20-07-PLAN.md, unchanged by this plan and still the
exact strings the retained, unedited calendar_disconnect_section()/
calendar_disconnect_confirm_page() call t() with (the auto-merge
package raises ValueError on a duplicate key across sibling modules —
see companion/i18n_fr/__init__.py). "Theme" is also absent — companion/
i18n_fr/nav.py already owns that exact key.

Copy follows D-09: sentence case, the typographic apostrophe (U+2019,
never a straight quote), and a non-breaking space (U+00A0) before ":"
";" "?" "!". Every value below matching 20-UI-SPEC.md's Copywriting
Contract Section C/H is copied verbatim from that table.
"""

CATALOG = {
    # --- The card's one-line caption (D-14a) ----------------------------
    "Flights from your calendar get their own colour on the frame.":
        "Les vols de votre calendrier ont leur propre couleur sur le "
        "cadre.",

    # --- "How it works" disclosure (D-14a) ------------------------------
    "How it works": "Comment ça marche",
    "It can only colour a flight that happens to be on screen — it "
    "does not track or announce anything on its own. Applies on the "
    "frame's next scheduled poll, not immediately.":
        "Il ne peut colorer qu’un vol déjà affiché à l’écran — il ne "
        "suit ni n’annonce rien de lui-même. S’applique lors de la "
        "prochaine vérification programmée du cadre, pas immédiatement.",

    # --- The status row (D-14b) ------------------------------------------
    "Connected": "Connecté",
    "Not connected": "Non connecté",
    "%d upcoming flights · checked %s": "%d vols à venir · vérifié %s",
    "The feed could not be read": "Impossible de lire le flux",

    # --- The Connect/Replace mini-form (D-14c) --------------------------
    "Connect calendar": "Connecter le calendrier",
    "Replace the feed URL": "Remplacer l’URL du flux",

    # D-17 (21-01-PLAN.md Task 2): the "How it works" disclosure's
    # collapsed one-sentence French entry is deleted in this same
    # commit as its English source constant in companion/pages/
    # config_page.py — the display mode that selected it is gone.
}
