# -*- coding: utf-8 -*-
"""companion/i18n_fr/home.py — French strings for the Home page
(companion/pages/home_page.py, D-05), 20-06-PLAN.md.

One sibling module of the companion/i18n_fr package (see that
package's __init__.py for the auto-merge/duplicate-key contract this
module participates in). Every key here is the exact English source
string a call site in companion/pages/home_page.py passes to
companion.i18n.t() — including any "%s" placeholder, unchanged.

Deliberately absent: "Home" — companion/i18n_fr/nav.py already owns
that exact key (the nav label), and home_page.py's own page-title
render site calls `i18n.t(PAGE_TITLE)` with that same English string,
reusing nav.py's "Accueil" entry rather than redefining it (the
auto-merge package raises ValueError on a duplicate key across sibling
modules — see companion/i18n_fr/__init__.py).

Copy follows D-09 (20-CONTEXT.md): sentence case, the typographic
apostrophe (U+2019, never a straight quote), and a non-breaking space
(U+00A0) before ":" ";" "?" "!". Every French value below matching
20-UI-SPEC.md's Copywriting Contract Section A is copied verbatim from
that table; the handful of keys the copy table does not list (the page
purpose, the no-panel/no-flights empty states, the flight-direction
words) are pre-existing home_page.py strings this plan's own D-05 sweep
translates for the first time.
"""

CATALOG = {
    # --- Page header (companion/pages/home_page.py's render()) ---------
    "Your frame at a glance.": "Votre cadre en un coup d’œil.",

    # --- Hero: the picture caption (20-UI-SPEC.md §A) -------------------
    "Rendered %s": "Généré %s",
    "The picture currently on the frame":
        "L’image actuellement affichée sur le cadre",
    "Nothing rendered yet.": "Rien n’a encore été généré.",
    "The server saves a copy of each picture it sends to the frame; the "
    "latest one will appear here.":
        "Le serveur conserve une copie de chaque image envoyée au cadre ; "
        "la plus récente apparaîtra ici.",

    # --- Hero: the flight one-liner's direction word --------------------
    "Departing": "Au départ",
    "Arriving": "À l’arrivée",

    # --- Status card headline (20-UI-SPEC.md §A) ------------------------
    "Next update ≈ %s": "Prochaine mise à jour ≈ %s",
    "Expected since %s": "Attendue depuis %s",

    # --- Status card: the visually-hidden landmark heading --------------
    "Status": "Statut",

    # --- Status-row labels (20-UI-SPEC.md §A) ---------------------------
    "Frame": "Cadre",
    "Battery": "Batterie",
    "Flight data": "Données de vol",

    # --- Status-row verdicts (20-UI-SPEC.md §A) -------------------------
    # FRAME_STATE_TEXT's three values are byte-identical to health_page.
    # DEVICE_STATE_TEXT's own three values (20-RESEARCH.md Pitfall 3 —
    # this is exactly why the two dicts must never be edited to differ:
    # they legitimately describe the same states identically on both
    # pages). companion/i18n_fr/health.py (20-03-PLAN.md) already owns
    # "Checking in normally"/"Has not checked in for a while"/"Has not
    # checked in for a long time" as catalogue keys — the auto-merge
    # package raises on a duplicate key, so this module reuses those
    # three entries by NOT redefining them here; i18n.t() resolves them
    # from the one shared catalogue regardless of which page calls it.
    "Up to date": "À jour",
    "A little stale": "Un peu daté",
    "Stale — the server may be down": "Données anciennes — le serveur est peut-être en panne",
    "Healthy": "Bonne",
    "Dropping quickly": "Baisse rapidement",
    "No reading yet": "Aucune mesure pour l’instant",

    # --- Health link (20-UI-SPEC.md §A) ---------------------------------
    "See details on Health": "Voir les détails dans État",

    # --- Recent flights (20-UI-SPEC.md §A) ------------------------------
    "Recent flights": "Vols récents",
    "See all flights": "Voir tous les vols",
    "No flights yet.": "Aucun vol pour l’instant.",
    "The first aircraft the frame detects on the watched runway will "
    "appear here.":
        "Le premier avion détecté par le cadre sur la piste surveillée "
        "apparaîtra ici.",
    "%s illustration": "Illustration %s",
}
