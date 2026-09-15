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
    # 22-04-PLAN.md Task 1 (critical constraint 8): "Attendue depuis %s"
    # (feminine agreement, from this call site's own former grammatical
    # context) is reconciled here to 22-UI-SPEC.md's locked Copywriting
    # Contract value, "Attendu depuis %s" (no agreement) — the same
    # French key this module's own frame-state headline consumer
    # (companion/layout.py's frame_strip_html(), via
    # _FRAME_HEADLINE_LATE_TEXT) now renders live. 22-02-SUMMARY.md
    # flagged this exact discrepancy as unresolved pending a real
    # consumer; this plan is that consumer, so it reconciles it here
    # rather than leaving it for 22-05 (which owns no file this string
    # lives in).
    "Next update ≈ %s": "Prochaine mise à jour ≈ %s",
    "Expected since %s": "Attendu depuis %s",

    # --- Frame strip: the Quiet hours caption link (CFG-69, 27-08-PLAN.md
    # Task 2) — companion/layout.py's own frame_strip_html(), keyed here
    # for the same "this catalogue already holds that module's other
    # frame-strip strings" reason "Expected since %s" above does.
    "Change the schedule": "Modifier l’horaire",

    # --- Status card: the visually-hidden landmark heading --------------
    "Status": "Statut",

    # --- Status-row labels (20-UI-SPEC.md §A) ---------------------------
    # 22-07-PLAN.md Task 1 (X4): "Frame" is renamed to "Check-ins" for
    # home_page.FRAME_ROW_LABEL — the strip's own <h2> heading (a
    # DIFFERENT constant, companion/layout.py's FRAME_STRIP_HEADING)
    # keeps "Frame"/"Cadre", so that entry is NOT removed from this
    # catalogue even though home_page.py no longer reads it directly.
    "Check-ins": "Connexions",
    "Frame": "Cadre",
    "Battery": "Batterie",
    "Flight data": "Données de vol",

    # --- Status-row verdicts (20-UI-SPEC.md §A) -------------------------
    # FRAME_STATE_TEXT's "ok"/"warn"/"error" values are byte-identical
    # to health_page.DEVICE_STATE_TEXT's own three values
    # (20-RESEARCH.md Pitfall 3 — this is exactly why the two dicts must
    # never be edited to differ: they legitimately describe the same
    # states identically on both pages). companion/i18n_fr/health.py
    # (20-03-PLAN.md) already owns "Checking in normally"/"Has not
    # checked in for a while"/"Has not checked in for a long time" as
    # catalogue keys — the auto-merge package raises on a duplicate
    # key, so this module reuses those three entries by NOT redefining
    # them here; i18n.t() resolves them from the one shared catalogue
    # regardless of which page calls it. 22-07-PLAN.md Task 1 (D-03/
    # CFG-26) widens FRAME_STATE_TEXT with a fourth "off" key —
    # "Asleep for quiet hours" — reusing companion/i18n_fr/health.py's
    # OWN 22-04-PLAN.md Task 3 entry for the identical English string,
    # for the same reason: not redefined here either. DATA_STATE_TEXT's
    # own new "off" key ("No detection yet") likewise reuses health.py's
    # 22-03-PLAN.md Task 1 entry.
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

    # --- The day band (CFG-42, 24-06-PLAN.md Task 2) --------------------
    #
    # "heures calmes" and "reveil" are BOTH pre-existing terms in this
    # catalogue's own vocabulary, reused rather than re-coined:
    # companion/i18n_fr/display.py and nav.py render "Quiet hours" as
    # "Heures calmes", and companion/i18n_fr/frame_state.py already calls
    # the device's wake a "reveil" ("Prochain reveil vers %s"). A band
    # that invented a third word for the event the frame strip above it
    # already names would read as a different event.
    # "Today" is NOT redefined here: companion/i18n_fr/flights.py already
    # owns that exact key ("Aujourd’hui") and the auto-merge package
    # raises on a duplicate. i18n.t() resolves it from the one shared
    # catalogue whichever page calls it — the same reuse this module's
    # own header records for "Home".
    "The frame's check-ins through the day, midnight to midnight":
        "Les réveils du cadre au fil de la journée, de minuit à minuit",
    "No check-ins recorded on %s.": "Aucun réveil enregistré le %s.",
    "1 check-in on %s.": "1 réveil le %s.",
    # The placeholders stay in the English order (count, then day): both
    # languages say the number first.
    "%s check-ins on %s.": "%s réveils le %s.",
    "Some marks are merged — check-ins closer together than the band can "
    "separate are drawn as one.":
        "Certaines marques sont fusionnées : les réveils trop rapprochés pour "
        "que la bande puisse les séparer sont dessinés comme un seul.",
    "Shaded: quiet hours, %s to %s.":
        "Zone grisée : heures calmes, de %s à %s.",
}
