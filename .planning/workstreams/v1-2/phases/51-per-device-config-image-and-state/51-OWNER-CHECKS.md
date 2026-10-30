# Phase 51 — Vérifications pour le propriétaire

**Rien n'est déployé en production.** Ces vérifications se font sur un
ordinateur de développement, avec deux cadres simulés. Le cadre réel d'Orly
n'est pas touché, et aucun serveur de production n'est contacté.

À ne PAS faire : ne lancez aucun déploiement en production (ni `deploy.sh`,
`activate.sh` ou `provision.sh`) tant que la phase 47 n'est pas terminée et
que vous n'avez pas décidé vous-même de passer en production.

## Préparation (une seule fois)

Dans un terminal, depuis le dossier du projet (`/home/user/skypane`) :

1. Créez un dossier d'essai et remplissez-le avec le cadre d'Orly et deux
   cadres simulés :

   ```
   D=$(mktemp -d)
   SKYPANE_SIM_HARDWARE=1 PYTHONPATH=.:test-support server/.venv/bin/python3 \
     -c "import sys; from skypane_two_device_fleet import seed_two_device_fleet as s; s(sys.argv[1])" "$D"
   echo "$D"
   ```

2. Lancez le compagnon sur votre machine uniquement :

   ```
   SKYPANE_SIM_HARDWARE=1 SKYPANE_COMPANION_PASSWORD=essai-local \
     server/.venv/bin/python3 -m companion.app --bind 127.0.0.1 --port 8099 --state-dir "$D"
   ```

3. Ouvrez http://127.0.0.1:8099 dans votre navigateur et entrez le mot de
   passe `essai-local`.

**Attention : un deuxième cadre doit toujours être ajouté avec
`--state-path auto`** (`fleet_cli devices add ... --state-path auto`). Sans
cela, il partagerait l'état du cadre d'Orly (image, historique, batterie) ;
l'outil refuse désormais cet ajout dès qu'un cadre d'Orly existe.

Les deux cadres simulés s'appellent `sim-1` et `sim-2`. Le cadre d'Orly
s'appelle « Cadre d'Orly » (ou « Orly frame » en anglais).

## Les vérifications

1. **Le sélecteur de cadre.** En haut de chaque page, sous le titre, vous
   devez voir une liste intitulée « Cadre » avec trois choix : le cadre
   d'Orly en premier, puis `sim-1` et `sim-2`. Choisissez `sim-1`.
   Résultat attendu : la page se recharge et l'adresse du navigateur contient
   `/devices/…` ; le menu (Accueil, Affichage, Vols, Compagnies, Santé,
   Appareil) garde ce cadre quand vous changez de page.

2. **Passer d'un cadre à l'autre.** Choisissez `sim-2`, puis le cadre d'Orly.
   Résultat attendu : chaque cadre montre ses propres informations ; il n'y a
   jamais de retour automatique vers un autre cadre. Une adresse avec un
   identifiant inventé (par exemple `/devices/d_00000000/`) affiche une page
   « introuvable », pas le cadre d'Orly.

3. **« Vérifier maintenant » pour un seul cadre.** Sélectionnez `sim-1`,
   ouvrez la page Appareil et appuyez sur « Actualiser maintenant ».
   Résultat attendu : un message « Vérification terminée » confirme la
   vérification pour `sim-1` seulement. Revenez sur `sim-2` et sur le cadre d'Orly : leur dernière
   vérification n'a pas changé. (Sur votre machine, cette vérification
   interroge les sources publiques de vols ; sans connexion elle peut
   indiquer qu'elle n'a pas abouti, ce qui est normal pour l'essai.)
   Un second appui juste après est refusé poliment (le bouton reste désactivé pendant le délai d'attente).

4. **Heures calmes et fuseau horaire d'un seul cadre.** Sélectionnez `sim-1`,
   ouvrez Affichage, changez les heures calmes (début et fin) et choisissez un
   autre « Fuseau horaire » (par exemple Martinique), puis enregistrez.
   Résultat attendu : un message de confirmation ; la page `sim-1` affiche les
   nouvelles valeurs. Ouvrez `sim-2` et le cadre d'Orly : leurs heures calmes
   et leur fuseau sont inchangés. Un fuseau qui n'est pas dans la liste doit
   être refusé avec le message « Choisissez un fuseau horaire dans la
   liste. »

5. **Cadre jamais vu.** Un cadre qui n'a encore jamais contacté le serveur
   s'affiche dans la liste avec « pas encore vu » et un petit badge « Pas
   encore vu ». Ouvrez ses pages Accueil, Santé et Historique.
   Résultat attendu : des messages clairs d'état vide (rien de ce cadre n'est
   encore arrivé), sans erreur et sans reprendre les données d'un autre cadre.
   Un cadre qui ne se manifeste plus depuis longtemps affiche « hors ligne »
   de la même façon.

6. **Le cadre d'Orly est inchangé.** Choisissez le cadre d'Orly et parcourez
   Accueil, Affichage, Vols, Compagnies, Santé, Appareil et Mise à jour.
   Résultat attendu : ces pages ressemblent à ce que vous connaissiez ; leurs
   adresses n'ont pas de `/devices/…`. La page « Mise à jour » est la même
   pour tous les cadres (elle n'est jamais préfixée par un cadre).

7. **Un seul cadre : rien de nouveau.** (Facultatif.) Si le dossier d'essai
   ne contient que le cadre d'Orly, aucun sélecteur n'apparaît et les pages
   sont identiques à avant.

Quand vous avez fini : arrêtez le compagnon avec Ctrl+C dans son terminal.

## Ce qui reste de votre côté

- Décider quand (et si) passer en production : pas avant la fin de la
  phase 47 et votre feu vert explicite.
- Tester avec un vrai second cadre ou une seconde carte quand vous en aurez
  un (la matière actuelle simule seulement le comportement).
- Décider du sort des points en suspens listés ci-dessous (espacement des
  appels aux fournisseurs de vols, rendu par type de matériel).

---

## For the verifier (English)

Facts to confirm:

- `devices.id` is text (`d_` plus 8 hex), so per-device directories are
  `devices/d_xxxxxxxx` (the context assumed a numeric id).
- Poll-now is refused for hardware that is not 1200x1600 until per-hardware
  rendering exists.
- Update stays global: its link is never prefixed with `/devices/<id>`.
- Non-live image URLs have the shape `/img/<id>/<sha>.bin`; the live frame
  keeps `/img/<sha>.bin`.
- Rollback note: the previous release ignores `devices/` and the `timezone`
  key in device config, so rolling back leaves the live frame working.
- Provider-spacing between devices (shared polling budget) is deferred to the
  fleet-budget phase.
- No deploy, activate or provision command was run.
