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

    # --- Page header / purpose / freshness (health_page.py) -----------
    "Screen status and server data quality, in one place.":
        "L’état de l’écran et la qualité des données du serveur, au même endroit.",
    "Updating…": "Mise à jour…",
    "Updated ": "Mis à jour ",
    "Pause updates": "Suspendre les mises à jour",
    "Resume updates": "Reprendre les mises à jour",

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
    "Running on schedule": "Fonctionne comme prévu",
    "A little behind": "Un peu en retard",
    "Has not run for a long time": "N’a pas fonctionné depuis longtemps",
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

    # --- Battery trend section -------------------------------------------
    "Battery trend": "Tendance de la batterie",
    "Last 3 months, daily average": "3 derniers mois, moyenne quotidienne",
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
    "— the ADS-B pipeline and route resolution: is the data fresh and "
    "trustworthy.":
        "— le pipeline ADS-B et la résolution des trajets : les "
        "données sont-elles fraîches et fiables.",

    # --- Unresolved-prefix registry / filter bar --------------------------
    "Airlines we could not name": "Compagnies non identifiées",
    "No coverage gaps.": "Aucune lacune de couverture.",
    "Every airline we've seen recently has been named — nothing left "
    "to look up.":
        "Toutes les compagnies vues récemment ont été identifiées — il "
        "n’y a plus rien à rechercher.",
    "This list is read-only here — each row's Resolve link opens the "
    "Airlines page to name that airline (and add artwork, if it "
    "needs one).":
        "Cette liste est en lecture seule ici — le lien Résoudre de "
        "chaque ligne ouvre la page Compagnies pour nommer cette "
        "compagnie (et ajouter une image, si besoin).",
    "Filter by prefix": "Filtrer par préfixe",
    "No matching prefixes": "Aucun préfixe correspondant",
    "Try a different search, or Clear filter to see all %d prefixes.":
        "Essayez une autre recherche, ou effacez le filtre pour voir "
        "les %d préfixes.",
    "%d of %d shown": "%d sur %d affichés",
    "Clear": "Effacer",
    "Prefix": "Préfixe",
    "Count": "Nombre",
    "First seen": "Vu pour la première fois",
    "Last seen": "Vu pour la dernière fois",
    "Example callsign": "Exemple d’indicatif",
    "Resolve": "Résoudre",
    "Resolve prefix %s": "Résoudre le préfixe %s",
    "Resolve this prefix": "Résoudre ce préfixe",

    # --- Resolution-statistics table --------------------------------------
    "How well we name flights": "Notre capacité à identifier les vols",
    "No resolution data yet.": "Aucune donnée de résolution pour l’instant.",
    "No flight events recorded yet — resolution statistics appear "
    "once the ADS-B pipeline has detected a flight.":
        "Aucun événement de vol enregistré pour l’instant — les "
        "statistiques de résolution apparaissent une fois que le "
        "pipeline ADS-B a détecté un vol.",
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

    # --- Degrade-not-raise fallback --------------------------------------
    "Health history is temporarily unavailable — check the companion "
    "service logs.":
        "L’historique d’état est temporairement indisponible — "
        "consultez les journaux du service companion.",
}
