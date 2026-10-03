# -*- coding: utf-8 -*-
"""French strings for the Display page's look card: the two pictures,
the look sheet's three choices, the colour x style table, the Special
looks list and the "New special look" form. Keyed by stable message id;
each id is declared in companion/settings/look.py, theme.py, calendar.py
or rules.py.

"Soft" is "clair" (as the registry's "Light" themes always were in
French), "Full" is "plein". A stripe ("bande") is feminine, so its
choices agree: "Aucune", "Pleine", "Claire".

Copy follows sentence case, the typographic apostrophe (U+2019, never
a straight quote), and a non-breaking space (U+00A0) before
":" ";" "?" "!".
"""

MESSAGES = {
    # --- Card -----------------------------------------------------------
    "look.departures_look": "Allure des départs",
    "look.arrivals_look": "Allure des arrivées",
    "look.calendar_flights_look": "Allure des vols du calendrier",
    "look.change": "Modifier",
    "look.change_the_look": "Modifier l’allure : %s",
    "look.preview_alt": "Aperçu : %s, %s",
    "look.reset": "Rétablir",
    "look.done": "Terminé",
    "look.close": "Fermer",

    # --- The three choices ---------------------------------------------
    "look.colour": "Couleur",
    "look.background": "Fond",
    "look.diagonal_stripe": "Bande diagonale",
    "look.black": "Noir",
    "look.yellow": "Jaune",
    "look.red": "Rouge",
    "look.green": "Vert",
    "look.blue": "Bleu",
    "look.background_paper": "Papier",
    "look.background_full": "Plein",
    "look.background_soft": "Clair",
    "look.stripe_none": "Aucune",
    "look.stripe_solid": "Pleine",
    "look.stripe_soft": "Claire",

    # --- Colour x style table ------------------------------------------
    "look.style_solid": "Plein",
    "look.style_soft": "Clair",
    "look.style_stripe": "Bande",
    "look.style_soft_stripe": "Bande claire",
    "look.style_stripe_on_soft": "Bande sur fond clair",
    "look.plain_paper": "Papier uni",
    "look.not_available": "%s : indisponible",
    "look.colour_and_style": "%s : couleur et style",
    "look.why_some_cells_are_empty": "Pourquoi certaines cases sont vides",
    "look.a_stripe_would_vanish_on_a_full_background":
        "Une bande disparaîtrait sur un fond plein.",
    "look.a_soft_stripe_would_vanish_on_a_soft_background":
        "Une bande claire disparaîtrait sur un fond clair.",
    "look.text_on_a_stripe_is_white_unreadable_on_yellow":
        "Le texte sur une bande est blanc, et le blanc sur du jaune est illisible.",
    "look.the_frame_has_no_theme_for_this_combination":
        "Le cadre n’a pas encore de thème pour cette combinaison.",

    # --- Special looks -------------------------------------------------
    "look.special_looks": "Allures spéciales",
    "look.override_the_look_for_one_airline_flight_or_aircraft":
        "Changez l’allure d’une compagnie, d’un vol ou d’un avion.",
    "look.most_specific_wins":
        "La plus précise l’emporte : calendrier, puis vol, avion, compagnie. "
        "Ajouter une clé déjà présente remplace son allure.",
    "look.calendar": "Calendrier",
    "look.flights_in_your_calendar": "Vols de votre calendrier",
    "look.calendar_connection": "Connexion du calendrier",
    "look.add_a_special_look": "Ajouter une allure spéciale",
    "look.new_special_look": "Nouvelle allure spéciale",
    "look.look": "Allure",
    "look.matching_flights_will_look_like_this":
        "Les vols concernés auront cette allure, sauf si une allure plus "
        "précise s’applique.",
}
