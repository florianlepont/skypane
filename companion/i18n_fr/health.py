# -*- coding: utf-8 -*-
"""companion/i18n_fr/health.py — French strings for companion/layout.py's
language-aware date helpers (D-07) and for the Health page
(companion/pages/health_page.py, D-05), 20-03-PLAN.md.

One sibling module of the companion/i18n_fr package (see that
package's __init__.py for the auto-merge/duplicate-key contract this
module participates in). Every key here is the exact English source
string a call site in companion/layout.py or companion/pages/
health_page.py passes to companion.i18n.t()/t_lang() — including any
"%d"/"%s"/"%%" placeholder, unchanged. A handful of keys (e.g.
"Resolve", "Count") are shared by more than one call site on the
Health page — one catalogue entry, several readers, never a duplicate.

Copy follows D-09: sentence case, the typographic apostrophe (U+2019,
never a straight quote), and a non-breaking space (U+00A0) before
":" ";" "?" "!". The relative-age connector and quantity strings below
additionally carry a real U+00A0 between a number and its unit
(D-07's own example: "il y a 1 j").
"""

CATALOG = {
    # --- companion/layout.py's relative_age_text()/local_clock_text()
    #     (D-07) — the copy lives here rather than as a layout.py
    #     literal so it stays with the rest of the French catalogue. --
    "just now": "à l’instant",
    "%s ago": "il y a %s",

    # 23-03-PLAN.md Task 1 (D14/CFG-34): the same ladder read FORWARDS,
    # for layout.relative_future_text(). The connector and the
    # under-a-minute collapse sit here, beside the past form's own, and
    # NOT as a literal in the script that will tick these elements
    # (plan 23-05) — which is what lets that script carry no French at
    # all. "dans un instant" mirrors "à l’instant"'s own collapse of the
    # whole sub-minute bucket into one phrase rather than a literal
    # second count; the quantity strings carry the same real U+00A0
    # between the number and the unit (D-09, e.g. "dans 4 min").
    "in a moment": "dans un instant",
    "in %s": "dans %s",

    # 23-05-PLAN.md Task 1 (D14/CFG-34): the SAME ladder again, this
    # time as nine complete wordings rather than as a connector plus a
    # unit. companion/static/relative-time.js rewrites these elements
    # once a second, so the wordings have to exist client-side; they are
    # rendered onto <body> by layout.page_shell() and read back with
    # getAttribute(), which is what lets that script carry no French at
    # all — the four English forms above it are its no-attribute
    # fallbacks and nothing more.
    #
    # "#" is where the number goes. It is NOT "%s": these strings reach
    # the browser as attribute values on a rendered page, and this
    # harness's own Check 3 scans every French render for a stray
    # "%s"/"%d"/"{}". A wording with no "#" in it takes no number at all
    # — which is how French collapsing its whole sub-minute bucket into
    # a phrase ("à l’instant", "dans un instant", repeated here from the
    # entries above) stays DATA rather than becoming a branch in the
    # script.
    #
    # These cannot drift from layout.relative_age_text()/
    # relative_future_text(): companion/test_companion_app.py fills each
    # one with the quantity _age_bucket() picks and asserts equality
    # against those functions, in both languages, for every bucket.
    "#s ago": "à l’instant",
    "#m ago": "il y a # min",
    "#h ago": "il y a # h",
    "#d ago": "il y a # j",
    "in #s": "dans un instant",
    "in #m": "dans # min",
    "in #h": "dans # h",
    "in #d": "dans # j",

    # What a countdown reads once its instant has passed — neutral, and
    # never a warning word. See layout.RELATIVE_WAITING_TEXT's own
    # comment.
    "waiting…": "en attente…",

    # --- Page header / purpose / freshness (health_page.py) -----------
    "Screen status and server data quality, in one place.":
        "L’état de l’écran et la qualité des données du serveur, au même endroit.",
    "Updating…": "Mise à jour…",
    "Updated ": "Mis à jour ",

    # --- D-14 anomaly banner --------------------------------------------
    "Something needs attention — check the tiles below.":
        "Quelque chose nécessite votre attention — consultez les tuiles ci-dessous.",
    "warning": "avertissement",
    "error": "erreur",
    "issue": "problème",
    "Device check-in is stale.": "Le cadre ne répond plus.",
    "Flight data is stale.": "Données de vol anciennes.",
    "Battery dropped abnormally.":
        "Baisse anormale de batterie.",
    "Data sources disagreed recently.":
        "Sources en désaccord récemment.",
    "Some airlines are unidentified.": "Compagnies non identifiées.",
    "All data sources failed.": "Toutes les sources ont échoué.",

    # --- CFG-05 source-fault landing block ------------------------------
    "ADS-B source outage": "Panne de source ADS-B",
    "The frame's alert badge is showing because every configured ADS-B "
    "source (%s) failed to respond on the most recent pipeline run — "
    "this is a data-source outage, not a device problem.":
        "Le badge d’alerte du cadre s’affiche parce qu’aucune source ADS-B "
        "configurée (%s) n’a répondu lors du dernier passage du pipeline — "
        "il s’agit d’une panne de source de données, pas d’un problème matériel.",

    # --- Device / Pipeline / Corroboration tiles ------------------------
    "Device last checked in": "Dernière connexion de l’appareil",
    "Flight data last updated": "Dernière mise à jour des données de vol",
    "ADS-B pipeline last ran": "Dernière exécution du pipeline ADS-B",
    "Do the two data sources agree?": "Les deux sources de données concordent-elles ?",
    "Corroboration": "Corroboration",
    "Last aircraft detected": "Dernier avion détecté",
    "Checking in normally": "Se connecte normalement",
    "Has not checked in for a while": "N’a pas répondu depuis un moment",
    "Has not checked in for a long time": "N’a pas répondu depuis longtemps",
    # --- 22-04-PLAN.md Task 3 (D-03/CFG-26): the frame's own held state,
    #     the neutral "off" device_state — never a warning ---------------
    "Asleep for quiet hours": "En veille pendant les heures calmes",
    "Running on schedule": "Fonctionne comme prévu",
    "A little behind": "Un peu en retard",
    "Has not run for a long time": "N’a pas fonctionné depuis longtemps",
    # --- 22-03-PLAN.md Task 1 (B2): the pipeline's real never-ran state ---
    "No detection yet": "Aucune détection pour l’instant.",
    "The frame has not reported a flight since it started.":
        "Le cadre n’a signalé aucun vol depuis son démarrage.",
    "Sources agree": "Les sources concordent",
    "Sources disagreed recently": "Les sources se sont contredites récemment",
    "Nothing to compare yet.": "Rien à comparer pour l’instant.",
    "This appears once the frame has recorded at least one flight.":
        "Ceci apparaît une fois que le cadre a enregistré au moins un vol.",
    "More details": "Plus de détails",
    "Both agree": "Les deux concordent",
    "Both flight-data sources on the frame picked the same aircraft.":
        "Les deux sources de données de vol du cadre ont identifié le même avion.",
    "Only one saw it": "Une seule l’a vu",
    "Only one of the two sources returned an aircraft this cycle — "
    "that is not the same as a disagreement, there was simply nothing "
    "from the other source to compare it against.":
        "Une seule des deux sources a renvoyé un avion ce cycle — ce n’est "
        "pas un désaccord, il n’y avait simplement rien à comparer du "
        "côté de l’autre source.",
    "They disagree": "Elles se contredisent",
    "The two sources named different aircraft, so nothing was shown "
    "that cycle — the display kept the previous image instead.":
        "Les deux sources ont identifié des avions différents, donc rien "
        "n’a été affiché ce cycle — l’écran a conservé l’image précédente.",

    # --- Resolution-rate tile --------------------------------------------
    "Flights we could name": "Vols que nous avons pu identifier",
    "Route resolution rate": "Taux de résolution des trajets",
    "%.1f%% resolved": "%.1f %% résolus",
    "over the last %d days, %d events": "au cours des %d derniers jours, %d événements",
    # 22-12-PLAN.md Task 1 (D-06/B16, CFG-29): the singular sibling of
    # the line above — health_page._RESOLUTION_DETAIL_SINGULAR_TEMPLATE.
    # A window holding exactly one detection read "1 events" in English
    # and "1 événements" here; both counts stay in the same order, and
    # only the noun loses its "s" (the day count is a fixed 30, so it
    # never needs a singular form of its own).
    "over the last %d days, %d event": "au cours des %d derniers jours, %d événement",

    # --- Battery trend section -------------------------------------------
    # 29-06-PLAN.md Task 1 (CFG-84): the "Battery trend"/"Tendance de la
    # batterie" entry that used to live here is DELETED outright, not
    # left as a dead translation — BATTERY_SECTION_HEADING (the module
    # constant that produced it) no longer exists, superseded by
    # BATTERY_SECTION_HEADING_TEMPLATE below. test_i18n.py's Check 2
    # (no dead translations) would fail on a stale entry no source
    # produces any more.
    "Battery · %d months": "Batterie · %d mois",
    "Last 3 months, daily average": "3 derniers mois, moyenne quotidienne",
    "%s — daily average (%d reading)": "%s — moyenne quotidienne (%d relevé)",
    "%s — daily average (%d readings)": "%s — moyenne quotidienne (%d relevés)",
    "%s — daily average": "%s — moyenne quotidienne",
    # 24-05-PLAN.md Task 2 (CFG-41): the drawn low-battery threshold's
    # legend. The connector stays the "—" every other label in this
    # section uses, and D-09's real U+00A0 sits before the "%%" exactly
    # as "%.1f %% résolus" above already does.
    "Low battery \u2014 %d mV (\u2248 %d%%)":
        "Batterie faible \u2014 %d mV (\u2248 %d\u00a0%%)",
    "Latest %d readings": "%d derniers relevés",
    "No battery readings yet.": "Aucun relevé de batterie pour l’instant.",
    "No battery telemetry recorded yet — check back after the "
    "device's next poll.":
        "Aucune télémétrie de batterie enregistrée pour l’instant — "
        "revenez après la prochaine vérification de l’appareil.",
    "Timestamp": "Horodatage",
    "Battery (mV)": "Batterie (mV)",
    "View %d reading%s": "Voir %d relevé%s",

    # --- Screen / Server & data section intros ---------------------------
    "Screen": "Écran",
    "— the physical frame: is it checking in, and how's the battery.":
        "— le cadre physique : se connecte-t-il, et comment va la batterie.",
    "Server & data": "Serveur et données",
    # 29-06-PLAN.md Task 3 (CFG-79): shortened from 15 words to 12 —
    # surfaced only by Task 3’s own bilingual, render-level site-wide
    # check. The English source is already exactly at the 12-word
    # floor; the French translation’s real non-breaking space before
    # its colon (D-09) costs one extra whitespace-split token the
    # English colon does not, so "sont-elles fraîches et" is trimmed
    # to stay under the same floor without losing "route resolution"
    # itself.
    "— the ADS-B pipeline and route resolution: is the data fresh and "
    "trustworthy.":
        "— le pipeline ADS-B et la résolution des trajets : "
        "données fiables ?",

    # --- Unresolved-prefix registry / filter bar --------------------------
    "Airlines we could not name": "Compagnies non identifiées",
    "No coverage gaps.": "Aucune lacune de couverture.",
    "Every airline we've seen recently has been named — nothing left "
    "to look up.":
        "Toutes les compagnies vues récemment ont été identifiées — il "
        "n’y a plus rien à rechercher.",
    # 29-06-PLAN.md Task 2 (CFG-79): the note is shortened to one
    # sentence and its instruction clause moves, unchanged in wording,
    # into _READ_ONLY_NOTE_DETAIL's own entry below.
    "This list is read-only here.": "Cette liste est en lecture seule ici.",
    "Each row's Resolve link opens the Airlines page to name that "
    "airline (and add artwork, if it needs one).":
        "Le lien Résoudre de chaque ligne ouvre la page Compagnies pour "
        "nommer cette compagnie (et ajouter une image, si besoin).",
    "Filter by prefix": "Filtrer par préfixe",
    "No matching prefixes": "Aucun préfixe correspondant",
    "Try a different search, or Clear filter to see all %d prefixes.":
        "Essayez une autre recherche, ou effacez le filtre pour voir "
        "les %d préfixes.",
    "%d of %d shown": "%d sur %d affichés",
    "Clear": "Effacer",
    "Prefix": "Préfixe",
    "Count": "Nombre",
    # 22-12-PLAN.md Task 2 (B12): shortened from "Vu pour la première
    # fois" / "Vu pour la dernière fois". The unresolved-prefix table
    # measured 1026px in French inside an 830px wrap at a 1280px
    # viewport; stacking the two timestamp cells (the Flights precedent)
    # brought it to 900px and left these two HEADERS as the widest thing
    # in their own columns, at 189px of ink each. At 102px each the
    # table measures 790px and fits, with the Resolve column reachable
    # without horizontal scrolling — both numbers taken from a headless
    # Chromium probe, not by eye.
    #
    # The English sources are deliberately unchanged: English measured
    # 830/830 after stacking alone, so there was nothing to fix there,
    # and rewording a column that fits would be a copy change with no
    # cause. These two keys are ALSO read by companion/pages/
    # airlines_page.py's RESOLVE_CONTEXT_LABELS (the resolve dialog's
    # <dt> labels) — one catalogue entry, several readers, which is this
    # module's own stated contract; the shorter, parallel pair reads
    # correctly in that definition list too.
    "First seen": "Première fois",
    "Last seen": "Dernière fois",
    "Example callsign": "Exemple d’indicatif",
    "Resolve": "Résoudre",
    "Resolve prefix %s": "Résoudre le préfixe %s",
    "Resolve this prefix": "Résoudre ce préfixe",

    # --- Resolution-statistics table --------------------------------------
    "How well we name flights": "Notre capacité à identifier les vols",
    # 22-03-PLAN.md Task 2 (B3): replaces the former "No resolution data
    # yet." / "No flight events recorded yet — resolution statistics
    # appear once the ADS-B pipeline has detected a flight." pair, which
    # never named the window. Kept as an unformatted "%d" template,
    # exactly like the English source constant.
    "No flights in the last %d days": "Aucun vol depuis %d jours",
    "The frame has not recorded a detection in this window. It will "
    "appear here after the next wake.":
        "Le cadre n’a enregistré aucune détection sur cette période. "
        "Elle apparaîtra ici après le prochain réveil.",
    "Other": "Autre",
    "A route source this page does not recognise, or none was recorded "
    "at all — still counted here so the total always matches every "
    "event in the window.":
        "Une source de trajet que cette page ne reconnaît pas, ou "
        "aucune n’a été enregistrée — comptabilisée ici afin que le "
        "total corresponde toujours à chaque événement de la période.",
    "Source": "Source",
    "Description": "Description",
    "Fresh lookup": "Recherche fraîche",
    "A live lookup in the route database resolved a full route this cycle.":
        "Une recherche en direct dans la base de trajets a résolu un "
        "trajet complet ce cycle.",
    "Cached hit": "Résultat en cache",
    "A previously-cached route was reused, sparing a network request.":
        "Un trajet précédemment mis en cache a été réutilisé, évitant "
        "une requête réseau.",
    "Airline only": "Compagnie seulement",
    "The route database had no route, but the callsign's ICAO prefix "
    "identified the airline from the static prefix table.":
        "La base de trajets n’avait aucun trajet, mais le préfixe ICAO "
        "de l’indicatif a identifié la compagnie grâce à la table de "
        "préfixes statique.",
    "Miss": "Échec",
    "Neither the route database nor the static prefix table resolved "
    "anything for this callsign, so it shows up in the Airlines we "
    "could not name list above.":
        "Ni la base de trajets ni la table de préfixes statique n’ont "
        "rien résolu pour cet indicatif, il apparaît donc dans la liste "
        "Compagnies non identifiées ci-dessus.",
    "Manual": "Manuel",
    "The operator resolved this callsign's prefix by hand, from the "
    "companion web interface.":
        "L’opérateur a résolu à la main le préfixe de cet indicatif, "
        "depuis l’interface web companion.",

    # --- 24-07-PLAN.md Task 2 (CFG-43): the check-in regularity grid ----
    #
    # The heading is 24-RESEARCH.md open decision 3's own wording:
    # "Régularité des relevés", never "ponctualité". The English source
    # already refuses the roadmap's own phrasing for this drawing because
    # the expected interval is not recoverable from the record, and a
    # French sibling that reintroduced the claim would put it back in
    # half the app's pages. A check scans the rendered page in BOTH
    # languages for exactly that word.
    #
    # "relevé" rather than "réveil" throughout, and that is the same
    # distinction the English keeps: a check-in is something the SERVER
    # recorded, a wake is something the FRAME did, and this grid can
    # only report the first.
    "Check-in regularity": "Régularité des relevés",
    # 29-06-PLAN.md Task 3 (CFG-79): shortened from 17 words to 12 —
    # surfaced only by Task 3's own bilingual, render-level site-wide
    # check (Task 2's own checks never measured French word count).
    "Each cell is one day of observed check-in regularity, oldest first.":
        "Chaque case représente un jour observé, du plus ancien au "
        "plus récent.",
    "Judged against the cadence configured now — a check-in every %s — not "
    "necessarily the cadence in force on an earlier day.":
        "Évaluée selon la cadence configurée actuellement — un relevé "
        "toutes les %s — pas nécessairement celle en vigueur les jours "
        "précédents.",
    "This frame's cadence cannot be determined, so the grid is judged against "
    "the fallback staleness floors rather than against a configured cadence.":
        "La cadence de ce cadre ne peut pas être déterminée : la grille est "
        "donc évaluée selon les seuils de repli, et non selon une cadence "
        "configurée.",
    "A day with no record is not proof the frame did not wake: a log rotation "
    "this server missed leaves exactly the same gap.":
        "Un jour sans relevé ne prouve pas que le cadre ne s’est pas "
        "réveillé : une rotation de journal manquée par ce serveur laisse "
        "exactement le même trou.",
    "No check-in intervals are recorded yet, so every day below is a day the "
    "record says nothing about.":
        "Aucun intervalle entre relevés n’est encore enregistré : chaque jour "
        "ci-dessous est donc un jour sur lequel l’enregistrement ne dit rien.",
    # The four state words, and the two tooltip shapes they appear in.
    # "Aucun relevé" is the absence of an observation, never a verdict —
    # which is why it is not "Manquant" with a qualifier.
    "On cadence": "Dans la cadence",
    "Late": "En retard",
    "Missing": "Manquant",
    "No record": "Aucun relevé",
    "%s — %s: longest observed gap %s": "%s — %s : plus long écart observé %s",
    "Observed check-in regularity, one cell per day over the last %d days: "
    "%d on cadence, %d late, %d missing, %d with no record.":
        "Régularité observée des relevés, une case par jour sur les %d "
        "derniers jours : %d dans la cadence, %d en retard, %d manquants, "
        "%d sans relevé.",

    # --- Off-box backup card (SEC-04, D-07/D-23, 37-02-PLAN.md) -----------
    "Off-box backup": "Sauvegarde hors serveur",
    "Off-box backup up to date": "Sauvegarde hors serveur à jour",
    "Off-box backup overdue": "Sauvegarde hors serveur en retard",
    "Last off-box backup": "Dernière sauvegarde hors serveur",
    # D-09: a real U+00A0 between the number and "jours", the same rule
    # this module's own docstring states for every quantity string.
    "No off-box backup in the last 3 days.":
        "Aucune sauvegarde hors serveur depuis 3 jours.",
    "No off-box backup has been pulled yet.":
        "Aucune sauvegarde hors serveur n’a encore été récupérée.",
    # layout.concise_timestamp_html()'s own `fallback` parameter — this
    # card's one non-quantity, non-page-specific string, added here
    # rather than as a second layout.py-level catalogue entry because
    # this is its only call site across the app (grep confirms no
    # other page passes a `fallback=i18n.t("never")` call).
    "never": "jamais",

    # --- Degrade-not-raise fallback --------------------------------------
    "Health history is temporarily unavailable — check the companion "
    "service logs.":
        "L’historique d’état est temporairement indisponible — "
        "consultez les journaux du service companion.",
}
