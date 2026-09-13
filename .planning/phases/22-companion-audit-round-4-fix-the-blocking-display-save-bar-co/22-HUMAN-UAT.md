---
status: partial
phase: 22-companion-audit-round-4-fix-the-blocking-display-save-bar-co
source: [22-AUDIT.md, 22-VALIDATION.md, 22-01..22-16-SUMMARY.md]
started: 2026-09-13T08:19:00+00:00
updated: 2026-09-13T08:19:00+00:00
---

## Current Test

[awaiting human testing — one automated failure found first, see Issues]

## Automated visual sweep (done by Claude, not pending)

Six pages × two widths (1280 / 390 px) × light and dark, driven through a real
Chromium against a seeded state directory, logged in through the real form.
Measured `scrollWidth` against the viewport on every combination.

| Result | Detail |
|---|---|
| 23 of 24 clean | No horizontal overflow on Vols, Affichage, Compagnies, État or Connexion at either width, in either theme |
| **1 failure** | **Accueil overflows horizontally at 390 px — `scrollWidth` 411 px against a 390 px viewport, in both themes** |

Bottom tab bar checked separately and correct: `position: fixed`, 57 px tall,
bottom edge at 844 px = the viewport's own height. (It appears mid-page in a
full-page screenshot; that is a capture artefact of fixed positioning, not a bug.)

## Issues

### I1 — Accueil scrolls sideways on a phone (regression against this phase's own standard)

**Found by:** automated sweep above, confirmed by DOM measurement and screenshot.

**Symptom:** at 390 px the Accueil page is 411 px wide, so the phone scrolls
sideways. In « Vols récents », all five rows show their relative age
(`(il y a 42 j)`) cut off at the right edge.

**Cause, measured not guessed:** `.recent-flight__time` is `white-space: nowrap`
inside a 308 px `.recent-flight` grid. Its own box is 93 px wide and ends at
x=349 — inside the card — but its inline content cannot wrap, so the
`.time-value__age` child paints out to x=411, past the card and past the
viewport. Present in French (411 px) and English (408 px) alike, so it is the
`nowrap` and the column width, not a translation length.

**Scope:** this is Accueil's share of B11, the defect 22-09 / 22-11 / 22-12 each
measured and closed on their own pages. Accueil's `nowrap` came from 22-07
("one line for the recent-flight time"); no plan measured Accueil's
`scrollWidth` at 390 px afterwards.

**Status:** routed to a fix; not left for the developer to find on a real phone.

## Tests

### 1. Sur un vrai téléphone, faire défiler Accueil, Vols, Affichage, Compagnies et État de haut en bas (X9, B11, rendu réel)
expected: Aucun défilement horizontal nulle part ; la barre d'onglets du bas reste collée en bas sous le pouce, au-dessus de la barre d'adresse, et l'encoche / la zone sûre ne la coupe pas
result: [pending]

### 2. Sur téléphone, appuyer sur « Plus » dans la barre d'onglets, puis sur chaque onglet (X9, T5)
expected: La feuille « Plus » s'ouvre vers le haut sans pousser la page ; chaque onglet mène à la bonne page ; l'onglet actif est visiblement distinct ; le point d'alerte de santé reste visible quand la feuille est fermée
result: [pending]

### 3. Sur la page de connexion, téléphone et PC, taper un mauvais mot de passe puis utiliser l'œil « afficher le mot de passe » (X3)
expected: Champ et bouton font la même largeur et 44 px de haut, l'un au-dessus de l'autre sur téléphone ; l'erreur est annoncée ; l'œil révèle et masque. Avec JavaScript désactivé, l'œil n'apparaît pas du tout (il ne doit jamais être là sans rien faire)
result: [pending]

### 4. Cliquer FR puis EN sur le sélecteur de langue et laisser le pointeur immobile (B7)
expected: Après le rechargement, le libellé survolé reste lisible — pas de texte qui disparaît dans son propre fond
result: [pending]

### 5. Éteindre l'écran depuis la bande Cadre sur le vrai cadre, et chronométrer (D-04, CFG-27)
expected: Le délai annoncé par la phrase calculée correspond à ce qui se passe vraiment — c'est la seule affirmation de cette phase que seul le vrai matériel peut confirmer
result: [pending]

### 6. Laisser passer une vraie nuit avec les heures calmes actives, et regarder Accueil / État le matin (X2, CFG-26)
expected: Aucun état « en retard » ou d'avertissement pendant la fenêtre calme ; la prochaine mise à jour annoncée correspond à la fin de la fenêtre
result: [pending]

### 7. Relire la table de mesures de 22-AUDIT.md à 1280 px et 390 px, clair et sombre, FR et EN (CFG-30)
expected: Chaque ligne de la table correspond à ce qui est à l'écran — sauf X6, dont la cible de hauteur de page est explicitement NON atteinte (2389 px contre 2000 px ; le reste est la grille de pastilles, reportée en phase 23), et le séparateur de jour des Vols, qui affiche le mois abrégé (« 26 août ») et non le mois complet prévu par la spec
result: [pending]

## Summary

Automated verification is complete and green apart from one real defect this
sweep found: 16/16 plans, CFG-25..CFG-31 ticked, CI runs 176–192 all green with
the browser harness genuinely running (22 checks, 40.4 s, the slowest file in the
suite), full suite at 93 % coverage against a floor of 83, ruff clean, and no
temporary test allowance left standing.

One automated failure (I1, Accueil's horizontal overflow at 390 px) was found
during this pass and is being fixed rather than handed over.

Seven tests remain for the developer: the real-device and real-hardware checks
that no harness can stand in for, plus the visual re-read of the audit's own
measurement table.
