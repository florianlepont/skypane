# Audit UI/UX du companion — 17 septembre 2026

## Verdict

Le companion possède déjà une identité visuelle cohérente, une bonne hiérarchie de cartes et un rendu clair/sombre solide. Le problème principal n'est plus un manque de finition graphique générale : c'est la densité. Sur téléphone, plusieurs écrans demandent trop de défilement, exposent trop d'explications avant l'action et conservent quelques contrôles trop compacts.

Deux défauts visuels concrets ont été corrigés pendant l'audit :

1. le cadran des heures calmes affichait ses valeurs internes en minutes (`480 → 1080`), tout en laissant les heures visibles à côté des champs sur les anciennes valeurs ;
2. le libellé `Compagnies` était tronqué dans la barre d'onglets mobile.

## Périmètre vérifié

- Routes : Accueil, Affichage, Vols, Compagnies, État et Appareil.
- Viewports : 390 × 844 px et 1280 × 900 px ; contrôle complémentaire de la navigation à 360 px.
- Thèmes : clair et sombre.
- Interactions : connexion, changement de thème, préréglages du cadran des heures calmes, sauvegarde automatique et persistance après rechargement.
- Contrôles techniques : largeur du document, éléments peignant hors du viewport, dimensions des contrôles, erreurs console et tests Python ciblés.

Résultat transversal : aucun débordement horizontal global n'a été détecté sur les six routes, en mobile ou en desktop. Aucune erreur console n'a été relevée.

## Mesures principales

| Écran | Hauteur mobile 390 px | Hauteur desktop 1280 px | Lecture |
|---|---:|---:|---|
| Accueil | 2 807 px | 1 640 px | Propre, mais les états vides ajoutent beaucoup de texte |
| Affichage | 3 556 px | 2 608 px | Trop long sur mobile ; nombreuses sections et explications |
| Vols | 6 710 px | 2 537 px | Point de friction majeur ; 36 cartes dans la fixture |
| Compagnies | 2 719 px | 1 568 px | Le contenu principal arrive tard sur mobile |
| État | 2 927 px | 1 894 px | Dense, mais structure globalement lisible |
| Appareil | 1 866 px | 1 476 px | Peu de réglages, beaucoup de prose |

Ces hauteurs ne sont pas des seuils de conformité. Elles rendent visible le rapport entre le nombre d'actions utiles et la quantité de page à parcourir.

## Constats priorisés

### P0 — Corrigé : incohérence du cadran des heures calmes

Après un préréglage, l'arc et les champs passaient bien à `08:00` et `18:00`, mais la légende affichait `480 → 1080` et les valeurs normalisées restaient à `23:00` et `07:00`. La cause était un rendu direct de la valeur numérique interne au lieu d'utiliser le codec `HH:MM` du champ.

Le correctif fait maintenant suivre les trois surfaces visibles par la même conversion. Le séparateur de durée disparaît également lorsque la durée est temporairement vide pendant une interaction.

### P1 — Corrigé : `Compagnies` tronqué dans la navigation mobile

À 390 px, le libellé était rendu comme `Compagn...`. L'inset horizontal du pill laissait 62 px pour un mot qui en demande 65. Le nouvel inset laisse le libellé complet à 360 px et à 390 px, sans réduire la zone tactile de l'onglet.

### P1 — Vols est beaucoup trop long sur téléphone

La fixture réaliste produit 36 cartes et une page de 6 710 px. L'horodatage et l'indicatif se disputent aussi la même ligne dans certaines cartes, ce qui provoque des retours visuellement maladroits.

Recommandation : afficher 10 à 15 vols, puis un bouton `Afficher plus`; garder le résumé d'une carte sur une seule grille stable et placer les détails secondaires dans son disclosure. Le filtre doit rester immédiatement visible.

### P1 — Trop d'explications avant les actions

Les pages Affichage et Appareil répètent souvent trois idées : ce que fait le réglage, quand il s'applique et son impact. La page Appareil est l'exemple le plus net : deux réglages simples occupent plus de deux écrans avant même les diagnostics.

