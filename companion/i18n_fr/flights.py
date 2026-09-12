# -*- coding: utf-8 -*-
"""companion/i18n_fr/flights.py — French strings for the Flights page
(companion/pages/history_page.py, D-05), 20-10-PLAN.md Task 3.

One sibling module of the companion/i18n_fr package (see that
package's __init__.py for the auto-merge/duplicate-key contract this
module participates in). Every key here is the exact English source
string a call site in companion/pages/history_page.py passes to
companion.i18n.t() — including any "%s"/"%d" placeholder, unchanged.

Deliberately absent (reused from a sibling module rather than
redefined — the auto-merge package raises ValueError on a duplicate
key across sibling modules, see companion/i18n_fr/__init__.py):
- "Flights" — companion/i18n_fr/nav.py already owns that exact key
  (the nav label, "Vols" — history_page.PAGE_TITLE is this same
  string).
- "Timestamp" / "Corroboration" — companion/i18n_fr/health.py already
  owns these exact keys (its own registry-table column labels).
- "Callsign" / "Runway" — companion/i18n_fr/display.py already owns
  these exact keys (the flight-colours "Match by" segment / the
  Runway group heading).
- "Both agree" / "They disagree" / "Only one saw it" / "More details" /
  "%d of %d shown" / "Clear" — companion/i18n_fr/health.py already
  owns these exact keys (its own corroboration copy and filter bar).
- "Close" — companion/i18n_fr/airlines.py already owns that exact key
  (the shared click-to-enlarge lightbox's dismissal control, the same
  English text this page's own lightbox uses).
- "Departing" / "Arriving" — companion/i18n_fr/home.py already owns
  these exact keys (history_page._CONFIRMED_STATE_LABELS' own two
  values are byte-identical to home_page's direction words).

Copy follows D-09 (20-CONTEXT.md): sentence case, the typographic
apostrophe (U+2019, never a straight quote), and a non-breaking space
(U+00A0) before ":" ";" "?" "!".
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
    "Type": "Modèle",
    "Route": "Trajet",
    "State": "Sens",
    "Hex": "Code hex",
    "Full timestamp": "Horodatage complet",
    "Recent flights table, scrollable": "Tableau des vols récents, défilable",

    # --- Corroboration's own two remaining, not-yet-shared labels --------
    "Single-source": "Source unique",
    "Unknown": "Inconnu",

    # --- The table's filter bar (D-20) -----------------------------------
    "Filter by callsign or hex": "Filtrer par indicatif ou code hex",
    "No matching flights": "Aucun vol correspondant",
    "Try a different search, or Clear filter to see all %d flights.":
        "Essayez une autre recherche, ou effacez le filtre pour voir "
        "les %d vols.",

    # --- Copy-to-clipboard accessible names (D-23) -----------------------
    "Copy callsign %s": "Copier l’indicatif %s",
    "Copy hex ID for %s": "Copier le code hex pour %s",
    "Copy timestamp for %s": "Copier l’horodatage pour %s",
    "no callsign": "aucun indicatif",
    "no reading yet": "aucune mesure pour l’instant",

    # --- The per-row "View panel near this time" lightbox (D-20) --------
    "View panel near this time": "Voir le panneau proche de cette heure",
    "Picture shown on the frame": "Image affichée sur le cadre",
    "Picture from %s": "Image du %s",
    "This is the nearest recorded render, not necessarily from this "
    "exact flight — the panel updates on its own wake/poll cycle. "
    "Colours are nominal render-internal swatches, not colour-accurate "
    "against real Spectra 6 glass.":
        "Ceci est le rendu enregistré le plus proche, pas nécessairement "
        "celui de ce vol exact — le panneau se met à jour selon son "
        "propre cycle de réveil et de vérification. Les couleurs sont "
        "des teintes internes de rendu, pas une reproduction fidèle du "
        "vrai verre Spectra 6.",

    # --- The unresolved-airline link to Health (D-21) --------------------
    "View unresolved prefixes": "Voir les préfixes non résolus",
    "Airline unknown": "Compagnie inconnue",
}
