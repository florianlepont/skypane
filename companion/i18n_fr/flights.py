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
- "Flight" — companion/i18n_fr/rules.py already owns this exact key
  (colour_rules.RULE_KIND_CALLSIGN's own display label, "Vol") —
  21-03-PLAN.md Task 1 (D-15)'s new Flight-column header is the
  identical English source string, so it reuses that entry rather than
  redefining it here.

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
    # 21-03-PLAN.md Task 1 (D-15): "Type" (formerly "Modèle") is
    # deleted — the aircraft-type word is no longer a standalone header;
    # it now lives inside the Flight column's data-only "{airline} ·
    # {aircraft type}" secondary line, which is never translated (the
    # type/airline text is data, not a UI label — 21-UI-SPEC.md §F).
    "When": "Quand",
    # 21-03-PLAN.md Task 1 (D-15): the visually-hidden toggle-column
    # header naming the Task 2 row-toggle button's column.
    "Details": "Détails",
    # 22-09-PLAN.md Task 1 (X5): the row-toggle button's own two states.
    # The visible "More"/"Plus" and "Less"/"Moins" labels are RETIRED
    # with the text button itself — the toggle is icon-only now, and
    # these two strings are its swapped ACCESSIBLE NAME (an aria-label
    # companion/static/flight-rows.js reads back out of the
    # data-show-label/data-hide-label attributes this page renders).
    # They deliberately name the picture as well as the details: the
    # panel-picture control now lives inside that detail row, and a name
    # saying only "details" would hide it from the one user who most
    # needs to be told it is there.
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
    # D-06 (20-11-PLAN.md Task 3): companion/static/copy-button.js's own
    # on-success feedback text, now server-rendered via each button's
    # data-copied-text attribute instead of a hardcoded English literal.
    "Copied": "Copié",

    # --- The per-row "View panel near this time" lightbox (D-20) --------
    "View panel near this time": "Voir le panneau proche de cette heure",
    "Picture shown on the frame": "Image affichée sur le cadre",
    "Picture from %s": "Image du %s",
    # 20-12-PLAN.md Task 1: COLOUR_CAVEAT's own key, independent of the
    # LIGHTBOX_NOTE composition below that folds it in verbatim — the
    # completeness harness treats a constant used only by concatenation
    # as still needing its own catalogue entry (it is a real, reusable
    # sentence per its own defining comment in history_page.py).
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

    # --- The unresolved-airline link (D-21, retargeted by 22-09) ---------
    # 22-09-PLAN.md Task 2 (X5): "View unresolved prefixes" is RETIRED
    # with the two-hop route it named (Flights -> Health's read-only
    # list -> Airlines). The link goes straight to the Airlines resolve
    # view for this flight's own prefix now, so it names the action it
    # performs instead of the list it used to land on.
    "Name this airline": "Nommer cette compagnie",
    "Airline unknown": "Compagnie inconnue",
    "Route unavailable": "Trajet indisponible",

    # --- 22-09-PLAN.md Task 2 (X5): the day separators ------------------
    # The absolute form ("26 août") is not a catalogue entry: it is
    # composed at render time from layout.month_abbr(), which is
    # local_clock_text()'s own already-translated month table.
    "Today": "Aujourd’hui",
    "Yesterday": "Hier",

    # --- 22-09-PLAN.md Task 2 (X5): the panel-picture control -----------
    # Its VISIBLE label, now that it is a labelled text control inside
    # the detail row rather than a 16px icon-only eye in the summary
    # row. "View panel near this time" survives above as its title.
    "View picture": "Voir l’image",
}
