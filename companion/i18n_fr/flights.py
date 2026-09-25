# -*- coding: utf-8 -*-
"""French strings for the Flights page
(companion/pages/history_page.py). Every key is the exact English
source string a call site passes to companion.i18n.t(), including any
"%s"/"%d" placeholder.

Several keys are deliberately absent here and reused from sibling
modules instead ("Flights", "Timestamp", "Corroboration", "Callsign",
"Runway", the corroboration/filter-bar copy, "Close", "Departing",
"Arriving", "Flight") — the auto-merge package raises ValueError on a
duplicate key across sibling modules.

Copy follows sentence case, the typographic apostrophe (U+2019, never
a straight quote), and a non-breaking space (U+00A0) before
":" ";" "?" "!".
"""

CATALOG = {
    # --- Page header, empty/unavailable states --------------------------
    "The latest %d aircraft the frame has shown.":
        "Les %d derniers avions que le cadre a affichés.",
    "No flights detected yet — check back after the next poll cycle.":
        "Aucun vol détecté pour l’instant — revenez après le prochain "
        "cycle de vérification.",
    "The flight list is temporarily unavailable — try again in a "
    "minute.":
        "La liste des vols est temporairement indisponible — réessayez "
        "dans une minute.",

    # --- Table/column headers and the mobile card's dt labels -----------
    "When": "Quand",
    # Visually-hidden header naming the row-toggle button's column.
    "Details": "Détails",
    # The row-toggle button's swapped accessible name, read by
    # flight-rows.js — names the picture too, since that control lives
    # inside the same detail row.
    "Show flight details and picture":
        "Afficher les détails du vol et l’image",
    "Hide flight details and picture":
        "Masquer les détails du vol et l’image",
    "Route": "Trajet",
    "State": "Sens",
    "Hex": "Code hex",
    "Full timestamp": "Horodatage complet",
    "Recent flights table, scrollable": "Tableau des vols récents, défilable",

    # --- Corroboration's own two remaining, not-yet-shared labels --------
    "Single-source": "Source unique",
    "Unknown": "Inconnu",

    # --- The table's filter bar -----------------------------------------
    "Filter by callsign or hex": "Filtrer par indicatif ou code hex",
    "No matching flights": "Aucun vol correspondant",
    "Try a different search, or Clear filter to see all %d flights.":
        "Essayez une autre recherche, ou effacez le filtre pour voir "
        "les %d vols.",
    # The empty-state body used only while a limit is in force and rows
    # remain unloaded.
    "Try a different search — this only searches the %d flights shown.":
        "Essayez une autre recherche — seuls les %d vols affichés sont "
        "cherchés.",

    # --- Copy-to-clipboard accessible names -------------------------------
    "Copy callsign %s": "Copier l’indicatif %s",
    "Copy hex ID for %s": "Copier le code hex pour %s",
    "Copy timestamp for %s": "Copier l’horodatage pour %s",
    "no callsign": "aucun indicatif",
    "no reading yet": "aucune mesure pour l’instant",
    # copy-button.js's on-success feedback text, server-rendered via
    # each button's data-copied-text attribute.
    "Copied": "Copié",

    # --- The per-row "View panel near this time" lightbox ---------------
    "View panel near this time": "Voir le panneau proche de cette heure",
    "Picture shown on the frame": "Image affichée sur le cadre",
    "Picture from %s": "Image du %s",
    # A key of its own: the completeness harness needs an entry even
    # though this text is also folded into the composed note below.
    "Colours are nominal render-internal swatches, not colour-accurate "
    "against real Spectra 6 glass.":
        "Les couleurs sont des teintes internes de rendu, pas une "
        "reproduction fidèle du vrai verre Spectra 6.",
    "This is the nearest recorded render, not necessarily from this "
    "exact flight — the panel updates on its own wake/poll cycle. "
    "Colours are nominal render-internal swatches, not colour-accurate "
    "against real Spectra 6 glass.":
        "Ceci est le rendu enregistré le plus proche, pas nécessairement "
        "celui de ce vol exact — le panneau se met à jour selon son "
        "propre cycle de réveil et de vérification. Les couleurs sont "
        "des teintes internes de rendu, pas une reproduction fidèle du "
        "vrai verre Spectra 6.",

    # --- The unresolved-airline link -------------------------------------
    # Links straight to the Airlines resolve view for this flight's own
    # prefix, naming the action it performs.
    "Name this airline": "Nommer cette compagnie",
    "Airline unknown": "Compagnie inconnue",
    "Route unavailable": "Trajet indisponible",

    # --- The day separators -----------------------------------------
    # The absolute form ("26 août") is not a catalogue entry: it is
    # composed at render time from layout.month_abbr().
    "Today": "Aujourd’hui",
    "Yesterday": "Hier",

    # The panel-picture control's visible label.
    "View picture": "Voir l’image",

    "Show more (%d remaining)": "Afficher plus (%d restants)",
}
