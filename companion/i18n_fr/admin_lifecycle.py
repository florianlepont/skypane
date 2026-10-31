# -*- coding: utf-8 -*-
"""French strings for the frame lifecycle result toasts. The source-side
Message for each id is declared in companion/console_lifecycle.py; this
module only carries the French.
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
}
