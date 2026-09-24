# -*- coding: utf-8 -*-
"""companion/i18n_fr/common.py — French strings for the login page, the
404 page, the shared "Sign out" control (D-01/D-04/D-05,
20-01-PLAN.md Task 1), and — as of 22-08-PLAN.md Task 1 (D-06/B16) —
every flash-banner template in companion/app.py's FLASH_MESSAGES dict
and the two pre-session <title> literals ("Not Found", the login
shell's "Login - %s"). 37-05-PLAN.md Task 1 (SEC-03) adds the 403
page's two strings, the same pre-session shape as the 404 page above.

One sibling module of the companion/i18n_fr package (see that
package's __init__.py for the auto-merge/duplicate-key contract this
module participates in). Every key here is the exact English source
string a call site in companion/app.py or companion/layout.py passes
to companion.i18n.t() — including the "%d"/"%s"/"{n}"/"{s}"/"{key}"
placeholder shape, unchanged.

Copy follows D-09: sentence case, the typographic apostrophe (U+2019,
never a straight quote), and a non-breaking space (U+00A0) before
":" ";" "?" "!".

22-08-PLAN.md Task 1: two FLASH_MESSAGES values are deliberately
ABSENT here — "Poll triggered recently — try again in {n}s." (already
keyed in companion/i18n_fr/display.py, from the Frame strip's own
poll-cooldown copy) and "Test notification sent."/"Couldn't reach
that topic — check the URL." (already keyed in companion/i18n_fr/
notifications.py, from the Notifications card's own "Send a test"
outcomes) — the package's own auto-merge _build_catalog() raises
ValueError on a duplicate key across sibling modules, and all three
already have a live entry elsewhere, each predating this module's own
FLASH_MESSAGES coverage. companion.i18n.t() resolves them from their
existing home either way, since the merged CATALOG is one flat dict
keyed by the English string regardless of which sibling module
supplied it.
"""

