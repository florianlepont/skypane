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
runway_label(), e.g. "White", "Runway 3 (07/25)") and the screen label
(screens.py's "Plane frame") ARE translated (Polish fix 5, D-05) — at
the config_page.py display sites that call i18n.t() on the registry's
own returned text, never by changing server/device_config.py's or
companion/screens.py's own English values or their ids. Their French
entries live in the dedicated companion/i18n_fr/registry.py module
(one cross-page catalogue for every registry label this app renders,
rather than duplicating them per consuming page module) — not here.

Copy follows D-09: sentence case, the typographic apostrophe (U+2019,
never a straight quote), and a non-breaking space (U+00A0) before
":" ";" "?" "!".

20-12-PLAN.md Task 1 (D-08's completeness/dead-translation harness):
removed 14 entries the Calendar-card and Flight-colours rebuilds
(20-09-PLAN.md) superseded and left behind — the old one-piece
Calendar status sentences ("Connected — waiting for the first
sync."/"Connected — last synced "/"Not connected. Paste your
calendar's feed URL below to connect one."), the old calendar-theme
disclaimer paragraph and its "Used only when..." companion sentence,
the old "Per-flight colour rules" heading and its "Override the
theme..." disclosure body, the old one-line value-field hint ("Exact
callsign (e.g. AFR1234)..."), the old empty state ("No rules yet"/"Add
one above to give a specific flight..."), and the old rules table's
"Kind"/"Key"/"Added" column headers (D-15c's `.rule-row` list has no
column headers at all). Also added here: the Notifications URL
field's own shorter "That link is too long." error and the workday
quiet-hours preset's own pre-baked label ("Open menu" and " —
attention needed" are the same harness's finds, but live in
companion/i18n_fr/nav.py instead — companion/layout.py's own render
sites for both had never been wrapped in i18n.t() until this plan).
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
    "Match by": "Correspondance par",
    "Value": "Valeur",
    "Add rule": "Ajouter la règle",
    "Callsign": "Indicatif",
    "ICAO24 hex": "Code hexadécimal ICAO24",
    "Callsign prefix": "Préfixe d’indicatif",
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
    # 20-12-PLAN.md Task 1: the workday preset's own pre-baked label
    # (QUIET_HOURS_PRESET_WORKDAY_LABEL, computed once at import time
    # from the template above with the literal "08:00"/"18:00" default
    # times) is read through i18n.t() as its own value, independent of
    # the template — the completeness harness treats a module-level
    # constant computed at import time the same as a literal one.
    "Work day (08:00–18:00)": "Journée de travail (08:00–18:00)",
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
    # 20-12-PLAN.md Task 1: the Notifications topic-URL field's own
    # shorter error (ERROR_NOTIFICATIONS_URL_TOO_LONG) — distinct from
    # the calendar URL's longer message above, never the same key.
    "That link is too long.": "Ce lien est trop long.",
}
