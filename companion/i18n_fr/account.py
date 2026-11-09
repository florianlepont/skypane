# -*- coding: utf-8 -*-
"""French strings for the sign-in surfaces (login card with Auth0 and the
legacy shared password, the refusals, the generic sign-in
errors, the sign-in/sign-out interstitial), the Account page, and the
shell's legacy-access flag. The source-side Message for each id is
declared in companion/login_page.py, companion/pages/account_page.py and
companion/ui_nav.py; this module only carries the French.
"""

MESSAGES = {
    # --- Login card -------------------------------------------------
    "account.sign_in_to_manage_your_skypane_frames":
        "Connectez-vous pour gérer vos cadres SkyPane.",
    "account.sign_in_is_not_configured":
        "La connexion n’est pas configurée",

    "account.first_visit_use_the_email_address_you_were":
        "Première visite\u00a0? Utilisez l’adresse e-mail avec laquelle on vous "
        "a invité.",

    # --- Refusals --------------------------------------------------
    "account.this_account_can_t_sign_in": "Ce compte ne peut pas se connecter",
    "account.it_has_not_been_invited_to_skypane_or_its":
        "Il n’a pas été invité sur SkyPane, ou son accès a été désactivé. "
        "Demandez à l’administrateur, ou connectez-vous avec l’adresse de "
        "votre invitation.",
    "account.use_another_account": "Utiliser un autre compte",
    "account.back_to_sign_in": "Retour à la connexion",
    "account.back_to_account": "Retour au compte",
    "account.sign_in_again": "Se reconnecter",
    "account.confirm_your_email_address": "Confirmez votre adresse e-mail",
    "account.your_sign_in_account_has_not_confirmed_its_email":
        "Votre compte de connexion n’a pas encore confirmé son adresse "
        "e-mail. Ouvrez le message de confirmation dans votre boîte de "
        "réception, puis reconnectez-vous.",
    "account.no_message_ask_the_administrator_to_resend_it":
        "Pas de message\u00a0? Demandez à l’administrateur de le renvoyer.",

    # --- Generic sign-in errors ------------------------------------
    "account.sign_in_could_not_be_completed":
        "La connexion n’a pas abouti",
    "account.press_sign_in_to_try_again_if_it_keeps":
        "Appuyez sur Se connecter pour réessayer. Si cela se reproduit, "
        "vérifiez que les cookies sont activés.",
    "account.sign_in_took_too_long": "La connexion a pris trop de temps",
    "account.session_expired_title": "Votre session a expiré",
    "account.session_expired_detail": "Reconnectez-vous pour reprendre où vous en étiez.",
    "account.press_sign_in_to_start_again":
        "Appuyez sur Se connecter pour recommencer.",
    "account.sign_in_was_cancelled": "La connexion a été annulée",
    "account.press_sign_in_whenever_you_are_ready":
        "Appuyez sur Se connecter quand vous voulez.",
    "account.sign_in_is_not_available_right_now":
        "La connexion est indisponible pour le moment",
    "account.try_again_in_a_few_minutes_if_it_lasts":
        "Réessayez dans quelques minutes. Si cela dure, prévenez "
        "l’administrateur.",
    "account.too_many_attempts": "Trop de tentatives",
    "account.wait_a_minute_then_press_sign_in":
        "Attendez une minute, puis appuyez sur Se connecter.",

    # --- Interstitial ----------------------------------------------
    "account.signing_you_in": "Connexion en cours…",
    "account.signing_you_out": "Déconnexion en cours…",
    "account.signing_in": "Connexion",
    "account.signing_out": "Déconnexion",
    "account.continue_to_s": "Continuer vers %s",
    "account.account": "Compte",

    # --- Account page ------------------------------------------------
    "account.your_skypane_sign_in_and_preferences":
        "Votre connexion SkyPane et vos préférences.",
    "account.identity": "Identité",
    "account.email": "E-mail",
    "account.role": "Rôle",
    "account.user": "Utilisateur",
    "account.administrator": "Administrateur",
    "account.preferences": "Préférences",
    "account.language": "Langue",
    "account.language_hint": "La langue des pages du compagnon.",
    "account.theme": "Thème",
    "account.theme_hint": "Clair, sombre, ou selon le système.",
    "account.my_frames": "Mes cadres",
    "account.unnamed_frame": "Cadre sans nom",
    "account.shared_by": "Partagé par %s",
    "account.leave_frame": "Quitter le cadre",
    "account.leave_frame_aria": "Quitter le cadre\u00a0: %s",
    "account.frame_owner": "Propriétaire",
    "account.frame_co_manager": "Co-gestionnaire",
    "account.co_manager_of_one": "Co-gestionnaire de 1 cadre",
    "account.co_manager_of_many": "Co-gestionnaire de %d cadres",
    "account.manage_access_aria": "Gérer l’accès\u00a0: %s",
}
