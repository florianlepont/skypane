# -*- coding: utf-8 -*-
"""companion/i18n_fr/display.py — French strings for the Display and
Device pages (D-01/D-04/D-05/D-09, 20-07-PLAN.md Task 3).

One sibling module of the companion/i18n_fr package (see that
package's __init__.py for the auto-merge/duplicate-key contract this
module participates in). Every key here is the exact English source
string a call site in companion/pages/config_page.py passes to
companion.i18n.t() — including any "%s"/"%d"/"{n}" placeholder shape,
unchanged.

Three keys config_page.py also calls t() on are deliberately absent
here — "Theme", "Display" and "Device" are already defined in
companion/i18n_fr/nav.py (the nav labels) and "Screen" is already
defined in companion/i18n_fr/health.py; the package's own duplicate-key
guard would raise if this module redefined any of the three. Every
theme/runway *name* shown to people (device_config.theme_label()/
runway_label(), e.g. "White", "Runway 3 (07/25)") is a registry value
this plan deliberately leaves untranslated — a cross-page, registry-
wide concern out of this plan's own scope (see 20-07-SUMMARY.md).

Copy follows D-09: sentence case, the typographic apostrophe (U+2019,
never a straight quote), and a non-breaking space (U+00A0) before
":" ";" "?" "!".
"""

