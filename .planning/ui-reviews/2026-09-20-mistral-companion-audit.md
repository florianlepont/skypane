# Audit Mistral du companion — 20 septembre 2026

## Provenance

Cet audit n'a pas été produit par le projet. Il a été écrit par « Vibe Code » (Vibe Nuage Agent, Mistral AI) et poussé directement sur `main` le 20 septembre 2026, commit `d288e27`, sans pull request ni relecture.

Il arrivait en trois fichiers sous `audits/` : une partie 2026 en deux morceaux et un prétendu audit de référence « 2024 ». Le présent document les remplace : tout ce qui suit est ce qui reste après vérification contre le code, et le répertoire `audits/` a été supprimé.

## Fiabilité

Trois réserves, qui expliquent pourquoi cet audit est condensé ici plutôt que conservé tel quel.

D'abord la ligne de base. Le fichier « 2024 » a été créé dans le même commit que les deux autres, et le premier commit du dépôt date du 2026-08-04 : il n'a jamais existé de code SkyPane en 2024, donc aucun audit de 2024. Toute la narration « évolution depuis 2024 », les notes chiffrées, les gains de points et la liste des « problèmes résolus depuis 2024 » sont une mise en scène et ont été retirées en bloc — avec les notes sur dix, les efforts en étoiles, et les métriques UX (satisfaction, taux d'erreur, temps par tâche) qui ne reposent sur aucune mesure.

Ensuite les chiffres, remesurés un par un. `companion/pages/config_page.py` fait 6 460 lignes, et non « 355 794 lignes » : l'audit a pris des octets pour des lignes, 356 Ko étant juste et sa conversion en lignes fausse. Les tests font 66 622 lignes sur 7 fichiers, et non « environ 85 000 ». Il y a 17 fichiers JavaScript, et non 14. En revanche `companion/static/style.css` fait bien 10 546 lignes et 506 Ko, et l'internationalisation compte bien 13 modules.

Enfin la méthode. L'audit ne mesure rien lui-même : aucun viewport, aucune hauteur de page, aucune cible tactile, aucune capture. Plusieurs de ses constats sont contredits par le code du dépôt, listés plus bas sous « Écarté ». Ce qui suit est ce qui survit à la relecture.

## Constats retenus

### Vols n'a pas de pagination

La page liste tous les vols sans découpage. Retenu parce que le constat est vérifiable et déjà mesuré ailleurs : l'audit du 17 septembre 2026 le classe P1, avec 36 cartes et une page de 6 710 px sur téléphone, et recommande 10 à 15 vols suivis d'un bouton d'affichage progressif. L'audit Mistral confirme ce constat sans y ajouter de mesure.

### Appareil et Affichage exposent trop de prose avant l'action

Formulé comme « interface un peu technique » pour Appareil, et trop d'explications pour Affichage. Retenu parce qu'il recoupe exactement le P1 « trop d'explications avant les actions » de l'audit du 17 septembre, qui relève deux écrans de lecture avant les deux réglages d'Appareil.

### Compagnies reste difficile à parcourir

Formulé comme « interface un peu complexe ». Retenu au titre de corroboration du P2 du 17 septembre : sur téléphone, la galerie des compagnies connues arrive après le titre, deux textes d'introduction, l'action d'édition et la section des compagnies non identifiées.

### Deux fichiers sont devenus monolithiques

`companion/pages/config_page.py` (6 460 lignes, 356 Ko) et `companion/static/style.css` (10 546 lignes, 506 Ko). Retenu comme dette de maintenabilité, pas comme défaut critique : aucun seuil n'a été fixé pour ce projet, aucune régression n'est attribuée à ces tailles, et un découpage n'apporte rien à l'utilisateur. À traiter quand une phase touche déjà largement l'un des deux, pas pour lui-même. La remarque voisine sur la duplication de motifs HTML relève du même sac, elle aussi sans mesure derrière elle.

### Peu d'états de chargement visibles — mineur, non vérifié

Trois occurrences seulement de `aria-busy`, spinner ou loading dans les assets statiques, et `quick-switch.js` procède par bascule optimiste. Retenu comme note mineure, à confirmer par une mesure réelle avant toute action : ce n'est pas un défaut établi.

## Ce qui fonctionne déjà bien

L'audit est juste sur les forces, et elles sont vérifiables dans le code :

- aucune dépendance externe ; serveur en bibliothèque standard Python, HTML rendu côté serveur, pas d'étape de build ;
- une seule source de navigation, `NAV_GROUPS`, rendue par `sidebar_nav()` en desktop et `_tab_bar_html()` en mobile, complétée par le panneau compte et préférences ;
- des tokens CSS — échelle d'espacement par pas de 4 px, quatre tailles de texte, tokens de mouvement — les thèmes clair et sombre, et `prefers-reduced-motion` respecté ;
- `companion/contrast_check.py`, qui impose les contrastes WCAG AA et une distance d'au moins 28 dE76 entre l'accent et les couleurs de statut ;
- une CSP en place, avec `script-src 'self'` et aucun script inline ;
- l'internationalisation FR et EN sur 13 modules ;
- la limitation des tentatives de connexion (`LoginThrottle`).

## Écarté

Ces constats de l'audit sont clos. Ils ne doivent pas être rouverts sans élément nouveau.

| Constat de l'audit | Pourquoi il est écarté |
|---|---|
| « Pas de rate limiting » | Faux : `companion/auth.py` implémente `LoginThrottle`, avec un seuil d'échecs et un verrouillage de 300 s. |
| « CSP trop permissive, retirer `unsafe-inline` » | `script-src 'self'` ne porte déjà aucun `unsafe-inline` ; seul `style-src` en a un, documenté comme délibéré dans `companion/app.py` pour sept styles inline. |
| « Pas de focus trap pour les modales » | `panel-lookup.js` documente l'emploi de l'élément natif `<dialog>` précisément pour ses sémantiques natives de fermeture au clavier, d'arrière-plan et de piégeage du focus. Choix assumé. |
| « Pas de tooltips » | Quinze attributs `title` existent dans `layout.py` et les pages. |
| « Peu de régions `aria-live` » | Dix occurrences dans le rendu Python ; l'affirmation n'est étayée par aucun relevé. |
| « ES5 seulement, passer à ES6+ » | Le sous-ensemble ES5 est une contrainte documentée du projet — pas d'étape de build, pas de bundler — rappelée en tête de plusieurs scripts. Refus assumé, pas défaut. |
| « Breadcrumbs partiellement implémentés » | Aucun fil d'Ariane n'existe dans `companion/`. L'audit se contredit d'ailleurs lui-même en déplorant ailleurs leur absence complète. |
| « Pas de breadcrumbs », « pas de bouton Retour » | Sans objet : six pages de premier niveau, aucune imbrication, barre latérale permanente en desktop et barre d'onglets en mobile. |
| « Health remonté dans la barre mobile » et « bouton More pour Health et Device » | Les deux affirmations se contredisent dans le même document ; aucune n'est retenue. |
| Toute ligne « problème résolu depuis 2024 » | Ligne de base inventée, voir « Fiabilité ». |
| « Pas de raccourcis clavier » | Vrai, mais sans valeur ici : application de réglages sur six pages, avec navigation permanente. |
| « Adopter BEM », « JSDoc ou TypeScript », « tests unitaires JS », « bibliothèque utilitaire JS », « moderniser le design » | Recommandations génériques, sans mesure ni symptôme observé dans ce dépôt. |

## Suite

Les constats retenus ne justifient pas une phase à eux seuls. Vols, la prose d'Appareil et d'Affichage, et l'ordre de Compagnies sont déjà les trois premières lignes de l'ordre recommandé par l'audit du 17 septembre 2026 (`.planning/ui-reviews/2026-09-17-companion-ui-ux-audit.md`, relevé mesuré, non versionné à ce jour) : ils rejoignent cet arriéré-là au lieu d'en ouvrir un second.

La dette de maintenabilité des deux gros fichiers reste hors de cet arriéré d'interface, à traiter par opportunité.