Recommandation éditoriale : une phrase courte sous le titre de carte, puis les précisions rares dans `Comment ça marche`. Exemples de direction :

- `Réglages techniques du cadre.` pour l'introduction Appareil ;
- `S'allume brièvement au réveil du cadre.` pour la LED ;
- `Plus court : données plus fraîches, batterie plus sollicitée.` pour l'intervalle ;
- `Le cadre dort pendant cette plage.` pour les heures calmes.

### P1 — Plusieurs cibles tactiles restent trop petites

Mesures observées sur téléphone : boutons de préréglage et d'action à 36 px de haut, champ de filtre à 32 px, contrôle `Effacer` autour de 18 px. Certains boutons icône possèdent une zone de hit-test synthétique de 44 px et ne sont donc pas concernés.

Recommandation : porter à 44 px les actions autonomes sur mobile, en priorité `Effacer`, les préréglages d'heures calmes, `Connecter le calendrier`, `Envoyer un test` et l'actualisation manuelle. Le gain doit venir de la zone cliquable et du padding, pas d'un grossissement visuel systématique.

### P2 — Valeur horaire dupliquée dans les navigateurs déjà en 24 h

Les champs natifs affichent par exemple `23:00`, puis leur sibling de compatibilité réaffiche `23:00`. Ce sibling protège les navigateurs qui imposent un rendu 12 h malgré la langue, mais devient du bruit sur les navigateurs corrects.

Recommandation : conserver le fallback sans JavaScript, puis le masquer au chargement seulement si le champ natif restitue déjà sans ambiguïté le format 24 h.

### P2 — Compagnies retarde sa galerie principale

Sur mobile, le titre, deux textes d'introduction, l'action d'édition, la section des compagnies non identifiées et le filtre précèdent la grille des compagnies connues. L'utilisateur venu vérifier une illustration doit faire défiler avant de voir le contenu principal.

Recommandation : placer filtre + galerie connue juste après le titre ; déplacer les compagnies non identifiées et l'édition dans une section secondaire clairement annoncée.

### P2 — État est lisible mais éditorialement chargé

La bannière d'alerte, les chips, les cartes et les titres longs s'accumulent. Le titre `Tendance de la batterie — 3 derniers mois, moyenne quotidienne` mérite d'être raccourci visuellement, par exemple `Batterie · 3 mois`, avec la précision dans une légende.

## Ce qui fonctionne déjà bien

- Palette, typographie et surfaces cohérentes en clair et sombre.
- Hiérarchie visuelle forte entre titre de page, groupes et cartes.
- Navigation desktop stable et barre mobile toujours accessible.
- Aucun overflow horizontal sur le corpus vérifié.
- États de focus, contrastes et zones tactiles synthétiques déjà largement couverts par les tests du projet.
- Les réglages essentiels utilisent des contrôles compréhensibles et la sauvegarde automatique est perceptible.

## Ordre recommandé pour la suite

1. Réduire la page Vols : pagination progressive et grille mobile stable.
2. Faire une passe éditoriale Appareil + Affichage avec une limite d'une phrase par description visible.
3. Remonter la galerie connue sur Compagnies.
4. Porter les actions autonomes mobiles à 44 px.
5. Supprimer conditionnellement le doublon visuel des heures.
6. Refaire la matrice de contrôle à 360 / 390 / 768 / 1280 px, en français et en anglais, clair et sombre.

## Garde-fous d'acceptation

- aucun `scrollWidth` supérieur au viewport ;
- aucun libellé de navigation ellipsé à partir de 360 px ;
- aucune action autonome sous 44 px sur téléphone ;
- aucune valeur interne technique visible dans l'UI ;
- descriptions visibles limitées à deux lignes mobiles dans le cas général ;
- les actions principales apparaissent avant les explications détaillées ;
- rendu identique fonctionnellement avec JavaScript bloqué, hors améliorations explicitement progressives.
