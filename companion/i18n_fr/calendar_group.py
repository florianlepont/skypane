# -*- coding: utf-8 -*-
"""French strings for the Calendar row's status line and its Manage sheet
(companion/settings/calendar.py), keyed by stable message id (see
companion/i18n.py's Message/msg()). Every id is declared at its own
display site in companion/settings/calendar.py — this module only carries
each id's French translation.

"Cancel" and the disconnect confirmation page's own strings are
deliberately absent, declared instead in companion/i18n_fr/display.py,
which the auto-merge package would otherwise reject as duplicate ids.
"""

MESSAGES = {
    "calendar_group.connected": "Connecté",
    "calendar_group.not_connected": "Non connecté",
    "calendar_group.pill_out_of_date": "Pas à jour",
    "calendar_group.pill_error": "Erreur",
    "calendar_group.pill_waiting": "En attente",
    "calendar_group.pill_ignored": "Ignoré",
    "calendar_group.pill_check": "À vérifier",
    "calendar_group.1_flight_in_the_next_48_h_checked":
        "1 vol dans les 48 h · vérifié %s",
    "calendar_group.flights_in_the_next_48_h_checked":
        "%d vols dans les 48 h · vérifié %s",
    "calendar_group.0_flights_found_check_it_s_the_right_calendar":
        "0 vol trouvé — vérifiez que c’est le bon calendrier · vérifié %s",
    "calendar_group.first_read_at_the_frame_s_next_check":
        "Première lecture au prochain passage du cadre",
    "calendar_group.last_read_the_frame_keeps_the_last_flights":
        "Dernière lecture %s · le cadre garde les derniers vols lus",
    "calendar_group.couldn_t_read_the_calendar_last_read":
        "Lecture impossible · dernière lecture %s",
    "calendar_group.couldn_t_read_the_calendar":
        "Lecture du calendrier impossible",
    "calendar_group.saved_link_ignored_it_was_readable_by_others":
        "Lien enregistré ignoré — il était lisible par d’autres sur le "
        "serveur. Collez-le à nouveau pour le stocker en sûreté.",
    "calendar_group.no_calendar": "Aucun calendrier",
    "calendar_group.colour_the_flights_from_your_calendar_on_screen":
        "Colorez à l’écran les vols de votre calendrier.",
    "calendar_group.manage": "Gérer",
    "calendar_group.connect": "Connecter",
    "calendar_group.replace": "Remplacer",
    "calendar_group.checking": "Vérification…",
    "calendar_group.sheet_title_template": "Calendrier %s",
    "calendar_group.connect_a_calendar": "Connecter un calendrier",
    "calendar_group.calendar_link": "Lien du calendrier",
    "calendar_group.new_link": "Nouveau lien",
    "calendar_group.private_link_never_shown_again":
        "Lien privé, jamais réaffiché",
    "calendar_group.https_or_webcal": "https:// ou webcal://…",
    "calendar_group.the_private_ical_link_it_stays_on_the_server":
        "Le lien iCal privé. Il reste sur le serveur et n’est jamais "
        "réaffiché.",
    "calendar_group.the_old_link_stays_active_until_the_new_one":
        "L’ancien lien reste actif tant que le nouveau n’a pas répondu.",
    "calendar_group.only_colours_a_flight_already_on_screen":
        "Colore seulement un vol déjà à l’écran ; ne suit ni n’annonce "
        "rien. Pris en compte au prochain réveil du cadre.",
    "calendar_group.that_isn_t_a_calendar_link":
        "Ce n’est pas un lien de calendrier : il doit commencer par "
        "https:// ou webcal://.",
    "calendar_group.that_link_doesn_t_answer_nothing_was_changed":
        "Ce lien ne répond pas. Rien n’a été modifié.",
    "calendar_group.close": "Fermer",
    "calendar_group.disconnect": "Déconnecter",
    "calendar_group.disconnect_provider": "Déconnecter %s ?",
    "calendar_group.the_link_and_the_flights_it_supplied_are_deleted":
        "Le lien et les vols qu’il fournissait sont supprimés du "
        "serveur. Pour reconnecter, collez à nouveau le lien.",
}
