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
        "En vol, le plus bas d’abord.",
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
        "Le cadre affiche l’avion en vol le plus bas dans le rayon.",

    "detection.location_label": "Lieu",
    "detection.location_option": "%(name)s — %(lat)s, %(lon)s",
    "detection.location_option_outside": "%(name)s — hors de France",
    "detection.rounding_note":
        "Partagé avec les fournisseurs de données, arrondi à environ 1 km.",
    "detection.radius_label": "Rayon (kilomètres)",
    "detection.radius_hint": "De 2 à 28 km.",
    "detection.no_location_heading": "Aucun lieu pour l’instant",
    "detection.no_location_body":
        "Ajoutez un lieu ci-dessous, puis choisissez-le ici pour suivre les "
        "avions autour.",
    "detection.add_location": "Ajouter un lieu",
    "detection.locations_title": "Vos lieux",
    "detection.locations_caption":
        "Les lieux enregistrés ici peuvent servir à vos cadres.",
    "detection.locations_title_owner": "Lieux du propriétaire de ce cadre",
    "detection.locations_caption_owner":
        "Vous enregistrez des lieux pour le propriétaire de ce cadre.",
    "detection.edit_location": "Modifier le lieu",
    "detection.edit_location_named": "Modifier le lieu %(name)s",
    "detection.edit_location_summary": "Modifier les détails du lieu",
    "detection.field_name": "Nom",
    "detection.field_latitude": "Latitude",
    "detection.field_longitude": "Longitude",
    "detection.latitude_hint": "Degrés décimaux, par exemple 48,8566.",
    "detection.longitude_hint": "Degrés décimaux, par exemple 2,3522.",
    "detection.save_location": "Enregistrer le lieu",
    "detection.cancel_location": "Annuler le lieu",
    "detection.location_saved_flash":
        "Lieu enregistré — vous pouvez maintenant le choisir ci-dessus.",

    "detection.error_location_missing": "Choisissez un lieu.",
    "detection.error_location_unavailable":
        "Ce lieu n’est pas disponible. Choisissez-en un dans la liste.",
    "detection.error_location_outside":
        "Ce lieu est hors de la France métropolitaine. Choisissez un lieu en "
        "France.",
    "detection.error_radius":
        "Saisissez un nombre entier de kilomètres de 2 à 28.",
    "detection.error_name":
        "Saisissez un nom de 60 caractères au maximum.",
    "detection.error_number": "Saisissez un nombre tel que 48,8566.",
    "detection.error_timezone": "Choisissez un fuseau horaire dans la liste.",

    "detection.error_mode": "Choisissez un mode de détection.",
    "detection.error_airport": "Choisissez un aéroport.",
    "detection.error_runway_missing": "Choisissez une piste.",
    "detection.error_runway_unknown":
        "Cette piste n’existe pas dans cet aéroport. Choisissez-en une dans "
        "la liste.",
}
