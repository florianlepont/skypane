# -*- coding: utf-8 -*-
"""French strings for the sign-in surfaces (login card with Auth0 and the
legacy shared password, the not-invited refusal, the generic sign-in
errors, the sign-in/sign-out interstitial), the Account page, and the
shell's legacy-access flag. The source-side Message for each id is
declared in companion/login_page.py, companion/pages/account_page.py and
companion/ui_nav.py; this module only carries the French.
"""

MESSAGES = {
    # --- Login card -------------------------------------------------
    "account.sign_in_to_manage_your_skypane_frames":
        "Connectez-vous pour gérer vos cadres SkyPane.",
    "account.use_the_shared_password_legacy":
        "Utiliser le mot de passe partagé (ancien accès)",
    "account.legacy": "Ancien accès",
    "account.temporary_access_for_the_administrator_it":
        "Accès temporaire pour l’administrateur. Il sera retiré une fois "
        "la connexion Auth0 en service.",
    "account.sign_in_with_password": "Se connecter avec le mot de passe",
    "account.sign_in_is_not_configured":
        "La connexion n’est pas configurée",

    # --- Not-invited refusal ---------------------------------------
    "account.no_invitation_found": "Aucune invitation trouvée",
    "account.this_account_has_not_been_invited_to_skypane":
        "Ce compte n’a pas été invité sur SkyPane. Demandez une invitation "
        "à l’administrateur.",
    "account.back_to_sign_in": "Retour à la connexion",
    "account.back_to_account": "Retour au compte",

    # --- Generic sign-in errors ------------------------------------
    "account.sign_in_could_not_be_completed":
        "La connexion n’a pas pu aboutir",
    "account.start_again_from_this_page_if_it_keeps":
        "Recommencez depuis cette page. Si cela persiste, vérifiez que "
        "les cookies sont activés.",
    "account.sign_in_took_too_long": "La connexion a pris trop de temps",
    "account.start_again_from_this_page":
        "Recommencez depuis cette page.",
    "account.sign_in_is_not_available_right_now":
        "La connexion n’est pas disponible pour le moment",
    "account.try_again_in_a_few_minutes": "Réessayez dans quelques minutes.",
    "account.password_sign_in_is_turned_off":
        "La connexion par mot de passe est désactivée",
    "account.use_the_sign_in_button_above":
        "Utilisez le bouton Se connecter ci-dessus.",

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
    "account.administrator_legacy_access":
        "Administrateur (ancien accès)",
    "account.preferences": "Préférences",
    "account.frames": "Cadres",
    "account.your_frames_will_appear_here": "Vos cadres apparaîtront ici",
    "account.once_an_administrator_pairs_a_frame_to_your":
        "Dès qu’un administrateur associe un cadre à votre compte, il "
        "apparaîtra sur cette page.",

    # --- Shell flag --------------------------------------------------
    "account.legacy_access": "Ancien accès",
    "account.signed_in_with_the_shared_password":
        "Connecté avec le mot de passe partagé",
}