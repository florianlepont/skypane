# -*- coding: utf-8 -*-
"""French strings for the Home page (companion/pages/home_page.py).
Every key is the exact English source string a call site passes to
companion.i18n.t(), including any "%s" placeholder.

Deliberately absent: "Home" — companion/i18n_fr/nav.py already owns
that exact key, and home_page.py's page-title render site reuses
that entry rather than redefining it (the auto-merge package raises
ValueError on a duplicate key across sibling modules).

Copy follows sentence case, the typographic apostrophe (U+2019,
never a straight quote), and a non-breaking space (U+00A0) before
":" ";" "?" "!".
"""

CATALOG = {
    "Your frame at a glance.": "Votre cadre en un coup d’œil.",

    "Rendered %s": "Généré %s",
    "The picture currently on the frame":
        "L’image actuellement affichée sur le cadre",
    "Nothing rendered yet.": "Rien n’a encore été généré.",
    "The server saves a copy of each picture it sends to the frame; the "
    "latest one will appear here.":
        "Le serveur conserve une copie de chaque image envoyée au cadre ; "
        "la plus récente apparaîtra ici.",

    "Departing": "Au départ",
    "Arriving": "À l’arrivée",

    # Reconciled to the same French key the frame-strip headline
    # consumer (companion/layout.py's frame_strip_html()) renders
    # live — grammatical agreement matches that shared context, not
    # a re-derivation of this page's own former wording.
    "Next update ≈ %s": "Prochaine mise à jour ≈ %s",
    "Expected since %s": "Attendu depuis %s",

    # companion/layout.py's own frame_strip_html(), keyed here for
    # the same shared-catalogue reason as the entry above.
    "Change the schedule": "Modifier l’horaire",

    "Status": "Statut",

    # The strip's own <h2> heading (companion/layout.py's
    # FRAME_STRIP_HEADING, a different constant) keeps "Frame"/
    # "Cadre", so that entry stays even though home_page.py no
    # longer reads it directly.
    "Check-ins": "Connexions",
    "Frame": "Cadre",
    "Battery": "Batterie",
    "Flight data": "Données de vol",

    # Byte-identical to health_page.DEVICE_STATE_TEXT's own values —
    # the two dicts must never be edited to differ, since they
    # describe the same states identically on both pages. The "off"
    # keys ("Asleep for quiet hours", "No detection yet") reuse
    # companion/i18n_fr/health.py's own entries for the identical
    # English strings rather than redefining them here.
    "Up to date": "À jour",
    "A little stale": "Un peu daté",
    "Stale — the server may be down": "Données anciennes — le serveur est peut-être en panne",
    "Healthy": "Bonne",
    "Dropping quickly": "Baisse rapidement",
    "No reading yet": "Aucune mesure pour l’instant",

    "See details on Health": "Voir les détails dans État",

    "Recent flights": "Vols récents",
    "See all flights": "Voir tous les vols",
    "No flights yet.": "Aucun vol pour l’instant.",
    "The first aircraft the frame detects on the watched runway will "
    "appear here.":
        "Le premier avion détecté par le cadre sur la piste surveillée "
        "apparaîtra ici.",
    "%s illustration": "Illustration %s",

    # "heures calmes" and "réveil" are both pre-existing terms in
    # this catalogue's vocabulary, reused rather than re-coined, so
    # the band names the same event the frame strip above it names.
    # "Today" is not redefined here: companion/i18n_fr/flights.py
    # already owns that exact key.
    "The frame's check-ins through the day, midnight to midnight":
        "Les réveils du cadre au fil de la journée, de minuit à minuit",
    "No check-ins recorded on %s.": "Aucun réveil enregistré le %s.",
    "1 check-in on %s.": "1 réveil le %s.",
    # The placeholders stay in the English order: both languages say the number first.
    "%s check-ins on %s.": "%s réveils le %s.",
    "Some marks are merged — check-ins closer together than the band can "
    "separate are drawn as one.":
        "Certaines marques sont fusionnées : les réveils trop rapprochés pour "
        "que la bande puisse les séparer sont dessinés comme un seul.",
    "Shaded: quiet hours, %s to %s.":
        "Zone grisée : heures calmes, de %s à %s.",
}
