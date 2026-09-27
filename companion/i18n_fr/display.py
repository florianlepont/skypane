# -*- coding: utf-8 -*-
"""French strings for the Display and Device pages.

Mid-migration: CATALOG below still carries every entry whose only
declaring call site is companion/pages/config_page.py (not yet
migrated onto companion.i18n.Message this plan) or one of
companion/settings/notifications.py, calendar.py, rules.py (declared
later in this same plan's second task) — each key there is still the
exact English source string that call site passes to
companion.i18n.t(), including any "%s"/"%d"/"{n}" placeholder shape.
MESSAGES carries every entry already declared as a stable-id Message by
a settings module this plan's first task migrated, or by an earlier
plan's shared/page module (ui_base.py, frame_state.py, flash.py,
history_page.py, airlines_page.py) — this module only carries each
id's French translation there.

"Theme", "Display" and "Device" are already defined in
companion/i18n_fr/nav.py, and "Screen" in
companion/i18n_fr/health.py — deliberately absent here since the
package's duplicate-key/id guard would raise otherwise. Every
theme/runway *name* shown to people, and the screen label, are
translated at the config_page.py/settings display sites that call
i18n.t() on the registry's own returned text; their French entries live
in companion/i18n_fr/registry.py, not here.

Copy follows sentence case, the typographic apostrophe (U+2019, never
a straight quote), and a non-breaking space (U+00A0) before
":" ";" "?" "!".
"""

CATALOG = {
    # --- Display/Device page shells -------------------------------------
    "Everything about what the frame shows and when.":
        "Tout ce que le cadre affiche, et quand.",
    "Hardware, data and diagnostics for the frame.":
        "Matériel, données et diagnostics du cadre.",
    "Settings": "Réglages",
    "Screen: %s": "Écran : %s",
    "Screen type": "Type d’écran",

    # --- Display's three supersections ----------------------------
    "Look": "Aspect",
    "— the theme, flight colours and calendar that decide how the "
    "picture looks.":
        "— le thème, les couleurs de vol et le calendrier qui "
        "décident de l’apparence de l’image.",
    "What it watches": "Ce qu’il surveille",
    "— which Orly runway the frame is watching.":
        "— quelle piste d’Orly le cadre surveille.",
    "When it is on": "Quand il est allumé",
    "— when the screen is lit and when it stays quiet.":
        "— quand l’écran est allumé et quand il reste silencieux.",

    # --- Device's own two supersections plus the Poll card's own
    #     one-card supersection -------------------------------------
    "When it wakes": "Quand il se réveille",
    "— how often the frame wakes up to fetch a new picture.":
        "— à quelle fréquence le cadre se réveille pour récupérer une "
        "nouvelle image.",
    "How it tells you": "Comment il vous prévient",
    "— the light on the frame and the alerts on your phone.":
        "— le voyant du cadre et les alertes sur votre téléphone.",
    "When you can't wait": "Quand vous ne pouvez pas attendre",
    "— fetch a new picture right now.":
        "— récupère une nouvelle image tout de suite.",

    # --- Aspect card's rules usage row -----------------------------
    "1 rule": "1 règle",
    "%d rules": "%d règles",
    "No rules yet": "Aucune règle pour l’instant",

    # --- Calendar row's connection block --------------------------------
    # The confirmation-page strings below (with a question mark, or
    # naming "calendar"/"calendar?" alone) belong to
    # calendar_disconnect_confirm_page(); the merged card's own small
    # Disconnect button reads the shorter "Disconnect" instead
    # (companion/i18n_fr/calendar_group.py).
    "Connected, but ignored — its saved link on the server became "
    "readable beyond this frame. Paste the feed URL again below to "
    "store it safely.":
        "Connecté, mais ignoré — son lien enregistré sur le serveur "
        "est devenu lisible au-delà de ce cadre. Collez à nouveau "
        "l’URL du flux ci-dessous pour le stocker en sécurité.",
    "Calendar feed URL": "URL du flux du calendrier",
    "Your calendar's private iCal link. Stored on the server and "
    "never shown back here — pasting a new one replaces the old.":
        "Le lien iCal privé de votre calendrier. Stocké sur le serveur "
        "et jamais réaffiché ici — en coller un nouveau remplace "
        "l’ancien.",
    "Disconnect this calendar and delete the flights it supplied?":
        "Déconnecter ce calendrier et supprimer les vols qu’il a "
        "fournis ?",
    "Disconnect calendar?": "Déconnecter le calendrier ?",
    "This disconnects your calendar and deletes the flights it "
    "supplied from the server. This can't be undone — you'd need to "
    "paste the feed URL again to reconnect.":
        "Ceci déconnecte votre calendrier et supprime du serveur les "
        "vols qu’il a fournis. Cette action est irréversible — vous "
        "devrez coller à nouveau l’URL du flux pour vous reconnecter.",
    "Disconnect calendar": "Déconnecter le calendrier",
    "Cancel": "Annuler",

    # --- Flight colours / per-flight rules ------------------------------
    "Match by": "Correspondance par",
    "Value": "Valeur",
    "Add rule": "Ajouter la règle",
    "ICAO24 hex": "Code hexadécimal ICAO24",
    "Callsign prefix": "Préfixe d’indicatif",

    # --- Device-only groups: two retired action wordings that reach no
    # i18n.t() call any more (a role="switch" control is now named by
    # the setting via aria-labelledby, never by an action) — kept only
    # as names a test asserts are no longer rendered.
    "Switch on": "Allumer",
    "Switch off": "Éteindre",
    "Turn on": "Activer",
    "Turn off": "Désactiver",

    "Manual refresh": "Actualisation manuelle",
    "Trigger an immediate poll cycle.":
        "Déclenchez un cycle de vérification immédiat.",
    "Trigger poll now": "Déclencher une vérification maintenant",
    "Polling…": "Vérification en cours…",

    # --- Save --------------------------------------------------------
    "Save settings": "Enregistrer les réglages",
    "Next wake": "Prochain réveil",

    # The restored dirty-save-bar's connector/progress words and the
    # "Saving…" progressive, sharing the "Enregistrer les réglages"
    # verb and the "Vérification en cours…" ellipsis style above.
    "Saving…": "Enregistrement…",
    "Unsaved changes": "Modifications non enregistrées",
    " changed": " modifié",
    " and ": " et ",
    ", and ": " et ",
    "1 unsaved change": "1 modification non enregistrée",
    " unsaved changes": " modifications non enregistrées",

    # The Notifications topic-URL field's own shorter error, distinct
    # from the calendar URL's longer message below.
    "That link is too long.": "Ce lien est trop long.",
}

