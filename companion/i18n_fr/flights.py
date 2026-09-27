# -*- coding: utf-8 -*-
"""French strings for the Flights page
(companion/pages/history_page.py). Every entry is migrated onto a
stable message id: the source-side Message is declared where the
English constant already lives (companion/pages/history_page.py),
never here — this module only carries each id's French translation.

Several ids are deliberately absent here and reused from sibling
modules instead ("Flights", "Timestamp", "Corroboration", "Callsign",
"Runway", the corroboration/filter-bar copy, "Close", "Departing",
"Arriving", "Flight") — the auto-merge package raises ValueError on a
duplicate id across sibling modules.

Copy follows sentence case, the typographic apostrophe (U+2019, never
a straight quote), and a non-breaking space (U+00A0) before
":" ";" "?" "!".
"""

MESSAGES = {
    # --- Page header, empty/unavailable states --------------------------
    "flights.the_latest_aircraft_the_frame_has_shown":
        "Les %d derniers avions que le cadre a affichés.",
    "flights.no_flights_detected_yet_check_back_after_the":
        "Aucun vol détecté pour l’instant — revenez après le prochain "
        "cycle de vérification.",
    "flights.the_flight_list_is_temporarily_unavailable_try":
        "La liste des vols est temporairement indisponible — réessayez "
        "dans une minute.",

    # --- Table/column headers and the mobile card's dt labels -----------
    "flights.when": "Quand",
    # Visually-hidden header naming the row-toggle button's column.
    "flights.details": "Détails",
    # The row-toggle button's swapped accessible name, read by
    # flight-rows.js — names the picture too, since that control lives
    # inside the same detail row.
    "flights.show_flight_details_and_picture":
        "Afficher les détails du vol et l’image",
    "flights.hide_flight_details_and_picture":
        "Masquer les détails du vol et l’image",
    "flights.route": "Trajet",
    "flights.state": "Sens",
    "flights.hex": "Code hex",
    "flights.full_timestamp": "Horodatage complet",
    "flights.recent_flights_table_scrollable": "Tableau des vols récents, défilable",

    # --- Corroboration's own two remaining, not-yet-shared labels --------
    "flights.single_source": "Source unique",
    "flights.unknown": "Inconnu",

    # --- The table's filter bar -----------------------------------------
    "flights.filter_by_callsign_or_hex": "Filtrer par indicatif ou code hex",
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
    "flights.copy_callsign": "Copier l’indicatif %s",
    "flights.copy_hex_id_for": "Copier le code hex pour %s",
    "flights.copy_timestamp_for": "Copier l’horodatage pour %s",
    "flights.no_callsign": "aucun indicatif",
    "flights.no_reading_yet": "aucune mesure pour l’instant",
    # copy-button.js's on-success feedback text, server-rendered via
    # each button's data-copied-text attribute.
    "flights.copied": "Copié",

    # --- The per-row "View panel near this time" lightbox ---------------
    "flights.view_panel_near_this_time": "Voir le panneau proche de cette heure",
    "flights.picture_shown_on_the_frame": "Image affichée sur le cadre",
    "flights.picture_from": "Image du %s",
    # A key of its own: the completeness harness needs an entry even
    # though this text is also folded into the composed note below.
    "flights.colours_are_nominal_render_internal_swatches":
        "Les couleurs sont des teintes internes de rendu, pas une "
        "reproduction fidèle du vrai verre Spectra 6.",
    "flights.this_is_the_nearest_recorded_render_not":
        "Ceci est le rendu enregistré le plus proche, pas nécessairement "
        "celui de ce vol exact — le panneau se met à jour selon son "
        "propre cycle de réveil et de vérification. Les couleurs sont "
        "des teintes internes de rendu, pas une reproduction fidèle du "
        "vrai verre Spectra 6.",

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

    # The panel-picture control's visible label.
    "flights.view_picture": "Voir l’image",

    "flights.show_more_remaining": "Afficher plus (%d restants)",
}
