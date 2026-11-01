# -*- coding: utf-8 -*-
"""French strings for frame co-management: the Co-managers card and the flash
toasts.

The source-side Message for each id is declared in
companion/pages/co_managers_card.py; this module only carries the French.
"""

MESSAGES = {
    "co_managers.heading": "Co-gestionnaires",
    "co_managers.purpose_manage":
        "Les personnes qui peuvent modifier les réglages de ce cadre avec le "
        "propriétaire. Elles ne peuvent ni le retirer ni le réattribuer.",
    "co_managers.purpose_read_only":
        "Ces personnes gèrent ce cadre. Seul le propriétaire ou un "
        "administrateur peut modifier la liste.",
    "co_managers.pill_owner": "Propriétaire",
    "co_managers.pill_you": "Vous",
    "co_managers.pill_disabled": "Désactivé",
    "co_managers.empty_heading": "Aucun co-gestionnaire pour l’instant",
    "co_managers.empty_body_owner":
        "Ajoutez quelqu’un par adresse e-mail pour qu’il puisse aussi gérer ce cadre.",
    "co_managers.empty_body_admin":
        "Choisissez une personne invitée pour qu’elle puisse aussi gérer ce cadre.",
    "co_managers.label_email": "Adresse e-mail",
    "co_managers.helper_email": "La personne doit déjà être invitée sur SkyPane.",
    "co_managers.label_person": "Personne invitée",
    "co_managers.choose_person": "Choisir une personne",
    "co_managers.no_candidates":
        "Toutes les personnes invitées sont déjà sur ce cadre.",
    "co_managers.add_button": "Ajouter un co-gestionnaire",
    "co_managers.remove_button": "Enlever",
    "co_managers.remove_aria": "Enlever %s de ce cadre",
    "co_managers.leave": "Quitter ce cadre",
    "co_managers.leave_consequence":
        "Vous perdrez l’accès à ce cadre et à ses réglages. Le propriétaire "
        "ou un administrateur pourra vous ajouter de nouveau.",
    "co_managers.leave_keep": "Rester sur ce cadre",
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
