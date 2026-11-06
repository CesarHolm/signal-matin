---
name: gazette
description: Fabrique l'édition numérique quotidienne de Signal Matin en mode hybride — GitHub collecte et publie, toi tu fais rédiger tri, brèves et articles — via la branche claude/editions. Utilisée par la tâche planifiée du matin ; « essai » dans la demande produit une édition d'essai.
---

# Gazette Signal Matin (mode hybride)

Répartition du travail :
- **GitHub** (workflow `fabrication` de la branche `claude/editions`) : tout ce qui touche
  internet — flux, textes complets, PDF — puis mise en page, mémoire et e-mail. Sans IA.
- **Toi** : faire rédiger, par des sous-agents, les réponses demandées dans `a_faire/`.
  Tu n'accèdes à aucun site d'actualité et tu n'en as pas besoin.

Vous échangez les fichiers par la branche `claude/editions` : tu pousses `tour.json`
(et tes réponses), GitHub répond par `etat.json` (et les nouvelles demandes).

Règles absolues :
- Aucune information extérieure aux textes fournis. Aucune recherche web.
- Ne jamais afficher ni demander de clé ou de secret.
- Ne jamais modifier le code, la configuration ni d'autre branche que `claude/editions`.

## 1. Préparation

Depuis la racine du dépôt :

```bash
git fetch -q origin cesar/personnalisation claude/editions
git checkout -q cesar/personnalisation
git worktree add -f livraison origin/claude/editions
git -C livraison checkout -q -B claude/editions origin/claude/editions
pip install -q -e . 2>&1 | tail -1
```

Dossier de l'édition :
- édition normale : `D=livraison/editions/$(TZ=Europe/Paris date +%F)` ;
- si la demande contient « essai » : `D=livraison/editions/$(TZ=Europe/Paris date +%F)-essai-$(TZ=Europe/Paris date +%H%M)`.

Si `$D/etat.json` existe déjà avec `"termine": true` (édition normale), l'édition du jour
est déjà envoyée : arrête-toi et réponds « Édition du jour déjà produite ».

## 2. Boucle (5 tours au plus)

Tour `N` (1, 2, 3…) :

1. **Envoyer le tour à GitHub** :
   ```bash
   mkdir -p "$D"
   echo '{"tour": N, "essai": ESSAI, "final": FINAL}' > "$D/tour.json"   # ESSAI/FINAL : true ou false
   cd livraison && git add -A editions \
     && git -c user.name="Signal Matin (agent)" -c user.email="noreply@anthropic.com" commit -qm "Tour N $(basename "$D")" \
     && git pull -q --rebase origin claude/editions && git push -q origin HEAD:claude/editions; cd ..
   ```
   `ESSAI` vaut `true` pour une édition d'essai (tous les tours). `FINAL` vaut `false`, sauf au
   dernier recours (ci-dessous).
2. **Attendre la réponse** (commande longue : délai de l'outil Bash = 600000 ms) :
   ```bash
   python main.py journal-agent attendre "$D" --tour N
   ```
   - **Code 4** (délai dépassé) : relance la même commande, 2 fois au plus ; ensuite, échec (étape 4).
   - **Code 2** : le programme a échoué sur GitHub. Note la raison affichée et passe à l'étape 4.
   - **Code 0** : lis `$D/etat.json`.
     - `"termine": true` : l'édition est publiée et l'e-mail envoyé. Passe à l'étape 4 (succès).
     - sinon `"a_faire"` liste les demandes en attente : fais-les traiter (ci-dessous), lance
       `python main.py journal-agent verifier "$D"`, fais refaire **une fois** les réponses
       signalées (en donnant le problème au sous-agent), puis passe au tour `N+1`.

Ordre normal : tour 1 = collecte et demandes de tri ; tour 2 = textes et demandes d'articles
et de brèves ; tour 3 = édition terminée.

**Dernier recours** : si une demande reste sans réponse valable après la seconde tentative, ou
au 4e tour non terminé, envoie le tour suivant avec `"final": true` : GitHub termine l'édition
avec les sections manquantes signalées en tête de l'e-mail.

### Faire traiter les demandes

Chaque fichier `a_faire/<id>.json` contient : `modele` (haiku ou sonnet), `systeme` (la
consigne), `contenu` (le message à traiter), `schema` (format JSON attendu), `sortie` (fichier
à écrire) et parfois `limite_caracteres`.

Regroupe les demandes pour limiter le nombre de sous-agents :
- toutes les demandes `haiku` (tri-*, mots, breves) : **un seul** sous-agent, modèle `haiku` ;
- les demandes `sonnet` (syn-*) : des sous-agents de modèle `sonnet`, **4 demandes au plus** chacun.

Lance tous les sous-agents d'un même tour **en parallèle** (outil Agent, type
`general-purpose`, paramètre `model` = `haiku` ou `sonnet`), avec ce message, en
remplaçant la liste par des chemins absolus :

> Pour chacun de ces fichiers, l'un après l'autre : <D>/a_faire/<id>.json, …
> Lis le fichier. Le champ « systeme » est ta consigne, le champ « contenu » le message à traiter.
> Applique la consigne au contenu à la lettre, en français, sans aucune information extérieure
> au contenu, sans recherche web et sans ouvrir d'autre fichier. Écris uniquement l'objet JSON de
> ta réponse, conforme au champ « schema », dans le fichier <D>/<sortie> (UTF-8, rien autour).
> Si « limite_caracteres » est indiqué, le total chapô + intertitres + textes des sections +
> synthèse doit faire 90 à 100 % de cette limite : compte-le avec Python avant d'écrire et ajuste.
> Si le contenu réunit plusieurs SOURCES, rédige un seul article à partir de toutes celles qui
> traitent du même fait (voir la consigne de vérification en tête du contenu).
> Termine par une ligne par fichier : « <id> OK » ou « <id> PROBLÈME : … ».

Tu ne rédiges pas toi-même et tu ne lis pas les textes des articles : tu coordonnes. Si un
sous-agent échoue, relance-le une fois pour les fichiers concernés.

## 3. Ce que tu ne fais pas

- Pas de `journal-agent avancer` ni `publier` dans ta session : GitHub s'en charge.
- Pas de collecte, pas de `curl`, pas de recherche web.

## 4. Compte rendu

Termine par **une seule ligne** :
- succès : « Édition <date> livrée : N articles, M brèves » (d'après la fin du journal de
  `etat.json`, + « incomplète : … » si des sections manquent) ;
- échec : « ÉCHEC gazette <date> : <raison en une phrase> ». Cesar relancera l'édition à la main.
