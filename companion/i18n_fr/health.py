# -*- coding: utf-8 -*-
"""French strings for companion/layout.py's language-aware date
helpers and for the Health page (companion/pages/health_page.py),
companion/health_signals.py and companion/battery_chart.py. Every entry
is migrated onto a stable message id: the source-side Message is
declared where the English constant already lives, never here — this
module only carries each id's French translation. A handful of ids
(e.g. "health.resolve", "health.count") are shared by more than one
call site on the Health page — one catalogue entry, several readers.

Copy follows sentence case, the typographic apostrophe (U+2019,
never a straight quote), and a non-breaking space (U+00A0) before
":" ";" "?" "!". The relative-age connector and quantity strings
below additionally carry a real U+00A0 between a number and its
unit (e.g. "il y a 1\u00a0j").
"""

MESSAGES = {
    # companion/layout.py's relative_age_text()/local_clock_text() —
    # the copy lives here rather than as a layout.py literal so it
    # stays with the rest of the French catalogue.
    "health.just_now": "à l’instant",
    "health.ago": "il y a %s",

    # The same ladder read forwards, for layout.relative_future_text().
    # The connector and the under-a-minute collapse sit here, beside
    # the past form's own, and not as a literal in the script that
    # ticks these elements, which is what lets that script carry no
    # French at all. The quantity strings carry the same real U+00A0
    # between the number and the unit (e.g. "dans 4\u00a0min").
    "health.in_a_moment": "dans un instant",
    "health.in": "dans %s",

    # The same ladder again, this time as nine complete wordings
    # rather than as a connector plus a unit.
    # companion/static/relative-time.js rewrites these elements once a
    # second, so the wordings have to exist client-side; they are
    # rendered onto <body> and read back with getAttribute(), which is
    # what lets that script carry no French at all — the four English
    # forms above are its no-attribute fallbacks.
    #
    # "#" is where the number goes, never "%s": these strings reach the
    # browser as attribute values, and a stray "%s"/"%d"/"{}" here would
    # fail the harness's own scan. A wording with no "#" in it takes no
    # number at all, which is how French's collapsed sub-minute bucket
    # ("à l’instant", "dans un instant") stays data rather than a
    # branch in the script. These cannot drift from
    # layout.relative_age_text()/relative_future_text(): a test fills
    # each one with the quantity _age_bucket() picks and asserts
    # equality against those functions, in both languages, per bucket.
    "health.s_ago": "à l’instant",
    "health.m_ago": "il y a # min",
    "health.h_ago": "il y a # h",
    "health.d_ago": "il y a # j",
    "health.in_s": "dans un instant",
    "health.in_m": "dans # min",
    "health.in_h": "dans # h",
    "health.in_d": "dans # j",

    # What a countdown reads once its instant has passed — neutral,
    # and never a warning word.
    "health.waiting": "en attente…",

    # --- Page header / purpose / freshness (health_page.py) -----------
    "health.updating": "Mise à jour…",

    # --- Anomaly banner --------------------------------------------
    "health.something_needs_attention_check_the_tiles_below":
        "Quelque chose nécessite votre attention — consultez les lignes ci-dessous.",
    "health.warning": "avertissement",
    "health.error": "erreur",
    "health.issue": "problème",
    "health.device_check_in_is_stale": "Le cadre ne répond plus.",
    "health.flight_data_is_stale": "Données de vol anciennes.",
    "health.battery_dropped_abnormally":
        "Baisse anormale de batterie.",
    "health.data_sources_disagreed_recently":
        "Sources en désaccord récemment.",
    "health.some_airlines_are_unidentified": "Compagnies non identifiées.",
    "health.all_data_sources_failed": "Toutes les sources ont échoué.",

    # --- Source-fault landing block ---------------------------------
    "health.ads_b_source_outage": "Panne de source ADS-B",
    "health.the_frame_s_alert_badge_is_showing_because":
        "Le badge d’alerte du cadre s’affiche parce qu’aucune source ADS-B "
        "configurée (%s) n’a répondu lors du dernier passage du pipeline — "
        "il s’agit d’une panne de source de données, pas d’un problème matériel.",

    # --- Frame connection / flight data / sources rows ------------------
    "health.device_connection_help":
        "Moment où le cadre a contacté le serveur pour la dernière fois.",
    "health.last_aircraft_detected": "Dernier avion détecté",
    "health.checking_in_normally": "Se connecte normalement",
    "health.has_not_checked_in_for_a_while": "N’a pas répondu depuis un moment",
    "health.has_not_checked_in_for_a_long_time": "N’a pas répondu depuis longtemps",
    # The frame's own held state, the neutral "off" device_state —
    # never a warning.
    "health.asleep_for_quiet_hours": "En veille pendant les heures calmes",
    "health.running_on_schedule": "Fonctionne comme prévu",
    "health.a_little_behind": "Un peu en retard",
    "health.has_not_run_for_a_long_time": "N’a pas fonctionné depuis longtemps",
    # The pipeline's real never-ran state.
    "health.no_detection_yet": "Aucune détection pour l’instant.",
    "health.the_frame_has_not_reported_a_flight_since_it":
        "Le cadre n’a signalé aucun vol depuis son démarrage.",
    "health.sources_agree": "Les sources concordent",
    "health.sources_disagreed_recently": "Les sources se sont contredites récemment",
    "health.nothing_to_compare_yet": "Rien à comparer pour l’instant",
    "health.this_appears_once_the_frame_has_recorded_at":
        "Ceci apparaît une fois que le cadre a enregistré au moins un vol.",
    "health.more_details": "Plus de détails",
    "health.both_agree": "Les deux concordent",
    "health.both_flight_data_sources_on_the_frame_picked":
        "Les deux sources de données de vol du cadre ont identifié le même avion.",
    "health.only_one_saw_it": "Une seule l’a vu",
    "health.only_one_of_the_two_sources_returned_an":
        "Une seule des deux sources a renvoyé un avion ce cycle — ce n’est "
        "pas un désaccord, il n’y avait simplement rien à comparer du "
        "côté de l’autre source.",
    "health.they_disagree": "Elles se contredisent",
    "health.the_two_sources_named_different_aircraft_so":
        "Les deux sources ont identifié des avions différents, donc rien "
        "n’a été affiché ce cycle — l’écran a conservé l’image précédente.",

    # --- Flight identification row ---------------------------------------
    "health.over_the_last_days_events": "au cours des %d derniers jours, %d événements",
    # The singular sibling of the line above. A window holding
    # exactly one detection reads "1 events" in English and
    # "1 événements" here; only the noun loses its "s" (the day count
    # is a fixed 30, so it never needs a singular form of its own).
    "health.over_the_last_days_event": "au cours des %d derniers jours, %d événement",

    # --- Battery trend section -------------------------------------------
    "health.battery": "Batterie",
    "health.low_battery_pct": "Batterie faible \u2014 %d\u00a0%%",
    "health.battery_unit_group": "Unité du graphique de batterie",
    "health.battery_unit_percent": "Pourcentage",
    "health.battery_unit_voltage": "Tension",
    "health.last_3_months_daily_average": "3 derniers mois, moyenne quotidienne",
    "health.daily_average_reading": "%s — moyenne quotidienne (%d relevé)",
    "health.daily_average_readings": "%s — moyenne quotidienne (%d relevés)",
    "health.daily_average": "%s — moyenne quotidienne",
    # The drawn low-battery threshold's legend. The connector stays
    # the "—" every other label in this section uses, and the real
    # U+00A0 sits before the "%%" as it does above.
    "health.low_battery_mv":
        "Batterie faible \u2014 %d mV (\u2248 %d\u00a0%%)",
    "health.latest_readings": "%d derniers relevés",
    "health.no_battery_readings_yet": "Aucun relevé de batterie pour l’instant.",
    "health.no_battery_telemetry_recorded_yet_check_back":
        "Aucune télémétrie de batterie enregistrée pour l’instant — "
        "revenez après la prochaine vérification de l’appareil.",
    "health.timestamp": "Horodatage",
    "health.battery_mv": "Batterie (mV)",
    "health.view_reading": "Voir %d relevé%s",

    # --- Health rows (companion/health_rows.py, health_page.py) ----------
    # The four state words are spoken, never shown: each row's icon shape
    # carries the state visually.
    "health.row_state_ok": "Normal",
    "health.row_state_warn": "À surveiller",
    "health.row_state_error": "Problème",
    "health.row_state_off": "Neutre",
    "health.row_connection": "Connexion du cadre",
    "health.row_battery": "Batterie",
    "health.row_flight_data": "Données de vol",
    "health.row_sources": "Sources de données",
    "health.row_battery_ok": "Niveau normal",
    "health.row_battery_warn": "Baisse plus rapide que prévu",
    "health.row_backup_ok": "À jour",
    "health.row_backup_warn": "En retard",
    "health.row_no_readings": "Aucun relevé pour l’instant",
    "health.row_no_check_in": "Aucune connexion pour l’instant",
    "health.row_unavailable": "Indisponible",
    "health.row_last_check_in": "Dernière connexion",
    "health.row_next_wake": "Prochain réveil",
    "health.row_last_run": "Dernière exécution",
    # Real U+00A0 between each figure and its unit or sign.
    "health.row_battery_value": "%d\u00a0%% · %d\u00a0mV",
    "health.row_no_disagreement": "Aucun désaccord",
    "health.row_one_disagreement": "1\u00a0désaccord",
    "health.row_n_disagreements": "%d\u00a0désaccords",
    "health.row_identified": "%s\u00a0%% des vols identifiés",
    "health.row_to_resolve": "%d à résoudre",
    "health.row_nothing_to_resolve": "Rien à résoudre",

    # --- Screen / Server & data group headings ---------------------------
    "health.screen": "Écran",
    "health.server_data": "Serveur et données",

    # --- Unresolved-prefix registry / filter bar --------------------------
    "health.airlines_we_could_not_name": "Compagnies non identifiées",
    "health.no_coverage_gaps": "Aucune lacune de couverture.",
    "health.every_airline_we_ve_seen_recently_has_been":
        "Toutes les compagnies vues récemment ont été identifiées — il "
        "n’y a plus rien à rechercher.",
    # This note is one sentence; the instruction clause is in the
    # read-only note detail entry below.
    "health.this_list_is_read_only_here": "Cette liste est en lecture seule ici.",
    "health.each_row_s_resolve_link_opens_the_airlines_page":
        "Le lien Résoudre de chaque ligne ouvre la page Compagnies pour "
        "nommer cette compagnie (et ajouter une image, si besoin).",
    "health.filter_by_prefix": "Filtrer par préfixe",
    "health.search_placeholder": "Préfixe…",
    "health.no_matching_prefixes": "Aucun préfixe correspondant",
    "health.try_a_different_search_or_clear_filter_to_see":
        "Essayez une autre recherche, ou effacez le filtre pour voir "
        "les %d préfixes.",
    "health.of_shown": "%d sur %d affichés",
    "health.clear": "Effacer",
    "health.prefix": "Préfixe",
    "health.count": "Nombre",
    # These two keys are also read by
    # airlines_page.RESOLVE_CONTEXT_LABELS (the resolve dialog's <dt>
    # labels) — one catalogue entry, several readers.
    "health.first_seen": "Première fois",
    "health.last_seen": "Dernière fois",
    "health.example_callsign": "Exemple d’indicatif",
    "health.resolve": "Résoudre",
    "health.resolve_prefix": "Résoudre le préfixe %s",
    "health.resolve_this_prefix": "Résoudre ce préfixe",

    # --- Resolution-statistics table --------------------------------------
    "health.how_well_we_name_flights": "Identification des vols",
    # Kept as an unformatted "%d" template, exactly like the English
    # source constant.
    "health.no_flights_in_the_last_days": "Aucun vol depuis %d jours",
    "health.the_frame_has_not_recorded_a_detection_in_this":
        "Le cadre n’a enregistré aucune détection sur cette période. "
        "Elle apparaîtra ici après le prochain réveil.",
    "health.other": "Autre",
    "health.a_route_source_this_page_does_not_recognise_or":
        "Une source de trajet que cette page ne reconnaît pas, ou "
        "aucune n’a été enregistrée — comptabilisée ici afin que le "
        "total corresponde toujours à chaque événement de la période.",
    "health.source": "Source",
    "health.description": "Description",
    "health.fresh_lookup": "Recherche fraîche",
    "health.a_live_lookup_in_the_route_database_resolved_a":
        "Une recherche en direct dans la base de trajets a résolu un "
        "trajet complet ce cycle.",
    "health.cached_hit": "Résultat en cache",
    "health.a_previously_cached_route_was_reused_sparing_a":
        "Un trajet précédemment mis en cache a été réutilisé, évitant "
        "une requête réseau.",
    "health.airline_only": "Compagnie seulement",
    "health.the_route_database_had_no_route_but_the":
        "La base de trajets n’avait aucun trajet, mais le préfixe ICAO "
        "de l’indicatif a identifié la compagnie grâce à la table de "
        "préfixes statique.",
    "health.miss": "Échec",
    "health.neither_the_route_database_nor_the_static":
        "Ni la base de trajets ni la table de préfixes statique n’ont "
        "rien résolu pour cet indicatif, il apparaît donc dans la liste "
        "Compagnies non identifiées ci-dessus.",
    "health.manual": "Manuel",
    "health.the_operator_resolved_this_callsign_s_prefix_by":
        "L’opérateur a résolu à la main le préfixe de cet indicatif, "
        "depuis l’interface web companion.",

    # --- Off-box backup card --------------------------------------
    "health.off_box_backup": "Sauvegarde hors serveur",
    "health.last_off_box_backup": "Dernière sauvegarde hors serveur",
    # A real U+00A0 between the number and "jours".
    "health.no_off_box_backup_in_the_last_3_days":
        "Aucune sauvegarde hors serveur depuis 3 jours.",
    "health.no_off_box_backup_has_been_pulled_yet":
        "Aucune sauvegarde hors serveur n’a encore été récupérée.",
    # layout.concise_timestamp_html()'s own fallback parameter — this
    # card's one non-quantity, non-page-specific string; its only call
    # site across the app.
    "health.never": "jamais",

    # --- Degrade-not-raise fallback --------------------------------------
    "health.health_history_is_temporarily_unavailable_check":
        "L’historique d’état est temporairement indisponible — "
        "consultez les journaux du service companion.",
}
