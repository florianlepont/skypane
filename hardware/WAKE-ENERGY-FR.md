# Fiche pas à pas pour le propriétaire : mesurer l'énergie d'un réveil (en français)

Cette fiche explique, étape par étape, ce que vous avez à faire pour la mise à jour de test du cadre. Elle est en français simple. Vous n'avez besoin d'aucune compétence technique. Si quelque chose ne se passe pas comme prévu, arrêtez-vous et écrivez-moi dans le chat. Ne devinez pas.

Règles qui valent pour toute la fiche :

- **C'est vous qui décidez et qui cliquez.** Je ne fusionne rien, je ne crée aucune version, je n'approuve aucune étape sur GitHub, je ne planifie aucune installation, je ne branche rien sur le cadre et je ne mets rien en ligne à votre place.
- **Ne me donnez jamais de secret.** Ne collez et ne tapez dans le chat aucun mot de passe, aucune clé, aucun jeton (« token »). Je n'en ai pas besoin. Si un écran vous en demande un, arrêtez-vous et écrivez-moi.
- **Vous pouvez vous arrêter après n'importe quelle étape.** Rien ne force à aller jusqu'au bout.

Quelques mots :

- **Réveil** (ou **visite**) : le moment où le cadre se réveille, appelle le serveur, puis se rendort. Entre deux réveils, il dort.
- **Version du logiciel** (« firmware ») : le programme qui tourne dans le cadre. Une version s'appelle par exemple `fw-v1.0.2`.
- **Tag** : une étiquette qui donne son nom à une version dans GitHub. Pousser un tag, c'est annoncer « voici une nouvelle version ».
- **Pull request** : la proposition de changement sur GitHub. La « fusionner », c'est l'accepter.
- **Export** : la liste des réveils (heure, tension de la batterie, version, et maintenant les durées de chaque phase du réveil). Lecture seule.
- **mV** : millivolt, l'unité de la tension de la batterie. 3500 mV est une batterie très basse.

