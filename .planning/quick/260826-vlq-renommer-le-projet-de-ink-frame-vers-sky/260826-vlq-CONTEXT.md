# Quick Task 260826-vlq: Renommer le projet de Ink Frame vers SkyPane - Context

**Gathered:** 2026-08-26
**Status:** Ready for planning

<domain>
## Task Boundary

Renommer le projet de "Ink Frame" / "ink-frame" / "inkframe" vers "SkyPane" / "skypane", partout :
1. Repo GitHub `florianlepont/ink-frame` -> `florianlepont/skypane` (`gh repo rename`, mise à jour du remote `origin` local)
2. Dossier local `/Users/florian/Projects/ink-frame` -> `/Users/florian/Projects/skypane` (dernière étape, casse le cwd de la session courante)
3. Toute la documentation (CLAUDE.md, README.md, ARCHITECTURE.md, COMPLIANCE.md, .planning/PROJECT.md, .planning/ROADMAP.md, .planning/REQUIREMENTS.md, server/README.md, deploy/README.md, firmware/VENDOR.md, hardware docs, etc.)
4. Services systemd en production sur le VPS OVH réel (`ubuntu@vps-<id>.vps.ovh.net`, cf. `deploy/README.md`) : `inkframe-byos.service`, `inkframe-poll.service`/`.timer`, plus `deploy.sh`/`provision.sh` qui les référencent
5. Le firmware C (`firmware/main/state_machine.c`, `nvs_schema.h`, `app_main.c`, et tout autre fichier référençant "inkframe")

</domain>

<decisions>
## Implementation Decisions

### Convention de nommage (services systemd + NVS namespace)
- Garder la structure existante, changer uniquement le préfixe : `inkframe-byos.service` -> `skypane-byos.service`, `inkframe-poll.service`/`.timer` -> `skypane-poll.service`/`.timer`
- Le NVS namespace du firmware suit la même règle si littéralement `"inkframe"`

### Reflash firmware
- Le device physique tourne actuellement sur batterie, pas accessible en USB dans cette session
- Portée de cette tâche : mettre à jour le code firmware (identifiants/strings "inkframe" -> "skypane") et vérifier qu'il compile (`firmware/build.sh`), SANS reflasher
- Le reflash réel est explicitement différé — à faire par le développeur plus tard, quand le device peut être branché en USB
- Tant que le device n'est pas reflashé, il continue de tourner avec l'ancien firmware (ancien NVS namespace, anciens logs) contre le nouveau serveur renommé — c'est acceptable, le protocole HTTP entre device et serveur ne dépend pas du nom du service ni du NVS namespace

### Downtime en production
- Quelques minutes de coupure de service acceptables pendant le redéploiement (stop anciens services -> install nouveaux -> vérification santé)
- Pas besoin d'un mécanisme de bascule sans coupure (over-engineering pour un projet perso avec un seul device, cycle de poll de 30s)

### Claude's Discretion
- Remote git local : après le `gh repo rename`, mettre à jour l'URL du remote `origin` via `git remote set-url` (GitHub redirige aussi automatiquement l'ancienne URL, donc pas bloquant si oublié, mais à faire proprement)
- Renommage du dossier local : dernière étape de toute la tâche, une fois tout le reste (repo GitHub, docs, prod, firmware code) commité et poussé — annoncer clairement à l'utilisateur que la session actuelle devra être relancée depuis le nouveau chemin après ce `mv`
- Ordre d'exécution global recommandé : (a) docs + code firmware (commits locaux), (b) redéploiement prod (services systemd renommés + `deploy.sh`/`provision.sh` mis à jour), (c) `gh repo rename` + mise à jour remote, (d) push, (e) rename du dossier local en tout dernier
- Le nom "SkyPane" et sa casse dans le code (variables, macros C) suivent les conventions déjà en place dans chaque fichier (ex: majuscules pour les macros C, minuscules-avec-tirets pour les noms de service/fichiers)

</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches. L'utilisateur a explicitement choisi la portée complète (cosmétique + prod + firmware), pas seulement cosmétique, lors d'une question de cadrage préalable.

</specifics>

<canonical_refs>
## Canonical References

No external specs — requirements fully captured in decisions above.

</canonical_refs>
