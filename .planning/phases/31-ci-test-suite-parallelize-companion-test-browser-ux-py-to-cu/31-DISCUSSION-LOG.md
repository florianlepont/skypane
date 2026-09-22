# Phase 31: CI test suite — parallelize companion/test_browser_ux.py - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-09-22
**Phase:** 31-ci-test-suite-parallelize-companion-test-browser-ux-py-to-cu
**Areas discussed:** Ampleur du refactor, Mécanisme de parallélisation, Budget cible

---

## Ampleur du refactor (scope / risk appetite)

| Option | Description | Selected |
|--------|-------------|----------|
| Incrémentale | Extraire 2-3 gros groupes de scénarios d'abord, mesurer, puis décider de continuer | ✓ |
| Tout d'un coup | Découper la totalité du fichier en une seule phase | |
| Laisser le planner décider | Pas de décision figée, le planner évalue pendant research/plan | |

**User's choice:** Incrémentale.

| Option (critère de continuation) | Description | Selected |
|--------|-------------|----------|
| Gain proportionnel mesuré | ≥~30-40% de temps de mur gagné sur le job CI "test" valide la poursuite | ✓ |
| Continuer systématiquement | Une deuxième phase est planifiée peu importe le gain mesuré | |
| À revoir ensemble après coup | Pas de critère fixé à l'avance | |

**User's choice:** Gain proportionnel mesuré (≥~30-40%).
**Notes:** L'utilisateur a explicitement rejeté le découpage complet en une seule phase — le fichier est le plus gros et le plus documenté du repo (150+ scénarios enchaînés, `EXPECTED_CHECK_COUNT` global), jugé trop risqué à traiter d'un coup.

---

## Mécanisme de parallélisation

| Option | Description | Selected |
|--------|-------------|----------|
| Pool local existant | Les fichiers extraits rejoignent HARNESSES de scripts/run_all_tests.py, aucun changement CI YAML | ✓ |
| Matrix GitHub Actions | Chaque groupe sur son propre runner, plus de cœurs mais setup dupliqué (~35s/shard) | |
| Les deux, à évaluer par le planner | Comparaison chiffrée une fois le découpage fait | |

**User's choice:** Pool local existant.
**Notes:** Aucun changement à `.github/workflows/ci.yml` attendu pour cette phase.

---

## Budget cible

| Option | Description | Selected |
|--------|-------------|----------|
| Pas de cible fixe | "Nettement plus rapide qu'aujourd'hui" suffit, arrêt aux rendements décroissants | ✓ |
| Cible chiffrée | Objectif précis fixé maintenant (ex: job "test" sous 2-3 minutes) | |

**User's choice:** Pas de cible fixe.

---

## Claude's Discretion

- Frontières exactes des 2-3 groupes de scénarios extraits dans cette phase (suivre les zones fonctionnelles naturelles de l'app : Vols, Compagnies, Paramètres, État, Calendrier, thème, uploads, cibles tactiles).
- Chaque fichier extrait lance sa propre instance `companion/app.py` + son propre `browser` Playwright, comme tous les autres harnesses `companion/test_*.py` existants.
- Factorisation ou duplication des helpers partagés (`_login`, `_wait_for_bar`, `seed_state_dir`, etc.) entre l'ancien fichier et les nouveaux.
- Chaque fichier extrait garde son propre `EXPECTED_CHECK_COUNT`, conforme à la convention D-07 (Phase 4) déjà suivie par tous les harnesses du repo.

## Deferred Ideas

- Décomposition complète du reste de `companion/test_browser_ux.py` au-delà des 2-3 premiers groupes — conditionnée au critère de gain mesuré (D-05) d'une phase future.
- Matrix GitHub Actions — explicitement écarté pour cette phase, à reconsidérer seulement si le pool local se révèle limité par les 4 cœurs du runner CI même après extraction.
- Cache du téléchargement Chromium de Playwright en CI (~20s/run, non lié au goulot d'étranglement principal) — repéré pendant l'investigation initiale, hors scope de cette phase.
