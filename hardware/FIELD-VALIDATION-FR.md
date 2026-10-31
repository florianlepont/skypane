# Fiche pas à pas pour le propriétaire (en français)

Cette fiche explique, étape par étape, ce que vous avez à faire pour la validation du cadre. Elle est en français simple. Vous n'avez besoin d'aucune compétence technique. À chaque étape, la ligne « A noter » dit ce qu'il faut écrire sur un papier (ou dans un message). Si quelque chose ne se passe pas comme prévu, arrêtez-vous et écrivez-moi dans le chat. Ne devinez pas.

Quelques mots :

- **Health** (« santé ») : la page du site de réglage qui montre la tension de la batterie et les heures des visites du cadre.
- **Device** (« appareil ») : la page où l'on règle l'intervalle, c'est-à-dire le temps entre deux visites du cadre.
- **Display** (« écran ») : la page où l'on allume ou éteint l'écran.
- **Visite** : le moment où le cadre se réveille et appelle le serveur. Entre deux visites, il dort.
- **Export** : un fichier qui contient la liste des visites (heure, tension de la batterie, version du logiciel, force du signal). Il ne contient rien d'autre.

Les heures sont celles de Paris. Jusqu'au 25 octobre 2026 on est à l'heure d'été (UTC+2). Après, c'est l'heure d'hiver (UTC+1).

---

## Partie A : le test de 900 secondes (revue vers le 28 octobre 2026, 19 h heure de Paris)

Le test a commencé le 23 octobre 2026 vers 6 h 25, batterie chargée la nuit, première lecture 4058 mV, câble USB débranché.

**Avant la revue : ne touchez pas au cadre.** Ne le branchez pas en USB, ne le réinitialisez pas, ne changez aucun réglage. Si le cadre a été branché en USB (même un instant), écrivez l'heure et dites-le-moi.

1. Ouvrez la page **Health** du site de réglage.
   A noter : la tension de la batterie en mV (le dernier chiffre affiché) et l'heure à laquelle vous la lisez.
2. Notez aussi l'heure de la dernière visite affichée sur la page Health.
   A noter : cette heure.
3. Faites l'export, avec les étapes ci-dessous (une seule méthode, toujours la même).

### Faire l'export (Terminal sur votre Mac)

L'export est une lecture seule : il ne change rien sur le serveur. C'est la même méthode que vous avez utilisée le 8 octobre 2026.

1. Ouvrez le Terminal : appuyez sur Cmd + Espace, tapez `Terminal`, appuyez sur Entrée. Une fenêtre avec du texte s'ouvre.
2. Copiez tout le bloc ci-dessous, de la ligne `ssh` jusqu'à la ligne `PY` (la dernière), sans rien oublier. Remplacez `<adresse du serveur>` par l'adresse du serveur, la même que pour l'export du 8 octobre. Si vous ne l'avez plus, dites-le-moi dans le chat et je vous la demanderai : elle n'est écrite nulle part dans les fichiers du projet, donc je ne l'invente pas.

```
ssh ubuntu@<adresse du serveur> "sudo python3 - '2026-10-23T04:25:00Z'" <<'PY' > ~/Desktop/export-900s.jsonl
import json, sqlite3, sys
conn = sqlite3.connect('file:/opt/skypane/state/history.db?mode=ro', uri=True)
conn.execute('PRAGMA busy_timeout=5000')
conn.row_factory = sqlite3.Row
rows = conn.execute(
    'SELECT ts, battery_mv, fw_version, boot_reason, rssi '
    'FROM device_health WHERE ts >= ? ORDER BY ts', (sys.argv[1],))
for row in rows:
    print(json.dumps(dict(row)))
PY
```

   L'heure `2026-10-23T04:25:00Z` est 6 h 25 heure de Paris moins 2 heures (Paris est à l'heure d'été, UTC+2). C'est un calcul de ma part. Elle est volontairement un peu avant le début du test.
3. Collez dans la fenêtre du Terminal (Cmd + V) et appuyez sur Entrée. Vous n'avez pas à taper de mot de passe de votre Mac : la commande « sudo » s'exécute sur le serveur, pas sur votre Mac, et le compte du serveur n'a pas besoin de mot de passe pour cela. Seules deux questions peuvent apparaître :
   - La phrase secrète de votre clé de connexion (si elle en a une). Quand vous la tapez, rien ne s'affiche : c'est normal. Tapez-la et appuyez sur Entrée.
   - Seulement la première fois depuis ce Mac : `Are you sure you want to continue connecting (yes/no)?` Tapez `yes` puis Entrée.
   Si une autre question apparaît, en particulier si on vous demande un mot de passe pour le serveur : arrêtez-vous et écrivez-moi. Ne devinez pas.
