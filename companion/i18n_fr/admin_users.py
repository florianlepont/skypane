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
    "admin_users.status_invited": "Invité, pas encore connecté",
    "admin_users.status_invited_help":
        "Cette personne a été ajoutée mais ne s’est pas encore connectée. La mention "
        "disparaît à sa première connexion.",
    "admin_users.this_is_you": "C’est vous.",
    "admin_users.the_last_active_administrator_cannot_be_changed":
        "Le dernier administrateur actif ne peut pas être modifié.",
    "admin_users.save_role": "Enregistrer le rôle",
    "admin_users.unlink_identity": "Réinitialiser la connexion",
    "admin_users.delete_user": "Supprimer l’utilisateur",
    "admin_users.promote_title": "Nommer cette personne administrateur\u00a0?",
    "admin_users.promote_what":
        "%s pourra gérer tous les cadres, tous les utilisateurs et tous les réglages.",
    "admin_users.promote_submit": "Nommer administrateur",
    "admin_users.promote_keep": "Garder utilisateur",
    "admin_users.demote_title": "Retirer les droits d’administrateur\u00a0?",
    "admin_users.demote_what":
        "%s perdra la console d’administration et ne verra plus que les cadres "
        "qu’il possède ou co-gère.",
    "admin_users.demote_submit": "Retirer les droits",
    "admin_users.demote_keep": "Garder administrateur",
    "admin_users.delete_user_title": "Supprimer cet utilisateur\u00a0?",
    "admin_users.delete_user_keep": "Garder cet utilisateur",
    "admin_users.delete_user_what":
        "%s est retiré de SkyPane et perd l’accès à ses cadres. Cette action est "
        "définitive.",
    "admin_users.unlink_identity_hint":
        "Déconnecte cette personne\u00a0; elle relie de nouveau son compte de connexion à "
        "sa prochaine connexion.",
    "admin_users.invite_a_user": "Inviter un utilisateur",
    "admin_users.invite_a_user_button": "+ Inviter un utilisateur",
    "admin_users.invite_user": "Inviter",
    "admin_users.cancel": "Annuler",
    "admin_users.done": "Terminé",
    "admin_users.copy": "Copier",
    "admin_users.send_new_invitation": "Envoyer une nouvelle invitation",
    "admin_users.invitation_ready": "Invitation prête",
    "admin_users.send_this_link_to": "Envoyez ce lien à %s",
    "admin_users.invitation_hint":
        "Il n’est affiché qu’une fois. Traitez-le comme un secret\u00a0: il expire "
        "dans {ttl}. La personne choisit son mot de passe, puis ouvre {url} et se "
        "connecte.",
    "admin_users.invitation_hint_no_url":
        "Il n’est affiché qu’une fois. Traitez-le comme un secret\u00a0: il expire "
        "dans {ttl}. La personne choisit son mot de passe, puis ouvre l’application "
        "et se connecte.",
    "admin_users.ttl_days": "%d jours",
    "admin_users.ttl_hours": "%d heures",
    "admin_users.invitation_link_message":
        "Bonjour, vous êtes invité(e) sur SkyPane. Ouvrez ce lien pour choisir votre "
        "mot de passe (il expire dans {ttl})\u00a0: {link} Ouvrez ensuite {url} et "
        "connectez-vous avec l’adresse {email}.",
    "admin_users.invitation_link_message_no_url":
        "Bonjour, vous êtes invité(e) sur SkyPane. Ouvrez ce lien pour choisir votre "
        "mot de passe (il expire dans {ttl})\u00a0: {link} Ouvrez ensuite l’application "
        "et connectez-vous avec l’adresse {email}.",
    "admin_users.invitation_not_created": "Lien d’invitation non créé",
    "admin_users.invitation_not_created_lead":
        "%s est invité(e), mais aucun lien d’invitation n’a été créé.",
    "admin_users.try_again": "Réessayer",
    "admin_users.invitation_failed_busy":
        "Le service de connexion est occupé. Réessayez dans un instant.",
    "admin_users.invitation_failed_generic":
        "Le service de connexion n’a pas accepté la demande. Réessayez\u00a0; si cela "
        "persiste, vérifiez les réglages Auth0 du serveur.",
    "admin_users.invitation_failed_not_set_up":
        "Les invitations automatiques ne sont pas configurées sur ce serveur. Créez "
        "leur compte dans Auth0 à la main.",
    "admin_users.invitation_failed_connection_id":
        "Une nouvelle invitation pour une personne qui a déjà un compte Auth0 demande "
        "l’identifiant de connexion Auth0 sur le serveur "
        "(SKYPANE_AUTH0_DB_CONNECTION_ID). Voir le guide de déploiement.",
    "admin_users.n_frames": "%d cadres",
    "admin_users.one_frame": "1 cadre",
    "admin_users.you": "Vous",
    "admin_users.status_active": "Actif",
    "admin_users.co_manager_suffix": "cogestionnaire",
    "admin_users.self_lock": "Vous ne pouvez pas vous désactiver ni vous rétrograder.",
    "admin_users.copied": "Copié",
    "admin_users.enter_a_valid_email_address": "Saisissez une adresse e-mail valide.",
    "admin_users.that_email_is_already_invited": "Cet e-mail est déjà invité.",
    "admin_users.choose_a_role": "Choisissez un rôle.",
    "admin_users.flash_action_refused": "Action refusée",
    "admin_users.flash_role_saved": "Rôle enregistré",
    "admin_users.flash_role_saved_detail": "{email} est maintenant {role}.",
    "admin_users.flash_user_disabled": "Utilisateur désactivé",
    "admin_users.flash_user_disabled_detail":
        "La session de {email} est fermée ; la connexion est impossible.",
    "admin_users.flash_user_enabled": "Utilisateur activé",
    "admin_users.flash_user_enabled_detail": "{email} peut de nouveau se connecter.",
    "admin_users.flash_identity_unlinked": "Connexion réinitialisée",
    "admin_users.flash_identity_unlinked_detail":
        "La session de {email} est fermée ; son compte de connexion sera relié de "
        "nouveau à la prochaine connexion.",
    "admin_users.flash_last_admin_detail":
        "Il doit rester au moins un administrateur actif.",
    "admin_users.flash_self_action_detail":
        "Vous ne pouvez pas vous désactiver, vous rétrograder ni vous supprimer.",
    "admin_users.flash_user_deleted": "Utilisateur supprimé",
    "admin_users.flash_user_deleted_detail":
        "{email} a été supprimé. Le journal d’audit conserve son adresse.",
    "admin_users.flash_owns_frame_detail":
        "{email} possède encore le cadre {frame}. Réaffectez ou retirez d’abord le "
        "cadre. Rien n’a été changé.",
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