Ce qui est **vérifié** (je l'ai lu dans les fichiers du projet) est dit tel quel. Ce qui est **supposé** ou **non encore vérifié** est dit aussi.

---

## Partie A : mise à jour de test, mesurer ce que le cadre consomme à chaque réveil

### 1. Ce qui change, ce qui ne change pas, ce que ça coûte

**Ce qui change.** À chaque réveil, le cadre enverra en plus un petit message de chiffres : combien de temps a duré chaque phase du réveil précédent (démarrage, Wi-Fi, demande de l'image, téléchargement, dessin sur l'écran). Le serveur les range dans l'historique, à côté de la tension de la batterie.

**Ce qui ne change pas.** Rien de ce que le cadre affiche, ni quand il se réveille :

- le dessin de l'écran est le même ;
- l'intervalle entre deux réveils est le même ;
- les heures calmes, l'écran éteint et la protection quand la batterie est presque vide fonctionnent comme avant ;
- le cadre ne fait aucune demande de plus au serveur, et n'écrit rien de plus dans sa mémoire permanente (les chiffres restent dans une petite mémoire qui tient pendant le sommeil).

Cela, je l'ai vérifié en relisant le code. Je n'ai **pas** pu le mesurer sur le vrai cadre : le coût réel de ces ajouts n'est pas mesuré. D'après la relecture, il est négligeable.

**Ce que ça coûte.**

- La mise à jour elle-même consomme, une seule fois, à peu près l'équivalent de trois rafraîchissements d'écran de batterie. C'est une estimation de ma part, pas une mesure.
- Pendant la mise à jour, la page Health montrera un petit trou dans la tension de la batterie et un nouveau numéro de version. C'est normal.
- Le test de l'ancienne batterie ne doit plus être en cours. Selon votre propre règle, la fenêtre de mesure de 3600 secondes doit être terminée avant de commencer.

**Ce que les chiffres pourront dire, et ce qu'ils ne diront peut-être pas.**

- Pour calculer l'énergie d'un réveil, il faut une période de mesure d'au moins 14 jours avec le même intervalle. Avant cela, je peux montrer les durées mesurées par le cadre, mais pas une énergie.
- Le modèle peut **refuser** de donner un chiffre d'énergie. C'est un résultat possible, pas une panne. Il est probable, parce que l'image change presque à chaque réveil chez vous : les réveils se ressemblent trop pour séparer les causes. Dans ce cas il dit exactement quelle donnée manque, par exemple une seconde période de 14 jours avec un autre intervalle. Je vous le demanderai alors, et c'est vous qui déciderez.
- Tous les chiffres d'énergie sont des estimations faites à partir de la tension et des durées, sur la capacité annoncée de la batterie. Ce ne sont pas des mesures de courant.

### 2. Avant de commencer : trois vérifications

Rien ne commence tant que ces trois points ne sont pas réglés.

1. **Le bilan du 7 novembre 2026 est fait.** *Vous* me confirmez dans le chat que le bilan est terminé et que la fenêtre de mesure de 3600 secondes est fermée. Si vous voulez quand même faire la mise à jour pendant cette fenêtre, vous me le dites clairement : c'est votre choix, mais les chiffres de la fenêtre ne seront plus comparables.
2. **Le programme du cadre n'a pas encore été compilé pour la puce du cadre dans mon environnement de travail.** Je n'ai pas pu lancer la compilation ici (le service qui sert à compiler n'était pas disponible). Les tests qui n'ont pas besoin du cadre passent, mais ce n'est pas la même chose. *Moi*, je regarde le résultat de la compilation faite par GitHub (le contrôle appelé « Firmware Build »). *Vous ne créez aucune version tant que ce contrôle n'est pas vert.* S'il est rouge, j'explique pourquoi et je corrige, et on attend.
3. **La batterie du cadre est au-dessus de 3500 mV** sur la page Health. À 3500 mV ou moins, le cadre refuse la mise à jour (étape 6). *Vous* notez la tension affichée et la version actuelle du cadre, c'est-à-dire la ligne « Sur le cadre : … » de la page Mise à jour (c'est la version à laquelle on reviendra en cas de souci, étape 8).

Conseil, qui est aussi la règle de travail retenue : ne branchez pas la nouvelle batterie de remplacement le même jour. Ainsi, les données de cette batterie restent bien à part. Dites-moi si vous préférez autrement.

### 3. D'abord le serveur (rien ne change encore sur le cadre)

Le serveur doit savoir ranger les nouveaux chiffres **avant** que le cadre les envoie.

1. *Vous* : ouvrez la pull request sur GitHub et lisez-la. Le texte dit ce qui change. Si une phrase vous inquiète, demandez-moi.
2. *Vous* : si vous êtes d'accord, cliquez sur le bouton vert de fusion (« Merge pull request »), puis confirmez. Moi, je ne le fais pas.
3. *Vous* : GitHub lance alors une mise en ligne du serveur qui attend votre accord. Dans GitHub, ouvrez l'onglet **Actions**, cliquez sur la ligne la plus récente du flux « CI », puis cliquez sur le bouton **Review deployments** (« examiner les déploiements »), cochez **production** et validez. Les noms exacts des boutons viennent de GitHub, pas du projet : s'ils sont un peu différents chez vous, dites-moi ce que vous voyez. Cette étape met en ligne le **serveur seulement**. Rien n'arrive au cadre.
4. *Moi* : une fois la mise en ligne terminée, je lis l'export par le service de réseau de la plateforme. Je ne vois jamais le jeton, vous ne me le donnez pas. J'attends de voir les treize nouvelles colonnes, **vides** pour tous les anciens réveils (par exemple `wake_seq` vaut « null »). Si l'accès à l'export n'est pas disponible, je vous le dis ; il ne faut rien me coller.
5. *Moi* : je vous dis « le serveur est prêt » ou ce qui ne va pas. On ne passe à l'étape suivante que sur « prêt ».

### 4. La porte de signature (une version du programme du cadre)

Chaque version doit être signée, sinon le cadre la refuse. La clé de signature reste dans GitHub : ni vous ni moi ne la voyons ni ne la manipulons.

1. *Moi* : je propose le numéro de la nouvelle version, plus grand que la dernière publiée (le serveur refuse un numéro plus petit ou égal). Le format est `fw-v` suivi de trois nombres, par exemple `fw-v1.0.3`. *Vous* validez le numéro.
2. *Vous* : créez le tag sur la version fusionnée de la branche principale (`main`). Si vous préférez, dites-moi « donne-moi la commande » : je vous écris les deux lignes exactes à copier dans le Terminal. Elles ne contiennent aucun secret. Je ne les lance pas moi-même.
3. *Vous* : GitHub démarre la fabrication et la signature. Elle attend **votre** accord. Dans l'onglet **Actions**, ouvrez la ligne du flux de la version (fichier `firmware-release`), cliquez sur **Review deployments**, cochez **firmware-signing** et validez. Seul le relecteur désigné, c'est-à-dire vous, peut le faire. C'est voulu.
4. *Moi* : je regarde que la fabrication et la vérification de la signature réussissent. S'il y a une erreur, je vous l'explique et rien n'est publié.

### 5. La porte de mise en ligne (rendre la version disponible)

1. Quand la signature réussit, GitHub lance de lui-même une dernière mise en ligne, qui attend encore votre accord.
2. *Vous* : dans **Actions**, ouvrez la nouvelle ligne du flux « CI » qui vient d'apparaître, cliquez sur **Review deployments**, cochez **production** et validez.
3. Résultat : la version est **disponible** sur la page Mise à jour. Rien n'est installé : le cadre ne change pas tant que vous ne le demandez pas (étape suivante).

### 6. Installer la version depuis la page Mise à jour

1. *Vous* : ouvrez le site de réglage, puis la page **Mise à jour** (dans le groupe « Avancé »). Elle montre une carte **« Mise à jour disponible »** avec un bouton **« Installer fw-v… »**. Dessous, la liste **« Versions »** montre toutes les versions publiées.
2. *Vous* : cliquez sur **Installer**. Une page de confirmation demande « Installer le firmware … ? » et dit que le cadre téléchargera la version à son prochain réveil, vers une heure donnée. Pendant les heures calmes, elle dit « à la fin des heures calmes ». Pour renoncer, il y a **Annuler**.
3. *Vous* : confirmez. La carte passe à **« Mise à jour planifiée »**. Tant que le cadre ne s'est pas réveillé, un bouton **Annuler** reste disponible.
4. *Le cadre* installe la version à son prochain réveil, donc au plus tard après un intervalle. L'écran montre brièvement une page « mise à jour en cours », puis redevient normal. Le cadre garde la nouvelle version seulement après un premier contact réussi avec le serveur ; sinon il revient tout seul à l'ancienne.
5. **Si la batterie est à 3500 mV ou moins**, le cadre **refuse** la mise à jour pour ne pas risquer de s'éteindre en route (c'est vérifié dans le programme : « à ou en dessous de 3500 mV »). La version reste l'ancienne. Je n'ai pas vérifié s'il réessaie tout seul aux réveils suivants : si rien ne se passe après deux ou trois réveils, dites-le-moi, on rechargera ou on attendra.

