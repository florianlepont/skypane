# -*- coding: utf-8 -*-
"""companion/i18n_fr/nav.py — French strings for the nav labels and the
nav-footer switches (D-01/D-04/D-05/D-09, 20-01-PLAN.md Task 1).

One sibling module of the companion/i18n_fr package (see that
package's __init__.py for the auto-merge/duplicate-key contract this
module participates in).

The seven nav labels are fixed verbatim by D-09 (20-CONTEXT.md):
Accueil, Affichage, Vols, Compagnies, Avancé, État, Appareil. The
footer strings below are 20-UI-SPEC.md's Copywriting Contract
Section F. "FR"/"EN" are identifiers, not translated, and therefore
have no entry here — companion/layout.py's D-05 comment records the
same exclusion.

Copy follows D-09: sentence case, the typographic apostrophe (U+2019,
never a straight quote), and a non-breaking space (U+00A0) before
":" ";" "?" "!".
"""

CATALOG = {
    # --- Nav labels (companion/layout.py's NAV_GROUPS / NAV_TABS) ------
    "Home": "Accueil",
    "Display": "Affichage",
    "Flights": "Vols",
    "Airlines": "Compagnies",
    "Advanced": "Avancé",
    "Health": "État",
    "Device": "Appareil",

    # --- Nav-footer switches (20-UI-SPEC.md §F) -------------------------
    # D-17 (21-01-PLAN.md Task 1): "Simple mode"/"Simple"/"Full" are
    # deleted in this same commit as layout._mode_form_html() itself —
    # the simple/full mode switch these three strings backed is gone,
    # so keeping their French entries would orphan them and fail
    # test_i18n.py's dead-translation check (Pitfall 5/R-13).
    "Language": "Langue",
    "Theme": "Thème",

    # --- The hamburger toggle's fixed accessible name, and the nav
    #     Health dot's visually-hidden suffix (20-12-PLAN.md Task 1: a
    #     real D-05 gap found by the completeness harness — both render
    #     sites had been left un-wrapped since their own introducing
    #     plan) --------------------------------------------------------
    "Open menu": "Ouvrir le menu",
    " — attention needed": " — attention requise",

    # --- The nav state reminder (D-03/R-04, 21-04-PLAN.md Task 2) -------
    # Fully French — R-04 corrects 21-CONTEXT.md D-03's own "Heures
    # calmes off" drafting shorthand, which left the second word
    # untranslated. "Activées"/"désactivées" agrees with the verb pair
    # this app already ships for the same toggle ("Activer"/
    # "Désactiver" — companion/i18n_fr/display.py's "Turn on"/"Turn
    # off"), keeping one consistent activate/deactivate metaphor for
    # Quiet hours and one consistent on/off, lit/unlit metaphor for
    # Screen, rather than forcing both toggles onto the same verb.
    "Screen on": "Écran allumé",
    "Screen off": "Écran éteint",
    "Quiet hours on": "Heures calmes activées",
    "Quiet hours off": "Heures calmes désactivées",
    "Screen and quiet hours status — go to Home":
        "État de l’écran et des heures calmes — aller à l’accueil",
}
