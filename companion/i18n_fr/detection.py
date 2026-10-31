# -*- coding: utf-8 -*-
"""French strings for the Detection page: the summary of the saved setting,
the mode choice, airport search and runway cards, and the inline errors.

Copy follows sentence case, the typographic apostrophe (U+2019), a
non-breaking space (U+00A0) before ":" ";" "?" "!" and inside guillemets,
and a decimal comma in prose. The frame's own text rows are English and
never appear here.

The source-side Message for each id is declared in
companion/pages/detection_page.py; this module only carries the French.
"""

MESSAGES = {
    "detection.detection": "Détection",
    "detection.page_purpose":
        "Choisissez les vols affichés par ce cadre : le trafic d’une "
        "piste, ou les avions autour d’un lieu.",
    "detection.back_to_display": "Retour à l’affichage",

    "detection.current_setting": "Réglage actuel",
    "detection.following": "Suivi",
    "detection.text_on_the_frame": "Texte sur le cadre",
    "detection.when_nothing_is_in_range": "Quand rien n’est à portée",
    "detection.summary_runway": "Piste %(runway)s à %(airport)s",
    "detection.summary_runway_detail":
        "Décollages et atterrissages, dans les deux sens.",
    "detection.summary_position":
        "Avions à moins de %(radius)d km de %(location)s",
    "detection.summary_position_detail":
        "En vol, sous 10 000 ft, le plus bas d’abord.",
    "detection.legacy_runway_pill": "Piste %(number)s",
    "detection.fail_safe_toast":
        "Aucun lieu utilisable — le cadre continue de suivre la piste 3 "
        "d’Orly jusqu’à ce que vous choisissiez un lieu en France.",
    "detection.saved_flash":
        "Détection enregistrée — le cadre l’utilisera à son prochain réveil.",

    "detection.detection_mode": "Mode de détection",
    "detection.airport_and_runway": "Aéroport et piste",
    "detection.around_a_location": "Autour d’un lieu",

    "detection.airport": "Aéroport",
    "detection.find_an_airport": "Trouver un aéroport",
    "detection.search_hint":
        "Cherchez par code OACI, code IATA, nom ou ville.",
    "detection.airports": "Aéroports",
    "detection.search_airports": "Rechercher des aéroports",
    "detection.airports_found": "%(count)d aéroports trouvés",
    "detection.one_airport_found": "1 aéroport trouvé",
    "detection.no_airport_matches":
        "Aucun aéroport ne correspond à « %(query)s »",
    "detection.airports_capped":
        "Les %(shown)d premiers aéroports sur %(total)d. Affinez votre "
        "recherche pour réduire la liste.",
    "detection.no_airport_found": "Aucun aéroport trouvé",
    "detection.no_airport_found_body":
        "Vérifiez l’orthographe, ou essayez un code OACI comme LFPG ou un "
        "code IATA comme CDG.",
    "detection.unknown_airport": "Cet aéroport n’est pas dans le catalogue.",
    "detection.selected_airport": "Aéroport choisi",
    "detection.change_airport": "Changer d’aéroport",

    "detection.runway": "Piste",
    "detection.runway_caption":
        "Le cadre suit les décollages et atterrissages dans les deux sens.",
    "detection.runway_bearing": "Cap %(a)s° / %(b)s° (vrai)",
    "detection.surface_asphalt": "Asphalte",
    "detection.surface_concrete": "Béton",
    "detection.surface_grass": "Herbe",
    "detection.surface_gravel": "Gravier",
    "detection.frame_tag_hint":
        "Le cadre étiquette cet aéroport « %(code)s », puis la "
        "piste, par exemple %(example)s.",

    "detection.location": "Lieu",
    "detection.location_caption":
        "Le cadre affiche l’avion en vol le plus bas, sous 10 000 ft, "
        "dans le rayon.",

    "detection.error_mode": "Choisissez un mode de détection.",
    "detection.error_airport": "Choisissez un aéroport.",
    "detection.error_runway_missing": "Choisissez une piste.",
    "detection.error_runway_unknown":
        "Cette piste n’existe pas dans cet aéroport. Choisissez-en une dans "
        "la liste.",
}
