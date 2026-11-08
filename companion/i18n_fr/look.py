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
    "look.save": "Enregistrer",
    "look.done": "Terminé",
    "look.close": "Fermer",
    "look.follows_departures_note": (
        "Cette allure suit celle des départs. Désactivez pour choisir la vôtre."),

    # --- The three choices ---------------------------------------------
    "look.colour": "Couleur principale",
    "look.background": "Fond",
    "look.diagonal_stripe": "Bande diagonale",
    "look.black": "Noir",
    "look.yellow": "Jaune",
    "look.red": "Rouge",
    "look.green": "Vert",
    "look.blue": "Bleu",
    "look.background_paper": "Blanc",
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
    "look.style_soft_stripe_on_full": "Bande claire sur fond plein",
    "look.style_stripe_on_full": "Bande sur fond plein",
    "look.style_soft_stripe_on_soft": "Bande claire sur fond clair",
    "look.plain_paper": "Papier uni",
    "look.not_available": "%s : indisponible",
    "look.colour_and_style": "%s : couleur et style",
    "look.colour_and_style_stripes": "%s : couleur et style, bandes sur un fond",
    "look.why_some_cells_are_empty": "Pourquoi certaines cases sont vides",
    "look.same_rendering_without_solid_stripe_on_full":
        "Sur un fond plein, une bande pleine est invisible\u00a0: même rendu que sans bande.",
    "look.same_rendering_without_stripe_on_soft":
        "Une bande claire sur un fond clair est invisible\u00a0: même rendu que sans bande.",
    "look.colour_changes_nothing_on_plain_paper":
        "Sur papier blanc uni, la couleur ne change rien\u00a0: choisissez d’abord un fond ou une bande.",
    "look.the_frame_has_no_theme_for_this_combination":
        "Le cadre n’a pas encore de thème pour cette combinaison.",

    # --- Special looks -------------------------------------------------
    "look.special_looks": "Looks spéciaux",
    "look.override_the_look_for_one_airline_flight_or_aircraft":
        "Une allure à part pour une compagnie, un vol ou un avion.",
    "look.most_specific_wins":
        "La plus précise l’emporte\u00a0: calendrier, puis vol, avion, compagnie.",
    "look.calendar": "Calendrier",
    "look.flights_in_your_calendar": "Allure des vols du calendrier",
    "look.new_special_look": "Nouvelle allure spéciale",
    "look.edit_special_look": "Modifier l’allure spéciale",
    "look.create_look": "Créer l’allure",
    "look.look": "Allure",
    "look.matching_flights_will_look_like_this":
        "Les vols concernés auront cette allure.",
}
