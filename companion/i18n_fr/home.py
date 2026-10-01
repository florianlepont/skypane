# -*- coding: utf-8 -*-
"""French strings for the Home page (companion/pages/home_page.py).
Every entry is migrated onto a stable message id: the source-side
Message is declared where the English constant already lives
(companion/pages/home_page.py, companion/frame_state.py,
companion/ui_base.py), never here — this module only carries each id's
French translation.

Deliberately absent: "Home" — companion/i18n_fr/nav.py already owns
that id, and home_page.py's page-title render site reuses that Message
rather than redeclaring it (the auto-merge package raises ValueError on
a duplicate id across sibling modules).

Copy follows sentence case, the typographic apostrophe (U+2019,
never a straight quote), and a non-breaking space (U+00A0) before
":" ";" "?" "!".
"""

MESSAGES = {
    "home.current_frame": "Dernière image envoyée au cadre",

    "home.rendered": "Généré %s",
    "home.the_picture_currently_on_the_frame":
        "L’image actuellement affichée sur le cadre",
    "home.nothing_rendered_yet": "Rien n’a encore été généré.",
    "home.the_server_saves_a_copy_of_each_picture_it":
        "Le serveur conserve une copie de chaque image envoyée au cadre ; "
        "la plus récente apparaîtra ici.",

    "home.departing": "Au départ",
    "home.arriving": "À l’arrivée",

    # Reconciled to the same French key the frame-strip headline
    # consumer (companion/layout.py's frame_strip_html()) renders
    # live — grammatical agreement matches that shared context, not
    # a re-derivation of this page's own former wording.
    "home.next_update": "Prochaine mise à jour ≈ %s",
    "home.expected_since": "Attendu depuis %s",

    # companion/layout.py's own frame_strip_html(), keyed here for
    # the same shared-catalogue reason as the entry above.
    "home.change_the_schedule": "Modifier l’horaire",

    "home.status": "Statut",

    # The strip's own <h2> heading (companion/ui_base.py's
    # FRAME_STRIP_HEADING, a different constant) keeps "Frame"/
    # "Cadre", so that entry stays even though home_page.py no
    # longer reads it directly.
    "home.check_ins": "Connexions",
    "home.frame": "Cadre",
    "home.battery": "Batterie",
    "home.flight_data": "Données de vol",

    # Byte-identical to health_page.DEVICE_STATE_TEXT's own values —
    # the two dicts must never be edited to differ, since they
    # describe the same states identically on both pages. The "off"
    # keys ("Asleep for quiet hours", "No detection yet") reuse
    # companion/i18n_fr/health.py's own entries for the identical
    # English strings rather than redefining them here.
    "home.up_to_date": "À jour",
    "home.a_little_stale": "Un peu daté",
    "home.stale_the_server_may_be_down": "Données anciennes — le serveur est peut-être en panne",
    "home.healthy": "Bonne",
    "home.dropping_quickly": "Baisse rapidement",
    "home.no_reading_yet": "Aucune mesure pour l’instant",

    "home.see_details_on_health": "Voir les détails dans État",
    "home.battery_fact": "Batterie · %s",
    "home.battery_fact_empty": "Batterie · Aucune mesure pour l’instant",
    "home.action_needed": "Un élément demande votre attention",
    "home.review_status": "Voir l’état",

    "home.recent_flights": "Vols récents",
    "home.see_all_flights": "Voir tous les vols",
    "home.no_flights_yet": "Aucun vol pour l’instant.",
    "home.the_first_aircraft_the_frame_detects_on_the":
        "Le premier avion détecté par le cadre sur la piste surveillée "
        "apparaîtra ici.",
    "home.illustration": "Illustration %s",

    # "heures calmes" and "réveil" are both pre-existing terms in
    # this catalogue's vocabulary, reused rather than re-coined, so
    # the band names the same event the frame strip above it names.
    # "Today" is not redefined here: companion/i18n_fr/flights.py
    # already owns that id.
    "home.the_frame_s_check_ins_through_the_day_midnight":
        "Les réveils du cadre au fil de la journée, de minuit à minuit",
    "home.no_check_ins_recorded_on": "Aucun réveil enregistré le %s.",
    "home.1_check_in_on": "1 réveil le %s.",
    # The placeholders stay in the English order: both languages say the number first.
    "home.check_ins_on": "%s réveils le %s.",
    "home.some_marks_are_merged_check_ins_closer_together":
        "Certaines marques sont fusionnées : les réveils trop rapprochés pour "
        "que la bande puisse les séparer sont dessinés comme un seul.",
    "home.shaded_quiet_hours_to":
        "Zone grisée : heures calmes, de %s à %s.",
}