CATALOG = {
    # --- Display/Device page shells (config_page.py's render()) --------
    "Everything about what the frame shows and when.":
        "Tout ce que le cadre affiche, et quand.",
    "Hardware, data and diagnostics for the frame. Nothing here needs "
    "changing day to day.":
        "Matériel, données et diagnostics du cadre. Rien ici n’a "
        "besoin d’être changé au quotidien.",
    "Settings": "Réglages",
    "Screen: %s": "Écran : %s",
    "Screen type": "Type d’écran",

    # --- Display's three supersections (D-12, 20-UI-SPEC.md §B) --------
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
        "S’applique la prochaine fois que le cadre se réveille.",

    # --- Theme card (config_page.py's theme_fieldset()) ----------------
    "Panel colors for departing/arriving flights. Applies on the "
    "device's next scheduled poll, not immediately.":
        "Couleurs du panneau pour les vols au départ et à l’arrivée. "
        "S’applique lors de la prochaine vérification programmée de "
        "l’appareil, pas immédiatement.",
    "Use a different theme for arrivals":
        "Utiliser un thème différent pour les arrivées",
    "Arrivals theme": "Thème des arrivées",
    "current": "actuel",
    "Sample panel rendered in the %s theme":
        "Exemple de panneau avec le thème %s",
    "Selected": "Sélectionné",

    # --- The live theme preview above the chip grid (D-22..D-24,
    #     20-11-PLAN.md Task 2, 20-UI-SPEC.md copy table E) -------------
    "Live preview of the %s theme": "Aperçu en direct du thème %s",
    "Preview with your last flight: %s":
        "Aperçu avec votre dernier vol : %s",
    "Preview with a sample flight": "Aperçu avec un vol d’exemple",

    # --- Runway card (config_page.py's runway_fieldset()) --------------
    "Runway": "Piste",
    "Which Orly runway the device watches. Applies on the next "
    "scheduled poll, not immediately.":
        "Quelle piste d’Orly l’appareil surveille. S’applique "
        "lors de la prochaine vérification programmée, pas immédiatement.",
    "Airport diagram for %s": "Schéma de l’aéroport pour %s",

    # --- Calendar card (config_page.py's calendar_group()/
    #     calendar_disconnect_section()/calendar_disconnect_confirm_
    #     page()) --------------------------------------------------------
    "Calendar": "Calendrier",
    "When the flight the frame is currently showing is one your "
    "connected calendar lists, it uses this theme instead of the usual "
    "one. It can only colour a flight that happens to be on screen — "
    "it does not track or announce anything on its own. Applies on "
    "the frame's next scheduled poll, not immediately.":
        "Quand le vol actuellement affiché par le cadre figure dans "
        "votre calendrier connecté, il utilise ce thème à la place du "
        "thème habituel. Il ne peut colorer qu’un vol déjà affiché à "
        "l’écran — il ne suit ni n’annonce rien de lui-même. "
        "S’applique lors de la prochaine vérification programmée du "
        "cadre, pas immédiatement.",
    "Connected — waiting for the first sync.":
        "Connecté — en attente de la première synchronisation.",
    "Connected — last synced ": "Connecté — dernière synchronisation ",
    "Not connected. Paste your calendar's feed URL below to connect one.":
        "Non connecté. Collez l’URL du flux de votre calendrier "
        "ci-dessous pour en connecter un.",
    "Connected, but ignored — its saved link on the server became "
    "readable beyond this frame. Paste the feed URL again below to "
    "store it safely.":
        "Connecté, mais ignoré — son lien enregistré sur le serveur "
        "est devenu lisible au-delà de ce cadre. Collez à nouveau "
        "l’URL du flux ci-dessous pour le stocker en sécurité.",
    "Used only when a flight from the calendar happens to be the one "
    "on screen.":
        "Utilisé uniquement quand un vol du calendrier est celui "
        "affiché à l’écran.",
    "Calendar feed URL": "URL du flux du calendrier",
    "Your calendar's private iCal link. Stored on the server and "
    "never shown back here — pasting a new one replaces the old.":
        "Le lien iCal privé de votre calendrier. Stocké sur le serveur "
        "et jamais réaffiché ici — en coller un nouveau remplace "
        "l’ancien.",
    "Disconnect this calendar and delete the flights it supplied":
        "Déconnecter ce calendrier et supprimer les vols qu’il a fournis",
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

    # --- Flight colours / per-flight rules (config_page.py's
    #     _rule_add_form_html()/_rule_row_html()/_rules_section_html())
    "Per-flight colour rules": "Couleurs par vol",
    "Override the theme for one exact flight, aircraft, or carrier. "
    "Most specific match wins — a callsign rule beats a hex rule, "
    "which beats a prefix rule — and adding a key that's already in "
    "use replaces the existing rule for it. Applies on the frame's "
    "next scheduled poll, not immediately.":
        "Remplacez le thème pour un vol, un avion ou une compagnie "
        "précis. La règle la plus précise l’emporte — un indicatif "
        "l’emporte sur un code hexadécimal, qui l’emporte sur un "
        "préfixe — et l’ajout d’une clé déjà utilisée remplace la "
        "règle existante pour cette clé. S’applique lors de la "
        "prochaine vérification programmée du cadre, pas immédiatement.",
    "Match by": "Correspondance par",
    "Value": "Valeur",
    "Add rule": "Ajouter la règle",
    "Exact callsign (e.g. AFR1234), ICAO24 hex (e.g. 3944F2), or a "
    "3-letter prefix (e.g. AFR) — matching the kind selected above.":
        "Indicatif exact (ex. AFR1234), code hexadécimal ICAO24 (ex. "
        "3944F2), ou préfixe de 3 lettres (ex. AFR) — selon le type "
        "sélectionné ci-dessus.",
    "No rules yet": "Encore aucune règle",
    "Add one above to give a specific flight, aircraft, or carrier "
    "its own theme, regardless of direction.":
        "Ajoutez-en une ci-dessus pour donner son propre thème à un "
        "vol, un avion ou une compagnie précis, quelle que soit la "
        "direction.",
    "Callsign": "Indicatif",
    "ICAO24 hex": "Code hexadécimal ICAO24",
    "Callsign prefix": "Préfixe d’indicatif",
    "Kind": "Type",
    "Key": "Clé",
    "Added": "Ajouté",
    "Delete": "Supprimer",

    # --- Screen on/off + Quiet hours cards, and their shared instant-
    #     switch words (config_page.py's display_group()/
    #     quiet_hours_group(), D-19) ----------------------------------
    "Screen on / off": "Écran allumé / éteint",
    "Turns the physical panel off remotely, without touching the "
    "hardware. Takes effect within about 5 minutes, both switching "
    "off and back on.":
        "Éteint le panneau physique à distance, sans toucher au "
        "matériel. Prend effet en environ 5 minutes, à l’extinction "
        "comme au rallumage.",
    "Enable display": "Activer l’écran",
    "Quiet hours": "Heures calmes",
    "Pauses the frame's wake, poll and display cycle overnight. "
    "Applies on the next scheduled poll, which may now be hours away.":
        "Met en pause le réveil, la vérification et l’affichage du "
        "cadre pendant la nuit. S’applique lors de la prochaine "
        "vérification programmée, qui peut désormais être dans "
        "plusieurs heures.",
    "Enable quiet hours": "Activer les heures calmes",
    "Start": "Début",
    "End": "Fin",
    "Night (%s–%s)": "Nuit (%s–%s)",
    "Work day (%s–%s)": "Journée de travail (%s–%s)",
    "Always on (off)": "Toujours allumé (désactivé)",
    "On": "Allumé",
    "Off": "Éteint",
    "Switch on": "Allumer",
    "Switch off": "Éteindre",
    "Turn on": "Activer",
    "Turn off": "Désactiver",
    "On — %s to %s": "Allumé — %s à %s",

    # --- Device-only groups (config_page.py's led_group()/
    #     wake_interval_group()/poll_trigger_section()) -----------------
    "Diagnostic LED": "LED de diagnostic",
    "Lit only during the device's brief wake window, not visible "
    "from the wall side. Applies on the next scheduled poll.":
        "Allumée seulement pendant la brève fenêtre de réveil de "
        "l’appareil, non visible du côté mur. S’applique lors de "
        "la prochaine vérification programmée.",
    "Enable diagnostic LED": "Activer la LED de diagnostic",
    "Wake interval": "Intervalle de réveil",
    "How often the frame wakes to poll for updates. Shorter means "
    "fresher info and more battery drain; longer means more battery "
    "life and staler info at a glance. Applies on the next scheduled "
    "poll.":
        "À quelle fréquence le cadre se réveille pour vérifier les "
        "mises à jour. Plus court signifie des informations plus "
        "fraîches et plus de décharge de la batterie ; plus long "
        "signifie plus d’autonomie et des informations plus datées "
        "en un coup d’œil. S’applique lors de la prochaine "
        "vérification programmée.",
    "Wake interval (seconds)": "Intervalle de réveil (secondes)",
    "Uses server default": "Utilise la valeur par défaut du serveur",
    "Manual refresh": "Actualisation manuelle",
    "Manually trigger an immediate poll cycle instead of waiting for "
    "the next scheduled one.":
        "Déclenchez manuellement une vérification immédiate au lieu "
        "d’attendre la prochaine programmée.",
    "Trigger poll now": "Déclencher une vérification maintenant",
    "Polling…": "Vérification en cours…",
    "Poll triggered recently — try again in {n}s.":
        "Vérification déclenchée récemment — réessayez dans {n} s.",

    # --- Dirty bar / Save (config_page.py's render()) -------------------
    "Unsaved changes": "Modifications non enregistrées",
    "Save settings": "Enregistrer les réglages",
    "Next wake": "Prochain réveil",
    " (next wake ≈ %s)": " (prochain réveil ≈ %s)",

    # --- The dirty bar's own five connector words (D-06, 20-11-PLAN.md
    #     Task 3) — companion/static/dirty-state.js reads these as
    #     data-* attributes rather than hardcoding them in English.
    " changed": " modifié",
    " and ": " et ",
    ", and ": " et ",
    "1 unsaved change": "1 modification non enregistrée",
    " unsaved changes": " modifications non enregistrées",

    # --- Field-level validation errors (config_page.py's
    #     _field_error_html(), rendered wherever `errors` carries one) --
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
}
