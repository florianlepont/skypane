# -*- coding: utf-8 -*-
"""French strings for the Users page and its result toasts. The source-side
Message for each id is declared in companion/pages/users_page.py and
companion/console_users.py; this module only carries the French.
"""

MESSAGES = {
    "admin_users.users": "Utilisateurs",
    "admin_users.n_users": "%d utilisateurs",
    "admin_users.one_user": "1 utilisateur",
    "admin_users.email": "Adresse e-mail",
    "admin_users.role": "Rôle",
    "admin_users.role_user": "Utilisateur",
    "admin_users.role_administrator": "Administrateur",
    "admin_users.status_disabled": "Désactivé",
    "admin_users.status_invited": "Invité",
    "admin_users.this_is_you": "C’est vous.",
    "admin_users.the_last_active_administrator_cannot_be_changed":
        "Le dernier administrateur actif ne peut pas être modifié.",
    "admin_users.save_role": "Enregistrer le rôle",
    "admin_users.unlink_identity": "Dissocier l’identité",
    "admin_users.invite_a_user": "Inviter un utilisateur",
    "admin_users.they_sign_in_with_this_email_through_auth0_skypane_does":
        "Ils se connectent avec cette adresse via Auth0. SkyPane ne leur envoie "
        "aucun message\u00a0: prévenez-les vous-même.",
    "admin_users.invite_a_user_button": "+ Inviter un utilisateur",
    "admin_users.invite_user": "Inviter",
    "admin_users.back_to_users": "Retour aux utilisateurs",
    "admin_users.n_frames": "%d cadres",
    "admin_users.one_frame": "1 cadre",
    "admin_users.you": "Vous",
    "admin_users.enter_a_valid_email_address": "Saisissez une adresse e-mail valide.",
    "admin_users.that_email_is_already_invited": "Cet e-mail est déjà invité.",
    "admin_users.choose_a_role": "Choisissez un rôle.",
    "admin_users.flash_action_refused": "Action refusée",
    "admin_users.flash_invitation_saved": "Invitation enregistrée",
    "admin_users.flash_invitation_saved_detail":
        "Dites à {email} de se connecter avec cette adresse.",
    "admin_users.flash_role_saved": "Rôle enregistré",
    "admin_users.flash_role_saved_detail": "{email} est maintenant {role}.",
    "admin_users.flash_user_disabled": "Utilisateur désactivé",
    "admin_users.flash_user_disabled_detail":
        "La session de {email} est fermée ; la connexion est impossible.",
    "admin_users.flash_user_enabled": "Utilisateur activé",
    "admin_users.flash_user_enabled_detail": "{email} peut de nouveau se connecter.",
    "admin_users.flash_identity_unlinked": "Identité dissociée",
    "admin_users.flash_identity_unlinked_detail":
        "La session de {email} est fermée ; son identité sera associée de nouveau "
        "à la prochaine connexion.",
    "admin_users.flash_last_admin_detail":
        "Il doit rester au moins un administrateur actif.",
    "admin_users.flash_self_action_detail":
        "Vous ne pouvez pas vous désactiver ni vous rétrograder.",
    "admin_users.flash_user_not_found": "Utilisateur introuvable",
    "admin_users.flash_user_not_found_detail":
        "Il a peut-être déjà été modifié. Rien n’a été changé.",
    "admin_users.flash_nothing_to_unlink": "Rien à dissocier",
    "admin_users.flash_nothing_to_unlink_detail":
        "Cette personne n’a aucune identité associée. Rien n’a été changé.",
    "admin_users.flash_choose_a_role": "Choisissez un rôle",
    "admin_users.flash_choose_a_role_detail":
        "Le rôle doit être Utilisateur ou Administrateur. Rien n’a été changé.",
    "admin_users.col_user": "Utilisateur",
    "admin_users.col_frames": "Cadres",
    "admin_users.col_last_sign_in": "Dernière connexion",
    "admin_users.col_active": "Actif",
    "admin_users.never_signed_in": "Jamais connecté",
    "admin_users.role_of_aria": "Rôle de %s",
    "admin_users.active_aria": "Actif\u00a0: %s",
    "admin_users.more_actions_aria": "Autres actions pour %s",
}
