# -*- coding: utf-8 -*-
"""French strings for the Display and Device pages, keyed by stable
message id (see companion/i18n.py's Message/msg()). Every id is
declared at its own display site, in companion/pages/config_page.py or
one of companion/settings/*.py — this module only carries each id's
French translation.

"Theme", "Display" and "Device" are already defined in
companion/i18n_fr/nav.py, and "Screen" in
companion/i18n_fr/health.py — deliberately absent here since the
package's duplicate-id guard would raise otherwise. Every theme/runway
*name* shown to people, and the screen label, are translated at the
config_page.py/settings display sites that call i18n.t() on the
registry's own returned text; their French entries live in
companion/i18n_fr/registry.py, not here.

Copy follows sentence case, the typographic apostrophe (U+2019, never
a straight quote), and a non-breaking space (U+00A0) before
":" ";" "?" "!".

Four retired action wordings ("Switch on"/"Switch off"/"Turn on"/
"Turn off", French "Allumer"/"Éteindre"/"Activer"/"Désactiver") used to
live here as a legacy English-keyed residual: a role="switch" control
is now named by the setting via aria-labelledby, never by an action,
so companion/ui_base.py's own QUICK_ACTION_SWITCH_ON_BUTTON/
QUICK_ACTION_SWITCH_OFF_BUTTON/QUICK_ACTION_QUIET_TURN_ON_BUTTON/
QUICK_ACTION_QUIET_TURN_OFF_BUTTON reach no i18n.t() call site any
more. With no call site left to declare a stable-id Message, and the
legacy English-keyed lookup removed entirely, these four entries were
deleted rather than migrated. Reintroducing one of these actions means
adding a fresh i18n.msg() declaration and a fresh MESSAGES entry, not
restoring these.
"""

