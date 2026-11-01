# -*- coding: utf-8 -*-
"""French strings for frame co-management: the flash toasts.

The source-side Message for each id is declared in
companion/pages/co_managers_card.py; this module only carries the French.
"""

MESSAGES = {
    "co_managers.flash_added":
        "Co-gestionnaire ajouté — cette personne peut désormais gérer ce cadre.",
    "co_managers.flash_removed":
        "Co-gestionnaire retiré — cette personne n’a plus accès à ce cadre.",
    "co_managers.flash_left":
        "Vous avez quitté le cadre — il n’apparaît plus dans votre compte.",
    "co_managers.flash_add_refused":
        "Cette adresse ne peut pas être ajoutée — vérifiez l’orthographe, ou "
        "demandez à un administrateur d’inviter d’abord cette personne.",
    "co_managers.flash_failed":
        "Impossible de mettre à jour les co-gestionnaires — réessayez dans un "
        "instant.",
    "co_managers.flash_leave_noop":
        "Rien n’a changé — seuls les co-gestionnaires peuvent quitter un cadre.",
}
