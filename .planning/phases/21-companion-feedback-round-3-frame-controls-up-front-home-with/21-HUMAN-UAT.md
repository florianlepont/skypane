---
status: partial
phase: 21-companion-feedback-round-3-frame-controls-up-front-home-with
source: [21-VERIFICATION.md, 21-REVIEW.md]
started: 2026-09-12T12:57:48+00:00
updated: 2026-09-12T12:57:48+00:00
---

## Current Test

[awaiting human testing]

## Tests

### 1. Sur l'Accueil et sur Affichage, appuyer sur « Éteindre » puis « Allumer » dans la bande Cadre, puis « Activer » / « Désactiver » les heures calmes (D-01, D-02, R-02)
expected: Chaque appui revient sur la page où il a été fait (Accueil reste Accueil, Affichage reste Affichage) avec un bandeau de confirmation ; le rappel « Écran … · Heures calmes … » dans la navigation change en même temps
result: [pending]

### 2. Regarder l'Accueil sur le téléphone et sur le PC : bande Cadre, trois tuiles, image et vols récents (D-04, D-05)
expected: La prochaine mise à jour est le texte le plus gros de la bande ; les trois tuiles Cadre / Batterie / Données de vol sont lisibles ; sur PC l'image et les vols récents sont côte à côte, sur téléphone empilés, sans texte coupé ni chevauchement
result: [pending]

### 3. Sur Affichage → Couleurs du cadre, cliquer chaque ligne (Départs, Arrivées, Vols du calendrier, Règles par vol), choisir une pastille, puis Enregistrer ; refaire avec JavaScript désactivé (D-06..D-12, R-05)
expected: L'aperçu et la grille suivent la ligne cliquée ; « Comme les départs » remet Arrivées / Calendrier sur le thème des départs après Enregistrer ; sans JavaScript les quatre blocs sont visibles et se sauvegardent quand même ; la ligne « Règles par vol » montre la liste et le petit formulaire
result: [pending]

### 4. Au clavier seulement (Tab / flèches), parcourir les quatre lignes de Couleurs du cadre et le bouton « Plus » du tableau des vols (21-REVIEW.md CR-01)
expected: Un anneau de focus visible sur la ligne active ; les flèches changent la ligne sélectionnée ; « Plus » ouvre la ligne de détail et l'annonce (aria-expanded)
result: [pending]

### 5. Connecter un vrai flux iCal sur Affichage → Calendrier, puis utiliser « Remplacer l'URL du flux » et le petit bouton gris « Déconnecter » (D-13, D-14, R-10)
expected: Une seule tuile : état + URL masquée (hôte seulement, jamais le lien complet) ; « Remplacer » ouvre le champ sur place ; « Déconnecter » demande confirmation avant d'agir
result: [pending]

### 6. Ouvrir Vols sur le PC (fenêtre ≈ 1280 px) en français puis en anglais, filtrer, et déplier « Plus » sur deux lignes (D-15, D-16)
expected: Aucune barre de défilement horizontale ; le filtre masque aussi la ligne de détail d'une ligne filtrée ; le détail montre hex, horodatage ISO, piste et bouton Copier ; sur téléphone les cartes n'ont pas changé
result: [pending]

### 7. Vérifier le pied de navigation et la page État (D-17, D-18)
expected: Plus de sélecteur Simple / Complet (FR · EN et Auto / Light / Dark restent) ; plus de bouton « Suspendre les mises à jour » sur État ; le compte à rebours et le graphique de batterie fonctionnent, avec des mois et un relevé en français
result: [pending]

### 8. Sur Compagnies, nommer une compagnie non identifiée et envoyer une image à l'étape B sans passer par « Modifier les images » (D-19, D-20)
expected: La zone d'envoi est proposée directement ; « Modifier les images » ne sert plus qu'à remplacer / supprimer les images existantes
result: [pending]

## Summary

8 tests pending — the browser-only checks of phase 21 (real device switches, keyboard focus, native confirm, real iCal feed, real upload). Everything automated is green: 21-VERIFICATION.md 10/10, 21-REVIEW.md resolved, full suite apart from the five documented root-sandbox checks, ruff clean, FR/EN sweep at 1280/390 px clean.