MESSAGES = {
    # --- Display/Device page shells -------------------------------------
    "display.everything_about_what_the_frame_shows_and_when":
        "Tout ce que le cadre affiche, et quand.",
    "display.hardware_data_and_diagnostics_for_the_frame":
        "Matériel, données et diagnostics du cadre.",
    "display.settings": "Réglages",
    "display.screen": "Écran : %s",
    "display.screen_type": "Type d’écran",
    "display.selected": "Sélectionné",
    "display.current": "Actuel",

    # --- Display's three supersections ----------------------------
    "display.look": "Aspect",
    "display.the_theme_flight_colours_and_calendar_that":
        "— le thème, les couleurs de vol et le calendrier qui "
        "décident de l’apparence de l’image.",
    "display.what_it_watches": "Ce qu’il surveille",
    "display.which_orly_runway_the_frame_is_watching":
        "— quelle piste d’Orly le cadre surveille.",
    "display.when_it_is_on": "Quand il est allumé",
    "display.when_the_screen_is_lit_and_when_it_stays_quiet":
        "— quand l’écran est allumé et quand il reste silencieux.",
    "display.applies_the_next_time_the_frame_wakes_up":
        "S’applique au prochain réveil du cadre.",

    # --- Device's own two supersections plus the Poll card's own
    #     one-card supersection -------------------------------------
    "display.when_it_wakes": "Quand il se réveille",
    "display.how_often_the_frame_wakes_up_to_fetch_a_new":
        "— à quelle fréquence le cadre se réveille pour récupérer une "
        "nouvelle image.",
    "display.how_it_tells_you": "Comment il vous prévient",
    "display.the_light_on_the_frame_and_the_alerts_on_your":
        "— le voyant du cadre et les alertes sur votre téléphone.",
    "display.when_you_can_t_wait": "Quand vous ne pouvez pas attendre",
    "display.fetch_a_new_picture_right_now":
        "— récupère une nouvelle image tout de suite.",

    # --- Aspect card ---------------------------------------------------
    # This identity translation is required, not optional: the
    # FR-completeness harness fails an untranslated id regardless of
    # the two words being the same. A different id from "display.look"
    # above (Display's supersection heading), not a duplicate of it.
    "display.aspect": "Aspect",
    "display.departures": "Départs",
    "display.arrivals": "Arrivées",
    "display.calendar_flights": "Vols du calendrier",
    "display.per_flight_rules": "Règles par vol",
    "display.same_as_departures": "Comme les départs",
    "display.1_rule": "1 règle",
    "display.rules": "%d règles",
    "display.no_rules_yet": "Aucune règle pour l’instant",
    # The one-line legend under the rule-add form's compact chip grid,
    # naming the two swatch dots as departures/arrivals, joined into
    # one phrase with no separator.
    "display.departures_arrivals": "Départs et arrivées",

    # --- The live theme preview above the chip grid -----------------
    "display.live_preview_of_the_theme": "Aperçu en direct du thème %s",
    "display.preview_with_your_last_flight":
        "Aperçu avec votre dernier vol : %s",
    "display.preview_with_a_sample_flight": "Aperçu avec un vol d’exemple",
    # The theme chip grid's per-chip image alt text (companion/theme_
    # preview.py). Never translated before this id existed either — kept
    # identical to the English so the render stays byte-for-byte
    # unchanged (see test_i18n.py's _UNCHANGED_IN_FRENCH); a real French
    # alt text is a follow-up, not a rendered-output change this
    # refactor-only migration may make.
    "display.sample_panel_rendered_in_the_theme":
        "Sample panel rendered in the %s theme",

    # --- Runway card ---------------------------------------------------
    "display.runway": "Piste",
    "display.which_orly_runway_the_device_watches":
        "Quelle piste d’Orly l’appareil surveille.",
    "display.airport_diagram_for": "Schéma de l’aéroport pour %s",

    # --- Calendar row's connection block --------------------------------
    # The confirmation-page strings below (with a question mark, or
    # naming "calendar"/"calendar?" alone) belong to
    # calendar_disconnect_confirm_page(); the merged card's own small
    # Disconnect button reads the shorter "Disconnect" instead
    # (companion/i18n_fr/calendar_group.py).
    "display.connected_but_ignored_its_saved_link_on_the":
        "Connecté, mais ignoré — son lien enregistré sur le serveur "
        "est devenu lisible au-delà de ce cadre. Collez à nouveau "
        "l’URL du flux ci-dessous pour le stocker en sécurité.",
    "display.calendar_feed_url": "URL du flux du calendrier",
    "display.your_calendar_s_private_ical_link_stored_on_the":
        "Le lien iCal privé de votre calendrier. Stocké sur le serveur "
        "et jamais réaffiché ici — en coller un nouveau remplace "
        "l’ancien.",
    "display.disconnect_this_calendar_and_delete_the_flights":
        "Déconnecter ce calendrier et supprimer les vols qu’il a "
        "fournis ?",
    "display.disconnect_calendar": "Déconnecter le calendrier ?",
    "display.this_disconnects_your_calendar_and_deletes_the":
        "Ceci déconnecte votre calendrier et supprime du serveur les "
        "vols qu’il a fournis. Cette action est irréversible — vous "
        "devrez coller à nouveau l’URL du flux pour vous reconnecter.",
    "display.disconnect_calendar_2": "Déconnecter le calendrier",
    "display.cancel": "Annuler",

    # --- Flight colours / per-flight rules ------------------------------
    "display.match_by": "Correspondance par",
    "display.value": "Valeur",
    "display.add_rule": "Ajouter la règle",
    "display.callsign": "Indicatif",
    "display.icao24_hex": "Code hexadécimal ICAO24",
    "display.callsign_prefix": "Préfixe d’indicatif",
    "display.delete": "Supprimer",

    # --- Quiet hours card ------------------------------------------------
    "display.quiet_hours": "Heures calmes",
    "display.pauses_the_frame_s_wake_poll_and_display_cycle":
        "Suspend le réveil, la vérification et l’affichage du cadre "
        "pendant cette plage.",
    "display.start": "Début",
    "display.end": "Fin",
    # The two quiet-hours dial handles' accessible names. Each handle is
    # a real <button> carrying role="slider" with a bare time as its
    # aria-valuetext, so only these two names need a French sibling.
    # Not composed from "Quiet hours" + "Start": a French accessible
    # name is a phrase, not two catalogue entries joined with a space.
    "display.quiet_hours_start": "Début des heures calmes",
    "display.quiet_hours_end": "Fin des heures calmes",
    # The duration ladder's client-side wordings, pinned equal to
    # duration_text()'s own return per bucket. The real U+00A0 between
    # "#" and the unit matches duration_text()'s French branch
    # byte-for-byte; a plain space would silently desync the two.
    "display.s": "# s",
    "display.m": "# min",
    "display.h": "# h",
    "display.d": "# j",
    "display.night": "Nuit",
    "display.day": "Journée",
    "display.always_on": "Toujours actif",
    "display.on": "Allumé",
    "display.off": "Éteint",
    "display.on_to": "Allumé — %s à %s",

    # --- Device-only groups ----------------------------------------------
    "display.diagnostic_led": "LED de diagnostic",
    "display.lit_only_during_the_device_s_brief_wake_window":
        "Allumée seulement pendant la brève période de réveil.",
    "display.wake_interval": "Intervalle de réveil",
    "display.shorter_fresher_data_more_battery_drain":
        "Plus court, données plus fraîches, batterie sollicitée.",
    "display.wake_interval_seconds": "Intervalle de réveil (secondes)",
    # The range input's own accessible name, distinct from the number
    # input's label above — two controls sharing one accessible name is
    # how a screen-reader visitor loses track of which they are on.
    "display.wake_interval_slider": "Curseur d’intervalle de réveil",
    # The two gauges: "#" is the quantity's place in both, and the unit
    # is always whole minutes in both languages, which keeps these
    # sentences free of a plural form. U+00A0 between the number and
    # its unit, as layout.duration_text() does for its French branch.
    "display.a_plane_reaches_the_frame_at_most_min_later":
        "Un avion apparaît sur le cadre au plus # min plus tard.",
    # The two absolute-figure wordings, singular and plural both — a
    # days count of 1 is reachable (a nearly empty battery).
    "display.day_of_battery_left_from_this_frame_s_own":
        "≈ # jour d’autonomie restante, d’après les relevés "
        "récents de ce cadre.",
    "display.days_of_battery_left_from_this_frame_s_own":
        "≈ # jours d’autonomie restante, d’après les relevés "
        "récents de ce cadre.",
    "display.not_enough_battery_history_yet_to_say_how_long":
        "Pas encore assez d’historique de batterie pour dire combien "
        "de temps dure une charge.",
    "display.while_the_screen_is_off_the_frame_wakes_every":
        "Quand l’écran est éteint, le cadre se réveille toutes les %s "
        "à la place.",
    # "%d" is the saved cadence, filled server-side; "#" is the
    # proposed one, filled client-side as the slider moves. The
    # relative clause names both cadences rather than a ratio, so it
    # carries no decimal at all.
    "display.this_setting_wakes_the_frame_every_min_instead":
        "Ce réglage réveille le cadre toutes les # min au lieu de toutes "
        "les %d min.",
    "display.uses_server_default": "Utilise la valeur par défaut du serveur",
    "display.manual_refresh": "Actualisation manuelle",
    "display.trigger_an_immediate_poll_cycle":
        "Déclenchez un cycle de vérification immédiat.",
    "display.trigger_poll_now": "Déclencher une vérification maintenant",
    "display.polling": "Vérification en cours…",
    "display.poll_triggered_recently_try_again_in_n_s":
        "Vérification déclenchée récemment — réessayez dans {n} s.",

    # --- Save --------------------------------------------------------
    "display.save_settings": "Enregistrer les réglages",
    "display.next_wake": "Prochain réveil",
    "display.next_wake_2": " (prochain réveil ≈ %s)",
    # Symbolic notation ("≈" plus a placeholder already localized by its
    # caller), identical in both languages — not a missed translation,
    # listed in test_i18n.py's _UNCHANGED_IN_FRENCH cognate set.
    "display.next_wake_approx": "≈ %s",

    # The restored dirty-save-bar's connector/progress words and the
    # "Saving…" progressive, sharing the "Enregistrer les réglages"
    # verb and the "Vérification en cours…" ellipsis style above.
    "display.saving": "Enregistrement…",
    "display.unsaved_changes": "Modifications non enregistrées",
    "display.changed": " modifié",
    "display.and": " et ",
    "display.and_2": " et ",
    "display.1_unsaved_change": "1 modification non enregistrée",
    "display.unsaved_changes_2": " modifications non enregistrées",

    # --- Field-level validation errors ------------------------------
    "display.that_is_not_one_of_the_available_choices":
        "Ce n’est pas l’un des choix disponibles.",
    "display.that_switch_sent_an_unexpected_value":
        "Cet interrupteur a envoyé une valeur inattendue.",
    "display.enter_a_whole_number_of_seconds_between_60_and":
        "Entrez un nombre entier de secondes entre 60 et 3600.",
    "display.enter_a_time_as_hh_mm_for_example_23_00":
        "Entrez une heure au format HH:MM, par exemple 23:00.",
    "display.that_link_is_too_long_or_conflicts_with_the":
        "Ce lien est trop long, ou entre en conflit avec l’option de "
        "déconnexion ci-dessous.",
    # The Notifications topic-URL field's own shorter error, distinct
    # from the calendar URL's longer message above.
    "display.that_link_is_too_long": "Ce lien est trop long.",
}
