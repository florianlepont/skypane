# -*- coding: utf-8 -*-
"""French strings for the login page, the 404 and 403 pages, the shared
"Sign out" control, and every flash-banner template in
companion/flash.py's FLASH_MESSAGES dict. Every entry is migrated onto
a stable message id: the source-side Message is declared where the
English constant already lives (companion/login_page.py,
companion/app.py, companion/flash.py, companion/ui_shell.py,
companion/ui_nav.py, companion/ui_base.py), never here — this module
only carries each id's French translation.

One FLASH_MESSAGES value is deliberately absent here — the Frame
strip's poll-cooldown copy — already keyed in a sibling module; the
auto-merge package raises ValueError on a duplicate id across sibling
modules.
"""

MESSAGES = {
    # --- The shared filter bar (companion/ui_filter.py) -------------------
    "common.clear_search": "Effacer la recherche",

    # --- Login page ------------------------------------------------
    "common.sign_in_to_manage_this_device_s_settings":
        "Connectez-vous pour gérer les réglages de cet appareil.",
    "common.too_many_attempts_try_again_in_s":
        "Trop de tentatives — réessayez dans %d s.",
    "common.password": "Mot de passe",
    "common.sign_in": "Se connecter",
    "common.incorrect_password_try_again":
        "Mot de passe incorrect. Réessayez.",
    # The show-password toggle's two accessible names. The toggle is
    # icon-only, so these are the only names it ever has.
    "common.show_password": "Afficher le mot de passe",
    "common.hide_password": "Masquer le mot de passe",
    "common.login": "Connexion",

    # --- 404 page ----------------------------------------------------
    "common.page_not_found": "Page introuvable.",
    "common.the_page_you_requested_doesn_t_exist_or_may":
        "La page demandée n’existe pas ou a peut-être été déplacée.",
    "common.back_to_home": "Retour à l’accueil",
    # The 404 page's own <title> — a short form distinct from the
    # page heading's longer sentence above.
    "common.not_found": "Introuvable",

    # --- 403 page ------------------------------------------------------
    "common.request_refused": "Requête refusée",
    "common.this_request_came_from_another_site_so_it_was":
        "Cette requête venait d’un autre site, elle a donc été refusée. "
        "Ouvrez SkyPane directement et réessayez.",

    # --- Shared footer control -----------------------------------------
    "common.sign_out": "Se déconnecter",

    # --- Toasts (shared by every flash and persistent alert) --------
    # Spoken before each toast's title, never shown.
    "common.toast_tone_success": "Succès :",
    "common.toast_tone_info": "Information :",
    "common.toast_tone_warning": "Avertissement :",
    "common.toast_tone_error": "Erreur :",
    "common.toast_tone_pending": "En attente :",
    "common.dismiss_this_message": "Masquer ce message",
    "common.undo": "Annuler",
    "common.see_health": "Voir l’état",

    # --- Flash banners ---------------------------------------------
    "common.screen_switched_on_the_frame_will_wake_up_and":
        "Écran allumé — le cadre va se réveiller et afficher une image "
        "dans environ cinq minutes.",
    "common.screen_switched_off_the_frame_will_blank_itself":
        "Écran éteint — le cadre va s’effacer dans environ cinq "
        "minutes.",
    "common.quiet_hours_turned_on_applies_the_next_time_the":
        "Heures calmes activées — s’applique au prochain réveil du "
        "cadre.",
    "common.quiet_hours_turned_off_applies_the_next_time":
        "Heures calmes désactivées — s’applique au prochain réveil du "
        "cadre.",
    # The Diagnostic LED's own two outcomes, worded on the quiet-hours
    # pair above rather than the screen pair — the LED takes effect on
    # the frame's next wake rather than within about five minutes.
    "common.diagnostic_led_turned_on_applies_the_next_time":
        "LED de diagnostic allumée — s’applique au prochain réveil du "
        "cadre.",
    "common.diagnostic_led_turned_off_applies_the_next_time":
        "LED de diagnostic éteinte — s’applique au prochain réveil du "
        "cadre.",
    "common.couldn_t_change_that_please_try_again":
        "Impossible de modifier ce réglage — réessayez.",
    "common.saved": "Enregistré — %s",
    "common.couldn_t_save_settings_please_try_again_if_this":
        "Impossible d’enregistrer les réglages — réessayez. Si le "
        "problème persiste, consultez les journaux du service "
        "companion.",
    "common.refresh_requested_server_check_completed":
        "Actualisation demandée — le serveur a fini de vérifier les nouvelles données de vol. "
        "Le cadre peut se mettre à jour lors d’un prochain réveil.",
    "common.poll_trigger_failed_please_try_again_if_this":
        "Échec du déclenchement de la vérification — réessayez. Si le "
        "problème persiste, consultez les journaux du service "
        "companion.",
    "common.a_poll_is_already_in_progress_try_again_in_a":
        "Une vérification est déjà en cours — réessayez dans un "
        "instant.",
    "common.illustration_replaced_the_frame_will_use_it":
        "Illustration remplacée — le cadre l’utilisera à son prochain "
        "réveil et à sa prochaine vérification.",
    "common.couldn_t_use_that_image_upload_a_transparent":
        "Impossible d’utiliser cette image — envoyez un PNG "
        "transparent d’au moins 1200 pixels de large, au format "
        "paysage (plus large que haut).",
    "common.couldn_t_replace_the_illustration_please_try":
        "Impossible de remplacer l’illustration — réessayez. Si le "
        "problème persiste, consultez les journaux du service "
        "companion.",
    "common.airline_name_saved_the_frame_will_pick_it_up":
        "Nom de compagnie enregistré — le cadre le récupérera à son "
        "prochain réveil et à sa prochaine vérification.",
    "common.airline_renamed_new_flights_will_use_it":
        "Nom de compagnie enregistré — Vols et Accueil l’affichent dès "
        "maintenant, et le cadre l’utilisera à son prochain réveil et à "
        "sa prochaine vérification.",
    "common.airline_name_reset_to_skypane_s_name":
        "Nom de SkyPane rétabli — Vols et Accueil l’affichent dès "
        "maintenant, et le cadre l’utilisera à son prochain réveil et à "
        "sa prochaine vérification.",
    "common.that_airline_can_t_be_renamed_anymore":
        "Cette compagnie ne peut plus être renommée ici — rechargez la "
        "page Compagnies et réessayez.",
    "common.the_renamed_airlines_list_is_full_200_entries":
        "La liste des compagnies renommées est pleine (200 entrées) — "
        "rétablissez-en une avant d’en renommer une autre.",
    "common.another_airline_already_uses_that_name":
        "Une autre compagnie utilise déjà ce nom — essayez-en un autre.",
    "common.couldn_t_save_that_airline_name":
        "Impossible d’enregistrer ce nom de compagnie — le dossier d’état "
        "du cadre n’est peut-être pas accessible en écriture.",
    "common.enter_an_airline_name_before_saving":
        "Saisissez un nom de compagnie avant d’enregistrer.",
    "common.that_name_s_too_long_airline_names_top_out_at":
        "Ce nom est trop long — les noms de compagnie sont limités à "
        "100 caractères.",
    "common.that_name_is_reserved_for_the_frame_s_own":
        "Ce nom est réservé à l’illustration de repli du cadre — "
        "utilisez plutôt le vrai nom de la compagnie.",
    "common.that_coverage_gap_isn_t_there_anymore_check":
        "Cette lacune de couverture n’existe plus — consultez État "
        "pour les lacunes actuelles.",
    "common.the_manual_resolution_list_is_full_200_entries":
        "La liste des résolutions manuelles est pleine (200 entrées) "
        "— supprimez-en une avant d’en ajouter une autre.",
    "common.couldn_t_save_that_resolution_the_frame_s_state":
        "Impossible d’enregistrer cette résolution — le dossier "
        "d’état du cadre n’est peut-être pas accessible en écriture.",
    "common.couldn_t_delete_that_entry_the_frame_s_state":
        "Impossible de supprimer cette entrée — le dossier d’état du "
        "cadre n’est peut-être pas accessible en écriture.",
    "common.that_name_can_t_be_used_for_an_illustration_try":
        "Ce nom ne peut pas être utilisé pour une illustration — "
        "essayez une autre orthographe, ou un nom avec des lettres et "
        "des chiffres.",
    "common.rule_added_the_frame_will_use_it_next_time_it":
        "Règle ajoutée — le cadre l’utilisera à son prochain réveil "
        "et à sa prochaine vérification.",
    "common.updated_the_rule_for_key_it_replaces_the_one":
        "Règle mise à jour pour {key} — elle remplace la précédente "
        "et s’appliquera au prochain réveil et à la prochaine "
        "vérification du cadre.",
    "common.that_doesn_t_match_the_selected_kind_s_format_a":
        "Cela ne correspond pas au format du type sélectionné — un "
        "indicatif (par ex. AFR1234), un hex ICAO24 (par ex. "
        "3944F2), ou un préfixe à 3 lettres (par ex. AFR).",
    "common.the_rules_list_is_full_200_entries_delete_an":
        "La liste des règles est pleine (200 entrées) — supprimez-en "
        "une avant d’en ajouter une autre.",
    "common.couldn_t_save_that_rule_the_frame_s_state":
        "Impossible d’enregistrer cette règle — le dossier d’état du "
        "cadre n’est peut-être pas accessible en écriture.",
    "common.rule_deleted_the_frame_will_stop_using_it_next":
        "Règle supprimée — le cadre cessera de l’utiliser à son "
        "prochain réveil et à sa prochaine vérification.",
    "common.couldn_t_delete_that_rule_the_frame_s_state":
        "Impossible de supprimer cette règle — le dossier d’état du "
        "cadre n’est peut-être pas accessible en écriture.",
    "common.connected_n_flight_s_from_this_calendar_in_the":
        "Connecté — {n} vol{s} de ce calendrier dans la fenêtre "
        "actuelle du cadre.",
    "common.saved_but_couldn_t_sync_that_calendar_right_now":
        "Enregistré, mais impossible de synchroniser ce calendrier "
        "pour le moment — vérifiez l’URL et réessayez. Le cadre "
        "continuera de réessayer selon son propre calendrier.",
    "common.calendar_disconnected_the_flights_it_supplied":
        "Calendrier déconnecté — les vols qu’il fournissait ont été "
        "supprimés du serveur.",
    "common.saved_a_poll_was_already_running_so_this":
        "Enregistré — une vérification était déjà en cours, ce "
        "calendrier se synchronisera donc à la prochaine vérification "
        "programmée du cadre.",
    "common.calendar_connected_n_flights_found":
        "Calendrier connecté — {n} vols trouvés.",
    "common.paste_a_valid_calendar_feed_url_to_connect_one":
        "Collez une URL de flux de calendrier valide pour en "
        "connecter un.",

    # The two neutral states freshness.js's refresh loop can be in,
    # rendered onto <body> by companion/ui_shell.py and read client-side;
    # the English forms are also the script's own no-attribute fallbacks.
    "common.paused": "En pause",
    "common.reconnecting": "Reconnexion…",

    # data_table()'s generic empty-rows fallback (companion/ui_components.py).
    "common.no_data_yet": "Aucune donnée pour l’instant.",
    "common.nothing_to_show_here_yet": "Rien à afficher ici pour l’instant.",
}
