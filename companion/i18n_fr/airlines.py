# -*- coding: utf-8 -*-
"""companion/i18n_fr/airlines.py — French strings for the Airlines page
(companion/pages/airlines_page.py, D-05), 20-10-PLAN.md.

One sibling module of the companion/i18n_fr package (see that
package's __init__.py for the auto-merge/duplicate-key contract this
module participates in). Every key here is the exact English source
string a call site in companion/pages/airlines_page.py passes to
companion.i18n.t() — including any "%s"/"%d" placeholder, unchanged.

Deliberately absent (reused from a sibling module rather than
redefined — the auto-merge package raises ValueError on a duplicate
key across sibling modules, see companion/i18n_fr/__init__.py):
- "Airlines" — companion/i18n_fr/nav.py already owns that exact key
  (the nav label, "Compagnies").
- "%s illustration" — companion/i18n_fr/home.py already owns that
  exact key (the recent-flights thumbnail's own alt-text template,
  byte-identical text, "Illustration %s").
- "Delete" — companion/i18n_fr/display.py already owns that exact key
  (the flight-colour-rules delete button, "Supprimer").
- "Prefix" / "First seen" / "Last seen" / "Example callsign" —
  companion/i18n_fr/health.py already owns these exact keys (the
  unresolved-prefix registry table's own column labels).
- "%d of %d shown" / "Clear" — companion/i18n_fr/health.py already
  owns these exact keys (its own filter-bar copy).

Task 1 (20-10-PLAN.md) added only the "Change pictures"/"Done" toggle's
three strings, pulled forward into that task's own commit so it was
independently buildable and its own French-render check passed at
that commit (the same precedent 20-01-SUMMARY.md/20-06-SUMMARY.md
document for their own Task 2/3 splits). Task 2 extends this same file
with the rest of the page's sweep — every remaining string on Airlines,
per D-05.

Copy follows D-09 (20-CONTEXT.md): sentence case, the typographic
apostrophe (U+2019, never a straight quote), guillemets («…») for an
embedded quotation rather than a straight or curly double-quote pair,
and a non-breaking space (U+00A0) before ":" ";" "?" "!".
"""

CATALOG = {
    # --- The "Change pictures"/"Done" toggle (D-36, 20-10-PLAN.md Task 1) --
    "Change pictures": "Modifier les images",
    "Done": "Terminé",
    "Replace an airline’s picture or add one for an airline that has "
    "none.": "Remplacez l’image d’une compagnie, ou ajoutez-en une pour "
    "une compagnie qui n’en a pas encore.",

    # --- Page header, gallery, cards (20-10-PLAN.md Task 2) -------------
    "Illustration reference for every airline this frame can recognize.":
        "Référence des illustrations pour chaque compagnie que le cadre "
        "peut reconnaître.",
    "Enlarge %s illustration": "Agrandir l’illustration %s",
    "Airline illustration": "Illustration de la compagnie",
    "Close": "Fermer",
    "Superseded": "Remplacée",
    "Resolved by hand": "Résolue à la main",
    "SkyPane’s built-in list now recognizes prefix %s as “%s” — its "
    "entry wins over the name you gave it (“%s”), so that artwork is "
    "no longer shown. Add artwork for “%s” below, or delete this "
    "entry.":
        "La liste intégrée de SkyPane reconnaît maintenant le préfixe %s "
        "comme « %s » — son entrée l’emporte sur le nom que vous lui "
        "aviez donné (« %s »), cette image n’est donc plus affichée. "
        "Ajoutez une image pour « %s » ci-dessous, ou supprimez cette "
        "entrée.",

    # --- The "Unidentified airlines" gap strip and its cards ------------
    "Unidentified airlines": "Compagnies non identifiées",
    "The frame saw these callsigns but doesn’t know the airline. Tap "
    "one to name it.":
        "Le cadre a vu ces indicatifs mais ne connaît pas la compagnie. "
        "Touchez-en un pour la nommer.",
    "Resolve prefix %s — example callsign %s":
        "Identifier le préfixe %s — exemple d’indicatif %s",
    "%d other unresolved prefixes — ": "%d autres préfixes non résolus — ",
    "see the full list": "voir la liste complète",
    "%d manual resolutions, %d superseded": "%d résolutions manuelles, %d remplacées",
    "%d manual resolutions": "%d résolutions manuelles",

    # --- The gallery's filter bar (D-16) ---------------------------------
    "Filter by airline or callsign": "Filtrer par compagnie ou indicatif",
    "No matching airlines": "Aucune compagnie correspondante",
    "Try a different search, or Clear filter to see all %d airlines.":
        "Essayez une autre recherche, ou effacez le filtre pour voir les "
        "%d compagnies.",

    # --- The "resolve an unidentified flight" section (D-03, D-10..D-13) --
    "← Back to Airlines": "← Retour à Compagnies",
    "That coverage gap isn’t there anymore — it may already be "
    "resolved. See Health for the complete list of current gaps.":
        "Cette lacune n’existe plus — elle est peut-être déjà résolue. "
        "Consultez État pour la liste complète des lacunes actuelles.",
    "Resolve an unidentified flight": "Identifier un vol non reconnu",
    "Every flight using prefix %s will show as this airline once you "
    "save a name.":
        "Chaque vol utilisant le préfixe %s s’affichera sous cette "
        "compagnie une fois le nom enregistré.",
    "Times seen": "Nombre de vues",
    "Airline name": "Nom de la compagnie",
    "Start typing — pick a suggestion if the airline already has "
    "artwork, so this reuses it instead of asking for a new upload.":
        "Commencez à taper — choisissez une suggestion si la compagnie "
        "a déjà une image, pour la réutiliser plutôt que d’en demander "
        "une nouvelle.",
    "Save airline name": "Enregistrer le nom de la compagnie",
    "Add an illustration for %s": "Ajouter une illustration pour %s",
    "Saved. This airline doesn’t have artwork yet — add one below, or "
    "skip for now.":
        "Enregistré. Cette compagnie n’a pas encore d’image — "
        "ajoutez-en une ci-dessous, ou ignorez pour l’instant.",
    "Skip — I’ll add artwork later": "Ignorer — j’ajouterai une image plus tard",
    "%s is already named for this prefix and has artwork — nothing "
    "more to do here.":
        "%s est déjà nommée pour ce préfixe et a une image — rien de "
        "plus à faire ici.",
    "Choose an image": "Choisir une image",
    "Deleting removes only this manual name — any uploaded artwork "
    "stays in place.":
        "La suppression retire uniquement ce nom manuel — toute image "
        "déjà chargée reste en place.",

    # --- The replace/upload forms' shared copy ---------------------------
    "Replace this illustration": "Remplacer cette illustration",
    "Upload": "Envoyer",
    "Transparent PNG, at least 1200px wide, landscape.":
        "PNG transparent, au moins 1200 px de large, au format paysage.",
}
