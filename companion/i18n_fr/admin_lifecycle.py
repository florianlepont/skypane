# -*- coding: utf-8 -*-
"""French strings for the frame lifecycle result toasts and the Audit log
page. The source-side Message for each id is declared in
companion/console_lifecycle.py and companion/pages/audit_page.py; this module
only carries the French.
"""

MESSAGES = {
    "admin_lifecycle.flash_reassigned": "Cadre réattribué",
    "admin_lifecycle.flash_reassigned_detail": "{frame} appartient maintenant à {email}.",
    "admin_lifecycle.flash_retired": "Cadre retiré",
    "admin_lifecycle.flash_retired_detail":
        "{frame} affichera un écran « retiré » à sa prochaine mise à jour. "
        "Ses données sont conservées.",
    "admin_lifecycle.flash_reactivated": "Cadre réactivé",
    "admin_lifecycle.flash_reactivated_detail":
        "Il repasse en association et affichera un nouveau code à sa prochaine mise à jour.",
    "admin_lifecycle.flash_action_refused": "Action refusée",
    "admin_lifecycle.flash_live_protected_detail":
        "Le cadre actif ne peut pas être retiré.",
    "admin_lifecycle.flash_frame_busy": "Cadre occupé",
    "admin_lifecycle.flash_frame_busy_detail":
        "Une mise à jour de ce cadre est en cours. Réessayez dans une minute.",
    "admin_lifecycle.flash_frame_not_found": "Cadre introuvable",
    "admin_lifecycle.flash_frame_not_found_detail":
        "Il a peut-être déjà été modifié. Rien n’a été changé.",
    "admin_lifecycle.flash_owner_unavailable": "Choisissez un propriétaire actif",
    "admin_lifecycle.flash_owner_unavailable_detail":
        "Cette personne est désactivée ou n’existe pas. Rien n’a été changé.",
    "admin_lifecycle.flash_same_owner": "Déjà propriétaire",
    "admin_lifecycle.flash_same_owner_detail":
        "Cette personne possède déjà ce cadre. Rien n’a été changé.",
    "admin_lifecycle.flash_action_failed": "Échec de l’action",
    "admin_lifecycle.flash_action_failed_detail":
        "Le cadre n’a pas pu être modifié. Ses données ont été conservées. "
        "Consultez le journal d’audit.",
    "admin_lifecycle.what_happened_on_the_platform_newest_first":
        "Ce qui s’est passé sur la plateforme, du plus récent au plus ancien.",
    "admin_lifecycle.when": "Quand",
    "admin_lifecycle.who": "Qui",
    "admin_lifecycle.action": "Action",
    "admin_lifecycle.target": "Cible",
    "admin_lifecycle.outcome": "Résultat",
    "admin_lifecycle.from": "Depuis",
    "admin_lifecycle.system": "Système",
    "admin_lifecycle.frame_actor": "Cadre",
    "admin_lifecycle.outcome_success": "Réussi",
    "admin_lifecycle.outcome_refused": "Refusé",
    "admin_lifecycle.outcome_failed": "Échoué",
    "admin_lifecycle.action_other": "Autre action",
    "admin_lifecycle.action_frame_register": "Cadre enregistré",
    "admin_lifecycle.action_pairing_issue": "Code d’association émis",
    "admin_lifecycle.action_pairing_claim": "Code d’association utilisé",
    "admin_lifecycle.action_device_reassign": "Cadre réattribué",
    "admin_lifecycle.action_device_retire": "Cadre retiré",
    "admin_lifecycle.action_device_reactivate": "Cadre réactivé",
    "admin_lifecycle.action_user_invite": "Utilisateur invité",
    "admin_lifecycle.action_user_role": "Rôle modifié",
    "admin_lifecycle.action_user_disable": "Utilisateur désactivé",
    "admin_lifecycle.action_user_enable": "Utilisateur activé",
    "admin_lifecycle.action_user_unlink": "Identité dissociée",
    "admin_lifecycle.action_location_add": "Lieu ajouté",
    "admin_lifecycle.action_location_update": "Lieu modifié",
    "admin_lifecycle.action_location_delete": "Lieu supprimé",
    "admin_lifecycle.action_release_install": "Installation de version programmée",
    "admin_lifecycle.action_release_cancel": "Installation de version annulée",
    "admin_lifecycle.chip_all": "Tous",
    "admin_lifecycle.chip_pairing": "Association",
    "admin_lifecycle.chip_frames": "Cadres",
    "admin_lifecycle.chip_users": "Utilisateurs",
    "admin_lifecycle.chip_locations": "Lieux",
    "admin_lifecycle.chip_releases": "Versions",
    "admin_lifecycle.chip_failed": "Échecs",
    "admin_lifecycle.filter_events": "Filtrer les événements",
    "admin_lifecycle.n_events": "%d événements",
    "admin_lifecycle.one_event": "1 événement",
    "admin_lifecycle.nothing_recorded_yet": "Rien d’enregistré pour l’instant",
    "admin_lifecycle.actions_such_as_pairing_role_changes_and_releases":
        "Les actions comme l’association, les changements de rôle et les versions "
        "apparaîtront ici.",
    "admin_lifecycle.no_events_match_this_filter": "Aucun événement pour ce filtre",
    "admin_lifecycle.choose_all_to_see_every_event": "Choisissez Tous pour tout voir.",
    "admin_lifecycle.older": "Plus anciens",
    "admin_lifecycle.newer": "Plus récents",
    "admin_lifecycle.audit_pages": "Pages du journal d’audit",
}
