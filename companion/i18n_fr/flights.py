# -*- coding: utf-8 -*-
"""French strings for the Flights page
(companion/pages/history_page.py). Every entry is migrated onto a
stable message id: the source-side Message is declared where the
English constant already lives (companion/pages/history_page.py),
never here — this module only carries each id's French translation.

Several ids are deliberately absent here and reused from sibling
modules instead ("Flights", "Timestamp", "Flight", the filter-bar copy, "Close",
"Departing", "Arriving") — the auto-merge package raises ValueError on a
duplicate id across sibling modules.

Copy follows sentence case, the typographic apostrophe (U+2019, never
a straight quote), and a non-breaking space (U+00A0) before
":" ";" "?" "!".
"""

MESSAGES = {
    # --- Page header, empty/unavailable states --------------------------
    "flights.no_flights_detected_yet_check_back_after_the":
        "Aucun vol détecté pour l’instant — revenez après le prochain "
        "cycle de vérification.",
    "flights.the_flight_list_is_temporarily_unavailable_try":
        "La liste des vols est temporairement indisponible — réessayez "
        "dans une minute.",

    # --- Table column headers ---------------------------------------------
    "flights.when": "Quand",
    "flights.route": "Trajet",
    "flights.state": "Sens",
    "flights.recent_flights_table_scrollable": "Tableau des vols récents, défilable",

    # --- The table's filter bar -----------------------------------------
    "flights.filter_flights": "Filtrer les vols",
    "flights.no_matching_flights": "Aucun vol correspondant",
    "flights.try_a_different_search_or_clear_filter_to_see":
        "Essayez une autre recherche, ou effacez le filtre pour voir "
        "les %d vols.",
    # The empty-state body used only while a limit is in force and rows
    # remain unloaded.
    "flights.try_a_different_search_this_only_searches_the":
        "Essayez une autre recherche — seuls les %d vols affichés sont "
        "cherchés.",

    # --- Copy-to-clipboard accessible names -------------------------------
    "flights.no_callsign": "aucun indicatif",
    "flights.no_reading_yet": "aucune mesure pour l’instant",
    # copy-button.js's on-success feedback text, server-rendered via
    # each button's data-copied-text attribute.

    # --- The per-row "View panel near this time" lightbox ---------------
    "flights.picture_shown_on_the_frame": "Image affichée sur le cadre",
    "flights.picture_from": "Image du %s",
    # --- The unresolved-airline link -------------------------------------
    # Links straight to the Airlines resolve view for this flight's own
    # prefix, naming the action it performs.
    "flights.name_this_airline": "Nommer cette compagnie",
    "flights.airline_unknown": "Compagnie inconnue",
    "flights.route_unavailable": "Trajet indisponible",

    # --- The day separators -----------------------------------------
    # The absolute form ("26 août") is not a catalogue entry: it is
    # composed at render time from layout.month_abbr().
    "flights.today": "Aujourd’hui",
    "flights.yesterday": "Hier",

    # The row-level picture link: visible label, hidden column header and
    # the per-row accessible name.
    "flights.view_picture": "Voir l’image",
    "flights.picture": "Image",
    "flights.view_picture_of": "Voir l’image de %s",

    "flights.show_more_remaining": "Afficher plus (%d restants)",
}
