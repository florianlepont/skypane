# -*- coding: utf-8 -*-
"""French strings for the Airlines page. Every key is the exact English
source string a call site in companion/pages/airlines_page.py passes to
companion.i18n.t(), including any "%s"/"%d" placeholder.

Some keys are deliberately absent here and reused from a sibling module
instead ("Airlines", "%s illustration", "Delete", the resolve-context
labels, the filter-bar copy) — the auto-merge package raises ValueError
on a duplicate key across sibling modules.

Copy follows sentence case, the typographic apostrophe (U+2019, never a
straight quote), guillemets («…») for an embedded quotation, and a
non-breaking space (U+00A0) before ":" ";" "?" "!".
"""

CATALOG = {
    # --- Page header, gallery, cards --------------------------------
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

    # --- The "Unidentified airlines" gap strip and its cards --------
    "Unidentified airlines": "Compagnies non identifiées",
    "Tap a callsign below to name its airline.":
        "Touchez un indicatif ci-dessous pour nommer sa compagnie.",
    "Resolve prefix %s — example callsign %s":
        "Identifier le préfixe %s — exemple d’indicatif %s",
    "%d other unresolved prefixes — ": "%d autres préfixes non résolus — ",
    "see the full list": "voir la liste complète",
    "%d manual resolutions, %d superseded": "%d résolutions manuelles, %d remplacées",
    "%d manual resolutions": "%d résolutions manuelles",
    # The singular halves: French and English agree on where this
    # boundary falls, but each language still owns its own string
    # rather than sharing a runtime rule.
    "%d manual resolution, %d superseded": "%d résolution manuelle, %d remplacée",
    "%d manual resolution": "%d résolution manuelle",

    # --- The gallery's filter bar ------------------------------------
    "Filter by airline or callsign": "Filtrer par compagnie ou indicatif",
    "No matching airlines": "Aucune compagnie correspondante",
    "Try a different search, or Clear filter to see all %d airlines.":
        "Essayez une autre recherche, ou effacez le filtre pour voir les "
        "%d compagnies.",

    # --- The "resolve an unidentified flight" section ----------------
    "← Back to Airlines": "← Retour à Compagnies",
    "That coverage gap isn’t there anymore — it may already be "
    "resolved. See Health for the complete list of current gaps.":
        "Cette lacune n’existe plus — elle est peut-être déjà résolue. "
        "Consultez État pour la liste complète des lacunes actuelles.",
    "Resolve an unidentified flight": "Identifier un vol non reconnu",
    "Every flight using prefix %s will show as this airline.":
        "Chaque vol utilisant le préfixe %s s’affichera sous cette "
        "compagnie.",
    "Times seen": "Nombre de vues",
    "Airline name": "Nom de la compagnie",
    "Start typing — pick a suggestion.":
        "Commencez à taper — choisissez une suggestion.",
    "Save airline name": "Enregistrer le nom de la compagnie",
    "Add an illustration for %s": "Ajouter une illustration pour %s",
    "Saved — add artwork below, or skip for now.":
        "Enregistré — ajoutez une image ci-dessous, ou ignorez pour "
        "l’instant.",
    "Skip — I’ll add artwork later": "Ignorer — j’ajouterai une image plus tard",
    "%s is already named for this prefix and has artwork — nothing "
    "more to do here.":
        "%s est déjà nommée pour ce préfixe et a une image — rien de "
        "plus à faire ici.",
    "Choose an image": "Choisir une image",
    "Deleting removes this manual name — any uploaded artwork stays in place.":
        "La suppression retire ce nom manuel — l’image reste en place.",

    # --- The replace/upload forms' shared copy ------------------------
    "Replace this illustration": "Remplacer cette illustration",
    "Upload": "Envoyer",
    "Transparent PNG, at least 1200px wide, landscape.":
        "PNG transparent, au moins 1200 px de large, au format paysage.",

    # --- The drag-and-drop upload affordance --------------------------
    # "cadrée", never "à quoi elle ressemblera": the preview shows the
    # frame the image will occupy; the server alone decides the final
    # crop, the same distinction the English copy makes.
    "Or drag an image onto this card.":
        "Ou glissez une image sur cette carte.",
    "Framing preview — how it will be framed.":
        "Aperçu du cadrage — comment elle sera cadrée.",
    "Framing preview of the image you chose":
        "Aperçu du cadrage de l’image choisie",
    "Only PNG images can be dropped here.":
        "Seules les images PNG peuvent être déposées ici.",
    "Drop one image at a time.": "Déposez une seule image à la fois.",
    "That image is larger than the %d MB limit.":
        "Cette image dépasse la limite de %d Mo.",
}