### 7. Comment savoir que ça a marché

1. *Vous* : au prochain réveil, la page **Health** affiche le **nouveau numéro de version**, et la carte de la page Mise à jour dit **« Le cadre est à jour »**. Dites-moi « le cadre est à jour » et le numéro que vous voyez.
2. *Moi* : je lis l'export (par le service de réseau de la plateforme, sans que vous ayez rien à coller, et sans mot de passe ni jeton). Je cherche des durées plausibles dans `wake_seq`, `boot_ms`, `wifi_ms` et les colonnes `prev_…`.
3. **Normal** : le premier réveil après la mise à jour n'a pas encore les chiffres du réveil précédent, c'est normal. Après une mise à jour, le cadre redémarre au lieu de dormir, donc il n'a rien à raconter sur le réveil d'avant. Je vérifie donc avec le **deuxième** réveil après l'installation. Une case vide sur le premier n'est pas une panne.
4. *Moi* : je contrôle aussi que le cadre garde ses chiffres pendant le sommeil (un réveil ultérieur doit citer le numéro du réveil précédent). Si oui, je vous dis « les chiffres arrivent bien ».
5. Ensuite, l'énergie ne se calcule pas tout de suite : il faut la période d'au moins 14 jours évoquée plus haut.

### 8. Le chemin du retour

Revenir à la version d'avant est permis et sans danger : les anciennes versions restent toutes sur le serveur.

1. *Vous* : sur la même page **Mise à jour**, ouvrez la ligne de la version d'avant dans la liste **« Versions »** (celle que vous avez notée à l'étape 2, par exemple `fw-v1.0.2` si c'est bien elle ; je n'ai pas pu vérifier le nom exact dans les fichiers du projet, d'où votre note). Le bouton discret s'appelle **« Revenir à fw-v… »**. Cliquez dessus, puis confirmez.
2. Le cadre fait le retour à son prochain réveil, comme pour une installation. Il garde les mêmes règles, dont le refus à 3500 mV ou moins.
3. **Si la nouvelle version démarre mal toute seule**, le cadre revient de lui-même à l'ancienne. La page Mise à jour montre alors **« Firmware rétabli »** ou **« Échec de l'installation »**. Dans ce cas, ne faites rien de plus et écrivez-moi.
4. **Si le cadre affiche un écran d'erreur ou ne se réveille plus** : ne le débranchez pas et n'essayez rien. Dites-moi ce que vous voyez et depuis quand. En dernier recours, il existe une remise du programme par le câble USB. C'est une opération délicate, que je ne vous ferai suivre pas à pas **que si vous me le demandez**. Elle n'a normalement pas lieu d'être : les contrôles de signature et le retour automatique existent justement pour l'éviter.

### Récapitulatif : qui fait quoi

| Étape | Qui |
|-------|-----|
| Confirmer le bilan du 7 novembre et la fenêtre fermée | vous |
| Vérifier que la compilation GitHub est verte | moi |
| Fusionner la pull request | vous |
| Approuver la mise en ligne du serveur (« production ») | vous |
| Vérifier les nouvelles colonnes vides dans l'export | moi |
| Créer le tag de la version | vous (je peux écrire la commande) |
| Approuver la signature (« firmware-signing ») | vous |
| Approuver la mise en ligne de la version (« production ») | vous |
| Cliquer sur Installer dans la page Mise à jour | vous |
| Revenir à l'ancienne version si besoin | vous |
| Lire l'export et dire si les chiffres sont plausibles | moi |

Dans tous les cas : aucun mot de passe, aucune clé et aucun jeton ne passe par le chat.
