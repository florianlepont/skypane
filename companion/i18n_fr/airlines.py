# -*- coding: utf-8 -*-
"""French strings for the Airlines page. Every entry is migrated onto a
stable message id: the source-side Message is declared where the
English constant already lives (companion/pages/airlines_page.py),
never here — this module only carries each id's French translation.

Some ids are deliberately absent here and reused from a sibling module
instead ("Airlines", the resolve-context labels, the filter-bar copy) — the auto-merge package raises ValueError
on a duplicate id across sibling modules.

Copy follows sentence case, the typographic apostrophe (U+2019, never a
straight quote), guillemets («…») for an embedded quotation, and a
non-breaking space (U+00A0) before ":" ";" "?" "!".
"""

MESSAGES = {
    # --- Page header, gallery, cards --------------------------------
    "airlines.aircraft_type": "Type d’appareil",
    "airlines.any_aircraft": "Tout appareil",
    "airlines.from_skypane": "Fourni par SkyPane",
    "airlines.built_in_artwork": "Illustration intégrée",
    "airlines.no_built_in_artwork": "Aucune illustration intégrée",
    "airlines.your_changes": "Vos modifications",
    "airlines.no_changes": "Aucune modification",
    "airlines.your_artwork_is_shown_instead": "Votre illustration est affichée à la place",
    "airlines.your_artwork": "Votre illustration",
    "airlines.no_artwork_yet": "Pas encore d’illustration",
    "airlines.built_in_name_used_instead": "Nom intégré utilisé à la place du vôtre",
    "airlines.replace_artwork": "Remplacer l’illustration",
    "airlines.add_artwork": "Ajouter une illustration",
    "airlines.action_for": "%s : %s",
    "airlines.enlarge_illustration": "Agrandir l’illustration %s",
    "airlines.airline_illustration": "Illustration de la compagnie",
    "airlines.close": "Fermer",
    "airlines.resolved_by_hand": "Résolue à la main",
    "airlines.skypane_s_built_in_list_now_recognizes_prefix":
        "La liste intégrée de SkyPane reconnaît maintenant le préfixe %s "
        "comme « %s » — son entrée l’emporte sur le nom que vous lui "
        "aviez donné (« %s »), cette image n’est donc plus affichée. "
        "Ajoutez une image pour « %s » ci-dessous, ou supprimez cette "
        "entrée.",

    # --- The "Unidentified airlines" gap strip and its cards --------
    "airlines.unidentified_airlines": "Compagnies non identifiées",
    "airlines.tap_a_callsign_below_to_name_its_airline":
        "Touchez un indicatif ci-dessous pour nommer sa compagnie.",
    "airlines.resolve_prefix_example_callsign":
        "Identifier le préfixe %s — exemple d’indicatif %s",
    "airlines.other_unresolved_prefixes": "%d autres préfixes non résolus — ",
    "airlines.see_the_full_list": "voir la liste complète",
    "airlines.manual_resolutions_superseded": "%d résolutions manuelles, %d remplacées",
    "airlines.manual_resolutions": "%d résolutions manuelles",
    # The singular halves: French and English agree on where this
    # boundary falls, but each language still owns its own string
    # rather than sharing a runtime rule.
    "airlines.manual_resolution_superseded": "%d résolution manuelle, %d remplacée",
    "airlines.manual_resolution": "%d résolution manuelle",

    # --- The gallery's filter bar ------------------------------------
    "airlines.filter_by_airline_or_callsign": "Filtrer par compagnie ou indicatif",
    "airlines.no_matching_airlines": "Aucune compagnie correspondante",
    "airlines.try_a_different_search_or_clear_filter_to_see":
        "Essayez une autre recherche, ou effacez le filtre pour voir les "
        "%d compagnies.",

    # --- The "resolve an unidentified flight" section ----------------
    "airlines.back_to_airlines": "← Retour à Compagnies",
    "airlines.that_coverage_gap_isn_t_there_anymore_it_may":
        "Cette lacune n’existe plus — elle est peut-être déjà résolue. "
        "Consultez État pour la liste complète des lacunes actuelles.",
    "airlines.resolve_an_unidentified_flight": "Identifier un vol non reconnu",
    "airlines.every_flight_using_prefix_will_show_as_this":
        "Chaque vol utilisant le préfixe %s s’affichera sous cette "
        "compagnie.",
    "airlines.times_seen": "Nombre de vues",
    "airlines.airline_name": "Nom de la compagnie",
    "airlines.start_typing_pick_a_suggestion":
        "Commencez à taper — choisissez une suggestion.",
    "airlines.save_airline_name": "Enregistrer le nom de la compagnie",
    "airlines.add_an_illustration_for": "Ajouter une illustration pour %s",
    "airlines.saved_add_artwork_below_or_skip_for_now":
        "Enregistré — ajoutez une image ci-dessous, ou ignorez pour "
        "l’instant.",
    "airlines.skip_i_ll_add_artwork_later": "Ignorer — j’ajouterai une image plus tard",
    "airlines.is_already_named_for_this_prefix_and_has":
        "%s est déjà nommée pour ce préfixe et a une image — rien de "
        "plus à faire ici.",
    "airlines.choose_an_image": "Choisir une image",
    "airlines.deleting_removes_the_name_you_gave_this_prefix":
        "Les vols de ce préfixe redeviennent non identifiés. "
        "L’illustration reste.",
    "airlines.delete_manual_name": "Supprimer mon nom",

    # --- The replace/upload forms' shared copy ------------------------
    "airlines.replace_this_illustration": "Remplacer cette illustration",
    "airlines.upload": "Envoyer",
    "airlines.transparent_png_at_least_1200px_wide_landscape":
        "PNG transparent, au moins 1200 px de large, au format paysage.",

    # --- The drag-and-drop upload affordance --------------------------
    # "cadrée", never "à quoi elle ressemblera": the preview shows the
    # frame the image will occupy; the server alone decides the final
    # crop, the same distinction the English copy makes.
    "airlines.drop_an_image_in_the_frame":
        "Déposez une image dans le cadre, ou choisissez-en une.",
    "airlines.framing_preview_of_the_image_you_chose":
        "Aperçu du cadrage de l’image choisie",
    "airlines.only_png_images_can_be_dropped_here":
        "Seules les images PNG peuvent être déposées ici.",
    "airlines.drop_one_image_at_a_time": "Déposez une seule image à la fois.",
    "airlines.that_image_is_larger_than_the_mb_limit":
        "Cette image dépasse la limite de %d Mo.",
}
