---
status: partial
phase: 22-companion-audit-round-4-fix-the-blocking-display-save-bar-co
source: [22-AUDIT.md, 22-VALIDATION.md, 22-01..22-16-SUMMARY.md]
started: 2026-09-13T08:19:00+00:00
updated: 2026-09-13T08:19:00+00:00
---

## Current Test

Tests 2, 3, 4, 7 pass. Test 1 failed — see I2. Tests 5 and 6 deferred (developer not in front of the frame).

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

**Cause — my first diagnosis was right in spirit and wrong in mechanism; the
corrected one:** `.recent-flight__time` carried `max-width: 60%`. It sits in
`.recent-flight`'s third, content-sized `auto` track, so that track resolves to
the item's own max-content width — and a percentage cap then resolves against
that same content-derived width, clamping the box to 60 % of exactly the content
it was meant to bound (clientWidth 88 px against scrollWidth 147 px in English,
93 px against 155 px in French — the ratio is 0.6 at every width from 320 px to
1440 px). Under `white-space: nowrap` nothing can reflow into the smaller box,
so the other 40 % paints outside it. I had blamed the `nowrap` and the column
width; in fact the column sized correctly and the cap forbade the item from
occupying the column it had already sized.

**It was never phone-only.** At 1280 px the age still paints outside its row
(right edge 1253 against a row ending at 1191) — it just stays inside the wider
viewport, so no scrollbar appears. That is why nine plans missed it: the desktop
half is invisible to a `scrollWidth` check.

**Scope:** this is Accueil's share of B11, the defect 22-09 / 22-11 / 22-12 each
measured and closed on their own pages. Accueil's `nowrap` came from 22-07
("one line for the recent-flight time"); no plan measured Accueil's
`scrollWidth` at 390 px afterwards.

**Status: FIXED** — quick task `260913-bjy`, commits `6a6fda2` / `2de7f0c`.
The fix is one deleted declaration (`max-width: 60%`); `white-space: nowrap`,
`justify-self`, `text-align` and the markup are untouched, so 22-07's one-line
intent is preserved rather than reverted. A wrapping treatment was measured
first and produced byte-identical numbers at every width — the `auto` track
always grows to max-content before `minmax(0, 1fr)` yields, so it would have
shipped inert; it was not added.

`companion/test_browser_ux.py` gains a check (22 → 23) that measures every
element against the viewport AND every `.recent-flights` descendant against its
own row box, in both languages, at 390 px and 1280 px — the row-box half is the
only assertion that can see the desktop escape. Mutation-tested twice, once by
the executor and once independently by me: restoring the declaration gives 22/23
with this check the sole failure; removing it gives 23/23.

## Tests

### 1. Sur un vrai téléphone, faire défiler Accueil, Vols, Affichage, Compagnies et État de haut en bas (X9, B11, rendu réel)
expected: Aucun défilement horizontal nulle part ; la barre d'onglets du bas reste collée en bas sous le pouce, au-dessus de la barre d'adresse, et l'encoche / la zone sûre ne la coupe pas
result: **FAIL** — défilement horizontal dans « Voir 20 relevés » sur État (2026-09-13, developer). Reproduit et diagnostiqué : voir I2.

### 2. Sur téléphone, appuyer sur « Plus » dans la barre d'onglets, puis sur chaque onglet (X9, T5)
expected: La feuille « Plus » s'ouvre vers le haut sans pousser la page ; chaque onglet mène à la bonne page ; l'onglet actif est visiblement distinct ; le point d'alerte de santé reste visible quand la feuille est fermée
result: **PASS** (2026-09-13, developer)

### 3. Sur la page de connexion, téléphone et PC, taper un mauvais mot de passe puis utiliser l'œil « afficher le mot de passe » (X3)
expected: Champ et bouton font la même largeur et 44 px de haut, l'un au-dessus de l'autre sur téléphone ; l'erreur est annoncée ; l'œil révèle et masque. Avec JavaScript désactivé, l'œil n'apparaît pas du tout (il ne doit jamais être là sans rien faire)
result: **PASS** (2026-09-13, developer)

### 4. Cliquer FR puis EN sur le sélecteur de langue et laisser le pointeur immobile (B7)
expected: Après le rechargement, le libellé survolé reste lisible — pas de texte qui disparaît dans son propre fond
result: **PASS** (2026-09-13, developer)

### 5. Éteindre l'écran depuis la bande Cadre sur le vrai cadre, et chronométrer (D-04, CFG-27)
expected: Le délai annoncé par la phrase calculée correspond à ce qui se passe vraiment — c'est la seule affirmation de cette phase que seul le vrai matériel peut confirmer
result: [deferred] — à valider quand le développeur sera devant le cadre

### 6. Laisser passer une vraie nuit avec les heures calmes actives, et regarder Accueil / État le matin (X2, CFG-26)
expected: Aucun état « en retard » ou d'avertissement pendant la fenêtre calme ; la prochaine mise à jour annoncée correspond à la fin de la fenêtre
result: [deferred] — à valider quand le développeur sera devant le cadre