4. Attendez que le Terminal revienne à une ligne vide avec un curseur (quelques secondes).
5. Vérifiez le fichier : tapez la commande suivante puis Entrée.

```
wc -l ~/Desktop/export-900s.jsonl
```

   Le Terminal affiche un nombre suivi du nom du fichier. On attend environ 500 à 550 lignes (96 visites par jour à 900 secondes, pendant environ 5,5 jours : calcul de ma part). Si le nombre est très petit (par exemple moins de 100) ou égal à 0, n'envoyez pas le fichier et écrivez-moi.
   A noter : le nombre de lignes affiché.
6. Envoyez-moi le fichier `export-900s.jsonl` (il est sur votre Bureau) en pièce jointe dans le chat. Il contient seulement l'heure, la tension de la batterie, la version du logiciel et la force du signal.

Si le Terminal ne marche pas : une photo ou une capture d'écran de la page Health ne peut pas servir à calculer l'estimation. Dites-le-moi simplement dans le chat et nous chercherons une autre solution.

---

## Partie A bis : export automatique

Cette partie est facultative et se fait une seule fois. Une fois en place, je pourrai récupérer moi-même l'historique de la batterie, sans que vous fassiez l'export de la Partie A. La commande de la Partie A reste la solution de secours : si quelque chose ne marche pas ici, utilisez-la.

Le code secret (le « jeton ») ne doit jamais être écrit dans le chat, ni dans un mail, ni dans un fichier du projet. Il va seulement à deux endroits : le serveur et le formulaire des secrets de l'environnement.

1. **Créer le jeton.** Dans le Terminal de votre Mac, tapez la commande ci-dessous puis Entrée. Elle affiche une longue suite de lettres et de chiffres : c'est le jeton. Gardez la fenêtre ouverte, vous allez le copier deux fois.

```
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
```

2. **Le mettre sur le serveur.** Connectez-vous au serveur comme d'habitude (`ssh ubuntu@<adresse du serveur>`), puis ouvrez le fichier `/opt/skypane/skypane.env` avec `sudo nano /opt/skypane/skypane.env`. Ajoutez en bas une ligne `SKYPANE_EXPORT_TOKEN=` suivie du jeton, sans espace ni guillemets. Enregistrez (Ctrl + O, Entrée) et quittez (Ctrl + X). Puis tapez `sudo systemctl restart skypane-companion`. Si une étape affiche une erreur, arrêtez-vous et écrivez-moi sans coller le jeton.
3. **Le mettre dans le formulaire des secrets.** Dans les réglages de l'environnement claude.ai, ajoutez un secret réseau : type `Bearer`, site autorisé = l'adresse du site de réglage, préfixe de chemin `/api/export/`, en-tête `Authorization`, préfixe `Bearer`, et le jeton comme valeur. Ce formulaire est le seul endroit où le jeton se colle en dehors du serveur.

Ensuite, dites-moi simplement « c'est en place » dans le chat, sans le jeton. Pour tout arrêter plus tard, supprimez la ligne `SKYPANE_EXPORT_TOKEN` du fichier et relancez la commande `systemctl restart` : l'export automatique cesse de répondre.

---

## Partie B : choisir et appliquer l'intervalle final

À faire seulement après que je vous ai donné le résultat et la valeur à choisir.

1. Ouvrez la page **Device**.
2. Dans la case de l'intervalle, tapez la valeur en secondes que nous avons choisie ensemble.
3. Enregistrez (bouton d'enregistrement de la page).
4. Rechargez la page (touche F5 ou Cmd + R).
5. Relisez la valeur affichée : elle doit être celle que vous avez tapée.
   A noter : la valeur lue et l'heure.

---

## Partie C : vérification écran éteint

But : vérifier que, écran éteint, le cadre revient bien à une visite toutes les 5 minutes environ.

Une chose à savoir : le cadre n'apprend que l'écran est éteint par la réponse à sa prochaine visite, après avoir dormi l'intervalle qu'on lui avait déjà donné. La première attente peut donc durer aussi longtemps que l'intervalle actuel, jusqu'à 60 minutes.

À faire en journée, en dehors de la plage 23 h 30 à 6 h.

1. Ouvrez la page **Device** et lisez l'intervalle actuel en minutes (900 secondes = 15 minutes, 3600 secondes = 60 minutes).
   A noter : l'intervalle actuel en minutes et l'heure.
2. Ouvrez la page **Health** et lisez l'heure de la dernière visite affichée : c'est « la dernière visite avant T0 ». Puis, sur la page **Display**, éteignez l'écran.
   A noter : l'heure à laquelle vous avez éteint l'écran (appelons-la T0), et l'heure de la dernière visite avant T0.
3. Ouvrez la page **Health** et rechargez-la toutes les quelques minutes. La première nouvelle visite après T0 s'appelle T1. Elle peut mettre jusqu'à l'ancien intervalle à arriver.
   A noter : l'heure de T1.
4. Après T1, attendez au moins 30 minutes de plus, en notant les heures des visites affichées sur la page Health. On attend une visite toutes les 5 minutes environ après T1.
   A noter : les heures des visites.
5. Rallumez l'écran sur la page **Display**. L'image se rafraîchit à la visite suivante du cadre.
   A noter : l'heure à laquelle vous avez rallumé l'écran.

**Si vous ne pouvez pas surveiller la page :** laissez l'écran éteint pendant l'ancien intervalle plus 45 à 60 minutes, compté depuis T0. Par exemple 105 à 120 minutes si l'ancien intervalle est de 3600 secondes, ou 60 à 75 minutes s'il est de 900 secondes. Puis rallumez.
   A noter : T0, l'heure de la dernière visite avant T0, et l'heure où vous avez rallumé l'écran.

Pourquoi ces heures : l'analyse commence à la dernière visite avant T0 et met de côté le premier écart (l'ancien intervalle). Elle a besoin d'au moins 6 écarts d'environ 5 minutes ensuite.