MESSAGES = {
    # --- Display/Device page shells -------------------------------------
    "display.selected": "Sélectionné",
    "display.current": "Actuel",

    # --- Display's three supersections ----------------------------
    # This identity translation is required, not optional: the
    # FR-completeness harness fails an untranslated key regardless of
    # the two words being the same. A different id from "display.look"
    # above (Display's supersection heading), not a duplicate of it.
    "display.aspect": "Aspect",
    "display.applies_the_next_time_the_frame_wakes_up":
        "S’applique au prochain réveil du cadre.",

    # --- Aspect card ---------------------------------------------------
    "display.departures": "Départs",
    "display.arrivals": "Arrivées",
    "display.calendar_flights": "Vols du calendrier",
    "display.per_flight_rules": "Règles par vol",
    "display.same_as_departures": "Comme les départs",
    # The one-line legend under the rule-add form's compact chip grid,
    # naming the two swatch dots as departures/arrivals, joined into
    # one phrase with no separator.
    "display.departures_arrivals": "Départs et arrivées",

    # --- The live theme preview above the chip grid -----------------
    "display.live_preview_of_the_theme": "Aperçu en direct du thème %s",
    "display.preview_with_your_last_flight":
        "Aperçu avec votre dernier vol : %s",
    "display.preview_with_a_sample_flight": "Aperçu avec un vol d’exemple",

    # --- Runway card ---------------------------------------------------
    "display.runway": "Piste",
    "display.which_orly_runway_the_device_watches":
        "Quelle piste d’Orly l’appareil surveille.",
    "display.airport_diagram_for": "Schéma de l’aéroport pour %s",

    # --- Calendar row's connection block --------------------------------
    "display.callsign": "Indicatif",
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
    "display.poll_triggered_recently_try_again_in_n_s":
        "Vérification déclenchée récemment — réessayez dans {n} s.",

    # --- Save --------------------------------------------------------
    "display.next_wake_2": " (prochain réveil ≈ %s)",

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
}