### 7. Relire la table de mesures de 22-AUDIT.md à 1280 px et 390 px, clair et sombre, FR et EN (CFG-30)
expected: Chaque ligne de la table correspond à ce qui est à l'écran — sauf X6, dont la cible de hauteur de page est explicitement NON atteinte (2389 px contre 2000 px ; le reste est la grille de pastilles, reportée en phase 23), et le séparateur de jour des Vols, qui affiche le mois abrégé (« 26 août ») et non le mois complet prévu par la spec
result: **PASS** (2026-09-13, developer)

## Summary

Automated verification is complete and green apart from one real defect this
sweep found: 16/16 plans, CFG-25..CFG-31 ticked, CI runs 176–192 all green with
the browser harness genuinely running (22 checks, 40.4 s, the slowest file in the
suite), full suite at 93 % coverage against a floor of 83, ruff clean, and no
temporary test allowance left standing.

One automated failure (I1, Accueil's horizontal overflow at 390 px) was found
during this pass and is now **fixed and pinned** — and it turned out to be wider
than the phone: the same cap was painting outside the card on the desktop too,
where no scrollbar could reveal it.

Seven tests remain for the developer: the real-device and real-hardware checks
that no harness can stand in for, plus the visual re-read of the audit's own
measurement table.

### I2 — « Voir 20 relevés » scrolls sideways on a phone (PRE-EXISTING, not caused by phase 22)

**Found by:** the developer, test 1, 2026-09-13. Reproduced and measured here.

**Symptom:** on État, opening the « Voir 20 relevés » disclosure gives the readings
table its own horizontal scroll at 390 px. The page itself does not scroll —
`documentElement.scrollWidth` stays 390 — so every page-level check in this phase
was blind to it, including my own 24-combination sweep: **the sweep never opened the
disclosure.**

**Measured:** wrapper `.data-table-wrap` clientWidth **308 px**; table **432 px**
(FR) / 369 px (EN) under `min-width: max-content`. Column 1 « Horodatage » is
**302 px** holding `31 juil. 08:00 (il y a 44 j)`; column 2 « Batterie (mV) » is
130 px. 302 + 130 = 432 against 308 — it overflows by 124 px and the wrapper
scrolls. The cell's own `white-space` is `normal`, so it *could* wrap; the table's
`min-width: max-content` floor is what forbids it.

**Not a phase-22 regression — verified, not assumed.** I built a worktree at the
merge base (`541d19c`) and compared `concise_timestamp_html()`'s visible output
across the boundary with identical inputs:

    PRE-22  fr '31 juil. 08:00 (il y a 44 j)'      POST-22 fr '31 juil. 08:00 (il y a 44 j)'
    PRE-22  en '31 Jul 08:00 (44d ago)'            POST-22 en '31 Jul 08:00 (44d ago)'

Byte-identical. 22-06 changed this timestamp's `title` attribute (invisible) and its
timezone handling, never the visible string. The overflow predates the phase.

**Same cause as B12, third table.** 22-12 measured exactly this
(`min-width: max-content` sizing every column to its content) and fixed the registry
table by stacking its merged cells. That rule's own comment says the treatment is
"NOT license to stack any other merged cell for consistency… applied to the second
table in this app that **demonstrably has it**". There is now a demonstration for a
third, with its own numbers — so this is the same local fix for the same measured
cause, not a consistency copy.

**Status:** routed to a fix.

## Found during verification, deliberately NOT fixed

At 320 px `.recent-flight__callsign` clips (a 19 px EN / 11 px FR box against a
58 px `scrollWidth`). The numbers are identical before and after the I1 fix, so
it was neither introduced nor worsened by it. Fixing it needs the column to
shrink under pressure, which a viewport media query cannot express: the row is
292 px wide at 1280 px and 308 px at 390 px, so viewport width does not predict
row width. The honest predictor is container width — a container query, which is
a layout mechanism this codebase does not yet use, and so its own plan rather
than a quick task's drive-by.

## Developer decision, 2026-09-13: 360 px is the floor

Two independent 320 px defects had accumulated (the readings table breaking mid-phrase,
the recent-flight callsign starving), and they jointly raised whether 320 px is a
supported width at all. Put to the developer with a side-by-side rendering of the same
table at 320 px and 360 px rather than as an abstract question.

**Decision: 360 px is the minimum supported width. Nothing is changed for 320 px.**

Consequences, recorded in `.claude/skills/sketch-findings-skypane/SKILL.md` so future
UI work reads them: design and measure down to 360 px; keep the existing 320 px
assertions (they pass and cost nothing); and if 320 px is ever the sole blocker on a
design, relax the width rather than contort the layout. The known 320 px imperfection
— `08:00 (il y` / `a 44 j)` instead of a clean break — is accepted as cosmetic.

The accessibility case is the one reason to revisit this: a 390 px phone becomes
roughly 320 px under a large browser font-size setting. To be revisited on a real
request, not pre-emptively.
