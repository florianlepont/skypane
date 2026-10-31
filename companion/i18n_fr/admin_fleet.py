# -*- coding: utf-8 -*-
"""French strings for the admin Fleet page: the frame table, the pairing
claim card, the registration card and the result toasts. The source-side
Message for each id is declared in companion/pages/fleet_page.py and
companion/console_pairing.py; this module only carries the French.
"""

MESSAGES = {
    "admin_fleet.every_frame_on_the_platform_with_its_owner_and_state":
        "Tous les cadres de la plateforme, avec leur propriétaire et leur état.",
    "admin_fleet.frames": "Cadres",
    "admin_fleet.n_frames": "%d cadres",
    "admin_fleet.one_frame": "1 cadre",
    "admin_fleet.frame": "Cadre",
    "admin_fleet.owner": "Propriétaire",
    "admin_fleet.hardware": "Matériel",
    "admin_fleet.last_seen": "Dernier contact",
    "admin_fleet.battery": "Batterie",
    "admin_fleet.firmware": "Version firmware",
    "admin_fleet.status": "État",
    "admin_fleet.actions": "Actions",
    "admin_fleet.n_a": "n/d",
    "admin_fleet.never_seen": "Jamais",
    "admin_fleet.unnamed_frame": "Cadre sans nom",
    "admin_fleet.waiting_for_pairing": "En attente d’association",
    "admin_fleet.formerly": "anciennement %s",
    "admin_fleet.unassigned": "Non attribué",
    "admin_fleet.live": "Actif",
    "admin_fleet.pending": "En attente",
    "admin_fleet.retired": "Retiré",
    "admin_fleet.low_battery": "Batterie faible",
    "admin_fleet.no_recent_contact": "Pas de contact récent",
    "admin_fleet.no_frames_yet": "Aucun cadre pour l’instant",
    "admin_fleet.register_a_frame_below_then_enter_the_code_shown_on":
        "Enregistrez un cadre ci-dessous, puis saisissez le code affiché sur son écran.",
    "admin_fleet.open_frame": "Ouvrir le cadre",
    "admin_fleet.reassign": "Réattribuer",
    "admin_fleet.retire": "Retirer",
    "admin_fleet.re_activate": "Réactiver",
    "admin_fleet.reassign_frame": "Réattribuer le cadre",
    "admin_fleet.retire_frame": "Retirer le cadre",
    "admin_fleet.re_activate_frame": "Réactiver le cadre",
    "admin_fleet.keep_frame": "Garder le cadre",
    "admin_fleet.new_owner": "Nouveau propriétaire",
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
        "Seul le propriétaire change. Rien n’est effacé.",
    "admin_fleet.the_current_owner": "Le propriétaire actuel",
    "admin_fleet.pair_a_frame": "Associer un cadre",
    "admin_fleet.enter_the_code_shown_on_the_frame_s_screen_and_choose":
        "Saisissez le code affiché sur l’écran du cadre et choisissez à qui il "
        "appartient.",
    "admin_fleet.pairing_code": "Code d’association",
    "admin_fleet.pair_owner": "Propriétaire",
    "admin_fleet.choose_an_owner_option": "Choisissez un propriétaire",
    "admin_fleet.pair_frame": "Associer le cadre",
    "admin_fleet.no_frame_is_waiting_for_a_code_register_one_first":
        "Aucun cadre n’attend de code. Enregistrez-en un d’abord.",
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
    "admin_fleet.register_a_frame": "Enregistrer un cadre",
    "admin_fleet.use_the_mac_and_secret_hash_printed_by_the_provisioning":
        "Utilisez l’adresse MAC et le hash du secret affichés par le script de "
        "provisionnement. Le secret lui-même n’est jamais saisi ici.",
    "admin_fleet.mac_address": "Adresse MAC",
    "admin_fleet.secret_hash_sha_256": "Hash du secret (SHA-256)",
    "admin_fleet.64_hex_characters": "64 caractères hexadécimaux",
    "admin_fleet.paste_the_sha_256_value_only":
        "Collez uniquement la valeur SHA-256. Tout ce qui n’est pas 64 "
        "caractères hexadécimaux est refusé.",
    "admin_fleet.hardware_label": "Type de matériel",
    "admin_fleet.register_frame": "Enregistrer le cadre",
    "admin_fleet.enter_a_valid_mac_address": "Saisissez une adresse MAC valide.",
    "admin_fleet.enter_the_64_character_hash": "Saisissez le hash de 64 caractères.",
    "admin_fleet.choose_the_hardware_type": "Choisissez le type de matériel.",
    "admin_fleet.choose_the_hardware_option": "Choisissez le type de matériel",
    "admin_fleet.flash_frame_paired": "Cadre associé",
    "admin_fleet.flash_frame_paired_detail":
        "{frame} appartient maintenant à {email}. Il affichera sa première "
        "image à la prochaine mise à jour.",
    "admin_fleet.flash_frame_registered": "Cadre enregistré",
    "admin_fleet.flash_frame_registered_detail":
        "Allumez-le. Il affichera un code d’association dans les 5 minutes.",
    "admin_fleet.flash_frame_duplicate":
        "Un cadre avec cette adresse est déjà enregistré.",
}
