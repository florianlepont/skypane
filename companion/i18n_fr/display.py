# -*- coding: utf-8 -*-
"""French strings for the Display and Device pages. Every key is the
exact English source string a call site in
companion/pages/config_page.py passes to companion.i18n.t(), including
any "%s"/"%d"/"{n}" placeholder shape.

"Theme", "Display" and "Device" are already defined in
companion/i18n_fr/nav.py, and "Screen" in
companion/i18n_fr/health.py — deliberately absent here since the
package's duplicate-key guard would raise otherwise. Every theme/runway
*name* shown to people, and the screen label, are translated at the
config_page.py display sites that call i18n.t() on the registry's own
returned text; their French entries live in companion/i18n_fr/registry.py,
not here.

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
    "Applies the next time the frame wakes up.":
        "S’applique au prochain réveil du cadre.",

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

    # --- Aspect card ---------------------------------------------------
    # This identity translation is required, not optional: the
    # FR-completeness harness fails an untranslated key regardless of
    # the two words being the same. A different English key from the
    # pre-existing "Look": "Aspect" entry above (Display's supersection
    # heading), not a duplicate of it.
    "Aspect": "Aspect",
    "Departures": "Départs",
    "Arrivals": "Arrivées",
    "Calendar flights": "Vols du calendrier",
    "Per-flight rules": "Règles par vol",
    "Same as departures": "Comme les départs",
    "1 rule": "1 règle",
    "%d rules": "%d règles",
    "No rules yet": "Aucune règle pour l’instant",
    "Selected": "Sélectionné",
    # The one-line legend under the rule-add form's compact chip grid,
    # naming the two swatch dots as departures/arrivals, joined into
    # one phrase with no separator.
    "Departures & arrivals": "Départs et arrivées",
    "Current": "Actuel",

    # --- The live theme preview above the chip grid -----------------
    "Live preview of the %s theme": "Aperçu en direct du thème %s",
    "Preview with your last flight: %s":
        "Aperçu avec votre dernier vol : %s",
    "Preview with a sample flight": "Aperçu avec un vol d’exemple",

    # --- Runway card ---------------------------------------------------
    "Runway": "Piste",
    "Which Orly runway the device watches.":
        "Quelle piste d’Orly l’appareil surveille.",
    "Airport diagram for %s": "Schéma de l’aéroport pour %s",

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
    "Callsign": "Indicatif",
    "ICAO24 hex": "Code hexadécimal ICAO24",
    "Callsign prefix": "Préfixe d’indicatif",
    "Delete": "Supprimer",

    # --- Quiet hours card ------------------------------------------------
    "Quiet hours": "Heures calmes",
    "Pauses the frame's wake, poll and display cycle during the "
    "schedule below.":
        "Suspend le réveil, la vérification et l’affichage du cadre "
        "pendant cette plage.",
    "Start": "Début",
    "End": "Fin",
    # The two quiet-hours dial handles' accessible names. Each handle is
    # a real <button> carrying role="slider" with a bare time as its
    # aria-valuetext, so only these two names need a French sibling.
    # Not composed from "Quiet hours" + "Start": a French accessible
    # name is a phrase, not two catalogue keys joined with a space.
    "Quiet hours start": "Début des heures calmes",
    "Quiet hours end": "Fin des heures calmes",
    # The duration ladder's client-side wordings, pinned equal to
    # duration_text()'s own return per bucket. The real U+00A0 between
    # "#" and the unit matches duration_text()'s French branch
    # byte-for-byte; a plain space would silently desync the two.
    "#s": "# s",
    "#m": "# min",
    "#h": "# h",
    "#d": "# j",
    "Night": "Nuit",
    "Day": "Journée",
    "Always on": "Toujours actif",
    "On": "Allumé",
    "Off": "Éteint",
    "Switch on": "Allumer",
    "Switch off": "Éteindre",
    "Turn on": "Activer",
    "Turn off": "Désactiver",
    "On — %s to %s": "Allumé — %s à %s",

    # --- Device-only groups ----------------------------------------------
    "Diagnostic LED": "LED de diagnostic",
    "Lit only during the device's brief wake window.":
        "Allumée seulement pendant la brève période de réveil.",
    "Wake interval": "Intervalle de réveil",
    "Shorter: fresher data, more battery drain.":
        "Plus court, données plus fraîches, batterie sollicitée.",
    "Wake interval (seconds)": "Intervalle de réveil (secondes)",
    # The range input's own accessible name, distinct from the number
    # input's label above — two controls sharing one accessible name is
    # how a screen-reader visitor loses track of which they are on.
    "Wake interval slider": "Curseur d’intervalle de réveil",
    # The two gauges: "#" is the quantity's place in both, and the unit
    # is always whole minutes in both languages, which keeps these
    # sentences free of a plural form. U+00A0 between the number and
    # its unit, as layout.duration_text() does for its French branch.
    "A plane reaches the frame at most # min later.":
        "Un avion apparaît sur le cadre au plus # min plus tard.",
    # The two absolute-figure wordings, singular and plural both — a
    # days count of 1 is reachable (a nearly empty battery).
    "≈ # day of battery left, from this frame's own recent readings.":
        "≈ # jour d’autonomie restante, d’après les relevés "
        "récents de ce cadre.",
    "≈ # days of battery left, from this frame's own recent readings.":
        "≈ # jours d’autonomie restante, d’après les relevés "
        "récents de ce cadre.",
    "Not enough battery history yet to say how long a charge lasts.":
        "Pas encore assez d’historique de batterie pour dire combien "
        "de temps dure une charge.",
    "While the screen is off, the frame wakes every %s instead.":
        "Quand l’écran est éteint, le cadre se réveille toutes les %s "
        "à la place.",
    # "%d" is the saved cadence, filled server-side; "#" is the
    # proposed one, filled client-side as the slider moves. The
    # relative clause names both cadences rather than a ratio, so it
    # carries no decimal at all.
    "This setting wakes the frame every # min instead of every %d min.":
        "Ce réglage réveille le cadre toutes les # min au lieu de toutes "
        "les %d min.",
    "Uses server default": "Utilise la valeur par défaut du serveur",
    "Manual refresh": "Actualisation manuelle",
    "Trigger an immediate poll cycle.":
        "Déclenchez un cycle de vérification immédiat.",
    "Trigger poll now": "Déclencher une vérification maintenant",
    "Polling…": "Vérification en cours…",
    "Poll triggered recently — try again in {n}s.":
        "Vérification déclenchée récemment — réessayez dans {n} s.",

    # --- Save --------------------------------------------------------
    "Save settings": "Enregistrer les réglages",
    "Next wake": "Prochain réveil",
    " (next wake ≈ %s)": " (prochain réveil ≈ %s)",

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

    # --- Field-level validation errors ------------------------------
    "That is not one of the available choices.":
        "Ce n’est pas l’un des choix disponibles.",
    "That switch sent an unexpected value.":
        "Cet interrupteur a envoyé une valeur inattendue.",
    "Enter a whole number of seconds between 60 and 3600.":
        "Entrez un nombre entier de secondes entre 60 et 3600.",
    "Enter a time as HH:MM, for example 23:00.":
        "Entrez une heure au format HH:MM, par exemple 23:00.",
    "That link is too long, or conflicts with the disconnect option "
    "below.":
        "Ce lien est trop long, ou entre en conflit avec l’option de "
        "déconnexion ci-dessous.",
    # The Notifications topic-URL field's own shorter error, distinct
    # from the calendar URL's longer message above.
    "That link is too long.": "Ce lien est trop long.",
}