### Export de la vérification écran éteint

Faites exactement les mêmes étapes que dans la partie A (« Faire l'export »), avec deux changements :

- le nom du fichier est `~/Desktop/export-ecran-eteint.jsonl` (à la place de `export-900s.jsonl`, dans le bloc et dans la commande `wc -l`) ;
- l'heure entre apostrophes, après `python3 -`, est T0 moins (l'ancien intervalle plus 5 minutes), convertie en heure UTC. Ainsi l'export contient certainement la dernière visite avant T0, dont l'analyse a besoin.

Exemple de conversion (un exemple, pas vos chiffres) : ancien intervalle 60 minutes, T0 = 14 h 10 à Paris le 24 octobre 2026. 14 h 10 moins 65 minutes = 13 h 05 à Paris. Paris est à l'heure d'été (UTC+2), donc on retire 2 heures : 11 h 05 UTC. On écrit `2026-10-24T11:05:00Z`. Après le 25 octobre 2026, Paris est en UTC+1 : on ne retire alors qu'1 heure.

Si vous hésitez sur la conversion, donnez-moi T0 et l'ancien intervalle dans le chat, je vous donne la ligne exacte.

---

## Partie D : contrôle de la batterie à la réception (commandée le 22 octobre 2026)

La liste complète des contrôles est dans `hardware/PACK-ACCEPTANCE.md`. Faites-les dans cet ordre.

**Ne branchez rien tant que la polarité n'est pas confirmée.** Un fil à l'envers détruit la carte et ce n'est pas réparable.

1. Lisez la référence imprimée sur la batterie.
   A noter : la référence lue. Elle doit être 333290, comme dans la commande.
2. Polarité, au multimètre, **avant** de brancher quoi que ce soit.
   Attention : ce n'est PAS la mesure de courant que vous avez refusée. Ici on mesure seulement une tension, avec la batterie seule, et rien n'est branché au cadre pour l'instant.
   - Réglez le multimètre sur la mesure de tension continue (tension continue, parfois marquée V avec un trait).
   - Posez la pointe rouge sur le contact d'un fil de la batterie et la pointe noire sur l'autre contact. Ne touchez pas les deux contacts avec la même pointe.
   - Si le multimètre affiche un nombre positif (par exemple 3,9), le fil sous la pointe rouge est le plus (+). S'il affiche un nombre négatif (par exemple -3,9), c'est l'inverse : le fil sous la pointe rouge est le moins (-).
   - Sur la carte du cadre, la broche la plus proche de la prise USB-C est le moins (-) et la plus éloignée est le plus (+).
   - Si le plus de la batterie ne correspond pas au plus de la carte : ne branchez pas, et écrivez-moi.
   A noter : la couleur du fil qui est le plus (+), et le nombre affiché par le multimètre avec son signe.
3. Place disponible : posez la batterie à plat derrière l'écran. Elle mesure 60 x 100 mm. Elle doit tenir entièrement, sans appuyer sur l'écran.
   A noter : oui ou non, et ce qui gêne éventuellement.
4. Première charge (seulement si les contrôles 1 à 3 sont bons) : branchez la batterie puis le câble USB. Regardez le voyant de charge et la tension sur la page Health. La tension doit monter jusqu'à un palier d'environ 4058 à 4112 mV. Pendant la charge, touchez de temps en temps la batterie et la carte du doigt : elles ne doivent pas devenir chaudes.
   A noter : ce que fait le voyant, l'heure de début, l'heure où le palier est atteint, et si quelque chose a chauffé. Si quelque chose chauffe, débranchez le câble USB et écrivez-moi.

---

La mesure de courant avec le multimètre en série, que vous avez refusée, reste facultative. Elle n'est jamais nécessaire pour cette phase.
