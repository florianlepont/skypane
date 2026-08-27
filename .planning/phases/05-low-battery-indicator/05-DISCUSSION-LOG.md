# Phase 5: Battery Life & Low-Battery Indicator - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-08-27
**Phase:** 05-low-battery-indicator (covers the low-battery-indicator plan specifically, not 05-01)
**Areas discussed:** Seuil et politique de déclenchement, Traitement visuel sur le poster verrouillé, Périmètre firmware (lecture ADC réelle), Interaction avec la couleur d'état DEPARTING/ARRIVING

---

## Seuil et politique de déclenchement (threshold policy)

| Option | Description | Selected |
|--------|-------------|----------|
| Verrouiller une estimation maintenant | Basée sur la courbe LiPo typique + le cutoff check-battery (3400mV) | ✓ |
| Laisser explicitement TBD | Infra câblée, valeur exacte laissée en placeholder | |

**User's choice:** Verrouiller une estimation maintenant.

| Option | Description | Selected |
|--------|-------------|----------|
| mV brut | Comparaison directe, cohérent avec check-battery | ✓ |
| Pourcentage dérivé | Nécessite une courbe de décharge pas encore mesurée | |

**User's choice:** mV brut.

**Follow-up:** valeur exacte proposée (3500 mV, marge au-dessus du cutoff 3400mV "vide") — confirmée telle quelle ("Oui, 3500 mV").

---

## Traitement visuel sur le poster verrouillé

| Option | Description | Selected |
|--------|-------------|----------|
| Petit accent texte, fond inchangé | Le fond Bleu/Vert reste, seul un élément passe en Jaune | ✓ |
| Fond entier Jaune | Rupture visuelle forte, perd le signal departing/arriving | |

**User's choice:** Petit accent, fond inchangé.

| Option | Description | Selected |
|--------|-------------|----------|
| Réutilise l'étiquette d'état (top-left) | Pas de nouvelle zone | |
| Nouvelle zone dédiée | — | (corrigé par l'utilisateur, voir notes) |

**User's choice (free text):** "Le texte DEPARTING ARRIVING n'est pas une étiquette d'état. Il faut une nouvelle zone à insérer, surement en bas à droite ou en bas à gauhe" — correction de la question initiale, qui confondait à tort le label d'état avec l'indicateur batterie.

**Notes:** Claude a proposé bas-à-gauche (seul espace libre, symétrique à la carte previous-flight en bas-à-droite) — confirmé.

| Option | Description | Selected |
|--------|-------------|----------|
| N'apparaît que si batterie faible | Même principe que la carte previous-flight (D-25) | ✓ |
| Toujours présente | Zone réservée en permanence | |

**User's choice:** N'apparaît que si batterie faible.

**Notes:** Question de cohérence (fond Bleu/Vert inchangé) initialement formulée en termes de "texte" — l'utilisateur a corrigé : "je confirme, mais tu me parles de texte alors que je pensais à un icône batterie tout simplement. même pas besoin d'être jaune." Ceci a rouvert le traitement visuel : icône plutôt que texte, couleur Blanc/Ivoire plutôt que Jaune (D-12 de 03-CONTEXT.md explicitement remis en cause).

**Sketch demandé par l'utilisateur** ("fais moi un sketch") — trois variantes générées et rendues contre la vraie palette/police/mise en page (`battery_icon_sketch.png`, `battery_icon_zoom.png`): A (icône seule, taille moyenne), B (icône + texte "LOW"), C (icône seule, plus grande).

**User's choice:** "icone seule, avec la taille du B" — combine le style de A (pas de texte) avec la taille de B (plus petite que C).

---

## Périmètre firmware (lecture ADC réelle)

| Option | Description | Selected |
|--------|-------------|----------|
| Tout maintenant | Firmware + serveur + vérification device réel | ✓ |
| Serveur/affichage seulement | ADC réel reporté à un plan séparé | |

**User's choice:** Tout maintenant.

**Notes:** Première formulation de la question ("je comprends en quoi consiste la première étape") ambiguë — reformulée en langage plus simple après que l'utilisateur a signalé ne pas comprendre ("je ne comprends pas ¨"), puis confirmée sans ambiguïté.

---

## Interaction avec la couleur d'état DEPARTING/ARRIVING

| Option | Description | Selected |
|--------|-------------|----------|
| Fond Bleu/Vert inchangé | Coexistence des deux signaux | ✓ |
| Reconsidérer | Retour sur le choix précédent | |

**User's choice:** Confirmé (fond inchangé), avec la correction texte→icône notée ci-dessus dans la même réponse.

---

## Claude's Discretion

- Position/taille exacte en pixels de l'icône (bornée par "bas-gauche, taille moyenne" — le sketch sert de référence, pas de spec verrouillée)
- Style exact du glyphe batterie (épaisseur de trait, coins, remplissage fixe vs proportionnel à la vraie lecture)
- Hystérésis/debounce autour du seuil 3500mV (non soulevé par l'utilisateur, ajouté par bonne pratique)
- Plomberie interne (comment la valeur mV circule du header HTTP jusqu'au rendu)
- Approche ADC/GPIO exacte sur le XIAO ESP32-S3 Plus (question de recherche, aucune doc existante dans le repo)

## Deferred Ideas

- Jauge batterie proportionnelle/vivante (pourcentage, jours restants) — non demandé, DEVICE-04 est satisfait par un glyphe fixe. Noté pour une future interface web compagnon (CFG-03, déjà seedée le 2026-08-27).
- Seuil définitif basé sur la vraie courbe de décharge — dépend de 05-01 Tâches 2-3, pas encore fait. Le seuil de 3500mV verrouillé ici est une estimation raisonnée, pas une mesure.
