# -*- coding: utf-8 -*-
"""French strings for the Detection page: the summary of the saved setting,
the airport search and the inline errors.

Copy follows sentence case, the typographic apostrophe (U+2019), a
non-breaking space (U+00A0) before ":" ";" "?" "!" and inside guillemets,
and a decimal comma in prose. The frame's own text rows are English and
never appear here.

The source-side Message for each id is declared in
companion/pages/detection_page.py; this module only carries the French. The
strings of the page itself (place, map, what to follow) are declared in
companion/pages/place_page.py and translated below.
"""

MESSAGES = {
    "detection.detection": "Détection",

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


    "detection.search_hint":
        "Cherchez par code OACI, code IATA, nom ou ville.",
    "detection.search_airports": "Rechercher des aéroports",
    "detection.airports_found": "%(count)d aéroports trouvés",
    "detection.one_airport_found": "1 aéroport trouvé",
    "detection.no_airport_matches":
        "Aucun aéroport ne correspond à « %(query)s »",
    "detection.no_airport_found": "Aucun aéroport trouvé",
    "detection.no_airport_found_body":
        "Vérifiez l’orthographe, ou essayez un code OACI comme LFPG ou un "
        "code IATA comme CDG.",
    "detection.unknown_airport": "Cet aéroport n’est pas dans le catalogue.",

    "detection.surface_asphalt": "Asphalte",
    "detection.surface_concrete": "Béton",
    "detection.surface_grass": "Herbe",
    "detection.surface_gravel": "Gravier",
    "detection.frame_tag_hint":
        "Le cadre étiquette cet aéroport « %(code)s », puis la "
        "piste, par exemple %(example)s.",


    "detection.field_latitude": "Latitude",
    "detection.field_longitude": "Longitude",
    "detection.latitude_hint": "Degrés décimaux, par exemple 48,8566.",
    "detection.longitude_hint": "Degrés décimaux, par exemple 2,3522.",
    "detection.location_saved_flash":
        "Lieu enregistré — vous pouvez maintenant le choisir ci-dessus.",

    "detection.place_saved_flash":
        "Lieu enregistré — La détection suit désormais {place}.",
    "detection.place_fallback_name": "le lieu choisi",

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

    # Page strings declared in companion/pages/place_page.py.
    "detection.page_purpose":
        "La détection suit votre lieu : choisissez un aéroport pour suivre une piste, ou placez un repère pour suivre la zone autour.",
    "detection.title":
        "Lieu",
    "detection.no_script_map":
        "La carte demande JavaScript et une connexion. Vous pouvez quand même choisir un lieu avec la liste d’aéroports ou en saisissant des coordonnées.",
    "detection.attribution": "© contributeurs d’OpenStreetMap",
    "detection.pin_placed": "Repère placé à %s, %s",
    "detection.tiles_failed":
        "Les images de la carte n’ont pas pu se charger. Le repère et les coordonnées fonctionnent toujours.",
    "detection.zoom_in": "Zoomer",
    "detection.zoom_out": "Dézoomer",
    "detection.show_france": "Voir toute la France",
    "detection.cluster_title": "Zoomer sur ces aéroports (%d)",
    "detection.search_none":
        "Aucun lieu trouvé en France. Essayez une autre orthographe, touchez la carte ou saisissez un code d’aéroport.",
    "detection.search_failed":
        "La recherche n’est pas disponible pour le moment. Touchez la carte ou saisissez un code d’aéroport.",
    "detection.row_searching": "Recherche en cours…",
    "detection.row_none": "Aucun lieu trouvé",
    "detection.row_failed": "Recherche indisponible pour le moment",
    "detection.search_short": "Tapez au moins 3 caractères pour chercher.",
    "detection.results_label": "Résultats de la recherche",
    "detection.locating": "Recherche de votre position…",
    "detection.located":
        "Position trouvée (à environ %d m). Vérifiez le repère, puis enregistrez.",
    "detection.locate_denied":
        "L’accès à la position est bloqué pour ce site. Autorisez-le dans les réglages du navigateur, ou cherchez un lieu, touchez la carte ou choisissez un aéroport.",
    "detection.locate_unavailable":
        "Votre position est introuvable. Réessayez à l’extérieur, ou cherchez un lieu.",
    "detection.locate_timeout":
        "La recherche de votre position a pris trop de temps. Réessayez, ou cherchez un lieu.",
    "detection.nearest_airport":
        "Aéroport le plus proche : %s, à %d km. Suivre sa piste ?",
    "detection.follow_airport": "Suivre %s",
    "detection.tap_hint": "Touchez la carte pour placer le point",
    "detection.move_hint": "Touchez la carte pour le déplacer",
    "detection.result_airport": "Aéroport",
    "detection.group_airports": "Aéroports",
    "detection.group_places": "Lieux et adresses",
    "detection.map_loading": "Chargement de la carte\u2026",
    "detection.map_label":
        "Carte. Utilisez les flèches pour déplacer, plus et moins pour zoomer.",
    "detection.search_label":
        "Rechercher un aéroport ou une adresse",
    "detection.search_button":
        "Rechercher un lieu",
    "detection.search_help":
        "Un code ou un nom d’aéroport choisit cet aéroport. Tout le reste est envoyé au service de recherche d’OpenStreetMap (Nominatim), après une courte pause, pendant la saisie.",
    "detection.locate":
        "Utiliser ma position",
    "detection.about_map":
        "À propos de cette carte",
    "detection.map_credits":
        "Données cartographiques © contributeurs d’OpenStreetMap, ODbL. Images de carte du serveur de tuiles d’OpenStreetMap. Recherche par Nominatim.",
    "detection.map_privacy":
        "Afficher la carte demande aux serveurs d’OpenStreetMap les images de la zone que vous regardez. La position enregistrée de votre cadre reste sur SkyPane.",
    "detection.report_problem":
        "Signaler un problème de carte",
    "detection.copyright_link":
        "Droits d’auteur d’OpenStreetMap",
    "detection.airports_title":
        "Aéroports français",
    "detection.filter_airports":
        "Filtrer les aéroports",
    "detection.search_placeholder":
        "Aéroport (ORY) ou adresse",
    "detection.mode_runway":
        "Aéroport",
    "detection.mode_area":
        "Ma position",
    "detection.mode_switch_label":
        "Ce que le cadre suit",
    "detection.area_heading":
        "Détection autour de ce point",
    "detection.runway_label":
        "Piste à suivre",
    "detection.pick_airport":
        "Choisissez un aéroport dans la liste pour suivre l’une de ses pistes.",
    "detection.radius_label":
        "Rayon (km)",
    "detection.radius_help":
        "Les avions proches de ce point sont affichés. 9 km est un bon début.",
    "detection.details_title":
        "Coordonnées et fuseau horaire",
    "detection.details_close":
        "Retour à la carte",
    "detection.label_field":
        "Nom du lieu",
    "detection.section_place":
        "Lieu",
}
