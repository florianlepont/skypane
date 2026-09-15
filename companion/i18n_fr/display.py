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
        "S’applique au prochain réveil du cadre.",

    # --- Frame colours card (config_page.py's _frame_colours_card_html(),
    #     D-06..D-12, 21-05-PLAN.md Task 1) — replaces the retired Theme
    #     card (theme_fieldset(), its own THEME_SECTION_CAPTION/"Use a
    #     different theme for arrivals"/"Arrivals theme"/"current"
    #     strings all deleted in this same commit as their English
    #     source constants, per test_i18n.py's dead-translation check) --
    "Frame colours": "Couleurs du cadre",
    "Departures": "Départs",
    "Arrivals": "Arrivées",
    "Calendar flights": "Vols du calendrier",
    "Per-flight rules": "Règles par vol",
    "Same as departures": "Comme les départs",
    "1 rule": "1 règle",
    "%d rules": "%d règles",
    "No rules yet": "Aucune règle pour l’instant",
    "Choose the colour theme for departures, arrivals, calendar "
    "flights and your own rules.":
        "Choisissez le thème de couleurs pour les départs, les "
        "arrivées, les vols du calendrier et vos propres règles.",
    "Selected": "Sélectionné",
    # 22-10-PLAN.md Task 1 (X6): the one-line legend under each chip
    # grid naming the two swatch dots. See config_page.py's
    # THEME_CHIP_SWATCH_LEGEND for why this names departures/arrivals
    # rather than 22-UI-SPEC.md's proposed "Background · Ink".
    #
    # 27-07-PLAN.md Task 3 (CFG-70): joined into one phrase, no
    # separator — see the English constant's own comment for why a
    # middle-dot legend over two identical swatches was itself X6's
    # defect wearing different words.
    "Departures & arrivals": "Départs et arrivées",
    # 22-10-PLAN.md Task 1 (T10/B16): the "Current" badge on the saved
    # chip/runway card, which used to be a hard-coded English
    # `content: "Current"` in style.css that no catalogue could reach.
    "Current": "Actuel",

    # --- 25-06-PLAN.md Task 2/3 (CFG-50): D5's theme carousel ---------
    #     The disclosure's body says the one thing that matters about
    #     it: nothing is hidden behind it. See
    #     config_page._theme_carousel_html() for why the disclosure
    #     governs the layout of the strip that follows it instead of
    #     holding a second copy of the same eighteen radios.
    "See all themes": "Voir tous les thèmes",
    "Opening this lays all %d themes out at once. They are all in the "
    "strip either way — it scrolls, and the arrow keys move through it.":
        "L’ouvrir affiche les %d thèmes d’un seul coup. Ils sont de "
        "toute façon tous dans la bande : elle défile, et les flèches "
        "du clavier la parcourent.",
    "Previous theme": "Thème précédent",
    "Next theme": "Thème suivant",

    # --- The live theme preview above the chip grid (D-22..D-24,
    #     20-11-PLAN.md Task 2, 20-UI-SPEC.md copy table E) -------------
    "Live preview of the %s theme": "Aperçu en direct du thème %s",
    "Preview with your last flight: %s":
        "Aperçu avec votre dernier vol : %s",
    "Preview with a sample flight": "Aperçu avec un vol d’exemple",

    # --- Runway card (config_page.py's runway_fieldset()) --------------
    "Runway": "Piste",
    # 25-03-PLAN.md Task 1 (CFG-47): the schematic clause, because the
    # group now draws a map. "indicatif" / "pas à l'échelle" carry the
    # same refusal-to-claim-a-survey the English does — a French visitor
    # given an unqualified diagram would be given a claim the drawing
    # cannot back up.
    "Which Orly runway the device watches. The diagram is schematic: "
    "relative bearings only, north up, not to scale. Applies on the "
    "next scheduled poll, not immediately.":
        "Quelle piste d’Orly l’appareil surveille. Le schéma est "
        "indicatif : orientations relatives seulement, nord en haut, "
        "pas à l’échelle. S’applique lors de la prochaine vérification "
        "programmée, pas immédiatement.",
    "Airport diagram for %s": "Schéma de l’aéroport pour %s",

    # --- Calendar card (config_page.py's merged calendar_group()/
    #     calendar_disconnect_confirm_page()) ---------------------------
    # 21-07-PLAN.md Task 1 (D-14, Pitfall 5): removed "Disconnect this
    # calendar and delete the flights it supplied" (no question mark) —
    # the merged card's own small Disconnect button now reads the
    # shorter "Disconnect" (companion/i18n_fr/calendar_group.py). The
    # otherwise-identical confirmation-page strings below (with a
    # question mark, or naming "calendar"/"calendar?" alone) are
    # untouched — they still belong to calendar_disconnect_confirm_
    # page(), unaffected by this merge.
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

    # --- Quiet hours card (config_page.py's quiet_hours_group(), D-19) -
    # 22-05-PLAN.md Task 1 (X1/D-04/D-12.1): "Screen on / off",
    # display_group()'s own caption, "Enable display" and "Enable quiet
    # hours" are all deleted here, in the same commit as their English
    # source constants/checkbox labels — the Frame strip is now the ONLY
    # on/off control for either setting, and none of the four is called
    # through i18n.t() anywhere any more.
    "Quiet hours": "Heures calmes",
    # 22-05-PLAN.md Task 1 (X1/D-04/D-12.1): the enable-by-schedule
    # sentence that replaces the retired "Applies on the next scheduled
    # poll, which may now be hours away" wording — Task 2 appends one
    # computed delay sentence (below) as this caption's own second
    # sentence, never a second, competing caption element. 27-06-
    # PLAN.md Task 3 (CFG-67): the mechanism clause naming the Frame
    # strip's switch is cut; the delay sentence it precedes is
    # untouched.
    "Pauses the frame's wake, poll and display cycle during the "
    "schedule below.":
        "Met en pause le réveil, la vérification et l’affichage du "
        "cadre pendant la plage horaire ci-dessous.",
    # 22-05-PLAN.md Task 2 (D-04): the two DELAY_DUE/DELAY_HELD delay-
    # sentence branches this caption's own computed second sentence uses
    # are DELIBERATELY NOT redefined here — they already have a live
    # entry in companion/i18n_fr/frame_state.py (22-02-PLAN.md Task 2),
    # and the package's own auto-merge guard raises on a duplicate key.
    # config_page.py's own scanner-visibility copies
    # (_QUIET_HOURS_DELAY_DUE_TEXT/_QUIET_HOURS_DELAY_HELD_TEXT) are what
    # make the D-05 AST scan trace these two CATALOG keys as genuinely
    # produced now — see that module's own comment for the pattern.
    "Start": "Début",
    "End": "Fin",
    # 25-04-PLAN.md Task 3 (CFG-48): the two quiet-hours dial handles'
    # accessible names. Each handle is a real <button> carrying
    # role="slider", and its aria-valuetext is the time ITSELF and
    # nothing else (the server writes the bare "{}" token, so the script
    # substitutes "23:00" and never a sentence) — which is why only the
    # two names below need a French sibling and the announced value does
    # not. Deliberately not composed from "Quiet hours" + "Start": a
    # French accessible name is a phrase, not two catalogue keys joined
    # with a space, and "Heures calmes Début" is not one.
    "Quiet hours start": "Début des heures calmes",
    "Quiet hours end": "Fin des heures calmes",
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
    # 23-07-PLAN.md Task 2 (D2/CFG-36): "Enable diagnostic LED" is
    # DELETED, not commented out. It was the label of the LED checkbox,
    # and that checkbox is retired — the Diagnostic LED is now a
    # role="switch" named by the group's own heading ("Diagnostic LED",
    # already a catalogue key) and stated by aria-checked, so there is no
    # action-shaped label left to translate. Check 2 of the i18n harness
    # is what found it: a key no module produces is a key nobody reads.
    "Wake interval": "Intervalle de réveil",
    # 27-06-PLAN.md Task 3 (CFG-67): shortened — the mechanism sentence
    # ("How often the frame wakes...") and the apply-timing sentence
    # ("Applies on the next scheduled poll.") are both cut; the
    # derived "(prochain réveil ≈ ...)" suffix already states the
    # apply timing with a real timestamp.
    "Shorter means fresher info and more battery drain; longer means "
    "more battery life and staler info at a glance.":
        "Plus court signifie des informations plus fraîches et plus de "
        "décharge de la batterie ; plus long signifie plus "
        "d’autonomie et des informations plus datées en un coup "
        "d’œil.",
    "Wake interval (seconds)": "Intervalle de réveil (secondes)",
    # 25-05-PLAN.md Task 2 (CFG-52): the range input's OWN accessible
    #     name. It needs one distinct from the number input's label
    #     above — two controls sharing one accessible name is how a
    #     screen-reader visitor loses track of which they are on.
    "Wake interval slider": "Curseur d’intervalle de réveil",
    # 25-05-PLAN.md Task 1 (CFG-49): the two gauges. "#" is the
    #     quantity's place in every one of these (layout.
    #     VALUE_CONTROL_TEXT_TOKEN) — never "%s"/"%d"/"{}", which
    #     Check 3 of this harness scans every French render for.
    #     The unit is "min" and the quantity is WHOLE MINUTES in
    #     both languages, which is what keeps these sentences free
    #     of a plural form and free of the s/m/h/d ladder — the
    #     configured band is 1..60 minutes, so the unit never
    #     changes mid-sweep. U+00A0 between the number and its
    #     unit, per D-09, exactly as layout.duration_text() already
    #     does for its own French branch.
    # 27-06-PLAN.md Task 3 (CFG-67): "after it passes" is cut in favour
    # of the shorter, equally exact "later" — "at most" is unchanged.
    "A plane reaches the frame at most # min later.":
        "Un avion apparaît sur le cadre au plus # min plus tard.",
    # The two absolute-figure wordings, SINGULAR and PLURAL both —
    #     a days count of 1 is reachable (a nearly empty battery)
    #     and "1 jours" is the missing-plural defect this harness
    #     has caught before. 27-06-PLAN.md Task 3 (CFG-67): "at this
    #     interval"/"à cet intervalle" is cut — the honesty
    #     attribution ("from this frame’s own recent readings") is
    #     UNCHANGED.
    "≈ # day of battery left, from this frame's own recent readings.":
        "≈ # jour d’autonomie restante, d’après les relevés "
        "récents de ce cadre.",
    "≈ # days of battery left, from this frame's own recent readings.":
        "≈ # jours d’autonomie restante, d’après les relevés "
        "récents de ce cadre.",
    # 27-06-PLAN.md Task 3 (CFG-67): the trailing reason clause is cut;
    # the refusal itself — D18’s honesty contract — is UNCHANGED.
    "Not enough battery history yet to say how long a charge lasts.":
        "Pas encore assez d’historique de batterie pour dire combien "
        "de temps dure une charge.",
    # 27-06-PLAN.md Task 3 (CFG-67): ", whatever this is set to" is cut —
    # "instead"/"à la place" already carries the override.
    "While the screen is off, the frame wakes every %s instead.":
        "Quand l’écran est éteint, le cadre se réveille toutes les %s "
        "à la place.",
    # The relative clause names both cadences rather than a ratio, so it
    #     carries no decimal at all — which is what keeps it out of the
    #     French decimal-comma question entirely. "%d" is the SAVED
    #     cadence, filled server-side; "#" is the proposed one, filled
    #     by companion/static/value-controls.js as the slider moves.
    "This setting wakes the frame every # min instead of every %d min.":
        "Ce réglage réveille le cadre toutes les # min au lieu de toutes "
        "les %d min.",
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

    # --- Save (config_page.py's render()) --------------------------------
    "Save settings": "Enregistrer les réglages",
    "Next wake": "Prochain réveil",
    " (next wake ≈ %s)": " (prochain réveil ≈ %s)",

    # --- 27-04-PLAN.md (D-04/CFG-63): the auto-save status region's two
    #     words, read as data-save-status-saving/data-save-status-saved
    #     by companion/static/dirty-state.js — replacing the retired
    #     dirty bar's own six connector/progress words (SUPERSEDED: " changed",
    #     " and ", ", and ", "1 unsaved change", " unsaved changes" and
    #     "Unsaved changes" are all deleted as dead catalogue entries
    #     along with the bar that read them).
    #
    #     "Enregistrement…" is the progressive form of the same verb
    #     "Enregistrer les réglages" above already uses, so the region
    #     reads as the same action continuing rather than a new one, and
    #     it carries the same single U+2026 ellipsis as "Vérification en
    #     cours…" above. "Enregistré" matches the existing "Saved — %s":
    #     "Enregistré — %s" entry (companion/i18n_fr/common.py) rather
    #     than inventing a second past-participle wording for the same
    #     event.
    "Saving…": "Enregistrement…",
    "Saved": "Enregistré",

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
