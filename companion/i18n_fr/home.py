# -*- coding: utf-8 -*-
"""French strings for the Home page (companion/pages/home_page.py).
Every entry is migrated onto a stable message id: the source-side
Message is declared where the English constant already lives
(companion/pages/home_page.py, companion/frame_state.py,
companion/ui_base.py), never here — this module only carries each id's
French translation.

Deliberately absent: "Home" — companion/i18n_fr/nav.py already owns
that id, and home_page.py's page-title render site reuses that Message
rather than redeclaring it (the auto-merge package raises ValueError on
a duplicate id across sibling modules).

Copy follows sentence case, the typographic apostrophe (U+2019,
never a straight quote), and a non-breaking space (U+00A0) before
":" ";" "?" "!".
"""

MESSAGES = {
    "home.greeting_default": "Bonjour",
    "home.greeting_with_name": "%s %s",
    "home.greeting_morning": "Bonjour",
    "home.greeting_afternoon": "Bon après-midi",
    "home.greeting_evening": "Bonsoir",
    "home.greeting_night": "Bonne nuit",

    "home.the_picture_currently_on_the_frame":
        "L’image actuellement affichée sur le cadre",
    "home.the_picture_currently_on_the_frame_flight":
        "L’image actuellement affichée sur le cadre\u00a0: %s",
    "home.the_server_saves_a_copy_of_each_picture_it":
        "Le serveur conserve une copie de chaque image envoyée au cadre ; "
        "la plus récente apparaîtra ici.",

    "home.departing": "Au départ",
    "home.arriving": "À l’arrivée",
    "home.overhead": "Au-dessus",

    # Reconciled to the same French key the frame-strip headline
    # consumer (companion/layout.py's frame_strip_html()) renders
    # live — grammatical agreement matches that shared context, not
    # a re-derivation of this page's own former wording.
    "home.next_update": "Prochain rafraîchissement %s",
    "home.expected_since": "Mise à jour en retard · attendue à %s",

    # companion/layout.py's own frame_strip_html(), keyed here for
    # the same shared-catalogue reason as the entry above.
    "home.change_the_schedule": "Modifier l’horaire",

    "home.frame": "Cadre",
    "home.no_reading_yet": "Aucune mesure pour l’instant",

    "home.cycle_ring": "Cycle du cadre\u00a0: prochain rafraîchissement %s",
    "home.frame_state": "État du cadre",
    "home.state_screen_on": "Écran allumé",
    "home.state_title_screen_off": "Écran éteint",
    "home.state_detail_screen_off": "Le cadre reste vide",
    "home.state_title_quiet_hours": "Heures calmes",
    "home.state_detail_quiet_hours": "L’écran se repose jusqu’à %s",
    "home.state_title_battery": "Batterie très faible",
    "home.state_detail_battery": "Le cadre se repose jusqu’à sa recharge",
    "home.cadence_info":
        "Le cadre dort entre deux mises à jour pour économiser sa batterie\u00a0: "
        "il se réveille environ toutes les %s, il ne se rafraîchit donc pas en continu.",
    "home.cadence_info_label": "À propos des mises à jour",
    "home.cadence_no_interval":
        "Pour économiser sa batterie, le cadre dort entre deux mises à jour\u00a0: "
        "il ne se rafraîchit donc pas en continu.",
    "home.switches": "Commandes du cadre",
    "home.group_frame": "Cadre",
    "home.edit_quiet_hours": "Modifier les heures calmes (%s)",
    "home.use_quiet_hours": "Utiliser les heures calmes",
    "home.save_quiet_hours": "Enregistrer les heures calmes",
    "home.quiet_hours_zone_sentence": "Fuseau\u00a0: {zone}. Changer dans {card}.",
    "home.quiet_intro": "Quand l’écran doit-il se reposer\u00a0?",
    "home.quiet_presets_label": "Préréglages des heures calmes",
    "home.quiet_or_choose": "Ou choisir ses heures",
    "home.battery_label": "Batterie",
    "home.rename_frame_label": "Nom du cadre",
    "home.battery_aria": "Batterie à environ %s",
    "home.battery_low": "Faible",
    "home.battery_critical": "Très faible",
    "home.battery_row_percent": "%d\u00a0%%",
    "home.battery_row_none": "Aucune mesure pour l’instant",
    "home.battery_row_autonomy": "autonomie %s",
    "home.battery_row_autonomy_short": "moins de 2 jours",
    "home.battery_row_autonomy_days": "~%d jours",
    "home.battery_row_autonomy_weeks": "~%d semaines",
    "home.battery_fact_empty": "Batterie · Aucune mesure pour l’instant",
    "home.action_needed": "Un élément demande votre attention",

    "home.recent_flights": "Vols récents",
    "home.see_all_flights": "Voir tous les vols",
    "home.no_flights_yet": "Aucun vol pour l’instant.",
    "home.the_first_aircraft_the_frame_detects_on_the":
        "Le premier avion détecté par le cadre sur la piste surveillée "
        "apparaîtra ici.",
    "home.illustration": "Illustration %s",
    "home.device_no_image_heading": "Pas encore d’image",
    "home.device_no_image_body":
        "La première image apparaîtra après une vérification ou le premier "
        "réveil du cadre.",

    "home.notice_explain_not_seen":
        "Votre cadre n’a pas encore contacté SkyPane.",
    "home.notice_explain_overdue":
        "Votre cadre ne s’est pas manifesté à l’heure.",
    "home.notice_explain_low_battery":
        "La batterie de votre cadre est faible.",
    "home.notice_explain_no_contact":
        "Votre cadre n’est plus en contact avec le serveur.",
    "home.notice_line_battery": "Batterie du cadre à %d %%",
    "home.notice_line_charging": "Le cadre est peut-être en charge.",
    "home.notice_line_last_check_in": "Dernière connexion du cadre : %s",
    "home.notice_line_last_contact": "Dernier contact : %s",
    "home.notice_tip_low_battery": "Rechargez-le ou branchez-le.",
    "home.notice_tip_overdue":
        "Attendez un cycle, s’il reste muet, contactez un administrateur.",
    "home.notice_tip_not_seen":
        "Vérifiez qu’il est alimenté, s’il reste muet, contactez un "
        "administrateur.",
    "home.notice_tip_no_contact":
        "Vérifiez son alimentation et votre Wi-Fi, s’il reste muet, contactez "
        "un administrateur.",
    "home.notice_contact_label": "Contacter un administrateur",
    "home.notice_mail_subject": "SkyPane : aide pour le cadre %s (%s)",
    "home.notice_mail_body":
        "Bonjour,\n\nMon cadre %s affiche l’état %s dans SkyPane.\n%s\nPouvez-vous "
        "regarder ?\n",
}
