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
    # --- Editor table ------------------------------------------------
    "airlines.table_caption": "Compagnies",
    "airlines.col_airline": "Compagnie",
    "airlines.col_prefixes": "Préfixes",
    "airlines.col_artwork": "Illustration",
    "airlines.col_views": "Vues",
    "airlines.col_last_seen": "Dernière vue",
    "airlines.name_aria": "Nom de la compagnie : %s",
    "airlines.table_save_name": "Enregistrer",
    "airlines.enlarge_artwork_of": "Agrandir l’illustration de %s",
    "airlines.table_upload": "Téléverser",
    "airlines.change_artwork": "Changer l’illustration",
    "airlines.uses_airline_artwork": "Utilise celle de la compagnie",
    "airlines.expand_types_aria": "Types d’appareil vus pour %s",
    "airlines.row_menu_aria": "Actions pour %s",
    "airlines.show_all_types": "Afficher les types d’appareil de toutes les compagnies",
    "airlines.reset_original_name": "Revenir au nom d’origine",
    "airlines.resolve_name_aria": "Nom de la compagnie pour le préfixe %s",
    "airlines.resolve_name_placeholder": "Nom de la compagnie",
    "airlines.resolve_type_aria": "Type d’appareil par défaut pour %s",
    "airlines.resolve_type_none": "Type d’appareil",
    "airlines.resolve_validate": "Valider",
    "airlines.resolve_ignore": "Ignorer",
    "airlines.named_by_hand": "Nommée à la main",
    "airlines.state_airline_default": "Celle de la compagnie",
    "airlines.state_own_artwork": "Illustration propre",
    "airlines.customise_artwork": "Personnaliser",
    "airlines.menu_revert_artwork": "Revenir à celle par défaut",
    "airlines.menu_delete_artwork": "Supprimer l’illustration",
    "airlines.menu_set_default_type": "Définir comme type par défaut",
    "airlines.menu_clear_default_type": "Retirer comme type par défaut",
    "airlines.default_type_pill": "Type par défaut",
    "airlines.unidentified_label": "Non identifiée",
    "airlines.views_one": "1 vue",
    "airlines.views_many": "%d vues",
    "airlines.table_not_seen": "Pas encore vue",
    # --- Page header, gallery, cards --------------------------------
    "airlines.aircraft_type": "Type d’appareil",
    "airlines.all_types": "Tous types",
    "airlines.add_artwork": "Ajouter une illustration",
    "airlines.action_for": "%s : %s",
    "airlines.airline_illustration": "Illustration de la compagnie",
    "airlines.close": "Fermer",
    "airlines.your_name_for_prefix_is_not_used":
        "Votre nom « %s » pour le préfixe %s n’est pas utilisé : le nom "
        "intégré « %s » l’emporte.",

    # --- The "Unidentified airlines" gap strip and its cards --------
    "airlines.resolve_prefix_example_callsign":
        "Identifier le préfixe %s — exemple d’indicatif %s",
    "airlines.other_unresolved_prefixes": "%d autres préfixes non résolus — ",
    "airlines.see_the_full_list": "voir la liste complète",

    # --- The gallery's filter bar ------------------------------------
    "airlines.filter_by_airline_or_callsign": "Filtrer par compagnie ou indicatif",
    "airlines.search_placeholder": "Compagnie ou indicatif…",
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
    "airlines.times_seen": "Nombre de vues",
    "airlines.airline_name": "Nom de la compagnie",
    "airlines.save_airline_name": "Enregistrer le nom de la compagnie",
    "airlines.add_an_illustration_for": "Ajouter une illustration pour %s",
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

    # --- The airline sheet (an airline row) ---------------------------
    "airlines.edit_airline": "Modifier %s",

    # --- The Airline collection page ----------------------------------
    "airlines.collection_progress": "%d compagnies repérées sur %d",
    "airlines.collection_progress_one": "%d compagnie repérée sur %d",
    "airlines.collection_next_goal": "encore %d pour le badge %d",
    "airlines.collection_next_goal_first":
        "Repérez une compagnie pour obtenir le badge Première observation",
    "airlines.collection_complete": "Vous avez repéré toutes les compagnies de la liste.",
    "airlines.collection_all_badges": "Vous avez obtenu tous les badges.",
    "airlines.collection_badges": "Badges de la collection",
    "airlines.collection_badge_first": "Première observation",
    "airlines.collection_badge_count": "%d compagnies",
    "airlines.collection_badge_earned": "Obtenu",
    "airlines.collection_badge_locked": "Verrouillé : repérez %d compagnies",
    "airlines.collection_badge_locked_first": "Verrouillé : repérez une compagnie",
    "airlines.collection_show": "Afficher",
    "airlines.collection_show_all": "Toutes",
    "airlines.collection_show_spotted": "Repérées",
    "airlines.collection_show_unseen": "Pas encore vues",
    "airlines.collection_sort_by": "Trier par",
    "airlines.collection_sort_most": "Les plus vues",
    "airlines.collection_sort_rarest": "Les plus rares",
    "airlines.collection_sort_latest": "Les plus récentes",
    "airlines.collection_sort_az": "A à Z",
    "airlines.collection_filter_label": "Filtrer les compagnies",
    "airlines.collection_filter_placeholder": "Filtrer",
    "airlines.collection_apply": "Appliquer",
    "airlines.collection_count": "Compagnies\u00a0: %d",
    "airlines.collection_count_template": "Compagnies\u00a0: #",
    "airlines.collection_range_rare": "Moins de %d passages",
    "airlines.collection_range_occasional": "De %d à %d passages",
    "airlines.collection_range_regular": "%d passages ou plus",
    "airlines.collection_legend": "Rareté des compagnies et des appareils",
    "airlines.collection_seen_many": "Vue %d fois",
    "airlines.collection_seen_once": "Vue une fois",
    "airlines.collection_not_seen": "Pas encore vue",
    "airlines.collection_new": "Nouveau",
    "airlines.collection_rarity_regular": "Habituelle",
    "airlines.collection_rarity_occasional": "Occasionnelle",
    "airlines.collection_rarity_rare": "Rare",
    "airlines.collection_rarity_sentence":
        "La rareté dépend du nombre de fois où votre cadre a vu une compagnie.",
    "airlines.collection_fact_times": "Nombre de passages",
    "airlines.collection_fact_first": "Première observation",
    "airlines.collection_fact_last": "Dernière observation",
    "airlines.collection_fact_types": "Types d’appareil observés",
    "airlines.collection_fact_rarity": "Rareté",
    "airlines.collection_fact_callsigns": "Indicatifs récents",
    "airlines.collection_empty_heading": "Votre collection commence avec le premier avion",
    "airlines.collection_empty_body":
        "Les compagnies apparaissent ici dès que votre cadre les voit.",
    "airlines.collection_no_match_body": "Essayez un autre filtre ou un nom plus court.",
}
