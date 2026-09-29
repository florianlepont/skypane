# -*- coding: utf-8 -*-
"""French strings for the Update page: the running version, the update
state words, the rollback banner, the scheduled/install sentences and
the version-history table.

Copy follows sentence case, the typographic apostrophe (U+2019, never
a straight quote), and a non-breaking space (U+00A0) before ":" ";"
"?" "!". "Version" and "Date" are genuine French words, spelled
identically to their English source (see test_i18n.py's
_UNCHANGED_IN_FRENCH cognate list) -- kept as the plain, compact
table-header nouns rather than a longer, distinct phrase.

Every entry is migrated onto a stable message id: the source-side
Message is declared in companion/pages/update_page.py, never here --
this module only carries each id's French translation. The nav label
itself ("nav.update") is owned by companion/i18n_fr/nav.py, alongside
the app's other nav labels.
"""

MESSAGES = {
    "update.status": "État",
    "update.version_history": "Historique des versions",
    "update.running_s": "Version en cours : %s",
    "update.no_version_reported_yet": "Aucune version signalée pour le moment",

    "update.available": "Disponible",
    "update.scheduled": "Planifiée",
    "update.in_progress": "En cours",
    "update.installed": "Installée",
    "update.failed": "Échec",

    "update.unknown_time": "une heure inconnue",
    "update.scheduled_installs_at_the_next_wake_around_s":
        "Planifiée — installation au prochain réveil, vers %s.",
    "update.scheduled_installs_when_quiet_hours_end_around_s":
        "Planifiée — installation à la fin des heures calmes, vers %s.",
    "update.firmware_rolled_back":
        "Firmware rétabli — la mise à jour vers %s a échoué au démarrage "
        "d’essai ; le cadre est revenu à %s.",

    "update.cancel": "Annuler",
    "update.install": "Installer",
    "update.not_installable": "Non installable",
    "update.install_firmware_s": "Installer le firmware %s ?",
    "update.the_frame_will_download_and_install_this":
        "Le cadre téléchargera et installera cette version à son "
        "prochain réveil, vers %s. Il conservera la mise à jour après un "
        "premier contact réussi — sinon, il revient automatiquement en "
        "arrière.",
    "update.the_frame_will_download_and_install_this_held":
        "Le cadre téléchargera et installera cette version à la fin des "
        "heures calmes, vers %s. Il conservera la mise à jour après un "
        "premier contact réussi — sinon, il revient automatiquement en "
        "arrière.",
    "update.couldn_t_schedule_that_update_please_try_again":
        "Impossible de planifier cette mise à jour — veuillez réessayer.",
    "update.couldn_t_cancel_the_frame_may_have_already":
        "Impossible d’annuler — le cadre a peut-être déjà commencé.",
    "update.an_update_is_already_installing_wait":
        "Une mise à jour est déjà en cours d’installation — veuillez "
        "patienter.",
    "update.install_s_now":
        "Installer %s maintenant ? Elle s’appliquera au prochain réveil.",

    "update.version": "Version",
    "update.date": "Date",
    "update.notes": "Remarques",
    "update.installed_column": "Installée",

    "update.no_releases_yet": "Aucune version publiée pour le moment",
    "update.publish_a_release":
        "Publiez une version en poussant un tag fw-v*. Elle apparaîtra ici "
        "une fois que la CI aura terminé la construction et la signature.",

    "update.bench": "Banc d’essai",
    "update.this_is_a_bench_build": "Il s’agit d’une version de banc d’essai.",
}
