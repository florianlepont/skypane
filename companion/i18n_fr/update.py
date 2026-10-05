# -*- coding: utf-8 -*-
"""French strings for the Update page: the call-to-action card, the
update state words, the rollback banner, the scheduled/install sentences
and the version list.

Copy follows sentence case, the typographic apostrophe (U+2019, never
a straight quote), and a non-breaking space (U+00A0) before ":" ";"
"?" "!". "Versions" is a genuine French word, spelled identically to its
English source (see test_i18n.py's _UNCHANGED_IN_FRENCH cognate list).

Every entry is migrated onto a stable message id: the source-side
Message is declared in companion/pages/update_page.py, never here --
this module only carries each id's French translation. The nav label
itself ("nav.update") is owned by companion/i18n_fr/nav.py, alongside
the app's other nav labels.
"""

MESSAGES = {
    "update.version_history": "Versions",
    "update.no_version_reported_yet": "Aucune version signalée pour le moment",

    "update.scheduled": "Planifiée",
    "update.in_progress": "En cours",

    "update.cta_up_to_date": "Le cadre est à jour",
    "update.cta_available": "Mise à jour disponible",
    "update.cta_scheduled": "Mise à jour planifiée",
    "update.cta_installing": "Installation en cours",
    "update.cta_failed": "Échec de l’installation",
    "update.cta_installing_body":
        "%s est en cours d’installation. Le cadre la conservera après un "
        "premier contact réussi\u00a0; sinon, il revient en arrière.",
    "update.cta_failed_body": "%s n’a pas pu être installée.",
    "update.cta_stays_on": "Le cadre reste sur %s.",
    "update.on_the_frame_s": "Sur le cadre\u00a0: %s",
    "update.installed_ago_s": "Installée %s",
    "update.installed_on_s": "Installée le %s",
    "update.released_ago_s": "Sortie %s",
    "update.released_on_s": "Sortie le %s",
    "update.last_installed_s": "Dernière installation\u00a0: %s",

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
    "update.install_version_s": "Installer %s",
    "update.roll_back_to_s": "Revenir à %s",
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


    "update.no_releases_yet": "Aucune version publiée pour le moment",
    "update.publish_a_release":
        "Publiez une version en poussant un tag fw-v*. Elle apparaîtra ici "
        "une fois que la CI aura terminé la construction et la signature.",

    "update.running_badge": "En cours",

    "update.bench": "Banc d’essai",
    "update.this_is_a_bench_build": "Il s’agit d’une version de banc d’essai.",
}