CATALOG = {
    # --- Login page (companion/app.py's _login_body()) -----------------
    "Sign in to manage this device's settings.":
        "Connectez-vous pour gérer les réglages de cet appareil.",
    "Too many attempts — try again in %ds.":
        "Trop de tentatives — réessayez dans %d s.",
    "Password": "Mot de passe",
    "Sign in": "Se connecter",
    "Incorrect password. Try again.":
        "Mot de passe incorrect. Réessayez.",
    # 22-13-PLAN.md Task 2 (X3): the show-password toggle's two
    # accessible names. The toggle is icon-only, so these are the ONLY
    # names it ever has — an untranslated pair here would leave the
    # control anonymous in French, not merely awkward.
    "Show password": "Afficher le mot de passe",
    "Hide password": "Masquer le mot de passe",

    # --- The login shell's own <title> (companion/layout.py's
    #     login_shell(), 22-08-PLAN.md Task 1: the literal lives THERE,
    #     not in app.py — verified live 2026-09-12) --------------------
    "Login": "Connexion",

    # --- 404 page (companion/app.py's _not_found_page(), NOT_FOUND_TITLE
    #     / NOT_FOUND_PURPOSE_TEXT) -----------------------------------
    "Page not found.": "Page introuvable.",
    "The page you requested doesn't exist or may have moved.":
        "La page demandée n’existe pas ou a peut-être été déplacée.",
    "Back to Home": "Retour à l’accueil",
    # The 404 page's own <title> — a short form distinct from
    # NOT_FOUND_TITLE above (that one is the page heading's longer
    # sentence); the literal was "Not Found" (22-08-PLAN.md Task 1).
    "Not Found": "Introuvable",

    # --- 403 page (companion/app.py's _forbidden_page(), FORBIDDEN_TITLE
    #     / FORBIDDEN_PURPOSE_TEXT) — SEC-03 (37-05-PLAN.md Task 1) -----
    "Request refused": "Requête refusée",
    "This request came from another site, so it was refused. Open SkyPane directly and try again.":
        "Cette requête venait d’un autre site, elle a donc été refusée. Ouvrez SkyPane directement et réessayez.",

    # --- Shared footer control (companion/layout.py's
    #     _logout_form_html()) -----------------------------------------
    "Sign out": "Se déconnecter",

    # --- Flash banners (companion/app.py's FLASH_MESSAGES, resolved
    #     through _resolve_flash_text(), 22-08-PLAN.md Task 1: B16's
    #     own finding — no FR catalogue carried a single FLASH string
    #     before this plan) -------------------------------------------
    "Screen switched on — the frame will wake up and show a picture "
    "within about five minutes.":
        "Écran allumé — le cadre va se réveiller et afficher une image "
        "dans environ cinq minutes.",
    "Screen switched off — the frame will blank itself within about "
    "five minutes.":
        "Écran éteint — le cadre va s’effacer dans environ cinq "
        "minutes.",
    "Quiet hours turned on — applies the next time the frame wakes up.":
        "Heures calmes activées — s’applique au prochain réveil du "
        "cadre.",
    "Quiet hours turned off — applies the next time the frame wakes up.":
        "Heures calmes désactivées — s’applique au prochain réveil du "
        "cadre.",
    # 23-07-PLAN.md Task 2 (D2/CFG-36): the Diagnostic LED's own two
    # outcomes, worded on the Quiet-hours pair above rather than the
    # Screen pair — like quiet hours, the LED takes effect on the frame's
    # next wake rather than within about five minutes.
    "Diagnostic LED turned on — applies the next time the frame wakes up.":
        "LED de diagnostic allumée — s’applique au prochain réveil du "
        "cadre.",
    "Diagnostic LED turned off — applies the next time the frame wakes up.":
        "LED de diagnostic éteinte — s’applique au prochain réveil du "
        "cadre.",
    "Couldn't change that — please try again.":
        "Impossible de modifier ce réglage — réessayez.",
    "Saved — %s": "Enregistré — %s",
    "Couldn't save settings — please try again. If this keeps "
    "happening, check the companion service logs.":
        "Impossible d’enregistrer les réglages — réessayez. Si le "
        "problème persiste, consultez les journaux du service "
        "companion.",
    "Refreshing — the frame's new picture will appear on Home within a "
    "few seconds.":
        "Actualisation en cours — la nouvelle image du cadre "
        "apparaîtra sur Accueil dans quelques secondes.",
    "Poll trigger failed — please try again. If this keeps happening, "
    "check the companion service logs.":
        "Échec du déclenchement de la vérification — réessayez. Si le "
        "problème persiste, consultez les journaux du service "
        "companion.",
    "A poll is already in progress — try again in a moment.":
        "Une vérification est déjà en cours — réessayez dans un "
        "instant.",
    "Illustration replaced — the frame will use it next time it wakes and polls.":
        "Illustration remplacée — le cadre l’utilisera à son prochain "
        "réveil et à sa prochaine vérification.",
    "Couldn't use that image — upload a transparent PNG that's at "
    "least 1200 pixels wide and landscape (wider than tall).":
        "Impossible d’utiliser cette image — envoyez un PNG "
        "transparent d’au moins 1200 pixels de large, au format "
        "paysage (plus large que haut).",
    "Couldn't replace the illustration — please try again. If this "
    "keeps happening, check the companion service logs.":
        "Impossible de remplacer l’illustration — réessayez. Si le "
        "problème persiste, consultez les journaux du service "
        "companion.",
    "Airline name saved — the frame will pick it up next time it "
    "wakes and polls.":
        "Nom de compagnie enregistré — le cadre le récupérera à son "
        "prochain réveil et à sa prochaine vérification.",
    "Enter an airline name before saving.":
        "Saisissez un nom de compagnie avant d’enregistrer.",
    "That name's too long — airline names top out at 100 characters.":
        "Ce nom est trop long — les noms de compagnie sont limités à "
        "100 caractères.",
    "That name is reserved for the frame's own fallback artwork — "
    "try the airline's real name instead.":
        "Ce nom est réservé à l’illustration de repli du cadre — "
        "utilisez plutôt le vrai nom de la compagnie.",
    "That coverage gap isn't there anymore — check Health for "
    "current gaps.":
        "Cette lacune de couverture n’existe plus — consultez État "
        "pour les lacunes actuelles.",
    "The manual-resolution list is full (200 entries) — delete an "
    "old one before adding another.":
        "La liste des résolutions manuelles est pleine (200 entrées) "
        "— supprimez-en une avant d’en ajouter une autre.",
    "Couldn't save that resolution — the frame's state directory "
    "may not be writable.":
        "Impossible d’enregistrer cette résolution — le dossier "
        "d’état du cadre n’est peut-être pas accessible en écriture.",
    "Couldn't delete that entry — the frame's state directory may "
    "not be writable.":
        "Impossible de supprimer cette entrée — le dossier d’état du "
        "cadre n’est peut-être pas accessible en écriture.",
    "That name can't be used for an illustration — try a different "
    "spelling, or a name with letters and numbers.":
        "Ce nom ne peut pas être utilisé pour une illustration — "
        "essayez une autre orthographe, ou un nom avec des lettres et "
        "des chiffres.",
    "Rule added — the frame will use it next time it wakes and polls.":
        "Règle ajoutée — le cadre l’utilisera à son prochain réveil "
        "et à sa prochaine vérification.",
    "Updated the rule for {key} — it replaces the one that was "
    "there before, applied next time the frame wakes and polls.":
        "Règle mise à jour pour {key} — elle remplace la précédente "
        "et s’appliquera au prochain réveil et à la prochaine "
        "vérification du cadre.",
    "That doesn't match the selected kind's format — a callsign "
    "(e.g. AFR1234), an ICAO24 hex (e.g. 3944F2), or a 3-letter "
    "prefix (e.g. AFR).":
        "Cela ne correspond pas au format du type sélectionné — un "
        "indicatif (par ex. AFR1234), un hex ICAO24 (par ex. "
        "3944F2), ou un préfixe à 3 lettres (par ex. AFR).",
    "The rules list is full (200 entries) — delete an old one "
    "before adding another.":
        "La liste des règles est pleine (200 entrées) — supprimez-en "
        "une avant d’en ajouter une autre.",
    "Couldn't save that rule — the frame's state directory may not "
    "be writable.":
        "Impossible d’enregistrer cette règle — le dossier d’état du "
        "cadre n’est peut-être pas accessible en écriture.",
    "Rule deleted — the frame will stop using it next time it "
    "wakes and polls.":
        "Règle supprimée — le cadre cessera de l’utiliser à son "
        "prochain réveil et à sa prochaine vérification.",
    "Couldn't delete that rule — the frame's state directory may "
    "not be writable.":
        "Impossible de supprimer cette règle — le dossier d’état du "
        "cadre n’est peut-être pas accessible en écriture.",
    "Connected — {n} flight{s} from this calendar in the frame's "
    "current window.":
        "Connecté — {n} vol{s} de ce calendrier dans la fenêtre "
        "actuelle du cadre.",
    "Saved, but couldn't sync that calendar right now — check the "
    "URL and try again. The frame will keep retrying on its own "
    "schedule.":
        "Enregistré, mais impossible de synchroniser ce calendrier "
        "pour le moment — vérifiez l’URL et réessayez. Le cadre "
        "continuera de réessayer selon son propre calendrier.",
    "Calendar disconnected — the flights it supplied have been "
    "deleted from the server.":
        "Calendrier déconnecté — les vols qu’il fournissait ont été "
        "supprimés du serveur.",
    "Saved — a poll was already running, so this calendar will "
    "sync on the frame's next scheduled poll.":
        "Enregistré — une vérification était déjà en cours, ce "
        "calendrier se synchronisera donc à la prochaine vérification "
        "programmée du cadre.",
    "Calendar connected — {n} flights found.":
        "Calendrier connecté — {n} vols trouvés.",
    "Paste a valid calendar feed URL to connect one.":
        "Collez une URL de flux de calendrier valide pour en "
        "connecter un.",
    # T13 (22-15-PLAN.md Task 2, 22-UI-SPEC.md §1's copy table): the two
    # neutral states companion/static/freshness.js's refresh loop can be
    # in. Rendered onto <body> by companion/layout.py and read
    # client-side; the English forms are also the script's own
    # no-attribute fallbacks, which is why companion/test_i18n.py's
    # Check 6 requires these entries from the JS side as well.
    "Paused": "En pause",
    "Reconnecting…": "Reconnexion…",
}
