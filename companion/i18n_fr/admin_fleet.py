# -*- coding: utf-8 -*-
"""French strings for the admin Fleet page: the frame list, its dialogs and
the result toasts. The source-side Message for each id is declared in
companion/pages/fleet_page.py and companion/console_pairing.py; this module
only carries the French.
"""

MESSAGES = {
    "admin_fleet.system_sub":
        "Le serveur derrière chaque cadre. Visible des administrateurs.",
    "admin_fleet.new_frame": "Nouveau cadre",
    "admin_fleet.formerly_owner": "Anciennement %s",
    "admin_fleet.switch_a_frame_on_when_its_pairing_code_appears_choose_add":
        "Allumez un cadre. Quand son code d’association s’affiche à l’écran, "
        "choisissez Ajouter un cadre.",
    "admin_fleet.keep_retired": "Laisser retiré",
    "admin_fleet.retire_frame_title": "Retirer «\u00a0%s\u00a0»\u00a0?",
    "admin_fleet.re_activate_frame_title": "Réactiver «\u00a0%s\u00a0»\u00a0?",
    "admin_fleet.add_a_frame": "Ajouter un cadre",
    "admin_fleet.frames": "Cadres",
    "admin_fleet.group_live": "En service",
    "admin_fleet.group_pending": "En attente d’appairage",
    "admin_fleet.group_retired": "Retirés",
    "admin_fleet.search_frames": "Rechercher parmi %d cadres",
    "admin_fleet.all_frames_n": "Tous les cadres (%d)",
    "admin_fleet.no_frame_found": "Aucun cadre trouvé",
    "admin_fleet.reactivate_wake_hint":
        "Le cadre affichera son code à son prochain réveil (24\u00a0h au plus). "
        "Appuyez sur Reset pour le relancer tout de suite.",
    "admin_fleet.unnamed_frame": "Cadre sans nom",
    "admin_fleet.waiting_for_pairing": "En attente d’association",
    "admin_fleet.unassigned": "Non attribué",
    "admin_fleet.no_frames_yet": "Aucun cadre pour l’instant",
    "admin_fleet.open_personal_view": "Ouvrir la vue personnelle",
    "admin_fleet.reassign": "Réattribuer",
    "admin_fleet.open_personal_view_aria": "Ouvrir la vue personnelle de %s",
    "admin_fleet.re_activate": "Réactiver",
    "admin_fleet.retire_frame": "Retirer le cadre",
    "admin_fleet.re_activate_frame": "Réactiver le cadre",
    "admin_fleet.keep_frame": "Garder le cadre",
    "admin_fleet.new_owner": "Nouveau propriétaire",
    "admin_fleet.reassign_frame_title": "Réattribuer «\u00a0%s\u00a0»\u00a0?",
    "admin_fleet.cancel": "Annuler",
    "admin_fleet.reassign_choose_owner_hint": "Choisissez un propriétaire pour continuer.",
    "admin_fleet.reassign_co_managers_lose_access":
        "Les cogestionnaires perdent l’accès à ce cadre.",
    "admin_fleet.reassign_aria": "Réattribuer %s à un autre propriétaire",
    "admin_fleet.this_frame_will_show_a_retired_screen_and_stop_updating":
        "Ce cadre affichera un écran « retiré » et ne se mettra plus à jour. "
        "Ses données sont conservées et vous pourrez le réactiver plus tard.",
    "admin_fleet.its_settings_and_history_are_erased_it_returns_to_pairing":
        "Ses réglages et son historique sont effacés. Il repasse en association "
        "et affiche un nouveau code.",
    "admin_fleet.settings_history_and_gallery_on_this_frame_are_erased":
        "Les réglages, l’historique et la galerie de %s sur ce cadre sont "
        "effacés. Le cadre redémarre comme un neuf.",
    "admin_fleet.only_the_owner_changes_nothing_is_erased":
        "Rien n’est effacé.",
    "admin_fleet.the_current_owner": "Le propriétaire actuel",
    "admin_fleet.pair_owner": "Propriétaire",
    "admin_fleet.choose_an_owner_option": "Choisissez un propriétaire",
    "admin_fleet.pair_frame": "Associer le cadre",
    "admin_fleet.admin_suffix": "(administrateur)",
    "admin_fleet.code_not_recognised": "Code non reconnu",
    "admin_fleet.the_code_is_wrong_expired_or_already_used":
        "Le code est erroné, expiré ou déjà utilisé. Un nouveau code apparaît "
        "sur le cadre dans les 35 minutes.",
    "admin_fleet.check_the_code_and_try_again": "Vérifiez le code et réessayez.",
    "admin_fleet.too_many_attempts": "Trop de tentatives",
    "admin_fleet.wait_a_few_minutes_before_trying_again":
        "Patientez quelques minutes avant de réessayer.",
    "admin_fleet.enter_the_pairing_code": "Saisissez le code d’association.",
    "admin_fleet.choose_an_owner": "Choisissez un propriétaire.",
    "admin_fleet.that_user_is_no_longer_available":
        "Cet utilisateur n’est plus disponible.",
    "admin_fleet.enter_a_valid_mac_address": "Saisissez une adresse MAC valide.",
    "admin_fleet.enter_the_64_character_hash": "Saisissez le hash de 64 caractères.",
    "admin_fleet.choose_the_hardware_type": "Choisissez le type de matériel.",
    "admin_fleet.flash_frame_paired": "Cadre associé",
    "admin_fleet.flash_frame_paired_detail":
        "{frame} appartient maintenant à {email}. Il affichera sa première "
        "image à la prochaine mise à jour.",
    "admin_fleet.flash_frame_registered": "Cadre enregistré",
    "admin_fleet.flash_frame_registered_detail":
        "Allumez-le. Il affichera un code d’association dans les 5 minutes.",
    "admin_fleet.flash_frame_duplicate":
        "Un cadre avec cette adresse est déjà enregistré.",
    "admin_fleet.retired_on": "Retiré le %s",
    "admin_fleet.belonged_to": "Appartenait à %s",
    "admin_fleet.code_shown_ago": "Code affiché %s",
    "admin_fleet.system_heading": "Système",
    "admin_fleet.block_state": "État",
    "admin_fleet.tabs_label": "Sections du cadre",
    "admin_fleet.tile_connection": "Connexion",
    "admin_fleet.tile_details": "Détails",
    "admin_fleet.tile_firmware": "Micrologiciel",
    "admin_fleet.back_to_frame": "Retour à %s",
    "admin_fleet.block_settings": "Réglages",
    "admin_fleet.block_access": "Accès",
    "admin_fleet.system_unavailable":
        "Aucune information système n’est disponible pour l’instant.",
    "admin_fleet.unknown_frame": "Ce cadre est introuvable.",
    "admin_fleet.retire_this_frame": "Retirer ce cadre…",
    "admin_fleet.retire_this_frame_hint":
        "Le cadre n’affiche plus rien et libère son propriétaire.",
    "admin_fleet.retire_this_frame_action": "Retirer…",
}
